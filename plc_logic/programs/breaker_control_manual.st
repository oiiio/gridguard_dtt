(*
OpenPLC Breaker Control with Manual Override
- IX0.0: Start button (auto mode)
- IX0.1: Manual mode enable  
- QX0.0: Circuit breaker output
- QX0.1: Status indicator

Manual control via Modbus:
- Write to address 10001 (mapped to IX0.1) to enable manual mode
- When in manual mode, QX0.0 can be controlled via Modbus
*)

PROGRAM breaker_control_manual
VAR
    (* Inputs *)
    start_button AT %IX0.0 : BOOL;         (* Auto mode start button *)
    manual_enable AT %IX0.1 : BOOL;        (* Manual mode enable *)
    
    (* Outputs *) 
    circuit_breaker AT %QX0.0 : BOOL;      (* Circuit breaker control *)
    status_led AT %QX0.1 : BOOL;           (* Status indicator *)
    
    (* Internal variables *)
    manual_mode : BOOL := FALSE;
    breaker_command : BOOL := FALSE;
    prev_manual_enable : BOOL := FALSE;
    manual_toggle : BOOL := FALSE;
END_VAR

(* Detect rising edge on manual enable for mode switching *)
manual_toggle := manual_enable AND NOT prev_manual_enable;
prev_manual_enable := manual_enable;

(* Switch to manual mode on rising edge *)
IF manual_toggle THEN
    manual_mode := NOT manual_mode;
END_IF;

(* Control logic *)
IF manual_mode THEN
    (* Manual mode: preserve current output state unless overridden *)
    (* The output can be controlled directly via Modbus writes to QX0.0 *)
    (* We don't override it here, letting manual control work *)
    status_led := TRUE;  (* Indicate manual mode *)
ELSE
    (* Auto mode: output follows start button *)
    circuit_breaker := start_button;
    status_led := start_button;  (* Status follows breaker in auto mode *)
END_IF;

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_control_manual;
    END_RESOURCE
END_CONFIGURATION
