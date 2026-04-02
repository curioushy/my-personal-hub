#!/usr/bin/env python3
"""
Optical Screen-to-Camera Transfer — Encoder (v2)

Reads a file, encodes it into animated color-grid frames using LT fountain
codes + Reed-Solomon, and outputs a standalone transmitter.html that can be
opened directly from the filesystem (file:// URL). No server required.

Usage:
    python encoder.py <file_path> [options]
    python encoder.py photo.jpg --grid 32 --fps 20
"""

import argparse
import base64
import hashlib
import json
import math
import os
import struct
import sys
import zlib
from pathlib import Path

try:
    import reedsolo
except ImportError:
    print("ERROR: reedsolo not installed. Run: pip install reedsolo")
    sys.exit(1)

# ─── Constants ────────────────────────────────────────────────────────────────

DATA_COLORS = [
    (0,   0,   0),    # 0 = Black
    (255, 0,   0),    # 1 = Red
    (0,   255, 0),    # 2 = Green
    (0,   0,   255),  # 3 = Blue
]

MARKER_COLORS = {
    'TL': (0,   255, 255),  # Cyan
    'TR': (255, 0,   255),  # Magenta
    'BL': (255, 255, 0),    # Yellow
    'BR': (255, 255, 255),  # White
}

FRAME_CONFIG = 0x00
FRAME_DATA   = 0x01
FRAME_END    = 0xFF

PRIM = 0x11D  # GF(256) primitive polynomial

# ─── xorshift32 PRNG (§3.3) ──────────────────────────────────────────────────

def xorshift32(state):
    if state == 0:
        state = 1
    state ^= (state << 13) & 0xFFFFFFFF
    state = state & 0xFFFFFFFF
    state ^= (state >> 17)
    state = state & 0xFFFFFFFF
    state ^= (state << 5) & 0xFFFFFFFF
    state = state & 0xFFFFFFFF
    return state

# ─── Robust Soliton Distribution (§3.4) ──────────────────────────────────────

def robust_soliton_cdf(K, c=0.1, delta=0.5):
    if K <= 1:
        return [(1, 1.0)]

    rho = [0.0] * (K + 1)
    rho[1] = 1.0 / K
    for i in range(2, K + 1):
        rho[i] = 1.0 / (i * (i - 1))

    S = c * math.log(K / delta) * math.sqrt(K)
    S = max(S, 1.0)
    pivot = max(1, round(K / S))

    tau = [0.0] * (K + 1)
    for i in range(1, min(pivot, K + 1)):
        tau[i] = S / (i * K)
    if pivot <= K:
        tau[pivot] = S * math.log(S / delta) / K

    total = sum(rho[i] + tau[i] for i in range(1, K + 1))
    cdf = []
    cumulative = 0.0
    for d in range(1, K + 1):
        prob = (rho[d] + tau[d]) / total
        if prob > 1e-10:
            cumulative += prob
            cdf.append((d, min(cumulative, 1.0)))
    if cdf:
        cdf[-1] = (cdf[-1][0], 1.0)
    return cdf

# ─── LT Symbol Generation (§3.5) ─────────────────────────────────────────────

def generate_symbol(i, K, blocks, block_size, cdf):
    # Step 1: Determine degree
    state = xorshift32(((i + 1) * 2654435761) & 0xFFFFFFFF)
    r = state / 0xFFFFFFFF
    degree = 1
    for (d, cum) in cdf:
        if r <= cum:
            degree = d
            break
    degree = min(degree, K)

    # Step 2: Select source blocks
    seed = ((i + 1) * 1103515245 + 12345) & 0xFFFFFFFF
    if seed == 0:
        seed = 1
    selected = set()
    state2 = seed
    attempts = 0
    while len(selected) < degree and attempts < degree * 10:
        state2 = xorshift32(state2)
        selected.add(state2 % K)
        attempts += 1

    # Step 3: XOR selected blocks
    symbol = bytearray(block_size)
    for idx in selected:
        blk = blocks[idx]
        for j in range(block_size):
            symbol[j] ^= blk[j]

    return bytes(symbol)

# ─── Frame Capacity (§2.5, §2.6) ─────────────────────────────────────────────

def compute_frame_params(grid_size, ecc_percent):
    N = grid_size
    data_cells = N * N - 36
    frame_bytes = data_cells // 4

    ecc_bytes = max(2, frame_bytes * ecc_percent // 100)

    if frame_bytes <= 255:
        rs_blocks = 1
        rs_total  = frame_bytes
        rs_ecc    = ecc_bytes
        rs_data   = frame_bytes - ecc_bytes
    else:
        rs_blocks = math.ceil(frame_bytes / 255)
        rs_total  = frame_bytes // rs_blocks
        rs_ecc    = ecc_bytes // rs_blocks
        rs_data   = rs_total - rs_ecc

    payload = rs_data * rs_blocks - 4  # 4-byte header
    return {
        'frame_bytes':         frame_bytes,
        'rs_blocks_per_frame': rs_blocks,
        'rs_total_per_block':  rs_total,
        'rs_ecc_per_block':    rs_ecc,
        'rs_data_per_block':   rs_data,
        'payload_per_frame':   payload,
    }

# ─── RS Encode ────────────────────────────────────────────────────────────────

def rs_encode_block(data_bytes, nsym):
    rs = reedsolo.RSCodec(nsym, fcr=0, prim=PRIM)
    return bytes(rs.encode(bytearray(data_bytes)))

def rs_encode_frame(raw_data, params):
    """RS-encode the raw data (header+payload) into frame_bytes."""
    n_blocks = params['rs_blocks_per_frame']
    data_per = params['rs_data_per_block']
    ecc_per  = params['rs_ecc_per_block']

    encoded = bytearray()
    for b in range(n_blocks):
        chunk = raw_data[b * data_per : (b + 1) * data_per]
        enc = rs_encode_block(chunk, ecc_per)
        encoded.extend(enc)
    return bytes(encoded)

# ─── Build Frame Raw Data ────────────────────────────────────────────────────

def build_frame_raw(frame_type, symbol_index, payload, params):
    total_data = params['rs_data_per_block'] * params['rs_blocks_per_frame']
    header = bytes([
        frame_type,
        (symbol_index >> 16) & 0xFF,
        (symbol_index >> 8)  & 0xFF,
        symbol_index & 0xFF,
    ])
    raw = header + payload
    if len(raw) < total_data:
        raw += b'\x00' * (total_data - len(raw))
    return raw[:total_data]

# ─── Grid Layout (§2.3) ──────────────────────────────────────────────────────

def is_marker(row, col, N):
    ms = 3
    if row < ms and col < ms:         return 'TL'
    if row < ms and col >= N - ms:    return 'TR'
    if row >= N - ms and col < ms:    return 'BL'
    if row >= N - ms and col >= N-ms: return 'BR'
    return None

# ─── Frame → RGB Grid (§2.4) ─────────────────────────────────────────────────

def frame_bytes_to_grid(frame_encoded, N):
    """Convert RS-encoded bytes → flat list of (r,g,b) for N×N grid."""
    # Unpack bytes to 2-bit cell values (MSB first)
    cells = []
    for byte in frame_encoded:
        cells.append((byte >> 6) & 3)
        cells.append((byte >> 4) & 3)
        cells.append((byte >> 2) & 3)
        cells.append(byte & 3)

    grid = []
    ci = 0
    for row in range(N):
        for col in range(N):
            m = is_marker(row, col, N)
            if m:
                grid.append(MARKER_COLORS[m])
            else:
                v = cells[ci] if ci < len(cells) else 0
                grid.append(DATA_COLORS[v])
                ci += 1
    return grid

def grid_to_b64(grid):
    flat = bytearray()
    for (r, g, b) in grid:
        flat.extend([r, g, b])
    return base64.b64encode(bytes(flat)).decode('ascii')

# ─── Encoding Pipeline (§5.3) ────────────────────────────────────────────────

def encode_file(file_path, grid_size=24, fps=15, ecc_percent=20, overhead=1.5):
    raw_data = Path(file_path).read_bytes()
    filename = Path(file_path).name
    file_size = len(raw_data)

    sha256_bytes = hashlib.sha256(raw_data).digest()
    sha256_hex = sha256_bytes.hex()

    compressed = zlib.compress(raw_data, 9)
    if len(compressed) < file_size:
        data = bytes([0x01]) + compressed
        is_compressed = True
        comp_pct = 100.0 * len(compressed) / file_size
    else:
        data = bytes([0x00]) + raw_data
        is_compressed = False
        comp_pct = None

    params = compute_frame_params(grid_size, ecc_percent)
    block_size = params['payload_per_frame']

    if block_size <= 0:
        print(f"ERROR: Grid {grid_size}×{grid_size} with {ecc_percent}% ECC has no payload capacity.")
        sys.exit(1)

    K = math.ceil(len(data) / block_size)
    padded = data + b'\x00' * (K * block_size - len(data))
    blocks = [padded[i * block_size:(i + 1) * block_size] for i in range(K)]

    cdf = robust_soliton_cdf(K)
    num_symbols = max(K + 10, int(K * overhead))

    # ── Config payload (§2.8) ────────────────────────────────────────────
    max_fn = max(0, block_size - 46)
    fn_bytes = filename.encode('utf-8')[:max_fn]

    config_payload = bytearray()
    config_payload.append(grid_size)          # 0: grid_size
    config_payload.append(4)                  # 1: num_colors
    config_payload.append(fps)                # 2: fps
    config_payload.append(ecc_percent)        # 3: ecc_percent
    config_payload += struct.pack('>I', file_size)   # 4-7: file_size
    config_payload += struct.pack('>H', K)           # 8-9: K
    config_payload += struct.pack('>H', block_size)  # 10-11: block_size
    config_payload += sha256_bytes                   # 12-43: sha256
    config_payload.append(0x01 if is_compressed else 0x00)  # 44: flags
    config_payload.append(len(fn_bytes))             # 45: filename_len
    config_payload += fn_bytes                       # 46+: filename
    config_payload = bytes(config_payload)

    # ── End payload (§2.8) ───────────────────────────────────────────────
    end_payload = sha256_bytes + struct.pack('>I', num_symbols)

    # ── Console output (§5.6) ────────────────────────────────────────────
    print(f"[+] File: {filename} ({file_size:,} bytes)")
    print(f"[+] SHA-256: {sha256_hex}")
    if is_compressed:
        print(f"[+] Compressed: {len(compressed):,} bytes ({comp_pct:.1f}%)")
    else:
        print(f"[+] Not compressed (incompressible)")
    print(f"[+] Grid: {grid_size}×{grid_size}, Payload/frame: {block_size} bytes")
    print(f"[+] Source blocks: {K}, Generating {num_symbols} fountain symbols")

    total_frames = fps + num_symbols + fps
    est_time = total_frames / fps
    print(f"[+] Total frames: {total_frames} (config: {fps}, data: {num_symbols}, end: {fps})")
    print(f"[+] Estimated transfer time: {est_time:.1f}s at {fps} fps")

    # ── Generate frames ──────────────────────────────────────────────────
    frames_b64 = []

    # Config frames
    for _ in range(fps):
        raw = build_frame_raw(FRAME_CONFIG, 0, config_payload, params)
        enc = rs_encode_frame(raw, params)
        grid = frame_bytes_to_grid(enc, grid_size)
        frames_b64.append(grid_to_b64(grid))

    # Data frames
    for i in range(num_symbols):
        if i % 100 == 0 and i > 0:
            print(f"    Encoding symbol {i}/{num_symbols}...", end='\r')
        symbol = generate_symbol(i, K, blocks, block_size, cdf)
        raw = build_frame_raw(FRAME_DATA, i, symbol, params)
        enc = rs_encode_frame(raw, params)
        grid = frame_bytes_to_grid(enc, grid_size)
        frames_b64.append(grid_to_b64(grid))
    if num_symbols > 100:
        print(f"    Encoding symbol {num_symbols}/{num_symbols} done.")

    # End frames
    for _ in range(fps):
        raw = build_frame_raw(FRAME_END, 0xFFFFFF, end_payload, params)
        enc = rs_encode_frame(raw, params)
        grid = frame_bytes_to_grid(enc, grid_size)
        frames_b64.append(grid_to_b64(grid))

    config_meta = {
        'grid_size':   grid_size,
        'fps':         fps,
        'ecc_percent': ecc_percent,
        'file_name':   filename,
        'file_size':   file_size,
        'sha256':      sha256_hex,
        'K':           K,
        'block_size':  block_size,
        'num_symbols': num_symbols,
        'config_count': fps,
        'data_count':   num_symbols,
        'end_count':    fps,
        'total_frames': total_frames,
    }
    return frames_b64, config_meta

# ─── Transmitter HTML Template (§5.5) ─────────────────────────────────────────

def build_transmitter_html(frames_b64, meta):
    frame_data_json = json.dumps({
        'config': meta,
        'frames': frames_b64,
    })

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Optical Transfer — Transmitter</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#111;color:#eee;font-family:-apple-system,monospace;display:flex;flex-direction:column;align-items:center;padding:16px;min-height:100vh}}
h1{{font-size:1.3em;color:#7cf;margin-bottom:12px}}
#info{{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}}
.ib{{background:#222;border-radius:6px;padding:10px 14px;min-width:120px;text-align:center}}
.ib .l{{font-size:.65em;color:#888;text-transform:uppercase;letter-spacing:1px}}
.ib .v{{font-size:1em;color:#fff;margin-top:2px}}
#canvas-wrap{{position:relative}}
canvas{{image-rendering:pixelated;image-rendering:crisp-edges;display:block;border:2px solid #333;border-radius:4px}}
#controls{{margin-top:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:center}}
button{{background:#3a7cd5;border:none;color:#fff;padding:8px 20px;border-radius:5px;cursor:pointer;font-size:.95em;font-family:inherit}}
button:hover{{background:#5a9cf5}}
button:disabled{{background:#444;cursor:default}}
#phase{{font-size:1.1em;font-weight:bold;color:#7cf;letter-spacing:2px;min-width:100px;text-align:center}}
#progress-wrap{{width:min(400px,90vw);background:#222;border-radius:4px;height:8px;overflow:hidden;margin-top:8px}}
#progress-bar{{height:100%;background:#3a7cd5;width:0%;transition:width .2s}}
#stats{{font-size:.78em;color:#888;margin-top:6px;text-align:center}}
.sz{{display:flex;align-items:center;gap:6px;font-size:.8em;color:#aaa}}
input[type=range]{{width:100px}}
#instructions{{max-width:500px;text-align:center;font-size:.8em;color:#999;margin-top:16px;line-height:1.5}}
</style>
</head>
<body>
<h1>Optical Transfer</h1>
<div id="info">
  <div class="ib"><div class="l">File</div><div class="v" id="i-file"></div></div>
  <div class="ib"><div class="l">Size</div><div class="v" id="i-size"></div></div>
  <div class="ib"><div class="l">Grid</div><div class="v" id="i-grid"></div></div>
  <div class="ib"><div class="l">FPS</div><div class="v" id="i-fps"></div></div>
  <div class="ib"><div class="l">ECC</div><div class="v" id="i-ecc"></div></div>
  <div class="ib"><div class="l">Blocks</div><div class="v" id="i-k"></div></div>
</div>
<div id="canvas-wrap"><canvas id="c"></canvas></div>
<div id="controls">
  <span id="phase">READY</span>
  <button id="btn-start">&#9654; Start</button>
  <button id="btn-pause" disabled>&#9208; Pause</button>
  <button id="btn-stop" disabled>&#9209; Stop</button>
  <div class="sz">
    Size: <input type="range" id="sz" min="200" max="1200" step="20" value="720">
    <span id="szl">720px</span>
  </div>
</div>
<div id="progress-wrap"><div id="progress-bar"></div></div>
<div id="stats"></div>
<div id="instructions">Open the decoder on your iPhone, point the camera at this screen, then press Start.</div>

<script>
const FRAME_DATA = {frame_data_json};
const CFG = FRAME_DATA.config;
const FRAMES = FRAME_DATA.frames;
const N = CFG.grid_size;
const TOTAL = CFG.total_frames;
const CFG_CNT = CFG.config_count;
const DATA_CNT = CFG.data_count;

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let displaySize = 720;

function setSize(s) {{
  displaySize = s;
  const cell = Math.floor(s / N);
  canvas.width = cell * N;
  canvas.height = cell * N;
}}
setSize(720);

function fmtB(b) {{
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(2) + ' MB';
}}

document.getElementById('i-file').textContent = CFG.file_name.length > 20 ? CFG.file_name.slice(0,18) + '...' : CFG.file_name;
document.getElementById('i-size').textContent = fmtB(CFG.file_size);
document.getElementById('i-grid').textContent = N + 'x' + N;
document.getElementById('i-fps').textContent = CFG.fps;
document.getElementById('i-ecc').textContent = CFG.ecc_percent + '%';
document.getElementById('i-k').textContent = CFG.K;

const szSlider = document.getElementById('sz');
const szLabel = document.getElementById('szl');
szSlider.oninput = () => {{ szLabel.textContent = szSlider.value + 'px'; setSize(+szSlider.value); }};

let fi = 0, loops = 0, running = false, paused = false, t0 = 0, timer = null;

function phaseOf(i) {{
  if (i < CFG_CNT) return 'CONFIG';
  if (i < CFG_CNT + DATA_CNT) return 'DATA';
  if (i < TOTAL) return 'END';
  return 'LOOPING';
}}

function renderFrame(idx) {{
  const raw = atob(FRAMES[idx]);
  const cell = Math.floor(displaySize / N);
  for (let r = 0; r < N; r++) {{
    for (let c = 0; c < N; c++) {{
      const base = (r * N + c) * 3;
      ctx.fillStyle = `rgb(${{raw.charCodeAt(base)}},${{raw.charCodeAt(base+1)}},${{raw.charCodeAt(base+2)}})`;
      ctx.fillRect(c * cell, r * cell, cell, cell);
    }}
  }}
}}

function tick() {{
  if (!running || paused) return;
  renderFrame(fi % TOTAL);
  const pct = Math.min(100, fi / TOTAL * 100);
  document.getElementById('progress-bar').style.width = pct + '%';
  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  document.getElementById('phase').textContent = phaseOf(fi % TOTAL);
  document.getElementById('stats').textContent =
    'Frame ' + (fi % TOTAL) + '/' + TOTAL + ' | Loop ' + loops + ' | ' + elapsed + 's';
  fi++;
  if (fi % TOTAL === 0) {{
    // Loop: jump back to first data frame (skip re-showing config)
    fi = CFG_CNT;
    loops++;
  }}
}}

document.getElementById('btn-start').onclick = () => {{
  if (running) return;
  running = true; paused = false; fi = 0; loops = 0; t0 = Date.now();
  document.getElementById('btn-start').disabled = true;
  document.getElementById('btn-pause').disabled = false;
  document.getElementById('btn-stop').disabled = false;
  szSlider.disabled = true;
  document.getElementById('instructions').style.display = 'none';
  timer = setInterval(tick, 1000 / CFG.fps);
}};

document.getElementById('btn-pause').onclick = () => {{
  if (!running) return;
  paused = !paused;
  document.getElementById('btn-pause').textContent = paused ? '\\u25B6 Resume' : '\\u23F8 Pause';
  document.getElementById('phase').textContent = paused ? 'PAUSED' : phaseOf(fi % TOTAL);
}};

document.getElementById('btn-stop').onclick = () => {{
  running = false; paused = false;
  if (timer) {{ clearInterval(timer); timer = null; }}
  document.getElementById('btn-start').disabled = false;
  document.getElementById('btn-pause').disabled = true;
  document.getElementById('btn-stop').disabled = true;
  document.getElementById('btn-pause').textContent = '\\u23F8 Pause';
  document.getElementById('phase').textContent = 'STOPPED';
  szSlider.disabled = false;
}};

// Preview first frame
renderFrame(0);
</script>
</body>
</html>
'''

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Optical Transfer Encoder — encodes a file into a standalone transmitter HTML.')
    p.add_argument('file', help='File to transmit')
    p.add_argument('--grid',     type=int,   default=24,   help='Grid size NxN (default: 24, range: 16-48)')
    p.add_argument('--fps',      type=int,   default=15,   help='Frame rate (default: 15, range: 1-30)')
    p.add_argument('--ecc',      type=int,   default=20,   help='RS ECC percentage (default: 20, range: 5-50)')
    p.add_argument('--overhead', type=float, default=1.5,  help='Fountain overhead ratio (default: 1.5)')
    p.add_argument('--output',   type=str,   default='transmitter.html', help='Output filename (default: transmitter.html)')
    args = p.parse_args()

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    fsize = os.path.getsize(args.file)
    if fsize > 10 * 1024 * 1024:
        print(f"Warning: File is {fsize / 1048576:.1f} MB — transfer will be slow.")
    if fsize == 0:
        print("ERROR: File is empty.")
        sys.exit(1)

    frames_b64, meta = encode_file(args.file, args.grid, args.fps, args.ecc, args.overhead)

    html = build_transmitter_html(frames_b64, meta)
    out_path = Path(args.output)
    out_path.write_text(html, encoding='utf-8')
    out_size = out_path.stat().st_size

    print(f"[+] Output: {args.output} ({out_size / 1048576:.1f} MB)")
    print(f"[+] Open {args.output} in your browser to begin.")

if __name__ == '__main__':
    main()
