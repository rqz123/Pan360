# Pan360 Quick Start Guide

## ✅ Installation Complete!

You've successfully installed the Pan360 system. Here's what's ready:

### What We've Set Up

- ✅ Virtual environment with system package access
- ✅ All Python dependencies installed
- ✅ Camera detected: OV5647 (Pi Camera V2)
- ✅ Motor controller ready
- ✅ Configuration files in place

## 🎯 Next Steps

### 1. Wire Your Hardware

**Connect the ULN2003 Stepper Motor Driver:**

| Driver Pin | Pi GPIO | Physical Pin |
|------------|---------|--------------|
| IN1        | GPIO 17 | Pin 11       |
| IN2        | GPIO 18 | Pin 12       |
| IN3        | GPIO 27 | Pin 13       |
| IN4        | GPIO 22 | Pin 15       |
| VCC (+)    | 5V      | Pin 2        |
| GND (-)    | Ground  | Pin 6        |

**Camera:** Already connected to CSI port ✅

### 2. Test the Motor

```bash
cd ~/Works/Pan360
source venv/bin/activate
python3 src/test_motor.py
```

This will:
- Rotate 90° clockwise
- Rotate 90° counter-clockwise
- Complete a full 360° rotation
- Return to home position

### 3. Run Your First Panoramic Scan

```bash
cd ~/Works/Pan360
source venv/bin/activate
python3 src/pan360.py
```

**Default Settings:**
- 24 images (15° increments)
- 360° total rotation
- 0.8s settle time per capture
- Fixed exposure for consistent stitching

### 4. Customize Your Scan

Edit `config/config.yaml`:

```yaml
scan:
  angle_increment: 10.0    # More images, better quality
  total_angle: 360.0       # Full 360° panorama
  settle_time: 1.0         # Increase if images are blurry
```

**Angle Recommendations:**
- **10°** = 36 images, highest quality, ~5-7 minutes
- **15°** = 24 images, good quality, ~3-4 minutes (default)
- **20°** = 18 images, faster scan, ~2-3 minutes

## 📸 Creating Your Panorama

After capturing images:

### Option 1: Hugin (Recommended)

```bash
sudo apt-get install hugin
hugin
```

1. Load images from `images/` directory
2. Auto-align images
3. Optimize and stitch
4. Export final panorama

### Option 2: Python OpenCV

```python
import cv2
import glob

# Load images
images = []
for filename in sorted(glob.glob('images/pan360_*_angle_*.jpg')):
    img = cv2.imread(filename)
    images.append(img)

# Stitch panorama
stitcher = cv2.Stitcher.create()
status, pano = stitcher.stitch(images)

if status == cv2.Stitcher_OK:
    cv2.imwrite('panorama.jpg', pano)
```

## 🔧 Troubleshooting

### Camera Issues

**"No module named 'libcamera'"**
- Already fixed! We're using `--system-site-packages` venv

**Images are dark/overexposed**
```yaml
# Edit config/config.yaml
camera:
  exposure:
    time: 20000  # Increase for brighter
    gain: 1.5    # Increase for brighter
```

**Images are blurry**
```yaml
scan:
  settle_time: 1.5  # Increase settling time
```

### Motor Issues

**Motor doesn't move**
1. Check wiring connections
2. Verify GPIO pins in config match your wiring
3. Test with: `python3 src/test_motor.py`

**Motor skips steps (jerky movement)**
```yaml
motor:
  step_delay: 0.002  # Increase for slower, smoother rotation
```

## 💡 Pro Tips

1. **Lighting**: Avoid direct sunlight changes during scan
2. **Stability**: Mount on tripod or stable surface
3. **Height**: Position at eye level for best results
4. **Overlap**: 30-50% overlap between images is ideal
5. **Test First**: Do a quick 180° test scan before full 360°

## 📁 Project Structure

```
Pan360/
├── config/
│   └── config.yaml       # Your settings
├── images/               # Captured images go here
│   └── pan360_YYYYMMDD_HHMMSS_angle_XXX.XX.jpg
├── src/
│   ├── pan360.py        # Main application
│   ├── test_motor.py    # Motor testing
│   └── test_camera.py   # Camera testing
└── venv/                # Virtual environment
```

## 🚀 Ready to Scan!

Your system is fully configured. Start with a test scan:

```bash
source venv/bin/activate
python3 src/pan360.py
```

Happy panorama shooting! 📸🌍
