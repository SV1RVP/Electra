# ⚡ Electra - UPS Status Central Monitor 🔋📊

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%20v3.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.3.5-emerald.svg)](version.json)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Raspberry%20Pi-purple.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)

**Electra** is an advanced, multi-UPS real-time monitoring and alerting system designed for home labs, server rooms, and critical infrastructure. It combines local high-speed USB HID drivers with remote telemetry agents over LAN/WireGuard VPN, rendering a sleek **Cyberpunk/Glassmorphic WebUI Dashboard**, interactive **Chart.js** historical telemetry, and intelligent **Viber Channel Bot** notifications.

**Creator:** Alexandros - Ermis Tsourapas (SV1RVP)  
**License:** GNU Affero General Public License v3.0 (AGPL-3.0)

---

# 🇬🇧 English Documentation

## 🌟 Key Features

### 🔌 Universal Multi-UPS, Auto-Discovery & Persistent Port Locking
- **Autonomous Multi-Protocol Auto-Discovery**: Automatically probes and detects which protocol each connected UPS communicates with on initial startup without requiring manual driver selection.
- **Persistent Hardware Port Locking**: Automatically locks and saves the unique physical USB hardware path (`device_id`) and protocol driver (`driver_type`) into `profiles.json`. Each slot (`Local-1`, `Local-2`) remains permanently associated with its physical port across system reboots, preventing port swapping or slot collisions.
- **WebUI One-Click Re-Scan (🔍 Re-Scan USB Ports)**: Available inside the WebUI Settings modal to easily re-scan all physical USB/Serial ports and update hardware mappings whenever cables or UPS units are swapped.
- **Physical Collision Prevention (Multi-Port Deduplication)**: Tracks unique physical USB endpoints (`hidraw` / Windows HID paths, PyUSB bus-address pairs, and Serial ports). When multiple USB devices (even **identical UPS models**) are plugged in, each is assigned to a distinct monitoring slot without duplication or crosstalk.
- **Pluggable Protocol Support**:
  1. **Cypress / Megatec Q1 (`0665:5161`)**: TEC, Voltronic Power, OEM Megatec, FSP, Masterguard, Kstar.
  2. **MEC0003 / Richcomm Generic HID (`0001:0000`)**: Turbo-X, Tescom Leo LCD, Mustek, PowerWalker, Centralion.
  3. **USB HID Power Device Class (PDC)**: **APC by Schneider Electric** (`051D`), **CyberPower** (`0764`), **Eaton** (`0463`), **Tripp Lite** (`09AE`).
  4. **Serial-over-USB Megatec Q1**: Virtual COM / `ttyUSB` / FTDI / CH340 / CP2102 serial bridges.
  5. **Remote-1 (Remote Site via IP)**: Standalone remote telemetry agent posting live metrics over secure REST API (`/api/remote/push`) across local networks or WireGuard VPN tunnels.
- **Dynamic Names & Locations**: Full customization of display names, locations, rated watts, and battery capacities directly from the WebUI Settings modal or `profiles.json`.

### 🖥️ Modern WebUI Dashboard
- **Cyberpunk / Glassmorphic UI**: High-contrast, glowing neon aesthetic with dark mode and optional light theme.
- **Animated Power Flow Diagram**: Real-time animated visualization of power routing (Mains $\rightarrow$ Inverter $\rightarrow$ Battery $\rightarrow$ Loads) for each active UPS.
- **Live Circular Gauges**: Responsive SVG gauges for Load % and Battery SoC %.
- **Active Protocol & Locked Port Badges**: Displays active protocol name (e.g. `Cypress Q1`, `MEC0003`, `APC PDC`, `Serial`) directly on each UPS card and in Settings.
- **Server-Sent Events (SSE)**: Sub-second live data streaming without aggressive HTTP polling.
- **Full Bilingual Localization (🇬🇷 EL / 🇬🇧 EN)**: Complete support for Greek and English across the entire WebUI (all labels, tooltips, charts, cards, and modal settings) as well as all Viber notifications.
- **Web Audio Alarms**: Synthesized audible alerts for power outages, grid restores, and severe overload conditions.

### 📊 Database, Historical Telemetry & Smart Recording
- **Permanent SQLite Storage (`telemetry.db`)**: High-performance SQLite engine with Write-Ahead Logging (WAL) and non-blocking asynchronous writing.
- **Configurable Logging Interval (`db_log_interval_seconds`)**: Customize how frequently telemetry is written to disk (default: `60 sec`, range: `2s` to `300s`).
- **Configurable History Retention (`db_retention_days`)**: Set automated database housekeeping to retain records for `7`, `14`, `30` (default), `60`, `90`, `180`, `365` days, or `0` (Infinite / Unlimited history).
- **Smart Event-Based Recording (`db_log_on_change`)**: Immediately records a new database entry whenever noticeable changes occur in voltage ($\ge 2\text{V}$), load ($\ge 3\%$), battery ($\ge 1\%$), or operating mode (Line $\leftrightarrow$ Battery) without waiting for the time interval to expire.
- **High-Resolution Outage Recording (`db_outage_fast_log`)**: Automatically boosts logging resolution to **1-second (`1s`) intervals** during ongoing power outages (Battery mode), capturing high-precision discharge curves and voltage drops throughout the blackout.
- **Interactive Chart.js Visualizations**: Filter and compare live and historical metrics across 5 different timeframes (**5m Live**, **1h**, **6h**, **24h**, **7d**) with single-click CSV and JSON data export.

### 🔋 Intelligent Battery & Runtime Engine
- **Accurate Runtime Estimation**: Combines non-linear SLA battery discharge curves with Peukert's law correction ($I^k \cdot t = C$).
- **Adaptive Battery Health Learning**: Tracks discharge curves during real outages to calculate battery degradation and health state over time.
- **Critical Low Battery Indicator**: Configurable threshold (e.g. $\le 20\%$) with a pulsing warning badge (`🪫 Critical low battery`) in the WebUI and critical Viber alerts.

### 📱 Smart Viber Alerting System
- **Bilingual Alerts**: Automatically formats and broadcasts messages in Greek 🇬🇷 or English 🇬🇧 according to the active system language.
- **Power Outage Detection**: Instant alert with input voltage drop, current load (Watts), battery %, and estimated autonomy.
- **Periodic Repeating Outage Updates**: Recurring live telemetry updates sent every $X$ seconds (configurable, e.g. 30s/60s) during ongoing power outages showing elapsed outage time.
- **Power Restored Notice**: Notifies when grid power returns, including total outage duration calculation (e.g. `2m 20s`).
- **Overload Warnings**: Triggered when load exceeds user-defined threshold (default: 70%).
- **Self-Healing Webhook Handler**: Automatically recovers from webhook desynchronization (Viber error code 10) and retries message delivery seamlessly.
- **Automated Daily Status Report**: Scheduled daily summary broadcast at a user-defined time (e.g. 09:00).

### 🔄 One-Click Auto-Update & Maintenance
- **WebUI Version Checker**: Header widget displays the current version (`v1.1.0`) with a single-click update checker.
- **One-Click Update ("⚡ Update Now")**: Pulls new code from Git or downloads the universal update ZIP, extracts files safely (preserving configurations and telemetry databases), and automatically restarts the background service.

---

## 🛠️ Supported Hardware & Protocols

| UPS Family / Protocol | Physical Interface | VID : PID / Port | Communication Protocol |
| :--- | :--- | :--- | :--- |
| **Cypress Q1 / OEM Megatec** | USB HID | `0665:5161` | Cypress QS / Q1 Protocol |
| **MEC0003 Generic HID** | USB HID / PyUSB | `0001:0000` | MEC0003 String Descriptors |
| **APC by Schneider Electric (Smart-UPS / Back-UPS)** | USB HID | `051D:0002` | USB HID Power Device Class (PDC) |
| **CyberPower Systems (PDC Series)** | USB HID | `0764:0501`, `0764:0601` | USB HID Power Device Class (PDC) |
| **Eaton / Powerware** | USB HID | `0463:ffff` | USB HID Power Device Class (PDC) |
| **Tripp Lite** | USB HID | `09AE:0001` | USB HID Power Device Class (PDC) |
| **Serial-over-USB (FTDI / CH340 / CP2102 / Prolific)** | Virtual COM / ttyUSB | `COM1..32` / `/dev/ttyUSB*` | Megatec Q1 ASCII Protocol |
| **Any Remote UPS / PC (Remote Agent)** | HTTP / WireGuard | Remote REST Port `8088` | JSON Push API (`/api/remote/push`) |

---

## 🚀 Installation Guide

### 🐧 Linux & Raspberry Pi OS Installation

1. **Clone the repository**:
   ```bash
   git clone https://gitlab.com/SV1RVP/ups-status.git
   cd ups-status
   ```
2. **Run the universal installer**:
   ```bash
   chmod +x install-linux.sh
   ./install-linux.sh
   ```
   *The installer automatically installs system packages (`python3-venv`, `libusb`, `libhidapi`), configures USB udev permissions, sets up Python `.venv`, and creates and starts the `systemd` service (`ups-status.service`).*

3. **Access the WebUI**:
   - Open your browser at `http://localhost:8088` (or `http://<YOUR_IP>:8088`).

---

### 🪟 Windows Installation

1. **Download or Clone the repository**:
   ```cmd
   git clone https://gitlab.com/SV1RVP/ups-status.git
   cd "ups-status"
   ```
2. **Run the installer**:
   - Double-click `install-windows.bat` (or run `install.bat`).
   - The installer verifies Python 3.10+, creates `.venv`, installs dependencies from `requirements.txt`, creates default config files, and offers to enable Autostart on Windows boot.
3. **Start the server**:
   - Double-click `start_server.bat`.
   - Access the dashboard at `http://localhost:8088`.

> [!NOTE]
> **Windows 11 Notice (Smart App Control):**  
> When running `install-windows.bat` or `start_server.bat`, Windows 11 may show a standard informational prompt: *"Smart App Control has blocked part of this app"*.  
> **This does not affect program operation in any way** — it is a standard Windows informational prompt because local scripts and open-source Python binaries (`hidapi`, `libusb`) do not carry commercial paid certificates. The Web server and background monitoring continue to run 100% normally in the background.  
> *(To prevent the prompt from showing, right-click the `.bat` file $\rightarrow$ **Properties** $\rightarrow$ Check **"Unblock"** $\rightarrow$ Apply).*

---

## 🌐 Remote UPS Agent Deployment

To monitor a UPS connected to another machine (e.g. a remote PC or server across a WireGuard VPN tunnel):

1. Copy the `remote_agent/` directory to the target machine.
2. Edit `remote_agent/agent_config.json`:
   ```json
   {
     "server_url": "http://10.10.1.10:8088/api/remote/push",
     "api_key": "ups_remote_secret_key_123",
     "ups_name": "Remote-1",
     "location": "Remote Site",
     "driver": "auto",
     "interval_seconds": 2.0
   }
   ```
3. Run the agent:
   - **Windows**: Run `run_agent.bat` (or `python ups_agent.py`).
   - **Linux**: Run `./run_agent.sh`.
4. The central server will automatically receive and plot live metrics from the remote UPS!

---

## ⚙️ Configuration & Customization

The system stores configurations in:
- `config.json`: System language (`"language": "el"` / `"en"`), Web server settings, Viber token & receiver ID, alert toggles, outage repeat intervals, database retention, and thresholds.
- `profiles.json`: Display names, locations, rated watts, battery parameters, and locked physical USB hardware paths (`device_id` & `driver_type`) for each UPS slot.

### Example `config.json`:
```json
{
  "language": "el",
  "server": {
    "host": "0.0.0.0",
    "port": 8088,
    "poll_interval_seconds": 2.0
  },
  "viber": {
    "enabled": true,
    "channel_token": "YOUR_VIBER_AUTH_TOKEN_HERE",
    "sender_name": "UPS Monitor",
    "receiver_id": ""
  },
  "alerts": {
    "power_outage_alert": true,
    "power_restore_alert": true,
    "outage_repeat_alert": true,
    "overload_alert": true,
    "disconnect_alert": true,
    "battery_low_alert": true,
    "daily_report": true
  },
  "outage_repeat_interval_seconds": 60,
  "battery_low_threshold_pct": 20,
  "overload_threshold_pct": 70,
  "daily_report_time": "09:00",
  "db_log_interval_seconds": 60,
  "db_retention_days": 30,
  "db_log_on_change": true,
  "db_outage_fast_log": true,
  "remote_api_key": "ups_remote_secret_key_123"
}
```

---

## 🗑️ Uninstallation

### On Linux:
```bash
chmod +x uninstall-linux.sh
./uninstall-linux.sh
```
*Stops and disables the `ups-status.service`, removes systemd service files, and cleans up udev rules.*

### On Windows:
- Double-click `uninstall-windows.bat`.
*Stops running background Python processes and removes the startup shortcut.*

---
---

# 🇬🇷 Ελληνική Τεκμηρίωση

## 🌟 Βασικά Χαρακτηριστικά

### 🔌 Universal Υποστήριξη Multi-UPS, Αυτόματη Ανίχνευση & Μόνιμο Κλείδωμα Θυρών
- **Αυτόνομη Πολυπρωτοκολλική Ανίχνευση (Auto-Discovery)**: Ανιχνεύει αυτόματα το πρωτόκολλο επικοινωνίας κάθε συνδεδεμένου UPS στην πρώτη εκκίνηση, χωρίς να απαιτείται χειροκίνητη επιλογή driver.
- **Μόνιμο Κλείδωμα Θυρών Hardware (Persistent Port Locking)**: Αποθηκεύει αυτόματα το μοναδικό φυσικό hardware path (`device_id`) και τον driver (`driver_type`) στο `profiles.json`. Κάθε θέση (`Local-1`, `Local-2`) παραμένει μόνιμα αντιστοιχισμένη στη συγκεκριμένη φυσική θύρα ακόμη και μετά από επανεκκινήσεις του υπολογιστή, αποτρέποντας το μπέρδεμα των θέσεων.
- **Επανασάρωση με 1 Κλικ (🔍 Επανασάρωση Θυρών USB)**: Άμεσα προσβάσιμο κουμπί μέσα από τις Ρυθμίσεις του WebUI για εύκολο επαναπροσδιορισμό των θυρών σε περίπτωση αλλαγής καλωδίων ή αντικατάστασης UPS.
- **Αποτροπή Συγκρούσεων (Multi-Port Deduplication)**: Παρακολουθεί μοναδικά φυσικά endpoints USB (`hidraw` / Windows HID paths, PyUSB bus-address pairs και Serial ports). Ακόμα και αν συνδεθούν **πανομοιότυπα μοντέλα UPS**, το καθένα αναγνωρίζεται σε ξεχωριστό Slot χωρίς διπλοεγγραφές ή παρεμβολές.
- **Πλούσια Υποστήριξη Πρωτοκόλλων**:
  1. **Cypress / Megatec Q1 (`0665:5161`)**: TEC, Voltronic Power, OEM Megatec, FSP, Masterguard, Kstar.
  2. **MEC0003 / Richcomm Generic HID (`0001:0000`)**: Turbo-X, Tescom Leo LCD, Mustek, PowerWalker, Centralion.
  3. **USB HID Power Device Class (PDC)**: **APC by Schneider Electric** (`051D`), **CyberPower** (`0764`), **Eaton** (`0463`), **Tripp Lite** (`09AE`).
  4. **Serial-over-USB Megatec Q1**: Εικονικές θύρες COM / `ttyUSB` / FTDI / CH340 / CP2102 serial bridges.
  5. **Remote-1 (Απομακρυσμένη Τοποθεσία μέσω IP)**: Αυτόνομος agent τηλεμετρίας που στέλνει ζωντανά δεδομένα μέσω ασφαλούς REST API (`/api/remote/push`) σε τοπικό δίκτυο ή WireGuard VPN tunnel.
- **Δυναμικά Ονόματα & Τοποθεσίες**: Πλήρης παραμετροποίηση ονομάτων εμφάνισης, τοποθεσιών, ονομαστικής ισχύος (Watts) και χωρητικότητας μπαταρίας από το WebUI ή το `profiles.json`.

### 🖥️ Σύγχρονο WebUI Dashboard
- **Cyberpunk / Glassmorphic Σχεδιασμός**: Υψηλής αντίθεσης neon αισθητική με Dark Mode και εναλλακτικό Light Theme.
- **Κινούμενο Διάγραμμα Ροής Ισχύος (Power Flow Animation)**: Ζωντανή οπτικοποίηση της ροής ρεύματος (Δίκτυο ΔΕΗ $\rightarrow$ Inverter $\rightarrow$ Μπαταρία $\rightarrow$ Φορτία) για κάθε ενεργό UPS.
- **Ζωντανά Κυκλικά Όργανα (SVG Gauges)**: Διαδραστικές ενδείξεις για Φορτίο % και Στάθμη Μπαταρίας %.
- **Ετικέτες Ενεργού Πρωτοκόλλου & Κλειδωμένης Θύρας**: Εμφάνιση του πρωτοκόλλου (π.χ. `Cypress Q1`, `MEC0003`, `APC PDC`, `Serial`) απευθείας σε κάθε κάρτα UPS.
- **Τεχνολογία Server-Sent Events (SSE)**: Ζωντανή ροή δεδομένων υποδευτερολέπτου χωρίς επιβαρυντικό HTTP polling.
- **Πλήρης Διγλωσσική Υποστήριξη (🇬🇷 Ελληνικά / 🇬🇧 English)**: 100% υποστήριξη Ελληνικών και Αγγλικών σε όλο το WebUI (όλες οι ετικέτες, tooltips, γραφήματα, κάρτες, ρυθμίσεις) και στα μηνύματα Viber.
- **Ηχητικοί Συναγερμοί (Web Audio Alarms)**: Συνθετικοί ηχητικοί τόνοι για διακοπή ρεύματος, επαναφορά δικτύου και υπερφόρτωση.

### 📊 Βάση Δεδομένων, Ιστορικό Τηλεμετρίας & Έξυπνη Καταγραφή
- **Μόνιμη Αποθήκευση SQLite (`telemetry.db`)**: Υψηλής απόδοσης SQLite μηχανή με Write-Ahead Logging (WAL) και ασύγχρονη μη-μπλοκαριστική εγγραφή.
- **Ρυθμιζόμενη Συχνότητα Καταγραφής (`db_log_interval_seconds`)**: Ορισμός συχνότητας αποθήκευσης μετρήσεων στο δίσκο (προεπιλογή: `60 sec`, εύρος: `2s` έως `300s`).
- **Ρυθμιζόμενη Διατήρηση Ιστορικού (`db_retention_days`)**: Αυτόματη εκκαθάριση παλαιών εγγραφών για `7`, `14`, `30` (προεπιλογή), `60`, `90`, `180`, `365` ημέρες ή `0` (Άπειρο / Χωρίς Διαγραφή).
- **Έξυπνη Καταγραφή σε Αλλαγές Μετρήσεων (`db_log_on_change`)**: Άμεση καταγραφή νέας εγγραφής στη βάση όποτε υπάρξει αισθητή μεταβολή στην τάση ($\ge 2\text{V}$), στο φορτίο ($\ge 3\%$), στη μπαταρία ($\ge 1\%$) ή στην κατάσταση (Line $\leftrightarrow$ Battery) χωρίς αναμονή του χρονοδιακόπτη.
- **Υψηλή Ανάλυση σε Διακοπή Ρεύματος (`db_outage_fast_log`)**: Αυτόματη αύξηση της ανάλυσης καταγραφής σε **1 δευτερόλεπτο (`1s`)** κατά τη διάρκεια διακοπής ρεύματος (Battery Mode), εξασφαλίζοντας μέγιστη ακρίβεια στην καμπύλη εκφόρτισης και την πτώση τάσης.
- **Διαδραστικά Γραφήματα Chart.js**: Φιλτράρισμα και σύγκριση ζωντανών και ιστορικών μετρήσεων σε 5 χρονικά διαστήματα (**5m Live**, **1h**, **6h**, **24h**, **7d**) με εξαγωγή σε CSV και JSON.

### 🔋 Έξυπνος Αλγόριθμος Μπαταρίας & Αυτονομίας
- **Ακριβής Εκτίμηση Χρόνου Αυτονομίας**: Συνδυασμός μη-γραμμικών καμπυλών εκφόρτισης μπαταριών SLA με διόρθωση νόμου Peukert ($I^k \cdot t = C$).
- **Προσαρμοστική Εκμάθηση Υγείας Μπαταρίας**: Παρακολούθηση πραγματικών εκφορτίσεων για τον υπολογισμό της φθοράς και της κατάστασης υγείας των συσσωρευτών στο χρόνο.
- **Ένδειξη Κρίσιμης Χαμηλής Ισχύος**: Ρυθμιζόμενο όριο (π.χ. $\le 20\%$) με παλλόμενη προειδοποίηση (`🪫 Κρίσιμη χαμηλή ισχύς`) στο WebUI και άμεσες ειδοποιήσεις Viber.

### 📱 Έξυπνο Σύστημα Ειδοποιήσεων Viber
- **Δίγλωσσα Μηνύματα**: Αυτόματη μορφοποίηση και αποστολή μηνυμάτων στα Ελληνικά 🇬🇷 ή Αγγλικά 🇬🇧 βάσει της επιλεγμένης γλώσσας.
- **Ειδοποίηση Διακοπής Ρεύματος (⚡🚨)**: Άμεσο μήνυμα με την πτώση τάσης, το τρέχον φορτίο (Watts), τη στάθμη μπαταρίας % και την εκτιμώμενη αυτονομία.
- **Επαναλαμβανόμενες Ενημερώσεις Διακοπής**: Περιοδική αποστολή ζωντανής κατάστασης κάθε $X$ δευτερόλεπτα (π.χ. 30s/60s) κατά τη διάρκεια της διακοπής με ένδειξη διάρκειας.
- **Ειδοποίηση Επαναφοράς Ρεύματος (⚡🟢)**: Ενημέρωση κατά την επιστροφή της τάσης δικτύου με υπολογισμό της συνολικής διάρκειας διακοπής (π.χ. `2λ 20δ`).
- **Προειδοποιήσεις Υπερφόρτωσης (🔥)**: Αποστολή ειδοποίησης όταν το φορτίο υπερβεί το καθορισμένο όριο (προεπιλογή: 70%).
- **Αυτόματη Επιδιόρθωση Webhook**: Αυτόματη ανάκτηση και επαναπροσπάθεια σε περίπτωση αποσυγχρονισμού webhook (Viber error 10).
- **Προγραμματισμένη Ημερήσια Αναφορά**: Αυτόματη αποστολή σύνοψης κατάστασης σε προκαθορισμένη ώρα (π.χ. 09:00).

### 🔄 Αυτόματη Ενημέρωση με 1 Κλικ
- **Έλεγχος Έκδοσης στο WebUI**: Εμφάνιση της τρέχουσας έκδοσης (`v1.1.0`) στην κεφαλίδα με κουμπί ελέγχου νεότερης έκδοσης.
- **Ενημέρωση με 1 Κλικ («⚡ Ενημέρωση Τώρα»)**: Λήψη του νέου κώδικα από το Git ή ZIP, ασφαλής εφαρμογή των αρχείων (διατηρώντας τις ρυθμίσεις και τη βάση δεδομένων) και αυτόματη επανεκκίνηση της υπηρεσίας.

---

## 🛠️ Υποστηριζόμενο Υλικό & Πρωτόκολλα

| Οικογένεια UPS / Πρωτόκολλο | Φυσική Διασύνδεση | VID : PID / Θύρα | Πρωτόκολλο Επικοινωνίας |
| :--- | :--- | :--- | :--- |
| **Cypress Q1 / OEM Megatec** | USB HID | `0665:5161` | Cypress QS / Q1 Protocol |
| **MEC0003 Generic HID** | USB HID / PyUSB | `0001:0000` | MEC0003 String Descriptors |
| **APC by Schneider Electric (Smart-UPS / Back-UPS)** | USB HID | `051D:0002` | USB HID Power Device Class (PDC) |
| **CyberPower Systems (PDC Series)** | USB HID | `0764:0501`, `0764:0601` | USB HID Power Device Class (PDC) |
| **Eaton / Powerware** | USB HID | `0463:ffff` | USB HID Power Device Class (PDC) |
| **Tripp Lite** | USB HID | `09AE:0001` | USB HID Power Device Class (PDC) |
| **Serial-over-USB (FTDI / CH340 / CP2102 / Prolific)** | Virtual COM / ttyUSB | `COM1..32` / `/dev/ttyUSB*` | Megatec Q1 ASCII Protocol |
| **Οποιοδήποτε Απομακρυσμένο UPS / PC (Remote Agent)** | HTTP / WireGuard | Remote REST Port `8088` | JSON Push API (`/api/remote/push`) |

---

## 🚀 Οδηγός Εγκατάστασης

### 🐧 Εγκατάσταση σε Linux & Raspberry Pi OS

1. **Κλωνοποίηση του αποθετηρίου**:
   ```bash
   git clone https://gitlab.com/SV1RVP/ups-status.git
   cd ups-status
   ```
2. **Εκτέλεση του αυτόματου εγκαταστάτη**:
   ```bash
   chmod +x install-linux.sh
   ./install-linux.sh
   ```
   *Το script εγκαθιστά αυτόματα τα απαραίτητα πακέτα (`python3-venv`, `libusb`, `libhidapi`), ρυθμίζει τα δικαιώματα udev για USB, δημιουργεί το `.venv` και εκκινεί την υπηρεσία systemd (`ups-status.service`).*

3. **Πρόσβαση στο WebUI**:
   - Ανοίξτε τον browser στη διεύθυνση `http://localhost:8088` (ή `http://<IP_ΣΑΣ>:8088`).

---

### 🪟 Εγκατάσταση σε Windows

1. **Λήψη ή Κλωνοποίηση του αποθετηρίου**:
   ```cmd
   git clone https://gitlab.com/SV1RVP/ups-status.git
   cd "ups-status"
   ```
2. **Εκτέλεση του installer**:
   - Κάντε διπλό κλικ στο `install-windows.bat` (ή `install.bat`).
   - Ο εγκαταστάτης ελέγχει την Python 3.10+, δημιουργεί το `.venv`, εγκαθιστά τα requirements, δημιουργεί τα default αρχεία ρυθμίσεων και προσφέρει αυτόματη εκκίνηση με τα Windows.
3. **Εκκίνηση του Server**:
   - Κάντε διπλό κλικ στο `start_server.bat`.
   - Ανοίξτε το dashboard στο `http://localhost:8088`.

> [!NOTE]
> **Σημείωση για Windows 11 (Smart App Control / Έλεγχος Έξυπνων Εφαρμογών):**  
> Κατά την εκτέλεση του `install-windows.bat` ή `start_server.bat`, υπάρχει μεγάλη πιθανότητα τα Windows 11 να εμφανίσουν ενημερωτικό παράθυρο *"Smart App Control has blocked part of this app"*.  
> **Αυτό δεν επηρεάζει καθόλου τη λειτουργία του προγράμματος** — είναι καθαρά τυπικό ενημερωτικό μήνυμα επειδή τα τοπικά scripts και οι open-source Python βιβλιοθήκες (`hidapi`, `libusb`) δεν διαθέτουν πληρωμένη εμπορική ψηφιακή υπογραφή. Ο Web server και το monitoring συνεχίζουν να εκτελούνται 100% κανονικά στο παρασκήνιο.  
> *(Αν θέλετε να μην εμφανίζεται, μπορείτε να κάνετε Δεξί κλικ στο `.bat` $\rightarrow$ **Ιδιότητες** $\rightarrow$ Τσεκάρισμα **«Κατάργηση αποκλεισμού» (Unblock)** $\rightarrow$ Εφαρμογή).*

---

## 🌐 Εγκατάσταση Απομακρυσμένου Agent (Remote UPS Agent)

Για την παρακολούθηση UPS συνδεδεμένου σε άλλο μηχάνημα (π.χ. απομακρυσμένο PC/Server μέσω WireGuard VPN):

1. Αντιγράψτε τον φάκελο `remote_agent/` στο απομακρυσμένο μηχάνημα.
2. Επεξεργαστείτε το `remote_agent/agent_config.json`:
   ```json
   {
     "server_url": "http://10.10.1.10:8088/api/remote/push",
     "api_key": "ups_remote_secret_key_123",
     "ups_name": "Remote-1",
     "location": "Remote Site",
     "driver": "auto",
     "interval_seconds": 2.0
   }
   ```
3. Εκτελέστε τον agent:
   - **Windows**: Εκτελέστε το `run_agent.bat` (ή `python ups_agent.py`).
   - **Linux**: Εκτελέστε το `./run_agent.sh`.
4. Ο κεντρικός server θα αρχίσει να λαμβάνει και να καταγράφει αυτόματα ζωντανή τηλεμετρία!

---

## ⚙️ Ρυθμίσεις & Παραμετροποίηση

Οι ρυθμίσεις του συστήματος αποθηκεύονται στα:
- `config.json`: Γλώσσα συστήματος (`"language": "el"` / `"en"`), ρυθμίσεις Web server, κλειδιά Viber, επιλογές ειδοποιήσεων, διαστήματα καταγραφής βάσης και όρια συναγερμών.
- `profiles.json`: Ονόματα εμφάνισης, τοποθεσίες, ονομαστική ισχύς (Watts), παράμετροι μπαταρίας και κλειδωμένα hardware paths (`device_id` & `driver_type`) για κάθε slot.

### Παράδειγμα `config.json`:
```json
{
  "language": "el",
  "server": {
    "host": "0.0.0.0",
    "port": 8088,
    "poll_interval_seconds": 2.0
  },
  "viber": {
    "enabled": true,
    "channel_token": "YOUR_VIBER_AUTH_TOKEN_HERE",
    "sender_name": "UPS Monitor",
    "receiver_id": ""
  },
  "alerts": {
    "power_outage_alert": true,
    "power_restore_alert": true,
    "outage_repeat_alert": true,
    "overload_alert": true,
    "disconnect_alert": true,
    "battery_low_alert": true,
    "daily_report": true
  },
  "outage_repeat_interval_seconds": 60,
  "battery_low_threshold_pct": 20,
  "overload_threshold_pct": 70,
  "daily_report_time": "09:00",
  "db_log_interval_seconds": 60,
  "db_retention_days": 30,
  "db_log_on_change": true,
  "db_outage_fast_log": true,
  "remote_api_key": "ups_remote_secret_key_123"
}
```

---

## 🗑️ Απεγκατάσταση

### Σε Linux:
```bash
chmod +x uninstall-linux.sh
./uninstall-linux.sh
```
*Τερματίζει και απενεργοποιεί την υπηρεσία `ups-status.service`, αφαιρεί τα αρχεία systemd και καθαρίζει τους κανόνες udev.*

### Σε Windows:
- Κάντε διπλό κλικ στο `uninstall-windows.bat`.
*Τερματίζει τις παρασκηνιακές διεργασίες Python και αφαιρεί τη συντόμευση αυτόματης εκκίνησης.*

---

## 📜 License / Άδεια Χρήσης

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.  
See the [LICENSE](LICENSE) file for complete license terms.

---

## 👤 Author & Credits / Δημιουργός

**Alexandros - Ermis Tsourapas (SV1RVP)**  
Amateur Radio Operator & Developer  
Athens, Greece 🇬🇷
