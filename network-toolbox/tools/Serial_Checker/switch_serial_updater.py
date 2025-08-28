import pandas as pd
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('switch_serial.log'),
        logging.StreamHandler()
    ]
)

def get_switch_serial(ip: str, username: str, password: str) -> Optional[str]:
    """
    Connect to a Cisco switch and retrieve its serial number.
    
    Args:
        ip: IP address of the switch
        username: SSH username
        password: SSH password
    
    Returns:
        str: Serial number if successful, None if failed
    """
    device = {
        'device_type': 'cisco_ios',
        'ip': ip,
        'username': username,
        'password': password,
    }
    
    try:
        logging.info(f"Attempting to connect to switch at {ip}")
        with ConnectHandler(**device) as connection:
            # Get full show version output
            output = connection.send_command('show version')
            
            if not isinstance(output, str):
                logging.error(f"Unexpected output type from {ip}: {type(output)}")
                return None
                
            # Try different patterns to find serial number
            serial = None
            
            # Pattern 1: System serial number
            if "System serial number" in output.lower():
                for line in output.split('\n'):
                    if "System serial number" in line.lower():
                        serial = line.split(':')[-1].strip()
                        break
            
            # Pattern 2: System Serial Number
            elif "System Serial Number" in output:
                for line in output.split('\n'):
                    if "System Serial Number" in line:
                        serial = line.split(':')[-1].strip()
                        break
            
            # Pattern 3: Look for specific line format
            else:
                for line in output.split('\n'):
                    if any(pattern in line for pattern in [
                        "Processor board ID",
                        "Chassis Serial Number",
                        "Serial Number"
                    ]):
                        parts = line.split(':' if ':' in line else 'ID')
                        if len(parts) > 1:
                            serial = parts[-1].strip()
                            break
            
            if serial:
                logging.info(f"Successfully retrieved serial number from {ip}")
                return serial
            else:
                logging.warning(f"Could not find serial number in output from {ip}")
                logging.debug(f"Full output from {ip}: {output}")
                return None
                
    except NetMikoTimeoutException:
        logging.error(f"Timeout while connecting to {ip}")
        return None
    except NetMikoAuthenticationException:
        logging.error(f"Authentication failed for {ip}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while connecting to {ip}: {str(e)}")
        return None

def process_excel_file(file_path: str, username: str, password: str) -> None:
    """
    Process Excel file and update serial numbers for all switches.
    
    Args:
        file_path: Path to the Excel file
        username: SSH username
        password: SSH password
    """
    try:
        # Read Excel file with all sheets
        excel_file = pd.ExcelFile(file_path)
        
        # Process each sheet
        for sheet_name in excel_file.sheet_names:
            logging.info(f"Processing sheet: {sheet_name}")
            
            # Read the sheet
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Check if required column exists
            if 'Switch IP' not in df.columns:
                logging.warning(f"Sheet {sheet_name} does not have 'Switch IP' column. Skipping.")
                continue
            
            # Add Serial Number column if it doesn't exist
            if 'Serial Number' not in df.columns:
                df.insert(
                    df.columns.get_loc('Switch IP') + 1,
                    'Serial Number',
                    ''
                )
            
            # Process each switch
            for index, row in df.iterrows():
                ip = str(row['Switch IP']).strip()
                
                # Skip empty or invalid IPs
                if not ip or pd.isna(ip):
                    continue
                
                # Get serial number
                serial = get_switch_serial(ip, username, password)
                if serial:
                    df.at[index, 'Serial Number'] = serial
            
            # Write the updated sheet back to the file
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
            logging.info(f"Completed processing sheet: {sheet_name}")
            
    except Exception as e:
        logging.error(f"Error processing Excel file: {str(e)}")
        raise

def main():
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    username = os.getenv('SWITCH_USERNAME')
    password = os.getenv('SWITCH_PASSWORD')
    excel_file = os.getenv('EXCEL_FILE_PATH')
    
    if not all([username, password, excel_file]):
        logging.error("Missing required environment variables")
        print("Please set SWITCH_USERNAME, SWITCH_PASSWORD, and EXCEL_FILE_PATH in .env file")
        return
    
    try:
        if excel_file is None or username is None or password is None:
            raise ValueError("Excel file path, username, or password is None")
        process_excel_file(excel_file, username, password)
        print("Successfully updated serial numbers in the Excel file")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Check the log file for more details")

if __name__ == "__main__":
    main() 