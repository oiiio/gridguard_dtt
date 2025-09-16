(*
OpenPLC Simple Toggle Breaker Control
Uses QX0.0 as both output and toggle input
- Write to QX0.0 to toggle the breaker state
*)

PROGRAM breaker_toggle
VAR
    circuit_breaker AT %QX0.0 : BOOL;      (* Circuit breaker - both input and output *)
    
    (* Internal variables for edge detection *)
    prev_state : BOOL := FALSE;
    internal_breaker : BOOL := FALSE;
    toggle_command : BOOL;
END_VAR

(* Read the current command from Modbus *)
toggle_command := circuit_breaker;

(* Detect rising edge (0->1 transition) for toggle *)
IF toggle_command AND NOT prev_state THEN
    internal_breaker := NOT internal_breaker;
END_IF;

(* Update previous state for next scan *)
prev_state := toggle_command;

(* Output the internal breaker state *)
circuit_breaker := internal_breaker;

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#50ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_toggle;
    END_RESOURCE
END_CONFIGURATION
