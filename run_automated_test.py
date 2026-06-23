#!/usr/bin/env python3
"""
Master Automated Test Runner
Runs complete test with config update, container restart, and data capture
"""

import subprocess
import time
import sys
import os
import yaml


def check_camera_stream():
    """
    Probe the camera RTSP source directly to confirm it is alive.
    Returns True if reachable, False otherwise.
    """
    print("  Checking camera stream at rtsp://192.168.1.238:8554/stream ...")
    try:
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-rtsp_transport', 'tcp',
                '-timeout', '5000000',  # 5 seconds
                '-i', 'rtsp://192.168.1.238:8554/stream',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1'
            ],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  ✓ Camera stream is live")
            return True
        else:
            print(result.stderr.decode())
            print("  ✗ Camera stream unreachable (ffprobe returned error)")
            return False
    except subprocess.TimeoutExpired:
        print("  ✗ Camera stream unreachable (connection timed out)")
        return False
    except FileNotFoundError:
        print("  ✗ ffprobe not found — make sure ffmpeg is installed and in PATH")
        return False
    except Exception as e:
        print(f"  ✗ Camera check failed: {e}")
        return False
def update_go2rtc_config(config_params):
    """Update iphone_cam stream with new ffmpeg configuration"""

    config_path = "C:/Home-Assistant-RTSP-Server/software/deployment/camera-streaming/go2rtc/config/go2rtc.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    if 'streams' not in config:
        config['streams'] = {}

    # Update camera with test parameters
    config['streams']['iphone_cam'] = [
         f"ffmpeg:rtsp://192.168.1.238:8554/stream#video={config_params['codec']}#hardware=nvenc#width={config_params['width']}#height={config_params['height']}#bitrate={config_params['bitrate']}#framerate={config_params['framerate']}"
         #f"ffmpeg:rtsp://192.168.1.238:8554/stream#video={config_params['codec']}#hardware=cuda#width={config_params['width']}#height={config_params['height']}#bitrate={config_params['bitrate']}#framerate={config_params['framerate']}"
        #'rtsp://192.168.1.238:8554/stream',
        #f"ffmpeg:iphone_cam#video={config_params['codec']}#width={config_params['width']}#height={config_params['height']}#bitrate={config_params['bitrate']}#framerate={config_params['framerate']}"
    ]

    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(
        f"✓ Updated iphone_cam: {config_params['codec']}, {config_params['width']}x{config_params['height']}, {config_params['bitrate']}, {config_params['framerate']}fps")

def restart_container():
    """Restart Go2RTC container"""
    
    print("Restarting Go2RTC container...")
    result = subprocess.run(['docker', 'restart', 'go2rtc'], capture_output=True)
    
    if result.returncode == 0:
        print("✓ Container restarted successfully")
        return True
    else:
        print(f"✗ Failed to restart container: {result.stderr.decode()}")
        return False

def trigger_stream():
    """Start consuming Go2RTC stream to force transcoding"""
    try:
        process = subprocess.Popen(
            ['ffmpeg', '-i', 'rtsp://localhost:8554/iphone_cam',
             '-f', 'null', '-'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("  ✓ Stream consumer started")
        return process
    except Exception as e:
        print(f"  ✗ Failed to start consumer: {e}")
        return None


def wait_for_active_stream(timeout=60):
    """Trigger and wait until Go2RTC is actively transcoding.
    Returns the consumer process if successful, None if failed."""
    print("  Waiting for active stream...")
    start = time.time()
    consumer = None
    while time.time() - start < timeout:
        try:
            # Kill previous consumer attempt before retrying
            if consumer:
                consumer.terminate()

            consumer = trigger_stream()  # nudge go2rtc to connect

            time.sleep(3)  # give it a moment before probing

            result = subprocess.run(
                ['ffprobe',
                 '-v', 'error',
                 '-rtsp_transport', 'tcp',
                 '-timeout', '5000000',
                 '-i', 'rtsp://localhost:8554/iphone_cam',
                 '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1'],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                print("  ✓ Active stream detected!")
                return consumer  # return the live consumer process
            else:
                time.sleep(5)
        except Exception as e:
            print(f"  Warning: {e}")
            time.sleep(5)

    print("  ✗ Stream not detected after timeout!")
    if consumer:
        consumer.terminate()
    return None

def verify_data_capture():
    """Verify Go2RTC container is running and producing stats"""
    try:
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format',
             '{{.Name}},{{.CPUPerc}}'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if 'go2rtc' in line.lower():
                    cpu = float(line.split(',')[1].strip().replace('%', ''))
                    print(f"  ✓ Container active - CPU: {cpu:.1f}%")
                    return True
        print("  ✗ Container not found in stats!")
        return False
    except Exception as e:
        print(f"  ✗ Stats verification error: {e}")
        return False

def run_test(test_id, config_params, duration=60, stabilization_time=60):
    """Run complete automated test"""
    
    print("\n" + "="*80)
    print(f"RUNNING TEST: {test_id}")
    print("="*80)

    # Step 0: Verify camera is reachable before doing anything
    print("\n[0/6] Verifying camera stream...")
    if not check_camera_stream():
        print("\n✗ Test aborted: Camera is not streaming.")
        print("  → Connect the camera and try again.")
        return False
    
    # Step 1: Update configuration
    print("\n[1/6] Updating configuration...")
    update_go2rtc_config(config_params)
    
    # Step 2: Restart container
    print("\n[2/6] Restarting container...")
    if not restart_container():
        print("✗ Test failed: Could not restart container")
        return False
    
    # Step 3: Wait for stabilization
    print(f"\n[3/6] Waiting {stabilization_time} seconds for stabilization...")
    for i in range(stabilization_time, 0, -1):
        print(f"\r  Stabilizing... {i} seconds remaining", end='', flush=True)
        time.sleep(1)
    print("\n✓ Stream stabilized")

    print("\n[4/6] Waiting for active stream...")
    consumer = wait_for_active_stream(timeout=60)
    if not consumer:
        print("✗ Test failed: go2rtc did not start streaming")
        return False

    # Step 5: Capture performance data
    print(f"\n[5/6] Capturing performance data for {duration} seconds...")
    import capture_stats
    log_file = capture_stats.capture_docker_stats(test_id, duration)

    # Stop consumer after capture
    consumer.terminate()
    print("  ✓ Stream consumer stopped")

    # Step 6: Cool down
    print("\n[6/6] Cooling down before next test...")
    time.sleep(10)

    print(f"\n✓ Test {test_id} completed successfully!")
    print(f"  Data saved to: {log_file}")
    
    return True

# Test configurations
TESTS = {
    'T1A': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '2000k', 'framerate': '30'},
    'T1B': {'codec': 'h265', 'width': '1920', 'height': '1080', 'bitrate': '2000k', 'framerate': '30'},
    'T2A': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '2000k', 'framerate': '30'},
    'T2B': {'codec': 'h264', 'width': '1280', 'height': '720',  'bitrate': '2000k', 'framerate': '30'},
    'T2C': {'codec': 'h264', 'width': '854',  'height': '480',  'bitrate': '2000k', 'framerate': '30'},
    'T3A': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '2000k', 'framerate': '30'},
    'T3B': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '1000k', 'framerate': '30'},
    'T3C': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '500k',  'framerate': '30'},
    'T4A': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '2000k', 'framerate': '30'},
    'T4B': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '2000k', 'framerate': '15'},
    'T4C': {'codec': 'h264', 'width': '1920', 'height': '1080', 'bitrate': '2000k', 'framerate': '10'},
    'T5A': {'codec': 'h265', 'width': '1280', 'height': '720',  'bitrate': '2000k', 'framerate': '30'},
    'T5B': {'codec': 'h265', 'width': '854',  'height': '480',  'bitrate': '2000k', 'framerate': '30'},
    'T6A': {'codec': 'h265', 'width': '1920', 'height': '1080', 'bitrate': '1000k', 'framerate': '30'},
    'T6B': {'codec': 'h265', 'width': '1920', 'height': '1080', 'bitrate': '500k',  'framerate': '30'},
}

def main():
    """Run all tests automatically"""
    
    # Create directories
    os.makedirs('test_results/logs', exist_ok=True)
    
    if len(sys.argv) > 1:
        # Run specific test
        test_id = sys.argv[1]
        run_num = sys.argv[2] if len(sys.argv) > 2 else '1'
        
        if test_id not in TESTS:
            print(f"Unknown test: {test_id}")
            print(f"Available tests: {', '.join(TESTS.keys())}")
            return
        
        config = TESTS[test_id].copy()
        
        run_test(f'{test_id}_run{run_num}', config)
    else:
        # Run all tests
        print("="*80)
        print("AUTOMATED TEST SUITE - ALL TESTS")
        print("="*80)
        print(f"\nTotal tests to run: {len(TESTS) * 3} (11 configs × 3 runs)")
        print("\nThis will take approximately 2-3 hours.")
        input("\nPress Enter to start, or Ctrl+C to cancel...")
        
        for test_id, config in TESTS.items():
            for run_num in range(1, 4):  # 3 runs per config
                config_copy = config.copy()
                
                success = run_test(f'{test_id}_run{run_num}', config_copy)
                
                if not success:
                    print(f"\n✗ Test {test_id}_run{run_num} failed!")
                    choice = input("Continue with remaining tests? (y/n): ")
                    if choice.lower() != 'y':
                        break
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED!")
        print("="*80)
        print("\nNext step: Run 'python analyze_results.py' to generate charts")

if __name__ == "__main__":
    main()