#!/bin/bash

# GridGuard SCADA System - Status Check Script
# This script shows the current status of all system components

echo "📊 GridGuard SCADA System Status"
echo "============================================"

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
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check Docker containers
echo ""
print_status "Docker Containers:"
docker compose ps

# Check OpenPLC Web Interface
echo ""
print_status "Service Availability:"
if curl -s -f "http://localhost:8080" > /dev/null 2>&1; then
    print_success "OpenPLC Web Interface (http://localhost:8080) - Available"
else
    print_error "OpenPLC Web Interface (http://localhost:8080) - Not Available"
fi

# Check OpenPLC Modbus Server
if timeout 2 nc -z localhost 502 2>/dev/null; then
    print_success "OpenPLC Modbus Server (port 502) - Available"
else
    print_warning "OpenPLC Modbus Server (port 502) - Not Available (Program may not be loaded)"
fi

# Check SCADA Dashboard
if curl -s -f "http://localhost:5001" > /dev/null 2>&1; then
    print_success "SCADA Dashboard (http://localhost:5001) - Available"
else
    print_error "SCADA Dashboard (http://localhost:5001) - Not Available"
fi

# Check SCADA Dashboard API
if curl -s -f "http://localhost:5001/api/status" > /dev/null 2>&1; then
    print_success "SCADA Dashboard API - Available"
    
    # Get some key metrics
    echo ""
    print_status "Current System Metrics:"
    curl -s http://localhost:5001/api/status | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    plc_status = data['plc_status']
    metrics = data['system_metrics']
    grid_data = data['grid_data']
    
    print(f'  • PLC Connected: {plc_status[\"connected\"]}')
    print(f'  • Breaker State: {\"CLOSED\" if plc_status[\"breaker_state\"] else \"OPEN\"}')
    print(f'  • System Uptime: {metrics[\"uptime_formatted\"]}')
    print(f'  • Total Cycles: {metrics[\"total_cycles\"]}')
    print(f'  • Error Count: {metrics[\"error_count\"]}')
    print(f'  • Cycles/Min: {metrics[\"cycles_per_minute\"]}')
    
    # Power system status
    if grid_data and 'lines' in grid_data and 'power_flow' in grid_data['lines']:
        power = list(grid_data['lines']['power_flow']['p_from_mw'].values())
        if power:
            print(f'  • Power Flow: {power[0]:.3f} MW')
    
except Exception as e:
    print(f'  Error parsing status: {e}')
"
else
    print_error "SCADA Dashboard API - Not Available"
fi

echo ""
print_status "Log Commands:"
echo "  • All logs:        docker compose logs -f"
echo "  • OpenPLC logs:    docker compose logs -f openplc"
echo "  • Dashboard logs:  docker compose logs -f scada_dashboard"
echo "  • Console HMI logs: docker compose logs -f scada_hmi"

echo ""
print_status "Quick Actions:"
echo "  • Restart system:  ./start.sh"
echo "  • Stop system:     ./stop.sh"
echo "  • View status:     ./status.sh"
