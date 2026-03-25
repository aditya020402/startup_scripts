import os
import sys
import time
import asyncio
import subprocess
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

# Configuration - Edit VM list only!
VM_CONFIG = {
    "vm-web-01": "rg-east-prod",
    "vm-db-01": "rg-central-dev", 
    "vm-app-01": "rg-west-staging",
    # VM_NAME: RESOURCE_GROUP
}

def check_az_login():
    """Check login and get subscription ID automatically"""
    try:
        result = subprocess.run(["az", "account", "show"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            account_info = json.loads(result.stdout)
            global SUBSCRIPTION_ID  
            SUBSCRIPTION_ID = account_info["id"].split("/")[-1]  # Extract sub ID from /subscriptions/{sub}
            print(f"✅ Logged in to subscription: {SUBSCRIPTION_ID}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    
    print("🔐 Starting interactive Azure login (browser opens)...")
    login_process = subprocess.Popen(["az", "login"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT, 
                                   text=True,
                                   bufsize=1,
                                   universal_newlines=True)
    
    for line in login_process.stdout:
        print(line.strip())
    
    login_process.wait()
    
    if login_process.returncode == 0:
        # Re-check account after login
        result = subprocess.run(["az", "account", "show"], capture_output=True, text=True)
        account_info = json.loads(result.stdout)
        global SUBSCRIPTION_ID
        SUBSCRIPTION_ID = account_info["id"].split("/")[-1]
        print(f"✅ Login successful! Using subscription: {SUBSCRIPTION_ID}")
        return True
    print("❌ Login failed.")
    sys.exit(1)

async def start_vms():
    if 'SUBSCRIPTION_ID' not in globals():
        print("❌ No subscription found. Run az account set first.")
        sys.exit(1)
        
    credential = DefaultAzureCredential()
    compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)

    print(f"🚀 Starting {len(VM_CONFIG)} VMs at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    for vm_name, resource_group in VM_CONFIG.items():
        try:
            print(f"Starting {vm_name} in {resource_group}...")
            poller = compute_client.virtual_machines.begin_start(resource_group, vm_name)
            poller.result()
            print(f"✓ {vm_name} - Running")
        except Exception as e:
            print(f"✗ {vm_name}: {str(e)}")

if __name__ == "__main__":
    if check_az_login():
        if input("\nStart VMs now? (y/N): ").lower() == 'y':
            asyncio.run(start_vms())
        else:
            print("Cancelled.")
