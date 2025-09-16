#!/bin/bash

# GridGuard SCADA System - Startup Script
# This script handles the proper startup sequence for the SCADA system

set -e  # Exit on any error

echo "🚀 Starting GridGuard SCADA System..."
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for service to be ready
wait_for_service() {
    local service=$1
    local url=$2
    local timeout=${3:-60}
    local count=0
    
    print_status "Waiting for $service to be ready at $url..."
    
    while [ $count -lt $timeout ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_success "$service is ready!"
            return 0
        fi
        sleep 2
        count=$((count + 2))
        printf "."
    done
    
    print_error "$service failed to start within $timeout seconds"
    return 1
}

# Function to check if PLC program is loaded
check_plc_program() {
    print_status "Checking if PLC program is compiled and running..."
    
    # Try to connect to Modbus server
    if timeout 5 nc -z localhost 502 2>/dev/null; then
        print_success "PLC Modbus server is running!"
        return 0
    else
        print_warning "PLC Modbus server not available"
        return 1
    fi
}

# Step 1: Clean up any existing containers
print_status "Cleaning up existing containers..."
docker compose down > /dev/null 2>&1 || true

# Step 2: Start OpenPLC
print_status "Starting OpenPLC Runtime..."
docker compose up -d openplc

# Step 3: Wait for OpenPLC web interface
if wait_for_service "OpenPLC Web Interface" "http://localhost:8080"; then
    print_success "OpenPLC is running!"
else
    print_error "Failed to start OpenPLC"
    exit 1
fi

# Step 4: Check if PLC program is already loaded and running
if ! check_plc_program; then
    print_status "PLC program not detected. Attempting automated setup..."
    
    # Try automated PLC setup
    if python3 automate_openplc.py --timeout 30; then
        print_success "PLC program automatically uploaded and started!"
    else
        print_warning "Automated setup failed. Manual configuration required:"
        echo "  1. Open http://localhost:8080 in your browser"
        echo "  2. Login with: openplc / openplc"
        echo "  3. Go to 'Programs' → Upload 'plc_logic/programs/breaker_control_complete.st'"
        echo "  4. Compile the program (should show 'Compilation finished successfully!')"
        echo "  5. Go to 'Runtime' → Start PLC"
        echo ""
        
        # Option to continue without PLC or wait
        read -p "Continue with simulation mode? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Waiting for you to configure OpenPLC..."
            print_status "Press Enter when you've uploaded and started the PLC program..."
            read
            
            # Check again
            if check_plc_program; then
                print_success "PLC program is now running!"
            else
                print_warning "Still no PLC program detected, continuing in simulation mode..."
            fi
        fi
    fi
else
    print_success "PLC program is already running!"
fi

# Step 5: Start SCADA Dashboard
print_status "Starting SCADA Dashboard..."
docker compose up -d scada_dashboard

# Step 6: Wait for dashboard to be ready
if wait_for_service "SCADA Dashboard" "http://localhost:5001"; then
    print_success "SCADA Dashboard is running!"
else
    print_error "Failed to start SCADA Dashboard"
    exit 1
fi

# Step 7: Optionally start the original SCADA HMI (console version)
read -p "Start console SCADA HMI as well? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Starting console SCADA HMI..."
    docker compose up -d scada_hmi
    print_success "Console SCADA HMI is running!"
fi

# Final status
echo ""
echo "============================================"
print_success "GridGuard SCADA System is ready!"
echo ""
echo "📊 Access points:"
echo "  • SCADA Dashboard: http://localhost:5001"
echo "  • OpenPLC Config:  http://localhost:8080"
echo ""
echo "🔧 Management commands:"
echo "  • View logs:       docker compose logs -f"
echo "  • Stop system:     ./stop.sh (or docker compose down)"
echo "  • Restart:         ./start.sh"
echo ""

# Show running containers
print_status "Currently running containers:"
docker compose ps

echo ""
print_success "Startup complete! 🎉"
