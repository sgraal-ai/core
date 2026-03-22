from scoring_engine import compute, MemoryEntry

entries = [
    MemoryEntry(
        id="entry_001",
        content="Budapest office: Váci út 47, open 9-18",
        type="tool_state_memory",
        timestamp_age_days=94,
        source_trust=0.9,
        source_conflict=0.1,
        downstream_count=4,
    ),
    MemoryEntry(
        id="entry_002",
        content="Kovács Péter: +36 20 123 4567",
        type="preference_memory",
        timestamp_age_days=12,
        source_trust=0.95,
        source_conflict=0.45,
        downstream_count=2,
    ),
]

result = compute(entries, action_type="irreversible", domain="fintech")

print(f"Ω_MEM final:  {result.omega_mem_final}")
print(f"Decision:     {result.recommended_action}")
print(f"Assurance:    {result.assurance_score}")
print(f"Why:          {result.explainability_note}")
print(f"Components:   {result.component_breakdown}")
