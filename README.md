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
Angle increment: 15°
Number of images: 24
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
Total images captured: 24
Total time: 156.3s (2.6 minutes)
Images saved to: images/
============================================================
```

## Creating the Panorama

After capturing images, use stitching software:

### Option 1: Hugin (Free, Recommended)

```bash
# Install Hugin
sudo apt-get install hugin

# Launch Hugin
hugin
```

1. Load all images from the session
2. Create control points (auto-align)
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

# Stitch
stitcher = cv2.Stitcher.create()
status, panorama = stitcher.stitch(images)

if status == cv2.Stitcher_OK:
    cv2.imwrite('panorama.jpg', panorama)
    print("Panorama created successfully!")
else:
    print("Stitching failed")
```

### Option 3: Commercial Software

- **PTGui** (Windows/Mac) - Professional results
- **Microsoft ICE** (Windows) - Free, easy to use
- **Autopano** - Legacy but powerful

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
│   └── config.yaml          # Configuration file
├── images/                  # Captured images (auto-created)
├── src/
│   ├── pan360.py           # Main application
│   ├── stepper_motor.py    # Motor controller
│   ├── camera_controller.py # Camera controller
│   └── config.py           # Config loader
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Tips for Best Results

1. **Lighting**: Use consistent lighting, avoid direct sunlight changes
2. **Focus**: Lock focus for all images (manual focus mode)
3. **Exposure**: Use manual exposure to maintain brightness
4. **Overlap**: 30-50% overlap between images works best
5. **Stability**: Mount on a stable, level surface
6. **Height**: Position at average eye level for best perspective

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
