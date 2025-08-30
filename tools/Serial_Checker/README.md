# Switch Serial Number Collector

This Python script automates the process of collecting serial numbers from Cisco switches and updating them in an Excel spreadsheet. It supports multiple sheets in the Excel file, where each sheet represents a different hospital.

## Prerequisites

- Python 3.7 or higher
- Network access to the Cisco switches
- Valid credentials for the switches
- Excel file with a "Switch IP" column

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the template below:
   ```
   # Cisco switch credentials
   SWITCH_USERNAME=your_username
   SWITCH_PASSWORD=your_password
   
   # Path to your Excel file
   EXCEL_FILE_PATH=path/to/your/switches.xlsx
   ```

## Excel File Format

Your Excel file should have:
- A column named exactly "Switch IP" containing the IP addresses of the switches
- The script will automatically create a "Serial Number" column to the right of the "Switch IP" column

## Usage

1. Fill in your `.env` file with the correct credentials and file path
2. Run the script:
   ```bash
   python switch_serial_updater.py
   ```

The script will:
- Process each sheet in the Excel file
- Connect to each switch using the provided credentials
- Retrieve the serial number using the "show version" command
- Update the Excel file with the serial numbers
- Create a log file (`switch_serial.log`) with detailed information about the process

## Error Handling

The script includes comprehensive error handling for:
- Network connectivity issues
- Authentication failures
- Invalid Excel file format
- Missing columns
- Invalid IP addresses

All errors are logged to both the console and `switch_serial.log` file.

## Security Notes

- Never commit your `.env` file to version control
- Use strong passwords for switch access
- Ensure your network connection to the switches is secure

## Troubleshooting

If you encounter issues:
1. Check the `switch_serial.log` file for detailed error messages
2. Verify your network connectivity to the switches
3. Confirm your switch credentials are correct
4. Ensure your Excel file has the correct column name ("Switch IP") 