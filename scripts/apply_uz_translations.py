# -*- coding: utf-8 -*-
"""Apply Uzbek translations from translation_pairs.json to LanguageContext.tsx"""
import json
import re

with open('translation_pairs.json', encoding='utf-8') as f:
    pairs = json.load(f)

def norm(s):
    return s.replace('\u0451', '\u0435').replace('\u0401', '\u0415')  # ё -> e

ru_to_uz = {}
for row in pairs[1:]:
    ru, uz = row[0].strip(), row[1].strip()
    if ru and uz:
        ru_to_uz[ru] = uz
        ru_to_uz[ru.lower()] = uz
        n = norm(ru)
        ru_to_uz[n] = uz
        ru_to_uz[n.lower()] = uz

with open('apps/web/src/contexts/LanguageContext.tsx', encoding='utf-8') as f:
    content = f.read()

# Parse 'key': 'value' lines (handles escaped quotes in value)
def parse_entries(text):
    entries = {}
    pattern = r"'([^']+)':\s*'((?:[^'\\]|\\.)*)'"
    for m in re.finditer(pattern, text):
        entries[m.group(1)] = m.group(2).replace('\\\'', "'")
    return entries

# Find ru and uz blocks by splitting
idx_ru = content.find("  ru: {")
idx_uz = content.find("  uz: {")
if idx_ru == -1 or idx_uz == -1:
    raise SystemExit("Blocks not found")

# Extract block content (from { to }; for uz we need until "  }," before "};")
def extract_block(content, start_marker):
    start = content.find(start_marker)
    if start == -1:
        return None, None
    start = content.find('{', start) + 1
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
        i += 1
    return content[start:i-1], i

ru_block, _ = extract_block(content, "  ru: {")
uz_block, uz_end = extract_block(content, "  uz: {")

ru_entries = parse_entries(ru_block)
uz_entries = parse_entries(uz_block)

def find_uz(russian):
    if not russian:
        return None
    r = russian.strip()
    rn = norm(r)
    if r in ru_to_uz:
        return ru_to_uz[r]
    if rn in ru_to_uz:
        return ru_to_uz[rn]
    if r.lower() in ru_to_uz:
        return ru_to_uz[r.lower()]
    if rn.lower() in ru_to_uz:
        return ru_to_uz[rn.lower()]
    # Prefix match: longest Excel phrase that is prefix of app phrase (normalized)
    best_len, best_uz = 0, None
    for excel_ru, uz in ru_to_uz.items():
        if len(excel_ru) < 4:  # skip very short to avoid "Загрузить" matching "Загрузить отчёты"
            continue
        if rn.startswith(norm(excel_ru)) and len(excel_ru) > best_len:
            best_len, best_uz = len(excel_ru), uz
    return best_uz

# For every key, set uz[key] = find_uz(ru[key]) when found
updates = {}
for key in uz_entries:
    ru_val = ru_entries.get(key)
    new_val = find_uz(ru_val) if ru_val else None
    if new_val is not None:
        updates[key] = new_val

with open('uz_updates.json', 'w', encoding='utf-8') as f:
    json.dump(updates, f, ensure_ascii=False, indent=2)
print("Total keys with match from Excel:", len(updates))
# Show only changed
changed = {k: v for k, v in updates.items() if v != uz_entries.get(k)}
print("Changed (old != new):", len(changed))
for k, v in list(changed.items())[:25]:
    print(k, "->", v[:60] if len(v) > 60 else v)
