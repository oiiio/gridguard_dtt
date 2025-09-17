#!/usr/bin/env python3
"""
Single-run anomaly detector for testing.
This runs the anomaly detection once and exits, rather than monitoring continuously.
"""

import pandas as pd
from adtk.data import validate_series
from adtk.detector import OutlierDetector
from sklearn.neighbors import LocalOutlierFactor
import os
import sys

def run_single_anomaly_detection():
    """Run anomaly detection once on the current log data."""
    
    # Use local path when running locally, Docker path when in container
    if os.path.exists("/usr/src/app/logs/power_flow.log"):
        LOG_FILE = "/usr/src/app/logs/power_flow.log"
    else:
        LOG_FILE = "./logs/power_flow.log"
    
    print("=" * 60)
    print("SINGLE-RUN ANOMALY DETECTOR")
    print("=" * 60)
    print(f"Analyzing log file: {LOG_FILE}")
    
    if not os.path.exists(LOG_FILE):
        print(f"❌ ERROR: Log file not found at {LOG_FILE}")
        return False
    
    try:
        # Read the data
        data = pd.read_csv(
            LOG_FILE,
            header=None,
            names=["timestamp", "loading_percent"],
            index_col="timestamp",
            parse_dates=["timestamp"]
        )

        if data.empty:
            print("❌ No data in log file")
            return False

        # Filter for active data (non-zero loading)
        active_data = data[data["loading_percent"] > 0]
        
        print(f"📊 Total data points: {len(data)}")
        print(f"📊 Active data points: {len(active_data)}")
        
        if len(active_data) < 10:
            print(f"⚠️  WARNING: Insufficient active data points ({len(active_data)}) for reliable anomaly detection")
            return False

        # Show data statistics
        print(f"📊 Loading range: {active_data['loading_percent'].min():.1f}% to {active_data['loading_percent'].max():.1f}%")
        print(f"📊 Average loading: {active_data['loading_percent'].mean():.1f}%")
        print(f"📊 Data time range: {active_data.index.min()} to {active_data.index.max()}")

        # Validate the time series for ADTK
        s = validate_series(active_data["loading_percent"])
        
        # Convert to DataFrame for ADTK
        df_data = pd.DataFrame(s, columns=['loading_percent'])
        
        print(f"\n🔍 Running anomaly detection...")
        
        # Create and run anomaly detector
        outlier_detector = OutlierDetector(LocalOutlierFactor(contamination=0.1))
        anomalies = outlier_detector.fit_detect(df_data)

        # Process results
        if isinstance(anomalies, pd.Series):
            anomaly_timestamps = anomalies[anomalies == True].index
            
            print(f"✅ Anomaly detection completed!")
            print(f"🚨 Found {len(anomaly_timestamps)} anomalies")
            
            if len(anomaly_timestamps) > 0:
                print(f"\n--- ANOMALIES DETECTED ---")
                for i, timestamp in enumerate(anomaly_timestamps, 1):
                    loading_value = s.loc[timestamp]
                    print(f"  {i:2d}. {timestamp}: {loading_value:.2f}% loading")
                print(f"--- END OF {len(anomaly_timestamps)} ANOMALIES ---")
            else:
                print(f"✅ No anomalies detected - system operating normally")
                
            return True
        else:
            print(f"❌ ERROR: Unexpected anomaly detection result")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = run_single_anomaly_detection()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
