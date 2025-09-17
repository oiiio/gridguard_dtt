#!/usr/bin/env python3
"""
Test runner for the standalone GridGuard system.
This script lets you test different components without Docker.
"""

import subprocess
import time
import os
import signal
import sys

def run_quick_test():
    """Run a quick test to verify everything works"""
    print("🧪 Running Quick System Test...")
    
    # Test the physical process
    result = subprocess.run([
        sys.executable, "test_physical_process.py", "--quick"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Physical process test passed!")
        print(result.stdout)
    else:
        print("❌ Physical process test failed!")
        print(result.stderr)
        return False
    
    return True

def run_full_test(duration=60):
    """Run the full system test with anomaly detection"""
    print(f"🚀 Running Full System Test for {duration} seconds...")
    print("   This will start the physical process and anomaly detector")
    print("   Press Ctrl+C to stop early\n")
    
    # Clean up old logs
    if os.path.exists("./logs/power_flow.log"):
        os.remove("./logs/power_flow.log")
        print("🧹 Cleaned up old log files")
    
    processes = []
    
    try:
        # Start the physical process
        print("🔌 Starting physical process simulator...")
        physical_process = subprocess.Popen([
            sys.executable, "test_physical_process.py"
        ])
        processes.append(physical_process)
        
        # Wait a bit for the log file to be created
        time.sleep(10)
        
        # Start the anomaly detector
        print("🔍 Starting anomaly detector...")
        anomaly_detector = subprocess.Popen([
            sys.executable, "test_anomaly_detector.py"
        ])
        processes.append(anomaly_detector)
        
        # Let them run for the specified duration
        print(f"⏳ Running for {duration} seconds... (Ctrl+C to stop)")
        time.sleep(duration)
        
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
    finally:
        # Clean up processes
        print("🧹 Cleaning up processes...")
        for proc in processes:
            if proc.poll() is None:  # Process is still running
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        
        print("✅ Test completed!")
        
        # Show log summary
        log_file = "./logs/power_flow.log"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
            print(f"📊 Generated {len(lines)} data points in log file")

def run_synthetic_anomaly_test():
    """Run anomaly detection with synthetic data"""
    print("🧪 Running Synthetic Anomaly Test...")
    
    result = subprocess.run([
        sys.executable, "test_anomaly_detector.py", "--test"
    ])
    
    return result.returncode == 0

def main():
    """Main test runner"""
    print("=" * 60)
    print("🔬 GridGuard Standalone Test Suite")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            success = run_quick_test()
            sys.exit(0 if success else 1)
            
        elif command == "full":
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            run_full_test(duration)
            
        elif command == "anomaly":
            success = run_synthetic_anomaly_test()
            sys.exit(0 if success else 1)
            
        else:
            print(f"❌ Unknown command: {command}")
            show_usage()
            sys.exit(1)
    else:
        show_usage()

def show_usage():
    """Show usage information"""
    print("\nUsage:")
    print("  python test_runner.py quick                    # Quick system test")
    print("  python test_runner.py full [duration]          # Full test with anomaly detection")
    print("  python test_runner.py anomaly                  # Test anomaly detection with synthetic data")
    print("\nExamples:")
    print("  python test_runner.py quick")
    print("  python test_runner.py full 120")
    print("  python test_runner.py anomaly")

if __name__ == "__main__":
    main()
