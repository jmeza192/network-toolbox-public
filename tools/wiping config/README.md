# Configuration Wiper Script

This script connects to Cisco switches and removes specific configuration elements like SNMP settings, NTP servers, banners, logging hosts, and user accounts. It's designed for cleaning up switch configurations in bulk.

## Prerequisites

1. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file (copy from `.env.example` and configure)

3. Prepare your Excel file with switch IP addresses

## Configuration

### Environment Variables (.env file)

Create a `.env` file in the same directory as the script (use `.env.example` as template):

```bash
# Target usernames to remove from switch configurations
TARGET_USERNAME_1=username1
TARGET_USERNAME_2=username2
TARGET_USERNAME_3=username3
```

The script will display which usernames it will target when it starts.

## Excel File Requirements

The script requires an Excel file named `switch_list.xlsx` with the following specifications:

### Required Columns:
- **IP**: Contains the IP addresses of switches to clean up
  - Column name must be exactly `IP` (case-sensitive)
  - One IP address per row
  - IP addresses should be in standard IPv4 format (e.g., 192.168.1.1)

### Example Excel Structure:
| IP          |
|-------------|
| 10.1.1.1    |
| 10.1.1.2    |
| 10.1.1.3    |
| 10.1.1.4    |

## Usage

1. Ensure your `switch_list.xlsx` file is in the same directory as the script
2. Run the script:
   ```bash
   python wipeConfig.py
   ```
3. When prompted, enter:
   - Username for switch access
   - Password for switch access
   - Enable password (if required)

## What Gets Removed

The script removes the following configuration elements:

### SNMP Configuration:
- All `snmp-server` commands

### NTP Configuration:
- `ntp server` entries
- `ntp source` settings
- `ntp authenticate` settings
- `ntp authentication-key` entries
- `ntp trusted-key` settings

### Banner Configuration:
- `banner exec` messages
- `banner login` messages
- `banner motd` messages

### Network Services:
- `logging host` entries
- `ip domain-name` settings
- `ip host` entries
- `ip name-server` entries
- `tacacs-server host` entries

### User Accounts:
The script targets specific usernames for removal based on your `.env` configuration:
- Configure `TARGET_USERNAME_1`, `TARGET_USERNAME_2`, etc. in your `.env` file
- Up to 5 different target usernames are supported
- If no environment variables are set, falls back to default hardcoded usernames

### TTY Line Configuration:
- Removes password encryption from TTY lines
- Updates line configuration to use local authentication

## Output

- **Console Output**: Real-time progress and status updates
- **Error Log**: Failed commands are logged to `removal_errors.txt`
- **Configuration Changes**: All changes are committed to the switch's running and startup configuration

## Safety Features

- **Error Logging**: All failed commands are logged for review
- **Individual Switch Processing**: Failure on one switch doesn't stop processing of others
- **Command Verification**: Each configuration removal is attempted individually
- **Connection Handling**: Robust error handling for network and authentication issues

## Important Notes

⚠️ **WARNING**: This script makes permanent configuration changes to your switches.

- **Backup First**: Always backup your switch configurations before running this script
- **Test Environment**: Test in a non-production environment first
- **Review Targets**: Verify the IP addresses in your Excel file are correct
- **Credentials**: Ensure you have appropriate administrative access
- **Network Access**: Switches must be reachable via SSH (port 22)

## Error Handling

The script includes comprehensive error handling for:
- Network connectivity issues
- Authentication failures
- Invalid Excel file format
- Missing IP addresses
- Command execution failures

All errors are logged to `removal_errors.txt` with details about which switch and command failed.

## Troubleshooting

If you encounter issues:
1. Check the `removal_errors.txt` file for detailed error messages
2. Verify network connectivity to the switches
3. Confirm your credentials have sufficient privileges
4. Ensure your Excel file has the correct column name (`IP`)
5. Verify switches are accessible via SSH on port 22