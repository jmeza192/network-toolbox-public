import os
import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from dotenv import load_dotenv
from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException, ReadTimeout

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('check_cdp_aps.log')
	]
)

# Load environment variables from .env file next to this script
ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(ENV_PATH, override=True)

# Credentials: set these in .env
# SWITCH_USERNAME=your_username
# SWITCH_PASSWORD=your_password
# SWITCH_ENABLE_PASSWORD=optional_enable
USERNAME = os.getenv('SWITCH_USERNAME')
PASSWORD = os.getenv('SWITCH_PASSWORD')
ENABLE_PASSWORD = os.getenv('SWITCH_ENABLE_PASSWORD', '')

# Backup credentials (any of these variants are accepted)
BACKUP_USERNAME = (
	os.getenv('SWITCH_USERNAME_2')
	or os.getenv('SWITCH_BACKUP_USERNAME')
	or os.getenv('FALLBACK_USERNAME')
)
BACKUP_PASSWORD = (
	os.getenv('SWITCH_PASSWORD_2')
	or os.getenv('SWITCH_BACKUP_PASSWORD')
	or os.getenv('FALLBACK_PASSWORD')
)
BACKUP_ENABLE_PASSWORD = (
	os.getenv('SWITCH_ENABLE_PASSWORD_2')
	or os.getenv('SWITCH_BACKUP_ENABLE_PASSWORD')
	or os.getenv('FALLBACK_ENABLE_PASSWORD', '')
)

# Sites list loaded from environment variables - requires .env file
SITES: Dict[str, Tuple[str, List[str]]] = {
	"1": (os.getenv('LOCATION_1_NAME'), [os.getenv('LOCATION_1_IP')]),
	"2": (os.getenv('LOCATION_2_NAME'), [os.getenv('LOCATION_2_IP')]),
	"3": (os.getenv('LOCATION_3_NAME'), [os.getenv('LOCATION_3_IP')]),
	"4": (os.getenv('LOCATION_4_NAME'), [os.getenv('LOCATION_4_IP')]),
	"5": (os.getenv('LOCATION_5_NAME'), [os.getenv('LOCATION_5_IP')]),
	"6": (os.getenv('LOCATION_6_NAME'), [os.getenv('LOCATION_6_IP')]),
	"7": (os.getenv('LOCATION_7_NAME'), [os.getenv('LOCATION_7_IP')]),
	"8": (os.getenv('LOCATION_8_NAME'), [os.getenv('LOCATION_8_IP')]),
	"9": (os.getenv('LOCATION_9_NAME'), [os.getenv('LOCATION_9_IP')]),
	"10": (os.getenv('LOCATION_10_NAME'), [os.getenv('LOCATION_10_IP')]),
	"11": (os.getenv('LOCATION_11_NAME'), [os.getenv('LOCATION_11_IP')]),
	"12": (os.getenv('LOCATION_12_NAME'), [os.getenv('LOCATION_12_IP')]),
	"13": (os.getenv('LOCATION_13_NAME'), [os.getenv('LOCATION_13_IP')]),
	"14": (os.getenv('LOCATION_14_NAME'), [os.getenv('LOCATION_14_IP')]),
	"15": (os.getenv('LOCATION_15_NAME'), [os.getenv('LOCATION_15_IP')]),
	"16": (os.getenv('LOCATION_16_NAME'), [os.getenv('LOCATION_16_IP')]),
}

AP_PLATFORM_PATTERN = re.compile(
	# Common Cisco AP identifiers in CDP Platform field (handles AIR-CAPxxxx, AIR APxxxx, Catalyst 91xx)
	r"(AIR[-–—\s]?(?:CAP|AP)\d+|Cisco\s*AP|Catalyst\s?9\d{2}|C91\d{2})",
	re.IGNORECASE,
)


def connect_to_switch(ip: str, username: str, password: str, enable_password: str = ""):
	device = {
		'device_type': 'cisco_ios',
		'host': ip,
		'username': username,
		'password': password,
		'fast_cli': False,
		'global_delay_factor': 2,
		'timeout': 45,
		'banner_timeout': 45,
		'auth_timeout': 45,
	}
	if enable_password:
		device['secret'] = enable_password
	try:
		logging.info(f"Connecting to {ip}...")
		conn = ConnectHandler(**device)
		# Stabilize prompt and disable paging
		conn.find_prompt()
		if enable_password:
			conn.enable()
		# Use timing variant and flush channel to avoid partial echoes lingering
		conn.send_command_timing("terminal length 0", cmd_verify=False)
		try:
			conn.clear_buffer()
		except Exception:
			pass
		return conn
	except (NetMikoAuthenticationException, NetMikoTimeoutException) as e:
		logging.error(f"Failed to connect to {ip}: {e}")
		return None
	except Exception as e:
		logging.error(f"Unexpected error connecting to {ip}: {e}")
		return None


def get_credential_chain() -> List[Tuple[str, str, str, str]]:
	"""Return a list of credential tuples: (label, username, password, enable)."""
	chain: List[Tuple[str, str, str, str]] = []
	if USERNAME and PASSWORD:
		chain.append(("primary", USERNAME, PASSWORD, ENABLE_PASSWORD or ""))
	if BACKUP_USERNAME and BACKUP_PASSWORD:
		chain.append(("backup", BACKUP_USERNAME, BACKUP_PASSWORD, BACKUP_ENABLE_PASSWORD or ""))
	return chain


def connect_with_fallback(ip: str) -> Tuple[Optional[object], Optional[str], Optional[str]]:
	"""Try primary creds then backup. Returns (connection, label, username)."""
	chain = get_credential_chain()
	if not chain:
		logging.error("No credentials available from environment variables")
		return None, None, None
	for idx, (label, user, pwd, secret) in enumerate(chain, start=1):
		logging.info(f"Attempt {idx}/{len(chain)}: connecting to {ip} using {label} credentials ({user})")
		conn = connect_to_switch(ip, user, pwd, secret)
		if conn:
			logging.info(f"Connected to {ip} using {label} credentials ({user})")
			return conn, label, user
		logging.warning(f"Connection failed to {ip} using {label} credentials ({user}); trying next if available...")
	return None, None, None


def parse_cdp_detail_for_aps(cdp_output: str) -> List[Dict[str, str]]:
	"""
	Parse 'show cdp neighbors detail' output and return only Cisco AP neighbors.
	Each neighbor dict contains: device_id, ip, platform, local_interface, port_id
	This implementation is line-based and tolerant of indentation/wrapping.
	"""
	neighbors: List[Dict[str, str]] = []
	if not isinstance(cdp_output, str):
		return neighbors

	current = {
		"device_id": "",
		"ip": "",
		"platform": "",
		"local_interface": "",
		"port_id": "",
	}
	block_lines: List[str] = []

	def flush_block() -> None:
		nonlocal current, block_lines
		if not block_lines:
			return
		block_text = "\n".join(block_lines)
		# Backfill any missing fields from the accumulated block
		if not current["device_id"]:
			val = _capture_first_group(r"Device ID:\s*(.+)", block_text)
			current["device_id"] = val or ""
		if not current["ip"]:
			val = _capture_first_group(r"IP address:\s*([0-9.]+)", block_text)
			current["ip"] = val or ""
		if not current["platform"]:
			val = _capture_first_group(r"Platform:\s*([^,\n]+)", block_text)
			current["platform"] = val or ""
		if not current["local_interface"]:
			val = _capture_first_group(r"Interface:\s*([^,\n]+)", block_text)
			current["local_interface"] = val or ""
		if not current["port_id"]:
			val = _capture_first_group(r"Port ID\s*\(outgoing port\):\s*(.+)", block_text)
			current["port_id"] = val or ""

		# Determine if this block is an AP
		ap_like = False
		if current["platform"] and AP_PLATFORM_PATTERN.search(current["platform"]):
			ap_like = True
		elif AP_PLATFORM_PATTERN.search(block_text):
			ap_like = True

		if ap_like:
			neighbors.append({
				"device_id": current["device_id"],
				"ip": current["ip"],
				"platform": current["platform"] or (_capture_first_group(AP_PLATFORM_PATTERN.pattern, block_text) or ""),
				"local_interface": current["local_interface"],
				"port_id": current["port_id"],
			})

		# Reset for next block
		current = {
			"device_id": "",
			"ip": "",
			"platform": "",
			"local_interface": "",
			"port_id": "",
		}
		block_lines = []

	for line in cdp_output.splitlines():
		strip = line.strip()
		if strip.startswith("Device ID:"):
			# New neighbor begins; flush previous
			flush_block()
			block_lines.append(line)
			val = _capture_first_group(r"Device ID:\s*(.+)", line)
			current["device_id"] = val or ""
			continue
		# Accumulate lines for this block
		if strip:
			block_lines.append(line)
		# Update fields opportunistically
		if "IP address:" in line and not current["ip"]:
			val = _capture_first_group(r"IP address:\s*([0-9.]+)", line)
			if val:
				current["ip"] = val
		if "Platform:" in line and not current["platform"]:
			val = _capture_first_group(r"Platform:\s*([^,\n]+)", line)
			if val:
				current["platform"] = val
		if "Interface:" in line:
			val = _capture_first_group(r"Interface:\s*([^,\n]+)", line)
			if val:
				current["local_interface"] = val
			val2 = _capture_first_group(r"Port ID\s*\(outgoing port\):\s*(.+)", line)
			if val2:
				current["port_id"] = val2
		# Separator line often marks end of block
		if strip.startswith("-------------------------"):
			flush_block()

	# Flush the last block
	flush_block()

	return neighbors

# Fallback parser for 'show cdp neighbors' (brief/table) output
# Handles two-line entries where Device ID is on one line and details on the next
# Example detail line tokens include: <Local Intf> <Holdtime> <Capability...> <Platform> <Port ID>

def parse_cdp_brief_for_aps(cdp_output: str) -> List[Dict[str, str]]:
	if not isinstance(cdp_output, str):
		return []

	neighbors: List[Dict[str, str]] = []
	current_device: Optional[str] = None

	for raw_line in cdp_output.splitlines():
		line = raw_line.rstrip()
		if not line.strip():
			continue
		low = line.lower().strip()
		if low.startswith("capability codes") or low.startswith("device id") or "port id" in low and "platform" in low:
			# header lines
			continue
		if low.startswith("total cdp entries"):
			break
		# If line does not start with an interface keyword, assume it's a Device ID line
		if not re.match(r"^(\s*(Gig\S*|Gi\S*|Fa\S*|Ten\S*|Te\S*|Twe\S*|Eth\S*|Ethernet\S*|Gig\s|Fa\s|Ten\s|Twe\s))", line):
			current_device = line.strip()
			continue

		# This is a details line; extract fields
		tokens = line.split()
		if len(tokens) < 5:
			continue

		# Local interface can be one or two tokens depending on abbreviation
		if tokens[0] in {"Gig", "Gi", "Fa", "Ten", "Te", "Twe"}:
			if len(tokens) < 3:
				continue
			local_intf = f"{tokens[0]} {tokens[1]}"
			idx = 2
		else:
			local_intf = tokens[0]
			idx = 1

		# Skip holdtime token if it is a number
		if idx < len(tokens) and re.fullmatch(r"\d+", tokens[idx]):
			idx += 1

		# Detect platform across the remainder of the line to tolerate wraps/variable columns
		rest_of_line = " ".join(tokens[idx:])
		platform_match = AP_PLATFORM_PATTERN.search(rest_of_line)
		if not platform_match:
			continue
		platform = platform_match.group(0)
		# Port ID = everything after the platform match
		port_id = rest_of_line[platform_match.end():].strip()

		neighbors.append({
			"device_id": current_device or "",
			"ip": "",
			"platform": platform,
			"local_interface": local_intf,
			"port_id": port_id,
		})

	return neighbors


def run_cmd_robust(conn, command: str, expect: str = r"[>#]", timeout_primary: int = 120, timeout_fallback: int = 180) -> str:
	"""Run a command with multiple strategies to increase reliability."""
	output = ""
	try:
		output = conn.send_command(command, expect_string=expect, read_timeout=timeout_primary, cmd_verify=False)
		if isinstance(output, str) and output.strip():
			return output
	except Exception:
		pass
	# Fallback 1: without expect_string
	try:
		output = conn.send_command(command, read_timeout=timeout_fallback, cmd_verify=False)
		if isinstance(output, str) and output.strip():
			return output
	except Exception:
		pass
	# Fallback 2: timing variant
	try:
		output = conn.send_command_timing(command, delay_factor=2)
		return output if isinstance(output, str) else str(output)
	except Exception:
		return ""


def looks_like_cdp_detail(text: str) -> bool:
	return bool(text and ("Device ID:" in text or "Entry address(es):" in text or "Total cdp entries" in text))


def looks_like_cdp_brief(text: str) -> bool:
	# Many platforms print similar headers; any presence of Device ID or Total line is good enough
	return bool(text and ("Device ID" in text and "Port ID" in text) or "Total cdp entries" in text)


def _capture_first_group(pattern: str, text: str) -> Optional[str]:
	m = re.search(pattern, text, re.IGNORECASE)
	return m.group(1).strip() if m else None


def process_switch(ip: str) -> List[Dict[str, str]]:
	conn, label, user = connect_with_fallback(ip)
	if not conn:
		return []
	try:
		# Get CDP detail robustly
		output = run_cmd_robust(conn, "show cdp neighbors detail")
		# If output doesn't look like CDP, try resetting terminal length again and retry
		if not looks_like_cdp_detail(output):
			conn.send_command_timing("terminal length 0", cmd_verify=False)
			try:
				conn.clear_buffer()
			except Exception:
				pass
			output = run_cmd_robust(conn, "show cdp neighbors detail")

		# DEBUG dump if requested IPs (from environment variables)
		debug_ips = [os.getenv('SPECIAL_IP_1'), os.getenv('SPECIAL_IP_2'), os.getenv('SPECIAL_IP_3')]
		debug_ips = [ip_addr for ip_addr in debug_ips if ip_addr]  # Remove None values
		if ip in debug_ips:
			with open(f"debug_cdp_detail_{ip.replace('.', '_')}.txt", "w") as f:
				f.write(f"=== CDP DETAIL OUTPUT FOR {ip} ===\n")
				f.write(output or "")

		neighbors = parse_cdp_detail_for_aps(output)

		if not neighbors:
			brief = run_cmd_robust(conn, "show cdp neighbors")
			if ip in debug_ips:
				with open(f"debug_cdp_brief_{ip.replace('.', '_')}.txt", "w") as f:
					f.write(f"=== CDP BRIEF OUTPUT FOR {ip} ===\n")
					f.write(brief or "")
			neighbors = parse_cdp_brief_for_aps(brief)

		return dedupe_neighbors(neighbors)
	finally:
		try:
			conn.disconnect()
		except Exception:
			pass


def dedupe_neighbors(neigh_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
	seen = set()
	result: List[Dict[str, str]] = []
	for n in neigh_list:
		key = (
			n.get("device_id", ""),
			n.get("ip", ""),
			n.get("platform", "").lower(),
			n.get("local_interface", "").lower(),
			n.get("port_id", "").lower(),
		)
		if key in seen:
			continue
		seen.add(key)
		result.append(n)
	return result


def main():
	if not ((USERNAME and PASSWORD) or (BACKUP_USERNAME and BACKUP_PASSWORD)):
		print("Missing credentials in .env. Provide SWITCH_USERNAME/SWITCH_PASSWORD or SWITCH_USERNAME_2/SWITCH_PASSWORD_2.")
		return

	summary: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
	results_summary = []
	for key in sorted(SITES, key=lambda k: int(k)):
		site_name, ip_list = SITES[key]
		print(f"\nSite: {site_name}")
		for ip in ip_list:
			aps = process_switch(ip)
			if not aps:
				print(f" {ip}: no APs found")
				results_summary.append((site_name, ip, 0))
				continue
			print(f" {ip}: {len(aps)} AP(s)")
			for ap in aps:
				print(f"  - {ap['device_id'] or 'N/A'} ({ap['ip'] or 'N/A'}) [{ap['platform'] or 'N/A'}] @ {ap['local_interface'] or 'N/A'} -> {ap['port_id'] or 'N/A'}")
			results_summary.append((site_name, ip, len(aps)))

	# Final concise summary
	print("\nSummary:")
	for site_name, ip, count in results_summary:
		print(f" {site_name} | {ip}: {count} AP(s)")

	print("\nDone.")


if __name__ == '__main__':
	main()
