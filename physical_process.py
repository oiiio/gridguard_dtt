import pandapower as pp
from pymodbus.client import ModbusTcpClient
import time

# --- 1. Create the Power Grid Model ---
net = pp.create_empty_network()

# Create buses
bus1 = pp.create_bus(net, vn_kv=20., name="Bus 1")
bus2 = pp.create_bus(net, vn_kv=0.4, name="Bus 2")
bus3 = pp.create_bus(net, vn_kv=0.4, name="Bus 3")

# Create an external grid connection
pp.create_ext_grid(net, bus=bus1, vm_pu=1.02, name="Grid Connection")

# Create a transformer
pp.create_transformer(net, hv_bus=bus1, lv_bus=bus2, std_type="0.4 MVA 20/0.4 kV", name="Transformer")

# Create a load
pp.create_load(net, bus=bus3, p_mw=0.1, q_mvar=0.05, name="Load")

# Create a line with a switch (our circuit breaker)
line1 = pp.create_line(net, from_bus=bus2, to_bus=bus3, length_km=0.1, std_type="NAYY 4x50 SE", name="Line")
sw = pp.create_switch(net, bus=bus2, element=line1, et="l", closed=True, name="Circuit Breaker")

# --- 2. Connect to the OpenPLC ---
# The PLC is running in another Docker container, but on the same network.
# We can refer to it by its service name 'openplc'.
client = ModbusTcpClient('openplc', port=502)
client.connect()

print("--- Simulation Started ---")
print("Initial Grid State:")
pp.runpp(net)
print(net.res_line)


# --- 3. Simulation Loop ---
while True:
    # Read the state of the 'circuit_breaker' coil (%QX0.0) from the PLC.
    # Address 0 is for the first digital output.
    result = client.read_coils(0, 1)
    breaker_state = result.bits[0]

    # Update the simulation based on the PLC's output
    net.switch.loc[0, 'closed'] = breaker_state

    # Run the power flow calculation
    pp.runpp(net)

    print("\n--- Running Power Flow ---")
    print(f"PLC 'circuit_breaker' state (%QX0.0): {breaker_state}")
    print("Switch Table:")
    print(net.switch)
    print("Power Flow Results:")
    print(net.res_line)

    time.sleep(5) # Wait for 5 seconds before the next loop