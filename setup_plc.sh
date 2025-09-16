#!/bin/bash

# OpenPLC Setup Automation Script
# Automates the upload and start of PLC programs

set -e

echo "🤖 OpenPLC Automation Setup"
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Default program path
PROGRAM_PATH="${1:-plc_logic/programs/breaker_control_complete.st}"

# Check if program file exists
if [ ! -f "$PROGRAM_PATH" ]; then
    print_error "Program file not found: $PROGRAM_PATH"
    echo "Usage: $0 [program_file.st]"
    exit 1
fi

print_status "Using program file: $PROGRAM_PATH"

# Check if OpenPLC is running
print_status "Checking if OpenPLC is running..."
if ! curl -s -f "http://localhost:8080" > /dev/null 2>&1; then
    print_error "OpenPLC is not running. Please start it first with:"
    echo "  docker compose up -d openplc"
    exit 1
fi

# Run the Python automation script
print_status "Running automated PLC setup..."
echo ""

if python3 automate_openplc.py --program "$PROGRAM_PATH"; then
    echo ""
    print_success "🎉 OpenPLC automation completed successfully!"
    echo ""
    print_status "System is ready:"
    echo "  • OpenPLC Web: http://localhost:8080"
    echo "  • Modbus Server: localhost:502"
    echo "  • Program: $(basename "$PROGRAM_PATH")"
    echo ""
    print_status "You can now start the SCADA services:"
    echo "  docker compose up -d scada_dashboard"
    echo ""
else
    echo ""
    print_error "Automation failed. You may need to configure manually:"
    echo "  1. Open http://localhost:8080"
    echo "  2. Login with openplc/openplc"
    echo "  3. Upload and compile the program manually"
    echo ""
    exit 1
fi
