"""
SCADA Web Dashboard - Real-time monitoring interface
"""
import pandapower as pp
from pymodbus.client import ModbusTcpClient
import time
import threading
import json
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'scada_secret_key_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

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
                    'voltage_data': self.net.res_bus.vm_pu.to_dict() if hasattr(self.net, 'res_bus') else {}
                },
                'lines': {
                    'count': len(self.net.line),
                    'loading': self.net.res_line.loading_percent.to_dict() if hasattr(self.net, 'res_line') else {},
                    'power_flow': {
                        'p_from_mw': self.net.res_line.p_from_mw.to_dict() if hasattr(self.net, 'res_line') else {},
                        'q_from_mvar': self.net.res_line.q_from_mvar.to_dict() if hasattr(self.net, 'res_line') else {}
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

    def get_system_status(self):
        """Get current system status for web interface"""
        uptime = datetime.now() - self.system_metrics['uptime']
        
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
            'grid_data': self.grid_data
        }

# Global SCADA system instance
scada_system = SCADASystem()

def scada_worker():
    """Background worker thread for SCADA operations"""
    global scada_system
    
    logger.info("SCADA worker thread starting...")
    
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
    while scada_system.running:
        try:
            # Read PLC data (or simulate if not connected)
            if scada_system.plc_status['connected']:
                success = scada_system.read_plc_data()
                if not success:
                    # Try to reconnect
                    logger.info("Attempting to reconnect to PLC...")
                    scada_system.connect_to_plc()
            else:
                # Simulation mode - toggle breaker state every 30 seconds
                if scada_system.system_metrics['total_cycles'] % 6 == 0:
                    scada_system.plc_status['breaker_state'] = not scada_system.plc_status['breaker_state']
                    logger.info(f"Simulation mode: Breaker state = {scada_system.plc_status['breaker_state']}")
            
            # Run power flow calculation
            scada_system.run_power_flow()
            
            # Emit real-time data to web clients
            socketio.emit('scada_update', scada_system.get_system_status())
            
        except Exception as e:
            logger.error(f"Error in SCADA worker: {e}")
            scada_system.system_metrics['error_count'] += 1
        
        time.sleep(5)  # 5-second update cycle

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """REST API endpoint for system status"""
    return jsonify(scada_system.get_system_status())

@app.route('/api/grid-data')
def api_grid_data():
    """REST API endpoint for grid data"""
    return jsonify(scada_system.grid_data)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected to WebSocket')
    emit('scada_update', scada_system.get_system_status())

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected from WebSocket')

@socketio.on('toggle_breaker')
def handle_toggle_breaker():
    """Handle manual breaker toggle from web interface"""
    if scada_system.plc_status['connected'] and scada_system.client:
        try:
            # In a real system, you'd write to the PLC input that controls the breaker
            # For demonstration, we'll just toggle the local state
            new_state = not scada_system.plc_status['breaker_state']
            logger.info(f"Manual breaker toggle requested: {new_state}")
            
            # Note: In a real implementation, you'd write to PLC inputs here
            # result = scada_system.client.write_coil(address=0, value=new_state)
            
            emit('status', {'message': f'Breaker toggle requested: {"CLOSED" if new_state else "OPEN"}'})
        except Exception as e:
            emit('status', {'error': f'Failed to toggle breaker: {str(e)}'})
    else:
        emit('status', {'error': 'PLC not connected'})

if __name__ == '__main__':
    # Start the SCADA worker thread
    worker_thread = threading.Thread(target=scada_worker, daemon=True)
    worker_thread.start()
    
    logger.info("Starting SCADA Web Dashboard on http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
