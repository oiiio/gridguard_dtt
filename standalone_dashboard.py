"""
Standalone SCADA Web Dashboard - Runs outside Docker
Connects to OpenPLC container running on localhost:502
"""
import pandapower as pp
import pandas as pd
import numpy as np
from pymodbus.client import ModbusTcpClient
import time
import threading
import json
import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging

# Configure logging based on environment variables
QUIET_MODE = os.getenv('SCADA_QUIET_MODE', 'false').lower() == 'true'
CONSOLE_MODE = os.getenv('SCADA_CONSOLE_MODE', 'false').lower() == 'true'

if QUIET_MODE:
    logging.basicConfig(level=logging.ERROR)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Suppress Flask/SocketIO logs in quiet mode
if QUIET_MODE:
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
app = Flask(__name__)
app.config['SECRET_KEY'] = 'scada_secret_key_2025'
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)
import pandapower as pp
import pandas as pd
import numpy as np
from pymodbus.client import ModbusTcpClient
import time
import threading
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'scada_secret_key_2025'
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

class StandaloneSCADA:
    def __init__(self):
        self.grid_data = {}
        self.plc_status = {
            'connected': False,
            'last_update': None,
            'breaker_state': False,
            'connection_attempts': 0,
            'errors': []
        }
        self.system_metrics = {
            'uptime': datetime.now(),
            'total_cycles': 0,
            'error_count': 0
        }
        self.client = None
        self.net = None
        self.running = False
        self.simulation_data = {}
        self.simulation_time = 0
        self.initialize_grid()

    def initialize_grid(self):
        """Initialize a realistic power grid model"""
        try:
            self.net = pp.create_empty_network(name="GridGuard Demo System")
            
            # Create buses (voltage levels)
            self.bus_hv = pp.create_bus(self.net, vn_kv=138.0, name="HV Substation", type="n")
            self.bus_mv1 = pp.create_bus(self.net, vn_kv=13.8, name="MV Bus 1", type="n")
            self.bus_mv2 = pp.create_bus(self.net, vn_kv=13.8, name="MV Bus 2", type="n") 
            self.bus_lv1 = pp.create_bus(self.net, vn_kv=0.48, name="Load Center 1", type="n")
            self.bus_lv2 = pp.create_bus(self.net, vn_kv=0.48, name="Load Center 2", type="n")
            
            # External grid connection
            pp.create_ext_grid(self.net, bus=self.bus_hv, vm_pu=1.02, name="Transmission Grid")
            
            # Transformers
            pp.create_transformer(self.net, hv_bus=self.bus_hv, lv_bus=self.bus_mv1, 
                                std_type="25 MVA 110/20 kV", name="Main Transformer")
            pp.create_transformer(self.net, hv_bus=self.bus_mv1, lv_bus=self.bus_lv1,
                                std_type="0.63 MVA 20/0.4 kV", name="Distribution Transformer 1")
            pp.create_transformer(self.net, hv_bus=self.bus_mv2, lv_bus=self.bus_lv2,
                                std_type="0.63 MVA 20/0.4 kV", name="Distribution Transformer 2")
            
            # Dynamic loads
            self.load1 = pp.create_load(self.net, bus=self.bus_lv1, p_mw=0.8, q_mvar=0.3, name="Industrial Load")
            self.load2 = pp.create_load(self.net, bus=self.bus_lv2, p_mw=0.5, q_mvar=0.2, name="Commercial Load")
            self.load3 = pp.create_load(self.net, bus=self.bus_mv2, p_mw=2.1, q_mvar=0.8, name="Residential Feeder")
            
            # Generation
            pp.create_gen(self.net, bus=self.bus_mv2, p_mw=1.5, vm_pu=1.0, name="Distributed Generator")
            
            # Critical transmission line with PLC-controlled breaker
            self.critical_line = pp.create_line(self.net, from_bus=self.bus_mv1, to_bus=self.bus_mv2, 
                                              length_km=5.2, std_type="NA2XS2Y 1x185 RM/25 12/20 kV",
                                              name="Critical Transmission Line")
            
            # PLC-controlled circuit breaker
            self.breaker_switch = pp.create_switch(self.net, bus=self.bus_mv1, element=self.critical_line, 
                                                 et="l", closed=True, name="PLC Circuit Breaker")
            
            logger.info("Enhanced grid model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize grid model: {e}")
            self.system_metrics['error_count'] += 1

    def connect_to_plc(self):
        """Connect to OpenPLC running in Docker container"""
        try:
            # Connect to localhost:502 since OpenPLC container exposes port 502
            self.client = ModbusTcpClient('localhost', port=502)
            connected = self.client.connect()
            
            if connected:
                self.plc_status['connected'] = True
                self.plc_status['last_update'] = datetime.now()
                logger.info("Successfully connected to OpenPLC container")
                return True
            else:
                self.plc_status['connected'] = False
                logger.warning("Failed to connect to OpenPLC container")
                return False
                
        except Exception as e:
            self.plc_status['connected'] = False
            self.plc_status['errors'].append(f"{datetime.now()}: {str(e)}")
            self.system_metrics['error_count'] += 1
            logger.error(f"PLC connection error: {e}")
            return False

    def read_plc_data(self):
        """Read breaker state from PLC"""
        if not self.client or not self.plc_status['connected']:
            return False

        try:
            result = self.client.read_coils(address=0, count=1)
            if result.isError():
                logger.error(f"Error reading PLC coils: {result}")
                return False
            
            self.plc_status['breaker_state'] = result.bits[0]
            self.plc_status['last_update'] = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"Error reading PLC data: {e}")
            self.plc_status['errors'].append(f"{datetime.now()}: {str(e)}")
            return False

    def update_dynamic_loads(self):
        """Update loads with realistic time-varying patterns"""
        # Simulate daily load patterns (accelerated time)
        hour_of_day = (self.simulation_time / 10) % 24  # 10 seconds = 1 hour
        
        # Industrial load (stable, peak during work hours)
        industrial_factor = 0.7 + 0.3 * (1 + np.sin(2 * np.pi * (hour_of_day - 6) / 24))
        
        # Commercial load (peak during business hours)
        if 8 <= hour_of_day <= 18:
            commercial_factor = 0.9 + 0.2 * np.random.normal(0, 0.1)
        else:
            commercial_factor = 0.3 + 0.1 * np.random.normal(0, 0.1)
        
        # Residential load (peak evening)
        residential_factor = 0.4 + 0.6 * (1 + np.sin(2 * np.pi * (hour_of_day - 19) / 24)) ** 2
        
        # Add some random variation
        noise = 0.05 * np.random.normal(0, 1, 3)
        
        # Update loads
        self.net.load.loc[0, 'p_mw'] = max(0.2, 0.8 * industrial_factor + noise[0])
        self.net.load.loc[1, 'p_mw'] = max(0.1, 0.5 * commercial_factor + noise[1])  
        self.net.load.loc[2, 'p_mw'] = max(0.5, 2.1 * residential_factor + noise[2])
        
        # Update reactive power proportionally
        self.net.load.loc[0, 'q_mvar'] = self.net.load.loc[0, 'p_mw'] * 0.375
        self.net.load.loc[1, 'q_mvar'] = self.net.load.loc[1, 'p_mw'] * 0.4
        self.net.load.loc[2, 'q_mvar'] = self.net.load.loc[2, 'p_mw'] * 0.38

    def run_power_flow(self):
        """Run power flow calculation with enhanced data"""
        try:
            # Update breaker state
            breaker_state = self.plc_status['breaker_state']
            if not self.plc_status['connected']:
                # Simulation mode - cycle breaker every 30 seconds (6 cycles)
                cycle_time = self.simulation_time % 40
                breaker_state = cycle_time < 30
                self.plc_status['breaker_state'] = breaker_state
            
            self.net.switch.loc[0, 'closed'] = breaker_state
            
            # Update dynamic loads
            self.update_dynamic_loads()
            
            # Run power flow
            pp.runpp(self.net, algorithm="nr", max_iteration=20)
            
            # Create comprehensive simulation data
            self.simulation_data = {
                'timestamp': datetime.now().isoformat(),
                'breaker_state': breaker_state,
                'breaker_status': 'CLOSED' if breaker_state else 'OPEN',
                'system_frequency': 60.0 + np.random.normal(0, 0.02),
                'buses': [],
                'lines': [],
                'loads': [],
                'generators': [],
                'power_flow': {}
            }
            
            # Bus voltages
            for idx, bus in self.net.bus.iterrows():
                bus_data = {
                    'name': bus['name'],
                    'voltage_kv': bus['vn_kv'],
                    'voltage_pu': self.net.res_bus.loc[idx, 'vm_pu'],
                    'angle_deg': self.net.res_bus.loc[idx, 'va_degree'],
                    'voltage_actual': self.net.res_bus.loc[idx, 'vm_pu'] * bus['vn_kv']
                }
                self.simulation_data['buses'].append(bus_data)
            
            # Line flows
            for idx, line in self.net.line.iterrows():
                if idx in self.net.res_line.index:
                    line_data = {
                        'name': line['name'],
                        'from_bus': self.net.bus.loc[line['from_bus'], 'name'],
                        'to_bus': self.net.bus.loc[line['to_bus'], 'name'],
                        'p_from_mw': self.net.res_line.loc[idx, 'p_from_mw'],
                        'q_from_mvar': self.net.res_line.loc[idx, 'q_from_mvar'],
                        'loading_percent': self.net.res_line.loc[idx, 'loading_percent'],
                        'current_ka': self.net.res_line.loc[idx, 'i_from_ka']
                    }
                    self.simulation_data['lines'].append(line_data)
            
            # Load information
            for idx, load in self.net.load.iterrows():
                load_data = {
                    'name': load['name'],
                    'bus': self.net.bus.loc[load['bus'], 'name'],
                    'p_mw': load['p_mw'],
                    'q_mvar': load['q_mvar']
                }
                self.simulation_data['loads'].append(load_data)
            
            # Generator information
            for idx, gen in self.net.gen.iterrows():
                if idx in self.net.res_gen.index:
                    gen_data = {
                        'name': gen['name'],
                        'bus': self.net.bus.loc[gen['bus'], 'name'],
                        'p_mw': self.net.res_gen.loc[idx, 'p_mw'],
                        'q_mvar': self.net.res_gen.loc[idx, 'q_mvar']
                    }
                    self.simulation_data['generators'].append(gen_data)
            
            # Overall power flow summary
            total_load = sum([load['p_mw'] for load in self.simulation_data['loads']])
            total_generation = sum([gen['p_mw'] for gen in self.simulation_data['generators']])
            
            self.simulation_data['power_flow'] = {
                'total_load_mw': total_load,
                'total_generation_mw': total_generation,
                'grid_import_mw': self.net.res_ext_grid.loc[0, 'p_mw'],
                'system_losses_mw': abs(total_generation + self.net.res_ext_grid.loc[0, 'p_mw'] - total_load)
            }
            
            self.system_metrics['total_cycles'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Power flow calculation error: {e}")
            self.system_metrics['error_count'] += 1
            return False

    def get_system_status(self):
        """Get current system status for web interface"""
        uptime = datetime.now() - self.system_metrics['uptime']
        
        return {
            'plc_status': {
                'connected': self.plc_status['connected'],
                'last_update': self.plc_status['last_update'].isoformat() if self.plc_status['last_update'] else None,
                'breaker_state': self.plc_status['breaker_state'],
                'connection_attempts': self.plc_status['connection_attempts'],
                'recent_errors': self.plc_status['errors'][-3:] if self.plc_status['errors'] else []
            },
            'system_metrics': {
                'uptime_seconds': uptime.total_seconds(),
                'uptime_formatted': str(uptime).split('.')[0],
                'total_cycles': self.system_metrics['total_cycles'],
                'error_count': self.system_metrics['error_count']
            },
            'simulation': self.simulation_data
        }

# Global SCADA instance
scada = StandaloneSCADA()

def scada_worker():
    """Background worker thread"""
    if not QUIET_MODE:
        logger.info("🚀 Standalone SCADA worker starting...")
    
    # Try to connect to OpenPLC
    max_retries = 5
    for attempt in range(max_retries):
        if not QUIET_MODE:
            logger.info(f"Connecting to OpenPLC container (attempt {attempt + 1}/{max_retries})")
        if scada.connect_to_plc():
            break
        time.sleep(2)
    
    if not scada.plc_status['connected']:
        if not QUIET_MODE:
            logger.warning("⚠️  Running in simulation mode (no PLC connection)")
    else:
        if not QUIET_MODE:
            logger.info("✅ Connected to OpenPLC container")
    
    scada.running = True
    
    # Console mode setup
    if CONSOLE_MODE:
        print("\n" + "="*80)
        print("🎯 GridGuard SCADA - Live Console Monitor")
        print("="*80)
        print("🌐 Web Dashboard: http://localhost:5001")
        print("🔧 OpenPLC Interface: http://localhost:8080")
        print("Press Ctrl+C to stop")
        print("="*80)
        
        # Reserve space for live display (move cursor down)
        for _ in range(15):
            print()
    
    # Main loop
    cycle = 0
    while scada.running:
        try:
            cycle += 1
            
            # Read PLC or simulate
            if scada.plc_status['connected']:
                scada.read_plc_data()
            
            # Run power flow
            scada.run_power_flow()
            
            # Get status and emit to clients
            status = scada.get_system_status()
            socketio.emit('scada_update', status)
            
            # Display output based on mode
            sim = status['simulation']
            if sim:
                if CONSOLE_MODE:
                    # Clear previous output and move cursor up
                    sys.stdout.write('\033[15A')  # Move cursor up 15 lines
                    sys.stdout.write('\033[J')    # Clear from cursor to end of screen
                    
                    # Display live data in fixed position
                    now = datetime.now().strftime('%H:%M:%S')
                    print(f"⏰ Time: {now} | Cycle: {cycle:,}")
                    print(f"🔌 Circuit Breaker: {sim['breaker_status']} ({'PLC' if scada.plc_status['connected'] else 'SIM'})")
                    print(f"⚡ System Frequency: {sim['system_frequency']:.3f} Hz")
                    print("")
                    
                    # Power summary
                    pf = sim['power_flow']
                    print(f"📊 POWER FLOW SUMMARY")
                    print(f"   Total Load:       {pf['total_load_mw']:8.2f} MW")
                    print(f"   Total Generation: {pf['total_generation_mw']:8.2f} MW")
                    print(f"   Grid Import:      {pf['grid_import_mw']:8.2f} MW")
                    print(f"   System Losses:    {pf['system_losses_mw']:8.2f} MW")
                    print("")
                    
                    # Bus voltages
                    print(f"🏗️  BUS VOLTAGES")
                    for bus in sim['buses'][:3]:
                        print(f"   {bus['name']:<18}: {bus['voltage_actual']:7.1f} kV ({bus['voltage_pu']:5.3f} pu)")
                    print("")
                    
                    # Line status (if breaker closed)
                    if sim['breaker_state'] and sim.get('lines'):
                        line = sim['lines'][0]
                        print(f"🔗 CRITICAL LINE STATUS")
                        print(f"   Power Flow:    {line['p_from_mw']:7.2f} MW")
                        print(f"   Reactive:      {line['q_from_mvar']:7.2f} MVAR") 
                        print(f"   Loading:       {line['loading_percent']:7.1f}%")
                        print(f"   Current:       {line['current_ka']:7.3f} kA")
                    else:
                        print(f"🔗 CRITICAL LINE STATUS")
                        print(f"   Status: DISCONNECTED (Breaker Open)")
                        print("")
                        print("")
                        print("")
                    
                    sys.stdout.flush()
                
                elif not QUIET_MODE:
                    # Regular scrolling output
                    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
                    print(f"🔌 Breaker: {sim['breaker_status']}")
                    print(f"📊 Load: {sim['power_flow']['total_load_mw']:.2f} MW")
                    print(f"🏭 Import: {sim['power_flow']['grid_import_mw']:.2f} MW")
                    print(f"⚡ Freq: {sim['system_frequency']:.2f} Hz")
                    
                    # Show voltages
                    for bus in sim['buses'][:3]:
                        print(f"   {bus['name']}: {bus['voltage_actual']:.1f} kV")
            
            scada.simulation_time += 5
            
        except KeyboardInterrupt:
            if CONSOLE_MODE:
                print("\n\n🛑 Dashboard stopped by user")
            break
        except Exception as e:
            if not QUIET_MODE:
                logger.error(f"SCADA worker error: {e}")
            scada.system_metrics['error_count'] += 1
        
        time.sleep(5)

@app.route('/')
def index():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """REST API for status"""
    return jsonify(scada.get_system_status())

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f'Client connected: {request.sid}')
    emit('scada_update', scada.get_system_status())

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f'Client disconnected: {request.sid}')

if __name__ == '__main__':
    if not QUIET_MODE:
        print("=" * 60)
        print("🌟 GridGuard Standalone SCADA Dashboard")
        print("=" * 60)
        if not CONSOLE_MODE:
            print("📋 Setup Instructions:")
            print("1. Make sure OpenPLC container is running:")
            print("   docker-compose up openplc")
            print("2. Upload and start PLC program at http://localhost:8080")
            print("3. Dashboard will be available at http://localhost:5001")
        print("=" * 60)
    
    # Start worker thread
    worker_thread = threading.Thread(target=scada_worker, daemon=True)
    worker_thread.start()
    
    # In console mode, don't start Flask server in main thread
    if CONSOLE_MODE:
        # Start Flask in background thread
        flask_thread = threading.Thread(
            target=lambda: socketio.run(app, host='0.0.0.0', port=5001, debug=False, log_output=False),
            daemon=True
        )
        flask_thread.start()
        
        # Keep main thread alive for console display
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Dashboard stopped by user")
            sys.exit(0)
    else:
        # Normal web mode
        socketio.run(app, host='0.0.0.0', port=5001, debug=False, log_output=not QUIET_MODE)
