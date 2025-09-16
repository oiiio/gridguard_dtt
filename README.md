# GridGuard SCADA Digital Twin System

A comprehensive SCADA (Supervisory Control and Data Acquisition) system for power grid monitoring and control, featuring OpenPLC integration and real-time web dashboard.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   OpenPLC Web   │    │  SCADA Console  │
│  (Dashboard)    │    │   Interface     │    │      HMI        │
│ localhost:5001  │    │ localhost:8080  │    │   (Optional)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ HTTP/WebSocket       │ HTTP                 │ Terminal
          │                      │                      │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│ SCADA Dashboard │    │ OpenPLC Runtime │    │   SCADA HMI     │
│   (Flask App)   │◄───┤   + Modbus      │    │ (Python Script) │
│                 │    │   Server :502   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │    Docker Network          │
                    │   (control_network)        │
                    └────────────────────────────┘
```

## 🚀 Quick Start

### Method 1: Using Startup Scripts (Recommended)

```bash
# Start the system
./start.sh

# Check status
./status.sh

# Stop the system
./stop.sh
```

### Method 2: Manual Docker Compose

```bash
# Start core services
docker compose up -d

# Start with console HMI as well
docker compose --profile console up -d
```

## 📋 Proper Startup/Shutdown Protocol

### 🟢 **Startup Sequence**

1. **Clean Environment**
   ```bash
   ./stop.sh  # or docker compose down
   ```

2. **Start OpenPLC**
   ```bash
   # Starts automatically with ./start.sh
   # Manual: docker compose up -d openplc
   ```

3. **Configure PLC Program** (First time or after reset)
   - Open http://localhost:8080
   - Login: `openplc` / `openplc`
   - Go to **Programs** → **Browse** → Upload `plc_logic/programs/breaker_control_complete.st`
   - Click **Compile** (wait for "Compilation finished successfully!")
   - Go to **Runtime** → **Start PLC**
   - Verify Modbus server shows "Listening on port 502"

4. **Start SCADA Services**
   ```bash
   # Dashboard starts automatically with ./start.sh
   # Manual: docker compose up -d scada_dashboard
   ```

5. **Verify System**
   ```bash
   ./status.sh
   ```

### 🔴 **Shutdown Sequence**

1. **Graceful Shutdown**
   ```bash
   ./stop.sh
   ```

2. **Complete Cleanup** (if needed)
   ```bash
   docker compose down -v --remove-orphans
   docker system prune -f  # Optional: clean up unused Docker resources
   ```

## 🎯 **Service Access Points**

| Service | URL | Purpose |
|---------|-----|---------|
| **SCADA Dashboard** | http://localhost:5001 | Main monitoring interface |
| **OpenPLC Config** | http://localhost:8080 | PLC programming & control |
| **SCADA API** | http://localhost:5001/api/status | REST API for system data |

## 🔧 **Management Commands**

### Status & Monitoring
```bash
./status.sh                           # Full system status
docker compose ps                     # Container status
docker compose logs -f                # All logs (live)
docker compose logs -f scada_dashboard # Dashboard logs only
```

### Service Control
```bash
# Restart specific services
docker compose restart scada_dashboard
docker compose restart openplc

# Scale services (if needed)
docker compose up -d --scale scada_dashboard=2
```

### Debugging
```bash
# Execute commands in containers
docker exec -it scada_dashboard bash
docker exec -it openplc_runtime bash

# Test API directly
curl http://localhost:5001/api/status | python -m json.tool
```

## 🛠️ **Troubleshooting**

### Common Issues

1. **Port 5001 Access Denied**
   - Check if port is in use: `lsof -i :5001`
   - Restart dashboard: `docker compose restart scada_dashboard`

2. **PLC Not Connecting**
   - Verify OpenPLC program is compiled and running
   - Check Modbus server: `nc -z localhost 502`
   - Review PLC logs: `docker compose logs openplc`

3. **Dashboard Shows No Data**
   - Check API: `curl http://localhost:5001/api/status`
   - Verify WebSocket connection in browser console
   - Restart dashboard service

4. **NaN Values in Dashboard**
   - System automatically handles NaN values
   - If issues persist, restart: `./start.sh`

### Service Dependencies

```
openplc (healthy) 
├── scada_dashboard (depends on openplc health)
└── scada_hmi (depends on openplc health, profile: console)
```

## 📊 **System Features**

### SCADA Dashboard (Web Interface)
- Real-time monitoring with 5-second updates
- Interactive power system topology
- Historical charts (power flow, voltage)
- System metrics and health monitoring  
- Manual breaker control
- WebSocket-based live updates

### OpenPLC Integration
- Modbus/TCP communication on port 502
- Structured Text (ST) programming support
- Real-time I/O mapping (%IX0.0, %QX0.0)
- Web-based configuration interface

### Console HMI (Optional)
- Terminal-based monitoring
- Direct Modbus communication
- Detailed power flow calculations
- Error logging and diagnostics

## 🔄 **Development Workflow**

1. **Make Changes**
   ```bash
   # Edit code files
   # Modify PLC programs in plc_logic/programs/
   ```

2. **Test Changes**
   ```bash
   ./stop.sh
   ./start.sh
   ```

3. **Monitor System**
   ```bash
   ./status.sh
   docker compose logs -f scada_dashboard
   ```

## 📁 **File Structure**

```
gridguard_dtt/
├── start.sh                    # System startup script
├── stop.sh                     # System shutdown script
├── status.sh                   # Status checking script
├── docker-compose.yml          # Service orchestration
├── Dockerfile.scada            # SCADA services image
├── requirements.txt            # Python dependencies
├── web_dashboard.py            # Flask web dashboard
├── physical_process.py         # Console SCADA HMI
├── templates/
│   └── dashboard.html          # Web dashboard UI
└── plc_logic/
    └── programs/
        ├── breaker_control.st
        └── breaker_control_complete.st
```

## 🎯 **Best Practices**

1. **Always use the startup script** for consistent initialization
2. **Upload PLC program once** - it persists between restarts  
3. **Check status regularly** with `./status.sh`
4. **Monitor logs** for early issue detection
5. **Use graceful shutdown** to preserve data
6. **Test changes incrementally** with proper restart sequence

## 🚨 **Emergency Procedures**

### Complete System Reset
```bash
./stop.sh
docker compose down -v --remove-orphans
docker system prune -f
./start.sh
# Re-upload PLC program via web interface
```

### Quick Recovery
```bash
./stop.sh
./start.sh
```

---

**Happy monitoring! 🎉**
