"""
SCADA Web Dashboard - Real-time monitoring interface
"""
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection management
active_connections = set()
MAX_CONNECTIONS = 5  # Limit concurrent connections

app = Flask(__name__)
app.config['SECRET_KEY'] = 'scada_secret_key_2025'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True, 
                   transports=['websocket', 'polling'], 
                   allow_upgrades=True)

# Add CSP headers to allow JavaScript execution
@app.after_request
def after_request(response):
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob:; connect-src 'self' ws: wss:;"
    return response

class SCADASystem:
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
        self.initialize_grid()

    def initialize_grid(self):
        """Initialize the power grid model"""
        try:
            self.net = pp.create_empty_network()

            # Create buses
            bus1 = pp.create_bus(self.net, vn_kv=20., name="Bus 1")
            bus2 = pp.create_bus(self.net, vn_kv=0.4, name="Bus 2")
            bus3 = pp.create_bus(self.net, vn_kv=0.4, name="Bus 3")

            # Create an external grid connection
            pp.create_ext_grid(self.net, bus=bus1, vm_pu=1.02, name="Grid Connection")

            # Create a transformer
            pp.create_transformer(self.net, hv_bus=bus1, lv_bus=bus2, 
                                std_type="0.4 MVA 20/0.4 kV", name="Transformer")

            # Create a load
            pp.create_load(self.net, bus=bus3, p_mw=0.1, q_mvar=0.05, name="Load")

            # Create a line with a switch (circuit breaker)
            line1 = pp.create_line(self.net, from_bus=bus2, to_bus=bus3, 
                                 length_km=0.1, std_type="NAYY 4x50 SE", name="Line")
            sw = pp.create_switch(self.net, bus=bus2, element=line1, 
                                et="l", closed=True, name="Circuit Breaker")

            logger.info("Grid model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize grid model: {e}")
            self.system_metrics['error_count'] += 1

    def connect_to_plc(self):
        """Establish connection to OpenPLC"""
        try:
            self.client = ModbusTcpClient('openplc', port=502)
            connected = self.client.connect()
            
            if connected:
                self.plc_status['connected'] = True
                self.plc_status['last_update'] = datetime.now()
                logger.info("Successfully connected to OpenPLC")
                return True
            else:
                self.plc_status['connected'] = False
                logger.warning("Failed to connect to OpenPLC")
                return False
                
        except Exception as e:
            self.plc_status['connected'] = False
            self.plc_status['errors'].append(f"{datetime.now()}: {str(e)}")
            self.system_metrics['error_count'] += 1
            logger.error(f"PLC connection error: {e}")
            return False

    def read_plc_data(self):
        """Read data from PLC"""
        if not self.client or not self.plc_status['connected']:
            return False

        try:
            result = self.client.read_coils(address=0, count=1)
            if result.isError():
                logger.error(f"Error reading PLC coils: {result}")
                return False
            
            self.plc_status['breaker_state'] = result.bits[0]
            self.plc_status['last_update'] = datetime.now()
            self.plc_status['connection_attempts'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error reading PLC data: {e}")
            self.plc_status['errors'].append(f"{datetime.now()}: {str(e)}")
            self.system_metrics['error_count'] += 1
            return False

    def run_power_flow(self):
        """Run power flow calculation"""
        try:
            if self.net is None:
                return False

            # Update switch state based on PLC
            self.net.switch.loc[0, 'closed'] = self.plc_status['breaker_state']
            
            # Run power flow
            pp.runpp(self.net)
            
            # Extract results
            self.grid_data = {
                'timestamp': datetime.now().isoformat(),
                'breaker_closed': bool(self.plc_status['breaker_state']),
                'buses': {
                    'count': len(self.net.bus),
                    'voltage_data': {str(k): float(v) if not pd.isna(v) else 1.0 for k, v in self.net.res_bus.vm_pu.to_dict().items()} if hasattr(self.net, 'res_bus') else {}
                },
                'lines': {
                    'count': len(self.net.line),
                    'loading': {str(k): float(v) if not pd.isna(v) else 0.0 for k, v in self.net.res_line.loading_percent.to_dict().items()} if hasattr(self.net, 'res_line') else {},
                    'power_flow': {
                        'p_from_mw': {str(k): float(v) if not pd.isna(v) else 0.0 for k, v in self.net.res_line.p_from_mw.to_dict().items()} if hasattr(self.net, 'res_line') else {},
                        'q_from_mvar': {str(k): float(v) if not pd.isna(v) else 0.0 for k, v in self.net.res_line.q_from_mvar.to_dict().items()} if hasattr(self.net, 'res_line') else {}
                    }
                },
                'switches': self.net.switch.to_dict('records'),
                'loads': {
                    'active_power': self.net.load.p_mw.to_dict() if len(self.net.load) > 0 else {},
                    'reactive_power': self.net.load.q_mvar.to_dict() if len(self.net.load) > 0 else {}
                }
            }
            
            self.system_metrics['total_cycles'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Power flow calculation error: {e}")
            self.system_metrics['error_count'] += 1
            return False

    def get_simulation_data(self):
        """Get enhanced simulation data from file"""
        try:
            with open('/shared_data/scada_data.json', 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            # Return dynamic fallback data if file doesn't exist
            import time
            t = time.time()
            return {
                'timestamp': datetime.now().isoformat(),
                'breaker_state': self.plc_status.get('breaker_state', False),
                'breaker_status': 'CLOSED' if self.plc_status.get('breaker_state', False) else 'OPEN',
                'system_frequency': 60.0 + 0.05 * np.sin(t * 0.1),
                'buses': [
                    {'name': 'HV Substation', 'voltage_kv': 138.0, 'voltage_pu': 1.02 + 0.01*np.sin(t*0.05), 'voltage_actual': 138.0 * (1.02 + 0.01*np.sin(t*0.05))},
                    {'name': 'MV Bus 1', 'voltage_kv': 13.8, 'voltage_pu': 0.98 + 0.015*np.sin(t*0.07), 'voltage_actual': 13.8 * (0.98 + 0.015*np.sin(t*0.07))},
                    {'name': 'MV Bus 2', 'voltage_kv': 13.8, 'voltage_pu': 0.95 + 0.02*np.sin(t*0.03), 'voltage_actual': 13.8 * (0.95 + 0.02*np.sin(t*0.03))}
                ],
                'loads': [
                    {'name': 'Industrial Load', 'bus': 'Load Center 1', 'p_mw': 0.8 + 0.2*np.sin(t*0.02), 'q_mvar': 0.3 + 0.1*np.sin(t*0.02)},
                    {'name': 'Commercial Load', 'bus': 'Load Center 2', 'p_mw': 0.5 + 0.3*np.sin(t*0.04), 'q_mvar': 0.2 + 0.12*np.sin(t*0.04)},
                    {'name': 'Residential Feeder', 'bus': 'MV Bus 2', 'p_mw': 2.1 + 0.4*np.sin(t*0.01), 'q_mvar': 0.8 + 0.15*np.sin(t*0.01)}
                ],
                'generators': [
                    {'name': 'Distributed Generator', 'bus': 'MV Bus 2', 'p_mw': 1.5 + 0.2*np.sin(t*0.08), 'q_mvar': 0.3 + 0.1*np.cos(t*0.08)}
                ],
                'lines': [
                    {'name': 'Critical Transmission Line', 'from_bus': 'MV Bus 1', 'to_bus': 'MV Bus 2', 'p_from_mw': 1.2 + 0.3*np.sin(t*0.06), 'loading_percent': 45 + 15*np.sin(t*0.06), 'current_ka': 0.08 + 0.02*np.sin(t*0.06)}
                ],
                'power_flow': {
                    'total_load_mw': 3.4 + 0.6*np.sin(t*0.02),
                    'total_generation_mw': 1.5 + 0.2*np.sin(t*0.08),
                    'grid_import_mw': 1.9 + 0.4*np.sin(t*0.03),
                    'system_losses_mw': 0.05 + 0.02*np.sin(t*0.1)
                }
            }
        except Exception as e:
            logger.error(f"Error reading simulation data: {e}")
            return None

    def get_system_status(self):
        """Get current system status for web interface"""
        uptime = datetime.now() - self.system_metrics['uptime']
        sim_data = self.get_simulation_data()
        
        return {
            'plc_status': {
                'connected': self.plc_status['connected'],
                'last_update': self.plc_status['last_update'].isoformat() if self.plc_status['last_update'] else None,
                'breaker_state': self.plc_status['breaker_state'],
                'connection_attempts': self.plc_status['connection_attempts'],
                'recent_errors': self.plc_status['errors'][-5:] if self.plc_status['errors'] else []
            },
            'system_metrics': {
                'uptime_seconds': uptime.total_seconds(),
                'uptime_formatted': str(uptime).split('.')[0],
                'total_cycles': self.system_metrics['total_cycles'],
                'error_count': self.system_metrics['error_count'],
                'cycles_per_minute': round(self.system_metrics['total_cycles'] / max(uptime.total_seconds() / 60, 1), 2)
            },
            'grid_data': self.grid_data,
            'simulation': sim_data
        }

# Global SCADA system instance
scada_system = SCADASystem()

def scada_worker():
    """Background worker thread for SCADA operations"""
    global scada_system
    
    logger.info("SCADA worker thread starting...")
    
    try:
        # Initial connection attempt
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries and not scada_system.plc_status['connected']:
            logger.info(f"Attempting to connect to PLC (attempt {retry_count + 1}/{max_retries})")
            if scada_system.connect_to_plc():
                break
            time.sleep(3)
            retry_count += 1
        
        if not scada_system.plc_status['connected']:
            logger.warning("Could not establish PLC connection, running in simulation mode")
        
        scada_system.running = True
        
        # Main SCADA loop
        cycle_count = 0
        while scada_system.running:
            try:
                cycle_count += 1
                logger.info(f"SCADA cycle {cycle_count} starting...")
                
                # Read PLC data (or simulate if not connected)
                if scada_system.plc_status['connected']:
                    success = scada_system.read_plc_data()
                    if not success:
                        # Try to reconnect
                        logger.info("Attempting to reconnect to PLC...")
                        scada_system.connect_to_plc()
                else:
                    # Simulation mode - toggle breaker state every 30 seconds (6 cycles)
                    if cycle_count % 6 == 0:
                        scada_system.plc_status['breaker_state'] = not scada_system.plc_status['breaker_state']
                        logger.info(f"Simulation mode: Breaker state = {scada_system.plc_status['breaker_state']}")
                
                # Run power flow calculation
                logger.info("Running power flow calculation...")
                power_flow_success = scada_system.run_power_flow()
                logger.info(f"Power flow calculation: {'SUCCESS' if power_flow_success else 'FAILED'}")
                
                # Get system status
                logger.info("Getting system status...")
                system_status = scada_system.get_system_status()
                logger.info(f"System status retrieved: PLC={system_status['plc_status']['connected']}, Cycles={system_status['system_metrics']['total_cycles']}")
                
                # Emit real-time data to web clients
                logger.info("Emitting data to WebSocket clients...")
                socketio.emit('scada_update', system_status)
                logger.info("Data emitted successfully")
                
            except Exception as e:
                logger.error(f"Error in SCADA worker cycle {cycle_count}: {e}")
                logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
                scada_system.system_metrics['error_count'] += 1
            
            logger.info(f"SCADA cycle {cycle_count} complete, sleeping for 5 seconds...")
            time.sleep(5)  # 5-second update cycle
            
    except Exception as e:
        logger.error(f"Fatal error in SCADA worker thread: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/test')
def test():
    """Simple test page"""
    return render_template('test.html')

@app.route('/api/status')
def api_status():
    """REST API endpoint for system status"""
    status = scada_system.get_system_status()
    # Add connection info
    status['connections'] = {
        'active_count': len(active_connections),
        'max_allowed': MAX_CONNECTIONS,
        'active_clients': list(active_connections)
    }
    return jsonify(status)

@app.route('/api/grid-data')
def api_grid_data():
    """REST API endpoint for grid data"""
    return jsonify(scada_system.grid_data)

@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection with connection limiting"""
    client_id = request.sid
    
    # Check if we've exceeded the connection limit
    if len(active_connections) >= MAX_CONNECTIONS:
        logger.warning(f'Connection limit ({MAX_CONNECTIONS}) exceeded. Rejecting client: {client_id}')
        emit('connection_rejected', {'reason': 'Server at capacity'})
        return False  # Reject the connection
    
    # Add to active connections
    active_connections.add(client_id)
    logger.info(f'Client connected to WebSocket: {client_id} (Total connections: {len(active_connections)})')
    
    try:
        emit('scada_update', scada_system.get_system_status())
        logger.info(f'Initial data sent to client: {client_id}')
    except Exception as e:
        logger.error(f'Error sending initial data to client {client_id}: {e}')
        # Remove from active connections on error
        active_connections.discard(client_id)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    active_connections.discard(client_id)  # Remove from active connections
    logger.info(f'Client disconnected from WebSocket: {client_id} (Total connections: {len(active_connections)})')

@socketio.on('toggle_breaker')
def handle_toggle_breaker():
    """Handle manual breaker toggle from web interface"""
    if scada_system.plc_status['connected'] and scada_system.client:
        try:
            # Get current breaker state
            current_state = scada_system.plc_status.get('breaker_state', False)
            new_state = not current_state
            
            logger.info(f"Manual breaker toggle requested: {current_state} -> {new_state}")
            
            # Write to PLC output to set new state
            result = scada_system.client.write_coil(address=0, value=new_state)
            
            if not result.isError():
                scada_system.plc_status['breaker_state'] = new_state
                emit('status', {'message': f'Breaker {"CLOSED" if new_state else "OPEN"}'})
                logger.info(f"Successfully wrote {new_state} to PLC address 0")
            else:
                emit('status', {'error': f'Failed to write to PLC: {result}'})
                logger.error(f"PLC write failed: {result}")
                
        except Exception as e:
            emit('status', {'error': f'Failed to toggle breaker: {str(e)}'})
            logger.error(f"Breaker toggle error: {e}")
    else:
        emit('status', {'error': 'PLC not connected'})

if __name__ == '__main__':
    # Start the SCADA worker thread
    worker_thread = threading.Thread(target=scada_worker, daemon=True)
    worker_thread.start()
    
    logger.info("Starting SCADA Web Dashboard on http://0.0.0.0:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
