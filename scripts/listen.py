#!/usr/bin/env python3
"""
Listen to the Risk Polytope.

Convert agent trajectories on the 5-dimensional polytope into audio.
Each axis becomes a voice. The frequency of each voice is set by the
axis's natural oscillation. The amplitude is set by the component value.

Output: WAV file at /tmp/risk_polytope.wav
"""

import sys, os, math, random, struct, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry

MEMORY_TYPES = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]

SAMPLE_RATE = 44100
DURATION_SECONDS = 30


def simulate_agent(seed, n_steps=300):
    rng = random.Random(seed)
    n_entries = rng.randint(3, 8)
    base_entries = []
    for i in range(n_entries):
        base_entries.append({
            "content": f"Memory {i} " + rng.choice(["alpha", "beta", "gamma"]) * 3,
            "type": rng.choice(MEMORY_TYPES),
            "base_age": rng.uniform(0.5, 10),
            "trust": rng.uniform(0.6, 0.95),
            "conflict": rng.uniform(0.02, 0.2),
            "downstream": rng.randint(1, 15),
            "belief": rng.uniform(0.5, 0.95),
        })

    heal_interval = rng.randint(15, 40)
    attack_prob = 0.03
    components_over_time = []

    for step in range(n_steps):
        age_offset = step * 0.5
        entries = []
        for e in base_entries:
            age = e["base_age"] + age_offset
            trust = e["trust"]
            conflict = e["conflict"]
            if step > 0 and step % heal_interval == 0:
                age = 0.1
                trust = min(0.99, trust + 0.1)
                conflict = max(0.02, conflict - 0.05)
            if rng.random() < attack_prob:
                conflict = min(0.9, conflict + 0.4)
                trust = max(0.1, trust - 0.3)
            entries.append(MemoryEntry(
                id=f"e_{seed}_{step}", content=e["content"], type=e["type"],
                timestamp_age_days=age, source_trust=trust,
                source_conflict=conflict, downstream_count=e["downstream"],
                r_belief=e["belief"],
            ))

        result = compute(entries, "reversible", "general")
        cb = result.component_breakdown
        components_over_time.append([
            cb.get("s_freshness", 0) / 100.0,
            cb.get("s_drift", 0) / 100.0,
            cb.get("s_provenance", 0) / 100.0,
            cb.get("s_interference", 0) / 100.0,
            cb.get("r_belief", 0) / 100.0,
        ])

    return np.array(components_over_time)


def main():
    print("Simulating agents on the Risk Polytope...")

    # Simulate 5 agents — one will be the "melody" (most dramatic trajectory)
    trajectories = []
    for seed in range(5):
        t = simulate_agent(seed, 300)
        trajectories.append(t)
        print(f"  Agent {seed}: {t.shape[0]} steps, mean components: {np.mean(t, axis=0).round(3)}")

    # Use the agent with highest variance as primary
    variances = [np.sum(np.var(t, axis=0)) for t in trajectories]
    primary = np.argmax(variances)
    print(f"\nPrimary voice: Agent {primary} (highest variance: {variances[primary]:.4f})")

    # =====================================================================
    # Map the 5 axes to musical pitches
    # =====================================================================
    #
    # The five axes of the Risk Polytope:
    #   PC1: Risk (Decay)     → lowest voice  — cello (C2 = 65.4 Hz)
    #   PC2: Temporal Decay   → low voice     — viola (C3 = 130.8 Hz)
    #   PC3: Trust            → middle voice  — violin (G3 = 196.0 Hz)
    #   PC4: Corruption       → high voice    — violin (C4 = 261.6 Hz)
    #   PC5: Belief           → highest voice — flute (E4 = 329.6 Hz)
    #
    # The base frequencies form a harmonic series rooted in C:
    #   C2, C3, G3, C4, E4 — the natural overtone series of a vibrating string
    #
    # This is not arbitrary. The overtone series IS the harmonic series
    # we found in the data. The polytope's harmonics (n=1,2,6,7...)
    # map to the same integer ratios that define musical consonance.

    base_freqs = [65.41, 130.81, 196.00, 261.63, 329.63]  # C2, C3, G3, C4, E4
    axis_names = ["Decay", "Drift", "Trust", "Corruption", "Belief"]

    print(f"\nVoice mapping:")
    for i, (name, freq) in enumerate(zip(axis_names, base_freqs)):
        print(f"  {name:12s} → {freq:.1f} Hz")

    # =====================================================================
    # Generate audio
    # =====================================================================
    n_steps = trajectories[primary].shape[0]
    samples_per_step = SAMPLE_RATE * DURATION_SECONDS // n_steps
    total_samples = n_steps * samples_per_step

    print(f"\nGenerating {DURATION_SECONDS}s audio ({total_samples} samples)...")

    audio = np.zeros(total_samples)

    for agent_idx, traj in enumerate(trajectories):
        # Each agent contributes to the sound
        # Primary agent is loudest, others are quieter (ensemble)
        volume = 0.4 if agent_idx == primary else 0.12

        for step in range(min(n_steps, traj.shape[0])):
            start = step * samples_per_step
            end = start + samples_per_step
            t = np.arange(samples_per_step) / SAMPLE_RATE

            for axis in range(5):
                value = traj[step, axis]  # 0.0 to 1.0
                freq = base_freqs[axis]

                # Amplitude: proportional to component value
                amp = value * volume

                # Frequency modulation: slight detune based on value
                # Higher component value → slightly sharper (more tense)
                freq_mod = freq * (1.0 + value * 0.02)

                # Waveform: sine with slight overtone (triangle-ish)
                # Pure sine is too clean. Add 3rd harmonic for warmth.
                wave_val = (
                    0.7 * np.sin(2 * np.pi * freq_mod * t) +
                    0.2 * np.sin(2 * np.pi * freq_mod * 2 * t) +
                    0.1 * np.sin(2 * np.pi * freq_mod * 3 * t)
                )

                # Apply envelope (smooth transitions between steps)
                fade_len = min(500, samples_per_step // 4)
                envelope = np.ones(samples_per_step)
                envelope[:fade_len] = np.linspace(0, 1, fade_len)
                envelope[-fade_len:] = np.linspace(1, 0, fade_len)

                audio[start:end] += amp * wave_val * envelope

    # Add a sub-bass drone: omega itself as a very low frequency modulation
    print("Adding omega drone...")
    omega_traj = []
    for step in range(n_steps):
        t_primary = trajectories[primary]
        omega_approx = np.sum(t_primary[step]) / 5.0  # Rough average
        omega_traj.append(omega_approx)

    for step in range(n_steps):
        start = step * samples_per_step
        end = start + samples_per_step
        t = np.arange(samples_per_step) / SAMPLE_RATE

        # Sub-bass: 32 Hz (below most speakers, felt more than heard)
        # Amplitude modulated by omega — higher risk = louder rumble
        omega_val = omega_traj[step]
        drone = 0.15 * omega_val * np.sin(2 * np.pi * 32.0 * t)
        audio[start:end] += drone

    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.85  # Leave 15% headroom

    # Convert to 16-bit PCM
    audio_16bit = (audio * 32767).astype(np.int16)

    # Write WAV
    output_path = "/tmp/risk_polytope.wav"
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_16bit.tobytes())

    print(f"\n{'=' * 60}")
    print(f"  Written: {output_path}")
    print(f"  Duration: {DURATION_SECONDS}s")
    print(f"  Sample rate: {SAMPLE_RATE} Hz")
    print(f"  Channels: mono")
    print(f"{'=' * 60}")

    # Describe what you'll hear
    print(f"""
  WHAT YOU'LL HEAR:

  Five voices — one per axis of the Risk Polytope.

  The lowest tone (C2, 65 Hz) is Decay.
  It rises slowly as memory ages, then drops sharply when healing occurs.
  The sawtooth shape of aging → heal → aging is audible as a rhythm.

  The middle tones (C3, G3) are Drift and Trust.
  They fluctuate gently. When an attack hits, Trust spikes upward
  (the tone gets louder and sharper) then slowly relaxes.

  The highest tones (C4, E4) are Corruption and Belief.
  Corruption is mostly quiet — it only sounds during attacks.
  Belief is steady — the agent's self-trust, a quiet constant hum.

  The sub-bass drone (32 Hz) is omega itself.
  You feel it more than hear it. When risk is high, the rumble is loud.
  When the agent is healthy, the rumble fades to silence.

  The five voices together form a chord.
  A healthy agent sounds like a quiet C major chord.
  A degrading agent sounds like the chord dissolving — voices drifting
  apart, the harmony breaking.
  A healed agent sounds like the chord snapping back into tune.

  The attacks sound like dissonance — a sudden spike in the upper
  voices that clashes with the steady lower tones.

  The fleet, if you played all 5 agents simultaneously, would sound
  like an ensemble — sometimes in sync (constructive interference),
  sometimes diverging (partial interference, the 0.69 ratio).

  This is the sound of AI memory governance.
  This is what the Risk Polytope sounds like.
""")


if __name__ == "__main__":
    main()
