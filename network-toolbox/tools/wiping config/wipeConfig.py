from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException, ReadTimeout
import pandas as pd
from getpass import getpass
import os
import re
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Load switch IPs from Excel
excel_path = "switch_list.xlsx"  # Must have a column named "IP"
df = pd.read_excel(excel_path)
switch_ips = df['IP'].dropna().tolist()

# Get login credentials
username = input("Username: ")
password = getpass("Password: ")
enable_secret = getpass("Enable password: ")

# Load target usernames from environment variables
TARGET_USERNAMES = []
for i in range(1, 6):  # Support up to 5 target usernames
    target_user = os.getenv(f'TARGET_USERNAME_{i}')
    if target_user:
        TARGET_USERNAMES.append(target_user)

# Check if target usernames are configured
if not TARGET_USERNAMES:
    print("❌ Error: No TARGET_USERNAME_* environment variables found in .env file")
    print("❌ Please configure TARGET_USERNAME_1, TARGET_USERNAME_2, etc. in your .env file")
    print("❌ See .env.example for configuration template")
    exit(1)

TARGET_USERNAMES_LOWER = {u.lower() for u in TARGET_USERNAMES}
print(f"Target usernames to remove: {', '.join(TARGET_USERNAMES)}")

# Configuration patterns to remove
REMOVABLE_PREFIXES = [
    "snmp-server",
    "ntp server",
    "ntp source",
    "ntp authenticate",
    "ntp authentication-key",
    "ntp trusted-key",
    "banner exec",
    "banner login",
    "banner motd",
    "logging host",
    "ip domain-name",
    "ip host",
    "ip name-server",
    "tacacs-server host"
]

# Log file for errors
error_log_path = "removal_errors.txt"
if os.path.exists(error_log_path):
    os.remove(error_log_path)

def log_error(ip, cmd, error):
    with open(error_log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ip}] Failed on command: '{cmd}'\nError: {str(error)}\n\n")

def parse_line_config(output: str):
    lines_with_password7 = []
    needs_login_local_map = {}
    current_line = None

    for raw_line in output.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("line "):
            current_line = stripped
            # ensure key exists; default False (no change) until we see a need
            needs_login_local_map.setdefault(current_line, False)
            continue
        if current_line is None:
            continue
        if "password 7" in stripped:
            if current_line not in lines_with_password7:
                lines_with_password7.append(current_line)
        if "login" in stripped:
            if "login local" in stripped:
                needs_login_local_map[current_line] = False
            else:
                needs_login_local_map[current_line] = True

    return lines_with_password7, needs_login_local_map

# Add helper to apply configs and handle [confirm] prompts and sub-modes
def apply_config_with_confirms(conn, global_cmds, line_blocks):
    try:
        conn.config_mode()
    except Exception:
        pass

    def send_and_confirm(cmd: str):
        output = conn.send_command_timing(cmd, strip_prompt=False, strip_command=False)
        if re.search(r"\[confirm\]|\(y/n\)|\[yes/no\]|Destination filename", output, re.IGNORECASE):
            output = conn.send_command_timing("\n", strip_prompt=False, strip_command=False)
        return output

    # Apply global commands one-by-one
    for cmd in global_cmds:
        try:
            send_and_confirm(cmd)
        except Exception as e:
            # continue applying others but surface later via caller
            raise e

    # Apply per-line blocks
    for line_ctx, cmds in line_blocks.items():
        send_and_confirm(line_ctx)
        for sub in cmds:
            send_and_confirm(sub)
        conn.send_command_timing("exit", strip_prompt=False, strip_command=False)

    try:
        conn.exit_config_mode()
    except Exception:
        pass

# Begin loop
for ip in switch_ips:
    print(f"🔌 Connecting to {ip}...")
    try:
        conn = ConnectHandler(
            device_type="cisco_ios",
            host=ip,
            username=username,
            password=password,
            secret=enable_secret,
            fast_cli=False
        )
        conn.enable()

        print(f"📄 Getting config from {ip}...")
        try:
            # Stabilize session and disable paging
            conn.send_command_timing("terminal length 0")
            conn.send_command_timing("terminal width 511")
            device_prompt = conn.find_prompt()

            # Fetch only relevant lines using a single include-regex
            include_parts = [
                r"^snmp-server",
                r"^ntp server",
                r"^ntp source",
                r"^ntp authenticate",
                r"^ntp authentication-key",
                r"^ntp trusted-key",
                r"^banner exec",
                r"^banner login",
                r"^banner motd",
                r"^logging host",
                r"^ip domain-name",
                r"^ip host ",
                r"^ip name-server",
                r"^tacacs-server host",
                r"^tacacs-server key",
                r"^username "
            ]
            include_regex = "|".join(include_parts)
            show_cmd = f"show running-config | include {include_regex}"

            config_output = conn.send_command(
                show_cmd,
                expect_string=re.escape(device_prompt.strip()),
                read_timeout=120
            )
        except ReadTimeout:
            # Fallback that doesn't rely on prompt detection
            config_output = conn.send_command_timing(
                show_cmd,
                delay_factor=2,
                strip_prompt=False,
                strip_command=False
            )
        config_lines = config_output.splitlines()

        # Fetch 'line' sections to handle password 7 removal and login local
        line_show_cmd = "show running-config | section line"
        try:
            line_section_output = conn.send_command(
                line_show_cmd,
                expect_string=re.escape(device_prompt.strip()),
                read_timeout=120
            )
        except ReadTimeout:
            line_section_output = conn.send_command_timing(
                line_show_cmd,
                delay_factor=2,
                strip_prompt=False,
                strip_command=False
            )
        lines_with_password7, login_local_map = parse_line_config(line_section_output)

        print(f"🧹 Sending cleanup commands to {ip}...")
        # Build a single batched set of removal commands
        removal_cmds = []
        removal_cmds_set = set()

        # Avoid duplicate removals for global settings and multi-line banners
        name_server_removed = False
        domain_name_removed = False
        host_removed_names = set()
        banner_exec_removed = False
        banner_login_removed = False
        banner_motd_removed = False
        tacacs_key_removed = False
        # Track usernames removed
        user_removed_names = set()

        # Prefixes we can safely remove exactly as shown
        EXACT_PREFIXES = [
            "snmp-server",
            "ntp server",
            "ntp source",
            "ntp authenticate",
            "ntp authentication-key",
            "ntp trusted-key",
            "logging host",
            "tacacs-server host"
        ]

        for line in config_lines:
            stripped_line = line.strip()

            try:
                # ip name-server (handle VRF vs global)
                if stripped_line.startswith("ip name-server"):
                    if " vrf " in stripped_line:
                        candidate = "no " + stripped_line
                        if candidate not in removal_cmds_set:
                            removal_cmds.append(candidate)
                            removal_cmds_set.add(candidate)
                    else:
                        if not name_server_removed:
                            candidate = "no ip name-server"
                            removal_cmds.append(candidate)
                            removal_cmds_set.add(candidate)
                            name_server_removed = True

                # ip domain-name (single global setting)
                elif stripped_line.startswith("ip domain-name"):
                    if not domain_name_removed:
                        candidate = "no ip domain-name"
                        removal_cmds.append(candidate)
                        removal_cmds_set.add(candidate)
                        domain_name_removed = True

                # ip host (remove by hostname)
                elif stripped_line.startswith("ip host "):
                    parts = stripped_line.split()
                    if len(parts) >= 3:
                        host_name = parts[2]
                        if host_name not in host_removed_names:
                            candidate = f"no ip host {host_name}"
                            removal_cmds.append(candidate)
                            removal_cmds_set.add(candidate)
                            host_removed_names.add(host_name)

                # banners: remove once per type
                elif stripped_line.startswith("banner exec"):
                    if not banner_exec_removed:
                        candidate = "no banner exec"
                        removal_cmds.append(candidate)
                        removal_cmds_set.add(candidate)
                        banner_exec_removed = True
                elif stripped_line.startswith("banner login"):
                    if not banner_login_removed:
                        candidate = "no banner login"
                        removal_cmds.append(candidate)
                        removal_cmds_set.add(candidate)
                        banner_login_removed = True
                elif stripped_line.startswith("banner motd"):
                    if not banner_motd_removed:
                        candidate = "no banner motd"
                        removal_cmds.append(candidate)
                        removal_cmds_set.add(candidate)
                        banner_motd_removed = True

                # usernames: remove only targeted usernames
                elif stripped_line.startswith("username "):
                    parts = stripped_line.split()
                    if len(parts) >= 2:
                        user_name = parts[1]
                        if user_name.lower() in TARGET_USERNAMES_LOWER and user_name not in user_removed_names:
                            candidate = f"no username {user_name}"
                            if candidate not in removal_cmds_set:
                                removal_cmds.append(candidate)
                                removal_cmds_set.add(candidate)
                                user_removed_names.add(user_name)

                # tacacs key: remove generically (once)
                elif stripped_line.startswith("tacacs-server key"):
                    if not tacacs_key_removed:
                        candidate = "no tacacs-server key"
                        removal_cmds.append(candidate)
                        removal_cmds_set.add(candidate)
                        tacacs_key_removed = True

                # Default exact removals
                elif any(stripped_line.startswith(prefix) for prefix in EXACT_PREFIXES):
                    candidate = "no " + stripped_line
                    if candidate not in removal_cmds_set:
                        removal_cmds.append(candidate)
                        removal_cmds_set.add(candidate)

            except Exception as e:
                print(f"⚠️ Error while analyzing '{stripped_line}'")
                log_error(ip, stripped_line, e)

        # Prepare line-mode changes separately
        line_blocks = {}
        try:
            if 'lines_with_password7' in locals() and 'login_local_map' in locals():
                for line_ctx in lines_with_password7:
                    line_blocks.setdefault(line_ctx, []).append("no password 7")
                for line_ctx, needs_login_local in login_local_map.items():
                    if needs_login_local:
                        line_blocks.setdefault(line_ctx, []).append("login local")
        except Exception as e:
            print("⚠️ Error while preparing line-mode changes")
            log_error(ip, "line-mode-prep", e)

        # Send all removals with confirm-handling
        if removal_cmds or line_blocks:
            try:
                apply_config_with_confirms(conn, removal_cmds, line_blocks)
                # Auto-save configuration
                conn.save_config()
            except Exception as e:
                print("⚠️ Error during batched removal push")
                to_log = "\n".join(removal_cmds)
                for line_ctx, cmds in line_blocks.items():
                    to_log += f"\n{line_ctx}\n" + "\n".join(cmds)
                log_error(ip, to_log, e)

        conn.disconnect()
        print(f"✅ Finished cleanup for {ip}\n")

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as conn_err:
        print(f"❌ Could not connect to {ip}: {conn_err}")
        log_error(ip, "Connection", conn_err)
