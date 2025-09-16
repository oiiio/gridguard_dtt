# GridGuard SCADA - Standalone Dashboard

The SCADA dashboard has been simplified and extracted from Docker to run as a standalone application.

## Quick Start

### Option 1: Using the Shell Script with Options
```bash
# Normal mode with web dashboard
./run_dashboard.sh

# Quiet mode (minimal output)
./run_dashboard.sh --quiet

# Live console display (updating values in place)
./run_dashboard.sh --console

# Quiet console mode (live display with minimal logs)
./run_dashboard.sh --quiet --console
```

### Option 2: Using the Python Launcher
```bash
python3 launch_dashboard.py
```

### Option 3: Manual Setup
1. Install dependencies:
   ```bash
   pip3 install flask flask-socketio pandapower pymodbus numpy pandas
   ```

2. Start OpenPLC container:
   ```bash
   docker-compose up -d openplc
   ```

3. Run the dashboard:
   ```bash
   # Normal web mode
   python3 standalone_dashboard.py
   
   # Quiet mode
   SCADA_QUIET_MODE=true python3 standalone_dashboard.py
   
   # Console mode (live updating display)
   SCADA_CONSOLE_MODE=true python3 standalone_dashboard.py
   
   # Both modes
   SCADA_QUIET_MODE=true SCADA_CONSOLE_MODE=true python3 standalone_dashboard.py
   ```

## Display Modes

### **Web Dashboard Mode** (Default)
- Web interface at http://localhost:5001
- Real-time WebSocket updates
- Scrolling console output with system status

### **Console Mode** (`--console` or `-c`)
- Live updating display in terminal (no scrolling)
- Real-time power system values updating in place
- Shows:
  - ⏰ Current time and cycle count
  - 🔌 Circuit breaker status (PLC/SIM mode indicator)
  - ⚡ System frequency
  - 📊 Power flow summary (load, generation, import, losses)
  - 🏗️ Bus voltages for key substations  
  - 🔗 Critical transmission line status
- Web dashboard still available in background

### **Quiet Mode** (`--quiet` or `-q`)
- Suppresses INFO logs and startup messages
- Minimal console output
- Combines well with console mode for clean live display

## Shell Script Options

```bash
./run_dashboard.sh [OPTIONS]

Options:
  -q, --quiet     Suppress INFO logs and startup messages
  -c, --console   Show live updating console display (no scrolling)
  -h, --help      Show help message

Examples:
  ./run_dashboard.sh              # Normal web mode
  ./run_dashboard.sh --quiet      # Quiet web mode
  ./run_dashboard.sh --console    # Live console display
  ./run_dashboard.sh -q -c        # Quiet live console display
```

## Setup Steps

1. **Start OpenPLC**: The launcher will automatically start the OpenPLC container
2. **Configure PLC Program**:
   - Open http://localhost:8080
   - Login: `openplc` / `openplc`
   - Upload `plc_logic/programs/breaker_control_complete.st`
   - Compile and start the program
3. **Access Dashboard**: Open http://localhost:5001

## Features

- **Real-time Power System Simulation**: Dynamic loads, voltage levels, power flows
- **PLC Integration**: Connects directly to OpenPLC container (localhost:502)
- **Web Interface**: Real-time dashboard with WebSocket updates
- **Simulation Mode**: Runs with realistic data even without PLC connection
- **No Docker Complexity**: Runs as a simple Python application

## Dashboard Displays

- ⚡ System frequency (60Hz ± variations)
- 🔌 Circuit breaker status (controlled by PLC)
- 📊 Real-time load data (Industrial, Commercial, Residential)
- 🏭 Power generation and grid import
- 📈 Bus voltages and line loadings
- 🔗 Critical transmission line monitoring

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │    │  Standalone      │    │  OpenPLC        │
│   (localhost:   │◄──►│  Dashboard       │◄──►│  Container      │
│   5001)         │    │  (Python)        │    │  (localhost:502)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Why Standalone?

- **Simpler Setup**: No complex Docker networking
- **Easier Development**: Direct Python debugging
- **Better Performance**: No container overhead for dashboard
- **Flexible Deployment**: Run on any system with Python

## Troubleshooting

- **No PLC Connection**: Dashboard runs in simulation mode with realistic data
- **Port Conflicts**: Change port in `standalone_dashboard.py` if needed
- **Missing Dependencies**: Launchers will automatically install required packages
