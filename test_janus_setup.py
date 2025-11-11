#!/usr/bin/env python3
"""
Test script to verify Janus and GStreamer setup
"""

import sys
import subprocess
import gi

def test_gstreamer():
    """Test if GStreamer is installed and accessible"""
    print("Testing GStreamer installation...")
    try:
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        Gst.init(None)
        print("✓ GStreamer Python bindings OK")
        
        # Check for required plugins
        required_plugins = [
            'v4l2src',
            'videoconvert',
            'vp8enc',
            'webrtcbin',
            'rtpvp8pay'
        ]
        
        missing_plugins = []
        for plugin in required_plugins:
            factory = Gst.ElementFactory.find(plugin)
            if factory:
                print(f"✓ Plugin '{plugin}' found")
            else:
                print(f"✗ Plugin '{plugin}' NOT found")
                missing_plugins.append(plugin)
        
        if missing_plugins:
            print(f"\nMissing plugins: {', '.join(missing_plugins)}")
            print("Install with: sudo apt-get install gstreamer1.0-plugins-bad")
            return False
        
        return True
    except ImportError as e:
        print(f"✗ GStreamer Python bindings not found: {e}")
        print("Install with: sudo apt-get install python3-gi gir1.2-gstreamer-1.0")
        return False
    except Exception as e:
        print(f"✗ GStreamer error: {e}")
        return False

def test_camera():
    """Test if camera is accessible"""
    print("\nTesting camera access...")
    try:
        result = subprocess.run(
            ['v4l2-ctl', '--list-devices'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ Camera devices found:")
            print(result.stdout)
            return True
        else:
            print("✗ v4l2-ctl not found or no cameras detected")
            return False
    except FileNotFoundError:
        print("✗ v4l2-ctl not installed")
        print("Install with: sudo apt-get install v4l-utils")
        return False
    except Exception as e:
        print(f"✗ Camera test error: {e}")
        return False

def test_janus_connection(janus_url="http://localhost:8088/janus"):
    """Test if Janus server is accessible"""
    print(f"\nTesting Janus connection ({janus_url})...")
    try:
        import aiohttp
        import asyncio
        
        async def check():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        janus_url,
                        json={"janus": "info", "transaction": "test"},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"✓ Janus server is accessible")
                            print(f"  Response: {data.get('janus', 'unknown')}")
                            return True
                        else:
                            print(f"✗ Janus server returned status {resp.status}")
                            return False
            except aiohttp.ClientError as e:
                print(f"✗ Cannot connect to Janus: {e}")
                print("  Make sure Janus is running and accessible")
                return False
        
        return asyncio.run(check())
    except ImportError:
        print("✗ aiohttp not installed")
        print("Install with: pip install aiohttp")
        return False
    except Exception as e:
        print(f"✗ Janus connection test error: {e}")
        return False

def test_python_dependencies():
    """Test if Python dependencies are installed"""
    print("\nTesting Python dependencies...")
    dependencies = {
        'aiohttp': 'aiohttp',
        'gi': 'PyGObject'
    }
    
    all_ok = True
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} NOT installed")
            print(f"  Install with: pip install {package}")
            all_ok = False
    
    return all_ok

def main():
    """Run all tests"""
    print("=" * 60)
    print("Janus WebRTC Setup Test")
    print("=" * 60)
    
    results = []
    
    # Test Python dependencies
    results.append(("Python Dependencies", test_python_dependencies()))
    
    # Test GStreamer
    results.append(("GStreamer", test_gstreamer()))
    
    # Test camera
    results.append(("Camera", test_camera()))
    
    # Test Janus (optional, might not be running)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--janus-url", default="http://localhost:8088/janus",
                       help="Janus server URL")
    args = parser.parse_args()
    
    results.append(("Janus Connection", test_janus_connection(args.janus_url)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All tests passed! You're ready to stream.")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
