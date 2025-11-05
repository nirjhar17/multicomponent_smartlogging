from opensearchpy import OpenSearch
import json

# OpenSearch connection
host = "search-aiops-logs-v2-v5dyuq7c7syvyo2jawyqnxmqka.eu-north-1.es.amazonaws.com"
auth = ("admin", "Admin123!")

client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    ssl_show_warn=False,
    timeout=10
)

print("=" * 60)
print("🔍 OpenSearch Cluster Status")
print("=" * 60)

# Check cluster health
try:
    health = client.cluster.health()
    print(f"\n✅ Cluster Status: {health['status'].upper()}")
    print(f"   Nodes: {health['number_of_nodes']}")
    print(f"   Data Nodes: {health['number_of_data_nodes']}")
    print(f"   Active Shards: {health['active_shards']}")
except Exception as e:
    print(f"❌ Error getting cluster health: {e}")

# List all indices
print("\n" + "=" * 60)
print("📊 Available Indices")
print("=" * 60)

try:
    indices = client.cat.indices(format='json', s='index:asc')
    if indices:
        print(f"\nFound {len(indices)} indices:\n")
        for idx in indices:
            print(f"  • {idx['index']:40s} | Docs: {idx['docs.count']:>10s} | Size: {idx['store.size']:>10s} | Health: {idx['health']}")
    else:
        print("\n❌ No indices found!")
except Exception as e:
    print(f"❌ Error listing indices: {e}")

# Check for kubernetes logs specifically
print("\n" + "=" * 60)
print("🔍 Searching for Kubernetes Logs")
print("=" * 60)

try:
    # Try different index patterns
    patterns = ['kubernetes-*', 'openshift-*', 'app-*', 'infra-*', 'test-*']
    
    for pattern in patterns:
        try:
            result = client.count(index=pattern)
            if result['count'] > 0:
                print(f"\n✅ Pattern '{pattern}': {result['count']} documents")
        except:
            pass
    
    # Search for test-problematic-pods namespace
    try:
        search_result = client.search(
            index="*",
            body={
                "size": 0,
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"kubernetes.namespace_name": "test-problematic-pods"}},
                            {"match": {"namespace": "test-problematic-pods"}},
                            {"match": {"namespace_name": "test-problematic-pods"}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
        )
        count = search_result['hits']['total']['value']
        if count > 0:
            print(f"\n🎯 Found {count} logs from 'test-problematic-pods' namespace!")
        else:
            print(f"\n⚠️ No logs found for 'test-problematic-pods' namespace")
    except Exception as e:
        print(f"\n⚠️ Could not search for namespace: {e}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
