# Optical Transfer

Transfer files from PC to iPhone using animated color grids displayed on screen and captured by the phone camera. No network, no server, no cloud — just light.

## How It Works

1. **Encoder** (PC) reads a file, compresses it, applies LT fountain codes + Reed-Solomon error correction, and outputs a standalone HTML transmitter
2. **Transmitter** (PC browser) displays animated color-grid frames on a canvas
3. **Receiver** (iPhone Safari) captures frames via camera, decodes them, verifies SHA-256, and offers the file for download

## Quick Start

### One-time setup: Receiver
The receiver needs HTTPS for camera access. Open this URL on your iPhone and bookmark it:

**https://curioushy.github.io/my-personal-hub/optical-transfer/receiver.html**

### Each transfer: Encoder + Transmitter

```bash
pip install reedsolo    # one-time dependency

python encoder.py myfile.pdf                    # default settings
python encoder.py photo.jpg --grid 32 --fps 20  # larger grid, faster
```

This outputs `transmitter.html`. Open it in your browser, point the iPhone at the screen, and press Start.

## Encoder Options

| Option | Default | Description |
|---|---|---|
| `--grid N` | 24 | Grid size N×N (16-48) |
| `--fps N` | 15 | Frames per second (1-30) |
| `--ecc N` | 20 | Reed-Solomon ECC % (5-50) |
| `--overhead F` | 1.5 | Fountain code overhead (1.1-3.0) |
| `--output PATH` | transmitter.html | Output filename |

## Performance

| Grid | FPS | ~100KB transfer time |
|---|---|---|
| 24×24 | 15 | ~70s |
| 32×32 | 15 | ~33s |
| 24×24 | 30 | ~35s |
| 32×32 | 30 | ~17s |

## Technical Details

- **Encoding:** 4-color cells (Black/Red/Green/Blue) = 2 bits per cell
- **Error correction:** Reed-Solomon per frame + LT fountain codes across frames
- **Detection:** Colored corner markers (Cyan/Magenta/Yellow/White) for homography
- **Verification:** SHA-256 end-to-end checksum
