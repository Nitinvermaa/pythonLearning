#!/usr/bin/env python3
"""
Janus WebRTC Camera Streaming Client using GStreamer
This script captures camera feed and streams it to a Janus WebRTC server using SDP
"""

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')

from gi.repository import Gst, GstWebRTC, GstSdp, GLib
import json
import asyncio
import websockets
import argparse
import sys
import logging

# Initialize GStreamer
Gst.init(None)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JanusWebRTCClient:
    def __init__(self, janus_url, room_id=1234, camera_device="/dev/video0"):
        """
        Initialize Janus WebRTC client
        
        Args:
            janus_url: WebSocket URL to Janus server (e.g., ws://localhost:8188)
            room_id: Video room ID to join
            camera_device: Camera device path (default: /dev/video0)
        """
        self.janus_url = janus_url
        self.room_id = room_id
        self.camera_device = camera_device
        self.websocket = None
        self.session_id = None
        self.handle_id = None
        self.pipeline = None
        self.webrtcbin = None
        self.loop = None
        
    def create_pipeline(self):
        """Create GStreamer pipeline with WebRTC support"""
        # Pipeline for camera capture and WebRTC streaming
        pipeline_str = f"""
        v4l2src device={self.camera_device} ! 
        videoconvert ! 
        video/x-raw,width=640,height=480,framerate=30/1 ! 
        vp8enc deadline=1 target-bitrate=1000000 ! 
        rtpvp8pay ! 
        application/x-rtp,media=video,encoding-name=VP8,payload=96 ! 
        webrtcbin name=sendrecv bundle-policy=max-bundle
        
        audiotestsrc is-live=true wave=silence ! 
        audioconvert ! 
        audioresample ! 
        opusenc ! 
        rtpopuspay ! 
        application/x-rtp,media=audio,encoding-name=OPUS,payload=97 ! 
        sendrecv.
        """
        
        logger.info("Creating GStreamer pipeline...")
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.webrtcbin = self.pipeline.get_by_name('sendrecv')
        
        # Connect to WebRTC signals
        self.webrtcbin.connect('on-negotiation-needed', self.on_negotiation_needed)
        self.webrtcbin.connect('on-ice-candidate', self.on_ice_candidate)
        self.webrtcbin.connect('pad-added', self.on_pad_added)
        
        # Set STUN server (Google's public STUN server)
        self.webrtcbin.set_property('stun-server', 'stun://stun.l.google.com:19302')
        
        logger.info("Pipeline created successfully")
        
    def on_negotiation_needed(self, webrtc):
        """Handle negotiation needed signal"""
        logger.info("Negotiation needed - creating offer")
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, webrtc, None)
        webrtc.emit('create-offer', None, promise)
        
    def on_offer_created(self, promise, webrtc, user_data):
        """Handle offer creation"""
        promise.wait()
        reply = promise.get_reply()
        offer = reply['offer']
        
        logger.info("Offer created, setting local description")
        promise = Gst.Promise.new()
        webrtc.emit('set-local-description', offer, promise)
        promise.interrupt()
        
        # Send offer to Janus
        sdp_text = offer.sdp.as_text()
        logger.info(f"Local SDP Offer:\n{sdp_text}")
        
        asyncio.run_coroutine_threadsafe(
            self.send_offer_to_janus(sdp_text), 
            self.loop
        )
        
    def on_ice_candidate(self, webrtc, mline_index, candidate):
        """Handle ICE candidate"""
        logger.info(f"ICE candidate: {candidate}")
        asyncio.run_coroutine_threadsafe(
            self.send_ice_candidate(mline_index, candidate),
            self.loop
        )
        
    def on_pad_added(self, webrtc, pad):
        """Handle new pad added"""
        logger.info(f"Pad added: {pad.get_name()}")
        
    async def connect_to_janus(self):
        """Connect to Janus WebSocket server"""
        logger.info(f"Connecting to Janus at {self.janus_url}")
        self.websocket = await websockets.connect(self.janus_url)
        logger.info("Connected to Janus server")
        
        # Create session
        await self.create_session()
        
        # Attach to VideoRoom plugin
        await self.attach_plugin()
        
        # Join room as publisher
        await self.join_room()
        
    async def create_session(self):
        """Create Janus session"""
        message = {
            "janus": "create",
            "transaction": "create_session"
        }
        await self.websocket.send(json.dumps(message))
        
        response = await self.websocket.recv()
        data = json.loads(response)
        
        if data.get('janus') == 'success':
            self.session_id = data['data']['id']
            logger.info(f"Session created: {self.session_id}")
        else:
            raise Exception(f"Failed to create session: {data}")
            
    async def attach_plugin(self):
        """Attach to VideoRoom plugin"""
        message = {
            "janus": "attach",
            "plugin": "janus.plugin.videoroom",
            "transaction": "attach_plugin",
            "session_id": self.session_id
        }
        await self.websocket.send(json.dumps(message))
        
        response = await self.websocket.recv()
        data = json.loads(response)
        
        if data.get('janus') == 'success':
            self.handle_id = data['data']['id']
            logger.info(f"Plugin attached: {self.handle_id}")
        else:
            raise Exception(f"Failed to attach plugin: {data}")
            
    async def join_room(self):
        """Join video room as publisher"""
        message = {
            "janus": "message",
            "transaction": "join_room",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "body": {
                "request": "join",
                "room": self.room_id,
                "ptype": "publisher",
                "display": "Python GStreamer Client"
            }
        }
        await self.websocket.send(json.dumps(message))
        logger.info(f"Joining room {self.room_id}")
        
    async def send_offer_to_janus(self, sdp):
        """Send SDP offer to Janus"""
        message = {
            "janus": "message",
            "transaction": "publish",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "body": {
                "request": "publish",
                "audio": True,
                "video": True
            },
            "jsep": {
                "type": "offer",
                "sdp": sdp
            }
        }
        await self.websocket.send(json.dumps(message))
        logger.info("SDP offer sent to Janus")
        
    async def send_ice_candidate(self, mline_index, candidate):
        """Send ICE candidate to Janus"""
        if not self.session_id or not self.handle_id:
            return
            
        message = {
            "janus": "trickle",
            "transaction": "trickle",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "candidate": {
                "sdpMLineIndex": mline_index,
                "candidate": candidate
            }
        }
        await self.websocket.send(json.dumps(message))
        
    async def handle_janus_messages(self):
        """Handle incoming messages from Janus"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                logger.info(f"Received from Janus: {data.get('janus', 'unknown')}")
                
                # Handle SDP answer
                if 'jsep' in data:
                    jsep = data['jsep']
                    if jsep['type'] == 'answer':
                        logger.info("Received SDP answer from Janus")
                        logger.info(f"Remote SDP Answer:\n{jsep['sdp']}")
                        self.set_remote_description(jsep['sdp'])
                        
                # Handle ICE candidates
                if data.get('janus') == 'trickle' and 'candidate' in data:
                    candidate = data['candidate']
                    if candidate:
                        self.add_ice_candidate(candidate)
                        
                # Keep-alive
                if data.get('janus') == 'keepalive':
                    logger.debug("Received keepalive")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error handling Janus messages: {e}")
            
    def set_remote_description(self, sdp_text):
        """Set remote SDP description"""
        ret, sdp = GstSdp.SDPMessage.new_from_text(sdp_text)
        answer = GstWebRTC.WebRTCSessionDescription.new(
            GstWebRTC.WebRTCSDPType.ANSWER, sdp
        )
        promise = Gst.Promise.new()
        self.webrtcbin.emit('set-remote-description', answer, promise)
        promise.interrupt()
        logger.info("Remote description set")
        
    def add_ice_candidate(self, candidate):
        """Add ICE candidate"""
        mline_index = candidate.get('sdpMLineIndex', 0)
        candidate_str = candidate.get('candidate', '')
        self.webrtcbin.emit('add-ice-candidate', mline_index, candidate_str)
        logger.info(f"Added ICE candidate: {candidate_str}")
        
    async def start_streaming(self):
        """Start streaming to Janus"""
        # Create pipeline
        self.create_pipeline()
        
        # Connect to Janus
        await self.connect_to_janus()
        
        # Start pipeline
        logger.info("Starting GStreamer pipeline...")
        self.pipeline.set_state(Gst.State.PLAYING)
        
        # Handle Janus messages
        await self.handle_janus_messages()
        
    def stop(self):
        """Stop streaming"""
        if self.pipeline:
            logger.info("Stopping pipeline...")
            self.pipeline.set_state(Gst.State.NULL)
            
        if self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.websocket.close(),
                self.loop
            )
            
    def run(self):
        """Run the client"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            logger.info("Starting Janus WebRTC client...")
            self.loop.run_until_complete(self.start_streaming())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        finally:
            self.stop()
            self.loop.close()


def main():
    parser = argparse.ArgumentParser(
        description='Stream camera to Janus WebRTC server using GStreamer'
    )
    parser.add_argument(
        '--janus-url',
        default='ws://localhost:8188',
        help='Janus WebSocket URL (default: ws://localhost:8188)'
    )
    parser.add_argument(
        '--room-id',
        type=int,
        default=1234,
        help='Video room ID (default: 1234)'
    )
    parser.add_argument(
        '--camera',
        default='/dev/video0',
        help='Camera device (default: /dev/video0)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    # Create and run client
    client = JanusWebRTCClient(
        janus_url=args.janus_url,
        room_id=args.room_id,
        camera_device=args.camera
    )
    client.run()


if __name__ == '__main__':
    main()
