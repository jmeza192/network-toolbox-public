#!/usr/bin/env python3

import pandas as pd
from netmiko import ConnectHandler, BaseConnection
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    filename='tacacs_checker.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class Credentials:
    username: str
    password: str
    enable_password: Optional[str] = None
    description: str = "Default"

class TacacsChecker:
    def __init__(self, excel_file: str, clearpass_ips: List[str]):
        """Initialize the TacacsChecker with Excel file path and the new Clearpass IPs"""
        self.excel_file = excel_file
        self.clearpass_ips = clearpass_ips
        self.df = self._read_excel()
        
    def _read_excel(self) -> pd.DataFrame:
        """Read and validate Excel file"""
        try:
            df = pd.read_excel(self.excel_file)
            if 'IP' not in df.columns:
                raise ValueError("Excel file must contain an 'IP' column")
            
            # Initialize result columns
            new_columns = {
                'Login Username': '',
                'TACACS Status': '',
                'TACACS Configuration': '',
                'Found Clearpass IPs': ''
            }
            for col, default in new_columns.items():
                if col not in df.columns:
                    df[col] = default
            
            logging.info(f"Successfully read {len(df)} switches from Excel file")
            return df
            
        except Exception as e:
            logging.error(f"Error reading Excel file: {str(e)}")
            raise

    def _get_tacacs_config(self, connection: BaseConnection) -> Tuple[str, Dict]:
        """Get and parse TACACS configuration from switch"""
        # Try the filtered command first
        try:
            output = connection.send_command("show run | i tacacs", delay_factor=2)
        except Exception as e:
            logging.warning(f"Error running filtered command: {str(e)}")
            output = ""
            
        # If output is too short or empty, try full config and filter it ourselves
        if not isinstance(output, str) or len(output.strip().split('\n')) < 2:
            print("  Limited config output, trying full configuration...")
            output = connection.send_command("show run", delay_factor=3)  # Increased delay for full config
            if not isinstance(output, str):
                output = str(output)
            
            # Extract TACACS related configuration from full config
            config_lines = []
            in_block = False
            
            for line in output.split('\n'):
                line = line.rstrip()
                # Check for start of TACACS or AAA block
                if any(line.startswith(prefix) for prefix in ['aaa group server tacacs', 'tacacs', 'tacacs-server', ' server', 'ip tacacs']):
                    in_block = True
                    config_lines.append(line)
                # Continue capturing indented configuration
                elif in_block and line.startswith(' '):
                    config_lines.append(line)
                # Reset block flag if we hit a non-indented line
                elif not line.startswith(' '):
                    in_block = False
            
            output = '\n'.join(config_lines)
        
        # Parse the configuration
        tacacs_details = {
            'raw_config': output,
            'servers': [],
            'groups': {},
            'using_new_clearpass': False,
            'found_clearpass_ips': []
        }
    
        # Extract all server information (both new and old style)
        server_matches = re.finditer(r'(?:tacacs-server host|tacacs server|server name|server) (\S+)(?:\s+|$)', output)
        for match in server_matches:
            server = match.group(1)
            # If it's not an IP address, look for its IP in the config
            if not re.match(r'\d+\.\d+\.\d+\.\d+', server):
                ip_match = re.search(rf'{server}\s+address ipv4 (\d+\.\d+\.\d+\.\d+)', output)
                if ip_match:
                    server = ip_match.group(1)
            
            if server not in tacacs_details['servers']:
                tacacs_details['servers'].append(server)
                if server in self.clearpass_ips:
                    tacacs_details['using_new_clearpass'] = True
                    tacacs_details['found_clearpass_ips'].append(server)

        # Extract TACACS groups and resolve server names to IPs where possible
        for group_match in re.finditer(r'aaa group server tacacs\+ ([^\n]+)((?:\n[^\n]+)*)', output):
            group_name = group_match.group(1).strip()
            servers = re.findall(r'server (?:name )?(\S+)', group_match.group(2))
            resolved_servers = []
            for server in servers:
                if not re.match(r'\d+\.\d+\.\d+\.\d+', server):
                    ip_match = re.search(rf'{server}\s+address ipv4 (\d+\.\d+\.\d+\.\d+)', output)
                    resolved_servers.append(ip_match.group(1) if ip_match else server)
                else:
                    resolved_servers.append(server)
            tacacs_details['groups'][group_name] = resolved_servers

        return output, tacacs_details

    def check_switches(self, credentials_list: List[Credentials]) -> Dict:
        """Check TACACS configuration on all switches and update Excel file"""
        results = {
            'updated_switches': [],
            'outdated_switches': [],
            'unreachable_switches': []
        }

        total_switches = len(self.df)
        print(f"\nStarting checks on {total_switches} switches...")
        
        # Process each switch
        for index, row in self.df.iterrows():
            ip = str(row['IP'])
            print(f"\nChecking switch {index + 1}/{total_switches}: {ip}")
            
            switch_result = self._check_single_switch(ip, credentials_list)
            
            # Update Excel file with results
            mask = self.df['IP'] == ip
            self.df.loc[mask, 'Login Username'] = switch_result.get('login_username', 'N/A')
            
            if 'error' in switch_result:
                results['unreachable_switches'].append(switch_result)
                self.df.loc[mask, 'TACACS Status'] = f"Error: {switch_result['error']}"
                self.df.loc[mask, 'Found Clearpass IPs'] = 'N/A'
                self.df.loc[mask, 'TACACS Configuration'] = 'N/A'
                print(f"❌ Failed to check {ip}: {switch_result['error']}")
            else:
                if switch_result['config']['using_new_clearpass']:
                    results['updated_switches'].append(switch_result)
                    self.df.loc[mask, 'TACACS Status'] = 'Updated'
                    print(f"✅ {ip} has updated Clearpass IPs: {', '.join(switch_result['config']['found_clearpass_ips'])}")
                else:
                    results['outdated_switches'].append(switch_result)
                    self.df.loc[mask, 'TACACS Status'] = 'Outdated'
                    print(f"⚠️ {ip} has outdated Clearpass configuration")
                
                self.df.loc[mask, 'Found Clearpass IPs'] = ', '.join(switch_result['config']['found_clearpass_ips'])
                self.df.loc[mask, 'TACACS Configuration'] = switch_result['config']['raw_config']
            
            # Save progress after each switch
            try:
                self.df.to_excel(self.excel_file, index=False)
                print(f"Progress saved to Excel file ({index + 1}/{total_switches} switches processed)")
            except Exception as e:
                print(f"Warning: Could not save progress to Excel file: {str(e)}")
            
            # Print a progress summary every 5 switches
            if (index + 1) % 5 == 0 or index + 1 == total_switches:
                print(f"\nProgress Summary ({index + 1}/{total_switches} switches):")
                print(f"Updated: {len(results['updated_switches'])}")
                print(f"Outdated: {len(results['outdated_switches'])}")
                print(f"Unreachable: {len(results['unreachable_switches'])}")
        
        print("\nAll switches processed!")
        return results

    def _check_single_switch(self, ip: str, credentials_list: List[Credentials]) -> Dict:
        """Check TACACS configuration for a single switch"""
        for creds in credentials_list:
            device = {
                'device_type': 'cisco_ios',
                'ip': ip,
                'username': creds.username,
                'password': creds.password,
                'global_delay_factor': 2,  # Double the time netmiko waits
                'timeout': 60,  # Increase timeout to 60 seconds
                'banner_timeout': 20,  # Increase banner timeout
                'conn_timeout': 20,  # Increase connection timeout
            }
            
            if creds.enable_password:
                device['secret'] = creds.enable_password
            
            try:
                print(f"  Attempting to connect with {creds.description}...")
                connection = ConnectHandler(**device)
                
                # Wait for prompt to stabilize
                print("  Waiting for prompt...")
                connection.find_prompt()
                
                if creds.enable_password:
                    print("  Entering enable mode...")
                    connection.enable()
                    # Wait again after enable mode
                    connection.find_prompt()
                
                print(f"  Successfully connected using {creds.description} ({creds.username})")
                print("  Checking TACACS configuration...")
                
                # Add delay before sending command
                connection.send_command("terminal length 0")  # Disable paging
                _, tacacs_details = self._get_tacacs_config(connection)
                connection.disconnect()
                print("  Configuration retrieved successfully")
                
                return {
                    'ip': ip,
                    'login_username': creds.username,
                    'config': tacacs_details
                }
                
            except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
                print(f"  Failed to connect with {creds.description}: {str(e)}")
                continue
            except Exception as e:
                print(f"  Unexpected error with {creds.description}: {str(e)}")
                continue
            finally:
                # Ensure we try to disconnect in case of any error
                try:
                    if 'connection' in locals() and connection:
                        connection.disconnect()
                except:
                    pass
        
        return {
            'ip': ip,
            'login_username': None,
            'error': 'Failed to connect with all credentials'
        }

    def _save_results(self):
        """Save results to Excel file with backup"""
        try:
            # Create backup
            backup_file = self.excel_file.replace('.xlsx', '_backup.xlsx')
            pd.read_excel(self.excel_file).to_excel(backup_file, index=False)
            print(f"Created backup of original file: {backup_file}")
            
            # Save updated file
            self.df.to_excel(self.excel_file, index=False)
            print(f"Successfully updated Excel file with results: {self.excel_file}")
            
        except Exception as e:
            print(f"Error saving results to Excel: {str(e)}")
            raise

def load_credentials_from_env() -> List[Credentials]:
    """Load credentials from environment variables"""
    credentials_list = []
    
    # Load AD credentials
    ad_username = os.getenv('AD_USERNAME')
    ad_password = os.getenv('AD_PASSWORD')
    if ad_username and ad_password:
        credentials_list.append(Credentials(ad_username, ad_password, description="AD Account"))
    
    # Load Local Account 1 credentials
    local1_username = os.getenv('LOCAL1_USERNAME')
    local1_password = os.getenv('LOCAL1_PASSWORD')
    local1_enable = os.getenv('LOCAL1_ENABLE_PASSWORD')
    if local1_username and local1_password:
        credentials_list.append(Credentials(
            local1_username, 
            local1_password, 
            enable_password=local1_enable,
            description="Local Account 1"
        ))
    
    # Load Local Account 2 credentials
    local2_username = os.getenv('LOCAL2_USERNAME')
    local2_password = os.getenv('LOCAL2_PASSWORD')
    local2_enable = os.getenv('LOCAL2_ENABLE_PASSWORD')
    if local2_username and local2_password:
        credentials_list.append(Credentials(
            local2_username, 
            local2_password, 
            enable_password=local2_enable,
            description="Local Account 2"
        ))
    
    if not credentials_list:
        raise ValueError("No credentials found in environment variables. Please check your .env file.")
    
    return credentials_list

def main():
    print("Starting program...")
    
    # Debug: Print current working directory and .env file loading
    current_dir = os.getcwd()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Current working directory: {current_dir}")
    
    # Try to find Excel file
    excel_file = os.getenv('EXCEL_FILE_PATH', '').strip()
    if not excel_file:
        # Look for Excel files in the script directory
        excel_files = [f for f in os.listdir(script_dir) if f.endswith('.xlsx')]
        if len(excel_files) == 1:
            excel_file = excel_files[0]
            print(f"\nFound Excel file in script directory: {excel_file}")
        elif len(excel_files) > 1:
            print("\nFound multiple Excel files in script directory:")
            for i, f in enumerate(excel_files, 1):
                print(f"{i}. {f}")
            print("\nPlease set EXCEL_FILE_PATH in your .env file to specify which file to use.")
            raise ValueError("Multiple Excel files found. Please specify one in EXCEL_FILE_PATH")
        else:
            print("\nNo Excel files found in script directory.")
            raise ValueError("No Excel file found and EXCEL_FILE_PATH not set in .env file")
    
    # If path is not absolute, make it relative to script directory
    if not os.path.isabs(excel_file):
        excel_file = os.path.join(script_dir, excel_file)
    
    if not os.path.exists(excel_file):
        raise ValueError(f"Excel file not found: {excel_file}")
    
    print(f"Using Excel file: {excel_file}")
    
    # Get Clearpass IPs
    clearpass_ip1 = os.getenv('NEW_CLEARPASS_IP1')
    clearpass_ip2 = os.getenv('NEW_CLEARPASS_IP2')
    if not clearpass_ip1 or not clearpass_ip2:
        raise ValueError("Both NEW_CLEARPASS_IP1 and NEW_CLEARPASS_IP2 must be set in environment variables")
    
    clearpass_ips = [clearpass_ip1, clearpass_ip2]
    print(f"Using Clearpass IPs: {', '.join(clearpass_ips)}")
    
    # Initialize checker and run checks
    checker = TacacsChecker(excel_file, clearpass_ips)
    credentials_list = load_credentials_from_env()
    print(f"Found {len(credentials_list)} sets of credentials")
    
    print("Starting switch checks...")
    results = checker.check_switches(credentials_list)
    
    # Print results to console
    print("\nResults Summary:")
    print(f"Updated switches: {len(results['updated_switches'])}")
    print(f"Outdated switches: {len(results['outdated_switches'])}")
    print(f"Unreachable switches: {len(results['unreachable_switches'])}")
    
    # Print detailed results
    for category, switches in results.items():
        if not switches:
            continue
            
        print(f"\n{category.replace('_', ' ').title()}:")
        for switch in switches:
            print(f"\nIP: {switch['ip']}")
            print(f"Login username: {switch.get('login_username', 'N/A')}")
            
            if 'error' in switch:
                print(f"Error: {switch['error']}")
            else:
                if category == 'outdated_switches':
                    print("Missing Clearpass IPs:", 
                          ', '.join(ip for ip in clearpass_ips if ip not in switch['config']['found_clearpass_ips']))
                print("\nTACACS Configuration:")
                print("-" * 40)
                print(switch['config']['raw_config'])
                print("-" * 40)

if __name__ == "__main__":
    main()
