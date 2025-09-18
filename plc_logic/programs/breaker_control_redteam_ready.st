(*
GridGuard SCADA Red Team Testing PLC Program

Attack Vectors:
1. Emergency Bypass: Set bypass_active (QX0.5) = TRUE
2. Maintenance Mode: Write -559038737 to maint_key (MD12)
3. Timer Manipulation: Modify timer_preset (MD8)
*)

PROGRAM breaker_control_redteam_ready
VAR
    (* Located variables - I/O mapping *)
    start_btn AT %IX0.0 : BOOL;
    stop_btn AT %IX0.1 : BOOL;
    health_ok AT %IX0.2 : BOOL;
    breaker_out AT %QX0.0 : BOOL;
    status_led AT %QX0.1 : BOOL;
    fault_led AT %QX0.2 : BOOL;
    maint_led AT %QX0.3 : BOOL;
    alert_led AT %QX0.4 : BOOL;
    bypass_active AT %QX0.5 : BOOL;
    debug_active AT %QX0.6 : BOOL;
    counter AT %MD0 : DINT;
    event_count AT %MD4 : DINT;
    timer_preset AT %MD8 : DINT;
    maint_key AT %MD12 : DINT;
    
    (* Additional located variables *)
    breaker_state AT %QX0.7 : BOOL;
    safety_timer AT %MD16 : DINT;
    maint_mode AT %QX1.0 : BOOL;
END_VAR

    (* The program logic must begin AFTER the END_VAR block. *)

    (* Initialize on first run *)
    IF counter = 0 THEN
        timer_preset := 100;
        event_count := 0;
        maint_mode := FALSE;
        safety_timer := 0;
        breaker_state := TRUE;  (* Start with breaker CLOSED for red team testing *)
    END_IF;

    (* Increment counter *)
    counter := counter + 1;

    (* ATTACK VECTOR 1: Emergency Bypass *)
    IF bypass_active THEN
        breaker_state := start_btn;
        event_count := event_count + 1;
    ELSE
        (* Normal Operation - maintain closed state unless explicitly stopped *)
        IF start_btn THEN  (* Removed health_ok requirement *)
            IF safety_timer = 0 THEN
                safety_timer := timer_preset;
            END_IF;
        END_IF;

        IF safety_timer > 0 THEN
            safety_timer := safety_timer - 1;
            IF safety_timer = 0 AND start_btn THEN
                breaker_state := TRUE;
            END_IF;
        END_IF;

        (* Only open breaker if explicitly stopped or health explicitly fails *)
        IF stop_btn THEN
            breaker_state := FALSE;
            safety_timer := 0;
        (* Remove health_ok check since it defaults to FALSE when not connected *)
        (* ELSIF NOT health_ok THEN
            breaker_state := FALSE;
            safety_timer := 0; *)
        END_IF;
    END_IF;

    (* ATTACK VECTOR 2: Maintenance Override *)
    IF maint_key = -559038737 THEN
        maint_mode := TRUE;
        breaker_state := start_btn;
        event_count := event_count + 1;
    END_IF;

    (* Outputs *)
    breaker_out := breaker_state;
    status_led := breaker_state;
    fault_led := FALSE;  (* No health monitoring for now *)
    maint_led := maint_mode;
    alert_led := (event_count > 10);

END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : breaker_control_redteam_ready;
    END_RESOURCE
END_CONFIGURATION
