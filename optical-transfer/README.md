# Optical Transfer

Transfer files from PC to iPhone using animated color grids displayed on screen and captured by the phone camera. No network, no server, no cloud — just light.

## How It Works

1. **Transmitter** (PC browser) — drop a file, adjust settings, hit Start. Frames are generated on the fly in JavaScript.
2. **Receiver** (iPhone Safari) — captures frames via camera, decodes them, verifies SHA-256, and offers the file for download.

## Quick Start

### Transmitter (PC)
Open this in your PC browser and drop a file:

**https://curioushy.github.io/my-personal-hub/optical-transfer/transmitter.html**

Or open `transmitter.html` locally via `file://` — no server needed.

### Receiver (iPhone)
Open this on your iPhone Safari and bookmark it:

**https://curioushy.github.io/my-personal-hub/optical-transfer/receiver.html**

### Transfer
1. Open the transmitter on your PC, drop a file, adjust settings
2. Open the receiver on your iPhone, tap Start Camera
3. Point the iPhone at the PC screen, hit Start on the transmitter
4. Wait for the progress bar to fill — green = done
5. Tap Download on the iPhone

## Alternative: Python Encoder

For batch/CLI use, `encoder.py` is also available. It pre-generates all frames into a standalone HTML file:

```bash
pip install reedsolo
python encoder.py myfile.pdf --grid 32 --fps 20
open transmitter.html
```

## Settings

| Setting | Default | Description |
|---|---|---|
| Grid size | 24x24 | Larger = more data/frame, harder at distance |
| FPS | 15 | Higher = faster, more missed frames |
| ECC % | 20 | Higher = more error correction, less payload |
| Overhead | 1.5x | More fountain symbols = higher decode probability |
| 2-Color B/W | off | 1 bit/cell instead of 2 — slower but far more robust |

**Safe Mode** (⛨ button): presets Grid=16, FPS=5, ECC=50%, Overhead=3x, 2-Color. Use when the camera struggles to decode at default settings.

## Performance

| Grid | FPS | ~100KB transfer time |
|---|---|---|
| 24x24 | 15 | ~70s |
| 32x32 | 15 | ~33s |
| 24x24 | 30 | ~35s |
| 32x32 | 30 | ~17s |

## Technical Details

- **Encoding:** 4-color cells (Black/Red/Green/Blue) = 2 bits/cell; or 2-color (Black/White) = 1 bit/cell
- **Error correction:** Reed-Solomon per frame + LT fountain codes across frames
- **Detection:** 3 colored corner markers (Cyan TL, Magenta TR, Yellow BL) — 3-point affine transform for perspective correction; 4-cell black border around grid for isolation
- **Verification:** SHA-256 end-to-end checksum
- **Zero dependencies:** Transmitter and receiver run entirely in-browser (pako for zlib only)
