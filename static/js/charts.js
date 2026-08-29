/**
 * Electra - UPS Status Central Monitor
 * Interactive Chart.js Telemetry Engine with UPS Grouping & Rich Icons
 */

class UPSChartManager {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.chart = null;
    this.currentMetric = 'voltages'; // voltages, load, battery, frequency
    this.currentUPS = 'all'; // all, Local-1, Local-2, Remote-1
    this.currentPeriod = 3600; // 300, 3600, 21600, 86400, 604800
    this.cachedData = {};
    this.slotLabels = {
      'Local-1': 'UPS 1 (Local)',
      'Local-2': 'UPS 2 (Local)',
      'Remote-1': 'UPS 3 (Remote)'
    };
    this.initChart();
  }

  setSlotLabel(slot, label) {
    if (slot && label && this.slotLabels[slot] !== label) {
      this.slotLabels[slot] = label;
      if (this.chart && this.cachedData && Object.keys(this.cachedData).length > 0) {
        this.render();
      }
    }
  }

  getSlotDisplayName(key) {
    if (this.slotLabels[key]) return this.slotLabels[key];
    if (key.toLowerCase().includes('local-1') || key.toLowerCase().includes('tec')) return 'UPS 1';
    if (key.toLowerCase().includes('local-2') || key.toLowerCase().includes('turbo')) return 'UPS 2';
    if (key.toLowerCase().includes('remote')) return 'UPS 3 (Remote)';
    return key;
  }

  initChart() {
    if (!this.canvas) return;
    const ctx = this.canvas.getContext('2d');

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: []
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: '#a0aec0',
              font: { family: 'Outfit', size: 12, weight: '600' },
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 16,
              boxWidth: 8,
              boxHeight: 8,
            }
          },
          tooltip: {
            backgroundColor: 'rgba(10, 15, 29, 0.95)',
            titleColor: '#00f0ff',
            bodyColor: '#f0f4fc',
            borderColor: 'rgba(0, 240, 255, 0.35)',
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            usePointStyle: true,
            titleFont: { family: 'JetBrains Mono', size: 12, weight: '700' },
            bodyFont: { family: 'Outfit', size: 12, weight: '500' },
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed.y !== null) {
                  label += context.parsed.y;
                }
                return label;
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.04)',
              drawBorder: false,
            },
            ticks: {
              color: '#64748b',
              font: { family: 'JetBrains Mono', size: 10 },
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 10,
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
              drawBorder: false,
            },
            ticks: {
              color: '#94a3b8',
              font: { family: 'JetBrains Mono', size: 11 },
            }
          },
          y1: {
            type: 'linear',
            display: false,
            position: 'right',
            grid: {
              drawOnChartArea: false,
            },
            ticks: {
              color: '#ffab00',
              font: { family: 'JetBrains Mono', size: 11 },
            }
          }
        },
        elements: {
          line: {
            tension: 0.32,
            borderWidth: 2.2,
          },
          point: {
            radius: 0,
            hoverRadius: 5,
            hoverBorderWidth: 2,
          }
        },
        animation: {
          duration: 350
        }
      }
    });
  }

  setMetric(metric) {
    this.currentMetric = metric;
    this.render();
  }

  setUPS(upsName) {
    this.currentUPS = upsName;
    this.render();
  }

  setPeriod(periodSeconds) {
    this.currentPeriod = periodSeconds;
    this.fetchData();
  }

  async fetchData() {
    try {
      const resp = await fetch(`/api/history?period=${this.currentPeriod}`);
      const json = await resp.json();
      if (json.status === 'ok') {
        this.cachedData = json.history || {};
        this.render();
      }
    } catch (e) {
      console.warn('Failed to fetch history:', e);
    }
  }

  getUPSPalette(name) {
    const n = String(name).toLowerCase();
    if (n.includes('local-1') || n.includes('tec') || n.includes('primary')) {
      return { main: '#00f0ff', sec: '#0088ff', icon: '⚡' };
    }
    if (n.includes('local-2') || n.includes('turbo') || n.includes('secondary')) {
      return { main: '#00e676', sec: '#00b0ff', icon: '⚡' };
    }
    if (n.includes('remote') || n.includes('site') || n.includes('ip')) {
      return { main: '#ffab00', sec: '#ff1744', icon: '📡' };
    }
    return { main: '#8c52ff', sec: '#f50057', icon: '🔌' };
  }

  render() {
    if (!this.chart || !this.cachedData) return;

    let allTimestamps = new Set();
    const availableKeys = Object.keys(this.cachedData);

    let upsKeys = [];
    if (this.currentUPS === 'all') {
      upsKeys = availableKeys;
    } else {
      // Find matching key
      upsKeys = availableKeys.filter(k => k === this.currentUPS || k.toLowerCase().includes(this.currentUPS.toLowerCase()));
      if (upsKeys.length === 0 && availableKeys.length > 0) {
        upsKeys = availableKeys; // fallback
      }
    }

    upsKeys.forEach(k => {
      const arr = this.cachedData[k] || [];
      arr.forEach(pt => allTimestamps.add(pt.time_label));
    });

    const labels = Array.from(allTimestamps);
    const datasets = [];
    const isGreek = (window.currentLang || 'el') === 'el';

    if (this.currentMetric === 'voltages') {
      this.chart.options.scales.y.title = { display: true, text: isGreek ? 'Τάση (Volts)' : 'Voltage (V)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = false;

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = this.getUPSPalette(name);
        const displayName = this.getSlotDisplayName(name);
        
        datasets.push({
          label: `${pal.icon} [${displayName}] ${isGreek ? 'Είσοδος' : 'Input'} (V)`,
          data: series.map(d => d.input_v),
          borderColor: pal.main,
          backgroundColor: 'transparent',
          borderDash: [],
          yAxisID: 'y',
        });
        datasets.push({
          label: `🔌 [${displayName}] ${isGreek ? 'Έξοδος' : 'Output'} (V)`,
          data: series.map(d => d.output_v),
          borderColor: pal.sec,
          backgroundColor: 'transparent',
          borderDash: [4, 4],
          yAxisID: 'y',
        });
      });
    } else if (this.currentMetric === 'load') {
      this.chart.options.scales.y.title = { display: true, text: isGreek ? 'Φορτίο (%)' : 'Load (%)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = true;
      this.chart.options.scales.y1.title = { display: true, text: isGreek ? 'Ισχύς (Watts)' : 'Power (W)', color: '#ffab00' };

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = this.getUPSPalette(name);
        const displayName = this.getSlotDisplayName(name);

        datasets.push({
          label: `📊 [${displayName}] ${isGreek ? 'Φορτίο %' : 'Load %'}`,
          data: series.map(d => d.load_pct),
          borderColor: pal.main,
          backgroundColor: 'transparent',
          yAxisID: 'y',
        });
        datasets.push({
          label: `⚡ [${displayName}] ${isGreek ? 'Ισχύς W' : 'Power W'}`,
          data: series.map(d => d.load_w),
          borderColor: pal.sec || '#ffab00',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
          yAxisID: 'y1',
        });
      });
    } else if (this.currentMetric === 'battery') {
      this.chart.options.scales.y.title = { display: true, text: isGreek ? 'Στάθμη Μπαταρίας (%)' : 'Battery (%)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = true;
      this.chart.options.scales.y1.title = { display: true, text: isGreek ? 'Τάση Μπαταρίας (V)' : 'Battery (V)', color: '#00e676' };

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = this.getUPSPalette(name);
        const displayName = this.getSlotDisplayName(name);

        datasets.push({
          label: `🔋 [${displayName}] ${isGreek ? 'Στάθμη %' : 'Battery %'}`,
          data: series.map(d => d.battery_pct),
          borderColor: pal.main,
          backgroundColor: 'transparent',
          yAxisID: 'y',
        });
        datasets.push({
          label: `⚡ [${displayName}] ${isGreek ? 'Τάση V' : 'Voltage V'}`,
          data: series.map(d => d.battery_v),
          borderColor: pal.sec || '#00e676',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
          yAxisID: 'y1',
        });
      });
    } else if (this.currentMetric === 'frequency') {
      this.chart.options.scales.y.title = { display: true, text: isGreek ? 'Συχνότητα (Hz)' : 'Frequency (Hz)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = false;

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = this.getUPSPalette(name);
        const displayName = this.getSlotDisplayName(name);

        datasets.push({
          label: `〰️ [${displayName}] ${isGreek ? 'Συχνότητα Hz' : 'Frequency Hz'}`,
          data: series.map(d => d.input_hz),
          borderColor: pal.main,
          backgroundColor: 'transparent',
          yAxisID: 'y',
        });
      });
    }

    this.chart.data.labels = labels;
    this.chart.data.datasets = datasets;
    this.chart.update();
  }
}
