import os
import sys
import time
import asyncio
import subprocess
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

# User configures VMs + their SUB + RG
VM_CONFIG = [
    {"name": "vm-web-01", "subscription_id": "1111-2222-3333-4444-555555555555", "resource_group": "rg-east-prod"},
    {"name": "vm-db-01",  "subscription_id": "1234-5678-9012-3456-789012345678", "resource_group": "rg-central-dev"},
    {"name": "vm-app-01", "subscription_id": "1111-2222-3333-4444-555555555555", "resource_group": "rg-west-staging"},
    # Add more VMs here: {"name": "...", "subscription_id": "...", "resource_group": "..."}
]

def check_az_login():
    """Ensure logged in"""
    try:
        subprocess.run(["az", "account", "show"], check=True, capture_output=True, timeout=10)
        return True
    except:
        print("🔐 Starting login...")
        result = subprocess.run(["az", "login"], timeout=300)
        return result.returncode == 0

def switch_subscription(sub_id):
    """Switch to subscription and verify"""
    print(f"🔄 Switching to subscription: {sub_id}")
    result = subprocess.run(["az", "account", "set", "--subscription", sub_id], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        verify = subprocess.run(["az", "account", "show", "--query", "id", "-o", "tsv"], 
                              capture_output=True, text=True)
        current = verify.stdout.strip().split("/")[-1]
        if current == sub_id:
            print(f"✅ Switched to: {sub_id}")
            return True
    print(f"❌ Failed to switch to {sub_id}")
    return False

async def start_vm(compute_client, vm_name, resource_group):
    """Start single VM"""
    try:
        print(f"  → Starting {vm_name}...")
        poller = compute_client.virtual_machines.begin_start(resource_group, vm_name)
        poller.result()
        print(f"  ✓ {vm_name} - Running")
    except Exception as e:
        print(f"  ✗ {vm_name}: {str(e)}")

async def start_vms():
    if not check_az_login():
        print("❌ Login required.")
        sys.exit(1)
    
    print(f"🚀 Processing {len(VM_CONFIG)} VMs across subscriptions...")
    
    credential = DefaultAzureCredential()
    
    for config in VM_CONFIG:
        sub_id = config["subscription_id"]
        vm_name = config["name"]
        rg = config["resource_group"]
        
        # Switch subscription context
        if not switch_subscription(sub_id):
            print(f"Skipping {vm_name} due to sub switch failure")
            continue
            
        # Create client for this subscription
        compute_client = ComputeManagementClient(credential, sub_id)
        
        # Start VM
        await start_vm(compute_client, vm_name, rg)
        time.sleep(2)  # Rate limit courtesy

if __name__ == "__main__":
    if input(f"Start {len(VM_CONFIG)} VMs across subs? (y/N): ").lower() == 'y':
        asyncio.run(start_vms())
        print("🎉 Complete!")
    else:
        print("Cancelled.")
