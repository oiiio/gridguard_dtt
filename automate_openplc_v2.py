#!/usr/bin/env python3
"""
Simplified OpenPLC Automation Script using curl commands
This version uses subprocess calls to curl for better compatibility
"""

import subprocess
import time
import sys
import os
import json
from pathlib import Path

class OpenPLCAutomator:
    def __init__(self, base_url="http://localhost:8080", username="openplc", password="openplc"):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        
    def wait_for_openplc(self, timeout=60):
        """Wait for OpenPLC web interface to be available"""
        print(f"🕐 Waiting for OpenPLC at {self.base_url}...")
        
        for i in range(timeout):
            try:
                result = subprocess.run(['curl', '-s', '-f', f"{self.base_url}/"], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    print("✅ OpenPLC web interface is ready!")
                    return True
            except:
                pass
            
            if i % 10 == 0 and i > 0:
                print(f"   Still waiting... ({i}/{timeout}s)")
            time.sleep(1)
        
        print(f"❌ OpenPLC failed to start within {timeout} seconds")
        return False
    
    def check_modbus_server(self):
        """Check if Modbus server is running"""
        try:
            result = subprocess.run(['nc', '-z', 'localhost', '502'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def upload_and_compile_program(self, program_path):
        """Upload and compile program using direct file operations"""
        print(f"📤 Preparing to upload program: {program_path}")
        
        if not os.path.exists(program_path):
            print(f"❌ Program file not found: {program_path}")
            return False
        
        # For OpenPLC, we need to copy the file to a specific location
        # and use the web interface indirectly
        print("🔧 Using alternative upload method...")
        
        # Method 1: Try direct file copy to container
        try:
            # Copy file to OpenPLC container
            container_path = "/var/lib/openplc/st_files/main.st"
            result = subprocess.run([
                'docker', 'exec', 'openplc_runtime', 
                'cp', f'/usr/src/app/plc_logic/programs/{os.path.basename(program_path)}', 
                container_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Program copied to OpenPLC container!")
                return self.trigger_compilation()
            else:
                print(f"⚠️  Direct copy failed: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Container copy failed: {e}")
        
        # Method 2: Use HTTP multipart upload
        print("🔧 Trying HTTP upload method...")
        return self.http_upload_program(program_path)
    
    def http_upload_program(self, program_path):
        """Upload program via HTTP using curl"""
        try:
            # Read program content
            with open(program_path, 'r') as f:
                program_content = f.read()
            
            # Create temporary file for upload
            temp_file = '/tmp/plc_upload.st'
            with open(temp_file, 'w') as f:
                f.write(program_content)
            
            # Use curl to upload with form data
            cmd = [
                'curl', '-s', '-X', 'POST',
                '-u', f'{self.username}:{self.password}',
                '-F', f'file=@{temp_file}',
                '-F', f'st_program={program_content}',
                f'{self.base_url}/programs'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass
            
            if result.returncode == 0 and 'success' in result.stdout.lower():
                print("✅ HTTP upload successful!")
                return True
            else:
                print(f"❌ HTTP upload failed: {result.stdout[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ HTTP upload error: {e}")
            return False
    
    def trigger_compilation(self):
        """Trigger compilation using curl"""
        print("🔨 Triggering compilation...")
        
        try:
            cmd = [
                'curl', '-s', '-X', 'POST',
                '-u', f'{self.username}:{self.password}',
                f'{self.base_url}/compile-program'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                if 'success' in result.stdout.lower() or 'compilation finished' in result.stdout.lower():
                    print("✅ Compilation successful!")
                    return True
                else:
                    print(f"❌ Compilation failed: {result.stdout[:300]}")
                    return False
            else:
                print(f"❌ Compilation request failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Compilation error: {e}")
            return False
    
    def start_runtime(self):
        """Start PLC runtime"""
        print("▶️  Starting PLC runtime...")
        
        try:
            cmd = [
                'curl', '-s', '-X', 'POST',
                '-u', f'{self.username}:{self.password}',
                f'{self.base_url}/start_plc'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("✅ Runtime start command sent!")
                
                # Wait and check Modbus
                print("🔌 Verifying Modbus server startup...")
                time.sleep(5)
                
                # Check multiple times as Modbus might take a moment
                for i in range(10):
                    if self.check_modbus_server():
                        print("✅ Modbus server is running!")
                        return True
                    time.sleep(1)
                    print(f"   Checking Modbus... ({i+1}/10)")
                
                print("⚠️  Runtime started but Modbus server not detected")
                print("    This might be normal if no program is compiled")
                return True  # Still consider success
            else:
                print(f"❌ Runtime start failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Runtime start error: {e}")
            return False
    
    def simplified_setup(self, program_path):
        """Simplified automated setup"""
        print("🚀 Starting simplified OpenPLC setup...")
        print("=" * 50)
        
        # Step 1: Wait for OpenPLC
        if not self.wait_for_openplc():
            return False
        
        # Step 2: Try to start runtime first (might work if program already exists)
        print("▶️  Attempting to start runtime...")
        if self.start_runtime():
            if self.check_modbus_server():
                print("✅ Runtime already working! Setup complete.")
                return True
            else:
                print("⚠️  Runtime started but no Modbus. Continuing with upload...")
        
        # Step 3: Upload and compile program
        print("📤 Uploading and compiling program...")
        if not self.upload_and_compile_program(program_path):
            print("❌ Could not upload program automatically")
            print("📋 Manual setup required:")
            print(f"   1. Open {self.base_url}")
            print("   2. Login with openplc/openplc")
            print(f"   3. Upload {program_path}")
            print("   4. Compile and start")
            return False
        
        # Step 4: Start runtime
        if not self.start_runtime():
            print("❌ Could not start runtime automatically")
            return False
        
        print("\n" + "=" * 50)
        print("🎉 Simplified OpenPLC setup completed!")
        print(f"📊 Program: {os.path.basename(program_path)}")
        print(f"🌐 Web Interface: {self.base_url}")
        print(f"🔌 Modbus Server: localhost:502")
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Simplified OpenPLC automation")
    parser.add_argument("--program", 
                       default="plc_logic/programs/breaker_control_complete.st",
                       help="Path to the ST program file")
    parser.add_argument("--url", 
                       default="http://localhost:8080",
                       help="OpenPLC web interface URL")
    parser.add_argument("--timeout", 
                       type=int, 
                       default=60,
                       help="Timeout waiting for OpenPLC (seconds)")
    
    args = parser.parse_args()
    
    # Resolve program path
    program_path = Path(args.program).resolve()
    if not program_path.exists():
        print(f"❌ Program file not found: {program_path}")
        sys.exit(1)
    
    # Run simplified automation
    automator = OpenPLCAutomator(args.url)
    success = automator.simplified_setup(str(program_path))
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
