#!/usr/bin/env python3
"""
Standalone test version of the physical process simulator.
This version runs without Docker and can be used for testing and debugging.
"""

import pandapower as pp
import time
import numpy as np
import json
from datetime import datetime
import os

class PowerSystemHMI_Standalone:
    def __init__(self, log_to_file=True):
        self.log_to_file = log_to_file
        if self.log_to_file:
            # Use local directory for testing
            self.log_file = "./logs/power_flow.log"
            log_dir = os.path.dirname(self.log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
        
        self.setup_power_system()
        self.simulation_time = 0
        print("✅ Standalone Power System HMI initialized successfully!")
        
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
        
        # Critical transmission line with explicit parameters to fix loading calculation
        self.critical_line = pp.create_line_from_parameters(
            self.net, 
            from_bus=self.bus_mv1, 
            to_bus=self.bus_mv2,
            length_km=5.2,
            r_ohm_per_km=0.161,   # Resistance per km
            x_ohm_per_km=0.117,   # Reactance per km  
            c_nf_per_km=273,      # Capacitance per km
            max_i_ka=0.29,        # Maximum current in kA (critical for loading calculation)
            name="Critical Transmission Line"
        )
        
        # PLC-controlled circuit breaker
        self.breaker_switch = pp.create_switch(self.net, bus=self.bus_mv1, element=self.critical_line, 
                                             et="l", closed=True, name="PLC Circuit Breaker")
    
    def get_simulated_breaker_state(self):
        """Simulate breaker state for standalone testing"""
        # Breaker cycles: closed for 30s, open for 10s
        cycle_time = self.simulation_time % 40
        return cycle_time < 30
    
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
            # Disable numba to avoid warnings
            pp.runpp(self.net, algorithm="nr", max_iteration=20, numba=False)
            return True
        except Exception as e:
            print(f"❌ Power flow convergence error: {e}")
            return False
    
    def get_system_metrics(self):
        """Extract key system metrics for SCADA display"""
        breaker_state = self.get_simulated_breaker_state()
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
            vm_pu = self.net.res_bus.loc[idx, 'vm_pu']
            va_degree = self.net.res_bus.loc[idx, 'va_degree']
            
            # Handle NaN values for isolated buses
            if np.isnan(vm_pu):
                vm_pu = 0.0
            if np.isnan(va_degree):
                va_degree = 0.0
                
            bus_data = {
                'name': bus['name'],
                'voltage_kv': bus['vn_kv'],
                'voltage_pu': vm_pu,
                'angle_deg': va_degree,
                'voltage_actual': vm_pu * bus['vn_kv']
            }
            metrics['buses'].append(bus_data)
        
        # Line flows
        for idx, line in self.net.line.iterrows():
            if idx in self.net.res_line.index:
                loading_percent = self.net.res_line.loc[idx, 'loading_percent']
                
                # Handle NaN loading percentage (occurs when line is disconnected)
                if np.isnan(loading_percent):
                    # When breaker is open, set loading to 0
                    loading_percent = 0.0
                    current_ka = 0.0
                    p_from_mw = 0.0
                    q_from_mvar = 0.0
                else:
                    current_ka = self.net.res_line.loc[idx, 'i_from_ka']
                    p_from_mw = self.net.res_line.loc[idx, 'p_from_mw']
                    q_from_mvar = self.net.res_line.loc[idx, 'q_from_mvar']
                
                line_data = {
                    'name': line['name'],
                    'from_bus': self.net.bus.loc[line['from_bus'], 'name'],
                    'to_bus': self.net.bus.loc[line['to_bus'], 'name'],
                    'p_from_mw': p_from_mw,
                    'q_from_mvar': q_from_mvar,
                    'loading_percent': loading_percent,
                    'current_ka': current_ka,
                    'max_current_ka': self.net.line.loc[idx, 'max_i_ka']
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
    
    def run_simulation(self, duration=60, update_interval=5):
        """Main simulation loop"""
        print("🚀 GridGuard SCADA Simulation Started (Standalone)")
        print("=" * 60)
        end_time = self.simulation_time + duration
        
        while self.simulation_time < end_time:
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
                        if bus['voltage_pu'] == 0.0:
                            print(f"   {bus['name']}: ISOLATED (breaker open)")
                        else:
                            print(f"   {bus['name']}: {bus['voltage_actual']:.1f} kV ({bus['voltage_pu']:.3f} pu)")
                    
                    critical_line = next((line for line in metrics['lines'] if line['name'] == "Critical Transmission Line"), None)
                    
                    if metrics['breaker_state'] and critical_line:
                        print(f"🔗 Critical Line: {critical_line['p_from_mw']:.2f} MW, {critical_line['loading_percent']:.1f}% loading")
                    else:
                        print(f"🔗 Critical Line: DISCONNECTED (breaker open)")
                    
                    # Log data for anomaly detection
                    if self.log_to_file and critical_line:
                        if not np.isnan(critical_line['loading_percent']):
                            timestamp = metrics['timestamp']
                            loading_percent = critical_line['loading_percent']
                            with open(self.log_file, "a") as f:
                                f.write(f"{timestamp},{loading_percent}\n")
                        else:
                            # Log zero when breaker is open (no loading)
                            timestamp = metrics['timestamp']
                            with open(self.log_file, "a") as f:
                                f.write(f"{timestamp},0.0\n")
                else:
                    print("❌ Failed to get system metrics")
                
                self.simulation_time += update_interval
                time.sleep(update_interval)
                
            except KeyboardInterrupt:
                print("\n👋 Simulation stopped by user")
                break
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                break
        
        print("\n🏁 Simulation completed")
        if self.log_to_file and os.path.exists(self.log_file):
            print(f"📁 Log file saved to: {self.log_file}")

def main():
    """Run the standalone simulation"""
    try:
        # Create and run the simulation
        hmi = PowerSystemHMI_Standalone(log_to_file=True)
        
        print("\nStarting 60-second simulation with breaker cycling...")
        print("Press Ctrl+C to stop early\n")
        
        hmi.run_simulation(duration=60, update_interval=5)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
