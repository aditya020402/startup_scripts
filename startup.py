import os
import sys
import time
import asyncio
import subprocess
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

# Configuration - Edit these
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", input("Enter Subscription ID: "))
VM_CONFIG = {
    "vm-web-01": "rg-east-prod",
    "vm-db-01": "rg-central-dev", 
    "vm-app-01": "rg-west-staging",
    # VM_NAME: RESOURCE_GROUP
}

def check_az_login():
    """Check if Azure CLI is logged in, trigger login if needed"""
    try:
        result = subprocess.run(["az", "account", "show"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            sub_id = result.stdout.split('"id":"')[1].split('"')[0]
            print(f"✅ Already logged in to subscription: {sub_id}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("🔐 Starting interactive Azure login (browser will open)...")
    print("Complete login, then return here.")
    
    # Interactive az login (handles browser/MFA automatically)
    login_process = subprocess.Popen(["az", "login"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT, 
                                   text=True,
                                   bufsize=1,
                                   universal_newlines=True)
    
    # Stream output and wait for completion
    for line in login_process.stdout:
        print(line.strip())
    
    login_process.wait()
    
    if login_process.returncode == 0:
        print("✅ Login successful!")
        return True
    else:
        print("❌ Login failed. Exiting.")
        sys.exit(1)

async def start_vms():
    credential = DefaultAzureCredential()
    compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)

    print(f"🚀 Starting {len(VM_CONFIG)} VMs at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    for vm_name, resource_group in VM_CONFIG.items():
        try:
            print(f"Starting {vm_name} in {resource_group}...")
            poller = compute_client.virtual_machines.begin_start(resource_group, vm_name)
            result = poller.result()  # Wait for completion
            print(f"✓ {vm_name} in {resource_group} - Running")
        except Exception as e:
            print(f"✗ {vm_name} failed: {str(e)}")

    print("🎉 All VMs processed!")

if __name__ == "__main__":
    if not check_az_login():
        sys.exit(1)
    
    if input("Start VMs now? (y/N): ").lower() == 'y':
        asyncio.run(start_vms())
    else:
        print("Cancelled.")
