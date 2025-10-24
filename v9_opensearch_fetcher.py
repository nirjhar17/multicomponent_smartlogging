"""
OpenSearch Log Fetcher for v9
Fetches logs from OpenSearch instead of using oc commands
"""

from opensearchpy import OpenSearch
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

class OpenSearchLogFetcher:
    """Fetch logs from OpenSearch for multi-component analysis"""
    
    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        use_ssl: bool = True,
        verify_certs: bool = True
    ):
        """Initialize OpenSearch client"""
        self.client = OpenSearch(
            hosts=[f'https://{endpoint}'],
            http_auth=(username, password),
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            timeout=30
        )
        print(f"✅ Connected to OpenSearch: {endpoint}")
    
    def fetch_logs(
        self,
        component_type: str,
        device_name: Optional[str] = None,
        namespace: Optional[str] = None,
        pod_name: Optional[str] = None,
        time_range: str = '1h',
        max_logs: int = 1000,
        level_filter: Optional[List[str]] = None
    ) -> str:
        """
        Fetch logs from OpenSearch for a specific component
        
        Args:
            component_type: 'storage', 'server', 'database', 'kubernetes', 'firewall'
            device_name: Device/host name to filter (optional)
            namespace: K8s namespace (for kubernetes type)
            pod_name: Pod name (for kubernetes type)
            time_range: Time range like '1h', '6h', '24h'
            max_logs: Maximum number of logs to return
            level_filter: Filter by log level (e.g., ['ERROR', 'CRITICAL'])
        
        Returns:
            Formatted log string ready for RAG analysis
        """
        
        # Map component type to index pattern
        index_patterns = {
            'storage': 'storage-*',
            'server': 'server-*',
            'database': 'database-*',
            'kubernetes': 'kubernetes-*',
            'firewall': 'firewall-*'
        }
        
        index = index_patterns.get(component_type, '*-*')
        
        # Build query
        must_clauses = [
            {'range': {'@timestamp': {'gte': f'now-{time_range}'}}}
        ]
        
        # Add component-specific filters
        if component_type == 'kubernetes':
            if namespace:
                must_clauses.append({'term': {'namespace.keyword': namespace}})
            if pod_name:
                must_clauses.append({'term': {'pod_name.keyword': pod_name}})
        elif component_type in ['storage', 'server', 'database', 'firewall']:
            if device_name:
                # Try different field names for device (use .keyword for exact match)
                should_clauses = [
                    {'term': {'device.keyword': device_name}},
                    {'term': {'host.keyword': device_name}}
                ]
                must_clauses.append({'bool': {'should': should_clauses, 'minimum_should_match': 1}})
        
        # Add level filter (use .keyword for exact match)
        if level_filter:
            must_clauses.append({'terms': {'level.keyword': level_filter}})
        
        query_body = {
            'query': {
                'bool': {
                    'must': must_clauses
                }
            },
            'size': max_logs,
            'sort': [{'@timestamp': 'desc'}]
        }
        
        # Execute query
        try:
            result = self.client.search(index=index, body=query_body)
            hits = result['hits']['hits']
            total = result['hits']['total']['value']
            
            print(f"📊 Fetched {len(hits)} logs (total: {total}) from {index}")
            
            # Format logs for RAG system
            formatted_logs = []
            for hit in hits:
                log = hit['_source']
                
                # Format based on component type
                if component_type == 'kubernetes':
                    log_line = (
                        f"[{log.get('@timestamp', 'N/A')}] "
                        f"{log.get('level', 'INFO')} | "
                        f"Pod: {log.get('pod_name', 'N/A')} | "
                        f"Namespace: {log.get('namespace', 'N/A')} | "
                        f"{log.get('message', '')}"
                    )
                elif component_type == 'storage':
                    log_line = (
                        f"[{log.get('@timestamp', 'N/A')}] "
                        f"{log.get('level', 'INFO')} | "
                        f"Device: {log.get('device', 'N/A')} | "
                        f"{log.get('message', '')}"
                    )
                elif component_type in ['server', 'database']:
                    log_line = (
                        f"[{log.get('@timestamp', 'N/A')}] "
                        f"{log.get('level', 'INFO')} | "
                        f"Host: {log.get('host', 'N/A')} | "
                        f"{log.get('message', '')}"
                    )
                elif component_type == 'firewall':
                    log_line = (
                        f"[{log.get('@timestamp', 'N/A')}] "
                        f"{log.get('level', 'INFO')} | "
                        f"Device: {log.get('device', 'N/A')} | "
                        f"Action: {log.get('action', 'N/A')} | "
                        f"{log.get('message', '')}"
                    )
                else:
                    log_line = (
                        f"[{log.get('@timestamp', 'N/A')}] "
                        f"{log.get('level', 'INFO')} | "
                        f"{log.get('message', '')}"
                    )
                
                formatted_logs.append(log_line)
            
            return "\n".join(formatted_logs)
            
        except Exception as e:
            print(f"❌ Error fetching logs: {e}")
            return f"Error fetching logs: {e}"
    
    def fetch_multi_component_logs(
        self,
        time_range: str = '1h',
        level_filter: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Fetch logs from ALL components for correlation analysis
        
        Returns:
            Dictionary mapping component type to log string
        """
        components = ['storage', 'server', 'database', 'kubernetes', 'firewall']
        all_logs = {}
        
        print(f"\n🔍 Fetching logs from all components...")
        for component in components:
            logs = self.fetch_logs(
                component_type=component,
                time_range=time_range,
                level_filter=level_filter
            )
            all_logs[component] = logs
        
        return all_logs
    
    def get_namespace_list(self) -> List[str]:
        """Get list of unique OpenShift namespaces from openshift-logs index"""
        try:
            result = self.client.search(
                index='openshift-logs',
                body={
                    'size': 0,
                    'aggs': {
                        'namespaces': {
                            'terms': {
                                'field': 'kubernetes.namespace_name.keyword',
                                'size': 100,
                                'order': {'_count': 'desc'}
                            }
                        }
                    }
                }
            )
            
            namespaces = [bucket['key'] for bucket in result['aggregations']['namespaces']['buckets']]
            print(f"✅ Found {len(namespaces)} OpenShift namespaces")
            return namespaces
            
        except Exception as e:
            print(f"⚠️  Error getting namespace list: {e}")
            # Return some defaults if OpenSearch query fails
            return ["default", "kube-system"]
    
    def get_pod_list(self, namespace: str) -> List[str]:
        """Get list of unique pods for a specific OpenShift namespace (from logs AND events)"""
        try:
            # Query 1: Get pods from regular container logs
            result1 = self.client.search(
                index='openshift-logs',
                body={
                    'size': 0,
                    'query': {
                        'term': {
                            'kubernetes.namespace_name.keyword': namespace
                        }
                    },
                    'aggs': {
                        'pods': {
                            'terms': {
                                'field': 'kubernetes.pod_name.keyword',
                                'size': 100,
                                'order': {'_count': 'desc'}
                            }
                        }
                    }
                }
            )
            
            pods_from_logs = [bucket['key'] for bucket in result1['aggregations']['pods']['buckets']]
            
            # Query 2: Get pods from EventRouter events (for pods that never started)
            result2 = self.client.search(
                index='openshift-logs',
                body={
                    'size': 0,
                    'query': {
                        'bool': {
                            'must': [
                                {'term': {'kubernetes.namespace_name.keyword': 'openshift-logging'}},
                                {'match': {'kubernetes.pod_name': 'eventrouter'}},
                                {'term': {'kubernetes.event.involvedObject.namespace.keyword': namespace}},
                                {'term': {'kubernetes.event.involvedObject.kind.keyword': 'Pod'}}
                            ]
                        }
                    },
                    'aggs': {
                        'pods': {
                            'terms': {
                                'field': 'kubernetes.event.involvedObject.name.keyword',
                                'size': 100,
                                'order': {'_count': 'desc'}
                            }
                        }
                    }
                }
            )
            
            pods_from_events = [bucket['key'] for bucket in result2['aggregations']['pods']['buckets']]
            
            # Combine and deduplicate
            all_pods = sorted(set(pods_from_logs + pods_from_events))
            
            print(f"✅ Found {len(all_pods)} pods in namespace '{namespace}' ({len(pods_from_logs)} from logs, {len(pods_from_events)} from events)")
            return all_pods
            
        except Exception as e:
            print(f"⚠️  Error getting pod list for namespace '{namespace}': {e}")
            return []
    
    def get_device_list(self, component_type: str) -> List[str]:
        """Get list of unique devices/hosts for a component type"""
        index_patterns = {
            'storage': 'storage-*',
            'server': 'server-*',
            'database': 'database-*',
            'kubernetes': 'kubernetes-*',
            'firewall': 'firewall-*'
        }
        
        index = index_patterns.get(component_type, '*-*')
        
        # Get unique device names
        field = 'device' if component_type in ['storage', 'firewall'] else 'host'
        if component_type == 'kubernetes':
            field = 'pod_name'
        
        try:
            result = self.client.search(
                index=index,
                body={
                    'size': 0,
                    'aggs': {
                        'devices': {
                            'terms': {
                                'field': f'{field}.keyword' if field != 'pod_name' else 'pod_name.keyword',
                                'size': 100
                            }
                        }
                    }
                }
            )
            
            devices = [bucket['key'] for bucket in result['aggregations']['devices']['buckets']]
            return devices
            
        except Exception as e:
            print(f"⚠️  Error getting device list: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test OpenSearch connection"""
        try:
            info = self.client.info()
            print(f"✅ OpenSearch connection OK")
            print(f"   Cluster: {info['cluster_name']}")
            print(f"   Version: {info['version']['number']}")
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False


# Initialize from environment variables
def create_opensearch_fetcher() -> OpenSearchLogFetcher:
    """Create OpenSearch fetcher from environment variables"""
    endpoint = os.getenv(
        'OPENSEARCH_ENDPOINT',
        'search-aiops-logs-public-6vsge6br4ewitbdyrktodtvzhm.eu-north-1.es.amazonaws.com'
    )
    username = os.getenv('OPENSEARCH_USERNAME', 'admin')
    password = os.getenv('OPENSEARCH_PASSWORD', 'Admin123!@#')
    
    return OpenSearchLogFetcher(endpoint, username, password)


if __name__ == "__main__":
    # Test the fetcher
    print("🧪 Testing OpenSearch Fetcher...\n")
    
    fetcher = create_opensearch_fetcher()
    
    # Test connection
    fetcher.test_connection()
    
    # Test fetching storage logs
    print("\n📦 Testing storage logs fetch:")
    logs = fetcher.fetch_logs('storage', device_name='NAS-02', time_range='24h')
    print(f"Sample:\n{logs[:500]}...")
    
    # Test fetching kubernetes logs
    print("\n📦 Testing kubernetes logs fetch:")
    logs = fetcher.fetch_logs('kubernetes', namespace='production', time_range='24h')
    print(f"Sample:\n{logs[:500]}...")
    
    # Test device list
    print("\n📋 Available storage devices:")
    devices = fetcher.get_device_list('storage')
    print(f"   {devices}")
