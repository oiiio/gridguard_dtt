#!/bin/bash
# GridGuard SCADA Dashboard Launcher

# Parse command line arguments
QUIET_MODE=false
CONSOLE_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -q|--quiet)
            QUIET_MODE=true
            shift
            ;;
        -c|--console)
            CONSOLE_MODE=true
            shift
            ;;
        -h|--help)
            echo "GridGuard SCADA Dashboard Launcher"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -q, --quiet     Suppress INFO logs and startup messages"
            echo "  -c, --console   Show live updating console display (no scrolling)"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0              # Normal mode with web dashboard"
            echo "  $0 --quiet      # Quiet mode, minimal output"
            echo "  $0 --console    # Live console display with updating values"
            echo "  $0 -q -c        # Quiet console mode"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$QUIET_MODE" = false ]; then
    echo "🚀 GridGuard SCADA Dashboard Launcher"
    echo "=================================="
fi

# Check if OpenPLC container is running
if ! docker ps | grep -q openplc_runtime; then
    if [ "$QUIET_MODE" = false ]; then
        echo "❌ OpenPLC container not running!"
        echo "Starting OpenPLC container..."
    fi
    docker-compose up -d openplc > /dev/null 2>&1
    if [ "$QUIET_MODE" = false ]; then
        echo "⏳ Waiting for OpenPLC to start (15 seconds)..."
    fi
    sleep 15
fi

if [ "$QUIET_MODE" = false ]; then
    echo "✅ OpenPLC container is running"
    echo "🌐 OpenPLC Web Interface: http://localhost:8080"
    echo "   Login: openplc / openplc"
    echo ""
    echo "📊 Starting SCADA Dashboard..."
    echo "🌐 Dashboard will be available at: http://localhost:5001"
    echo ""
    if [ "$CONSOLE_MODE" = false ]; then
        echo "💡 Make sure you have:"
        echo "   1. Uploaded the PLC program (breaker_control_complete.st)"
        echo "   2. Compiled and started it in OpenPLC"
        echo ""
    fi
    echo "Press Ctrl+C to stop the dashboard"
    echo "=================================="
fi

# Install dependencies if needed
if ! python3 -c "import flask, pandapower, pymodbus" 2>/dev/null; then
    if [ "$QUIET_MODE" = false ]; then
        echo "📦 Installing required Python packages..."
    fi
    pip3 install flask flask-socketio pandapower pymodbus numpy pandas > /dev/null 2>&1
fi

# Set environment variables based on options
export SCADA_QUIET_MODE=$QUIET_MODE
export SCADA_CONSOLE_MODE=$CONSOLE_MODE

# Run the standalone dashboard
python3 standalone_dashboard.py
