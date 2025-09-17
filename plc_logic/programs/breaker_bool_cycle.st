(*
OpenPLC Automatic Breaker Cycling Program
Uses only BOOL variables to avoid INT declaration issues
Cycles breaker automatically without external inputs
*)

PROGRAM breaker_auto_cycle
VAR
    circuit_breaker AT %QX0.0 : BOOL;
    timer1 : BOOL;
    timer2 : BOOL;
    timer3 : BOOL;
    timer4 : BOOL;
    timer5 : BOOL;
END_VAR

(* Simple state machine using boolean cascade *)
(* This creates a slow cycling pattern *)
timer1 := NOT timer1;

IF timer1 THEN
    timer2 := NOT timer2;
END_IF;

IF timer2 THEN
    timer3 := NOT timer3;
END_IF;

IF timer3 THEN
    timer4 := NOT timer4;
END_IF;

IF timer4 THEN
    timer5 := NOT timer5;
END_IF;

(* Breaker follows timer5 with some logic for cycling *)
circuit_breaker := timer5 OR timer4;

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_auto_cycle;
    END_RESOURCE
END_CONFIGURATION
