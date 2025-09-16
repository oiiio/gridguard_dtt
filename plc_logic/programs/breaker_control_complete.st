(*
OpenPLC Breaker Control Program
This program implements simple breaker control logic equivalent to:
   | start_button |        ( circuit_breaker )
---|----] [-------|--------(---------------)---
   %IX0.0          %QX0.0
*)

PROGRAM breaker_control
VAR
    start_button AT %IX0.0 : BOOL;  (* Digital input - Start button *)
    circuit_breaker AT %QX0.0 : BOOL;  (* Digital output - Circuit breaker coil *)
END_VAR

(* Main control logic *)
(* Direct assignment: when start button is active, circuit breaker is energized *)
circuit_breaker := start_button;

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_control;
    END_RESOURCE
END_CONFIGURATION
