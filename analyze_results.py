#!/usr/bin/env python3
"""
Automated Analysis and Visualization of Go2RTC Performance Data
Processes captured logs and generates charts
"""

import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14

# Test group definitions
TEST_GROUPS = {
    'Group1_Codec':      {'tests': ['T1A', 'T1B'],       'title': 'Group 1: Codec Comparison (h264 vs h265)',          'labels': ['h264 1080p', 'h265 1080p']},
    'Group2_Resolution': {'tests': ['T2A', 'T2B', 'T2C'], 'title': 'Group 2: Resolution Comparison (h264)',             'labels': ['1920x1080', '1280x720', '854x480']},
    'Group3_Bitrate':    {'tests': ['T3A', 'T3B', 'T3C'], 'title': 'Group 3: Bitrate Comparison (h264 1080p)',          'labels': ['2000k', '1000k', '500k']},
    'Group4_Framerate':  {'tests': ['T4A', 'T4B', 'T4C'], 'title': 'Group 4: Framerate Comparison (h264 1080p)',        'labels': ['30fps', '15fps', '10fps']},
    'Group5_H265_Res':   {'tests': ['T5A', 'T5B'],        'title': 'Group 5: h265 Resolution Comparison',              'labels': ['h265 1280x720', 'h265 854x480']},
    'Group6_H265_Bit':   {'tests': ['T6A', 'T6B'],        'title': 'Group 6: h265 Bitrate Comparison',                 'labels': ['h265 1000k', 'h265 500k']},
}


def parse_memory_value(mem_str):
    """Convert memory string (e.g., '126.7MiB') to MB"""
    if pd.isna(mem_str):
        return 0

    mem_str = str(mem_str).strip()

    if 'GiB' in mem_str or 'GB' in mem_str:
        return float(mem_str.replace('GiB', '').replace('GB', '')) * 1024
    elif 'MiB' in mem_str or 'MB' in mem_str:
        return float(mem_str.replace('MiB', '').replace('MB', ''))
    elif 'KiB' in mem_str or 'KB' in mem_str:
        return float(mem_str.replace('KiB', '').replace('KB', '')) / 1024
    else:
        return 0


def parse_network_value(net_str):
    """Convert network string (e.g., '1.23GB') to MB"""
    if pd.isna(net_str):
        return 0

    net_str = str(net_str).strip()

    if 'GB' in net_str or 'GiB' in net_str:
        return float(net_str.replace('GB', '').replace('GiB', '')) * 1024
    elif 'MB' in net_str or 'MiB' in net_str:
        return float(net_str.replace('MB', '').replace('MiB', ''))
    elif 'KB' in net_str or 'KiB' in net_str:
        return float(net_str.replace('KB', '').replace('KiB', '')) / 1024
    else:
        return 0


def analyze_single_test(log_file):
    """Analyze a single test log file"""

    print(f"Analyzing: {log_file}")

    # Read CSV
    df = pd.read_csv(log_file)

    # Skip empty files
    if df.empty or len(df) < 2:
        print(f"  Skipping {log_file} - insufficient data")
        return None, None

    # Parse numeric values
    df['cpu_percent'] = pd.to_numeric(df['cpu_percent'], errors='coerce')
    df['cpu_normalized'] = pd.to_numeric(df['cpu_normalized'], errors='coerce')
    df['memory_percent'] = pd.to_numeric(df['memory_percent'], errors='coerce')
    df['memory_mb'] = df['memory_usage'].apply(parse_memory_value)
    df['net_input_mb'] = df['net_input'].apply(parse_network_value)
    df['net_output_mb'] = df['net_output'].apply(parse_network_value)

    # Calculate statistics
    stats = {
        'test_id': Path(log_file).stem.replace('_stats', ''),
        'cpu_mean': df['cpu_percent'].mean(),
        'cpu_mean_normalized': df['cpu_normalized'].mean(),
        'cpu_max': df['cpu_percent'].max(),
        'cpu_max_normalized': df['cpu_normalized'].max(),
        'cpu_min': df['cpu_percent'].min(),
        'cpu_std': df['cpu_percent'].std(),
        'memory_mean': df['memory_mb'].mean(),
        'memory_max': df['memory_mb'].max(),
        'net_input_start': df['net_input_mb'].iloc[0],
        'net_input_end': df['net_input_mb'].iloc[-1],
        'net_output_start': df['net_output_mb'].iloc[0],
        'net_output_end': df['net_output_mb'].iloc[-1],
        'duration_seconds': len(df),
        'samples': len(df)
    }

    # Calculate bandwidth (MB/s)
    if stats['duration_seconds'] > 0:
        stats['bandwidth_input_mbps'] = (stats['net_input_end'] - stats['net_input_start']) / stats['duration_seconds']
        stats['bandwidth_output_mbps'] = (stats['net_output_end'] - stats['net_output_start']) / stats['duration_seconds']
    else:
        stats['bandwidth_input_mbps'] = 0
        stats['bandwidth_output_mbps'] = 0

    return stats, df


def create_stability_chart(df, test_id, output_dir):
    """Create line chart showing stability over time"""

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle(f'Performance Stability Over Time: {test_id}', fontsize=16, fontweight='bold')

    time_seconds = range(len(df))

    # Normalized CPU Usage over time
    axes[0].plot(time_seconds, df['cpu_normalized'], linewidth=2, color='#2E86AB')
    axes[0].fill_between(time_seconds, df['cpu_normalized'], alpha=0.3, color='#2E86AB')
    axes[0].set_ylabel('CPU Usage (% of total capacity)', fontweight='bold')
    axes[0].set_title('CPU Utilization Stability (Normalized)')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(0, 100)

    # Memory Usage over time
    axes[1].plot(time_seconds, df['memory_mb'], linewidth=2, color='#A23B72')
    axes[1].fill_between(time_seconds, df['memory_mb'], alpha=0.3, color='#A23B72')
    axes[1].set_ylabel('Memory (MB)', fontweight='bold')
    axes[1].set_title('Memory Consumption Stability')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim(bottom=0)

    # Network I/O over time
    axes[2].plot(time_seconds, df['net_input_mb'], linewidth=2, label='Input', color='#F18F01')
    axes[2].set_xlabel('Time (seconds)', fontweight='bold')
    axes[2].set_ylabel('Network Data (MB)', fontweight='bold')
    axes[2].set_title('Network I/O Growth')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()

    output_file = os.path.join(output_dir, f'{test_id}_stability.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved stability chart: {output_file}")
    plt.close()


def create_group_chart(config_avg, group_name, group_info, output_dir):
    """Create bar chart for a single test group"""

    # Filter data for this group
    group_data = config_avg[config_avg['config'].isin(group_info['tests'])]

    if group_data.empty:
        print(f"  Skipping {group_name} - no data available")
        return

    # Use labels if all tests present, otherwise use test IDs
    if len(group_data) == len(group_info['tests']):
        labels = group_info['labels']
    else:
        labels = group_data['config'].tolist()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(group_info['title'], fontsize=16, fontweight='bold')

    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#44BBA4']

    # CPU Normalized
    bars = axes[0, 0].bar(labels, group_data['cpu_mean_normalized'],
                           color=colors[:len(labels)], alpha=0.8)
    axes[0, 0].set_ylabel('Average CPU Usage (% of capacity)', fontweight='bold')
    axes[0, 0].set_title('Average CPU Usage (Normalized)')
    axes[0, 0].grid(axis='y', alpha=0.3)
    axes[0, 0].set_ylim(0, 100)
    for bar, val in zip(bars, group_data['cpu_mean_normalized']):
        axes[0, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    # Memory
    bars = axes[0, 1].bar(labels, group_data['memory_mean'],
                           color=colors[:len(labels)], alpha=0.8)
    axes[0, 1].set_ylabel('Average Memory (MB)', fontweight='bold')
    axes[0, 1].set_title('Average Memory Usage')
    axes[0, 1].grid(axis='y', alpha=0.3)
    for bar, val in zip(bars, group_data['memory_mean']):
        axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{val:.0f}MB', ha='center', va='bottom', fontweight='bold')

    # Bandwidth
    bars = axes[1, 0].bar(labels, group_data['bandwidth_input_mbps'],
                           color=colors[:len(labels)], alpha=0.8)
    axes[1, 0].set_ylabel('Bandwidth (MB/s)', fontweight='bold')
    axes[1, 0].set_xlabel('Configuration', fontweight='bold')
    axes[1, 0].set_title('Input Bandwidth Usage')
    axes[1, 0].grid(axis='y', alpha=0.3)
    for bar, val in zip(bars, group_data['bandwidth_input_mbps']):
        axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                        f'{val:.3f}', ha='center', va='bottom', fontweight='bold')

    # Peak CPU Normalized
    bars = axes[1, 1].bar(labels, group_data['cpu_max_normalized'],
                           color=colors[:len(labels)], alpha=0.8)
    axes[1, 1].set_ylabel('Peak CPU Usage (% of capacity)', fontweight='bold')
    axes[1, 1].set_xlabel('Configuration', fontweight='bold')
    axes[1, 1].set_title('Peak CPU Usage (Normalized)')
    axes[1, 1].grid(axis='y', alpha=0.3)
    axes[1, 1].set_ylim(0, 100)
    for bar, val in zip(bars, group_data['cpu_max_normalized']):
        axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()

    output_file = os.path.join(output_dir, f'{group_name}_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved group chart: {output_file}")
    plt.close()


def create_comparison_charts(all_stats, output_dir):
    """Create overall and group-wise comparison charts"""

    # Convert to DataFrame
    df = pd.DataFrame(all_stats)

    # Extract test configuration info from test_id
    df['config'] = df['test_id'].str.extract(r'(T\d+[A-Z])')

    # Calculate averages across runs for each configuration
    config_avg = df.groupby('config').agg({
        'cpu_mean_normalized': 'mean',
        'cpu_max_normalized': 'max',
        'memory_mean': 'mean',
        'bandwidth_input_mbps': 'mean'
    }).reset_index()

    # --- Overall comparison chart ---
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Overall Performance Comparison Across All Configurations',
                 fontsize=16, fontweight='bold')

    axes[0, 0].bar(config_avg['config'], config_avg['cpu_mean_normalized'], color='#2E86AB', alpha=0.8)
    axes[0, 0].set_ylabel('Average CPU Usage (% of capacity)', fontweight='bold')
    axes[0, 0].set_title('CPU Usage by Configuration (Normalized)')
    axes[0, 0].tick_params(axis='x', rotation=45)
    axes[0, 0].grid(axis='y', alpha=0.3)
    axes[0, 0].set_ylim(0, 100)

    axes[0, 1].bar(config_avg['config'], config_avg['memory_mean'], color='#A23B72', alpha=0.8)
    axes[0, 1].set_ylabel('Average Memory (MB)', fontweight='bold')
    axes[0, 1].set_title('Memory Usage by Configuration')
    axes[0, 1].tick_params(axis='x', rotation=45)
    axes[0, 1].grid(axis='y', alpha=0.3)

    axes[1, 0].bar(config_avg['config'], config_avg['bandwidth_input_mbps'], color='#F18F01', alpha=0.8)
    axes[1, 0].set_ylabel('Bandwidth (MB/s)', fontweight='bold')
    axes[1, 0].set_xlabel('Configuration', fontweight='bold')
    axes[1, 0].set_title('Bandwidth Usage by Configuration')
    axes[1, 0].tick_params(axis='x', rotation=45)
    axes[1, 0].grid(axis='y', alpha=0.3)

    axes[1, 1].bar(config_avg['config'], config_avg['cpu_max_normalized'], color='#C73E1D', alpha=0.8)
    axes[1, 1].set_ylabel('Peak CPU Usage (% of capacity)', fontweight='bold')
    axes[1, 1].set_xlabel('Configuration', fontweight='bold')
    axes[1, 1].set_title('Peak CPU by Configuration (Normalized)')
    axes[1, 1].tick_params(axis='x', rotation=45)
    axes[1, 1].grid(axis='y', alpha=0.3)
    axes[1, 1].set_ylim(0, 100)

    plt.tight_layout()
    output_file = os.path.join(output_dir, 'overall_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved overall comparison chart: {output_file}")
    plt.close()

    # --- Group-wise charts ---
    print("\nGenerating group-wise charts...")
    for group_name, group_info in TEST_GROUPS.items():
        create_group_chart(config_avg, group_name, group_info, output_dir)

    return config_avg


def generate_summary_report(all_stats, output_file):
    """Generate CSV summary report"""

    df = pd.DataFrame(all_stats)

    # Round values
    df = df.round({
        'cpu_mean': 2,
        'cpu_mean_normalized': 2,
        'cpu_max': 2,
        'cpu_max_normalized': 2,
        'cpu_std': 2,
        'memory_mean': 1,
        'bandwidth_input_mbps': 3,
        'bandwidth_output_mbps': 3
    })

    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"\nSummary report saved: {output_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print(df[['test_id', 'cpu_mean', 'cpu_mean_normalized', 'cpu_max',
              'cpu_max_normalized', 'memory_mean', 'bandwidth_input_mbps']].to_string(index=False))
    print("=" * 80)


def main():
    """Main analysis function"""

    print("=" * 80)
    print("AUTOMATED PERFORMANCE ANALYSIS")
    print("=" * 80)

    # Create output directories
    os.makedirs('test_results/charts', exist_ok=True)

    # Find all log files
    log_files = glob.glob('test_results/logs/*_stats.csv')

    if not log_files:
        print("\nNo log files found in test_results/logs/")
        print("Please run capture_stats.py first!")
        return

    print(f"\nFound {len(log_files)} test log files")

    # Analyze each test
    all_stats = []

    for log_file in sorted(log_files):
        stats, df = analyze_single_test(log_file)

        # Skip empty files
        if stats is None:
            continue

        all_stats.append(stats)

        # Create stability chart for each test
        test_id = stats['test_id']
        create_stability_chart(df, test_id, 'test_results/charts')

    # Create comparison charts
    print("\nGenerating comparison charts...")
    config_avg = create_comparison_charts(all_stats, 'test_results/charts')

    # Generate summary report
    generate_summary_report(all_stats, 'test_results/performance_summary.csv')

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)
    print("\nGenerated files:")
    print("- Individual stability charts: test_results/charts/*_stability.png")
    print("- Overall comparison:          test_results/charts/overall_comparison.png")
    print("- Group 1 Codec:               test_results/charts/Group1_Codec_comparison.png")
    print("- Group 2 Resolution:          test_results/charts/Group2_Resolution_comparison.png")
    print("- Group 3 Bitrate:             test_results/charts/Group3_Bitrate_comparison.png")
    print("- Group 4 Framerate:           test_results/charts/Group4_Framerate_comparison.png")
    print("- Group 5 h265 Resolution:     test_results/charts/Group5_H265_Res_comparison.png")
    print("- Group 6 h265 Bitrate:        test_results/charts/Group6_H265_Bit_comparison.png")
    print("- Summary report:              test_results/performance_summary.csv")


if __name__ == "__main__":
    main()