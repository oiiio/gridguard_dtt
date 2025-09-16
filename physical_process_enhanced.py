import pandapower as pp
from pymodbus.client import ModbusTcpClient
import time
import numpy as np
import json
from datetime import datetime
import os # <-- ADDED: To handle file paths

class PowerSystemHMI:
    def __init__(self):
        # --- ADDED: Define log file path and ensure directory exists ---
        self.log_file = "/usr/src/app/logs/power_flow.log"
        log_dir = os.path.dirname(self.log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        # -----------------------------------------------------------------
        
        self.setup_power_system()
        self.connect_to_plc()
        self.simulation_time = 0
        
    def setup_power_system(self):
        """Create a realistic power grid model with multiple measurement points"""
        self.net = pp.create_empty_network(name="GridGuard Demo System")
        
        # Create buses (voltage levels)
        self.bus_hv = pp.create_bus(self.net, vn_kv=138.0, name="HV Substation", type="n")
        self.bus_mv1 = pp.create_bus(self.net, vn_kv=13.8, name="MV Bus 1", type="n")
        self.bus_mv2 = pp.create_bus(self.net, vn_kv=13.8, name="MV Bus 2", type="n") 
        self.bus_lv1 = pp.create_bus(self.net, vn_kv=0.48, name="Load Center 1", type="n")
        self.bus_lv2 = pp.create_bus(self.net, vn_kv=0.48, name="Load Center 2", type="n")
        
        # External grid connection (infinite bus)
        pp.create_ext_grid(self.net, bus=self.bus_hv, vm_pu=1.02, name="Transmission Grid")
        
        # Transformers
        pp.create_transformer(self.net, hv_bus=self.bus_hv, lv_bus=self.bus_mv1, 
                            std_type="25 MVA 110/20 kV", name="Main Transformer")
        pp.create_transformer(self.net, hv_bus=self.bus_mv1, lv_bus=self.bus_lv1,
                            std_type="0.63 MVA 20/0.4 kV", name="Distribution Transformer 1")
        pp.create_transformer(self.net, hv_bus=self.bus_mv2, lv_bus=self.bus_lv2,
                            std_type="0.63 MVA 20/0.4 kV", name="Distribution Transformer 2")
        
        # Loads with realistic and time-varying patterns
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
    
    def connect_to_plc(self):
        """Connect to OpenPLC Modbus server"""
        self.client = ModbusTcpClient('openplc', port=502)
        
        print("--- Connecting to OpenPLC Modbus Server ---")
        max_retries = 15
        for attempt in range(max_retries):
            try:
                print(f"Connection attempt {attempt + 1}/{max_retries}...")
                if self.client.connect():
                    print("✅ Connected to OpenPLC successfully!")
                    return
            except Exception as e:
                print(f"Connection attempt failed: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2)
        
        print("❌ Could not connect to OpenPLC after multiple attempts")
        print("Continuing with simulation mode...")
        self.client = None
    
    def get_plc_breaker_state(self):
        """Read breaker state from PLC"""
        if not self.client:
            # Simulation mode - create dynamic breaker behavior for demo
            # Breaker cycles: closed for 30s, open for 10s
            cycle_time = self.simulation_time % 40
            return cycle_time < 30
            
        try:
            result = self.client.read_coils(address=0, count=1)
            if result.isError():
                print(f"PLC read error: {result}")
                return True  # Default to closed
            return result.bits[0]
        except Exception as e:
            print(f"PLC communication error: {e}")
            return True
    
    def update_dynamic_loads(self):
        """Update loads with realistic time-varying patterns"""
        # Simulate daily load patterns
        hour_of_day = (self.simulation_time / 10) % 24  # 10 seconds = 1 hour for demo
        
        # Industrial load (more stable, peak during work hours)
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
        """Run power flow analysis and return results"""
        try:
            pp.runpp(self.net, algorithm="nr", max_iteration=20)
            return True
        except Exception as e:
            print(f"Power flow convergence error: {e}")
            return False
    
    def get_system_metrics(self):
        """Extract key system metrics for SCADA display"""
        breaker_state = self.get_plc_breaker_state()
        self.net.switch.loc[0, 'closed'] = breaker_state
        
        # Update dynamic loads
        self.update_dynamic_loads()
        
        # Run power flow
        converged = self.run_power_flow()
        
        if not converged:
            return None
            
        # Extract metrics
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'breaker_state': breaker_state,
            'breaker_status': 'CLOSED' if breaker_state else 'OPEN',
            'system_frequency': 60.0 + np.random.normal(0, 0.02),  # Hz
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
            metrics['buses'].append(bus_data)
        
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
                metrics['lines'].append(line_data)
        
        # Load information
        for idx, load in self.net.load.iterrows():
            load_data = {
                'name': load['name'],
                'bus': self.net.bus.loc[load['bus'], 'name'],
                'p_mw': load['p_mw'],
                'q_mvar': load['q_mvar']
            }
            metrics['loads'].append(load_data)
        
        # Generator information
        for idx, gen in self.net.gen.iterrows():
            if idx in self.net.res_gen.index:
                gen_data = {
                    'name': gen['name'],
                    'bus': self.net.bus.loc[gen['bus'], 'name'],
                    'p_mw': self.net.res_gen.loc[idx, 'p_mw'],
                    'q_mvar': self.net.res_gen.loc[idx, 'q_mvar']
                }
                metrics['generators'].append(gen_data)
        
        # Overall power flow summary
        total_load = sum([load['p_mw'] for load in metrics['loads']])
        total_generation = sum([gen['p_mw'] for gen in metrics['generators']])
        
        metrics['power_flow'] = {
            'total_load_mw': total_load,
            'total_generation_mw': total_generation,
            'grid_import_mw': self.net.res_ext_grid.loc[0, 'p_mw'],
            'system_losses_mw': abs(total_generation + self.net.res_ext_grid.loc[0, 'p_mw'] - total_load)
        }
        
        return metrics
    
    def run_simulation(self):
        """Main simulation loop"""
        print("🚀 GridGuard SCADA Simulation Started")
        print("=" * 50)
        
        while True:
            try:
                # Get system metrics
                metrics = self.get_system_metrics()
                
                if metrics:
                    # Print summary to console
                    print(f"\n⏰ Time: {metrics['timestamp']}")
                    print(f"🔌 Breaker State: {metrics['breaker_status']}")
                    print(f"📊 Total Load: {metrics['power_flow']['total_load_mw']:.2f} MW")
                    print(f"🏭 Grid Import: {metrics['power_flow']['grid_import_mw']:.2f} MW") 
                    print(f"⚡ System Frequency: {metrics['system_frequency']:.2f} Hz")
                    
                    # Show voltage levels
                    for bus in metrics['buses'][:3]:  # Show first 3 buses
                        print(f"   {bus['name']}: {bus['voltage_actual']:.1f} kV ({bus['voltage_pu']:.3f} pu)")
                    
                    critical_line = next((line for line in metrics['lines'] if line['name'] == "Critical Transmission Line"), None)
                    
                    if metrics['breaker_state'] and critical_line:
                        print(f"🔗 Critical Line: {critical_line['p_from_mw']:.2f} MW, {critical_line['loading_percent']:.1f}% loading")
                    
                    # --- ADDED: Log data for the anomaly detector ---
                    if critical_line:
                        timestamp = metrics['timestamp']
                        loading_percent = critical_line['loading_percent']
                        with open(self.log_file, "a") as f:
                            f.write(f"{timestamp},{loading_percent}\n")
                    # ---------------------------------------------------

                    # Save to shared file for web dashboard
                    # Ensure the directory exists before writing
                    web_data_path = '/shared_data/scada_data.json'
                    os.makedirs(os.path.dirname(web_data_path), exist_ok=True)
                    with open(web_data_path, 'w') as f:
                        json.dump(metrics, f, indent=2)
                
                self.simulation_time += 5
                time.sleep(5)  # Update every 5 seconds
                
            except KeyboardInterrupt:
                print("\n🛑 Simulation stopped by user")
                break
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    hmi = PowerSystemHMI()
    hmi.run_simulation()