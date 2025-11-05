from langsmith import Client
import os
from datetime import datetime

# Initialize client
client = Client(api_key=os.getenv("LANGSMITH_API_KEY", "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"))

trace_id = "ff92c63b-5b42-4ef6-9b6b-bef61c5081bc"

print("=" * 80)
print("COMPREHENSIVE TRACE ANALYSIS")
print("=" * 80)

# Get main trace
main_run = client.read_run(trace_id)
print(f"\n📊 MAIN TRACE")
print(f"   ID: {main_run.id}")
print(f"   Name: {main_run.name}")
print(f"   Status: {main_run.status}")
print(f"   Type: {main_run.run_type}")
print(f"   Duration: {(main_run.end_time - main_run.start_time).total_seconds():.2f}s")

# Get all child runs
child_runs = list(client.list_runs(trace_id=trace_id))
print(f"\n🔗 CHILD TRACES: {len(child_runs)} total")

# Group by name
from collections import defaultdict
by_name = defaultdict(list)
for run in child_runs:
    by_name[run.name].append(run)

print(f"\n📋 TRACE BREAKDOWN BY COMPONENT:")
for name, runs in sorted(by_name.items()):
    total_dur = sum((r.end_time - r.start_time).total_seconds() for r in runs if r.end_time and r.start_time)
    statuses = [r.status for r in runs]
    success_count = statuses.count('success')
    print(f"   {name:35s} | Count: {len(runs):2d} | {success_count}/{len(runs)} success | {total_dur:.2f}s total")

print(f"\n⏱️  TIMING ANALYSIS:")
sorted_runs = sorted(child_runs, key=lambda r: (r.end_time - r.start_time).total_seconds() if r.end_time and r.start_time else 0, reverse=True)
print("   Slowest operations:")
for run in sorted_runs[:5]:
    dur = (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else 0
    print(f"   • {run.name:35s} {dur:6.2f}s")

# Check for errors
errors = [r for r in child_runs if r.error or r.status == 'error']
print(f"\n❌ ERRORS: {len(errors)}")
if errors:
    for err in errors:
        print(f"   • {err.name}: {err.error}")
else:
    print("   ✅ No errors found")

print("\n" + "=" * 80)
