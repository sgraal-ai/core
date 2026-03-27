"""Migrate from Mem0 to mem0-sgraal in 5 minutes.

Before:  from mem0 import Memory
After:   from mem0_sgraal import SafeMemory
"""
# Step 1: Install
# pip install mem0-sgraal

# Step 2: Replace import (1 line change)
# from mem0 import Memory          # OLD
# from mem0_sgraal import SafeMemory as Memory  # NEW

# Step 3: Add API key
import os
# memory = SafeMemory(
#     api_key=os.environ["SGRAAL_API_KEY"],
#     on_block="warn",  # or "raise", "skip", "heal"
# )

# Step 4: Use exactly as before
# results = memory.search("user preferences")
# memory.add("User prefers dark mode", user_id="u1")

print("Migration complete! Every search() call now runs Sgraal preflight automatically.")
print("See https://sgraal.com/docs for full documentation.")
