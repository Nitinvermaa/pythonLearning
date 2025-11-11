#!/usr/bin/env python3
"""
Publish a local camera feed to a Janus VideoRoom using GStreamer WebRTC.

This script:
  * Connects to a Janus server over the public WebSocket transport
  * Attaches to the janus.plugin.videoroom plugin as a publisher
  * Negotiates SDP using GStreamer's webrtcbin element
  * Streams the default /dev/video0 camera using VP8 over RTP

Prerequisites on Ubuntu (WSL):
  sudo apt update
  sudo apt install -y \
       python3-gi python3-aiohttp \
       gstreamer1.0-tools gstreamer1.0-plugins-good \
       gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
       gstreamer1.0-libav gir1.2-gst-plugins-base-1.0 \
       gir1.2-gst-plugins-bad-1.0 gir1.2-gst-webrtc-1.0

Usage example:
  python3 janus_webrtc_publisher.py \
      --janus-url ws://127.0.0.1:8188/ \
      --room-id 1234 \
      --display-name "wsl-camera"
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import signal
import uuid
from typing import Any, Dict, Optional

import aiohttp

import gi  # type: ignore

gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst, GstSdp, GstWebRTC  # type: ignore


class JanusPublisher:
    """Publishes a camera feed to Janus VideoRoom using GStreamer WebRTC."""

    def __init__(
        self,
        janus_url: str,
        room_id: int,
        display_name: str,
        video_device: str,
        stun_server: Optional[str],
        bitrate: int,
        log_stats_interval: int = 30,
    ) -> None:
        Gst.init(None)
        self.janus_url = janus_url.rstrip("/") + "/"
        self.room_id = room_id
        self.display_name = display_name
        self.video_device = video_device
        self.stun_server = stun_server
        self.target_bitrate = bitrate
        self.log_stats_interval = log_stats_interval

        self.http_session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        self.session_id: Optional[int] = None
        self.handle_id: Optional[int] = None
        self.publisher_id: Optional[int] = None

        self._transactions: Dict[str, asyncio.Future[Any]] = {}
        self._stop_event = asyncio.Event()
        self._ws_reader_task: Optional[asyncio.Task[None]] = None
        self._keepalive_task: Optional[asyncio.Task[None]] = None
        self._bus_watch_task: Optional[asyncio.Task[None]] = None
        self._stats_task: Optional[asyncio.Task[None]] = None

        self.pipeline: Optional[Gst.Element] = None
        self.webrtc: Optional[Gst.Element] = None
        self._negotiation_done = asyncio.Event()
        self._publishing = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def run(self) -> None:
        """Entry point for running the publisher."""
        self.loop = asyncio.get_running_loop()
        await self._connect_transport()

        self._ws_reader_task = asyncio.create_task(self._ws_reader(), name="janus-ws-reader")
        await self._create_session()
        await self._attach_plugin()
        await self._join_room()

        self._build_pipeline()
        self._bus_watch_task = asyncio.create_task(self._bus_watch(), name="gstreamer-bus-watch")
        self._keepalive_task = asyncio.create_task(self._keepalive_loop(), name="janus-keepalive")
        if self.log_stats_interval > 0:
            self._stats_task = asyncio.create_task(self._log_stats_loop(), name="webrtc-stats")

        # Wait until stop is requested (Ctrl+C, EOS, or error)
        await self._stop_event.wait()
        await self.shutdown()

    async def shutdown(self) -> None:
        """Tear down the connection and GStreamer pipeline."""
        if self._stop_event.is_set() and self.pipeline:
            logging.info("Shutting down pipeline and Janus session")

        if self.pipeline is not None:
            self.pipeline.set_state(Gst.State.NULL)

        if self._stats_task:
            self._stats_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stats_task
        if self._bus_watch_task:
            self._bus_watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._bus_watch_task
        if self._keepalive_task:
            self._keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keepalive_task
        if self._ws_reader_task:
            self._ws_reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ws_reader_task

        if self.handle_id and self.session_id:
            await self._safe_send_janus_message({"request": "leave"})

        await self._destroy_session()

        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.http_session:
            await self.http_session.close()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    async def _connect_transport(self) -> None:
        logging.info("Connecting to Janus at %s", self.janus_url)
        self.http_session = aiohttp.ClientSession()
        self.ws = await self.http_session.ws_connect(self.janus_url, receive_timeout=None)

    async def _create_session(self) -> None:
        response = await self._send({"janus": "create"})
        self._ensure_success(response, "create session")
        self.session_id = response["data"]["id"]
        logging.info("Created Janus session %s", self.session_id)

    async def _destroy_session(self) -> None:
        if not self.session_id:
            return
        try:
            await self._send({"janus": "destroy", "session_id": self.session_id})
            logging.info("Destroyed Janus session %s", self.session_id)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logging.debug("Failed to destroy session: %s", exc)
        finally:
            self.session_id = None

    async def _attach_plugin(self) -> None:
        assert self.session_id is not None
        response = await self._send(
            {"janus": "attach", "session_id": self.session_id, "plugin": "janus.plugin.videoroom"}
        )
        self._ensure_success(response, "attach videoroom plugin")
        self.handle_id = response["data"]["id"]
        logging.info("Attached to videoroom plugin with handle %s", self.handle_id)

    async def _join_room(self) -> None:
        body = {
            "request": "join",
            "ptype": "publisher",
            "room": self.room_id,
            "display": self.display_name,
        }
        await self._send_janus_message(body)
        logging.info("Join request sent for room %s as %s", self.room_id, self.display_name)

    def _build_pipeline(self) -> None:
        logging.info("Building GStreamer pipeline for device %s", self.video_device)
        pipeline_description = f"""
            webrtcbin name=webrtcbin
            v4l2src device={self.video_device} !
                queue !
                videoconvert !
                videorate !
                video/x-raw,framerate=30/1 !
                vp8enc deadline=1 keyframe-max-dist=30 !
                rtpvp8pay pt=96 !
                application/x-rtp,media=video,encoding-name=VP8,payload=96 !
                queue !
                webrtcbin.
        """

        # Remove redundant whitespace/newlines to avoid parsing issues
        pipeline_definition = " ".join(line.strip() for line in pipeline_description.splitlines() if line.strip())
        self.pipeline = Gst.parse_launch(pipeline_definition)
        self.webrtc = self.pipeline.get_by_name("webrtcbin")
        if self.webrtc is None:
            raise RuntimeError("Failed to find webrtcbin in the pipeline")

        if self.stun_server:
            self.webrtc.set_property("stun-server", self.stun_server)
        self.webrtc.set_property("bundle-policy", GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE)

        self.webrtc.connect("on-negotiation-needed", self._on_negotiation_needed)
        self.webrtc.connect("on-ice-candidate", self._on_ice_candidate)

    async def _ws_reader(self) -> None:
        assert self.ws is not None
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = json.loads(msg.data)
                    await self._handle_janus_message(payload)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    raise msg.data
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logging.error("WebSocket reader error: %s", exc)
            self._stop_event.set()

    async def _handle_janus_message(self, payload: Dict[str, Any]) -> None:
        transaction = payload.get("transaction")
        if transaction and transaction in self._transactions:
            future = self._transactions.pop(transaction)
            if not future.done():
                future.set_result(payload)
            return

        kind = payload.get("janus")
        if kind == "event":
            await self._handle_plugin_event(payload)
        elif kind == "trickle":
            self._handle_remote_candidate(payload)
        elif kind == "webrtcup":
            logging.info("WebRTC connection established with Janus")
        elif kind == "hangup":
            reason = payload.get("reason", "unknown")
            logging.warning("Janus hangup: %s", reason)
            self._stop_event.set()
        elif kind == "slowlink":
            logging.warning("Janus reports slow link: %s", payload.get("uplink"))
        elif kind == "keepalive":
            logging.debug("Keepalive acknowledged")
        elif kind == "error":
            error = payload.get("error", {})
            logging.error("Janus error: %s", error)
            self._stop_event.set()
        else:
            logging.debug("Unhandled Janus message: %s", payload)

    async def _handle_plugin_event(self, payload: Dict[str, Any]) -> None:
        plugindata = payload.get("plugindata", {})
        data = plugindata.get("data", {})
        event = data.get("videoroom")

        if event == "joined":
            self.publisher_id = data.get("id")
            logging.info("Joined room %s as publisher %s", self.room_id, self.publisher_id)
            if self.pipeline:
                self.pipeline.set_state(Gst.State.PLAYING)
        elif event == "event":
            configured = data.get("configured")
            if configured == "ok":
                logging.info("Publishing confirmed by Janus")
                self._negotiation_done.set()
            new_publishers = data.get("publishers", [])
            if new_publishers:
                joined_ids = ", ".join(str(pub.get("id")) for pub in new_publishers)
                logging.info("Existing publishers in room: %s", joined_ids)
        elif event == "destroyed":
            logging.warning("Room %s has been destroyed", self.room_id)
            self._stop_event.set()
        elif event == "slow_link":
            logging.warning("Janus reports slow uplink")
        else:
            logging.debug("Unhandled plugin event: %s", data)

        jsep = payload.get("jsep")
        if jsep:
            await self._handle_remote_jsep(jsep)

    def _handle_remote_candidate(self, payload: Dict[str, Any]) -> None:
        if not self.webrtc:
            return
        candidate = payload.get("candidate")
        if not candidate:
            return
        if candidate.get("completed"):
            logging.debug("End of remote candidates")
            self.webrtc.emit("add-ice-candidate", -1, "")
            return

        cand_str = candidate.get("candidate")
        sdp_mline_index = int(candidate.get("sdpMLineIndex", 0))
        if cand_str:
            self.webrtc.emit("add-ice-candidate", sdp_mline_index, cand_str)
            logging.debug("Added remote ICE candidate (mline=%s)", sdp_mline_index)

    async def _handle_remote_jsep(self, jsep: Dict[str, Any]) -> None:
        if not self.webrtc:
            return
        if jsep.get("type") != "answer":
            logging.warning("Received unsupported JSEP type %s", jsep.get("type"))
            return

        sdp_text = jsep.get("sdp", "")
        ok, sdp_message = GstSdp.SDPMessage.new()
        if ok != GstSdp.SDPResult.OK:
            raise RuntimeError("Failed to allocate SDP message")

        parse_result = GstSdp.sdp_message_parse_buffer(sdp_text.encode("utf-8"), sdp_message)
        if parse_result != GstSdp.SDPResult.OK:
            raise RuntimeError(f"Failed to parse remote SDP: {parse_result}")

        answer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.ANSWER, sdp_message)
        self.webrtc.emit("set-remote-description", answer)
        logging.info("Remote SDP answer applied")

    def _on_negotiation_needed(self, element: Gst.Element) -> None:
        if not self.loop:
            logging.error("Asyncio loop missing during negotiation")
            return
        if self._publishing:
            logging.debug("Negotiation already in progress")
            return

        logging.info("Starting SDP offer negotiation")
        self._publishing = True
        promise = Gst.Promise.new_with_change_func(self._on_offer_created, element)
        element.emit("create-offer", None, promise)

    def _on_offer_created(self, promise: Gst.Promise, element: Gst.Element, _data: Any) -> None:
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value("offer")
        element.emit("set-local-description", offer)
        sdp_text = offer.sdp.as_text()

        if not self.loop:
            logging.error("Asyncio loop unavailable; cannot send offer")
            return
        asyncio.run_coroutine_threadsafe(self._publish_offer(sdp_text), self.loop)

    async def _publish_offer(self, sdp: str) -> None:
        body = {
            "request": "publish",
            "audio": False,
            "video": True,
            "bitrate": self.target_bitrate,
        }
        jsep = {"type": "offer", "sdp": sdp}
        await self._send_janus_message(body, jsep=jsep)
        logging.info("SDP offer sent to Janus")

    def _on_ice_candidate(self, element: Gst.Element, mlineindex: int, candidate: str) -> None:
        if not self.loop:
            logging.error("Asyncio loop unavailable for ICE candidate")
            return
        asyncio.run_coroutine_threadsafe(
            self._send_trickle_candidate(candidate, mlineindex),
            self.loop,
        )

    async def _send_trickle_candidate(self, candidate: str, sdp_mline_index: int) -> None:
        if not self.ws or not self.session_id or not self.handle_id:
            return
        payload = {
            "janus": "trickle",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "candidate": {
                "candidate": candidate,
                "sdpMid": str(sdp_mline_index),
                "sdpMLineIndex": sdp_mline_index,
            },
        }
        await self.ws.send_json(payload)
        logging.debug("Sent local ICE candidate (mline=%s)", sdp_mline_index)

    async def _send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        txn = uuid.uuid4().hex
        payload["transaction"] = txn
        future = asyncio.get_running_loop().create_future()
        self._transactions[txn] = future
        await self.ws.send_json(payload)  # type: ignore[arg-type]
        return await future

    async def _send_janus_message(self, body: Dict[str, Any], jsep: Optional[Dict[str, Any]] = None) -> None:
        assert self.session_id is not None and self.handle_id is not None
        payload: Dict[str, Any] = {
            "janus": "message",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "body": body,
        }
        if jsep:
            payload["jsep"] = jsep
        response = await self._send(payload)
        if response.get("janus") == "error":
            error = response.get("error", {})
            raise RuntimeError(f"Janus rejected message: {error}")
        # For plugin messages, Janus typically returns an ack; the real response is asynchronous.

    async def _safe_send_janus_message(self, body: Dict[str, Any]) -> None:
        try:
            await self._send_janus_message(body)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logging.debug("Failed to send message during shutdown: %s", exc)

    async def _keepalive_loop(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(30)
            if not self.session_id:
                continue
            payload = {
                "janus": "keepalive",
                "session_id": self.session_id,
                "transaction": uuid.uuid4().hex,
            }
            try:
                await self.ws.send_json(payload)  # type: ignore[arg-type]
            except Exception as exc:
                logging.warning("Keepalive failed: %s", exc)
                self._stop_event.set()

    async def _log_stats_loop(self) -> None:
        if not self.webrtc:
            return
        while not self._stop_event.is_set():
            await asyncio.sleep(self.log_stats_interval)
            try:
                promise = Gst.Promise.new()
                self.webrtc.emit("get-stats", None, promise)
                promise.wait()
                stats = promise.get_reply()
                logging.debug("WebRTC stats: %s", stats)
            except Exception:
                logging.debug("Unable to fetch WebRTC stats", exc_info=True)

    async def _bus_watch(self) -> None:
        if not self.pipeline:
            return
        bus = self.pipeline.get_bus()
        while not self._stop_event.is_set():
            msg = bus.timed_pop(1 * Gst.SECOND)
            if msg is None:
                continue
            message_type = msg.type
            if message_type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                logging.error("GStreamer error: %s (%s)", err, debug)
                self._stop_event.set()
            elif message_type == Gst.MessageType.EOS:
                logging.info("Pipeline signalled EOS")
                self._stop_event.set()

    @staticmethod
    def _ensure_success(response: Dict[str, Any], context: str) -> None:
        if response.get("janus") != "success":
            raise RuntimeError(f"Failed to {context}: {response}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish a camera feed to Janus via GStreamer WebRTC.")
    parser.add_argument("--janus-url", default="ws://127.0.0.1:8188/", help="Janus WebSocket URL (default: ws://127.0.0.1:8188/)")
    parser.add_argument("--room-id", type=int, default=1234, help="VideoRoom numeric ID to publish to (default: 1234)")
    parser.add_argument("--display-name", default="gstreamer-publisher", help="Display name shown in Janus")
    parser.add_argument("--video-device", default="/dev/video0", help="V4L2 video device to stream (default: /dev/video0)")
    parser.add_argument("--stun-server", default="stun://stun.l.google.com:19302", help="STUN server URI")
    parser.add_argument("--bitrate", type=int, default=1_000_000, help="Target publishing bitrate in bps (default: 1_000_000)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging verbosity")
    parser.add_argument("--stats-interval", type=int, default=30, help="Interval in seconds for verbose WebRTC stats logging (0 disables)")
    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )


async def main_async(args: argparse.Namespace) -> None:
    configure_logging(args.log_level)

    publisher = JanusPublisher(
        janus_url=args.janus_url,
        room_id=args.room_id,
        display_name=args.display_name,
        video_device=args.video_device,
        stun_server=args.stun_server,
        bitrate=args.bitrate,
        log_stats_interval=args.stats_interval,
    )

    def handle_signal() -> None:
        logging.info("Signal received, stopping...")
        publisher._stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    await publisher.run()


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
