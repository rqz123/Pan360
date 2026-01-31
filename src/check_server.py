#!/usr/bin/env python3
"""
Check Pan360 Stitching Server Status
Displays server health, available algorithms, and active jobs
"""

import requests
import sys
from datetime import datetime
from typing import Optional, Dict, Any


def check_server_health(server_url: str) -> Optional[Dict[str, Any]]:
    """Check if server is healthy"""
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"✗ Failed to connect to server: {e}")
        return None


def get_algorithms(server_url: str) -> Optional[list]:
    """Get list of available stitching algorithms"""
    try:
        response = requests.get(f"{server_url}/api/v1/algorithms", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("algorithms", [])
    except Exception as e:
        print(f"✗ Failed to get algorithms: {e}")
        return None


def get_jobs(server_url: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Get list of recent jobs"""
    try:
        response = requests.get(f"{server_url}/api/v1/jobs?limit={limit}", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"✗ Failed to get jobs: {e}")
        return None


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_timestamp


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check Pan360 server status")
    parser.add_argument(
        "--server",
        default="http://192.168.5.138:8000",
        help="Server URL (default: http://192.168.5.138:8000)"
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=10,
        help="Number of recent jobs to display (default: 10)"
    )
    
    args = parser.parse_args()
    
    server_url = args.server.rstrip('/')
    
    print("=" * 70)
    print("Pan360 Stitching Server Status")
    print("=" * 70)
    print(f"Server: {server_url}")
    print()
    
    # 1. Check Health
    print("─" * 70)
    print("SERVER HEALTH")
    print("─" * 70)
    
    health = check_server_health(server_url)
    if not health:
        print("✗ Server is not responding")
        sys.exit(1)
    
    print(f"Status:       ✓ {health.get('status', 'unknown').upper()}")
    print(f"Timestamp:    {format_timestamp(health.get('timestamp', ''))}")
    print(f"Active Jobs:  {health.get('active_jobs', 0)}")
    print(f"Total Jobs:   {health.get('total_jobs', 0)}")
    print()
    
    # 2. List Algorithms
    print("─" * 70)
    print("AVAILABLE STITCHING ALGORITHMS")
    print("─" * 70)
    
    algorithms = get_algorithms(server_url)
    if not algorithms:
        print("✗ Failed to retrieve algorithms")
    else:
        print(f"Total: {len(algorithms)} algorithms available\n")
        
        for i, alg in enumerate(algorithms, 1):
            recommended = "✓ RECOMMENDED" if alg.get("recommended") else ""
            print(f"{i}. {alg.get('name', 'Unknown')} {recommended}")
            print(f"   ID: {alg.get('id', 'unknown')}")
            print(f"   Description: {alg.get('description', 'N/A')}")
            
            params = alg.get('parameters', {})
            if params:
                print(f"   Parameters:")
                for param_name, param_info in params.items():
                    default = param_info.get('default', 'N/A')
                    desc = param_info.get('description', '')
                    print(f"     - {param_name}: {default} ({desc})")
            print()
    
    # 3. Recent Jobs
    print("─" * 70)
    print(f"RECENT JOBS (Last {args.jobs})")
    print("─" * 70)
    
    jobs_data = get_jobs(server_url, args.jobs)
    if not jobs_data:
        print("✗ Failed to retrieve jobs")
    else:
        jobs = jobs_data.get('jobs', [])
        
        if not jobs:
            print("No jobs found")
        else:
            for i, job in enumerate(jobs, 1):
                status = job.get('status', 'unknown')
                status_symbol = {
                    'completed': '✓',
                    'failed': '✗',
                    'processing': '⟳',
                    'queued': '○'
                }.get(status, '?')
                
                print(f"{i}. {status_symbol} {status.upper()}")
                print(f"   Job ID: {job.get('job_id', 'unknown')}")
                print(f"   Algorithm: {job.get('algorithm', 'N/A')}")
                print(f"   Created: {format_timestamp(job.get('created_at', ''))}")
                
                if job.get('completed_at'):
                    print(f"   Completed: {format_timestamp(job.get('completed_at', ''))}")
                
                if job.get('message'):
                    print(f"   Message: {job.get('message', '')}")
                
                stats = job.get('stats')
                if stats:
                    if 'width' in stats and 'height' in stats:
                        print(f"   Output: {stats['width']}x{stats['height']}px")
                    if 'processing_time' in stats:
                        print(f"   Processing Time: {stats['processing_time']:.1f}s")
                
                print()
    
    print("=" * 70)
    print("\nAPI Documentation: " + server_url + "/docs")
    print("=" * 70)


if __name__ == "__main__":
    main()
