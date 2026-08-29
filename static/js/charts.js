/**
 * Chart.js Integration for UPS Status Real-Time & Historical Monitoring
 */

class UPSChartManager {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.chart = null;
    this.currentMetric = 'voltages'; // voltages, load, battery, frequency
    this.currentUPS = 'all'; // all, TEC, Turbo-X, Remote-UPS
    this.currentPeriod = 3600; // 300, 3600, 21600, 86400, 604800
    this.cachedData = {};
    this.initChart();
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
              color: '#8a99b5',
              font: { family: 'Outfit', size: 12, weight: '500' },
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 18,
            }
          },
          tooltip: {
            backgroundColor: 'rgba(18, 26, 44, 0.95)',
            titleColor: '#00f0ff',
            bodyColor: '#f0f4fc',
            borderColor: 'rgba(0, 240, 255, 0.3)',
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            usePointStyle: true,
            titleFont: { family: 'JetBrains Mono', size: 12, weight: '700' },
            bodyFont: { family: 'Outfit', size: 12 },
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
              drawBorder: false,
            },
            ticks: {
              color: '#546481',
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
              color: '#8a99b5',
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
            tension: 0.35,
            borderWidth: 2.2,
          },
          point: {
            radius: 0,
            hoverRadius: 5,
            hoverBorderWidth: 2,
          }
        },
        animation: {
          duration: 400
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

  render() {
    if (!this.chart || !this.cachedData) return;

    const colors = {
      'TEC': { main: '#00f0ff', sec: '#0072ff', bg: 'rgba(0, 240, 255, 0.08)' },
      'Turbo-X': { main: '#00e676', sec: '#00b0ff', bg: 'rgba(0, 230, 118, 0.08)' },
      'Remote-UPS': { main: '#ffab00', sec: '#ff1744', bg: 'rgba(255, 171, 0, 0.08)' },
    };

    let allTimestamps = new Set();
    const upsKeys = this.currentUPS === 'all' ? Object.keys(this.cachedData) : [this.currentUPS];

    upsKeys.forEach(k => {
      const arr = this.cachedData[k] || [];
      arr.forEach(pt => allTimestamps.add(pt.time_label));
    });

    const labels = Array.from(allTimestamps);
    const datasets = [];
    let showDualY = false;

    if (this.currentMetric === 'voltages') {
      this.chart.options.scales.y.title = { display: true, text: 'Voltage (V)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = false;

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = colors[name] || { main: '#8c52ff', sec: '#ff1744' };
        
        datasets.push({
          label: `${name} In (V)`,
          data: series.map(d => d.input_v),
          borderColor: pal.main,
          backgroundColor: 'transparent',
          borderDash: [],
          yAxisID: 'y',
        });
        datasets.push({
          label: `${name} Out (V)`,
          data: series.map(d => d.output_v),
          borderColor: pal.sec,
          backgroundColor: 'transparent',
          borderDash: [4, 4],
          yAxisID: 'y',
        });
      });
    } else if (this.currentMetric === 'load') {
      showDualY = true;
      this.chart.options.scales.y.title = { display: true, text: 'Load (%)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = true;
      this.chart.options.scales.y1.title = { display: true, text: 'Power (W)', color: '#ffab00' };

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = colors[name] || { main: '#00f0ff', sec: '#ffab00' };

        datasets.push({
          label: `${name} Load %`,
          data: series.map(d => d.load_pct),
          borderColor: pal.main,
          backgroundColor: 'transparent',
          yAxisID: 'y',
        });
        datasets.push({
          label: `${name} Power (W)`,
          data: series.map(d => d.load_w),
          borderColor: pal.sec || '#ffab00',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
          yAxisID: 'y1',
        });
      });
    } else if (this.currentMetric === 'battery') {
      showDualY = true;
      this.chart.options.scales.y.title = { display: true, text: 'Battery (%)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = true;
      this.chart.options.scales.y1.title = { display: true, text: 'Voltage (V)', color: '#00e676' };

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = colors[name] || { main: '#00e676', sec: '#00f0ff' };

        datasets.push({
          label: `${name} Battery %`,
          data: series.map(d => d.battery_pct),
          borderColor: pal.main,
          backgroundColor: 'transparent',
          yAxisID: 'y',
        });
        datasets.push({
          label: `${name} Battery (V)`,
          data: series.map(d => d.battery_v),
          borderColor: pal.sec || '#00f0ff',
          backgroundColor: 'transparent',
          borderDash: [3, 3],
          yAxisID: 'y1',
        });
      });
    } else if (this.currentMetric === 'frequency') {
      this.chart.options.scales.y.title = { display: true, text: 'Frequency (Hz)', color: '#8a99b5' };
      this.chart.options.scales.y1.display = false;

      upsKeys.forEach(name => {
        const series = this.cachedData[name] || [];
        const pal = colors[name] || { main: '#8c52ff' };

        datasets.push({
          label: `${name} Input (Hz)`,
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
