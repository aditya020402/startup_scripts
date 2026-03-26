import os
import sys
import time
import asyncio
import subprocess
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

# User configures VMs + SUB + RG
VM_CONFIG = [
    {"name": "vm-web-01", "subscription_id": "1111-2222-3333-4444-555555555555", "resource_group": "rg-east-prod"},
    {"name": "vm-db-01",  "subscription_id": "1234-5678-9012-3456-789012345678", "resource_group": "rg-central-dev"},
    {"name": "vm-app-01", "subscription_id": "1111-2222-3333-4444-555555555555", "resource_group": "rg-west-staging"},
]

VM_STATUS = []  # Track results

def check_az_login():
    try:
        subprocess.run(["az", "account", "show"], check=True, capture_output=True, timeout=10)
        return True
    except:
        print("🔐 Starting login...")
        result = subprocess.run(["az", "login","--tenant","tenant_id"], timeout=300)
        return result.returncode == 0

def switch_subscription(sub_id):
    print(f"🔄 Switching to: {sub_id[:8]}...")
    result = subprocess.run(["az", "account", "set", "--subscription", sub_id], capture_output=True)
    return result.returncode == 0

def get_vm_status(compute_client, vm_name, resource_group):
    """Get real-time power state"""
    try:
        instance_view = compute_client.virtual_machines.instance_view(resource_group, vm_name)
        for status in instance_view.statuses:
            if 'powerstate' in status.code.lower():
                return status.code.split('/')[-1].title(), status.display_status or "OK"
        return "Unknown", "No power state"
    except Exception as e:
        return "Error", str(e)

async def process_vm(config):
    """Start VM + track status"""
    sub_id = config["subscription_id"]
    vm_name = config["name"]
    rg = config["resource_group"]
    
    if not switch_subscription(sub_id):
        VM_STATUS.append({"name": vm_name, "sub": sub_id[:8], "rg": rg, "start_ok": False, "reason": "Sub switch failed", "final_state": "N/A"})
        return
    
    credential = DefaultAzureCredential()
    compute_client = ComputeManagementClient(credential, sub_id)
    
    # Try start
    try:
        print(f"  → Starting {vm_name}...")
        poller = compute_client.virtual_machines.begin_start(rg, vm_name)
        poller.result()
        start_ok = True
        start_reason = "Started"
    except Exception as e:
        start_ok = False
        start_reason = str(e)
    
    # Get final status
    final_state, status_msg = get_vm_status(compute_client, vm_name, rg)
    VM_STATUS.append({
        "name": vm_name, 
        "sub": sub_id[:8]+"...", 
        "rg": rg, 
        "start_ok": start_ok,
        "reason": start_reason,
        "final_state": final_state,
        "status_msg": status_msg
    })
    
    print(f"  {vm_name}: {final_state}")

async def start_all_vms():
    if not check_az_login():
        print("❌ Login required.")
        return
    
    print(f"🚀 Processing {len(VM_CONFIG)} VMs...")
    for config in VM_CONFIG:
        await process_vm(config)
        time.sleep(2)
    
    # FINAL STATUS REPORT
    print("\n" + "="*80)
    print("📊 FINAL VM STATUS REPORT")
    print("="*80)
    print(f"{'VM':<15} {'Sub':<12} {'RG':<20} {'Start':<6} {'Reason':<25} {'Final State'}")
    print("-"*80)
    
    for status in VM_STATUS:
        start_icon = "✅" if status["start_ok"] else "❌"
        print(f"{status['name']:<15} {status['sub']:<12} {status['rg']:<20} "
              f"{start_icon:<6} {status['reason'][:24]:<25} {status['final_state']}")
    
    # Summary
    success = sum(1 for s in VM_STATUS if s["start_ok"])
    print(f"\n📈 SUMMARY: {success}/{len(VM_STATUS)} VMs started successfully")

if __name__ == "__main__":
    if input(f"Start {len(VM_CONFIG)} VMs? (y/N): ").lower() == 'y':
        asyncio.run(start_all_vms())
    else:
        print("Cancelled.")
