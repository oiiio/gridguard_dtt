#!/usr/bin/env python3
"""
Simple launcher for GridGuard SCADA Dashboard
This script will check dependencies and launch the dashboard
"""
import subprocess
import sys
import time
import importlib

def check_and_install_packages():
    """Check if required packages are installed, install if needed"""
    required_packages = [
        'flask',
        'flask_socketio', 
        'pandapower',
        'pymodbus',
        'numpy',
        'pandas'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"📦 Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            print("✅ Packages installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install packages: {e}")
            sys.exit(1)

def check_openplc_container():
    """Check if OpenPLC container is running"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=openplc_runtime', '--format', '{{.Names}}'],
            capture_output=True, text=True, check=True
        )
        return 'openplc_runtime' in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_openplc_container():
    """Start OpenPLC container if not running"""
    try:
        print("🚀 Starting OpenPLC container...")
        subprocess.run(['docker-compose', 'up', '-d', 'openplc'], check=True)
        print("⏳ Waiting for OpenPLC to start...")
        time.sleep(15)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Failed to start OpenPLC container: {e}")
        print("Make sure Docker is running and docker-compose.yml exists")
        return False

def main():
    print("🌟 GridGuard SCADA Dashboard Launcher")
    print("=" * 50)
    
    # Check dependencies
    print("🔍 Checking Python dependencies...")
    check_and_install_packages()
    
    # Check OpenPLC container
    print("🔍 Checking OpenPLC container...")
    if not check_openplc_container():
        print("⚠️  OpenPLC container not running")
        if not start_openplc_container():
            sys.exit(1)
    else:
        print("✅ OpenPLC container is running")
    
    print("\n📋 Quick Setup Checklist:")
    print("1. 🌐 Open http://localhost:8080 (OpenPLC Web Interface)")
    print("2. 🔐 Login with: openplc / openplc")
    print("3. 📁 Upload: plc_logic/programs/breaker_control_complete.st")
    print("4. ⚙️  Compile and start the program")
    print("5. 📊 Dashboard: http://localhost:5001")
    print("\n" + "=" * 50)
    print("🚀 Starting SCADA Dashboard...")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Launch the dashboard
    try:
        import standalone_dashboard
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
