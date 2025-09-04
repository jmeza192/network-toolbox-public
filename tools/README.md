# Network Toolbox

A comprehensive collection of Python-based network management tools for Cisco switch administration, monitoring, and configuration management. These tools are designed to automate common network operations across multiple switches efficiently and safely.

## 🚀 Overview

This toolbox contains specialized scripts for:
- **Authentication Management** - Converting AAA to local auth, TACACS server updates
- **Configuration Management** - VLAN changes, configuration cleanup
- **Monitoring & Auditing** - Connectivity testing, CDP discovery, serial number collection
- **Security Operations** - User account management, configuration hardening

## 📁 Tool Directory

### 🔐 Authentication & Security

| Tool | Purpose | Key Features |
|------|---------|--------------|
| **[ChangeToLoginLocal](ChangeToLoginLocal/)** | Convert switches from AAA to local authentication | AAA disable, local admin creation, VTY configuration |
| **[Tacacs_Checker_Changer](Tacacs_Checker_Changer/)** | Audit and update TACACS+ server configurations | Multi-credential testing, Clearpass migration, Excel reporting |
| **[wiping config](wiping%20config/)** | Remove specific configurations for security hardening | User cleanup, service removal, configuration sanitization |

### 🔧 Configuration Management

| Tool | Purpose | Key Features |
|------|---------|--------------|
| **[Vlan_Changer](Vlan_Changer/)** | Interactive VLAN assignment changes | Site-based management, port selection, safe configuration |

### 📊 Monitoring & Discovery

| Tool | Purpose | Key Features |
|------|---------|--------------|
| **[Check_Login](Check_Login/)** | Test SSH connectivity across multiple switches | Batch testing, credential validation, CSV reporting |
| **[Check_CDP_APs](Check_CDP_APs/)** | Discover Access Points via CDP | AP mapping, port discovery, detailed logging |
| **[Serial_Checker](Serial_Checker/)** | Collect and update switch serial numbers | Excel integration, multi-sheet support, automated updates |

## 🛠️ Prerequisites

### System Requirements
- **Python 3.7 or higher**
- **Network access** to target Cisco switches
- **Administrative credentials** for switch management
- **Excel files** with switch inventories (where applicable)

### Common Dependencies
All tools use similar Python packages:
```bash
netmiko          # Cisco device connectivity
pandas           # Excel file processing  
python-dotenv    # Environment variable management
openpyxl         # Excel file manipulation
```

## 📋 Quick Start Guide

### 1. Choose Your Tool
Browse the tool directory above and select the appropriate tool for your task.

### 2. Install Dependencies
Navigate to the specific tool directory and install requirements:
```bash
cd tools/[ToolName]
pip install -r requirements.txt
```

### 3. Configure Environment
Most tools require a `.env` file with credentials:
```bash
# Copy the example file
cp env.example .env

# Edit with your actual credentials
nano .env
```

### 4. Prepare Data Files
Tools that work with multiple switches typically require an Excel file with:
- A column named **"IP"** containing switch IP addresses
- Additional columns as specified in each tool's README

### 5. Run the Tool
```bash
python [script_name].py
```

## 🔧 Configuration Patterns

### Credential Management
Most tools support multiple authentication methods:
- **Primary credentials** for standard access
- **Fallback credentials** for different authentication scenarios
- **Enable passwords** for privilege escalation
- **Flexible naming** supporting various credential conventions

### Excel File Integration
Common Excel file requirements:
- **IP column** with switch IP addresses
- **Consistent formatting** across all sheets
- **Automatic column addition** for results and status
- **Multi-sheet support** where applicable

### Error Handling
All tools include robust error handling:
- **Connection timeout management**
- **Authentication failure recovery**
- **Configuration error logging**
- **Graceful failure handling**

## 📖 Individual Tool Documentation

Each tool directory contains:
- **README.md** - Detailed usage instructions and features
- **requirements.txt** - Python dependencies
- **env.example** - Environment variable template (where needed)
- **Python script** - The main tool implementation

## 🔍 Tool Selection Guide

### For Authentication Changes
- **Converting to local auth**: Use `ChangeToLoginLocal`
- **TACACS server updates**: Use `Tacacs_Checker_Changer`
- **User account cleanup**: Use `wiping config`

### For Configuration Management
- **VLAN assignments**: Use `Vlan_Changer`
- **Configuration cleanup**: Use `wiping config`

### For Monitoring & Discovery
- **Connectivity testing**: Use `Check_Login`
- **Access Point discovery**: Use `Check_CDP_APs`
- **Serial number collection**: Use `Serial_Checker`

## 🛡️ Security Best Practices

### Credential Security
- **Never commit** `.env` files to version control
- **Use strong passwords** for all accounts
- **Rotate credentials** regularly
- **Limit access** to tools and credentials

### Testing & Validation
- **Test in lab environment** before production use
- **Backup configurations** before making changes
- **Verify changes** after execution
- **Have rollback procedures** ready

### Network Safety
- **Coordinate downtime** for configuration changes
- **Have console access** available for recovery
- **Monitor network services** during and after changes
- **Document all changes** made through tools

## 📊 Logging & Troubleshooting

### Common Log Files
- **Tool-specific logs** (e.g., `tacacs_checker.log`, `check_cdp_aps.log`)
- **Error logs** for failed operations
- **Session logs** for debugging connection issues
- **Excel reports** with detailed results

### Troubleshooting Steps
1. **Check network connectivity** to target switches
2. **Verify credentials** in `.env` files
3. **Review tool-specific logs** for error details
4. **Check Excel file formats** and column names
5. **Verify switch compatibility** and access permissions

## 🔄 Maintenance & Updates

### Regular Maintenance
- **Update Python dependencies** periodically
- **Review and update** credential files
- **Test tools** against new switch firmware
- **Update Excel inventories** as network changes

### Tool Updates
- **Check for new features** in individual tool directories
- **Review documentation** for changes and improvements
- **Test updated tools** in lab environment
- **Update deployment procedures** as needed

## 📞 Support & Contribution

### Getting Help
- **Review individual tool README** files for specific guidance
- **Check log files** for detailed error information
- **Verify prerequisites** and dependencies
- **Test with simple scenarios** first

### Best Practices for Success
1. **Start small** - Test with a few switches first
2. **Read documentation** thoroughly before use
3. **Backup everything** before making changes
4. **Monitor progress** during execution
5. **Verify results** after completion

## 📝 License & Disclaimer

These tools are provided for network administration purposes. Always:
- **Test thoroughly** before production use
- **Backup configurations** before making changes
- **Follow your organization's** change management procedures
- **Verify compliance** with security policies

---

*Last Updated: 2024*
*For tool-specific documentation, see individual README files in each tool directory.* 
