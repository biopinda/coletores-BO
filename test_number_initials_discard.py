"""Test script to verify number+initials pattern detection"""

import re

# Test cases from user report
test_cases = [
    "1214, I.E.S.",
    "1215, I.E.S.",
    "1216, M.E.",
    "1217, I.E.S.",
    "1218, I.E.S.",
    "12196, M.B.",
    "1220, B.F.",
    "1222, I.E.S.",
    "1253, M.F.C.",
    "1254, M.F.C.",
    # Valid names that should NOT be discarded
    "Silva, I.E.S.",
    "Santos, M.E.",
    "Andrade, M.B.",
]

# Pattern from normalizer.py
pattern = r'^\d+\s*[,;-]\s*[A-Z]\.(?:[A-Z]\.)*\s*$'

print("Testing number+initials pattern detection:\n")
print(f"Pattern: {pattern}\n")

for test in test_cases:
    matches = bool(re.search(pattern, test))
    should_discard = "DISCARD X" if matches else "KEEP OK"
    print(f"{should_discard:15} | {test}")

print("\n" + "="*50)
print("\nExpected behavior:")
print("- Lines starting with numbers + initials: DISCARD")
print("- Lines with surname + initials: KEEP")
