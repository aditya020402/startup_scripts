# Azure VM Auto-Start Script 🚀

**Production-ready Python script to automatically login, switch subscriptions, start VMs across multiple resource groups/subscriptions, and generate detailed status reports.**

## ✨ Features

- ✅ **Interactive Azure login** (handles browser/MFA automatically)
- ✅ **Multi-subscription support** (auto-switches context per VM)
- ✅ **Multi-resource group** support
- ✅ **Real-time power state verification** (`Running/Starting/Deallocated`)
- ✅ **Comprehensive final status report** with success/fail reasons
- ✅ **Error resilient** (one VM failure ≠ all fail)
- ✅ **Tenant-specific login** option (bypasses selectors)


## Example config

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
    }
]
