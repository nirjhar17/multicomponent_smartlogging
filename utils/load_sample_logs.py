"""
Sample Log Generator for Multi-Component AIOps Demo

This script generates realistic sample logs for 5 infrastructure component types
and loads them into OpenSearch for demo/testing purposes.

Components:
- Database (PostgreSQL-style logs)
- Server (Application server logs)
- Storage (NAS/SAN logs)
- Firewall (Security logs)
- Kubernetes (via OpenShift ClusterLogForwarder - not generated here)

Usage:
    python load_sample_logs.py --opensearch-url https://your-opensearch-endpoint \
                                --username admin \
                                --password YourPassword

Author: AI Troubleshooter v9
"""

import argparse
import json
from datetime import datetime, timedelta
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
import random
import time


class SampleLogGenerator:
    """Generate realistic sample logs for different infrastructure components"""
    
    def __init__(self, opensearch_client, index_name="openshift-logs"):
        self.client = opensearch_client
        self.index_name = index_name
        self.base_time = datetime.utcnow()
    
    def generate_database_logs(self, device="db-server-01", count=50):
        """Generate PostgreSQL-style database logs with cascading failure scenario"""
        logs = []
        scenarios = [
            # Scenario 1: Deadlock
            {
                "level": "ERROR",
                "message": "Deadlock detected on table 'orders': Lock wait timeout exceeded for transaction attempting to modify order_id=1234"
            },
            # Scenario 2: Slow queries
            {
                "level": "WARNING",
                "message": "Slow query detected on {device}: SELECT * FROM orders WHERE status='pending' took 5200ms (threshold: 1000ms)"
            },
            # Scenario 3: Connection pool exhaustion
            {
                "level": "CRITICAL",
                "message": "Connection pool exhausted on {device}: Max connections (100) reached, 45 clients waiting"
            },
            # Scenario 4: Query timeout
            {
                "level": "ERROR",
                "message": "Query timeout on {device}: Transaction aborted after 30s waiting for disk I/O"
            },
            # Scenario 5: I/O delay (root cause)
            {
                "level": "WARNING",
                "message": "Disk I/O delay detected on /var/lib/postgresql: Average latency 8000ms (normal: <10ms)"
            }
        ]
        
        for i in range(count):
            scenario = random.choice(scenarios)
            timestamp = self.base_time - timedelta(hours=random.randint(1, 24))
            
            log = {
                "@timestamp": timestamp.isoformat() + "Z",
                "level": scenario["level"],
                "message": scenario["message"].format(device=device),
                "component": "database",
                "host": device,
                "device": device,
                "process": "postgresql",
                "pid": random.randint(1000, 9999)
            }
            logs.append(log)
        
        return logs
    
    def generate_server_logs(self, device="app-server-01", count=50):
        """Generate application server logs"""
        logs = []
        scenarios = [
            {
                "level": "ERROR",
                "message": "Process timeout: PostgreSQL process (PID {pid}) timeout after 30s waiting for disk read on /mnt/data/postgresql"
            },
            {
                "level": "WARNING",
                "message": "Load average critical: 45.2 (normal: <5.0) on {device} due to I/O wait"
            },
            {
                "level": "ERROR",
                "message": "Disk latency spike: 12000ms on /mnt/data, processes timing out"
            },
            {
                "level": "ERROR",
                "message": "High I/O wait: 95% on mount point /mnt/data (mounted from storage NAS-02 via NFS). Multiple processes blocked waiting for disk I/O."
            },
            {
                "level": "INFO",
                "message": "Application started successfully on {device}"
            }
        ]
        
        for i in range(count):
            scenario = random.choice(scenarios)
            timestamp = self.base_time - timedelta(hours=random.randint(1, 24))
            
            log = {
                "@timestamp": timestamp.isoformat() + "Z",
                "level": scenario["level"],
                "message": scenario["message"].format(device=device, pid=random.randint(1000, 9999)),
                "component": "server",
                "host": device,
                "device": device,
                "service": "application-service"
            }
            logs.append(log)
        
        return logs
    
    def generate_storage_logs(self, device="NAS-02", count=50):
        """Generate NAS/SAN storage logs"""
        logs = []
        scenarios = [
            {
                "level": "CRITICAL",
                "message": "RAID degraded: Disk 3 failed in RAID-5 array /dev/md0 on {device}"
            },
            {
                "level": "ERROR",
                "message": "Disk failure: /dev/sdd reporting SMART errors, replacement required"
            },
            {
                "level": "WARNING",
                "message": "High I/O latency: Average read latency 12000ms on {device} (normal: <10ms)"
            },
            {
                "level": "ERROR",
                "message": "NFS timeout: Multiple clients reporting timeouts accessing /exports/data from {device}"
            },
            {
                "level": "INFO",
                "message": "RAID rebuild started: Estimated time 4 hours"
            }
        ]
        
        for i in range(count):
            scenario = random.choice(scenarios)
            timestamp = self.base_time - timedelta(hours=random.randint(1, 24))
            
            log = {
                "@timestamp": timestamp.isoformat() + "Z",
                "level": scenario["level"],
                "message": scenario["message"].format(device=device),
                "component": "storage",
                "host": device,
                "device": device,
                "storage_type": "NAS"
            }
            logs.append(log)
        
        return logs
    
    def generate_firewall_logs(self, device="FW-01", count=50):
        """Generate firewall security logs"""
        logs = []
        scenarios = [
            {
                "level": "WARNING",
                "message": "Port scan detected from 203.0.113.45: Scanned ports 22,80,443,3306,5432 on {device}"
            },
            {
                "level": "CRITICAL",
                "message": "DDoS attack detected: 50,000 requests/sec from 198.51.100.0/24 targeting web-server-01"
            },
            {
                "level": "ERROR",
                "message": "Intrusion attempt blocked: SQL injection detected in HTTP POST to /api/login from 192.0.2.100"
            },
            {
                "level": "WARNING",
                "message": "Rate limit exceeded: IP 203.0.113.89 exceeded 1000 requests/min (limit: 100)"
            },
            {
                "level": "INFO",
                "message": "Connection allowed: 10.0.1.50:45678 -> 10.0.2.100:443 (HTTPS)"
            }
        ]
        
        for i in range(count):
            scenario = random.choice(scenarios)
            timestamp = self.base_time - timedelta(hours=random.randint(1, 24))
            
            log = {
                "@timestamp": timestamp.isoformat() + "Z",
                "level": scenario["level"],
                "message": scenario["message"].format(device=device),
                "component": "firewall",
                "host": device,
                "device": device,
                "firewall_type": "IDS/IPS"
            }
            logs.append(log)
        
        return logs
    
    def load_logs(self, logs):
        """Bulk load logs into OpenSearch"""
        actions = [
            {
                "_index": self.index_name,
                "_source": log
            }
            for log in logs
        ]
        
        success, failed = bulk(self.client, actions, raise_on_error=False)
        return success, failed


def main():
    parser = argparse.ArgumentParser(description="Load sample logs into OpenSearch for v9 demo")
    parser.add_argument("--opensearch-url", required=True, help="OpenSearch endpoint URL")
    parser.add_argument("--username", default="admin", help="OpenSearch username")
    parser.add_argument("--password", required=True, help="OpenSearch password")
    parser.add_argument("--index", default="openshift-logs", help="Index name")
    parser.add_argument("--count", type=int, default=50, help="Number of logs per component")
    
    args = parser.parse_args()
    
    # Connect to OpenSearch
    print(f"Connecting to OpenSearch: {args.opensearch_url}")
    client = OpenSearch(
        hosts=[{'host': args.opensearch_url.replace('https://', '').replace('http://', ''), 'port': 443}],
        http_auth=(args.username, args.password),
        use_ssl=True,
        verify_certs=True,
        ssl_show_warn=False,
        timeout=30
    )
    
    generator = SampleLogGenerator(client, args.index)
    
    # Generate and load logs for each component
    components = [
        ("Database", "db-server-01", generator.generate_database_logs),
        ("Database", "db-server-02", generator.generate_database_logs),
        ("Server", "app-server-01", generator.generate_server_logs),
        ("Server", "app-server-02", generator.generate_server_logs),
        ("Storage", "NAS-02", generator.generate_storage_logs),
        ("Firewall", "FW-01", generator.generate_firewall_logs),
    ]
    
    total_success = 0
    total_failed = 0
    
    for component_type, device, generate_func in components:
        print(f"\n📊 Generating {args.count} {component_type} logs for {device}...")
        logs = generate_func(device=device, count=args.count)
        
        print(f"   Loading into OpenSearch...")
        success, failed = generator.load_logs(logs)
        total_success += success
        total_failed += failed
        
        print(f"   ✅ Loaded {success} logs ({failed} failed)")
        time.sleep(1)  # Rate limiting
    
    print(f"\n{'='*60}")
    print(f"✅ COMPLETE: {total_success} logs loaded, {total_failed} failed")
    print(f"{'='*60}")
    print(f"\n📍 Logs available in index: {args.index}")
    print(f"🔍 Query in OpenSearch Dashboards to verify")


if __name__ == "__main__":
    main()

