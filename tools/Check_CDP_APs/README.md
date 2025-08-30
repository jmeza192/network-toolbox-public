# Check CDP APs Tool

A network automation script that connects to Cisco switches to discover and inventory access points (APs) using CDP (Cisco Discovery Protocol).

## Purpose

This tool automatically scans network switches to find all connected Cisco access points through CDP neighbor discovery. It provides a comprehensive inventory of APs across multiple network locations.

## Features

- **Multi-site support**: Configure up to 16 different network locations
- **Credential fallback**: Primary and backup authentication credentials
- **Robust CDP parsing**: Handles both detailed and brief CDP output formats
- **AP detection**: Identifies Cisco APs using platform pattern matching
- **Detailed reporting**: Shows AP device ID, IP address, platform, local interface, and port ID
- **Logging**: Comprehensive logging to `check_cdp_aps.log`
- **Debug mode**: Special debug output for specified IP addresses

## Prerequisites

- Python 3.6+
- Required packages (install with `pip install -r requirements.txt`):
  - netmiko
  - python-dotenv

## Configuration

1. Create a `.env` file in the same directory as the script (use `.env.example` as template)
2. Configure credentials:
   ```
   SWITCH_USERNAME=your_username
   SWITCH_PASSWORD=your_password
   SWITCH_ENABLE_PASSWORD=optional_enable_password
   ```
3. Configure network locations (up to 16 sites):
   ```
   LOCATION_1_NAME=Site1
   LOCATION_1_IP=192.168.1.1
   LOCATION_2_NAME=Site2
   LOCATION_2_IP=192.168.2.1
   ```

## Usage

```bash
python CheckCDPAPs.py
```

The script will automatically:
1. Connect to each configured switch
2. Run CDP neighbor commands
3. Parse and filter for access points
4. Display results grouped by site
5. Provide a final summary

## Output Example

```
Site: Main Office
 192.168.1.1: 3 AP(s)
  - AP-Office-101 (192.168.1.101) [AIR-CAP3702I-A-K9] @ Gi1/0/24 -> GigabitEthernet0
  - AP-Office-102 (192.168.1.102) [AIR-CAP2702I-A-K9] @ Gi2/0/12 -> GigabitEthernet0
  - AP-Office-103 (N/A) [Catalyst 9120AXI] @ Gi1/0/8 -> GigabitEthernet0

Summary:
 Main Office | 192.168.1.1: 3 AP(s)
```

## Error Handling

- Automatic credential fallback if primary authentication fails
- Robust command execution with multiple retry strategies
- Graceful handling of CDP command variations across switch platforms
- Connection timeout and authentication error recovery

## Debug Mode

Set `SPECIAL_IP_1`, `SPECIAL_IP_2`, or `SPECIAL_IP_3` environment variables to enable debug output for specific switches. This will create debug files with raw CDP command output.