#!/usr/bin/env python3
"""
Azure VM Auto-Start Script for GitLab CI / Production
Uses Service Principal authentication (headless, no interactive login)
Multi-subscription, multi-RG support with final status report
"""

import os
import sys
import time
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient

# VM Configuration - Edit this list
VM_CONFIG = [
    {
        "name": "vm-web-01", 
        "subscription_id": "12345678-1234-1234-1234-123456789012",
        "resource_group": "rg-east-prod"
    },
    {
        "name": "vm-db-01", 
        "subscription_id": "87654321-4321-4321-4321-210987654321", 
        "resource_group": "rg-central-dev"
    },
    {
        "name": "vm-app-01", 
        "subscription_id": "12345678-1234-1234-1234-123456789012",
        "resource_group": "rg-west-staging"
    }
    # Add more VMs: {"name": "...", "subscription_id": "...", "resource_group": "..."}
]

VM_STATUS = []  # Track all results

def get_credential() -> ClientSecretCredential:
    """Get Service Principal credential from env vars (GitLab CI)"""
    required_vars = ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        print("Set in GitLab: Settings → CI/CD → Variables")
        sys.exit(1)
    
    return ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET")
    )

def get_vm_status(compute_client: ComputeManagementClient, vm_name: str, resource_group: str) -> tuple[str, str]:
    """Get real-time VM power state"""
    try:
        instance_view = compute_client.virtual_machines.instance_view(resource_group, vm_name)
        for status in instance_view.statuses or []:
            code_lower = status.code.lower() if status.code else ""
            if 'powerstate' in code_lower:
                power_state = status.code.split('/')[-1].title()
                display_status = status.display_status or "OK"
                return power_state, display_status
        return "Unknown", "No power state found"
    except Exception as e:
        return "Error", str(e)[:50]

async def process_single_vm(config: Dict[str, Any]):
    """Process one VM: switch sub + start + verify status"""
    sub_id = config["subscription_id"]
    vm_name = config["name"]
    rg = config["resource_group"]
    
    print(f"\n🔄 Processing {vm_name} (sub: {sub_id[:8]}..., rg: {rg})")
    
    try:
        # Create client for this subscription
        credential = get_credential()
        compute_client = ComputeManagementClient(credential, sub_id)
        
        # Attempt to start VM
        print(f"  → Starting {vm_name}...")
        poller = compute_client.virtual_machines.begin_start(rg, vm_name)
        poller.result()  # Wait for completion
        
        # Verify final status
        final_state, status_msg = get_vm_status(compute_client, vm_name, rg)
        VM_STATUS.append({
            "name": vm_name,
            "subscription_short": sub_id[:8] + "...",
            "resource_group": rg,
            "start_ok": True,
            "start_reason": "Command succeeded",
            "final_state": final_state,
            "status_msg": status_msg
        })
        print(f"  ✓ {vm_name}: {final_state} ({status_msg})")
        
    except Exception as e:
        error_msg = str(e)[:100]
        VM_STATUS.append({
            "name": vm_name,
            "subscription_short": sub_id[:8] + "...",
            "resource_group": rg,
            "start_ok": False,
            "start_reason": error_msg,
            "final_state": "Failed",
            "status_msg": error_msg
        })
        print(f"  ✗ {vm_name}: {error_msg}")

async def main():
    """Main orchestration"""
    print(f"🌅 VM Auto-Start | {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"📋 Configured: {len(VM_CONFIG)} VMs")
    
    if not VM_CONFIG:
        print("❌ No VMs configured in VM_CONFIG")
        sys.exit(1)
    
    # Process all VMs sequentially
    for config in VM_CONFIG:
        await process_single_vm(config)
        await asyncio.sleep(2)  # Rate limiting
    
    # Generate final report
    print("\n" + "="*90)
    print("📊 FINAL VM STATUS REPORT")
    print("="*90)
    print(f"{'VM':<15} {'Sub':<12} {'RG':<20} {'Start':<6} {'Reason':<30} {'Final State'}")
    print("-"*90)
    
    success_count = 0
    for status in VM_STATUS:
        start_icon = "✅" if status["start_ok"] else "❌"
        print(f"{status['name']:<15} {status['subscription_short']:<12} {status['resource_group']:<20} "
              f"{start_icon:<6} {status['start_reason'][:29]:<30} {status['final_state']}")
        if status["start_ok"]:
            success_count += 1
    
    # Summary
    print(f"\n📈 SUMMARY: {success_count}/{len(VM_STATUS)} VMs started successfully")
    
    # Export for GitLab CI artifacts
    with open("vm-status.json", "w") as f:
        json.dump(VM_STATUS, f, indent=2)
    
    with open("vm-status.env", "w") as f:
        f.write(f"VM_SUCCESS_COUNT={success_count}\n")
        f.write(f"VM_TOTAL={len(VM_STATUS)}\n")
        f.write(f"VM_SUCCESS_RATE={(success_count/len(VM_STATUS)*100):.1f}%\n")
    
    print("💾 Status exported: vm-status.json | vm-status.env")
    sys.exit(0 if success_count == len(VM_STATUS) else 1)

if __name__ == "__main__":
    asyncio.run(main())
