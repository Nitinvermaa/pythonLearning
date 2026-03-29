#!/usr/bin/env python3
"""
Janus WebRTC Client for Windows
Streams camera feed from Windows to Janus server in WSL
Uses DirectShow for camera capture on Windows
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
    print("Or use GStreamer Windows installer")
    GST_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if GST_AVAILABLE:
    Gst.init(None)


class JanusWebRTCClientWindows:
    """Windows client for streaming camera to Janus server"""
    
    def __init__(self, janus_url="http://localhost:8088/janus", room_id=1234, 
                 camera_device=0, video_width=640, video_height=480, 
                 video_framerate=30):
        """
        Initialize Janus WebRTC Client for Windows
        
        Args:
            janus_url: Janus server URL (WSL: http://localhost:8088/janus)
            room_id: VideoRoom plugin room ID
            camera_device: Camera device index (0, 1, 2...) or device name
            video_width: Video width in pixels
            video_height: Video height in pixels
            video_framerate: Video framerate
        """
        if not GST_AVAILABLE:
            raise RuntimeError("GStreamer not available. Install GStreamer and PyGObject.")
        
        self.janus_url = janus_url
        self.room_id = room_id
        self.camera_device = camera_device
        self.video_width = video_width
        self.video_height = video_height
        self.video_framerate = video_framerate
        
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
    
    async def join_room(self, display_name="Windows Client"):
        """Join the video room as publisher"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.janus_url}/{self.session_id}/{self.handle_id}",
                json={
                    "janus": "message",
                    "transaction": self._generate_transaction(),
                    "body": {
                        "request": "join",
                        "ptype": "publisher",
                        "room": self.room_id,
                        "display": display_name
                    }
                }
            ) as resp:
                data = await resp.json()
                if data.get("janus") == "success":
                    logger.info(f"Joined room {self.room_id}")
                    return True
                else:
                    logger.error(f"Failed to join room: {data}")
                    return False
    
    async def publish_offer(self, sdp_offer):
        """Publish SDP offer to Janus"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.janus_url}/{self.session_id}/{self.handle_id}",
                json={
                    "janus": "message",
                    "transaction": self._generate_transaction(),
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
                if data.get("janus") == "success":
                    jsep = data.get("jsep", {})
                    if jsep.get("type") == "answer":
                        sdp_answer = jsep.get("sdp")
                        logger.info("Received SDP answer from Janus")
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"SDP Answer:\n{sdp_answer}")
                        return sdp_answer
                    else:
                        logger.error(f"Unexpected response: {data}")
                        return None
                else:
                    logger.error(f"Failed to publish offer: {data}")
                    return None
    
    def _generate_transaction(self):
        """Generate a random transaction ID"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    def on_offer_created(self, promise, user_data):
        """Callback when WebRTC offer is created"""
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value('offer')
        
        # Get SDP offer
        sdp_text = offer.sdp.as_text()
        logger.info("SDP Offer created")
        logger.debug(f"SDP Offer:\n{sdp_text}")
        
        # Schedule async task to send offer to Janus
        asyncio.run_coroutine_threadsafe(
            self._handle_offer(sdp_text),
            self.loop
        )
    
    async def _handle_offer(self, sdp_offer):
        """Handle SDP offer by sending to Janus and processing answer"""
        sdp_answer = await self.publish_offer(sdp_offer)
        if sdp_answer:
            # Set remote description (answer)
            answer = GstSdp.SDPMessage.new()
            GstSdp.sdp_message_parse_buffer(bytes(sdp_answer.encode()), answer)
            
            promise = Gst.Promise.new_with_change_callback(self.on_answer_set, None)
            self.webrtcbin.emit('set-remote-description', answer, promise)
    
    def on_answer_set(self, promise, user_data):
        """Callback when remote description is set"""
        promise.wait()
        reply = promise.get_reply()
        logger.info("Remote description set successfully")
    
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
    
    def create_pipeline(self):
        """Create GStreamer pipeline for Windows camera streaming"""
        # Create pipeline
        self.pipeline = Gst.Pipeline.new("webrtc-send-windows")
        
        # Windows uses dshowvideosrc (DirectShow)
        src = Gst.ElementFactory.make("dshowvideosrc", "src")
        if isinstance(self.camera_device, int):
            src.set_property("device-index", self.camera_device)
        else:
            src.set_property("device-name", self.camera_device)
        
        # Video conversion and scaling
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        videoscale = Gst.ElementFactory.make("videoscale", "videoscale")
        video_rate = Gst.ElementFactory.make("videorate", "videorate")
        
        # Video caps
        caps = Gst.Caps.from_string(
            f"video/x-raw,width={self.video_width},height={self.video_height},"
            f"framerate={self.video_framerate}/1,format=I420"
        )
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        capsfilter.set_property("caps", caps)
        
        # VP8 encoder
        vp8enc = Gst.ElementFactory.make("vp8enc", "vp8enc")
        vp8enc.set_property("target-bitrate", 1000000)  # 1 Mbps
        vp8enc.set_property("deadline", 1)  # Real-time encoding
        
        # RTP payloader
        rtpvp8pay = Gst.ElementFactory.make("rtpvp8pay", "rtpvp8pay")
        rtpvp8pay.set_property("picture-id-mode", 2)
        
        # WebRTC bin
        self.webrtcbin = Gst.ElementFactory.make("webrtcbin", "webrtcbin")
        self.webrtcbin.set_property("stun-server", "stun://stun.l.google.com:19302")
        self.webrtcbin.set_property("bundle-policy", 1)
        
        # Connect signals
        self.webrtcbin.connect("on-negotiation-needed", self.on_negotiation_needed)
        self.webrtcbin.connect("on-ice-candidate", self.on_ice_candidate)
        self.webrtcbin.connect("notify::connection-state", self.on_connection_state)
        self.webrtcbin.connect("notify::ice-connection-state", self.on_ice_connection_state)
        
        # Add elements to pipeline
        self.pipeline.add(src)
        self.pipeline.add(videoconvert)
        self.pipeline.add(videoscale)
        self.pipeline.add(video_rate)
        self.pipeline.add(capsfilter)
        self.pipeline.add(vp8enc)
        self.pipeline.add(rtpvp8pay)
        self.pipeline.add(self.webrtcbin)
        
        # Link elements
        src.link(videoconvert)
        videoconvert.link(videoscale)
        videoscale.link(video_rate)
        video_rate.link(capsfilter)
        capsfilter.link(vp8enc)
        vp8enc.link(rtpvp8pay)
        rtpvp8pay.link(self.webrtcbin)
        
        logger.info("GStreamer pipeline created (Windows DirectShow)")
    
    def on_negotiation_needed(self, element):
        """Callback when WebRTC negotiation is needed"""
        logger.info("WebRTC negotiation needed, creating offer")
        promise = Gst.Promise.new_with_change_callback(self.on_offer_created, None)
        element.emit('create-offer', None, promise)
    
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
    
    async def start(self):
        """Start the streaming client"""
        logger.info("Starting Janus WebRTC client (Windows)...")
        
        self.loop = asyncio.get_event_loop()
        
        if not await self.create_session():
            logger.error("Failed to create Janus session")
            return False
        
        if not await self.attach_plugin():
            logger.error("Failed to attach to plugin")
            return False
        
        if not await self.join_room():
            logger.error("Failed to join room")
            return False
        
        self.create_pipeline()
        
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Failed to start pipeline")
            return False
        
        logger.info("Pipeline started, streaming camera feed...")
        return True
    
    def stop(self):
        """Stop the streaming client"""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            logger.info("Pipeline stopped")
    
    async def run(self):
        """Run the client (blocking)"""
        try:
            if await self.start():
                logger.info("Streaming active. Press Ctrl+C to stop.")
                while True:
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Janus WebRTC Camera Streaming Client (Windows)")
    parser.add_argument("--janus-url", default="http://localhost:8088/janus",
                       help="Janus server URL (default: http://localhost:8088/janus)")
    parser.add_argument("--room-id", type=int, default=1234,
                       help="VideoRoom room ID (default: 1234)")
    parser.add_argument("--camera-device", default=0, type=int,
                       help="Camera device index (default: 0)")
    parser.add_argument("--width", type=int, default=640,
                       help="Video width (default: 640)")
    parser.add_argument("--height", type=int, default=480,
                       help="Video height (default: 480)")
    parser.add_argument("--fps", type=int, default=30,
                       help="Video framerate (default: 30)")
    
    args = parser.parse_args()
    
    client = JanusWebRTCClientWindows(
        janus_url=args.janus_url,
        room_id=args.room_id,
        camera_device=args.camera_device,
        video_width=args.width,
        video_height=args.height,
        video_framerate=args.fps
    )
    
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
