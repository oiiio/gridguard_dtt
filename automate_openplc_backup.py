#!/usr/bin/env python3
"""
OpenPLC Automation Script
Automatically uploads, compiles, and starts PLC programs via REST API
"""

import requests
import time
import sys
import os
from pathlib import Path

class OpenPLCAutomator:
    def __init__(self, base_url="http://localhost:8080", username="openplc", password="openplc"):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        
    def wait_for_openplc(self, timeout=60):
        """Wait for OpenPLC web interface to be available"""
        print(f"🕐 Waiting for OpenPLC at {self.base_url}...")
        
        for i in range(timeout):
            try:
                response = self.session.get(f"{self.base_url}/")
                if response.status_code == 200:
                    print("✅ OpenPLC web interface is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            if i % 10 == 0 and i > 0:
                print(f"   Still waiting... ({i}/{timeout}s)")
            time.sleep(1)
        
        print(f"❌ OpenPLC failed to start within {timeout} seconds")
        return False
    
    def login(self):
        """Login to OpenPLC and establish session"""
        print("🔐 Logging into OpenPLC...")
        
        try:
            # Get login page to establish session
            login_page = self.session.get(f"{self.base_url}/login")
            if login_page.status_code != 200:
                print(f"❌ Failed to access OpenPLC: {login_page.status_code}")
                return False
            
            # Perform login with form data
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            response = self.session.post(f"{self.base_url}/login", data=login_data, allow_redirects=True)
            
            # Check if we're at dashboard (successful login)
            if 'dashboard' in response.url or response.status_code == 200:
                print("✅ Successfully logged into OpenPLC!")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"Response URL: {response.url}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def upload_and_compile_program(session, program_path, program_name="Automated Program", program_description="Uploaded via automation script"):
    """Upload and compile a PLC program"""
    try:
        print(f"� Uploading program: {program_path}")
        
        # Step 1: Upload the file
        with open(program_path, 'rb') as f:
            files = {'file': f}
            response = session.post(f"{BASE_URL}/upload-program", files=files, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code}")
            return False
            
        print("✅ Program file uploaded successfully")
        
        # Step 2: Extract the uploaded filename and epoch from the response
        # The response contains a form with hidden fields for the uploaded file
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        prog_file_input = soup.find('input', {'name': 'prog_file'})
        epoch_time_input = soup.find('input', {'name': 'epoch_time'})
        
        if not prog_file_input or not epoch_time_input:
            print("❌ Could not extract uploaded file information")
            return False
            
        uploaded_filename = prog_file_input.get('value')
        epoch_time = epoch_time_input.get('value')
        
        print(f"📋 Uploaded filename: {uploaded_filename}")
        
        # Step 3: Complete the upload by submitting the program info form
        upload_data = {
            'prog_name': program_name,
            'prog_descr': program_description,
            'prog_file': uploaded_filename,
            'epoch_time': epoch_time
        }
        
        info_response = session.post(f"{BASE_URL}/upload-program-action", data=upload_data, timeout=30)
        if info_response.status_code != 200:
            print(f"❌ Program info submission failed: {info_response.status_code}")
            return False
            
        print("✅ Program info submitted successfully")
        
        # Step 4: The response redirects to the compilation page, follow it
        print("⚙️  Starting compilation...")
        compile_url = f"{BASE_URL}/compile-program?file={uploaded_filename}"
        compile_response = session.get(compile_url, timeout=10)
        
        if compile_response.status_code != 200:
            print(f"❌ Failed to start compilation: {compile_response.status_code}")
            return False
        
        print("🔄 Compilation started, monitoring progress...")
        
        # Step 5: Poll the compilation logs until completion
        max_wait_time = 120  # 2 minutes max
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                logs_response = session.get(f"{BASE_URL}/compilation-logs", timeout=10)
                if logs_response.status_code == 200:
                    logs = logs_response.text
                    
                    if "Compilation finished successfully!" in logs:
                        print("✅ Program compiled successfully!")
                        print("📋 Compilation output:")
                        print(logs.split('
')[-10:])  # Show last 10 lines
                        return True
                    elif "Compilation finished with errors!" in logs:
                        print("❌ Compilation failed with errors!")
                        print("📋 Compilation output:")
                        print(logs)
                        return False
                    else:
                        # Still compiling, show progress
                        lines = logs.strip().split('
')
                        if lines:
                            last_line = lines[-1].strip()
                            if last_line:
                                print(f"🔄 {last_line}")
                
                time.sleep(2)  # Wait 2 seconds before checking again
                
            except Exception as e:
                print(f"⚠️  Error checking compilation status: {e}")
                time.sleep(2)
        
        print("❌ Compilation timed out")
        return False
            
    except Exception as e:
        print(f"❌ Error during upload/compile: {e}")
        return False
    
    def compile_program(self):
        """Compile the uploaded program"""
        print("🔨 Compiling PLC program...")
        
        try:
            # Trigger compilation
            response = self.session.post(f"{self.base_url}/compile-program")
            
            if response.status_code == 200:
                # Check compilation result
                if 'success' in response.text.lower() or 'compilation finished successfully' in response.text.lower():
                    print("✅ Program compiled successfully!")
                    return True
                else:
                    print("❌ Compilation failed!")
                    print(f"Response: {response.text[:300]}...")
                    return False
            else:
                print(f"❌ Compilation request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Compilation error: {e}")
            return False
    
    def start_runtime(self):
        """Start the PLC runtime"""
        print("▶️  Starting PLC runtime...")
        
        try:
            # Start the runtime
            response = self.session.post(f"{self.base_url}/start_plc")
            
            if response.status_code == 200:
                print("✅ PLC runtime started!")
                
                # Wait a moment and verify Modbus server
                print("🔌 Verifying Modbus server...")
                time.sleep(3)
                
                if self.check_modbus_server():
                    print("✅ Modbus server is running!")
                    return True
                else:
                    print("⚠️  Runtime started but Modbus server not detected")
                    return True  # Still consider it successful
            else:
                print(f"❌ Failed to start runtime: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Runtime start error: {e}")
            return False
    
    def stop_runtime(self):
        """Stop the PLC runtime"""
        print("⏹️  Stopping PLC runtime...")
        
        try:
            response = self.session.post(f"{self.base_url}/stop_plc")
            if response.status_code == 200:
                print("✅ PLC runtime stopped!")
                return True
            else:
                print(f"❌ Failed to stop runtime: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Runtime stop error: {e}")
            return False
    
    def check_modbus_server(self):
        """Check if Modbus server is running"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 502))
            sock.close()
            return result == 0
        except:
            return False
    
    def get_runtime_status(self):
        """Get current runtime status"""
        try:
            response = self.session.get(f"{self.base_url}/runtime")
            if response.status_code == 200:
                # Parse status from response
                if 'running' in response.text.lower():
                    return "running"
                elif 'stopped' in response.text.lower():
                    return "stopped"
                else:
                    return "unknown"
            return "error"
        except:
            return "error"
    
    def full_setup(self, program_path):
        """Complete automated setup: upload, compile, and start"""
        print("🚀 Starting OpenPLC automated setup...")
        print("=" * 50)
        
        # Step 1: Wait for OpenPLC
        if not self.wait_for_openplc():
            return False
        
        # Step 2: Login
        if not self.login():
            return False
        
        # Step 3: Check current status
        status = self.get_runtime_status()
        print(f"📊 Current runtime status: {status}")
        
        # Step 4: Stop runtime if running (to upload new program)
        if status == "running":
            if not self.stop_runtime():
                print("⚠️  Could not stop runtime, continuing anyway...")
        
        # Step 5: Upload program
        if not self.upload_program(program_path):
            return False
        
        # Step 6: Compile program
        if not self.compile_program():
            return False
        
        # Step 7: Start runtime
        if not self.start_runtime():
            return False
        
        print("\n" + "=" * 50)
        print("🎉 OpenPLC automated setup completed successfully!")
        print(f"📊 Program: {os.path.basename(program_path)}")
        print(f"🌐 Web Interface: {self.base_url}")
        print(f"🔌 Modbus Server: localhost:502")
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Automate OpenPLC program upload and startup")
    parser.add_argument("--program", 
                       default="plc_logic/programs/breaker_control_complete.st",
                       help="Path to the ST program file")
    parser.add_argument("--url", 
                       default="http://localhost:8080",
                       help="OpenPLC web interface URL")
    parser.add_argument("--username", 
                       default="openplc",
                       help="OpenPLC username")
    parser.add_argument("--password", 
                       default="openplc", 
                       help="OpenPLC password")
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
    
    # Run automation
    automator = OpenPLCAutomator(args.url, args.username, args.password)
    success = automator.full_setup(str(program_path))
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
