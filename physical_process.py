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

# Wait for OpenPLC to be ready and establish connection
print("--- Waiting for OpenPLC Modbus TCP connection ---")
print("IMPORTANT: OpenPLC needs a compiled PLC program running for Modbus to work!")
print("If connection keeps failing:")
print("1. Open http://localhost:8080 in your browser")
print("2. Login with openplc/openplc") 
print("3. Upload plc_logic/programs/breaker_control_complete.st")
print("4. Compile and start the program")
print("-" * 60)

max_retries = 30
retry_count = 0
connected = False

while retry_count < max_retries and not connected:
    try:
        print(f"Connection attempt {retry_count + 1}/{max_retries}...")
        connected = client.connect()
        if connected:
            print("Connected to OpenPLC Modbus server successfully!")
            break
        else:
            print(f"Connection attempt {retry_count + 1} failed, retrying in 2 seconds...")
    except Exception as e:
        print(f"Connection attempt {retry_count + 1} failed with error: {e}, retrying in 2 seconds...")
    
    time.sleep(2)
    retry_count += 1

if not connected:
    print("=" * 60)
    print("ERROR: Failed to connect to OpenPLC Modbus server!")
    print("This usually means:")
    print("1. OpenPLC web server is running but no PLC program is loaded")
    print("2. The PLC program failed to compile")
    print("3. The PLC runtime is not started")
    print("")
    print("TO FIX:")
    print("1. Open http://localhost:8080")
    print("2. Go to 'Programs' -> Upload 'breaker_control_complete.st'")
    print("3. Compile the program (should show 'Compilation finished successfully!')")
    print("4. Go to 'Runtime' -> Start PLC")
    print("5. Restart this container: docker compose restart scada_hmi")
    print("=" * 60)
    exit(1)

print("--- Simulation Started ---")
print("Initial Grid State:")
pp.runpp(net)
print(net.res_line)


# --- 3. Simulation Loop ---
while True:
    try:
        # Read the state of the 'circuit_breaker' coil (%QX0.0) from the PLC.
        # Address 0 is for the first digital output.
        # In pymodbus 3.x, read_coils takes address and count as keyword arguments
        result = client.read_coils(address=0, count=1)
        
        if result.isError():
            print(f"Error reading coils: {result}")
            breaker_state = True  # Default to closed state
        else:
            breaker_state = result.bits[0]
    except Exception as e:
        print(f"Error communicating with PLC: {e}")
        breaker_state = True  # Default to closed state

    # Update the simulation based on the PLC's output
    net.switch.loc[0, 'closed'] = breaker_state

    # Run the power flow calculation
    try:
        pp.runpp(net)
        print("\n--- Running Power Flow ---")
        print(f"PLC 'circuit_breaker' state (%QX0.0): {breaker_state}")
        print("Switch Table:")
        print(net.switch)
        print("Power Flow Results:")
        print(net.res_line)
    except Exception as e:
        print(f"Error running power flow calculation: {e}")

    time.sleep(5) # Wait for 5 seconds before the next loop