"""
Simple test script to debug the SCADA system
"""
import pandapower as pp
import time

def test_grid_creation():
    print("Testing grid creation...")
    try:
        net = pp.create_empty_network()
        bus1 = pp.create_bus(net, vn_kv=20., name="Bus 1")
        bus2 = pp.create_bus(net, vn_kv=0.4, name="Bus 2")
        bus3 = pp.create_bus(net, vn_kv=0.4, name="Bus 3")
        
        pp.create_ext_grid(net, bus=bus1, vm_pu=1.02, name="Grid Connection")
        pp.create_transformer(net, hv_bus=bus1, lv_bus=bus2, std_type="0.4 MVA 20/0.4 kV", name="Transformer")
        pp.create_load(net, bus=bus3, p_mw=0.1, q_mvar=0.05, name="Load")
        
        line1 = pp.create_line(net, from_bus=bus2, to_bus=bus3, length_km=0.1, std_type="NAYY 4x50 SE", name="Line")
        sw = pp.create_switch(net, bus=bus2, element=line1, et="l", closed=True, name="Circuit Breaker")
        
        print(f"Grid created successfully:")
        print(f"- Buses: {len(net.bus)}")
        print(f"- Lines: {len(net.line)}")
        print(f"- Switches: {len(net.switch)}")
        
        return net
    except Exception as e:
        print(f"Error creating grid: {e}")
        return None

def test_power_flow(net):
    print("\nTesting power flow calculation...")
    try:
        pp.runpp(net)
        print("Power flow calculation successful!")
        print("Line results:")
        print(net.res_line)
        print("Bus results:")
        print(net.res_bus)
        return True
    except Exception as e:
        print(f"Error in power flow: {e}")
        return False

if __name__ == "__main__":
    print("SCADA System Debug Test")
    print("=" * 40)
    
    # Test grid creation
    net = test_grid_creation()
    if net is None:
        exit(1)
    
    # Test power flow
    if not test_power_flow(net):
        exit(1)
    
    print("\nAll tests passed! Grid simulation is working correctly.")
    
    # Test simulation loop
    print("\nTesting simulation loop...")
    for i in range(5):
        breaker_state = (i % 2 == 0)  # Alternate between True/False
        net.switch.loc[0, 'closed'] = breaker_state
        
        try:
            pp.runpp(net)
            power_flow = net.res_line.p_from_mw.iloc[0]
            voltage = net.res_bus.vm_pu.iloc[0]
            
            print(f"Cycle {i+1}: Breaker={'CLOSED' if breaker_state else 'OPEN'}, Power={power_flow:.3f} MW, Voltage={voltage:.3f} pu")
        except Exception as e:
            print(f"Error in cycle {i+1}: {e}")
        
        time.sleep(1)
    
    print("\nSimulation test complete!")
