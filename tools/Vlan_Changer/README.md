# VLAN Changer Tool

A network automation script that locates network devices by IP address or MAC address and changes their access port VLAN configuration on Cisco switches.

## Purpose

This tool helps network administrators quickly find a device's switch port and change its VLAN assignment. It automatically traverses the network topology through CDP neighbors to locate access ports, even when devices are connected through multiple network layers.

## Features

- **Multi-site support**: Configure up to 20 different network locations
- **Dual lookup modes**: Find devices by IP address or MAC address
- **Automatic topology traversal**: Follows CDP neighbors through trunks to find access ports
- **Port-channel support**: Handles EtherChannel/port-channel configurations
- **VLAN configuration**: Set both access and voice VLANs
- **Credential fallback**: Multiple authentication credential sets
- **Smart retry logic**: Adaptive timing for slow switches
- **Configuration verification**: Confirms changes were applied correctly
- **Automatic saving**: Saves configuration to switch memory

## Prerequisites

- Python 3.6+
- Required packages (install with `pip install -r requirements.txt`):
  - netmiko
  - python-dotenv

## Configuration

1. Create a `.env` file in the same directory as the script (use `.env.example` as template)
2. Configure primary credentials:
   ```
   PRIMARY_USERNAME=your_username
   PRIMARY_PASSWORD=your_password
   ```
3. Configure fallback credentials (optional but recommended):
   ```
   FALLBACK_USER1=backup_username
   FALLBACK_PASS1=backup_password
   FALLBACK_SECRET1=enable_password
   ```
4. Configure network locations (up to 20 sites):
   ```
   VLAN_LOCATION_1_NAME=Main Office
   VLAN_LOCATION_1_IP=192.168.1.1
   VLAN_LOCATION_2_NAME=Branch Office
   VLAN_LOCATION_2_IP=192.168.2.1
   ```

## Usage

```bash
python VlanChange.py
```

The script will prompt you to:
1. Select a network site
2. Choose lookup method (IP or MAC address)
3. Enter the device identifier
4. Specify new access VLAN
5. Optionally specify voice VLAN
6. Confirm the changes

## Example Session

```
Select site:
 1) Main Office    192.168.1.1
 2) Branch Office  192.168.2.1
Enter choice 1-20: 1

Lookup by IP or MAC? (ip/mac): ip
Device IP: 192.168.1.100

✔ Connected to 192.168.1.1 as admin
↳ ARP: 192.168.1.100 → 001a.2b3c.4d5e

✓ Device found on 192.168.1.10  port Gi1/0/24

Access VLAN (blank cancels): 100
Voice VLAN (Enter to skip): 200
CONFIRM Gi1/0/24 → access 100, voice 200? (y/N): y

Pushing config …
✔ Configuration saved successfully
✔ Done.
```

## How It Works

1. **Device Location**: 
   - For IP lookup: Finds MAC address in ARP table
   - For MAC lookup: Uses provided MAC address
   
2. **Port Discovery**:
   - Searches MAC address table on core switches
   - If found on trunk port, follows CDP neighbors
   - Continues until access port is found
   - Handles port-channel configurations

3. **VLAN Configuration**:
   - Tests switch responsiveness and adapts timing
   - Applies configuration with verification
   - Retries failed commands automatically
   - Saves configuration to memory

## Switch Compatibility

- Cisco IOS/IOS-XE switches
- Supports various interface naming conventions (Gi, Fa, Te, etc.)
- Handles different CDP output formats
- Adapts to switch response times automatically

## Error Handling

- Multiple credential fallback options
- Automatic retry logic for slow switches
- Configuration verification before completion
- Detailed error messages and debugging output
- Graceful handling of network topology changes