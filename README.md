# Pan360 - 360° Panoramic Surveillance Camera

A Raspberry Pi-based automated panoramic camera system that captures 360° images using a stepper motor-controlled rotating platform.

## Hardware Requirements

- **Raspberry Pi 4** (or Zero WH)
- **Pi Camera Module** (V2, V3, or HQ)
- **28BYJ-48 Stepper Motor** with ULN2003 Driver Board
- **Power Supply** (5V for Pi and motor)
- **Mounting Hardware** (camera mount, motor platform)

## Hardware Setup

### Wiring Connections

**ULN2003 Driver to Raspberry Pi:**
| ULN2003 Pin | GPIO Pin (BCM) | Physical Pin |
|-------------|----------------|--------------|
| IN1         | GPIO 17        | Pin 11       |
| IN2         | GPIO 18        | Pin 12       |
| IN3         | GPIO 27        | Pin 13       |
| IN4         | GPIO 22        | Pin 15       |
| VCC (+)     | 5V             | Pin 2        |
| GND (-)     | Ground         | Pin 6        |

**Pi Camera Module:**
- Connect to the camera CSI port on the Raspberry Pi

### Physical Assembly

1. Mount the Pi Camera Module on a rotating platform
2. Attach the platform to the stepper motor shaft
3. Secure the motor to a stable base
4. Ensure the camera can rotate freely 360° without obstruction
5. Level the camera for horizontal panoramas

### ⚠️ Important: Nodal Point Alignment

**To prevent ghosting/parallax errors, the camera must rotate around its entrance pupil (nodal point).**

- **Nodal Point**: The optical center where light converges (~2-3mm behind lens front for Pi Camera V2)
- **Parallax**: When rotation axis ≠ nodal point, causing foreground/background misalignment
- **Solution**: Use adjustable mount to position camera so nodal point is on rotation axis

**Quick Test**: Place a close object and distant object in view. Rotate camera. If they shift relative to each other, adjust camera forward/backward until no relative movement occurs.

## Software Installation

### 1. Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Enable Camera

```bash
sudo raspi-config
# Navigate to: Interface Options -> Camera -> Enable
# Reboot if prompted
```

### 3. Install System Dependencies

```bash
# Install camera dependencies
sudo apt-get install -y python3-pip python3-picamera2

# Install Python libraries
sudo apt-get install -y python3-libcamera python3-kms++

# Install GPIO library
sudo apt-get install -y python3-rpi.gpio

# Install YAML parser
sudo apt-get install -y python3-yaml

# Install build dependencies (needed for picamera2)
sudo apt-get install -y libcap-dev
```

### 4. Install Python Requirements

**For Raspberry Pi OS Bookworm (2023+):**

```bash
cd ~/Works/Pan360

# Create a virtual environment with access to system packages
# (Required for libcamera access)
python3 -m venv --system-site-packages venv

# Activate the virtual environment
source venv/bin/activate

# Install requirements
pip3 install -r requirements.txt
```

**For older Raspberry Pi OS:**

```bash
cd ~/Works/Pan360
pip3 install -r requirements.txt
```

**Note:** Always activate the virtual environment before running the scripts:
```bash
source venv/bin/activate
```

### 5. Verify Camera

```bash
# Test camera
libcamera-still -o test.jpg

# If this works, you're ready to go!
```

## Configuration

Edit `config/config.yaml` to customize your setup:

### Motor Settings
```yaml
motor:
  gpio_pins: [17, 18, 27, 22]  # BCM pin numbers
  step_delay: 0.001             # Motor speed (lower = faster)
```

### Camera Settings
```yaml
camera:
  resolution: [3280, 2464]      # Image resolution
  exposure:
    time: 10000                  # Exposure time (µs)
    gain: 1.0                    # ISO gain
```

### Scan Settings
```yaml
scan:
  angle_increment: 15.0          # Degrees between shots
  settle_time: 0.8              # Vibration settling time
  clockwise: true               # Rotation direction
```

**Angle Increment Guidelines:**
- **10°**: High overlap, best quality, 36 images
- **15°**: Good overlap, balanced, 24 images
- **20°**: Minimal overlap, faster scan, 18 images
- **25°**: Current setting (15 images) - requires precise nodal alignment

## Usage

### Basic Scan

```bash
cd ~/Works/Pan360

# Activate virtual environment (if using one)
source venv/bin/activate

# Run the scanner
python3 src/pan360.py
```

### What Happens:

1. **Initialization**: Motor and camera are configured
2. **Scanning**: Camera rotates and captures images at each angle
3. **Progress**: Real-time updates show completion status
4. **Completion**: Returns to home position, displays summary

### Example Output:

```
============================================================
Pan360 - 360° Panoramic Camera System
============================================================

Loading configuration...
Configuration loaded from: config/config.yaml

------------------------------------------------------------
Initializing hardware...
------------------------------------------------------------

[Motor] Initializing stepper motor...
[Motor] GPIO Pins: [17, 18, 27, 22]
[Motor] Motor initialized successfully

[Camera] Initializing Pi Camera...
[Camera] Resolution: (3280, 2464)
Camera initialized successfully

============================================================
Starting Panoramic Scan
============================================================
Session ID: 20260120_143052
Total rotation: 360°
Angle increment: 25°
Number of images: 15
============================================================

Image 1/24
[Motor] Rotating to 0.00°...
[Camera] Settling for 0.8s...
Capturing image at angle 0.00°...
Saved: images/pan360_20260120_143052_angle_000.00.jpg

...

============================================================
Scan Complete!
============================================================
Total images captured: 15
Total time: 93.5s (1.6 minutes)
Images saved to: images/
============================================================
```

## Workflow Overview

Pan360 supports **two workflows** for creating panoramas:

```
┌─────────────────────────────────────────────────────────┐
│  WORKFLOW 1: Hybrid (Pi Capture + PC/Server Stitching) │
│  ────────────────────────────────────────────────────── │
│  1. Pi captures images                                  │
│  2. Pi uploads to server                                │
│  3. Server stitches using AI algorithms                 │
│  4. Pi downloads result                                 │
│  ✓ Fast on Pi, powerful processing on PC                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  WORKFLOW 2: Local (All on Raspberry Pi)                │
│  ────────────────────────────────────────────────────── │
│  1. Pi captures images                                  │
│  2. Pi stitches locally                                 │
│  3. Result saved on Pi                                  │
│  ⚠ Slower, limited by Pi CPU                           │
└─────────────────────────────────────────────────────────┘
```

## Workflow 1: Hybrid Pi-PC Stitching (Recommended)

This workflow lets the Pi focus on capturing while offloading intensive stitching to a more powerful PC/server.

### Prerequisites

1. **PC/Server Setup**: See [README_SERVER.md](README_SERVER.md) for detailed instructions
2. **Network**: Pi and PC on same network (or port forwarding configured)
3. **Server Running**: Stitching server must be active on PC

### Quick Start

#### 1. Start Server on PC/Windows:
```bash
cd C:\Works\Pan360\server
python stitching_server.py --host 0.0.0.0 --port 8000
```

#### 2. Configure Pi to Use Server:

**Option A: Edit config.yaml (persistent)**
```yaml
server:
  enabled: true
  url: "http://192.168.5.138:8000"  # Your PC's IP
  algorithm: "simple_angle"
  auto_download: true
  output_dir: "output"
```

**Option B: Use command-line flags (temporary)**
```bash
# No configuration needed
```

#### 3. Run Capture on Pi:

```bash
cd ~/Works/Pan360
source venv/bin/activate

# With config.yaml server.enabled: true
python src/pan360.py

# OR use --upload flag
python src/pan360.py --upload --server http://192.168.5.138:8000
```

#### 4. Automatic Process:
```
[Pi] Capturing images...          ████████████ (30s)
[Pi] Uploading to server...       ████████████ (15s)
[Server] Stitching panorama...    ████████████ (120s)
[Pi] Downloading result...        ████████████ (5s)
✓ Panorama saved to output/panorama_remote_20260126_143052.jpg
```

### Manual Upload (Optional)

Upload existing images without new capture:

```bash
# Auto-discover images in images/ directory
python src/upload_client.py

# Or specify images explicitly
python src/upload_client.py images/angle_*.jpg --server http://192.168.5.138:8000
```

### Available Stitching Algorithms

| Algorithm | Description | Speed | Quality | Recommended |
|-----------|-------------|-------|---------|-------------|
| **simple_angle** | Geometric placement using known angles | Fast | Excellent | ✓ Yes |
| **opencv_auto** | OpenCV automatic stitcher | Medium | Good | For testing |
| **manual** | Feature-based manual pipeline | Slow | Variable | For research |

Change algorithm:
```bash
python src/pan360.py --upload --algorithm opencv_auto
```

### Monitor Server

View API documentation at: **http://192.168.5.138:8000/docs**

Check server health:
```bash
curl http://192.168.5.138:8000/health
```

---

## Workflow 2: Local Stitching on Pi

Stitch directly on Raspberry Pi without a server.

### Prerequisites

Install OpenCV on Pi:
```bash
source venv/bin/activate
pip install opencv-python opencv-contrib-python
```

### Process

#### 1. Capture Images:
```bash
python src/pan360.py
# Images saved to images/angle_000.jpg ... angle_350.jpg
```

#### 2. Stitch Locally:
```bash
# Compare all algorithms
python src/stitch_compare.py

# Or use specific stitcher
python -c "
from stitching import SimpleAngleStitcher
from pathlib import Path

images = sorted(Path('images').glob('angle_*.jpg'))
stitcher = SimpleAngleStitcher()
pano, stats = stitcher.stitch([str(i) for i in images])
stitcher.save_result(pano, 'output/panorama_local.jpg')
"
```

#### 3. Result:
```
✓ Panorama saved to output/panorama_local.jpg
⚠ Processing time: ~120-300s (depending on Pi model)
```

### Third-Party Stitching Software

Transfer images to PC and use:

**Free Options:**
- **Hugin** (Linux/Windows/Mac) - Professional, open-source
- **Microsoft ICE** (Windows) - Easy to use

**Commercial:**
- **PTGui** (Windows/Mac) - Industry standard
- **Autopano** - Legacy but powerful

---

## Workflow Comparison

| Feature | Hybrid (Pi+PC) | Local (Pi Only) |
|---------|----------------|-----------------|
| **Setup Complexity** | Medium | Simple |
| **Capture Speed** | Fast | Fast |
| **Stitching Speed** | Fast (PC) | Slow (Pi CPU) |
| **Quality** | High | High |
| **Pi CPU Usage** | Low | High |
| **Network Required** | Yes | No |
| **Best For** | Production use | Testing, offline |

---

## Quick Reference Commands

### Hybrid Workflow
```bash
# Start server (on PC)
cd C:\Works\Pan360\server
python stitching_server.py

# Capture and upload (on Pi)
python src/pan360.py --upload --server http://192.168.5.138:8000
```

### Local Workflow
```bash
# Capture (on Pi)
python src/pan360.py

# Stitch (on Pi)
python src/stitch_compare.py
```

### Manual Upload
```bash
# Upload existing images
python src/upload_client.py
```

## Troubleshooting

### Camera Not Detected

```bash
# Check camera connection
libcamera-hello

# If error, check:
# 1. Cable connection to CSI port
# 2. Camera is enabled in raspi-config
# 3. Camera is not locked by another process
```

### Motor Not Moving

1. Check wiring connections
2. Verify GPIO pin numbers in config
3. Test motor independently:

```python
from src.stepper_motor import StepperMotor

motor = StepperMotor([17, 18, 27, 22])
motor.rotate_angle(90)  # Should rotate 90°
motor.cleanup()
```

### Images Are Blurry

- Increase `settle_time` in config (try 1.0-1.5s)
- Reduce motor speed (increase `step_delay`)
- Ensure camera is firmly mounted

### Stitching Fails

- Use smaller `angle_increment` for more overlap
- Ensure consistent lighting across all captures
- Check that images are sharp and well-focused
- Manually adjust exposure settings if needed

### Ghosting / Parallax Artifacts

**Symptom:** Double images, misaligned overlaps

**Cause:** Camera not rotating around nodal point

**Solutions:**
1. Adjust camera position on mount (forward/backward)
2. Test with close + distant objects until no parallax
3. Increase overlap: use 15° or 10° angle increment
4. Keep subjects >3m away to minimize parallax effects

## Advanced Usage

### Custom Scan Angles

Modify the configuration to scan specific angles:

```yaml
scan:
  angle_increment: 10.0
  total_angle: 180.0  # Half panorama
```

### Manual Camera Control

```python
from src.camera_controller import CameraController

camera = CameraController()
camera.initialize()

# Adjust exposure
camera.set_exposure(exposure_time=20000, gain=2.0)

# Capture
camera.capture(angle=0, session_id="custom")

camera.close()
```

### Test Individual Components

```bash
# Test motor only
python3 -c "from src.stepper_motor import StepperMotor; m = StepperMotor([17,18,27,22]); m.rotate_angle(360); m.cleanup()"

# Test camera only
python3 -c "from src.camera_controller import CameraController; c = CameraController(); c.initialize(); c.capture(0, 'test'); c.close()"
```

## Project Structure

```
Pan360/
├── config/
│   └── config.yaml              # Configuration file
├── images/                      # Captured images (auto-created)
├── output/                      # Stitched panoramas (auto-created)
├── src/
│   ├── pan360.py               # Main capture application
│   ├── stepper_motor.py        # Motor controller
│   ├── camera_controller.py    # Camera controller
│   ├── config.py               # Config loader
│   ├── upload_client.py        # Upload client for hybrid workflow
│   ├── check_server.py         # Server status checker
│   ├── stitch_compare.py       # Local stitching comparison tool
│   └── stitching/              # Stitching algorithms
│       ├── base_stitcher.py            # Abstract base class
│       ├── simple_angle_stitcher.py    # Angle-based (recommended)
│       ├── opencv_auto_stitcher.py     # OpenCV automatic
│       └── manual_stitcher.py          # Manual pipeline
├── server/                      # PC/Server components
│   ├── stitching_server.py     # REST API server
│   └── requirements.txt        # Server dependencies
├── requirements.txt             # Pi dependencies
├── README.md                   # Main documentation (this file)
└── README_SERVER.md            # Server setup guide
```

## Tips for Best Results

1. **Nodal Point Alignment** (Critical for quality):
   - Camera must rotate around entrance pupil to prevent ghosting
   - Test: no relative movement between close/distant objects when rotating
   - Use adjustable mount for precise positioning

2. **Lighting**: Use consistent lighting, avoid sunlight changes during scan

3. **Focus**: Lock focus for all images

4. **Overlap**: 30-50% overlap (15-20° angle increment)

5. **Stability**: Stable mount, adequate settle_time (0.8-1.5s)

6. **Distance**: Keep subjects >3m away to minimize parallax

7. **Algorithm**: Use `simple_angle` for motorized panoramas with known angles

## License

This project is open-source. Feel free to modify and adapt for your needs.

## Contributing

Contributions welcome! Areas for improvement:
- Automatic exposure bracketing
- Real-time preview
- Web interface for control
- Video mode for time-lapse panoramas
- Support for vertical (multi-row) panoramas

## Support

For issues or questions, please open an issue on the project repository.

---

**Happy Panorama Shooting! 📸**
