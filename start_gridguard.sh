#!/bin/bash
# GridGuard Complete Startup Script
# This script handles the complete setup process

echo "🚀 GridGuard SCADA - Complete Startup"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Start OpenPLC
echo -e "\n${BLUE}Step 1: Starting OpenPLC Container${NC}"
if docker ps | grep -q openplc_runtime; then
    echo -e "${GREEN}✅ OpenPLC container already running${NC}"
else
    echo "Starting OpenPLC container..."
    docker-compose up -d openplc > /dev/null 2>&1
    echo "⏳ Waiting for OpenPLC to initialize (20 seconds)..."
    sleep 20
    echo -e "${GREEN}✅ OpenPLC container started${NC}"
fi

# Step 2: Check OpenPLC accessibility
echo -e "\n${BLUE}Step 2: Checking OpenPLC Web Interface${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8080/login > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OpenPLC web interface is accessible${NC}"
        break
    else
        echo "⏳ Waiting for OpenPLC web interface... (attempt $i/10)"
        sleep 3
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}❌ Could not connect to OpenPLC web interface${NC}"
        echo "Please check Docker and try again"
        exit 1
    fi
done

# Step 3: Display setup instructions
echo -e "\n${BLUE}Step 3: OpenPLC Configuration Required${NC}"
echo -e "${YELLOW}⚠️  MANUAL SETUP REQUIRED ⚠️${NC}"
echo ""
echo "Please complete these steps in your web browser:"
echo ""
echo -e "${BLUE}1.${NC} Open: ${YELLOW}http://localhost:8080${NC}"
echo -e "${BLUE}2.${NC} Login with:"
echo "   Username: ${YELLOW}openplc${NC}"
echo "   Password: ${YELLOW}openplc${NC}"
echo ""
echo -e "${BLUE}3.${NC} Upload PLC Program:"
echo "   → Click '${YELLOW}Programs${NC}' in left menu"
echo "   → Click '${YELLOW}Browse${NC}' and select:"
echo "     ${YELLOW}plc_logic/programs/breaker_control_complete.st${NC}"
echo "   → Click '${YELLOW}Upload program${NC}'"
echo ""
echo -e "${BLUE}4.${NC} Compile Program:"
echo "   → Click '${YELLOW}Compile${NC}' next to the uploaded program"
echo "   → Wait for '${GREEN}Compilation finished successfully!${NC}'"
echo ""
echo -e "${BLUE}5.${NC} Start PLC Runtime:"
echo "   → Click '${YELLOW}Runtime${NC}' in left menu"
echo "   → Click '${YELLOW}Start PLC${NC}'"
echo "   → Verify status shows '${GREEN}PLC is RUNNING${NC}'"
echo ""

# Wait for user confirmation
echo -e "${YELLOW}Press ENTER after completing the OpenPLC setup...${NC}"
read -r

# Step 4: Start SCADA Dashboard
echo -e "\n${BLUE}Step 4: Starting SCADA Dashboard${NC}"
echo ""
echo "Choose display mode:"
echo "1) Live Console Display (recommended)"
echo "2) Web Dashboard with Logs"
echo "3) Quiet Web Dashboard"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo -e "\n${GREEN}🎯 Starting Live Console Display${NC}"
        echo -e "${BLUE}Dashboard will also be available at: http://localhost:5001${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        ./run_dashboard.sh --quiet --console
        ;;
    2)
        echo -e "\n${GREEN}🌐 Starting Web Dashboard with Logs${NC}"
        echo -e "${BLUE}Open: http://localhost:5001${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        ./run_dashboard.sh
        ;;
    3)
        echo -e "\n${GREEN}🌐 Starting Quiet Web Dashboard${NC}"
        echo -e "${BLUE}Open: http://localhost:5001${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        ./run_dashboard.sh --quiet
        ;;
    *)
        echo -e "${RED}Invalid choice. Starting default mode...${NC}"
        ./run_dashboard.sh --quiet --console
        ;;
esac
