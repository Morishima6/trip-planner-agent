import sys
sys.stdout.reconfigure(encoding='utf-8')

for fname in ['e:/intern/projects/trip-planner-agent/.env', 'e:/intern/projects/trip-planner-agent/.env.example']:
    with open(fname, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8')
    # Check for emoji bytes
    for i, b in enumerate(raw):
        if b > 0x80:
            if b & 0xF8 == 0xF0:  # 4-byte (emoji)
                seq = raw[i:i+4]
                print(f"{fname} @ {i}: {[hex(x) for x in seq]} -> U+{ord(seq.decode('utf-8')):04X}")
