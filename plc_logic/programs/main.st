CONFIGURATION config
    RESOURCE resource1 ON PLC
        TASK main_task(INTERVAL := T#100ms, PRIORITY := 0);
        PROGRAM instance0 WITH main_task : breaker_control;
    END_RESOURCE
END_CONFIGURATION
