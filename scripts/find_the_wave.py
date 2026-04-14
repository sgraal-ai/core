#!/usr/bin/env python3
"""
Find the Wave.

The Risk Polytope is 5-dimensional, flat, convex. Agents move on it.
Does the motion have resonance? Do disturbances propagate as waves?

1. FREQUENCY: Does the omega time series have natural frequencies?
2. RESONANCE: Does the heal cycle create standing patterns?
3. PROPAGATION: Do disturbances travel between coupled agents?
4. HARMONICS: Are there overtones — higher modes of oscillation?
5. INTERFERENCE: Do waves from different agents superpose?
"""

import sys, os, math, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry

MEMORY_TYPES = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]


def simulate_agent_trajectory(seed, n_steps=200, domain="general", action_type="reversible"):
    """Simulate an agent's trajectory on the Risk Polytope.

    The agent starts with fresh memory, accumulates decay,
    heals periodically, and occasionally gets attacked.
    """
    rng = random.Random(seed)
    trajectory = []
    omegas = []
    components_over_time = []

    # Initial memory state
    n_entries = rng.randint(3, 8)
    base_entries = []
    for i in range(n_entries):
        base_entries.append({
            "id": f"e_{seed}_{i}",
            "content": f"Memory {i} " + rng.choice(["alpha", "beta", "gamma"]) * 3,
            "type": rng.choice(MEMORY_TYPES),
            "base_age": rng.uniform(0.5, 10),
            "trust": rng.uniform(0.6, 0.95),
            "conflict": rng.uniform(0.02, 0.2),
            "downstream": rng.randint(1, 15),
            "belief": rng.uniform(0.5, 0.95),
        })

    heal_interval = rng.randint(15, 40)  # Steps between heals
    attack_prob = 0.03  # 3% chance of attack per step

    for step in range(n_steps):
        # Age increases each step
        age_offset = step * 0.5  # 0.5 days per step

        # Build entries with current age
        entries = []
        for e in base_entries:
            age = e["base_age"] + age_offset
            trust = e["trust"]
            conflict = e["conflict"]

            # Periodic healing: reset age
            if step > 0 and step % heal_interval == 0:
                age = 0.1
                trust = min(0.99, trust + 0.1)
                conflict = max(0.02, conflict - 0.05)

            # Occasional attack: spike conflict
            if rng.random() < attack_prob:
                conflict = min(0.9, conflict + 0.4)
                trust = max(0.1, trust - 0.3)

            entries.append(MemoryEntry(
                id=e["id"], content=e["content"], type=e["type"],
                timestamp_age_days=age, source_trust=trust,
                source_conflict=conflict, downstream_count=e["downstream"],
                r_belief=e["belief"],
            ))

        result = compute(entries, action_type, domain)
        omegas.append(result.omega_mem_final)

        cb = result.component_breakdown
        components_over_time.append([
            cb.get("s_freshness", 0), cb.get("s_drift", 0),
            cb.get("s_provenance", 0), cb.get("s_interference", 0),
            cb.get("r_belief", 0),
        ])

    return np.array(omegas), np.array(components_over_time)


def compute_power_spectrum(signal):
    """Compute power spectrum via FFT."""
    n = len(signal)
    # Remove mean (DC component)
    signal_centered = signal - np.mean(signal)
    # Apply Hanning window to reduce spectral leakage
    window = np.hanning(n)
    windowed = signal_centered * window
    # FFT
    fft_vals = np.fft.rfft(windowed)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(n)
    return freqs[1:], power[1:]  # Skip DC


def find_peaks(freqs, power, n_peaks=5):
    """Find top peaks in power spectrum."""
    peaks = []
    for i in range(1, len(power) - 1):
        if power[i] > power[i-1] and power[i] > power[i+1]:
            peaks.append((freqs[i], power[i], 1.0/freqs[i] if freqs[i] > 0 else float('inf')))
    peaks.sort(key=lambda x: x[1], reverse=True)
    return peaks[:n_peaks]


def compute_cross_spectrum(signal_a, signal_b):
    """Compute cross-spectral density and coherence between two signals."""
    n = min(len(signal_a), len(signal_b))
    a = signal_a[:n] - np.mean(signal_a[:n])
    b = signal_b[:n] - np.mean(signal_b[:n])
    window = np.hanning(n)
    fft_a = np.fft.rfft(a * window)
    fft_b = np.fft.rfft(b * window)
    cross = fft_a * np.conj(fft_b)
    power_a = np.abs(fft_a) ** 2
    power_b = np.abs(fft_b) ** 2
    # Coherence: |S_ab|² / (S_aa · S_bb)
    coherence = np.abs(cross) ** 2 / (power_a * power_b + 1e-20)
    freqs = np.fft.rfftfreq(n)
    return freqs[1:], coherence[1:], np.angle(cross[1:])


def main():
    N_AGENTS = 30
    N_STEPS = 200

    print("=" * 60)
    print("  SEARCHING FOR THE WAVE")
    print("=" * 60)

    # =====================================================================
    # 1. FREQUENCY — Natural oscillations in omega time series
    # =====================================================================
    print("\n" + "=" * 60)
    print("  1. FREQUENCY ANALYSIS")
    print("=" * 60)

    all_omegas = []
    all_components = []
    all_peaks = []

    print(f"\nSimulating {N_AGENTS} agents × {N_STEPS} steps...")
    for agent_id in range(N_AGENTS):
        domain = ["general", "fintech", "medical", "coding"][agent_id % 4]
        action = ["reversible", "irreversible"][agent_id % 2]
        omegas, components = simulate_agent_trajectory(agent_id, N_STEPS, domain, action)
        all_omegas.append(omegas)
        all_components.append(components)

        freqs, power = compute_power_spectrum(omegas)
        peaks = find_peaks(freqs, power, n_peaks=3)
        all_peaks.extend(peaks)

    # Aggregate peak frequencies across all agents
    peak_freqs = [p[0] for p in all_peaks if p[2] < 100]  # Exclude very long periods
    if peak_freqs:
        peak_hist, peak_bins = np.histogram(peak_freqs, bins=20)
        dominant_bin = np.argmax(peak_hist)
        dominant_freq = (peak_bins[dominant_bin] + peak_bins[dominant_bin + 1]) / 2
        dominant_period = 1.0 / dominant_freq if dominant_freq > 0 else float('inf')

        print(f"\nDominant frequency across fleet: {dominant_freq:.4f} cycles/step")
        print(f"Dominant period: {dominant_period:.1f} steps")
        print(f"  = {dominant_period * 0.5:.1f} days (at 0.5 days/step)")

        # Show frequency distribution
        print(f"\nFrequency distribution (top peaks from {N_AGENTS} agents):")
        for i in range(len(peak_bins) - 1):
            if peak_hist[i] > 0:
                f_lo = peak_bins[i]
                f_hi = peak_bins[i + 1]
                period = 1.0 / ((f_lo + f_hi) / 2) if (f_lo + f_hi) > 0 else float('inf')
                bar = "█" * peak_hist[i]
                print(f"  f={f_lo:.3f}-{f_hi:.3f} (T={period:.1f}): {bar} ({peak_hist[i]})")

        # Check: is there a single dominant frequency or many?
        sorted_hist = sorted(peak_hist, reverse=True)
        if len(sorted_hist) >= 2 and sorted_hist[0] > 2 * sorted_hist[1]:
            print(f"\n  → SINGLE DOMINANT FREQUENCY detected at T={dominant_period:.1f} steps")
            print(f"  → This is the NATURAL FREQUENCY of the system")
            has_frequency = True
        else:
            print(f"\n  → Multiple frequencies present (no single dominant mode)")
            has_frequency = False
    else:
        print("\n  No significant peaks found")
        has_frequency = False
        dominant_period = 0

    # =====================================================================
    # 2. RESONANCE — Do the five axes oscillate in sync?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  2. RESONANCE")
    print("=" * 60)

    # For each agent, compute per-axis power spectra and check if they share frequencies
    axis_names = ["Decay", "Drift", "Trust", "Corruption", "Belief"]
    resonance_count = 0
    total_pairs = 0

    for agent_id in range(min(10, N_AGENTS)):
        comps = all_components[agent_id]
        axis_peaks = []
        for axis in range(5):
            signal = comps[:, axis]
            if np.std(signal) < 1e-6:
                axis_peaks.append([])
                continue
            freqs, power = compute_power_spectrum(signal)
            peaks = find_peaks(freqs, power, n_peaks=2)
            axis_peaks.append([p[0] for p in peaks])

        # Check if any two axes share a peak frequency (within 10%)
        for i in range(5):
            for j in range(i + 1, 5):
                total_pairs += 1
                for fi in axis_peaks[i]:
                    for fj in axis_peaks[j]:
                        if fi > 0 and fj > 0 and abs(fi - fj) / fi < 0.1:
                            resonance_count += 1

    resonance_ratio = resonance_count / max(total_pairs, 1)
    print(f"\nAxis resonance (shared frequencies between axes):")
    print(f"  Resonant pairs: {resonance_count} / {total_pairs} ({resonance_ratio*100:.1f}%)")

    if resonance_ratio > 0.3:
        print(f"  → STRONG RESONANCE: axes oscillate at the same frequencies")
        print(f"  → The five dimensions are coupled oscillators")
        has_resonance = True
    elif resonance_ratio > 0.1:
        print(f"  → WEAK RESONANCE: some coupling between axes")
        has_resonance = True
    else:
        print(f"  → NO RESONANCE: axes oscillate independently")
        has_resonance = False

    # =====================================================================
    # 3. PROPAGATION — Do disturbances travel between agents?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  3. WAVE PROPAGATION")
    print("=" * 60)

    # Compute coherence between agent pairs
    coherence_scores = []
    phase_delays = []

    for i in range(min(15, N_AGENTS)):
        for j in range(i + 1, min(15, N_AGENTS)):
            freqs, coh, phase = compute_cross_spectrum(all_omegas[i], all_omegas[j])
            # Average coherence in the dominant frequency band
            if has_frequency and dominant_period > 0:
                target_freq = 1.0 / dominant_period
                band = np.abs(freqs - target_freq) < 0.01
                if np.any(band):
                    band_coh = np.mean(coh[band])
                    band_phase = np.mean(phase[band])
                    coherence_scores.append(band_coh)
                    phase_delays.append(band_phase)

            # Also check broadband coherence
            mean_coh = np.mean(coh)
            coherence_scores.append(mean_coh)

    if coherence_scores:
        mean_coherence = np.mean(coherence_scores)
        max_coherence = np.max(coherence_scores)
        print(f"\nInter-agent coherence:")
        print(f"  Mean coherence: {mean_coherence:.4f}")
        print(f"  Max coherence:  {max_coherence:.4f}")

        if mean_coherence > 0.3:
            print(f"  → WAVES DETECTED: disturbances propagate between agents")
            has_wave = True
        elif mean_coherence > 0.1:
            print(f"  → WEAK COUPLING: some correlation but not clear wave propagation")
            has_wave = False
        else:
            print(f"  → NO PROPAGATION: agents oscillate independently")
            has_wave = False

        if phase_delays:
            mean_phase = np.mean(np.abs(phase_delays))
            print(f"  Mean phase delay: {mean_phase:.4f} radians ({mean_phase*180/np.pi:.1f}°)")
            if mean_phase > 0.1:
                # Compute wave speed: frequency × wavelength
                # wavelength ≈ phase delay / frequency
                print(f"  → Phase delay suggests a traveling wave, not a standing wave")
    else:
        has_wave = False
        print(f"  Insufficient data for coherence analysis")

    # =====================================================================
    # 4. HARMONICS — Are there higher modes?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  4. HARMONICS")
    print("=" * 60)

    # Check if peak frequencies are integer multiples of the fundamental
    if all_peaks:
        fundamental_candidates = sorted(set(p[0] for p in all_peaks if p[0] > 0.005))[:3]
        for fund in fundamental_candidates:
            harmonics = []
            for p in all_peaks:
                if p[0] > 0:
                    ratio = p[0] / fund
                    nearest_int = round(ratio)
                    if nearest_int >= 1 and abs(ratio - nearest_int) < 0.15:
                        harmonics.append((nearest_int, p[0], p[1]))
            if len(set(h[0] for h in harmonics)) >= 3:
                print(f"\n  Fundamental frequency: {fund:.4f} (T={1/fund:.1f} steps)")
                print(f"  Harmonics found:")
                for n, f, p in sorted(set(harmonics)):
                    print(f"    n={n}: f={f:.4f} (T={1/f:.1f}), power={p:.1f}")
                print(f"  → HARMONIC SERIES DETECTED")
                has_harmonics = True
                break
        else:
            print(f"  No clear harmonic series found")
            has_harmonics = False
    else:
        has_harmonics = False
        print(f"  No peaks to analyze")

    # =====================================================================
    # 5. INTERFERENCE — Do waves superpose?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  5. INTERFERENCE")
    print("=" * 60)

    # Compute the fleet-average omega and check if it shows constructive/destructive interference
    fleet_omega = np.mean(all_omegas, axis=0)
    individual_amplitudes = [np.std(o) for o in all_omegas]
    fleet_amplitude = np.std(fleet_omega)
    sum_amplitudes = np.mean(individual_amplitudes)

    print(f"\n  Mean individual amplitude: {sum_amplitudes:.2f}")
    print(f"  Fleet average amplitude:  {fleet_amplitude:.2f}")
    print(f"  Interference ratio: {fleet_amplitude / (sum_amplitudes + 1e-10):.4f}")

    if fleet_amplitude > 0.8 * sum_amplitudes:
        print(f"  → CONSTRUCTIVE INTERFERENCE: agents oscillate in phase")
        interference_type = "constructive"
    elif fleet_amplitude < 0.3 * sum_amplitudes:
        print(f"  → DESTRUCTIVE INTERFERENCE: agents oscillate out of phase (cancellation)")
        interference_type = "destructive"
    else:
        print(f"  → PARTIAL INTERFERENCE: some cancellation, some reinforcement")
        interference_type = "partial"

    # =====================================================================
    # 6. THE WAVE EQUATION
    # =====================================================================
    print("\n" + "=" * 60)
    print("  6. THE WAVE")
    print("=" * 60)

    print(f"""
  Frequency:     {'YES — T = ' + f'{dominant_period:.1f} steps ({dominant_period*0.5:.1f} days)' if has_frequency else 'no dominant frequency'}
  Resonance:     {'YES — axes coupled at shared frequencies' if has_resonance else 'NO — axes independent'}
  Propagation:   {'YES — coherent oscillation between agents' if has_wave else 'NO — agents independent'}
  Harmonics:     {'YES — integer multiples of fundamental' if has_harmonics else 'NO — no harmonic series'}
  Interference:  {interference_type}
""")

    if has_frequency and has_resonance:
        print(f"  THE SYSTEM OSCILLATES.")
        print(f"  Natural period: {dominant_period:.1f} steps = {dominant_period*0.5:.1f} days")
        print(f"  The heal cycle creates a driven oscillation on the Risk Polytope.")

        if has_wave:
            print(f"\n  THE WAVE EXISTS.")
            print(f"  Disturbances propagate between agents.")
            print(f"  The fleet is a coupled oscillator network.")
        else:
            print(f"\n  No wave propagation detected.")
            print(f"  Each agent oscillates independently — standing waves only.")

        if has_harmonics:
            print(f"\n  HARMONICS EXIST.")
            print(f"  The oscillation has overtones — the motion is not sinusoidal.")
            print(f"  The waveform is complex, decomposable into Fourier modes.")

        if interference_type == "destructive":
            print(f"\n  DESTRUCTIVE INTERFERENCE in the fleet average.")
            print(f"  Individual agents oscillate but the fleet average is stable.")
            print(f"  The fleet is self-stabilizing through phase diversity.")
        elif interference_type == "constructive":
            print(f"\n  CONSTRUCTIVE INTERFERENCE in the fleet average.")
            print(f"  Agents oscillate in sync — the fleet amplifies individual risk.")
            print(f"  This is dangerous: correlated oscillation can cause fleet-wide BLOCK.")

    else:
        print(f"  No clear wave behavior detected.")
        print(f"  The motion on the Risk Polytope is aperiodic or noise-dominated.")

    # Save results
    import json
    results = {
        "has_frequency": bool(has_frequency),
        "dominant_period_steps": float(dominant_period) if has_frequency else None,
        "dominant_period_days": float(dominant_period * 0.5) if has_frequency else None,
        "has_resonance": bool(has_resonance),
        "resonance_ratio": float(resonance_ratio),
        "has_wave": bool(has_wave),
        "mean_coherence": float(mean_coherence) if coherence_scores else None,
        "has_harmonics": bool(has_harmonics),
        "interference_type": interference_type,
        "fleet_amplitude": float(fleet_amplitude),
        "individual_amplitude": float(sum_amplitudes),
        "n_agents": N_AGENTS,
        "n_steps": N_STEPS,
    }
    with open("/tmp/the_wave.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved to /tmp/the_wave.json")


if __name__ == "__main__":
    main()
