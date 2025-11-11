#!/usr/bin/env python3
"""
Simple test script to verify camera access and GStreamer installation
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import sys

Gst.init(None)

def test_camera(device="/dev/video0"):
    """Test if camera is accessible via GStreamer"""
    print(f"Testing camera at {device}...")
    
    # Simple pipeline to display camera feed
    pipeline_str = f"""
    v4l2src device={device} ! 
    videoconvert ! 
    autovideosink
    """
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        pipeline.set_state(Gst.State.PLAYING)
        
        print("Camera test started. Press Ctrl+C to stop...")
        print("If you see a window with camera feed, the camera is working!")
        
        loop = GLib.MainLoop()
        
        # Handle bus messages
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        
        def on_message(bus, message):
            t = message.type
            if t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print(f"Error: {err}, {debug}")
                loop.quit()
            elif t == Gst.MessageType.EOS:
                print("End of stream")
                loop.quit()
                
        bus.connect("message", on_message)
        
        try:
            loop.run()
        except KeyboardInterrupt:
            print("\nStopped by user")
            
        pipeline.set_state(Gst.State.NULL)
        print("Camera test completed")
        
    except Exception as e:
        print(f"Error: {e}")
        return False
        
    return True

def list_video_devices():
    """List available video devices"""
    import os
    print("\nLooking for video devices...")
    devices = []
    for i in range(10):
        device = f"/dev/video{i}"
        if os.path.exists(device):
            devices.append(device)
            print(f"  Found: {device}")
    
    if not devices:
        print("  No video devices found!")
        print("\nOn WSL, you might need to:")
        print("  1. Install usbipd on Windows")
        print("  2. Attach USB camera to WSL")
        print("  3. See: https://learn.microsoft.com/en-us/windows/wsl/connect-usb")
    
    return devices

if __name__ == "__main__":
    print("=" * 60)
    print("Camera and GStreamer Test")
    print("=" * 60)
    
    # List devices
    devices = list_video_devices()
    
    if devices:
        print(f"\nTesting first device: {devices[0]}")
        test_camera(devices[0])
    else:
        print("\nNo camera devices found. Please check your camera setup.")
        sys.exit(1)
