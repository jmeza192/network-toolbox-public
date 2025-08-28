# TACACS Checker and Changer

This script connects to Cisco network devices to check their current TACACS configuration and optionally update them with new TACACS server IPs.

## Prerequisites

1. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your credentials:
   ```
   PRIMARY_USERNAME=your_username
   PRIMARY_PASSWORD=your_password
   
   # Fallback credentials (optional)
   FALLBACK_USER1=fallback_user
   FALLBACK_PASS1=fallback_pass
   FALLBACK_SECRET1=fallback_enable_secret
   ```

## Excel File Requirements

The script requires an Excel file (e.g., `Change tacacs IP address.xlsx`) with the following specifications:

### Required Columns:
- **IP**: Contains the IP addresses of network devices to connect to
  - Column name must be exactly `IP` (case-sensitive)
  - One IP address per row
  - IP addresses should be in standard IPv4 format (e.g., 192.168.1.1)

### Generated Columns:
The script will automatically create and populate the following columns:
- **Login Username**: Username used to successfully connect
- **TACACS Status**: Current TACACS configuration status
- **TACACS Configuration**: Full TACACS server configuration found on device
- **Connection Status**: Whether connection was successful
- **Error Details**: Any errors encountered during connection/processing

### Example Excel Structure:
| IP          | Login Username | TACACS Status | TACACS Configuration | Connection Status | Error Details |
|-------------|----------------|---------------|---------------------|-------------------|---------------|
| 10.1.1.1    |                |               |                     |                   |               |
| 10.1.1.2    |                |               |                     |                   |               |
| 10.1.1.3    |                |               |                     |                   |               |

## Usage

### Check TACACS Configuration Only:
```bash
python Tacacs_Checker.py path/to/your/excel_file.xlsx
```

### Check and Update TACACS Servers:
```bash
python Tacacs_Checker.py path/to/your/excel_file.xlsx --clearpass-ips 10.1.1.100 10.1.1.101
```

## Features

- **Multi-credential Support**: Attempts primary credentials first, then falls back to configured backup credentials
- **TACACS Detection**: Identifies current TACACS server configurations
- **Configuration Update**: Can replace old TACACS servers with new ClearPass IPs
- **Comprehensive Logging**: Detailed logging to `tacacs_checker.log`
- **Error Handling**: Graceful handling of connection failures and authentication issues
- **Excel Integration**: Results are written back to the original Excel file

## Command Line Arguments

- **excel_file**: Path to the Excel file containing device IPs (required)
- **--clearpass-ips**: Space-separated list of new TACACS server IPs to configure (optional)

## Output

- Results are written directly back to the Excel file
- Detailed logs are saved to `tacacs_checker.log`
- Progress is displayed in the console during execution

## TACACS Configuration Changes

When `--clearpass-ips` is provided, the script will:
1. Remove existing `tacacs-server host` configurations
2. Add new TACACS server configurations with the provided IPs
3. Configure appropriate TACACS settings (timeout, key, etc.)

## Notes

- The script uses SSH to connect to devices (ensure port 22 is accessible)
- Supports Cisco IOS devices
- Empty or invalid IP addresses in the Excel file will be skipped
- Connection timeouts and authentication failures are logged but don't stop processing
- Always backup your Excel file before running configuration changes