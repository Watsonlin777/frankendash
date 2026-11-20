# Frankendash Data Sources Inventory
## Task 3 Completion: Verified read-only data sources

### Phones Panel Data Sources

#### 1. SSH Tunnels (Reverse SSH access)
- **Phone A (PHB110)**: Port 2222 on 127.0.0.1 ✅ **VERIFIED LISTENING**
- **Phone B (PJZ110)**: Port 2223 on 127.0.0.1 ❌ **NOT LISTENING** (port not found)
- **Protocol**: SSH tunnel for remote access
- **Access**: Read-only tunnel status check

#### 2. ADB Debug Bridges
- **Phone A ADB**: Port 18091 on 127.0.0.1 ✅ **VERIFIED LISTENING**
- **Phone B ADB**: Port 18092 on 127.0.0.1 ❌ **NOT LISTENING** (port not found)
- **Command**: `adb -H 127.0.0.1 -P 18091 devices` (timeout observed)
- **Location**: `/usr/bin/adb` available

#### 3. Termux Status Server
- **Port**: 18123 on 127.0.0.1 ❌ **NOT LISTENING** (port not found)
- **Expected endpoint**: `127.0.0.1:18123/status`
- **Purpose**: Termux service status (trigger/collector/collect/sync)

#### 4. Location Data Files
- **Raw location data**: `/root/life/raw/` ✅ **DIRECTORY EXISTS**
  - Contains JSONL files: `raw_2026-10-24.jsonl`, `raw_2026-10-25.jsonl`, etc.
- **Location watch state**: `/root/life/location_watch_state.json` ✅ **FILE EXISTS**
- **Phone configs**: `/root/life/phones/` ✅ **DIRECTORY EXISTS**
  - Contains: `A/` subdirectory, `A.conf` config file
- **ADB state/logs**: `/root/life/adb_state.json`, various `.log` files ✅ **FILES EXIST**

### Gateway Panel Data Sources

#### 1. Magpie Gateway API
- **Endpoint**: `http://127.0.0.1:3425/v1/models` ✅ **VERIFIED ACCESSIBLE**
- **Port**: 3425 ✅ **VERIFIED LISTENING** (magpie service running)
- **Response**: JSON model list with provider health/routing info
- **Service PID**: 1432040 (magpie)

#### 2. Magpie Usage Data
- **Command**: `magpie usage --csv today` ✅ **VERIFIED WORKING**
- **Location**: `/root/.local/bin/magpie`
- **Output**: CSV format with timestamped usage records
- **Alternative**: Usage logs (exact path TBD - check magpie config)

### Notifications Panel Data Sources

#### 1. WeCom Notification Scripts
- **Water reminder**: `/root/.hermes/scripts/water_reminder.py` ✅ **FILE EXISTS**
- **Water state**: `/root/.hermes/water_state.json` ✅ **FILE EXISTS**
- **WeCom platform code**: `/root/.hermes/installs/*/workspace/plugins/platforms/wecom/` ✅ **DIRECTORY EXISTS**
- **Watchdog scripts**: Various watchdog scripts in hermes directories ✅ **FILES EXIST**

#### 2. Notification Logs
- **Hermes logs directory**: `/root/.hermes/logs/` ✅ **DIRECTORY EXISTS**
  - `agent.log` - Primary agent log (current: 1.5MB)
  - `errors.log` - Error log (current: 448KB)
  - `gateway-exit-diag.log` - Gateway diagnostics
  - Historical logs: `.log.1`, `.log.2`, etc.
- **System logs**: Journal/system logs (no WeCom-specific entries found in today's journal)

### Privacy Considerations
All data sources verified as **READ-ONLY**. No write operations needed or performed.
No coordinates, IPs, phone numbers, webhook URLs, keys, or tokens will be exposed in:
- UI display
- API responses  
- Application logs
- Repository files

### Source Failure Handling
When any source cannot be reached:
- Show "unknown" status
- Include last-good timestamp if available
- **NEVER** guess values or show 0
- Timeout: 5 seconds per source (as per design)

### Data Freshness Requirements
- Phone location data > 2 hours old → flag as "stale" with timestamp
- Server-side cache: 60 seconds
- Frontend auto-refresh: 60 seconds

