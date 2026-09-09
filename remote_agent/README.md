# 🔋 Remote UPS Monitoring Agent

Αυτός ο φάκελος περιέχει τον αυτόνομο client/agent για την παρακολούθηση UPS συνδεδεμένου μέσω USB σε απομακρυσμένο υπολογιστή και την αποστολή των μετρήσεων στον κεντρικό **UPS Status Web Server** (μέσω WireGuard / LAN / Internet).

---

## 🚀 Οδηγίες Εγκατάστασης & Εκτέλεσης στο Remote PC

### Βήμα 1: Αντιγραφή Φακέλου
Αντιγράψτε ολόκληρο τον φάκελο `remote_agent` στο απομακρυσμένο PC (π.χ. στην Επιφάνεια Εργασίας `Desktop\remote_agent`).

### Βήμα 2: Εγκατάσταση (μία φορά)
- **Windows**: Τρέξτε το **`install-windows.bat`** (διπλό κλικ).
- **Linux / Raspberry Pi**: Τρέξτε `chmod +x install-linux.sh && ./install-linux.sh`.

### Βήμα 3: Ρύθμιση IP (WireGuard / LAN)
Ανοίξτε το αρχείο **`agent_config.json`** με ένα κειμενογράφο και ρυθμίστε την IP του κεντρικού Server:

```json
{
  "server_url": "http://<IP_TOU_SERVER>:8088/api/remote/push",
  "api_key": "ups_remote_secret_key_123",
  "ups_name": "Remote-1",
  "location": "Remote Site",
  "poll_interval_seconds": 2.0,
  "driver_type": "auto"
}
```

> 💡 **Σημείωση**: Αντικαταστήστε το `<YOUR_SERVER_IP>` με την IP του μηχανήματος που τρέχει το κεντρικό WebUI (π.χ. `http://<YOUR_SERVER_IP>:8088/api/remote/push`).

### Βήμα 4: Εκκίνηση Agent
- **Windows**: Τρέξτε το **`run_agent.bat`**.
- **Linux**: Τρέξτε `./run_agent.sh` (ή ενεργοποιείται αυτόματα ως systemd service αν επιλέχθηκε στο install).

Θα δείτε άμεσα στο τερματικό:
```text
[21:20:00] 🟢 Push OK -> Mode: Line | In: 234.0V | Out: 234.0V | Load: 9.0% | Batt: 26.7V (100.0%)
```
Και τα δεδομένα θα εμφανίζονται ζωντανά στο WebUI!

---

## 🌐 Σύνδεση Πολλαπλών Remote UPS (Multi-Remote Auto-Discovery)

Το σύστημα υποστηρίζει **απεριόριστα Remote UPS ταυτόχρονα** με αυτόματη αναγνώριση (Auto-Discovery):

1. **Πρώτο Remote PC**:
   Στο `agent_config.json`, ορίστε `"ups_name": "Remote-1"`.
2. **Δεύτερο Remote PC**:
   Στο `agent_config.json`, ορίστε `"ups_name": "Remote-2"`.
3. **Τρίτο Remote PC κ.ο.κ.**:
   Στο `agent_config.json`, ορίστε `"ups_name": "Remote-3"`.

Μόλις ο server λάβει μετρήσεις από ένα νέο Remote UPS:
- Εμφανίζει αυτόματα νέα κάρτα στο Dashboard.
- Προσθέτει δυναμικά το αντίστοιχο κουμπί στα γραφήματα ιστορικού.
- Καταχωρεί αυτόματα το προφίλ στις Ρυθμίσεις (Settings -> Profiles), όπου μπορείτε να προσαρμόσετε το όνομα εμφάνισης, την τοποθεσία, τα rated watts, ή να το ενεργοποιήσετε/απενεργοποιήσετε.
- Οι εντολές Self-Test και σίγασης Buzzer αποστέλλονται απομονωμένα αποκλειστικά στο συγκεκριμένο UPS!

---

## 🔄 Χειροκίνητη Ενημέρωση Agent (Manual Update)

Ο φάκελος περιλαμβάνει αυτόνομο μηχανισμό ενημέρωσης (`update.py`):

1. **Εκτέλεση Ενημέρωσης**:
   - **Windows**: Κάντε διπλό κλικ στο **`update.bat`** (ή `python update.py`).
   - **Linux**: Εκτελέστε **`./update.sh`** (ή `python3 update.py`).

2. **Ασφάλεια Ρυθμίσεων (`agent_config.json`)**:
   - Το εργαλείο **δεν διαγράφει ούτε μηδενίζει** τις ρυθμίσεις σας.
   - Συγχωνεύει αυτόματα τυχόν νέες παραμέτρους της νέας έκδοσης διατηρώντας τις υπάρχουσες τιμές σας (IP, API Key, Όνομα UPS κ.λπ.).
   - Δημιουργεί αυτόματο αντίγραφο ασφαλείας (`agent_config.json.bak`).
   - Σε περίπτωση σημαντικής ασυμβατότητας (conflict) στη δομή των ρυθμίσεων, εμφανίζει ευκρινή προειδοποίηση ώστε να ελέγξετε και να επιβεβαιώσετε τις παραμέτρους.

