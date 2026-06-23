#!/usr/bin/env python3
"""
Automated Docker Stats Capture for Go2RTC Performance Testing
Captures CPU, Memory, and Network statistics during streaming tests
"""

import subprocess
import time
import csv
import sys
import os
from datetime import datetime


def capture_docker_stats(test_id, duration=60, interval=1):
    """
    Capture Docker container statistics for specified duration

    Args:
        test_id: Test identifier (e.g., 'T1A_run1')
        duration: How long to capture (seconds)
        interval: How often to sample (seconds)
    """

    output_file = f"test_results/logs/{test_id}_stats.csv"

    print(f"Starting data capture for {test_id}")
    print(f"Duration: {duration} seconds")
    print(f"Output: {output_file}")

    # Get number of CPU cores for normalization
    num_cpus = os.cpu_count()

    # Create CSV file with headers
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp',
            'container',
            'cpu_percent',
            'cpu_normalized',
            'num_cpus',
            'memory_usage',
            'memory_limit',
            'memory_percent',
            'net_input',
            'net_output'
        ])

    # Capture stats for duration
    samples = 0
    start_time = time.time()

    while time.time() - start_time < duration:
        try:
            # Get Docker stats (no streaming, single snapshot)
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format',
                 '{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}}'],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Parse output
                for line in result.stdout.strip().split('\n'):
                    if 'go2rtc' in line.lower():
                        parts = line.split(',')

                        # Extract values
                        container = parts[0].strip()
                        cpu_raw = float(parts[1].strip().replace('%', ''))
                        cpu_normalized = round(cpu_raw / num_cpus, 2)
                        mem_usage_raw = parts[2].strip().split('/')[0].strip()
                        mem_limit_raw = parts[2].strip().split('/')[1].strip() if '/' in parts[2] else ''
                        mem_percent_raw = parts[3].strip().replace('%', '')
                        net_io = parts[4].strip() if len(parts) > 4 else ''

                        # Parse network I/O
                        net_input = ''
                        net_output = ''
                        if '/' in net_io:
                            net_input = net_io.split('/')[0].strip()
                            net_output = net_io.split('/')[1].strip()

                        # Write to CSV
                        with open(output_file, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                timestamp,
                                container,
                                cpu_raw,
                                cpu_normalized,
                                num_cpus,
                                mem_usage_raw,
                                mem_limit_raw,
                                mem_percent_raw,
                                net_input,
                                net_output
                            ])

                        samples += 1
                        print(f"\rSamples captured: {samples}/{duration}", end='', flush=True)
                        break

            time.sleep(interval)

        except subprocess.TimeoutExpired:
            print("\nWarning: Docker command timed out, retrying...")
            continue
        except Exception as e:
            print(f"\nError capturing stats: {e}")
            continue

    print(f"\n\nCapture complete!")
    print(f"Total samples: {samples}")
    print(f"Data saved to: {output_file}")

    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python capture_stats.py <test_id> [duration]")
        print("Example: python capture_stats.py T1A_run1 60")
        sys.exit(1)

    test_id = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    capture_docker_stats(test_id, duration)