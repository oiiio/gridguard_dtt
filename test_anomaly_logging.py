#!/usr/bin/env python3
"""
Test the anomaly detector logging functionality locally.
"""

import sys
import os
import time

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our anomaly detector
from anomaly_detector import setup_logging, LOG_FILE, ANOMALY_LOG_FILE, LOG_DIR

def test_logging():
    """Test that logging is working properly."""
    print("Testing anomaly detector logging...")
    
    # Set up logging
    logger = setup_logging()
    
    # Test some log messages
    logger.info("Test message: Logging system initialized")
    logger.info("🚨 Test anomaly detected at test time")
    logger.error("Test error message")
    
    # Check if log file was created
    if os.path.exists(ANOMALY_LOG_FILE):
        print(f"✅ Log file created successfully: {ANOMALY_LOG_FILE}")
        
        # Read and display the log content
        with open(ANOMALY_LOG_FILE, 'r') as f:
            content = f.read()
            print(f"Log file content:\n{content}")
            
        return True
    else:
        print(f"❌ Log file not created at: {ANOMALY_LOG_FILE}")
        return False

def test_single_anomaly_run():
    """Test running a single anomaly detection cycle with logging."""
    print("\nTesting single anomaly detection run with logging...")
    
    if not os.path.exists(LOG_FILE):
        print(f"❌ Power flow log not found at: {LOG_FILE}")
        return False
    
    # Import and run a single cycle
    from anomaly_detector import monitor_and_detect
    
    print("Running one iteration of anomaly detection (will timeout after 15 seconds)...")
    
    # This will run the monitor function but we'll stop it quickly
    try:
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Test timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(15)  # 15 second timeout
        
        monitor_and_detect()
        
    except (KeyboardInterrupt, TimeoutError):
        print("Stopped monitoring (this is expected for the test)")
        pass
    except Exception as e:
        print(f"Error during monitoring: {e}")
        return False
    finally:
        import signal
        signal.alarm(0)  # Cancel the alarm
    
    # Check if logs were written
    if os.path.exists(ANOMALY_LOG_FILE):
        print(f"✅ Anomaly detection logged successfully")
        
        # Show recent log entries
        with open(ANOMALY_LOG_FILE, 'r') as f:
            lines = f.readlines()
            print(f"\nLast few log entries:")
            for line in lines[-10:]:  # Show last 10 lines
                print(f"  {line.strip()}")
        
        return True
    else:
        print(f"❌ No log file created during detection")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ANOMALY DETECTOR LOGGING TEST")
    print("=" * 60)
    
    success = True
    
    # Test 1: Basic logging
    if not test_logging():
        success = False
    
    # Test 2: Anomaly detection with logging
    if not test_single_anomaly_run():
        success = False
    
    print(f"\n{'✅ ALL LOGGING TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
