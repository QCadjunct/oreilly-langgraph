# Restore IDS configuration
echo "🚨 Restoring IDS configuration..."
for ids_backup in ids_config_*.tar.gz; do
    if [ -f "$ids_backup" ]; then
        tar -xzf "$ids_backup"
        sudo cp -r ids_backup/twintower-ids /etc/ 2>/dev/null || true
        break
    fi
done

# Restore performance optimizations
echo "⚡ Restoring performance optimizations..."
for perf_backup in performance_*.tar.gz; do
    if [ -f "$perf_backup" ]; then
        tar -xzf "$perf_backup"
        sudo cp -r performance_backup/twintower-performance /etc/ 2>/dev/null || true
        sudo cp performance_backup/99-twintower-*.conf /etc/sysctl.d/ 2>/dev/null || true
        sudo sysctl -p
        break
    fi
done

# Restore management scripts
echo "📋 Restoring management scripts..."
for scripts_backup in management_scripts_*.tar.gz; do
    if [ -f "$scripts_backup" ]; then
        tar -xzf "$scripts_backup"
        cp scripts_backup/*.sh ~/
        chmod +x ~/*.sh
        break
    fi
done

# Restart services
echo "🔄 Restarting services..."
sudo systemctl daemon-reload
sudo systemctl restart ufw
sudo systemctl restart twintower-ids 2>/dev/null || true
sudo systemctl restart twintower-traffic 2>/dev/null || true
sudo systemctl restart twintower-performance 2>/dev/null || true

# Cleanup
rm -rf "$RESTORE_DIR"

echo "✅ System restoration completed!"
echo "📋 Please run verification script to ensure all components are working"
RESTORE_EOF

    chmod +x ~/restore_firewall_system.sh
    
    # Execute restoration
    ~/restore_firewall_system.sh "$RESTORE_FILE"
    
    log_message "✅ System restoration completed"
}

# Function to verify backup integrity
verify_backup_integrity() {
    log_message "🔍 Verifying backup integrity..."
    
    local verification_failed=0
    
    # Check backup directories
    for dir in configs logs scripts data full; do
        if [ ! -d "$BACKUP_DIR/$dir" ]; then
            log_message "❌ Missing backup directory: $dir"
            verification_failed=1
        fi
    done
    
    # Check recent backups
    local recent_backups=$(find "$BACKUP_DIR" -name "*.tar.gz" -mtime -1 | wc -l)
    if [ $recent_backups -eq 0 ]; then
        log_message "⚠️  No recent backups found"
    else
        log_message "✅ Found $recent_backups recent backup files"
    fi
    
    # Test backup file integrity
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime -7 | while read backup_file; do
        if tar -tzf "$backup_file" > /dev/null 2>&1; then
            log_message "✅ Backup file integrity OK: $(basename "$backup_file")"
        else
            log_message "❌ Backup file corrupted: $(basename "$backup_file")"
            verification_failed=1
        fi
    done
    
    if [ $verification_failed -eq 0 ]; then
        log_message "✅ Backup integrity verification passed"
    else
        log_message "❌ Backup integrity verification failed"
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    log_message "🧹 Cleaning up old backups..."
    
    # Keep last 30 days of backups
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null || true
    
    # Keep last 10 full backups
    ls -t "$BACKUP_DIR/full/"*.tar.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    
    # Keep last 20 config backups
    ls -t "$BACKUP_DIR/configs/"*.tar.gz 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null || true
    
    # Keep last 15 log backups
    ls -t "$BACKUP_DIR/logs/"*.tar.gz 2>/dev/null | tail -n +16 | xargs rm -f 2>/dev/null || true
    
    log_message "✅ Old backups cleaned up"
}

# Function to create automated backup service
create_backup_service() {
    log_message "⚙️ Creating automated backup service..."
    
    # Create backup service
    cat << BACKUP_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-backup.service
[Unit]
Description=TwinTower Firewall & Access Control Backup Service
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/home/$(whoami)/firewall_backup_system.sh backup full
StandardOutput=journal
StandardError=journal
BACKUP_SERVICE_EOF

    # Create backup timer
    cat << BACKUP_TIMER_EOF | sudo tee /etc/systemd/system/twintower-backup.timer
[Unit]
Description=Run TwinTower Backup Daily
Requires=twintower-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
BACKUP_TIMER_EOF

    # Enable and start timer
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-backup.timer
    sudo systemctl start twintower-backup.timer
    
    log_message "✅ Automated backup service created"
}

# Function to generate backup report
generate_backup_report() {
    log_message "📋 Generating backup report..."
    
    local report_file="/tmp/backup_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << REPORT_EOF
TwinTower Firewall & Access Control Backup Report
================================================
Generated: $(date)
Tower: $TOWER_NAME

Backup Directory: $BACKUP_DIR
Total Backup Size: $(du -sh "$BACKUP_DIR" | cut -f1)

Backup Summary:
--------------
Configuration Backups: $(ls "$BACKUP_DIR/configs/"*.tar.gz 2>/dev/null | wc -l)
Log Backups: $(ls "$BACKUP_DIR/logs/"*.tar.gz 2>/dev/null | wc -l)
Script Backups: $(ls "$BACKUP_DIR/scripts/"*.tar.gz 2>/dev/null | wc -l)
Data Backups: $(ls "$BACKUP_DIR/data/"*.tar.gz 2>/dev/null | wc -l)
Full Backups: $(ls "$BACKUP_DIR/full/"*.tar.gz 2>/dev/null | wc -l)

Recent Backups (Last 7 Days):
-----------------------------
$(find "$BACKUP_DIR" -name "*.tar.gz" -mtime -7 -exec ls -lh {} \; | awk '{print $9, $5, $6, $7, $8}')

Backup Service Status:
---------------------
$(sudo systemctl is-active twintower-backup.timer 2>/dev/null && echo "Automated backup: ACTIVE" || echo "Automated backup: INACTIVE")

Disk Usage:
----------
$(df -h "$BACKUP_DIR" | tail -1)

Backup Integrity:
----------------
$(find "$BACKUP_DIR" -name "*.tar.gz" -mtime -7 | wc -l) recent backup files verified

Recommendations:
---------------
$([ $(du -s "$BACKUP_DIR" | cut -f1) -gt 1048576 ] && echo "Consider archiving old backups - directory size > 1GB" || echo "Backup directory size is optimal")
$([ $(find "$BACKUP_DIR" -name "*.tar.gz" -mtime -1 | wc -l) -eq 0 ] && echo "No recent backups - check backup schedule" || echo "Recent backups are current")

REPORT_EOF

    log_message "📋 Backup report generated: $report_file"
    echo "$report_file"
}

# Main execution
main() {
    echo -e "${BLUE}💾 TwinTower Firewall & Access Control Backup System${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME, Action: $ACTION${NC}"
    echo -e "${BLUE}====================================================${NC}"
    
    create_backup_directories
    
    case "$ACTION" in
        "backup")
            case "$BACKUP_TYPE" in
                "configs")
                    backup_ufw_config
                    backup_network_zones
                    backup_zero_trust
                    backup_ids_config
                    backup_performance_config
                    ;;
                "logs")
                    backup_logs
                    ;;
                "scripts")
                    backup_scripts
                    ;;
                "data")
                    backup_data
                    ;;
                "full")
                    backup_ufw_config
                    backup_network_zones
                    backup_zero_trust
                    backup_ids_config
                    backup_performance_config
                    backup_logs
                    backup_scripts
                    backup_data
                    create_full_backup
                    cleanup_old_backups
                    ;;
                *)
                    echo "Invalid backup type: $BACKUP_TYPE"
                    echo "Usage: $0 backup <configs|logs|scripts|data|full>"
                    exit 1
                    ;;
            esac
            
            echo -e "${GREEN}✅ Backup completed successfully!${NC}"
            ;;
        "restore")
            restore_from_backup
            ;;
        "verify")
            verify_backup_integrity
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "service")
            create_backup_service
            ;;
        "report")
            generate_backup_report
            ;;
        "list")
            echo -e "${YELLOW}📋 Available Backups${NC}"
            echo "===================="
            
            for category in configs logs scripts data full; do
                echo -e "${BLUE}$category Backups:${NC}"
                ls -lah "$BACKUP_DIR/$category/"*.tar.gz 2>/dev/null | tail -5 || echo "  No backups found"
                echo
            done
            ;;
        *)
            echo "Usage: $0 <backup|restore|verify|cleanup|service|report|list> [backup_type] [restore_file]"
            echo
            echo "Examples:"
            echo "  $0 backup full                    # Create full backup"
            echo "  $0 backup configs                 # Backup only configurations"
            echo "  $0 restore /path/to/backup.tar.gz # Restore from backup"
            echo "  $0 verify                         # Verify backup integrity"
            echo "  $0 cleanup                        # Clean up old backups"
            echo "  $0 service                        # Setup automated backups"
            echo "  $0 report                         # Generate backup report"
            echo "  $0 list                           # List available backups"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/firewall_backup_system.sh
```

### **Step 2: Execute Backup System Setup**

```bash
# Create comprehensive backup
./firewall_backup_system.sh backup full

# Setup automated backup service
./firewall_backup_system.sh service

# Generate backup report
./firewall_backup_system.sh report

# List available backups
./firewall_backup_system.sh list

# Verify backup integrity
./firewall_backup_system.sh verify
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🚀 **Next Steps**

### **Section 5C Completion Checklist**

Verify the following components are properly configured:

- ✅ **Advanced UFW firewall** with intelligent rules and optimization
- ✅ **Network segmentation** with security zones (DMZ, Internal, Trusted, Management, GPU)
- ✅ **Zero-trust access policies** with identity, device, and network controls
- ✅ **Intrusion detection system** with real-time monitoring and alerting
- ✅ **Network traffic monitoring** with performance analysis
- ✅ **Performance optimization** for network, firewall, and system components
- ✅ **Comprehensive backup system** with automated scheduling

### **Final Verification Commands**

```bash
# Create final verification script
cat > ~/verify_section_5c.sh << 'EOF'
#!/bin/bash

echo "🔍 Section 5C Final Verification"
echo "================================="

# Check UFW firewall
echo "1. UFW Firewall:"
sudo ufw status | grep -q "Status: active" && echo "✅ UFW Active" || echo "❌ UFW Inactive"

# Check network zones
echo "2. Network Zones:"
[ -d "/etc/network-zones" ] && echo "✅ Network zones configured" || echo "❌ Network zones missing"

# Check zero-trust
echo "3. Zero-Trust:"
[ -d "/etc/zero-trust" ] && echo "✅ Zero-trust configured" || echo "❌ Zero-trust missing"

# Check IDS
echo "4. Intrusion Detection:"
[ -d "/etc/twintower-ids" ] && echo "✅ IDS configured" || echo "❌ IDS missing"

# Check traffic monitoring
echo "5. Traffic Monitoring:"
[ -d "/etc/twintower-traffic" ] && echo "✅ Traffic monitoring configured" || echo "❌ Traffic monitoring missing"

# Check performance optimization
echo "6. Performance Optimization:"
[ -f "/etc/sysctl.d/99-twintower-network.conf" ] && echo "✅ Performance optimized" || echo "❌ Performance not optimized"

# Check backup system
echo "7. Backup System:"
[ -d "/home/$(whoami)/firewall_backups" ] && echo "✅ Backup system configured" || echo "❌ Backup system missing"

# Check services
echo "8. Services:"
sudo systemctl is-active twintower-ids && echo "✅ IDS service running" || echo "⚠️  IDS service stopped"
sudo systemctl is-active twintower-traffic && echo "✅ Traffic service running" || echo "⚠️  Traffic service stopped"
sudo systemctl is-active twintower-performance && echo "✅ Performance service running" || echo "⚠️  Performance service stopped"

echo "================================="
echo "✅ Section 5C verification complete!"
EOF

chmod +x ~/verify_section_5c.sh
./verify_section_5c.sh
```

### **Security Dashboard Access**

Access your comprehensive security management tools:

```bash
# Main security dashboard
./ufw_dashboard.sh

# Network zones dashboard
./zone_dashboard.sh

# Zero-trust dashboard
./zt_dashboard.sh

# IDS dashboard
./ids_dashboard.sh

# Traffic monitoring dashboard
./traffic_dashboard.sh

# Performance dashboard
./performance_dashboard.sh
```

### **Complete TwinTower Security Architecture**

Your TwinTower GPU infrastructure now has enterprise-grade security:

```
Internet ←→ Tailscale Mesh ←→ Advanced Firewall ←→ Zero-Trust ←→ TwinTower Infrastructure
                                      ↓                ↓
                               Network Zones    IDS/IPS System
                                      ↓                ↓
                            Traffic Monitoring  Performance Optimization
                                      ↓                ↓
                              Automated Backup  Comprehensive Logging
```

### **Service Management Commands**

```bash
# Start all security services
sudo systemctl start twintower-ids twintower-traffic twintower-performance

# Enable all services for boot
sudo systemctl enable twintower-ids twintower-traffic twintower-performance twintower-backup.timer

# Check service status
sudo systemctl status twintower-ids twintower-traffic twintower-performance

# View service logs
sudo journalctl -u twintower-ids -f
sudo journalctl -u twintower-traffic -f
sudo journalctl -u twintower-performance -f
```

### **Maintenance Tasks**

```bash
# Daily tasks
./firewall_backup_system.sh backup configs
./performance_optimizer.sh report

# Weekly tasks
./firewall_backup_system.sh backup full
./intrusion_detection.sh report
./network_traffic_monitor.sh report

# Monthly tasks
./firewall_backup_system.sh cleanup
./performance_optimizer.sh optimize all
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📝 **Section 5C Summary**

**What was accomplished:**
- ✅ **Advanced UFW firewall** with intelligent rules, rate limiting, and performance optimization
- ✅ **Network segmentation** with 5 security zones (DMZ, Internal, Trusted, Management, GPU)
- ✅ **Zero-trust access control** with identity, device, and network-based policies
- ✅ **Intrusion detection system** with real-time monitoring, alerting, and automated response
- ✅ **Network traffic monitoring** with bandwidth analysis, anomaly detection, and performance metrics
- ✅ **Performance optimization** for network, firewall, and system components
- ✅ **Comprehensive backup system** with automated scheduling and integrity verification

**Security Architecture Completed:**
```
🌐 Internet Traffic
    ↓
🔥 Advanced UFW Firewall (Layer 1)
    ↓
🌐 Network Zones (Layer 2)
    ↓
🔒 Zero-Trust Policies (Layer 3)
    ↓
🚨 Intrusion Detection (Layer 4)
    ↓
📊 Traffic Monitoring (Layer 5)
    ↓
🖥️ TwinTower Infrastructure
```

**Management Tools Created:**
- `advanced_ufw_manager.sh` - Comprehensive firewall management
- `network_segmentation.sh` - Zone-based network security
- `zero_trust_access.sh` - Identity and device access control
- `intrusion_detection.sh` - Real-time threat detection
- `network_traffic_monitor.sh` - Traffic analysis and monitoring
- `performance_optimizer.sh` - System performance optimization
- `firewall_backup_system.sh` - Complete backup and recovery

**Security Monitoring Dashboard:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                    🔐 TwinTower Security Center                      │
├─────────────────────────────────────────────────────────────────────┤
│ 🔥 Firewall: Active    🌐 Zones: 5 Active    🔒 Zero-Trust: Enabled │
│ 🚨 IDS: Monitoring     📊 Traffic: Normal    ⚡ Performance: Optimal │
│ 💾 Backup: Scheduled   📈 Alerts: 0 Critical 🎯 Compliance: 100%   │
└─────────────────────────────────────────────────────────────────────┘
```

**Complete TwinTower Security Framework:**
Your TwinTower GPU infrastructure now implements a comprehensive, enterprise-grade security framework with:

- **Multi-layered defense** - 5 distinct security layers
- **Zero-trust architecture** - Never trust, always verify
- **Real-time monitoring** - Continuous threat detection
- **Automated response** - Intelligent threat mitigation
- **Performance optimization** - Security without compromise
- **Comprehensive backup** - Complete disaster recovery

**🎉 Congratulations!** You have successfully completed Section 5C and the entire TwinTower GPU Infrastructure Security Framework. Your system is now protected by enterprise-grade security controls with comprehensive monitoring, alerting, and automated response capabilities.

**[⬆️ Back to TOC](#-table-of-contents)**/')
MEM_USAGE=\$(free | grep "Mem:" | awk '{print int(\$3*100/\$2)}')
DISK_USAGE=\$(df -h / | tail -1 | awk '{print \$5}' | sed 's/%//')
LOAD_AVG=\$(uptime | awk -F'load average:' '{print \$2}' | awk '{print \$1}' | sed 's/,//')

echo -e "CPU Usage: \${GREEN}\$CPU_USAGE%\${NC}"
echo -e "Memory Usage: \${GREEN}\$MEM_USAGE%\${NC}"
echo -e "Disk Usage: \${GREEN}\$DISK_USAGE%\${NC}"
echo -e "Load Average: \${GREEN}\$LOAD_AVG\${NC}"
echo

# Network Performance
echo -e "\${YELLOW}🌐 Network Performance\${NC}"
echo "----------------------"
ACTIVE_CONNECTIONS=\$(netstat -tn | grep ESTABLISHED | wc -l)
LISTENING_PORTS=\$(netstat -tln | grep LISTEN | wc -l)
PRIMARY_INTERFACE=\$(ip route | grep default | awk '{print \$5}' | head -1)

echo -e "Active Connections: \${GREEN}\$ACTIVE_CONNECTIONS\${NC}"
echo -e "Listening Ports: \${GREEN}\$LISTENING_PORTS\${NC}"
echo -e "Primary Interface: \${GREEN}\$PRIMARY_INTERFACE\${NC}"

if [ -n "\$PRIMARY_INTERFACE" ]; then
    INTERFACE_STATS=\$(cat /proc/net/dev | grep "\$PRIMARY_INTERFACE:" | tr -s ' ')
    if [ -n "\$INTERFACE_STATS" ]; then
        RX_BYTES=\$(echo "\$INTERFACE_STATS" | cut -d' ' -f2)
        TX_BYTES=\$(echo "\$INTERFACE_STATS" | cut -d' ' -f10)
        RX_MB=\$(echo "scale=2; \$RX_BYTES / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
        TX_MB=\$(echo "scale=2; \$TX_BYTES / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
        echo -e "Traffic RX: \${GREEN}\$RX_MB MB\${NC}"
        echo -e "Traffic TX: \${GREEN}\$TX_MB MB\${NC}"
    fi
fi
echo

# Firewall Performance
echo -e "\${YELLOW}🔥 Firewall Performance\${NC}"
echo "-----------------------"
UFW_STATUS=\$(sudo ufw status | head -1)
UFW_RULES=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
CONNTRACK_COUNT=\$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")
CONNTRACK_MAX=\$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "0")

echo -e "UFW Status: \${GREEN}\$UFW_STATUS\${NC}"
echo -e "UFW Rules: \${GREEN}\$UFW_RULES\${NC}"
echo -e "Connection Tracking: \${GREEN}\$CONNTRACK_COUNT/\$CONNTRACK_MAX\${NC}"

if [ \$CONNTRACK_MAX -gt 0 ]; then
    CONNTRACK_USAGE=\$(echo "scale=2; \$CONNTRACK_COUNT * 100 / \$CONNTRACK_MAX" | bc -l)
    echo -e "Conntrack Usage: \${GREEN}\$CONNTRACK_USAGE%\${NC}"
fi
echo

# Performance Alerts
echo -e "\${YELLOW}🚨 Performance Alerts\${NC}"
echo "---------------------"
if [ -f "\$PERF_LOG_DIR/alerts.log" ]; then
    ALERT_COUNT=\$(tail -n 20 "\$PERF_LOG_DIR/alerts.log" | wc -l)
    if [ \$ALERT_COUNT -gt 0 ]; then
        echo -e "Recent Alerts: \${RED}\$ALERT_COUNT\${NC}"
        tail -n 5 "\$PERF_LOG_DIR/alerts.log" | while read line; do
            echo -e "  \${RED}⚠️\${NC} \$line"
        done
    else
        echo -e "Recent Alerts: \${GREEN}0\${NC}"
    fi
else
    echo -e "No alert data available"
fi
echo

# System Health
echo -e "\${YELLOW}💓 System Health\${NC}"
echo "----------------"
UPTIME=\$(uptime | awk '{print \$3, \$4}' | sed 's/,//')
PROCESSES=\$(ps aux | wc -l)
ZOMBIES=\$(ps aux | grep -c '<defunct>' || echo "0")

echo -e "Uptime: \${GREEN}\$UPTIME\${NC}"
echo -e "Processes: \${GREEN}\$PROCESSES\${NC}"
echo -e "Zombies: \${GREEN}\$ZOMBIES\${NC}"

# Check critical services
SERVICES=("ssh" "docker" "tailscaled" "ufw")
echo -e "Critical Services:"
for service in "\${SERVICES[@]}"; do
    if sudo systemctl is-active --quiet "\$service"; then
        echo -e "  \${GREEN}✅ \$service\${NC}"
    else
        echo -e "  \${RED}❌ \$service\${NC}"
    fi
done
echo

# Performance Trends
echo -e "\${YELLOW}📈 Performance Trends\${NC}"
echo "--------------------"
if [ -f "\$PERF_DATA_DIR/system_metrics.csv" ]; then
    echo "Last 5 measurements:"
    tail -n 5 "\$PERF_DATA_DIR/system_metrics.csv" | while IFS=',' read ts cpu mem disk load conn; do
        time_str=\$(date -d "@\$ts" '+%H:%M:%S')
        echo -e "  \$time_str - CPU: \${GREEN}\$cpu%\${NC}, RAM: \${GREEN}\$mem%\${NC}, Conn: \${GREEN}\$conn\${NC}"
    done
else
    echo -e "No trend data available"
fi
echo

# Optimization Status
echo -e "\${YELLOW}⚡ Optimization Status\${NC}"
echo "---------------------"
if [ -f "/etc/sysctl.d/99-twintower-network.conf" ]; then
    echo -e "Network Optimization: \${GREEN}✅ Applied\${NC}"
else
    echo -e "Network Optimization: \${RED}❌ Not Applied\${NC}"
fi

if [ -f "/etc/sysctl.d/99-twintower-system.conf" ]; then
    echo -e "System Optimization: \${GREEN}✅ Applied\${NC}"
else
    echo -e "System Optimization: \${RED}❌ Not Applied\${NC}"
fi

if [ -f "/etc/ufw/sysctl.conf.backup"* ]; then
    echo -e "Firewall Optimization: \${GREEN}✅ Applied\${NC}"
else
    echo -e "Firewall Optimization: \${RED}❌ Not Applied\${NC}"
fi
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Start monitoring: ./performance_monitor.sh daemon"
echo "2. Generate report: ./performance_monitor.sh report"
echo "3. Check status: ./performance_monitor.sh status"
echo "4. Optimize system: ./performance_optimizer.sh optimize"
echo "5. View top processes: top"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
PERF_DASHBOARD_EOF

    chmod +x ~/performance_dashboard.sh
    
    log_message "✅ Performance dashboard created"
}

# Function to create performance service
create_performance_service() {
    log_message "⚙️ Creating performance monitoring service..."
    
    cat << PERF_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-performance.service
[Unit]
Description=TwinTower Performance Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/performance_monitor.sh daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
PERF_SERVICE_EOF

    # Enable service
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-performance.service
    
    log_message "✅ Performance monitoring service created"
}

# Main execution
main() {
    echo -e "${BLUE}⚡ TwinTower Performance Optimization${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}====================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_performance_optimization
            optimize_network_performance
            optimize_firewall_performance
            optimize_system_performance
            create_performance_monitoring
            create_performance_dashboard
            create_performance_service
            
            echo -e "${GREEN}✅ Performance optimization configured!${NC}"
            ;;
        "optimize")
            case "$OPTIMIZATION_TYPE" in
                "network")
                    optimize_network_performance
                    ;;
                "firewall")
                    optimize_firewall_performance
                    ;;
                "system")
                    optimize_system_performance
                    ;;
                "all")
                    optimize_network_performance
                    optimize_firewall_performance
                    optimize_system_performance
                    ;;
                *)
                    echo "Invalid optimization type: $OPTIMIZATION_TYPE"
                    echo "Usage: $0 optimize <network|firewall|system|all>"
                    exit 1
                    ;;
            esac
            
            echo -e "${GREEN}✅ Performance optimization completed!${NC}"
            ;;
        "start")
            sudo systemctl start twintower-performance.service
            echo -e "${GREEN}✅ Performance monitoring service started${NC}"
            ;;
        "stop")
            sudo systemctl stop twintower-performance.service
            echo -e "${GREEN}✅ Performance monitoring service stopped${NC}"
            ;;
        "status")
            ~/performance_dashboard.sh
            ;;
        "monitor")
            ~/performance_monitor.sh daemon
            ;;
        "report")
            ~/performance_monitor.sh report
            ;;
        "dashboard")
            ~/performance_dashboard.sh
            ;;
        *)
            echo "Usage: $0 <setup|optimize|start|stop|status|monitor|report|dashboard>"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/performance_optimizer.sh
```

### **Step 2: Execute Performance Optimization**

```bash
# Setup performance optimization
./performance_optimizer.sh setup

# Start performance monitoring
./performance_optimizer.sh start

# View performance dashboard
./performance_optimizer.sh dashboard

# Generate performance report
./performance_optimizer.sh report
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔄 **Backup & Recovery**

### **Step 1: Create Comprehensive Backup System**

```bash
cat > ~/firewall_backup_system.sh << 'EOF'
#!/bin/bash

# TwinTower Firewall & Access Control Backup System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-backup}"
BACKUP_TYPE="${2:-full}"
RESTORE_FILE="${3:-}"
TOWER_NAME="${4:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Backup configuration
BACKUP_DIR="/home/$(whoami)/firewall_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_LOG="$BACKUP_DIR/backup.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$BACKUP_LOG"
}

# Function to create backup directories
create_backup_directories() {
    log_message "📁 Creating backup directories..."
    
    mkdir -p "$BACKUP_DIR"/{configs,logs,scripts,data,full}
    touch "$BACKUP_LOG"
    
    log_message "✅ Backup directories created"
}

# Function to backup UFW configuration
backup_ufw_config() {
    log_message "🔥 Backing up UFW configuration..."
    
    local ufw_backup="$BACKUP_DIR/configs/ufw_config_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create UFW backup structure
    mkdir -p "$temp_dir/ufw_backup"
    
    # Backup UFW files
    sudo cp -r /etc/ufw "$temp_dir/ufw_backup/" 2>/dev/null || true
    sudo cp /etc/default/ufw "$temp_dir/ufw_backup/" 2>/dev/null || true
    
    # Backup UFW status and rules
    sudo ufw status verbose > "$temp_dir/ufw_backup/ufw_status.txt" 2>/dev/null || true
    sudo ufw status numbered > "$temp_dir/ufw_backup/ufw_rules.txt" 2>/dev/null || true
    
    # Backup iptables rules
    sudo iptables-save > "$temp_dir/ufw_backup/iptables.rules" 2>/dev/null || true
    sudo ip6tables-save > "$temp_dir/ufw_backup/ip6tables.rules" 2>/dev/null || true
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$ufw_backup" ufw_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ UFW configuration backed up: $ufw_backup"
}

# Function to backup network zones
backup_network_zones() {
    log_message "🌐 Backing up network zones..."
    
    local zones_backup="$BACKUP_DIR/configs/zones_config_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create zones backup structure
    mkdir -p "$temp_dir/zones_backup"
    
    # Backup zone configurations
    if [ -d "/etc/network-zones" ]; then
        sudo cp -r /etc/network-zones "$temp_dir/zones_backup/" 2>/dev/null || true
    fi
    
    # Backup zone management scripts
    cp ~/network_segmentation.sh "$temp_dir/zones_backup/" 2>/dev/null || true
    cp ~/zone_monitor.sh "$temp_dir/zones_backup/" 2>/dev/null || true
    cp ~/zone_dashboard.sh "$temp_dir/zones_backup/" 2>/dev/null || true
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$zones_backup" zones_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ Network zones backed up: $zones_backup"
}

# Function to backup zero-trust policies
backup_zero_trust() {
    log_message "🔒 Backing up zero-trust policies..."
    
    local zt_backup="$BACKUP_DIR/configs/zero_trust_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create zero-trust backup structure
    mkdir -p "$temp_dir/zero_trust_backup"
    
    # Backup zero-trust configurations
    if [ -d "/etc/zero-trust" ]; then
        sudo cp -r /etc/zero-trust "$temp_dir/zero_trust_backup/" 2>/dev/null || true
    fi
    
    # Backup zero-trust scripts
    cp ~/zero_trust_access.sh "$temp_dir/zero_trust_backup/" 2>/dev/null || true
    cp ~/zt_enforcement_engine.sh "$temp_dir/zero_trust_backup/" 2>/dev/null || true
    cp ~/zt_dashboard.sh "$temp_dir/zero_trust_backup/" 2>/dev/null || true
    
    # Backup session data
    if [ -d "/var/lib/zero-trust" ]; then
        sudo cp -r /var/lib/zero-trust "$temp_dir/zero_trust_backup/" 2>/dev/null || true
    fi
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$zt_backup" zero_trust_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ Zero-trust policies backed up: $zt_backup"
}

# Function to backup IDS configuration
backup_ids_config() {
    log_message "🚨 Backing up IDS configuration..."
    
    local ids_backup="$BACKUP_DIR/configs/ids_config_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create IDS backup structure
    mkdir -p "$temp_dir/ids_backup"
    
    # Backup IDS configurations
    if [ -d "/etc/twintower-ids" ]; then
        sudo cp -r /etc/twintower-ids "$temp_dir/ids_backup/" 2>/dev/null || true
    fi
    
    # Backup IDS scripts
    cp ~/intrusion_detection.sh "$temp_dir/ids_backup/" 2>/dev/null || true
    cp ~/ids_detection_engine.sh "$temp_dir/ids_backup/" 2>/dev/null || true
    cp ~/ids_dashboard.sh "$temp_dir/ids_backup/" 2>/dev/null || true
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$ids_backup" ids_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ IDS configuration backed up: $ids_backup"
}

# Function to backup performance optimizations
backup_performance_config() {
    log_message "⚡ Backing up performance optimizations..."
    
    local perf_backup="$BACKUP_DIR/configs/performance_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create performance backup structure
    mkdir -p "$temp_dir/performance_backup"
    
    # Backup performance configurations
    if [ -d "/etc/twintower-performance" ]; then
        sudo cp -r /etc/twintower-performance "$temp_dir/performance_backup/" 2>/dev/null || true
    fi
    
    # Backup sysctl optimizations
    sudo cp /etc/sysctl.d/99-twintower-*.conf "$temp_dir/performance_backup/" 2>/dev/null || true
    
    # Backup performance scripts
    cp ~/performance_optimizer.sh "$temp_dir/performance_backup/" 2>/dev/null || true
    cp ~/performance_monitor.sh "$temp_dir/performance_backup/" 2>/dev/null || true
    cp ~/performance_dashboard.sh "$temp_dir/performance_backup/" 2>/dev/null || true
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$perf_backup" performance_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ Performance optimizations backed up: $perf_backup"
}

# Function to backup logs
backup_logs() {
    log_message "📊 Backing up system logs..."
    
    local logs_backup="$BACKUP_DIR/logs/system_logs_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create logs backup structure
    mkdir -p "$temp_dir/logs_backup"
    
    # Backup firewall logs
    sudo cp /var/log/ufw.log "$temp_dir/logs_backup/" 2>/dev/null || true
    
    # Backup IDS logs
    if [ -d "/var/log/twintower-ids" ]; then
        sudo cp -r /var/log/twintower-ids "$temp_dir/logs_backup/" 2>/dev/null || true
    fi
    
    # Backup traffic logs
    if [ -d "/var/log/twintower-traffic" ]; then
        sudo cp -r /var/log/twintower-traffic "$temp_dir/logs_backup/" 2>/dev/null || true
    fi
    
    # Backup performance logs
    if [ -d "/var/log/twintower-performance" ]; then
        sudo cp -r /var/log/twintower-performance "$temp_dir/logs_backup/" 2>/dev/null || true
    fi
    
    # Backup zero-trust logs
    sudo cp /var/log/zero-trust*.log "$temp_dir/logs_backup/" 2>/dev/null || true
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$logs_backup" logs_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ System logs backed up: $logs_backup"
}

# Function to backup management scripts
backup_scripts() {
    log_message "📋 Backing up management scripts..."
    
    local scripts_backup="$BACKUP_DIR/scripts/management_scripts_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create scripts backup structure
    mkdir -p "$temp_dir/scripts_backup"
    
    # Backup all management scripts
    cp ~/advanced_ufw_manager.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/network_segmentation.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/zero_trust_access.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/intrusion_detection.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/network_traffic_monitor.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/performance_optimizer.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/firewall_backup_system.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    
    # Backup dashboard scripts
    cp ~/ufw_dashboard.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/zone_dashboard.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/zt_dashboard.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/ids_dashboard.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/traffic_dashboard.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    cp ~/performance_dashboard.sh "$temp_dir/scripts_backup/" 2>/dev/null || true
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$scripts_backup" scripts_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ Management scripts backed up: $scripts_backup"
}

# Function to backup data
backup_data() {
    log_message "💾 Backing up system data..."
    
    local data_backup="$BACKUP_DIR/data/system_data_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create data backup structure
    mkdir -p "$temp_dir/data_backup"
    
    # Backup traffic data
    if [ -d "/var/lib/twintower-traffic" ]; then
        sudo cp -r /var/lib/twintower-traffic "$temp_dir/data_backup/" 2>/dev/null || true
    fi
    
    # Backup performance data
    if [ -d "/var/lib/twintower-performance" ]; then
        sudo cp -r /var/lib/twintower-performance "$temp_dir/data_backup/" 2>/dev/null || true
    fi
    
    # Backup IDS data
    if [ -d "/var/lib/twintower-ids" ]; then
        sudo cp -r /var/lib/twintower-ids "$temp_dir/data_backup/" 2>/dev/null || true
    fi
    
    # Backup zero-trust session data
    if [ -d "/var/lib/zero-trust" ]; then
        sudo cp -r /var/lib/zero-trust "$temp_dir/data_backup/" 2>/dev/null || true
    fi
    
    # Create backup archive
    cd "$temp_dir"
    tar -czf "$data_backup" data_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ System data backed up: $data_backup"
}

# Function to create full system backup
create_full_backup() {
    log_message "🎯 Creating full system backup..."
    
    local full_backup="$BACKUP_DIR/full/full_backup_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    # Create full backup structure
    mkdir -p "$temp_dir/full_backup"
    
    # Copy all individual backups
    cp -r "$BACKUP_DIR/configs"/* "$temp_dir/full_backup/" 2>/dev/null || true
    cp -r "$BACKUP_DIR/logs"/* "$temp_dir/full_backup/" 2>/dev/null || true
    cp -r "$BACKUP_DIR/scripts"/* "$temp_dir/full_backup/" 2>/dev/null || true
    cp -r "$BACKUP_DIR/data"/* "$temp_dir/full_backup/" 2>/dev/null || true
    
    # Create backup manifest
    cat > "$temp_dir/full_backup/backup_manifest.txt" << MANIFEST_EOF
TwinTower Firewall & Access Control Full Backup
===============================================
Backup Date: $(date)
Tower Name: $TOWER_NAME
Backup Type: Full System Backup
Backup Location: $full_backup

System Information:
------------------
Hostname: $(hostname)
OS Version: $(lsb_release -d | cut -f2)
Kernel Version: $(uname -r)
UFW Version: $(ufw --version | head -1)
Tailscale Version: $(tailscale version | head -1)

Backup Contents:
---------------
$(ls -la "$temp_dir/full_backup/" | grep -E '\.(tar\.gz|txt)echo "5. Real-time monitor: watch -n 1 './traffic_dashboard.sh'"

echo
echo -e "\${BLUE}=========================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/traffic_dashboard.sh
    
    log_message "✅ Traffic monitoring dashboard created"
}

# Function to create traffic monitoring service
create_traffic_service() {
    log_message "⚙️ Creating traffic monitoring service..."
    
    cat << TRAFFIC_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-traffic.service
[Unit]
Description=TwinTower Network Traffic Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/traffic_analyzer.sh daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
TRAFFIC_SERVICE_EOF

    # Enable service
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-traffic.service
    
    log_message "✅ Traffic monitoring service created"
}

# Function to create traffic testing tools
create_traffic_testing() {
    log_message "🧪 Creating traffic testing tools..."
    
    cat << TRAFFIC_TEST_EOF > ~/test_traffic_monitoring.sh
#!/bin/bash

# TwinTower Traffic Monitoring Test Suite
set -e

TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Traffic Monitoring Test Suite\${NC}"
echo -e "\${BLUE}==========================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test monitoring infrastructure
echo -e "\${YELLOW}🔧 Testing Monitoring Infrastructure\${NC}"
echo "------------------------------------"
run_test "Config directory exists" "[ -d '\$TRAFFIC_CONFIG_DIR' ]"
run_test "Log directory exists" "[ -d '\$TRAFFIC_LOG_DIR' ]"
run_test "Data directory exists" "[ -d '\$TRAFFIC_DATA_DIR' ]"
run_test "Monitor config exists" "[ -f '\$TRAFFIC_CONFIG_DIR/monitor.conf' ]"
run_test "Interface config exists" "[ -f '\$TRAFFIC_CONFIG_DIR/interfaces.conf' ]"

# Test monitoring tools
echo -e "\${YELLOW}📊 Testing Monitoring Tools\${NC}"
echo "---------------------------"
run_test "Traffic analyzer exists" "[ -f '\$HOME/traffic_analyzer.sh' ]"
run_test "Traffic dashboard exists" "[ -f '\$HOME/traffic_dashboard.sh' ]"
run_test "Interface detector exists" "[ -f '\$HOME/detect_interfaces.sh' ]"

# Test system commands
echo -e "\${YELLOW}⚙️ Testing System Commands\${NC}"
echo "--------------------------"
run_test "netstat command available" "command -v netstat"
run_test "iftop command available" "command -v iftop"
run_test "vnstat command available" "command -v vnstat"

# Test network interfaces
echo -e "\${YELLOW}🌐 Testing Network Interfaces\${NC}"
echo "-----------------------------"
run_test "Primary interface detected" "[ -n '\$(ip route | grep default | awk \"{print \\\$5}\" | head -1)' ]"
run_test "Loopback interface exists" "ip addr show lo"
run_test "Interface statistics available" "[ -f '/proc/net/dev' ]"

# Test traffic analysis
echo -e "\${YELLOW}📈 Testing Traffic Analysis\${NC}"
echo "---------------------------"
run_test "Connection counting works" "netstat -tn | grep ESTABLISHED | wc -l"
run_test "Port listening detection" "netstat -tln | grep LISTEN | wc -l"
run_test "Process net dev reading" "cat /proc/net/dev | grep -E '^[[:space:]]*lo:'"

# Test log file creation
echo -e "\${YELLOW}📝 Testing Log Files\${NC}"
echo "--------------------"
run_test "Monitor log writable" "touch '\$TRAFFIC_LOG_DIR/test.log' && rm '\$TRAFFIC_LOG_DIR/test.log'"
run_test "Data directory writable" "touch '\$TRAFFIC_DATA_DIR/test.dat' && rm '\$TRAFFIC_DATA_DIR/test.dat'"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All traffic monitoring tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
TRAFFIC_TEST_EOF

    chmod +x ~/test_traffic_monitoring.sh
    
    log_message "✅ Traffic testing tools created"
}

# Main execution
main() {
    echo -e "${BLUE}📊 TwinTower Network Traffic Monitoring${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=======================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_traffic_monitoring
            create_traffic_analyzer
            create_traffic_dashboard
            create_traffic_service
            create_traffic_testing
            
            echo -e "${GREEN}✅ Network traffic monitoring configured!${NC}"
            ;;
        "start")
            sudo systemctl start twintower-traffic.service
            echo -e "${GREEN}✅ Traffic monitoring service started${NC}"
            ;;
        "stop")
            sudo systemctl stop twintower-traffic.service
            echo -e "${GREEN}✅ Traffic monitoring service stopped${NC}"
            ;;
        "status")
            ~/traffic_dashboard.sh
            ;;
        "test")
            ~/test_traffic_monitoring.sh
            ;;
        "monitor")
            ~/traffic_analyzer.sh daemon
            ;;
        "report")
            ~/traffic_analyzer.sh report
            ;;
        "dashboard")
            ~/traffic_dashboard.sh
            ;;
        *)
            echo "Usage: $0 <setup|start|stop|status|test|monitor|report|dashboard>"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/network_traffic_monitor.sh
```

### **Step 2: Execute Network Traffic Monitoring Setup**

```bash
# Setup network traffic monitoring
./network_traffic_monitor.sh setup

# Start traffic monitoring service
./network_traffic_monitor.sh start

# View traffic dashboard
./network_traffic_monitor.sh dashboard

# Test monitoring functionality
./network_traffic_monitor.sh test
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## ⚡ **Performance Optimization**

### **Step 1: Create Performance Optimization System**

```bash
cat > ~/performance_optimizer.sh << 'EOF'
#!/bin/bash

# TwinTower Performance Optimization System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
OPTIMIZATION_TYPE="${2:-all}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Performance configuration
PERF_CONFIG_DIR="/etc/twintower-performance"
PERF_LOG_DIR="/var/log/twintower-performance"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$PERF_LOG_DIR/optimizer.log"
}

# Function to setup performance optimization infrastructure
setup_performance_optimization() {
    log_message "⚡ Setting up performance optimization infrastructure..."
    
    # Create directories
    sudo mkdir -p "$PERF_CONFIG_DIR" "$PERF_LOG_DIR"
    
    # Create performance configuration
    cat << PERF_CONFIG_EOF | sudo tee "$PERF_CONFIG_DIR/performance.conf"
# TwinTower Performance Configuration
PERF_ENABLED=true
PERF_PROFILE="balanced"
PERF_NETWORK_OPTIMIZATION=true
PERF_FIREWALL_OPTIMIZATION=true
PERF_SYSTEM_OPTIMIZATION=true
PERF_MONITORING_ENABLED=true
PERF_AUTO_TUNING=false
PERF_ALERTING_ENABLED=true
PERF_BACKUP_CONFIGS=true
PERF_CONFIG_EOF

    log_message "✅ Performance optimization infrastructure created"
}

# Function to optimize network performance
optimize_network_performance() {
    log_message "🌐 Optimizing network performance..."
    
    # Backup current network settings
    sudo cp /etc/sysctl.conf "/etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Create optimized network configuration
    cat << NETWORK_EOF | sudo tee /etc/sysctl.d/99-twintower-network.conf
# TwinTower Network Performance Optimization

# Core network settings
net.core.rmem_default = 262144
net.core.rmem_max = 134217728
net.core.wmem_default = 262144
net.core.wmem_max = 134217728
net.core.netdev_max_backlog = 30000
net.core.somaxconn = 4096

# TCP settings
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_rmem = 4096 32768 134217728
net.ipv4.tcp_wmem = 4096 32768 134217728
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_fack = 1
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_no_metrics_save = 1
net.ipv4.tcp_moderate_rcvbuf = 1
net.ipv4.tcp_rfc1337 = 1
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_keepalive_intvl = 60

# Connection tracking
net.netfilter.nf_conntrack_max = 2097152
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30
net.netfilter.nf_conntrack_tcp_timeout_fin_wait = 30
net.netfilter.nf_conntrack_tcp_timeout_close_wait = 30
net.netfilter.nf_conntrack_udp_timeout = 30
net.netfilter.nf_conntrack_udp_timeout_stream = 180
net.netfilter.nf_conntrack_generic_timeout = 300

# Buffer sizes
net.ipv4.udp_rmem_min = 8192
net.ipv4.udp_wmem_min = 8192
net.ipv4.tcp_adv_win_scale = 1

# Network security (with performance considerations)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1

# Memory and file limits
fs.file-max = 2097152
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
NETWORK_EOF

    # Apply network optimizations
    sudo sysctl -p /etc/sysctl.d/99-twintower-network.conf
    
    log_message "✅ Network performance optimized"
}

# Function to optimize firewall performance
optimize_firewall_performance() {
    log_message "🔥 Optimizing firewall performance..."
    
    # Create optimized iptables rules
    cat << IPTABLES_EOF | sudo tee /etc/iptables/rules.v4.optimized
# TwinTower Optimized iptables Rules
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

# Loopback
-A INPUT -i lo -j ACCEPT

# Connection tracking optimization
-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
-A INPUT -m conntrack --ctstate INVALID -j DROP

# Rate limiting for new connections
-A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name SSH
-A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP

# Tailscale network (optimized)
-A INPUT -s 100.64.0.0/10 -j ACCEPT

# Local network (optimized)
-A INPUT -s 192.168.1.0/24 -j ACCEPT

# Custom SSH ports
-A INPUT -p tcp --dport 2122 -j ACCEPT
-A INPUT -p tcp --dport 2222 -j ACCEPT
-A INPUT -p tcp --dport 2322 -j ACCEPT

# Docker Swarm (optimized)
-A INPUT -p tcp --dport 2377 -j ACCEPT
-A INPUT -p tcp --dport 7946 -j ACCEPT
-A INPUT -p udp --dport 7946 -j ACCEPT
-A INPUT -p udp --dport 4789 -j ACCEPT

# ICMP (rate limited)
-A INPUT -p icmp -m limit --limit 5/sec --limit-burst 10 -j ACCEPT

# Log dropped packets (rate limited)
-A INPUT -m limit --limit 5/min --limit-burst 10 -j LOG --log-prefix "IPTABLES-DROP: "

COMMIT
IPTABLES_EOF

    # Optimize UFW backend
    if [ -f "/etc/ufw/sysctl.conf" ]; then
        sudo cp "/etc/ufw/sysctl.conf" "/etc/ufw/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)"
        
        cat << UFW_SYSCTL_EOF | sudo tee -a /etc/ufw/sysctl.conf

# TwinTower UFW Performance Optimizations
net.netfilter.nf_conntrack_max = 2097152
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30
net.netfilter.nf_conntrack_buckets = 524288
net.netfilter.nf_conntrack_expect_max = 1024
UFW_SYSCTL_EOF
    fi
    
    log_message "✅ Firewall performance optimized"
}

# Function to optimize system performance
optimize_system_performance() {
    log_message "⚙️ Optimizing system performance..."
    
    # CPU frequency scaling
    if [ -f "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
        echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
    fi
    
    # Create system optimization configuration
    cat << SYSTEM_EOF | sudo tee /etc/sysctl.d/99-twintower-system.conf
# TwinTower System Performance Optimization

# Kernel parameters
kernel.panic = 30
kernel.pid_max = 4194304
kernel.threads-max = 4194304

# Memory management
vm.overcommit_memory = 1
vm.overcommit_ratio = 100
vm.vfs_cache_pressure = 50
vm.dirty_expire_centisecs = 3000
vm.dirty_writeback_centisecs = 500

# Process limits
fs.nr_open = 1048576
fs.file-max = 2097152

# Security limits (with performance considerations)
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 1
kernel.yama.ptrace_scope = 1
SYSTEM_EOF

    # Apply system optimizations
    sudo sysctl -p /etc/sysctl.d/99-twintower-system.conf
    
    # Optimize systemd services
    sudo systemctl daemon-reload
    
    log_message "✅ System performance optimized"
}

# Function to create performance monitoring
create_performance_monitoring() {
    log_message "📊 Creating performance monitoring system..."
    
    cat << PERF_MONITOR_EOF > ~/performance_monitor.sh
#!/bin/bash

# TwinTower Performance Monitor
set -e

PERF_LOG_DIR="/var/log/twintower-performance"
PERF_DATA_DIR="/var/lib/twintower-performance"
MONITOR_INTERVAL="\${1:-60}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$PERF_LOG_DIR/monitor.log"
}

# Function to collect system metrics
collect_system_metrics() {
    local timestamp=\$(date +%s)
    
    # CPU usage
    local cpu_usage=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//')
    
    # Memory usage
    local mem_total=\$(free -m | grep "Mem:" | awk '{print \$2}')
    local mem_used=\$(free -m | grep "Mem:" | awk '{print \$3}')
    local mem_usage=\$(echo "scale=2; \$mem_used * 100 / \$mem_total" | bc -l)
    
    # Disk usage
    local disk_usage=\$(df -h / | tail -1 | awk '{print \$5}' | sed 's/%//')
    
    # Load average
    local load_avg=\$(uptime | awk -F'load average:' '{print \$2}' | awk '{print \$1}' | sed 's/,//')
    
    # Network connections
    local connections=\$(netstat -tn | grep ESTABLISHED | wc -l)
    
    # Store metrics
    sudo mkdir -p "\$PERF_DATA_DIR"
    echo "\$timestamp,\$cpu_usage,\$mem_usage,\$disk_usage,\$load_avg,\$connections" >> "\$PERF_DATA_DIR/system_metrics.csv"
    
    log_message "Metrics: CPU \$cpu_usage%, RAM \$mem_usage%, Disk \$disk_usage%, Load \$load_avg, Connections \$connections"
}

# Function to collect network metrics
collect_network_metrics() {
    local timestamp=\$(date +%s)
    
    # Get primary interface
    local interface=\$(ip route | grep default | awk '{print \$5}' | head -1)
    
    if [ -n "\$interface" ]; then
        local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
        local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
        local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
        local rx_packets=\$(echo "\$stats" | cut -d' ' -f3)
        local tx_packets=\$(echo "\$stats" | cut -d' ' -f11)
        
        # Calculate rates if previous data exists
        local prev_file="\$PERF_DATA_DIR/network_prev.dat"
        if [ -f "\$prev_file" ]; then
            local prev_data=\$(cat "\$prev_file")
            local prev_time=\$(echo "\$prev_data" | cut -d',' -f1)
            local prev_rx_bytes=\$(echo "\$prev_data" | cut -d',' -f2)
            local prev_tx_bytes=\$(echo "\$prev_data" | cut -d',' -f3)
            
            local time_diff=\$((timestamp - prev_time))
            if [ \$time_diff -gt 0 ]; then
                local rx_rate=\$(echo "scale=2; (\$rx_bytes - \$prev_rx_bytes) / \$time_diff / 1024" | bc -l)
                local tx_rate=\$(echo "scale=2; (\$tx_bytes - \$prev_tx_bytes) / \$time_diff / 1024" | bc -l)
                
                echo "\$timestamp,\$interface,\$rx_rate,\$tx_rate,\$rx_packets,\$tx_packets" >> "\$PERF_DATA_DIR/network_metrics.csv"
                log_message "Network: \$interface RX \$rx_rate KB/s, TX \$tx_rate KB/s"
            fi
        fi
        
        # Store current data
        echo "\$timestamp,\$rx_bytes,\$tx_bytes" > "\$prev_file"
    fi
}

# Function to collect firewall metrics
collect_firewall_metrics() {
    local timestamp=\$(date +%s)
    
    # UFW statistics
    local ufw_active=\$(sudo ufw status | grep -c "Status: active" || echo "0")
    local ufw_rules=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
    
    # Connection tracking
    local conntrack_count=\$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")
    local conntrack_max=\$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "0")
    
    # Store metrics
    echo "\$timestamp,\$ufw_active,\$ufw_rules,\$conntrack_count,\$conntrack_max" >> "\$PERF_DATA_DIR/firewall_metrics.csv"
    
    log_message "Firewall: UFW Active \$ufw_active, Rules \$ufw_rules, Connections \$conntrack_count/\$conntrack_max"
}

# Function to detect performance issues
detect_performance_issues() {
    # Check CPU usage
    local cpu_usage=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//' | cut -d'.' -f1)
    if [ \$cpu_usage -gt 80 ]; then
        log_message "🚨 HIGH CPU USAGE: \$cpu_usage%"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH CPU: \$cpu_usage%" >> "\$PERF_LOG_DIR/alerts.log"
    fi
    
    # Check memory usage
    local mem_usage=\$(free | grep "Mem:" | awk '{print int(\$3*100/\$2)}')
    if [ \$mem_usage -gt 85 ]; then
        log_message "🚨 HIGH MEMORY USAGE: \$mem_usage%"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH MEMORY: \$mem_usage%" >> "\$PERF_LOG_DIR/alerts.log"
    fi
    
    # Check connection tracking
    local conntrack_count=\$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")
    local conntrack_max=\$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "1")
    local conntrack_usage=\$(echo "scale=2; \$conntrack_count * 100 / \$conntrack_max" | bc -l)
    
    if [ \$(echo "\$conntrack_usage > 80" | bc -l) -eq 1 ]; then
        log_message "🚨 HIGH CONNECTION TRACKING USAGE: \$conntrack_usage%"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH CONNTRACK: \$conntrack_usage%" >> "\$PERF_LOG_DIR/alerts.log"
    fi
}

# Function to generate performance report
generate_performance_report() {
    local report_file="/tmp/performance_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Performance Report
===========================
Generated: \$(date)
Tower: \$(hostname)

Current System Status:
---------------------
CPU Usage: \$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//')%
Memory Usage: \$(free | grep "Mem:" | awk '{print int(\$3*100/\$2)}')%
Disk Usage: \$(df -h / | tail -1 | awk '{print \$5}')
Load Average: \$(uptime | awk -F'load average:' '{print \$2}')
Active Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)

Network Performance:
-------------------
Primary Interface: \$(ip route | grep default | awk '{print \$5}' | head -1)
Connection Tracking: \$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")/\$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "N/A")

Firewall Status:
---------------
UFW Status: \$(sudo ufw status | head -1)
Active Rules: \$(sudo ufw status numbered | grep -c "^\[" || echo "0")

Recent Performance Alerts:
--------------------------
\$(tail -n 10 "\$PERF_LOG_DIR/alerts.log" 2>/dev/null || echo "No recent alerts")

Performance Trends:
------------------
\$(tail -n 5 "\$PERF_DATA_DIR/system_metrics.csv" 2>/dev/null | while IFS=',' read ts cpu mem disk load conn; do
    echo "\$(date -d "@\$ts" '+%H:%M:%S') - CPU: \$cpu%, RAM: \$mem%, Connections: \$conn"
done)

REPORT_EOF

    log_message "📋 Performance report generated: \$report_file"
    echo "\$report_file"
}

# Function to start performance monitoring
start_performance_monitoring() {
    log_message "🚀 Starting performance monitoring..."
    
    while true; do
        collect_system_metrics
        collect_network_metrics
        collect_firewall_metrics
        detect_performance_issues
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 60)) -eq 0 ]; then
            generate_performance_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_performance_monitoring
        ;;
    "report")
        generate_performance_report
        ;;
    "status")
        echo "Performance Monitor Status:"
        echo "=========================="
        echo "CPU: \$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//')%"
        echo "Memory: \$(free | grep "Mem:" | awk '{print int(\$3*100/\$2)}')%"
        echo "Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)"
        echo "Alerts: \$(tail -n 5 "\$PERF_LOG_DIR/alerts.log" 2>/dev/null | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <daemon|report|status>"
        exit 1
        ;;
esac
PERF_MONITOR_EOF

    chmod +x ~/performance_monitor.sh
    
    log_message "✅ Performance monitoring system created"
}

# Function to create performance dashboard
create_performance_dashboard() {
    log_message "📊 Creating performance dashboard..."
    
    cat << PERF_DASHBOARD_EOF > ~/performance_dashboard.sh
#!/bin/bash

# TwinTower Performance Dashboard
set -e

PERF_LOG_DIR="/var/log/twintower-performance"
PERF_DATA_DIR="/var/lib/twintower-performance"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}⚡ TwinTower Performance Dashboard\# Test IDS components
echo -e "\${YELLOW}⚙️ Testing IDS Components\${NC}"
echo "-------------------------"
run_test "Detection engine exists" "[ -f '\$HOME/ids_detection_engine.sh' ]"
run_test "Detection engine executable" "[ -x '\$HOME/ids_detection_engine.sh' ]"
run_test "IDS dashboard exists" "[ -f '\$HOME/ids_dashboard.sh' ]"
run_test "IDS service file exists" "[ -f '/etc/systemd/system/twintower-ids.service' ]"

# Test log files
echo -e "\${YELLOW}📊 Testing Log Files\${NC}"
echo "--------------------"
run_test "IDS log directory exists" "[ -d '/var/log/twintower-ids' ]"
run_test "IDS alert log exists" "[ -f '/var/log/twintower-ids/alerts.log' ]"
run_test "IDS detection log exists" "[ -f '/var/log/twintower-ids/detection.log' ]"

# Test rule syntax
echo -e "\${YELLOW}🔍 Testing Rule Syntax\${NC}"
echo "----------------------"
for rule_file in "\$IDS_RULES_DIR"/*.rules; do
    if [ -f "\$rule_file" ]; then
        rule_name=\$(basename "\$rule_file" .rules)
        run_test "Rule syntax valid: \$rule_name" "grep -E '^[^#]*\|[^|]*\|[^|]*\|[^|]*\## 🚨 **Intrusion Detection & Prevention**

### **Step 1: Create Advanced Intrusion Detection System**

```bash
cat > ~/intrusion_detection.sh << 'EOF'
#!/bin/bash

# TwinTower Intrusion Detection & Prevention System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
DETECTION_TYPE="${2:-realtime}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# IDS Configuration
IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="$IDS_LOG_DIR/detection.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$IDS_DETECTION_LOG"
}

# Function to setup IDS infrastructure
setup_ids_infrastructure() {
    log_message "🔧 Setting up IDS infrastructure..."
    
    # Create directories
    sudo mkdir -p "$IDS_CONFIG_DIR" "$IDS_RULES_DIR" "$IDS_LOG_DIR"
    sudo touch "$IDS_ALERT_LOG" "$IDS_DETECTION_LOG"
    
    # Create main IDS configuration
    cat << IDS_CONFIG_EOF | sudo tee "$IDS_CONFIG_DIR/ids.conf"
# TwinTower IDS Configuration
IDS_ENABLED=true
IDS_MODE="monitor"
IDS_SENSITIVITY="medium"
IDS_LOGGING_LEVEL="info"
IDS_ALERT_THRESHOLD=5
IDS_BLOCK_THRESHOLD=10
IDS_WHITELIST_ENABLED=true
IDS_LEARNING_MODE=false
IDS_REALTIME_ALERTS=true
IDS_EMAIL_ALERTS=false
IDS_WEBHOOK_ALERTS=false
IDS_AUTO_BLOCK=false
IDS_BLOCK_DURATION=3600
IDS_CLEANUP_INTERVAL=86400
IDS_CONFIG_EOF

    # Create whitelist configuration
    cat << WHITELIST_EOF | sudo tee "$IDS_CONFIG_DIR/whitelist.conf"
# TwinTower IDS Whitelist
# Trusted IP addresses and networks
100.64.0.0/10
192.168.1.0/24
127.0.0.0/8
::1/128

# Trusted processes
/usr/bin/ssh
/usr/bin/docker
/usr/bin/tailscale
/usr/sbin/sshd
WHITELIST_EOF

    log_message "✅ IDS infrastructure created"
}

# Function to create detection rules
create_detection_rules() {
    log_message "📋 Creating intrusion detection rules..."
    
    # SSH Attack Detection Rules
    cat << SSH_RULES_EOF | sudo tee "$IDS_RULES_DIR/ssh_attacks.rules"
# SSH Attack Detection Rules
# Rule format: PATTERN|SEVERITY|ACTION|DESCRIPTION

# Brute force attacks
authentication failure.*ssh|HIGH|ALERT|SSH brute force attempt
Failed password.*ssh|MEDIUM|COUNT|SSH failed password
Invalid user.*ssh|HIGH|ALERT|SSH invalid user attempt
ROOT LOGIN REFUSED.*ssh|HIGH|ALERT|SSH root login attempt

# SSH scanning
Connection closed.*ssh.*preauth|LOW|COUNT|SSH connection scanning
Connection reset.*ssh|LOW|COUNT|SSH connection reset
Received disconnect.*ssh|MEDIUM|COUNT|SSH premature disconnect

# Suspicious SSH activity
User.*not allowed.*ssh|HIGH|ALERT|SSH user not allowed
Maximum authentication attempts.*ssh|HIGH|ALERT|SSH max auth attempts
Timeout.*ssh|MEDIUM|COUNT|SSH timeout

# SSH protocol violations
Protocol.*ssh|HIGH|ALERT|SSH protocol violation
Bad protocol version.*ssh|HIGH|ALERT|SSH bad protocol version
SSH_RULES_EOF

    # Network Attack Detection Rules
    cat << NET_RULES_EOF | sudo tee "$IDS_RULES_DIR/network_attacks.rules"
# Network Attack Detection Rules

# Port scanning
nmap|HIGH|ALERT|Nmap scan detected
masscan|HIGH|ALERT|Masscan detected
SYN flood|HIGH|ALERT|SYN flood attack
Port.*scan|MEDIUM|ALERT|Port scan detected

# DDoS attacks
DDOS|HIGH|BLOCK|DDoS attack detected
flood|HIGH|ALERT|Flood attack detected
amplification|HIGH|ALERT|Amplification attack

# Network intrusion
backdoor|HIGH|BLOCK|Backdoor detected
trojan|HIGH|BLOCK|Trojan detected
botnet|HIGH|BLOCK|Botnet activity
malware|HIGH|BLOCK|Malware detected

# Protocol attacks
DNS.*poison|HIGH|ALERT|DNS poisoning attempt
ARP.*spoof|HIGH|ALERT|ARP spoofing detected
ICMP.*flood|MEDIUM|ALERT|ICMP flood detected
NET_RULES_EOF

    # Web Attack Detection Rules
    cat << WEB_RULES_EOF | sudo tee "$IDS_RULES_DIR/web_attacks.rules"
# Web Attack Detection Rules

# SQL Injection
union.*select|HIGH|ALERT|SQL injection attempt
drop.*table|HIGH|ALERT|SQL injection (DROP)
insert.*into|MEDIUM|COUNT|SQL injection (INSERT)
update.*set|MEDIUM|COUNT|SQL injection (UPDATE)

# XSS attacks
<script|HIGH|ALERT|XSS attack attempt
javascript:|HIGH|ALERT|XSS javascript injection
eval\(|HIGH|ALERT|XSS eval injection
alert\(|MEDIUM|COUNT|XSS alert injection

# Directory traversal
\.\./|HIGH|ALERT|Directory traversal attempt
etc/passwd|HIGH|ALERT|System file access attempt
etc/shadow|HIGH|ALERT|Shadow file access attempt

# Command injection
;.*rm|HIGH|ALERT|Command injection (rm)
;.*cat|MEDIUM|COUNT|Command injection (cat)
;.*wget|HIGH|ALERT|Command injection (wget)
;.*curl|HIGH|ALERT|Command injection (curl)
WEB_RULES_EOF

    # System Attack Detection Rules
    cat << SYS_RULES_EOF | sudo tee "$IDS_RULES_DIR/system_attacks.rules"
# System Attack Detection Rules

# Privilege escalation
sudo.*passwd|HIGH|ALERT|Sudo password change attempt
su.*root|HIGH|ALERT|Root escalation attempt
chmod.*777|MEDIUM|COUNT|Dangerous permissions change
chown.*root|HIGH|ALERT|Root ownership change

# File system attacks
rm.*rf|HIGH|ALERT|Dangerous file deletion
find.*exec|MEDIUM|COUNT|Find command execution
crontab.*e|MEDIUM|COUNT|Crontab modification

# Process injection
ptrace|HIGH|ALERT|Process injection attempt
gdb.*attach|HIGH|ALERT|Debugger attachment
strace.*p|MEDIUM|COUNT|Process tracing

# Resource exhaustion
fork.*bomb|HIGH|BLOCK|Fork bomb detected
memory.*exhaustion|HIGH|ALERT|Memory exhaustion
CPU.*100|MEDIUM|COUNT|High CPU usage
SYS_RULES_EOF

    log_message "✅ Detection rules created"
}

# Function to create real-time detection engine
create_detection_engine() {
    log_message "⚙️ Creating real-time detection engine..."
    
    cat << DETECTION_ENGINE_EOF > ~/ids_detection_engine.sh
#!/bin/bash

# TwinTower IDS Real-time Detection Engine
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="\$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="\$IDS_LOG_DIR/detection.log"
IDS_STATE_FILE="/var/lib/twintower-ids/state"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
source "\$IDS_CONFIG_DIR/ids.conf"

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$IDS_DETECTION_LOG"
}

alert_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - ALERT: \$1" | tee -a "\$IDS_ALERT_LOG"
}

# Function to check if IP is whitelisted
is_whitelisted() {
    local ip="\$1"
    local whitelist_file="\$IDS_CONFIG_DIR/whitelist.conf"
    
    if [ -f "\$whitelist_file" ]; then
        # Simple IP matching (in production use more sophisticated matching)
        if grep -q "\$ip" "\$whitelist_file"; then
            return 0
        fi
        
        # Check network ranges (simplified)
        if [[ "\$ip" =~ ^192\.168\.1\. ]] && grep -q "192.168.1.0/24" "\$whitelist_file"; then
            return 0
        fi
        
        if [[ "\$ip" =~ ^100\.64\. ]] && grep -q "100.64.0.0/10" "\$whitelist_file"; then
            return 0
        fi
    fi
    
    return 1
}

# Function to process detection rule
process_rule() {
    local rule="\$1"
    local log_line="\$2"
    local source_ip="\$3"
    
    # Parse rule: PATTERN|SEVERITY|ACTION|DESCRIPTION
    local pattern=\$(echo "\$rule" | cut -d'|' -f1)
    local severity=\$(echo "\$rule" | cut -d'|' -f2)
    local action=\$(echo "\$rule" | cut -d'|' -f3)
    local description=\$(echo "\$rule" | cut -d'|' -f4)
    
    # Check if log line matches pattern
    if echo "\$log_line" | grep -qi "\$pattern"; then
        # Skip if whitelisted
        if is_whitelisted "\$source_ip"; then
            return 0
        fi
        
        # Execute action based on severity and configuration
        case "\$action" in
            "ALERT")
                alert_message "[\$severity] \$description - IP: \$source_ip"
                if [ "\$IDS_REALTIME_ALERTS" = "true" ]; then
                    send_alert "\$severity" "\$description" "\$source_ip"
                fi
                ;;
            "BLOCK")
                alert_message "[\$severity] BLOCKING - \$description - IP: \$source_ip"
                if [ "\$IDS_AUTO_BLOCK" = "true" ]; then
                    block_ip "\$source_ip" "\$description"
                fi
                ;;
            "COUNT")
                increment_counter "\$source_ip" "\$description"
                ;;
        esac
    fi
}

# Function to extract source IP from log line
extract_source_ip() {
    local log_line="\$1"
    
    # Extract IP using various patterns
    local ip=\$(echo "\$log_line" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    
    if [ -z "\$ip" ]; then
        ip="unknown"
    fi
    
    echo "\$ip"
}

# Function to increment counter for repeated events
increment_counter() {
    local ip="\$1"
    local event="\$2"
    
    local counter_file="/var/lib/twintower-ids/counters/\$ip"
    sudo mkdir -p "/var/lib/twintower-ids/counters"
    
    local count=1
    if [ -f "\$counter_file" ]; then
        count=\$(cat "\$counter_file")
        count=\$((count + 1))
    fi
    
    echo "\$count" > "\$counter_file"
    
    # Check if threshold exceeded
    if [ "\$count" -ge "\$IDS_ALERT_THRESHOLD" ]; then
        alert_message "[THRESHOLD] IP \$ip exceeded threshold (\$count events) - \$event"
        
        if [ "\$count" -ge "\$IDS_BLOCK_THRESHOLD" ] && [ "\$IDS_AUTO_BLOCK" = "true" ]; then
            block_ip "\$ip" "Threshold exceeded: \$event"
        fi
    fi
}

# Function to block IP address
block_ip() {
    local ip="\$1"
    local reason="\$2"
    
    log_message "🚫 Blocking IP: \$ip - Reason: \$reason"
    
    # Block using UFW
    sudo ufw deny from "\$ip" comment "IDS Block: \$reason"
    
    # Schedule unblock
    if [ "\$IDS_BLOCK_DURATION" -gt 0 ]; then
        echo "sudo ufw delete deny from \$ip" | at now + "\$IDS_BLOCK_DURATION seconds" 2>/dev/null || true
    fi
}

# Function to send alert
send_alert() {
    local severity="\$1"
    local description="\$2"
    local source_ip="\$3"
    
    # Log alert
    log_message "🚨 ALERT [\$severity]: \$description from \$source_ip"
    
    # Send email alert if configured
    if [ "\$IDS_EMAIL_ALERTS" = "true" ] && [ -n "\$IDS_EMAIL_RECIPIENT" ]; then
        echo "IDS Alert: \$description from \$source_ip" | mail -s "TwinTower IDS Alert [\$severity]" "\$IDS_EMAIL_RECIPIENT"
    fi
    
    # Send webhook alert if configured
    if [ "\$IDS_WEBHOOK_ALERTS" = "true" ] && [ -n "\$IDS_WEBHOOK_URL" ]; then
        curl -X POST -H "Content-Type: application/json" \
            -d "{\"alert\":\"TwinTower IDS Alert\",\"severity\":\"\$severity\",\"description\":\"\$description\",\"source_ip\":\"\$source_ip\"}" \
            "\$IDS_WEBHOOK_URL" 2>/dev/null || true
    fi
}

# Function to monitor log files
monitor_logs() {
    log_message "🔍 Starting real-time log monitoring..."
    
    # Monitor multiple log files
    tail -f /var/log/auth.log /var/log/syslog /var/log/ufw.log /var/log/nginx/access.log 2>/dev/null | \
    while read log_line; do
        # Extract source IP
        source_ip=\$(extract_source_ip "\$log_line")
        
        # Process against all rule files
        for rule_file in "\$IDS_RULES_DIR"/*.rules; do
            if [ -f "\$rule_file" ]; then
                while IFS= read -r rule; do
                    # Skip comments and empty lines
                    if [[ "\$rule" =~ ^#.*\$ ]] || [[ -z "\$rule" ]]; then
                        continue
                    fi
                    
                    process_rule "\$rule" "\$log_line" "\$source_ip"
                done < "\$rule_file"
            fi
        done
    done
}

# Function to generate IDS report
generate_ids_report() {
    local report_file="/tmp/ids_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower IDS Report
==================
Generated: \$(date)
Tower: \$(hostname)

IDS Configuration:
-----------------
Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")
Mode: \$IDS_MODE
Sensitivity: \$IDS_SENSITIVITY
Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "ENABLED" || echo "DISABLED")

Detection Statistics (Last 24 hours):
------------------------------------
Total Alerts: \$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
High Severity: \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
Medium Severity: \$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
Low Severity: \$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")

Blocked IPs:
-----------
\$(sudo ufw status | grep "IDS Block" || echo "No IPs currently blocked")

Top Alert Sources:
-----------------
\$(grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -10)

Recent High-Priority Alerts:
----------------------------
\$(grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -10)

Rule Effectiveness:
------------------
SSH Attacks: \$(grep -c "SSH.*attempt" "\$IDS_ALERT_LOG" || echo "0")
Network Attacks: \$(grep -c "scan.*detected" "\$IDS_ALERT_LOG" || echo "0")
Web Attacks: \$(grep -c "injection.*attempt" "\$IDS_ALERT_LOG" || echo "0")
System Attacks: \$(grep -c "escalation.*attempt" "\$IDS_ALERT_LOG" || echo "0")

REPORT_EOF

    log_message "📋 IDS report generated: \$report_file"
    echo "\$report_file"
}

# Function to start IDS daemon
start_ids_daemon() {
    log_message "🚀 Starting IDS daemon..."
    
    # Create state directory
    sudo mkdir -p /var/lib/twintower-ids/counters
    
    # Start monitoring
    monitor_logs
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_ids_daemon
        ;;
    "test")
        # Test detection rules
        echo "Testing IDS rules..."
        echo "authentication failure ssh" | while read line; do
            source_ip=\$(extract_source_ip "\$line")
            process_rule "authentication failure.*ssh|HIGH|ALERT|SSH brute force test" "\$line" "\$source_ip"
        done
        ;;
    "report")
        generate_ids_report
        ;;
    "status")
        echo "IDS Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")"
        echo "Active Rules: \$(find "\$IDS_RULES_DIR" -name "*.rules" | wc -l)"
        echo "Recent Alerts: \$(tail -n 5 "\$IDS_ALERT_LOG" | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <daemon|test|report|status>"
        exit 1
        ;;
esac
DETECTION_ENGINE_EOF

    chmod +x ~/ids_detection_engine.sh
    
    log_message "✅ Detection engine created"
}

# Function to create IDS management dashboard
create_ids_dashboard() {
    log_message "📊 Creating IDS management dashboard..."
    
    cat << IDS_DASHBOARD_EOF > ~/ids_dashboard.sh
#!/bin/bash

# TwinTower IDS Management Dashboard
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_ALERT_LOG="/var/log/twintower-ids/alerts.log"
IDS_DETECTION_LOG="/var/log/twintower-ids/detection.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
if [ -f "\$IDS_CONFIG_DIR/ids.conf" ]; then
    source "\$IDS_CONFIG_DIR/ids.conf"
fi

clear
echo -e "\${BLUE}🚨 TwinTower IDS Management Dashboard\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# IDS Status
echo -e "\${YELLOW}🛡️ IDS Status\${NC}"
echo "-------------"
if [ "\$IDS_ENABLED" = "true" ]; then
    echo -e "IDS Status: \${GREEN}✅ ENABLED\${NC}"
else
    echo -e "IDS Status: \${RED}❌ DISABLED\${NC}"
fi

echo -e "Mode: \${GREEN}\$IDS_MODE\${NC}"
echo -e "Sensitivity: \${GREEN}\$IDS_SENSITIVITY\${NC}"
echo -e "Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "\${GREEN}✅ ENABLED\${NC}" || echo "\${RED}❌ DISABLED\${NC}")"
echo

# Detection Statistics
echo -e "\${YELLOW}📊 Detection Statistics (Last 24 hours)\${NC}"
echo "--------------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    TOTAL_ALERTS=\$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
    HIGH_ALERTS=\$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
    MEDIUM_ALERTS=\$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
    LOW_ALERTS=\$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")
    
    echo -e "Total Alerts: \${BLUE}\$TOTAL_ALERTS\${NC}"
    echo -e "High Severity: \${RED}\$HIGH_ALERTS\${NC}"
    echo -e "Medium Severity: \${YELLOW}\$MEDIUM_ALERTS\${NC}"
    echo -e "Low Severity: \${GREEN}\$LOW_ALERTS\${NC}"
else
    echo -e "No alert data available"
fi
echo

# Active Rules
echo -e "\${YELLOW}📋 Active Rules\${NC}"
echo "---------------"
if [ -d "\$IDS_CONFIG_DIR/rules" ]; then
    RULE_COUNT=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" -exec wc -l {} + | tail -1 | awk '{print \$1}' || echo "0")
    RULE_FILES=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" | wc -l)
    echo -e "Rule Files: \${GREEN}\$RULE_FILES\${NC}"
    echo -e "Total Rules: \${GREEN}\$RULE_COUNT\${NC}"
    
    for rule_file in "\$IDS_CONFIG_DIR/rules"/*.rules; do
        if [ -f "\$rule_file" ]; then
            rule_name=\$(basename "\$rule_file" .rules)
            rule_count=\$(grep -c "^[^#]" "\$rule_file" || echo "0")
            echo -e "  \${GREEN}•\${NC} \$rule_name: \$rule_count rules"
        fi
    done
else
    echo -e "No rules configured"
fi
echo

# Recent Alerts
echo -e "\${YELLOW}🚨 Recent High-Priority Alerts\${NC}"
echo "------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -5 | while read line; do
        timestamp=\$(echo "\$line" | awk '{print \$1, \$2, \$3}')
        alert_msg=\$(echo "\$line" | cut -d'-' -f3-)
        echo -e "  \${RED}⚠️\${NC} \$timestamp:\$alert_msg"
    done
    
    if [ \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG") -eq 0 ]; then
        echo -e "  \${GREEN}✅ No high-priority alerts\${NC}"
    fi
else
    echo -e "No alert data available"
fi
echo

# Blocked IPs
echo -e "\${YELLOW}🚫 Blocked IPs\${NC}"
echo "-------------"
BLOCKED_IPS=\$(sudo ufw status | grep "IDS Block" | wc -l)
if [ \$BLOCKED_IPS -gt 0 ]; then
    echo -e "Currently Blocked: \${RED}\$BLOCKED_IPS\${NC}"
    sudo ufw status | grep "IDS Block" | head -5 | while read line; do
        echo -e "  \${RED}🔒\${NC} \$line"
    done
else
    echo -e "Currently Blocked: \${GREEN}0\${NC}"
fi
echo

# Top Alert Sources
echo -e "\${YELLOW}📈 Top Alert Sources\${NC}"
echo "--------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    echo "Top 5 IPs by alert count:"
    grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -5 | while read count ip; do
        echo -e "  \${RED}\$ip\${NC}: \$count alerts"
    done
else
    echo -e "No alert data available"
fi
echo

# System Health
echo -e "\${YELLOW}💓 System Health\${NC}"
echo "----------------"
IDS_PROCESS=\$(pgrep -f "ids_detection_engine.sh" | wc -l)
if [ \$IDS_PROCESS -gt 0 ]; then
    echo -e "Detection Engine: \${GREEN}✅ Running\${NC}"
else
    echo -e "Detection Engine: \${RED}❌ Stopped\${NC}"
fi

LOG_SIZE=\$(du -h "\$IDS_ALERT_LOG" 2>/dev/null | cut -f1 || echo "0")
echo -e "Alert Log Size: \${GREEN}\$LOG_SIZE\${NC}"

DISK_USAGE=\$(df -h /var/log | tail -1 | awk '{print \$5}')
echo -e "Log Disk Usage: \${GREEN}\$DISK_USAGE\${NC}"
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Start IDS: ./ids_detection_engine.sh daemon"
echo "2. View alerts: tail -f \$IDS_ALERT_LOG"
echo "3. Generate report: ./ids_detection_engine.sh report"
echo "4. Test rules: ./ids_detection_engine.sh test"
echo "5. View blocked IPs: sudo ufw status | grep 'IDS Block'"

echo
echo -e "\${BLUE}====================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
IDS_DASHBOARD_EOF

    chmod +x ~/ids_dashboard.sh
    
    log_message "✅ IDS dashboard created"
}

# Function to create IDS service
create_ids_service() {
    log_message "⚙️ Creating IDS systemd service..."
    
    cat << IDS_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-ids.service
[Unit]
Description=TwinTower Intrusion Detection System
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/ids_detection_engine.sh daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
IDS_SERVICE_EOF

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-ids.service
    
    log_message "✅ IDS service created"
}

# Function to test IDS system
test_ids_system() {
    log_message "🧪 Testing IDS system..."
    
    cat << IDS_TEST_EOF > ~/test_ids_system.sh
#!/bin/bash

# TwinTower IDS System Test
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower IDS System Test\${NC}"
echo -e "\${BLUE}===========================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test IDS configuration
echo -e "\${YELLOW}🔧 Testing IDS Configuration\${NC}"
echo "----------------------------"
run_test "IDS config directory exists" "[ -d '\$IDS_CONFIG_DIR' ]"
run_test "IDS rules directory exists" "[ -d '\$IDS_RULES_DIR' ]"
run_test "IDS configuration file exists" "[ -f '\$IDS_CONFIG_DIR/ids.conf' ]"
run_test "IDS whitelist file exists" "[ -f '\$IDS_CONFIG_DIR/whitelist.conf' ]"

# Test detection rules
echo -e "\${YELLOW}📋 Testing Detection Rules\${NC}"
echo "--------------------------"
run_test "SSH attack rules exist" "[ -f '\$IDS_RULES_DIR/ssh_attacks.rules' ]"
run_test "Network attack rules exist" "[ -f '\$IDS_RULES_DIR/network_attacks.rules' ]"
run_test "Web attack rules exist" "[ -f '\$IDS_RULES_DIR/web_attacks.rules' ]"
run_test "System attack rules exist" "[ -f '\$IDS_RULES_DIR/system_attacks.rules' ]"

# Test IDS components
echo -e "\${YELLOW}# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access policies..."
    
    # Internal Network Policy
    cat << INTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/internal-network.json"
{
    "policy_name": "InternalNetwork",
    "description": "Internal network access policy",
    "version": "1.0",
    "priority": 250,
    "conditions": {
        "source_networks": ["192.168.1.0/24", "172.16.0.0/12", "10.0.0.0/8"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp", "udp", "icmp"],
        "encryption_required": false,
        "authentication_required": true
    },
    "permissions": {
        "ssh_access": true,
        "web_access": true,
        "api_access": true,
        "file_access": true
    },
    "restrictions": {
        "bandwidth_limit": "1Gbps",
        "connection_limit": 100,
        "rate_limit": "moderate"
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": false
    }
}
INTERNAL_NET_EOF

    # External Network Policy
    cat << EXTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/external-network.json"
{
    "policy_name": "ExternalNetwork",
    "description": "External network access policy (high security)",
    "version": "1.0",
    "priority": 500,
    "conditions": {
        "source_networks": ["0.0.0.0/0"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp"],
        "encryption_required": true,
        "authentication_required": true,
        "vpn_required": true
    },
    "permissions": {
        "ssh_access": false,
        "web_access": true,
        "api_access": false,
        "file_access": false
    },
    "restrictions": {
        "bandwidth_limit": "10Mbps",
        "connection_limit": 5,
        "rate_limit": "strict",
        "geolocation_required": true,
        "time_limited": true
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": true,
        "threat_intelligence": true
    }
}
EXTERNAL_NET_EOF

    log_message "✅ Network-based policies created"
}

# Function to create zero-trust enforcement engine
create_zt_enforcement() {
    log_message "⚙️ Creating zero-trust enforcement engine..."
    
    cat << ZT_ENGINE_EOF > ~/zt_enforcement_engine.sh
#!/bin/bash

# TwinTower Zero-Trust Enforcement Engine
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_LOG_FILE"
}

audit_log() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_AUDIT_LOG"
}

# Function to validate user access
validate_user_access() {
    local user="\$1"
    local source_ip="\$2"
    local requested_service="\$3"
    local auth_method="\$4"
    
    log_message "🔍 Validating access for user: \$user from \$source_ip"
    
    # Check if user exists
    if ! id "\$user" &>/dev/null; then
        audit_log "DENY: User \$user does not exist"
        return 1
    fi
    
    # Load and evaluate policies
    local policy_result=0
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            if evaluate_policy "\$policy_file" "\$user" "\$source_ip" "\$requested_service" "\$auth_method"; then
                policy_result=1
                break
            fi
        fi
    done
    
    if [ \$policy_result -eq 1 ]; then
        audit_log "ALLOW: User \$user access granted for \$requested_service"
        create_session "\$user" "\$source_ip" "\$requested_service"
        return 0
    else
        audit_log "DENY: User \$user access denied for \$requested_service"
        return 1
    fi
}

# Function to evaluate policy
evaluate_policy() {
    local policy_file="\$1"
    local user="\$2"
    local source_ip="\$3"
    local requested_service="\$4"
    local auth_method="\$5"
    
    # Parse JSON policy (simplified - in production use jq)
    local policy_name=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
    
    log_message "📋 Evaluating policy: \$policy_name"
    
    # Check user conditions
    if grep -q '"users"' "\$policy_file"; then
        local users=\$(grep '"users"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$users" == *"\$user"* ]]; then
            log_message "✅ User \$user matches policy \$policy_name"
        else
            log_message "❌ User \$user does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check network conditions
    if grep -q '"source_networks"' "\$policy_file"; then
        local networks=\$(grep '"source_networks"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if check_network_match "\$source_ip" "\$networks"; then
            log_message "✅ Source IP \$source_ip matches policy \$policy_name"
        else
            log_message "❌ Source IP \$source_ip does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check time restrictions
    if grep -q '"time_restrictions"' "\$policy_file"; then
        if check_time_restrictions "\$policy_file"; then
            log_message "✅ Time restrictions satisfied for policy \$policy_name"
        else
            log_message "❌ Time restrictions not satisfied for policy \$policy_name"
            return 1
        fi
    fi
    
    # Check service permissions
    if grep -q '"\$requested_service"' "\$policy_file"; then
        local service_allowed=\$(grep '"\$requested_service"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
        if [[ "\$service_allowed" == "true" ]]; then
            log_message "✅ Service \$requested_service allowed in policy \$policy_name"
            return 0
        else
            log_message "❌ Service \$requested_service not allowed in policy \$policy_name"
            return 1
        fi
    fi
    
    return 0
}

# Function to check network match
check_network_match() {
    local source_ip="\$1"
    local networks="\$2"
    
    # Simple network matching (in production use ipcalc or similar)
    if [[ "\$networks" == *"100.64.0.0/10"* ]] && [[ "\$source_ip" == 100.64.* ]]; then
        return 0
    elif [[ "\$networks" == *"192.168.1.0/24"* ]] && [[ "\$source_ip" == 192.168.1.* ]]; then
        return 0
    elif [[ "\$networks" == *"0.0.0.0/0"* ]]; then
        return 0
    fi
    
    return 1
}

# Function to check time restrictions
check_time_restrictions() {
    local policy_file="\$1"
    
    local current_hour=\$(date +%H)
    local current_day=\$(date +%A | tr '[:upper:]' '[:lower:]')
    
    # Check allowed hours (simplified)
    if grep -q '"allowed_hours"' "\$policy_file"; then
        local allowed_hours=\$(grep '"allowed_hours"' "\$policy_file" | cut -d'"' -f4)
        local start_hour=\$(echo "\$allowed_hours" | cut -d'-' -f1 | cut -d':' -f1)
        local end_hour=\$(echo "\$allowed_hours" | cut -d'-' -f2 | cut -d':' -f1)
        
        if [ "\$current_hour" -ge "\$start_hour" ] && [ "\$current_hour" -le "\$end_hour" ]; then
            return 0
        else
            return 1
        fi
    fi
    
    # Check allowed days (simplified)
    if grep -q '"allowed_days"' "\$policy_file"; then
        local allowed_days=\$(grep '"allowed_days"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$allowed_days" == *"\$current_day"* ]]; then
            return 0
        else
            return 1
        fi
    fi
    
    return 0
}

# Function to create session
create_session() {
    local user="\$1"
    local source_ip="\$2"
    local service="\$3"
    
    sudo mkdir -p "\$ZT_SESSION_DIR"
    
    local session_id=\$(date +%s)_\$(echo "\$user\$source_ip" | md5sum | cut -d' ' -f1 | head -c 8)
    local session_file="\$ZT_SESSION_DIR/\$session_id.session"
    
    cat > "\$session_file" << SESSION_EOF
{
    "session_id": "\$session_id",
    "user": "\$user",
    "source_ip": "\$source_ip",
    "service": "\$service",
    "start_time": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "last_activity": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "status": "active"
}
SESSION_EOF

    log_message "✅ Session created: \$session_id for user \$user"
}

# Function to monitor active sessions
monitor_sessions() {
    log_message "📊 Monitoring active sessions..."
    
    if [ -d "\$ZT_SESSION_DIR" ]; then
        local active_sessions=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
        log_message "Active sessions: \$active_sessions"
        
        # Check for expired sessions
        for session_file in "\$ZT_SESSION_DIR"/*.session; do
            if [ -f "\$session_file" ]; then
                local session_id=\$(basename "\$session_file" .session)
                local start_time=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
                
                # Check if session is older than 1 hour (3600 seconds)
                local current_time=\$(date +%s)
                local session_time=\$(date -d "\$start_time" +%s)
                local age=\$((current_time - session_time))
                
                if [ \$age -gt 3600 ]; then
                    log_message "⏰ Expiring session: \$session_id"
                    rm -f "\$session_file"
                fi
            fi
        done
    fi
}

# Function to generate compliance report
generate_compliance_report() {
    local report_file="/tmp/zt_compliance_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Zero-Trust Compliance Report
====================================
Generated: \$(date)
Tower: \$(hostname)

Policy Compliance:
-----------------
Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
Enforcement Status: \$(grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf" && echo "ENABLED" || echo "DISABLED")

Access Statistics (Last 24 hours):
---------------------------------
Total Access Attempts: \$(grep -c "Validating access" "\$ZT_LOG_FILE" || echo "0")
Successful Authentications: \$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
Denied Access Attempts: \$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")

Active Sessions:
---------------
Current Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)

Recent Security Events:
----------------------
\$(tail -n 20 "\$ZT_AUDIT_LOG" 2>/dev/null || echo "No recent events")

Policy Violations:
-----------------
\$(grep "DENY:" "\$ZT_AUDIT_LOG" | tail -10 || echo "No recent violations")

Recommendations:
---------------
\$([ \$(grep -c "DENY:" "\$ZT_AUDIT_LOG") -gt 10 ] && echo "High number of access denials - review policies" || echo "Access patterns appear normal")

REPORT_EOF

    log_message "📋 Compliance report generated: \$report_file"
    echo "\$report_file"
}

# Main execution
case "\${1:-monitor}" in
    "validate")
        validate_user_access "\$2" "\$3" "\$4" "\$5"
        ;;
    "monitor")
        log_message "🚀 Starting zero-trust monitoring..."
        while true; do
            monitor_sessions
            sleep 300
        done
        ;;
    "report")
        generate_compliance_report
        ;;
    "status")
        echo "Zero-Trust Status:"
        echo "=================="
        echo "Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)"
        echo "Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)"
        echo "Recent Events: \$(tail -n 5 "\$ZT_AUDIT_LOG" 2>/dev/null | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <validate|monitor|report|status>"
        echo "  validate <user> <source_ip> <service> <auth_method>"
        exit 1
        ;;
esac
ZT_ENGINE_EOF

    chmod +x ~/zt_enforcement_engine.sh
    
    log_message "✅ Zero-trust enforcement engine created"
}

# Function to create zero-trust monitoring dashboard
create_zt_dashboard() {
    log_message "📊 Creating zero-trust monitoring dashboard..."
    
    cat << ZT_DASHBOARD_EOF > ~/zt_dashboard.sh
#!/bin/bash

# TwinTower Zero-Trust Dashboard
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔒 TwinTower Zero-Trust Dashboard\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Zero-Trust Status
echo -e "\${YELLOW}🛡️ Zero-Trust Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_CONFIG_DIR/zero-trust.conf" ]; then
    if grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf"; then
        echo -e "Zero-Trust: \${GREEN}✅ ENABLED\${NC}"
    else
        echo -e "Zero-Trust: \${RED}❌ DISABLED\${NC}"
    fi
else
    echo -e "Zero-Trust: \${RED}❌ NOT CONFIGURED\${NC}"
fi

# Policy Status
POLICY_COUNT=\$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
echo -e "Active Policies: \${GREEN}\$POLICY_COUNT\${NC}"

# Session Status
if [ -d "\$ZT_SESSION_DIR" ]; then
    SESSION_COUNT=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
    echo -e "Active Sessions: \${GREEN}\$SESSION_COUNT\${NC}"
else
    echo -e "Active Sessions: \${YELLOW}0\${NC}"
fi
echo

# Access Statistics
echo -e "\${YELLOW}📊 Access Statistics (Last 24 hours)\${NC}"
echo "-----------------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    ALLOW_COUNT=\$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
    DENY_COUNT=\$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")
    TOTAL_COUNT=\$((ALLOW_COUNT + DENY_COUNT))
    
    echo -e "Total Requests: \${BLUE}\$TOTAL_COUNT\${NC}"
    echo -e "Allowed: \${GREEN}\$ALLOW_COUNT\${NC}"
    echo -e "Denied: \${RED}\$DENY_COUNT\${NC}"
    
    if [ \$TOTAL_COUNT -gt 0 ]; then
        SUCCESS_RATE=\$(echo "scale=2; \$ALLOW_COUNT * 100 / \$TOTAL_COUNT" | bc -l 2>/dev/null || echo "0")
        echo -e "Success Rate: \${GREEN}\$SUCCESS_RATE%\${NC}"
    fi
else
    echo -e "No audit data available"
fi
echo

# Active Policies
echo -e "\${YELLOW}📋 Active Policies\${NC}"
echo "------------------"
if [ -d "\$ZT_POLICIES_DIR" ]; then
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            POLICY_NAME=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
            PRIORITY=\$(grep '"priority"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
            echo -e "  \${GREEN}•\${NC} \$POLICY_NAME (Priority: \$PRIORITY)"
        fi
    done
else
    echo -e "No policies configured"
fi
echo

# Recent Events
echo -e "\${YELLOW}🔍 Recent Security Events\${NC}"
echo "-------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    tail -n 5 "\$ZT_AUDIT_LOG" | while read line; do
        if [[ "\$line" == *"ALLOW:"* ]]; then
            echo -e "\${GREEN}✅ \$line\${NC}"
        elif [[ "\$line" == *"DENY:"* ]]; then
            echo -e "\${RED}❌ \$line\${NC}"
        else
            echo -e "\${BLUE}ℹ️  \$line\${NC}"
        fi
    done
else
    echo -e "No recent events"
fi
echo

# Active Sessions
echo -e "\${YELLOW}👥 Active Sessions\${NC}"
echo "------------------"
if [ -d "\$ZT_SESSION_DIR" ]; then
    for session_file in "\$ZT_SESSION_DIR"/*.session; do
        if [ -f "\$session_file" ]; then
            USER=\$(grep '"user"' "\$session_file" | cut -d'"' -f4)
            SOURCE_IP=\$(grep '"source_ip"' "\$session_file" | cut -d'"' -f4)
            SERVICE=\$(grep '"service"' "\$session_file" | cut -d'"' -f4)
            START_TIME=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
            echo -e "  \${GREEN}•\${NC} \$USER from \$SOURCE_IP (\$SERVICE) - \$START_TIME"
        fi
    done
    
    if [ \$SESSION_COUNT -eq 0 ]; then
        echo -e "No active sessions"
    fi
else
    echo -e "No session data available"
fi
echo

# Compliance Status
echo -e "\${YELLOW}📊 Compliance Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    RECENT_VIOLATIONS=\$(grep "DENY:" "\$ZT_AUDIT_LOG" | grep "\$(date '+%Y-%m-%d')" | wc -l)
    
    if [ \$RECENT_VIOLATIONS -eq 0 ]; then
        echo -e "Compliance Status: \${GREEN}✅ GOOD\${NC}"
    elif [ \$RECENT_VIOLATIONS -lt 5 ]; then
        echo -e "Compliance Status: \${YELLOW}⚠️  MODERATE\${NC}"
    else
        echo -e "Compliance Status: \${RED}❌ NEEDS ATTENTION\${NC}"
    fi
    
    echo -e "Today's Violations: \${RED}\$RECENT_VIOLATIONS\${NC}"
else
    echo -e "Compliance Status: \${YELLOW}⚠️  NO DATA\${NC}"
fi
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View policies: ls \$ZT_POLICIES_DIR/"
echo "2. Monitor sessions: ./zt_enforcement_engine.sh monitor"
echo "3. Generate report: ./zt_enforcement_engine.sh report"
echo "4. Check status: ./zt_enforcement_engine.sh status"

echo
echo -e "\${BLUE}=================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
ZT_DASHBOARD_EOF

    chmod +x ~/zt_dashboard.sh
    
    log_message "✅ Zero-trust monitoring dashboard created"
}

# Function to create zero-trust testing suite
create_zt_testing() {
    log_message "🧪 Creating zero-trust testing suite..."
    
    cat << ZT_TEST_EOF > ~/test_zero_trust.sh
#!/bin/bash

# TwinTower Zero-Trust Testing Suite
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Zero-Trust Testing Suite\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zero-trust configuration
echo -e "\${YELLOW}🔧 Testing Zero-Trust Configuration\${NC}"
echo "-----------------------------------"
run_test "ZT config directory exists" "[ -d '\$ZT_CONFIG_DIR' ]"
run_test "ZT policies directory exists" "[ -d '\$ZT_POLICIES_DIR' ]"
run_test "ZT configuration file exists" "[ -f '\$ZT_CONFIG_DIR/zero-trust.conf' ]"

# Test policy files
echo -e "\${YELLOW}📋 Testing Policy Files\${NC}"
echo "----------------------"
run_test "Admin users policy exists" "[ -f '\$ZT_POLICIES_DIR/admin-users.json' ]"
run_test "Standard users policy exists" "[ -f '\$ZT_POLICIES_DIR/standard-users.json' ]"
run_test "Service accounts policy exists" "[ -f '\$ZT_POLICIES_DIR/service-accounts.json' ]"
run_test "Trusted devices policy exists" "[ -f '\$ZT_POLICIES_DIR/trusted-devices.json' ]"
run_test "BYOD policy exists" "[ -f '\$ZT_POLICIES_DIR/byod-devices.json' ]"

# Test enforcement engine
echo -e "\${YELLOW}⚙️ Testing Enforcement Engine\${NC}"
echo "-----------------------------"
run_test "Enforcement engine exists" "[ -f '\$HOME/zt_enforcement_engine.sh' ]"
run_test "Enforcement engine executable" "[ -x '\$HOME/zt_enforcement_engine.sh' ]"
run_test "ZT dashboard exists" "[ -f '\$HOME/zt_dashboard.sh' ]"

# Test log files
echo -e "\${YELLOW}📊 Testing Logging\${NC}"
echo "------------------"
run_test "ZT log file exists" "[ -f '/var/log/zero-trust.log' ]"
run_test "ZT audit log exists" "[ -f '/var/log/zero-trust-audit.log' ]"

# Test policy validation
echo -e "\${YELLOW}🔍 Testing Policy Validation\${NC}"
echo "----------------------------"
for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
    if [ -f "\$policy_file" ]; then
        policy_name=\$(basename "\$policy_file" .json)
        run_test "Policy \$policy_name is valid JSON" "python3 -m json.tool '\$policy_file' > /dev/null"
    fi
done

# Test access scenarios
echo -e "\${YELLOW}🚪 Testing Access Scenarios\${NC}"
echo "---------------------------"
run_test "Admin access validation" "./zt_enforcement_engine.sh validate ubuntu 100.64.0.1 ssh_access publickey"
run_test "External access blocking" "! ./zt_enforcement_engine.sh validate hacker 1.2.3.4 ssh_access password"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zero-trust tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
ZT_TEST_EOF

    chmod +x ~/test_zero_trust.sh
    
    log_message "✅ Zero-trust testing suite created"
}

# Main execution
main() {
    echo -e "${BLUE}🔒 TwinTower Zero-Trust Access Control${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_zero_trust
            create_identity_policies
            create_device_policies
            create_network_policies
            create_zt_enforcement
            create_zt_dashboard
            create_zt_testing
            
            # Create session directory
            sudo mkdir -p /var/lib/zero-trust/sessions
            
            echo -e "${GREEN}✅ Zero-trust access control configured!${NC}"
            ;;
        "status")
            ~/zt_dashboard.sh
            ;;
        "test")
            ~/test_zero_trust.sh
            ;;
        "monitor")
            ~/zt_enforcement_engine.sh monitor
            ;;
        "report")
            ~/zt_enforcement_engine.sh report
            ;;
        "validate")
            ~/zt_enforcement_engine.sh validate "$POLICY_NAME" "$3" "$4" "$5"
            ;;
        "policies")
            if [ -d "$ZT_POLICIES_DIR" ]; then
                for policy_file in "$ZT_POLICIES_DIR"/*.json; do
                    if [ -f "$policy_file" ]; then
                        policy_name=$(grep '"policy_name"' "$policy_file" | cut -d'"' -f4)
                        priority=$(grep '"priority"' "$policy_file" | cut -d':' -f2 | tr -d ' ,')
                        echo -e "${BLUE}Policy: $policy_name${NC} (Priority: $priority)"
                    fi
                done
            else
                echo -e "${RED}❌ No policies configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|test|monitor|report|validate|policies> [policy_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/zero_trust_access.sh
```

### **Step 2: Execute Zero-Trust Setup**

```bash
# Setup zero-trust access control
./zero_trust_access.sh setup

# View zero-trust status
./zero_trust_access.sh status

# Test zero-trust implementation
./zero_trust_access.sh test

# Monitor zero-trust enforcement
./zero_trust_access.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## # Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone-based firewall rules..."
    
    # Create UFW application profiles for each zone
    create_ufw_app_profiles
    
    # Apply zone-specific rules
    for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "$zone_file" ]; then
            source "$zone_file"
            apply_zone_rules "$ZONE_NAME" "$zone_file"
        fi
    done
    
    log_message "✅ Zone-based firewall rules implemented"
}

# Function to create UFW application profiles
create_ufw_app_profiles() {
    log_message "📋 Creating UFW application profiles..."
    
    # TwinTower Management Profile
    cat << MGMT_PROFILE_EOF | sudo tee /etc/ufw/applications.d/twintower-management
[TwinTower-Management]
title=TwinTower Management Services
description=Administrative and monitoring interfaces
ports=3000:3099/tcp|6000:6099/tcp

[TwinTower-SSH]
title=TwinTower SSH Services
description=Custom SSH ports for towers
ports=2122,2222,2322/tcp

[TwinTower-GPU]
title=TwinTower GPU Services
description=GPU compute and ML workloads
ports=4000:4099/tcp|8000:8099/tcp

[TwinTower-Docker]
title=TwinTower Docker Services
description=Container orchestration and services
ports=2377/tcp|4789/udp|7946/tcp|7946/udp|5000:5099/tcp
MGMT_PROFILE_EOF

    # Reload UFW application profiles
    sudo ufw app update all
    
    log_message "✅ UFW application profiles created"
}

# Function to apply zone-specific rules
apply_zone_rules() {
    local zone_name="$1"
    local zone_file="$2"
    
    log_message "🔒 Applying rules for zone: $zone_name"
    
    # Source zone configuration
    source "$zone_file"
    
    case "$zone_name" in
        "DMZ")
            # DMZ zone rules - restrictive
            sudo ufw deny from any to any port 22 comment "DMZ: Block SSH"
            sudo ufw allow from any to any port 80 comment "DMZ: Allow HTTP"
            sudo ufw allow from any to any port 443 comment "DMZ: Allow HTTPS"
            sudo ufw limit from any to any port 8080 comment "DMZ: Limit Alt HTTP"
            ;;
        "INTERNAL")
            # Internal zone rules - moderate
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Internal: SSH Access"
                sudo ufw allow from "$network" to any app TwinTower-Docker comment "Internal: Docker Services"
            done
            ;;
        "TRUSTED")
            # Trusted zone rules - permissive
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" comment "Trusted: Full Access"
            done
            ;;
        "MANAGEMENT")
            # Management zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-Management comment "Management: Admin Access"
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Management: SSH Access"
            done
            ;;
        "GPU")
            # GPU zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-GPU comment "GPU: Compute Access"
            done
            ;;
    esac
    
    log_message "✅ Zone rules applied for: $zone_name"
}

# Function to create zone monitoring
create_zone_monitoring() {
    log_message "📊 Creating zone monitoring system..."
    
    cat << ZONE_MONITOR_EOF > ~/zone_monitor.sh
#!/bin/bash

# TwinTower Zone Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-300}"
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/zone-monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor zone traffic
monitor_zone_traffic() {
    local zone_name="\$1"
    local zone_networks="\$2"
    
    log_message "📈 Monitoring traffic for zone: \$zone_name"
    
    # Count connections per zone
    local connection_count=0
    
    IFS=',' read -ra NETWORKS <<< "\$zone_networks"
    for network in "\${NETWORKS[@]}"; do
        # Count active connections from this network
        local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
        connection_count=\$((connection_count + net_connections))
    done
    
    log_message "Zone \$zone_name: \$connection_count active connections"
    
    # Check for anomalies
    if [ "\$connection_count" -gt 100 ]; then
        log_message "🚨 HIGH ALERT: Unusual connection count for zone \$zone_name: \$connection_count"
    fi
}

# Function to analyze zone security events
analyze_zone_security() {
    local zone_name="\$1"
    
    log_message "🔍 Analyzing security events for zone: \$zone_name"
    
    # Check UFW logs for zone-related blocks
    local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$zone_name" || echo "0")
    
    if [ "\$blocked_today" -gt 0 ]; then
        log_message "🛡️ Zone \$zone_name: \$blocked_today blocked attempts today"
    fi
}

# Function to generate zone report
generate_zone_report() {
    local report_file="/tmp/zone_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Network Zone Report
============================
Generated: \$(date)
Tower: \$(hostname)

Zone Status Overview:
--------------------
REPORT_EOF

    # Analyze each zone
    for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "\$zone_file" ]; then
            source "\$zone_file"
            echo "Zone: \$ZONE_NAME (\$ZONE_TRUST_LEVEL trust)" >> "\$report_file"
            echo "  Networks: \$ZONE_NETWORKS" >> "\$report_file"
            echo "  Ports: \$ZONE_PORTS" >> "\$report_file"
            echo "  Status: Active" >> "\$report_file"
            echo "" >> "\$report_file"
        fi
    done
    
    cat >> "\$report_file" << REPORT_EOF

Recent Security Events:
----------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | tail -10)

Zone Traffic Summary:
--------------------
\$(sudo ss -s)

REPORT_EOF

    log_message "📋 Zone report generated: \$report_file"
    echo "\$report_file"
}

# Function to start zone monitoring
start_zone_monitoring() {
    log_message "🚀 Starting zone monitoring daemon..."
    
    while true; do
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                monitor_zone_traffic "\$ZONE_NAME" "\$ZONE_NETWORKS"
                analyze_zone_security "\$ZONE_NAME"
            fi
        done
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 12)) -eq 0 ]; then
            generate_zone_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_zone_monitoring
        ;;
    "report")
        generate_zone_report
        ;;
    "status")
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                echo -e "\${BLUE}Zone: \$ZONE_NAME\${NC}"
                echo "  Trust Level: \$ZONE_TRUST_LEVEL"
                echo "  Networks: \$ZONE_NETWORKS"
                echo "  Ports: \$ZONE_PORTS"
                echo ""
            fi
        done
        ;;
    *)
        echo "Usage: \$0 <monitor|report|status>"
        exit 1
        ;;
esac
ZONE_MONITOR_EOF

    chmod +x ~/zone_monitor.sh
    
    log_message "✅ Zone monitoring system created"
}

# Function to create zone management dashboard
create_zone_dashboard() {
    log_message "📊 Creating zone management dashboard..."
    
    cat << DASHBOARD_EOF > ~/zone_dashboard.sh
#!/bin/bash

# TwinTower Zone Management Dashboard
set -e

ZONES_CONFIG_DIR="/etc/network-zones"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🌐 TwinTower Network Zone Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# Zone overview
echo -e "\${YELLOW}📋 Zone Overview\${NC}"
echo "----------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Determine status color based on trust level
        case "\$ZONE_TRUST_LEVEL" in
            "HIGH") STATUS_COLOR="\${GREEN}" ;;
            "MEDIUM") STATUS_COLOR="\${YELLOW}" ;;
            "LOW") STATUS_COLOR="\${RED}" ;;
            *) STATUS_COLOR="\${NC}" ;;
        esac
        
        echo -e "\${STATUS_COLOR}🔒 \$ZONE_NAME\${NC} (\$ZONE_TRUST_LEVEL trust)"
        echo "   Networks: \$ZONE_NETWORKS"
        echo "   Ports: \$ZONE_PORTS"
        echo ""
    fi
done

# Active connections per zone
echo -e "\${YELLOW}📊 Active Connections\${NC}"
echo "--------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Count connections (simplified)
        local connection_count=0
        IFS=',' read -ra NETWORKS <<< "\$ZONE_NETWORKS"
        for network in "\${NETWORKS[@]}"; do
            if [ "\$network" != "0.0.0.0/0" ]; then
                local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
                connection_count=\$((connection_count + net_connections))
            fi
        done
        
        echo -e "\$ZONE_NAME: \${GREEN}\$connection_count\${NC} active"
    fi
done
echo

# Security events
echo -e "\${YELLOW}🚨 Security Events (Today)\${NC}"
echo "-------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$ZONE_NAME" || echo "0")
        
        if [ "\$blocked_today" -gt 0 ]; then
            echo -e "\$ZONE_NAME: \${RED}\$blocked_today\${NC} blocked attempts"
        else
            echo -e "\$ZONE_NAME: \${GREEN}No threats\${NC}"
        fi
    fi
done
echo

# Zone rules summary
echo -e "\${YELLOW}📋 Zone Rules Summary\${NC}"
echo "--------------------"
TOTAL_RULES=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Total UFW Rules: \${GREEN}\$TOTAL_RULES\${NC}"
echo -e "Zone-based Rules: \${GREEN}\$(sudo ufw status | grep -c "Zone\|DMZ\|Internal\|Trusted\|Management\|GPU" || echo "0")\${NC}"
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Monitor zones: ./zone_monitor.sh"
echo "2. Generate report: ./zone_monitor.sh report"
echo "3. View UFW status: sudo ufw status verbose"
echo "4. Reload zones: ./network_segmentation.sh reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/zone_dashboard.sh
    
    log_message "✅ Zone management dashboard created"
}

# Function to create zone testing script
create_zone_testing() {
    log_message "🧪 Creating zone testing script..."
    
    cat << TEST_EOF > ~/test_network_zones.sh
#!/bin/bash

# TwinTower Network Zone Testing Script
set -e

ZONES_CONFIG_DIR="/etc/network-zones"
TEST_RESULTS="/tmp/zone_test_results_\$(date +%Y%m%d_%H%M%S).txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Network Zone Testing\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        echo "PASS: \$test_name" >> "\$TEST_RESULTS"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        echo "FAIL: \$test_name" >> "\$TEST_RESULTS"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zone configuration files
echo -e "\${YELLOW}📋 Testing Zone Configuration\${NC}"
echo "------------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        zone_name=\$(basename "\$zone_file" .conf)
        run_test "Zone config exists: \$zone_name" "[ -f '\$zone_file' ]"
        run_test "Zone config readable: \$zone_name" "[ -r '\$zone_file' ]"
    fi
done

# Test UFW application profiles
echo -e "\${YELLOW}🔧 Testing UFW Application Profiles\${NC}"
echo "-----------------------------------"
run_test "TwinTower-Management profile" "sudo ufw app info TwinTower-Management"
run_test "TwinTower-SSH profile" "sudo ufw app info TwinTower-SSH"
run_test "TwinTower-GPU profile" "sudo ufw app info TwinTower-GPU"
run_test "TwinTower-Docker profile" "sudo ufw app info TwinTower-Docker"

# Test zone-specific connectivity
echo -e "\${YELLOW}🌐 Testing Zone Connectivity\${NC}"
echo "----------------------------"

# Test Tailscale (Trusted Zone)
if command -v tailscale &> /dev/null; then
    TAILSCALE_IP=\$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "\$TAILSCALE_IP" ]; then
        run_test "Tailscale connectivity" "ping -c 1 \$TAILSCALE_IP"
    fi
fi

# Test SSH connectivity
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
run_test "SSH port accessible" "timeout 5 bash -c '</dev/tcp/localhost/\$SSH_PORT'"

# Test Docker connectivity
if command -v docker &> /dev/null; then
    run_test "Docker daemon accessible" "docker version"
fi

# Test zone isolation
echo -e "\${YELLOW}🔒 Testing Zone Isolation\${NC}"
echo "-------------------------"
run_test "UFW active" "sudo ufw status | grep -q 'Status: active'"
run_test "Default deny incoming" "sudo ufw status verbose | grep -q 'Default: deny (incoming)'"
run_test "Zone rules present" "sudo ufw status | grep -q 'Zone\|DMZ\|Internal\|Trusted'"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zone tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi

echo -e "\${BLUE}📄 Detailed results: \$TEST_RESULTS\${NC}"
TEST_EOF

    chmod +x ~/test_network_zones.sh
    
    log_message "✅ Zone testing script created"
}

# Main execution
main() {
    echo -e "${BLUE}🌐 TwinTower Network Segmentation & Zone Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}===================================================${NC}"
    
    case "$ACTION" in
        "setup")
            define_network_zones
            implement_zone_rules
            create_zone_monitoring
            create_zone_dashboard
            create_zone_testing
            
            echo -e "${GREEN}✅ Network segmentation configured!${NC}"
            ;;
        "status")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                ~/zone_dashboard.sh
            else
                echo -e "${RED}❌ Network zones not configured${NC}"
            fi
            ;;
        "monitor")
            ~/zone_monitor.sh
            ;;
        "test")
            ~/test_network_zones.sh
            ;;
        "reload")
            implement_zone_rules
            sudo ufw reload
            echo -e "${GREEN}✅ Zone rules reloaded${NC}"
            ;;
        "list")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
                    if [ -f "$zone_file" ]; then
                        source "$zone_file"
                        echo -e "${BLUE}Zone: $ZONE_NAME${NC}"
                        echo "  Description: $ZONE_DESCRIPTION"
                        echo "  Trust Level: $ZONE_TRUST_LEVEL"
                        echo "  Networks: $ZONE_NETWORKS"
                        echo ""
                    fi
                done
            else
                echo -e "${RED}❌ No zones configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|monitor|test|reload|list> [zone_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/network_segmentation.sh
```

### **Step 2: Execute Network Segmentation Setup**

```bash
# Setup network segmentation
./network_segmentation.sh setup

# View zone configuration
./network_segmentation.sh list

# Test zone implementation
./network_segmentation.sh test

# Monitor zones
./network_segmentation.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔒 **Zero-Trust Access Policies**

### **Step 1: Create Zero-Trust Access Control System**

```bash
cat > ~/zero_trust_access.sh << 'EOF'
#!/bin/bash

# TwinTower Zero-Trust Access Control System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
POLICY_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Zero-trust configuration
ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$ZT_LOG_FILE"
}

# Function to setup zero-trust infrastructure
setup_zero_trust() {
    log_message "🔒 Setting up zero-trust infrastructure..."
    
    # Create configuration directories
    sudo mkdir -p "$ZT_CONFIG_DIR" "$ZT_POLICIES_DIR"
    sudo touch "$ZT_LOG_FILE"
    
    # Create zero-trust configuration
    cat << ZT_CONFIG_EOF | sudo tee "$ZT_CONFIG_DIR/zero-trust.conf"
# TwinTower Zero-Trust Configuration
ZT_ENABLED=true
ZT_DEFAULT_POLICY="DENY"
ZT_LOGGING_LEVEL="INFO"
ZT_AUDIT_ENABLED=true
ZT_ENCRYPTION_REQUIRED=true
ZT_AUTHENTICATION_REQUIRED=true
ZT_AUTHORIZATION_REQUIRED=true
ZT_CONTINUOUS_VERIFICATION=true
ZT_SESSION_TIMEOUT=3600
ZT_MAX_FAILED_ATTEMPTS=3
ZT_LOCKOUT_DURATION=1800
ZT_GEOLOCATION_ENABLED=false
ZT_DEVICE_FINGERPRINTING=true
ZT_BEHAVIORAL_ANALYSIS=true
ZT_CONFIG_EOF

    log_message "✅ Zero-trust infrastructure created"
}

# Function to create identity-based policies
create_identity_policies() {
    log_message "👤 Creating identity-based access policies..."
    
    # Administrative Users Policy
    cat << ADMIN_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/admin-users.json"
{
    "policy_name": "AdminUsers",
    "description": "Administrative users with elevated privileges",
    "version": "1.0",
    "priority": 100,
    "conditions": {
        "users": ["ubuntu", "admin", "root"],
        "groups": ["sudo", "docker", "adm"],
        "authentication_methods": ["publickey", "certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "06:00-23:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": true,
        "docker_access": true,
        "gpu_access": true,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 5,
        "session_timeout": 3600,
        "idle_timeout": 1800,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "INFO",
        "log_commands": true,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
ADMIN_POLICY_EOF

    # Standard Users Policy
    cat << USER_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/standard-users.json"
{
    "policy_name": "StandardUsers",
    "description": "Standard users with limited privileges",
    "version": "1.0",
    "priority": 200,
    "conditions": {
        "users": ["user", "developer", "analyst"],
        "groups": ["users"],
        "authentication_methods": ["publickey"],
        "source_networks": ["100.64.0.0/10"],
        "time_restrictions": {
            "allowed_hours": "08:00-18:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": false,
        "gpu_access": true,
        "monitoring_access": false,
        "log_access": false
    },
    "restrictions": {
        "max_sessions": 2,
        "session_timeout": 2400,
        "idle_timeout": 900,
        "password_required": false,
        "mfa_required": true
    },
    "audit": {
        "log_level": "WARN",
        "log_commands": false,
        "log_file_access": false,
        "alert_on_failure": true
    }
}
USER_POLICY_EOF

    # Service Accounts Policy
    cat << SERVICE_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/service-accounts.json"
{
    "policy_name": "ServiceAccounts",
    "description": "Automated service accounts",
    "version": "1.0",
    "priority": 300,
    "conditions": {
        "users": ["docker", "monitoring", "backup"],
        "groups": ["service"],
        "authentication_methods": ["certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "00:00-23:59",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": true,
        "gpu_access": false,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 10,
        "session_timeout": 7200,
        "idle_timeout": 3600,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "ERROR",
        "log_commands": false,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
SERVICE_POLICY_EOF

    log_message "✅ Identity-based policies created"
}

# Function to create device-based policies
create_device_policies() {
    log_message "📱 Creating device-based access policies..."
    
    # Trusted Devices Policy
    cat << TRUSTED_DEVICE_EOF | sudo tee "$ZT_POLICIES_DIR/trusted-devices.json"
{
    "policy_name": "TrustedDevices",
    "description": "Pre-approved trusted devices",
    "version": "1.0",
    "priority": 150,
    "conditions": {
        "device_types": ["laptop", "workstation", "server"],
        "os_types": ["linux", "windows", "macos"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "current",
        "certificate_required": true
    },
    "permissions": {
        "full_access": true,
        "admin_access": true,
        "sensitive_data_access": true
    },
    "restrictions": {
        "geolocation_required": false,
        "vpn_required": false,
        "time_limited": false
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true
    }
}
TRUSTED_DEVICE_EOF

    # BYOD Policy
    cat << BYOD_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/byod-devices.json"
{
    "policy_name": "BYODDevices",
    "description": "Bring Your Own Device policy",
    "version": "1.0",
    "priority": 400,
    "conditions": {
        "device_types": ["mobile", "tablet", "personal-laptop"],
        "os_types": ["android", "ios", "windows", "macos", "linux"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "recent",
        "certificate_required": false
    },
    "permissions": {
        "full_access": false,
        "admin_access": false,
        "sensitive_data_access": false,
        "limited_access": true
    },
    "restrictions": {
        "geolocation_required": true,
        "vpn_required": true,
        "time_limited": true,
        "data_download_restricted": true,
        "screenshot_blocked": true
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true,
        "data_loss_prevention": true
    }
}
BYOD_POLICY_EOF

    log_message "✅ Device-based policies created"
}

# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access# 🔥 Section 5C: Firewall & Access Control
## TwinTower GPU Infrastructure Guide

---

### 📑 **Table of Contents**
- [🎯 Overview](#-overview)
- [🔧 Prerequisites](#-prerequisites)
- [🛡️ Advanced UFW Firewall Configuration](#-advanced-ufw-firewall-configuration)
- [🌐 Network Segmentation & Zone Management](#-network-segmentation--zone-management)
- [🔒 Zero-Trust Access Policies](#-zero-trust-access-policies)
- [🚨 Intrusion Detection & Prevention](#-intrusion-detection--prevention)
- [📊 Network Traffic Monitoring](#-network-traffic-monitoring)
- [⚡ Performance Optimization](#-performance-optimization)
- [🔄 Backup & Recovery](#-backup--recovery)
- [🚀 Next Steps](#-next-steps)

---

## 🎯 **Overview**

Section 5C implements comprehensive firewall and access control policies to complete your TwinTower GPU infrastructure security framework, building upon the secure Tailscale mesh (5A) and hardened SSH (5B) implementations.

### **What This Section Accomplishes:**
- ✅ Advanced UFW firewall with intelligent rules
- ✅ Network segmentation with security zones
- ✅ Zero-trust access policies and micro-segmentation
- ✅ Intrusion detection and prevention systems
- ✅ Real-time network traffic monitoring
- ✅ Performance-optimized security policies
- ✅ Automated threat response and mitigation

### **Security Architecture:**
```
Internet ←→ Tailscale Mesh ←→ Firewall Zones ←→ TwinTower Infrastructure
                                     ↓
    ┌─────────────────────────────────────────────────────────────────────┐
    │     DMZ Zone          Internal Zone        Management Zone           │
    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
    │  │ Public APIs │    │ GPU Cluster │    │ Admin Tools │              │
    │  │ Web Services│    │ Docker Swarm│    │ Monitoring  │              │
    │  └─────────────┘    └─────────────┘    └─────────────┘              │
    │         │                   │                   │                   │
    │    ┌─────────────────────────────────────────────────────────┐      │
    │    │          Firewall Rules & Access Control              │      │
    │    └─────────────────────────────────────────────────────────┘      │
    └─────────────────────────────────────────────────────────────────────┘
```

### **Port Management Strategy:**
- **Management Ports**: 3000-3099 (Web UIs, dashboards)
- **GPU Services**: 4000-4099 (ML/AI workloads)
- **Docker Services**: 5000-5099 (Container applications)
- **Monitoring**: 6000-6099 (Metrics, logging)
- **Custom Apps**: 7000-7099 (User applications)

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔧 **Prerequisites**

### **Required Infrastructure:**
- ✅ Section 5A completed (Tailscale mesh network operational)
- ✅ Section 5B completed (SSH hardening and port configuration)
- ✅ UFW firewall installed and configured
- ✅ Docker Swarm cluster operational
- ✅ Administrative access to all towers

### **Network Requirements:**
- ✅ Tailscale connectivity between all towers
- ✅ SSH access on custom ports (2122/2222/2322)
- ✅ Docker Swarm ports accessible
- ✅ Local network connectivity (192.168.1.0/24)

### **Verification Commands:**
```bash
# Verify previous sections
tailscale status
sudo systemctl status ssh
sudo ufw status
docker node ls
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🛡️ **Advanced UFW Firewall Configuration**

### **Step 1: Create Advanced UFW Management System**

```bash
cat > ~/advanced_ufw_manager.sh << 'EOF'
#!/bin/bash

# TwinTower Advanced UFW Management System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-status}"
TOWER_NAME="${2:-$(hostname)}"
TOWER_NUM=$(echo "$TOWER_NAME" | grep -o '[0-9]' | head -1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
UFW_CONFIG_DIR="/etc/ufw"
BACKUP_DIR="/home/$(whoami)/firewall_backups"
LOG_FILE="/var/log/ufw-manager.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to determine tower-specific ports
get_tower_ports() {
    local tower_num="$1"
    
    case "$tower_num" in
        "1")
            echo "SSH_PORT=2122 WEB_PORT=3001 GPU_PORT=4001 DOCKER_PORT=5001 MONITOR_PORT=6001"
            ;;
        "2")
            echo "SSH_PORT=2222 WEB_PORT=3002 GPU_PORT=4002 DOCKER_PORT=5002 MONITOR_PORT=6002"
            ;;
        "3")
            echo "SSH_PORT=2322 WEB_PORT=3003 GPU_PORT=4003 DOCKER_PORT=5003 MONITOR_PORT=6003"
            ;;
        *)
            echo "SSH_PORT=22 WEB_PORT=3000 GPU_PORT=4000 DOCKER_PORT=5000 MONITOR_PORT=6000"
            ;;
    esac
}

# Function to setup advanced UFW configuration
setup_advanced_ufw() {
    log_message "🔧 Setting up advanced UFW configuration..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup current UFW configuration
    if [ -d "$UFW_CONFIG_DIR" ]; then
        sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Reset UFW to clean state
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw default deny forward
    
    log_message "✅ UFW default policies configured"
}

# Function to configure network zones
configure_network_zones() {
    log_message "🌐 Configuring network security zones..."
    
    # Define network zones
    local LOCAL_NET="192.168.1.0/24"
    local TAILSCALE_NET="100.64.0.0/10"
    local DOCKER_NET="172.17.0.0/16"
    local SWARM_NET="10.0.0.0/8"
    
    # Allow loopback
    sudo ufw allow in on lo
    sudo ufw allow out on lo
    
    # Configure Tailscale zone (trusted)
    sudo ufw allow from "$TAILSCALE_NET" comment "Tailscale Network"
    
    # Configure local network zone (semi-trusted)
    sudo ufw allow from "$LOCAL_NET" to any port 22 comment "Local SSH"
    sudo ufw allow from "$LOCAL_NET" to any port 80 comment "Local HTTP"
    sudo ufw allow from "$LOCAL_NET" to any port 443 comment "Local HTTPS"
    
    # Configure Docker networks
    sudo ufw allow from "$DOCKER_NET" comment "Docker Network"
    sudo ufw allow from "$SWARM_NET" comment "Docker Swarm Network"
    
    log_message "✅ Network zones configured"
}

# Function to configure service-specific rules
configure_service_rules() {
    log_message "⚙️ Configuring service-specific firewall rules..."
    
    # Get tower-specific ports
    eval $(get_tower_ports "$TOWER_NUM")
    
    # SSH Rules
    sudo ufw allow "$SSH_PORT/tcp" comment "SSH Custom Port Tower$TOWER_NUM"
    
    # Docker Swarm Rules
    sudo ufw allow 2377/tcp comment "Docker Swarm Management"
    sudo ufw allow 7946/tcp comment "Docker Swarm Communication TCP"
    sudo ufw allow 7946/udp comment "Docker Swarm Communication UDP"
    sudo ufw allow 4789/udp comment "Docker Swarm Overlay Network"
    
    # Tailscale Rules
    sudo ufw allow 41641/udp comment "Tailscale"
    
    # GPU and ML Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$GPU_PORT" comment "GPU Services Tower$TOWER_NUM"
    sudo ufw allow from "192.168.1.0/24" to any port "$GPU_PORT" comment "GPU Services Local"
    
    # Web Management Interface
    sudo ufw allow from "$TAILSCALE_NET" to any port "$WEB_PORT" comment "Web Management Tower$TOWER_NUM"
    
    # Docker Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$DOCKER_PORT" comment "Docker Services Tower$TOWER_NUM"
    
    # Monitoring Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$MONITOR_PORT" comment "Monitoring Tower$TOWER_NUM"
    
    log_message "✅ Service-specific rules configured"
}

# Function to configure advanced security rules
configure_advanced_security() {
    log_message "🔒 Configuring advanced security rules..."
    
    # Rate limiting for SSH
    sudo ufw limit ssh comment "SSH Rate Limiting"
    
    # Block common attack patterns
    sudo ufw deny from 10.0.0.0/8 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 172.16.0.0/12 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 192.168.0.0/16 to any port 22 comment "Block RFC1918 SSH (except local)"
    sudo ufw allow from 192.168.1.0/24 to any port 22 comment "Allow local SSH"
    
    # Block suspicious ports
    sudo ufw deny 135/tcp comment "Block MS RPC"
    sudo ufw deny 139/tcp comment "Block NetBIOS"
    sudo ufw deny 445/tcp comment "Block SMB"
    sudo ufw deny 1433/tcp comment "Block MS SQL"
    sudo ufw deny 3389/tcp comment "Block RDP"
    
    # Allow ping but limit it
    sudo ufw allow from "$TAILSCALE_NET" proto icmp comment "Tailscale Ping"
    sudo ufw allow from "192.168.1.0/24" proto icmp comment "Local Ping"
    
    log_message "✅ Advanced security rules configured"
}

# Function to configure logging and monitoring
configure_logging() {
    log_message "📊 Configuring UFW logging and monitoring..."
    
    # Enable UFW logging
    sudo ufw logging on
    
    # Create custom logging configuration
    cat << LOG_CONFIG_EOF | sudo tee /etc/rsyslog.d/20-ufw.conf
# UFW logging configuration
:msg,contains,"[UFW " /var/log/ufw.log
& stop
LOG_CONFIG_EOF

    # Create log rotation
    cat << LOGROTATE_EOF | sudo tee /etc/logrotate.d/ufw-custom
/var/log/ufw.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 syslog adm
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
LOGROTATE_EOF

    # Restart rsyslog
    sudo systemctl restart rsyslog
    
    log_message "✅ UFW logging configured"
}

# Function to create UFW monitoring script
create_ufw_monitor() {
    log_message "📈 Creating UFW monitoring script..."
    
    cat << MONITOR_EOF > ~/ufw_monitor.sh
#!/bin/bash

# TwinTower UFW Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-60}"
LOG_FILE="/var/log/ufw-monitor.log"
ALERT_THRESHOLD=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor UFW status
monitor_ufw_status() {
    if sudo ufw status | grep -q "Status: active"; then
        log_message "✅ UFW is active"
        return 0
    else
        log_message "❌ UFW is inactive"
        return 1
    fi
}

# Function to analyze UFW logs
analyze_ufw_logs() {
    local blocked_count=\$(sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    local allowed_count=\$(sudo grep "\[UFW ALLOW\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    
    log_message "📊 Today's UFW activity - Blocked: \$blocked_count, Allowed: \$allowed_count"
    
    if [ "\$blocked_count" -gt "\$ALERT_THRESHOLD" ]; then
        log_message "🚨 HIGH ALERT: \$blocked_count blocked connections today"
        
        # Show top blocked IPs
        echo "Top blocked IPs today:" | tee -a "\$LOG_FILE"
        sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
        awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
        while read count ip; do
            echo "  \$ip: \$count attempts" | tee -a "\$LOG_FILE"
        done
    fi
}

# Function to check rule efficiency
check_rule_efficiency() {
    local total_rules=\$(sudo ufw status numbered | grep -c "^\[")
    log_message "📋 Total UFW rules: \$total_rules"
    
    if [ "\$total_rules" -gt 50 ]; then
        log_message "⚠️  Warning: High number of UFW rules may impact performance"
    fi
}

# Function to generate UFW report
generate_ufw_report() {
    local report_file="/tmp/ufw_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower UFW Monitoring Report
==============================
Generated: \$(date)
Tower: \$(hostname)

UFW Status:
----------
\$(sudo ufw status verbose)

Recent Activity (Last 24 hours):
-------------------------------
Blocked connections: \$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
Allowed connections: \$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)

Top Blocked IPs:
---------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Top Blocked Ports:
-----------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$14}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Recent Blocked Connections:
--------------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | tail -10)

REPORT_EOF

    echo "📋 UFW report generated: \$report_file"
    log_message "UFW report generated: \$report_file"
}

# Function to start monitoring daemon
start_monitoring() {
    log_message "🚀 Starting UFW monitoring daemon..."
    
    while true; do
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 60)) -eq 0 ]; then
            generate_ufw_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_monitoring
        ;;
    "status")
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        ;;
    "report")
        generate_ufw_report
        ;;
    *)
        echo "Usage: \$0 <monitor|status|report>"
        exit 1
        ;;
esac
MONITOR_EOF

    chmod +x ~/ufw_monitor.sh
    
    log_message "✅ UFW monitoring script created"
}

# Function to optimize UFW performance
optimize_ufw_performance() {
    log_message "⚡ Optimizing UFW performance..."
    
    # Create custom UFW configuration for performance
    cat << PERF_CONFIG_EOF | sudo tee /etc/ufw/sysctl.conf
# TwinTower UFW Performance Optimization

# Network performance
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.core.netdev_max_backlog = 5000

# Connection tracking
net.netfilter.nf_conntrack_max = 131072
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30

# Rate limiting
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048

# Security hardening
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
PERF_CONFIG_EOF

    # Apply sysctl settings
    sudo sysctl -p /etc/ufw/sysctl.conf
    
    log_message "✅ UFW performance optimized"
}

# Function to create UFW dashboard
create_ufw_dashboard() {
    log_message "📊 Creating UFW dashboard..."
    
    cat << DASHBOARD_EOF > ~/ufw_dashboard.sh
#!/bin/bash

# TwinTower UFW Dashboard
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔥 TwinTower UFW Firewall Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# UFW Status
echo -e "\${YELLOW}🛡️ UFW Status\${NC}"
echo "---------------"
if sudo ufw status | grep -q "Status: active"; then
    echo -e "Firewall Status: \${GREEN}✅ Active\${NC}"
else
    echo -e "Firewall Status: \${RED}❌ Inactive\${NC}"
fi

# Rule count
RULE_COUNT=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Active Rules: \${GREEN}\$RULE_COUNT\${NC}"

# Default policies
echo -e "Default Incoming: \${RED}DENY\${NC}"
echo -e "Default Outgoing: \${GREEN}ALLOW\${NC}"
echo

# Recent activity
echo -e "\${YELLOW}📈 Recent Activity (Last Hour)\${NC}"
echo "------------------------------"
HOUR_AGO=\$(date -d '1 hour ago' '+%b %d %H')
CURRENT_HOUR=\$(date '+%b %d %H')

BLOCKED_HOUR=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)
ALLOWED_HOUR=\$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)

echo -e "Blocked Connections: \${RED}\$BLOCKED_HOUR\${NC}"
echo -e "Allowed Connections: \${GREEN}\$ALLOWED_HOUR\${NC}"
echo

# Top blocked IPs
echo -e "\${YELLOW}🚫 Top Blocked IPs (Today)\${NC}"
echo "-------------------------"
sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
while read count ip; do
    echo -e "  \${RED}\$ip\${NC}: \$count attempts"
done
echo

# Service status
echo -e "\${YELLOW}⚙️ Service Status\${NC}"
echo "-----------------"
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
echo -e "SSH Port: \${GREEN}\$SSH_PORT\${NC}"

if sudo systemctl is-active --quiet docker; then
    echo -e "Docker: \${GREEN}✅ Running\${NC}"
else
    echo -e "Docker: \${RED}❌ Stopped\${NC}"
fi

if sudo systemctl is-active --quiet tailscaled; then
    echo -e "Tailscale: \${GREEN}✅ Running\${NC}"
else
    echo -e "Tailscale: \${RED}❌ Stopped\${NC}"
fi
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View detailed rules: sudo ufw status numbered"
echo "2. Monitor real-time: sudo tail -f /var/log/ufw.log"
echo "3. Generate report: ./ufw_monitor.sh report"
echo "4. Reload firewall: sudo ufw reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/ufw_dashboard.sh
    
    log_message "✅ UFW dashboard created"
}

# Main execution
main() {
    echo -e "${BLUE}🔥 TwinTower Advanced UFW Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME (Tower$TOWER_NUM)${NC}"
    echo -e "${BLUE}===================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_advanced_ufw
            configure_network_zones
            configure_service_rules
            configure_advanced_security
            configure_logging
            create_ufw_monitor
            optimize_ufw_performance
            create_ufw_dashboard
            
            # Enable UFW
            sudo ufw --force enable
            
            echo -e "${GREEN}✅ Advanced UFW configuration completed!${NC}"
            ;;
        "status")
            sudo ufw status verbose
            ;;
        "dashboard")
            ./ufw_dashboard.sh
            ;;
        "monitor")
            ./ufw_monitor.sh
            ;;
        "optimize")
            optimize_ufw_performance
            ;;
        "backup")
            sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
            echo -e "${GREEN}✅ UFW configuration backed up${NC}"
            ;;
        "reload")
            sudo ufw reload
            echo -e "${GREEN}✅ UFW reloaded${NC}"
            ;;
        *)
            echo "Usage: $0 <setup|status|dashboard|monitor|optimize|backup|reload> [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/advanced_ufw_manager.sh
```

### **Step 2: Execute Advanced UFW Setup**

```bash
# Setup advanced UFW configuration on each tower
./advanced_ufw_manager.sh setup $(hostname)

# Verify UFW status
./advanced_ufw_manager.sh status

# Launch UFW dashboard
./advanced_ufw_manager.sh dashboard
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🌐 **Network Segmentation & Zone Management**

### **Step 1: Create Network Segmentation System**

```bash
cat > ~/network_segmentation.sh << 'EOF'
#!/bin/bash

# TwinTower Network Segmentation & Zone Management
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
ZONE_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Network zones configuration
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/network-zones.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to define network zones
define_network_zones() {
    log_message "🌐 Defining network security zones..."
    
    sudo mkdir -p "$ZONES_CONFIG_DIR"
    
    # DMZ Zone - Public-facing services
    cat << DMZ_EOF | sudo tee "$ZONES_CONFIG_DIR/dmz.conf"
# DMZ Zone Configuration
ZONE_NAME="DMZ"
ZONE_DESCRIPTION="Public-facing services and APIs"
ZONE_NETWORKS="0.0.0.0/0"
ZONE_TRUST_LEVEL="LOW"
ZONE_PORTS="80,443,8080,8443"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="STRICT"
ZONE_INTRUSION_DETECTION="ENABLED"
DMZ_EOF

    # Internal Zone - Private infrastructure
    cat << INTERNAL_EOF | sudo tee "$ZONES_CONFIG_DIR/internal.conf"
# Internal Zone Configuration
ZONE_NAME="INTERNAL"
ZONE_DESCRIPTION="Private infrastructure and services"
ZONE_NETWORKS="192.168.1.0/24,172.16.0.0/12,10.0.0.0/8"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="22,80,443,2377,4789,7946"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
INTERNAL_EOF

    # Trusted Zone - Tailscale and management
    cat << TRUSTED_EOF | sudo tee "$ZONES_CONFIG_DIR/trusted.conf"
# Trusted Zone Configuration
ZONE_NAME="TRUSTED"
ZONE_DESCRIPTION="Tailscale mesh and management interfaces"
ZONE_NETWORKS="100.64.0.0/10"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="ALL"
ZONE_PROTOCOLS="tcp,udp,icmp"
ZONE_LOGGING="LOW"
ZONE_RATE_LIMIT="RELAXED"
ZONE_INTRUSION_DETECTION="MONITORING"
TRUSTED_EOF

    # Management Zone - Administrative access
    cat << MGMT_EOF | sudo tee "$ZONES_CONFIG_DIR/management.conf"
# Management Zone Configuration
ZONE_NAME="MANAGEMENT"
ZONE_DESCRIPTION="Administrative and monitoring services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="2122,2222,2322,3000-3099,6000-6099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
MGMT_EOF

    # GPU Zone - GPU compute services
    cat << GPU_EOF | sudo tee "$ZONES_CONFIG_DIR/gpu.conf"
# GPU Zone Configuration
ZONE_NAME="GPU"
ZONE_DESCRIPTION="GPU compute and ML services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="4000-4099,8000-8099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
GPU_EOF

    log_message "✅ Network zones defined"
}

# Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone '\$rule_file' > /dev/null || [ \$(grep -c '^[^#]' '\$rule_file') -eq 0 ]"
    fi
done

# Test detection functionality
echo -e "\${YELLOW}🎯 Testing Detection Functionality\${NC}"
echo "----------------------------------"
run_test "SSH brute force detection" "echo 'authentication failure ssh' | ./ids_detection_engine.sh test"
run_test "Rule processing works" "grep -q 'SSH brute force' /var/log/twintower-ids/detection.log"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All IDS tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
IDS_TEST_EOF

    chmod +x ~/test_ids_system.sh
    
    log_message "✅ IDS testing script created"
}

# Main execution
main() {
    echo -e "${BLUE}🚨 TwinTower Intrusion Detection & Prevention${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=============================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_ids_infrastructure
            create_detection_rules
            create_detection_engine
            create_ids_dashboard
            create_ids_service
            test_ids_system
            
            echo -e "${GREEN}✅ Intrusion Detection System configured!${NC}"
            ;;
        "start")
            sudo systemctl start twintower-ids.service
            echo -e "${GREEN}✅ IDS service started${NC}"
            ;;
        "stop")
            sudo systemctl stop twintower-ids.service
            echo -e "${GREEN}✅ IDS service stopped${NC}"
            ;;
        "status")
            ~/ids_dashboard.sh
            ;;
        "test")
            ~/test_ids_system.sh
            ;;
        "monitor")
            ~/ids_detection_engine.sh daemon
            ;;
        "report")
            ~/ids_detection_engine.sh report
            ;;
        "alerts")
            if [ -f "$IDS_ALERT_LOG" ]; then
                tail -f "$IDS_ALERT_LOG"
            else
                echo -e "${RED}❌ Alert log not found${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|start|stop|status|test|monitor|report|alerts>"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/intrusion_detection.sh
```

### **Step 2: Execute IDS Setup**

```bash
# Setup intrusion detection system
./intrusion_detection.sh setup

# Start IDS service
./intrusion_detection.sh start

# View IDS status
./intrusion_detection.sh status

# Test IDS functionality
./intrusion_detection.sh test
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📊 **Network Traffic Monitoring**

### **Step 1: Create Network Traffic Monitoring System**

```bash
cat > ~/network_traffic_monitor.sh << 'EOF'
#!/bin/bash

# TwinTower Network Traffic Monitoring System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
MONITOR_TYPE="${2:-realtime}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Traffic monitoring configuration
TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$TRAFFIC_LOG_DIR/monitor.log"
}

# Function to setup traffic monitoring infrastructure
setup_traffic_monitoring() {
    log_message "📊 Setting up traffic monitoring infrastructure..."
    
    # Create directories
    sudo mkdir -p "$TRAFFIC_CONFIG_DIR" "$TRAFFIC_LOG_DIR" "$TRAFFIC_DATA_DIR"
    
    # Install required packages
    sudo apt update
    sudo apt install -y iftop nethogs nload vnstat tcpdump wireshark-common
    
    # Create traffic monitoring configuration
    cat << TRAFFIC_CONFIG_EOF | sudo tee "$TRAFFIC_CONFIG_DIR/monitor.conf"
# TwinTower Traffic Monitoring Configuration
TRAFFIC_ENABLED=true
TRAFFIC_INTERFACE="auto"
TRAFFIC_SAMPLE_INTERVAL=60
TRAFFIC_RETENTION_DAYS=30
TRAFFIC_ALERT_THRESHOLD_MBPS=100
TRAFFIC_BANDWIDTH_LIMIT_MBPS=1000
TRAFFIC_PACKET_CAPTURE=false
TRAFFIC_DEEP_INSPECTION=false
TRAFFIC_GEOLOCATION=false
TRAFFIC_THREAT_DETECTION=true
TRAFFIC_ANOMALY_DETECTION=true
TRAFFIC_BASELINE_PERIOD=7
TRAFFIC_CONFIG_EOF

    # Create network interface detection script
    cat << INTERFACE_EOF > ~/detect_interfaces.sh
#!/bin/bash

# Detect primary network interface
PRIMARY_INTERFACE=\$(ip route | grep default | awk '{print \$5}' | head -1)
TAILSCALE_INTERFACE=\$(ip link show | grep tailscale | cut -d: -f2 | tr -d ' ')
DOCKER_INTERFACE=\$(ip link show | grep docker | cut -d: -f2 | tr -d ' ')

echo "Primary Interface: \$PRIMARY_INTERFACE"
echo "Tailscale Interface: \$TAILSCALE_INTERFACE"
echo "Docker Interface: \$DOCKER_INTERFACE"

# Create interface configuration
cat > "$TRAFFIC_CONFIG_DIR/interfaces.conf" << IFACE_EOF
PRIMARY_INTERFACE=\$PRIMARY_INTERFACE
TAILSCALE_INTERFACE=\$TAILSCALE_INTERFACE
DOCKER_INTERFACE=\$DOCKER_INTERFACE
IFACE_EOF
INTERFACE_EOF

    chmod +x ~/detect_interfaces.sh
    ~/detect_interfaces.sh
    
    log_message "✅ Traffic monitoring infrastructure created"
}

# Function to create traffic analysis engine
create_traffic_analyzer() {
    log_message "🔍 Creating traffic analysis engine..."
    
    cat << ANALYZER_EOF > ~/traffic_analyzer.sh
#!/bin/bash

# TwinTower Traffic Analysis Engine
set -e

TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
source "\$TRAFFIC_CONFIG_DIR/monitor.conf"
source "\$TRAFFIC_CONFIG_DIR/interfaces.conf"

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$TRAFFIC_LOG_DIR/analyzer.log"
}

# Function to collect interface statistics
collect_interface_stats() {
    local interface="\$1"
    local timestamp=\$(date +%s)
    
    # Get interface statistics
    local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
    
    if [ -n "\$stats" ]; then
        local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
        local rx_packets=\$(echo "\$stats" | cut -d' ' -f3)
        local rx_errors=\$(echo "\$stats" | cut -d' ' -f4)
        local rx_dropped=\$(echo "\$stats" | cut -d' ' -f5)
        local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
        local tx_packets=\$(echo "\$stats" | cut -d' ' -f11)
        local tx_errors=\$(echo "\$stats" | cut -d' ' -f12)
        local tx_dropped=\$(echo "\$stats" | cut -d' ' -f13)
        
        # Store statistics
        echo "\$timestamp,\$interface,\$rx_bytes,\$rx_packets,\$rx_errors,\$rx_dropped,\$tx_bytes,\$tx_packets,\$tx_errors,\$tx_dropped" >> "\$TRAFFIC_DATA_DIR/interface_stats.csv"
    fi
}

# Function to analyze bandwidth usage
analyze_bandwidth() {
    local interface="\$1"
    
    log_message "📊 Analyzing bandwidth usage for \$interface"
    
    # Get current bandwidth usage
    local current_rx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$2}')
    local current_tx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$10}')
    
    # Compare with previous measurement
    local prev_file="\$TRAFFIC_DATA_DIR/\$interface.prev"
    if [ -f "\$prev_file" ]; then
        local prev_data=\$(cat "\$prev_file")
        local prev_time=\$(echo "\$prev_data" | cut -d',' -f1)
        local prev_rx=\$(echo "\$prev_data" | cut -d',' -f2)
        local prev_tx=\$(echo "\$prev_data" | cut -d',' -f3)
        
        local current_time=\$(date +%s)
        local time_diff=\$((current_time - prev_time))
        
        if [ \$time_diff -gt 0 ]; then
            local rx_rate=\$(echo "scale=2; (\$current_rx - \$prev_rx) / \$time_diff / 1024 / 1024" | bc -l)
            local tx_rate=\$(echo "scale=2; (\$current_tx - \$prev_tx) / \$time_diff / 1024 / 1024" | bc -l)
            
            log_message "Interface \$interface: RX: \$rx_rate MB/s, TX: \$tx_rate MB/s"
            
            # Check for bandwidth alerts
            local total_rate=\$(echo "\$rx_rate + \$tx_rate" | bc -l)
            local alert_threshold=\$(echo "scale=2; \$TRAFFIC_ALERT_THRESHOLD_MBPS / 8" | bc -l)
            
            if [ \$(echo "\$total_rate > \$alert_threshold" | bc -l) -eq 1 ]; then
                log_message "🚨 HIGH BANDWIDTH ALERT: \$interface using \$total_rate MB/s"
                echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH BANDWIDTH: \$interface \$total_rate MB/s" >> "\$TRAFFIC_LOG_DIR/alerts.log"
            fi
        fi
    fi
    
    # Store current data
    echo "\$(date +%s),\$current_rx,\$current_tx" > "\$prev_file"
}

# Function to detect traffic anomalies
detect_anomalies() {
    local interface="\$1"
    
    log_message "🔍 Detecting traffic anomalies for \$interface"
    
    # Get recent traffic data
    local recent_data=\$(tail -n 100 "\$TRAFFIC_DATA_DIR/interface_stats.csv" | grep "\$interface")
    
    if [ -n "\$recent_data" ]; then
        # Calculate average traffic
        local avg_rx=\$(echo "\$recent_data" | awk -F',' '{sum+=\$3} END {print sum/NR}')
        local avg_tx=\$(echo "\$recent_data" | awk -F',' '{sum+=\$7} END {print sum/NR}')
        
        # Get current traffic
        local current_rx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$3}')
        local current_tx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$11}')
        
        # Check for anomalies (traffic 3x higher than average)
        if [ \$(echo "\$current_rx > \$avg_rx * 3" | bc -l) -eq 1 ]; then
            log_message "🚨 ANOMALY DETECTED: High RX packet rate on \$interface"
            echo "\$(date '+%Y-%m-%d %H:%M:%S') - ANOMALY: High RX packets \$interface" >> "\$TRAFFIC_LOG_DIR/alerts.log"
        fi
        
        if [ \$(echo "\$current_tx > \$avg_tx * 3" | bc -l) -eq 1 ]; then
            log_message "🚨 ANOMALY DETECTED: High TX packet rate on \$interface"
            echo "\$(date '+%Y-%m-%d %H:%M:%S') - ANOMALY: High TX packets \$interface" >> "\$TRAFFIC_LOG_DIR/alerts.log"
        fi
    fi
}

# Function to analyze connection patterns
analyze_connections() {
    log_message "🔗 Analyzing connection patterns"
    
    # Get active connections
    local connections=\$(netstat -tn | grep ESTABLISHED | wc -l)
    local listening_ports=\$(netstat -tln | grep LISTEN | wc -l)
    
    log_message "Active connections: \$connections"
    log_message "Listening ports: \$listening_ports"
    
    # Store connection data
    echo "\$(date +%s),\$connections,\$listening_ports" >> "\$TRAFFIC_DATA_DIR/connections.csv"
    
    # Check for connection flooding
    if [ \$connections -gt 1000 ]; then
        log_message "🚨 CONNECTION FLOOD ALERT: \$connections active connections"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - CONNECTION FLOOD: \$connections connections" >> "\$TRAFFIC_LOG_DIR/alerts.log"
    fi
}

# Function to monitor specific protocols
monitor_protocols() {
    log_message "📡 Monitoring protocol usage"
    
    # Monitor SSH connections
    local ssh_connections=\$(netstat -tn | grep ':22 ' | grep ESTABLISHED | wc -l)
    local custom_ssh=\$(netstat -tn | grep -E ':(2122|2222|2322) ' | grep ESTABLISHED | wc -l)
    
    # Monitor HTTP/HTTPS
    local http_connections=\$(netstat -tn | grep ':80 ' | grep ESTABLISHED | wc -l)
    local https_connections=\$(netstat -tn | grep ':443 ' | grep ESTABLISHED | wc -l)
    
    # Monitor Docker ports
    local docker_connections=\$(netstat -tn | grep -E ':(2377|4789|7946) ' | grep ESTABLISHED | wc -l)
    
    log_message "SSH: \$ssh_connections, Custom SSH: \$custom_ssh, HTTP: \$http_connections, HTTPS: \$https_connections, Docker: \$docker_connections"
    
    # Store protocol data
    echo "\$(date +%s),\$ssh_connections,\$custom_ssh,\$http_connections,\$https_connections,\$docker_connections" >> "\$TRAFFIC_DATA_DIR/protocols.csv"
}

# Function to generate traffic report
generate_traffic_report() {
    local report_file="/tmp/traffic_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Network Traffic Report
===============================
Generated: \$(date)
Tower: \$(hostname)

Interface Information:
---------------------
Primary Interface: \$PRIMARY_INTERFACE
Tailscale Interface: \$TAILSCALE_INTERFACE
Docker Interface: \$DOCKER_INTERFACE

Current Traffic Statistics:
--------------------------
REPORT_EOF

    # Add interface statistics
    for interface in \$PRIMARY_INTERFACE \$TAILSCALE_INTERFACE \$DOCKER_INTERFACE; do
        if [ -n "\$interface" ] && [ "\$interface" != "auto" ]; then
            echo "Interface: \$interface" >> "\$report_file"
            if [ -f "/proc/net/dev" ]; then
                local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
                if [ -n "\$stats" ]; then
                    local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
                    local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
                    local rx_mb=\$(echo "scale=2; \$rx_bytes / 1024 / 1024" | bc -l)
                    local tx_mb=\$(echo "scale=2; \$tx_bytes / 1024 / 1024" | bc -l)
                    echo "  RX: \$rx_mb MB" >> "\$report_file"
                    echo "  TX: \$tx_mb MB" >> "\$report_file"
                fi
            fi
            echo "" >> "\$report_file"
        fi
    done
    
    cat >> "\$report_file" << REPORT_EOF

Connection Summary:
------------------
Active Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)
Listening Ports: \$(netstat -tln | grep LISTEN | wc -l)

Top Connections by IP:
---------------------
\$(netstat -tn | grep ESTABLISHED | awk '{print \$5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head -10)

Recent Traffic Alerts:
---------------------
\$(tail -n 20 "\$TRAFFIC_LOG_DIR/alerts.log" 2>/dev/null || echo "No recent alerts")

Bandwidth Usage Trends:
----------------------
\$(tail -n 10 "\$TRAFFIC_DATA_DIR/interface_stats.csv" 2>/dev/null || echo "No trend data available")

Protocol Distribution:
---------------------
\$(tail -n 1 "\$TRAFFIC_DATA_DIR/protocols.csv" 2>/dev/null || echo "No protocol data available")

REPORT_EOF

    log_message "📋 Traffic report generated: \$report_file"
    echo "\$report_file"
}

# Function to start traffic monitoring daemon
start_traffic_monitor() {
    log_message "🚀 Starting traffic monitoring daemon..."
    
    while true; do
        # Monitor each interface
        for interface in \$PRIMARY_INTERFACE \$TAILSCALE_INTERFACE \$DOCKER_INTERFACE; do
            if [ -n "\$interface" ] && [ "\$interface" != "auto" ]; then
                collect_interface_stats "\$interface"
                analyze_bandwidth "\$interface"
                detect_anomalies "\$interface"
            fi
        done
        
        # Monitor connections and protocols
        analyze_connections
        monitor_protocols
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$TRAFFIC_SAMPLE_INTERVAL) % 60)) -eq 0 ]; then
            generate_traffic_report
        fi
        
        sleep "\$TRAFFIC_SAMPLE_INTERVAL"
    done
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_traffic_monitor
        ;;
    "report")
        generate_traffic_report
        ;;
    "status")
        echo "Traffic Monitor Status:"
        echo "======================"
        echo "Primary Interface: \$PRIMARY_INTERFACE"
        echo "Tailscale Interface: \$TAILSCALE_INTERFACE"
        echo "Docker Interface: \$DOCKER_INTERFACE"
        echo "Active Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)"
        echo "Recent Alerts: \$(tail -n 5 "\$TRAFFIC_LOG_DIR/alerts.log" 2>/dev/null | wc -l)"
        ;;
    "interfaces")
        echo "Network Interfaces:"
        echo "=================="
        ip addr show | grep -E '^[0-9]+:' | cut -d: -f2 | tr -d ' '
        ;;
    "connections")
        echo "Active Connections:"
        echo "=================="
        netstat -tn | grep ESTABLISHED | head -20
        ;;
    *)
        echo "Usage: \$0 <daemon|report|status|interfaces|connections>"
        exit 1
        ;;
esac
ANALYZER_EOF

    chmod +x ~/traffic_analyzer.sh
    
    log_message "✅ Traffic analysis engine created"
}

# Function to create traffic monitoring dashboard
create_traffic_dashboard() {
    log_message "📊 Creating traffic monitoring dashboard..."
    
    cat << DASHBOARD_EOF > ~/traffic_dashboard.sh
#!/bin/bash

# TwinTower Traffic Monitoring Dashboard
set -e

TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
if [ -f "\$TRAFFIC_CONFIG_DIR/monitor.conf" ]; then
    source "\$TRAFFIC_CONFIG_DIR/monitor.conf"
fi

if [ -f "\$TRAFFIC_CONFIG_DIR/interfaces.conf" ]; then
    source "\$TRAFFIC_CONFIG_DIR/interfaces.conf"
fi

clear
echo -e "\${BLUE}📊 TwinTower Traffic Monitoring Dashboard\${NC}"
echo -e "\${BLUE}=========================================\${NC}"
echo

# System Overview
echo -e "\${YELLOW}🌐 Network Overview\${NC}"
echo "-------------------"
echo -e "Primary Interface: \${GREEN}\$PRIMARY_INTERFACE\${NC}"
echo -e "Tailscale Interface: \${GREEN}\$TAILSCALE_INTERFACE\${NC}"
echo -e "Docker Interface: \${GREEN}\$DOCKER_INTERFACE\${NC}"
echo

# Current Traffic Statistics
echo -e "\${YELLOW}📈 Current Traffic Statistics\${NC}"
echo "-----------------------------"
for interface in \$PRIMARY_INTERFACE \$TAILSCALE_INTERFACE \$DOCKER_INTERFACE; do
    if [ -n "\$interface" ] && [ "\$interface" != "auto" ]; then
        echo -e "\${BLUE}Interface: \$interface\${NC}"
        
        if [ -f "/proc/net/dev" ]; then
            local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
            if [ -n "\$stats" ]; then
                local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
                local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
                local rx_packets=\$(echo "\$stats" | cut -d' ' -f3)
                local tx_packets=\$(echo "\$stats" | cut -d' ' -f11)
                
                local rx_mb=\$(echo "scale=2; \$rx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
                local tx_mb=\$(echo "scale=2; \$tx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
                
                echo -e "  RX: \${GREEN}\$rx_mb MB\${NC} (\$rx_packets packets)"
                echo -e "  TX: \${GREEN}\$tx_mb MB\${NC} (\$tx_packets packets)"
            fi
        fi
        echo
    fi
done

# Connection Statistics
echo -e "\${YELLOW}🔗 Connection Statistics\${NC}"
echo "------------------------"
ACTIVE_CONNECTIONS=\$(netstat -tn | grep ESTABLISHED | wc -l)
LISTENING_PORTS=\$(netstat -tln | grep LISTEN | wc -l)

echo -e "Active Connections: \${GREEN}\$ACTIVE_CONNECTIONS\${NC}"
echo -e "Listening Ports: \${GREEN}\$LISTENING_PORTS\${NC}"
echo

# Protocol Breakdown
echo -e "\${YELLOW}📡 Protocol Breakdown\${NC}"
echo "--------------------"
SSH_CONNECTIONS=\$(netstat -tn | grep ':22 ' | grep ESTABLISHED | wc -l)
CUSTOM_SSH=\$(netstat -tn | grep -E ':(2122|2222|2322) ' | grep ESTABLISHED | wc -l)
HTTP_CONNECTIONS=\$(netstat -tn | grep ':80 ' | grep ESTABLISHED | wc -l)
HTTPS_CONNECTIONS=\$(netstat -tn | grep ':443 ' | grep ESTABLISHED | wc -l)
DOCKER_CONNECTIONS=\$(netstat -tn | grep -E ':(2377|4789|7946) ' | grep ESTABLISHED | wc -l)

echo -e "SSH (standard): \${GREEN}\$SSH_CONNECTIONS\${NC}"
echo -e "SSH (custom): \${GREEN}\$CUSTOM_SSH\${NC}"
echo -e "HTTP: \${GREEN}\$HTTP_CONNECTIONS\${NC}"
echo -e "HTTPS: \${GREEN}\$HTTPS_CONNECTIONS\${NC}"
echo -e "Docker: \${GREEN}\$DOCKER_CONNECTIONS\${NC}"
echo

# Top Connections
echo -e "\${YELLOW}🏆 Top Connection Sources\${NC}"
echo "-------------------------"
echo "Top 5 IPs by connection count:"
netstat -tn | grep ESTABLISHED | awk '{print \$5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head -5 | while read count ip; do
    echo -e "  \${GREEN}\$ip\${NC}: \$count connections"
done
echo

# Recent Alerts
echo -e "\${YELLOW}🚨 Recent Traffic Alerts\${NC}"
echo "------------------------"
if [ -f "\$TRAFFIC_LOG_DIR/alerts.log" ]; then
    ALERT_COUNT=\$(tail -n 20 "\$TRAFFIC_LOG_DIR/alerts.log" | wc -l)
    if [ \$ALERT_COUNT -gt 0 ]; then
        echo -e "Recent Alerts: \${RED}\$ALERT_COUNT\${NC}"
        tail -n 5 "\$TRAFFIC_LOG_DIR/alerts.log" | while read line; do
            echo -e "  \${RED}⚠️\${NC} \$line"
        done
    else
        echo -e "Recent Alerts: \${GREEN}0\${NC}"
    fi
else
    echo -e "No alert data available"
fi
echo

# Bandwidth Usage
echo -e "\${YELLOW}📊 Bandwidth Usage\${NC}"
echo "------------------"
if [ -f "\$TRAFFIC_DATA_DIR/interface_stats.csv" ]; then
    echo "Recent bandwidth activity:"
    tail -n 3 "\$TRAFFIC_DATA_DIR/interface_stats.csv" | while IFS=',' read timestamp interface rx_bytes rx_packets rx_errors rx_dropped tx_bytes tx_packets tx_errors tx_dropped; do
        local time_str=\$(date -d "@\$timestamp" '+%H:%M:%S')
        local rx_mb=\$(echo "scale=2; \$rx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
        local tx_mb=\$(echo "scale=2; \$tx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
        echo -e "  \$time_str \${GREEN}\$interface\${NC}: RX \$rx_mb MB, TX \$tx_mb MB"
    done
else
    echo -e "No bandwidth data available"
fi
echo

# System Health
echo -e "\${YELLOW}💓 System Health\${NC}"
echo "----------------"
TRAFFIC_PROCESS=\$(pgrep -f "traffic_analyzer.sh" | wc -l)
if [ \$TRAFFIC_PROCESS -gt 0 ]; then
    echo -e "Traffic Monitor: \${GREEN}✅ Running\${NC}"
else
    echo -e "Traffic Monitor: \${RED}❌ Stopped\${NC}"
fi

LOG_SIZE=\$(du -h "\$TRAFFIC_LOG_DIR" 2>/dev/null | cut -f1 || echo "0")
echo -e "Log Directory Size: \${GREEN}\$LOG_SIZE\${NC}"

DATA_SIZE=\$(du -h "\$TRAFFIC_DATA_DIR" 2>/dev/null | cut -f1 || echo "0")
echo -e "Data Directory Size: \${GREEN}\$DATA_SIZE\${NC}"
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Start monitor: ./traffic_analyzer.sh daemon"
echo "2. View connections: ./traffic_analyzer.sh connections"
echo "3. Generate report: ./traffic_analyzer.sh report"
echo "4. View interfaces: ./traffic_analyzer.sh interfaces"
echo "5. Real-time monitor: watch## 🚨 **Intrusion Detection & Prevention**

### **Step 1: Create Advanced Intrusion Detection System**

```bash
cat > ~/intrusion_detection.sh << 'EOF'
#!/bin/bash

# TwinTower Intrusion Detection & Prevention System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
DETECTION_TYPE="${2:-realtime}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# IDS Configuration
IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="$IDS_LOG_DIR/detection.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$IDS_DETECTION_LOG"
}

# Function to setup IDS infrastructure
setup_ids_infrastructure() {
    log_message "🔧 Setting up IDS infrastructure..."
    
    # Create directories
    sudo mkdir -p "$IDS_CONFIG_DIR" "$IDS_RULES_DIR" "$IDS_LOG_DIR"
    sudo touch "$IDS_ALERT_LOG" "$IDS_DETECTION_LOG"
    
    # Create main IDS configuration
    cat << IDS_CONFIG_EOF | sudo tee "$IDS_CONFIG_DIR/ids.conf"
# TwinTower IDS Configuration
IDS_ENABLED=true
IDS_MODE="monitor"
IDS_SENSITIVITY="medium"
IDS_LOGGING_LEVEL="info"
IDS_ALERT_THRESHOLD=5
IDS_BLOCK_THRESHOLD=10
IDS_WHITELIST_ENABLED=true
IDS_LEARNING_MODE=false
IDS_REALTIME_ALERTS=true
IDS_EMAIL_ALERTS=false
IDS_WEBHOOK_ALERTS=false
IDS_AUTO_BLOCK=false
IDS_BLOCK_DURATION=3600
IDS_CLEANUP_INTERVAL=86400
IDS_CONFIG_EOF

    # Create whitelist configuration
    cat << WHITELIST_EOF | sudo tee "$IDS_CONFIG_DIR/whitelist.conf"
# TwinTower IDS Whitelist
# Trusted IP addresses and networks
100.64.0.0/10
192.168.1.0/24
127.0.0.0/8
::1/128

# Trusted processes
/usr/bin/ssh
/usr/bin/docker
/usr/bin/tailscale
/usr/sbin/sshd
WHITELIST_EOF

    log_message "✅ IDS infrastructure created"
}

# Function to create detection rules
create_detection_rules() {
    log_message "📋 Creating intrusion detection rules..."
    
    # SSH Attack Detection Rules
    cat << SSH_RULES_EOF | sudo tee "$IDS_RULES_DIR/ssh_attacks.rules"
# SSH Attack Detection Rules
# Rule format: PATTERN|SEVERITY|ACTION|DESCRIPTION

# Brute force attacks
authentication failure.*ssh|HIGH|ALERT|SSH brute force attempt
Failed password.*ssh|MEDIUM|COUNT|SSH failed password
Invalid user.*ssh|HIGH|ALERT|SSH invalid user attempt
ROOT LOGIN REFUSED.*ssh|HIGH|ALERT|SSH root login attempt

# SSH scanning
Connection closed.*ssh.*preauth|LOW|COUNT|SSH connection scanning
Connection reset.*ssh|LOW|COUNT|SSH connection reset
Received disconnect.*ssh|MEDIUM|COUNT|SSH premature disconnect

# Suspicious SSH activity
User.*not allowed.*ssh|HIGH|ALERT|SSH user not allowed
Maximum authentication attempts.*ssh|HIGH|ALERT|SSH max auth attempts
Timeout.*ssh|MEDIUM|COUNT|SSH timeout

# SSH protocol violations
Protocol.*ssh|HIGH|ALERT|SSH protocol violation
Bad protocol version.*ssh|HIGH|ALERT|SSH bad protocol version
SSH_RULES_EOF

    # Network Attack Detection Rules
    cat << NET_RULES_EOF | sudo tee "$IDS_RULES_DIR/network_attacks.rules"
# Network Attack Detection Rules

# Port scanning
nmap|HIGH|ALERT|Nmap scan detected
masscan|HIGH|ALERT|Masscan detected
SYN flood|HIGH|ALERT|SYN flood attack
Port.*scan|MEDIUM|ALERT|Port scan detected

# DDoS attacks
DDOS|HIGH|BLOCK|DDoS attack detected
flood|HIGH|ALERT|Flood attack detected
amplification|HIGH|ALERT|Amplification attack

# Network intrusion
backdoor|HIGH|BLOCK|Backdoor detected
trojan|HIGH|BLOCK|Trojan detected
botnet|HIGH|BLOCK|Botnet activity
malware|HIGH|BLOCK|Malware detected

# Protocol attacks
DNS.*poison|HIGH|ALERT|DNS poisoning attempt
ARP.*spoof|HIGH|ALERT|ARP spoofing detected
ICMP.*flood|MEDIUM|ALERT|ICMP flood detected
NET_RULES_EOF

    # Web Attack Detection Rules
    cat << WEB_RULES_EOF | sudo tee "$IDS_RULES_DIR/web_attacks.rules"
# Web Attack Detection Rules

# SQL Injection
union.*select|HIGH|ALERT|SQL injection attempt
drop.*table|HIGH|ALERT|SQL injection (DROP)
insert.*into|MEDIUM|COUNT|SQL injection (INSERT)
update.*set|MEDIUM|COUNT|SQL injection (UPDATE)

# XSS attacks
<script|HIGH|ALERT|XSS attack attempt
javascript:|HIGH|ALERT|XSS javascript injection
eval\(|HIGH|ALERT|XSS eval injection
alert\(|MEDIUM|COUNT|XSS alert injection

# Directory traversal
\.\./|HIGH|ALERT|Directory traversal attempt
etc/passwd|HIGH|ALERT|System file access attempt
etc/shadow|HIGH|ALERT|Shadow file access attempt

# Command injection
;.*rm|HIGH|ALERT|Command injection (rm)
;.*cat|MEDIUM|COUNT|Command injection (cat)
;.*wget|HIGH|ALERT|Command injection (wget)
;.*curl|HIGH|ALERT|Command injection (curl)
WEB_RULES_EOF

    # System Attack Detection Rules
    cat << SYS_RULES_EOF | sudo tee "$IDS_RULES_DIR/system_attacks.rules"
# System Attack Detection Rules

# Privilege escalation
sudo.*passwd|HIGH|ALERT|Sudo password change attempt
su.*root|HIGH|ALERT|Root escalation attempt
chmod.*777|MEDIUM|COUNT|Dangerous permissions change
chown.*root|HIGH|ALERT|Root ownership change

# File system attacks
rm.*rf|HIGH|ALERT|Dangerous file deletion
find.*exec|MEDIUM|COUNT|Find command execution
crontab.*e|MEDIUM|COUNT|Crontab modification

# Process injection
ptrace|HIGH|ALERT|Process injection attempt
gdb.*attach|HIGH|ALERT|Debugger attachment
strace.*p|MEDIUM|COUNT|Process tracing

# Resource exhaustion
fork.*bomb|HIGH|BLOCK|Fork bomb detected
memory.*exhaustion|HIGH|ALERT|Memory exhaustion
CPU.*100|MEDIUM|COUNT|High CPU usage
SYS_RULES_EOF

    log_message "✅ Detection rules created"
}

# Function to create real-time detection engine
create_detection_engine() {
    log_message "⚙️ Creating real-time detection engine..."
    
    cat << DETECTION_ENGINE_EOF > ~/ids_detection_engine.sh
#!/bin/bash

# TwinTower IDS Real-time Detection Engine
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="\$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="\$IDS_LOG_DIR/detection.log"
IDS_STATE_FILE="/var/lib/twintower-ids/state"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
source "\$IDS_CONFIG_DIR/ids.conf"

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$IDS_DETECTION_LOG"
}

alert_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - ALERT: \$1" | tee -a "\$IDS_ALERT_LOG"
}

# Function to check if IP is whitelisted
is_whitelisted() {
    local ip="\$1"
    local whitelist_file="\$IDS_CONFIG_DIR/whitelist.conf"
    
    if [ -f "\$whitelist_file" ]; then
        # Simple IP matching (in production use more sophisticated matching)
        if grep -q "\$ip" "\$whitelist_file"; then
            return 0
        fi
        
        # Check network ranges (simplified)
        if [[ "\$ip" =~ ^192\.168\.1\. ]] && grep -q "192.168.1.0/24" "\$whitelist_file"; then
            return 0
        fi
        
        if [[ "\$ip" =~ ^100\.64\. ]] && grep -q "100.64.0.0/10" "\$whitelist_file"; then
            return 0
        fi
    fi
    
    return 1
}

# Function to process detection rule
process_rule() {
    local rule="\$1"
    local log_line="\$2"
    local source_ip="\$3"
    
    # Parse rule: PATTERN|SEVERITY|ACTION|DESCRIPTION
    local pattern=\$(echo "\$rule" | cut -d'|' -f1)
    local severity=\$(echo "\$rule" | cut -d'|' -f2)
    local action=\$(echo "\$rule" | cut -d'|' -f3)
    local description=\$(echo "\$rule" | cut -d'|' -f4)
    
    # Check if log line matches pattern
    if echo "\$log_line" | grep -qi "\$pattern"; then
        # Skip if whitelisted
        if is_whitelisted "\$source_ip"; then
            return 0
        fi
        
        # Execute action based on severity and configuration
        case "\$action" in
            "ALERT")
                alert_message "[\$severity] \$description - IP: \$source_ip"
                if [ "\$IDS_REALTIME_ALERTS" = "true" ]; then
                    send_alert "\$severity" "\$description" "\$source_ip"
                fi
                ;;
            "BLOCK")
                alert_message "[\$severity] BLOCKING - \$description - IP: \$source_ip"
                if [ "\$IDS_AUTO_BLOCK" = "true" ]; then
                    block_ip "\$source_ip" "\$description"
                fi
                ;;
            "COUNT")
                increment_counter "\$source_ip" "\$description"
                ;;
        esac
    fi
}

# Function to extract source IP from log line
extract_source_ip() {
    local log_line="\$1"
    
    # Extract IP using various patterns
    local ip=\$(echo "\$log_line" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    
    if [ -z "\$ip" ]; then
        ip="unknown"
    fi
    
    echo "\$ip"
}

# Function to increment counter for repeated events
increment_counter() {
    local ip="\$1"
    local event="\$2"
    
    local counter_file="/var/lib/twintower-ids/counters/\$ip"
    sudo mkdir -p "/var/lib/twintower-ids/counters"
    
    local count=1
    if [ -f "\$counter_file" ]; then
        count=\$(cat "\$counter_file")
        count=\$((count + 1))
    fi
    
    echo "\$count" > "\$counter_file"
    
    # Check if threshold exceeded
    if [ "\$count" -ge "\$IDS_ALERT_THRESHOLD" ]; then
        alert_message "[THRESHOLD] IP \$ip exceeded threshold (\$count events) - \$event"
        
        if [ "\$count" -ge "\$IDS_BLOCK_THRESHOLD" ] && [ "\$IDS_AUTO_BLOCK" = "true" ]; then
            block_ip "\$ip" "Threshold exceeded: \$event"
        fi
    fi
}

# Function to block IP address
block_ip() {
    local ip="\$1"
    local reason="\$2"
    
    log_message "🚫 Blocking IP: \$ip - Reason: \$reason"
    
    # Block using UFW
    sudo ufw deny from "\$ip" comment "IDS Block: \$reason"
    
    # Schedule unblock
    if [ "\$IDS_BLOCK_DURATION" -gt 0 ]; then
        echo "sudo ufw delete deny from \$ip" | at now + "\$IDS_BLOCK_DURATION seconds" 2>/dev/null || true
    fi
}

# Function to send alert
send_alert() {
    local severity="\$1"
    local description="\$2"
    local source_ip="\$3"
    
    # Log alert
    log_message "🚨 ALERT [\$severity]: \$description from \$source_ip"
    
    # Send email alert if configured
    if [ "\$IDS_EMAIL_ALERTS" = "true" ] && [ -n "\$IDS_EMAIL_RECIPIENT" ]; then
        echo "IDS Alert: \$description from \$source_ip" | mail -s "TwinTower IDS Alert [\$severity]" "\$IDS_EMAIL_RECIPIENT"
    fi
    
    # Send webhook alert if configured
    if [ "\$IDS_WEBHOOK_ALERTS" = "true" ] && [ -n "\$IDS_WEBHOOK_URL" ]; then
        curl -X POST -H "Content-Type: application/json" \
            -d "{\"alert\":\"TwinTower IDS Alert\",\"severity\":\"\$severity\",\"description\":\"\$description\",\"source_ip\":\"\$source_ip\"}" \
            "\$IDS_WEBHOOK_URL" 2>/dev/null || true
    fi
}

# Function to monitor log files
monitor_logs() {
    log_message "🔍 Starting real-time log monitoring..."
    
    # Monitor multiple log files
    tail -f /var/log/auth.log /var/log/syslog /var/log/ufw.log /var/log/nginx/access.log 2>/dev/null | \
    while read log_line; do
        # Extract source IP
        source_ip=\$(extract_source_ip "\$log_line")
        
        # Process against all rule files
        for rule_file in "\$IDS_RULES_DIR"/*.rules; do
            if [ -f "\$rule_file" ]; then
                while IFS= read -r rule; do
                    # Skip comments and empty lines
                    if [[ "\$rule" =~ ^#.*\$ ]] || [[ -z "\$rule" ]]; then
                        continue
                    fi
                    
                    process_rule "\$rule" "\$log_line" "\$source_ip"
                done < "\$rule_file"
            fi
        done
    done
}

# Function to generate IDS report
generate_ids_report() {
    local report_file="/tmp/ids_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower IDS Report
==================
Generated: \$(date)
Tower: \$(hostname)

IDS Configuration:
-----------------
Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")
Mode: \$IDS_MODE
Sensitivity: \$IDS_SENSITIVITY
Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "ENABLED" || echo "DISABLED")

Detection Statistics (Last 24 hours):
------------------------------------
Total Alerts: \$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
High Severity: \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
Medium Severity: \$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
Low Severity: \$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")

Blocked IPs:
-----------
\$(sudo ufw status | grep "IDS Block" || echo "No IPs currently blocked")

Top Alert Sources:
-----------------
\$(grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -10)

Recent High-Priority Alerts:
----------------------------
\$(grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -10)

Rule Effectiveness:
------------------
SSH Attacks: \$(grep -c "SSH.*attempt" "\$IDS_ALERT_LOG" || echo "0")
Network Attacks: \$(grep -c "scan.*detected" "\$IDS_ALERT_LOG" || echo "0")
Web Attacks: \$(grep -c "injection.*attempt" "\$IDS_ALERT_LOG" || echo "0")
System Attacks: \$(grep -c "escalation.*attempt" "\$IDS_ALERT_LOG" || echo "0")

REPORT_EOF

    log_message "📋 IDS report generated: \$report_file"
    echo "\$report_file"
}

# Function to start IDS daemon
start_ids_daemon() {
    log_message "🚀 Starting IDS daemon..."
    
    # Create state directory
    sudo mkdir -p /var/lib/twintower-ids/counters
    
    # Start monitoring
    monitor_logs
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_ids_daemon
        ;;
    "test")
        # Test detection rules
        echo "Testing IDS rules..."
        echo "authentication failure ssh" | while read line; do
            source_ip=\$(extract_source_ip "\$line")
            process_rule "authentication failure.*ssh|HIGH|ALERT|SSH brute force test" "\$line" "\$source_ip"
        done
        ;;
    "report")
        generate_ids_report
        ;;
    "status")
        echo "IDS Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")"
        echo "Active Rules: \$(find "\$IDS_RULES_DIR" -name "*.rules" | wc -l)"
        echo "Recent Alerts: \$(tail -n 5 "\$IDS_ALERT_LOG" | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <daemon|test|report|status>"
        exit 1
        ;;
esac
DETECTION_ENGINE_EOF

    chmod +x ~/ids_detection_engine.sh
    
    log_message "✅ Detection engine created"
}

# Function to create IDS management dashboard
create_ids_dashboard() {
    log_message "📊 Creating IDS management dashboard..."
    
    cat << IDS_DASHBOARD_EOF > ~/ids_dashboard.sh
#!/bin/bash

# TwinTower IDS Management Dashboard
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_ALERT_LOG="/var/log/twintower-ids/alerts.log"
IDS_DETECTION_LOG="/var/log/twintower-ids/detection.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
if [ -f "\$IDS_CONFIG_DIR/ids.conf" ]; then
    source "\$IDS_CONFIG_DIR/ids.conf"
fi

clear
echo -e "\${BLUE}🚨 TwinTower IDS Management Dashboard\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# IDS Status
echo -e "\${YELLOW}🛡️ IDS Status\${NC}"
echo "-------------"
if [ "\$IDS_ENABLED" = "true" ]; then
    echo -e "IDS Status: \${GREEN}✅ ENABLED\${NC}"
else
    echo -e "IDS Status: \${RED}❌ DISABLED\${NC}"
fi

echo -e "Mode: \${GREEN}\$IDS_MODE\${NC}"
echo -e "Sensitivity: \${GREEN}\$IDS_SENSITIVITY\${NC}"
echo -e "Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "\${GREEN}✅ ENABLED\${NC}" || echo "\${RED}❌ DISABLED\${NC}")"
echo

# Detection Statistics
echo -e "\${YELLOW}📊 Detection Statistics (Last 24 hours)\${NC}"
echo "--------------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    TOTAL_ALERTS=\$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
    HIGH_ALERTS=\$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
    MEDIUM_ALERTS=\$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
    LOW_ALERTS=\$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")
    
    echo -e "Total Alerts: \${BLUE}\$TOTAL_ALERTS\${NC}"
    echo -e "High Severity: \${RED}\$HIGH_ALERTS\${NC}"
    echo -e "Medium Severity: \${YELLOW}\$MEDIUM_ALERTS\${NC}"
    echo -e "Low Severity: \${GREEN}\$LOW_ALERTS\${NC}"
else
    echo -e "No alert data available"
fi
echo

# Active Rules
echo -e "\${YELLOW}📋 Active Rules\${NC}"
echo "---------------"
if [ -d "\$IDS_CONFIG_DIR/rules" ]; then
    RULE_COUNT=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" -exec wc -l {} + | tail -1 | awk '{print \$1}' || echo "0")
    RULE_FILES=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" | wc -l)
    echo -e "Rule Files: \${GREEN}\$RULE_FILES\${NC}"
    echo -e "Total Rules: \${GREEN}\$RULE_COUNT\${NC}"
    
    for rule_file in "\$IDS_CONFIG_DIR/rules"/*.rules; do
        if [ -f "\$rule_file" ]; then
            rule_name=\$(basename "\$rule_file" .rules)
            rule_count=\$(grep -c "^[^#]" "\$rule_file" || echo "0")
            echo -e "  \${GREEN}•\${NC} \$rule_name: \$rule_count rules"
        fi
    done
else
    echo -e "No rules configured"
fi
echo

# Recent Alerts
echo -e "\${YELLOW}🚨 Recent High-Priority Alerts\${NC}"
echo "------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -5 | while read line; do
        timestamp=\$(echo "\$line" | awk '{print \$1, \$2, \$3}')
        alert_msg=\$(echo "\$line" | cut -d'-' -f3-)
        echo -e "  \${RED}⚠️\${NC} \$timestamp:\$alert_msg"
    done
    
    if [ \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG") -eq 0 ]; then
        echo -e "  \${GREEN}✅ No high-priority alerts\${NC}"
    fi
else
    echo -e "No alert data available"
fi
echo

# Blocked IPs
echo -e "\${YELLOW}🚫 Blocked IPs\${NC}"
echo "-------------"
BLOCKED_IPS=\$(sudo ufw status | grep "IDS Block" | wc -l)
if [ \$BLOCKED_IPS -gt 0 ]; then
    echo -e "Currently Blocked: \${RED}\$BLOCKED_IPS\${NC}"
    sudo ufw status | grep "IDS Block" | head -5 | while read line; do
        echo -e "  \${RED}🔒\${NC} \$line"
    done
else
    echo -e "Currently Blocked: \${GREEN}0\${NC}"
fi
echo

# Top Alert Sources
echo -e "\${YELLOW}📈 Top Alert Sources\${NC}"
echo "--------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    echo "Top 5 IPs by alert count:"
    grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -5 | while read count ip; do
        echo -e "  \${RED}\$ip\${NC}: \$count alerts"
    done
else
    echo -e "No alert data available"
fi
echo

# System Health
echo -e "\${YELLOW}💓 System Health\${NC}"
echo "----------------"
IDS_PROCESS=\$(pgrep -f "ids_detection_engine.sh" | wc -l)
if [ \$IDS_PROCESS -gt 0 ]; then
    echo -e "Detection Engine: \${GREEN}✅ Running\${NC}"
else
    echo -e "Detection Engine: \${RED}❌ Stopped\${NC}"
fi

LOG_SIZE=\$(du -h "\$IDS_ALERT_LOG" 2>/dev/null | cut -f1 || echo "0")
echo -e "Alert Log Size: \${GREEN}\$LOG_SIZE\${NC}"

DISK_USAGE=\$(df -h /var/log | tail -1 | awk '{print \$5}')
echo -e "Log Disk Usage: \${GREEN}\$DISK_USAGE\${NC}"
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Start IDS: ./ids_detection_engine.sh daemon"
echo "2. View alerts: tail -f \$IDS_ALERT_LOG"
echo "3. Generate report: ./ids_detection_engine.sh report"
echo "4. Test rules: ./ids_detection_engine.sh test"
echo "5. View blocked IPs: sudo ufw status | grep 'IDS Block'"

echo
echo -e "\${BLUE}====================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
IDS_DASHBOARD_EOF

    chmod +x ~/ids_dashboard.sh
    
    log_message "✅ IDS dashboard created"
}

# Function to create IDS service
create_ids_service() {
    log_message "⚙️ Creating IDS systemd service..."
    
    cat << IDS_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-ids.service
[Unit]
Description=TwinTower Intrusion Detection System
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/ids_detection_engine.sh daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
IDS_SERVICE_EOF

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-ids.service
    
    log_message "✅ IDS service created"
}

# Function to test IDS system
test_ids_system() {
    log_message "🧪 Testing IDS system..."
    
    cat << IDS_TEST_EOF > ~/test_ids_system.sh
#!/bin/bash

# TwinTower IDS System Test
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower IDS System Test\${NC}"
echo -e "\${BLUE}===========================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test IDS configuration
echo -e "\${YELLOW}🔧 Testing IDS Configuration\${NC}"
echo "----------------------------"
run_test "IDS config directory exists" "[ -d '\$IDS_CONFIG_DIR' ]"
run_test "IDS rules directory exists" "[ -d '\$IDS_RULES_DIR' ]"
run_test "IDS configuration file exists" "[ -f '\$IDS_CONFIG_DIR/ids.conf' ]"
run_test "IDS whitelist file exists" "[ -f '\$IDS_CONFIG_DIR/whitelist.conf' ]"

# Test detection rules
echo -e "\${YELLOW}📋 Testing Detection Rules\${NC}"
echo "--------------------------"
run_test "SSH attack rules exist" "[ -f '\$IDS_RULES_DIR/ssh_attacks.rules' ]"
run_test "Network attack rules exist" "[ -f '\$IDS_RULES_DIR/network_attacks.rules' ]"
run_test "Web attack rules exist" "[ -f '\$IDS_RULES_DIR/web_attacks.rules' ]"
run_test "System attack rules exist" "[ -f '\$IDS_RULES_DIR/system_attacks.rules' ]"

# Test IDS components
echo -e "\${YELLOW}# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access policies..."
    
    # Internal Network Policy
    cat << INTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/internal-network.json"
{
    "policy_name": "InternalNetwork",
    "description": "Internal network access policy",
    "version": "1.0",
    "priority": 250,
    "conditions": {
        "source_networks": ["192.168.1.0/24", "172.16.0.0/12", "10.0.0.0/8"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp", "udp", "icmp"],
        "encryption_required": false,
        "authentication_required": true
    },
    "permissions": {
        "ssh_access": true,
        "web_access": true,
        "api_access": true,
        "file_access": true
    },
    "restrictions": {
        "bandwidth_limit": "1Gbps",
        "connection_limit": 100,
        "rate_limit": "moderate"
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": false
    }
}
INTERNAL_NET_EOF

    # External Network Policy
    cat << EXTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/external-network.json"
{
    "policy_name": "ExternalNetwork",
    "description": "External network access policy (high security)",
    "version": "1.0",
    "priority": 500,
    "conditions": {
        "source_networks": ["0.0.0.0/0"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp"],
        "encryption_required": true,
        "authentication_required": true,
        "vpn_required": true
    },
    "permissions": {
        "ssh_access": false,
        "web_access": true,
        "api_access": false,
        "file_access": false
    },
    "restrictions": {
        "bandwidth_limit": "10Mbps",
        "connection_limit": 5,
        "rate_limit": "strict",
        "geolocation_required": true,
        "time_limited": true
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": true,
        "threat_intelligence": true
    }
}
EXTERNAL_NET_EOF

    log_message "✅ Network-based policies created"
}

# Function to create zero-trust enforcement engine
create_zt_enforcement() {
    log_message "⚙️ Creating zero-trust enforcement engine..."
    
    cat << ZT_ENGINE_EOF > ~/zt_enforcement_engine.sh
#!/bin/bash

# TwinTower Zero-Trust Enforcement Engine
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_LOG_FILE"
}

audit_log() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_AUDIT_LOG"
}

# Function to validate user access
validate_user_access() {
    local user="\$1"
    local source_ip="\$2"
    local requested_service="\$3"
    local auth_method="\$4"
    
    log_message "🔍 Validating access for user: \$user from \$source_ip"
    
    # Check if user exists
    if ! id "\$user" &>/dev/null; then
        audit_log "DENY: User \$user does not exist"
        return 1
    fi
    
    # Load and evaluate policies
    local policy_result=0
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            if evaluate_policy "\$policy_file" "\$user" "\$source_ip" "\$requested_service" "\$auth_method"; then
                policy_result=1
                break
            fi
        fi
    done
    
    if [ \$policy_result -eq 1 ]; then
        audit_log "ALLOW: User \$user access granted for \$requested_service"
        create_session "\$user" "\$source_ip" "\$requested_service"
        return 0
    else
        audit_log "DENY: User \$user access denied for \$requested_service"
        return 1
    fi
}

# Function to evaluate policy
evaluate_policy() {
    local policy_file="\$1"
    local user="\$2"
    local source_ip="\$3"
    local requested_service="\$4"
    local auth_method="\$5"
    
    # Parse JSON policy (simplified - in production use jq)
    local policy_name=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
    
    log_message "📋 Evaluating policy: \$policy_name"
    
    # Check user conditions
    if grep -q '"users"' "\$policy_file"; then
        local users=\$(grep '"users"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$users" == *"\$user"* ]]; then
            log_message "✅ User \$user matches policy \$policy_name"
        else
            log_message "❌ User \$user does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check network conditions
    if grep -q '"source_networks"' "\$policy_file"; then
        local networks=\$(grep '"source_networks"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if check_network_match "\$source_ip" "\$networks"; then
            log_message "✅ Source IP \$source_ip matches policy \$policy_name"
        else
            log_message "❌ Source IP \$source_ip does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check time restrictions
    if grep -q '"time_restrictions"' "\$policy_file"; then
        if check_time_restrictions "\$policy_file"; then
            log_message "✅ Time restrictions satisfied for policy \$policy_name"
        else
            log_message "❌ Time restrictions not satisfied for policy \$policy_name"
            return 1
        fi
    fi
    
    # Check service permissions
    if grep -q '"\$requested_service"' "\$policy_file"; then
        local service_allowed=\$(grep '"\$requested_service"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
        if [[ "\$service_allowed" == "true" ]]; then
            log_message "✅ Service \$requested_service allowed in policy \$policy_name"
            return 0
        else
            log_message "❌ Service \$requested_service not allowed in policy \$policy_name"
            return 1
        fi
    fi
    
    return 0
}

# Function to check network match
check_network_match() {
    local source_ip="\$1"
    local networks="\$2"
    
    # Simple network matching (in production use ipcalc or similar)
    if [[ "\$networks" == *"100.64.0.0/10"* ]] && [[ "\$source_ip" == 100.64.* ]]; then
        return 0
    elif [[ "\$networks" == *"192.168.1.0/24"* ]] && [[ "\$source_ip" == 192.168.1.* ]]; then
        return 0
    elif [[ "\$networks" == *"0.0.0.0/0"* ]]; then
        return 0
    fi
    
    return 1
}

# Function to check time restrictions
check_time_restrictions() {
    local policy_file="\$1"
    
    local current_hour=\$(date +%H)
    local current_day=\$(date +%A | tr '[:upper:]' '[:lower:]')
    
    # Check allowed hours (simplified)
    if grep -q '"allowed_hours"' "\$policy_file"; then
        local allowed_hours=\$(grep '"allowed_hours"' "\$policy_file" | cut -d'"' -f4)
        local start_hour=\$(echo "\$allowed_hours" | cut -d'-' -f1 | cut -d':' -f1)
        local end_hour=\$(echo "\$allowed_hours" | cut -d'-' -f2 | cut -d':' -f1)
        
        if [ "\$current_hour" -ge "\$start_hour" ] && [ "\$current_hour" -le "\$end_hour" ]; then
            return 0
        else
            return 1
        fi
    fi
    
    # Check allowed days (simplified)
    if grep -q '"allowed_days"' "\$policy_file"; then
        local allowed_days=\$(grep '"allowed_days"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$allowed_days" == *"\$current_day"* ]]; then
            return 0
        else
            return 1
        fi
    fi
    
    return 0
}

# Function to create session
create_session() {
    local user="\$1"
    local source_ip="\$2"
    local service="\$3"
    
    sudo mkdir -p "\$ZT_SESSION_DIR"
    
    local session_id=\$(date +%s)_\$(echo "\$user\$source_ip" | md5sum | cut -d' ' -f1 | head -c 8)
    local session_file="\$ZT_SESSION_DIR/\$session_id.session"
    
    cat > "\$session_file" << SESSION_EOF
{
    "session_id": "\$session_id",
    "user": "\$user",
    "source_ip": "\$source_ip",
    "service": "\$service",
    "start_time": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "last_activity": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "status": "active"
}
SESSION_EOF

    log_message "✅ Session created: \$session_id for user \$user"
}

# Function to monitor active sessions
monitor_sessions() {
    log_message "📊 Monitoring active sessions..."
    
    if [ -d "\$ZT_SESSION_DIR" ]; then
        local active_sessions=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
        log_message "Active sessions: \$active_sessions"
        
        # Check for expired sessions
        for session_file in "\$ZT_SESSION_DIR"/*.session; do
            if [ -f "\$session_file" ]; then
                local session_id=\$(basename "\$session_file" .session)
                local start_time=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
                
                # Check if session is older than 1 hour (3600 seconds)
                local current_time=\$(date +%s)
                local session_time=\$(date -d "\$start_time" +%s)
                local age=\$((current_time - session_time))
                
                if [ \$age -gt 3600 ]; then
                    log_message "⏰ Expiring session: \$session_id"
                    rm -f "\$session_file"
                fi
            fi
        done
    fi
}

# Function to generate compliance report
generate_compliance_report() {
    local report_file="/tmp/zt_compliance_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Zero-Trust Compliance Report
====================================
Generated: \$(date)
Tower: \$(hostname)

Policy Compliance:
-----------------
Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
Enforcement Status: \$(grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf" && echo "ENABLED" || echo "DISABLED")

Access Statistics (Last 24 hours):
---------------------------------
Total Access Attempts: \$(grep -c "Validating access" "\$ZT_LOG_FILE" || echo "0")
Successful Authentications: \$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
Denied Access Attempts: \$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")

Active Sessions:
---------------
Current Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)

Recent Security Events:
----------------------
\$(tail -n 20 "\$ZT_AUDIT_LOG" 2>/dev/null || echo "No recent events")

Policy Violations:
-----------------
\$(grep "DENY:" "\$ZT_AUDIT_LOG" | tail -10 || echo "No recent violations")

Recommendations:
---------------
\$([ \$(grep -c "DENY:" "\$ZT_AUDIT_LOG") -gt 10 ] && echo "High number of access denials - review policies" || echo "Access patterns appear normal")

REPORT_EOF

    log_message "📋 Compliance report generated: \$report_file"
    echo "\$report_file"
}

# Main execution
case "\${1:-monitor}" in
    "validate")
        validate_user_access "\$2" "\$3" "\$4" "\$5"
        ;;
    "monitor")
        log_message "🚀 Starting zero-trust monitoring..."
        while true; do
            monitor_sessions
            sleep 300
        done
        ;;
    "report")
        generate_compliance_report
        ;;
    "status")
        echo "Zero-Trust Status:"
        echo "=================="
        echo "Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)"
        echo "Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)"
        echo "Recent Events: \$(tail -n 5 "\$ZT_AUDIT_LOG" 2>/dev/null | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <validate|monitor|report|status>"
        echo "  validate <user> <source_ip> <service> <auth_method>"
        exit 1
        ;;
esac
ZT_ENGINE_EOF

    chmod +x ~/zt_enforcement_engine.sh
    
    log_message "✅ Zero-trust enforcement engine created"
}

# Function to create zero-trust monitoring dashboard
create_zt_dashboard() {
    log_message "📊 Creating zero-trust monitoring dashboard..."
    
    cat << ZT_DASHBOARD_EOF > ~/zt_dashboard.sh
#!/bin/bash

# TwinTower Zero-Trust Dashboard
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔒 TwinTower Zero-Trust Dashboard\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Zero-Trust Status
echo -e "\${YELLOW}🛡️ Zero-Trust Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_CONFIG_DIR/zero-trust.conf" ]; then
    if grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf"; then
        echo -e "Zero-Trust: \${GREEN}✅ ENABLED\${NC}"
    else
        echo -e "Zero-Trust: \${RED}❌ DISABLED\${NC}"
    fi
else
    echo -e "Zero-Trust: \${RED}❌ NOT CONFIGURED\${NC}"
fi

# Policy Status
POLICY_COUNT=\$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
echo -e "Active Policies: \${GREEN}\$POLICY_COUNT\${NC}"

# Session Status
if [ -d "\$ZT_SESSION_DIR" ]; then
    SESSION_COUNT=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
    echo -e "Active Sessions: \${GREEN}\$SESSION_COUNT\${NC}"
else
    echo -e "Active Sessions: \${YELLOW}0\${NC}"
fi
echo

# Access Statistics
echo -e "\${YELLOW}📊 Access Statistics (Last 24 hours)\${NC}"
echo "-----------------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    ALLOW_COUNT=\$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
    DENY_COUNT=\$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")
    TOTAL_COUNT=\$((ALLOW_COUNT + DENY_COUNT))
    
    echo -e "Total Requests: \${BLUE}\$TOTAL_COUNT\${NC}"
    echo -e "Allowed: \${GREEN}\$ALLOW_COUNT\${NC}"
    echo -e "Denied: \${RED}\$DENY_COUNT\${NC}"
    
    if [ \$TOTAL_COUNT -gt 0 ]; then
        SUCCESS_RATE=\$(echo "scale=2; \$ALLOW_COUNT * 100 / \$TOTAL_COUNT" | bc -l 2>/dev/null || echo "0")
        echo -e "Success Rate: \${GREEN}\$SUCCESS_RATE%\${NC}"
    fi
else
    echo -e "No audit data available"
fi
echo

# Active Policies
echo -e "\${YELLOW}📋 Active Policies\${NC}"
echo "------------------"
if [ -d "\$ZT_POLICIES_DIR" ]; then
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            POLICY_NAME=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
            PRIORITY=\$(grep '"priority"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
            echo -e "  \${GREEN}•\${NC} \$POLICY_NAME (Priority: \$PRIORITY)"
        fi
    done
else
    echo -e "No policies configured"
fi
echo

# Recent Events
echo -e "\${YELLOW}🔍 Recent Security Events\${NC}"
echo "-------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    tail -n 5 "\$ZT_AUDIT_LOG" | while read line; do
        if [[ "\$line" == *"ALLOW:"* ]]; then
            echo -e "\${GREEN}✅ \$line\${NC}"
        elif [[ "\$line" == *"DENY:"* ]]; then
            echo -e "\${RED}❌ \$line\${NC}"
        else
            echo -e "\${BLUE}ℹ️  \$line\${NC}"
        fi
    done
else
    echo -e "No recent events"
fi
echo

# Active Sessions
echo -e "\${YELLOW}👥 Active Sessions\${NC}"
echo "------------------"
if [ -d "\$ZT_SESSION_DIR" ]; then
    for session_file in "\$ZT_SESSION_DIR"/*.session; do
        if [ -f "\$session_file" ]; then
            USER=\$(grep '"user"' "\$session_file" | cut -d'"' -f4)
            SOURCE_IP=\$(grep '"source_ip"' "\$session_file" | cut -d'"' -f4)
            SERVICE=\$(grep '"service"' "\$session_file" | cut -d'"' -f4)
            START_TIME=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
            echo -e "  \${GREEN}•\${NC} \$USER from \$SOURCE_IP (\$SERVICE) - \$START_TIME"
        fi
    done
    
    if [ \$SESSION_COUNT -eq 0 ]; then
        echo -e "No active sessions"
    fi
else
    echo -e "No session data available"
fi
echo

# Compliance Status
echo -e "\${YELLOW}📊 Compliance Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    RECENT_VIOLATIONS=\$(grep "DENY:" "\$ZT_AUDIT_LOG" | grep "\$(date '+%Y-%m-%d')" | wc -l)
    
    if [ \$RECENT_VIOLATIONS -eq 0 ]; then
        echo -e "Compliance Status: \${GREEN}✅ GOOD\${NC}"
    elif [ \$RECENT_VIOLATIONS -lt 5 ]; then
        echo -e "Compliance Status: \${YELLOW}⚠️  MODERATE\${NC}"
    else
        echo -e "Compliance Status: \${RED}❌ NEEDS ATTENTION\${NC}"
    fi
    
    echo -e "Today's Violations: \${RED}\$RECENT_VIOLATIONS\${NC}"
else
    echo -e "Compliance Status: \${YELLOW}⚠️  NO DATA\${NC}"
fi
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View policies: ls \$ZT_POLICIES_DIR/"
echo "2. Monitor sessions: ./zt_enforcement_engine.sh monitor"
echo "3. Generate report: ./zt_enforcement_engine.sh report"
echo "4. Check status: ./zt_enforcement_engine.sh status"

echo
echo -e "\${BLUE}=================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
ZT_DASHBOARD_EOF

    chmod +x ~/zt_dashboard.sh
    
    log_message "✅ Zero-trust monitoring dashboard created"
}

# Function to create zero-trust testing suite
create_zt_testing() {
    log_message "🧪 Creating zero-trust testing suite..."
    
    cat << ZT_TEST_EOF > ~/test_zero_trust.sh
#!/bin/bash

# TwinTower Zero-Trust Testing Suite
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Zero-Trust Testing Suite\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zero-trust configuration
echo -e "\${YELLOW}🔧 Testing Zero-Trust Configuration\${NC}"
echo "-----------------------------------"
run_test "ZT config directory exists" "[ -d '\$ZT_CONFIG_DIR' ]"
run_test "ZT policies directory exists" "[ -d '\$ZT_POLICIES_DIR' ]"
run_test "ZT configuration file exists" "[ -f '\$ZT_CONFIG_DIR/zero-trust.conf' ]"

# Test policy files
echo -e "\${YELLOW}📋 Testing Policy Files\${NC}"
echo "----------------------"
run_test "Admin users policy exists" "[ -f '\$ZT_POLICIES_DIR/admin-users.json' ]"
run_test "Standard users policy exists" "[ -f '\$ZT_POLICIES_DIR/standard-users.json' ]"
run_test "Service accounts policy exists" "[ -f '\$ZT_POLICIES_DIR/service-accounts.json' ]"
run_test "Trusted devices policy exists" "[ -f '\$ZT_POLICIES_DIR/trusted-devices.json' ]"
run_test "BYOD policy exists" "[ -f '\$ZT_POLICIES_DIR/byod-devices.json' ]"

# Test enforcement engine
echo -e "\${YELLOW}⚙️ Testing Enforcement Engine\${NC}"
echo "-----------------------------"
run_test "Enforcement engine exists" "[ -f '\$HOME/zt_enforcement_engine.sh' ]"
run_test "Enforcement engine executable" "[ -x '\$HOME/zt_enforcement_engine.sh' ]"
run_test "ZT dashboard exists" "[ -f '\$HOME/zt_dashboard.sh' ]"

# Test log files
echo -e "\${YELLOW}📊 Testing Logging\${NC}"
echo "------------------"
run_test "ZT log file exists" "[ -f '/var/log/zero-trust.log' ]"
run_test "ZT audit log exists" "[ -f '/var/log/zero-trust-audit.log' ]"

# Test policy validation
echo -e "\${YELLOW}🔍 Testing Policy Validation\${NC}"
echo "----------------------------"
for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
    if [ -f "\$policy_file" ]; then
        policy_name=\$(basename "\$policy_file" .json)
        run_test "Policy \$policy_name is valid JSON" "python3 -m json.tool '\$policy_file' > /dev/null"
    fi
done

# Test access scenarios
echo -e "\${YELLOW}🚪 Testing Access Scenarios\${NC}"
echo "---------------------------"
run_test "Admin access validation" "./zt_enforcement_engine.sh validate ubuntu 100.64.0.1 ssh_access publickey"
run_test "External access blocking" "! ./zt_enforcement_engine.sh validate hacker 1.2.3.4 ssh_access password"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zero-trust tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
ZT_TEST_EOF

    chmod +x ~/test_zero_trust.sh
    
    log_message "✅ Zero-trust testing suite created"
}

# Main execution
main() {
    echo -e "${BLUE}🔒 TwinTower Zero-Trust Access Control${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_zero_trust
            create_identity_policies
            create_device_policies
            create_network_policies
            create_zt_enforcement
            create_zt_dashboard
            create_zt_testing
            
            # Create session directory
            sudo mkdir -p /var/lib/zero-trust/sessions
            
            echo -e "${GREEN}✅ Zero-trust access control configured!${NC}"
            ;;
        "status")
            ~/zt_dashboard.sh
            ;;
        "test")
            ~/test_zero_trust.sh
            ;;
        "monitor")
            ~/zt_enforcement_engine.sh monitor
            ;;
        "report")
            ~/zt_enforcement_engine.sh report
            ;;
        "validate")
            ~/zt_enforcement_engine.sh validate "$POLICY_NAME" "$3" "$4" "$5"
            ;;
        "policies")
            if [ -d "$ZT_POLICIES_DIR" ]; then
                for policy_file in "$ZT_POLICIES_DIR"/*.json; do
                    if [ -f "$policy_file" ]; then
                        policy_name=$(grep '"policy_name"' "$policy_file" | cut -d'"' -f4)
                        priority=$(grep '"priority"' "$policy_file" | cut -d':' -f2 | tr -d ' ,')
                        echo -e "${BLUE}Policy: $policy_name${NC} (Priority: $priority)"
                    fi
                done
            else
                echo -e "${RED}❌ No policies configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|test|monitor|report|validate|policies> [policy_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/zero_trust_access.sh
```

### **Step 2: Execute Zero-Trust Setup**

```bash
# Setup zero-trust access control
./zero_trust_access.sh setup

# View zero-trust status
./zero_trust_access.sh status

# Test zero-trust implementation
./zero_trust_access.sh test

# Monitor zero-trust enforcement
./zero_trust_access.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## # Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone-based firewall rules..."
    
    # Create UFW application profiles for each zone
    create_ufw_app_profiles
    
    # Apply zone-specific rules
    for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "$zone_file" ]; then
            source "$zone_file"
            apply_zone_rules "$ZONE_NAME" "$zone_file"
        fi
    done
    
    log_message "✅ Zone-based firewall rules implemented"
}

# Function to create UFW application profiles
create_ufw_app_profiles() {
    log_message "📋 Creating UFW application profiles..."
    
    # TwinTower Management Profile
    cat << MGMT_PROFILE_EOF | sudo tee /etc/ufw/applications.d/twintower-management
[TwinTower-Management]
title=TwinTower Management Services
description=Administrative and monitoring interfaces
ports=3000:3099/tcp|6000:6099/tcp

[TwinTower-SSH]
title=TwinTower SSH Services
description=Custom SSH ports for towers
ports=2122,2222,2322/tcp

[TwinTower-GPU]
title=TwinTower GPU Services
description=GPU compute and ML workloads
ports=4000:4099/tcp|8000:8099/tcp

[TwinTower-Docker]
title=TwinTower Docker Services
description=Container orchestration and services
ports=2377/tcp|4789/udp|7946/tcp|7946/udp|5000:5099/tcp
MGMT_PROFILE_EOF

    # Reload UFW application profiles
    sudo ufw app update all
    
    log_message "✅ UFW application profiles created"
}

# Function to apply zone-specific rules
apply_zone_rules() {
    local zone_name="$1"
    local zone_file="$2"
    
    log_message "🔒 Applying rules for zone: $zone_name"
    
    # Source zone configuration
    source "$zone_file"
    
    case "$zone_name" in
        "DMZ")
            # DMZ zone rules - restrictive
            sudo ufw deny from any to any port 22 comment "DMZ: Block SSH"
            sudo ufw allow from any to any port 80 comment "DMZ: Allow HTTP"
            sudo ufw allow from any to any port 443 comment "DMZ: Allow HTTPS"
            sudo ufw limit from any to any port 8080 comment "DMZ: Limit Alt HTTP"
            ;;
        "INTERNAL")
            # Internal zone rules - moderate
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Internal: SSH Access"
                sudo ufw allow from "$network" to any app TwinTower-Docker comment "Internal: Docker Services"
            done
            ;;
        "TRUSTED")
            # Trusted zone rules - permissive
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" comment "Trusted: Full Access"
            done
            ;;
        "MANAGEMENT")
            # Management zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-Management comment "Management: Admin Access"
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Management: SSH Access"
            done
            ;;
        "GPU")
            # GPU zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-GPU comment "GPU: Compute Access"
            done
            ;;
    esac
    
    log_message "✅ Zone rules applied for: $zone_name"
}

# Function to create zone monitoring
create_zone_monitoring() {
    log_message "📊 Creating zone monitoring system..."
    
    cat << ZONE_MONITOR_EOF > ~/zone_monitor.sh
#!/bin/bash

# TwinTower Zone Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-300}"
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/zone-monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor zone traffic
monitor_zone_traffic() {
    local zone_name="\$1"
    local zone_networks="\$2"
    
    log_message "📈 Monitoring traffic for zone: \$zone_name"
    
    # Count connections per zone
    local connection_count=0
    
    IFS=',' read -ra NETWORKS <<< "\$zone_networks"
    for network in "\${NETWORKS[@]}"; do
        # Count active connections from this network
        local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
        connection_count=\$((connection_count + net_connections))
    done
    
    log_message "Zone \$zone_name: \$connection_count active connections"
    
    # Check for anomalies
    if [ "\$connection_count" -gt 100 ]; then
        log_message "🚨 HIGH ALERT: Unusual connection count for zone \$zone_name: \$connection_count"
    fi
}

# Function to analyze zone security events
analyze_zone_security() {
    local zone_name="\$1"
    
    log_message "🔍 Analyzing security events for zone: \$zone_name"
    
    # Check UFW logs for zone-related blocks
    local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$zone_name" || echo "0")
    
    if [ "\$blocked_today" -gt 0 ]; then
        log_message "🛡️ Zone \$zone_name: \$blocked_today blocked attempts today"
    fi
}

# Function to generate zone report
generate_zone_report() {
    local report_file="/tmp/zone_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Network Zone Report
============================
Generated: \$(date)
Tower: \$(hostname)

Zone Status Overview:
--------------------
REPORT_EOF

    # Analyze each zone
    for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "\$zone_file" ]; then
            source "\$zone_file"
            echo "Zone: \$ZONE_NAME (\$ZONE_TRUST_LEVEL trust)" >> "\$report_file"
            echo "  Networks: \$ZONE_NETWORKS" >> "\$report_file"
            echo "  Ports: \$ZONE_PORTS" >> "\$report_file"
            echo "  Status: Active" >> "\$report_file"
            echo "" >> "\$report_file"
        fi
    done
    
    cat >> "\$report_file" << REPORT_EOF

Recent Security Events:
----------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | tail -10)

Zone Traffic Summary:
--------------------
\$(sudo ss -s)

REPORT_EOF

    log_message "📋 Zone report generated: \$report_file"
    echo "\$report_file"
}

# Function to start zone monitoring
start_zone_monitoring() {
    log_message "🚀 Starting zone monitoring daemon..."
    
    while true; do
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                monitor_zone_traffic "\$ZONE_NAME" "\$ZONE_NETWORKS"
                analyze_zone_security "\$ZONE_NAME"
            fi
        done
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 12)) -eq 0 ]; then
            generate_zone_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_zone_monitoring
        ;;
    "report")
        generate_zone_report
        ;;
    "status")
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                echo -e "\${BLUE}Zone: \$ZONE_NAME\${NC}"
                echo "  Trust Level: \$ZONE_TRUST_LEVEL"
                echo "  Networks: \$ZONE_NETWORKS"
                echo "  Ports: \$ZONE_PORTS"
                echo ""
            fi
        done
        ;;
    *)
        echo "Usage: \$0 <monitor|report|status>"
        exit 1
        ;;
esac
ZONE_MONITOR_EOF

    chmod +x ~/zone_monitor.sh
    
    log_message "✅ Zone monitoring system created"
}

# Function to create zone management dashboard
create_zone_dashboard() {
    log_message "📊 Creating zone management dashboard..."
    
    cat << DASHBOARD_EOF > ~/zone_dashboard.sh
#!/bin/bash

# TwinTower Zone Management Dashboard
set -e

ZONES_CONFIG_DIR="/etc/network-zones"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🌐 TwinTower Network Zone Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# Zone overview
echo -e "\${YELLOW}📋 Zone Overview\${NC}"
echo "----------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Determine status color based on trust level
        case "\$ZONE_TRUST_LEVEL" in
            "HIGH") STATUS_COLOR="\${GREEN}" ;;
            "MEDIUM") STATUS_COLOR="\${YELLOW}" ;;
            "LOW") STATUS_COLOR="\${RED}" ;;
            *) STATUS_COLOR="\${NC}" ;;
        esac
        
        echo -e "\${STATUS_COLOR}🔒 \$ZONE_NAME\${NC} (\$ZONE_TRUST_LEVEL trust)"
        echo "   Networks: \$ZONE_NETWORKS"
        echo "   Ports: \$ZONE_PORTS"
        echo ""
    fi
done

# Active connections per zone
echo -e "\${YELLOW}📊 Active Connections\${NC}"
echo "--------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Count connections (simplified)
        local connection_count=0
        IFS=',' read -ra NETWORKS <<< "\$ZONE_NETWORKS"
        for network in "\${NETWORKS[@]}"; do
            if [ "\$network" != "0.0.0.0/0" ]; then
                local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
                connection_count=\$((connection_count + net_connections))
            fi
        done
        
        echo -e "\$ZONE_NAME: \${GREEN}\$connection_count\${NC} active"
    fi
done
echo

# Security events
echo -e "\${YELLOW}🚨 Security Events (Today)\${NC}"
echo "-------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$ZONE_NAME" || echo "0")
        
        if [ "\$blocked_today" -gt 0 ]; then
            echo -e "\$ZONE_NAME: \${RED}\$blocked_today\${NC} blocked attempts"
        else
            echo -e "\$ZONE_NAME: \${GREEN}No threats\${NC}"
        fi
    fi
done
echo

# Zone rules summary
echo -e "\${YELLOW}📋 Zone Rules Summary\${NC}"
echo "--------------------"
TOTAL_RULES=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Total UFW Rules: \${GREEN}\$TOTAL_RULES\${NC}"
echo -e "Zone-based Rules: \${GREEN}\$(sudo ufw status | grep -c "Zone\|DMZ\|Internal\|Trusted\|Management\|GPU" || echo "0")\${NC}"
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Monitor zones: ./zone_monitor.sh"
echo "2. Generate report: ./zone_monitor.sh report"
echo "3. View UFW status: sudo ufw status verbose"
echo "4. Reload zones: ./network_segmentation.sh reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/zone_dashboard.sh
    
    log_message "✅ Zone management dashboard created"
}

# Function to create zone testing script
create_zone_testing() {
    log_message "🧪 Creating zone testing script..."
    
    cat << TEST_EOF > ~/test_network_zones.sh
#!/bin/bash

# TwinTower Network Zone Testing Script
set -e

ZONES_CONFIG_DIR="/etc/network-zones"
TEST_RESULTS="/tmp/zone_test_results_\$(date +%Y%m%d_%H%M%S).txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Network Zone Testing\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        echo "PASS: \$test_name" >> "\$TEST_RESULTS"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        echo "FAIL: \$test_name" >> "\$TEST_RESULTS"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zone configuration files
echo -e "\${YELLOW}📋 Testing Zone Configuration\${NC}"
echo "------------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        zone_name=\$(basename "\$zone_file" .conf)
        run_test "Zone config exists: \$zone_name" "[ -f '\$zone_file' ]"
        run_test "Zone config readable: \$zone_name" "[ -r '\$zone_file' ]"
    fi
done

# Test UFW application profiles
echo -e "\${YELLOW}🔧 Testing UFW Application Profiles\${NC}"
echo "-----------------------------------"
run_test "TwinTower-Management profile" "sudo ufw app info TwinTower-Management"
run_test "TwinTower-SSH profile" "sudo ufw app info TwinTower-SSH"
run_test "TwinTower-GPU profile" "sudo ufw app info TwinTower-GPU"
run_test "TwinTower-Docker profile" "sudo ufw app info TwinTower-Docker"

# Test zone-specific connectivity
echo -e "\${YELLOW}🌐 Testing Zone Connectivity\${NC}"
echo "----------------------------"

# Test Tailscale (Trusted Zone)
if command -v tailscale &> /dev/null; then
    TAILSCALE_IP=\$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "\$TAILSCALE_IP" ]; then
        run_test "Tailscale connectivity" "ping -c 1 \$TAILSCALE_IP"
    fi
fi

# Test SSH connectivity
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
run_test "SSH port accessible" "timeout 5 bash -c '</dev/tcp/localhost/\$SSH_PORT'"

# Test Docker connectivity
if command -v docker &> /dev/null; then
    run_test "Docker daemon accessible" "docker version"
fi

# Test zone isolation
echo -e "\${YELLOW}🔒 Testing Zone Isolation\${NC}"
echo "-------------------------"
run_test "UFW active" "sudo ufw status | grep -q 'Status: active'"
run_test "Default deny incoming" "sudo ufw status verbose | grep -q 'Default: deny (incoming)'"
run_test "Zone rules present" "sudo ufw status | grep -q 'Zone\|DMZ\|Internal\|Trusted'"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zone tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi

echo -e "\${BLUE}📄 Detailed results: \$TEST_RESULTS\${NC}"
TEST_EOF

    chmod +x ~/test_network_zones.sh
    
    log_message "✅ Zone testing script created"
}

# Main execution
main() {
    echo -e "${BLUE}🌐 TwinTower Network Segmentation & Zone Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}===================================================${NC}"
    
    case "$ACTION" in
        "setup")
            define_network_zones
            implement_zone_rules
            create_zone_monitoring
            create_zone_dashboard
            create_zone_testing
            
            echo -e "${GREEN}✅ Network segmentation configured!${NC}"
            ;;
        "status")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                ~/zone_dashboard.sh
            else
                echo -e "${RED}❌ Network zones not configured${NC}"
            fi
            ;;
        "monitor")
            ~/zone_monitor.sh
            ;;
        "test")
            ~/test_network_zones.sh
            ;;
        "reload")
            implement_zone_rules
            sudo ufw reload
            echo -e "${GREEN}✅ Zone rules reloaded${NC}"
            ;;
        "list")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
                    if [ -f "$zone_file" ]; then
                        source "$zone_file"
                        echo -e "${BLUE}Zone: $ZONE_NAME${NC}"
                        echo "  Description: $ZONE_DESCRIPTION"
                        echo "  Trust Level: $ZONE_TRUST_LEVEL"
                        echo "  Networks: $ZONE_NETWORKS"
                        echo ""
                    fi
                done
            else
                echo -e "${RED}❌ No zones configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|monitor|test|reload|list> [zone_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/network_segmentation.sh
```

### **Step 2: Execute Network Segmentation Setup**

```bash
# Setup network segmentation
./network_segmentation.sh setup

# View zone configuration
./network_segmentation.sh list

# Test zone implementation
./network_segmentation.sh test

# Monitor zones
./network_segmentation.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔒 **Zero-Trust Access Policies**

### **Step 1: Create Zero-Trust Access Control System**

```bash
cat > ~/zero_trust_access.sh << 'EOF'
#!/bin/bash

# TwinTower Zero-Trust Access Control System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
POLICY_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Zero-trust configuration
ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$ZT_LOG_FILE"
}

# Function to setup zero-trust infrastructure
setup_zero_trust() {
    log_message "🔒 Setting up zero-trust infrastructure..."
    
    # Create configuration directories
    sudo mkdir -p "$ZT_CONFIG_DIR" "$ZT_POLICIES_DIR"
    sudo touch "$ZT_LOG_FILE"
    
    # Create zero-trust configuration
    cat << ZT_CONFIG_EOF | sudo tee "$ZT_CONFIG_DIR/zero-trust.conf"
# TwinTower Zero-Trust Configuration
ZT_ENABLED=true
ZT_DEFAULT_POLICY="DENY"
ZT_LOGGING_LEVEL="INFO"
ZT_AUDIT_ENABLED=true
ZT_ENCRYPTION_REQUIRED=true
ZT_AUTHENTICATION_REQUIRED=true
ZT_AUTHORIZATION_REQUIRED=true
ZT_CONTINUOUS_VERIFICATION=true
ZT_SESSION_TIMEOUT=3600
ZT_MAX_FAILED_ATTEMPTS=3
ZT_LOCKOUT_DURATION=1800
ZT_GEOLOCATION_ENABLED=false
ZT_DEVICE_FINGERPRINTING=true
ZT_BEHAVIORAL_ANALYSIS=true
ZT_CONFIG_EOF

    log_message "✅ Zero-trust infrastructure created"
}

# Function to create identity-based policies
create_identity_policies() {
    log_message "👤 Creating identity-based access policies..."
    
    # Administrative Users Policy
    cat << ADMIN_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/admin-users.json"
{
    "policy_name": "AdminUsers",
    "description": "Administrative users with elevated privileges",
    "version": "1.0",
    "priority": 100,
    "conditions": {
        "users": ["ubuntu", "admin", "root"],
        "groups": ["sudo", "docker", "adm"],
        "authentication_methods": ["publickey", "certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "06:00-23:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": true,
        "docker_access": true,
        "gpu_access": true,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 5,
        "session_timeout": 3600,
        "idle_timeout": 1800,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "INFO",
        "log_commands": true,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
ADMIN_POLICY_EOF

    # Standard Users Policy
    cat << USER_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/standard-users.json"
{
    "policy_name": "StandardUsers",
    "description": "Standard users with limited privileges",
    "version": "1.0",
    "priority": 200,
    "conditions": {
        "users": ["user", "developer", "analyst"],
        "groups": ["users"],
        "authentication_methods": ["publickey"],
        "source_networks": ["100.64.0.0/10"],
        "time_restrictions": {
            "allowed_hours": "08:00-18:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": false,
        "gpu_access": true,
        "monitoring_access": false,
        "log_access": false
    },
    "restrictions": {
        "max_sessions": 2,
        "session_timeout": 2400,
        "idle_timeout": 900,
        "password_required": false,
        "mfa_required": true
    },
    "audit": {
        "log_level": "WARN",
        "log_commands": false,
        "log_file_access": false,
        "alert_on_failure": true
    }
}
USER_POLICY_EOF

    # Service Accounts Policy
    cat << SERVICE_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/service-accounts.json"
{
    "policy_name": "ServiceAccounts",
    "description": "Automated service accounts",
    "version": "1.0",
    "priority": 300,
    "conditions": {
        "users": ["docker", "monitoring", "backup"],
        "groups": ["service"],
        "authentication_methods": ["certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "00:00-23:59",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": true,
        "gpu_access": false,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 10,
        "session_timeout": 7200,
        "idle_timeout": 3600,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "ERROR",
        "log_commands": false,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
SERVICE_POLICY_EOF

    log_message "✅ Identity-based policies created"
}

# Function to create device-based policies
create_device_policies() {
    log_message "📱 Creating device-based access policies..."
    
    # Trusted Devices Policy
    cat << TRUSTED_DEVICE_EOF | sudo tee "$ZT_POLICIES_DIR/trusted-devices.json"
{
    "policy_name": "TrustedDevices",
    "description": "Pre-approved trusted devices",
    "version": "1.0",
    "priority": 150,
    "conditions": {
        "device_types": ["laptop", "workstation", "server"],
        "os_types": ["linux", "windows", "macos"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "current",
        "certificate_required": true
    },
    "permissions": {
        "full_access": true,
        "admin_access": true,
        "sensitive_data_access": true
    },
    "restrictions": {
        "geolocation_required": false,
        "vpn_required": false,
        "time_limited": false
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true
    }
}
TRUSTED_DEVICE_EOF

    # BYOD Policy
    cat << BYOD_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/byod-devices.json"
{
    "policy_name": "BYODDevices",
    "description": "Bring Your Own Device policy",
    "version": "1.0",
    "priority": 400,
    "conditions": {
        "device_types": ["mobile", "tablet", "personal-laptop"],
        "os_types": ["android", "ios", "windows", "macos", "linux"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "recent",
        "certificate_required": false
    },
    "permissions": {
        "full_access": false,
        "admin_access": false,
        "sensitive_data_access": false,
        "limited_access": true
    },
    "restrictions": {
        "geolocation_required": true,
        "vpn_required": true,
        "time_limited": true,
        "data_download_restricted": true,
        "screenshot_blocked": true
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true,
        "data_loss_prevention": true
    }
}
BYOD_POLICY_EOF

    log_message "✅ Device-based policies created"
}

# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access# 🔥 Section 5C: Firewall & Access Control
## TwinTower GPU Infrastructure Guide

---

### 📑 **Table of Contents**
- [🎯 Overview](#-overview)
- [🔧 Prerequisites](#-prerequisites)
- [🛡️ Advanced UFW Firewall Configuration](#-advanced-ufw-firewall-configuration)
- [🌐 Network Segmentation & Zone Management](#-network-segmentation--zone-management)
- [🔒 Zero-Trust Access Policies](#-zero-trust-access-policies)
- [🚨 Intrusion Detection & Prevention](#-intrusion-detection--prevention)
- [📊 Network Traffic Monitoring](#-network-traffic-monitoring)
- [⚡ Performance Optimization](#-performance-optimization)
- [🔄 Backup & Recovery](#-backup--recovery)
- [🚀 Next Steps](#-next-steps)

---

## 🎯 **Overview**

Section 5C implements comprehensive firewall and access control policies to complete your TwinTower GPU infrastructure security framework, building upon the secure Tailscale mesh (5A) and hardened SSH (5B) implementations.

### **What This Section Accomplishes:**
- ✅ Advanced UFW firewall with intelligent rules
- ✅ Network segmentation with security zones
- ✅ Zero-trust access policies and micro-segmentation
- ✅ Intrusion detection and prevention systems
- ✅ Real-time network traffic monitoring
- ✅ Performance-optimized security policies
- ✅ Automated threat response and mitigation

### **Security Architecture:**
```
Internet ←→ Tailscale Mesh ←→ Firewall Zones ←→ TwinTower Infrastructure
                                     ↓
    ┌─────────────────────────────────────────────────────────────────────┐
    │     DMZ Zone          Internal Zone        Management Zone           │
    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
    │  │ Public APIs │    │ GPU Cluster │    │ Admin Tools │              │
    │  │ Web Services│    │ Docker Swarm│    │ Monitoring  │              │
    │  └─────────────┘    └─────────────┘    └─────────────┘              │
    │         │                   │                   │                   │
    │    ┌─────────────────────────────────────────────────────────┐      │
    │    │          Firewall Rules & Access Control              │      │
    │    └─────────────────────────────────────────────────────────┘      │
    └─────────────────────────────────────────────────────────────────────┘
```

### **Port Management Strategy:**
- **Management Ports**: 3000-3099 (Web UIs, dashboards)
- **GPU Services**: 4000-4099 (ML/AI workloads)
- **Docker Services**: 5000-5099 (Container applications)
- **Monitoring**: 6000-6099 (Metrics, logging)
- **Custom Apps**: 7000-7099 (User applications)

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔧 **Prerequisites**

### **Required Infrastructure:**
- ✅ Section 5A completed (Tailscale mesh network operational)
- ✅ Section 5B completed (SSH hardening and port configuration)
- ✅ UFW firewall installed and configured
- ✅ Docker Swarm cluster operational
- ✅ Administrative access to all towers

### **Network Requirements:**
- ✅ Tailscale connectivity between all towers
- ✅ SSH access on custom ports (2122/2222/2322)
- ✅ Docker Swarm ports accessible
- ✅ Local network connectivity (192.168.1.0/24)

### **Verification Commands:**
```bash
# Verify previous sections
tailscale status
sudo systemctl status ssh
sudo ufw status
docker node ls
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🛡️ **Advanced UFW Firewall Configuration**

### **Step 1: Create Advanced UFW Management System**

```bash
cat > ~/advanced_ufw_manager.sh << 'EOF'
#!/bin/bash

# TwinTower Advanced UFW Management System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-status}"
TOWER_NAME="${2:-$(hostname)}"
TOWER_NUM=$(echo "$TOWER_NAME" | grep -o '[0-9]' | head -1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
UFW_CONFIG_DIR="/etc/ufw"
BACKUP_DIR="/home/$(whoami)/firewall_backups"
LOG_FILE="/var/log/ufw-manager.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to determine tower-specific ports
get_tower_ports() {
    local tower_num="$1"
    
    case "$tower_num" in
        "1")
            echo "SSH_PORT=2122 WEB_PORT=3001 GPU_PORT=4001 DOCKER_PORT=5001 MONITOR_PORT=6001"
            ;;
        "2")
            echo "SSH_PORT=2222 WEB_PORT=3002 GPU_PORT=4002 DOCKER_PORT=5002 MONITOR_PORT=6002"
            ;;
        "3")
            echo "SSH_PORT=2322 WEB_PORT=3003 GPU_PORT=4003 DOCKER_PORT=5003 MONITOR_PORT=6003"
            ;;
        *)
            echo "SSH_PORT=22 WEB_PORT=3000 GPU_PORT=4000 DOCKER_PORT=5000 MONITOR_PORT=6000"
            ;;
    esac
}

# Function to setup advanced UFW configuration
setup_advanced_ufw() {
    log_message "🔧 Setting up advanced UFW configuration..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup current UFW configuration
    if [ -d "$UFW_CONFIG_DIR" ]; then
        sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Reset UFW to clean state
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw default deny forward
    
    log_message "✅ UFW default policies configured"
}

# Function to configure network zones
configure_network_zones() {
    log_message "🌐 Configuring network security zones..."
    
    # Define network zones
    local LOCAL_NET="192.168.1.0/24"
    local TAILSCALE_NET="100.64.0.0/10"
    local DOCKER_NET="172.17.0.0/16"
    local SWARM_NET="10.0.0.0/8"
    
    # Allow loopback
    sudo ufw allow in on lo
    sudo ufw allow out on lo
    
    # Configure Tailscale zone (trusted)
    sudo ufw allow from "$TAILSCALE_NET" comment "Tailscale Network"
    
    # Configure local network zone (semi-trusted)
    sudo ufw allow from "$LOCAL_NET" to any port 22 comment "Local SSH"
    sudo ufw allow from "$LOCAL_NET" to any port 80 comment "Local HTTP"
    sudo ufw allow from "$LOCAL_NET" to any port 443 comment "Local HTTPS"
    
    # Configure Docker networks
    sudo ufw allow from "$DOCKER_NET" comment "Docker Network"
    sudo ufw allow from "$SWARM_NET" comment "Docker Swarm Network"
    
    log_message "✅ Network zones configured"
}

# Function to configure service-specific rules
configure_service_rules() {
    log_message "⚙️ Configuring service-specific firewall rules..."
    
    # Get tower-specific ports
    eval $(get_tower_ports "$TOWER_NUM")
    
    # SSH Rules
    sudo ufw allow "$SSH_PORT/tcp" comment "SSH Custom Port Tower$TOWER_NUM"
    
    # Docker Swarm Rules
    sudo ufw allow 2377/tcp comment "Docker Swarm Management"
    sudo ufw allow 7946/tcp comment "Docker Swarm Communication TCP"
    sudo ufw allow 7946/udp comment "Docker Swarm Communication UDP"
    sudo ufw allow 4789/udp comment "Docker Swarm Overlay Network"
    
    # Tailscale Rules
    sudo ufw allow 41641/udp comment "Tailscale"
    
    # GPU and ML Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$GPU_PORT" comment "GPU Services Tower$TOWER_NUM"
    sudo ufw allow from "192.168.1.0/24" to any port "$GPU_PORT" comment "GPU Services Local"
    
    # Web Management Interface
    sudo ufw allow from "$TAILSCALE_NET" to any port "$WEB_PORT" comment "Web Management Tower$TOWER_NUM"
    
    # Docker Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$DOCKER_PORT" comment "Docker Services Tower$TOWER_NUM"
    
    # Monitoring Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$MONITOR_PORT" comment "Monitoring Tower$TOWER_NUM"
    
    log_message "✅ Service-specific rules configured"
}

# Function to configure advanced security rules
configure_advanced_security() {
    log_message "🔒 Configuring advanced security rules..."
    
    # Rate limiting for SSH
    sudo ufw limit ssh comment "SSH Rate Limiting"
    
    # Block common attack patterns
    sudo ufw deny from 10.0.0.0/8 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 172.16.0.0/12 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 192.168.0.0/16 to any port 22 comment "Block RFC1918 SSH (except local)"
    sudo ufw allow from 192.168.1.0/24 to any port 22 comment "Allow local SSH"
    
    # Block suspicious ports
    sudo ufw deny 135/tcp comment "Block MS RPC"
    sudo ufw deny 139/tcp comment "Block NetBIOS"
    sudo ufw deny 445/tcp comment "Block SMB"
    sudo ufw deny 1433/tcp comment "Block MS SQL"
    sudo ufw deny 3389/tcp comment "Block RDP"
    
    # Allow ping but limit it
    sudo ufw allow from "$TAILSCALE_NET" proto icmp comment "Tailscale Ping"
    sudo ufw allow from "192.168.1.0/24" proto icmp comment "Local Ping"
    
    log_message "✅ Advanced security rules configured"
}

# Function to configure logging and monitoring
configure_logging() {
    log_message "📊 Configuring UFW logging and monitoring..."
    
    # Enable UFW logging
    sudo ufw logging on
    
    # Create custom logging configuration
    cat << LOG_CONFIG_EOF | sudo tee /etc/rsyslog.d/20-ufw.conf
# UFW logging configuration
:msg,contains,"[UFW " /var/log/ufw.log
& stop
LOG_CONFIG_EOF

    # Create log rotation
    cat << LOGROTATE_EOF | sudo tee /etc/logrotate.d/ufw-custom
/var/log/ufw.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 syslog adm
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
LOGROTATE_EOF

    # Restart rsyslog
    sudo systemctl restart rsyslog
    
    log_message "✅ UFW logging configured"
}

# Function to create UFW monitoring script
create_ufw_monitor() {
    log_message "📈 Creating UFW monitoring script..."
    
    cat << MONITOR_EOF > ~/ufw_monitor.sh
#!/bin/bash

# TwinTower UFW Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-60}"
LOG_FILE="/var/log/ufw-monitor.log"
ALERT_THRESHOLD=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor UFW status
monitor_ufw_status() {
    if sudo ufw status | grep -q "Status: active"; then
        log_message "✅ UFW is active"
        return 0
    else
        log_message "❌ UFW is inactive"
        return 1
    fi
}

# Function to analyze UFW logs
analyze_ufw_logs() {
    local blocked_count=\$(sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    local allowed_count=\$(sudo grep "\[UFW ALLOW\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    
    log_message "📊 Today's UFW activity - Blocked: \$blocked_count, Allowed: \$allowed_count"
    
    if [ "\$blocked_count" -gt "\$ALERT_THRESHOLD" ]; then
        log_message "🚨 HIGH ALERT: \$blocked_count blocked connections today"
        
        # Show top blocked IPs
        echo "Top blocked IPs today:" | tee -a "\$LOG_FILE"
        sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
        awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
        while read count ip; do
            echo "  \$ip: \$count attempts" | tee -a "\$LOG_FILE"
        done
    fi
}

# Function to check rule efficiency
check_rule_efficiency() {
    local total_rules=\$(sudo ufw status numbered | grep -c "^\[")
    log_message "📋 Total UFW rules: \$total_rules"
    
    if [ "\$total_rules" -gt 50 ]; then
        log_message "⚠️  Warning: High number of UFW rules may impact performance"
    fi
}

# Function to generate UFW report
generate_ufw_report() {
    local report_file="/tmp/ufw_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower UFW Monitoring Report
==============================
Generated: \$(date)
Tower: \$(hostname)

UFW Status:
----------
\$(sudo ufw status verbose)

Recent Activity (Last 24 hours):
-------------------------------
Blocked connections: \$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
Allowed connections: \$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)

Top Blocked IPs:
---------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Top Blocked Ports:
-----------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$14}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Recent Blocked Connections:
--------------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | tail -10)

REPORT_EOF

    echo "📋 UFW report generated: \$report_file"
    log_message "UFW report generated: \$report_file"
}

# Function to start monitoring daemon
start_monitoring() {
    log_message "🚀 Starting UFW monitoring daemon..."
    
    while true; do
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 60)) -eq 0 ]; then
            generate_ufw_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_monitoring
        ;;
    "status")
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        ;;
    "report")
        generate_ufw_report
        ;;
    *)
        echo "Usage: \$0 <monitor|status|report>"
        exit 1
        ;;
esac
MONITOR_EOF

    chmod +x ~/ufw_monitor.sh
    
    log_message "✅ UFW monitoring script created"
}

# Function to optimize UFW performance
optimize_ufw_performance() {
    log_message "⚡ Optimizing UFW performance..."
    
    # Create custom UFW configuration for performance
    cat << PERF_CONFIG_EOF | sudo tee /etc/ufw/sysctl.conf
# TwinTower UFW Performance Optimization

# Network performance
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.core.netdev_max_backlog = 5000

# Connection tracking
net.netfilter.nf_conntrack_max = 131072
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30

# Rate limiting
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048

# Security hardening
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
PERF_CONFIG_EOF

    # Apply sysctl settings
    sudo sysctl -p /etc/ufw/sysctl.conf
    
    log_message "✅ UFW performance optimized"
}

# Function to create UFW dashboard
create_ufw_dashboard() {
    log_message "📊 Creating UFW dashboard..."
    
    cat << DASHBOARD_EOF > ~/ufw_dashboard.sh
#!/bin/bash

# TwinTower UFW Dashboard
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔥 TwinTower UFW Firewall Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# UFW Status
echo -e "\${YELLOW}🛡️ UFW Status\${NC}"
echo "---------------"
if sudo ufw status | grep -q "Status: active"; then
    echo -e "Firewall Status: \${GREEN}✅ Active\${NC}"
else
    echo -e "Firewall Status: \${RED}❌ Inactive\${NC}"
fi

# Rule count
RULE_COUNT=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Active Rules: \${GREEN}\$RULE_COUNT\${NC}"

# Default policies
echo -e "Default Incoming: \${RED}DENY\${NC}"
echo -e "Default Outgoing: \${GREEN}ALLOW\${NC}"
echo

# Recent activity
echo -e "\${YELLOW}📈 Recent Activity (Last Hour)\${NC}"
echo "------------------------------"
HOUR_AGO=\$(date -d '1 hour ago' '+%b %d %H')
CURRENT_HOUR=\$(date '+%b %d %H')

BLOCKED_HOUR=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)
ALLOWED_HOUR=\$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)

echo -e "Blocked Connections: \${RED}\$BLOCKED_HOUR\${NC}"
echo -e "Allowed Connections: \${GREEN}\$ALLOWED_HOUR\${NC}"
echo

# Top blocked IPs
echo -e "\${YELLOW}🚫 Top Blocked IPs (Today)\${NC}"
echo "-------------------------"
sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
while read count ip; do
    echo -e "  \${RED}\$ip\${NC}: \$count attempts"
done
echo

# Service status
echo -e "\${YELLOW}⚙️ Service Status\${NC}"
echo "-----------------"
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
echo -e "SSH Port: \${GREEN}\$SSH_PORT\${NC}"

if sudo systemctl is-active --quiet docker; then
    echo -e "Docker: \${GREEN}✅ Running\${NC}"
else
    echo -e "Docker: \${RED}❌ Stopped\${NC}"
fi

if sudo systemctl is-active --quiet tailscaled; then
    echo -e "Tailscale: \${GREEN}✅ Running\${NC}"
else
    echo -e "Tailscale: \${RED}❌ Stopped\${NC}"
fi
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View detailed rules: sudo ufw status numbered"
echo "2. Monitor real-time: sudo tail -f /var/log/ufw.log"
echo "3. Generate report: ./ufw_monitor.sh report"
echo "4. Reload firewall: sudo ufw reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/ufw_dashboard.sh
    
    log_message "✅ UFW dashboard created"
}

# Main execution
main() {
    echo -e "${BLUE}🔥 TwinTower Advanced UFW Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME (Tower$TOWER_NUM)${NC}"
    echo -e "${BLUE}===================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_advanced_ufw
            configure_network_zones
            configure_service_rules
            configure_advanced_security
            configure_logging
            create_ufw_monitor
            optimize_ufw_performance
            create_ufw_dashboard
            
            # Enable UFW
            sudo ufw --force enable
            
            echo -e "${GREEN}✅ Advanced UFW configuration completed!${NC}"
            ;;
        "status")
            sudo ufw status verbose
            ;;
        "dashboard")
            ./ufw_dashboard.sh
            ;;
        "monitor")
            ./ufw_monitor.sh
            ;;
        "optimize")
            optimize_ufw_performance
            ;;
        "backup")
            sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
            echo -e "${GREEN}✅ UFW configuration backed up${NC}"
            ;;
        "reload")
            sudo ufw reload
            echo -e "${GREEN}✅ UFW reloaded${NC}"
            ;;
        *)
            echo "Usage: $0 <setup|status|dashboard|monitor|optimize|backup|reload> [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/advanced_ufw_manager.sh
```

### **Step 2: Execute Advanced UFW Setup**

```bash
# Setup advanced UFW configuration on each tower
./advanced_ufw_manager.sh setup $(hostname)

# Verify UFW status
./advanced_ufw_manager.sh status

# Launch UFW dashboard
./advanced_ufw_manager.sh dashboard
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🌐 **Network Segmentation & Zone Management**

### **Step 1: Create Network Segmentation System**

```bash
cat > ~/network_segmentation.sh << 'EOF'
#!/bin/bash

# TwinTower Network Segmentation & Zone Management
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
ZONE_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Network zones configuration
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/network-zones.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to define network zones
define_network_zones() {
    log_message "🌐 Defining network security zones..."
    
    sudo mkdir -p "$ZONES_CONFIG_DIR"
    
    # DMZ Zone - Public-facing services
    cat << DMZ_EOF | sudo tee "$ZONES_CONFIG_DIR/dmz.conf"
# DMZ Zone Configuration
ZONE_NAME="DMZ"
ZONE_DESCRIPTION="Public-facing services and APIs"
ZONE_NETWORKS="0.0.0.0/0"
ZONE_TRUST_LEVEL="LOW"
ZONE_PORTS="80,443,8080,8443"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="STRICT"
ZONE_INTRUSION_DETECTION="ENABLED"
DMZ_EOF

    # Internal Zone - Private infrastructure
    cat << INTERNAL_EOF | sudo tee "$ZONES_CONFIG_DIR/internal.conf"
# Internal Zone Configuration
ZONE_NAME="INTERNAL"
ZONE_DESCRIPTION="Private infrastructure and services"
ZONE_NETWORKS="192.168.1.0/24,172.16.0.0/12,10.0.0.0/8"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="22,80,443,2377,4789,7946"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
INTERNAL_EOF

    # Trusted Zone - Tailscale and management
    cat << TRUSTED_EOF | sudo tee "$ZONES_CONFIG_DIR/trusted.conf"
# Trusted Zone Configuration
ZONE_NAME="TRUSTED"
ZONE_DESCRIPTION="Tailscale mesh and management interfaces"
ZONE_NETWORKS="100.64.0.0/10"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="ALL"
ZONE_PROTOCOLS="tcp,udp,icmp"
ZONE_LOGGING="LOW"
ZONE_RATE_LIMIT="RELAXED"
ZONE_INTRUSION_DETECTION="MONITORING"
TRUSTED_EOF

    # Management Zone - Administrative access
    cat << MGMT_EOF | sudo tee "$ZONES_CONFIG_DIR/management.conf"
# Management Zone Configuration
ZONE_NAME="MANAGEMENT"
ZONE_DESCRIPTION="Administrative and monitoring services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="2122,2222,2322,3000-3099,6000-6099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
MGMT_EOF

    # GPU Zone - GPU compute services
    cat << GPU_EOF | sudo tee "$ZONES_CONFIG_DIR/gpu.conf"
# GPU Zone Configuration
ZONE_NAME="GPU"
ZONE_DESCRIPTION="GPU compute and ML services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="4000-4099,8000-8099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
GPU_EOF

    log_message "✅ Network zones defined"
}

# Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone)

Restoration Instructions:
------------------------
1. Extract backup: tar -xzf full_backup_${TOWER_NAME}_${TIMESTAMP}.tar.gz
2. Run restoration script: ./restore_firewall_system.sh
3. Verify system functionality: ./verify_system_restore.sh

Notes:
------
- Always test restoration on a non-production system first
- Verify all services are running after restoration
- Check firewall rules and network connectivity
- Validate zero-trust policies and IDS functionality

MANIFEST_EOF

    # Create full backup archive
    cd "$temp_dir"
    tar -czf "$full_backup" full_backup/
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ Full system backup created: $full_backup"
}

# Function to restore from backup
restore_from_backup() {
    log_message "🔄 Starting system restoration from backup..."
    
    if [ -z "$RESTORE_FILE" ]; then
        log_message "❌ No restore file specified"
        echo "Available backups:"
        ls -la "$BACKUP_DIR/full/"*.tar.gz 2>/dev/null || echo "No full backups found"
        exit 1
    fi
    
    if [ ! -f "$RESTORE_FILE" ]; then
        log_message "❌ Restore file not found: $RESTORE_FILE"
        exit 1
    fi
    
    # Create restoration script
    cat > ~/restore_firewall_system.sh << 'RESTORE_EOF'
#!/bin/bash

# TwinTower Firewall System Restoration Script
set -e

RESTORE_FILE="$1"
RESTORE_DIR="/tmp/twintower_restore_$(date +%Y%m%d_%H%M%S)"

if [ -z "$RESTORE_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "🔄 Starting system restoration..."

# Extract backup
mkdir -p "$RESTORE_DIR"
cd "$RESTORE_DIR"
tar -xzf "$RESTORE_FILE"

# Find backup directory
BACKUP_DIR=$(find . -name "full_backup" -type d | head -1)
if [ -z "$BACKUP_DIR" ]; then
    echo "❌ Invalid backup file structure"
    exit 1
fi

cd "$BACKUP_DIR"

# Restore UFW configuration
echo "🔥 Restoring UFW configuration..."
for ufw_backup in ufw_config_*.tar.gz; do
    if [ -f "$ufw_backup" ]; then
        tar -xzf "$ufw_backup"
        sudo cp -r ufw_backup/ufw/* /etc/ufw/ 2>/dev/null || true
        sudo ufw reload
        break
    fi
done

# Restore network zones
echo "🌐 Restoring network zones..."
for zones_backup in zones_config_*.tar.gz; do
    if [ -f "$zones_backup" ]; then
        tar -xzf "$zones_backup"
        sudo cp -r zones_backup/network-zones /etc/ 2>/dev/null || true
        break
    fi
done

# Restore zero-trust policies
echo "🔒 Restoring zero-trust policies..."
for zt_backup in zero_trust_*.tar.gz; do
    if [ -f "$zt_backup" ]; then
        tar -xzf "$zt_backup"
        sudo cp -r zero_trust_backup/zero-trust /etc/ 2>/dev/null || true
        sudo cp -r zero_trust_backup/zero-trust /var/lib/ 2>/dev/null || true
        break
    fi
done

# Restore IDS configuration
echo "🚨 Restoring IDS configuration..."
for ids_backup in ids_config_*.tar.gz; do
    if [ -f "$ids_backup" ]; then
        tar -xzf "$ids_backup"
        sudo cp -r ids_backup/twintower-ids /etc/ echo "5. Real-time monitor: watch -n 1 './traffic_dashboard.sh'"

echo
echo -e "\${BLUE}=========================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/traffic_dashboard.sh
    
    log_message "✅ Traffic monitoring dashboard created"
}

# Function to create traffic monitoring service
create_traffic_service() {
    log_message "⚙️ Creating traffic monitoring service..."
    
    cat << TRAFFIC_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-traffic.service
[Unit]
Description=TwinTower Network Traffic Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/traffic_analyzer.sh daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
TRAFFIC_SERVICE_EOF

    # Enable service
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-traffic.service
    
    log_message "✅ Traffic monitoring service created"
}

# Function to create traffic testing tools
create_traffic_testing() {
    log_message "🧪 Creating traffic testing tools..."
    
    cat << TRAFFIC_TEST_EOF > ~/test_traffic_monitoring.sh
#!/bin/bash

# TwinTower Traffic Monitoring Test Suite
set -e

TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Traffic Monitoring Test Suite\${NC}"
echo -e "\${BLUE}==========================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test monitoring infrastructure
echo -e "\${YELLOW}🔧 Testing Monitoring Infrastructure\${NC}"
echo "------------------------------------"
run_test "Config directory exists" "[ -d '\$TRAFFIC_CONFIG_DIR' ]"
run_test "Log directory exists" "[ -d '\$TRAFFIC_LOG_DIR' ]"
run_test "Data directory exists" "[ -d '\$TRAFFIC_DATA_DIR' ]"
run_test "Monitor config exists" "[ -f '\$TRAFFIC_CONFIG_DIR/monitor.conf' ]"
run_test "Interface config exists" "[ -f '\$TRAFFIC_CONFIG_DIR/interfaces.conf' ]"

# Test monitoring tools
echo -e "\${YELLOW}📊 Testing Monitoring Tools\${NC}"
echo "---------------------------"
run_test "Traffic analyzer exists" "[ -f '\$HOME/traffic_analyzer.sh' ]"
run_test "Traffic dashboard exists" "[ -f '\$HOME/traffic_dashboard.sh' ]"
run_test "Interface detector exists" "[ -f '\$HOME/detect_interfaces.sh' ]"

# Test system commands
echo -e "\${YELLOW}⚙️ Testing System Commands\${NC}"
echo "--------------------------"
run_test "netstat command available" "command -v netstat"
run_test "iftop command available" "command -v iftop"
run_test "vnstat command available" "command -v vnstat"

# Test network interfaces
echo -e "\${YELLOW}🌐 Testing Network Interfaces\${NC}"
echo "-----------------------------"
run_test "Primary interface detected" "[ -n '\$(ip route | grep default | awk \"{print \\\$5}\" | head -1)' ]"
run_test "Loopback interface exists" "ip addr show lo"
run_test "Interface statistics available" "[ -f '/proc/net/dev' ]"

# Test traffic analysis
echo -e "\${YELLOW}📈 Testing Traffic Analysis\${NC}"
echo "---------------------------"
run_test "Connection counting works" "netstat -tn | grep ESTABLISHED | wc -l"
run_test "Port listening detection" "netstat -tln | grep LISTEN | wc -l"
run_test "Process net dev reading" "cat /proc/net/dev | grep -E '^[[:space:]]*lo:'"

# Test log file creation
echo -e "\${YELLOW}📝 Testing Log Files\${NC}"
echo "--------------------"
run_test "Monitor log writable" "touch '\$TRAFFIC_LOG_DIR/test.log' && rm '\$TRAFFIC_LOG_DIR/test.log'"
run_test "Data directory writable" "touch '\$TRAFFIC_DATA_DIR/test.dat' && rm '\$TRAFFIC_DATA_DIR/test.dat'"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All traffic monitoring tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
TRAFFIC_TEST_EOF

    chmod +x ~/test_traffic_monitoring.sh
    
    log_message "✅ Traffic testing tools created"
}

# Main execution
main() {
    echo -e "${BLUE}📊 TwinTower Network Traffic Monitoring${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=======================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_traffic_monitoring
            create_traffic_analyzer
            create_traffic_dashboard
            create_traffic_service
            create_traffic_testing
            
            echo -e "${GREEN}✅ Network traffic monitoring configured!${NC}"
            ;;
        "start")
            sudo systemctl start twintower-traffic.service
            echo -e "${GREEN}✅ Traffic monitoring service started${NC}"
            ;;
        "stop")
            sudo systemctl stop twintower-traffic.service
            echo -e "${GREEN}✅ Traffic monitoring service stopped${NC}"
            ;;
        "status")
            ~/traffic_dashboard.sh
            ;;
        "test")
            ~/test_traffic_monitoring.sh
            ;;
        "monitor")
            ~/traffic_analyzer.sh daemon
            ;;
        "report")
            ~/traffic_analyzer.sh report
            ;;
        "dashboard")
            ~/traffic_dashboard.sh
            ;;
        *)
            echo "Usage: $0 <setup|start|stop|status|test|monitor|report|dashboard>"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/network_traffic_monitor.sh
```

### **Step 2: Execute Network Traffic Monitoring Setup**

```bash
# Setup network traffic monitoring
./network_traffic_monitor.sh setup

# Start traffic monitoring service
./network_traffic_monitor.sh start

# View traffic dashboard
./network_traffic_monitor.sh dashboard

# Test monitoring functionality
./network_traffic_monitor.sh test
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## ⚡ **Performance Optimization**

### **Step 1: Create Performance Optimization System**

```bash
cat > ~/performance_optimizer.sh << 'EOF'
#!/bin/bash

# TwinTower Performance Optimization System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
OPTIMIZATION_TYPE="${2:-all}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Performance configuration
PERF_CONFIG_DIR="/etc/twintower-performance"
PERF_LOG_DIR="/var/log/twintower-performance"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$PERF_LOG_DIR/optimizer.log"
}

# Function to setup performance optimization infrastructure
setup_performance_optimization() {
    log_message "⚡ Setting up performance optimization infrastructure..."
    
    # Create directories
    sudo mkdir -p "$PERF_CONFIG_DIR" "$PERF_LOG_DIR"
    
    # Create performance configuration
    cat << PERF_CONFIG_EOF | sudo tee "$PERF_CONFIG_DIR/performance.conf"
# TwinTower Performance Configuration
PERF_ENABLED=true
PERF_PROFILE="balanced"
PERF_NETWORK_OPTIMIZATION=true
PERF_FIREWALL_OPTIMIZATION=true
PERF_SYSTEM_OPTIMIZATION=true
PERF_MONITORING_ENABLED=true
PERF_AUTO_TUNING=false
PERF_ALERTING_ENABLED=true
PERF_BACKUP_CONFIGS=true
PERF_CONFIG_EOF

    log_message "✅ Performance optimization infrastructure created"
}

# Function to optimize network performance
optimize_network_performance() {
    log_message "🌐 Optimizing network performance..."
    
    # Backup current network settings
    sudo cp /etc/sysctl.conf "/etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Create optimized network configuration
    cat << NETWORK_EOF | sudo tee /etc/sysctl.d/99-twintower-network.conf
# TwinTower Network Performance Optimization

# Core network settings
net.core.rmem_default = 262144
net.core.rmem_max = 134217728
net.core.wmem_default = 262144
net.core.wmem_max = 134217728
net.core.netdev_max_backlog = 30000
net.core.somaxconn = 4096

# TCP settings
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_rmem = 4096 32768 134217728
net.ipv4.tcp_wmem = 4096 32768 134217728
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_fack = 1
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_no_metrics_save = 1
net.ipv4.tcp_moderate_rcvbuf = 1
net.ipv4.tcp_rfc1337 = 1
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_keepalive_intvl = 60

# Connection tracking
net.netfilter.nf_conntrack_max = 2097152
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30
net.netfilter.nf_conntrack_tcp_timeout_fin_wait = 30
net.netfilter.nf_conntrack_tcp_timeout_close_wait = 30
net.netfilter.nf_conntrack_udp_timeout = 30
net.netfilter.nf_conntrack_udp_timeout_stream = 180
net.netfilter.nf_conntrack_generic_timeout = 300

# Buffer sizes
net.ipv4.udp_rmem_min = 8192
net.ipv4.udp_wmem_min = 8192
net.ipv4.tcp_adv_win_scale = 1

# Network security (with performance considerations)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1

# Memory and file limits
fs.file-max = 2097152
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
NETWORK_EOF

    # Apply network optimizations
    sudo sysctl -p /etc/sysctl.d/99-twintower-network.conf
    
    log_message "✅ Network performance optimized"
}

# Function to optimize firewall performance
optimize_firewall_performance() {
    log_message "🔥 Optimizing firewall performance..."
    
    # Create optimized iptables rules
    cat << IPTABLES_EOF | sudo tee /etc/iptables/rules.v4.optimized
# TwinTower Optimized iptables Rules
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

# Loopback
-A INPUT -i lo -j ACCEPT

# Connection tracking optimization
-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
-A INPUT -m conntrack --ctstate INVALID -j DROP

# Rate limiting for new connections
-A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name SSH
-A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP

# Tailscale network (optimized)
-A INPUT -s 100.64.0.0/10 -j ACCEPT

# Local network (optimized)
-A INPUT -s 192.168.1.0/24 -j ACCEPT

# Custom SSH ports
-A INPUT -p tcp --dport 2122 -j ACCEPT
-A INPUT -p tcp --dport 2222 -j ACCEPT
-A INPUT -p tcp --dport 2322 -j ACCEPT

# Docker Swarm (optimized)
-A INPUT -p tcp --dport 2377 -j ACCEPT
-A INPUT -p tcp --dport 7946 -j ACCEPT
-A INPUT -p udp --dport 7946 -j ACCEPT
-A INPUT -p udp --dport 4789 -j ACCEPT

# ICMP (rate limited)
-A INPUT -p icmp -m limit --limit 5/sec --limit-burst 10 -j ACCEPT

# Log dropped packets (rate limited)
-A INPUT -m limit --limit 5/min --limit-burst 10 -j LOG --log-prefix "IPTABLES-DROP: "

COMMIT
IPTABLES_EOF

    # Optimize UFW backend
    if [ -f "/etc/ufw/sysctl.conf" ]; then
        sudo cp "/etc/ufw/sysctl.conf" "/etc/ufw/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)"
        
        cat << UFW_SYSCTL_EOF | sudo tee -a /etc/ufw/sysctl.conf

# TwinTower UFW Performance Optimizations
net.netfilter.nf_conntrack_max = 2097152
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30
net.netfilter.nf_conntrack_buckets = 524288
net.netfilter.nf_conntrack_expect_max = 1024
UFW_SYSCTL_EOF
    fi
    
    log_message "✅ Firewall performance optimized"
}

# Function to optimize system performance
optimize_system_performance() {
    log_message "⚙️ Optimizing system performance..."
    
    # CPU frequency scaling
    if [ -f "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
        echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
    fi
    
    # Create system optimization configuration
    cat << SYSTEM_EOF | sudo tee /etc/sysctl.d/99-twintower-system.conf
# TwinTower System Performance Optimization

# Kernel parameters
kernel.panic = 30
kernel.pid_max = 4194304
kernel.threads-max = 4194304

# Memory management
vm.overcommit_memory = 1
vm.overcommit_ratio = 100
vm.vfs_cache_pressure = 50
vm.dirty_expire_centisecs = 3000
vm.dirty_writeback_centisecs = 500

# Process limits
fs.nr_open = 1048576
fs.file-max = 2097152

# Security limits (with performance considerations)
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 1
kernel.yama.ptrace_scope = 1
SYSTEM_EOF

    # Apply system optimizations
    sudo sysctl -p /etc/sysctl.d/99-twintower-system.conf
    
    # Optimize systemd services
    sudo systemctl daemon-reload
    
    log_message "✅ System performance optimized"
}

# Function to create performance monitoring
create_performance_monitoring() {
    log_message "📊 Creating performance monitoring system..."
    
    cat << PERF_MONITOR_EOF > ~/performance_monitor.sh
#!/bin/bash

# TwinTower Performance Monitor
set -e

PERF_LOG_DIR="/var/log/twintower-performance"
PERF_DATA_DIR="/var/lib/twintower-performance"
MONITOR_INTERVAL="\${1:-60}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$PERF_LOG_DIR/monitor.log"
}

# Function to collect system metrics
collect_system_metrics() {
    local timestamp=\$(date +%s)
    
    # CPU usage
    local cpu_usage=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//')
    
    # Memory usage
    local mem_total=\$(free -m | grep "Mem:" | awk '{print \$2}')
    local mem_used=\$(free -m | grep "Mem:" | awk '{print \$3}')
    local mem_usage=\$(echo "scale=2; \$mem_used * 100 / \$mem_total" | bc -l)
    
    # Disk usage
    local disk_usage=\$(df -h / | tail -1 | awk '{print \$5}' | sed 's/%//')
    
    # Load average
    local load_avg=\$(uptime | awk -F'load average:' '{print \$2}' | awk '{print \$1}' | sed 's/,//')
    
    # Network connections
    local connections=\$(netstat -tn | grep ESTABLISHED | wc -l)
    
    # Store metrics
    sudo mkdir -p "\$PERF_DATA_DIR"
    echo "\$timestamp,\$cpu_usage,\$mem_usage,\$disk_usage,\$load_avg,\$connections" >> "\$PERF_DATA_DIR/system_metrics.csv"
    
    log_message "Metrics: CPU \$cpu_usage%, RAM \$mem_usage%, Disk \$disk_usage%, Load \$load_avg, Connections \$connections"
}

# Function to collect network metrics
collect_network_metrics() {
    local timestamp=\$(date +%s)
    
    # Get primary interface
    local interface=\$(ip route | grep default | awk '{print \$5}' | head -1)
    
    if [ -n "\$interface" ]; then
        local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
        local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
        local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
        local rx_packets=\$(echo "\$stats" | cut -d' ' -f3)
        local tx_packets=\$(echo "\$stats" | cut -d' ' -f11)
        
        # Calculate rates if previous data exists
        local prev_file="\$PERF_DATA_DIR/network_prev.dat"
        if [ -f "\$prev_file" ]; then
            local prev_data=\$(cat "\$prev_file")
            local prev_time=\$(echo "\$prev_data" | cut -d',' -f1)
            local prev_rx_bytes=\$(echo "\$prev_data" | cut -d',' -f2)
            local prev_tx_bytes=\$(echo "\$prev_data" | cut -d',' -f3)
            
            local time_diff=\$((timestamp - prev_time))
            if [ \$time_diff -gt 0 ]; then
                local rx_rate=\$(echo "scale=2; (\$rx_bytes - \$prev_rx_bytes) / \$time_diff / 1024" | bc -l)
                local tx_rate=\$(echo "scale=2; (\$tx_bytes - \$prev_tx_bytes) / \$time_diff / 1024" | bc -l)
                
                echo "\$timestamp,\$interface,\$rx_rate,\$tx_rate,\$rx_packets,\$tx_packets" >> "\$PERF_DATA_DIR/network_metrics.csv"
                log_message "Network: \$interface RX \$rx_rate KB/s, TX \$tx_rate KB/s"
            fi
        fi
        
        # Store current data
        echo "\$timestamp,\$rx_bytes,\$tx_bytes" > "\$prev_file"
    fi
}

# Function to collect firewall metrics
collect_firewall_metrics() {
    local timestamp=\$(date +%s)
    
    # UFW statistics
    local ufw_active=\$(sudo ufw status | grep -c "Status: active" || echo "0")
    local ufw_rules=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
    
    # Connection tracking
    local conntrack_count=\$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")
    local conntrack_max=\$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "0")
    
    # Store metrics
    echo "\$timestamp,\$ufw_active,\$ufw_rules,\$conntrack_count,\$conntrack_max" >> "\$PERF_DATA_DIR/firewall_metrics.csv"
    
    log_message "Firewall: UFW Active \$ufw_active, Rules \$ufw_rules, Connections \$conntrack_count/\$conntrack_max"
}

# Function to detect performance issues
detect_performance_issues() {
    # Check CPU usage
    local cpu_usage=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//' | cut -d'.' -f1)
    if [ \$cpu_usage -gt 80 ]; then
        log_message "🚨 HIGH CPU USAGE: \$cpu_usage%"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH CPU: \$cpu_usage%" >> "\$PERF_LOG_DIR/alerts.log"
    fi
    
    # Check memory usage
    local mem_usage=\$(free | grep "Mem:" | awk '{print int(\$3*100/\$2)}')
    if [ \$mem_usage -gt 85 ]; then
        log_message "🚨 HIGH MEMORY USAGE: \$mem_usage%"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH MEMORY: \$mem_usage%" >> "\$PERF_LOG_DIR/alerts.log"
    fi
    
    # Check connection tracking
    local conntrack_count=\$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")
    local conntrack_max=\$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "1")
    local conntrack_usage=\$(echo "scale=2; \$conntrack_count * 100 / \$conntrack_max" | bc -l)
    
    if [ \$(echo "\$conntrack_usage > 80" | bc -l) -eq 1 ]; then
        log_message "🚨 HIGH CONNECTION TRACKING USAGE: \$conntrack_usage%"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH CONNTRACK: \$conntrack_usage%" >> "\$PERF_LOG_DIR/alerts.log"
    fi
}

# Function to generate performance report
generate_performance_report() {
    local report_file="/tmp/performance_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Performance Report
===========================
Generated: \$(date)
Tower: \$(hostname)

Current System Status:
---------------------
CPU Usage: \$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//')%
Memory Usage: \$(free | grep "Mem:" | awk '{print int(\$3*100/\$2)}')%
Disk Usage: \$(df -h / | tail -1 | awk '{print \$5}')
Load Average: \$(uptime | awk -F'load average:' '{print \$2}')
Active Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)

Network Performance:
-------------------
Primary Interface: \$(ip route | grep default | awk '{print \$5}' | head -1)
Connection Tracking: \$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")/\$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "N/A")

Firewall Status:
---------------
UFW Status: \$(sudo ufw status | head -1)
Active Rules: \$(sudo ufw status numbered | grep -c "^\[" || echo "0")

Recent Performance Alerts:
--------------------------
\$(tail -n 10 "\$PERF_LOG_DIR/alerts.log" 2>/dev/null || echo "No recent alerts")

Performance Trends:
------------------
\$(tail -n 5 "\$PERF_DATA_DIR/system_metrics.csv" 2>/dev/null | while IFS=',' read ts cpu mem disk load conn; do
    echo "\$(date -d "@\$ts" '+%H:%M:%S') - CPU: \$cpu%, RAM: \$mem%, Connections: \$conn"
done)

REPORT_EOF

    log_message "📋 Performance report generated: \$report_file"
    echo "\$report_file"
}

# Function to start performance monitoring
start_performance_monitoring() {
    log_message "🚀 Starting performance monitoring..."
    
    while true; do
        collect_system_metrics
        collect_network_metrics
        collect_firewall_metrics
        detect_performance_issues
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 60)) -eq 0 ]; then
            generate_performance_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_performance_monitoring
        ;;
    "report")
        generate_performance_report
        ;;
    "status")
        echo "Performance Monitor Status:"
        echo "=========================="
        echo "CPU: \$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | sed 's/%us,//')%"
        echo "Memory: \$(free | grep "Mem:" | awk '{print int(\$3*100/\$2)}')%"
        echo "Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)"
        echo "Alerts: \$(tail -n 5 "\$PERF_LOG_DIR/alerts.log" 2>/dev/null | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <daemon|report|status>"
        exit 1
        ;;
esac
PERF_MONITOR_EOF

    chmod +x ~/performance_monitor.sh
    
    log_message "✅ Performance monitoring system created"
}

# Function to create performance dashboard
create_performance_dashboard() {
    log_message "📊 Creating performance dashboard..."
    
    cat << PERF_DASHBOARD_EOF > ~/performance_dashboard.sh
#!/bin/bash

# TwinTower Performance Dashboard
set -e

PERF_LOG_DIR="/var/log/twintower-performance"
PERF_DATA_DIR="/var/lib/twintower-performance"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}⚡ TwinTower Performance Dashboard\# Test IDS components
echo -e "\${YELLOW}⚙️ Testing IDS Components\${NC}"
echo "-------------------------"
run_test "Detection engine exists" "[ -f '\$HOME/ids_detection_engine.sh' ]"
run_test "Detection engine executable" "[ -x '\$HOME/ids_detection_engine.sh' ]"
run_test "IDS dashboard exists" "[ -f '\$HOME/ids_dashboard.sh' ]"
run_test "IDS service file exists" "[ -f '/etc/systemd/system/twintower-ids.service' ]"

# Test log files
echo -e "\${YELLOW}📊 Testing Log Files\${NC}"
echo "--------------------"
run_test "IDS log directory exists" "[ -d '/var/log/twintower-ids' ]"
run_test "IDS alert log exists" "[ -f '/var/log/twintower-ids/alerts.log' ]"
run_test "IDS detection log exists" "[ -f '/var/log/twintower-ids/detection.log' ]"

# Test rule syntax
echo -e "\${YELLOW}🔍 Testing Rule Syntax\${NC}"
echo "----------------------"
for rule_file in "\$IDS_RULES_DIR"/*.rules; do
    if [ -f "\$rule_file" ]; then
        rule_name=\$(basename "\$rule_file" .rules)
        run_test "Rule syntax valid: \$rule_name" "grep -E '^[^#]*\|[^|]*\|[^|]*\|[^|]*\## 🚨 **Intrusion Detection & Prevention**

### **Step 1: Create Advanced Intrusion Detection System**

```bash
cat > ~/intrusion_detection.sh << 'EOF'
#!/bin/bash

# TwinTower Intrusion Detection & Prevention System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
DETECTION_TYPE="${2:-realtime}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# IDS Configuration
IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="$IDS_LOG_DIR/detection.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$IDS_DETECTION_LOG"
}

# Function to setup IDS infrastructure
setup_ids_infrastructure() {
    log_message "🔧 Setting up IDS infrastructure..."
    
    # Create directories
    sudo mkdir -p "$IDS_CONFIG_DIR" "$IDS_RULES_DIR" "$IDS_LOG_DIR"
    sudo touch "$IDS_ALERT_LOG" "$IDS_DETECTION_LOG"
    
    # Create main IDS configuration
    cat << IDS_CONFIG_EOF | sudo tee "$IDS_CONFIG_DIR/ids.conf"
# TwinTower IDS Configuration
IDS_ENABLED=true
IDS_MODE="monitor"
IDS_SENSITIVITY="medium"
IDS_LOGGING_LEVEL="info"
IDS_ALERT_THRESHOLD=5
IDS_BLOCK_THRESHOLD=10
IDS_WHITELIST_ENABLED=true
IDS_LEARNING_MODE=false
IDS_REALTIME_ALERTS=true
IDS_EMAIL_ALERTS=false
IDS_WEBHOOK_ALERTS=false
IDS_AUTO_BLOCK=false
IDS_BLOCK_DURATION=3600
IDS_CLEANUP_INTERVAL=86400
IDS_CONFIG_EOF

    # Create whitelist configuration
    cat << WHITELIST_EOF | sudo tee "$IDS_CONFIG_DIR/whitelist.conf"
# TwinTower IDS Whitelist
# Trusted IP addresses and networks
100.64.0.0/10
192.168.1.0/24
127.0.0.0/8
::1/128

# Trusted processes
/usr/bin/ssh
/usr/bin/docker
/usr/bin/tailscale
/usr/sbin/sshd
WHITELIST_EOF

    log_message "✅ IDS infrastructure created"
}

# Function to create detection rules
create_detection_rules() {
    log_message "📋 Creating intrusion detection rules..."
    
    # SSH Attack Detection Rules
    cat << SSH_RULES_EOF | sudo tee "$IDS_RULES_DIR/ssh_attacks.rules"
# SSH Attack Detection Rules
# Rule format: PATTERN|SEVERITY|ACTION|DESCRIPTION

# Brute force attacks
authentication failure.*ssh|HIGH|ALERT|SSH brute force attempt
Failed password.*ssh|MEDIUM|COUNT|SSH failed password
Invalid user.*ssh|HIGH|ALERT|SSH invalid user attempt
ROOT LOGIN REFUSED.*ssh|HIGH|ALERT|SSH root login attempt

# SSH scanning
Connection closed.*ssh.*preauth|LOW|COUNT|SSH connection scanning
Connection reset.*ssh|LOW|COUNT|SSH connection reset
Received disconnect.*ssh|MEDIUM|COUNT|SSH premature disconnect

# Suspicious SSH activity
User.*not allowed.*ssh|HIGH|ALERT|SSH user not allowed
Maximum authentication attempts.*ssh|HIGH|ALERT|SSH max auth attempts
Timeout.*ssh|MEDIUM|COUNT|SSH timeout

# SSH protocol violations
Protocol.*ssh|HIGH|ALERT|SSH protocol violation
Bad protocol version.*ssh|HIGH|ALERT|SSH bad protocol version
SSH_RULES_EOF

    # Network Attack Detection Rules
    cat << NET_RULES_EOF | sudo tee "$IDS_RULES_DIR/network_attacks.rules"
# Network Attack Detection Rules

# Port scanning
nmap|HIGH|ALERT|Nmap scan detected
masscan|HIGH|ALERT|Masscan detected
SYN flood|HIGH|ALERT|SYN flood attack
Port.*scan|MEDIUM|ALERT|Port scan detected

# DDoS attacks
DDOS|HIGH|BLOCK|DDoS attack detected
flood|HIGH|ALERT|Flood attack detected
amplification|HIGH|ALERT|Amplification attack

# Network intrusion
backdoor|HIGH|BLOCK|Backdoor detected
trojan|HIGH|BLOCK|Trojan detected
botnet|HIGH|BLOCK|Botnet activity
malware|HIGH|BLOCK|Malware detected

# Protocol attacks
DNS.*poison|HIGH|ALERT|DNS poisoning attempt
ARP.*spoof|HIGH|ALERT|ARP spoofing detected
ICMP.*flood|MEDIUM|ALERT|ICMP flood detected
NET_RULES_EOF

    # Web Attack Detection Rules
    cat << WEB_RULES_EOF | sudo tee "$IDS_RULES_DIR/web_attacks.rules"
# Web Attack Detection Rules

# SQL Injection
union.*select|HIGH|ALERT|SQL injection attempt
drop.*table|HIGH|ALERT|SQL injection (DROP)
insert.*into|MEDIUM|COUNT|SQL injection (INSERT)
update.*set|MEDIUM|COUNT|SQL injection (UPDATE)

# XSS attacks
<script|HIGH|ALERT|XSS attack attempt
javascript:|HIGH|ALERT|XSS javascript injection
eval\(|HIGH|ALERT|XSS eval injection
alert\(|MEDIUM|COUNT|XSS alert injection

# Directory traversal
\.\./|HIGH|ALERT|Directory traversal attempt
etc/passwd|HIGH|ALERT|System file access attempt
etc/shadow|HIGH|ALERT|Shadow file access attempt

# Command injection
;.*rm|HIGH|ALERT|Command injection (rm)
;.*cat|MEDIUM|COUNT|Command injection (cat)
;.*wget|HIGH|ALERT|Command injection (wget)
;.*curl|HIGH|ALERT|Command injection (curl)
WEB_RULES_EOF

    # System Attack Detection Rules
    cat << SYS_RULES_EOF | sudo tee "$IDS_RULES_DIR/system_attacks.rules"
# System Attack Detection Rules

# Privilege escalation
sudo.*passwd|HIGH|ALERT|Sudo password change attempt
su.*root|HIGH|ALERT|Root escalation attempt
chmod.*777|MEDIUM|COUNT|Dangerous permissions change
chown.*root|HIGH|ALERT|Root ownership change

# File system attacks
rm.*rf|HIGH|ALERT|Dangerous file deletion
find.*exec|MEDIUM|COUNT|Find command execution
crontab.*e|MEDIUM|COUNT|Crontab modification

# Process injection
ptrace|HIGH|ALERT|Process injection attempt
gdb.*attach|HIGH|ALERT|Debugger attachment
strace.*p|MEDIUM|COUNT|Process tracing

# Resource exhaustion
fork.*bomb|HIGH|BLOCK|Fork bomb detected
memory.*exhaustion|HIGH|ALERT|Memory exhaustion
CPU.*100|MEDIUM|COUNT|High CPU usage
SYS_RULES_EOF

    log_message "✅ Detection rules created"
}

# Function to create real-time detection engine
create_detection_engine() {
    log_message "⚙️ Creating real-time detection engine..."
    
    cat << DETECTION_ENGINE_EOF > ~/ids_detection_engine.sh
#!/bin/bash

# TwinTower IDS Real-time Detection Engine
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="\$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="\$IDS_LOG_DIR/detection.log"
IDS_STATE_FILE="/var/lib/twintower-ids/state"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
source "\$IDS_CONFIG_DIR/ids.conf"

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$IDS_DETECTION_LOG"
}

alert_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - ALERT: \$1" | tee -a "\$IDS_ALERT_LOG"
}

# Function to check if IP is whitelisted
is_whitelisted() {
    local ip="\$1"
    local whitelist_file="\$IDS_CONFIG_DIR/whitelist.conf"
    
    if [ -f "\$whitelist_file" ]; then
        # Simple IP matching (in production use more sophisticated matching)
        if grep -q "\$ip" "\$whitelist_file"; then
            return 0
        fi
        
        # Check network ranges (simplified)
        if [[ "\$ip" =~ ^192\.168\.1\. ]] && grep -q "192.168.1.0/24" "\$whitelist_file"; then
            return 0
        fi
        
        if [[ "\$ip" =~ ^100\.64\. ]] && grep -q "100.64.0.0/10" "\$whitelist_file"; then
            return 0
        fi
    fi
    
    return 1
}

# Function to process detection rule
process_rule() {
    local rule="\$1"
    local log_line="\$2"
    local source_ip="\$3"
    
    # Parse rule: PATTERN|SEVERITY|ACTION|DESCRIPTION
    local pattern=\$(echo "\$rule" | cut -d'|' -f1)
    local severity=\$(echo "\$rule" | cut -d'|' -f2)
    local action=\$(echo "\$rule" | cut -d'|' -f3)
    local description=\$(echo "\$rule" | cut -d'|' -f4)
    
    # Check if log line matches pattern
    if echo "\$log_line" | grep -qi "\$pattern"; then
        # Skip if whitelisted
        if is_whitelisted "\$source_ip"; then
            return 0
        fi
        
        # Execute action based on severity and configuration
        case "\$action" in
            "ALERT")
                alert_message "[\$severity] \$description - IP: \$source_ip"
                if [ "\$IDS_REALTIME_ALERTS" = "true" ]; then
                    send_alert "\$severity" "\$description" "\$source_ip"
                fi
                ;;
            "BLOCK")
                alert_message "[\$severity] BLOCKING - \$description - IP: \$source_ip"
                if [ "\$IDS_AUTO_BLOCK" = "true" ]; then
                    block_ip "\$source_ip" "\$description"
                fi
                ;;
            "COUNT")
                increment_counter "\$source_ip" "\$description"
                ;;
        esac
    fi
}

# Function to extract source IP from log line
extract_source_ip() {
    local log_line="\$1"
    
    # Extract IP using various patterns
    local ip=\$(echo "\$log_line" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    
    if [ -z "\$ip" ]; then
        ip="unknown"
    fi
    
    echo "\$ip"
}

# Function to increment counter for repeated events
increment_counter() {
    local ip="\$1"
    local event="\$2"
    
    local counter_file="/var/lib/twintower-ids/counters/\$ip"
    sudo mkdir -p "/var/lib/twintower-ids/counters"
    
    local count=1
    if [ -f "\$counter_file" ]; then
        count=\$(cat "\$counter_file")
        count=\$((count + 1))
    fi
    
    echo "\$count" > "\$counter_file"
    
    # Check if threshold exceeded
    if [ "\$count" -ge "\$IDS_ALERT_THRESHOLD" ]; then
        alert_message "[THRESHOLD] IP \$ip exceeded threshold (\$count events) - \$event"
        
        if [ "\$count" -ge "\$IDS_BLOCK_THRESHOLD" ] && [ "\$IDS_AUTO_BLOCK" = "true" ]; then
            block_ip "\$ip" "Threshold exceeded: \$event"
        fi
    fi
}

# Function to block IP address
block_ip() {
    local ip="\$1"
    local reason="\$2"
    
    log_message "🚫 Blocking IP: \$ip - Reason: \$reason"
    
    # Block using UFW
    sudo ufw deny from "\$ip" comment "IDS Block: \$reason"
    
    # Schedule unblock
    if [ "\$IDS_BLOCK_DURATION" -gt 0 ]; then
        echo "sudo ufw delete deny from \$ip" | at now + "\$IDS_BLOCK_DURATION seconds" 2>/dev/null || true
    fi
}

# Function to send alert
send_alert() {
    local severity="\$1"
    local description="\$2"
    local source_ip="\$3"
    
    # Log alert
    log_message "🚨 ALERT [\$severity]: \$description from \$source_ip"
    
    # Send email alert if configured
    if [ "\$IDS_EMAIL_ALERTS" = "true" ] && [ -n "\$IDS_EMAIL_RECIPIENT" ]; then
        echo "IDS Alert: \$description from \$source_ip" | mail -s "TwinTower IDS Alert [\$severity]" "\$IDS_EMAIL_RECIPIENT"
    fi
    
    # Send webhook alert if configured
    if [ "\$IDS_WEBHOOK_ALERTS" = "true" ] && [ -n "\$IDS_WEBHOOK_URL" ]; then
        curl -X POST -H "Content-Type: application/json" \
            -d "{\"alert\":\"TwinTower IDS Alert\",\"severity\":\"\$severity\",\"description\":\"\$description\",\"source_ip\":\"\$source_ip\"}" \
            "\$IDS_WEBHOOK_URL" 2>/dev/null || true
    fi
}

# Function to monitor log files
monitor_logs() {
    log_message "🔍 Starting real-time log monitoring..."
    
    # Monitor multiple log files
    tail -f /var/log/auth.log /var/log/syslog /var/log/ufw.log /var/log/nginx/access.log 2>/dev/null | \
    while read log_line; do
        # Extract source IP
        source_ip=\$(extract_source_ip "\$log_line")
        
        # Process against all rule files
        for rule_file in "\$IDS_RULES_DIR"/*.rules; do
            if [ -f "\$rule_file" ]; then
                while IFS= read -r rule; do
                    # Skip comments and empty lines
                    if [[ "\$rule" =~ ^#.*\$ ]] || [[ -z "\$rule" ]]; then
                        continue
                    fi
                    
                    process_rule "\$rule" "\$log_line" "\$source_ip"
                done < "\$rule_file"
            fi
        done
    done
}

# Function to generate IDS report
generate_ids_report() {
    local report_file="/tmp/ids_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower IDS Report
==================
Generated: \$(date)
Tower: \$(hostname)

IDS Configuration:
-----------------
Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")
Mode: \$IDS_MODE
Sensitivity: \$IDS_SENSITIVITY
Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "ENABLED" || echo "DISABLED")

Detection Statistics (Last 24 hours):
------------------------------------
Total Alerts: \$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
High Severity: \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
Medium Severity: \$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
Low Severity: \$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")

Blocked IPs:
-----------
\$(sudo ufw status | grep "IDS Block" || echo "No IPs currently blocked")

Top Alert Sources:
-----------------
\$(grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -10)

Recent High-Priority Alerts:
----------------------------
\$(grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -10)

Rule Effectiveness:
------------------
SSH Attacks: \$(grep -c "SSH.*attempt" "\$IDS_ALERT_LOG" || echo "0")
Network Attacks: \$(grep -c "scan.*detected" "\$IDS_ALERT_LOG" || echo "0")
Web Attacks: \$(grep -c "injection.*attempt" "\$IDS_ALERT_LOG" || echo "0")
System Attacks: \$(grep -c "escalation.*attempt" "\$IDS_ALERT_LOG" || echo "0")

REPORT_EOF

    log_message "📋 IDS report generated: \$report_file"
    echo "\$report_file"
}

# Function to start IDS daemon
start_ids_daemon() {
    log_message "🚀 Starting IDS daemon..."
    
    # Create state directory
    sudo mkdir -p /var/lib/twintower-ids/counters
    
    # Start monitoring
    monitor_logs
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_ids_daemon
        ;;
    "test")
        # Test detection rules
        echo "Testing IDS rules..."
        echo "authentication failure ssh" | while read line; do
            source_ip=\$(extract_source_ip "\$line")
            process_rule "authentication failure.*ssh|HIGH|ALERT|SSH brute force test" "\$line" "\$source_ip"
        done
        ;;
    "report")
        generate_ids_report
        ;;
    "status")
        echo "IDS Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")"
        echo "Active Rules: \$(find "\$IDS_RULES_DIR" -name "*.rules" | wc -l)"
        echo "Recent Alerts: \$(tail -n 5 "\$IDS_ALERT_LOG" | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <daemon|test|report|status>"
        exit 1
        ;;
esac
DETECTION_ENGINE_EOF

    chmod +x ~/ids_detection_engine.sh
    
    log_message "✅ Detection engine created"
}

# Function to create IDS management dashboard
create_ids_dashboard() {
    log_message "📊 Creating IDS management dashboard..."
    
    cat << IDS_DASHBOARD_EOF > ~/ids_dashboard.sh
#!/bin/bash

# TwinTower IDS Management Dashboard
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_ALERT_LOG="/var/log/twintower-ids/alerts.log"
IDS_DETECTION_LOG="/var/log/twintower-ids/detection.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
if [ -f "\$IDS_CONFIG_DIR/ids.conf" ]; then
    source "\$IDS_CONFIG_DIR/ids.conf"
fi

clear
echo -e "\${BLUE}🚨 TwinTower IDS Management Dashboard\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# IDS Status
echo -e "\${YELLOW}🛡️ IDS Status\${NC}"
echo "-------------"
if [ "\$IDS_ENABLED" = "true" ]; then
    echo -e "IDS Status: \${GREEN}✅ ENABLED\${NC}"
else
    echo -e "IDS Status: \${RED}❌ DISABLED\${NC}"
fi

echo -e "Mode: \${GREEN}\$IDS_MODE\${NC}"
echo -e "Sensitivity: \${GREEN}\$IDS_SENSITIVITY\${NC}"
echo -e "Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "\${GREEN}✅ ENABLED\${NC}" || echo "\${RED}❌ DISABLED\${NC}")"
echo

# Detection Statistics
echo -e "\${YELLOW}📊 Detection Statistics (Last 24 hours)\${NC}"
echo "--------------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    TOTAL_ALERTS=\$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
    HIGH_ALERTS=\$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
    MEDIUM_ALERTS=\$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
    LOW_ALERTS=\$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")
    
    echo -e "Total Alerts: \${BLUE}\$TOTAL_ALERTS\${NC}"
    echo -e "High Severity: \${RED}\$HIGH_ALERTS\${NC}"
    echo -e "Medium Severity: \${YELLOW}\$MEDIUM_ALERTS\${NC}"
    echo -e "Low Severity: \${GREEN}\$LOW_ALERTS\${NC}"
else
    echo -e "No alert data available"
fi
echo

# Active Rules
echo -e "\${YELLOW}📋 Active Rules\${NC}"
echo "---------------"
if [ -d "\$IDS_CONFIG_DIR/rules" ]; then
    RULE_COUNT=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" -exec wc -l {} + | tail -1 | awk '{print \$1}' || echo "0")
    RULE_FILES=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" | wc -l)
    echo -e "Rule Files: \${GREEN}\$RULE_FILES\${NC}"
    echo -e "Total Rules: \${GREEN}\$RULE_COUNT\${NC}"
    
    for rule_file in "\$IDS_CONFIG_DIR/rules"/*.rules; do
        if [ -f "\$rule_file" ]; then
            rule_name=\$(basename "\$rule_file" .rules)
            rule_count=\$(grep -c "^[^#]" "\$rule_file" || echo "0")
            echo -e "  \${GREEN}•\${NC} \$rule_name: \$rule_count rules"
        fi
    done
else
    echo -e "No rules configured"
fi
echo

# Recent Alerts
echo -e "\${YELLOW}🚨 Recent High-Priority Alerts\${NC}"
echo "------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -5 | while read line; do
        timestamp=\$(echo "\$line" | awk '{print \$1, \$2, \$3}')
        alert_msg=\$(echo "\$line" | cut -d'-' -f3-)
        echo -e "  \${RED}⚠️\${NC} \$timestamp:\$alert_msg"
    done
    
    if [ \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG") -eq 0 ]; then
        echo -e "  \${GREEN}✅ No high-priority alerts\${NC}"
    fi
else
    echo -e "No alert data available"
fi
echo

# Blocked IPs
echo -e "\${YELLOW}🚫 Blocked IPs\${NC}"
echo "-------------"
BLOCKED_IPS=\$(sudo ufw status | grep "IDS Block" | wc -l)
if [ \$BLOCKED_IPS -gt 0 ]; then
    echo -e "Currently Blocked: \${RED}\$BLOCKED_IPS\${NC}"
    sudo ufw status | grep "IDS Block" | head -5 | while read line; do
        echo -e "  \${RED}🔒\${NC} \$line"
    done
else
    echo -e "Currently Blocked: \${GREEN}0\${NC}"
fi
echo

# Top Alert Sources
echo -e "\${YELLOW}📈 Top Alert Sources\${NC}"
echo "--------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    echo "Top 5 IPs by alert count:"
    grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -5 | while read count ip; do
        echo -e "  \${RED}\$ip\${NC}: \$count alerts"
    done
else
    echo -e "No alert data available"
fi
echo

# System Health
echo -e "\${YELLOW}💓 System Health\${NC}"
echo "----------------"
IDS_PROCESS=\$(pgrep -f "ids_detection_engine.sh" | wc -l)
if [ \$IDS_PROCESS -gt 0 ]; then
    echo -e "Detection Engine: \${GREEN}✅ Running\${NC}"
else
    echo -e "Detection Engine: \${RED}❌ Stopped\${NC}"
fi

LOG_SIZE=\$(du -h "\$IDS_ALERT_LOG" 2>/dev/null | cut -f1 || echo "0")
echo -e "Alert Log Size: \${GREEN}\$LOG_SIZE\${NC}"

DISK_USAGE=\$(df -h /var/log | tail -1 | awk '{print \$5}')
echo -e "Log Disk Usage: \${GREEN}\$DISK_USAGE\${NC}"
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Start IDS: ./ids_detection_engine.sh daemon"
echo "2. View alerts: tail -f \$IDS_ALERT_LOG"
echo "3. Generate report: ./ids_detection_engine.sh report"
echo "4. Test rules: ./ids_detection_engine.sh test"
echo "5. View blocked IPs: sudo ufw status | grep 'IDS Block'"

echo
echo -e "\${BLUE}====================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
IDS_DASHBOARD_EOF

    chmod +x ~/ids_dashboard.sh
    
    log_message "✅ IDS dashboard created"
}

# Function to create IDS service
create_ids_service() {
    log_message "⚙️ Creating IDS systemd service..."
    
    cat << IDS_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-ids.service
[Unit]
Description=TwinTower Intrusion Detection System
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/ids_detection_engine.sh daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
IDS_SERVICE_EOF

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-ids.service
    
    log_message "✅ IDS service created"
}

# Function to test IDS system
test_ids_system() {
    log_message "🧪 Testing IDS system..."
    
    cat << IDS_TEST_EOF > ~/test_ids_system.sh
#!/bin/bash

# TwinTower IDS System Test
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower IDS System Test\${NC}"
echo -e "\${BLUE}===========================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test IDS configuration
echo -e "\${YELLOW}🔧 Testing IDS Configuration\${NC}"
echo "----------------------------"
run_test "IDS config directory exists" "[ -d '\$IDS_CONFIG_DIR' ]"
run_test "IDS rules directory exists" "[ -d '\$IDS_RULES_DIR' ]"
run_test "IDS configuration file exists" "[ -f '\$IDS_CONFIG_DIR/ids.conf' ]"
run_test "IDS whitelist file exists" "[ -f '\$IDS_CONFIG_DIR/whitelist.conf' ]"

# Test detection rules
echo -e "\${YELLOW}📋 Testing Detection Rules\${NC}"
echo "--------------------------"
run_test "SSH attack rules exist" "[ -f '\$IDS_RULES_DIR/ssh_attacks.rules' ]"
run_test "Network attack rules exist" "[ -f '\$IDS_RULES_DIR/network_attacks.rules' ]"
run_test "Web attack rules exist" "[ -f '\$IDS_RULES_DIR/web_attacks.rules' ]"
run_test "System attack rules exist" "[ -f '\$IDS_RULES_DIR/system_attacks.rules' ]"

# Test IDS components
echo -e "\${YELLOW}# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access policies..."
    
    # Internal Network Policy
    cat << INTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/internal-network.json"
{
    "policy_name": "InternalNetwork",
    "description": "Internal network access policy",
    "version": "1.0",
    "priority": 250,
    "conditions": {
        "source_networks": ["192.168.1.0/24", "172.16.0.0/12", "10.0.0.0/8"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp", "udp", "icmp"],
        "encryption_required": false,
        "authentication_required": true
    },
    "permissions": {
        "ssh_access": true,
        "web_access": true,
        "api_access": true,
        "file_access": true
    },
    "restrictions": {
        "bandwidth_limit": "1Gbps",
        "connection_limit": 100,
        "rate_limit": "moderate"
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": false
    }
}
INTERNAL_NET_EOF

    # External Network Policy
    cat << EXTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/external-network.json"
{
    "policy_name": "ExternalNetwork",
    "description": "External network access policy (high security)",
    "version": "1.0",
    "priority": 500,
    "conditions": {
        "source_networks": ["0.0.0.0/0"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp"],
        "encryption_required": true,
        "authentication_required": true,
        "vpn_required": true
    },
    "permissions": {
        "ssh_access": false,
        "web_access": true,
        "api_access": false,
        "file_access": false
    },
    "restrictions": {
        "bandwidth_limit": "10Mbps",
        "connection_limit": 5,
        "rate_limit": "strict",
        "geolocation_required": true,
        "time_limited": true
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": true,
        "threat_intelligence": true
    }
}
EXTERNAL_NET_EOF

    log_message "✅ Network-based policies created"
}

# Function to create zero-trust enforcement engine
create_zt_enforcement() {
    log_message "⚙️ Creating zero-trust enforcement engine..."
    
    cat << ZT_ENGINE_EOF > ~/zt_enforcement_engine.sh
#!/bin/bash

# TwinTower Zero-Trust Enforcement Engine
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_LOG_FILE"
}

audit_log() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_AUDIT_LOG"
}

# Function to validate user access
validate_user_access() {
    local user="\$1"
    local source_ip="\$2"
    local requested_service="\$3"
    local auth_method="\$4"
    
    log_message "🔍 Validating access for user: \$user from \$source_ip"
    
    # Check if user exists
    if ! id "\$user" &>/dev/null; then
        audit_log "DENY: User \$user does not exist"
        return 1
    fi
    
    # Load and evaluate policies
    local policy_result=0
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            if evaluate_policy "\$policy_file" "\$user" "\$source_ip" "\$requested_service" "\$auth_method"; then
                policy_result=1
                break
            fi
        fi
    done
    
    if [ \$policy_result -eq 1 ]; then
        audit_log "ALLOW: User \$user access granted for \$requested_service"
        create_session "\$user" "\$source_ip" "\$requested_service"
        return 0
    else
        audit_log "DENY: User \$user access denied for \$requested_service"
        return 1
    fi
}

# Function to evaluate policy
evaluate_policy() {
    local policy_file="\$1"
    local user="\$2"
    local source_ip="\$3"
    local requested_service="\$4"
    local auth_method="\$5"
    
    # Parse JSON policy (simplified - in production use jq)
    local policy_name=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
    
    log_message "📋 Evaluating policy: \$policy_name"
    
    # Check user conditions
    if grep -q '"users"' "\$policy_file"; then
        local users=\$(grep '"users"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$users" == *"\$user"* ]]; then
            log_message "✅ User \$user matches policy \$policy_name"
        else
            log_message "❌ User \$user does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check network conditions
    if grep -q '"source_networks"' "\$policy_file"; then
        local networks=\$(grep '"source_networks"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if check_network_match "\$source_ip" "\$networks"; then
            log_message "✅ Source IP \$source_ip matches policy \$policy_name"
        else
            log_message "❌ Source IP \$source_ip does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check time restrictions
    if grep -q '"time_restrictions"' "\$policy_file"; then
        if check_time_restrictions "\$policy_file"; then
            log_message "✅ Time restrictions satisfied for policy \$policy_name"
        else
            log_message "❌ Time restrictions not satisfied for policy \$policy_name"
            return 1
        fi
    fi
    
    # Check service permissions
    if grep -q '"\$requested_service"' "\$policy_file"; then
        local service_allowed=\$(grep '"\$requested_service"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
        if [[ "\$service_allowed" == "true" ]]; then
            log_message "✅ Service \$requested_service allowed in policy \$policy_name"
            return 0
        else
            log_message "❌ Service \$requested_service not allowed in policy \$policy_name"
            return 1
        fi
    fi
    
    return 0
}

# Function to check network match
check_network_match() {
    local source_ip="\$1"
    local networks="\$2"
    
    # Simple network matching (in production use ipcalc or similar)
    if [[ "\$networks" == *"100.64.0.0/10"* ]] && [[ "\$source_ip" == 100.64.* ]]; then
        return 0
    elif [[ "\$networks" == *"192.168.1.0/24"* ]] && [[ "\$source_ip" == 192.168.1.* ]]; then
        return 0
    elif [[ "\$networks" == *"0.0.0.0/0"* ]]; then
        return 0
    fi
    
    return 1
}

# Function to check time restrictions
check_time_restrictions() {
    local policy_file="\$1"
    
    local current_hour=\$(date +%H)
    local current_day=\$(date +%A | tr '[:upper:]' '[:lower:]')
    
    # Check allowed hours (simplified)
    if grep -q '"allowed_hours"' "\$policy_file"; then
        local allowed_hours=\$(grep '"allowed_hours"' "\$policy_file" | cut -d'"' -f4)
        local start_hour=\$(echo "\$allowed_hours" | cut -d'-' -f1 | cut -d':' -f1)
        local end_hour=\$(echo "\$allowed_hours" | cut -d'-' -f2 | cut -d':' -f1)
        
        if [ "\$current_hour" -ge "\$start_hour" ] && [ "\$current_hour" -le "\$end_hour" ]; then
            return 0
        else
            return 1
        fi
    fi
    
    # Check allowed days (simplified)
    if grep -q '"allowed_days"' "\$policy_file"; then
        local allowed_days=\$(grep '"allowed_days"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$allowed_days" == *"\$current_day"* ]]; then
            return 0
        else
            return 1
        fi
    fi
    
    return 0
}

# Function to create session
create_session() {
    local user="\$1"
    local source_ip="\$2"
    local service="\$3"
    
    sudo mkdir -p "\$ZT_SESSION_DIR"
    
    local session_id=\$(date +%s)_\$(echo "\$user\$source_ip" | md5sum | cut -d' ' -f1 | head -c 8)
    local session_file="\$ZT_SESSION_DIR/\$session_id.session"
    
    cat > "\$session_file" << SESSION_EOF
{
    "session_id": "\$session_id",
    "user": "\$user",
    "source_ip": "\$source_ip",
    "service": "\$service",
    "start_time": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "last_activity": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "status": "active"
}
SESSION_EOF

    log_message "✅ Session created: \$session_id for user \$user"
}

# Function to monitor active sessions
monitor_sessions() {
    log_message "📊 Monitoring active sessions..."
    
    if [ -d "\$ZT_SESSION_DIR" ]; then
        local active_sessions=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
        log_message "Active sessions: \$active_sessions"
        
        # Check for expired sessions
        for session_file in "\$ZT_SESSION_DIR"/*.session; do
            if [ -f "\$session_file" ]; then
                local session_id=\$(basename "\$session_file" .session)
                local start_time=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
                
                # Check if session is older than 1 hour (3600 seconds)
                local current_time=\$(date +%s)
                local session_time=\$(date -d "\$start_time" +%s)
                local age=\$((current_time - session_time))
                
                if [ \$age -gt 3600 ]; then
                    log_message "⏰ Expiring session: \$session_id"
                    rm -f "\$session_file"
                fi
            fi
        done
    fi
}

# Function to generate compliance report
generate_compliance_report() {
    local report_file="/tmp/zt_compliance_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Zero-Trust Compliance Report
====================================
Generated: \$(date)
Tower: \$(hostname)

Policy Compliance:
-----------------
Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
Enforcement Status: \$(grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf" && echo "ENABLED" || echo "DISABLED")

Access Statistics (Last 24 hours):
---------------------------------
Total Access Attempts: \$(grep -c "Validating access" "\$ZT_LOG_FILE" || echo "0")
Successful Authentications: \$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
Denied Access Attempts: \$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")

Active Sessions:
---------------
Current Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)

Recent Security Events:
----------------------
\$(tail -n 20 "\$ZT_AUDIT_LOG" 2>/dev/null || echo "No recent events")

Policy Violations:
-----------------
\$(grep "DENY:" "\$ZT_AUDIT_LOG" | tail -10 || echo "No recent violations")

Recommendations:
---------------
\$([ \$(grep -c "DENY:" "\$ZT_AUDIT_LOG") -gt 10 ] && echo "High number of access denials - review policies" || echo "Access patterns appear normal")

REPORT_EOF

    log_message "📋 Compliance report generated: \$report_file"
    echo "\$report_file"
}

# Main execution
case "\${1:-monitor}" in
    "validate")
        validate_user_access "\$2" "\$3" "\$4" "\$5"
        ;;
    "monitor")
        log_message "🚀 Starting zero-trust monitoring..."
        while true; do
            monitor_sessions
            sleep 300
        done
        ;;
    "report")
        generate_compliance_report
        ;;
    "status")
        echo "Zero-Trust Status:"
        echo "=================="
        echo "Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)"
        echo "Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)"
        echo "Recent Events: \$(tail -n 5 "\$ZT_AUDIT_LOG" 2>/dev/null | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <validate|monitor|report|status>"
        echo "  validate <user> <source_ip> <service> <auth_method>"
        exit 1
        ;;
esac
ZT_ENGINE_EOF

    chmod +x ~/zt_enforcement_engine.sh
    
    log_message "✅ Zero-trust enforcement engine created"
}

# Function to create zero-trust monitoring dashboard
create_zt_dashboard() {
    log_message "📊 Creating zero-trust monitoring dashboard..."
    
    cat << ZT_DASHBOARD_EOF > ~/zt_dashboard.sh
#!/bin/bash

# TwinTower Zero-Trust Dashboard
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔒 TwinTower Zero-Trust Dashboard\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Zero-Trust Status
echo -e "\${YELLOW}🛡️ Zero-Trust Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_CONFIG_DIR/zero-trust.conf" ]; then
    if grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf"; then
        echo -e "Zero-Trust: \${GREEN}✅ ENABLED\${NC}"
    else
        echo -e "Zero-Trust: \${RED}❌ DISABLED\${NC}"
    fi
else
    echo -e "Zero-Trust: \${RED}❌ NOT CONFIGURED\${NC}"
fi

# Policy Status
POLICY_COUNT=\$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
echo -e "Active Policies: \${GREEN}\$POLICY_COUNT\${NC}"

# Session Status
if [ -d "\$ZT_SESSION_DIR" ]; then
    SESSION_COUNT=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
    echo -e "Active Sessions: \${GREEN}\$SESSION_COUNT\${NC}"
else
    echo -e "Active Sessions: \${YELLOW}0\${NC}"
fi
echo

# Access Statistics
echo -e "\${YELLOW}📊 Access Statistics (Last 24 hours)\${NC}"
echo "-----------------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    ALLOW_COUNT=\$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
    DENY_COUNT=\$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")
    TOTAL_COUNT=\$((ALLOW_COUNT + DENY_COUNT))
    
    echo -e "Total Requests: \${BLUE}\$TOTAL_COUNT\${NC}"
    echo -e "Allowed: \${GREEN}\$ALLOW_COUNT\${NC}"
    echo -e "Denied: \${RED}\$DENY_COUNT\${NC}"
    
    if [ \$TOTAL_COUNT -gt 0 ]; then
        SUCCESS_RATE=\$(echo "scale=2; \$ALLOW_COUNT * 100 / \$TOTAL_COUNT" | bc -l 2>/dev/null || echo "0")
        echo -e "Success Rate: \${GREEN}\$SUCCESS_RATE%\${NC}"
    fi
else
    echo -e "No audit data available"
fi
echo

# Active Policies
echo -e "\${YELLOW}📋 Active Policies\${NC}"
echo "------------------"
if [ -d "\$ZT_POLICIES_DIR" ]; then
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            POLICY_NAME=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
            PRIORITY=\$(grep '"priority"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
            echo -e "  \${GREEN}•\${NC} \$POLICY_NAME (Priority: \$PRIORITY)"
        fi
    done
else
    echo -e "No policies configured"
fi
echo

# Recent Events
echo -e "\${YELLOW}🔍 Recent Security Events\${NC}"
echo "-------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    tail -n 5 "\$ZT_AUDIT_LOG" | while read line; do
        if [[ "\$line" == *"ALLOW:"* ]]; then
            echo -e "\${GREEN}✅ \$line\${NC}"
        elif [[ "\$line" == *"DENY:"* ]]; then
            echo -e "\${RED}❌ \$line\${NC}"
        else
            echo -e "\${BLUE}ℹ️  \$line\${NC}"
        fi
    done
else
    echo -e "No recent events"
fi
echo

# Active Sessions
echo -e "\${YELLOW}👥 Active Sessions\${NC}"
echo "------------------"
if [ -d "\$ZT_SESSION_DIR" ]; then
    for session_file in "\$ZT_SESSION_DIR"/*.session; do
        if [ -f "\$session_file" ]; then
            USER=\$(grep '"user"' "\$session_file" | cut -d'"' -f4)
            SOURCE_IP=\$(grep '"source_ip"' "\$session_file" | cut -d'"' -f4)
            SERVICE=\$(grep '"service"' "\$session_file" | cut -d'"' -f4)
            START_TIME=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
            echo -e "  \${GREEN}•\${NC} \$USER from \$SOURCE_IP (\$SERVICE) - \$START_TIME"
        fi
    done
    
    if [ \$SESSION_COUNT -eq 0 ]; then
        echo -e "No active sessions"
    fi
else
    echo -e "No session data available"
fi
echo

# Compliance Status
echo -e "\${YELLOW}📊 Compliance Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    RECENT_VIOLATIONS=\$(grep "DENY:" "\$ZT_AUDIT_LOG" | grep "\$(date '+%Y-%m-%d')" | wc -l)
    
    if [ \$RECENT_VIOLATIONS -eq 0 ]; then
        echo -e "Compliance Status: \${GREEN}✅ GOOD\${NC}"
    elif [ \$RECENT_VIOLATIONS -lt 5 ]; then
        echo -e "Compliance Status: \${YELLOW}⚠️  MODERATE\${NC}"
    else
        echo -e "Compliance Status: \${RED}❌ NEEDS ATTENTION\${NC}"
    fi
    
    echo -e "Today's Violations: \${RED}\$RECENT_VIOLATIONS\${NC}"
else
    echo -e "Compliance Status: \${YELLOW}⚠️  NO DATA\${NC}"
fi
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View policies: ls \$ZT_POLICIES_DIR/"
echo "2. Monitor sessions: ./zt_enforcement_engine.sh monitor"
echo "3. Generate report: ./zt_enforcement_engine.sh report"
echo "4. Check status: ./zt_enforcement_engine.sh status"

echo
echo -e "\${BLUE}=================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
ZT_DASHBOARD_EOF

    chmod +x ~/zt_dashboard.sh
    
    log_message "✅ Zero-trust monitoring dashboard created"
}

# Function to create zero-trust testing suite
create_zt_testing() {
    log_message "🧪 Creating zero-trust testing suite..."
    
    cat << ZT_TEST_EOF > ~/test_zero_trust.sh
#!/bin/bash

# TwinTower Zero-Trust Testing Suite
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Zero-Trust Testing Suite\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zero-trust configuration
echo -e "\${YELLOW}🔧 Testing Zero-Trust Configuration\${NC}"
echo "-----------------------------------"
run_test "ZT config directory exists" "[ -d '\$ZT_CONFIG_DIR' ]"
run_test "ZT policies directory exists" "[ -d '\$ZT_POLICIES_DIR' ]"
run_test "ZT configuration file exists" "[ -f '\$ZT_CONFIG_DIR/zero-trust.conf' ]"

# Test policy files
echo -e "\${YELLOW}📋 Testing Policy Files\${NC}"
echo "----------------------"
run_test "Admin users policy exists" "[ -f '\$ZT_POLICIES_DIR/admin-users.json' ]"
run_test "Standard users policy exists" "[ -f '\$ZT_POLICIES_DIR/standard-users.json' ]"
run_test "Service accounts policy exists" "[ -f '\$ZT_POLICIES_DIR/service-accounts.json' ]"
run_test "Trusted devices policy exists" "[ -f '\$ZT_POLICIES_DIR/trusted-devices.json' ]"
run_test "BYOD policy exists" "[ -f '\$ZT_POLICIES_DIR/byod-devices.json' ]"

# Test enforcement engine
echo -e "\${YELLOW}⚙️ Testing Enforcement Engine\${NC}"
echo "-----------------------------"
run_test "Enforcement engine exists" "[ -f '\$HOME/zt_enforcement_engine.sh' ]"
run_test "Enforcement engine executable" "[ -x '\$HOME/zt_enforcement_engine.sh' ]"
run_test "ZT dashboard exists" "[ -f '\$HOME/zt_dashboard.sh' ]"

# Test log files
echo -e "\${YELLOW}📊 Testing Logging\${NC}"
echo "------------------"
run_test "ZT log file exists" "[ -f '/var/log/zero-trust.log' ]"
run_test "ZT audit log exists" "[ -f '/var/log/zero-trust-audit.log' ]"

# Test policy validation
echo -e "\${YELLOW}🔍 Testing Policy Validation\${NC}"
echo "----------------------------"
for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
    if [ -f "\$policy_file" ]; then
        policy_name=\$(basename "\$policy_file" .json)
        run_test "Policy \$policy_name is valid JSON" "python3 -m json.tool '\$policy_file' > /dev/null"
    fi
done

# Test access scenarios
echo -e "\${YELLOW}🚪 Testing Access Scenarios\${NC}"
echo "---------------------------"
run_test "Admin access validation" "./zt_enforcement_engine.sh validate ubuntu 100.64.0.1 ssh_access publickey"
run_test "External access blocking" "! ./zt_enforcement_engine.sh validate hacker 1.2.3.4 ssh_access password"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zero-trust tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
ZT_TEST_EOF

    chmod +x ~/test_zero_trust.sh
    
    log_message "✅ Zero-trust testing suite created"
}

# Main execution
main() {
    echo -e "${BLUE}🔒 TwinTower Zero-Trust Access Control${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_zero_trust
            create_identity_policies
            create_device_policies
            create_network_policies
            create_zt_enforcement
            create_zt_dashboard
            create_zt_testing
            
            # Create session directory
            sudo mkdir -p /var/lib/zero-trust/sessions
            
            echo -e "${GREEN}✅ Zero-trust access control configured!${NC}"
            ;;
        "status")
            ~/zt_dashboard.sh
            ;;
        "test")
            ~/test_zero_trust.sh
            ;;
        "monitor")
            ~/zt_enforcement_engine.sh monitor
            ;;
        "report")
            ~/zt_enforcement_engine.sh report
            ;;
        "validate")
            ~/zt_enforcement_engine.sh validate "$POLICY_NAME" "$3" "$4" "$5"
            ;;
        "policies")
            if [ -d "$ZT_POLICIES_DIR" ]; then
                for policy_file in "$ZT_POLICIES_DIR"/*.json; do
                    if [ -f "$policy_file" ]; then
                        policy_name=$(grep '"policy_name"' "$policy_file" | cut -d'"' -f4)
                        priority=$(grep '"priority"' "$policy_file" | cut -d':' -f2 | tr -d ' ,')
                        echo -e "${BLUE}Policy: $policy_name${NC} (Priority: $priority)"
                    fi
                done
            else
                echo -e "${RED}❌ No policies configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|test|monitor|report|validate|policies> [policy_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/zero_trust_access.sh
```

### **Step 2: Execute Zero-Trust Setup**

```bash
# Setup zero-trust access control
./zero_trust_access.sh setup

# View zero-trust status
./zero_trust_access.sh status

# Test zero-trust implementation
./zero_trust_access.sh test

# Monitor zero-trust enforcement
./zero_trust_access.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## # Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone-based firewall rules..."
    
    # Create UFW application profiles for each zone
    create_ufw_app_profiles
    
    # Apply zone-specific rules
    for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "$zone_file" ]; then
            source "$zone_file"
            apply_zone_rules "$ZONE_NAME" "$zone_file"
        fi
    done
    
    log_message "✅ Zone-based firewall rules implemented"
}

# Function to create UFW application profiles
create_ufw_app_profiles() {
    log_message "📋 Creating UFW application profiles..."
    
    # TwinTower Management Profile
    cat << MGMT_PROFILE_EOF | sudo tee /etc/ufw/applications.d/twintower-management
[TwinTower-Management]
title=TwinTower Management Services
description=Administrative and monitoring interfaces
ports=3000:3099/tcp|6000:6099/tcp

[TwinTower-SSH]
title=TwinTower SSH Services
description=Custom SSH ports for towers
ports=2122,2222,2322/tcp

[TwinTower-GPU]
title=TwinTower GPU Services
description=GPU compute and ML workloads
ports=4000:4099/tcp|8000:8099/tcp

[TwinTower-Docker]
title=TwinTower Docker Services
description=Container orchestration and services
ports=2377/tcp|4789/udp|7946/tcp|7946/udp|5000:5099/tcp
MGMT_PROFILE_EOF

    # Reload UFW application profiles
    sudo ufw app update all
    
    log_message "✅ UFW application profiles created"
}

# Function to apply zone-specific rules
apply_zone_rules() {
    local zone_name="$1"
    local zone_file="$2"
    
    log_message "🔒 Applying rules for zone: $zone_name"
    
    # Source zone configuration
    source "$zone_file"
    
    case "$zone_name" in
        "DMZ")
            # DMZ zone rules - restrictive
            sudo ufw deny from any to any port 22 comment "DMZ: Block SSH"
            sudo ufw allow from any to any port 80 comment "DMZ: Allow HTTP"
            sudo ufw allow from any to any port 443 comment "DMZ: Allow HTTPS"
            sudo ufw limit from any to any port 8080 comment "DMZ: Limit Alt HTTP"
            ;;
        "INTERNAL")
            # Internal zone rules - moderate
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Internal: SSH Access"
                sudo ufw allow from "$network" to any app TwinTower-Docker comment "Internal: Docker Services"
            done
            ;;
        "TRUSTED")
            # Trusted zone rules - permissive
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" comment "Trusted: Full Access"
            done
            ;;
        "MANAGEMENT")
            # Management zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-Management comment "Management: Admin Access"
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Management: SSH Access"
            done
            ;;
        "GPU")
            # GPU zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-GPU comment "GPU: Compute Access"
            done
            ;;
    esac
    
    log_message "✅ Zone rules applied for: $zone_name"
}

# Function to create zone monitoring
create_zone_monitoring() {
    log_message "📊 Creating zone monitoring system..."
    
    cat << ZONE_MONITOR_EOF > ~/zone_monitor.sh
#!/bin/bash

# TwinTower Zone Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-300}"
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/zone-monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor zone traffic
monitor_zone_traffic() {
    local zone_name="\$1"
    local zone_networks="\$2"
    
    log_message "📈 Monitoring traffic for zone: \$zone_name"
    
    # Count connections per zone
    local connection_count=0
    
    IFS=',' read -ra NETWORKS <<< "\$zone_networks"
    for network in "\${NETWORKS[@]}"; do
        # Count active connections from this network
        local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
        connection_count=\$((connection_count + net_connections))
    done
    
    log_message "Zone \$zone_name: \$connection_count active connections"
    
    # Check for anomalies
    if [ "\$connection_count" -gt 100 ]; then
        log_message "🚨 HIGH ALERT: Unusual connection count for zone \$zone_name: \$connection_count"
    fi
}

# Function to analyze zone security events
analyze_zone_security() {
    local zone_name="\$1"
    
    log_message "🔍 Analyzing security events for zone: \$zone_name"
    
    # Check UFW logs for zone-related blocks
    local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$zone_name" || echo "0")
    
    if [ "\$blocked_today" -gt 0 ]; then
        log_message "🛡️ Zone \$zone_name: \$blocked_today blocked attempts today"
    fi
}

# Function to generate zone report
generate_zone_report() {
    local report_file="/tmp/zone_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Network Zone Report
============================
Generated: \$(date)
Tower: \$(hostname)

Zone Status Overview:
--------------------
REPORT_EOF

    # Analyze each zone
    for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "\$zone_file" ]; then
            source "\$zone_file"
            echo "Zone: \$ZONE_NAME (\$ZONE_TRUST_LEVEL trust)" >> "\$report_file"
            echo "  Networks: \$ZONE_NETWORKS" >> "\$report_file"
            echo "  Ports: \$ZONE_PORTS" >> "\$report_file"
            echo "  Status: Active" >> "\$report_file"
            echo "" >> "\$report_file"
        fi
    done
    
    cat >> "\$report_file" << REPORT_EOF

Recent Security Events:
----------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | tail -10)

Zone Traffic Summary:
--------------------
\$(sudo ss -s)

REPORT_EOF

    log_message "📋 Zone report generated: \$report_file"
    echo "\$report_file"
}

# Function to start zone monitoring
start_zone_monitoring() {
    log_message "🚀 Starting zone monitoring daemon..."
    
    while true; do
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                monitor_zone_traffic "\$ZONE_NAME" "\$ZONE_NETWORKS"
                analyze_zone_security "\$ZONE_NAME"
            fi
        done
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 12)) -eq 0 ]; then
            generate_zone_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_zone_monitoring
        ;;
    "report")
        generate_zone_report
        ;;
    "status")
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                echo -e "\${BLUE}Zone: \$ZONE_NAME\${NC}"
                echo "  Trust Level: \$ZONE_TRUST_LEVEL"
                echo "  Networks: \$ZONE_NETWORKS"
                echo "  Ports: \$ZONE_PORTS"
                echo ""
            fi
        done
        ;;
    *)
        echo "Usage: \$0 <monitor|report|status>"
        exit 1
        ;;
esac
ZONE_MONITOR_EOF

    chmod +x ~/zone_monitor.sh
    
    log_message "✅ Zone monitoring system created"
}

# Function to create zone management dashboard
create_zone_dashboard() {
    log_message "📊 Creating zone management dashboard..."
    
    cat << DASHBOARD_EOF > ~/zone_dashboard.sh
#!/bin/bash

# TwinTower Zone Management Dashboard
set -e

ZONES_CONFIG_DIR="/etc/network-zones"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🌐 TwinTower Network Zone Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# Zone overview
echo -e "\${YELLOW}📋 Zone Overview\${NC}"
echo "----------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Determine status color based on trust level
        case "\$ZONE_TRUST_LEVEL" in
            "HIGH") STATUS_COLOR="\${GREEN}" ;;
            "MEDIUM") STATUS_COLOR="\${YELLOW}" ;;
            "LOW") STATUS_COLOR="\${RED}" ;;
            *) STATUS_COLOR="\${NC}" ;;
        esac
        
        echo -e "\${STATUS_COLOR}🔒 \$ZONE_NAME\${NC} (\$ZONE_TRUST_LEVEL trust)"
        echo "   Networks: \$ZONE_NETWORKS"
        echo "   Ports: \$ZONE_PORTS"
        echo ""
    fi
done

# Active connections per zone
echo -e "\${YELLOW}📊 Active Connections\${NC}"
echo "--------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Count connections (simplified)
        local connection_count=0
        IFS=',' read -ra NETWORKS <<< "\$ZONE_NETWORKS"
        for network in "\${NETWORKS[@]}"; do
            if [ "\$network" != "0.0.0.0/0" ]; then
                local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
                connection_count=\$((connection_count + net_connections))
            fi
        done
        
        echo -e "\$ZONE_NAME: \${GREEN}\$connection_count\${NC} active"
    fi
done
echo

# Security events
echo -e "\${YELLOW}🚨 Security Events (Today)\${NC}"
echo "-------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$ZONE_NAME" || echo "0")
        
        if [ "\$blocked_today" -gt 0 ]; then
            echo -e "\$ZONE_NAME: \${RED}\$blocked_today\${NC} blocked attempts"
        else
            echo -e "\$ZONE_NAME: \${GREEN}No threats\${NC}"
        fi
    fi
done
echo

# Zone rules summary
echo -e "\${YELLOW}📋 Zone Rules Summary\${NC}"
echo "--------------------"
TOTAL_RULES=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Total UFW Rules: \${GREEN}\$TOTAL_RULES\${NC}"
echo -e "Zone-based Rules: \${GREEN}\$(sudo ufw status | grep -c "Zone\|DMZ\|Internal\|Trusted\|Management\|GPU" || echo "0")\${NC}"
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Monitor zones: ./zone_monitor.sh"
echo "2. Generate report: ./zone_monitor.sh report"
echo "3. View UFW status: sudo ufw status verbose"
echo "4. Reload zones: ./network_segmentation.sh reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/zone_dashboard.sh
    
    log_message "✅ Zone management dashboard created"
}

# Function to create zone testing script
create_zone_testing() {
    log_message "🧪 Creating zone testing script..."
    
    cat << TEST_EOF > ~/test_network_zones.sh
#!/bin/bash

# TwinTower Network Zone Testing Script
set -e

ZONES_CONFIG_DIR="/etc/network-zones"
TEST_RESULTS="/tmp/zone_test_results_\$(date +%Y%m%d_%H%M%S).txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Network Zone Testing\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        echo "PASS: \$test_name" >> "\$TEST_RESULTS"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        echo "FAIL: \$test_name" >> "\$TEST_RESULTS"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zone configuration files
echo -e "\${YELLOW}📋 Testing Zone Configuration\${NC}"
echo "------------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        zone_name=\$(basename "\$zone_file" .conf)
        run_test "Zone config exists: \$zone_name" "[ -f '\$zone_file' ]"
        run_test "Zone config readable: \$zone_name" "[ -r '\$zone_file' ]"
    fi
done

# Test UFW application profiles
echo -e "\${YELLOW}🔧 Testing UFW Application Profiles\${NC}"
echo "-----------------------------------"
run_test "TwinTower-Management profile" "sudo ufw app info TwinTower-Management"
run_test "TwinTower-SSH profile" "sudo ufw app info TwinTower-SSH"
run_test "TwinTower-GPU profile" "sudo ufw app info TwinTower-GPU"
run_test "TwinTower-Docker profile" "sudo ufw app info TwinTower-Docker"

# Test zone-specific connectivity
echo -e "\${YELLOW}🌐 Testing Zone Connectivity\${NC}"
echo "----------------------------"

# Test Tailscale (Trusted Zone)
if command -v tailscale &> /dev/null; then
    TAILSCALE_IP=\$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "\$TAILSCALE_IP" ]; then
        run_test "Tailscale connectivity" "ping -c 1 \$TAILSCALE_IP"
    fi
fi

# Test SSH connectivity
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
run_test "SSH port accessible" "timeout 5 bash -c '</dev/tcp/localhost/\$SSH_PORT'"

# Test Docker connectivity
if command -v docker &> /dev/null; then
    run_test "Docker daemon accessible" "docker version"
fi

# Test zone isolation
echo -e "\${YELLOW}🔒 Testing Zone Isolation\${NC}"
echo "-------------------------"
run_test "UFW active" "sudo ufw status | grep -q 'Status: active'"
run_test "Default deny incoming" "sudo ufw status verbose | grep -q 'Default: deny (incoming)'"
run_test "Zone rules present" "sudo ufw status | grep -q 'Zone\|DMZ\|Internal\|Trusted'"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zone tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi

echo -e "\${BLUE}📄 Detailed results: \$TEST_RESULTS\${NC}"
TEST_EOF

    chmod +x ~/test_network_zones.sh
    
    log_message "✅ Zone testing script created"
}

# Main execution
main() {
    echo -e "${BLUE}🌐 TwinTower Network Segmentation & Zone Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}===================================================${NC}"
    
    case "$ACTION" in
        "setup")
            define_network_zones
            implement_zone_rules
            create_zone_monitoring
            create_zone_dashboard
            create_zone_testing
            
            echo -e "${GREEN}✅ Network segmentation configured!${NC}"
            ;;
        "status")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                ~/zone_dashboard.sh
            else
                echo -e "${RED}❌ Network zones not configured${NC}"
            fi
            ;;
        "monitor")
            ~/zone_monitor.sh
            ;;
        "test")
            ~/test_network_zones.sh
            ;;
        "reload")
            implement_zone_rules
            sudo ufw reload
            echo -e "${GREEN}✅ Zone rules reloaded${NC}"
            ;;
        "list")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
                    if [ -f "$zone_file" ]; then
                        source "$zone_file"
                        echo -e "${BLUE}Zone: $ZONE_NAME${NC}"
                        echo "  Description: $ZONE_DESCRIPTION"
                        echo "  Trust Level: $ZONE_TRUST_LEVEL"
                        echo "  Networks: $ZONE_NETWORKS"
                        echo ""
                    fi
                done
            else
                echo -e "${RED}❌ No zones configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|monitor|test|reload|list> [zone_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/network_segmentation.sh
```

### **Step 2: Execute Network Segmentation Setup**

```bash
# Setup network segmentation
./network_segmentation.sh setup

# View zone configuration
./network_segmentation.sh list

# Test zone implementation
./network_segmentation.sh test

# Monitor zones
./network_segmentation.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔒 **Zero-Trust Access Policies**

### **Step 1: Create Zero-Trust Access Control System**

```bash
cat > ~/zero_trust_access.sh << 'EOF'
#!/bin/bash

# TwinTower Zero-Trust Access Control System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
POLICY_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Zero-trust configuration
ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$ZT_LOG_FILE"
}

# Function to setup zero-trust infrastructure
setup_zero_trust() {
    log_message "🔒 Setting up zero-trust infrastructure..."
    
    # Create configuration directories
    sudo mkdir -p "$ZT_CONFIG_DIR" "$ZT_POLICIES_DIR"
    sudo touch "$ZT_LOG_FILE"
    
    # Create zero-trust configuration
    cat << ZT_CONFIG_EOF | sudo tee "$ZT_CONFIG_DIR/zero-trust.conf"
# TwinTower Zero-Trust Configuration
ZT_ENABLED=true
ZT_DEFAULT_POLICY="DENY"
ZT_LOGGING_LEVEL="INFO"
ZT_AUDIT_ENABLED=true
ZT_ENCRYPTION_REQUIRED=true
ZT_AUTHENTICATION_REQUIRED=true
ZT_AUTHORIZATION_REQUIRED=true
ZT_CONTINUOUS_VERIFICATION=true
ZT_SESSION_TIMEOUT=3600
ZT_MAX_FAILED_ATTEMPTS=3
ZT_LOCKOUT_DURATION=1800
ZT_GEOLOCATION_ENABLED=false
ZT_DEVICE_FINGERPRINTING=true
ZT_BEHAVIORAL_ANALYSIS=true
ZT_CONFIG_EOF

    log_message "✅ Zero-trust infrastructure created"
}

# Function to create identity-based policies
create_identity_policies() {
    log_message "👤 Creating identity-based access policies..."
    
    # Administrative Users Policy
    cat << ADMIN_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/admin-users.json"
{
    "policy_name": "AdminUsers",
    "description": "Administrative users with elevated privileges",
    "version": "1.0",
    "priority": 100,
    "conditions": {
        "users": ["ubuntu", "admin", "root"],
        "groups": ["sudo", "docker", "adm"],
        "authentication_methods": ["publickey", "certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "06:00-23:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": true,
        "docker_access": true,
        "gpu_access": true,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 5,
        "session_timeout": 3600,
        "idle_timeout": 1800,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "INFO",
        "log_commands": true,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
ADMIN_POLICY_EOF

    # Standard Users Policy
    cat << USER_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/standard-users.json"
{
    "policy_name": "StandardUsers",
    "description": "Standard users with limited privileges",
    "version": "1.0",
    "priority": 200,
    "conditions": {
        "users": ["user", "developer", "analyst"],
        "groups": ["users"],
        "authentication_methods": ["publickey"],
        "source_networks": ["100.64.0.0/10"],
        "time_restrictions": {
            "allowed_hours": "08:00-18:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": false,
        "gpu_access": true,
        "monitoring_access": false,
        "log_access": false
    },
    "restrictions": {
        "max_sessions": 2,
        "session_timeout": 2400,
        "idle_timeout": 900,
        "password_required": false,
        "mfa_required": true
    },
    "audit": {
        "log_level": "WARN",
        "log_commands": false,
        "log_file_access": false,
        "alert_on_failure": true
    }
}
USER_POLICY_EOF

    # Service Accounts Policy
    cat << SERVICE_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/service-accounts.json"
{
    "policy_name": "ServiceAccounts",
    "description": "Automated service accounts",
    "version": "1.0",
    "priority": 300,
    "conditions": {
        "users": ["docker", "monitoring", "backup"],
        "groups": ["service"],
        "authentication_methods": ["certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "00:00-23:59",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": true,
        "gpu_access": false,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 10,
        "session_timeout": 7200,
        "idle_timeout": 3600,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "ERROR",
        "log_commands": false,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
SERVICE_POLICY_EOF

    log_message "✅ Identity-based policies created"
}

# Function to create device-based policies
create_device_policies() {
    log_message "📱 Creating device-based access policies..."
    
    # Trusted Devices Policy
    cat << TRUSTED_DEVICE_EOF | sudo tee "$ZT_POLICIES_DIR/trusted-devices.json"
{
    "policy_name": "TrustedDevices",
    "description": "Pre-approved trusted devices",
    "version": "1.0",
    "priority": 150,
    "conditions": {
        "device_types": ["laptop", "workstation", "server"],
        "os_types": ["linux", "windows", "macos"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "current",
        "certificate_required": true
    },
    "permissions": {
        "full_access": true,
        "admin_access": true,
        "sensitive_data_access": true
    },
    "restrictions": {
        "geolocation_required": false,
        "vpn_required": false,
        "time_limited": false
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true
    }
}
TRUSTED_DEVICE_EOF

    # BYOD Policy
    cat << BYOD_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/byod-devices.json"
{
    "policy_name": "BYODDevices",
    "description": "Bring Your Own Device policy",
    "version": "1.0",
    "priority": 400,
    "conditions": {
        "device_types": ["mobile", "tablet", "personal-laptop"],
        "os_types": ["android", "ios", "windows", "macos", "linux"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "recent",
        "certificate_required": false
    },
    "permissions": {
        "full_access": false,
        "admin_access": false,
        "sensitive_data_access": false,
        "limited_access": true
    },
    "restrictions": {
        "geolocation_required": true,
        "vpn_required": true,
        "time_limited": true,
        "data_download_restricted": true,
        "screenshot_blocked": true
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true,
        "data_loss_prevention": true
    }
}
BYOD_POLICY_EOF

    log_message "✅ Device-based policies created"
}

# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access# 🔥 Section 5C: Firewall & Access Control
## TwinTower GPU Infrastructure Guide

---

### 📑 **Table of Contents**
- [🎯 Overview](#-overview)
- [🔧 Prerequisites](#-prerequisites)
- [🛡️ Advanced UFW Firewall Configuration](#-advanced-ufw-firewall-configuration)
- [🌐 Network Segmentation & Zone Management](#-network-segmentation--zone-management)
- [🔒 Zero-Trust Access Policies](#-zero-trust-access-policies)
- [🚨 Intrusion Detection & Prevention](#-intrusion-detection--prevention)
- [📊 Network Traffic Monitoring](#-network-traffic-monitoring)
- [⚡ Performance Optimization](#-performance-optimization)
- [🔄 Backup & Recovery](#-backup--recovery)
- [🚀 Next Steps](#-next-steps)

---

## 🎯 **Overview**

Section 5C implements comprehensive firewall and access control policies to complete your TwinTower GPU infrastructure security framework, building upon the secure Tailscale mesh (5A) and hardened SSH (5B) implementations.

### **What This Section Accomplishes:**
- ✅ Advanced UFW firewall with intelligent rules
- ✅ Network segmentation with security zones
- ✅ Zero-trust access policies and micro-segmentation
- ✅ Intrusion detection and prevention systems
- ✅ Real-time network traffic monitoring
- ✅ Performance-optimized security policies
- ✅ Automated threat response and mitigation

### **Security Architecture:**
```
Internet ←→ Tailscale Mesh ←→ Firewall Zones ←→ TwinTower Infrastructure
                                     ↓
    ┌─────────────────────────────────────────────────────────────────────┐
    │     DMZ Zone          Internal Zone        Management Zone           │
    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
    │  │ Public APIs │    │ GPU Cluster │    │ Admin Tools │              │
    │  │ Web Services│    │ Docker Swarm│    │ Monitoring  │              │
    │  └─────────────┘    └─────────────┘    └─────────────┘              │
    │         │                   │                   │                   │
    │    ┌─────────────────────────────────────────────────────────┐      │
    │    │          Firewall Rules & Access Control              │      │
    │    └─────────────────────────────────────────────────────────┘      │
    └─────────────────────────────────────────────────────────────────────┘
```

### **Port Management Strategy:**
- **Management Ports**: 3000-3099 (Web UIs, dashboards)
- **GPU Services**: 4000-4099 (ML/AI workloads)
- **Docker Services**: 5000-5099 (Container applications)
- **Monitoring**: 6000-6099 (Metrics, logging)
- **Custom Apps**: 7000-7099 (User applications)

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔧 **Prerequisites**

### **Required Infrastructure:**
- ✅ Section 5A completed (Tailscale mesh network operational)
- ✅ Section 5B completed (SSH hardening and port configuration)
- ✅ UFW firewall installed and configured
- ✅ Docker Swarm cluster operational
- ✅ Administrative access to all towers

### **Network Requirements:**
- ✅ Tailscale connectivity between all towers
- ✅ SSH access on custom ports (2122/2222/2322)
- ✅ Docker Swarm ports accessible
- ✅ Local network connectivity (192.168.1.0/24)

### **Verification Commands:**
```bash
# Verify previous sections
tailscale status
sudo systemctl status ssh
sudo ufw status
docker node ls
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🛡️ **Advanced UFW Firewall Configuration**

### **Step 1: Create Advanced UFW Management System**

```bash
cat > ~/advanced_ufw_manager.sh << 'EOF'
#!/bin/bash

# TwinTower Advanced UFW Management System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-status}"
TOWER_NAME="${2:-$(hostname)}"
TOWER_NUM=$(echo "$TOWER_NAME" | grep -o '[0-9]' | head -1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
UFW_CONFIG_DIR="/etc/ufw"
BACKUP_DIR="/home/$(whoami)/firewall_backups"
LOG_FILE="/var/log/ufw-manager.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to determine tower-specific ports
get_tower_ports() {
    local tower_num="$1"
    
    case "$tower_num" in
        "1")
            echo "SSH_PORT=2122 WEB_PORT=3001 GPU_PORT=4001 DOCKER_PORT=5001 MONITOR_PORT=6001"
            ;;
        "2")
            echo "SSH_PORT=2222 WEB_PORT=3002 GPU_PORT=4002 DOCKER_PORT=5002 MONITOR_PORT=6002"
            ;;
        "3")
            echo "SSH_PORT=2322 WEB_PORT=3003 GPU_PORT=4003 DOCKER_PORT=5003 MONITOR_PORT=6003"
            ;;
        *)
            echo "SSH_PORT=22 WEB_PORT=3000 GPU_PORT=4000 DOCKER_PORT=5000 MONITOR_PORT=6000"
            ;;
    esac
}

# Function to setup advanced UFW configuration
setup_advanced_ufw() {
    log_message "🔧 Setting up advanced UFW configuration..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup current UFW configuration
    if [ -d "$UFW_CONFIG_DIR" ]; then
        sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Reset UFW to clean state
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw default deny forward
    
    log_message "✅ UFW default policies configured"
}

# Function to configure network zones
configure_network_zones() {
    log_message "🌐 Configuring network security zones..."
    
    # Define network zones
    local LOCAL_NET="192.168.1.0/24"
    local TAILSCALE_NET="100.64.0.0/10"
    local DOCKER_NET="172.17.0.0/16"
    local SWARM_NET="10.0.0.0/8"
    
    # Allow loopback
    sudo ufw allow in on lo
    sudo ufw allow out on lo
    
    # Configure Tailscale zone (trusted)
    sudo ufw allow from "$TAILSCALE_NET" comment "Tailscale Network"
    
    # Configure local network zone (semi-trusted)
    sudo ufw allow from "$LOCAL_NET" to any port 22 comment "Local SSH"
    sudo ufw allow from "$LOCAL_NET" to any port 80 comment "Local HTTP"
    sudo ufw allow from "$LOCAL_NET" to any port 443 comment "Local HTTPS"
    
    # Configure Docker networks
    sudo ufw allow from "$DOCKER_NET" comment "Docker Network"
    sudo ufw allow from "$SWARM_NET" comment "Docker Swarm Network"
    
    log_message "✅ Network zones configured"
}

# Function to configure service-specific rules
configure_service_rules() {
    log_message "⚙️ Configuring service-specific firewall rules..."
    
    # Get tower-specific ports
    eval $(get_tower_ports "$TOWER_NUM")
    
    # SSH Rules
    sudo ufw allow "$SSH_PORT/tcp" comment "SSH Custom Port Tower$TOWER_NUM"
    
    # Docker Swarm Rules
    sudo ufw allow 2377/tcp comment "Docker Swarm Management"
    sudo ufw allow 7946/tcp comment "Docker Swarm Communication TCP"
    sudo ufw allow 7946/udp comment "Docker Swarm Communication UDP"
    sudo ufw allow 4789/udp comment "Docker Swarm Overlay Network"
    
    # Tailscale Rules
    sudo ufw allow 41641/udp comment "Tailscale"
    
    # GPU and ML Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$GPU_PORT" comment "GPU Services Tower$TOWER_NUM"
    sudo ufw allow from "192.168.1.0/24" to any port "$GPU_PORT" comment "GPU Services Local"
    
    # Web Management Interface
    sudo ufw allow from "$TAILSCALE_NET" to any port "$WEB_PORT" comment "Web Management Tower$TOWER_NUM"
    
    # Docker Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$DOCKER_PORT" comment "Docker Services Tower$TOWER_NUM"
    
    # Monitoring Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$MONITOR_PORT" comment "Monitoring Tower$TOWER_NUM"
    
    log_message "✅ Service-specific rules configured"
}

# Function to configure advanced security rules
configure_advanced_security() {
    log_message "🔒 Configuring advanced security rules..."
    
    # Rate limiting for SSH
    sudo ufw limit ssh comment "SSH Rate Limiting"
    
    # Block common attack patterns
    sudo ufw deny from 10.0.0.0/8 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 172.16.0.0/12 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 192.168.0.0/16 to any port 22 comment "Block RFC1918 SSH (except local)"
    sudo ufw allow from 192.168.1.0/24 to any port 22 comment "Allow local SSH"
    
    # Block suspicious ports
    sudo ufw deny 135/tcp comment "Block MS RPC"
    sudo ufw deny 139/tcp comment "Block NetBIOS"
    sudo ufw deny 445/tcp comment "Block SMB"
    sudo ufw deny 1433/tcp comment "Block MS SQL"
    sudo ufw deny 3389/tcp comment "Block RDP"
    
    # Allow ping but limit it
    sudo ufw allow from "$TAILSCALE_NET" proto icmp comment "Tailscale Ping"
    sudo ufw allow from "192.168.1.0/24" proto icmp comment "Local Ping"
    
    log_message "✅ Advanced security rules configured"
}

# Function to configure logging and monitoring
configure_logging() {
    log_message "📊 Configuring UFW logging and monitoring..."
    
    # Enable UFW logging
    sudo ufw logging on
    
    # Create custom logging configuration
    cat << LOG_CONFIG_EOF | sudo tee /etc/rsyslog.d/20-ufw.conf
# UFW logging configuration
:msg,contains,"[UFW " /var/log/ufw.log
& stop
LOG_CONFIG_EOF

    # Create log rotation
    cat << LOGROTATE_EOF | sudo tee /etc/logrotate.d/ufw-custom
/var/log/ufw.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 syslog adm
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
LOGROTATE_EOF

    # Restart rsyslog
    sudo systemctl restart rsyslog
    
    log_message "✅ UFW logging configured"
}

# Function to create UFW monitoring script
create_ufw_monitor() {
    log_message "📈 Creating UFW monitoring script..."
    
    cat << MONITOR_EOF > ~/ufw_monitor.sh
#!/bin/bash

# TwinTower UFW Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-60}"
LOG_FILE="/var/log/ufw-monitor.log"
ALERT_THRESHOLD=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor UFW status
monitor_ufw_status() {
    if sudo ufw status | grep -q "Status: active"; then
        log_message "✅ UFW is active"
        return 0
    else
        log_message "❌ UFW is inactive"
        return 1
    fi
}

# Function to analyze UFW logs
analyze_ufw_logs() {
    local blocked_count=\$(sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    local allowed_count=\$(sudo grep "\[UFW ALLOW\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    
    log_message "📊 Today's UFW activity - Blocked: \$blocked_count, Allowed: \$allowed_count"
    
    if [ "\$blocked_count" -gt "\$ALERT_THRESHOLD" ]; then
        log_message "🚨 HIGH ALERT: \$blocked_count blocked connections today"
        
        # Show top blocked IPs
        echo "Top blocked IPs today:" | tee -a "\$LOG_FILE"
        sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
        awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
        while read count ip; do
            echo "  \$ip: \$count attempts" | tee -a "\$LOG_FILE"
        done
    fi
}

# Function to check rule efficiency
check_rule_efficiency() {
    local total_rules=\$(sudo ufw status numbered | grep -c "^\[")
    log_message "📋 Total UFW rules: \$total_rules"
    
    if [ "\$total_rules" -gt 50 ]; then
        log_message "⚠️  Warning: High number of UFW rules may impact performance"
    fi
}

# Function to generate UFW report
generate_ufw_report() {
    local report_file="/tmp/ufw_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower UFW Monitoring Report
==============================
Generated: \$(date)
Tower: \$(hostname)

UFW Status:
----------
\$(sudo ufw status verbose)

Recent Activity (Last 24 hours):
-------------------------------
Blocked connections: \$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
Allowed connections: \$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)

Top Blocked IPs:
---------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Top Blocked Ports:
-----------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$14}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Recent Blocked Connections:
--------------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | tail -10)

REPORT_EOF

    echo "📋 UFW report generated: \$report_file"
    log_message "UFW report generated: \$report_file"
}

# Function to start monitoring daemon
start_monitoring() {
    log_message "🚀 Starting UFW monitoring daemon..."
    
    while true; do
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 60)) -eq 0 ]; then
            generate_ufw_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_monitoring
        ;;
    "status")
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        ;;
    "report")
        generate_ufw_report
        ;;
    *)
        echo "Usage: \$0 <monitor|status|report>"
        exit 1
        ;;
esac
MONITOR_EOF

    chmod +x ~/ufw_monitor.sh
    
    log_message "✅ UFW monitoring script created"
}

# Function to optimize UFW performance
optimize_ufw_performance() {
    log_message "⚡ Optimizing UFW performance..."
    
    # Create custom UFW configuration for performance
    cat << PERF_CONFIG_EOF | sudo tee /etc/ufw/sysctl.conf
# TwinTower UFW Performance Optimization

# Network performance
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.core.netdev_max_backlog = 5000

# Connection tracking
net.netfilter.nf_conntrack_max = 131072
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30

# Rate limiting
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048

# Security hardening
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
PERF_CONFIG_EOF

    # Apply sysctl settings
    sudo sysctl -p /etc/ufw/sysctl.conf
    
    log_message "✅ UFW performance optimized"
}

# Function to create UFW dashboard
create_ufw_dashboard() {
    log_message "📊 Creating UFW dashboard..."
    
    cat << DASHBOARD_EOF > ~/ufw_dashboard.sh
#!/bin/bash

# TwinTower UFW Dashboard
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔥 TwinTower UFW Firewall Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# UFW Status
echo -e "\${YELLOW}🛡️ UFW Status\${NC}"
echo "---------------"
if sudo ufw status | grep -q "Status: active"; then
    echo -e "Firewall Status: \${GREEN}✅ Active\${NC}"
else
    echo -e "Firewall Status: \${RED}❌ Inactive\${NC}"
fi

# Rule count
RULE_COUNT=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Active Rules: \${GREEN}\$RULE_COUNT\${NC}"

# Default policies
echo -e "Default Incoming: \${RED}DENY\${NC}"
echo -e "Default Outgoing: \${GREEN}ALLOW\${NC}"
echo

# Recent activity
echo -e "\${YELLOW}📈 Recent Activity (Last Hour)\${NC}"
echo "------------------------------"
HOUR_AGO=\$(date -d '1 hour ago' '+%b %d %H')
CURRENT_HOUR=\$(date '+%b %d %H')

BLOCKED_HOUR=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)
ALLOWED_HOUR=\$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)

echo -e "Blocked Connections: \${RED}\$BLOCKED_HOUR\${NC}"
echo -e "Allowed Connections: \${GREEN}\$ALLOWED_HOUR\${NC}"
echo

# Top blocked IPs
echo -e "\${YELLOW}🚫 Top Blocked IPs (Today)\${NC}"
echo "-------------------------"
sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
while read count ip; do
    echo -e "  \${RED}\$ip\${NC}: \$count attempts"
done
echo

# Service status
echo -e "\${YELLOW}⚙️ Service Status\${NC}"
echo "-----------------"
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
echo -e "SSH Port: \${GREEN}\$SSH_PORT\${NC}"

if sudo systemctl is-active --quiet docker; then
    echo -e "Docker: \${GREEN}✅ Running\${NC}"
else
    echo -e "Docker: \${RED}❌ Stopped\${NC}"
fi

if sudo systemctl is-active --quiet tailscaled; then
    echo -e "Tailscale: \${GREEN}✅ Running\${NC}"
else
    echo -e "Tailscale: \${RED}❌ Stopped\${NC}"
fi
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View detailed rules: sudo ufw status numbered"
echo "2. Monitor real-time: sudo tail -f /var/log/ufw.log"
echo "3. Generate report: ./ufw_monitor.sh report"
echo "4. Reload firewall: sudo ufw reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/ufw_dashboard.sh
    
    log_message "✅ UFW dashboard created"
}

# Main execution
main() {
    echo -e "${BLUE}🔥 TwinTower Advanced UFW Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME (Tower$TOWER_NUM)${NC}"
    echo -e "${BLUE}===================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_advanced_ufw
            configure_network_zones
            configure_service_rules
            configure_advanced_security
            configure_logging
            create_ufw_monitor
            optimize_ufw_performance
            create_ufw_dashboard
            
            # Enable UFW
            sudo ufw --force enable
            
            echo -e "${GREEN}✅ Advanced UFW configuration completed!${NC}"
            ;;
        "status")
            sudo ufw status verbose
            ;;
        "dashboard")
            ./ufw_dashboard.sh
            ;;
        "monitor")
            ./ufw_monitor.sh
            ;;
        "optimize")
            optimize_ufw_performance
            ;;
        "backup")
            sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
            echo -e "${GREEN}✅ UFW configuration backed up${NC}"
            ;;
        "reload")
            sudo ufw reload
            echo -e "${GREEN}✅ UFW reloaded${NC}"
            ;;
        *)
            echo "Usage: $0 <setup|status|dashboard|monitor|optimize|backup|reload> [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/advanced_ufw_manager.sh
```

### **Step 2: Execute Advanced UFW Setup**

```bash
# Setup advanced UFW configuration on each tower
./advanced_ufw_manager.sh setup $(hostname)

# Verify UFW status
./advanced_ufw_manager.sh status

# Launch UFW dashboard
./advanced_ufw_manager.sh dashboard
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🌐 **Network Segmentation & Zone Management**

### **Step 1: Create Network Segmentation System**

```bash
cat > ~/network_segmentation.sh << 'EOF'
#!/bin/bash

# TwinTower Network Segmentation & Zone Management
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
ZONE_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Network zones configuration
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/network-zones.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to define network zones
define_network_zones() {
    log_message "🌐 Defining network security zones..."
    
    sudo mkdir -p "$ZONES_CONFIG_DIR"
    
    # DMZ Zone - Public-facing services
    cat << DMZ_EOF | sudo tee "$ZONES_CONFIG_DIR/dmz.conf"
# DMZ Zone Configuration
ZONE_NAME="DMZ"
ZONE_DESCRIPTION="Public-facing services and APIs"
ZONE_NETWORKS="0.0.0.0/0"
ZONE_TRUST_LEVEL="LOW"
ZONE_PORTS="80,443,8080,8443"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="STRICT"
ZONE_INTRUSION_DETECTION="ENABLED"
DMZ_EOF

    # Internal Zone - Private infrastructure
    cat << INTERNAL_EOF | sudo tee "$ZONES_CONFIG_DIR/internal.conf"
# Internal Zone Configuration
ZONE_NAME="INTERNAL"
ZONE_DESCRIPTION="Private infrastructure and services"
ZONE_NETWORKS="192.168.1.0/24,172.16.0.0/12,10.0.0.0/8"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="22,80,443,2377,4789,7946"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
INTERNAL_EOF

    # Trusted Zone - Tailscale and management
    cat << TRUSTED_EOF | sudo tee "$ZONES_CONFIG_DIR/trusted.conf"
# Trusted Zone Configuration
ZONE_NAME="TRUSTED"
ZONE_DESCRIPTION="Tailscale mesh and management interfaces"
ZONE_NETWORKS="100.64.0.0/10"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="ALL"
ZONE_PROTOCOLS="tcp,udp,icmp"
ZONE_LOGGING="LOW"
ZONE_RATE_LIMIT="RELAXED"
ZONE_INTRUSION_DETECTION="MONITORING"
TRUSTED_EOF

    # Management Zone - Administrative access
    cat << MGMT_EOF | sudo tee "$ZONES_CONFIG_DIR/management.conf"
# Management Zone Configuration
ZONE_NAME="MANAGEMENT"
ZONE_DESCRIPTION="Administrative and monitoring services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="2122,2222,2322,3000-3099,6000-6099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
MGMT_EOF

    # GPU Zone - GPU compute services
    cat << GPU_EOF | sudo tee "$ZONES_CONFIG_DIR/gpu.conf"
# GPU Zone Configuration
ZONE_NAME="GPU"
ZONE_DESCRIPTION="GPU compute and ML services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="4000-4099,8000-8099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
GPU_EOF

    log_message "✅ Network zones defined"
}

# Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone '\$rule_file' > /dev/null || [ \$(grep -c '^[^#]' '\$rule_file') -eq 0 ]"
    fi
done

# Test detection functionality
echo -e "\${YELLOW}🎯 Testing Detection Functionality\${NC}"
echo "----------------------------------"
run_test "SSH brute force detection" "echo 'authentication failure ssh' | ./ids_detection_engine.sh test"
run_test "Rule processing works" "grep -q 'SSH brute force' /var/log/twintower-ids/detection.log"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All IDS tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
IDS_TEST_EOF

    chmod +x ~/test_ids_system.sh
    
    log_message "✅ IDS testing script created"
}

# Main execution
main() {
    echo -e "${BLUE}🚨 TwinTower Intrusion Detection & Prevention${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=============================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_ids_infrastructure
            create_detection_rules
            create_detection_engine
            create_ids_dashboard
            create_ids_service
            test_ids_system
            
            echo -e "${GREEN}✅ Intrusion Detection System configured!${NC}"
            ;;
        "start")
            sudo systemctl start twintower-ids.service
            echo -e "${GREEN}✅ IDS service started${NC}"
            ;;
        "stop")
            sudo systemctl stop twintower-ids.service
            echo -e "${GREEN}✅ IDS service stopped${NC}"
            ;;
        "status")
            ~/ids_dashboard.sh
            ;;
        "test")
            ~/test_ids_system.sh
            ;;
        "monitor")
            ~/ids_detection_engine.sh daemon
            ;;
        "report")
            ~/ids_detection_engine.sh report
            ;;
        "alerts")
            if [ -f "$IDS_ALERT_LOG" ]; then
                tail -f "$IDS_ALERT_LOG"
            else
                echo -e "${RED}❌ Alert log not found${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|start|stop|status|test|monitor|report|alerts>"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/intrusion_detection.sh
```

### **Step 2: Execute IDS Setup**

```bash
# Setup intrusion detection system
./intrusion_detection.sh setup

# Start IDS service
./intrusion_detection.sh start

# View IDS status
./intrusion_detection.sh status

# Test IDS functionality
./intrusion_detection.sh test
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📊 **Network Traffic Monitoring**

### **Step 1: Create Network Traffic Monitoring System**

```bash
cat > ~/network_traffic_monitor.sh << 'EOF'
#!/bin/bash

# TwinTower Network Traffic Monitoring System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
MONITOR_TYPE="${2:-realtime}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Traffic monitoring configuration
TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$TRAFFIC_LOG_DIR/monitor.log"
}

# Function to setup traffic monitoring infrastructure
setup_traffic_monitoring() {
    log_message "📊 Setting up traffic monitoring infrastructure..."
    
    # Create directories
    sudo mkdir -p "$TRAFFIC_CONFIG_DIR" "$TRAFFIC_LOG_DIR" "$TRAFFIC_DATA_DIR"
    
    # Install required packages
    sudo apt update
    sudo apt install -y iftop nethogs nload vnstat tcpdump wireshark-common
    
    # Create traffic monitoring configuration
    cat << TRAFFIC_CONFIG_EOF | sudo tee "$TRAFFIC_CONFIG_DIR/monitor.conf"
# TwinTower Traffic Monitoring Configuration
TRAFFIC_ENABLED=true
TRAFFIC_INTERFACE="auto"
TRAFFIC_SAMPLE_INTERVAL=60
TRAFFIC_RETENTION_DAYS=30
TRAFFIC_ALERT_THRESHOLD_MBPS=100
TRAFFIC_BANDWIDTH_LIMIT_MBPS=1000
TRAFFIC_PACKET_CAPTURE=false
TRAFFIC_DEEP_INSPECTION=false
TRAFFIC_GEOLOCATION=false
TRAFFIC_THREAT_DETECTION=true
TRAFFIC_ANOMALY_DETECTION=true
TRAFFIC_BASELINE_PERIOD=7
TRAFFIC_CONFIG_EOF

    # Create network interface detection script
    cat << INTERFACE_EOF > ~/detect_interfaces.sh
#!/bin/bash

# Detect primary network interface
PRIMARY_INTERFACE=\$(ip route | grep default | awk '{print \$5}' | head -1)
TAILSCALE_INTERFACE=\$(ip link show | grep tailscale | cut -d: -f2 | tr -d ' ')
DOCKER_INTERFACE=\$(ip link show | grep docker | cut -d: -f2 | tr -d ' ')

echo "Primary Interface: \$PRIMARY_INTERFACE"
echo "Tailscale Interface: \$TAILSCALE_INTERFACE"
echo "Docker Interface: \$DOCKER_INTERFACE"

# Create interface configuration
cat > "$TRAFFIC_CONFIG_DIR/interfaces.conf" << IFACE_EOF
PRIMARY_INTERFACE=\$PRIMARY_INTERFACE
TAILSCALE_INTERFACE=\$TAILSCALE_INTERFACE
DOCKER_INTERFACE=\$DOCKER_INTERFACE
IFACE_EOF
INTERFACE_EOF

    chmod +x ~/detect_interfaces.sh
    ~/detect_interfaces.sh
    
    log_message "✅ Traffic monitoring infrastructure created"
}

# Function to create traffic analysis engine
create_traffic_analyzer() {
    log_message "🔍 Creating traffic analysis engine..."
    
    cat << ANALYZER_EOF > ~/traffic_analyzer.sh
#!/bin/bash

# TwinTower Traffic Analysis Engine
set -e

TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
source "\$TRAFFIC_CONFIG_DIR/monitor.conf"
source "\$TRAFFIC_CONFIG_DIR/interfaces.conf"

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$TRAFFIC_LOG_DIR/analyzer.log"
}

# Function to collect interface statistics
collect_interface_stats() {
    local interface="\$1"
    local timestamp=\$(date +%s)
    
    # Get interface statistics
    local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
    
    if [ -n "\$stats" ]; then
        local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
        local rx_packets=\$(echo "\$stats" | cut -d' ' -f3)
        local rx_errors=\$(echo "\$stats" | cut -d' ' -f4)
        local rx_dropped=\$(echo "\$stats" | cut -d' ' -f5)
        local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
        local tx_packets=\$(echo "\$stats" | cut -d' ' -f11)
        local tx_errors=\$(echo "\$stats" | cut -d' ' -f12)
        local tx_dropped=\$(echo "\$stats" | cut -d' ' -f13)
        
        # Store statistics
        echo "\$timestamp,\$interface,\$rx_bytes,\$rx_packets,\$rx_errors,\$rx_dropped,\$tx_bytes,\$tx_packets,\$tx_errors,\$tx_dropped" >> "\$TRAFFIC_DATA_DIR/interface_stats.csv"
    fi
}

# Function to analyze bandwidth usage
analyze_bandwidth() {
    local interface="\$1"
    
    log_message "📊 Analyzing bandwidth usage for \$interface"
    
    # Get current bandwidth usage
    local current_rx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$2}')
    local current_tx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$10}')
    
    # Compare with previous measurement
    local prev_file="\$TRAFFIC_DATA_DIR/\$interface.prev"
    if [ -f "\$prev_file" ]; then
        local prev_data=\$(cat "\$prev_file")
        local prev_time=\$(echo "\$prev_data" | cut -d',' -f1)
        local prev_rx=\$(echo "\$prev_data" | cut -d',' -f2)
        local prev_tx=\$(echo "\$prev_data" | cut -d',' -f3)
        
        local current_time=\$(date +%s)
        local time_diff=\$((current_time - prev_time))
        
        if [ \$time_diff -gt 0 ]; then
            local rx_rate=\$(echo "scale=2; (\$current_rx - \$prev_rx) / \$time_diff / 1024 / 1024" | bc -l)
            local tx_rate=\$(echo "scale=2; (\$current_tx - \$prev_tx) / \$time_diff / 1024 / 1024" | bc -l)
            
            log_message "Interface \$interface: RX: \$rx_rate MB/s, TX: \$tx_rate MB/s"
            
            # Check for bandwidth alerts
            local total_rate=\$(echo "\$rx_rate + \$tx_rate" | bc -l)
            local alert_threshold=\$(echo "scale=2; \$TRAFFIC_ALERT_THRESHOLD_MBPS / 8" | bc -l)
            
            if [ \$(echo "\$total_rate > \$alert_threshold" | bc -l) -eq 1 ]; then
                log_message "🚨 HIGH BANDWIDTH ALERT: \$interface using \$total_rate MB/s"
                echo "\$(date '+%Y-%m-%d %H:%M:%S') - HIGH BANDWIDTH: \$interface \$total_rate MB/s" >> "\$TRAFFIC_LOG_DIR/alerts.log"
            fi
        fi
    fi
    
    # Store current data
    echo "\$(date +%s),\$current_rx,\$current_tx" > "\$prev_file"
}

# Function to detect traffic anomalies
detect_anomalies() {
    local interface="\$1"
    
    log_message "🔍 Detecting traffic anomalies for \$interface"
    
    # Get recent traffic data
    local recent_data=\$(tail -n 100 "\$TRAFFIC_DATA_DIR/interface_stats.csv" | grep "\$interface")
    
    if [ -n "\$recent_data" ]; then
        # Calculate average traffic
        local avg_rx=\$(echo "\$recent_data" | awk -F',' '{sum+=\$3} END {print sum/NR}')
        local avg_tx=\$(echo "\$recent_data" | awk -F',' '{sum+=\$7} END {print sum/NR}')
        
        # Get current traffic
        local current_rx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$3}')
        local current_tx=\$(cat /proc/net/dev | grep "\$interface:" | awk '{print \$11}')
        
        # Check for anomalies (traffic 3x higher than average)
        if [ \$(echo "\$current_rx > \$avg_rx * 3" | bc -l) -eq 1 ]; then
            log_message "🚨 ANOMALY DETECTED: High RX packet rate on \$interface"
            echo "\$(date '+%Y-%m-%d %H:%M:%S') - ANOMALY: High RX packets \$interface" >> "\$TRAFFIC_LOG_DIR/alerts.log"
        fi
        
        if [ \$(echo "\$current_tx > \$avg_tx * 3" | bc -l) -eq 1 ]; then
            log_message "🚨 ANOMALY DETECTED: High TX packet rate on \$interface"
            echo "\$(date '+%Y-%m-%d %H:%M:%S') - ANOMALY: High TX packets \$interface" >> "\$TRAFFIC_LOG_DIR/alerts.log"
        fi
    fi
}

# Function to analyze connection patterns
analyze_connections() {
    log_message "🔗 Analyzing connection patterns"
    
    # Get active connections
    local connections=\$(netstat -tn | grep ESTABLISHED | wc -l)
    local listening_ports=\$(netstat -tln | grep LISTEN | wc -l)
    
    log_message "Active connections: \$connections"
    log_message "Listening ports: \$listening_ports"
    
    # Store connection data
    echo "\$(date +%s),\$connections,\$listening_ports" >> "\$TRAFFIC_DATA_DIR/connections.csv"
    
    # Check for connection flooding
    if [ \$connections -gt 1000 ]; then
        log_message "🚨 CONNECTION FLOOD ALERT: \$connections active connections"
        echo "\$(date '+%Y-%m-%d %H:%M:%S') - CONNECTION FLOOD: \$connections connections" >> "\$TRAFFIC_LOG_DIR/alerts.log"
    fi
}

# Function to monitor specific protocols
monitor_protocols() {
    log_message "📡 Monitoring protocol usage"
    
    # Monitor SSH connections
    local ssh_connections=\$(netstat -tn | grep ':22 ' | grep ESTABLISHED | wc -l)
    local custom_ssh=\$(netstat -tn | grep -E ':(2122|2222|2322) ' | grep ESTABLISHED | wc -l)
    
    # Monitor HTTP/HTTPS
    local http_connections=\$(netstat -tn | grep ':80 ' | grep ESTABLISHED | wc -l)
    local https_connections=\$(netstat -tn | grep ':443 ' | grep ESTABLISHED | wc -l)
    
    # Monitor Docker ports
    local docker_connections=\$(netstat -tn | grep -E ':(2377|4789|7946) ' | grep ESTABLISHED | wc -l)
    
    log_message "SSH: \$ssh_connections, Custom SSH: \$custom_ssh, HTTP: \$http_connections, HTTPS: \$https_connections, Docker: \$docker_connections"
    
    # Store protocol data
    echo "\$(date +%s),\$ssh_connections,\$custom_ssh,\$http_connections,\$https_connections,\$docker_connections" >> "\$TRAFFIC_DATA_DIR/protocols.csv"
}

# Function to generate traffic report
generate_traffic_report() {
    local report_file="/tmp/traffic_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Network Traffic Report
===============================
Generated: \$(date)
Tower: \$(hostname)

Interface Information:
---------------------
Primary Interface: \$PRIMARY_INTERFACE
Tailscale Interface: \$TAILSCALE_INTERFACE
Docker Interface: \$DOCKER_INTERFACE

Current Traffic Statistics:
--------------------------
REPORT_EOF

    # Add interface statistics
    for interface in \$PRIMARY_INTERFACE \$TAILSCALE_INTERFACE \$DOCKER_INTERFACE; do
        if [ -n "\$interface" ] && [ "\$interface" != "auto" ]; then
            echo "Interface: \$interface" >> "\$report_file"
            if [ -f "/proc/net/dev" ]; then
                local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
                if [ -n "\$stats" ]; then
                    local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
                    local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
                    local rx_mb=\$(echo "scale=2; \$rx_bytes / 1024 / 1024" | bc -l)
                    local tx_mb=\$(echo "scale=2; \$tx_bytes / 1024 / 1024" | bc -l)
                    echo "  RX: \$rx_mb MB" >> "\$report_file"
                    echo "  TX: \$tx_mb MB" >> "\$report_file"
                fi
            fi
            echo "" >> "\$report_file"
        fi
    done
    
    cat >> "\$report_file" << REPORT_EOF

Connection Summary:
------------------
Active Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)
Listening Ports: \$(netstat -tln | grep LISTEN | wc -l)

Top Connections by IP:
---------------------
\$(netstat -tn | grep ESTABLISHED | awk '{print \$5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head -10)

Recent Traffic Alerts:
---------------------
\$(tail -n 20 "\$TRAFFIC_LOG_DIR/alerts.log" 2>/dev/null || echo "No recent alerts")

Bandwidth Usage Trends:
----------------------
\$(tail -n 10 "\$TRAFFIC_DATA_DIR/interface_stats.csv" 2>/dev/null || echo "No trend data available")

Protocol Distribution:
---------------------
\$(tail -n 1 "\$TRAFFIC_DATA_DIR/protocols.csv" 2>/dev/null || echo "No protocol data available")

REPORT_EOF

    log_message "📋 Traffic report generated: \$report_file"
    echo "\$report_file"
}

# Function to start traffic monitoring daemon
start_traffic_monitor() {
    log_message "🚀 Starting traffic monitoring daemon..."
    
    while true; do
        # Monitor each interface
        for interface in \$PRIMARY_INTERFACE \$TAILSCALE_INTERFACE \$DOCKER_INTERFACE; do
            if [ -n "\$interface" ] && [ "\$interface" != "auto" ]; then
                collect_interface_stats "\$interface"
                analyze_bandwidth "\$interface"
                detect_anomalies "\$interface"
            fi
        done
        
        # Monitor connections and protocols
        analyze_connections
        monitor_protocols
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$TRAFFIC_SAMPLE_INTERVAL) % 60)) -eq 0 ]; then
            generate_traffic_report
        fi
        
        sleep "\$TRAFFIC_SAMPLE_INTERVAL"
    done
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_traffic_monitor
        ;;
    "report")
        generate_traffic_report
        ;;
    "status")
        echo "Traffic Monitor Status:"
        echo "======================"
        echo "Primary Interface: \$PRIMARY_INTERFACE"
        echo "Tailscale Interface: \$TAILSCALE_INTERFACE"
        echo "Docker Interface: \$DOCKER_INTERFACE"
        echo "Active Connections: \$(netstat -tn | grep ESTABLISHED | wc -l)"
        echo "Recent Alerts: \$(tail -n 5 "\$TRAFFIC_LOG_DIR/alerts.log" 2>/dev/null | wc -l)"
        ;;
    "interfaces")
        echo "Network Interfaces:"
        echo "=================="
        ip addr show | grep -E '^[0-9]+:' | cut -d: -f2 | tr -d ' '
        ;;
    "connections")
        echo "Active Connections:"
        echo "=================="
        netstat -tn | grep ESTABLISHED | head -20
        ;;
    *)
        echo "Usage: \$0 <daemon|report|status|interfaces|connections>"
        exit 1
        ;;
esac
ANALYZER_EOF

    chmod +x ~/traffic_analyzer.sh
    
    log_message "✅ Traffic analysis engine created"
}

# Function to create traffic monitoring dashboard
create_traffic_dashboard() {
    log_message "📊 Creating traffic monitoring dashboard..."
    
    cat << DASHBOARD_EOF > ~/traffic_dashboard.sh
#!/bin/bash

# TwinTower Traffic Monitoring Dashboard
set -e

TRAFFIC_CONFIG_DIR="/etc/twintower-traffic"
TRAFFIC_LOG_DIR="/var/log/twintower-traffic"
TRAFFIC_DATA_DIR="/var/lib/twintower-traffic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
if [ -f "\$TRAFFIC_CONFIG_DIR/monitor.conf" ]; then
    source "\$TRAFFIC_CONFIG_DIR/monitor.conf"
fi

if [ -f "\$TRAFFIC_CONFIG_DIR/interfaces.conf" ]; then
    source "\$TRAFFIC_CONFIG_DIR/interfaces.conf"
fi

clear
echo -e "\${BLUE}📊 TwinTower Traffic Monitoring Dashboard\${NC}"
echo -e "\${BLUE}=========================================\${NC}"
echo

# System Overview
echo -e "\${YELLOW}🌐 Network Overview\${NC}"
echo "-------------------"
echo -e "Primary Interface: \${GREEN}\$PRIMARY_INTERFACE\${NC}"
echo -e "Tailscale Interface: \${GREEN}\$TAILSCALE_INTERFACE\${NC}"
echo -e "Docker Interface: \${GREEN}\$DOCKER_INTERFACE\${NC}"
echo

# Current Traffic Statistics
echo -e "\${YELLOW}📈 Current Traffic Statistics\${NC}"
echo "-----------------------------"
for interface in \$PRIMARY_INTERFACE \$TAILSCALE_INTERFACE \$DOCKER_INTERFACE; do
    if [ -n "\$interface" ] && [ "\$interface" != "auto" ]; then
        echo -e "\${BLUE}Interface: \$interface\${NC}"
        
        if [ -f "/proc/net/dev" ]; then
            local stats=\$(cat /proc/net/dev | grep "\$interface:" | tr -s ' ')
            if [ -n "\$stats" ]; then
                local rx_bytes=\$(echo "\$stats" | cut -d' ' -f2)
                local tx_bytes=\$(echo "\$stats" | cut -d' ' -f10)
                local rx_packets=\$(echo "\$stats" | cut -d' ' -f3)
                local tx_packets=\$(echo "\$stats" | cut -d' ' -f11)
                
                local rx_mb=\$(echo "scale=2; \$rx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
                local tx_mb=\$(echo "scale=2; \$tx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
                
                echo -e "  RX: \${GREEN}\$rx_mb MB\${NC} (\$rx_packets packets)"
                echo -e "  TX: \${GREEN}\$tx_mb MB\${NC} (\$tx_packets packets)"
            fi
        fi
        echo
    fi
done

# Connection Statistics
echo -e "\${YELLOW}🔗 Connection Statistics\${NC}"
echo "------------------------"
ACTIVE_CONNECTIONS=\$(netstat -tn | grep ESTABLISHED | wc -l)
LISTENING_PORTS=\$(netstat -tln | grep LISTEN | wc -l)

echo -e "Active Connections: \${GREEN}\$ACTIVE_CONNECTIONS\${NC}"
echo -e "Listening Ports: \${GREEN}\$LISTENING_PORTS\${NC}"
echo

# Protocol Breakdown
echo -e "\${YELLOW}📡 Protocol Breakdown\${NC}"
echo "--------------------"
SSH_CONNECTIONS=\$(netstat -tn | grep ':22 ' | grep ESTABLISHED | wc -l)
CUSTOM_SSH=\$(netstat -tn | grep -E ':(2122|2222|2322) ' | grep ESTABLISHED | wc -l)
HTTP_CONNECTIONS=\$(netstat -tn | grep ':80 ' | grep ESTABLISHED | wc -l)
HTTPS_CONNECTIONS=\$(netstat -tn | grep ':443 ' | grep ESTABLISHED | wc -l)
DOCKER_CONNECTIONS=\$(netstat -tn | grep -E ':(2377|4789|7946) ' | grep ESTABLISHED | wc -l)

echo -e "SSH (standard): \${GREEN}\$SSH_CONNECTIONS\${NC}"
echo -e "SSH (custom): \${GREEN}\$CUSTOM_SSH\${NC}"
echo -e "HTTP: \${GREEN}\$HTTP_CONNECTIONS\${NC}"
echo -e "HTTPS: \${GREEN}\$HTTPS_CONNECTIONS\${NC}"
echo -e "Docker: \${GREEN}\$DOCKER_CONNECTIONS\${NC}"
echo

# Top Connections
echo -e "\${YELLOW}🏆 Top Connection Sources\${NC}"
echo "-------------------------"
echo "Top 5 IPs by connection count:"
netstat -tn | grep ESTABLISHED | awk '{print \$5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head -5 | while read count ip; do
    echo -e "  \${GREEN}\$ip\${NC}: \$count connections"
done
echo

# Recent Alerts
echo -e "\${YELLOW}🚨 Recent Traffic Alerts\${NC}"
echo "------------------------"
if [ -f "\$TRAFFIC_LOG_DIR/alerts.log" ]; then
    ALERT_COUNT=\$(tail -n 20 "\$TRAFFIC_LOG_DIR/alerts.log" | wc -l)
    if [ \$ALERT_COUNT -gt 0 ]; then
        echo -e "Recent Alerts: \${RED}\$ALERT_COUNT\${NC}"
        tail -n 5 "\$TRAFFIC_LOG_DIR/alerts.log" | while read line; do
            echo -e "  \${RED}⚠️\${NC} \$line"
        done
    else
        echo -e "Recent Alerts: \${GREEN}0\${NC}"
    fi
else
    echo -e "No alert data available"
fi
echo

# Bandwidth Usage
echo -e "\${YELLOW}📊 Bandwidth Usage\${NC}"
echo "------------------"
if [ -f "\$TRAFFIC_DATA_DIR/interface_stats.csv" ]; then
    echo "Recent bandwidth activity:"
    tail -n 3 "\$TRAFFIC_DATA_DIR/interface_stats.csv" | while IFS=',' read timestamp interface rx_bytes rx_packets rx_errors rx_dropped tx_bytes tx_packets tx_errors tx_dropped; do
        local time_str=\$(date -d "@\$timestamp" '+%H:%M:%S')
        local rx_mb=\$(echo "scale=2; \$rx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
        local tx_mb=\$(echo "scale=2; \$tx_bytes / 1024 / 1024" | bc -l 2>/dev/null || echo "0")
        echo -e "  \$time_str \${GREEN}\$interface\${NC}: RX \$rx_mb MB, TX \$tx_mb MB"
    done
else
    echo -e "No bandwidth data available"
fi
echo

# System Health
echo -e "\${YELLOW}💓 System Health\${NC}"
echo "----------------"
TRAFFIC_PROCESS=\$(pgrep -f "traffic_analyzer.sh" | wc -l)
if [ \$TRAFFIC_PROCESS -gt 0 ]; then
    echo -e "Traffic Monitor: \${GREEN}✅ Running\${NC}"
else
    echo -e "Traffic Monitor: \${RED}❌ Stopped\${NC}"
fi

LOG_SIZE=\$(du -h "\$TRAFFIC_LOG_DIR" 2>/dev/null | cut -f1 || echo "0")
echo -e "Log Directory Size: \${GREEN}\$LOG_SIZE\${NC}"

DATA_SIZE=\$(du -h "\$TRAFFIC_DATA_DIR" 2>/dev/null | cut -f1 || echo "0")
echo -e "Data Directory Size: \${GREEN}\$DATA_SIZE\${NC}"
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Start monitor: ./traffic_analyzer.sh daemon"
echo "2. View connections: ./traffic_analyzer.sh connections"
echo "3. Generate report: ./traffic_analyzer.sh report"
echo "4. View interfaces: ./traffic_analyzer.sh interfaces"
echo "5. Real-time monitor: watch## 🚨 **Intrusion Detection & Prevention**

### **Step 1: Create Advanced Intrusion Detection System**

```bash
cat > ~/intrusion_detection.sh << 'EOF'
#!/bin/bash

# TwinTower Intrusion Detection & Prevention System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
DETECTION_TYPE="${2:-realtime}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# IDS Configuration
IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="$IDS_LOG_DIR/detection.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$IDS_DETECTION_LOG"
}

# Function to setup IDS infrastructure
setup_ids_infrastructure() {
    log_message "🔧 Setting up IDS infrastructure..."
    
    # Create directories
    sudo mkdir -p "$IDS_CONFIG_DIR" "$IDS_RULES_DIR" "$IDS_LOG_DIR"
    sudo touch "$IDS_ALERT_LOG" "$IDS_DETECTION_LOG"
    
    # Create main IDS configuration
    cat << IDS_CONFIG_EOF | sudo tee "$IDS_CONFIG_DIR/ids.conf"
# TwinTower IDS Configuration
IDS_ENABLED=true
IDS_MODE="monitor"
IDS_SENSITIVITY="medium"
IDS_LOGGING_LEVEL="info"
IDS_ALERT_THRESHOLD=5
IDS_BLOCK_THRESHOLD=10
IDS_WHITELIST_ENABLED=true
IDS_LEARNING_MODE=false
IDS_REALTIME_ALERTS=true
IDS_EMAIL_ALERTS=false
IDS_WEBHOOK_ALERTS=false
IDS_AUTO_BLOCK=false
IDS_BLOCK_DURATION=3600
IDS_CLEANUP_INTERVAL=86400
IDS_CONFIG_EOF

    # Create whitelist configuration
    cat << WHITELIST_EOF | sudo tee "$IDS_CONFIG_DIR/whitelist.conf"
# TwinTower IDS Whitelist
# Trusted IP addresses and networks
100.64.0.0/10
192.168.1.0/24
127.0.0.0/8
::1/128

# Trusted processes
/usr/bin/ssh
/usr/bin/docker
/usr/bin/tailscale
/usr/sbin/sshd
WHITELIST_EOF

    log_message "✅ IDS infrastructure created"
}

# Function to create detection rules
create_detection_rules() {
    log_message "📋 Creating intrusion detection rules..."
    
    # SSH Attack Detection Rules
    cat << SSH_RULES_EOF | sudo tee "$IDS_RULES_DIR/ssh_attacks.rules"
# SSH Attack Detection Rules
# Rule format: PATTERN|SEVERITY|ACTION|DESCRIPTION

# Brute force attacks
authentication failure.*ssh|HIGH|ALERT|SSH brute force attempt
Failed password.*ssh|MEDIUM|COUNT|SSH failed password
Invalid user.*ssh|HIGH|ALERT|SSH invalid user attempt
ROOT LOGIN REFUSED.*ssh|HIGH|ALERT|SSH root login attempt

# SSH scanning
Connection closed.*ssh.*preauth|LOW|COUNT|SSH connection scanning
Connection reset.*ssh|LOW|COUNT|SSH connection reset
Received disconnect.*ssh|MEDIUM|COUNT|SSH premature disconnect

# Suspicious SSH activity
User.*not allowed.*ssh|HIGH|ALERT|SSH user not allowed
Maximum authentication attempts.*ssh|HIGH|ALERT|SSH max auth attempts
Timeout.*ssh|MEDIUM|COUNT|SSH timeout

# SSH protocol violations
Protocol.*ssh|HIGH|ALERT|SSH protocol violation
Bad protocol version.*ssh|HIGH|ALERT|SSH bad protocol version
SSH_RULES_EOF

    # Network Attack Detection Rules
    cat << NET_RULES_EOF | sudo tee "$IDS_RULES_DIR/network_attacks.rules"
# Network Attack Detection Rules

# Port scanning
nmap|HIGH|ALERT|Nmap scan detected
masscan|HIGH|ALERT|Masscan detected
SYN flood|HIGH|ALERT|SYN flood attack
Port.*scan|MEDIUM|ALERT|Port scan detected

# DDoS attacks
DDOS|HIGH|BLOCK|DDoS attack detected
flood|HIGH|ALERT|Flood attack detected
amplification|HIGH|ALERT|Amplification attack

# Network intrusion
backdoor|HIGH|BLOCK|Backdoor detected
trojan|HIGH|BLOCK|Trojan detected
botnet|HIGH|BLOCK|Botnet activity
malware|HIGH|BLOCK|Malware detected

# Protocol attacks
DNS.*poison|HIGH|ALERT|DNS poisoning attempt
ARP.*spoof|HIGH|ALERT|ARP spoofing detected
ICMP.*flood|MEDIUM|ALERT|ICMP flood detected
NET_RULES_EOF

    # Web Attack Detection Rules
    cat << WEB_RULES_EOF | sudo tee "$IDS_RULES_DIR/web_attacks.rules"
# Web Attack Detection Rules

# SQL Injection
union.*select|HIGH|ALERT|SQL injection attempt
drop.*table|HIGH|ALERT|SQL injection (DROP)
insert.*into|MEDIUM|COUNT|SQL injection (INSERT)
update.*set|MEDIUM|COUNT|SQL injection (UPDATE)

# XSS attacks
<script|HIGH|ALERT|XSS attack attempt
javascript:|HIGH|ALERT|XSS javascript injection
eval\(|HIGH|ALERT|XSS eval injection
alert\(|MEDIUM|COUNT|XSS alert injection

# Directory traversal
\.\./|HIGH|ALERT|Directory traversal attempt
etc/passwd|HIGH|ALERT|System file access attempt
etc/shadow|HIGH|ALERT|Shadow file access attempt

# Command injection
;.*rm|HIGH|ALERT|Command injection (rm)
;.*cat|MEDIUM|COUNT|Command injection (cat)
;.*wget|HIGH|ALERT|Command injection (wget)
;.*curl|HIGH|ALERT|Command injection (curl)
WEB_RULES_EOF

    # System Attack Detection Rules
    cat << SYS_RULES_EOF | sudo tee "$IDS_RULES_DIR/system_attacks.rules"
# System Attack Detection Rules

# Privilege escalation
sudo.*passwd|HIGH|ALERT|Sudo password change attempt
su.*root|HIGH|ALERT|Root escalation attempt
chmod.*777|MEDIUM|COUNT|Dangerous permissions change
chown.*root|HIGH|ALERT|Root ownership change

# File system attacks
rm.*rf|HIGH|ALERT|Dangerous file deletion
find.*exec|MEDIUM|COUNT|Find command execution
crontab.*e|MEDIUM|COUNT|Crontab modification

# Process injection
ptrace|HIGH|ALERT|Process injection attempt
gdb.*attach|HIGH|ALERT|Debugger attachment
strace.*p|MEDIUM|COUNT|Process tracing

# Resource exhaustion
fork.*bomb|HIGH|BLOCK|Fork bomb detected
memory.*exhaustion|HIGH|ALERT|Memory exhaustion
CPU.*100|MEDIUM|COUNT|High CPU usage
SYS_RULES_EOF

    log_message "✅ Detection rules created"
}

# Function to create real-time detection engine
create_detection_engine() {
    log_message "⚙️ Creating real-time detection engine..."
    
    cat << DETECTION_ENGINE_EOF > ~/ids_detection_engine.sh
#!/bin/bash

# TwinTower IDS Real-time Detection Engine
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"
IDS_LOG_DIR="/var/log/twintower-ids"
IDS_ALERT_LOG="\$IDS_LOG_DIR/alerts.log"
IDS_DETECTION_LOG="\$IDS_LOG_DIR/detection.log"
IDS_STATE_FILE="/var/lib/twintower-ids/state"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
source "\$IDS_CONFIG_DIR/ids.conf"

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$IDS_DETECTION_LOG"
}

alert_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - ALERT: \$1" | tee -a "\$IDS_ALERT_LOG"
}

# Function to check if IP is whitelisted
is_whitelisted() {
    local ip="\$1"
    local whitelist_file="\$IDS_CONFIG_DIR/whitelist.conf"
    
    if [ -f "\$whitelist_file" ]; then
        # Simple IP matching (in production use more sophisticated matching)
        if grep -q "\$ip" "\$whitelist_file"; then
            return 0
        fi
        
        # Check network ranges (simplified)
        if [[ "\$ip" =~ ^192\.168\.1\. ]] && grep -q "192.168.1.0/24" "\$whitelist_file"; then
            return 0
        fi
        
        if [[ "\$ip" =~ ^100\.64\. ]] && grep -q "100.64.0.0/10" "\$whitelist_file"; then
            return 0
        fi
    fi
    
    return 1
}

# Function to process detection rule
process_rule() {
    local rule="\$1"
    local log_line="\$2"
    local source_ip="\$3"
    
    # Parse rule: PATTERN|SEVERITY|ACTION|DESCRIPTION
    local pattern=\$(echo "\$rule" | cut -d'|' -f1)
    local severity=\$(echo "\$rule" | cut -d'|' -f2)
    local action=\$(echo "\$rule" | cut -d'|' -f3)
    local description=\$(echo "\$rule" | cut -d'|' -f4)
    
    # Check if log line matches pattern
    if echo "\$log_line" | grep -qi "\$pattern"; then
        # Skip if whitelisted
        if is_whitelisted "\$source_ip"; then
            return 0
        fi
        
        # Execute action based on severity and configuration
        case "\$action" in
            "ALERT")
                alert_message "[\$severity] \$description - IP: \$source_ip"
                if [ "\$IDS_REALTIME_ALERTS" = "true" ]; then
                    send_alert "\$severity" "\$description" "\$source_ip"
                fi
                ;;
            "BLOCK")
                alert_message "[\$severity] BLOCKING - \$description - IP: \$source_ip"
                if [ "\$IDS_AUTO_BLOCK" = "true" ]; then
                    block_ip "\$source_ip" "\$description"
                fi
                ;;
            "COUNT")
                increment_counter "\$source_ip" "\$description"
                ;;
        esac
    fi
}

# Function to extract source IP from log line
extract_source_ip() {
    local log_line="\$1"
    
    # Extract IP using various patterns
    local ip=\$(echo "\$log_line" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    
    if [ -z "\$ip" ]; then
        ip="unknown"
    fi
    
    echo "\$ip"
}

# Function to increment counter for repeated events
increment_counter() {
    local ip="\$1"
    local event="\$2"
    
    local counter_file="/var/lib/twintower-ids/counters/\$ip"
    sudo mkdir -p "/var/lib/twintower-ids/counters"
    
    local count=1
    if [ -f "\$counter_file" ]; then
        count=\$(cat "\$counter_file")
        count=\$((count + 1))
    fi
    
    echo "\$count" > "\$counter_file"
    
    # Check if threshold exceeded
    if [ "\$count" -ge "\$IDS_ALERT_THRESHOLD" ]; then
        alert_message "[THRESHOLD] IP \$ip exceeded threshold (\$count events) - \$event"
        
        if [ "\$count" -ge "\$IDS_BLOCK_THRESHOLD" ] && [ "\$IDS_AUTO_BLOCK" = "true" ]; then
            block_ip "\$ip" "Threshold exceeded: \$event"
        fi
    fi
}

# Function to block IP address
block_ip() {
    local ip="\$1"
    local reason="\$2"
    
    log_message "🚫 Blocking IP: \$ip - Reason: \$reason"
    
    # Block using UFW
    sudo ufw deny from "\$ip" comment "IDS Block: \$reason"
    
    # Schedule unblock
    if [ "\$IDS_BLOCK_DURATION" -gt 0 ]; then
        echo "sudo ufw delete deny from \$ip" | at now + "\$IDS_BLOCK_DURATION seconds" 2>/dev/null || true
    fi
}

# Function to send alert
send_alert() {
    local severity="\$1"
    local description="\$2"
    local source_ip="\$3"
    
    # Log alert
    log_message "🚨 ALERT [\$severity]: \$description from \$source_ip"
    
    # Send email alert if configured
    if [ "\$IDS_EMAIL_ALERTS" = "true" ] && [ -n "\$IDS_EMAIL_RECIPIENT" ]; then
        echo "IDS Alert: \$description from \$source_ip" | mail -s "TwinTower IDS Alert [\$severity]" "\$IDS_EMAIL_RECIPIENT"
    fi
    
    # Send webhook alert if configured
    if [ "\$IDS_WEBHOOK_ALERTS" = "true" ] && [ -n "\$IDS_WEBHOOK_URL" ]; then
        curl -X POST -H "Content-Type: application/json" \
            -d "{\"alert\":\"TwinTower IDS Alert\",\"severity\":\"\$severity\",\"description\":\"\$description\",\"source_ip\":\"\$source_ip\"}" \
            "\$IDS_WEBHOOK_URL" 2>/dev/null || true
    fi
}

# Function to monitor log files
monitor_logs() {
    log_message "🔍 Starting real-time log monitoring..."
    
    # Monitor multiple log files
    tail -f /var/log/auth.log /var/log/syslog /var/log/ufw.log /var/log/nginx/access.log 2>/dev/null | \
    while read log_line; do
        # Extract source IP
        source_ip=\$(extract_source_ip "\$log_line")
        
        # Process against all rule files
        for rule_file in "\$IDS_RULES_DIR"/*.rules; do
            if [ -f "\$rule_file" ]; then
                while IFS= read -r rule; do
                    # Skip comments and empty lines
                    if [[ "\$rule" =~ ^#.*\$ ]] || [[ -z "\$rule" ]]; then
                        continue
                    fi
                    
                    process_rule "\$rule" "\$log_line" "\$source_ip"
                done < "\$rule_file"
            fi
        done
    done
}

# Function to generate IDS report
generate_ids_report() {
    local report_file="/tmp/ids_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower IDS Report
==================
Generated: \$(date)
Tower: \$(hostname)

IDS Configuration:
-----------------
Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")
Mode: \$IDS_MODE
Sensitivity: \$IDS_SENSITIVITY
Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "ENABLED" || echo "DISABLED")

Detection Statistics (Last 24 hours):
------------------------------------
Total Alerts: \$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
High Severity: \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
Medium Severity: \$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
Low Severity: \$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")

Blocked IPs:
-----------
\$(sudo ufw status | grep "IDS Block" || echo "No IPs currently blocked")

Top Alert Sources:
-----------------
\$(grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -10)

Recent High-Priority Alerts:
----------------------------
\$(grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -10)

Rule Effectiveness:
------------------
SSH Attacks: \$(grep -c "SSH.*attempt" "\$IDS_ALERT_LOG" || echo "0")
Network Attacks: \$(grep -c "scan.*detected" "\$IDS_ALERT_LOG" || echo "0")
Web Attacks: \$(grep -c "injection.*attempt" "\$IDS_ALERT_LOG" || echo "0")
System Attacks: \$(grep -c "escalation.*attempt" "\$IDS_ALERT_LOG" || echo "0")

REPORT_EOF

    log_message "📋 IDS report generated: \$report_file"
    echo "\$report_file"
}

# Function to start IDS daemon
start_ids_daemon() {
    log_message "🚀 Starting IDS daemon..."
    
    # Create state directory
    sudo mkdir -p /var/lib/twintower-ids/counters
    
    # Start monitoring
    monitor_logs
}

# Main execution
case "\${1:-daemon}" in
    "daemon")
        start_ids_daemon
        ;;
    "test")
        # Test detection rules
        echo "Testing IDS rules..."
        echo "authentication failure ssh" | while read line; do
            source_ip=\$(extract_source_ip "\$line")
            process_rule "authentication failure.*ssh|HIGH|ALERT|SSH brute force test" "\$line" "\$source_ip"
        done
        ;;
    "report")
        generate_ids_report
        ;;
    "status")
        echo "IDS Status: \$([ "\$IDS_ENABLED" = "true" ] && echo "ENABLED" || echo "DISABLED")"
        echo "Active Rules: \$(find "\$IDS_RULES_DIR" -name "*.rules" | wc -l)"
        echo "Recent Alerts: \$(tail -n 5 "\$IDS_ALERT_LOG" | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <daemon|test|report|status>"
        exit 1
        ;;
esac
DETECTION_ENGINE_EOF

    chmod +x ~/ids_detection_engine.sh
    
    log_message "✅ Detection engine created"
}

# Function to create IDS management dashboard
create_ids_dashboard() {
    log_message "📊 Creating IDS management dashboard..."
    
    cat << IDS_DASHBOARD_EOF > ~/ids_dashboard.sh
#!/bin/bash

# TwinTower IDS Management Dashboard
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_ALERT_LOG="/var/log/twintower-ids/alerts.log"
IDS_DETECTION_LOG="/var/log/twintower-ids/detection.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load configuration
if [ -f "\$IDS_CONFIG_DIR/ids.conf" ]; then
    source "\$IDS_CONFIG_DIR/ids.conf"
fi

clear
echo -e "\${BLUE}🚨 TwinTower IDS Management Dashboard\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# IDS Status
echo -e "\${YELLOW}🛡️ IDS Status\${NC}"
echo "-------------"
if [ "\$IDS_ENABLED" = "true" ]; then
    echo -e "IDS Status: \${GREEN}✅ ENABLED\${NC}"
else
    echo -e "IDS Status: \${RED}❌ DISABLED\${NC}"
fi

echo -e "Mode: \${GREEN}\$IDS_MODE\${NC}"
echo -e "Sensitivity: \${GREEN}\$IDS_SENSITIVITY\${NC}"
echo -e "Auto-block: \$([ "\$IDS_AUTO_BLOCK" = "true" ] && echo "\${GREEN}✅ ENABLED\${NC}" || echo "\${RED}❌ DISABLED\${NC}")"
echo

# Detection Statistics
echo -e "\${YELLOW}📊 Detection Statistics (Last 24 hours)\${NC}"
echo "--------------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    TOTAL_ALERTS=\$(grep -c "ALERT:" "\$IDS_ALERT_LOG" || echo "0")
    HIGH_ALERTS=\$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG" || echo "0")
    MEDIUM_ALERTS=\$(grep -c "\[MEDIUM\]" "\$IDS_ALERT_LOG" || echo "0")
    LOW_ALERTS=\$(grep -c "\[LOW\]" "\$IDS_ALERT_LOG" || echo "0")
    
    echo -e "Total Alerts: \${BLUE}\$TOTAL_ALERTS\${NC}"
    echo -e "High Severity: \${RED}\$HIGH_ALERTS\${NC}"
    echo -e "Medium Severity: \${YELLOW}\$MEDIUM_ALERTS\${NC}"
    echo -e "Low Severity: \${GREEN}\$LOW_ALERTS\${NC}"
else
    echo -e "No alert data available"
fi
echo

# Active Rules
echo -e "\${YELLOW}📋 Active Rules\${NC}"
echo "---------------"
if [ -d "\$IDS_CONFIG_DIR/rules" ]; then
    RULE_COUNT=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" -exec wc -l {} + | tail -1 | awk '{print \$1}' || echo "0")
    RULE_FILES=\$(find "\$IDS_CONFIG_DIR/rules" -name "*.rules" | wc -l)
    echo -e "Rule Files: \${GREEN}\$RULE_FILES\${NC}"
    echo -e "Total Rules: \${GREEN}\$RULE_COUNT\${NC}"
    
    for rule_file in "\$IDS_CONFIG_DIR/rules"/*.rules; do
        if [ -f "\$rule_file" ]; then
            rule_name=\$(basename "\$rule_file" .rules)
            rule_count=\$(grep -c "^[^#]" "\$rule_file" || echo "0")
            echo -e "  \${GREEN}•\${NC} \$rule_name: \$rule_count rules"
        fi
    done
else
    echo -e "No rules configured"
fi
echo

# Recent Alerts
echo -e "\${YELLOW}🚨 Recent High-Priority Alerts\${NC}"
echo "------------------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    grep "\[HIGH\]" "\$IDS_ALERT_LOG" | tail -5 | while read line; do
        timestamp=\$(echo "\$line" | awk '{print \$1, \$2, \$3}')
        alert_msg=\$(echo "\$line" | cut -d'-' -f3-)
        echo -e "  \${RED}⚠️\${NC} \$timestamp:\$alert_msg"
    done
    
    if [ \$(grep -c "\[HIGH\]" "\$IDS_ALERT_LOG") -eq 0 ]; then
        echo -e "  \${GREEN}✅ No high-priority alerts\${NC}"
    fi
else
    echo -e "No alert data available"
fi
echo

# Blocked IPs
echo -e "\${YELLOW}🚫 Blocked IPs\${NC}"
echo "-------------"
BLOCKED_IPS=\$(sudo ufw status | grep "IDS Block" | wc -l)
if [ \$BLOCKED_IPS -gt 0 ]; then
    echo -e "Currently Blocked: \${RED}\$BLOCKED_IPS\${NC}"
    sudo ufw status | grep "IDS Block" | head -5 | while read line; do
        echo -e "  \${RED}🔒\${NC} \$line"
    done
else
    echo -e "Currently Blocked: \${GREEN}0\${NC}"
fi
echo

# Top Alert Sources
echo -e "\${YELLOW}📈 Top Alert Sources\${NC}"
echo "--------------------"
if [ -f "\$IDS_ALERT_LOG" ]; then
    echo "Top 5 IPs by alert count:"
    grep "ALERT:" "\$IDS_ALERT_LOG" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort | uniq -c | sort -nr | head -5 | while read count ip; do
        echo -e "  \${RED}\$ip\${NC}: \$count alerts"
    done
else
    echo -e "No alert data available"
fi
echo

# System Health
echo -e "\${YELLOW}💓 System Health\${NC}"
echo "----------------"
IDS_PROCESS=\$(pgrep -f "ids_detection_engine.sh" | wc -l)
if [ \$IDS_PROCESS -gt 0 ]; then
    echo -e "Detection Engine: \${GREEN}✅ Running\${NC}"
else
    echo -e "Detection Engine: \${RED}❌ Stopped\${NC}"
fi

LOG_SIZE=\$(du -h "\$IDS_ALERT_LOG" 2>/dev/null | cut -f1 || echo "0")
echo -e "Alert Log Size: \${GREEN}\$LOG_SIZE\${NC}"

DISK_USAGE=\$(df -h /var/log | tail -1 | awk '{print \$5}')
echo -e "Log Disk Usage: \${GREEN}\$DISK_USAGE\${NC}"
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Start IDS: ./ids_detection_engine.sh daemon"
echo "2. View alerts: tail -f \$IDS_ALERT_LOG"
echo "3. Generate report: ./ids_detection_engine.sh report"
echo "4. Test rules: ./ids_detection_engine.sh test"
echo "5. View blocked IPs: sudo ufw status | grep 'IDS Block'"

echo
echo -e "\${BLUE}====================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
IDS_DASHBOARD_EOF

    chmod +x ~/ids_dashboard.sh
    
    log_message "✅ IDS dashboard created"
}

# Function to create IDS service
create_ids_service() {
    log_message "⚙️ Creating IDS systemd service..."
    
    cat << IDS_SERVICE_EOF | sudo tee /etc/systemd/system/twintower-ids.service
[Unit]
Description=TwinTower Intrusion Detection System
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/ids_detection_engine.sh daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
IDS_SERVICE_EOF

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable twintower-ids.service
    
    log_message "✅ IDS service created"
}

# Function to test IDS system
test_ids_system() {
    log_message "🧪 Testing IDS system..."
    
    cat << IDS_TEST_EOF > ~/test_ids_system.sh
#!/bin/bash

# TwinTower IDS System Test
set -e

IDS_CONFIG_DIR="/etc/twintower-ids"
IDS_RULES_DIR="\$IDS_CONFIG_DIR/rules"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower IDS System Test\${NC}"
echo -e "\${BLUE}===========================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test IDS configuration
echo -e "\${YELLOW}🔧 Testing IDS Configuration\${NC}"
echo "----------------------------"
run_test "IDS config directory exists" "[ -d '\$IDS_CONFIG_DIR' ]"
run_test "IDS rules directory exists" "[ -d '\$IDS_RULES_DIR' ]"
run_test "IDS configuration file exists" "[ -f '\$IDS_CONFIG_DIR/ids.conf' ]"
run_test "IDS whitelist file exists" "[ -f '\$IDS_CONFIG_DIR/whitelist.conf' ]"

# Test detection rules
echo -e "\${YELLOW}📋 Testing Detection Rules\${NC}"
echo "--------------------------"
run_test "SSH attack rules exist" "[ -f '\$IDS_RULES_DIR/ssh_attacks.rules' ]"
run_test "Network attack rules exist" "[ -f '\$IDS_RULES_DIR/network_attacks.rules' ]"
run_test "Web attack rules exist" "[ -f '\$IDS_RULES_DIR/web_attacks.rules' ]"
run_test "System attack rules exist" "[ -f '\$IDS_RULES_DIR/system_attacks.rules' ]"

# Test IDS components
echo -e "\${YELLOW}# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access policies..."
    
    # Internal Network Policy
    cat << INTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/internal-network.json"
{
    "policy_name": "InternalNetwork",
    "description": "Internal network access policy",
    "version": "1.0",
    "priority": 250,
    "conditions": {
        "source_networks": ["192.168.1.0/24", "172.16.0.0/12", "10.0.0.0/8"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp", "udp", "icmp"],
        "encryption_required": false,
        "authentication_required": true
    },
    "permissions": {
        "ssh_access": true,
        "web_access": true,
        "api_access": true,
        "file_access": true
    },
    "restrictions": {
        "bandwidth_limit": "1Gbps",
        "connection_limit": 100,
        "rate_limit": "moderate"
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": false
    }
}
INTERNAL_NET_EOF

    # External Network Policy
    cat << EXTERNAL_NET_EOF | sudo tee "$ZT_POLICIES_DIR/external-network.json"
{
    "policy_name": "ExternalNetwork",
    "description": "External network access policy (high security)",
    "version": "1.0",
    "priority": 500,
    "conditions": {
        "source_networks": ["0.0.0.0/0"],
        "destination_networks": ["192.168.1.0/24"],
        "protocols": ["tcp"],
        "encryption_required": true,
        "authentication_required": true,
        "vpn_required": true
    },
    "permissions": {
        "ssh_access": false,
        "web_access": true,
        "api_access": false,
        "file_access": false
    },
    "restrictions": {
        "bandwidth_limit": "10Mbps",
        "connection_limit": 5,
        "rate_limit": "strict",
        "geolocation_required": true,
        "time_limited": true
    },
    "security": {
        "intrusion_detection": true,
        "malware_scanning": true,
        "data_loss_prevention": true,
        "threat_intelligence": true
    }
}
EXTERNAL_NET_EOF

    log_message "✅ Network-based policies created"
}

# Function to create zero-trust enforcement engine
create_zt_enforcement() {
    log_message "⚙️ Creating zero-trust enforcement engine..."
    
    cat << ZT_ENGINE_EOF > ~/zt_enforcement_engine.sh
#!/bin/bash

# TwinTower Zero-Trust Enforcement Engine
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_LOG_FILE"
}

audit_log() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$ZT_AUDIT_LOG"
}

# Function to validate user access
validate_user_access() {
    local user="\$1"
    local source_ip="\$2"
    local requested_service="\$3"
    local auth_method="\$4"
    
    log_message "🔍 Validating access for user: \$user from \$source_ip"
    
    # Check if user exists
    if ! id "\$user" &>/dev/null; then
        audit_log "DENY: User \$user does not exist"
        return 1
    fi
    
    # Load and evaluate policies
    local policy_result=0
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            if evaluate_policy "\$policy_file" "\$user" "\$source_ip" "\$requested_service" "\$auth_method"; then
                policy_result=1
                break
            fi
        fi
    done
    
    if [ \$policy_result -eq 1 ]; then
        audit_log "ALLOW: User \$user access granted for \$requested_service"
        create_session "\$user" "\$source_ip" "\$requested_service"
        return 0
    else
        audit_log "DENY: User \$user access denied for \$requested_service"
        return 1
    fi
}

# Function to evaluate policy
evaluate_policy() {
    local policy_file="\$1"
    local user="\$2"
    local source_ip="\$3"
    local requested_service="\$4"
    local auth_method="\$5"
    
    # Parse JSON policy (simplified - in production use jq)
    local policy_name=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
    
    log_message "📋 Evaluating policy: \$policy_name"
    
    # Check user conditions
    if grep -q '"users"' "\$policy_file"; then
        local users=\$(grep '"users"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$users" == *"\$user"* ]]; then
            log_message "✅ User \$user matches policy \$policy_name"
        else
            log_message "❌ User \$user does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check network conditions
    if grep -q '"source_networks"' "\$policy_file"; then
        local networks=\$(grep '"source_networks"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if check_network_match "\$source_ip" "\$networks"; then
            log_message "✅ Source IP \$source_ip matches policy \$policy_name"
        else
            log_message "❌ Source IP \$source_ip does not match policy \$policy_name"
            return 1
        fi
    fi
    
    # Check time restrictions
    if grep -q '"time_restrictions"' "\$policy_file"; then
        if check_time_restrictions "\$policy_file"; then
            log_message "✅ Time restrictions satisfied for policy \$policy_name"
        else
            log_message "❌ Time restrictions not satisfied for policy \$policy_name"
            return 1
        fi
    fi
    
    # Check service permissions
    if grep -q '"\$requested_service"' "\$policy_file"; then
        local service_allowed=\$(grep '"\$requested_service"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
        if [[ "\$service_allowed" == "true" ]]; then
            log_message "✅ Service \$requested_service allowed in policy \$policy_name"
            return 0
        else
            log_message "❌ Service \$requested_service not allowed in policy \$policy_name"
            return 1
        fi
    fi
    
    return 0
}

# Function to check network match
check_network_match() {
    local source_ip="\$1"
    local networks="\$2"
    
    # Simple network matching (in production use ipcalc or similar)
    if [[ "\$networks" == *"100.64.0.0/10"* ]] && [[ "\$source_ip" == 100.64.* ]]; then
        return 0
    elif [[ "\$networks" == *"192.168.1.0/24"* ]] && [[ "\$source_ip" == 192.168.1.* ]]; then
        return 0
    elif [[ "\$networks" == *"0.0.0.0/0"* ]]; then
        return 0
    fi
    
    return 1
}

# Function to check time restrictions
check_time_restrictions() {
    local policy_file="\$1"
    
    local current_hour=\$(date +%H)
    local current_day=\$(date +%A | tr '[:upper:]' '[:lower:]')
    
    # Check allowed hours (simplified)
    if grep -q '"allowed_hours"' "\$policy_file"; then
        local allowed_hours=\$(grep '"allowed_hours"' "\$policy_file" | cut -d'"' -f4)
        local start_hour=\$(echo "\$allowed_hours" | cut -d'-' -f1 | cut -d':' -f1)
        local end_hour=\$(echo "\$allowed_hours" | cut -d'-' -f2 | cut -d':' -f1)
        
        if [ "\$current_hour" -ge "\$start_hour" ] && [ "\$current_hour" -le "\$end_hour" ]; then
            return 0
        else
            return 1
        fi
    fi
    
    # Check allowed days (simplified)
    if grep -q '"allowed_days"' "\$policy_file"; then
        local allowed_days=\$(grep '"allowed_days"' "\$policy_file" | cut -d'[' -f2 | cut -d']' -f1)
        if [[ "\$allowed_days" == *"\$current_day"* ]]; then
            return 0
        else
            return 1
        fi
    fi
    
    return 0
}

# Function to create session
create_session() {
    local user="\$1"
    local source_ip="\$2"
    local service="\$3"
    
    sudo mkdir -p "\$ZT_SESSION_DIR"
    
    local session_id=\$(date +%s)_\$(echo "\$user\$source_ip" | md5sum | cut -d' ' -f1 | head -c 8)
    local session_file="\$ZT_SESSION_DIR/\$session_id.session"
    
    cat > "\$session_file" << SESSION_EOF
{
    "session_id": "\$session_id",
    "user": "\$user",
    "source_ip": "\$source_ip",
    "service": "\$service",
    "start_time": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "last_activity": "\$(date '+%Y-%m-%d %H:%M:%S')",
    "status": "active"
}
SESSION_EOF

    log_message "✅ Session created: \$session_id for user \$user"
}

# Function to monitor active sessions
monitor_sessions() {
    log_message "📊 Monitoring active sessions..."
    
    if [ -d "\$ZT_SESSION_DIR" ]; then
        local active_sessions=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
        log_message "Active sessions: \$active_sessions"
        
        # Check for expired sessions
        for session_file in "\$ZT_SESSION_DIR"/*.session; do
            if [ -f "\$session_file" ]; then
                local session_id=\$(basename "\$session_file" .session)
                local start_time=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
                
                # Check if session is older than 1 hour (3600 seconds)
                local current_time=\$(date +%s)
                local session_time=\$(date -d "\$start_time" +%s)
                local age=\$((current_time - session_time))
                
                if [ \$age -gt 3600 ]; then
                    log_message "⏰ Expiring session: \$session_id"
                    rm -f "\$session_file"
                fi
            fi
        done
    fi
}

# Function to generate compliance report
generate_compliance_report() {
    local report_file="/tmp/zt_compliance_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Zero-Trust Compliance Report
====================================
Generated: \$(date)
Tower: \$(hostname)

Policy Compliance:
-----------------
Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
Enforcement Status: \$(grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf" && echo "ENABLED" || echo "DISABLED")

Access Statistics (Last 24 hours):
---------------------------------
Total Access Attempts: \$(grep -c "Validating access" "\$ZT_LOG_FILE" || echo "0")
Successful Authentications: \$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
Denied Access Attempts: \$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")

Active Sessions:
---------------
Current Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)

Recent Security Events:
----------------------
\$(tail -n 20 "\$ZT_AUDIT_LOG" 2>/dev/null || echo "No recent events")

Policy Violations:
-----------------
\$(grep "DENY:" "\$ZT_AUDIT_LOG" | tail -10 || echo "No recent violations")

Recommendations:
---------------
\$([ \$(grep -c "DENY:" "\$ZT_AUDIT_LOG") -gt 10 ] && echo "High number of access denials - review policies" || echo "Access patterns appear normal")

REPORT_EOF

    log_message "📋 Compliance report generated: \$report_file"
    echo "\$report_file"
}

# Main execution
case "\${1:-monitor}" in
    "validate")
        validate_user_access "\$2" "\$3" "\$4" "\$5"
        ;;
    "monitor")
        log_message "🚀 Starting zero-trust monitoring..."
        while true; do
            monitor_sessions
            sleep 300
        done
        ;;
    "report")
        generate_compliance_report
        ;;
    "status")
        echo "Zero-Trust Status:"
        echo "=================="
        echo "Active Policies: \$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)"
        echo "Active Sessions: \$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)"
        echo "Recent Events: \$(tail -n 5 "\$ZT_AUDIT_LOG" 2>/dev/null | wc -l)"
        ;;
    *)
        echo "Usage: \$0 <validate|monitor|report|status>"
        echo "  validate <user> <source_ip> <service> <auth_method>"
        exit 1
        ;;
esac
ZT_ENGINE_EOF

    chmod +x ~/zt_enforcement_engine.sh
    
    log_message "✅ Zero-trust enforcement engine created"
}

# Function to create zero-trust monitoring dashboard
create_zt_dashboard() {
    log_message "📊 Creating zero-trust monitoring dashboard..."
    
    cat << ZT_DASHBOARD_EOF > ~/zt_dashboard.sh
#!/bin/bash

# TwinTower Zero-Trust Dashboard
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"
ZT_AUDIT_LOG="/var/log/zero-trust-audit.log"
ZT_SESSION_DIR="/var/lib/zero-trust/sessions"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔒 TwinTower Zero-Trust Dashboard\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Zero-Trust Status
echo -e "\${YELLOW}🛡️ Zero-Trust Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_CONFIG_DIR/zero-trust.conf" ]; then
    if grep -q "ZT_ENABLED=true" "\$ZT_CONFIG_DIR/zero-trust.conf"; then
        echo -e "Zero-Trust: \${GREEN}✅ ENABLED\${NC}"
    else
        echo -e "Zero-Trust: \${RED}❌ DISABLED\${NC}"
    fi
else
    echo -e "Zero-Trust: \${RED}❌ NOT CONFIGURED\${NC}"
fi

# Policy Status
POLICY_COUNT=\$(ls "\$ZT_POLICIES_DIR"/*.json 2>/dev/null | wc -l)
echo -e "Active Policies: \${GREEN}\$POLICY_COUNT\${NC}"

# Session Status
if [ -d "\$ZT_SESSION_DIR" ]; then
    SESSION_COUNT=\$(ls "\$ZT_SESSION_DIR"/*.session 2>/dev/null | wc -l)
    echo -e "Active Sessions: \${GREEN}\$SESSION_COUNT\${NC}"
else
    echo -e "Active Sessions: \${YELLOW}0\${NC}"
fi
echo

# Access Statistics
echo -e "\${YELLOW}📊 Access Statistics (Last 24 hours)\${NC}"
echo "-----------------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    ALLOW_COUNT=\$(grep -c "ALLOW:" "\$ZT_AUDIT_LOG" || echo "0")
    DENY_COUNT=\$(grep -c "DENY:" "\$ZT_AUDIT_LOG" || echo "0")
    TOTAL_COUNT=\$((ALLOW_COUNT + DENY_COUNT))
    
    echo -e "Total Requests: \${BLUE}\$TOTAL_COUNT\${NC}"
    echo -e "Allowed: \${GREEN}\$ALLOW_COUNT\${NC}"
    echo -e "Denied: \${RED}\$DENY_COUNT\${NC}"
    
    if [ \$TOTAL_COUNT -gt 0 ]; then
        SUCCESS_RATE=\$(echo "scale=2; \$ALLOW_COUNT * 100 / \$TOTAL_COUNT" | bc -l 2>/dev/null || echo "0")
        echo -e "Success Rate: \${GREEN}\$SUCCESS_RATE%\${NC}"
    fi
else
    echo -e "No audit data available"
fi
echo

# Active Policies
echo -e "\${YELLOW}📋 Active Policies\${NC}"
echo "------------------"
if [ -d "\$ZT_POLICIES_DIR" ]; then
    for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
        if [ -f "\$policy_file" ]; then
            POLICY_NAME=\$(grep '"policy_name"' "\$policy_file" | cut -d'"' -f4)
            PRIORITY=\$(grep '"priority"' "\$policy_file" | cut -d':' -f2 | tr -d ' ,')
            echo -e "  \${GREEN}•\${NC} \$POLICY_NAME (Priority: \$PRIORITY)"
        fi
    done
else
    echo -e "No policies configured"
fi
echo

# Recent Events
echo -e "\${YELLOW}🔍 Recent Security Events\${NC}"
echo "-------------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    tail -n 5 "\$ZT_AUDIT_LOG" | while read line; do
        if [[ "\$line" == *"ALLOW:"* ]]; then
            echo -e "\${GREEN}✅ \$line\${NC}"
        elif [[ "\$line" == *"DENY:"* ]]; then
            echo -e "\${RED}❌ \$line\${NC}"
        else
            echo -e "\${BLUE}ℹ️  \$line\${NC}"
        fi
    done
else
    echo -e "No recent events"
fi
echo

# Active Sessions
echo -e "\${YELLOW}👥 Active Sessions\${NC}"
echo "------------------"
if [ -d "\$ZT_SESSION_DIR" ]; then
    for session_file in "\$ZT_SESSION_DIR"/*.session; do
        if [ -f "\$session_file" ]; then
            USER=\$(grep '"user"' "\$session_file" | cut -d'"' -f4)
            SOURCE_IP=\$(grep '"source_ip"' "\$session_file" | cut -d'"' -f4)
            SERVICE=\$(grep '"service"' "\$session_file" | cut -d'"' -f4)
            START_TIME=\$(grep '"start_time"' "\$session_file" | cut -d'"' -f4)
            echo -e "  \${GREEN}•\${NC} \$USER from \$SOURCE_IP (\$SERVICE) - \$START_TIME"
        fi
    done
    
    if [ \$SESSION_COUNT -eq 0 ]; then
        echo -e "No active sessions"
    fi
else
    echo -e "No session data available"
fi
echo

# Compliance Status
echo -e "\${YELLOW}📊 Compliance Status\${NC}"
echo "--------------------"
if [ -f "\$ZT_AUDIT_LOG" ]; then
    RECENT_VIOLATIONS=\$(grep "DENY:" "\$ZT_AUDIT_LOG" | grep "\$(date '+%Y-%m-%d')" | wc -l)
    
    if [ \$RECENT_VIOLATIONS -eq 0 ]; then
        echo -e "Compliance Status: \${GREEN}✅ GOOD\${NC}"
    elif [ \$RECENT_VIOLATIONS -lt 5 ]; then
        echo -e "Compliance Status: \${YELLOW}⚠️  MODERATE\${NC}"
    else
        echo -e "Compliance Status: \${RED}❌ NEEDS ATTENTION\${NC}"
    fi
    
    echo -e "Today's Violations: \${RED}\$RECENT_VIOLATIONS\${NC}"
else
    echo -e "Compliance Status: \${YELLOW}⚠️  NO DATA\${NC}"
fi
echo

# Quick Actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View policies: ls \$ZT_POLICIES_DIR/"
echo "2. Monitor sessions: ./zt_enforcement_engine.sh monitor"
echo "3. Generate report: ./zt_enforcement_engine.sh report"
echo "4. Check status: ./zt_enforcement_engine.sh status"

echo
echo -e "\${BLUE}=================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
ZT_DASHBOARD_EOF

    chmod +x ~/zt_dashboard.sh
    
    log_message "✅ Zero-trust monitoring dashboard created"
}

# Function to create zero-trust testing suite
create_zt_testing() {
    log_message "🧪 Creating zero-trust testing suite..."
    
    cat << ZT_TEST_EOF > ~/test_zero_trust.sh
#!/bin/bash

# TwinTower Zero-Trust Testing Suite
set -e

ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="\$ZT_CONFIG_DIR/policies"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Zero-Trust Testing Suite\${NC}"
echo -e "\${BLUE}====================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zero-trust configuration
echo -e "\${YELLOW}🔧 Testing Zero-Trust Configuration\${NC}"
echo "-----------------------------------"
run_test "ZT config directory exists" "[ -d '\$ZT_CONFIG_DIR' ]"
run_test "ZT policies directory exists" "[ -d '\$ZT_POLICIES_DIR' ]"
run_test "ZT configuration file exists" "[ -f '\$ZT_CONFIG_DIR/zero-trust.conf' ]"

# Test policy files
echo -e "\${YELLOW}📋 Testing Policy Files\${NC}"
echo "----------------------"
run_test "Admin users policy exists" "[ -f '\$ZT_POLICIES_DIR/admin-users.json' ]"
run_test "Standard users policy exists" "[ -f '\$ZT_POLICIES_DIR/standard-users.json' ]"
run_test "Service accounts policy exists" "[ -f '\$ZT_POLICIES_DIR/service-accounts.json' ]"
run_test "Trusted devices policy exists" "[ -f '\$ZT_POLICIES_DIR/trusted-devices.json' ]"
run_test "BYOD policy exists" "[ -f '\$ZT_POLICIES_DIR/byod-devices.json' ]"

# Test enforcement engine
echo -e "\${YELLOW}⚙️ Testing Enforcement Engine\${NC}"
echo "-----------------------------"
run_test "Enforcement engine exists" "[ -f '\$HOME/zt_enforcement_engine.sh' ]"
run_test "Enforcement engine executable" "[ -x '\$HOME/zt_enforcement_engine.sh' ]"
run_test "ZT dashboard exists" "[ -f '\$HOME/zt_dashboard.sh' ]"

# Test log files
echo -e "\${YELLOW}📊 Testing Logging\${NC}"
echo "------------------"
run_test "ZT log file exists" "[ -f '/var/log/zero-trust.log' ]"
run_test "ZT audit log exists" "[ -f '/var/log/zero-trust-audit.log' ]"

# Test policy validation
echo -e "\${YELLOW}🔍 Testing Policy Validation\${NC}"
echo "----------------------------"
for policy_file in "\$ZT_POLICIES_DIR"/*.json; do
    if [ -f "\$policy_file" ]; then
        policy_name=\$(basename "\$policy_file" .json)
        run_test "Policy \$policy_name is valid JSON" "python3 -m json.tool '\$policy_file' > /dev/null"
    fi
done

# Test access scenarios
echo -e "\${YELLOW}🚪 Testing Access Scenarios\${NC}"
echo "---------------------------"
run_test "Admin access validation" "./zt_enforcement_engine.sh validate ubuntu 100.64.0.1 ssh_access publickey"
run_test "External access blocking" "! ./zt_enforcement_engine.sh validate hacker 1.2.3.4 ssh_access password"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zero-trust tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi
ZT_TEST_EOF

    chmod +x ~/test_zero_trust.sh
    
    log_message "✅ Zero-trust testing suite created"
}

# Main execution
main() {
    echo -e "${BLUE}🔒 TwinTower Zero-Trust Access Control${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_zero_trust
            create_identity_policies
            create_device_policies
            create_network_policies
            create_zt_enforcement
            create_zt_dashboard
            create_zt_testing
            
            # Create session directory
            sudo mkdir -p /var/lib/zero-trust/sessions
            
            echo -e "${GREEN}✅ Zero-trust access control configured!${NC}"
            ;;
        "status")
            ~/zt_dashboard.sh
            ;;
        "test")
            ~/test_zero_trust.sh
            ;;
        "monitor")
            ~/zt_enforcement_engine.sh monitor
            ;;
        "report")
            ~/zt_enforcement_engine.sh report
            ;;
        "validate")
            ~/zt_enforcement_engine.sh validate "$POLICY_NAME" "$3" "$4" "$5"
            ;;
        "policies")
            if [ -d "$ZT_POLICIES_DIR" ]; then
                for policy_file in "$ZT_POLICIES_DIR"/*.json; do
                    if [ -f "$policy_file" ]; then
                        policy_name=$(grep '"policy_name"' "$policy_file" | cut -d'"' -f4)
                        priority=$(grep '"priority"' "$policy_file" | cut -d':' -f2 | tr -d ' ,')
                        echo -e "${BLUE}Policy: $policy_name${NC} (Priority: $priority)"
                    fi
                done
            else
                echo -e "${RED}❌ No policies configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|test|monitor|report|validate|policies> [policy_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/zero_trust_access.sh
```

### **Step 2: Execute Zero-Trust Setup**

```bash
# Setup zero-trust access control
./zero_trust_access.sh setup

# View zero-trust status
./zero_trust_access.sh status

# Test zero-trust implementation
./zero_trust_access.sh test

# Monitor zero-trust enforcement
./zero_trust_access.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## # Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone-based firewall rules..."
    
    # Create UFW application profiles for each zone
    create_ufw_app_profiles
    
    # Apply zone-specific rules
    for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "$zone_file" ]; then
            source "$zone_file"
            apply_zone_rules "$ZONE_NAME" "$zone_file"
        fi
    done
    
    log_message "✅ Zone-based firewall rules implemented"
}

# Function to create UFW application profiles
create_ufw_app_profiles() {
    log_message "📋 Creating UFW application profiles..."
    
    # TwinTower Management Profile
    cat << MGMT_PROFILE_EOF | sudo tee /etc/ufw/applications.d/twintower-management
[TwinTower-Management]
title=TwinTower Management Services
description=Administrative and monitoring interfaces
ports=3000:3099/tcp|6000:6099/tcp

[TwinTower-SSH]
title=TwinTower SSH Services
description=Custom SSH ports for towers
ports=2122,2222,2322/tcp

[TwinTower-GPU]
title=TwinTower GPU Services
description=GPU compute and ML workloads
ports=4000:4099/tcp|8000:8099/tcp

[TwinTower-Docker]
title=TwinTower Docker Services
description=Container orchestration and services
ports=2377/tcp|4789/udp|7946/tcp|7946/udp|5000:5099/tcp
MGMT_PROFILE_EOF

    # Reload UFW application profiles
    sudo ufw app update all
    
    log_message "✅ UFW application profiles created"
}

# Function to apply zone-specific rules
apply_zone_rules() {
    local zone_name="$1"
    local zone_file="$2"
    
    log_message "🔒 Applying rules for zone: $zone_name"
    
    # Source zone configuration
    source "$zone_file"
    
    case "$zone_name" in
        "DMZ")
            # DMZ zone rules - restrictive
            sudo ufw deny from any to any port 22 comment "DMZ: Block SSH"
            sudo ufw allow from any to any port 80 comment "DMZ: Allow HTTP"
            sudo ufw allow from any to any port 443 comment "DMZ: Allow HTTPS"
            sudo ufw limit from any to any port 8080 comment "DMZ: Limit Alt HTTP"
            ;;
        "INTERNAL")
            # Internal zone rules - moderate
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Internal: SSH Access"
                sudo ufw allow from "$network" to any app TwinTower-Docker comment "Internal: Docker Services"
            done
            ;;
        "TRUSTED")
            # Trusted zone rules - permissive
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" comment "Trusted: Full Access"
            done
            ;;
        "MANAGEMENT")
            # Management zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-Management comment "Management: Admin Access"
                sudo ufw allow from "$network" to any app TwinTower-SSH comment "Management: SSH Access"
            done
            ;;
        "GPU")
            # GPU zone rules
            IFS=',' read -ra NETWORKS <<< "$ZONE_NETWORKS"
            for network in "${NETWORKS[@]}"; do
                sudo ufw allow from "$network" to any app TwinTower-GPU comment "GPU: Compute Access"
            done
            ;;
    esac
    
    log_message "✅ Zone rules applied for: $zone_name"
}

# Function to create zone monitoring
create_zone_monitoring() {
    log_message "📊 Creating zone monitoring system..."
    
    cat << ZONE_MONITOR_EOF > ~/zone_monitor.sh
#!/bin/bash

# TwinTower Zone Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-300}"
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/zone-monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor zone traffic
monitor_zone_traffic() {
    local zone_name="\$1"
    local zone_networks="\$2"
    
    log_message "📈 Monitoring traffic for zone: \$zone_name"
    
    # Count connections per zone
    local connection_count=0
    
    IFS=',' read -ra NETWORKS <<< "\$zone_networks"
    for network in "\${NETWORKS[@]}"; do
        # Count active connections from this network
        local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
        connection_count=\$((connection_count + net_connections))
    done
    
    log_message "Zone \$zone_name: \$connection_count active connections"
    
    # Check for anomalies
    if [ "\$connection_count" -gt 100 ]; then
        log_message "🚨 HIGH ALERT: Unusual connection count for zone \$zone_name: \$connection_count"
    fi
}

# Function to analyze zone security events
analyze_zone_security() {
    local zone_name="\$1"
    
    log_message "🔍 Analyzing security events for zone: \$zone_name"
    
    # Check UFW logs for zone-related blocks
    local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$zone_name" || echo "0")
    
    if [ "\$blocked_today" -gt 0 ]; then
        log_message "🛡️ Zone \$zone_name: \$blocked_today blocked attempts today"
    fi
}

# Function to generate zone report
generate_zone_report() {
    local report_file="/tmp/zone_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower Network Zone Report
============================
Generated: \$(date)
Tower: \$(hostname)

Zone Status Overview:
--------------------
REPORT_EOF

    # Analyze each zone
    for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
        if [ -f "\$zone_file" ]; then
            source "\$zone_file"
            echo "Zone: \$ZONE_NAME (\$ZONE_TRUST_LEVEL trust)" >> "\$report_file"
            echo "  Networks: \$ZONE_NETWORKS" >> "\$report_file"
            echo "  Ports: \$ZONE_PORTS" >> "\$report_file"
            echo "  Status: Active" >> "\$report_file"
            echo "" >> "\$report_file"
        fi
    done
    
    cat >> "\$report_file" << REPORT_EOF

Recent Security Events:
----------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | tail -10)

Zone Traffic Summary:
--------------------
\$(sudo ss -s)

REPORT_EOF

    log_message "📋 Zone report generated: \$report_file"
    echo "\$report_file"
}

# Function to start zone monitoring
start_zone_monitoring() {
    log_message "🚀 Starting zone monitoring daemon..."
    
    while true; do
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                monitor_zone_traffic "\$ZONE_NAME" "\$ZONE_NETWORKS"
                analyze_zone_security "\$ZONE_NAME"
            fi
        done
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 12)) -eq 0 ]; then
            generate_zone_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_zone_monitoring
        ;;
    "report")
        generate_zone_report
        ;;
    "status")
        for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
            if [ -f "\$zone_file" ]; then
                source "\$zone_file"
                echo -e "\${BLUE}Zone: \$ZONE_NAME\${NC}"
                echo "  Trust Level: \$ZONE_TRUST_LEVEL"
                echo "  Networks: \$ZONE_NETWORKS"
                echo "  Ports: \$ZONE_PORTS"
                echo ""
            fi
        done
        ;;
    *)
        echo "Usage: \$0 <monitor|report|status>"
        exit 1
        ;;
esac
ZONE_MONITOR_EOF

    chmod +x ~/zone_monitor.sh
    
    log_message "✅ Zone monitoring system created"
}

# Function to create zone management dashboard
create_zone_dashboard() {
    log_message "📊 Creating zone management dashboard..."
    
    cat << DASHBOARD_EOF > ~/zone_dashboard.sh
#!/bin/bash

# TwinTower Zone Management Dashboard
set -e

ZONES_CONFIG_DIR="/etc/network-zones"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🌐 TwinTower Network Zone Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# Zone overview
echo -e "\${YELLOW}📋 Zone Overview\${NC}"
echo "----------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Determine status color based on trust level
        case "\$ZONE_TRUST_LEVEL" in
            "HIGH") STATUS_COLOR="\${GREEN}" ;;
            "MEDIUM") STATUS_COLOR="\${YELLOW}" ;;
            "LOW") STATUS_COLOR="\${RED}" ;;
            *) STATUS_COLOR="\${NC}" ;;
        esac
        
        echo -e "\${STATUS_COLOR}🔒 \$ZONE_NAME\${NC} (\$ZONE_TRUST_LEVEL trust)"
        echo "   Networks: \$ZONE_NETWORKS"
        echo "   Ports: \$ZONE_PORTS"
        echo ""
    fi
done

# Active connections per zone
echo -e "\${YELLOW}📊 Active Connections\${NC}"
echo "--------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        # Count connections (simplified)
        local connection_count=0
        IFS=',' read -ra NETWORKS <<< "\$ZONE_NETWORKS"
        for network in "\${NETWORKS[@]}"; do
            if [ "\$network" != "0.0.0.0/0" ]; then
                local net_connections=\$(sudo netstat -tn | grep ESTABLISHED | grep -c "\$network" || echo "0")
                connection_count=\$((connection_count + net_connections))
            fi
        done
        
        echo -e "\$ZONE_NAME: \${GREEN}\$connection_count\${NC} active"
    fi
done
echo

# Security events
echo -e "\${YELLOW}🚨 Security Events (Today)\${NC}"
echo "-------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        source "\$zone_file"
        
        local blocked_today=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | grep -c "\$ZONE_NAME" || echo "0")
        
        if [ "\$blocked_today" -gt 0 ]; then
            echo -e "\$ZONE_NAME: \${RED}\$blocked_today\${NC} blocked attempts"
        else
            echo -e "\$ZONE_NAME: \${GREEN}No threats\${NC}"
        fi
    fi
done
echo

# Zone rules summary
echo -e "\${YELLOW}📋 Zone Rules Summary\${NC}"
echo "--------------------"
TOTAL_RULES=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Total UFW Rules: \${GREEN}\$TOTAL_RULES\${NC}"
echo -e "Zone-based Rules: \${GREEN}\$(sudo ufw status | grep -c "Zone\|DMZ\|Internal\|Trusted\|Management\|GPU" || echo "0")\${NC}"
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. Monitor zones: ./zone_monitor.sh"
echo "2. Generate report: ./zone_monitor.sh report"
echo "3. View UFW status: sudo ufw status verbose"
echo "4. Reload zones: ./network_segmentation.sh reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/zone_dashboard.sh
    
    log_message "✅ Zone management dashboard created"
}

# Function to create zone testing script
create_zone_testing() {
    log_message "🧪 Creating zone testing script..."
    
    cat << TEST_EOF > ~/test_network_zones.sh
#!/bin/bash

# TwinTower Network Zone Testing Script
set -e

ZONES_CONFIG_DIR="/etc/network-zones"
TEST_RESULTS="/tmp/zone_test_results_\$(date +%Y%m%d_%H%M%S).txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}🧪 TwinTower Network Zone Testing\${NC}"
echo -e "\${BLUE}=================================\${NC}"
echo

# Test results tracking
PASSED=0
FAILED=0

run_test() {
    local test_name="\$1"
    local test_command="\$2"
    
    echo -e "\${YELLOW}🔍 Testing: \$test_name\${NC}"
    
    if eval "\$test_command" > /dev/null 2>&1; then
        echo -e "\${GREEN}✅ PASS: \$test_name\${NC}"
        echo "PASS: \$test_name" >> "\$TEST_RESULTS"
        PASSED=\$((PASSED + 1))
    else
        echo -e "\${RED}❌ FAIL: \$test_name\${NC}"
        echo "FAIL: \$test_name" >> "\$TEST_RESULTS"
        FAILED=\$((FAILED + 1))
    fi
}

# Test zone configuration files
echo -e "\${YELLOW}📋 Testing Zone Configuration\${NC}"
echo "------------------------------"
for zone_file in "\$ZONES_CONFIG_DIR"/*.conf; do
    if [ -f "\$zone_file" ]; then
        zone_name=\$(basename "\$zone_file" .conf)
        run_test "Zone config exists: \$zone_name" "[ -f '\$zone_file' ]"
        run_test "Zone config readable: \$zone_name" "[ -r '\$zone_file' ]"
    fi
done

# Test UFW application profiles
echo -e "\${YELLOW}🔧 Testing UFW Application Profiles\${NC}"
echo "-----------------------------------"
run_test "TwinTower-Management profile" "sudo ufw app info TwinTower-Management"
run_test "TwinTower-SSH profile" "sudo ufw app info TwinTower-SSH"
run_test "TwinTower-GPU profile" "sudo ufw app info TwinTower-GPU"
run_test "TwinTower-Docker profile" "sudo ufw app info TwinTower-Docker"

# Test zone-specific connectivity
echo -e "\${YELLOW}🌐 Testing Zone Connectivity\${NC}"
echo "----------------------------"

# Test Tailscale (Trusted Zone)
if command -v tailscale &> /dev/null; then
    TAILSCALE_IP=\$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "\$TAILSCALE_IP" ]; then
        run_test "Tailscale connectivity" "ping -c 1 \$TAILSCALE_IP"
    fi
fi

# Test SSH connectivity
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
run_test "SSH port accessible" "timeout 5 bash -c '</dev/tcp/localhost/\$SSH_PORT'"

# Test Docker connectivity
if command -v docker &> /dev/null; then
    run_test "Docker daemon accessible" "docker version"
fi

# Test zone isolation
echo -e "\${YELLOW}🔒 Testing Zone Isolation\${NC}"
echo "-------------------------"
run_test "UFW active" "sudo ufw status | grep -q 'Status: active'"
run_test "Default deny incoming" "sudo ufw status verbose | grep -q 'Default: deny (incoming)'"
run_test "Zone rules present" "sudo ufw status | grep -q 'Zone\|DMZ\|Internal\|Trusted'"

# Generate test report
echo
echo -e "\${BLUE}📋 Test Results Summary\${NC}"
echo "======================="
echo -e "Tests Passed: \${GREEN}\$PASSED\${NC}"
echo -e "Tests Failed: \${RED}\$FAILED\${NC}"
echo -e "Total Tests: \$((PASSED + FAILED))"
echo

if [ \$FAILED -eq 0 ]; then
    echo -e "\${GREEN}🎉 All zone tests passed!\${NC}"
else
    echo -e "\${RED}⚠️  \$FAILED tests failed - review configuration\${NC}"
fi

echo -e "\${BLUE}📄 Detailed results: \$TEST_RESULTS\${NC}"
TEST_EOF

    chmod +x ~/test_network_zones.sh
    
    log_message "✅ Zone testing script created"
}

# Main execution
main() {
    echo -e "${BLUE}🌐 TwinTower Network Segmentation & Zone Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME${NC}"
    echo -e "${BLUE}===================================================${NC}"
    
    case "$ACTION" in
        "setup")
            define_network_zones
            implement_zone_rules
            create_zone_monitoring
            create_zone_dashboard
            create_zone_testing
            
            echo -e "${GREEN}✅ Network segmentation configured!${NC}"
            ;;
        "status")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                ~/zone_dashboard.sh
            else
                echo -e "${RED}❌ Network zones not configured${NC}"
            fi
            ;;
        "monitor")
            ~/zone_monitor.sh
            ;;
        "test")
            ~/test_network_zones.sh
            ;;
        "reload")
            implement_zone_rules
            sudo ufw reload
            echo -e "${GREEN}✅ Zone rules reloaded${NC}"
            ;;
        "list")
            if [ -d "$ZONES_CONFIG_DIR" ]; then
                for zone_file in "$ZONES_CONFIG_DIR"/*.conf; do
                    if [ -f "$zone_file" ]; then
                        source "$zone_file"
                        echo -e "${BLUE}Zone: $ZONE_NAME${NC}"
                        echo "  Description: $ZONE_DESCRIPTION"
                        echo "  Trust Level: $ZONE_TRUST_LEVEL"
                        echo "  Networks: $ZONE_NETWORKS"
                        echo ""
                    fi
                done
            else
                echo -e "${RED}❌ No zones configured${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 <setup|status|monitor|test|reload|list> [zone_name] [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/network_segmentation.sh
```

### **Step 2: Execute Network Segmentation Setup**

```bash
# Setup network segmentation
./network_segmentation.sh setup

# View zone configuration
./network_segmentation.sh list

# Test zone implementation
./network_segmentation.sh test

# Monitor zones
./network_segmentation.sh monitor
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔒 **Zero-Trust Access Policies**

### **Step 1: Create Zero-Trust Access Control System**

```bash
cat > ~/zero_trust_access.sh << 'EOF'
#!/bin/bash

# TwinTower Zero-Trust Access Control System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
POLICY_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Zero-trust configuration
ZT_CONFIG_DIR="/etc/zero-trust"
ZT_POLICIES_DIR="$ZT_CONFIG_DIR/policies"
ZT_LOG_FILE="/var/log/zero-trust.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$ZT_LOG_FILE"
}

# Function to setup zero-trust infrastructure
setup_zero_trust() {
    log_message "🔒 Setting up zero-trust infrastructure..."
    
    # Create configuration directories
    sudo mkdir -p "$ZT_CONFIG_DIR" "$ZT_POLICIES_DIR"
    sudo touch "$ZT_LOG_FILE"
    
    # Create zero-trust configuration
    cat << ZT_CONFIG_EOF | sudo tee "$ZT_CONFIG_DIR/zero-trust.conf"
# TwinTower Zero-Trust Configuration
ZT_ENABLED=true
ZT_DEFAULT_POLICY="DENY"
ZT_LOGGING_LEVEL="INFO"
ZT_AUDIT_ENABLED=true
ZT_ENCRYPTION_REQUIRED=true
ZT_AUTHENTICATION_REQUIRED=true
ZT_AUTHORIZATION_REQUIRED=true
ZT_CONTINUOUS_VERIFICATION=true
ZT_SESSION_TIMEOUT=3600
ZT_MAX_FAILED_ATTEMPTS=3
ZT_LOCKOUT_DURATION=1800
ZT_GEOLOCATION_ENABLED=false
ZT_DEVICE_FINGERPRINTING=true
ZT_BEHAVIORAL_ANALYSIS=true
ZT_CONFIG_EOF

    log_message "✅ Zero-trust infrastructure created"
}

# Function to create identity-based policies
create_identity_policies() {
    log_message "👤 Creating identity-based access policies..."
    
    # Administrative Users Policy
    cat << ADMIN_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/admin-users.json"
{
    "policy_name": "AdminUsers",
    "description": "Administrative users with elevated privileges",
    "version": "1.0",
    "priority": 100,
    "conditions": {
        "users": ["ubuntu", "admin", "root"],
        "groups": ["sudo", "docker", "adm"],
        "authentication_methods": ["publickey", "certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "06:00-23:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": true,
        "docker_access": true,
        "gpu_access": true,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 5,
        "session_timeout": 3600,
        "idle_timeout": 1800,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "INFO",
        "log_commands": true,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
ADMIN_POLICY_EOF

    # Standard Users Policy
    cat << USER_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/standard-users.json"
{
    "policy_name": "StandardUsers",
    "description": "Standard users with limited privileges",
    "version": "1.0",
    "priority": 200,
    "conditions": {
        "users": ["user", "developer", "analyst"],
        "groups": ["users"],
        "authentication_methods": ["publickey"],
        "source_networks": ["100.64.0.0/10"],
        "time_restrictions": {
            "allowed_hours": "08:00-18:00",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": false,
        "gpu_access": true,
        "monitoring_access": false,
        "log_access": false
    },
    "restrictions": {
        "max_sessions": 2,
        "session_timeout": 2400,
        "idle_timeout": 900,
        "password_required": false,
        "mfa_required": true
    },
    "audit": {
        "log_level": "WARN",
        "log_commands": false,
        "log_file_access": false,
        "alert_on_failure": true
    }
}
USER_POLICY_EOF

    # Service Accounts Policy
    cat << SERVICE_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/service-accounts.json"
{
    "policy_name": "ServiceAccounts",
    "description": "Automated service accounts",
    "version": "1.0",
    "priority": 300,
    "conditions": {
        "users": ["docker", "monitoring", "backup"],
        "groups": ["service"],
        "authentication_methods": ["certificate"],
        "source_networks": ["100.64.0.0/10", "192.168.1.0/24"],
        "time_restrictions": {
            "allowed_hours": "00:00-23:59",
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
    },
    "permissions": {
        "ssh_access": true,
        "sudo_access": false,
        "docker_access": true,
        "gpu_access": false,
        "monitoring_access": true,
        "log_access": true
    },
    "restrictions": {
        "max_sessions": 10,
        "session_timeout": 7200,
        "idle_timeout": 3600,
        "password_required": false,
        "mfa_required": false
    },
    "audit": {
        "log_level": "ERROR",
        "log_commands": false,
        "log_file_access": true,
        "alert_on_failure": true
    }
}
SERVICE_POLICY_EOF

    log_message "✅ Identity-based policies created"
}

# Function to create device-based policies
create_device_policies() {
    log_message "📱 Creating device-based access policies..."
    
    # Trusted Devices Policy
    cat << TRUSTED_DEVICE_EOF | sudo tee "$ZT_POLICIES_DIR/trusted-devices.json"
{
    "policy_name": "TrustedDevices",
    "description": "Pre-approved trusted devices",
    "version": "1.0",
    "priority": 150,
    "conditions": {
        "device_types": ["laptop", "workstation", "server"],
        "os_types": ["linux", "windows", "macos"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "current",
        "certificate_required": true
    },
    "permissions": {
        "full_access": true,
        "admin_access": true,
        "sensitive_data_access": true
    },
    "restrictions": {
        "geolocation_required": false,
        "vpn_required": false,
        "time_limited": false
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true
    }
}
TRUSTED_DEVICE_EOF

    # BYOD Policy
    cat << BYOD_POLICY_EOF | sudo tee "$ZT_POLICIES_DIR/byod-devices.json"
{
    "policy_name": "BYODDevices",
    "description": "Bring Your Own Device policy",
    "version": "1.0",
    "priority": 400,
    "conditions": {
        "device_types": ["mobile", "tablet", "personal-laptop"],
        "os_types": ["android", "ios", "windows", "macos", "linux"],
        "encryption_required": true,
        "antivirus_required": true,
        "patch_level": "recent",
        "certificate_required": false
    },
    "permissions": {
        "full_access": false,
        "admin_access": false,
        "sensitive_data_access": false,
        "limited_access": true
    },
    "restrictions": {
        "geolocation_required": true,
        "vpn_required": true,
        "time_limited": true,
        "data_download_restricted": true,
        "screenshot_blocked": true
    },
    "audit": {
        "device_fingerprinting": true,
        "behavior_monitoring": true,
        "anomaly_detection": true,
        "data_loss_prevention": true
    }
}
BYOD_POLICY_EOF

    log_message "✅ Device-based policies created"
}

# Function to create network-based policies
create_network_policies() {
    log_message "🌐 Creating network-based access# 🔥 Section 5C: Firewall & Access Control
## TwinTower GPU Infrastructure Guide

---

### 📑 **Table of Contents**
- [🎯 Overview](#-overview)
- [🔧 Prerequisites](#-prerequisites)
- [🛡️ Advanced UFW Firewall Configuration](#-advanced-ufw-firewall-configuration)
- [🌐 Network Segmentation & Zone Management](#-network-segmentation--zone-management)
- [🔒 Zero-Trust Access Policies](#-zero-trust-access-policies)
- [🚨 Intrusion Detection & Prevention](#-intrusion-detection--prevention)
- [📊 Network Traffic Monitoring](#-network-traffic-monitoring)
- [⚡ Performance Optimization](#-performance-optimization)
- [🔄 Backup & Recovery](#-backup--recovery)
- [🚀 Next Steps](#-next-steps)

---

## 🎯 **Overview**

Section 5C implements comprehensive firewall and access control policies to complete your TwinTower GPU infrastructure security framework, building upon the secure Tailscale mesh (5A) and hardened SSH (5B) implementations.

### **What This Section Accomplishes:**
- ✅ Advanced UFW firewall with intelligent rules
- ✅ Network segmentation with security zones
- ✅ Zero-trust access policies and micro-segmentation
- ✅ Intrusion detection and prevention systems
- ✅ Real-time network traffic monitoring
- ✅ Performance-optimized security policies
- ✅ Automated threat response and mitigation

### **Security Architecture:**
```
Internet ←→ Tailscale Mesh ←→ Firewall Zones ←→ TwinTower Infrastructure
                                     ↓
    ┌─────────────────────────────────────────────────────────────────────┐
    │     DMZ Zone          Internal Zone        Management Zone           │
    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
    │  │ Public APIs │    │ GPU Cluster │    │ Admin Tools │              │
    │  │ Web Services│    │ Docker Swarm│    │ Monitoring  │              │
    │  └─────────────┘    └─────────────┘    └─────────────┘              │
    │         │                   │                   │                   │
    │    ┌─────────────────────────────────────────────────────────┐      │
    │    │          Firewall Rules & Access Control              │      │
    │    └─────────────────────────────────────────────────────────┘      │
    └─────────────────────────────────────────────────────────────────────┘
```

### **Port Management Strategy:**
- **Management Ports**: 3000-3099 (Web UIs, dashboards)
- **GPU Services**: 4000-4099 (ML/AI workloads)
- **Docker Services**: 5000-5099 (Container applications)
- **Monitoring**: 6000-6099 (Metrics, logging)
- **Custom Apps**: 7000-7099 (User applications)

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔧 **Prerequisites**

### **Required Infrastructure:**
- ✅ Section 5A completed (Tailscale mesh network operational)
- ✅ Section 5B completed (SSH hardening and port configuration)
- ✅ UFW firewall installed and configured
- ✅ Docker Swarm cluster operational
- ✅ Administrative access to all towers

### **Network Requirements:**
- ✅ Tailscale connectivity between all towers
- ✅ SSH access on custom ports (2122/2222/2322)
- ✅ Docker Swarm ports accessible
- ✅ Local network connectivity (192.168.1.0/24)

### **Verification Commands:**
```bash
# Verify previous sections
tailscale status
sudo systemctl status ssh
sudo ufw status
docker node ls
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🛡️ **Advanced UFW Firewall Configuration**

### **Step 1: Create Advanced UFW Management System**

```bash
cat > ~/advanced_ufw_manager.sh << 'EOF'
#!/bin/bash

# TwinTower Advanced UFW Management System
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-status}"
TOWER_NAME="${2:-$(hostname)}"
TOWER_NUM=$(echo "$TOWER_NAME" | grep -o '[0-9]' | head -1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
UFW_CONFIG_DIR="/etc/ufw"
BACKUP_DIR="/home/$(whoami)/firewall_backups"
LOG_FILE="/var/log/ufw-manager.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to determine tower-specific ports
get_tower_ports() {
    local tower_num="$1"
    
    case "$tower_num" in
        "1")
            echo "SSH_PORT=2122 WEB_PORT=3001 GPU_PORT=4001 DOCKER_PORT=5001 MONITOR_PORT=6001"
            ;;
        "2")
            echo "SSH_PORT=2222 WEB_PORT=3002 GPU_PORT=4002 DOCKER_PORT=5002 MONITOR_PORT=6002"
            ;;
        "3")
            echo "SSH_PORT=2322 WEB_PORT=3003 GPU_PORT=4003 DOCKER_PORT=5003 MONITOR_PORT=6003"
            ;;
        *)
            echo "SSH_PORT=22 WEB_PORT=3000 GPU_PORT=4000 DOCKER_PORT=5000 MONITOR_PORT=6000"
            ;;
    esac
}

# Function to setup advanced UFW configuration
setup_advanced_ufw() {
    log_message "🔧 Setting up advanced UFW configuration..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup current UFW configuration
    if [ -d "$UFW_CONFIG_DIR" ]; then
        sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Reset UFW to clean state
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw default deny forward
    
    log_message "✅ UFW default policies configured"
}

# Function to configure network zones
configure_network_zones() {
    log_message "🌐 Configuring network security zones..."
    
    # Define network zones
    local LOCAL_NET="192.168.1.0/24"
    local TAILSCALE_NET="100.64.0.0/10"
    local DOCKER_NET="172.17.0.0/16"
    local SWARM_NET="10.0.0.0/8"
    
    # Allow loopback
    sudo ufw allow in on lo
    sudo ufw allow out on lo
    
    # Configure Tailscale zone (trusted)
    sudo ufw allow from "$TAILSCALE_NET" comment "Tailscale Network"
    
    # Configure local network zone (semi-trusted)
    sudo ufw allow from "$LOCAL_NET" to any port 22 comment "Local SSH"
    sudo ufw allow from "$LOCAL_NET" to any port 80 comment "Local HTTP"
    sudo ufw allow from "$LOCAL_NET" to any port 443 comment "Local HTTPS"
    
    # Configure Docker networks
    sudo ufw allow from "$DOCKER_NET" comment "Docker Network"
    sudo ufw allow from "$SWARM_NET" comment "Docker Swarm Network"
    
    log_message "✅ Network zones configured"
}

# Function to configure service-specific rules
configure_service_rules() {
    log_message "⚙️ Configuring service-specific firewall rules..."
    
    # Get tower-specific ports
    eval $(get_tower_ports "$TOWER_NUM")
    
    # SSH Rules
    sudo ufw allow "$SSH_PORT/tcp" comment "SSH Custom Port Tower$TOWER_NUM"
    
    # Docker Swarm Rules
    sudo ufw allow 2377/tcp comment "Docker Swarm Management"
    sudo ufw allow 7946/tcp comment "Docker Swarm Communication TCP"
    sudo ufw allow 7946/udp comment "Docker Swarm Communication UDP"
    sudo ufw allow 4789/udp comment "Docker Swarm Overlay Network"
    
    # Tailscale Rules
    sudo ufw allow 41641/udp comment "Tailscale"
    
    # GPU and ML Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$GPU_PORT" comment "GPU Services Tower$TOWER_NUM"
    sudo ufw allow from "192.168.1.0/24" to any port "$GPU_PORT" comment "GPU Services Local"
    
    # Web Management Interface
    sudo ufw allow from "$TAILSCALE_NET" to any port "$WEB_PORT" comment "Web Management Tower$TOWER_NUM"
    
    # Docker Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$DOCKER_PORT" comment "Docker Services Tower$TOWER_NUM"
    
    # Monitoring Services
    sudo ufw allow from "$TAILSCALE_NET" to any port "$MONITOR_PORT" comment "Monitoring Tower$TOWER_NUM"
    
    log_message "✅ Service-specific rules configured"
}

# Function to configure advanced security rules
configure_advanced_security() {
    log_message "🔒 Configuring advanced security rules..."
    
    # Rate limiting for SSH
    sudo ufw limit ssh comment "SSH Rate Limiting"
    
    # Block common attack patterns
    sudo ufw deny from 10.0.0.0/8 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 172.16.0.0/12 to any port 22 comment "Block RFC1918 SSH"
    sudo ufw deny from 192.168.0.0/16 to any port 22 comment "Block RFC1918 SSH (except local)"
    sudo ufw allow from 192.168.1.0/24 to any port 22 comment "Allow local SSH"
    
    # Block suspicious ports
    sudo ufw deny 135/tcp comment "Block MS RPC"
    sudo ufw deny 139/tcp comment "Block NetBIOS"
    sudo ufw deny 445/tcp comment "Block SMB"
    sudo ufw deny 1433/tcp comment "Block MS SQL"
    sudo ufw deny 3389/tcp comment "Block RDP"
    
    # Allow ping but limit it
    sudo ufw allow from "$TAILSCALE_NET" proto icmp comment "Tailscale Ping"
    sudo ufw allow from "192.168.1.0/24" proto icmp comment "Local Ping"
    
    log_message "✅ Advanced security rules configured"
}

# Function to configure logging and monitoring
configure_logging() {
    log_message "📊 Configuring UFW logging and monitoring..."
    
    # Enable UFW logging
    sudo ufw logging on
    
    # Create custom logging configuration
    cat << LOG_CONFIG_EOF | sudo tee /etc/rsyslog.d/20-ufw.conf
# UFW logging configuration
:msg,contains,"[UFW " /var/log/ufw.log
& stop
LOG_CONFIG_EOF

    # Create log rotation
    cat << LOGROTATE_EOF | sudo tee /etc/logrotate.d/ufw-custom
/var/log/ufw.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 syslog adm
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
LOGROTATE_EOF

    # Restart rsyslog
    sudo systemctl restart rsyslog
    
    log_message "✅ UFW logging configured"
}

# Function to create UFW monitoring script
create_ufw_monitor() {
    log_message "📈 Creating UFW monitoring script..."
    
    cat << MONITOR_EOF > ~/ufw_monitor.sh
#!/bin/bash

# TwinTower UFW Monitoring Script
set -e

MONITOR_INTERVAL="\${1:-60}"
LOG_FILE="/var/log/ufw-monitor.log"
ALERT_THRESHOLD=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Function to monitor UFW status
monitor_ufw_status() {
    if sudo ufw status | grep -q "Status: active"; then
        log_message "✅ UFW is active"
        return 0
    else
        log_message "❌ UFW is inactive"
        return 1
    fi
}

# Function to analyze UFW logs
analyze_ufw_logs() {
    local blocked_count=\$(sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    local allowed_count=\$(sudo grep "\[UFW ALLOW\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
    
    log_message "📊 Today's UFW activity - Blocked: \$blocked_count, Allowed: \$allowed_count"
    
    if [ "\$blocked_count" -gt "\$ALERT_THRESHOLD" ]; then
        log_message "🚨 HIGH ALERT: \$blocked_count blocked connections today"
        
        # Show top blocked IPs
        echo "Top blocked IPs today:" | tee -a "\$LOG_FILE"
        sudo grep "\[UFW BLOCK\]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
        awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
        while read count ip; do
            echo "  \$ip: \$count attempts" | tee -a "\$LOG_FILE"
        done
    fi
}

# Function to check rule efficiency
check_rule_efficiency() {
    local total_rules=\$(sudo ufw status numbered | grep -c "^\[")
    log_message "📋 Total UFW rules: \$total_rules"
    
    if [ "\$total_rules" -gt 50 ]; then
        log_message "⚠️  Warning: High number of UFW rules may impact performance"
    fi
}

# Function to generate UFW report
generate_ufw_report() {
    local report_file="/tmp/ufw_report_\$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "\$report_file" << REPORT_EOF
TwinTower UFW Monitoring Report
==============================
Generated: \$(date)
Tower: \$(hostname)

UFW Status:
----------
\$(sudo ufw status verbose)

Recent Activity (Last 24 hours):
-------------------------------
Blocked connections: \$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)
Allowed connections: \$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep "\$(date '+%b %d')" | wc -l)

Top Blocked IPs:
---------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Top Blocked Ports:
-----------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | awk '{print \$14}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -10)

Recent Blocked Connections:
--------------------------
\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | tail -10)

REPORT_EOF

    echo "📋 UFW report generated: \$report_file"
    log_message "UFW report generated: \$report_file"
}

# Function to start monitoring daemon
start_monitoring() {
    log_message "🚀 Starting UFW monitoring daemon..."
    
    while true; do
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        
        # Generate report every hour
        if [ \$(((\$(date +%s) / \$MONITOR_INTERVAL) % 60)) -eq 0 ]; then
            generate_ufw_report
        fi
        
        sleep "\$MONITOR_INTERVAL"
    done
}

# Main execution
case "\${1:-monitor}" in
    "monitor")
        start_monitoring
        ;;
    "status")
        monitor_ufw_status
        analyze_ufw_logs
        check_rule_efficiency
        ;;
    "report")
        generate_ufw_report
        ;;
    *)
        echo "Usage: \$0 <monitor|status|report>"
        exit 1
        ;;
esac
MONITOR_EOF

    chmod +x ~/ufw_monitor.sh
    
    log_message "✅ UFW monitoring script created"
}

# Function to optimize UFW performance
optimize_ufw_performance() {
    log_message "⚡ Optimizing UFW performance..."
    
    # Create custom UFW configuration for performance
    cat << PERF_CONFIG_EOF | sudo tee /etc/ufw/sysctl.conf
# TwinTower UFW Performance Optimization

# Network performance
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.core.netdev_max_backlog = 5000

# Connection tracking
net.netfilter.nf_conntrack_max = 131072
net.netfilter.nf_conntrack_tcp_timeout_established = 7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30

# Rate limiting
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048

# Security hardening
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
PERF_CONFIG_EOF

    # Apply sysctl settings
    sudo sysctl -p /etc/ufw/sysctl.conf
    
    log_message "✅ UFW performance optimized"
}

# Function to create UFW dashboard
create_ufw_dashboard() {
    log_message "📊 Creating UFW dashboard..."
    
    cat << DASHBOARD_EOF > ~/ufw_dashboard.sh
#!/bin/bash

# TwinTower UFW Dashboard
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔥 TwinTower UFW Firewall Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# UFW Status
echo -e "\${YELLOW}🛡️ UFW Status\${NC}"
echo "---------------"
if sudo ufw status | grep -q "Status: active"; then
    echo -e "Firewall Status: \${GREEN}✅ Active\${NC}"
else
    echo -e "Firewall Status: \${RED}❌ Inactive\${NC}"
fi

# Rule count
RULE_COUNT=\$(sudo ufw status numbered | grep -c "^\[" || echo "0")
echo -e "Active Rules: \${GREEN}\$RULE_COUNT\${NC}"

# Default policies
echo -e "Default Incoming: \${RED}DENY\${NC}"
echo -e "Default Outgoing: \${GREEN}ALLOW\${NC}"
echo

# Recent activity
echo -e "\${YELLOW}📈 Recent Activity (Last Hour)\${NC}"
echo "------------------------------"
HOUR_AGO=\$(date -d '1 hour ago' '+%b %d %H')
CURRENT_HOUR=\$(date '+%b %d %H')

BLOCKED_HOUR=\$(sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)
ALLOWED_HOUR=\$(sudo grep "[UFW ALLOW]" /var/log/ufw.log | grep -E "(\$HOUR_AGO|\$CURRENT_HOUR)" | wc -l)

echo -e "Blocked Connections: \${RED}\$BLOCKED_HOUR\${NC}"
echo -e "Allowed Connections: \${GREEN}\$ALLOWED_HOUR\${NC}"
echo

# Top blocked IPs
echo -e "\${YELLOW}🚫 Top Blocked IPs (Today)\${NC}"
echo "-------------------------"
sudo grep "[UFW BLOCK]" /var/log/ufw.log | grep "\$(date '+%b %d')" | \
awk '{print \$13}' | cut -d= -f2 | sort | uniq -c | sort -nr | head -5 | \
while read count ip; do
    echo -e "  \${RED}\$ip\${NC}: \$count attempts"
done
echo

# Service status
echo -e "\${YELLOW}⚙️ Service Status\${NC}"
echo "-----------------"
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
echo -e "SSH Port: \${GREEN}\$SSH_PORT\${NC}"

if sudo systemctl is-active --quiet docker; then
    echo -e "Docker: \${GREEN}✅ Running\${NC}"
else
    echo -e "Docker: \${RED}❌ Stopped\${NC}"
fi

if sudo systemctl is-active --quiet tailscaled; then
    echo -e "Tailscale: \${GREEN}✅ Running\${NC}"
else
    echo -e "Tailscale: \${RED}❌ Stopped\${NC}"
fi
echo

# Quick actions
echo -e "\${YELLOW}🔧 Quick Actions\${NC}"
echo "----------------"
echo "1. View detailed rules: sudo ufw status numbered"
echo "2. Monitor real-time: sudo tail -f /var/log/ufw.log"
echo "3. Generate report: ./ufw_monitor.sh report"
echo "4. Reload firewall: sudo ufw reload"

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ Dashboard updated: \$(date)\${NC}"
DASHBOARD_EOF

    chmod +x ~/ufw_dashboard.sh
    
    log_message "✅ UFW dashboard created"
}

# Main execution
main() {
    echo -e "${BLUE}🔥 TwinTower Advanced UFW Management${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME (Tower$TOWER_NUM)${NC}"
    echo -e "${BLUE}===================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_advanced_ufw
            configure_network_zones
            configure_service_rules
            configure_advanced_security
            configure_logging
            create_ufw_monitor
            optimize_ufw_performance
            create_ufw_dashboard
            
            # Enable UFW
            sudo ufw --force enable
            
            echo -e "${GREEN}✅ Advanced UFW configuration completed!${NC}"
            ;;
        "status")
            sudo ufw status verbose
            ;;
        "dashboard")
            ./ufw_dashboard.sh
            ;;
        "monitor")
            ./ufw_monitor.sh
            ;;
        "optimize")
            optimize_ufw_performance
            ;;
        "backup")
            sudo cp -r "$UFW_CONFIG_DIR" "$BACKUP_DIR/ufw_backup_$(date +%Y%m%d_%H%M%S)"
            echo -e "${GREEN}✅ UFW configuration backed up${NC}"
            ;;
        "reload")
            sudo ufw reload
            echo -e "${GREEN}✅ UFW reloaded${NC}"
            ;;
        *)
            echo "Usage: $0 <setup|status|dashboard|monitor|optimize|backup|reload> [tower_name]"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/advanced_ufw_manager.sh
```

### **Step 2: Execute Advanced UFW Setup**

```bash
# Setup advanced UFW configuration on each tower
./advanced_ufw_manager.sh setup $(hostname)

# Verify UFW status
./advanced_ufw_manager.sh status

# Launch UFW dashboard
./advanced_ufw_manager.sh dashboard
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🌐 **Network Segmentation & Zone Management**

### **Step 1: Create Network Segmentation System**

```bash
cat > ~/network_segmentation.sh << 'EOF'
#!/bin/bash

# TwinTower Network Segmentation & Zone Management
# Section 5C: Firewall & Access Control

set -e

ACTION="${1:-setup}"
ZONE_NAME="${2:-}"
TOWER_NAME="${3:-$(hostname)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Network zones configuration
ZONES_CONFIG_DIR="/etc/network-zones"
LOG_FILE="/var/log/network-zones.log"

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to define network zones
define_network_zones() {
    log_message "🌐 Defining network security zones..."
    
    sudo mkdir -p "$ZONES_CONFIG_DIR"
    
    # DMZ Zone - Public-facing services
    cat << DMZ_EOF | sudo tee "$ZONES_CONFIG_DIR/dmz.conf"
# DMZ Zone Configuration
ZONE_NAME="DMZ"
ZONE_DESCRIPTION="Public-facing services and APIs"
ZONE_NETWORKS="0.0.0.0/0"
ZONE_TRUST_LEVEL="LOW"
ZONE_PORTS="80,443,8080,8443"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="STRICT"
ZONE_INTRUSION_DETECTION="ENABLED"
DMZ_EOF

    # Internal Zone - Private infrastructure
    cat << INTERNAL_EOF | sudo tee "$ZONES_CONFIG_DIR/internal.conf"
# Internal Zone Configuration
ZONE_NAME="INTERNAL"
ZONE_DESCRIPTION="Private infrastructure and services"
ZONE_NETWORKS="192.168.1.0/24,172.16.0.0/12,10.0.0.0/8"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="22,80,443,2377,4789,7946"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
INTERNAL_EOF

    # Trusted Zone - Tailscale and management
    cat << TRUSTED_EOF | sudo tee "$ZONES_CONFIG_DIR/trusted.conf"
# Trusted Zone Configuration
ZONE_NAME="TRUSTED"
ZONE_DESCRIPTION="Tailscale mesh and management interfaces"
ZONE_NETWORKS="100.64.0.0/10"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="ALL"
ZONE_PROTOCOLS="tcp,udp,icmp"
ZONE_LOGGING="LOW"
ZONE_RATE_LIMIT="RELAXED"
ZONE_INTRUSION_DETECTION="MONITORING"
TRUSTED_EOF

    # Management Zone - Administrative access
    cat << MGMT_EOF | sudo tee "$ZONES_CONFIG_DIR/management.conf"
# Management Zone Configuration
ZONE_NAME="MANAGEMENT"
ZONE_DESCRIPTION="Administrative and monitoring services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="HIGH"
ZONE_PORTS="2122,2222,2322,3000-3099,6000-6099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="HIGH"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
MGMT_EOF

    # GPU Zone - GPU compute services
    cat << GPU_EOF | sudo tee "$ZONES_CONFIG_DIR/gpu.conf"
# GPU Zone Configuration
ZONE_NAME="GPU"
ZONE_DESCRIPTION="GPU compute and ML services"
ZONE_NETWORKS="100.64.0.0/10,192.168.1.0/24"
ZONE_TRUST_LEVEL="MEDIUM"
ZONE_PORTS="4000-4099,8000-8099"
ZONE_PROTOCOLS="tcp,udp"
ZONE_LOGGING="MEDIUM"
ZONE_RATE_LIMIT="MODERATE"
ZONE_INTRUSION_DETECTION="ENABLED"
GPU_EOF

    log_message "✅ Network zones defined"
}

# Function to implement zone-based firewall rules
implement_zone_rules() {
    log_message "🔧 Implementing zone
