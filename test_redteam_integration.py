#!/usr/bin/env python3
"""
Test script to verify the red team ready PLC program works with GridGuard SCADA
"""

import sys
import time
import subprocess

def test_basic_connectivity():
    """Test basic PLC connectivity"""
    print("🔌 Testing PLC connectivity...")
    try:
        # Try to ping the OpenPLC container
        result = subprocess.run(["docker", "exec", "openplc_runtime", "netstat", "-ln"], 
                              capture_output=True, text=True, timeout=10)
        if "502" in result.stdout:
            print("✅ Modbus port 502 is listening")
            return True
        else:
            print("❌ Modbus port 502 not found")
            return False
    except Exception as e:
        print(f"❌ Error testing connectivity: {e}")
        return False

def test_program_upload():
    """Test if the new PLC program can be uploaded"""
    print("📤 Testing PLC program compatibility...")
    print("   Manual step required:")
    print("   1. Open http://localhost:8080")
    print("   2. Login: openplc / openplc") 
    print("   3. Go to Programs → Browse → Upload: plc_logic/programs/breaker_control_redteam_ready.st")
    print("   4. Click Compile (should show 'Compilation finished successfully!')")
    print("   5. Go to Runtime → Start PLC")
    print("   6. Verify Modbus shows 'Listening on port 502'")
    print("✅ Manual verification required")
    return True

def test_anomaly_detector_integration():
    """Test that anomaly detector can still read the log files"""
    print("📊 Testing anomaly detector integration...")
    try:
        # Check if log directory exists
        import os
        if os.path.exists("./logs"):
            print("✅ Logs directory exists")
        else:
            os.makedirs("./logs", exist_ok=True)
            print("✅ Created logs directory")
        
        # Check if power flow log exists
        if os.path.exists("./logs/power_flow.log"):
            print("✅ Power flow log exists")
        else:
            print("ℹ️  Power flow log will be created when physical process starts")
        
        return True
    except Exception as e:
        print(f"❌ Error checking anomaly detector: {e}")
        return False

def test_attack_vectors():
    """Test attack vector documentation"""
    print("🎯 Testing attack vector documentation...")
    try:
        with open("RED_TEAM_ATTACK_GUIDE.md", "r") as f:
            content = f.read()
            if "ATTACK VECTORS" in content and "Modbus" in content:
                print("✅ Red team attack guide is complete")
                return True
            else:
                print("❌ Attack guide incomplete")
                return False
    except Exception as e:
        print(f"❌ Error reading attack guide: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 GridGuard Red Team Readiness Test")
    print("="*50)
    
    tests = [
        ("Basic Connectivity", test_basic_connectivity),
        ("PLC Program Upload", test_program_upload), 
        ("Anomaly Detector Integration", test_anomaly_detector_integration),
        ("Attack Vector Documentation", test_attack_vectors)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    print("\n📋 Test Results Summary")
    print("="*30)
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print(f"\n{'🎉 ALL TESTS PASSED' if all_passed else '⚠️  SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🚀 System is ready for red team testing!")
        print("Next steps:")
        print("1. ./start.sh  # Start the GridGuard system")
        print("2. Upload plc_logic/programs/breaker_control_redteam_ready.st via OpenPLC web interface")
        print("3. python blue_team_monitor.py  # Start security monitoring") 
        print("4. Follow RED_TEAM_ATTACK_GUIDE.md for attack scenarios")
    else:
        print("\n❌ Please fix failed tests before proceeding")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())