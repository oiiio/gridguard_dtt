#!/usr/bin/env python3
"""
Blue Team PLC Security Monitor for GridGuard SCADA
==================================================

This script monitors the PLC for red team attack indicators by reading
security-related Modbus registers and detecting suspicious patterns.

Integrates with the existing anomaly detector to provide comprehensive
cybersecurity monitoring of the SCADA system.
"""

import time
import sys
import os
from datetime import datetime
try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    from pymodbus.client.sync import ModbusTcpClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/security_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PLCSecurityMonitor:
    def __init__(self, host='localhost', port=502):
        self.client = ModbusTcpClient(host=host, port=port)
        self.baseline_values = {}
        self.alert_thresholds = {
            'security_event_max': 10,
            'safety_timer_min': 50,
            'safety_timer_max': 500,
            'expected_signature': 0x12345678,
            'max_command_frequency': 5  # commands per minute
        }
        self.command_history = []
        self.last_values = {}
        
    def connect(self):
        """Connect to the PLC"""
        if self.client.connect():
            logger.info("✅ Connected to PLC successfully")
            return True
        else:
            logger.error("❌ Failed to connect to PLC")
            return False
    
    def read_security_registers(self):
        """Read all security-related registers from PLC"""
        try:
            # Read holding registers (memory data)
            holding_registers = self.client.read_holding_registers(address=0, count=25)
            if holding_registers.isError():
                logger.error(f"❌ Error reading holding registers: {holding_registers}")
                return None
            
            # Read coils (digital outputs)
            coils = self.client.read_coils(address=0, count=8)
            if coils.isError():
                logger.error(f"❌ Error reading coils: {coils}")
                return None
            
            # Parse register data
            registers = holding_registers.registers
            coil_bits = coils.bits[:8]  # Only first 8 coils
            
            return {
                'cycle_counter': registers[0] if len(registers) > 0 else 0,
                'last_command_time': registers[1] if len(registers) > 1 else 0,
                'security_event_count': registers[2] if len(registers) > 2 else 0,
                'maintenance_override': registers[3] if len(registers) > 3 else 0,
                'safety_timer_preset': registers[4] if len(registers) > 4 else 0,
                'health_signature': registers[5] if len(registers) > 5 else 0,
                'covert_channel_data': registers[6] if len(registers) > 6 else 0,
                'circuit_breaker': coil_bits[0] if len(coil_bits) > 0 else False,
                'system_status_led': coil_bits[1] if len(coil_bits) > 1 else False,
                'fault_led': coil_bits[2] if len(coil_bits) > 2 else False,
                'maintenance_led': coil_bits[3] if len(coil_bits) > 3 else False,
                'security_alert_led': coil_bits[4] if len(coil_bits) > 4 else False,
                'emergency_bypass': coil_bits[5] if len(coil_bits) > 5 else False,
                'debug_mode': coil_bits[6] if len(coil_bits) > 6 else False,
            }
            
        except Exception as e:
            logger.error(f"❌ Exception reading registers: {e}")
            return None
    
    def analyze_security_events(self, current_data):
        """Analyze current data for security threats"""
        alerts = []
        
        if not current_data:
            return alerts
        
        # Check 1: Security Event Counter
        sec_events = current_data.get('security_event_count', 0)
        if sec_events > self.alert_thresholds['security_event_max']:
            alerts.append({
                'type': 'HIGH_SECURITY_EVENTS', 
                'severity': 'HIGH',
                'message': f'Security event counter at {sec_events} (threshold: {self.alert_thresholds["security_event_max"]})',
                'value': sec_events
            })
        
        # Check 2: Maintenance Override Detection
        maint_override = current_data.get('maintenance_override', 0)
        if maint_override == 0xDEADBEEF:
            alerts.append({
                'type': 'MAINTENANCE_BYPASS_ACTIVE',
                'severity': 'CRITICAL', 
                'message': 'Maintenance override bypass detected (0xDEADBEEF)',
                'value': hex(maint_override)
            })
        elif maint_override != 0:
            alerts.append({
                'type': 'UNAUTHORIZED_MAINTENANCE',
                'severity': 'HIGH',
                'message': f'Unauthorized maintenance override value: {hex(maint_override)}',
                'value': hex(maint_override)
            })
        
        # Check 3: Safety Timer Manipulation
        safety_timer = current_data.get('safety_timer_preset', 100)
        if safety_timer < self.alert_thresholds['safety_timer_min'] or safety_timer > self.alert_thresholds['safety_timer_max']:
            alerts.append({
                'type': 'SAFETY_TIMER_MANIPULATION',
                'severity': 'HIGH',
                'message': f'Safety timer preset outside normal range: {safety_timer}ms',
                'value': safety_timer
            })
        
        # Check 4: System Health Signature
        signature = current_data.get('health_signature', 0)
        if signature != self.alert_thresholds['expected_signature']:
            alerts.append({
                'type': 'SYSTEM_COMPROMISE',
                'severity': 'CRITICAL',
                'message': f'System health signature corrupted: {hex(signature)} (expected: {hex(self.alert_thresholds["expected_signature"])})',
                'value': hex(signature)
            })
        
        # Check 5: Emergency Bypass
        if current_data.get('emergency_bypass', False):
            alerts.append({
                'type': 'EMERGENCY_BYPASS_ACTIVE',
                'severity': 'HIGH',
                'message': 'Emergency bypass is currently active',
                'value': True
            })
        
        # Check 6: Debug Mode Activity
        if current_data.get('debug_mode', False):
            covert_data = current_data.get('covert_channel_data', 0)
            alerts.append({
                'type': 'DEBUG_MODE_ACTIVE',
                'severity': 'MEDIUM',
                'message': f'Debug mode active, covert channel data: {covert_data}',
                'value': covert_data
            })
        
        # Check 7: Command Timing Analysis
        last_cmd_time = current_data.get('last_command_time', 0)
        current_time = int(time.time())
        
        if last_cmd_time in self.last_values:
            if last_cmd_time != self.last_values.get('last_command_time', 0):
                self.command_history.append(current_time)
                # Keep only last 10 minutes of history
                self.command_history = [t for t in self.command_history if current_time - t < 600]
                
                # Check command frequency  
                recent_commands = len([t for t in self.command_history if current_time - t < 60])
                if recent_commands > self.alert_thresholds['max_command_frequency']:
                    alerts.append({
                        'type': 'HIGH_COMMAND_FREQUENCY',
                        'severity': 'MEDIUM',
                        'message': f'High command frequency detected: {recent_commands} commands in last minute',
                        'value': recent_commands
                    })
        
        return alerts
    
    def log_security_alert(self, alert):
        """Log security alert with appropriate formatting"""
        severity_emoji = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️', 
            'MEDIUM': '🔍',
            'LOW': 'ℹ️'
        }
        
        emoji = severity_emoji.get(alert['severity'], '❓')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_message = f"{emoji} [{alert['severity']}] {alert['type']}: {alert['message']}"
        logger.warning(log_message)
        
        # Write to security log file
        with open('logs/security_alerts.log', 'a') as f:
            f.write(f"{timestamp},{alert['severity']},{alert['type']},{alert['message']},{alert['value']}\n")
    
    def print_status_summary(self, data):
        """Print current system status"""
        if not data:
            return
        
        status_line = f"🔐 PLC Security Status | "
        status_line += f"Events: {data.get('security_event_count', 0):02d} | "
        status_line += f"Breaker: {'OPEN' if data.get('circuit_breaker', False) else 'CLOSED'} | "
        
        # Status indicators
        indicators = []
        if data.get('maintenance_led', False):
            indicators.append("MAINT")
        if data.get('fault_led', False):
            indicators.append("FAULT")  
        if data.get('security_alert_led', False):
            indicators.append("SEC-ALERT")
        if data.get('emergency_bypass', False):
            indicators.append("BYPASS")
        if data.get('debug_mode', False):
            indicators.append("DEBUG")
            
        status_line += f"Flags: {','.join(indicators) if indicators else 'NORMAL'}"
        logger.info(status_line)
    
    def run_monitoring(self, interval=5):
        """Main monitoring loop"""
        logger.info("🛡️  Starting PLC Security Monitoring")
        logger.info("="*60)
        logger.info("Monitoring for red team attack indicators...")
        logger.info(f"Update interval: {interval} seconds")
        
        if not self.connect():
            return
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        try:
            iteration = 0
            while True:
                iteration += 1
                
                # Read current PLC state
                current_data = self.read_security_registers()
                
                if current_data:
                    # Analyze for security threats
                    alerts = self.analyze_security_events(current_data)
                    
                    # Process any alerts
                    if alerts:
                        logger.warning(f"\n🚨 SECURITY ALERTS DETECTED ({len(alerts)} total)")
                        for alert in alerts:
                            self.log_security_alert(alert)
                    
                    # Print status summary every 5 iterations (25 seconds)  
                    if iteration % 5 == 0:
                        self.print_status_summary(current_data)
                    
                    # Store values for next comparison
                    self.last_values = current_data.copy()
                
                else:
                    logger.error("❌ Failed to read PLC data")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("\n👋 Security monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")
        finally:
            self.client.close()

def main():
    """Main entry point"""
    print("🛡️  GridGuard PLC Security Monitor")
    print("="*50)
    print("Monitoring PLC for red team attack indicators...")
    print("Press Ctrl+C to stop\n")
    
    monitor = PLCSecurityMonitor()
    monitor.run_monitoring()

if __name__ == "__main__":
    main()