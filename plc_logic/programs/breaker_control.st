PROGRAM breaker_control
VAR
    start_button AT %IX0.0 : BOOL;  (* Input - Start button *)
    circuit_breaker AT %QX0.0 : BOOL;  (* Output - Circuit breaker coil *)
END_VAR

(* Simple breaker control logic *)
(* When start button is pressed, energize circuit breaker *)
circuit_breaker := start_button;

END_PROGRAM
