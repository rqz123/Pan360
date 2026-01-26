# Pan360 Server Setup Guide

## Overview

The Pan360 server is a REST API service that receives images from Raspberry Pi clients and performs panorama stitching using various algorithms. This hybrid approach allows the Pi to focus on image capture while offloading computationally intensive AI stitching to a more powerful PC or server.

## Architecture

```
┌─────────────────┐         Upload Images         ┌─────────────────┐
│  Raspberry Pi   │ ──────────────────────────────>│  PC/Server      │
│  (Pan360 Client)│                                │  (Stitching API)│
│                 │ <────────────────────────────  │                 │
│  - Capture      │   Download Panorama Result     │  - AI Stitching │
│  - Upload       │                                │  - GPU/CPU      │
└─────────────────┘                                └─────────────────┘
```

## System Requirements

### Server/PC Requirements
- **OS**: Linux, macOS, or Windows
- **Python**: 3.8 or later
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 10GB+ free space for uploaded images and results
- **CPU**: Multi-core processor (or GPU for future AI algorithms)
- **Network**: Accessible to Raspberry Pi (same LAN or port forwarding)

### Raspberry Pi Requirements
- Already configured Pan360 system
- Network connectivity to server
- Python `requests` library installed

## Installation

### 1. Server Setup

#### Clone Repository (if not already)
```bash
git clone https://github.com/rqz123/Pan360.git
cd Pan360
```

#### Install Server Dependencies
```bash
cd server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Verify Installation
```bash
python stitching_server.py --help
```

### 2. Configuration

The server reads stitching algorithms from `../src/stitching/` directory. Ensure the main Pan360 code is present.

### 3. Start the Server

#### Development Mode (with auto-reload)
```bash
python stitching_server.py --reload
```

#### Production Mode
```bash
python stitching_server.py --host 0.0.0.0 --port 8000
```

Options:
- `--host`: IP address to bind (default: 0.0.0.0 = all interfaces)
- `--port`: Port number (default: 8000)
- `--reload`: Enable auto-reload for development

#### Using uvicorn directly
```bash
uvicorn stitching_server:app --host 0.0.0.0 --port 8000
```

#### Run as background service (Linux)
```bash
# Using nohup
nohup python stitching_server.py > server.log 2>&1 &

# Using systemd (recommended for production)
# Create /etc/systemd/system/pan360-server.service
```

### 4. Firewall Configuration

Allow incoming connections on port 8000:

**Linux (UFW)**
```bash
sudo ufw allow 8000/tcp
```

**Linux (iptables)**
```bash
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

**Windows Firewall**
```powershell
New-NetFirewallRule -DisplayName "Pan360 Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

## Raspberry Pi Client Setup

### 1. Install Dependencies
```bash
cd /home/rzhang/Works/Pan360
source venv/bin/activate
pip install requests
```

### 2. Configure Server in config.yaml
```yaml
server:
  enabled: true  # Enable remote stitching
  url: "http://192.168.1.100:8000"  # Replace with your server IP
  timeout: 300
  algorithm: "simple_angle"
  parameters:
    blend_width: 100
  auto_download: true
  output_dir: "output"
```

### 3. Test Connection
```bash
# Test from Pi to server
python src/upload_client.py images/*.jpg --server http://192.168.1.100:8000
```

## Usage

### From Raspberry Pi

#### Capture and Upload Automatically
```bash
# With config.yaml server.enabled: true
python src/pan360.py

# Or override with command line
python src/pan360.py --upload
python src/pan360.py --upload --server http://192.168.1.100:8000
python src/pan360.py --upload --algorithm opencv_auto
```

#### Upload Existing Images
```bash
python src/upload_client.py images/*.jpg \
  --server http://192.168.1.100:8000 \
  --output panorama.jpg \
  --algorithm simple_angle
```

### Server API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### List Available Algorithms
```bash
curl http://localhost:8000/api/v1/algorithms
```

#### Upload Images (manual)
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "algorithm=simple_angle"
```

#### Check Job Status
```bash
curl http://localhost:8000/api/v1/status/{job_id}
```

#### Download Result
```bash
curl http://localhost:8000/api/v1/download/{job_id} -o panorama.jpg
```

#### List All Jobs
```bash
curl http://localhost:8000/api/v1/jobs
```

## API Documentation

Once the server is running, access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Stitching Algorithms

### 1. Simple Angle Stitcher (Recommended)
- Uses known camera angles for geometric placement
- Fast and reliable for motorized panoramas
- No feature matching required
- **Best for**: Pan360 with precise motor control

### 2. OpenCV Auto Stitcher
- High-level OpenCV stitcher API
- Automatic feature detection and matching
- May fail on 360° panoramas
- **Best for**: General panoramas with overlap

### 3. Manual Pipeline Stitcher
- Full control over stitching steps
- Feature detection, matching, homography
- More parameters to tune
- **Best for**: Experimentation and research

## Monitoring and Maintenance

### View Server Logs
```bash
# If using nohup
tail -f server.log

# If using systemd
journalctl -u pan360-server -f
```

### Monitor Active Jobs
```bash
curl http://localhost:8000/api/v1/jobs | python -m json.tool
```

### Clean Up Old Jobs
Jobs persist in memory. Restart server to clear completed jobs, or implement automatic cleanup.

### Storage Management
- **Uploads**: `server/uploads/` - one directory per job
- **Results**: `server/results/` - panorama outputs
- Manually delete old files or implement cleanup script

## Troubleshooting

### Server won't start
```bash
# Check if port is in use
sudo netstat -tulpn | grep 8000

# Try different port
python stitching_server.py --port 8080
```

### Pi can't connect to server
```bash
# Test network connectivity from Pi
ping 192.168.1.100

# Test HTTP connection
curl http://192.168.1.100:8000/health

# Check firewall on server
```

### Import errors on server
```bash
# Ensure stitching modules are accessible
ls ../src/stitching/

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

### Stitching fails
- Check server logs for detailed error messages
- Try different algorithm (simple_angle is most reliable)
- Verify images are properly captured and uploaded

### Out of memory
- Reduce image resolution in Pi config
- Add swap space on server
- Use machine with more RAM

## Performance Optimization

### For Simple Angle Stitcher
- Adjust `blend_width` (50-200px typical)
- Use GPU-accelerated OpenCV if available

### For OpenCV Stitcher
- Adjust `confidence_threshold`
- May need to pre-process images

### Server Performance
- Use SSD for faster I/O
- Enable multiple worker processes:
  ```bash
  uvicorn stitching_server:app --workers 4
  ```

## Security Considerations

⚠️ **Current implementation has no authentication**

For production use:
1. Add API key authentication
2. Use HTTPS with SSL certificates
3. Implement rate limiting
4. Restrict access by IP address
5. Use reverse proxy (nginx, Apache)

### Example: Add API Key
```python
# In stitching_server.py
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "your-secret-key":
        raise HTTPException(status_code=403, detail="Invalid API key")

# Add dependency to endpoints
@app.post("/api/v1/upload", dependencies=[Depends(verify_api_key)])
```

## Advanced: Production Deployment

### Using Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY server/requirements.txt .
RUN pip install -r requirements.txt
COPY server/ ./server/
COPY src/ ./src/
CMD ["uvicorn", "server.stitching_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using systemd Service
```ini
[Unit]
Description=Pan360 Stitching Server
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/Pan360/server
ExecStart=/path/to/venv/bin/python stitching_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable pan360-server
sudo systemctl start pan360-server
```

## Future Enhancements

- [ ] GPU acceleration for stitching
- [ ] Deep learning stitching algorithms (UDIS, GANs)
- [ ] Web interface for job management
- [ ] Database for job persistence
- [ ] Multi-user support with authentication
- [ ] Webhook notifications when jobs complete
- [ ] Automatic cleanup of old jobs
- [ ] Rate limiting and quotas
- [ ] Cloud deployment (AWS, Azure, GCP)

## Support

For issues or questions:
- GitHub Issues: https://github.com/rqz123/Pan360/issues
- Check logs on both Pi and server
- Review API documentation at `/docs` endpoint

## License

Part of the Pan360 project - see main README for license information.
