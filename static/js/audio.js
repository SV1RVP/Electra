/**
 * Web Audio API Sound Generator for UPS Alarms & Chimes
 */

class SoundAlertManager {
  constructor() {
    this.audioCtx = null;
    this.enabled = true;
    this.volume = 0.8;
  }

  _initContext() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContext();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  setEnabled(enabled) {
    this.enabled = !!enabled;
  }

  setVolume(vol) {
    this.volume = Math.max(0, Math.min(1, parseFloat(vol) || 0.8));
  }

  playPowerOutage() {
    if (!this.enabled) return;
    try {
      this._initContext();
      const now = this.audioCtx.currentTime;
      
      // Dual high-pitch emergency alert beep
      for (let i = 0; i < 3; i++) {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, now + i * 0.25);
        osc.frequency.exponentialRampToValueAtTime(440, now + i * 0.25 + 0.18);
        
        gain.gain.setValueAtTime(this.volume * 0.4, now + i * 0.25);
        gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.25 + 0.2);
        
        osc.connect(gain);
        gain.connect(this.audioCtx.destination);
        
        osc.start(now + i * 0.25);
        osc.stop(now + i * 0.25 + 0.22);
      }
    } catch (e) {
      console.warn('Audio play error:', e);
    }
  }

  playPowerRestored() {
    if (!this.enabled) return;
    try {
      this._initContext();
      const now = this.audioCtx.currentTime;
      
      // Pleasant upward chime: C5 -> E5 -> G5 -> C6
      const notes = [523.25, 659.25, 783.99, 1046.50];
      notes.forEach((freq, idx) => {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now + idx * 0.12);
        
        gain.gain.setValueAtTime(this.volume * 0.35, now + idx * 0.12);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.12 + 0.35);
        
        osc.connect(gain);
        gain.connect(this.audioCtx.destination);
        
        osc.start(now + idx * 0.12);
        osc.stop(now + idx * 0.12 + 0.4);
      });
    } catch (e) {
      console.warn('Audio play error:', e);
    }
  }

  playOverloadAlert() {
    if (!this.enabled) return;
    try {
      this._initContext();
      const now = this.audioCtx.currentTime;
      
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      
      osc.type = 'square';
      osc.frequency.setValueAtTime(600, now);
      osc.frequency.linearRampToValueAtTime(900, now + 0.15);
      osc.frequency.linearRampToValueAtTime(600, now + 0.3);
      
      gain.gain.setValueAtTime(this.volume * 0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      
      osc.start(now);
      osc.stop(now + 0.36);
    } catch (e) {
      console.warn('Audio play error:', e);
    }
  }
}

window.soundAlerts = new SoundAlertManager();
