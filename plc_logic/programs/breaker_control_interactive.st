(*
OpenPLC Interactive Breaker Control Program
This program allows remote control of the circuit breaker via Modbus
- QX0.0: Circuit breaker output (controlled by logic)
- QX0.1: Manual control register (writable via Modbus)
- QX0.2: System status indicator
*)

PROGRAM breaker_control_interactive
VAR
    (* Inputs *)
    start_button AT %IX0.0 : BOOL;         (* Physical start button input *)
    
    (* Outputs *)
    circuit_breaker AT %QX0.0 : BOOL;      (* Circuit breaker coil *)
    manual_control AT %QX0.1 : BOOL;       (* Manual control flag (writable) *)
    system_active AT %QX0.2 : BOOL;        (* System status indicator *)
    
    (* Internal variables *)
    prev_manual_control : BOOL;            (* Previous state for edge detection *)
    breaker_state : BOOL;                  (* Internal breaker state *)
    manual_mode : BOOL;                    (* Manual mode flag *)
    toggle_trigger : BOOL;                 (* Toggle edge detection *)
END_VAR

(* Initialize on first scan *)
IF NOT system_active THEN
    system_active := TRUE;
    breaker_state := FALSE;
    manual_mode := FALSE;
    prev_manual_control := manual_control;
END_IF;

(* Detect rising edge on manual control for toggle operation *)
toggle_trigger := manual_control AND NOT prev_manual_control;
prev_manual_control := manual_control;

(* Toggle breaker state on manual control edge *)
IF toggle_trigger THEN
    breaker_state := NOT breaker_state;
    manual_mode := TRUE;
END_IF;

(* Auto mode: breaker follows start button *)
IF NOT manual_mode AND start_button THEN
    breaker_state := TRUE;
END_IF;

(* Output the breaker state *)
circuit_breaker := breaker_state;

(* Reset manual mode if start button is pressed *)
IF start_button THEN
    manual_mode := FALSE;
END_IF;

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_control_interactive;
    END_RESOURCE
END_CONFIGURATION
