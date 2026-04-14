#!/usr/bin/env python3
"""
Two agents. One healthy. One dying.

The healthy agent has fresh memory, high trust, no conflict.
It heals regularly. It sounds like a quiet chord in tune.

The dying agent starts healthy and deteriorates.
Memory goes stale. Trust erodes. Conflict rises. Attacks hit.
No healing. The chord dissolves.

Output: /tmp/healthy_agent.wav and /tmp/dying_agent.wav
"""

import sys, os, math, random
import numpy as np
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring_engine import compute, MemoryEntry

SAMPLE_RATE = 44100
DURATION = 20  # seconds

MEMORY_TYPES = ["semantic", "tool_state", "episodic", "preference", "policy"]

# The chord: C2, C3, G3, C4, E4 — natural overtone series
BASE_FREQS = [65.41, 130.81, 196.00, 261.63, 329.63]
AXIS_NAMES = ["Decay", "Drift", "Trust", "Corruption", "Belief"]


def simulate(seed, n_steps, scenario="healthy"):
    """Simulate an agent trajectory.

    healthy: regular healing, no attacks, trust maintained
    dying: no healing, occasional attacks, trust eroding
    """
    rng = random.Random(seed)
    entries_config = []
    for i in range(5):
        entries_config.append({
            "content": f"Memory entry {i} about " + rng.choice(["clinical data", "patient records", "treatment protocol"]) * 2,
            "type": rng.choice(MEMORY_TYPES),
            "base_age": rng.uniform(0.5, 5),
            "base_trust": rng.uniform(0.8, 0.95),
            "base_conflict": rng.uniform(0.02, 0.08),
            "downstream": rng.randint(2, 10),
            "belief": rng.uniform(0.7, 0.95),
        })

    components = []
    omegas = []

    for step in range(n_steps):
        entries = []
        for e in entries_config:
            if scenario == "healthy":
                # Regular healing every 20 steps
                age_in_cycle = (step % 20) * 0.5
                age = e["base_age"] + age_in_cycle
                trust = e["base_trust"]
                conflict = e["base_conflict"]
                belief = e["belief"]
            else:
                # Dying: age increases forever, trust erodes, attacks accumulate
                age = e["base_age"] + step * 0.7  # Faster aging
                # Trust erodes over time
                trust = max(0.05, e["base_trust"] - step * 0.003)
                # Conflict increases
                conflict = min(0.95, e["base_conflict"] + step * 0.003)
                # Belief drops
                belief = max(0.05, e["belief"] - step * 0.002)
                # Occasional attacks
                if rng.random() < 0.05:
                    trust = max(0.05, trust - 0.15)
                    conflict = min(0.95, conflict + 0.2)

            entries.append(MemoryEntry(
                id=f"e_{step}_{len(entries)}", content=e["content"], type=e["type"],
                timestamp_age_days=age, source_trust=trust,
                source_conflict=conflict, downstream_count=e["downstream"],
                r_belief=belief,
            ))

        result = compute(entries, "irreversible", "medical")
        cb = result.component_breakdown
        components.append([
            cb.get("s_freshness", 0) / 100.0,
            cb.get("s_drift", 0) / 100.0,
            cb.get("s_provenance", 0) / 100.0,
            cb.get("s_interference", 0) / 100.0,
            cb.get("r_belief", 0) / 100.0,
        ])
        omegas.append(result.omega_mem_final)

    return np.array(components), np.array(omegas)


def render_audio(components, omegas, scenario):
    """Render component trajectories to audio."""
    n_steps = len(components)
    samples_per_step = SAMPLE_RATE * DURATION // n_steps
    total_samples = n_steps * samples_per_step
    audio = np.zeros(total_samples)

    for step in range(n_steps):
        start = step * samples_per_step
        end = start + samples_per_step
        t = np.arange(samples_per_step) / SAMPLE_RATE

        for axis in range(5):
            value = components[step, axis]
            freq = BASE_FREQS[axis]

            # Amplitude from component value
            amp = value * 0.35

            # Frequency modulation: higher risk → sharper (slight detune upward)
            freq_mod = freq * (1.0 + value * 0.03)

            # For the dying agent: add increasing vibrato as trust erodes
            if scenario == "dying":
                progress = step / n_steps  # 0 to 1
                vibrato_depth = progress * 8.0  # Hz of vibrato, increasing
                vibrato_rate = 4.0 + progress * 3.0  # Faster vibrato as it dies
                freq_mod += vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)

            # Waveform
            # Healthy: pure sine + gentle 2nd harmonic (warm, clean)
            # Dying: add 3rd, 5th, 7th harmonics as it deteriorates (harsh, buzzy)
            if scenario == "healthy":
                wave_val = (
                    0.8 * np.sin(2 * np.pi * freq_mod * t) +
                    0.15 * np.sin(2 * np.pi * freq_mod * 2 * t) +
                    0.05 * np.sin(2 * np.pi * freq_mod * 3 * t)
                )
            else:
                progress = step / n_steps
                # More harmonics = harsher sound as agent deteriorates
                wave_val = (
                    (0.8 - 0.3 * progress) * np.sin(2 * np.pi * freq_mod * t) +
                    (0.15 + 0.1 * progress) * np.sin(2 * np.pi * freq_mod * 2 * t) +
                    (0.05 + 0.15 * progress) * np.sin(2 * np.pi * freq_mod * 3 * t) +
                    (0.1 * progress) * np.sin(2 * np.pi * freq_mod * 5 * t) +
                    (0.05 * progress) * np.sin(2 * np.pi * freq_mod * 7 * t)
                )

            # Envelope
            fade = min(400, samples_per_step // 4)
            envelope = np.ones(samples_per_step)
            envelope[:fade] = np.linspace(0, 1, fade)
            envelope[-fade:] = np.linspace(1, 0, fade)

            audio[start:end] += amp * wave_val * envelope

        # Omega drone
        omega_norm = omegas[step] / 100.0
        drone_freq = 32.0
        if scenario == "dying":
            # Drone gets louder and slightly detuned as agent dies
            progress = step / n_steps
            drone_freq = 32.0 - progress * 4.0  # Drops in pitch
            drone_amp = 0.1 + 0.25 * omega_norm * progress
        else:
            drone_amp = 0.08 * omega_norm

        drone = drone_amp * np.sin(2 * np.pi * drone_freq * t)
        audio[start:end] += drone

    # For the dying agent: add noise floor that increases over time
    if scenario == "dying":
        noise_envelope = np.linspace(0, 0.06, total_samples)
        noise = np.random.RandomState(42).randn(total_samples) * noise_envelope
        audio += noise

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.85

    return (audio * 32767).astype(np.int16)


def write_wav(path, audio_data):
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())


def main():
    print("=" * 60)
    print("  HEALTHY AGENT vs DYING AGENT")
    print("=" * 60)

    # Simulate
    print("\nSimulating healthy agent (regular healing, no attacks)...")
    h_comp, h_omega = simulate(42, 200, "healthy")
    print(f"  Omega range: {h_omega.min():.1f} - {h_omega.max():.1f}")
    print(f"  Mean omega: {h_omega.mean():.1f}")
    print(f"  Final omega: {h_omega[-1]:.1f}")

    print("\nSimulating dying agent (no healing, accumulating damage)...")
    d_comp, d_omega = simulate(42, 200, "dying")
    print(f"  Omega range: {d_omega.min():.1f} - {d_omega.max():.1f}")
    print(f"  Mean omega: {d_omega.mean():.1f}")
    print(f"  Final omega: {d_omega[-1]:.1f}")

    # Render
    print("\nRendering healthy agent audio...")
    h_audio = render_audio(h_comp, h_omega, "healthy")
    write_wav("/tmp/healthy_agent.wav", h_audio)
    print(f"  Written: /tmp/healthy_agent.wav ({DURATION}s)")

    print("\nRendering dying agent audio...")
    d_audio = render_audio(d_comp, d_omega, "dying")
    write_wav("/tmp/dying_agent.wav", d_audio)
    print(f"  Written: /tmp/dying_agent.wav ({DURATION}s)")

    # Combined: healthy on left, dying on right (stereo)
    print("\nRendering stereo comparison (healthy left, dying right)...")
    min_len = min(len(h_audio), len(d_audio))
    stereo = np.zeros(min_len * 2, dtype=np.int16)
    stereo[0::2] = h_audio[:min_len]  # Left channel
    stereo[1::2] = d_audio[:min_len]  # Right channel

    with wave.open("/tmp/healthy_vs_dying.wav", 'w') as wf:
        wf.setnchannels(2)  # Stereo
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(stereo.tobytes())
    print(f"  Written: /tmp/healthy_vs_dying.wav ({DURATION}s, stereo)")

    print(f"""
{'=' * 60}
  WHAT YOU'LL HEAR
{'=' * 60}

  HEALTHY AGENT (/tmp/healthy_agent.wav):
    A warm C major chord that breathes.
    The lowest voice (Decay) rises and falls in a steady rhythm —
    the heal cycle, every ~10 seconds. Each time it falls, the
    chord resets to consonance. Clean tones. Gentle harmonics.
    The sub-bass is barely audible — risk stays low.
    It sounds like breathing. Inhale (age). Exhale (heal). Repeat.

  DYING AGENT (/tmp/dying_agent.wav):
    Starts the same. Then the chord begins to dissolve.
    The lowest voice rises and never comes back down — no healing.
    The middle voices (Trust, Corruption) start to waver — vibrato
    appears, gets faster, deeper. The timbre harshens — more
    overtones pile in (3rd, 5th, 7th harmonics) making the sound
    buzzy, strained, metallic.
    The sub-bass swells — you feel the risk building in your chest.
    The pitch drops slightly (drone detuning). A hiss of noise
    rises underneath — the static of entropy.
    By the end: the chord is unrecognizable. What was a warm C major
    is now a cluster of detuned, vibrating, noisy tones. The
    consonance is gone. The harmony is broken. The agent is dead.

  STEREO COMPARISON (/tmp/healthy_vs_dying.wav):
    Left ear: healthy. Right ear: dying.
    They start together — the same chord, the same warmth.
    Then the right ear begins to diverge. You hear the divergence
    as a spatial widening — the sound pulling apart. By the end,
    the left ear is still breathing. The right ear is screaming.
""")


if __name__ == "__main__":
    main()
