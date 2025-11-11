# Janus WebRTC Camera Streaming - Quick Start

This is a Python client that streams your camera feed to a Janus WebRTC server using GStreamer and SDP (Session Description Protocol).

## 🚀 Quick Setup (3 Steps)

### 1. Run the Setup Script

```bash
chmod +x setup_janus_client.sh
./setup_janus_client.sh
```

This will install:
- GStreamer with WebRTC support
- Video4Linux utilities
- Python dependencies
- All required plugins

### 2. Make Sure Janus is Running

```bash
# Check if Janus is running
curl http://localhost:8088/janus

# If not running, start Janus
janus
```

### 3. Start Streaming!

```bash
# Test your camera first
python3 test_camera.py

# Start streaming to Janus
python3 janus_webrtc_client.py
```

## 📹 What This Does

The client will:
1. ✅ Connect to your Janus server via WebSocket
2. ✅ Capture video from your camera (`/dev/video0`)
3. ✅ Encode video with VP8 codec
4. ✅ Create and exchange SDP offers/answers
5. ✅ Establish WebRTC connection with ICE candidates
6. ✅ Stream video in real-time to Janus

## 🎥 View Your Stream

Open in browser:
```
http://localhost:8088/demos/videoroomtest.html
```

Then join room `1234` to see your camera stream!

## ⚙️ Configuration

### Change Camera Device
```bash
python3 janus_webrtc_client.py --camera /dev/video1
```

### Connect to Different Janus Server
```bash
python3 janus_webrtc_client.py --janus-url ws://192.168.1.100:8188
```

### Join Different Room
```bash
python3 janus_webrtc_client.py --room-id 5678
```

### Enable Verbose Logging
```bash
python3 janus_webrtc_client.py --verbose
```

## 🐛 Troubleshooting

### No Camera Found?

**On WSL**, attach your USB camera from Windows:

```powershell
# In PowerShell (as Administrator)
winget install --interactive --exact dorssel.usbipd-win
usbipd list
usbipd bind --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

### Can't Connect to Janus?

```bash
# Make sure Janus is running
ps aux | grep janus

# Start Janus if not running
janus -d 6  # Verbose mode for debugging
```

### Pipeline Errors?

```bash
# Check if all GStreamer plugins are installed
gst-inspect-1.0 webrtcbin
gst-inspect-1.0 vp8enc
gst-inspect-1.0 v4l2src
```

## 📚 Full Documentation

- **[JANUS_SETUP_GUIDE.md](JANUS_SETUP_GUIDE.md)** - Complete setup instructions
- **[WEBRTC_SDP_GUIDE.md](WEBRTC_SDP_GUIDE.md)** - How WebRTC and SDP work
- **[janus_config.json](janus_config.json)** - Configuration file

## 🔧 Files Created

| File | Description |
|------|-------------|
| `janus_webrtc_client.py` | Main client script |
| `test_camera.py` | Camera testing utility |
| `setup_janus_client.sh` | Automated setup script |
| `janus_config.json` | Configuration file |
| `JANUS_SETUP_GUIDE.md` | Detailed setup guide |
| `WEBRTC_SDP_GUIDE.md` | WebRTC/SDP technical guide |

## 💡 Example Commands

```bash
# Test everything step by step
python3 test_camera.py                    # 1. Test camera
python3 janus_webrtc_client.py --verbose  # 2. Start streaming

# Custom configuration
python3 janus_webrtc_client.py \
  --janus-url ws://localhost:8188 \
  --room-id 1234 \
  --camera /dev/video0 \
  --verbose

# View available cameras
v4l2-ctl --list-devices

# Monitor GStreamer pipeline
GST_DEBUG=3 python3 janus_webrtc_client.py
```

## 🌐 Architecture

```
┌──────────────┐     WebSocket      ┌──────────────┐
│   Python     │◄──────SDP──────────┤    Janus     │
│   Client     │                    │   Server     │
│              │◄────ICE Trickle────┤              │
│  GStreamer   │                    │  VideoRoom   │
│  WebRTC      │═══════RTP══════════►│   Plugin     │
└──────┬───────┘    (Video/Audio)   └──────┬───────┘
       │                                    │
  ┌────▼─────┐                        ┌────▼─────┐
  │  Camera  │                        │ Web      │
  │ /dev/    │                        │ Browser  │
  │ video0   │                        │ Viewer   │
  └──────────┘                        └──────────┘
```

## 🎯 What You Can Do Next

1. **Stream to multiple viewers** - Join same room from multiple browsers
2. **Change codecs** - Use H.264 instead of VP8
3. **Add audio** - Replace `audiotestsrc` with real microphone
4. **Adjust quality** - Change resolution, framerate, bitrate
5. **Add effects** - Use GStreamer filters for effects

## 📞 Need Help?

Run with verbose logging and check logs:

```bash
# Enable all debug output
GST_DEBUG=4 python3 janus_webrtc_client.py --verbose 2>&1 | tee debug.log

# Check Janus logs
janus -d 6 2>&1 | tee janus.log
```

## 🎓 Learn More

- [Janus GitHub](https://github.com/meetecho/janus-gateway)
- [GStreamer WebRTC](https://gstreamer.freedesktop.org/documentation/webrtc/)
- [WebRTC Standards](https://webrtc.org/)

Happy streaming! 🎉
