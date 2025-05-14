#!/usr/bin/env python3
"""
Migrate trusted commands from full commands to base commands.
Run this once after updating the code.
"""
import os
import json
from pathlib import Path

# Path to preferences file
prefs_file = Path(os.path.expanduser("~/.angela/preferences.json"))

# Load current preferences
with open(prefs_file, "r") as f:
    prefs = json.load(f)

# Extract all full commands
full_commands = prefs.get("trust", {}).get("trusted_commands", [])
print(f"Found {len(full_commands)} trusted commands")

# Extract base commands
base_commands = set()
for cmd in full_commands:
    parts = cmd.split()
    if parts:
        base_cmd = parts[0]
        base_commands.add(base_cmd)
        print(f"Full command: '{cmd}' → Base command: '{base_cmd}'")

# Replace with base commands
prefs["trust"]["trusted_commands"] = sorted(list(base_commands))
print(f"\nNew trusted commands list: {prefs['trust']['trusted_commands']}")

# Save updated preferences
with open(prefs_file, "w") as f:
    json.dump(prefs, f, indent=2)

print(f"Updated {prefs_file} with {len(base_commands)} base commands")
