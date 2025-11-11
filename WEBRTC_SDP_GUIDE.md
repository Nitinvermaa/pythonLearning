# Understanding WebRTC and SDP in the Janus Client

This document explains how WebRTC and SDP (Session Description Protocol) work in the context of streaming camera feed to Janus.

## What is WebRTC?

WebRTC (Web Real-Time Communication) is a technology that enables real-time communication of audio, video, and data in web browsers and mobile applications. Key features:

- **Peer-to-peer communication** (with server-assisted signaling)
- **Low latency** streaming
- **Built-in encryption** (DTLS/SRTP)
- **NAT traversal** using ICE, STUN, and TURN

## What is SDP?

SDP (Session Description Protocol) is a format for describing multimedia communication sessions. It includes:

- **Media types** (audio, video)
- **Codecs** (VP8, H.264, Opus, etc.)
- **Transport information** (IP addresses, ports)
- **Encryption keys** and security parameters
- **Bandwidth** requirements

### Example SDP Offer

```
v=0
o=- 12345 67890 IN IP4 127.0.0.1
s=Python GStreamer WebRTC Client
t=0 0
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=rtcp-mux
a=sendrecv
a=mid:video0
a=rtpmap:96 VP8/90000
a=ice-ufrag:abc123
a=ice-pwd:xyz789
```

## WebRTC Signaling Flow with Janus

### 1. Connection Setup

```
Client                          Janus Server
  |                                  |
  |---(WebSocket Connect)----------->|
  |                                  |
  |---{create session}-------------->|
  |<--{session_id}-------------------|
  |                                  |
  |---{attach to videoroom}--------->|
  |<--{handle_id}-------------------|
  |                                  |
  |---{join room}------------------>|
  |<--{joined}----------------------|
```

### 2. SDP Negotiation (Offer/Answer)

```
Client                          Janus Server
  |                                  |
  |  (Camera starts capturing)       |
  |                                  |
  |---{SDP Offer}------------------>|
  |   - Video: VP8, 640x480         |
  |   - Audio: Opus, 48kHz          |
  |   - ICE candidates              |
  |                                  |
  |<--{SDP Answer}------------------|
  |   - Accepted formats            |
  |   - Server ICE candidates       |
  |                                  |
```

### 3. ICE Candidate Exchange

```
Client                          Janus Server
  |                                  |
  |---{ICE candidate 1}------------>|
  |---{ICE candidate 2}------------>|
  |<--{ICE candidate 1}-------------|
  |<--{ICE candidate 2}-------------|
  |                                  |
  |  (ICE negotiation completes)    |
  |                                  |
```

### 4. Media Streaming

```
Client                          Janus Server
  |                                  |
  |====(RTP Video Stream)==========>|
  |====(RTP Audio Stream)==========>|
  |                                  |
  |<===(RTCP Reports)===============|
  |                                  |
```

## How the Python Client Works

### GStreamer Pipeline Architecture

```
┌─────────────┐
│  v4l2src    │  Camera Capture
│ /dev/video0 │
└──────┬──────┘
       │
       v
┌─────────────┐
│videoconvert │  Format Conversion
└──────┬──────┘
       │
       v
┌─────────────┐
│   vp8enc    │  VP8 Video Encoding
└──────┬──────┘
       │
       v
┌─────────────┐
│ rtpvp8pay   │  RTP Packetization
└──────┬──────┘
       │
       v
┌─────────────┐
│ webrtcbin   │  WebRTC Handling
│             │  - SDP negotiation
│             │  - ICE candidates
│             │  - DTLS/SRTP
└─────────────┘
```

### Key Components in the Code

#### 1. WebRTC Bin Setup

```python
self.webrtcbin = self.pipeline.get_by_name('sendrecv')

# Connect signals
self.webrtcbin.connect('on-negotiation-needed', self.on_negotiation_needed)
self.webrtcbin.connect('on-ice-candidate', self.on_ice_candidate)

# Set STUN server for NAT traversal
self.webrtcbin.set_property('stun-server', 'stun://stun.l.google.com:19302')
```

#### 2. Creating SDP Offer

```python
def on_negotiation_needed(self, webrtc):
    """Called when WebRTC needs to create an offer"""
    promise = Gst.Promise.new_with_change_func(self.on_offer_created, webrtc, None)
    webrtc.emit('create-offer', None, promise)

def on_offer_created(self, promise, webrtc, user_data):
    """Called when offer is created"""
    reply = promise.get_reply()
    offer = reply['offer']
    
    # Set as local description
    promise = Gst.Promise.new()
    webrtc.emit('set-local-description', offer, promise)
    
    # Get SDP text and send to Janus
    sdp_text = offer.sdp.as_text()
    self.send_offer_to_janus(sdp_text)
```

#### 3. Handling SDP Answer

```python
def set_remote_description(self, sdp_text):
    """Set the SDP answer from Janus"""
    # Parse SDP text
    ret, sdp = GstSdp.SDPMessage.new_from_text(sdp_text)
    
    # Create answer description
    answer = GstWebRTC.WebRTCSessionDescription.new(
        GstWebRTC.WebRTCSDPType.ANSWER, sdp
    )
    
    # Set as remote description
    promise = Gst.Promise.new()
    self.webrtcbin.emit('set-remote-description', answer, promise)
```

#### 4. ICE Candidate Handling

```python
def on_ice_candidate(self, webrtc, mline_index, candidate):
    """Called when local ICE candidate is found"""
    # Send to Janus
    self.send_ice_candidate(mline_index, candidate)

def add_ice_candidate(self, candidate):
    """Add remote ICE candidate from Janus"""
    mline_index = candidate.get('sdpMLineIndex', 0)
    candidate_str = candidate.get('candidate', '')
    self.webrtcbin.emit('add-ice-candidate', mline_index, candidate_str)
```

## Janus Protocol Messages

### Create Session

```json
{
  "janus": "create",
  "transaction": "create_session"
}
```

Response:
```json
{
  "janus": "success",
  "transaction": "create_session",
  "data": {
    "id": 123456789
  }
}
```

### Attach to Plugin

```json
{
  "janus": "attach",
  "plugin": "janus.plugin.videoroom",
  "transaction": "attach_plugin",
  "session_id": 123456789
}
```

### Join Room

```json
{
  "janus": "message",
  "transaction": "join_room",
  "session_id": 123456789,
  "handle_id": 987654321,
  "body": {
    "request": "join",
    "room": 1234,
    "ptype": "publisher",
    "display": "Python GStreamer Client"
  }
}
```

### Publish (with SDP Offer)

```json
{
  "janus": "message",
  "transaction": "publish",
  "session_id": 123456789,
  "handle_id": 987654321,
  "body": {
    "request": "publish",
    "audio": true,
    "video": true
  },
  "jsep": {
    "type": "offer",
    "sdp": "v=0\r\no=- 12345 67890 IN IP4 127.0.0.1\r\n..."
  }
}
```

### Trickle ICE

```json
{
  "janus": "trickle",
  "transaction": "trickle",
  "session_id": 123456789,
  "handle_id": 987654321,
  "candidate": {
    "sdpMLineIndex": 0,
    "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host"
  }
}
```

## NAT Traversal (ICE/STUN/TURN)

### ICE (Interactive Connectivity Establishment)

ICE finds the best path for peer-to-peer connection:

1. **Host candidates**: Direct local IP
2. **Server reflexive candidates**: Public IP via STUN
3. **Relayed candidates**: Media relay via TURN

### STUN (Session Traversal Utilities for NAT)

STUN helps discover your public IP address:

```python
self.webrtcbin.set_property('stun-server', 'stun://stun.l.google.com:19302')
```

### TURN (Traversal Using Relays around NAT)

TURN relays media when direct connection fails:

```python
self.webrtcbin.set_property('turn-server', 'turn://user:pass@turn.example.com:3478')
```

## Video Codecs Supported

### VP8 (Default)
- Open source, royalty-free
- Good quality at lower bitrates
- Wide browser support
- Fast encoding

```python
vp8enc deadline=1 target-bitrate=1000000
```

### VP9
- Better compression than VP8
- Requires more CPU
- Good for high-quality streaming

```python
vp9enc deadline=1 target-bitrate=1000000
```

### H.264
- Most widely supported
- Hardware acceleration available
- Patent encumbered

```python
x264enc tune=zerolatency bitrate=1000
```

## Audio Codecs Supported

### Opus (Default)
- Designed for interactive speech and music
- Low latency
- Excellent quality

```python
opusenc bitrate=128000
```

### G.711
- Legacy codec
- Lower quality
- Minimal CPU usage

## Monitoring and Debugging

### Enable GStreamer Debug

```bash
export GST_DEBUG=3  # 0=none, 1=error, 2=warning, 3=info, 4=debug, 5=trace
export GST_DEBUG_FILE=/tmp/gstreamer.log
python3 janus_webrtc_client.py --verbose
```

### View Pipeline Graph

```bash
export GST_DEBUG_DUMP_DOT_DIR=/tmp
# After running, convert .dot to image:
dot -Tpng /tmp/*.dot -o pipeline.png
```

### Monitor WebRTC Stats

You can add stats collection in the code:

```python
def get_stats(self):
    promise = Gst.Promise.new_with_change_func(self.on_stats, None, None)
    self.webrtcbin.emit('get-stats', None, promise)

def on_stats(self, promise, user_data1, user_data2):
    stats = promise.get_reply()
    # Process stats
    print(stats)
```

## Security Considerations

### DTLS (Datagram Transport Layer Security)
- Encrypts media streams
- Automatic in WebRTC
- Uses self-signed certificates

### SRTP (Secure Real-time Transport Protocol)
- Encrypts RTP packets
- Keys exchanged via DTLS

### WebSocket Security
For production, use WSS (WebSocket Secure):

```python
client = JanusWebRTCClient(janus_url='wss://janus.example.com:8989')
```

## Performance Tuning

### Reduce Latency

1. **Lower video resolution**:
   ```python
   video/x-raw,width=320,height=240,framerate=30/1
   ```

2. **Faster encoding preset**:
   ```python
   vp8enc deadline=1 cpu-used=16
   ```

3. **Reduce buffer sizes**:
   ```python
   v4l2src ! ... ! queue max-size-buffers=1 leaky=downstream
   ```

### Improve Quality

1. **Higher bitrate**:
   ```python
   vp8enc target-bitrate=2000000
   ```

2. **Higher resolution**:
   ```python
   video/x-raw,width=1280,height=720
   ```

3. **Better encoding**:
   ```python
   vp8enc deadline=0 cpu-used=0
   ```

## Common Issues and Solutions

### Issue: Camera permission denied
```bash
sudo usermod -a -G video $USER
sudo chmod 666 /dev/video0
```

### Issue: WebRTC connection fails
- Check STUN/TURN configuration
- Verify firewall allows UDP traffic
- Check NAT settings

### Issue: No audio/video
- Check codec support: `gst-inspect-1.0 vp8enc`
- Verify camera works: `v4l2-ctl --list-formats-ext`
- Check Janus room configuration

## References

- [WebRTC Specification](https://www.w3.org/TR/webrtc/)
- [SDP RFC 4566](https://tools.ietf.org/html/rfc4566)
- [ICE RFC 8445](https://tools.ietf.org/html/rfc8445)
- [GStreamer WebRTC](https://gstreamer.freedesktop.org/documentation/webrtc/)
- [Janus Documentation](https://janus.conf.meetecho.com/docs/)
