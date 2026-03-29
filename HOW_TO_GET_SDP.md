# How to Get SDP Content from Janus

This guide explains how to extract and work with SDP (Session Description Protocol) content from Janus WebRTC server.

## Understanding SDP in Janus Responses

When you interact with Janus, SDP content is returned in the `jsep` (JavaScript Session Establishment Protocol) field of the JSON response:

```json
{
    "janus": "success",
    "session_id": 1234567890,
    "data": {...},
    "jsep": {
        "type": "answer",        // or "offer"
        "sdp": "v=0\r\no=..."    // The actual SDP content
    }
}
```

## Method 1: Get SDP Answer When Publishing

When you publish a stream (send video), you send an SDP offer and Janus returns an SDP answer:

```python
import asyncio
import aiohttp

async def get_sdp_from_publish():
    janus_url = "http://localhost:8088/janus"
    session_id = 1234567890  # Your session ID
    handle_id = 9876543210   # Your handle ID
    
    # Your SDP offer (from GStreamer WebRTC, etc.)
    sdp_offer = "v=0\r\no=..."
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{janus_url}/{session_id}/{handle_id}",
            json={
                "janus": "message",
                "transaction": "abc123",
                "jsep": {
                    "type": "offer",
                    "sdp": sdp_offer
                },
                "body": {
                    "request": "publish",
                    "audio": False,
                    "video": True
                }
            }
        ) as resp:
            data = await resp.json()
            
            # Extract SDP answer
            if data.get("janus") == "success":
                jsep = data.get("jsep", {})
                sdp_answer = jsep.get("sdp")
                print("SDP Answer from Janus:")
                print(sdp_answer)
```

## Method 2: Get SDP When Subscribing (Viewing)

When you subscribe to a stream (receive video), Janus sends an SDP offer:

```python
async def get_sdp_from_subscribe():
    # Join as subscriber
    async with session.post(
        f"{janus_url}/{session_id}/{handle_id}",
        json={
            "janus": "message",
            "transaction": "abc123",
            "body": {
                "request": "join",
                "ptype": "subscriber",
                "room": 1234
            }
        }
    ) as resp:
        data = await resp.json()
        
        # Janus sends an SDP offer in the response
        if data.get("janus") == "event":
            jsep = data.get("jsep", {})
            if jsep.get("type") == "offer":
                sdp_offer = jsep.get("sdp")
                print("SDP Offer from Janus:")
                print(sdp_offer)
```

## Method 3: Extract SDP from Any Response

Here's a helper function to extract SDP from any Janus response:

```python
def extract_sdp_from_janus_response(janus_response):
    """
    Extract SDP from Janus JSON response
    
    Returns:
        dict with 'type' and 'sdp', or None
    """
    if not janus_response or janus_response.get("janus") != "success":
        return None
    
    jsep = janus_response.get("jsep")
    if not jsep:
        return None
    
    return {
        "type": jsep.get("type"),  # "offer" or "answer"
        "sdp": jsep.get("sdp")     # SDP string
    }

# Usage
response = await session.post(...)
data = await response.json()
sdp_data = extract_sdp_from_janus_response(data)

if sdp_data:
    print(f"SDP Type: {sdp_data['type']}")
    print(f"SDP Content:\n{sdp_data['sdp']}")
```

## Method 4: Get SDP from Events (Long Polling)

Janus can send SDP updates via events. Use long polling:

```python
async def get_sdp_from_events():
    async with session.get(
        f"{janus_url}/{session_id}/{handle_id}",
        params={"maxev": 1},  # Get up to 1 event
        timeout=aiohttp.ClientTimeout(total=30)
    ) as resp:
        if resp.status == 200:
            data = await resp.json()
            if data.get("janus") == "event":
                jsep = data.get("jsep", {})
                if jsep:
                    sdp = jsep.get("sdp")
                    print("SDP from event:", sdp)
```

## In the Main Client Code

Looking at `janus_webrtc_client.py`, SDP is extracted here:

```python
# Line 142-147: Extract SDP answer from Janus response
jsep = data.get("jsep", {})
if jsep.get("type") == "answer":
    sdp_answer = jsep.get("sdp")
    logger.info("Received SDP answer from Janus")
    return sdp_answer
```

## Example: Complete SDP Extraction

```python
import asyncio
import aiohttp
import json

async def get_sdp_example():
    janus_url = "http://localhost:8088/janus"
    
    # 1. Create session
    async with aiohttp.ClientSession() as session:
        async with session.post(
            janus_url,
            json={"janus": "create", "transaction": "test123"}
        ) as resp:
            session_data = await resp.json()
            session_id = session_data["data"]["id"]
    
    # 2. Attach to plugin
    async with session.post(
        f"{janus_url}/{session_id}",
        json={
            "janus": "attach",
            "plugin": "janus.plugin.videoroom",
            "transaction": "test456"
        }
    ) as resp:
        handle_data = await resp.json()
        handle_id = handle_data["data"]["id"]
    
    # 3. Join room and get SDP
    async with session.post(
        f"{janus_url}/{session_id}/{handle_id}",
        json={
            "janus": "message",
            "transaction": "test789",
            "body": {
                "request": "join",
                "ptype": "publisher",
                "room": 1234
            }
        }
    ) as resp:
        join_data = await resp.json()
        
        # Check if there's SDP in the response
        if "jsep" in join_data:
            sdp_type = join_data["jsep"]["type"]
            sdp_content = join_data["jsep"]["sdp"]
            
            print(f"Got SDP {sdp_type}:")
            print(sdp_content)
            
            # Save to file
            with open("janus_sdp.txt", "w") as f:
                f.write(sdp_content)

asyncio.run(get_sdp_example())
```

## SDP Content Structure

SDP content is a text string that looks like:

```
v=0
o=- 1234567890 2 IN IP4 127.0.0.1
s=Janus
t=0 0
a=group:BUNDLE 0
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=ice-ufrag:janus
a=ice-pwd:januspwd123456
a=fingerprint:sha-256 AA:BB:CC:DD:...
a=setup:active
a=mid:0
a=sendonly
a=rtcp-mux
a=rtpmap:96 VP8/90000
a=candidate:1 1 UDP 2130706431 192.168.1.100 5000 typ host
```

Key parts:
- `v=0`: SDP version
- `o=...`: Origin (session identifier)
- `m=video`: Media description
- `a=ice-ufrag` / `a=ice-pwd`: ICE credentials
- `a=fingerprint`: DTLS fingerprint
- `a=candidate`: ICE candidates for NAT traversal

## Running the Example Script

Use the provided example script:

```bash
# Show SDP structure and parse example
python3 get_sdp_from_janus.py --example 2

# Try to get SDP from real Janus server (requires running Janus)
python3 get_sdp_from_janus.py --example 1 --janus-url http://localhost:8088/janus
```

## Summary

1. **SDP is in `jsep` field**: All Janus responses with SDP have it in `response["jsep"]["sdp"]`
2. **Type indicates offer/answer**: `jsep["type"]` is either "offer" or "answer"
3. **Extract after API calls**: SDP comes in responses to publish, subscribe, or join requests
4. **Use helper function**: The `extract_sdp_from_response()` method in the client handles this

The main client (`janus_webrtc_client.py`) already extracts SDP automatically, but you can use these methods to get SDP for other purposes like logging, debugging, or custom processing.
