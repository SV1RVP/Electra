/**
 * UPS STATUS WEBUI - MAIN CONTROLLER & REAL-TIME STATE
 * Full Bilingual Localization (Greek 🇬🇷 / English 🇬🇧)
 * Persistent Port Locking, Manual Re-Scan, Database Retention & Smart Logging Controls
 */

// Bilingual Translation Dictionary
const I18N = {
  el: {
    app_title: "UPS STATUS MONITOR",
    app_subtitle: "Κεντρικός Έλεγχος & Τηλεμετρία",
    live_status: "LIVE STREAM",
    update_checking: "Έλεγχος...",
    btn_check_update: "Έλεγχος",
    btn_update_now: "⚡ Ενημέρωση Τώρα",
    btn_charts: "Γραφήματα",
    btn_events: "Ιστορικό",
    btn_settings: "Ρυθμίσεις",
    btn_test_viber: "Αποστολή Δοκιμαστικού Viber",
    btn_daily_report_now: "Αποστολή Ημερήσιας Αναφοράς Τώρα",
    btn_rescan_usb: "Επανασάρωση Θυρών USB",
    lbl_port_bound: "Κλειδωμένη Θύρα",
    lbl_port_unbound: "Auto-Scan / Μη συνδεδεμένο",
    btn_save: "💾 Αποθήκευση",
    btn_close: "Κλείσιμο",
    btn_export_csv: "Εξαγωγή CSV",
    btn_export_json: "Εξαγωγή JSON",

    total_power: "ΣΥΝΟΛΙΚΗ ΙΣΧΥΣ",
    avg_load: "ΜΕΣΟ ΦΟΡΤΙΟ",
    grid_status: "ΚΑΤΑΣΤΑΣΗ ΔΙΚΤΥΟΥ",
    active_units: "ΕΝΕΡΓΑ UPS",
    sub_real_consumption: "Πραγματική κατανάλωση",
    sub_alarm_limit: "Όριο συναγερμού: 70%",
    sub_active_desc: "2 Τοπικά + 1 Απομακρυσμένο",

    status_normal: "ΟΜΑΛΗ (ΔΕΗ OK)",
    status_battery: "ΔΙΑΚΟΠΗ (ΜΠΑΤΑΡΙΑ)",
    status_overload: "ΥΠΕΡΦΟΡΤΩΣΗ",
    status_offline: "ΑΠΟΣΥΝΔΕΔΕΜΕΝΟ",

    load_label: "ΦΟΡΤΙΟ",
    battery_label: "ΜΠΑΤΑΡΙΑ",
    runtime_est: "Εκτιμώμενη Αυτονομία",
    critical_low_power: "Κρίσιμη χαμηλή ισχύς",
    battery_health: "Υγεία Μπαταρίας",

    grid_in: "Είσοδος",
    ups_out: "Έξοδος",
    frequency: "Συχνότητα",
    batt_volts: "Τάση Μπατ.",
    beeper: "Beeper",
    status_mode: "Κατάσταση",

    pf_grid: "Δίκτυο ΔΕΗ",
    pf_inverter: "Inverter",
    pf_battery: "Μπαταρία",
    pf_loads: "Φορτία",

    tab_voltages: "Τάσεις (V)",
    tab_load: "Φορτίο & Watts",
    tab_battery: "Μπαταρία (% / V)",
    tab_freq: "Συχνότητα (Hz)",
    chart_all_ups: "Όλα τα UPS (Σύγκριση)",

    period_5m: "5m Live",
    period_1h: "1 Ώρα",
    period_6h: "6 Ώρες",
    period_24h: "24 Ώρες",
    period_7d: "7 Ημέρες",

    events_title: "Καταγραφή Συμβάντων & Ειδοποιήσεων",
    col_time: "Ώρα",
    col_ups: "UPS",
    col_type: "Τύπος",
    col_severity: "Σοβαρότητα",
    col_message: "Μήνυμα",

    settings_title: "Ρυθμίσεις Συστήματος & Ειδοποιήσεων",
    sec_viber: "📱 Ρυθμίσεις Viber Channel & Alerts",
    lbl_viber_token: "Viber Channel / Bot Auth Token:",
    lbl_viber_sender: "Όνομα Αποστολέα (Sender Name):",
    lbl_viber_receiver: "Receiver ID (Προαιρετικό - για Direct User Bot μηνύματα):",

    sec_triggers: "⚡ Όρια & Αυτόματες Ειδοποιήσεις",
    lbl_daily_time: "Ώρα Ημερήσιας Αναφοράς (HH:MM):",
    lbl_overload_thresh: "Όριο Συναγερμού Υπερφόρτωσης:",
    lbl_battery_low_thresh: "Όριο Κρίσιμα Χαμηλής Ισχύος Μπαταρίας:",
    desc_battery_low: "Εμφάνιση της ένδειξης «Κρίσιμη χαμηλή ισχύς» στο WebUI και στο Viber όταν η στάθμη μπαταρίας πέσει σε αυτό το επίπεδο.",
    lbl_outage_repeat: "Διάστημα Επαναλαμβανόμενης Ενημέρωσης σε Διακοπή (Viber):",
    desc_outage_repeat: "Αποστολή ζωντανής κατάστασης (Μπαταρία %, Αυτονομία, Φορτίο, Διάρκεια) στο Viber κάθε Χ δευτερόλεπτα κατά τη διάρκεια της διακοπής.",

    chk_outage: "🚨 Ειδοποίηση Άμεσης Διακοπής Ρεύματος (Power Outage)",
    chk_outage_repeat: "⏳ Επαναλαμβανόμενη ενημέρωση κατά τη διάρκεια διακοπής (κάθε X sec)",
    chk_restore: "🟢 Ειδοποίηση Επαναφοράς Ρεύματος με διάρκεια διακοπής",
    chk_overload: "🔥 Ειδοποίηση Υπερφόρτωσης Φορτίου (> 70%)",
    chk_disconnect: "🔌 Ειδοποίηση Απώλειας / Επαναφοράς Επικοινωνίας με UPS",
    chk_low_batt: "🪫 Ειδοποίηση «Κρίσιμη χαμηλή ισχύς» Μπαταρίας",
    chk_daily: "📊 Ημερήσια Αναφορά Κατάστασης στην καθορισμένη ώρα",

    sec_database: "📊 Ρυθμίσεις Βάσης Δεδομένων & Ιστορικού",
    desc_database: "Ρυθμίστε τη συχνότητα καταγραφής μετρήσεων στο δίσκο και τη διάρκεια διατήρησης ιστορικού τηλεμετρίας.",
    lbl_db_interval: "Συχνότητα Καταγραφής (Log Interval):",
    desc_db_interval: "Πόσο συχνά γράφονται οι μετρήσεις στη βάση δεδομένων (προεπιλογή: 60 δευτερόλεπτα).",
    lbl_db_retention: "Διατήρηση Ιστορικού (Ημέρες):",
    desc_db_retention: "Επιλέξτε πόσο παλιές εγγραφές θα διατηρούνται στη βάση δεδομένων SQLite. Επιλέξτε «Άπειρο» για απεριόριστη διατήρηση.",
    chk_db_log_on_change: "⚡ Αυτόματη καταγραφή σε σημαντική μεταβολή τάσης/φορτίου (αντί για χρονική καθυστέρηση)",
    chk_db_outage_fast_log: "🚨 Υψηλή ανάλυση καταγραφής (ανά 1 sec) κατά τη διάρκεια διακοπής ρεύματος (Μπαταρία)",

    sec_profiles: "⚡ Προφίλ, Ονόματα & Τοποθεσίες UPS",
    desc_profiles: "Ορίστε τα ονόματα εμφάνισης και τις τοποθεσίες των 3 UPS. Οι θύρες USB κλειδώνονται μόνιμα ώστε κάθε UPS να αντιστοιχεί σταθερά στο ίδιο Slot.",
    tag_ups1: "UPS 1 (Local USB 1)",
    tag_ups2: "UPS 2 (Local USB 2)",
    tag_ups3: "UPS 3 (Remote Network / IP)",
    lbl_enabled: "Ενεργό",
    lbl_display_name: "Όνομα Εμφάνισης (Display Name):",
    lbl_location: "Τοποθεσία (Location):",
    lbl_rated_w: "Ονομαστική Ισχύς (Watts):",

    sec_remote_agent: "🌐 Απομακρυσμένο UPS (Remote Agent over IP)",
    lbl_api_key: "Secret API Key για Push Τηλεμετρίας:",
    desc_api_key: "Χρησιμοποιείται στο ups_agent.py για ασφαλή μετάδοση δεδομένων στο /api/remote/push.",

    btn_buzzer_on: "🔔 Buzzer ON",
    btn_buzzer_off: "🔕 Buzzer Muted",
    btn_selftest: "🧪 Self-Test (10s)",
    btn_selftest_running: "⏳ Δοκιμή σε εξέλιξη...",
    lbl_last_selftest: "Τελευταίο Self-Test",
    selftest_passed: "✅ Επιτυχές",
    selftest_failed: "❌ Αποτυχία",
    selftest_running: "⏳ Σε εξέλιξη",
    selftest_none: "Δεν έχει εκτελεστεί",

    sec_self_test: "🧪 Αυτόματο Self-Test & Χρονοδιάγραμμα",
    btn_run_all_selftest: "Self-Test σε όλα τα UPS",
    desc_self_test_schedule: "Ρυθμίστε τον αυτόματο περιοδικό έλεγχο μπαταρίας των UPS με χρονοδιακόπτη (Timer) και αυτόματη αποστολή feedback αποτελέσματος στο Viber.",
    chk_enable_selftest_schedule: "Ενεργοποίηση Προγραμματισμένου Self-Test (Timer)",
    lbl_selftest_freq: "Συχνότητα Ελέγχου:",
    opt_freq_daily: "Καθημερινά",
    opt_freq_weekly: "Εβδομαδιαία",
    opt_freq_monthly: "Μηνιαία",
    lbl_selftest_time: "Ώρα Δοκιμής (HH:MM):",
    lbl_selftest_day_week: "Ημέρα Εβδομάδας:",
    lbl_selftest_day_month: "Ημέρα Μήνα (1-31):",
    opt_day_sunday: "Κυριακή",
    opt_day_monday: "Δευτέρα",
    opt_day_tuesday: "Τρίτη",
    opt_day_wednesday: "Τετάρτη",
    opt_day_thursday: "Πέμπτη",
    opt_day_friday: "Παρασκευή",
    opt_day_saturday: "Σάββατο",
    chk_selftest_viber: "📱 Αποστολή αναλυτικού αποτελέσματος Self-Test στο Viber Channel",
    chk_selftest_alert: "🧪 Ειδοποίηση Αποτελέσματος Self-Test (Επιτυχία / Αποτυχία)",

    unit_h: "ω",
    unit_m: "λ",
    unit_min: "λεπτά",
    runtime_over_10h: "> 10 ώρες",

    toast_outage: "⚠️ Διακοπή ρεύματος στο {name}! Λειτουργία με μπαταρία.",
    toast_restored: "🟢 Επαναφορά ρεύματος στο {name}!",
    toast_overload: "🔥 Υπερφόρτωση στο {name}!",
    toast_saved: "Οι ρυθμίσεις αποθηκεύτηκαν επιτυχώς!",
    toast_save_err: "Σφάλμα αποθήκευσης ρυθμίσεων",
    toast_test_ok: "Το δοκιμαστικό μήνυμα εστάλη επιτυχώς στο Viber!",
    toast_daily_ok: "Η ημερήσια αναφορά εστάλη στο Viber!",
    toast_rescan_start: "Εκκίνηση σάρωσης όλων των θυρών USB & Serial...",
    toast_rescan_ok: "Η επανασάρωση ολοκληρώθηκε! Οι θύρες USB κλειδώθηκαν.",
    toast_rescan_err: "Σφάλμα κατά την επανασάρωση θυρών USB.",
    toast_selftest_started: "🧪 Έναρξη Self-Test (10δ) στο {name}...",
    toast_selftest_passed: "✅ Το Self-Test στο {name} ολοκληρώθηκε επιτυχώς!",
    toast_selftest_failed: "🚨❌ Αποτυχία Self-Test στο {name}! Ελέγξτε τη μπαταρία.",
    toast_buzzer_on: "🔔 Ο ηχητικός συναγερμός (Buzzer) ενεργοποιήθηκε στο {name}.",
    toast_buzzer_off: "🔕 Ο ηχητικός συναγερμός (Buzzer) σιγάστηκε στο {name}.",
  },
  en: {
    app_title: "UPS STATUS MONITOR",
    app_subtitle: "Centralized Monitoring & Telemetry",
    live_status: "LIVE STREAM",
    update_checking: "Checking...",
    btn_check_update: "Check",
    btn_update_now: "⚡ Update Now",
    btn_charts: "Charts",
    btn_events: "History",
    btn_settings: "Settings",
    btn_test_viber: "Send Test Viber Alert",
    btn_daily_report_now: "Send Daily Report Now",
    btn_rescan_usb: "Re-Scan USB Ports",
    lbl_port_bound: "Locked Port",
    lbl_port_unbound: "Auto-Scan / Unbound",
    btn_save: "💾 Save",
    btn_close: "Close",
    btn_export_csv: "Export CSV",
    btn_export_json: "Export JSON",

    total_power: "TOTAL POWER",
    avg_load: "AVG LOAD",
    grid_status: "GRID STATUS",
    active_units: "ACTIVE UNITS",
    sub_real_consumption: "Real-time consumption",
    sub_alarm_limit: "Alarm threshold: 70%",
    sub_active_desc: "2 Local + 1 Remote",

    status_normal: "NORMAL (MAINS OK)",
    status_battery: "OUTAGE (BATTERY)",
    status_overload: "OVERLOAD",
    status_offline: "OFFLINE",

    load_label: "LOAD",
    battery_label: "BATTERY",
    runtime_est: "Estimated Runtime",
    critical_low_power: "Critical low battery",
    battery_health: "Battery Health",

    grid_in: "Input",
    ups_out: "Output",
    frequency: "Frequency",
    batt_volts: "Batt Volts",
    beeper: "Beeper",
    status_mode: "Status",

    pf_grid: "Mains Grid",
    pf_inverter: "Inverter",
    pf_battery: "Battery",
    pf_loads: "Loads",

    tab_voltages: "Voltages (V)",
    tab_load: "Load & Watts",
    tab_battery: "Battery (% / V)",
    tab_freq: "Frequency (Hz)",
    chart_all_ups: "All UPS (Comparison)",

    period_5m: "5m Live",
    period_1h: "1 Hour",
    period_6h: "6 Hours",
    period_24h: "24 Hours",
    period_7d: "7 Days",

    events_title: "Incident & Event Log",
    col_time: "Time",
    col_ups: "UPS",
    col_type: "Type",
    col_severity: "Severity",
    col_message: "Message",

    settings_title: "System & Notification Settings",
    sec_viber: "📱 Viber Channel & Alerts Settings",
    lbl_viber_token: "Viber Channel / Bot Auth Token:",
    lbl_viber_sender: "Sender Name:",
    lbl_viber_receiver: "Receiver ID (Optional - for Direct User Bot messages):",

    sec_triggers: "⚡ Thresholds & Automated Alerts",
    lbl_daily_time: "Daily Report Time (HH:MM):",
    lbl_overload_thresh: "Overload Alarm Threshold:",
    lbl_battery_low_thresh: "Critical Low Battery Threshold:",
    desc_battery_low: "Display the 'Critical low battery' badge in WebUI and Viber when battery drops below this level.",
    lbl_outage_repeat: "Recurring Outage Update Interval (Viber):",
    desc_outage_repeat: "Send live status updates (Battery %, Runtime, Load, Elapsed) to Viber every X seconds during outages.",

    chk_outage: "🚨 Instant Mains Power Outage Alert",
    chk_outage_repeat: "⏳ Recurring status updates during outage (every X sec)",
    chk_restore: "🟢 Mains Power Restored Alert with outage duration",
    chk_overload: "🔥 Overload Warning Alert (> threshold)",
    chk_disconnect: "🔌 UPS Communication Lost / Restored Alert",
    chk_low_batt: "🪫 'Critical Low Battery' Warning Alert",
    chk_daily: "📊 Daily Status Report at scheduled time",

    sec_database: "📊 Database & History Retention Settings",
    desc_database: "Configure telemetry logging frequency to disk and database history retention duration.",
    lbl_db_interval: "Logging Interval (Log Interval):",
    desc_db_interval: "How often metrics are written to SQLite database (default: 60 seconds).",
    lbl_db_retention: "History Retention (Days):",
    desc_db_retention: "Select how long historical records are retained in SQLite database. Choose 'Infinite' for unlimited retention.",
    chk_db_log_on_change: "⚡ Automatically log on significant voltage/load changes (event-based)",
    chk_db_outage_fast_log: "🚨 High-resolution logging (every 1 sec) during power outages (Battery mode)",

    sec_profiles: "⚡ UPS Profiles, Names & Locations",
    desc_profiles: "Set display names and locations for all 3 UPS slots. USB ports are permanently locked to ensure consistent hardware mapping.",
    tag_ups1: "UPS 1 (Local USB 1)",
    tag_ups2: "UPS 2 (Local USB 2)",
    tag_ups3: "UPS 3 (Remote Network / IP)",
    lbl_enabled: "Enabled",
    lbl_display_name: "Display Name:",
    lbl_location: "Location:",
    lbl_rated_w: "Rated Power (Watts):",

    sec_remote_agent: "🌐 Remote UPS (Remote Agent over IP)",
    lbl_api_key: "Secret API Key for Telemetry Push:",
    desc_api_key: "Used in ups_agent.py for secure telemetry push to /api/remote/push.",

    btn_buzzer_on: "🔔 Buzzer ON",
    btn_buzzer_off: "🔕 Buzzer Muted",
    btn_selftest: "🧪 Self-Test (10s)",
    btn_selftest_running: "⏳ Testing...",
    lbl_last_selftest: "Last Self-Test",
    selftest_passed: "✅ Passed",
    selftest_failed: "❌ Failed",
    selftest_running: "⏳ Running",
    selftest_none: "Never run",

    sec_self_test: "🧪 Automated Self-Test & Schedule",
    btn_run_all_selftest: "Self-Test All Units",
    desc_self_test_schedule: "Configure periodic automated battery self-tests via timer with instant Viber feedback.",
    chk_enable_selftest_schedule: "Enable Scheduled Battery Self-Test (Timer)",
    lbl_selftest_freq: "Test Frequency:",
    opt_freq_daily: "Daily",
    opt_freq_weekly: "Weekly",
    opt_freq_monthly: "Monthly",
    lbl_selftest_time: "Test Time (HH:MM):",
    lbl_selftest_day_week: "Day of Week:",
    lbl_selftest_day_month: "Day of Month (1-31):",
    opt_day_sunday: "Sunday",
    opt_day_monday: "Monday",
    opt_day_tuesday: "Tuesday",
    opt_day_wednesday: "Wednesday",
    opt_day_thursday: "Thursday",
    opt_day_friday: "Friday",
    opt_day_saturday: "Saturday",
    chk_selftest_viber: "📱 Send detailed Self-Test results to Viber Channel",
    chk_selftest_alert: "🧪 Self-Test Result Alert (Pass / Fail)",

    unit_h: "h",
    unit_m: "m",
    unit_min: "min",
    runtime_over_10h: "> 10 hours",

    toast_outage: "⚠️ Mains power outage on {name}! Running on battery.",
    toast_restored: "🟢 Mains power restored on {name}!",
    toast_overload: "🔥 Overload on {name}!",
    toast_saved: "Settings saved successfully!",
    toast_save_err: "Failed to save settings",
    toast_test_ok: "Test alert sent successfully to Viber!",
    toast_daily_ok: "Daily report sent to Viber!",
    toast_rescan_start: "Scanning all USB & Serial ports...",
    toast_rescan_ok: "Hardware re-scan completed! Ports locked.",
    toast_rescan_err: "Failed to re-scan USB ports.",
    toast_selftest_started: "🧪 Started Self-Test (10s) on {name}...",
    toast_selftest_passed: "✅ Self-Test on {name} completed successfully!",
    toast_selftest_failed: "🚨❌ Self-Test on {name} failed! Check battery.",
    toast_buzzer_on: "🔔 Alarm buzzer enabled on {name}.",
    toast_buzzer_off: "🔕 Alarm buzzer muted on {name}.",
  }
};

let currentLang = 'el';
let chartManager = null;
let sseSource = null;
let lastKnownModes = {};
let currentBatteryLowThreshold = 20;

document.addEventListener('DOMContentLoaded', () => {
  try {
    initEventListeners();
  } catch (e) {
    console.error('initEventListeners error:', e);
  }

  try {
    const savedLang = localStorage.getItem('ups_monitor_lang') || 'el';
    setLanguage(savedLang, false);
  } catch (e) {
    console.error('setLanguage error:', e);
  }

  try {
    fetchInitialData();
  } catch (e) {
    console.error('fetchInitialData error:', e);
  }

  try {
    connectSSE();
  } catch (e) {
    console.error('connectSSE error:', e);
  }

  try {
    chartManager = new UPSChartManager('telemetryChart');
    chartManager.fetchData();
  } catch (e) {
    console.error('chartManager error:', e);
  }

  try {
    checkSystemUpdate(false);
  } catch (e) {}
});

function t(key) {
  return I18N[currentLang]?.[key] || key;
}

function formatRuntime(minutes) {
  if (minutes === null || minutes === undefined || minutes < 0) return '—';
  if (minutes >= 600) return t('runtime_over_10h');
  const total = Math.round(minutes);
  if (total < 60) return `${total} ${t('unit_min')}`;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${h}${t('unit_h')} ${m > 0 ? m + t('unit_m') : ''}`;
}

async function setLanguage(lang, syncBackend = true) {
  currentLang = lang;
  try {
    localStorage.setItem('ups_monitor_lang', lang);
  } catch (e) {}

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const k = el.getAttribute('data-i18n');
    el.textContent = t(k);
  });

  const btn = document.getElementById('langToggleBtn');
  if (btn) btn.textContent = lang === 'el' ? '🇬🇷 EL' : '🇬🇧 EN';

  if (syncBackend) {
    try {
      fetch('/api/settings/language', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang })
      }).catch(() => {});
    } catch (e) {}

    const container = document.getElementById('upsGridContainer');
    if (container) {
      container.innerHTML = '';
      fetchInitialData();
    }
    if (chartManager) {
      chartManager.fetchData();
    }
  }
}

function initEventListeners() {
  const langBtn = document.getElementById('langToggleBtn');
  if (langBtn) {
    langBtn.addEventListener('click', () => {
      setLanguage(currentLang === 'el' ? 'en' : 'el', true);
    });
  }

  const themeBtn = document.getElementById('themeToggleBtn');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      document.body.classList.toggle('light-theme');
      const isLight = document.body.classList.contains('light-theme');
      themeBtn.innerHTML = isLight ? '☀️ Light' : '🌙 Dark';
    });
  }

  const soundBtn = document.getElementById('soundToggleBtn');
  if (soundBtn) {
    soundBtn.addEventListener('click', () => {
      const active = soundBtn.getAttribute('data-active') === 'true';
      const next = !active;
      soundBtn.setAttribute('data-active', next);
      if (window.soundAlerts) window.soundAlerts.setEnabled(next);
      soundBtn.innerHTML = next ? '🔊 Audio ON' : '🔇 Audio Muted';
      showToast(next ? 'Sound Alarms Enabled' : 'Sound Alarms Muted', 'info');
    });
  }

  const settingsBtn = document.getElementById('settingsBtn');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const testViberBtn = document.getElementById('testViberBtn');
  const dailyReportBtn = document.getElementById('dailyReportBtn');
  const btnRescan = document.getElementById('btnRescanDevices');

  if (settingsBtn) settingsBtn.addEventListener('click', openSettingsModal);
  if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', closeSettingsModal);
  if (cancelSettingsBtn) cancelSettingsBtn.addEventListener('click', closeSettingsModal);
  if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', saveSettings);
  if (testViberBtn) testViberBtn.addEventListener('click', testViber);
  if (dailyReportBtn) dailyReportBtn.addEventListener('click', triggerDailyReport);
  if (btnRescan) btnRescan.addEventListener('click', rescanDevices);

  const retentionSelect = document.getElementById('dbRetentionSelect');
  if (retentionSelect) {
    retentionSelect.addEventListener('change', (e) => {
      const val = parseInt(e.target.value, 10);
      const disp = document.getElementById('dbRetentionValDisplay');
      if (disp) {
        disp.textContent = val === 0 ? (currentLang === 'el' ? '♾️ Άπειρο' : '♾️ Infinite') : `${val} ${currentLang === 'el' ? 'ημέρες' : 'days'}`;
      }
    });
  }

  const btnCheckUpdate = document.getElementById('btnCheckUpdate');
  const btnUpdateNow = document.getElementById('btnUpdateNow');
  if (btnCheckUpdate) btnCheckUpdate.addEventListener('click', () => checkSystemUpdate(true));
  if (btnUpdateNow) btnUpdateNow.addEventListener('click', performSystemUpdate);

  const freqSelect = document.getElementById('selfTestFrequencySelect');
  if (freqSelect) {
    freqSelect.addEventListener('change', (e) => {
      updateSelfTestFrequencyUI(e.target.value);
    });
  }

  const btnRunAll = document.getElementById('btnRunAllSelfTest');
  if (btnRunAll) {
    btnRunAll.addEventListener('click', handleRunAllSelfTest);
  }

  document.querySelectorAll('.metric-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.metric-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (chartManager) chartManager.setMetric(btn.getAttribute('data-metric'));
    });
  });

  document.querySelectorAll('.period-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.period-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (chartManager) chartManager.setPeriod(parseInt(btn.getAttribute('data-period')));
    });
  });

  document.querySelectorAll('.chart-ups-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.chart-ups-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const upsVal = btn.getAttribute('data-ups') || 'all';
      if (chartManager) chartManager.setUPS(upsVal);
    });
  });

  const chartUpsSelect = document.getElementById('chartUpsSelect');
  if (chartUpsSelect) {
    chartUpsSelect.addEventListener('change', (e) => {
      if (chartManager) chartManager.setUPS(e.target.value);
    });
  }

  document.getElementById('exportCsvBtn')?.addEventListener('click', () => {
    window.open('/api/export/csv?type=events', '_blank');
  });
  document.getElementById('exportJsonBtn')?.addEventListener('click', () => {
    window.open('/api/events?limit=500', '_blank');
  });
}

function updateChartTabs(profMap) {
  if (!profMap) return;
  for (const [slot, info] of Object.entries(profMap)) {
    const disp = info.display_name || slot;
    if (chartManager) {
      chartManager.setSlotLabel(slot, disp);
    }
    const sLower = slot.toLowerCase();
    if (sLower.includes('local-1') || sLower.includes('tec') || sLower.includes('primary') || sLower.includes('usb 1')) {
      const lbl = document.getElementById('chartLabelLocal1');
      if (lbl) lbl.textContent = disp;
    } else if (sLower.includes('local-2') || sLower.includes('turbo') || sLower.includes('secondary') || sLower.includes('usb 2')) {
      const lbl = document.getElementById('chartLabelLocal2');
      if (lbl) lbl.textContent = disp;
    } else if (sLower.includes('remote') || sLower.includes('3') || sLower.includes('network') || sLower.includes('ip')) {
      const lbl = document.getElementById('chartLabelRemote');
      if (lbl) lbl.textContent = disp;
    }
  }
}

function connectSSE() {
  if (sseSource) {
    sseSource.close();
  }

  sseSource = new EventSource('/api/stream');

  sseSource.addEventListener('ups_status', (e) => {
    try {
      const data = JSON.parse(e.data);
      updateDashboard(data);
    } catch (err) {
      console.error('SSE JSON error:', err);
    }
  });

  sseSource.addEventListener('ups_event', (e) => {
    try {
      const ev = JSON.parse(e.data);
      handleIncomingEvent(ev);
    } catch (err) {
      console.error('Event stream error:', err);
    }
  });

  sseSource.onerror = () => {
    setTimeout(connectSSE, 4000);
  };
}

async function fetchInitialData() {
  try {
    const resp = await fetch('/api/status');
    const data = await resp.json();
    updateDashboard(data);
    loadEvents();
  } catch (e) {
    console.warn('Initial fetch error:', e);
  }
}

function updateDashboard(payload) {
  if (!payload || !payload.ups_list) return;

  const profMap = {};
  payload.ups_list.forEach((u, idx) => {
    const key = u.slot_name || u.name || (idx === 0 ? 'Local-1' : (idx === 1 ? 'Local-2' : 'Remote-1'));
    profMap[key] = { display_name: u.display_name || u.name, location: u.location };
  });
  updateChartTabs(profMap);

  const summary = payload.summary || {};
  const totalWattsEl = document.getElementById('summaryTotalWatts');
  const avgLoadEl = document.getElementById('summaryAvgLoad');
  const activeUnitsEl = document.getElementById('summaryActiveUnits');

  if (totalWattsEl) totalWattsEl.textContent = `${summary.total_watts || 0} W`;
  if (avgLoadEl) avgLoadEl.textContent = `${summary.avg_load_pct || 0}%`;
  if (activeUnitsEl) activeUnitsEl.textContent = `${summary.online_ups || 0} / ${summary.total_ups || 3}`;

  const gridStatusEl = document.getElementById('summaryGridStatus');
  const gridCardEl = document.getElementById('summaryGridCard');

  if (gridStatusEl && gridCardEl) {
    if (summary.system_status === 'ON_BATTERY') {
      gridStatusEl.textContent = t('status_battery');
      gridCardEl.className = 'summary-card status-outage';
    } else if (summary.system_status === 'OVERLOAD') {
      gridStatusEl.textContent = t('status_overload');
      gridCardEl.className = 'summary-card status-warn';
    } else {
      gridStatusEl.textContent = t('status_normal');
      gridCardEl.className = 'summary-card status-normal';
    }
  }

  const container = document.getElementById('upsGridContainer');
  if (container) {
    payload.ups_list.forEach((ups, idx) => {
      if (!ups.slot_name) {
        ups.slot_name = idx === 0 ? 'Local-1' : idx === 1 ? 'Local-2' : 'Remote-1';
      }
      const safeId = (ups.slot_name || ups.name || `ups-${idx}`).replace(/[^a-zA-Z0-9_-]/g, '_');
      let card = document.getElementById(`ups-card-${safeId}`);
      if (!card) {
        card = createUPSCardElement(ups, safeId);
        container.appendChild(card);
      }
      updateUPSCard(card, ups);
      checkAudioAlerts(ups);
    });
  }
}

function checkAudioAlerts(ups) {
  const oldMode = lastKnownModes[ups.name];
  const newMode = (ups.mode || '').capitalize();
  const displayName = ups.display_name || ups.name;

  if (oldMode && oldMode !== newMode) {
    if (newMode === 'Battery') {
      if (window.soundAlerts) window.soundAlerts.playPowerOutage();
      showToast(t('toast_outage').replace('{name}', displayName), 'error');
    } else if (oldMode === 'Battery' && newMode === 'Line') {
      if (window.soundAlerts) window.soundAlerts.playPowerRestored();
      showToast(t('toast_restored').replace('{name}', displayName), 'success');
    }
  }

  if (ups.load_pct && ups.load_pct >= 70 && (!oldMode || oldMode !== 'overload')) {
    if (window.soundAlerts) window.soundAlerts.playOverloadAlert();
  }

  lastKnownModes[ups.name] = newMode;
}

String.prototype.capitalize = function() {
  return this.charAt(0).toUpperCase() + this.slice(1);
};

function createUPSCardElement(ups, safeId) {
  const div = document.createElement('div');
  div.id = `ups-card-${safeId}`;
  div.className = 'ups-card';
  const displayName = ups.display_name || ups.name;
  const location = ups.location || 'Local';
  div.innerHTML = `
    <div class="ups-header">
      <div class="ups-title-group">
        <div class="ups-name">
          <span>⚡</span>
          <span class="card-name">${escapeHtml(displayName)}</span>
        </div>
        <div class="ups-location">
          <span>📍</span>
          <span class="card-location">${escapeHtml(location)}</span>
        </div>
        <div class="ups-driver-tag" title="Active Protocol & Port">
          <span>🔌</span>
          <span class="card-source">${escapeHtml(ups.source || 'Auto-Scan')}</span>
        </div>
      </div>
      <div class="card-badge badge-mode badge-line">Line</div>
    </div>

    <div class="gauges-row">
      <!-- LOAD GAUGE -->
      <div class="gauge-box">
        <div class="gauge-label">${t('load_label')}</div>
        <div class="gauge-svg-container">
          <svg viewBox="0 0 100 100">
            <circle class="gauge-bg" cx="50" cy="50" r="42" />
            <circle class="gauge-progress gauge-load-progress" cx="50" cy="50" r="42" stroke-dasharray="264" stroke-dashoffset="264" />
          </svg>
          <div class="gauge-center-text">
            <span class="gauge-val gauge-load-val">0</span>
            <span class="gauge-unit">%</span>
          </div>
        </div>
        <div class="gauge-subtext gauge-watts-val">0 W</div>
      </div>

      <!-- BATTERY GAUGE -->
      <div class="gauge-box">
        <div class="gauge-label">${t('battery_label')}</div>
        <div class="gauge-svg-container">
          <svg viewBox="0 0 100 100">
            <circle class="gauge-bg" cx="50" cy="50" r="42" />
            <circle class="gauge-progress gauge-batt-progress" cx="50" cy="50" r="42" stroke-dasharray="264" stroke-dashoffset="0" />
          </svg>
          <div class="gauge-center-text">
            <span class="gauge-val gauge-batt-val">100</span>
            <span class="gauge-unit">%</span>
          </div>
        </div>
        <div class="gauge-subtext gauge-battv-val">24.0 V</div>
      </div>
    </div>

    <!-- METRICS GRID -->
    <div class="metrics-grid">
      <div class="metric-item">
        <span class="lbl">${t('grid_in')}</span>
        <span class="val card-input-v">230 V</span>
      </div>
      <div class="metric-item">
        <span class="lbl">${t('ups_out')}</span>
        <span class="val card-output-v">230 V</span>
      </div>
      <div class="metric-item">
        <span class="lbl">${t('frequency')}</span>
        <span class="val card-freq">50.0 Hz</span>
      </div>
      <div class="metric-item">
        <span class="lbl">${t('batt_volts')}</span>
        <span class="val card-battery-v">27.2 V</span>
      </div>
      <div class="metric-item">
        <span class="lbl">${t('beeper')}</span>
        <span class="val card-beeper">OFF</span>
      </div>
      <div class="metric-item">
        <span class="lbl">${t('status_mode')}</span>
        <span class="val card-mode-val">Line</span>
      </div>
    </div>

    <!-- RUNTIME BANNER -->
    <div class="runtime-banner">
      <span class="lbl">⏱️ ${t('runtime_est')}:</span>
      <span class="val card-runtime">—</span>
    </div>

    <!-- CRITICAL POWER BADGE -->
    <div class="critical-power-badge">
      <span>🪫</span>
      <span class="lbl-crit-badge"><strong>${t('critical_low_power')}</strong></span>
    </div>

    <!-- ACTION BUTTONS ROW (BUZZER TOGGLE & SELF-TEST) -->
    <div class="ups-card-actions">
      <button type="button" class="btn-action-pill btn-buzzer buzzer-toggle-btn" data-slot="${escapeHtml(ups.slot_name || safeId)}" title="Toggle Alarm Buzzer">
        <span class="buzzer-icon">🔔</span>
        <span class="buzzer-text">${t('btn_buzzer_on')}</span>
      </button>
      <button type="button" class="btn-action-pill btn-selftest selftest-action-btn" data-slot="${escapeHtml(ups.slot_name || safeId)}" title="Run 10-Second Battery Self-Test">
        <span class="selftest-icon">🧪</span>
        <span class="selftest-text">${t('btn_selftest')}</span>
      </button>
    </div>

    <!-- LAST SELF-TEST STATUS BAR -->
    <div class="selftest-badge-bar">
      <span class="st-title">🧪 <span>${t('lbl_last_selftest')}</span>:</span>
      <span class="badge-test-status badge-test-none card-selftest-badge">${t('selftest_none')}</span>
    </div>

    <!-- POWER FLOW ANIMATION -->
    <div class="power-flow-container">
      <div class="power-flow-diagram">
        <div class="pf-node pf-grid active">
          <div class="pf-icon">⚡</div>
          <span>${t('pf_grid')}</span>
        </div>
        <div class="pf-line pf-line-1 active"></div>
        <div class="pf-node pf-ups active">
          <div class="pf-icon">🔋</div>
          <span>${t('pf_inverter')}</span>
        </div>
        <div class="pf-line pf-line-2 active"></div>
        <div class="pf-node pf-loads active">
          <div class="pf-icon">🖥️</div>
          <span>${t('pf_loads')}</span>
        </div>
      </div>
    </div>
  `;

  // Attach action button click listeners
  const buzzerBtn = div.querySelector('.buzzer-toggle-btn');
  if (buzzerBtn) {
    buzzerBtn.addEventListener('click', () => {
      const slot = buzzerBtn.getAttribute('data-slot') || ups.slot_name || safeId;
      handleBuzzerToggle(slot, buzzerBtn);
    });
  }

  const selfTestBtn = div.querySelector('.selftest-action-btn');
  if (selfTestBtn) {
    selfTestBtn.addEventListener('click', () => {
      const slot = selfTestBtn.getAttribute('data-slot') || ups.slot_name || safeId;
      handleSelfTestStart(slot, selfTestBtn);
    });
  }

  return div;
}

function updateUPSCard(card, ups) {
  const nameEl = card.querySelector('.card-name');
  if (nameEl) nameEl.textContent = ups.display_name || ups.name;
  
  const locEl = card.querySelector('.card-location');
  if (locEl) locEl.textContent = ups.location || 'Local';
  
  const srcEl = card.querySelector('.card-source');
  if (srcEl) srcEl.textContent = ups.source || 'Auto-Scan';

  const badge = card.querySelector('.card-badge');
  const mode = (ups.mode || (ups.connected ? 'Line' : 'Offline')).capitalize();
  if (badge) {
    badge.textContent = mode;
    card.classList.remove('is-battery-mode', 'is-offline');
    if (!ups.connected) {
      badge.className = 'card-badge badge-mode badge-offline';
      card.classList.add('is-offline');
    } else if (mode === 'Battery') {
      badge.className = 'card-badge badge-mode badge-battery';
      card.classList.add('is-battery-mode');
    } else {
      badge.className = 'card-badge badge-mode badge-line';
    }
  }

  // Load Gauge
  const loadPct = ups.load_pct !== null && ups.load_pct !== undefined ? Math.round(ups.load_pct) : 0;
  const loadProgress = card.querySelector('.gauge-load-progress');
  const loadVal = card.querySelector('.gauge-load-val');
  const loadWatts = card.querySelector('.gauge-watts-val');

  if (loadVal) loadVal.textContent = loadPct;
  if (loadWatts) loadWatts.textContent = ups.load_w_est !== null ? `${Math.round(ups.load_w_est)} W` : '— W';

  if (loadProgress) {
    const loadOffset = 264 - (264 * Math.min(100, loadPct)) / 100;
    loadProgress.style.strokeDashoffset = loadOffset;
    if (loadPct >= 70) {
      loadProgress.style.stroke = 'var(--accent-red)';
    } else if (loadPct >= 50) {
      loadProgress.style.stroke = 'var(--accent-amber)';
    } else {
      loadProgress.style.stroke = 'var(--accent-cyan)';
    }
  }

  // Battery Gauge
  const battPct = ups.battery_pct !== null && ups.battery_pct !== undefined ? Math.round(ups.battery_pct) : null;
  const battProgress = card.querySelector('.gauge-batt-progress');
  const battVal = card.querySelector('.gauge-batt-val');
  const battV = card.querySelector('.gauge-battv-val');

  if (battVal) {
    if (battPct !== null) {
      battVal.textContent = battPct;
    } else {
      battVal.textContent = mode === 'Line' ? 'CHG' : '—';
    }
  }

  if (battProgress) {
    if (battPct !== null) {
      const battOffset = 264 - (264 * Math.min(100, battPct)) / 100;
      battProgress.style.strokeDashoffset = battOffset;
    } else {
      battProgress.style.strokeDashoffset = 0;
    }
    if (battPct !== null && battPct <= currentBatteryLowThreshold) {
      battProgress.style.stroke = 'var(--accent-red)';
    } else if (battPct !== null && battPct <= 50) {
      battProgress.style.stroke = 'var(--accent-amber)';
    } else {
      battProgress.style.stroke = 'var(--accent-green)';
    }
  }

  if (battV) battV.textContent = ups.battery_v !== null ? `${ups.battery_v.toFixed(1)} V` : '— V';

  // Critical Low Power Badge
  const isCriticalPower = ups.connected && (ups.battery_low || (battPct !== null && battPct <= currentBatteryLowThreshold && mode === 'Battery'));
  const critBadge = card.querySelector('.critical-power-badge');
  if (critBadge) {
    if (isCriticalPower) {
      critBadge.classList.add('active');
      critBadge.innerHTML = `<span>🪫</span> <span><strong>${t('critical_low_power')}</strong> (${t('battery_label')}: ${battPct !== null ? battPct + '%' : 'Low'})</span>`;
    } else {
      critBadge.classList.remove('active');
    }
  }

  // Metrics Table Values
  const inV = card.querySelector('.card-input-v');
  if (inV) inV.textContent = ups.input_v !== null ? `${ups.input_v.toFixed(1)} V` : '—';
  
  const outV = card.querySelector('.card-output-v');
  if (outV) outV.textContent = ups.output_v !== null ? `${ups.output_v.toFixed(1)} V` : '—';

  const freqEl = card.querySelector('.card-freq');
  if (freqEl) freqEl.textContent = ups.input_hz !== null ? `${ups.input_hz.toFixed(1)} Hz` : '—';

  const battVEl = card.querySelector('.card-battery-v');
  if (battVEl) battVEl.textContent = ups.battery_v !== null ? `${ups.battery_v.toFixed(1)} V` : '—';

  const beepEl = card.querySelector('.card-beeper');
  if (beepEl) beepEl.textContent = ups.beeper_on ? 'ON' : 'OFF';

  const modeEl = card.querySelector('.card-mode-val');
  if (modeEl) modeEl.textContent = mode;

  // Runtime
  const runtimeEl = card.querySelector('.card-runtime');
  if (runtimeEl) runtimeEl.textContent = formatRuntime(ups.runtime_minutes);

  // Buzzer Button State
  const buzzerBtn = card.querySelector('.buzzer-toggle-btn');
  if (buzzerBtn) {
    const isBuzzerOn = ups.beeper_on !== false && ups.beeper_on !== null;
    const iconEl = buzzerBtn.querySelector('.buzzer-icon');
    const textEl = buzzerBtn.querySelector('.buzzer-text');
    if (isBuzzerOn) {
      buzzerBtn.classList.remove('buzzer-off');
      buzzerBtn.classList.add('buzzer-on');
      if (iconEl) iconEl.textContent = '🔔';
      if (textEl) textEl.textContent = t('btn_buzzer_on');
    } else {
      buzzerBtn.classList.remove('buzzer-on');
      buzzerBtn.classList.add('buzzer-off');
      if (iconEl) iconEl.textContent = '🔕';
      if (textEl) textEl.textContent = t('btn_buzzer_off');
    }
  }

  // Self-Test Button & Running Progress
  const stBtn = card.querySelector('.selftest-action-btn');
  if (stBtn) {
    const isTesting = Boolean(ups.test_active || ups.test_progress);
    const textEl = stBtn.querySelector('.selftest-text');
    const iconEl = stBtn.querySelector('.selftest-icon');
    if (isTesting) {
      stBtn.classList.add('running');
      stBtn.disabled = true;
      const rem = ups.test_progress?.remaining !== undefined ? `${ups.test_progress.remaining}s` : '...';
      if (iconEl) iconEl.innerHTML = '<span class="spin-icon">⏳</span>';
      if (textEl) textEl.textContent = `${t('btn_selftest_running')} (${rem})`;
    } else {
      stBtn.classList.remove('running');
      stBtn.disabled = !ups.connected || mode !== 'Line';
      if (iconEl) iconEl.textContent = '🧪';
      if (textEl) textEl.textContent = t('btn_selftest');
    }
  }

  // Last Self-Test History Badge
  const stBadge = card.querySelector('.card-selftest-badge');
  if (stBadge) {
    const lastTest = ups.last_self_test;
    if (ups.test_active || ups.test_progress) {
      stBadge.className = 'badge-test-status badge-test-running';
      stBadge.innerHTML = `<span class="spin-icon">⏳</span> ${t('selftest_running')}`;
    } else if (lastTest && lastTest.status === 'PASSED') {
      stBadge.className = 'badge-test-status badge-test-passed';
      const vStr = lastTest.battery_v_min ? `${lastTest.battery_v_min.toFixed(1)}V • ` : '';
      const timeShort = (lastTest.timestamp_iso || '').substring(5, 16);
      stBadge.innerHTML = `✅ ${t('selftest_passed')} (${vStr}${timeShort})`;
    } else if (lastTest && lastTest.status === 'FAILED') {
      stBadge.className = 'badge-test-status badge-test-failed';
      const timeShort = (lastTest.timestamp_iso || '').substring(5, 16);
      stBadge.innerHTML = `❌ ${t('selftest_failed')} (${timeShort})`;
    } else {
      stBadge.className = 'badge-test-status badge-test-none';
      stBadge.textContent = t('selftest_none');
    }
  }

  // Power Flow Diagram Elements
  const pfGrid = card.querySelector('.pf-grid');
  const pfUps = card.querySelector('.pf-ups');
  const pfLoads = card.querySelector('.pf-loads');
  const pfLine1 = card.querySelector('.pf-line-1');
  const pfLine2 = card.querySelector('.pf-line-2');

  if (pfGrid && pfUps && pfLoads && pfLine1 && pfLine2) {
    pfGrid.className = 'pf-node pf-grid';
    pfUps.className = 'pf-node pf-ups';
    pfLoads.className = 'pf-node pf-loads';
    pfLine1.className = 'pf-line pf-line-1';
    pfLine2.className = 'pf-line pf-line-2';

    if (ups.connected && mode === 'Line') {
      pfGrid.classList.add('active');
      pfUps.classList.add('active');
      pfLoads.classList.add('active');
      pfLine1.classList.add('active');
      pfLine2.classList.add('active');
    } else if (ups.connected && mode === 'Battery') {
      pfUps.classList.add('battery-active');
      pfLoads.classList.add('battery-active');
      pfLine1.classList.remove('active');
      pfLine2.classList.add('battery-flow');
    }
  }
}

async function loadEvents() {
  try {
    const resp = await fetch('/api/events?limit=40');
    const json = await resp.json();
    if (json.status === 'ok') {
      const tbody = document.getElementById('eventsTableBody');
      if (tbody) {
        tbody.innerHTML = '';
        json.events.forEach(ev => appendEventRow(ev, false));
      }
    }
  } catch (e) {
    console.warn('Failed to load events:', e);
  }
}

function handleIncomingEvent(ev) {
  appendEventRow(ev, true);
  showToast(`${ev.ups_name}: ${ev.event_type}`, ev.severity);
}

function appendEventRow(ev, prepend = false) {
  const tbody = document.getElementById('eventsTableBody');
  if (!tbody) return;

  const tr = document.createElement('tr');
  const sevClass = `sev-${ev.severity || 'info'}`;
  
  tr.innerHTML = `
    <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(ev.timestamp_iso || '')}</td>
    <td><strong>${escapeHtml(ev.ups_name)}</strong></td>
    <td><span class="badge-sev ${sevClass}">${escapeHtml(ev.event_type)}</span></td>
    <td><span class="badge-sev ${sevClass}">${escapeHtml(ev.severity || 'INFO')}</span></td>
    <td style="white-space: pre-line; font-size: 0.82rem;">${escapeHtml(ev.message)}</td>
  `;

  if (prepend && tbody.firstChild) {
    tbody.insertBefore(tr, tbody.firstChild);
    if (tbody.children.length > 50) tbody.removeChild(tbody.lastChild);
  } else {
    tbody.appendChild(tr);
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

let currentProfilesCache = {};

function updateChartSelectOptions(profiles) {
  const select = document.getElementById('chartUpsSelect');
  if (!select) return;
  const currentVal = select.value || 'all';

  let optionsHtml = `<option value="all">${t('chart_all_ups')}</option>`;
  if (profiles && Object.keys(profiles).length > 0) {
    for (const [key, p] of Object.entries(profiles)) {
      if (p && p.enabled !== false) {
        optionsHtml += `<option value="${escapeHtml(key)}">${escapeHtml(p.display_name || key)}</option>`;
      }
    }
  } else {
    optionsHtml += `
      <option value="Local-1">Primary UPS (USB 1)</option>
      <option value="Local-2">Secondary UPS (USB 2)</option>
      <option value="Remote-1">Remote UPS (Network / IP)</option>
    `;
  }
  select.innerHTML = optionsHtml;
  select.value = currentVal;
}

function formatBindingBadge(prof) {
  if (prof && prof.device_id && prof.driver_type) {
    const devShort = prof.device_id.length > 35 ? prof.device_id.substring(0, 32) + '...' : prof.device_id;
    return `🔒 ${t('lbl_port_bound')}: ${prof.driver_type} (${devShort})`;
  }
  return `🔓 ${t('lbl_port_unbound')}`;
}

async function openSettingsModal() {
  try {
    const resp = await fetch('/api/settings');
    const data = await resp.json();
    const cfg = data.config || {};
    const viber = cfg.viber || {};
    const alerts = cfg.alerts || {};
    const profiles = data.profiles || {};
    currentProfilesCache = profiles;
    updateChartSelectOptions(profiles);

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    };
    const setChk = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = val;
    };

    setVal('viberTokenInput', viber.channel_token || '');
    setVal('viberSenderInput', viber.sender_name || 'UPS Monitor');
    setVal('viberReceiverInput', viber.receiver_id || '');
    setVal('dailyReportTimeInput', cfg.daily_report_time || '09:00');
    setVal('overloadSlider', cfg.overload_threshold_pct || 70);
    
    const ovDisplay = document.getElementById('overloadValDisplay');
    if (ovDisplay) ovDisplay.textContent = `${cfg.overload_threshold_pct || 70}%`;

    currentBatteryLowThreshold = cfg.battery_low_threshold_pct || 20;
    setVal('batteryLowSlider', currentBatteryLowThreshold);
    setVal('batteryLowInput', currentBatteryLowThreshold);
    const battDisplay = document.getElementById('batteryLowValDisplay');
    if (battDisplay) battDisplay.textContent = `${currentBatteryLowThreshold}%`;

    const outageRepeatInterval = cfg.outage_repeat_interval_seconds || 60;
    setVal('outageRepeatSlider', outageRepeatInterval);
    setVal('outageRepeatInput', outageRepeatInterval);
    const repDisplay = document.getElementById('outageRepeatValDisplay');
    if (repDisplay) repDisplay.textContent = `${outageRepeatInterval} sec`;

    // Database Retention & Log Interval
    const dbInterval = cfg.db_log_interval_seconds || cfg.server?.db_log_interval_seconds || 60;
    setVal('dbIntervalSlider', dbInterval);
    setVal('dbIntervalInput', dbInterval);
    const intervalDisplay = document.getElementById('dbIntervalValDisplay');
    if (intervalDisplay) intervalDisplay.textContent = `${dbInterval} sec`;

    const dbRetention = cfg.db_retention_days !== undefined ? cfg.db_retention_days : 30;
    setVal('dbRetentionSelect', dbRetention);
    const retDisplay = document.getElementById('dbRetentionValDisplay');
    if (retDisplay) {
      retDisplay.textContent = dbRetention === 0 ? (currentLang === 'el' ? '♾️ Άπειρο' : '♾️ Infinite') : `${dbRetention} ${currentLang === 'el' ? 'ημέρες' : 'days'}`;
    }

    setChk('chkDbLogOnChange', cfg.db_log_on_change !== false);
    setChk('chkDbOutageFastLog', cfg.db_outage_fast_log !== false);

    setChk('chkOutageAlert', alerts.power_outage_alert !== false);
    setChk('chkOutageRepeatAlert', alerts.outage_repeat_alert !== false);
    setChk('chkRestoreAlert', alerts.power_restore_alert !== false);
    setChk('chkOverloadAlert', alerts.overload_alert !== false);
    setChk('chkDisconnectAlert', alerts.disconnect_alert !== false);
    setChk('chkLowBattAlert', alerts.battery_low_alert !== false);
    setChk('chkDailyReport', alerts.daily_report !== false);
    setChk('chkSelfTestAlert', alerts.self_test_alert !== false);

    // Self-Test Scheduler Settings
    const selfTestCfg = cfg.self_test || {};
    setChk('chkSelfTestScheduleEnabled', selfTestCfg.schedule_enabled === true);
    setVal('selfTestFrequencySelect', selfTestCfg.frequency || 'daily');
    setVal('selfTestTimeInput', selfTestCfg.time || '09:00');
    setVal('selfTestDayOfWeekSelect', selfTestCfg.day_of_week || 'sunday');
    setVal('selfTestDayOfMonthInput', selfTestCfg.day_of_month || 1);
    setChk('chkSelfTestViberNotify', selfTestCfg.notify_viber !== false);
    updateSelfTestFrequencyUI(selfTestCfg.frequency || 'daily');

    const l1Prof = profiles['Local-1'] || profiles.TEC || {};
    const l2Prof = profiles['Local-2'] || profiles['Turbo-X'] || {};
    const remoteProf = profiles['Remote-1'] || profiles['Remote-UPS'] || {};

    const l1Badge = document.getElementById('local1BindingBadge');
    if (l1Badge) l1Badge.textContent = formatBindingBadge(l1Prof);

    const l2Badge = document.getElementById('local2BindingBadge');
    if (l2Badge) l2Badge.textContent = formatBindingBadge(l2Prof);

    setVal('local1DisplayNameInput', l1Prof.display_name || 'Primary UPS (USB 1)');
    setVal('local1LocationInput', l1Prof.location || 'Local Port 1');
    setVal('local1RatedWInput', l1Prof.rated_w || 1200);
    setChk('local1ProfileEnabled', l1Prof.enabled !== false);

    setVal('local2DisplayNameInput', l2Prof.display_name || 'Secondary UPS (USB 2)');
    setVal('local2LocationInput', l2Prof.location || 'Local Port 2');
    setVal('local2RatedWInput', l2Prof.rated_w || 1200);
    setChk('local2ProfileEnabled', l2Prof.enabled !== false);

    setVal('remoteDisplayNameInput', remoteProf.display_name || 'Remote UPS (Network / IP)');
    setVal('remoteLocationInput', remoteProf.location || 'Remote Site');
    setVal('remoteRatedWInput', remoteProf.rated_w || 1200);
    setChk('remoteProfileEnabled', remoteProf.enabled !== false);

    setVal('remoteApiKeyInput', cfg.remote_api_key || '');

    document.getElementById('settingsModal')?.classList.add('active');
  } catch (e) {
    showToast(t('toast_save_err'), 'error');
  }
}

function closeSettingsModal() {
  document.getElementById('settingsModal')?.classList.remove('active');
}

async function rescanDevices() {
  const btn = document.getElementById('btnRescanDevices');
  const icon = document.getElementById('rescanIcon');
  if (btn) {
    btn.disabled = true;
    btn.style.opacity = '0.7';
  }
  if (icon) icon.textContent = '⏳';
  showToast(t('toast_rescan_start'), 'info');

  try {
    const resp = await fetch('/api/devices/rescan', { method: 'POST' });
    const json = await resp.json();
    if (json.status === 'success') {
      showToast(t('toast_rescan_ok'), 'success');
      if (json.profiles) {
        currentProfilesCache = json.profiles;
        const l1Badge = document.getElementById('local1BindingBadge');
        const l2Badge = document.getElementById('local2BindingBadge');
        if (l1Badge) l1Badge.textContent = formatBindingBadge(json.profiles['Local-1']);
        if (l2Badge) l2Badge.textContent = formatBindingBadge(json.profiles['Local-2']);
        updateChartSelectOptions(json.profiles);
      }
      fetchInitialData();
    } else {
      showToast(t('toast_rescan_err'), 'error');
    }
  } catch (e) {
    showToast(`Re-Scan Error: ${e}`, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.style.opacity = '1';
    }
    if (icon) icon.textContent = '🔍';
  }
}

async function saveSettings() {
  const getVal = (id, def = '') => document.getElementById(id)?.value?.trim() || def;
  const getChk = (id) => document.getElementById(id)?.checked ?? true;

  const viberToken = getVal('viberTokenInput');
  const viberSender = getVal('viberSenderInput', 'UPS Monitor');
  const viberReceiver = getVal('viberReceiverInput');
  const dailyTime = getVal('dailyReportTimeInput', '09:00');
  const overloadPct = parseFloat(getVal('overloadSlider', '70')) || 70;
  const batteryLowPct = parseFloat(getVal('batteryLowInput', '20')) || 20;
  currentBatteryLowThreshold = batteryLowPct;
  const apiKey = getVal('remoteApiKeyInput');

  const dbLogInterval = parseInt(getVal('dbIntervalInput', '60'), 10) || 60;
  const dbRetentionDays = parseInt(getVal('dbRetentionSelect', '30'), 10);
  const dbLogOnChange = getChk('chkDbLogOnChange');
  const dbOutageFastLog = getChk('chkDbOutageFastLog');

  const l1DisplayName = getVal('local1DisplayNameInput', 'Primary UPS (USB 1)');
  const l1Location = getVal('local1LocationInput', 'Local Port 1');
  const l1RatedW = parseFloat(getVal('local1RatedWInput', '1200')) || 1200;
  const l1Enabled = getChk('local1ProfileEnabled');

  const l2DisplayName = getVal('local2DisplayNameInput', 'Secondary UPS (USB 2)');
  const l2Location = getVal('local2LocationInput', 'Local Port 2');
  const l2RatedW = parseFloat(getVal('local2RatedWInput', '1200')) || 1200;
  const l2Enabled = getChk('local2ProfileEnabled');

  const remoteDisplayName = getVal('remoteDisplayNameInput', 'Remote UPS (Network / IP)');
  const remoteLocation = getVal('remoteLocationInput', 'Remote Site');
  const remoteRatedW = parseFloat(getVal('remoteRatedWInput', '1200')) || 1200;
  const remoteEnabled = getChk('remoteProfileEnabled');

  const outageRepeatSec = parseInt(getVal('outageRepeatInput', '60'), 10) || 60;

  const selfTestScheduleEnabled = getChk('chkSelfTestScheduleEnabled');
  const selfTestFreq = getVal('selfTestFrequencySelect', 'daily');
  const selfTestTime = getVal('selfTestTimeInput', '09:00');
  const selfTestDayOfWeek = getVal('selfTestDayOfWeekSelect', 'sunday');
  const selfTestDayOfMonth = parseInt(getVal('selfTestDayOfMonthInput', '1'), 10) || 1;
  const selfTestViberNotify = getChk('chkSelfTestViberNotify');
  const selfTestAlert = getChk('chkSelfTestAlert');

  const payload = {
    config: {
      language: currentLang,
      viber: {
        enabled: true,
        channel_token: viberToken,
        sender_name: viberSender,
        receiver_id: viberReceiver,
      },
      alerts: {
        power_outage_alert: getChk('chkOutageAlert'),
        outage_repeat_alert: getChk('chkOutageRepeatAlert'),
        power_restore_alert: getChk('chkRestoreAlert'),
        overload_alert: getChk('chkOverloadAlert'),
        disconnect_alert: getChk('chkDisconnectAlert'),
        battery_low_alert: getChk('chkLowBattAlert'),
        daily_report: getChk('chkDailyReport'),
        self_test_alert: selfTestAlert,
      },
      self_test: {
        schedule_enabled: selfTestScheduleEnabled,
        frequency: selfTestFreq,
        time: selfTestTime,
        day_of_week: selfTestDayOfWeek,
        day_of_month: selfTestDayOfMonth,
        notify_viber: selfTestViberNotify,
        target_slots: ['Local-1', 'Local-2'],
      },
      outage_repeat_interval_seconds: outageRepeatSec,
      overload_threshold_pct: overloadPct,
      battery_low_threshold_pct: batteryLowPct,
      daily_report_time: dailyTime,
      db_log_interval_seconds: dbLogInterval,
      db_retention_days: dbRetentionDays,
      db_log_on_change: dbLogOnChange,
      db_outage_fast_log: dbOutageFastLog,
      remote_api_key: apiKey,
      ui_settings: {
        language: currentLang,
      }
    },
    profiles: {
      'Local-1': {
        ...((currentProfilesCache && currentProfilesCache['Local-1']) || {}),
        display_name: l1DisplayName,
        location: l1Location,
        rated_w: l1RatedW,
        enabled: l1Enabled,
      },
      'Local-2': {
        ...((currentProfilesCache && currentProfilesCache['Local-2']) || {}),
        display_name: l2DisplayName,
        location: l2Location,
        rated_w: l2RatedW,
        enabled: l2Enabled,
      },
      'Remote-1': {
        ...((currentProfilesCache && currentProfilesCache['Remote-1']) || {}),
        display_name: remoteDisplayName,
        location: remoteLocation,
        rated_w: remoteRatedW,
        enabled: remoteEnabled,
      },
    }
  };

  try {
    const resp = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const res = await resp.json();
    if (res.status === 'success') {
      showToast(t('toast_saved'), 'success');
      currentProfilesCache = payload.profiles;
      updateChartSelectOptions(payload.profiles);
      closeSettingsModal();
      fetchInitialData();
    } else {
      showToast(t('toast_save_err'), 'error');
    }
  } catch (e) {
    showToast(`Error: ${e}`, 'error');
  }
}

async function testViber() {
  showToast(currentLang === 'el' ? 'Αποστολή δοκιμαστικού μηνύματος στο Viber...' : 'Sending test message to Viber...', 'info');
  try {
    const resp = await fetch('/api/viber/test', { method: 'POST' });
    const res = await resp.json();
    if (res.status === 'success') {
      showToast(t('toast_test_ok'), 'success');
    } else {
      showToast(`Viber Error: ${res.message}`, 'error');
    }
  } catch (e) {
    showToast(`Connection error: ${e}`, 'error');
  }
}

async function triggerDailyReport() {
  showToast(currentLang === 'el' ? 'Αποστολή ημερήσιας αναφοράς στο Viber...' : 'Sending daily report to Viber...', 'info');
  try {
    const resp = await fetch('/api/viber/daily-report', { method: 'POST' });
    const res = await resp.json();
    if (res.status === 'success') {
      showToast(t('toast_daily_ok'), 'success');
    } else {
      showToast(`Error: ${res.message}`, 'error');
    }
  } catch (e) {
    showToast(`Connection error: ${e}`, 'error');
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${type === 'error' ? '❌' : (type === 'success' ? '✅' : 'ℹ️')}</span> <span>${escapeHtml(message)}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

async function checkSystemUpdate(manual = false) {
  const infoEl = document.getElementById('updateInfo');
  const tagEl = document.getElementById('versionTag');
  const btnNow = document.getElementById('btnUpdateNow');
  const btnCheck = document.getElementById('btnCheckUpdate');

  if (manual && btnCheck) {
    btnCheck.textContent = '...';
    btnCheck.disabled = true;
  }

  try {
    const resp = await fetch('/api/update/status');
    const data = await resp.json();

    if (data.local_version && tagEl) {
      tagEl.textContent = `v${data.local_version}`;
    }

    if (data.update_available) {
      if (infoEl) infoEl.innerHTML = `<strong style="color: #ff007f;">v${data.remote_version} ${currentLang === 'el' ? 'Διαθέσιμο!' : 'Available!'}</strong>`;
      if (btnNow) btnNow.style.display = 'inline-block';
      if (manual) showToast(`v${data.remote_version} ${currentLang === 'el' ? 'είναι διαθέσιμη!' : 'is available!'}`, 'info');
    } else {
      if (infoEl) infoEl.textContent = currentLang === 'el' ? 'Ενημερωμένο' : 'Up to date';
      if (btnNow) btnNow.style.display = 'none';
      if (manual) showToast(currentLang === 'el' ? 'Το σύστημα είναι ήδη στην τελευταία έκδοση!' : 'System is already up to date!', 'success');
    }
  } catch (e) {
    if (infoEl) infoEl.textContent = 'Offline';
    if (manual) showToast(currentLang === 'el' ? 'Αδυναμία ελέγχου ενημερώσεων' : 'Could not check for updates', 'warning');
  } finally {
    if (manual && btnCheck) {
      btnCheck.textContent = t('btn_check_update');
      btnCheck.disabled = false;
    }
  }
}

async function performSystemUpdate() {
  const confirmMsg = currentLang === 'el'
    ? 'Θέλετε να ξεκινήσει η αυτόματη ενημέρωση του Electra και η επανεκκίνηση της υπηρεσίας;'
    : 'Do you want to start the Electra update and restart the service?';

  if (!confirm(confirmMsg)) {
    return;
  }

  const btnNow = document.getElementById('btnUpdateNow');
  if (btnNow) {
    btnNow.textContent = currentLang === 'el' ? '⏳ Λήψη...' : '⏳ Downloading...';
    btnNow.disabled = true;
  }

  showToast(currentLang === 'el' ? 'Λήψη ενημέρωσης από το GitLab και ασφαλής εφαρμογή αρχείων...' : 'Downloading update from GitLab and safely applying files...', 'info');

  try {
    const resp = await fetch('/api/update/perform', { method: 'POST' });
    const res = await resp.json();

    if (res.status === 'success' || res.success) {
      showToast(currentLang === 'el' ? 'Η ενημέρωση ολοκληρώθηκε! Επανεκκίνηση διακομιστή...' : 'Update completed! Restarting server...', 'success');
      let attempts = 0;
      const pollTimer = setInterval(async () => {
        attempts++;
        try {
          const chk = await fetch('/api/version', { cache: 'no-store' });
          if (chk.ok) {
            clearInterval(pollTimer);
            window.location.reload();
          }
        } catch (e) {
          if (attempts > 30) {
            clearInterval(pollTimer);
            window.location.reload();
          }
        }
      }, 1500);
    } else {
      showToast(`Update error: ${res.message}`, 'error');
      if (btnNow) {
        btnNow.textContent = t('btn_update_now');
        btnNow.disabled = false;
      }
    }
  } catch (e) {
    showToast(currentLang === 'el' ? 'Επανεκκίνηση διακομιστή... Επαναφόρτωση...' : 'Server restart... Reloading...', 'info');
    setTimeout(() => {
      window.location.reload();
    }, 5000);
  }
}

class UPSChartManager {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.chart = null;
    this.metric = 'voltages';
    this.period = 3600;
    this.selectedUPS = 'all';
    this.slotLabels = {};
    this.colors = {
      'Local-1': { main: '#00f0ff', fill: 'rgba(0, 240, 255, 0.12)' },
      'Local-2': { main: '#00e676', fill: 'rgba(0, 230, 118, 0.12)' },
      'Remote-1': { main: '#ff007f', fill: 'rgba(255, 0, 127, 0.12)' },
      'Primary UPS (USB 1)': { main: '#00f0ff', fill: 'rgba(0, 240, 255, 0.12)' },
      'Secondary UPS (USB 2)': { main: '#00e676', fill: 'rgba(0, 230, 118, 0.12)' },
      'Remote UPS (Network / IP)': { main: '#ff007f', fill: 'rgba(255, 0, 127, 0.12)' },
      'TEC': { main: '#00f0ff', fill: 'rgba(0, 240, 255, 0.12)' },
      'Turbo-X': { main: '#00e676', fill: 'rgba(0, 230, 118, 0.12)' },
      'Remote-UPS': { main: '#ff007f', fill: 'rgba(255, 0, 127, 0.12)' },
    };
    this.initChart();
  }

  setSlotLabel(slot, label) {
    if (slot && label) {
      this.slotLabels[slot] = label;
    }
  }

  matchesSelectedUPS(upsName) {
    if (!this.selectedUPS || this.selectedUPS === 'all') return true;
    if (upsName === this.selectedUPS) return true;
    const sel = this.selectedUPS.toLowerCase().replace(/[-_ ]/g, '');
    const name = (upsName || '').toLowerCase().replace(/[-_ ]/g, '');
    
    if (name === sel || name.includes(sel) || sel.includes(name)) return true;
    
    if ((sel.includes('local1') || sel.includes('primary') || sel.includes('usb1') || sel.includes('tec') || sel === '1') &&
        (name.includes('local1') || name.includes('primary') || name.includes('usb1') || name.includes('tec') || name === '1')) {
      return true;
    }
    if ((sel.includes('local2') || sel.includes('secondary') || sel.includes('usb2') || sel.includes('turbo') || sel === '2') &&
        (name.includes('local2') || name.includes('secondary') || name.includes('usb2') || name.includes('turbo') || name === '2')) {
      return true;
    }
    if ((sel.includes('remote') || sel.includes('network') || sel.includes('ip') || sel.includes('site') || sel === '3') &&
        (name.includes('remote') || name.includes('network') || name.includes('ip') || name.includes('site') || name === '3')) {
      return true;
    }
    return false;
  }

  getSlotColor(upsName) {
    const k = String(upsName || '').toLowerCase();
    if (k.includes('local-1') || k.includes('primary') || k.includes('tec') || k.includes('usb 1') || k.includes('1')) {
      return { main: '#00f0ff', fill: 'rgba(0, 240, 255, 0.12)' };
    }
    if (k.includes('local-2') || k.includes('secondary') || k.includes('turbo') || k.includes('usb 2') || k.includes('2')) {
      return { main: '#00e676', fill: 'rgba(0, 230, 118, 0.12)' };
    }
    if (k.includes('remote') || k.includes('ip') || k.includes('network') || k.includes('site') || k.includes('3')) {
      return { main: '#ff007f', fill: 'rgba(255, 0, 127, 0.12)' };
    }
    return { main: '#ffab00', fill: 'rgba(255, 171, 0, 0.12)' };
  }

  getSlotInfo(upsName) {
    const k = String(upsName || '').toLowerCase();
    const custom = this.slotLabels[upsName];
    if (custom) {
      let icon = '⚡';
      if (k.includes('local-2') || k.includes('turbo') || k.includes('secondary') || k.includes('2')) icon = '🔌';
      else if (k.includes('remote') || k.includes('3') || k.includes('network') || k.includes('ip')) icon = '📡';
      return { label: custom, icon, fullTitle: `${icon} ${custom}` };
    }
    if (k.includes('local-1') || k.includes('tec') || k.includes('primary') || k.includes('usb 1')) {
      return { label: 'Primary UPS (USB 1)', icon: '⚡', fullTitle: '⚡ Primary UPS (USB 1)' };
    }
    if (k.includes('local-2') || k.includes('turbo') || k.includes('secondary') || k.includes('usb 2')) {
      return { label: 'Secondary UPS (USB 2)', icon: '🔌', fullTitle: '🔌 Secondary UPS (USB 2)' };
    }
    if (k.includes('remote') || k.includes('ip') || k.includes('site') || k.includes('3')) {
      return { label: 'Remote UPS (Network / IP)', icon: '📡', fullTitle: '📡 Remote UPS (IP)' };
    }
    return { label: upsName, icon: '⚡', fullTitle: `⚡ ${upsName}` };
  }

  initChart() {
    if (!this.canvas || typeof Chart === 'undefined') return;
    try {
      const ctx = this.canvas.getContext('2d');
      this.chart = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 400 },
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              position: 'top',
              labels: {
                color: '#8892b0',
                font: { family: 'Outfit, sans-serif', size: 12, weight: '600' },
                padding: 16,
                usePointStyle: true,
                pointStyle: 'circle'
              }
            },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#00f0ff',
              bodyColor: '#e2e8f0',
              borderColor: 'rgba(0, 240, 255, 0.25)',
              borderWidth: 1,
              padding: 10,
              cornerRadius: 8,
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#8892b0', maxTicksLimit: 12 }
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#8892b0' }
            }
          }
        }
      });
    } catch (e) {
      console.warn('Chart initialization error:', e);
    }
  }

  setMetric(metric) {
    this.metric = metric;
    this.fetchData();
  }

  setPeriod(period) {
    this.period = period;
    this.fetchData();
  }

  setUPS(ups) {
    this.selectedUPS = ups;
    this.fetchData();
  }

  async fetchData() {
    try {
      let url = `/api/history?period=${this.period}`;
      if (this.selectedUPS && this.selectedUPS !== 'all') {
        url += `&ups_name=${encodeURIComponent(this.selectedUPS)}`;
      }
      const resp = await fetch(url);
      const json = await resp.json();
      if (json.status === 'ok') {
        this.updateDatasets(json.history || json.data);
      }
    } catch (e) {
      console.warn('History fetch error:', e);
    }
  }

  updateDatasets(historyData) {
    if (!this.chart) return;
    const datasets = [];
    let commonLabels = [];

    const formatTs = (ts) => {
      const d = new Date(ts * 1000);
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      const ss = String(d.getSeconds()).padStart(2, '0');
      if (this.period <= 300) return `${hh}:${mm}:${ss}`;
      if (this.period <= 86400) return `${hh}:${mm}`;
      return `${d.getDate()}/${d.getMonth()+1} ${hh}:${mm}`;
    };

    for (const [upsName, records] of Object.entries(historyData || {})) {
      if (!this.matchesSelectedUPS(upsName)) continue;
      const palette = this.getSlotColor(upsName);
      const dev = this.getSlotInfo(upsName);

      if (!commonLabels.length && records && records.length) {
        commonLabels = records.map(r => formatTs(r.timestamp));
      }

      if (this.metric === 'voltages') {
        datasets.push({
          label: `⚡ [${dev.fullTitle}] ${currentLang === 'el' ? 'Έξοδος (V)' : 'Output (V)'}`,
          data: records.map(r => r.output_v),
          borderColor: palette.main,
          backgroundColor: palette.fill,
          fill: false,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 0,
        });
        datasets.push({
          label: `〰️ [${dev.fullTitle}] ${currentLang === 'el' ? 'Είσοδος ΔΕΗ (V)' : 'Grid In (V)'}`,
          data: records.map(r => r.input_v),
          borderColor: 'rgba(148, 163, 184, 0.7)',
          borderDash: [4, 4],
          fill: false,
          tension: 0.3,
          borderWidth: 1.5,
          pointRadius: 0,
        });
      } else if (this.metric === 'load') {
        datasets.push({
          label: `📊 [${dev.fullTitle}] ${currentLang === 'el' ? 'Φορτίο (%)' : 'Load (%)'}`,
          data: records.map(r => r.load_pct),
          borderColor: palette.main,
          backgroundColor: palette.fill,
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 0,
        });
        datasets.push({
          label: `💡 [${dev.fullTitle}] ${currentLang === 'el' ? 'Κατανάλωση (Watts)' : 'Power (Watts)'}`,
          data: records.map(r => r.load_w),
          borderColor: '#ffab00',
          fill: false,
          tension: 0.3,
          borderWidth: 1.5,
          pointRadius: 0,
        });
      } else if (this.metric === 'battery') {
        datasets.push({
          label: `🔋 [${dev.fullTitle}] ${currentLang === 'el' ? 'Μπαταρία (%)' : 'Battery (%)'}`,
          data: records.map(r => r.battery_pct),
          borderColor: palette.main,
          backgroundColor: palette.fill,
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 0,
        });
        datasets.push({
          label: `⚡ [${dev.fullTitle}] ${currentLang === 'el' ? 'Τάση Μπαταρίας (V)' : 'Battery Volts (V)'}`,
          data: records.map(r => r.battery_v),
          borderColor: '#00e676',
          borderDash: [3, 3],
          fill: false,
          tension: 0.3,
          borderWidth: 1.5,
          pointRadius: 0,
        });
      } else if (this.metric === 'frequency') {
        datasets.push({
          label: `〰️ [${dev.fullTitle}] ${currentLang === 'el' ? 'Συχνότητα (Hz)' : 'Frequency (Hz)'}`,
          data: records.map(r => r.input_hz),
          borderColor: palette.main,
          backgroundColor: palette.fill,
          fill: false,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 0,
        });
      }
    }

    this.chart.data.labels = commonLabels;
    this.chart.data.datasets = datasets;
    this.chart.update('none');
  }
}

window.soundAlerts = {
  enabled: true,
  audioCtx: null,

  init() {
    if (!this.audioCtx) {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioCtx = new AudioContext();
      } catch (e) {}
    }
  },

  setEnabled(val) {
    this.enabled = val;
  },

  beep(freq, durationMs, count = 1, pauseMs = 100) {
    if (!this.enabled) return;
    this.init();
    if (!this.audioCtx) return;

    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }

    let delay = 0;
    for (let i = 0; i < count; i++) {
      setTimeout(() => {
        try {
          const osc = this.audioCtx.createOscillator();
          const gain = this.audioCtx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);
          gain.gain.setValueAtTime(0.3, this.audioCtx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.0001, this.audioCtx.currentTime + durationMs / 1000);
          osc.connect(gain);
          gain.connect(this.audioCtx.destination);
          osc.start();
          osc.stop(this.audioCtx.currentTime + durationMs / 1000);
        } catch (e) {}
      }, delay);
      delay += durationMs + pauseMs;
    }
  },

  playPowerOutage() {
    this.beep(880, 250, 3, 150);
  },

  playPowerRestored() {
    this.beep(523, 150, 1, 50);
    setTimeout(() => this.beep(659, 150, 1, 50), 180);
    setTimeout(() => this.beep(783, 250, 1, 50), 360);
  },

  playOverloadAlert() {
    this.beep(1200, 100, 4, 80);
  }
};

function updateSelfTestFrequencyUI(freq) {
  const dayWeekGrp = document.getElementById('selfTestDayOfWeekGroup');
  const dayMonthGrp = document.getElementById('selfTestDayOfMonthGroup');
  if (dayWeekGrp) dayWeekGrp.style.display = freq === 'weekly' ? 'block' : 'none';
  if (dayMonthGrp) dayMonthGrp.style.display = freq === 'monthly' ? 'block' : 'none';
}

async function handleBuzzerToggle(slotName, btnElement) {
  if (!slotName) return;
  try {
    if (btnElement) btnElement.disabled = true;
    const resp = await fetch(`/api/ups/${encodeURIComponent(slotName)}/buzzer/toggle`, {
      method: 'POST',
    });
    const rawText = await resp.text();
    let data;
    try {
      data = JSON.parse(rawText);
    } catch (e) {
      showToast(`Buzzer toggle response error (${resp.status}): ${rawText.substring(0, 80)}`, 'error');
      return;
    }
    if (resp.ok && data.status === 'success') {
      const isNowOn = Boolean(data.beeper_on);
      const toastMsg = isNowOn
        ? t('toast_buzzer_on').replace('{name}', slotName)
        : t('toast_buzzer_off').replace('{name}', slotName);
      showToast(toastMsg, 'info');
      fetchInitialData();
    } else {
      showToast(data.detail || data.error || data.message || 'Failed to toggle buzzer', 'error');
    }
  } catch (err) {
    showToast(`Buzzer toggle error: ${err.message}`, 'error');
  } finally {
    if (btnElement) btnElement.disabled = false;
  }
}

async function handleSelfTestStart(slotName, btnElement) {
  if (!slotName) return;
  try {
    if (btnElement) {
      btnElement.disabled = true;
      btnElement.classList.add('running');
    }
    const resp = await fetch(`/api/ups/${encodeURIComponent(slotName)}/self-test`, {
      method: 'POST',
    });
    const rawText = await resp.text();
    let data;
    try {
      data = JSON.parse(rawText);
    } catch (e) {
      showToast(`Self-test response error (${resp.status}): ${rawText.substring(0, 80)}`, 'error');
      if (btnElement) {
        btnElement.disabled = false;
        btnElement.classList.remove('running');
      }
      return;
    }
    if (resp.ok && (data.status === 'started' || data.status === 'success')) {
      showToast(t('toast_selftest_started').replace('{name}', slotName), 'info');
      fetchInitialData();
    } else {
      showToast(data.detail || data.error || data.message || 'Failed to start self-test', 'error');
      if (btnElement) {
        btnElement.disabled = false;
        btnElement.classList.remove('running');
      }
    }
  } catch (err) {
    showToast(`Self-test error: ${err.message}`, 'error');
    if (btnElement) {
      btnElement.disabled = false;
      btnElement.classList.remove('running');
    }
  }
}

async function handleRunAllSelfTest() {
  const btn = document.getElementById('btnRunAllSelfTest');
  if (btn) btn.disabled = true;
  showToast(currentLang === 'el' ? 'Έναρξη Self-Test σε όλα τα ενεργά UPS...' : 'Triggering Self-Test on all active units...', 'info');

  const slots = ['Local-1', 'Local-2', 'Remote-1'];
  for (const s of slots) {
    try {
      await fetch(`/api/ups/${encodeURIComponent(s)}/self-test`, { method: 'POST' });
    } catch (e) {}
  }
  setTimeout(() => {
    if (btn) btn.disabled = false;
    fetchInitialData();
  }, 1000);
}

