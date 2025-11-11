#!/usr/bin/env python3
"""
Example: How to get SDP content from Janus
Demonstrates different ways to retrieve and display SDP from Janus server
"""

import asyncio
import aiohttp
import json
import random
import string


class JanusSDPExtractor:
    """Helper class to extract SDP from Janus responses"""
    
    def __init__(self, janus_url="http://localhost:8088/janus"):
        self.janus_url = janus_url
        self.session_id = None
        self.handle_id = None
    
    def _generate_transaction(self):
        """Generate a random transaction ID"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
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
                    print(f"✓ Created session: {self.session_id}")
                    return True
                else:
                    print(f"✗ Failed to create session: {data}")
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
                    print(f"✓ Attached to plugin: {self.handle_id}")
                    return True
                else:
                    print(f"✗ Failed to attach plugin: {data}")
                    return False
    
    async def join_room_and_get_sdp(self, room_id=1234, display_name="SDP Extractor"):
        """
        Join a room and get SDP answer from Janus
        
        This demonstrates getting SDP when joining as a viewer (subscriber)
        """
        async with aiohttp.ClientSession() as session:
            # First, create a dummy SDP offer to trigger Janus to send an answer
            # In a real scenario, you'd create this from your WebRTC client
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
                        "room": room_id,
                        "display": display_name
                    }
                }
            ) as resp:
                data = await resp.json()
                return self._extract_sdp_from_response(data)
    
    async def publish_and_get_sdp(self, room_id=1234, sdp_offer=None):
        """
        Publish to a room and get SDP answer from Janus
        
        This is what happens when you publish (send video)
        """
        if not sdp_offer:
            sdp_offer = self._create_dummy_sdp_offer()
        
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
                return self._extract_sdp_from_response(data)
    
    def _extract_sdp_from_response(self, janus_response):
        """
        Extract SDP from Janus response
        
        Janus responses have SDP in the 'jsep' field:
        {
            "janus": "success",
            "data": {...},
            "jsep": {
                "type": "answer",  # or "offer"
                "sdp": "v=0\r\no=..."  # The SDP content
            }
        }
        """
        if janus_response.get("janus") != "success":
            print(f"✗ Janus error: {janus_response}")
            return None
        
        jsep = janus_response.get("jsep")
        if not jsep:
            print("✗ No jsep field in response")
            return None
        
        sdp_type = jsep.get("type")  # "offer" or "answer"
        sdp_content = jsep.get("sdp")  # The actual SDP string
        
        if not sdp_content:
            print("✗ No SDP content in jsep")
            return None
        
        return {
            "type": sdp_type,
            "sdp": sdp_content,
            "full_jsep": jsep
        }
    
    def _create_dummy_sdp_offer(self):
        """
        Create a minimal SDP offer for testing
        In real usage, this would come from your WebRTC client (GStreamer, etc.)
        """
        return """v=0
o=- 0 0 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=msid-semantic: WMS
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:test
a=ice-pwd:testpwd
a=fingerprint:sha-256 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
a=setup:actpass
a=mid:0
a=sendonly
a=rtcp-mux
a=rtpmap:96 VP8/90000
a=ssrc:1234 cname:test
"""
    
    def display_sdp(self, sdp_data):
        """Pretty print SDP content"""
        if not sdp_data:
            print("No SDP data to display")
            return
        
        print("\n" + "=" * 60)
        print(f"SDP {sdp_data['type'].upper()}")
        print("=" * 60)
        print(sdp_data['sdp'])
        print("=" * 60)
        
        # Parse and show key SDP attributes
        sdp_lines = sdp_data['sdp'].split('\n')
        print("\nKey SDP Information:")
        print("-" * 60)
        
        for line in sdp_lines:
            line = line.strip()
            if line.startswith('v='):
                print(f"Version: {line[2:]}")
            elif line.startswith('o='):
                print(f"Origin: {line[2:50]}...")
            elif line.startswith('m='):
                print(f"Media: {line[2:]}")
            elif line.startswith('a=ice-ufrag:'):
                print(f"ICE ufrag: {line[13:]}")
            elif line.startswith('a=ice-pwd:'):
                print(f"ICE pwd: {line[11:]}...")
            elif line.startswith('a=fingerprint:'):
                print(f"Fingerprint: {line[14:50]}...")
            elif line.startswith('a=candidate:'):
                print(f"Candidate: {line[12:80]}...")
    
    async def get_sdp_from_event(self):
        """
        Get SDP from Janus events (long polling)
        Janus can send events with SDP updates
        """
        if not self.session_id or not self.handle_id:
            print("✗ Must create session and attach plugin first")
            return None
        
        async with aiohttp.ClientSession() as session:
            # Long poll for events
            async with session.get(
                f"{self.janus_url}/{self.session_id}/{self.handle_id}",
                params={"maxev": 1},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("janus") == "event":
                        return self._extract_sdp_from_response(data)
                return None


async def example_get_sdp_from_publish():
    """Example: Get SDP answer when publishing"""
    print("\n" + "=" * 60)
    print("Example 1: Get SDP Answer from Janus when Publishing")
    print("=" * 60)
    
    extractor = JanusSDPExtractor()
    
    # Create session
    if not await extractor.create_session():
        return
    
    # Attach to plugin
    if not await extractor.attach_plugin():
        return
    
    # Publish and get SDP answer
    print("\nPublishing to room 1234...")
    sdp_data = await extractor.publish_and_get_sdp(room_id=1234)
    
    if sdp_data:
        extractor.display_sdp(sdp_data)
        
        # Save SDP to file
        with open("janus_sdp_answer.txt", "w") as f:
            f.write(sdp_data['sdp'])
        print("\n✓ SDP saved to janus_sdp_answer.txt")
    else:
        print("✗ Failed to get SDP from Janus")


async def example_parse_existing_response():
    """Example: Parse SDP from an existing Janus response"""
    print("\n" + "=" * 60)
    print("Example 2: Parse SDP from Janus Response")
    print("=" * 60)
    
    # Example Janus response (what you'd get from the API)
    example_response = {
        "janus": "success",
        "session_id": 1234567890,
        "transaction": "abc123",
        "data": {
            "id": 9876543210
        },
        "jsep": {
            "type": "answer",
            "sdp": """v=0
o=- 1234567890 2 IN IP4 127.0.0.1
s=Janus
t=0 0
a=group:BUNDLE 0
a=msid-semantic: WMS janus
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:janus
a=ice-pwd:januspwd123456
a=fingerprint:sha-256 AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99
a=setup:active
a=mid:0
a=recvonly
a=rtcp-mux
a=rtpmap:96 VP8/90000
a=ssrc:1111 cname:janus
a=candidate:1 1 UDP 2130706431 192.168.1.100 5000 typ host
a=candidate:2 1 UDP 1694498815 203.0.113.1 5001 typ srflx
"""
        }
    }
    
    extractor = JanusSDPExtractor()
    sdp_data = extractor._extract_sdp_from_response(example_response)
    
    if sdp_data:
        extractor.display_sdp(sdp_data)


async def example_get_sdp_from_events():
    """Example: Get SDP from Janus events"""
    print("\n" + "=" * 60)
    print("Example 3: Get SDP from Janus Events (Long Polling)")
    print("=" * 60)
    
    extractor = JanusSDPExtractor()
    
    if not await extractor.create_session():
        return
    
    if not await extractor.attach_plugin():
        return
    
    print("\nLong polling for events (timeout: 30s)...")
    print("(In a real scenario, Janus would send events after WebRTC negotiation)")
    
    sdp_data = await extractor.get_sdp_from_event()
    
    if sdp_data:
        extractor.display_sdp(sdp_data)
    else:
        print("No SDP in events (this is normal if no active session)")


def show_sdp_structure():
    """Show the structure of SDP content"""
    print("\n" + "=" * 60)
    print("SDP Structure Explanation")
    print("=" * 60)
    
    print("""
SDP (Session Description Protocol) content from Janus typically includes:

1. Session-level attributes:
   - v=0                    (version)
   - o=...                  (origin: username, session ID, etc.)
   - s=-                    (session name)
   - t=0 0                  (timing)

2. Media description (m=):
   - m=video 9 UDP/TLS/RTP/SAVPF 96
     (media type, port, protocol, format)

3. Connection info (c=):
   - c=IN IP4 0.0.0.0       (connection address)

4. ICE attributes:
   - a=ice-ufrag:...        (ICE username fragment)
   - a=ice-pwd:...          (ICE password)
   - a=candidate:...        (ICE candidates for NAT traversal)

5. DTLS fingerprint:
   - a=fingerprint:sha-256 ...  (DTLS certificate fingerprint)

6. Media attributes:
   - a=rtpmap:96 VP8/90000  (codec information)
   - a=ssrc:...             (synchronization source)

In Janus responses, SDP is in the 'jsep' field:
{
    "jsep": {
        "type": "answer",    # or "offer"
        "sdp": "v=0\\r\\n..."  # The SDP string
    }
}
""")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Get SDP content from Janus")
    parser.add_argument("--janus-url", default="http://localhost:8088/janus",
                       help="Janus server URL")
    parser.add_argument("--example", type=int, choices=[1, 2, 3, 4], default=4,
                       help="Example to run (1=publish, 2=parse, 3=events, 4=all)")
    
    args = parser.parse_args()
    
    if args.example == 1:
        await example_get_sdp_from_publish()
    elif args.example == 2:
        await example_parse_existing_response()
    elif args.example == 3:
        await example_get_sdp_from_events()
    elif args.example == 4:
        show_sdp_structure()
        await example_parse_existing_response()
        # Uncomment to test with real Janus server:
        # await example_get_sdp_from_publish()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}", exc_info=True)
