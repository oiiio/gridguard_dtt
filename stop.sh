#!/bin/bash

# GridGuard SCADA System - Shutdown Script
# This script handles the proper shutdown sequence for the SCADA system

set -e  # Exit on any error

echo "🛑 Stopping GridGuard SCADA System..."
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

# Show current status
print_status "Current running containers:"
docker compose ps

# Graceful shutdown
print_status "Stopping all SCADA services..."
docker compose down

# Optional: Clean up volumes and networks
read -p "Clean up all data and networks? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleaning up volumes and networks..."
    docker compose down -v --remove-orphans
    print_success "Complete cleanup performed!"
else
    print_status "Data and networks preserved for next startup"
fi

echo ""
print_success "GridGuard SCADA System stopped! 🛑"
echo ""
echo "To restart the system, run: ./start.sh"
