(*
OpenPLC Automatic Breaker Cycling Program
Uses only simple boolean logic like breaker_control_complete.st
Cycles breaker: CLOSED most of the time, OPEN occasionally
*)

PROGRAM breaker_auto_cycle
VAR
    circuit_breaker AT %QX0.0 : BOOL;
    always_on AT %IX0.0 : BOOL;
END_VAR

(* Simple cycling logic: breaker follows input state *)
(* This will be controlled by SCADA simulation instead *)
circuit_breaker := always_on;

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_auto_cycle;
    END_RESOURCE
END_CONFIGURATION
