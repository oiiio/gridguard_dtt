#!/usr/bin/env python3
"""
Test script to run the anomaly detector locally on existing log data.
This helps verify the anomaly detector works before running it in Docker.
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_log_parsing():
    """Test that we can properly read and parse the log file."""
    log_file = "./logs/power_flow.log"
    
    if not os.path.exists(log_file):
        print(f"ERROR: Log file not found at {log_file}")
        print("Make sure the SCADA HMI system has been running to generate log data.")
        return False
    
    print(f"Testing log file parsing...")
    print(f"Log file: {log_file}")
    
    try:
        # Read the log file the same way the anomaly detector does
        data = pd.read_csv(
            log_file,
            header=None,  # No header row in the file
            names=["timestamp", "loading_percent"],  # Specify column names
            index_col="timestamp",
            parse_dates=["timestamp"]
        )
        
        print(f"✓ Successfully read {len(data)} rows from log file")
        print(f"✓ Data range: {data.index.min()} to {data.index.max()}")
        
        # Show some statistics
        active_data = data[data["loading_percent"] > 0]
        print(f"✓ Active data points (loading > 0): {len(active_data)}")
        
        if len(active_data) > 0:
            print(f"✓ Loading range: {active_data['loading_percent'].min():.1f}% to {active_data['loading_percent'].max():.1f}%")
            print(f"✓ Average loading: {active_data['loading_percent'].mean():.1f}%")
        
        # Show last few entries
        print(f"\nLast 5 entries:")
        print(data.tail())
        
        return True
        
    except Exception as e:
        print(f"ERROR parsing log file: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_anomaly_detection():
    """Test the anomaly detection on the existing log data."""
    log_file = "./logs/power_flow.log"
    
    if not os.path.exists(log_file):
        print(f"ERROR: Log file not found at {log_file}")
        return False
    
    try:
        # Import the required libraries
        from adtk.data import validate_series
        from adtk.detector import OutlierDetector
        from sklearn.neighbors import LocalOutlierFactor
        
        print(f"\nTesting anomaly detection...")
        
        # Read data
        data = pd.read_csv(
            log_file,
            header=None,
            names=["timestamp", "loading_percent"],
            index_col="timestamp",
            parse_dates=["timestamp"]
        )
        
        # Filter for active data only
        active_data = data[data["loading_percent"] > 0]
        
        if len(active_data) < 10:
            print(f"WARNING: Only {len(active_data)} active data points. Need at least 10 for reliable anomaly detection.")
            return False
        
        # Validate the time series
        s = validate_series(active_data["loading_percent"])
        
        # Convert to DataFrame for ADTK
        df_data = pd.DataFrame(s, columns=['loading_percent'])
        
        # Create anomaly detector
        outlier_detector = OutlierDetector(LocalOutlierFactor(contamination=0.1))
        
        print(f"✓ Running anomaly detection on {len(df_data)} data points...")
        anomalies = outlier_detector.fit_detect(df_data)
        
        # Check results
        if isinstance(anomalies, pd.Series):
            anomaly_timestamps = anomalies[anomalies == True].index
            
            print(f"✓ Anomaly detection completed")
            print(f"✓ Found {len(anomaly_timestamps)} anomalies")
            
            if len(anomaly_timestamps) > 0:
                print(f"\n--- ANOMALIES DETECTED ---")
                for timestamp in anomaly_timestamps:
                    loading_value = s.loc[timestamp]
                    print(f"  {timestamp}: {loading_value:.2f}% loading")
                print(f"--- END ANOMALIES ---")
            else:
                print(f"✓ No anomalies detected in current data")
                
            return True
        else:
            print(f"ERROR: Unexpected anomaly detection result type: {type(anomalies)}")
            return False
            
    except ImportError as e:
        print(f"ERROR: Missing required library: {e}")
        print(f"Run: pip install adtk scikit-learn")
        return False
    except Exception as e:
        print(f"ERROR in anomaly detection: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run the test suite for the anomaly detector."""
    print("=" * 60)
    print("ANOMALY DETECTOR LOCAL TEST")
    print("=" * 60)
    
    # Test 1: Log file parsing
    if not test_log_parsing():
        print(f"\n❌ Log parsing test FAILED")
        return False
    
    # Test 2: Anomaly detection
    if not test_anomaly_detection():
        print(f"\n❌ Anomaly detection test FAILED")
        return False
    
    print(f"\n✅ ALL TESTS PASSED!")
    print(f"The anomaly detector should work correctly in Docker now.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
