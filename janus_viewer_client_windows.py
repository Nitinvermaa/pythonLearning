#!/usr/bin/env python3
"""
Janus WebRTC Viewer Client for Windows
Receives video stream from Janus server and displays it
Uses GStreamer WebRTC to receive and decode video
"""

import json
import asyncio
import aiohttp
import sys
import logging
import random
import string

# Try to import GStreamer (Windows)
try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstWebRTC', '1.0')
    gi.require_version('GstSdp', '1.0')
    from gi.repository import Gst, GstWebRTC, GstSdp, GLib
    GST_AVAILABLE = True
except ImportError:
    print("Warning: GStreamer Python bindings not available")
    print("Install: pip install PyGObject")
    GST_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if GST_AVAILABLE:
    Gst.init(None)


class JanusViewerClientWindows:
    """Windows client for viewing Janus streams"""
    
    def __init__(self, janus_url="http://localhost:8088/janus", room_id=1234, 
                 feed_id=None):
        """
        Initialize Janus Viewer Client
        
        Args:
            janus_url: Janus server URL
            room_id: VideoRoom plugin room ID
            feed_id: Publisher feed ID to subscribe to (None = auto-detect)
        """
        if not GST_AVAILABLE:
            raise RuntimeError("GStreamer not available. Install GStreamer and PyGObject.")
        
        self.janus_url = janus_url
        self.room_id = room_id
        self.feed_id = feed_id
        
        self.session_id = None
        self.handle_id = None
        self.loop = None
        self.pipeline = None
        self.webrtcbin = None
        
    async def create_session(self):
        """Create a session with Janus server"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.janus_url}",
                json={"janus": "create", "transaction": self._generate_transaction()}
            ) as resp:
                data = await resp.json()
                if data.get("janus") == "success":
                    self.session_id = data["data"]["id"]
                    logger.info(f"Created session: {self.session_id}")
                    return True
                else:
                    logger.error(f"Failed to create session: {data}")
                    return False
    
    async def attach_plugin(self, plugin="janus.plugin.videoroom"):
        """Attach to VideoRoom plugin"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.janus_url}/{self.session_id}",
                json={
                    "janus": "attach",
                    "plugin": plugin,
                    "transaction": self._generate_transaction()
                }
            ) as resp:
                data = await resp.json()
                if data.get("janus") == "success":
                    self.handle_id = data["data"]["id"]
                    logger.info(f"Attached to plugin: {self.handle_id}")
                    return True
                else:
                    logger.error(f"Failed to attach plugin: {data}")
                    return False
    
    async def list_participants(self):
        """List participants in room to find feed ID"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.janus_url}/{self.session_id}/{self.handle_id}",
                json={
                    "janus": "message",
                    "transaction": self._generate_transaction(),
                    "body": {
                        "request": "listparticipants",
                        "room": self.room_id
                    }
                }
            ) as resp:
                data = await resp.json()
                if data.get("janus") == "success":
                    participants = data.get("plugindata", {}).get("data", {}).get("participants", [])
                    publishers = [p for p in participants if p.get("publisher")]
                    if publishers:
                        feed_id = publishers[0].get("id")
                        logger.info(f"Found publisher feed ID: {feed_id}")
                        return feed_id
                    else:
                        logger.warning("No publishers found in room")
                        return None
                else:
                    logger.error(f"Failed to list participants: {data}")
                    return None
    
    async def subscribe(self, feed_id):
        """Subscribe to a publisher feed"""
        async with aiohttp.ClientSession() as session:
            # First, create a dummy SDP offer to trigger Janus
            # In real implementation, we'd create this from webrtcbin
            dummy_offer = self._create_dummy_sdp_offer()
            
            async with session.post(
                f"{self.janus_url}/{self.session_id}/{self.handle_id}",
                json={
                    "janus": "message",
                    "transaction": self._generate_transaction(),
                    "jsep": {
                        "type": "offer",
                        "sdp": dummy_offer
                    },
                    "body": {
                        "request": "join",
                        "ptype": "subscriber",
                        "room": self.room_id,
                        "feed": feed_id
                    }
                }
            ) as resp:
                data = await resp.json()
                if data.get("janus") == "success" or data.get("janus") == "event":
                    jsep = data.get("jsep", {})
                    if jsep.get("type") == "offer":
                        sdp_offer = jsep.get("sdp")
                        logger.info("Received SDP offer from Janus")
                        return sdp_offer
                    else:
                        logger.error(f"Unexpected response: {data}")
                        return None
                else:
                    logger.error(f"Failed to subscribe: {data}")
                    return None
    
    async def send_answer(self, sdp_answer):
        """Send SDP answer to Janus"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.janus_url}/{self.session_id}/{self.handle_id}",
                json={
                    "janus": "message",
                    "transaction": self._generate_transaction(),
                    "jsep": {
                        "type": "answer",
                        "sdp": sdp_answer
                    },
                    "body": {
                        "request": "start",
                        "room": self.room_id
                    }
                }
            ) as resp:
                data = await resp.json()
                if data.get("janus") == "success" or data.get("janus") == "event":
                    logger.info("SDP answer sent successfully")
                    return True
                else:
                    logger.error(f"Failed to send answer: {data}")
                    return False
    
    def _create_dummy_sdp_offer(self):
        """Create a minimal SDP offer for subscription"""
        return """v=0
o=- 0 0 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=msid-semantic: WMS
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:viewer
a=ice-pwd:viewerpwd
a=fingerprint:sha-256 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
a=setup:actpass
a=mid:0
a=recvonly
a=rtcp-mux
a=rtpmap:96 VP8/90000
"""
    
    def _generate_transaction(self):
        """Generate a random transaction ID"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    def create_pipeline(self):
        """Create GStreamer pipeline for receiving video"""
        self.pipeline = Gst.Pipeline.new("webrtc-receive-windows")
        
        # WebRTC bin for receiving
        self.webrtcbin = Gst.ElementFactory.make("webrtcbin", "webrtcbin")
        self.webrtcbin.set_property("stun-server", "stun://stun.l.google.com:19302")
        self.webrtcbin.set_property("bundle-policy", 1)
        
        # Connect signals
        self.webrtcbin.connect("on-negotiation-needed", self.on_negotiation_needed)
        self.webrtcbin.connect("on-ice-candidate", self.on_ice_candidate)
        self.webrtcbin.connect("notify::connection-state", self.on_connection_state)
        self.webrtcbin.connect("notify::ice-connection-state", self.on_ice_connection_state)
        
        # Video decode and display pipeline
        # webrtcbin receives RTP → depayload → decode → convert → display
        rtpvp8depay = Gst.ElementFactory.make("rtpvp8depay", "rtpvp8depay")
        vp8dec = Gst.ElementFactory.make("vp8dec", "vp8dec")
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        autovideosink = Gst.ElementFactory.make("autovideosink", "autovideosink")
        
        # Add elements
        self.pipeline.add(self.webrtcbin)
        self.pipeline.add(rtpvp8depay)
        self.pipeline.add(vp8dec)
        self.pipeline.add(videoconvert)
        self.pipeline.add(autovideosink)
        
        # Link webrtcbin src pad to depayloader
        # We need to link dynamically when pad is created
        self.webrtcbin.connect("pad-added", self.on_pad_added, rtpvp8depay)
        
        # Link rest of pipeline
        rtpvp8depay.link(vp8dec)
        vp8dec.link(videoconvert)
        videoconvert.link(autovideosink)
        
        logger.info("GStreamer receive pipeline created")
    
    def on_pad_added(self, element, pad, depay):
        """Handle new pad from webrtcbin"""
        caps = pad.get_current_caps()
        if caps:
            structure = caps.get_structure(0)
            name = structure.get_name()
            if name.startswith("application/x-rtp"):
                logger.info(f"Linking RTP pad: {name}")
                pad.link(depay.get_static_pad("sink"))
            else:
                logger.warning(f"Unexpected pad type: {name}")
    
    def on_negotiation_needed(self, element):
        """Callback when WebRTC negotiation is needed"""
        logger.info("WebRTC negotiation needed (viewer)")
        # For viewer, we wait for offer from Janus
        # This is handled in the subscribe method
    
    def on_ice_candidate(self, webrtcbin, mlineindex, candidate):
        """Handle ICE candidate"""
        if candidate:
            if hasattr(candidate, 'get_string'):
                candidate_str = candidate.get_string('candidate')[1]
            else:
                candidate_str = str(candidate)
            
            logger.debug(f"ICE candidate (mline {mlineindex}): {candidate_str}")
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._send_ice_candidate(mlineindex, candidate_str),
                    self.loop
                )
    
    async def _send_ice_candidate(self, mlineindex, candidate):
        """Send ICE candidate to Janus"""
        if not self.session_id or not self.handle_id:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.janus_url}/{self.session_id}/{self.handle_id}",
                    json={
                        "janus": "trickle",
                        "transaction": self._generate_transaction(),
                        "candidate": {
                            "candidate": candidate,
                            "sdpMLineIndex": mlineindex
                        }
                    }
                ) as resp:
                    logger.debug(f"ICE candidate sent (mline {mlineindex})")
        except Exception as e:
            logger.warning(f"Failed to send ICE candidate: {e}")
    
    def on_connection_state(self, webrtcbin, pspec):
        """Monitor WebRTC connection state"""
        state = webrtcbin.get_property("connection-state")
        state_name = GstWebRTC.WebRTCPeerConnectionState.to_string(state)
        logger.info(f"Connection state: {state_name}")
    
    def on_ice_connection_state(self, webrtcbin, pspec):
        """Monitor ICE connection state"""
        state = webrtcbin.get_property("ice-connection-state")
        state_name = GstWebRTC.WebRTCICEConnectionState.to_string(state)
        logger.info(f"ICE connection state: {state_name}")
    
    async def handle_sdp_offer(self, sdp_offer):
        """Handle SDP offer from Janus and create answer"""
        # Parse SDP offer
        offer = GstSdp.SDPMessage.new()
        GstSdp.sdp_message_parse_buffer(bytes(sdp_offer.encode()), offer)
        
        # Set remote description (offer)
        promise = Gst.Promise.new_with_change_callback(self.on_offer_set, None)
        self.webrtcbin.emit('set-remote-description', offer, promise)
    
    def on_offer_set(self, promise, user_data):
        """Callback when remote offer is set"""
        promise.wait()
        reply = promise.get_reply()
        logger.info("Remote offer set, creating answer")
        
        # Create answer
        promise = Gst.Promise.new_with_change_callback(self.on_answer_created, None)
        self.webrtcbin.emit('create-answer', None, promise)
    
    def on_answer_created(self, promise, user_data):
        """Callback when answer is created"""
        promise.wait()
        reply = promise.get_reply()
        answer = reply.get_value('answer')
        
        sdp_answer = answer.sdp.as_text()
        logger.info("SDP Answer created")
        logger.debug(f"SDP Answer:\n{sdp_answer}")
        
        # Send answer to Janus
        asyncio.run_coroutine_threadsafe(
            self.send_answer(sdp_answer),
            self.loop
        )
    
    async def start(self):
        """Start the viewer client"""
        logger.info("Starting Janus viewer client (Windows)...")
        
        self.loop = asyncio.get_event_loop()
        
        if not await self.create_session():
            return False
        
        if not await self.attach_plugin():
            return False
        
        # Get feed ID if not provided
        if not self.feed_id:
            self.feed_id = await self.list_participants()
            if not self.feed_id:
                logger.error("No publisher found to subscribe to")
                return False
        
        # Create pipeline
        self.create_pipeline()
        
        # Start pipeline
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Failed to start pipeline")
            return False
        
        # Subscribe and get SDP offer
        sdp_offer = await self.subscribe(self.feed_id)
        if sdp_offer:
            await self.handle_sdp_offer(sdp_offer)
        else:
            logger.error("Failed to get SDP offer from Janus")
            return False
        
        logger.info("Viewer started, waiting for video...")
        return True
    
    def stop(self):
        """Stop the viewer client"""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            logger.info("Viewer stopped")
    
    async def run(self):
        """Run the viewer (blocking)"""
        try:
            if await self.start():
                logger.info("Viewing active. Press Ctrl+C to stop.")
                while True:
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Janus WebRTC Viewer Client (Windows)")
    parser.add_argument("--janus-url", default="http://localhost:8088/janus",
                       help="Janus server URL (default: http://localhost:8088/janus)")
    parser.add_argument("--room-id", type=int, default=1234,
                       help="VideoRoom room ID (default: 1234)")
    parser.add_argument("--feed-id", type=int, default=None,
                       help="Publisher feed ID (default: auto-detect)")
    
    args = parser.parse_args()
    
    client = JanusViewerClientWindows(
        janus_url=args.janus_url,
        room_id=args.room_id,
        feed_id=args.feed_id
    )
    
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
