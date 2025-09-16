#!/usr/bin/env python3
"""
Script to automatically configure OpenPLC and wait for Modbus server to be ready
"""
import requests
import time
import sys
from pymodbus.client import ModbusTcpClient

def wait_for_web_interface(host='openplc', port=8080, timeout=60):
    """Wait for OpenPLC web interface to be ready"""
    print(f"Waiting for OpenPLC web interface at {host}:{port}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f'http://{host}:{port}', timeout=5)
            if response.status_code == 200:
                print("OpenPLC web interface is ready!")
                return True
        except requests.exceptions.RequestException as e:
            print(f"Web interface not ready yet: {e}")
        
        time.sleep(2)
    
    print(f"Timeout waiting for OpenPLC web interface after {timeout} seconds")
    return False

def check_modbus_server(host='openplc', port=502, timeout=30):
    """Check if Modbus TCP server is responding"""
    print(f"Checking Modbus TCP server at {host}:{port}...")
    
    client = ModbusTcpClient(host, port=port)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if client.connect():
                # Try a simple read operation
                result = client.read_coils(address=0, count=1)
                if not result.isError():
                    print("Modbus TCP server is ready and responding!")
                    client.close()
                    return True
                else:
                    print(f"Modbus server connected but returned error: {result}")
            else:
                print("Could not connect to Modbus server, retrying...")
        except Exception as e:
            print(f"Modbus connection attempt failed: {e}")
        
        client.close()
        time.sleep(2)
    
    print(f"Timeout waiting for Modbus TCP server after {timeout} seconds")
    return False

def main():
    print("=== OpenPLC Setup and Verification ===")
    
    # Wait for web interface
    if not wait_for_web_interface():
        print("ERROR: OpenPLC web interface is not ready")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("OpenPLC Web Interface is ready!")
    print("Please manually configure OpenPLC:")
    print("1. Open http://localhost:8080 in your browser")
    print("2. Login (default: openplc/openplc)")
    print("3. Go to 'Programs' and upload breaker_control_complete.st")
    print("4. Compile the program")
    print("5. Go to 'Runtime' and start the PLC")
    print("6. The script will then check for Modbus connectivity")
    print("="*50 + "\n")
    
    # Wait for user to set up the PLC
    input("Press Enter after you've uploaded and started the PLC program...")
    
    # Check Modbus server
    if check_modbus_server():
        print("SUCCESS: OpenPLC is fully configured and ready!")
        return True
    else:
        print("ERROR: Modbus TCP server is not responding")
        print("Make sure you've:")
        print("- Uploaded a PLC program")
        print("- Compiled it successfully")
        print("- Started the runtime")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
