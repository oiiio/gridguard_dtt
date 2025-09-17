(*
OpenPLC Automatic Breaker Cycling Program
Automatically cycles the breaker: CLOSED for 30s, OPEN for 10s
Perfect for testing anomaly detection systems
*)

PROGRAM breaker_auto_cycle
VAR
    circuit_breaker AT %QX0.0 : BOOL;
    cycle_counter AT %MD0 : DINT;
    cycle_limit AT %MD4 : DINT;
    closed_limit AT %MD8 : DINT;
END_VAR

(* Initialize constants on first run *)
IF cycle_limit = 0 THEN
    cycle_limit := 2000;
    closed_limit := 1500;
END_IF;

(* Increment counter *)
cycle_counter := cycle_counter + 1;

(* Reset counter when cycle completes *)
IF cycle_counter >= cycle_limit THEN
    cycle_counter := 0;
END_IF;

(* Breaker logic: CLOSED for first 30s, OPEN for last 10s *)
IF cycle_counter < closed_limit THEN
    circuit_breaker := TRUE;
ELSE
    circuit_breaker := FALSE;
END_IF;

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_auto_cycle;
    END_RESOURCE
END_CONFIGURATION
