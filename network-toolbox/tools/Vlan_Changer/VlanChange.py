import re, socket, getpass, sys, time
from typing import Optional, Tuple, List
from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Get credentials from environment variables
PRIMARY_USERNAME = os.getenv('PRIMARY_USERNAME')
PRIMARY_PASSWORD = os.getenv('PRIMARY_PASSWORD')

# Load fallback credentials
FALLBACK = [
    (
        os.getenv('FALLBACK_USER1', ''),
        os.getenv('FALLBACK_PASS1', ''),
        os.getenv('FALLBACK_SECRET1', '')
    ),
    (
        os.getenv('FALLBACK_USER2', ''),
        os.getenv('FALLBACK_PASS2', ''),
        os.getenv('FALLBACK_SECRET2', '')
    ),
    (
        os.getenv('FALLBACK_USER3', ''),
        os.getenv('FALLBACK_PASS3', ''),
        os.getenv('FALLBACK_SECRET3', '')
    ),
    (
        os.getenv('FALLBACK_USER4', ''),
        os.getenv('FALLBACK_PASS4', ''),
        os.getenv('FALLBACK_SECRET4', '')
    )
]

# Filter out any empty fallback credentials
FALLBACK = [creds for creds in FALLBACK if all(creds)]

def check_credentials():
    """Check if credentials are properly configured"""
    if not PRIMARY_USERNAME or not PRIMARY_PASSWORD:
        sys.exit("❌ Error: Primary credentials not found in .env file")
    if not FALLBACK:
        print("⚠ Warning: No fallback credentials configured in .env file")

# Sites loaded from environment variables - requires .env file
SITES = {
    "1": (os.getenv('VLAN_LOCATION_1_NAME'), [os.getenv('VLAN_LOCATION_1_IP')]),
    "2": (os.getenv('VLAN_LOCATION_2_NAME'), [os.getenv('VLAN_LOCATION_2_IP')]),
    "3": (os.getenv('VLAN_LOCATION_3_NAME'), [os.getenv('VLAN_LOCATION_3_IP')]),
    "4": (os.getenv('VLAN_LOCATION_4_NAME'), [ip for ip in [os.getenv('VLAN_LOCATION_4_IP_1'), os.getenv('VLAN_LOCATION_4_IP_2')] if ip]),
    "5": (os.getenv('VLAN_LOCATION_5_NAME'), [os.getenv('VLAN_LOCATION_5_IP')]),
    "6": (os.getenv('VLAN_LOCATION_6_NAME'), [os.getenv('VLAN_LOCATION_6_IP')]),
    "7": (os.getenv('VLAN_LOCATION_7_NAME'), [os.getenv('VLAN_LOCATION_7_IP')]),
    "8": (os.getenv('VLAN_LOCATION_8_NAME'), [os.getenv('VLAN_LOCATION_8_IP')]),
    "9": (os.getenv('VLAN_LOCATION_9_NAME'), [os.getenv('VLAN_LOCATION_9_IP')]),
    "10": (os.getenv('VLAN_LOCATION_10_NAME'), [os.getenv('VLAN_LOCATION_10_IP')]),
    "11": (os.getenv('VLAN_LOCATION_11_NAME'), [os.getenv('VLAN_LOCATION_11_IP')]),
    "12": (os.getenv('VLAN_LOCATION_12_NAME'), [os.getenv('VLAN_LOCATION_12_IP')]),
    "13": (os.getenv('VLAN_LOCATION_13_NAME'), [os.getenv('VLAN_LOCATION_13_IP')]),
    "14": (os.getenv('VLAN_LOCATION_14_NAME'), [os.getenv('VLAN_LOCATION_14_IP')]),
    "15": (os.getenv('VLAN_LOCATION_15_NAME'), [os.getenv('VLAN_LOCATION_15_IP')]),
    "16": (os.getenv('VLAN_LOCATION_16_NAME'), [os.getenv('VLAN_LOCATION_16_IP')]),
    "17": (os.getenv('VLAN_LOCATION_17_NAME'), [os.getenv('VLAN_LOCATION_17_IP')]),
    "18": (os.getenv('VLAN_LOCATION_18_NAME'), [os.getenv('VLAN_LOCATION_18_IP')]),
    "19": (os.getenv('VLAN_LOCATION_19_NAME'), [os.getenv('VLAN_LOCATION_19_IP')]),
    "20": (os.getenv('VLAN_LOCATION_20_NAME'), [os.getenv('VLAN_LOCATION_20_IP')])
}

def choose_site() -> Tuple[str, List[str]]:
    print("\nSelect site:")
    for num, (name, ips) in SITES.items():
        print(f" {num}) {name:<11} {' / '.join(ips)}")
    choice = input("Enter choice 1-20: ").strip()
    if choice in SITES:
        return SITES[choice]
    sys.exit("❌  Invalid choice")

esc_pat = re.compile(r'\x1b\[[0-9;]*[mK]')

def clean_prompt(pr):
    pr = esc_pat.sub("", pr)
    return pr.rstrip(">#")

def connect_with_fallback(ip: str, prim_user: str, prim_pwd: str):
    chain = [(prim_user, prim_pwd, None)] + FALLBACK
    for user, pwd, secret in chain:
        try:
            conn = ConnectHandler(
                device_type="cisco_ios",
                host=ip,
                username=user,
                password=pwd,
                secret=(secret or pwd),
                fast_cli=False,  # More reliable across diverse devices
                global_delay_factor=1,  # Start with minimal delay
                timeout=20,  # Reduced from 30
                banner_timeout=20,  # Reduced from 60
                auth_timeout=20,  # Reduced from 30
            )
            # Use Netmiko's built-in prompt handling; avoid overriding base_pattern which can break on some devices
            try:
                conn.set_base_prompt()
            except Exception:
                raw_prompt = conn.find_prompt()
                conn.base_prompt = clean_prompt(raw_prompt)
            # Avoid command verification/prompt-pattern issues on quirky devices
            try:
                out = conn.send_command_timing("terminal length 0", cmd_verify=False)
                if "Invalid input" in out or "% " in out or "Unknown command" in out:
                    conn.send_command_timing("terminal pager 0", cmd_verify=False)
            except Exception:
                pass
            if secret:
                conn.enable()
            print(f"✔ Connected to {ip} as {user}")
            return conn, user, pwd
        except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
            print(f"✖ Auth/Timeout as {user}: {e}")
            continue
        except Exception as e:
            print(f"✖ Other SSH error as {user}: {e}")
            continue
    print(f"‼  All credential sets failed for {ip}")
    return None, None, None

def normalize_mac(raw: str) -> str:
    hex_only = re.sub(r'[^0-9A-Fa-f]', '', raw)
    if len(hex_only) != 12:
        raise ValueError(f"MAC '{raw}' is not 12 hex digits")
    hex_only = hex_only.lower()
    return f"{hex_only[:4]}.{hex_only[4:8]}.{hex_only[8:]}"

def mac_from_arp(conn, ip) -> Optional[str]:
    out = conn.send_command(f"show ip arp {ip}", read_timeout=180, cmd_verify=False)
    m = re.search(r"((?:[0-9a-f]{4}\.){2}[0-9a-f]{4})", out, re.I)
    return m.group(1).lower() if m else None

def flex_show_mac(conn, mac_dot) -> Tuple[Optional[str], Optional[str]]:
    for root in ("show mac address-table", "show mac-address-table"):
        out = conn.send_command(f"{root} | include {mac_dot}", read_timeout=180, cmd_verify=False)
        if "% Invalid" in out or "Unknown" in out:
            continue
        for line in out.splitlines():
            if mac_dot not in line.lower():
                continue
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == "*":
                parts.pop(0)
            if len(parts) < 3:
                continue
            return parts[0], parts[-1]
    return None, None

def is_trunk(conn, intf) -> bool:
    sw = conn.send_command(f"show interface {intf} switchport", read_timeout=180, cmd_verify=False)
    return "Mode: trunk" in sw or "Administrative Mode: trunk" in sw

def cdp_neighbor_ip(conn, intf) -> Optional[str]:
    out = conn.send_command(f"show cdp neighbors {intf} detail", read_timeout=180, cmd_verify=False)
    m = re.search(r"IP address: (\S+)", out)
    return m.group(1) if m else None

def get_po_members(conn, po, max_retries=3):
    """Get members for a port-channel with retries"""
    po_num = po.lstrip("Po").lstrip("po")
    print(f"Getting members for port-channel {po_num}...")
    
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"Retry attempt {attempt + 1}/{max_retries} to get port-channel members...")
            time.sleep(2)  # Wait 2 seconds between retries
            
        try:
            # Try both command formats
            commands = [
                f"show etherchannel {po_num} summary",
                f"show interface {po} etherchannel",
                "show etherchannel summary"
            ]
            
            members = []
            for cmd in commands:
                if members:  # If we already found members, don't try other commands
                    break
                    
                print(f"Trying command: {cmd}")
                out = conn.send_command(cmd, read_timeout=30, cmd_verify=False)
                
                if "Invalid input" in out:
                    print(f"Command not supported: {cmd}")
                    continue
                
                # Look for the line that starts with the port-channel number
                for line in out.splitlines():
                    # Skip header lines and empty lines
                    if not line.strip() or 'Protocol' in line or 'Flags:' in line or '----' in line:
                        continue
                    # Look for lines starting with our port-channel number
                    parts = line.strip().split()
                    po_num_str = str(po_num)
                    is_target_line = False
                    if parts:
                        if parts[0] == po_num_str or parts[0] == po:
                            is_target_line = True
                        else:
                            for tok in parts:
                                if re.match(rf'^Po{po_num_str}(?:\b|\()', tok, re.I):
                                    is_target_line = True
                                    break
                    if is_target_line:
                        # The ports are typically the last elements in the line
                        for part in parts:
                            # Remove state indicators like (P), (D), etc. BEFORE matching
                            clean_intf = re.sub(r"\(.*?\)", "", part)
                            # Match various interface formats and allow 2-3 segment numbering
                            if re.match(r'^(Twe|Ten|Te|Fo|Hu|Gi|Fa|Eth|Et)\d+(?:/\d+){1,3}$', clean_intf, re.I):
                                if clean_intf not in members:  # Avoid duplicates
                                    members.append(clean_intf)
            
            if members:
                print(f"Found members for {po}: {', '.join(members)}")
                return members
            
            print(f"No members found in command output. Debug output:")
            print("-" * 40)
            print(out)
            print("-" * 40)
            
        except Exception as e:
            print(f"Error getting port-channel members (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                print(f"Failed to get port-channel members after {max_retries} attempts")
                return []
            continue
    
    print(f"⚠ No members found for {po}")
    return []

def get_cdp_from_po(conn, po) -> Optional[str]:
    """Try to get CDP neighbor IP from any member of a port channel"""
    members = get_po_members(conn, po)
    if not members:
        print(f"⚠ No members found for {po}")
        return None
        
    for member in members:
        print(f"  Trying CDP on port channel member {member}...")
        nbr_ip = cdp_neighbor_ip(conn, member)
        if nbr_ip:
            return nbr_ip
    
    print(f"⚠ No CDP neighbors found on any member of {po}")
    return None

def first_member_of_po(conn, po) -> Optional[str]:
    po_num = po.lstrip("Po").lstrip("po")
    out = conn.send_command("show etherchannel summary", read_timeout=180, cmd_verify=False)
    for line in out.splitlines():
        if f"Po{po_num}" in line:
            for tok in line.split():
                if re.match(r"^[GT]i\d+/\d+(/\d+)?", tok, re.I):
                    return re.sub(r"\(.*?\)", "", tok)
    return None

def find_access_port(conn, this_ip, user, pwd, mac_dot) -> Tuple[Optional[str], Optional[str]]:
    vlan, intf = flex_show_mac(conn, mac_dot)
    if not intf:
        return None, None
    if not is_trunk(conn, intf):
        return this_ip, intf

    cdp_intf = intf
    if intf.lower().startswith("po"):
        nbr_ip = get_cdp_from_po(conn, intf)
        if not nbr_ip:
            return None, None
    else:
        nbr_ip = cdp_neighbor_ip(conn, cdp_intf)
        if not nbr_ip:
            return None, None

    nbr_conn, *_ = connect_with_fallback(nbr_ip, user, pwd)
    if not nbr_conn:
        return None, None
    final_ip, final_port = find_access_port(nbr_conn, nbr_ip, user, pwd, mac_dot)
    nbr_conn.disconnect()
    return final_ip, final_port

def test_switch_responsiveness(conn) -> float:
    """Test switch response time and return appropriate delay factor"""
    try:
        print("Testing switch responsiveness...")
        
        # First test basic command response with a simpler command
        start = time.time()
        conn.send_command("show clock", read_timeout=30, cmd_verify=False)
        basic_response_time = time.time() - start
        
        # Now test config mode entry time with explicit prompt handling
        print("Testing config mode entry time...")
        start = time.time()
        conn.send_command("configure terminal", expect_string=r"#", read_timeout=30)
        conn.send_command("end", expect_string=r"#", read_timeout=30)
        config_response_time = time.time() - start
        
        print(f"Basic command response time: {basic_response_time:.1f} seconds")
        print(f"Config mode entry time: {config_response_time:.1f} seconds")
        
        # Use the worse of the two times to determine delay factor
        response_time = max(basic_response_time, config_response_time)
        
        # Adjusted delay factors with lower minimums for fast switches
        if response_time > 60:  # More than 1 minute
            return 8  # Extremely slow switch
        elif response_time > 30:  # More than 30 seconds
            return 6  # Very very slow switch
        elif response_time > 10:
            return 4  # Very slow switch
        elif response_time > 5:
            return 2  # Slow switch
        elif response_time > 2:
            return 1.5  # Moderate speed
        else:
            return 1  # Fast switch
    except Exception as e:
        print(f"⚠ Could not test switch speed: {e}")
        print("Using moderate delay factor")
        return 2  # Use moderate delay if test fails

def push_config_with_retry(conn, commands, max_retries=3):
    """Push configuration with retries for slow/laggy switches"""
    # Test switch responsiveness and set delay factor
    delay_factor = test_switch_responsiveness(conn)
    print(f"Using delay factor {delay_factor}x for this switch")
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"Retry attempt {attempt + 1}/{max_retries}...")
                wait_time = 10 * attempt * delay_factor
                print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            
            print("Entering configuration mode...")
            conn.send_command(
                "configure terminal",
                expect_string=r"#",
                read_timeout=60 * delay_factor,
                cmd_verify=False,
                strip_prompt=True,
                strip_command=True
            )
            
            if not conn.check_config_mode():
                raise Exception("Failed to enter configuration mode")
            
            print("Applying configuration commands...")
            for cmd in commands:
                conn.send_command_timing(
                    cmd,
                    read_timeout=60 * delay_factor,
                    delay_factor=delay_factor,
                    strip_prompt=True,
                    strip_command=True
                )
                time.sleep(0.1)
            
            print("Exiting configuration mode...")
            conn.send_command(
                "end",
                expect_string=r"#",
                read_timeout=30,
                strip_prompt=True,
                strip_command=True
            )
            
            process_wait = max(2, 3 * delay_factor)
            print(f"⏳ Waiting {process_wait}s for switch to process changes...")
            time.sleep(process_wait)
            
            # Verify the config was applied
            print("Verifying configuration...")
            for cmd in commands:
                if cmd.startswith("interface "):
                    intf = cmd.split()[1]
                    
                    # Try different show commands to get interface config
                    verify_commands = [
                        f"show run interface {intf}",
                        f"show run int {intf}",
                        f"show interface {intf} switchport",
                    ]
                    
                    verify = None
                    for vcmd in verify_commands:
                        print(f"\nTrying verification command: {vcmd}")
                        output = conn.send_command(
                            vcmd,
                            read_timeout=60 * delay_factor,
                            cmd_verify=False,
                            strip_prompt=True,
                            strip_command=True
                        )
                        print("\nRaw command output:")
                        print("-" * 40)
                        print(output)
                        print("-" * 40)
                        
                        if output and not output.startswith("Invalid input"):
                            verify = output
                            break
                    
                    if not verify:
                        print("⚠ Could not get interface configuration output")
                        continue
                    
                    # For switchport command output, convert to running-config style
                    if "Administrative Mode:" in verify:
                        config_lines = []
                        for line in verify.splitlines():
                            line = line.strip()
                            if "Administrative Mode: access" in line:
                                config_lines.append("switchport mode access")
                            elif "Access Mode VLAN:" in line:
                                vlan = line.split()[-1]
                                if vlan != "1":  # Only add if not default VLAN
                                    config_lines.append(f"switchport access vlan {vlan}")
                            elif "Voice VLAN:" in line:
                                vlan = line.split()[-1]
                                if vlan != "none":
                                    config_lines.append(f"switchport voice vlan {vlan}")
                        verify = "\n".join(config_lines)
                    
                    # Clean up the verification output
                    verify_lines = []
                    for line in verify.splitlines():
                        line = line.strip()
                        if (line and 
                            not line.endswith('#') and 
                            not line.endswith('(config)#') and 
                            not line.endswith('(config-if)#') and
                            not 'Building configuration' in line and
                            not 'Current configuration' in line and
                            line != '!'):
                            verify_lines.append(line)
                    
                    verify = '\n'.join(verify_lines)
                    
                    # Define what we need to verify based on the commands
                    verification_checks = []
                    for config_cmd in commands[2:]:  # Skip default and interface commands
                        if "access vlan" in config_cmd:
                            vlan_num = config_cmd.split()[-1]
                            verification_checks.append(
                                (f"switchport access vlan {vlan_num}", f"access vlan {vlan_num}", f"Access Mode VLAN: {vlan_num}")
                            )
                        elif "voice vlan" in config_cmd:
                            vlan_num = config_cmd.split()[-1]
                            verification_checks.append(
                                (f"switchport voice vlan {vlan_num}", f"voice vlan {vlan_num}", f"Voice VLAN: {vlan_num}")
                            )
                        elif "mode access" in config_cmd:
                            verification_checks.append(
                                ("switchport mode access", "switchport access", "mode access", "Administrative Mode: access")
                            )
                        elif "portfast" in config_cmd:
                            verification_checks.append(
                                ("spanning-tree portfast", "portfast", "spanning-tree portfast edge")
                            )
                        elif "no shutdown" in config_cmd:
                            if "shutdown" not in verify:
                                continue
                            verification_checks.append(
                                ("no shutdown", "no shut")
                            )
                    
                    # Check each configuration element
                    failed_checks = []
                    for check_options in verification_checks:
                        found = False
                        for option in check_options:
                            if any(option.lower() in line.lower() for line in verify_lines):
                                found = True
                                break
                        if not found:
                            failed_checks.append(check_options[0])
                    
                    if failed_checks:
                        print("\nDebug Information:")
                        print("Expected configurations:")
                        for check_options in verification_checks:
                            print(f"  - Any of: {' OR '.join(check_options)}")
                        print("\nActual interface configuration:")
                        print(verify)
                        print("\nFailed checks:")
                        for failed in failed_checks:
                            print(f"  - {failed}")
                        
                        # If using show interface switchport and verification failed,
                        # consider it a success if we see the correct VLAN
                        if "Administrative Mode:" in verify:
                            for line in verify.splitlines():
                                if "Access Mode VLAN:" in line and str(access_vlan) in line:
                                    print("\n✓ Configuration verified through switchport command")
                                    break
                            else:
                                raise Exception("Config verification failed - see output above for details")
                        else:
                            raise Exception("Config verification failed - see output above for details")
                    
                    print("✓ Configuration verified successfully")
                    print("Saving configuration...")
                    
                    conn.send_command_timing(
                        "write memory",
                        read_timeout=300 * delay_factor,
                        delay_factor=delay_factor,
                        strip_prompt=True,
                        strip_command=True
                    )
                    print("✔ Configuration saved successfully")
                    
                    # Show final interface configuration
                    print("\nFinal interface configuration:")
                    print("-" * 40)
                    final_config = conn.send_command(
                        f"show run interface {intf}",
                        read_timeout=60 * delay_factor,
                        cmd_verify=False,
                        strip_prompt=True,
                        strip_command=True
                    )
                    if not final_config or "Invalid input" in final_config:
                        final_config = conn.send_command(
                            f"show interface {intf} switchport",
                            read_timeout=60 * delay_factor,
                            cmd_verify=False,
                            strip_prompt=True,
                            strip_command=True
                        )
                    
                    # Clean up the final config output
                    final_lines = []
                    for line in final_config.splitlines():
                        line = line.strip()
                        if (line and 
                            not line.endswith('#') and 
                            not line.endswith('(config)#') and 
                            not line.endswith('(config-if)#') and
                            not 'Building configuration' in line and
                            not 'Current configuration' in line and
                            line != '!'):
                            final_lines.append(line)
                    print('\n'.join(final_lines))
                    print("-" * 40)
                    
                    return True
            
        except Exception as e:
            print(f"⚠ Configuration attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to apply configuration after {max_retries} attempts")
            continue

def main():
    # Check credentials at startup
    check_credentials()
    
    site, cores = choose_site()
    print(f"\nSite: {site}  cores: {', '.join(cores)}")

    mode = ""
    while mode not in ("ip", "mac"):
        mode = input("\nLookup by IP or MAC? (ip/mac): ").strip().lower()

    if mode == "ip":
        ip_input = input("Device IP: ").strip()
    else:
        try:
            mac_dot = normalize_mac(input("Device MAC: ").strip())
        except ValueError as e:
            sys.exit(e)

    core_conn = None
    for ip_core in cores:
        print(f"\n★ Connecting to core {ip_core}")
        core_conn, good_user, good_pwd = connect_with_fallback(ip_core, PRIMARY_USERNAME, PRIMARY_PASSWORD)
        if not core_conn:
            continue

        if mode == "ip":
            mac_dot = mac_from_arp(core_conn, ip_input)
            if not mac_dot:
                print(f"MAC not in ARP on {ip_core}")
                core_conn.disconnect(); core_conn=None
                continue
            print(f"↳ ARP: {ip_input} → {mac_dot}")

        final_ip, final_port = find_access_port(core_conn, ip_core, good_user, good_pwd, mac_dot)
        if final_ip:
            break
        print(f"MAC not on {ip_core}")
        core_conn.disconnect(); core_conn = None

    if not core_conn or not final_ip:
        sys.exit("‼  Could not locate device on any core.")

    final_conn = core_conn if final_ip == core_conn.host else connect_with_fallback(final_ip, PRIMARY_USERNAME, PRIMARY_PASSWORD)[0]
    if not final_conn:
        return

    print(f"\n✓ Device found on {final_ip}  port {final_port}")
    print(final_conn.send_command(f"show run interface {final_port}", read_timeout=180, cmd_verify=False))

    access_vlan = input("\nAccess VLAN (blank cancels): ").strip()
    if not access_vlan.isdigit():
        print("Cancelled."); final_conn.disconnect(); core_conn.disconnect(); return

    voice_vlan = input("Voice VLAN (Enter to skip): ").strip()
    if voice_vlan and not voice_vlan.isdigit():
        print("Cancelled."); final_conn.disconnect(); core_conn.disconnect(); return

    summary = f"{final_port} → access {access_vlan}"
    if voice_vlan:
        summary += f", voice {voice_vlan}"
    if input(f"CONFIRM {summary}? (y/N): ").strip().lower() != "y":
        print("Cancelled."); final_conn.disconnect(); core_conn.disconnect(); return

    cmds = [
        f"default interface {final_port}",
        f"interface {final_port}",
        "switchport mode access",
        f"switchport access vlan {access_vlan}",
    ]
    if voice_vlan:
        cmds.append(f"switchport voice vlan {voice_vlan}")
    cmds += ["spanning-tree portfast", "no shutdown"]

    print("\nPushing config …")
    try:
        print(push_config_with_retry(final_conn, cmds))
        print("✔ Done.")
    except Exception as e:
        print(f"❌ Failed to apply configuration: {e}")
        print("Please verify the configuration manually.")

    final_conn.disconnect()
    if final_conn is not core_conn:
        core_conn.disconnect()

if __name__ == "__main__":
    main()
