# Network Toolbox

A collection of Python automation scripts for managing Cisco network infrastructure. These tools help automate common network administration tasks including switch configuration, monitoring, and maintenance.

## Overview

This toolbox contains several specialized scripts designed to work with Cisco network equipment:

| Script | Purpose | Spreadsheet Required | Environment Config |
|--------|---------|---------------------|-------------------|
| [Check_CDP_APs](#check-cdp-aps) | Monitor Access Points via CDP | No | Yes (.env) |
| [Serial_Checker](#serial-checker) | Collect switch serial numbers | Yes (Switch IP column) | Yes (.env) |
| [Tacacs_Checker_Changer](#tacacs-checker-changer) | Audit/update TACACS configuration | Yes (IP column) | Yes (.env) |
| [Vlan_Changer](#vlan-changer) | Modify VLAN configurations | No | Yes (.env) |
| [Wiping Config](#wiping-config) | Clean up switch configurations | Yes (switch_list.xlsx) | Yes (.env.example) |

## Prerequisites

### System Requirements
- Python 3.7 or higher
- Network access to Cisco devices via SSH (port 22)
- Valid credentials for device access

### Common Python Dependencies
All scripts use similar dependencies. Install them using:
```bash
pip install -r tools/[script_folder]/requirements.txt
```

Common packages include:
- `netmiko` - SSH connections to network devices
- `python-dotenv` - Environment variable management
- `pandas` - Excel file processing (where applicable)

## Environment Configuration

Most scripts use `.env` files for configuration. Each script folder contains:
- `env-template.txt` - Template with placeholder values (safe to share)
- `.env.example` - Additional environment template (where available)

### Setup Process
1. Copy `.env.example` to `.env` in the script's folder
2. Edit `.env` with your actual values
3. Never commit the `.env` file to version control (it's already in .gitignore)

### Security Features
- `.env` files are automatically ignored by git
- `.env.example` files contain no secrets and are safe to share/commit
- Each tool has its own isolated environment configuration
- Cursor IDE is configured to hide `.env` files but show `.env.example` templates

## Scripts Documentation

### Check CDP APs
**Location**: `tools/Check_CDP_APs/`
**Purpose**: Monitors Access Points connected to switches via CDP (Cisco Discovery Protocol)

**Features**:
- Discovers APs connected to switch ports
- Supports 16 configurable locations
- Multiple credential fallback support
- Debug logging for troubleshooting
- No spreadsheet required

**Configuration**: Requires `.env` file with credentials and location details:
```
# Primary credentials
SWITCH_USERNAME=your_username
SWITCH_PASSWORD=your_password

# Locations
LOCATION_1_NAME=Your Location Name
LOCATION_1_IP=192.168.1.10
```

### Serial Checker
**Location**: `tools/Serial_Checker/`
**Purpose**: Connects to switches and retrieves their serial numbers

**Features**:
- Processes multiple Excel sheets
- Auto-creates Serial Number column
- Comprehensive error handling
- Progress logging

**Requirements**:
- Excel file with `Switch IP` column (configurable path in .env)
- `.env` file with credentials and file path

**Configuration**:
```
SWITCH_USERNAME=your_username
SWITCH_PASSWORD=your_password
EXCEL_FILE_PATH=switches.xlsx
```

### Tacacs Checker Changer
**Location**: `tools/Tacacs_Checker_Changer/`
**Purpose**: Audits and updates TACACS server configurations on network devices

**Features**:
- Check current TACACS configuration
- Verify new ClearPass server configurations
- Multi-credential fallback support (AD + local accounts)
- Detailed Excel reporting with status updates
- Progress tracking and logging

**Requirements**:
- Excel file with `IP` column
- `.env` file with credentials and ClearPass IPs

**Configuration**:
```
# Excel file path
EXCEL_FILE_PATH=switches.xlsx

# ClearPass servers to check for
NEW_CLEARPASS_IP1=192.168.1.10
NEW_CLEARPASS_IP2=192.168.1.11

# Multiple credential sets
AD_USERNAME=your_ad_user
AD_PASSWORD=your_ad_password
LOCAL1_USERNAME=local_user1
LOCAL1_PASSWORD=local_password1
```

### VLAN Changer
**Location**: `tools/Vlan_Changer/`
**Purpose**: Modifies VLAN configurations on network devices

**Features**:
- Interactive site selection (1-20)
- MAC address lookup via ARP tables
- Port channel member detection
- Switch responsiveness testing with adaptive delays
- Multiple credential fallback support
- Comprehensive VLAN configuration verification

**Configuration**: Requires `.env` file with credentials and locations:
```
# Primary credentials
PRIMARY_USERNAME=your_username
PRIMARY_PASSWORD=your_password

# Fallback credentials
FALLBACK_USER1=backup_user1
FALLBACK_PASS1=backup_pass1

# VLAN locations (up to 20)
VLAN_LOCATION_1_NAME=Site Name
VLAN_LOCATION_1_IP=192.168.1.10
```

### Wiping Config
**Location**: `tools/wiping config/`
**Purpose**: Removes specific configuration elements from switches

**Features**:
- Removes SNMP, NTP, banners, logging hosts
- Removes specific user accounts
- Updates TTY line configurations (removes password 7, sets login local)
- Removes TACACS server configurations
- Comprehensive error logging

**⚠️ WARNING**: This script makes permanent configuration changes!

**Requirements**:
- Excel file: `switch_list.xlsx` with `IP` column
- Administrative credentials with config access
- Interactive credential entry (currently prompts for username/password)

**Configuration**: Optional `.env.example` template available for reference:
```
# Currently prompts for credentials at runtime
# Optional: modify script to use these environment variables
# USERNAME=your_username
# PASSWORD=your_password
# ENABLE_SECRET=your_enable_password
```

**Removes**:
- SNMP server configurations
- NTP settings and servers  
- Banner messages (exec, login, motd)
- Logging hosts and domain settings
- IP host entries and name servers
- TACACS server hosts and keys
- Specific user accounts 
- Password 7 configurations on TTY lines

## Security Best Practices

### Credential Management
- Never hardcode credentials in scripts
- Use `.env` files for sensitive information
- Add `.env` to `.gitignore`
- Use strong, unique passwords
- Implement credential rotation

### Network Security
- Ensure secure connections to network devices
- Use dedicated management networks where possible
- Implement proper access controls
- Monitor and log all administrative actions

### File Security
- Keep `.env` files secure and backed up
- Don't commit sensitive configuration files (they're in .gitignore)
- Share `.env.example` templates safely (no secrets)
- Use appropriate file permissions
- Regular security audits of scripts

## Common Usage Patterns

### First-time Setup
```bash
# 1. Choose your script
cd tools/[script_name]/

# 2. Install dependencies  
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your actual values

# 4. Prepare spreadsheet (if required)
# Follow script-specific README for format

# 5. Run the script
python [script_name].py
```

### Troubleshooting
1. Check the script's log file for detailed errors
2. Verify network connectivity to devices
3. Confirm credentials are correct and have sufficient privileges
4. Validate spreadsheet format and column names
5. Review script-specific README for additional requirements

## Project Structure
```
network-toolbox/
├── README.md                           # This file
├── .gitignore                          # Git ignore file (protects .env files)
└── tools/
    ├── Check_CDP_APs/
    │   ├── CheckCDPAPs.py              # Main script
    │   ├── requirements.txt            # Python dependencies
    │   ├── .env.example               # Environment template
    │   └── README.md                  # Script documentation
    ├── Serial_Checker/
    │   ├── switch_serial_updater.py    # Main script
    │   ├── requirements.txt
    │   ├── .env.example
    │   └── README.md
    ├── Tacacs_Checker_Changer/
    │   ├── Tacacs_Checker.py           # Main script
    │   ├── requirements.txt
    │   ├── .env.example
    │   └── README.md
    ├── Vlan_Changer/
    │   ├── VlanChange.py               # Main script
    │   ├── requirements.txt
    │   ├── .env.example
    │   └── README.md
    └── wiping config/
        ├── wipeConfig.py               # Main script
        ├── requirements.txt
        ├── .env.example               # Environment template
        └── README.md
```

## Contributing

When adding new scripts or modifying existing ones:
1. Follow the established project structure
2. Include comprehensive error handling
3. Add appropriate logging
4. Create/update README documentation
5. Use environment variables for sensitive data
6. Include requirements.txt file
7. Test thoroughly before deployment

## Support

For issues or questions:
1. Check the script-specific README file
2. Review log files for error details
3. Verify prerequisites and configuration
4. Test in a non-production environment first

---

**⚠️ Important**: Always backup your network configurations before running any automation scripts. Test in a lab environment first when possible.
