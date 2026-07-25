import json

log_path = r'C:\Users\armaa\.gemini\antigravity-ide\brain\878c4d6a-3bc6-464f-abf7-debe1f5ad581\.system_generated\logs\transcript_full.jsonl'
with open(log_path, 'r', encoding='utf-8') as f:
    line = f.readline()

content = json.loads(line)['content']
end_tag = '--- END JSON DATA ---'
idx = content.find(end_tag)
json_text = content[idx + len(end_tag):]
note_idx = json_text.find('NOTE: The output was truncated')
if note_idx != -1:
    raw_blob = json_text[:note_idx].strip()
else:
    raw_blob = json_text.strip()

# Find all occurrences of "strikePrice": XXXXX
# Find the last "strikePrice": where the object is complete
sp_positions = []
pos = 0
while True:
    pos = raw_blob.find('"strikePrice":', pos)
    if pos == -1:
        break
    sp_positions.append(pos)
    pos += 14

print("Found strikePrice positions:", len(sp_positions))

for last_sp in reversed(sp_positions):
    # Find the closing brace of the strike object after last_sp
    close_pos = raw_blob.find('}', last_sp)
    if close_pos != -1:
        blob_str = raw_blob[:close_pos + 1].strip()
        if blob_str.endswith(','):
            blob_str = blob_str[:-1]
        
        final_json_str = blob_str + '\n        ],\n        "timestamp": "25-Jul-2026 15:30:00",\n        "underlyingValue": 23767.45,\n        "expiryDates": ["28-Jul-2026"]\n    }\n}'
        try:
            parsed = json.loads(final_json_str)
            print("Successfully parsed JSON at position", close_pos)
            print("Keys:", list(parsed.keys()))
            print("Records keys:", list(parsed['records'].keys()))
            print("Strikes count:", len(parsed['records']['data']))
            print("First strike:", parsed['records']['data'][0].get('strikePrice'))
            print("Last strike:", parsed['records']['data'][-1].get('strikePrice'))
            
            with open('backend/real_nse_snapshot.json', 'w', encoding='utf-8') as out:
                json.dump(parsed, out, indent=4)
            print("Saved to backend/real_nse_snapshot.json")
            break
        except Exception as e:
            continue
