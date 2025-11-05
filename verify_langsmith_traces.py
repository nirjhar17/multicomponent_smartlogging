#!/usr/bin/env python3
"""
LangSmith Trace Verification Script
Checks if traces are being sent to LangSmith successfully
"""

import os
import sys
from datetime import datetime, timedelta
from langsmith import Client

# Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "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")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ai-troubleshooter-v10")

def verify_langsmith_health():
    """Verify LangSmith connection and recent traces"""
    
    print("=" * 60)
    print("🔍 LangSmith Health Check")
    print("=" * 60)
    
    try:
        # Initialize client
        client = Client(api_key=LANGSMITH_API_KEY)
        print(f"✅ Connected to LangSmith API")
        print(f"📊 Project: {LANGSMITH_PROJECT}")
        print()
        
        # Get recent runs (last 24 hours)
        print("📈 Fetching recent traces...")
        since = datetime.now() - timedelta(hours=24)
        
        runs = list(client.list_runs(
            project_name=LANGSMITH_PROJECT,
            start_time=since,
            limit=10
        ))
        
        print(f"✅ Found {len(runs)} traces in the last 24 hours")
        print()
        
        if runs:
            print("🔍 Recent Traces:")
            print("-" * 60)
            for i, run in enumerate(runs[:5], 1):
                print(f"{i}. Run ID: {run.id}")
                print(f"   Name: {run.name}")
                print(f"   Start: {run.start_time}")
                print(f"   Status: {run.status}")
                if run.error:
                    print(f"   ⚠️  Error: {run.error}")
                print()
            
            # Summary stats
            total_runs = len(runs)
            successful = sum(1 for r in runs if r.status == "success")
            failed = sum(1 for r in runs if r.status == "error")
            
            print("📊 Summary Statistics:")
            print(f"   Total runs: {total_runs}")
            print(f"   ✅ Successful: {successful}")
            print(f"   ❌ Failed: {failed}")
            print(f"   Success rate: {(successful/total_runs*100):.1f}%")
            print()
            
            print("🔗 View in Dashboard:")
            print(f"   https://smith.langchain.com/o/default/projects/p/{LANGSMITH_PROJECT}")
            
        else:
            print("⚠️  No traces found in the last 24 hours")
            print("   This could mean:")
            print("   1. The app hasn't processed any queries recently")
            print("   2. Tracing is not configured correctly")
            print("   3. There's a connectivity issue with LangSmith")
            
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to LangSmith: {e}")
        print()
        print("Troubleshooting tips:")
        print("1. Check API key is valid")
        print("2. Verify network connectivity")
        print("3. Ensure project name is correct")
        return False

if __name__ == "__main__":
    success = verify_langsmith_health()
    sys.exit(0 if success else 1)
