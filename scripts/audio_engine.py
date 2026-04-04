#!/usr/bin/env python3
"""
Finzora AI — Ambient Müzik Sentez Motoru v2
============================================
FM sentez + akor ilerleme + reverb + filtre + stereo
Instagram story videoları için 15 saniyelik profesyonel ambient parçalar üretir.

Kullanım:
  python3 scripts/audio_engine.py --mood dramatic --duration 15 --output story_audio.wav
  python3 scripts/audio_engine.py --mood bullish
  python3 scripts/audio_engine.py --mood bearish
  python3 scripts/audio_engine.py --mood neutral
  python3 scripts/audio_engine.py --mood tension

Mood'lar:
  dramatic  — gerilimli, sinematik (savaş/kriz haberleri)
  bullish   — yükseliş, umut verici (piyasa rallisi)
  bearish   — karanlık, endişeli (düşüş haberleri) 
  neutral   — sakin, profesyonel (eğitim/analiz)
  tension   — gergin, beklenti (kazanç açıklaması öncesi)
"""

import numpy as np
from scipy.signal import butter, sosfilt, sawtooth
from scipy.io import wavfile
import argparse
import os
import wave
import struct

SR = 44100  # sample rate

# ============================================================
# TEMEL ARAÇLAR
# ============================================================

def note_freq(note_name):
    """Nota adından frekans: A4=440Hz, C4=261.6Hz vb."""
    notes = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,
             'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
    if note_name[-1].isdigit():
        octave = int(note_name[-1])
        name = note_name[:-1]
    else:
        octave = 4
        name = note_name
    semitone = notes[name] - 9 + (octave - 4) * 12
    return 440.0 * (2 ** (semitone / 12.0))


def adsr_envelope(duration, attack=0.3, decay=0.2, sustain_level=0.6, release=0.5):
    """ADSR zarf üret"""
    n = int(duration * SR)
    env = np.zeros(n)
    
    a_samples = int(attack * SR)
    d_samples = int(decay * SR)
    r_samples = int(release * SR)
    s_samples = max(0, n - a_samples - d_samples - r_samples)
    
    idx = 0
    # Attack
    if a_samples > 0:
        end = min(idx + a_samples, n)
        env[idx:end] = np.linspace(0, 1, end - idx)
        idx = end
    # Decay
    if d_samples > 0 and idx < n:
        end = min(idx + d_samples, n)
        env[idx:end] = np.linspace(1, sustain_level, end - idx)
        idx = end
    # Sustain
    if s_samples > 0 and idx < n:
        end = min(idx + s_samples, n)
        env[idx:end] = sustain_level
        idx = end
    # Release
    if idx < n:
        env[idx:] = np.linspace(sustain_level, 0, n - idx)
    
    return env


def lowpass_filter(audio, cutoff, order=4):
    """Butterworth low-pass filtre"""
    nyq = SR / 2
    cutoff = min(cutoff, nyq * 0.95)
    sos = butter(order, cutoff / nyq, btype='low', output='sos')
    return sosfilt(sos, audio)


def simple_reverb(audio, decay=0.4, delays_ms=[23, 37, 53, 71, 97]):
    """Schroeder tarzı basit reverb"""
    out = audio.copy()
    for d_ms in delays_ms:
        d_samples = int(d_ms / 1000 * SR)
        delayed = np.zeros_like(audio)
        delayed[d_samples:] = audio[:-d_samples] * decay
        out += delayed
        decay *= 0.75
    # Normalize
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak
    return out


def stereo_spread(mono, width=0.3):
    """Mono sinyali stereo'ya çevir - hafif delay ile genişlik"""
    delay_samples = int(0.012 * SR)  # 12ms stereo delay
    left = mono.copy()
    right = np.zeros_like(mono)
    right[delay_samples:] = mono[:-delay_samples]
    
    mid = (left + right) / 2
    side = (left - right) / 2
    
    left_out = mid + side * width
    right_out = mid - side * width
    
    return np.column_stack([left_out, right_out])


# ============================================================
# SENTEZ MODÜLLERI
# ============================================================

def fm_pad(freq, duration, mod_ratio=2.0, mod_depth=0.5, detune=0.003):
    """FM sentez pad sesi — sıcak, derin"""
    t = np.linspace(0, duration, int(duration * SR), endpoint=False)
    
    # Detuned oscilator çifti (kalınlık için)
    carrier1 = np.sin(2 * np.pi * freq * t + 
                       mod_depth * np.sin(2 * np.pi * freq * mod_ratio * t))
    carrier2 = np.sin(2 * np.pi * freq * (1 + detune) * t + 
                       mod_depth * 0.8 * np.sin(2 * np.pi * freq * mod_ratio * (1 + detune) * t))
    carrier3 = np.sin(2 * np.pi * freq * (1 - detune) * t + 
                       mod_depth * 0.6 * np.sin(2 * np.pi * freq * mod_ratio * (1 - detune) * t))
    
    pad = (carrier1 * 0.5 + carrier2 * 0.3 + carrier3 * 0.2)
    
    # Yavaş tremolo
    tremolo = 1.0 + 0.08 * np.sin(2 * np.pi * 0.25 * t)
    pad *= tremolo
    
    return pad


def sub_bass(freq, duration, drive=0.3):
    """Alt bas — derin, sıcak"""
    t = np.linspace(0, duration, int(duration * SR), endpoint=False)
    
    # Sine + hafif harmonik
    bass = np.sin(2 * np.pi * freq * t)
    bass += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    bass += 0.1 * np.sin(2 * np.pi * freq * 3 * t)
    
    # Soft saturation
    bass = np.tanh(bass * (1 + drive))
    
    return lowpass_filter(bass, 200)


def shimmer_texture(freq, duration, density=0.7):
    """Yüksek frekanslı parıltı dokusu"""
    t = np.linspace(0, duration, int(duration * SR), endpoint=False)
    
    shimmer = np.zeros_like(t)
    for i in range(5):
        ratio = 4 + i * 2  # 4x, 6x, 8x, 10x, 12x harmonik
        phase_mod = np.sin(2 * np.pi * (0.1 + i * 0.07) * t) * 1.5
        shimmer += (0.5 ** i) * np.sin(2 * np.pi * freq * ratio * t + phase_mod)
    
    # Yavaş dalga ile modüle et
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t)
    shimmer *= mod * density * 0.15
    
    return shimmer


def noise_sweep(duration, start_freq=200, end_freq=2000):
    """Filtreli gürültü süpürmesi — geçiş efekti"""
    t = np.linspace(0, duration, int(duration * SR), endpoint=False)
    noise = np.random.randn(len(t)) * 0.1
    
    # Frekans süpürmesi (lineer)
    freqs = np.linspace(start_freq, end_freq, 20)
    out = np.zeros_like(t)
    
    chunk_size = len(t) // 20
    for i, freq in enumerate(freqs):
        start = i * chunk_size
        end = min(start + chunk_size, len(t))
        chunk = noise[start:end]
        filtered = lowpass_filter(np.pad(chunk, (100, 100), mode='reflect'), freq)[100:100+len(chunk)]
        out[start:end] = filtered[:end-start]
    
    env = adsr_envelope(duration, attack=1.0, decay=0.5, sustain_level=0.3, release=2.0)
    return out * env


# ============================================================
# AKOR İLERLEMELERİ
# ============================================================

CHORD_PROGRESSIONS = {
    'dramatic': [
        # Am - F - C - G (sinematik, epik)
        ['A2', 'A3', 'C4', 'E4'],
        ['F2', 'F3', 'A3', 'C4'],
        ['C2', 'C3', 'E3', 'G3'],
        ['G2', 'G3', 'B3', 'D4'],
    ],
    'bullish': [
        # C - G - Am - F (pozitif, yükselişçi)
        ['C2', 'C3', 'E3', 'G3'],
        ['G2', 'G3', 'B3', 'D4'],
        ['A2', 'A3', 'C4', 'E4'],
        ['F2', 'F3', 'A3', 'C4'],
    ],
    'bearish': [
        # Am - Dm - Em - Am (karanlık, kaygılı)
        ['A2', 'A3', 'C4', 'E4'],
        ['D2', 'D3', 'F3', 'A3'],
        ['E2', 'E3', 'G3', 'B3'],
        ['A2', 'A3', 'C4', 'E4'],
    ],
    'neutral': [
        # Cmaj7 - Fmaj7 - Dm7 - G7 (jazz/lo-fi, sakin)
        ['C2', 'C3', 'E3', 'G3', 'B3'],
        ['F2', 'F3', 'A3', 'C4', 'E4'],
        ['D2', 'D3', 'F3', 'A3', 'C4'],
        ['G2', 'G3', 'B3', 'D4', 'F4'],
    ],
    'tension': [
        # Cm - Ab - Eb - Bb (gerilim, beklenti)
        ['C2', 'C3', 'Eb3', 'G3'],
        ['Ab2', 'Ab3', 'C4', 'Eb4'],
        ['Eb2', 'Eb3', 'G3', 'Bb3'],
        ['Bb2', 'Bb3', 'D4', 'F4'],
    ],
}

MOOD_PARAMS = {
    'dramatic': {
        'mod_depth': 0.8, 'mod_ratio': 2.0, 'cutoff': 3000,
        'reverb_decay': 0.5, 'bass_vol': 0.35, 'pad_vol': 0.4,
        'shimmer_vol': 0.15, 'noise_vol': 0.05, 'tempo': 0.27,
    },
    'bullish': {
        'mod_depth': 0.4, 'mod_ratio': 3.0, 'cutoff': 5000,
        'reverb_decay': 0.35, 'bass_vol': 0.25, 'pad_vol': 0.45,
        'shimmer_vol': 0.2, 'noise_vol': 0.03, 'tempo': 0.22,
    },
    'bearish': {
        'mod_depth': 1.2, 'mod_ratio': 1.5, 'cutoff': 1800,
        'reverb_decay': 0.6, 'bass_vol': 0.4, 'pad_vol': 0.35,
        'shimmer_vol': 0.08, 'noise_vol': 0.08, 'tempo': 0.35,
    },
    'neutral': {
        'mod_depth': 0.3, 'mod_ratio': 2.5, 'cutoff': 4000,
        'reverb_decay': 0.3, 'bass_vol': 0.2, 'pad_vol': 0.5,
        'shimmer_vol': 0.12, 'noise_vol': 0.02, 'tempo': 0.25,
    },
    'tension': {
        'mod_depth': 1.0, 'mod_ratio': 1.414, 'cutoff': 2200,
        'reverb_decay': 0.55, 'bass_vol': 0.35, 'pad_vol': 0.38,
        'shimmer_vol': 0.1, 'noise_vol': 0.1, 'tempo': 0.3,
    },
}


# ============================================================
# ANA ÜRETİCİ
# ============================================================

def generate_ambient(mood='dramatic', duration=15, seed=None):
    """
    Profesyonel ambient parça üret.
    
    Args:
        mood: dramatic|bullish|bearish|neutral|tension
        duration: saniye
        seed: tekrarlanabilirlik için random seed
    
    Returns:
        numpy array (stereo, float64)
    """
    if seed is not None:
        np.random.seed(seed)
    
    params = MOOD_PARAMS[mood]
    chords = CHORD_PROGRESSIONS[mood]
    n_samples = int(duration * SR)
    
    # Her akor için süre
    chord_dur = duration / len(chords)
    
    # Katmanları oluştur
    pad_layer = np.zeros(n_samples)
    bass_layer = np.zeros(n_samples)
    shimmer_layer = np.zeros(n_samples)
    
    for i, chord_notes in enumerate(chords):
        start = int(i * chord_dur * SR)
        end = min(int((i + 1) * chord_dur * SR), n_samples)
        seg_dur = (end - start) / SR
        
        # Her nota için pad
        chord_pad = np.zeros(end - start)
        for j, note in enumerate(chord_notes):
            freq = note_freq(note)
            vol = 0.6 if j < 2 else 0.4  # bas notalar daha yüksek
            
            if freq < 100:
                # Bas notalar sub_bass ile
                note_audio = sub_bass(freq, seg_dur, drive=0.2) * vol
                bass_layer[start:end] += note_audio[:end-start] * params['bass_vol']
            else:
                # Üst notalar FM pad ile
                note_audio = fm_pad(freq, seg_dur, 
                                   mod_ratio=params['mod_ratio'],
                                   mod_depth=params['mod_depth']) * vol
                chord_pad += note_audio[:end-start]
        
        # Akorlar arası crossfade
        xfade = int(0.5 * SR)  # 500ms crossfade
        env = np.ones(end - start)
        if xfade < len(env):
            env[:xfade] = np.linspace(0, 1, xfade)
            env[-xfade:] = np.linspace(1, 0, xfade)
        
        pad_layer[start:end] += chord_pad * env * params['pad_vol']
        
        # Shimmer (sadece üst akor notalarından)
        if len(chord_notes) >= 3:
            shim_freq = note_freq(chord_notes[2])
            shim = shimmer_texture(shim_freq, seg_dur) * env
            shimmer_layer[start:end] += shim[:end-start] * params['shimmer_vol']
    
    # Noise texture
    noise_layer = noise_sweep(duration, 
                              start_freq=300 if mood != 'bearish' else 100,
                              end_freq=1500 if mood != 'bearish' else 800) * params['noise_vol']
    
    # Mix
    mix = pad_layer + bass_layer + shimmer_layer + noise_layer[:n_samples]
    
    # Low-pass filtre
    mix = lowpass_filter(mix, params['cutoff'])
    
    # Reverb
    mix = simple_reverb(mix, decay=params['reverb_decay'])
    
    # Master fade in/out
    fade_in = int(1.5 * SR)
    fade_out = int(2.0 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    
    # Normalize
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.85
    
    # Stereo
    stereo = stereo_spread(mix, width=0.35)
    
    return stereo


def save_wav(audio, filepath, sample_rate=SR):
    """Stereo float64 array'i 16-bit WAV olarak kaydet"""
    # Normalize ve 16-bit'e çevir
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9
    
    audio_16 = (audio * 32767).astype(np.int16)
    
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(2)  # stereo
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_16.tobytes())


# ============================================================
# CLI
# ============================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Finzora AI Ambient Müzik Motoru v2')
    parser.add_argument('--mood', default='dramatic', 
                       choices=['dramatic', 'bullish', 'bearish', 'neutral', 'tension'],
                       help='Müzik ruh hali')
    parser.add_argument('--duration', type=int, default=15, help='Süre (saniye)')
    parser.add_argument('--output', default=None, help='Çıktı dosya yolu')
    parser.add_argument('--seed', type=int, default=None, help='Random seed')
    parser.add_argument('--all', action='store_true', help='Tüm mood lari üret')
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    audio_dir = os.path.join(base_dir, 'assets', 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    if args.all:
        # Tüm mood'ları üret
        for mood in MOOD_PARAMS.keys():
            out = os.path.join(audio_dir, f'ambient_{mood}_{args.duration}s.wav')
            print(f"  🎵 {mood}...")
            audio = generate_ambient(mood=mood, duration=args.duration, seed=args.seed)
            save_wav(audio, out)
            size_kb = os.path.getsize(out) / 1024
            print(f"     ✓ {out} ({size_kb:.0f} KB)")
        print("\n  ✅ tüm mood'lar üretildi!")
    else:
        out = args.output or os.path.join(audio_dir, f'ambient_{args.mood}_{args.duration}s.wav')
        print(f"\n  🎵 Finzora AI Ambient Motoru v2")
        print(f"     Mood: {args.mood}")
        print(f"     Süre: {args.duration}s")
        
        audio = generate_ambient(mood=args.mood, duration=args.duration, seed=args.seed)
        save_wav(audio, out)
        
        size_kb = os.path.getsize(out) / 1024
        print(f"\n  ✅ Kaydedildi: {out} ({size_kb:.0f} KB)")
