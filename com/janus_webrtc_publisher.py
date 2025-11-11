#!/usr/bin/env python3
"""
GStreamer WebRTC publisher for Janus.

This script captures audio/video from local sources, negotiates WebRTC using SDP
through the Janus VideoRoom plugin, and publishes the media into a room.

Example:
    python com/janus_webrtc_publisher.py \
        --janus-url ws://127.0.0.1:8188 \
        --room 1234 \
        --display mypublisher
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import string
import threading
from dataclasses import dataclass
from random import choices
from typing import Any, Dict, Optional

import websockets
from websockets.client import WebSocketClientProtocol

from gi.repository import GLib, Gst, GstSdp, GstWebRTC


def _random_transaction() -> str:
    return "".join(choices(string.ascii_letters + string.digits, k=12))


@dataclass
class AppConfig:
    janus_url: str
    room_id: int
    display: str
    secret: Optional[str] = None
    token: Optional[str] = None
    video_source: str = "v4l2src device=/dev/video0"
    audio_source: str = "pulsesrc"
    stun_server: Optional[str] = "stun://stun.l.google.com:19302"
    turn_server: Optional[str] = None
    video_bitrate: int = 1_500_000  # bits per second
    audio_bitrate: int = 128_000  # bits per second
    heartbeat_interval: int = 30

    def to_publish_body(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "request": "publish",
            "audio": True,
            "video": True,
            "bitrate": self.video_bitrate,
        }
        if self.secret:
            body["secret"] = self.secret
        if self.token:
            body["token"] = self.token
        return body


class JanusError(RuntimeError):
    """Raised when Janus returns an error payload."""


class JanusPublisher:
    def __init__(self, config: AppConfig, loop: asyncio.AbstractEventLoop):
        self.config = config
        self.loop = loop
        self.ws: Optional[WebSocketClientProtocol] = None
        self.session_id: Optional[int] = None
        self.handle_id: Optional[int] = None
        self.transactions: Dict[str, asyncio.Future] = {}
        self.running = False

        self.pipeline: Optional[Gst.Element] = None
        self.webrtc: Optional[Gst.Element] = None
        self.glib_loop = GLib.MainLoop()
        self.glib_thread: Optional[threading.Thread] = None

        self._joined_async = asyncio.Event()
        self._joined_thread = threading.Event()
        self._pending_negotiation = False

    async def start(self) -> None:
        Gst.init(None)
        self._build_pipeline()

        self.glib_thread = threading.Thread(
            target=self._run_glib_loop, name="glib-mainloop", daemon=True
        )
        self.glib_thread.start()

        self.running = True
        await self._connect()
        await self._create_session()
        await self._attach_plugin()
        await self._join_room()

        await self._joined_async.wait()
        logging.info("Joined Janus room %s as %s", self.config.room_id, self.config.display)

        GLib.idle_add(self.pipeline.set_state, Gst.State.PLAYING)

        await asyncio.gather(
            self._heartbeat(),
            self._ws_listener(),
            return_exceptions=False,
        )

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        logging.info("Shutting down publisher")

        if self.pipeline is not None:
            GLib.idle_add(self.pipeline.set_state, Gst.State.NULL)

        if self.handle_id and self.session_id:
            await self._send(
                {
                    "janus": "message",
                    "session_id": self.session_id,
                    "handle_id": self.handle_id,
                    "body": {"request": "unpublish"},
                }
            )
            await self._send(
                {
                    "janus": "detach",
                    "session_id": self.session_id,
                    "handle_id": self.handle_id,
                }
            )
        if self.session_id:
            await self._send({"janus": "destroy", "session_id": self.session_id})

        if self.ws:
            await self.ws.close()

        if self.glib_loop.is_running():
            self.glib_loop.quit()
        if self.glib_thread and self.glib_thread.is_alive():
            self.glib_thread.join(timeout=2)

    def _run_glib_loop(self) -> None:
        try:
            self.glib_loop.run()
        except Exception:
            logging.exception("GLib main loop error")

    async def _connect(self) -> None:
        logging.info("Connecting to Janus at %s", self.config.janus_url)
        self.ws = await websockets.connect(self.config.janus_url, ping_interval=None)

    async def _create_session(self) -> None:
        response = await self._request({"janus": "create"})
        self.session_id = response["data"]["id"]
        logging.info("Created Janus session %s", self.session_id)

    async def _attach_plugin(self) -> None:
        if self.session_id is None:
            raise RuntimeError("Session not created")
        response = await self._request(
            {
                "janus": "attach",
                "session_id": self.session_id,
                "plugin": "janus.plugin.videoroom",
            }
        )
        self.handle_id = response["data"]["id"]
        logging.info("Attached to VideoRoom plugin (%s)", self.handle_id)

    async def _join_room(self) -> None:
        if self.session_id is None or self.handle_id is None:
            raise RuntimeError("Plugin not attached")
        body: Dict[str, Any] = {
            "request": "join",
            "ptype": "publisher",
            "room": self.config.room_id,
            "display": self.config.display,
        }
        if self.config.token:
            body["token"] = self.config.token
        response = await self._request(
            {
                "janus": "message",
                "session_id": self.session_id,
                "handle_id": self.handle_id,
                "body": body,
            }
        )
        plugindata = response.get("plugindata", {}).get("data", {})
        if plugindata.get("videoroom") != "joined":
            raise JanusError(f"Join failed: {plugindata}")
        self._joined_async.set()
        self._joined_thread.set()
        logging.info("Publisher ID: %s", plugindata.get("id"))
        if self._pending_negotiation:
            GLib.idle_add(self._trigger_offer)

    async def _heartbeat(self) -> None:
        if self.session_id is None:
            return
        try:
            while self.running:
                await asyncio.sleep(self.config.heartbeat_interval)
                await self._send({"janus": "keepalive", "session_id": self.session_id})
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.exception("Heartbeat task failed")

    async def _ws_listener(self) -> None:
        assert self.ws is not None
        async for raw in self.ws:
            message = json.loads(raw)
            transaction = message.get("transaction")

            if transaction and transaction in self.transactions:
                if message["janus"] == "ack":
                    continue
                future = self.transactions.pop(transaction)
                if message.get("janus") == "error":
                    error_code = message.get("error", {}).get("code")
                    error_reason = message.get("error", {}).get("reason")
                    future.set_exception(JanusError(f"{error_code}: {error_reason}"))
                else:
                    future.set_result(message)
                continue

            kind = message.get("janus")
            if kind == "webrtcup":
                logging.info("Janus reports WebRTC is up")
            elif kind == "media":
                logging.debug("Media event: %s", message)
            elif kind == "trickle":
                await self._handle_remote_candidate(message)
            elif kind == "event":
                await self._handle_plugin_event(message)
            elif kind == "hangup":
                logging.warning("Janus hangup: %s", message.get("reason"))
                await self.stop()
                break
            elif kind == "error":
                logging.error("Janus error outside transaction: %s", message)
            else:
                logging.debug("Unhandled message: %s", message)

    async def _handle_plugin_event(self, message: Dict[str, Any]) -> None:
        plugindata = message.get("plugindata", {}).get("data", {})
        event = plugindata.get("videoroom")
        if event == "joined":
            if not self._joined_async.is_set():
                self._joined_async.set()
                self._joined_thread.set()
                logging.info("Publisher ID: %s", plugindata.get("id"))
                if self._pending_negotiation:
                    GLib.idle_add(self._trigger_offer)
        elif event == "event":
            logging.debug("Plugin event: %s", plugindata)
        elif event == "destroyed":
            logging.warning("Room %s was destroyed", self.config.room_id)
            await self.stop()
            return

        jsep = message.get("jsep")
        if jsep:
            self._set_remote_description(jsep)

    async def _handle_remote_candidate(self, message: Dict[str, Any]) -> None:
        candidate = message.get("candidate")
        if not candidate or "candidate" not in candidate:
            return
        sdp_mline = candidate.get("sdpMLineIndex", -1)
        sdp_candidate = candidate["candidate"]

        def _add_candidate() -> bool:
            if self.webrtc is None:
                return False
            logging.debug("Adding remote candidate (mline %s)", sdp_mline)
            self.webrtc.emit("add-ice-candidate", sdp_mline, sdp_candidate)
            return False

        GLib.idle_add(_add_candidate)

    def _set_remote_description(self, jsep: Dict[str, Any]) -> None:
        sdp_type = jsep.get("type")
        sdp_text = jsep.get("sdp")
        if sdp_type not in {"answer", "offer"} or not sdp_text:
            logging.error("Invalid JSEP from Janus: %s", jsep)
            return

        def _apply_remote() -> bool:
            if self.webrtc is None:
                return False
            res, sdpmsg = GstSdp.sdp_message_new_from_text(sdp_text)
            if res != GstSdp.SDPResult.OK:
                logging.error("Failed to parse remote SDP: %s", res)
                return False
            desc_type = (
                GstWebRTC.WebRTCSDPType.ANSWER if sdp_type == "answer" else GstWebRTC.WebRTCSDPType.OFFER
            )
            desc = GstWebRTC.WebRTCSessionDescription.new(desc_type, sdpmsg)
            logging.info("Setting remote description (%s)", sdp_type)
            self.webrtc.emit("set-remote-description", desc)
            return False

        GLib.idle_add(_apply_remote)

    def _build_pipeline(self) -> None:
        pipeline_description = (
            "webrtcbin name=webrtcbin bundle-policy=max-bundle "
            f"{self.config.video_source} ! queue ! videoconvert ! queue ! "
            f"vp8enc deadline=1 target-bitrate={self.config.video_bitrate} ! rtpvp8pay pt=96 ! "
            "application/x-rtp,media=video,encoding-name=VP8,payload=96 ! webrtcbin. "
            f"{self.config.audio_source} ! queue ! audioconvert ! audioresample ! queue ! "
            f"opusenc bitrate={self.config.audio_bitrate} ! rtpopuspay pt=111 ! "
            "application/x-rtp,media=audio,encoding-name=OPUS,payload=111 ! webrtcbin."
        )

        self.pipeline = Gst.parse_launch(pipeline_description)
        self.webrtc = self.pipeline.get_by_name("webrtcbin")
        if self.webrtc is None:
            raise RuntimeError("Failed to create webrtcbin")

        if self.config.stun_server:
            self.webrtc.set_property("stun-server", self.config.stun_server)
        if self.config.turn_server:
            self.webrtc.set_property("turn-server", self.config.turn_server)

        self.webrtc.connect("on-negotiation-needed", self._on_negotiation_needed)
        self.webrtc.connect("on-ice-candidate", self._on_ice_candidate)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message) -> None:
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, dbg = message.parse_error()
            logging.error("Pipeline error: %s (debug: %s)", err, dbg)
        elif t == Gst.MessageType.WARNING:
            err, dbg = message.parse_warning()
            logging.warning("Pipeline warning: %s (debug: %s)", err, dbg)
        elif t == Gst.MessageType.EOS:
            logging.info("Pipeline reached EOS")
            GLib.idle_add(self.pipeline.set_state, Gst.State.NULL)

    def _on_negotiation_needed(self, webrtcbin: Gst.Element) -> None:
        if not self._joined_thread.is_set():
            logging.debug("Negotiation requested before join; deferring")
            self._pending_negotiation = True
            return
        self._trigger_offer()

    def _trigger_offer(self) -> bool:
        if self.webrtc is None or not self.running:
            return False

        def _offer_created(promise: Gst.Promise, _data: Optional[Any]) -> None:
            promise.wait()
            reply = promise.get_reply()
            offer = reply.get_value("offer")
            self.webrtc.emit("set-local-description", offer)
            sdp_text = offer.sdp.as_text()
            asyncio.run_coroutine_threadsafe(self._send_offer(sdp_text), self.loop)

        logging.info("Creating SDP offer")
        promise = Gst.Promise.new_with_change_func(_offer_created, None)
        self.webrtc.emit("create-offer", None, promise)
        return False

    def _on_ice_candidate(self, element: Gst.Element, mline_index: int, candidate: str) -> None:
        if not self.running or self.session_id is None or self.handle_id is None:
            return

        payload: Dict[str, Any]
        if candidate:
            payload = {"candidate": candidate, "sdpMLineIndex": mline_index}
        else:
            payload = {"completed": True}
        asyncio.run_coroutine_threadsafe(self._trickle(payload), self.loop)

    async def _trickle(self, candidate: Dict[str, Any]) -> None:
        if self.session_id is None or self.handle_id is None or self.ws is None:
            return
        message = {
            "janus": "trickle",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "candidate": candidate,
        }
        await self.ws.send(json.dumps(message))

    async def _send_offer(self, sdp: str) -> None:
        if self.session_id is None or self.handle_id is None:
            raise RuntimeError("Cannot send offer without session and handle")

        body = self.config.to_publish_body()
        request = {
            "janus": "message",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "body": body,
            "jsep": {"type": "offer", "sdp": sdp},
        }
        await self._request(request)

    async def _send(self, payload: Dict[str, Any]) -> None:
        if self.ws is None:
            raise RuntimeError("WebSocket not connected")
        await self.ws.send(json.dumps(payload))

    async def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.ws is None:
            raise RuntimeError("WebSocket not connected")

        transaction = _random_transaction()
        payload["transaction"] = transaction
        future: asyncio.Future = self.loop.create_future()
        self.transactions[transaction] = future

        await self.ws.send(json.dumps(payload))
        response = await future

        kind = response.get("janus")
        if kind == "error":
            error = response.get("error", {})
            raise JanusError(f"{error.get('code')}: {error.get('reason')}")
        if kind not in {"success", "event"}:
            logging.debug("Unexpected response kind: %s", kind)
        return response


async def run_app(config: AppConfig) -> None:
    loop = asyncio.get_running_loop()
    app = JanusPublisher(config, loop)

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        if not stop_event.is_set():
            stop_event.set()
            asyncio.create_task(app.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            signal.signal(sig, lambda *_: asyncio.create_task(app.stop()))

    try:
        await app.start()
    except asyncio.CancelledError:
        pass
    except Exception:
        logging.exception("Publisher stopped with error")
    finally:
        await app.stop()


def parse_args() -> AppConfig:
    parser = argparse.ArgumentParser(description="Publish a camera feed to Janus via WebRTC (GStreamer).")
    parser.add_argument("--janus-url", default="ws://127.0.0.1:8188", help="Janus WebSocket base URL.")
    parser.add_argument("--room", type=int, required=True, help="VideoRoom numeric ID to publish into.")
    parser.add_argument("--display", default="gstreamer-publisher", help="Display name shown in Janus.")
    parser.add_argument("--secret", help="Room secret if configured.")
    parser.add_argument("--token", help="Token if the room requires authentication.")
    parser.add_argument(
        "--video-source",
        default="v4l2src device=/dev/video0",
        help="GStreamer source element for video (e.g. 'videotestsrc is-live=true').",
    )
    parser.add_argument(
        "--audio-source",
        default="pulsesrc",
        help="GStreamer source element for audio (e.g. 'autoaudiosrc').",
    )
    parser.add_argument(
        "--stun",
        dest="stun_server",
        default="stun://stun.l.google.com:19302",
        help="Optional STUN server URI.",
    )
    parser.add_argument("--turn", dest="turn_server", help="Optional TURN server URI (user:pass@host:port?transport=udp).")
    parser.add_argument(
        "--video-bitrate",
        type=int,
        default=1_500_000,
        help="Video target bitrate in bits per second for vp8enc.",
    )
    parser.add_argument(
        "--audio-bitrate",
        type=int,
        default=128_000,
        help="Audio bitrate in bits per second for opusenc.",
    )
    parser.add_argument(
        "--heartbeat",
        type=int,
        default=30,
        help="Keepalive interval in seconds.",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING...).")

    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return AppConfig(
        janus_url=args.janus_url,
        room_id=args.room,
        display=args.display,
        secret=args.secret,
        token=args.token,
        video_source=args.video_source,
        audio_source=args.audio_source,
        stun_server=args.stun_server,
        turn_server=args.turn_server,
        video_bitrate=args.video_bitrate,
        audio_bitrate=args.audio_bitrate,
        heartbeat_interval=args.heartbeat,
    )


def main() -> None:
    config = parse_args()
    asyncio.run(run_app(config))


if __name__ == "__main__":
    main()
