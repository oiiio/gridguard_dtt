# GridGuard SCADA - Standalone Dashboard

The SCADA dashboard has been simplified and extracted from Docker to run as a standalone application.

## ⚡ Quick Reference

```bash
# 1. Start everything
./run_dashboard.sh --quiet --console

# 2. Configure OpenPLC (one time setup)
# - Open: http://localhost:8080 (openplc/openplc)
# - Upload: plc_logic/programs/breaker_control_complete.st  
# - Compile and Start PLC

# 3. Monitor dashboard
# - Console: Live updating display in terminal
# - Web: http://localhost:5001
```

## 🚀 Complete Setup Guide (Start to Finish)

### **Step 1: Start OpenPLC Container**
```bash
# Start OpenPLC in Docker
docker-compose up -d openplc

# Or use the dashboard script (it will auto-start OpenPLC)
./run_dashboard.sh
```

### **Step 2: Configure OpenPLC Web Interface**
1. **Open OpenPLC Web Interface**: http://localhost:8080
2. **Login**: 
   - Username: `openplc`
   - Password: `openplc`

### **Step 3: Upload PLC Program**
1. Click **"Programs"** in the left menu
2. Click **"Browse"** and select: `plc_logic/programs/breaker_control_complete.st`
3. Click **"Upload program"**
4. You should see: "Program uploaded successfully!"

### **Step 4: Compile PLC Program**
1. The program should now appear in the programs list
2. Click **"Compile"** next to `breaker_control_complete.st`
3. Wait for compilation (10-30 seconds)
4. You should see: **"Compilation finished successfully!"**
5. If compilation fails, check that the .st file is valid Structured Text

### **Step 5: Start PLC Runtime**
1. Click **"Runtime"** in the left menu
2. Click **"Start PLC"**
3. You should see: **"PLC runtime started successfully!"**
4. Status should show: **"PLC is RUNNING"**

### **Step 6: Start SCADA Dashboard**
```bash
# Option A: Live console display (recommended)
./run_dashboard.sh --quiet --console

# Option B: Web dashboard with logs
./run_dashboard.sh

# Option C: Quiet web mode
./run_dashboard.sh --quiet
```

### **Step 7: Verify Everything Works**
- **Console Mode**: You should see live updating values in terminal
- **Web Mode**: Open http://localhost:5001 for dashboard
- **PLC Connection**: Look for "PLC" indicator (vs "SIM" for simulation mode)
- **Breaker Control**: Values should show realistic power system data

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

### **OpenPLC Issues**
- **Can't connect to http://localhost:8080**: 
  - Check if container is running: `docker ps | grep openplc`
  - Restart container: `docker-compose restart openplc`
- **Compilation fails**: 
  - Verify file path: `plc_logic/programs/breaker_control_complete.st`
  - Check file syntax (should be valid Structured Text)
- **Can't start PLC Runtime**:
  - Make sure program compiled successfully first
  - Try stopping and restarting: Runtime → Stop PLC → Start PLC

### **Dashboard Issues**
- **No PLC Connection**: Dashboard runs in simulation mode with realistic data
- **Port Conflicts**: Change port in `standalone_dashboard.py` if needed
- **Missing Dependencies**: Script will automatically install required packages
- **Console mode not updating**: Make sure terminal supports ANSI escape codes

### **Quick Verification Checklist**
✅ OpenPLC container running (`docker ps`)  
✅ OpenPLC web interface accessible (http://localhost:8080)  
✅ PLC program uploaded and compiled successfully  
✅ PLC runtime started and showing "RUNNING"  
✅ Dashboard shows "PLC" mode (not "SIM")  
✅ Values are updating every 5 seconds  
✅ Web dashboard accessible (http://localhost:5001)  

### **Expected Output in Console Mode**
```
⏰ Time: 14:23:45 | Cycle: 1,234
🔌 Circuit Breaker: CLOSED (PLC)
⚡ System Frequency: 60.012 Hz

📊 POWER FLOW SUMMARY
   Total Load:          2.84 MW
   Total Generation:    1.67 MW
   Grid Import:         1.94 MW
   System Losses:       0.07 MW

🏗️  BUS VOLTAGES
   HV Substation     : 140.8 kV (1.020 pu)
   MV Bus 1          :  13.5 kV (0.978 pu)
   MV Bus 2          :  13.1 kV (0.949 pu)

🔗 CRITICAL LINE STATUS
   Power Flow:       1.23 MW
   Reactive:         0.45 MVAR
   Loading:         52.1%
   Current:          0.089 kA
```
