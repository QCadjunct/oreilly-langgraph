# 🔐 Section 5A: Tailscale Mesh VPN Setup
## TwinTower GPU Infrastructure Guide

---

### 📑 **Table of Contents**
- [🎯 Overview](#-overview)
- [🔧 Prerequisites](#-prerequisites)
- [📦 Tailscale Installation](#-tailscale-installation)
- [🌐 Mesh Network Configuration](#-mesh-network-configuration)
- [🔗 Tower Authentication](#-tower-authentication)
- [📡 Network Testing & Verification](#-network-testing--verification)
- [🎛️ Management & Monitoring](#-management--monitoring)
- [🔄 Backup & Recovery](#-backup--recovery)
- [🚀 Next Steps](#-next-steps)

---

## 🎯 **Overview**

Section 5A establishes a secure Tailscale mesh VPN network across your TwinTower GPU infrastructure, providing zero-trust networking with automatic encryption and simplified connectivity management.

### **What This Section Accomplishes:**
- ✅ Tailscale mesh VPN across all 3 towers
- ✅ Automatic peer discovery and connection
- ✅ End-to-end encryption between towers
- ✅ Cross-platform compatibility (Windows/WSL2/Linux)
- ✅ Foundation for secure remote access
- ✅ Network monitoring and management tools

### **Architecture Overview:**
```
TwinTower1 (192.168.1.100) ←→ Tailscale Mesh ←→ TwinTower2 (192.168.1.101)
                                    ↕
                               TwinTower3 (192.168.1.102)
                                    ↕
                            Remote Access Points
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔧 **Prerequisites**

### **Required Infrastructure:**
- ✅ TwinTower infrastructure (Sections 1-4 complete)
- ✅ WSL2 Ubuntu 24.04 on all towers
- ✅ Docker Swarm cluster operational
- ✅ Internet connectivity on all towers
- ✅ Administrative access to all systems

### **Network Requirements:**
- ✅ Outbound HTTPS (443) access
- ✅ UDP 41641 for Tailscale (automatic)
- ✅ Local network access between towers
- ✅ Email account for Tailscale authentication

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📦 **Tailscale Installation**

### **Step 1: Install Tailscale on All Towers**

Create the installation script:

```bash
# Create Tailscale installation script
cat > ~/install_tailscale.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Installation Script
# Section 5A: Tailscale Mesh VPN Setup

set -e

TOWER_NAME="${1:-$(hostname)}"
LOG_FILE="/var/log/tailscale-install.log"

echo "🚀 Starting Tailscale installation for $TOWER_NAME..."

# Create log directory
sudo mkdir -p /var/log
sudo touch $LOG_FILE

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | sudo tee -a $LOG_FILE
}

# Update system packages
log_message "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Add Tailscale repository
log_message "Adding Tailscale repository..."
curl -fsSL https://tailscale.com/install.sh | sh

# Verify installation
log_message "Verifying Tailscale installation..."
if command -v tailscale &> /dev/null; then
    TAILSCALE_VERSION=$(tailscale version | head -n1)
    log_message "Tailscale installed successfully: $TAILSCALE_VERSION"
    echo "✅ Tailscale installation complete for $TOWER_NAME"
else
    log_message "ERROR: Tailscale installation failed"
    echo "❌ Tailscale installation failed"
    exit 1
fi

# Create systemd service directory
sudo mkdir -p /etc/systemd/system/tailscaled.service.d

# Create service override for better logging
cat << 'SERVICE_EOF' | sudo tee /etc/systemd/system/tailscaled.service.d/override.conf
[Service]
Environment=TS_DEBUG=true
StandardOutput=journal
StandardError=journal
SERVICE_EOF

# Enable and start Tailscale service
log_message "Enabling and starting Tailscale service..."
sudo systemctl daemon-reload
sudo systemctl enable tailscaled
sudo systemctl start tailscaled

# Verify service status
if sudo systemctl is-active --quiet tailscaled; then
    log_message "Tailscale service started successfully"
    echo "✅ Tailscale service running"
else
    log_message "ERROR: Tailscale service failed to start"
    echo "❌ Tailscale service failed to start"
    exit 1
fi

echo "🎉 Tailscale installation completed successfully for $TOWER_NAME"
log_message "Installation completed successfully for $TOWER_NAME"
EOF

chmod +x ~/install_tailscale.sh
```

### **Step 2: Execute Installation on Each Tower**

Run on **TwinTower1**:
```bash
# On TwinTower1 WSL2
./install_tailscale.sh TwinTower1
```

Run on **TwinTower2**:
```bash
# On TwinTower2 WSL2
./install_tailscale.sh TwinTower2
```

Run on **TwinTower3**:
```bash
# On TwinTower3 WSL2
./install_tailscale.sh TwinTower3
```

### **Step 3: Verify Installation Status**

Create verification script:

```bash
cat > ~/verify_tailscale.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Verification Script
echo "🔍 Verifying Tailscale installation..."

# Check Tailscale version
echo "📋 Tailscale Version:"
tailscale version

# Check service status
echo "⚙️ Service Status:"
sudo systemctl status tailscaled --no-pager -l

# Check network status
echo "🌐 Network Status:"
tailscale status

# Check logs
echo "📄 Recent Logs:"
sudo journalctl -u tailscaled --no-pager -n 10

echo "✅ Verification complete"
EOF

chmod +x ~/verify_tailscale.sh
./verify_tailscale.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🌐 **Mesh Network Configuration**

### **Step 1: Configure Tailscale Settings**

Create the configuration script:

```bash
cat > ~/configure_tailscale.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Configuration Script
set -e

TOWER_NAME="${1:-$(hostname)}"
CONFIG_FILE="/etc/tailscale/config.json"

echo "🔧 Configuring Tailscale for $TOWER_NAME..."

# Create configuration directory
sudo mkdir -p /etc/tailscale

# Create Tailscale configuration
cat << 'CONFIG_EOF' | sudo tee $CONFIG_FILE
{
    "Version": "1.0",
    "AuthKey": "",
    "Hostname": "",
    "AdvertiseRoutes": [],
    "AcceptRoutes": true,
    "AcceptDNS": true,
    "ShieldsUp": false,
    "RunWebClient": false,
    "RunSSH": false,
    "ExitNode": false,
    "ExitNodeAllowLANAccess": true,
    "AdvertiseTags": ["tag:twintower", "tag:gpu-cluster"],
    "LogLevel": "info"
}
CONFIG_EOF

# Set proper permissions
sudo chmod 600 $CONFIG_FILE
sudo chown root:root $CONFIG_FILE

# Create startup configuration
cat << 'STARTUP_EOF' | sudo tee /etc/tailscale/startup.conf
# TwinTower Tailscale Startup Configuration
# This file contains startup parameters for Tailscale

# Enable subnet routing
SUBNET_ROUTES="192.168.1.0/24"

# Enable SSH
ENABLE_SSH="true"

# Accept DNS
ACCEPT_DNS="true"

# Accept routes
ACCEPT_ROUTES="true"

# Logging level
LOG_LEVEL="info"
STARTUP_EOF

echo "✅ Tailscale configuration created for $TOWER_NAME"
EOF

chmod +x ~/configure_tailscale.sh
```

### **Step 2: Set Up Network Routing**

Create routing configuration:

```bash
cat > ~/setup_routing.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Routing Setup
set -e

TOWER_NAME="${1:-$(hostname)}"
LOCAL_SUBNET="192.168.1.0/24"

echo "🛣️ Setting up network routing for $TOWER_NAME..."

# Enable IP forwarding
echo "Enabling IP forwarding..."
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Configure iptables for Tailscale
echo "Configuring iptables..."
sudo iptables -t nat -A POSTROUTING -o tailscale0 -j MASQUERADE
sudo iptables -A FORWARD -i tailscale0 -j ACCEPT
sudo iptables -A FORWARD -o tailscale0 -j ACCEPT

# Save iptables rules
sudo apt install -y iptables-persistent
sudo netfilter-persistent save

# Create routing script
cat << 'ROUTE_EOF' | sudo tee /usr/local/bin/tailscale-routing.sh
#!/bin/bash
# TwinTower Tailscale Routing Script

# Wait for Tailscale to be ready
sleep 5

# Configure routing
iptables -t nat -A POSTROUTING -o tailscale0 -j MASQUERADE
iptables -A FORWARD -i tailscale0 -j ACCEPT
iptables -A FORWARD -o tailscale0 -j ACCEPT

echo "Tailscale routing configured"
ROUTE_EOF

sudo chmod +x /usr/local/bin/tailscale-routing.sh

# Create systemd service for routing
cat << 'SERVICE_EOF' | sudo tee /etc/systemd/system/tailscale-routing.service
[Unit]
Description=Tailscale Routing Setup
After=tailscaled.service
Requires=tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/tailscale-routing.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Enable routing service
sudo systemctl daemon-reload
sudo systemctl enable tailscale-routing.service

echo "✅ Network routing configured for $TOWER_NAME"
EOF

chmod +x ~/setup_routing.sh
```

### **Step 3: Configure Each Tower**

Execute on each tower:

```bash
# Run on each tower
./configure_tailscale.sh $(hostname)
./setup_routing.sh $(hostname)
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔗 **Tower Authentication**

### **Step 1: Authenticate First Tower (TwinTower3 - Primary)**

```bash
# On TwinTower3 (primary/manager)
echo "🔑 Authenticating TwinTower3 as primary node..."

# Start Tailscale with authentication
sudo tailscale up \
    --hostname=twinover3-primary \
    --advertise-routes=192.168.1.0/24 \
    --accept-routes=true \
    --accept-dns=true \
    --ssh=true \
    --shields-up=false

# The command will output a URL - open it in your browser to authenticate
echo "🌐 Open the displayed URL in your browser to authenticate"
echo "📝 Use your preferred authentication method (Google, GitHub, etc.)"
```

### **Step 2: Authenticate Remaining Towers**

**On TwinTower1:**
```bash
echo "🔑 Authenticating TwinTower1 as worker node..."

sudo tailscale up \
    --hostname=twinover1-worker \
    --accept-routes=true \
    --accept-dns=true \
    --ssh=true \
    --shields-up=false

# Follow the authentication URL
```

**On TwinTower2:**
```bash
echo "🔑 Authenticating TwinTower2 as worker node..."

sudo tailscale up \
    --hostname=twinover2-worker \
    --accept-routes=true \
    --accept-dns=true \
    --ssh=true \
    --shields-up=false

# Follow the authentication URL
```

### **Step 3: Create Authentication Management Script**

```bash
cat > ~/manage_auth.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Authentication Management
set -e

TOWER_NAME="${1:-$(hostname)}"
ACTION="${2:-status}"

case $ACTION in
    "status")
        echo "🔍 Checking authentication status for $TOWER_NAME..."
        tailscale status
        ;;
    "logout")
        echo "🚪 Logging out $TOWER_NAME..."
        sudo tailscale logout
        ;;
    "login")
        echo "🔑 Initiating login for $TOWER_NAME..."
        if [[ "$TOWER_NAME" == *"tower3"* ]] || [[ "$TOWER_NAME" == *"primary"* ]]; then
            sudo tailscale up \
                --hostname=twinover3-primary \
                --advertise-routes=192.168.1.0/24 \
                --accept-routes=true \
                --accept-dns=true \
                --ssh=true \
                --shields-up=false
        else
            WORKER_NUM=$(echo $TOWER_NAME | grep -o '[0-9]' | head -1)
            sudo tailscale up \
                --hostname=twinover${WORKER_NUM}-worker \
                --accept-routes=true \
                --accept-dns=true \
                --ssh=true \
                --shields-up=false
        fi
        ;;
    "restart")
        echo "🔄 Restarting Tailscale service for $TOWER_NAME..."
        sudo systemctl restart tailscaled
        sleep 5
        tailscale status
        ;;
    *)
        echo "Usage: $0 <tower_name> <status|logout|login|restart>"
        exit 1
        ;;
esac
EOF

chmod +x ~/manage_auth.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📡 **Network Testing & Verification**

### **Step 1: Create Comprehensive Test Suite**

```bash
cat > ~/test_tailscale_mesh.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Mesh Testing Suite
set -e

echo "🧪 Starting Tailscale mesh network testing..."

# Test configuration
declare -A TOWERS=(
    ["twinover1-worker"]=""
    ["twinover2-worker"]=""
    ["twinover3-primary"]=""
)

# Function to run tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo "🔍 Running test: $test_name"
    if eval "$test_command"; then
        echo "✅ PASS: $test_name"
        return 0
    else
        echo "❌ FAIL: $test_name"
        return 1
    fi
}

# Test 1: Service Status
echo "========================================"
echo "🔧 TEST 1: Service Status"
echo "========================================"
run_test "Tailscale Service Running" "sudo systemctl is-active --quiet tailscaled"

# Test 2: Network Status
echo "========================================"
echo "🌐 TEST 2: Network Status"
echo "========================================"
echo "Current Tailscale Status:"
tailscale status

# Test 3: IP Assignment
echo "========================================"
echo "📍 TEST 3: IP Assignment"
echo "========================================"
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "Not assigned")
echo "Tailscale IP: $TAILSCALE_IP"
run_test "Tailscale IP Assigned" "[[ '$TAILSCALE_IP' != 'Not assigned' ]]"

# Test 4: DNS Resolution
echo "========================================"
echo "🔍 TEST 4: DNS Resolution"
echo "========================================"
for hostname in twinover1-worker twinover2-worker twinover3-primary; do
    if [[ "$hostname" != "$(hostname)" ]]; then
        run_test "DNS Resolution: $hostname" "nslookup $hostname | grep -q 'Address:'"
    fi
done

# Test 5: Ping Tests
echo "========================================"
echo "🏓 TEST 5: Connectivity Tests"
echo "========================================"
for hostname in twinover1-worker twinover2-worker twinover3-primary; do
    if [[ "$hostname" != "$(hostname)" ]]; then
        run_test "Ping: $hostname" "ping -c 3 $hostname > /dev/null 2>&1"
    fi
done

# Test 6: Port Accessibility
echo "========================================"
echo "🔌 TEST 6: Port Accessibility"
echo "========================================"
for hostname in twinover1-worker twinover2-worker twinover3-primary; do
    if [[ "$hostname" != "$(hostname)" ]]; then
        run_test "SSH Port: $hostname:22" "timeout 5 bash -c '</dev/tcp/$hostname/22'"
    fi
done

# Test 7: Routing Table
echo "========================================"
echo "🛣️ TEST 7: Routing Table"
echo "========================================"
echo "Current routing table:"
ip route show | grep tailscale || echo "No Tailscale routes found"

# Test 8: Firewall Status
echo "========================================"
echo "🔥 TEST 8: Firewall Status"
echo "========================================"
if command -v ufw &> /dev/null; then
    sudo ufw status
else
    echo "UFW not installed"
fi

# Test 9: Performance Test
echo "========================================"
echo "⚡ TEST 9: Performance Test"
echo "========================================"
for hostname in twinover1-worker twinover2-worker twinover3-primary; do
    if [[ "$hostname" != "$(hostname)" ]]; then
        echo "Testing bandwidth to $hostname..."
        timeout 10 iperf3 -c $hostname -t 5 2>/dev/null || echo "iperf3 not available or connection failed"
    fi
done

echo "🎉 Tailscale mesh testing completed!"
EOF

chmod +x ~/test_tailscale_mesh.sh
```

### **Step 2: Run Tests on Each Tower**

```bash
# Run comprehensive tests
./test_tailscale_mesh.sh

# Quick connectivity check
echo "🔍 Quick connectivity check..."
tailscale ping twinover1-worker
tailscale ping twinover2-worker  
tailscale ping twinover3-primary
```

### **Step 3: Create Monitoring Script**

```bash
cat > ~/monitor_tailscale.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Monitoring Script
set -e

MONITOR_INTERVAL=30
LOG_FILE="/var/log/tailscale-monitor.log"

echo "📊 Starting Tailscale monitoring..."

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# Function to check connectivity
check_connectivity() {
    local target="$1"
    local result
    
    if ping -c 1 -W 5 "$target" &> /dev/null; then
        result="✅ ONLINE"
    else
        result="❌ OFFLINE"
    fi
    
    echo "$result"
}

# Function to monitor network
monitor_network() {
    while true; do
        log_message "=== Network Status Check ==="
        
        # Check service status
        if sudo systemctl is-active --quiet tailscaled; then
            log_message "Service: ✅ Running"
        else
            log_message "Service: ❌ Stopped"
        fi
        
        # Check IP assignment
        TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "Not assigned")
        log_message "IP: $TAILSCALE_IP"
        
        # Check peer connectivity
        for peer in twinover1-worker twinover2-worker twinover3-primary; do
            if [[ "$peer" != "$(hostname)" ]]; then
                status=$(check_connectivity "$peer")
                log_message "Peer $peer: $status"
            fi
        done
        
        log_message "=== End Status Check ==="
        sleep $MONITOR_INTERVAL
    done
}

# Start monitoring
monitor_network
EOF

chmod +x ~/monitor_tailscale.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🎛️ **Management & Monitoring**

### **Step 1: Create Management Dashboard**

```bash
cat > ~/tailscale_dashboard.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Management Dashboard
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display header
show_header() {
    clear
    echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    🔐 TwinTower Tailscale Management Dashboard                    ${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to show status
show_status() {
    echo -e "${YELLOW}📊 System Status${NC}"
    echo "----------------------------------------"
    
    # Service status
    if sudo systemctl is-active --quiet tailscaled; then
        echo -e "Service Status: ${GREEN}✅ Running${NC}"
    else
        echo -e "Service Status: ${RED}❌ Stopped${NC}"
    fi
    
    # IP assignment
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "Not assigned")
    echo -e "Tailscale IP: ${GREEN}$TAILSCALE_IP${NC}"
    
    # Hostname
    echo -e "Hostname: ${GREEN}$(hostname)${NC}"
    
    echo ""
}

# Function to show peers
show_peers() {
    echo -e "${YELLOW}🌐 Peer Status${NC}"
    echo "----------------------------------------"
    tailscale status
    echo ""
}

# Function to show routes
show_routes() {
    echo -e "${YELLOW}🛣️ Routes${NC}"
    echo "----------------------------------------"
    ip route show | grep tailscale || echo "No Tailscale routes found"
    echo ""
}

# Function to show logs
show_logs() {
    echo -e "${YELLOW}📄 Recent Logs${NC}"
    echo "----------------------------------------"
    sudo journalctl -u tailscaled --no-pager -n 10
    echo ""
}

# Function to show menu
show_menu() {
    echo -e "${YELLOW}🎛️ Management Options${NC}"
    echo "----------------------------------------"
    echo "1. Refresh Status"
    echo "2. View Detailed Logs"
    echo "3. Restart Service"
    echo "4. Test Connectivity"
    echo "5. View Configuration"
    echo "6. Logout/Login"
    echo "7. Monitor Mode"
    echo "8. Exit"
    echo ""
    echo -n "Select option (1-8): "
}

# Function to handle menu selection
handle_menu() {
    local choice
    read -r choice
    
    case $choice in
        1)
            echo "🔄 Refreshing status..."
            sleep 1
            ;;
        2)
            echo "📄 Viewing detailed logs..."
            sudo journalctl -u tailscaled --no-pager -n 50
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "🔄 Restarting service..."
            sudo systemctl restart tailscaled
            sleep 3
            echo "✅ Service restarted"
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "🔍 Testing connectivity..."
            ./test_tailscale_mesh.sh
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "⚙️ Current configuration:"
            tailscale status --json | jq . 2>/dev/null || tailscale status
            read -p "Press Enter to continue..."
            ;;
        6)
            echo "🔑 Logout/Login process..."
            ./manage_auth.sh $(hostname) logout
            sleep 2
            ./manage_auth.sh $(hostname) login
            read -p "Press Enter to continue..."
            ;;
        7)
            echo "📊 Starting monitor mode..."
            ./monitor_tailscale.sh
            ;;
        8)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option"
            read -p "Press Enter to continue..."
            ;;
    esac
}

# Main loop
main() {
    while true; do
        show_header
        show_status
        show_peers
        show_routes
        show_menu
        handle_menu
    done
}

# Start dashboard
main
EOF

chmod +x ~/tailscale_dashboard.sh
```

### **Step 2: Create Service Management Scripts**

```bash
# Service control script
cat > ~/tailscale_service.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Service Management
set -e

ACTION="$1"
TOWER_NAME="${2:-$(hostname)}"

case $ACTION in
    "start")
        echo "🚀 Starting Tailscale service on $TOWER_NAME..."
        sudo systemctl start tailscaled
        sudo systemctl start tailscale-routing
        ;;
    "stop")
        echo "🛑 Stopping Tailscale service on $TOWER_NAME..."
        sudo systemctl stop tailscale-routing
        sudo systemctl stop tailscaled
        ;;
    "restart")
        echo "🔄 Restarting Tailscale service on $TOWER_NAME..."
        sudo systemctl restart tailscaled
        sudo systemctl restart tailscale-routing
        ;;
    "status")
        echo "📊 Checking Tailscale service status on $TOWER_NAME..."
        sudo systemctl status tailscaled --no-pager
        sudo systemctl status tailscale-routing --no-pager
        ;;
    "enable")
        echo "🔧 Enabling Tailscale service on $TOWER_NAME..."
        sudo systemctl enable tailscaled
        sudo systemctl enable tailscale-routing
        ;;
    "disable")
        echo "🔧 Disabling Tailscale service on $TOWER_NAME..."
        sudo systemctl disable tailscale-routing
        sudo systemctl disable tailscaled
        ;;
    *)
        echo "Usage: $0 <start|stop|restart|status|enable|disable> [tower_name]"
        exit 1
        ;;
esac

echo "✅ Operation completed successfully"
EOF

chmod +x ~/tailscale_service.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔄 **Backup & Recovery**

### **Step 1: Create Backup Script**

```bash
cat > ~/backup_tailscale.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Backup Script
set -e

BACKUP_DIR="/home/$(whoami)/tailscale_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="tailscale_backup_${TIMESTAMP}.tar.gz"

echo "💾 Starting Tailscale configuration backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create temporary backup directory
TEMP_DIR=$(mktemp -d)
BACKUP_TEMP="$TEMP_DIR/tailscale_backup_$TIMESTAMP"
mkdir -p "$BACKUP_TEMP"

# Backup configuration files
echo "📄 Backing up configuration files..."
if [ -d "/etc/tailscale" ]; then
    sudo cp -r /etc/tailscale "$BACKUP_TEMP/"
fi

# Backup service files
echo "⚙️ Backing up service files..."
sudo cp /etc/systemd/system/tailscaled.service.d/override.conf "$BACKUP_TEMP/" 2>/dev/null || true
sudo cp /etc/systemd/system/tailscale-routing.service "$BACKUP_TEMP/" 2>/dev/null || true
sudo cp /usr/local/bin/tailscale-routing.sh "$BACKUP_TEMP/" 2>/dev/null || true

# Backup network configuration
echo "🌐 Backing up network configuration..."
cp /etc/sysctl.conf "$BACKUP_TEMP/" 2>/dev/null || true
sudo iptables-save > "$BACKUP_TEMP/iptables.rules" 2>/dev/null || true

# Backup authentication state (if safe to do so)
echo "🔑 Backing up authentication state..."
if [ -f "/var/lib/tailscale/tailscaled.state" ]; then
    sudo cp /var/lib/tailscale/tailscaled.state "$BACKUP_TEMP/" 2>/dev/null || true
fi

# Create management scripts backup
echo "📋 Backing up management scripts..."
cp ~/install_tailscale.sh "$BACKUP_TEMP/" 2>/dev/null || true
cp ~/configure_tailscale.sh "$BACKUP_TEMP/" 2>/dev/null || true
cp ~/setup_routing.sh "$BACKUP_TEMP/" 2>/dev/null || true
cp ~/manage_auth.sh "$BACKUP_TEMP/" 2>/dev/null || true
cp ~/test_tailscale_mesh.sh "$BACKUP_TEMP/" 2>/dev/null || true
cp ~/monitor_tailscale.sh "$BACKUP_TEMP/" 2>/dev/null || true
cp ~/tailscale_dashboard.sh "$BACKUP_TEMP/" 2>/dev/null || true

# Create backup metadata
cat > "$BACKUP_TEMP/backup_info.txt" << INFO_EOF
TwinTower Tailscale Backup Information
=====================================
Backup Date: $(date)
Hostname: $(hostname)
Tailscale Version: $(tailscale version | head -n1)
Backup Location: $BACKUP_DIR/$BACKUP_FILE
System Info: $(uname -a)

Files Included:
-

# 🔐 Section 5B: SSH Hardening & Port Configuration
## TwinTower GPU Infrastructure Guide

---

### 📑 **Table of Contents**
- [🎯 Overview](#-overview)
- [🔧 Prerequisites](#-prerequisites)
- [🔑 SSH Key Generation & Management](#-ssh-key-generation--management)
- [🛡️ SSH Configuration Hardening](#-ssh-configuration-hardening)
- [🔢 Custom Port Configuration](#-custom-port-configuration)
- [🔒 Authentication & Access Control](#-authentication--access-control)
- [🧪 Security Testing & Verification](#-security-testing--verification)
- [📊 Monitoring & Logging](#-monitoring--logging)
- [🔄 Backup & Recovery](#-backup--recovery)
- [🚀 Next Steps](#-next-steps)

---

## 🎯 **Overview**

Section 5B implements comprehensive SSH hardening and custom port configuration across your TwinTower GPU infrastructure, building upon the secure Tailscale mesh network established in Section 5A.

### **What This Section Accomplishes:**
- ✅ SSH hardening with enterprise-grade security
- ✅ Custom port configuration (2122/2222/2322)
- ✅ Key-based authentication with centralized management
- ✅ Advanced security policies and access controls
- ✅ Comprehensive logging and monitoring
- ✅ Automated security testing and verification

### **Security Architecture:**
```
Remote Access ←→ Tailscale Mesh ←→ Hardened SSH ←→ TwinTower Infrastructure
                                        ↓
    ┌─────────────────────────────────────────────────────────────────────┐
    │  SSH Port 2122        SSH Port 2222        SSH Port 2322           │
    │  TwinTower1           TwinTower2           TwinTower3               │
    │  (Key Auth)           (Key Auth)           (Key Auth)               │
    │  Hardened Config      Hardened Config      Hardened Config         │
    └─────────────────────────────────────────────────────────────────────┘
```

### **Port Convention:**
- **TwinTower1**: SSH Port 2122 (Standard + 100)
- **TwinTower2**: SSH Port 2222 (Standard + 200)  
- **TwinTower3**: SSH Port 2322 (Standard + 300)

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔧 **Prerequisites**

### **Required Infrastructure:**
- ✅ Section 5A completed (Tailscale mesh network operational)
- ✅ WSL2 Ubuntu 24.04 on all towers
- ✅ Administrative access to all systems
- ✅ Tailscale connectivity verified between towers

### **Security Requirements:**
- ✅ Root/sudo access on all towers
- ✅ Backup of existing SSH configurations
- ✅ Understanding of SSH key management
- ✅ Access to secure key storage location

### **Verification Commands:**
```bash
# Verify Tailscale connectivity
tailscale status

# Check current SSH service
sudo systemctl status ssh

# Verify administrative access
sudo -l
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔑 **SSH Key Generation & Management**

### **Step 1: Create SSH Key Management Infrastructure**

```bash
# Create SSH key management script
cat > ~/ssh_key_manager.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Key Management Script
# Section 5B: SSH Hardening & Port Configuration

set -e

# Configuration
SSH_DIR="$HOME/.ssh"
KEYS_DIR="$SSH_DIR/twintower_keys"
BACKUP_DIR="$HOME/ssh_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to create directories
create_directories() {
    log_message "Creating SSH key management directories..."
    mkdir -p "$SSH_DIR" "$KEYS_DIR" "$BACKUP_DIR"
    chmod 700 "$SSH_DIR" "$KEYS_DIR"
}

# Function to backup existing keys
backup_existing_keys() {
    log_message "Backing up existing SSH keys..."
    
    if [ -f "$SSH_DIR/id_rsa" ] || [ -f "$SSH_DIR/id_ed25519" ]; then
        BACKUP_FILE="$BACKUP_DIR/ssh_keys_backup_$TIMESTAMP.tar.gz"
        tar -czf "$BACKUP_FILE" -C "$SSH_DIR" . 2>/dev/null || true
        log_message "Backup created: $BACKUP_FILE"
    else
        log_message "No existing keys to backup"
    fi
}

# Function to generate master key pair
generate_master_key() {
    log_message "Generating master ED25519 key pair..."
    
    MASTER_KEY="$KEYS_DIR/twintower_master_ed25519"
    
    if [ ! -f "$MASTER_KEY" ]; then
        ssh-keygen -t ed25519 -f "$MASTER_KEY" -N "" -C "twintower-master-$(date +%Y%m%d)"
        chmod 600 "$MASTER_KEY"
        chmod 644 "$MASTER_KEY.pub"
        log_message "Master key generated: $MASTER_KEY"
    else
        log_message "Master key already exists: $MASTER_KEY"
    fi
}

# Function to generate tower-specific keys
generate_tower_keys() {
    log_message "Generating tower-specific key pairs..."
    
    for tower in 1 2 3; do
        TOWER_KEY="$KEYS_DIR/twintower${tower}_ed25519"
        
        if [ ! -f "$TOWER_KEY" ]; then
            ssh-keygen -t ed25519 -f "$TOWER_KEY" -N "" -C "twintower${tower}-$(date +%Y%m%d)"
            chmod 600 "$TOWER_KEY"
            chmod 644 "$TOWER_KEY.pub"
            log_message "Tower${tower} key generated: $TOWER_KEY"
        else
            log_message "Tower${tower} key already exists: $TOWER_KEY"
        fi
    done
}

# Function to generate RSA backup keys
generate_rsa_backup_keys() {
    log_message "Generating RSA backup key pairs..."
    
    RSA_KEY="$KEYS_DIR/twintower_rsa_4096"
    
    if [ ! -f "$RSA_KEY" ]; then
        ssh-keygen -t rsa -b 4096 -f "$RSA_KEY" -N "" -C "twintower-rsa-backup-$(date +%Y%m%d)"
        chmod 600 "$RSA_KEY"
        chmod 644 "$RSA_KEY.pub"
        log_message "RSA backup key generated: $RSA_KEY"
    else
        log_message "RSA backup key already exists: $RSA_KEY"
    fi
}

# Function to create SSH config
create_ssh_config() {
    log_message "Creating SSH client configuration..."
    
    cat > "$SSH_DIR/config" << 'CONFIG_EOF'
# TwinTower SSH Configuration
# Section 5B: SSH Hardening & Port Configuration

# Global settings
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
    Compression yes
    ForwardAgent no
    ForwardX11 no
    HashKnownHosts yes
    VerifyHostKeyDNS yes
    StrictHostKeyChecking yes
    UserKnownHostsFile ~/.ssh/known_hosts
    IdentitiesOnly yes

# TwinTower1 - Worker Node
Host twinover1 twinover1-worker tower1
    HostName twinover1-worker
    Port 2122
    User ubuntu
    IdentityFile ~/.ssh/twintower_keys/twintower1_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
    PubkeyAuthentication yes
    PasswordAuthentication no
    ChallengeResponseAuthentication no

# TwinTower2 - Worker Node
Host twinover2 twinover2-worker tower2
    HostName twinover2-worker
    Port 2222
    User ubuntu
    IdentityFile ~/.ssh/twintower_keys/twintower2_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
    PubkeyAuthentication yes
    PasswordAuthentication no
    ChallengeResponseAuthentication no

# TwinTower3 - Primary Node
Host twinover3 twinover3-primary tower3
    HostName twinover3-primary
    Port 2322
    User ubuntu
    IdentityFile ~/.ssh/twintower_keys/twintower3_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
    PubkeyAuthentication yes
    PasswordAuthentication no
    ChallengeResponseAuthentication no

# Master key fallback
Host twinover* tower*
    IdentityFile ~/.ssh/twintower_keys/twintower_master_ed25519
    IdentityFile ~/.ssh/twintower_keys/twintower_rsa_4096
CONFIG_EOF

    chmod 600 "$SSH_DIR/config"
    log_message "SSH client configuration created"
}

# Function to display key information
display_key_info() {
    log_message "SSH Key Information Summary"
    echo -e "${YELLOW}=====================================${NC}"
    
    for key in "$KEYS_DIR"/*.pub; do
        if [ -f "$key" ]; then
            echo -e "${GREEN}Key:${NC} $(basename "$key")"
            echo -e "${GREEN}Fingerprint:${NC} $(ssh-keygen -lf "$key")"
            echo -e "${GREEN}Type:${NC} $(ssh-keygen -lf "$key" | awk '{print $4}')"
            echo ""
        fi
    done
}

# Function to create authorized_keys template
create_authorized_keys_template() {
    log_message "Creating authorized_keys template..."
    
    TEMPLATE_FILE="$KEYS_DIR/authorized_keys_template"
    
    cat > "$TEMPLATE_FILE" << 'TEMPLATE_EOF'
# TwinTower Authorized Keys Template
# Section 5B: SSH Hardening & Port Configuration
# 
# Usage: Copy this template to ~/.ssh/authorized_keys on each tower
# Replace with actual public keys from twintower_keys directory

# Restriction options for enhanced security
# from="IP_ADDRESS",no-agent-forwarding,no-X11-forwarding,no-port-forwarding

# Master key (emergency access)
# MASTER_KEY_PLACEHOLDER

# Tower-specific keys
# TOWER1_KEY_PLACEHOLDER
# TOWER2_KEY_PLACEHOLDER  
# TOWER3_KEY_PLACEHOLDER

# RSA backup key
# RSA_KEY_PLACEHOLDER
TEMPLATE_EOF

    log_message "Template created: $TEMPLATE_FILE"
}

# Main execution
main() {
    echo -e "${BLUE}🔑 TwinTower SSH Key Management${NC}"
    echo -e "${BLUE}=================================${NC}"
    
    create_directories
    backup_existing_keys
    generate_master_key
    generate_tower_keys
    generate_rsa_backup_keys
    create_ssh_config
    display_key_info
    create_authorized_keys_template
    
    echo -e "${GREEN}✅ SSH key management setup completed!${NC}"
    echo -e "${YELLOW}📋 Next steps:${NC}"
    echo "1. Review generated keys in: $KEYS_DIR"
    echo "2. Distribute public keys to towers"
    echo "3. Configure SSH hardening on each tower"
}

# Execute main function
main "$@"
EOF

chmod +x ~/ssh_key_manager.sh
```

### **Step 2: Generate SSH Keys**

```bash
# Execute SSH key generation
./ssh_key_manager.sh
```

### **Step 3: Create Key Distribution Script**

```bash
cat > ~/distribute_ssh_keys.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Key Distribution Script
set -e

KEYS_DIR="$HOME/.ssh/twintower_keys"
TARGET_TOWER="$1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$TARGET_TOWER" ]; then
    echo "Usage: $0 <tower1|tower2|tower3|all>"
    exit 1
fi

# Function to distribute keys to a tower
distribute_to_tower() {
    local tower_num="$1"
    local tower_host="twinover${tower_num}-worker"
    
    if [ "$tower_num" == "3" ]; then
        tower_host="twinover3-primary"
    fi
    
    echo -e "${BLUE}📤 Distributing keys to Tower${tower_num} (${tower_host})${NC}"
    
    # Create authorized_keys content
    local auth_keys_content=""
    
    # Add master key
    if [ -f "$KEYS_DIR/twintower_master_ed25519.pub" ]; then
        auth_keys_content+="# Master key for emergency access\n"
        auth_keys_content+="$(cat "$KEYS_DIR/twintower_master_ed25519.pub")\n\n"
    fi
    
    # Add tower-specific key
    if [ -f "$KEYS_DIR/twintower${tower_num}_ed25519.pub" ]; then
        auth_keys_content+="# Tower${tower_num} specific key\n"
        auth_keys_content+="$(cat "$KEYS_DIR/twintower${tower_num}_ed25519.pub")\n\n"
    fi
    
    # Add RSA backup key
    if [ -f "$KEYS_DIR/twintower_rsa_4096.pub" ]; then
        auth_keys_content+="# RSA backup key\n"
        auth_keys_content+="$(cat "$KEYS_DIR/twintower_rsa_4096.pub")\n\n"
    fi
    
    # Create temporary authorized_keys file
    local temp_file=$(mktemp)
    echo -e "$auth_keys_content" > "$temp_file"
    
    # Copy to tower (using current SSH access)
    echo "Copying keys to $tower_host..."
    scp "$temp_file" "$tower_host:~/.ssh/authorized_keys_new"
    
    # Set proper permissions and replace
    ssh "$tower_host" "chmod 600 ~/.ssh/authorized_keys_new && mv ~/.ssh/authorized_keys_new ~/.ssh/authorized_keys"
    
    # Clean up
    rm "$temp_file"
    
    echo -e "${GREEN}✅ Keys distributed to Tower${tower_num}${NC}"
}

# Main execution
case "$TARGET_TOWER" in
    "tower1" | "1")
        distribute_to_tower 1
        ;;
    "tower2" | "2")
        distribute_to_tower 2
        ;;
    "tower3" | "3")
        distribute_to_tower 3
        ;;
    "all")
        distribute_to_tower 1
        distribute_to_tower 2
        distribute_to_tower 3
        ;;
    *)
        echo "Invalid tower: $TARGET_TOWER"
        echo "Usage: $0 <tower1|tower2|tower3|all>"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Key distribution completed!${NC}"
EOF

chmod +x ~/distribute_ssh_keys.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🛡️ **SSH Configuration Hardening**

### **Step 1: Create SSH Hardening Script**

```bash
cat > ~/ssh_hardening.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Hardening Script
# Section 5B: SSH Hardening & Port Configuration

set -e

TOWER_NAME="${1:-$(hostname)}"
TOWER_NUM=$(echo "$TOWER_NAME" | grep -o '[0-9]' | head -1)
SSH_PORT=""

# Determine SSH port based on tower number
case "$TOWER_NUM" in
    "1") SSH_PORT=2122 ;;
    "2") SSH_PORT=2222 ;;
    "3") SSH_PORT=2322 ;;
    *) 
        echo "❌ Could not determine tower number from hostname: $TOWER_NAME"
        exit 1
        ;;
esac

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_message "🔐 Starting SSH hardening for Tower$TOWER_NUM (Port: $SSH_PORT)"

# Backup existing SSH configuration
backup_ssh_config() {
    log_message "📋 Backing up existing SSH configuration..."
    
    BACKUP_DIR="/home/$(whoami)/ssh_config_backup"
    mkdir -p "$BACKUP_DIR"
    
    if [ -f "/etc/ssh/sshd_config" ]; then
        sudo cp "/etc/ssh/sshd_config" "$BACKUP_DIR/sshd_config.backup.$(date +%Y%m%d_%H%M%S)"
        log_message "Backup created in: $BACKUP_DIR"
    fi
}

# Create hardened SSH configuration
create_hardened_config() {
    log_message "🛡️ Creating hardened SSH configuration..."
    
    cat << CONFIG_EOF | sudo tee /etc/ssh/sshd_config
# TwinTower SSH Hardened Configuration
# Section 5B: SSH Hardening & Port Configuration
# Tower: $TOWER_NUM, Port: $SSH_PORT

# Basic Configuration
Port $SSH_PORT
AddressFamily inet
ListenAddress 0.0.0.0

# Host Key Configuration
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

# Ciphers and Algorithms (Hardened)
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha2-256,hmac-sha2-512
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512

# Authentication Settings
LoginGraceTime 30
PermitRootLogin no
StrictModes yes
MaxAuthTries 3
MaxSessions 5
MaxStartups 3:30:10

# Public Key Authentication
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys .ssh/authorized_keys2

# Disable Dangerous Authentication Methods
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
KerberosAuthentication no
GSSAPIAuthentication no
UsePAM no

# User Access Control
AllowUsers ubuntu
DenyUsers root
AllowGroups ubuntu sudo
DenyGroups root

# Network and Protocol Settings
Protocol 2
IgnoreRhosts yes
HostbasedAuthentication no
PermitUserEnvironment no
ClientAliveInterval 300
ClientAliveCountMax 2
TCPKeepAlive yes
Compression no

# X11 and Forwarding (Disabled for Security)
X11Forwarding no
X11DisplayOffset 10
X11UseLocalhost yes
PermitTTY yes
PrintMotd no
PrintLastLog yes
AllowTcpForwarding no
AllowStreamLocalForwarding no
GatewayPorts no
PermitTunnel no

# Logging Configuration
SyslogFacility AUTH
LogLevel VERBOSE

# SFTP Configuration
Subsystem sftp internal-sftp

# Additional Security Settings
DebianBanner no
VersionAddendum none
Banner /etc/ssh/banner
PermitUserRC no
AllowAgentForwarding no
DisableForwarding yes

# Connection Limits
MaxStartups 3:30:10
LoginGraceTime 30
CONFIG_EOF

    log_message "✅ Hardened SSH configuration created"
}

# Create SSH banner
create_ssh_banner() {
    log_message "🏷️ Creating SSH banner..."
    
    cat << BANNER_EOF | sudo tee /etc/ssh/banner
╔══════════════════════════════════════════════════════════════════════════════════╗
║                        🔐 AUTHORIZED ACCESS ONLY 🔐                              ║
║                                                                                  ║
║  This system is for authorized users only. All activities are logged and        ║
║  monitored. Unauthorized access is strictly prohibited and will be prosecuted   ║
║  to the full extent of the law.                                                 ║
║                                                                                  ║
║  TwinTower GPU Infrastructure - Tower $TOWER_NUM                                     ║
║  SSH Port: $SSH_PORT                                                                ║
║  Connection Time: $(date)                                           ║
║                                                                                  ║
║  By continuing, you acknowledge that you are authorized to access this system.  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
BANNER_EOF

    sudo chmod 644 /etc/ssh/banner
    log_message "✅ SSH banner created"
}

# Generate new host keys
regenerate_host_keys() {
    log_message "🔑 Regenerating SSH host keys..."
    
    # Remove old host keys
    sudo rm -f /etc/ssh/ssh_host_*
    
    # Generate new host keys
    sudo ssh-keygen -t rsa -b 4096 -f /etc/ssh/ssh_host_rsa_key -N "" -C "Tower$TOWER_NUM-$(date +%Y%m%d)"
    sudo ssh-keygen -t ecdsa -b 521 -f /etc/ssh/ssh_host_ecdsa_key -N "" -C "Tower$TOWER_NUM-$(date +%Y%m%d)"
    sudo ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N "" -C "Tower$TOWER_NUM-$(date +%Y%m%d)"
    
    # Set proper permissions
    sudo chmod 600 /etc/ssh/ssh_host_*
    sudo chmod 644 /etc/ssh/ssh_host_*.pub
    
    log_message "✅ New host keys generated"
}

# Configure fail2ban for SSH protection
configure_fail2ban() {
    log_message "🛡️ Configuring fail2ban..."
    
    # Install fail2ban
    sudo apt update
    sudo apt install -y fail2ban
    
    # Create jail configuration
    cat << JAIL_EOF | sudo tee /etc/fail2ban/jail.d/ssh-twintower.conf
[sshd]
enabled = true
port = $SSH_PORT
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
findtime = 600
bantime = 3600
ignoreip = 127.0.0.1/8 192.168.1.0/24 100.64.0.0/10
JAIL_EOF

    # Enable and start fail2ban
    sudo systemctl enable fail2ban
    sudo systemctl restart fail2ban
    
    log_message "✅ fail2ban configured"
}

# Configure SSH logging
configure_ssh_logging() {
    log_message "📊 Configuring SSH logging..."
    
    # Create rsyslog configuration for SSH
    cat << RSYSLOG_EOF | sudo tee /etc/rsyslog.d/50-ssh.conf
# SSH logging configuration
auth,authpriv.* /var/log/ssh.log
if \$programname == 'sshd' then /var/log/ssh-detailed.log
& stop
RSYSLOG_EOF

    # Create logrotate configuration
    cat << LOGROTATE_EOF | sudo tee /etc/logrotate.d/ssh-twintower
/var/log/ssh.log
/var/log/ssh-detailed.log
{
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
    
    log_message "✅ SSH logging configured"
}

# Test SSH configuration
test_ssh_config() {
    log_message "🧪 Testing SSH configuration..."
    
    # Test SSH daemon configuration
    if sudo sshd -t; then
        log_message "✅ SSH configuration is valid"
    else
        log_message "❌ SSH configuration has errors"
        exit 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🔐 TwinTower SSH Hardening - Tower$TOWER_NUM${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    backup_ssh_config
    create_hardened_config
    create_ssh_banner
    regenerate_host_keys
    configure_fail2ban
    configure_ssh_logging
    test_ssh_config
    
    echo -e "${GREEN}✅ SSH hardening completed for Tower$TOWER_NUM!${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: SSH will restart on port $SSH_PORT${NC}"
    echo -e "${YELLOW}📋 Next steps:${NC}"
    echo "1. Verify SSH key distribution"
    echo "2. Test SSH connectivity on new port"
    echo "3. Restart SSH service: sudo systemctl restart ssh"
}

# Execute main function
main "$@"
EOF

chmod +x ~/ssh_hardening.sh
```

### **Step 2: Execute SSH Hardening on Each Tower**

**Important**: Execute this on each tower individually to avoid losing access:

```bash
# Execute on each tower
./ssh_hardening.sh

# After configuration, restart SSH service
sudo systemctl restart ssh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔢 **Custom Port Configuration**

### **Step 1: Create Port Configuration Script**

```bash
cat > ~/configure_ssh_ports.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Port Configuration Script
set -e

TOWER_NAME="${1:-$(hostname)}"
ACTION="${2:-configure}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to determine port based on tower
get_ssh_port() {
    local tower_num=$(echo "$TOWER_NAME" | grep -o '[0-9]' | head -1)
    
    case "$tower_num" in
        "1") echo "2122" ;;
        "2") echo "2222" ;;
        "3") echo "2322" ;;
        *) echo "22" ;;
    esac
}

# Function to configure firewall for SSH port
configure_firewall() {
    local ssh_port="$1"
    
    log_message "🔥 Configuring firewall for SSH port $ssh_port..."
    
    # Install UFW if not present
    sudo apt update
    sudo apt install -y ufw
    
    # Reset UFW to defaults
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH on custom port
    sudo ufw allow $ssh_port/tcp comment "SSH Custom Port"
    
    # Allow SSH on standard port temporarily (for transition)
    sudo ufw allow 22/tcp comment "SSH Standard Port (Temporary)"
    
    # Allow Tailscale
    sudo ufw allow 41641/udp comment "Tailscale"
    
    # Allow Docker Swarm ports
    sudo ufw allow 2377/tcp comment "Docker Swarm Management"
    sudo ufw allow 7946/tcp comment "Docker Swarm Communication"
    sudo ufw allow 7946/udp comment "Docker Swarm Communication"
    sudo ufw allow 4789/udp comment "Docker Swarm Overlay"
    
    # Allow local network
    sudo ufw allow from 192.168.1.0/24 comment "Local Network"
    
    # Allow Tailscale network
    sudo ufw allow from 100.64.0.0/10 comment "Tailscale Network"
    
    # Enable UFW
    sudo ufw --force enable
    
    log_message "✅ Firewall configured for SSH port $ssh_port"
}

# Function to update SSH service configuration
update_ssh_service() {
    local ssh_port="$1"
    
    log_message "⚙️ Updating SSH service configuration..."
    
    # Create systemd override for SSH service
    sudo mkdir -p /etc/systemd/system/ssh.service.d
    
    cat << SERVICE_EOF | sudo tee /etc/systemd/system/ssh.service.d/override.conf
[Service]
# TwinTower SSH Service Override
# Custom port: $ssh_port
ExecStart=
ExecStart=/usr/sbin/sshd -D -p $ssh_port
ExecReload=
ExecReload=/bin/kill -HUP \$MAINPID

[Unit]
Description=OpenBSD Secure Shell server (TwinTower Port $ssh_port)
After=network.target auditd.service
ConditionPathExists=!/etc/ssh/sshd_not_to_be_run

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    # Reload systemd
    sudo systemctl daemon-reload
    
    log_message "✅ SSH service configuration updated"
}

# Function to create port monitoring script
create_port_monitor() {
    local ssh_port="$1"
    
    log_message "📊 Creating port monitoring script..."
    
    cat << MONITOR_EOF > ~/monitor_ssh_port.sh
#!/bin/bash

# TwinTower SSH Port Monitoring Script
set -e

SSH_PORT="$ssh_port"
TOWER_NAME="$(hostname)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\${BLUE}📊 SSH Port Monitor - \$TOWER_NAME (Port: \$SSH_PORT)\${NC}"
echo -e "\${BLUE}================================================\${NC}"

# Check if SSH is listening on the custom port
echo -e "\${YELLOW}🔍 Checking SSH service status...\${NC}"
if sudo systemctl is-active --quiet ssh; then
    echo -e "\${GREEN}✅ SSH service is running\${NC}"
else
    echo -e "\${RED}❌ SSH service is not running\${NC}"
fi

# Check port listening
echo -e "\${YELLOW}🔍 Checking port listening...\${NC}"
if sudo netstat -tlnp | grep -q ":\$SSH_PORT "; then
    echo -e "\${GREEN}✅ SSH is listening on port \$SSH_PORT\${NC}"
else
    echo -e "\${RED}❌ SSH is not listening on port \$SSH_PORT\${NC}"
fi

# Check firewall rules
echo -e "\${YELLOW}🔍 Checking firewall rules...\${NC}"
if sudo ufw status | grep -q "\$SSH_PORT/tcp"; then
    echo -e "\${GREEN}✅ Firewall allows SSH on port \$SSH_PORT\${NC}"
else
    echo -e "\${RED}❌ Firewall does not allow SSH on port \$SSH_PORT\${NC}"
fi

# Check active connections
echo -e "\${YELLOW}🔍 Active SSH connections...\${NC}"
sudo netstat -tnp | grep ":\$SSH_PORT " | grep ESTABLISHED || echo "No active connections"

# Check recent SSH logs
echo -e "\${YELLOW}🔍 Recent SSH activity...\${NC}"
sudo tail -n 10 /var/log/auth.log | grep sshd || echo "No recent SSH activity"

# Check fail2ban status
echo -e "\${YELLOW}🔍 Checking fail2ban status...\${NC}"
if sudo systemctl is-active --quiet fail2ban; then
    echo -e "\${GREEN}✅ fail2ban is active\${NC}"
    sudo fail2ban-client status sshd || echo "SSH jail not active"
else
    echo -e "\${RED}❌ fail2ban is not active\${NC}"
fi

echo -e "\${BLUE}================================================\${NC}"
echo -e "\${GREEN}✅ SSH port monitoring completed\${NC}"
MONITOR_EOF

    chmod +x ~/monitor_ssh_port.sh
    
    log_message "✅ Port monitoring script created"
}

# Function to test SSH connectivity
test_ssh_connectivity() {
    local ssh_port="$1"
    
    log_message "🧪 Testing SSH connectivity on port $ssh_port..."
    
    # Test local SSH connection
    if timeout 5 bash -c "</dev/tcp/localhost/$ssh_port"; then
        log_message "✅ Local SSH port $ssh_port is accessible"
    else
        log_message "❌ Local SSH port $ssh_port is not accessible"
        return 1
    fi
    
    # Test SSH daemon configuration
    if sudo sshd -t; then
        log_message "✅ SSH configuration is valid"
    else
        log_message "❌ SSH configuration has errors"
        return 1
    fi
}

# Function to create transition script
create_transition_script() {
    local ssh_port="$1"
    
    log_message "🔄 Creating transition script..."
    
    cat << TRANSITION_EOF > ~/ssh_port_transition.sh
#!/bin/bash

# TwinTower SSH Port Transition Script
set -e

SSH_PORT="$ssh_port"
TOWER_NAME="$(hostname)"

echo "🔄 Transitioning SSH to port \$SSH_PORT..."

# Step 1: Restart SSH service
echo "1. Restarting SSH service..."
sudo systemctl restart ssh
sleep 3

# Step 2: Verify SSH is running on new port
echo "2. Verifying SSH on new port..."
if sudo netstat -tlnp | grep -q ":\$SSH_PORT "; then
    echo "✅ SSH is listening on port \$SSH_PORT"
else
    echo "❌ SSH is not listening on port \$SSH_PORT"
    exit 1
fi

# Step 3: Test connectivity
echo "3. Testing connectivity..."
if timeout 5 bash -c "</dev/tcp/localhost/\$SSH_PORT"; then
    echo "✅ SSH port \$SSH_PORT is accessible"
else
    echo "❌ SSH port \$SSH_PORT is not accessible"
    exit 1
fi

# Step 4: Update firewall (remove standard port after verification)
echo "4. Updating firewall..."
echo "⚠️  Standard SSH port (22) is still open for safety"
echo "⚠️  Remove it manually after verifying new port works: sudo ufw delete allow 22/tcp"

# Step 5: Display connection information
echo "5. Connection information:"
echo "   SSH Port: \$SSH_PORT"
echo "   Connect with: ssh -p \$SSH_PORT user@hostname"
echo "   Tailscale: ssh user@tailscale-hostname"

echo "✅ Transition completed successfully!"
TRANSITION_EOF

    chmod +x ~/ssh_port_transition.sh
    
    log_message "✅ Transition script created"
}

# Main execution
main() {
    local ssh_port=$(get_ssh_port)
    
    echo -e "${BLUE}🔢 TwinTower SSH Port Configuration${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME, Port: $ssh_port${NC}"
    echo -e "${BLUE}====================================${NC}"
    
    case "$ACTION" in
        "configure")
            configure_firewall "$ssh_port"
            update_ssh_service "$ssh_port"
            create_port_monitor "$ssh_port"
            test_ssh_connectivity "$ssh_port"
            create_transition_script "$ssh_port"
            
            echo -e "${GREEN}✅ SSH port configuration completed!${NC}"
            echo -e "${YELLOW}📋 Next steps:${NC}"
            echo "1. Run transition script: ./ssh_port_transition.sh"
            echo "2. Test SSH connectivity on new port"
            echo "3. Remove standard port (22) from firewall when ready"
            ;;
        "test")
            test_ssh_connectivity "$ssh_port"
            ;;
        "monitor")
            ./monitor_ssh_port.sh
            ;;
        *)
            echo "Usage: $0 <tower_name> <configure|test|monitor>"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/configure_ssh_ports.sh
```

### **Step 2: Execute Port Configuration on Each Tower**

```bash
# Configure SSH ports on each tower
./configure_ssh_ports.sh $(hostname) configure

# Execute the transition
./ssh_port_transition.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔒 **Authentication & Access Control**

### **Step 1: Create Advanced Authentication Script**

```bash
cat > ~/setup_ssh_auth.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Authentication & Access Control Setup
set -e

TOWER_NAME="${1:-$(hostname)}"
AUTH_MODE="${2:-standard}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to setup SSH certificate authority
setup_ssh_ca() {
    log_message "🏛️ Setting up SSH Certificate Authority..."
    
    SSH_CA_DIR="/etc/ssh/ca"
    sudo mkdir -p "$SSH_CA_DIR"
    
    # Generate CA key if it doesn't exist
    if [ ! -f "$SSH_CA_DIR/twintower_ca" ]; then
        sudo ssh-keygen -t ed25519 -f "$SSH_CA_DIR/twintower_ca" -N "" -C "TwinTower-CA-$(date +%Y%m%d)"
        sudo chmod 600 "$SSH_CA_DIR/twintower_ca"
        sudo chmod 644 "$SSH_CA_DIR/twintower_ca.pub"
    fi
    
    # Configure SSH to trust the CA
    if ! grep -q "TrustedUserCAKeys" /etc/ssh/sshd_config; then
        echo "TrustedUserCAKeys $SSH_CA_DIR/twintower_ca.pub" | sudo tee -a /etc/ssh/sshd_config
    fi
    
    log_message "✅ SSH Certificate Authority configured"
}

# Function to create user certificates
create_user_certificates() {
    log_message "📜 Creating user certificates..."
    
    SSH_CA_DIR="/etc/ssh/ca"
    CERT_DIR="/home/$(whoami)/.ssh/certificates"
    mkdir -p "$CERT_DIR"
    
    # Create certificate for current user
    USER_KEY="$HOME/.ssh/twintower_keys/twintower_master_ed25519"
    USER_CERT="$CERT_DIR/twintower_user_cert"
    
    if [ -f "$USER_KEY.pub" ]; then
        sudo ssh-keygen -s "$SSH_CA_DIR/twintower_ca" \
            -I "$(whoami)@$(hostname)" \
            -n "$(whoami)" \
            -V "+52w" \
            -z 1 \
            "$USER_KEY.pub"
        
        mv "$USER_KEY-cert.pub" "$USER_CERT.pub"
        chmod 644 "$USER_CERT.pub"
        
        log_message "✅ User certificate created: $USER_CERT.pub"
    fi
}

# Function to configure SSH key restrictions
configure_key_restrictions() {
    log_message "🔐 Configuring SSH key restrictions..."
    
    AUTHORIZED_KEYS="$HOME/.ssh/authorized_keys"
    TEMP_FILE=$(mktemp)
    
    # Process each key in authorized_keys
    while IFS= read -r line; do
        if [[ "$line" =~ ^ssh- ]] || [[ "$line" =~ ^ecdsa- ]] || [[ "$line" =~ ^ed25519- ]]; then
            # Add restrictions to public keys
            echo "no-agent-forwarding,no-port-forwarding,no-X11-forwarding,command=\"/usr/local/bin/ssh-command-wrapper.sh\" $line" >> "$TEMP_FILE"
        else
            # Keep comments and other lines as-is
            echo "$line" >> "$TEMP_FILE"
        fi
    done < "$AUTHORIZED_KEYS"
    
    # Replace authorized_keys with restricted version
    mv "$TEMP_FILE" "$AUTHORIZED_KEYS"
    chmod 600 "$AUTHORIZED_KEYS"
    
    log_message "✅ SSH key restrictions configured"
}

# Function to create SSH command wrapper
create_ssh_command_wrapper() {
    log_message "🔧 Creating SSH command wrapper..."
    
    cat << WRAPPER_EOF | sudo tee /usr/local/bin/ssh-command-wrapper.sh
#!/bin/bash

# TwinTower SSH Command Wrapper
# Provides additional security and logging for SSH commands

# Log the SSH command
logger -t ssh-wrapper "User: \$USER, Command: \$SSH_ORIGINAL_COMMAND, Client: \$SSH_CLIENT"

# Allow specific commands only
case "\$SSH_ORIGINAL_COMMAND" in
    "")
        # Interactive shell allowed
        exec /bin/bash
        ;;
    "docker "*|"sudo docker "*|"tailscale "*|"systemctl "*|"journalctl "*)
        # Allow Docker, Tailscale, and system commands
        exec \$SSH_ORIGINAL_COMMAND
        ;;
    "ls "*|"pwd"|"whoami"|"id"|"uptime"|"df "*|"free "*|"ps "*|"top"|"htop")
        # Allow basic system information commands
        exec \$SSH_ORIGINAL_COMMAND
        ;;
    "cat "*|"tail "*|"head "*|"grep "*|"awk "*|"sed "*")
        # Allow basic text processing (restricted paths)
        if [[ "\$SSH_ORIGINAL_COMMAND" =~ /etc/shadow|/etc/passwd ]]; then
            echo "Access denied: Sensitive file access not allowed"
            exit 1
        fi
        exec \$SSH_ORIGINAL_COMMAND
        ;;
    *)
        echo "Command not allowed: \$SSH_ORIGINAL_COMMAND"
        logger -t ssh-wrapper "DENIED - User: \$USER, Command: \$SSH_ORIGINAL_COMMAND, Client: \$SSH_CLIENT"
        exit 1
        ;;
esac
WRAPPER_EOF

    sudo chmod +x /usr/local/bin/ssh-command-wrapper.sh
    
    log_message "✅ SSH command wrapper created"
}

# Function to setup SSH rate limiting
setup_ssh_rate_limiting() {
    log_message "⚡ Setting up SSH rate limiting..."
    
    # Create custom fail2ban jail for SSH
    cat << JAIL_EOF | sudo tee /etc/fail2ban/jail.d/ssh-rate-limit.conf
[ssh-rate-limit]
enabled = true
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
findtime = 300
bantime = 1800
action = iptables[name=SSH, port=ssh, protocol=tcp]
         sendmail-whois[name=SSH, dest=root]
JAIL_EOF

    # Create custom filter for aggressive SSH attempts
    cat << FILTER_EOF | sudo tee /etc/fail2ban/filter.d/ssh-aggressive.conf
[Definition]
failregex = ^%(__prefix_line)s(?:error: PAM: )?[aA]uthentication (?:failure|error) for .* from <HOST>( via \S+)?\s*$
            ^%(__prefix_line)s(?:error: )?Received disconnect from <HOST>: 3: .*: Auth fail$
            ^%(__prefix_line)sFailed \S+ for .* from <HOST>(?: port \d*)?(?: ssh\d*)?$
            ^%(__prefix_line)sROOT LOGIN REFUSED.* FROM <HOST>$
            ^%(__prefix_line)s[iI](?:llegal|nvalid) user .* from <HOST>$
            ^%(__prefix_line)sUser .+ from <HOST> not allowed because not listed in AllowUsers$
            ^%(__prefix_line)sUser .+ from <HOST> not allowed because listed in DenyUsers$
            ^%(__prefix_line)sUser .+ from <HOST> not allowed because not in any group$
            ^%(__prefix_line)srefused connect from \S+ \(<HOST>\)$
            ^%(__prefix_line)sReceived disconnect from <HOST>: 11: Bye Bye$
            ^%(__prefix_line)sConnection closed by <HOST>$
            ^%(__prefix_line)sConnection from <HOST> closed$
ignoreregex =
FILTER_EOF

    # Add aggressive SSH jail
    cat << AGGRESSIVE_EOF | sudo tee /etc/fail2ban/jail.d/ssh-aggressive.conf
[ssh-aggressive]
enabled = true
filter = ssh-aggressive
logpath = /var/log/auth.log
maxretry = 3
findtime = 120
bantime = 3600
action = iptables[name=SSH-AGG, port=ssh, protocol=tcp]
AGGRESSIVE_EOF

    # Restart fail2ban
    sudo systemctl restart fail2ban
    
    log_message "✅ SSH rate limiting configured"
}

# Function to create SSH audit logging
setup_ssh_audit_logging() {
    log_message "📊 Setting up SSH audit logging..."
    
    # Create audit rules for SSH
    cat << AUDIT_EOF | sudo tee /etc/audit/rules.d/ssh.rules
# SSH Audit Rules
-w /etc/ssh/sshd_config -p wa -k ssh_config
-w /etc/ssh/ -p wa -k ssh_keys
-w /home/ -p wa -k ssh_user_keys
-a always,exit -F arch=b64 -S connect -F a2=16 -k ssh_connections
-a always,exit -F arch=b32 -S connect -F a2=16 -k ssh_connections
AUDIT_EOF

    # Install and configure auditd
    sudo apt install -y auditd audispd-plugins
    
    # Restart auditd
    sudo systemctl restart auditd
    
    # Create SSH log analysis script
    cat << ANALYSIS_EOF > ~/ssh_audit_analysis.sh
#!/bin/bash

# TwinTower SSH Audit Analysis
echo "📊 SSH Audit Analysis Report"
echo "============================"

# Recent SSH logins
echo "🔍 Recent SSH logins:"
sudo ausearch -k ssh_connections -ts recent | grep -E "type=SOCKADDR|type=SYSCALL" | head -20

# SSH configuration changes
echo "🔍 SSH configuration changes:"
sudo ausearch -k ssh_config -ts today

# SSH key access
echo "🔍 SSH key access:"
sudo ausearch -k ssh_keys -ts today

echo "✅ Analysis complete"
ANALYSIS_EOF

    chmod +x ~/ssh_audit_analysis.sh
    
    log_message "✅ SSH audit logging configured"
}

# Function to create SSH security dashboard
create_ssh_security_dashboard() {
    log_message "📋 Creating SSH security dashboard..."
    
    cat << DASHBOARD_EOF > ~/ssh_security_dashboard.sh
#!/bin/bash

# TwinTower SSH Security Dashboard
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "\${BLUE}🔐 TwinTower SSH Security Dashboard\${NC}"
echo -e "\${BLUE}===================================\${NC}"
echo

# SSH Service Status
echo -e "\${YELLOW}📊 SSH Service Status\${NC}"
echo "--------------------"
if sudo systemctl is-active --quiet ssh; then
    echo -e "Service Status: \${GREEN}✅ Running\${NC}"
else
    echo -e "Service Status: \${RED}❌ Stopped\${NC}"
fi

# SSH Port Status
SSH_PORT=\$(sudo ss -tlnp | grep sshd | awk '{print \$4}' | cut -d: -f2 | head -1)
echo -e "SSH Port: \${GREEN}\$SSH_PORT\${NC}"

# Active SSH Connections
echo -e "\${YELLOW}🔗 Active SSH Connections\${NC}"
echo "-------------------------"
sudo netstat -tnp | grep ":\$SSH_PORT " | grep ESTABLISHED | wc -l | xargs echo "Active connections:"

# fail2ban Status
echo -e "\${YELLOW}🛡️ fail2ban Status\${NC}"
echo "------------------"
if sudo systemctl is-active --quiet fail2ban; then
    echo -e "fail2ban Status: \${GREEN}✅ Active\${NC}"
    echo "Banned IPs:"
    sudo fail2ban-client status sshd | grep "Banned IP list" | cut -d: -f2 | wc -w | xargs echo
else
    echo -e "fail2ban Status: \${RED}❌ Inactive\${NC}"
fi

# Recent SSH Activity
echo -e "\${YELLOW}📈 Recent SSH Activity\${NC}"
echo "----------------------"
echo "Last 10 SSH events:"
sudo tail -n 10 /var/log/auth.log | grep sshd | cut -d' ' -f1-3,9- | tail -5

# Security Score
echo -e "\${YELLOW}🎯 Security Score\${NC}"
echo "----------------"
SCORE=0

# Check if password auth is disabled
if grep -q "PasswordAuthentication no" /etc/ssh/sshd_config; then
    SCORE=\$((SCORE + 20))
fi

# Check if root login is disabled
if grep -q "PermitRootLogin no" /etc/ssh/sshd_config; then
    SCORE=\$((SCORE + 20))
fi

# Check if custom port is used
if [ "\$SSH_PORT" != "22" ]; then
    SCORE=\$((SCORE + 15))
fi

# Check if fail2ban is active
if sudo systemctl is-active --quiet fail2ban; then
    SCORE=\$((SCORE + 15))
fi

# Check if key authentication is configured
if [ -f "\$HOME/.ssh/authorized_keys" ]; then
    SCORE=\$((SCORE + 15))
fi

# Check if SSH hardening is applied
if grep -q "MaxAuthTries 3" /etc/ssh/sshd_config; then
    SCORE=\$((SCORE + 15))
fi

if [ \$SCORE -ge 80 ]; then
    echo -e "Security Score: \${GREEN}\$SCORE/100 - Excellent\${NC}"
elif [ \$SCORE -ge 60 ]; then
    echo -e "Security Score: \${YELLOW}\$SCORE/100 - Good\${NC}"
else
    echo -e "Security Score: \${RED}\$SCORE/100 - Needs Improvement\${NC}"
fi

echo
echo -e "\${BLUE}===================================\${NC}"
echo -e "\${GREEN}✅ SSH Security Dashboard Complete\${NC}"
DASHBOARD_EOF

    chmod +x ~/ssh_security_dashboard.sh
    
    log_message "✅ SSH security dashboard created"
}

# Main execution
main() {
    echo -e "${BLUE}🔒 TwinTower SSH Authentication & Access Control${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME, Mode: $AUTH_MODE${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    case "$AUTH_MODE" in
        "standard")
            configure_key_restrictions
            create_ssh_command_wrapper
            setup_ssh_rate_limiting
            setup_ssh_audit_logging
            create_ssh_security_dashboard
            ;;
        "advanced")
            setup_ssh_ca
            create_user_certificates
            configure_key_restrictions
            create_ssh_command_wrapper
            setup_ssh_rate_limiting
            setup_ssh_audit_logging
            create_ssh_security_dashboard
            ;;
        "audit")
            ./ssh_audit_analysis.sh
            ;;
        "dashboard")
            ./ssh_security_dashboard.sh
            ;;
        *)
            echo "Usage: $0 <tower_name> <standard|advanced|audit|dashboard>"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}✅ SSH authentication and access control configured!${NC}"
}

# Execute main function
main "$@"
EOF

chmod +x ~/setup_ssh_auth.sh
```

### **Step 2: Execute Authentication Setup**

```bash
# Execute authentication setup on each tower
./setup_ssh_auth.sh $(hostname) standard

# For advanced certificate-based authentication
./setup_ssh_auth.sh $(hostname) advanced
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🧪 **Security Testing & Verification**

### **Step 1: Create Comprehensive Security Test Suite**

```bash
cat > ~/test_ssh_security.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Security Testing Suite
# Section 5B: SSH Hardening & Port Configuration

set -e

TOWER_NAME="${1:-$(hostname)}"
TEST_MODE="${2:-full}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
PASSED=0
FAILED=0
WARNINGS=0

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"
    
    echo -e "${YELLOW}🔍 Testing: $test_name${NC}"
    
    if eval "$test_command"; then
        if [ "$expected_result" = "pass" ]; then
            echo -e "${GREEN}✅ PASS: $test_name${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "${RED}❌ FAIL: $test_name (unexpected pass)${NC}"
            FAILED=$((FAILED + 1))
        fi
    else
        if [ "$expected_result" = "fail" ]; then
            echo -e "${GREEN}✅ PASS: $test_name (expected fail)${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "${RED}❌ FAIL: $test_name${NC}"
            FAILED=$((FAILED + 1))
        fi
    fi
    echo
}

# Test SSH Service Configuration
test_ssh_service() {
    log_message "🔧 Testing SSH Service Configuration"
    echo "====================================="
    
    # Test 1: SSH service is running
    run_test "SSH Service Running" "sudo systemctl is-active --quiet ssh" "pass"
    
    # Test 2: SSH configuration is valid
    run_test "SSH Configuration Valid" "sudo sshd -t 2>/dev/null" "pass"
    
    # Test 3: Custom port is configured
    SSH_PORT=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    run_test "Custom SSH Port ($SSH_PORT)" "[ '$SSH_PORT' != '22' ]" "pass"
    
    # Test 4: SSH is listening on correct port
    run_test "SSH Listening on Port $SSH_PORT" "sudo netstat -tlnp | grep -q ':$SSH_PORT '" "pass"
}

# Test SSH Hardening Configuration
test_ssh_hardening() {
    log_message "🛡️ Testing SSH Hardening Configuration"
    echo "======================================"
    
    # Test password authentication disabled
    run_test "Password Authentication Disabled" "grep -q 'PasswordAuthentication no' /etc/ssh/sshd_config" "pass"
    
    # Test root login disabled
    run_test "Root Login Disabled" "grep -q 'PermitRootLogin no' /etc/ssh/sshd_config" "pass"
    
    # Test X11 forwarding disabled
    run_test "X11 Forwarding Disabled" "grep -q 'X11Forwarding no' /etc/ssh/sshd_config" "pass"
    
    # Test TCP forwarding disabled
    run_test "TCP Forwarding Disabled" "grep -q 'AllowTcpForwarding no' /etc/ssh/sshd_config" "pass"
    
    # Test max auth tries configured
    run_test "Max Auth Tries Configured" "grep -q 'MaxAuthTries 3' /etc/ssh/sshd_config" "pass"
    
    # Test login grace time configured
    run_test "Login Grace Time Configured" "grep -q 'LoginGraceTime 30' /etc/ssh/sshd_config" "pass"
    
    # Test strong ciphers configured
    run_test "Strong Ciphers Configured" "grep -q 'chacha20-poly1305@openssh.com' /etc/ssh/sshd_config" "pass"
    
    # Test strong MACs configured
    run_test "Strong MACs Configured" "grep -q 'hmac-sha2-256-etm@openssh.com' /etc/ssh/sshd_config" "pass"
}

# Test Authentication and Access Control
test_authentication() {
    log_message "🔐 Testing Authentication and Access Control"
    echo "==========================================="
    
    # Test public key authentication enabled
    run_test "Public Key Authentication Enabled" "grep -q 'PubkeyAuthentication yes' /etc/ssh/sshd_config" "pass"
    
    # Test authorized_keys file exists
    run_test "Authorized Keys File Exists" "[ -f '$HOME/.ssh/authorized_keys' ]" "pass"
    
    # Test authorized_keys permissions
    run_test "Authorized Keys Permissions" "[ '$(stat -c %a $HOME/.ssh/authorized_keys)' = '600' ]" "pass"
    
    # Test SSH directory permissions
    run_test "SSH Directory Permissions" "[ '$(stat -c %a $HOME/.ssh)' = '700' ]" "pass"
    
    # Test user restrictions
    run_test "User Restrictions Configured" "grep -q 'AllowUsers ubuntu' /etc/ssh/sshd_config" "pass"
    
    # Test empty passwords denied
    run_test "Empty Passwords Denied" "grep -q 'PermitEmptyPasswords no' /etc/ssh/sshd_config" "pass"
}

# Test Firewall Configuration
test_firewall() {
    log_message "🔥 Testing Firewall Configuration"
    echo "================================="
    
    # Test UFW is active
    run_test "UFW Firewall Active" "sudo ufw status | grep -q 'Status: active'" "pass"
    
    # Test SSH port allowed
    SSH_PORT=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    run_test "SSH Port Allowed in Firewall" "sudo ufw status | grep -q '$SSH_PORT/tcp'" "pass"
    
    # Test default deny incoming
    run_test "Default Deny Incoming" "sudo ufw status verbose | grep -q 'Default: deny (incoming)'" "pass"
    
    # Test default allow outgoing
    run_test "Default Allow Outgoing" "sudo ufw status verbose | grep -q 'Default: allow (outgoing)'" "pass"
}

# Test fail2ban Configuration
test_fail2ban() {
    log_message "🛡️ Testing fail2ban Configuration"
    echo "================================="
    
    # Test fail2ban service is running
    run_test "fail2ban Service Running" "sudo systemctl is-active --quiet fail2ban" "pass"
    
    # Test SSH jail is active
    run_test "SSH Jail Active" "sudo fail2ban-client status sshd >/dev/null 2>&1" "pass"
    
    # Test fail2ban configuration exists
    run_test "fail2ban SSH Configuration Exists" "[ -f '/etc/fail2ban/jail.d/ssh-twintower.conf' ]" "pass"
    
    # Test custom fail2ban filters
    run_test "Custom fail2ban Filters Exist" "[ -f '/etc/fail2ban/filter.d/ssh-aggressive.conf' ]" "pass"
}

# Test SSH Connectivity
test_ssh_connectivity() {
    log_message "🔗 Testing SSH Connectivity"
    echo "==========================="
    
    SSH_PORT=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    
    # Test local SSH connection
    run_test "Local SSH Port Accessible" "timeout 5 bash -c '</dev/tcp/localhost/$SSH_PORT'" "pass"
    
    # Test SSH key authentication (if keys are configured)
    if [ -f "$HOME/.ssh/twintower_keys/twintower_master_ed25519" ]; then
        run_test "SSH Key Authentication Test" "ssh -o BatchMode=yes -o ConnectTimeout=5 -p $SSH_PORT localhost 'echo test' 2>/dev/null" "pass"
    fi
    
    # Test Tailscale SSH connectivity
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "$TAILSCALE_IP" ]; then
        run_test "Tailscale SSH Connectivity" "timeout 5 bash -c '</dev/tcp/$TAILSCALE_IP/$SSH_PORT'" "pass"
    fi
}

# Test SSH Logging
test_ssh_logging() {
    log_message "📊 Testing SSH Logging"
    echo "======================"
    
    # Test SSH log files exist
    run_test "SSH Log File Exists" "[ -f '/var/log/auth.log' ]" "pass"
    
    # Test custom SSH logging configuration
    run_test "Custom SSH Logging Config" "[ -f '/etc/rsyslog.d/50-ssh.conf' ]" "pass"
    
    # Test SSH detailed log exists
    run_test "SSH Detailed Log Exists" "[ -f '/var/log/ssh-detailed.log' ]" "pass"
    
    # Test logrotate configuration
    run_test "SSH Logrotate Config" "[ -f '/etc/logrotate.d/ssh-twintower' ]" "pass"
    
    # Test auditd is running
    run_test "Auditd Service Running" "sudo systemctl is-active --quiet auditd" "pass"
}

# Test SSH Security Features
test_ssh_security_features() {
    log_message "🔒 Testing SSH Security Features"
    echo "================================"
    
    # Test SSH banner exists
    run_test "SSH Banner Configured" "[ -f '/etc/ssh/banner' ]" "pass"
    
    # Test SSH command wrapper exists
    run_test "SSH Command Wrapper Exists" "[ -f '/usr/local/bin/ssh-command-wrapper.sh' ]" "pass"
    
    # Test SSH CA configuration (if advanced mode)
    if [ -f "/etc/ssh/ca/twintower_ca" ]; then
        run_test "SSH CA Key Exists" "[ -f '/etc/ssh/ca/twintower_ca' ]" "pass"
        run_test "SSH CA Trust Configured" "grep -q 'TrustedUserCAKeys' /etc/ssh/sshd_config" "pass"
    fi
    
    # Test SSH key restrictions
    if [ -f "$HOME/.ssh/authorized_keys" ]; then
        run_test "SSH Key Restrictions Applied" "grep -q 'no-agent-forwarding' $HOME/.ssh/authorized_keys" "pass"
    fi
}

# Test Security Vulnerabilities
test_security_vulnerabilities() {
    log_message "🚨 Testing Security Vulnerabilities"
    echo "==================================="
    
    # Test for weak SSH configurations
    run_test "Weak Ciphers Disabled" "! grep -q 'aes128-cbc' /etc/ssh/sshd_config" "pass"
    run_test "Weak MACs Disabled" "! grep -q 'hmac-sha1' /etc/ssh/sshd_config" "pass"
    run_test "Weak Key Exchange Disabled" "! grep -q 'diffie-hellman-group1-sha1' /etc/ssh/sshd_config" "pass"
    
    # Test for SSH protocol version
    run_test "SSH Protocol 2 Only" "grep -q 'Protocol 2' /etc/ssh/sshd_config" "pass"
    
    # Test for dangerous SSH settings
    run_test "Agent Forwarding Disabled" "grep -q 'AllowAgentForwarding no' /etc/ssh/sshd_config" "pass"
    run_test "Gateway Ports Disabled" "grep -q 'GatewayPorts no' /etc/ssh/sshd_config" "pass"
    run_test "Permit Tunnel Disabled" "grep -q 'PermitTunnel no' /etc/ssh/sshd_config" "pass"
}

# Performance Tests
test_ssh_performance() {
    log_message "⚡ Testing SSH Performance"
    echo "========================="
    
    SSH_PORT=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    
    # Test SSH connection speed
    echo "Testing SSH connection speed..."
    CONNECT_TIME=$(timeout 10 bash -c "time (echo > /dev/tcp/localhost/$SSH_PORT)" 2>&1 | grep real | awk '{print $2}' || echo "failed")
    
    if [ "$CONNECT_TIME" != "failed" ]; then
        echo -e "${GREEN}✅ SSH connection time: $CONNECT_TIME${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "fail2ban: ${RED}❌ Inactive${NC}"
    fi
    
    if sudo ufw status | grep -q "Status: active"; then
        echo -e "UFW Firewall: ${GREEN}✅ Active${NC}"
    else
        echo -e "UFW Firewall: ${RED}❌ Inactive${NC}"
    fi
    echo
    
    # Recent activity
    echo -e "${YELLOW}📈 Recent Activity${NC}"
    echo "------------------"
    echo "Last 5 SSH events:"
    sudo tail -n 5 /var/log/auth.log | grep sshd | cut -d' ' -f1-3,9- | while read line; do
        echo "  $line"
    done
    echo
    
    # Alerts
    if [ -f "$ALERT_LOG" ]; then
        local alert_count=$(sudo wc -l < "$ALERT_LOG" 2>/dev/null || echo "0")
        if [ "$alert_count" -gt 0 ]; then
            echo -e "${YELLOW}🚨 Recent Alerts${NC}"
            echo "---------------"
            sudo tail -n 3 "$ALERT_LOG" | while read line; do
                echo -e "  ${RED}$line${NC}"
            done
        fi
    fi
    
    echo -e "${BLUE}====================================${NC}"
    echo -e "${GREEN}✅ Dashboard updated: $(date)${NC}"
}

# Function to create real-time SSH monitor
realtime_ssh_monitor() {
    log_message "📊 Starting real-time SSH monitoring..."
    
    echo -e "${BLUE}🔍 Real-time SSH Monitor${NC}"
    echo -e "${BLUE}Press Ctrl+C to stop${NC}"
    echo -e "${BLUE}========================${NC}"
    
    # Monitor SSH auth log in real-time
    sudo tail -f /var/log/auth.log | grep --line-buffered sshd | while read line; do
        timestamp=$(echo "$line" | awk '{print $1, $2, $3}')
        
        if echo "$line" | grep -q "Accepted publickey"; then
            user=$(echo "$line" | awk '{print $9}')
            ip=$(echo "$line" | awk '{print $11}')
            echo -e "${GREEN}✅ $timestamp - Successful login: $user from $ip${NC}"
        elif echo "$line" | grep -q "Failed password"; then
            user=$(echo "$line" | awk '{print $9}')
            ip=$(echo "$line" | awk '{print $11}')
            echo -e "${RED}❌ $timestamp - Failed login: $user from $ip${NC}"
        elif echo "$line" | grep -q "Invalid user"; then
            user=$(echo "$line" | awk '{print $10}')
            ip=$(echo "$line" | awk '{print $12}')
            echo -e "${YELLOW}⚠️  $timestamp - Invalid user: $user from $ip${NC}"
        elif echo "$line" | grep -q "Connection closed"; then
            ip=$(echo "$line" | awk '{print $12}')
            echo -e "${BLUE}🔌 $timestamp - Connection closed from $ip${NC}"
        fi
    done
}

# Function to start monitoring daemon
start_monitoring_daemon() {
    log_message "🚀 Starting SSH monitoring daemon..."
    
    while true; do
        monitor_ssh_connections
        monitor_ssh_health
        
        # Generate dashboard every 10 cycles
        if [ $(($(date +%s) / $MONITOR_INTERVAL % 10)) -eq 0 ]; then
            generate_ssh_dashboard > /tmp/ssh_dashboard_latest.txt
        fi
        
        # Generate analysis every hour
        if [ $(($(date +%s) / $MONITOR_INTERVAL % 60)) -eq 0 ]; then
            analyze_ssh_logs
        fi
        
        sleep "$MONITOR_INTERVAL"
    done
}

# Function to create SSH log rotation
setup_log_rotation() {
    log_message "🔄 Setting up SSH log rotation..."
    
    cat << LOGROTATE_EOF | sudo tee /etc/logrotate.d/ssh-monitoring
/var/log/ssh-monitor.log
/var/log/ssh-alerts.log
/var/log/ssh-stats.log
{
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
LOGROTATE_EOF

    log_message "✅ SSH log rotation configured"
}

# Function to create SSH monitoring alerts
setup_monitoring_alerts() {
    log_message "📧 Setting up SSH monitoring alerts..."
    
    # Create alert script
    cat << ALERT_EOF | sudo tee /usr/local/bin/ssh-alert.sh
#!/bin/bash

# TwinTower SSH Alert Script
ALERT_TYPE="\$1"
ALERT_MESSAGE="\$2"
ALERT_LOG="/var/log/ssh-alerts.log"

# Log alert
echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$ALERT_TYPE: \$ALERT_MESSAGE" >> "\$ALERT_LOG"

# Send email alert (if configured)
if [ -f "/etc/ssh-monitor.conf" ]; then
    source /etc/ssh-monitor.conf
    if [ "\$ENABLE_EMAIL_ALERTS" = "true" ]; then
        echo "\$ALERT_MESSAGE" | mail -s "SSH Alert: \$ALERT_TYPE" "\$EMAIL_RECIPIENT"
    fi
fi

# Send Slack alert (if configured)
if [ -f "/etc/ssh-monitor.conf" ]; then
    source /etc/ssh-monitor.conf
    if [ "\$ENABLE_SLACK_ALERTS" = "true" ] && [ -n "\$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"SSH Alert: \$ALERT_TYPE - \$ALERT_MESSAGE\"}" \
            "\$SLACK_WEBHOOK_URL"
    fi
fi
ALERT_EOF

    sudo chmod +x /usr/local/bin/ssh-alert.sh
    log_message "✅ SSH monitoring alerts configured"
}

# Function to create SSH statistics reporter
create_stats_reporter() {
    log_message "📊 Creating SSH statistics reporter..."
    
    cat << STATS_EOF > ~/ssh_stats_reporter.sh
#!/bin/bash

# TwinTower SSH Statistics Reporter
set -e

REPORT_TYPE="\${1:-daily}"
STATS_LOG="/var/log/ssh-stats.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

generate_daily_report() {
    echo -e "\${BLUE}📊 SSH Daily Statistics Report\${NC}"
    echo -e "\${BLUE}Date: \$(date '+%Y-%m-%d')\${NC}"
    echo -e "\${BLUE}==============================\${NC}"
    echo
    
    # Parse statistics from log
    if [ -f "\$STATS_LOG" ]; then
        local today=\$(date '+%Y-%m-%d')
        local stats_today=\$(grep "\$today" "\$STATS_LOG")
        
        if [ -n "\$stats_today" ]; then
            echo -e "\${YELLOW}Connection Statistics:\${NC}"
            echo "\$stats_today" | tail -1 | cut -d',' -f2- | tr ',' '\n' | while read stat; do
                echo "  \$stat"
            done
            echo
            
            # Calculate averages
            local avg_connections=\$(echo "\$stats_today" | awk -F',' '{sum+=\$2; count++} END {print sum/count}')
            local total_failed=\$(echo "\$stats_today" | awk -F',' '{sum+=\$3} END {print sum}')
            local total_successful=\$(echo "\$stats_today" | awk -F',' '{sum+=\$4} END {print sum}')
            
            echo -e "\${YELLOW}Daily Totals:\${NC}"
            echo "  Average Active Connections: \$avg_connections"
            echo "  Total Failed Attempts: \$total_failed"
            echo "  Total Successful Logins: \$total_successful"
        else
            echo "No statistics available for today"
        fi
    else
        echo "Statistics log not found"
    fi
    
    echo
    echo -e "\${GREEN}✅ Daily report generated\${NC}"
}

generate_weekly_report() {
    echo -e "\${BLUE}📊 SSH Weekly Statistics Report\${NC}"
    echo -e "\${BLUE}Week ending: \$(date '+%Y-%m-%d')\${NC}"
    echo -e "\${BLUE}===============================\${NC}"
    echo
    
    # Generate weekly statistics
    local week_start=\$(date -d '7 days ago' '+%Y-%m-%d')
    
    if [ -f "\$STATS_LOG" ]; then
        local stats_week=\$(awk -v start="\$week_start" '\$1 >= start' "\$STATS_LOG")
        
        if [ -n "\$stats_week" ]; then
            echo -e "\${YELLOW}Weekly Summary:\${NC}"
            local total_failed=\$(echo "\$stats_week" | awk -F',' '{sum+=\$3} END {print sum}')
            local total_successful=\$(echo "\$stats_week" | awk -F',' '{sum+=\$4} END {print sum}')
            local avg_connections=\$(echo "\$stats_week" | awk -F',' '{sum+=\$2; count++} END {print sum/count}')
            
            echo "  Total Failed Attempts: \$total_failed"
            echo "  Total Successful Logins: \$total_successful"
            echo "  Average Active Connections: \$avg_connections"
            
            # Calculate success rate
            local total_attempts=\$((total_failed + total_successful))
            if [ \$total_attempts -gt 0 ]; then
                local success_rate=\$(echo "scale=2; \$total_successful * 100 / \$total_attempts" | bc)
                echo "  Success Rate: \$success_rate%"
            fi
        else
            echo "No statistics available for this week"
        fi
    else
        echo "Statistics log not found"
    fi
    
    echo
    echo -e "\${GREEN}✅ Weekly report generated\${NC}"
}

case "\$REPORT_TYPE" in
    "daily")
        generate_daily_report
        ;;
    "weekly")
        generate_weekly_report
        ;;
    *)
        echo "Usage: \$0 <daily|weekly>"
        exit 1
        ;;
esac
STATS_EOF

    chmod +x ~/ssh_stats_reporter.sh
    log_message "✅ SSH statistics reporter created"
}

# Main execution
main() {
    echo -e "${BLUE}📊 TwinTower SSH Monitoring System${NC}"
    echo -e "${BLUE}Action: $ACTION${NC}"
    echo -e "${BLUE}===================================${NC}"
    
    case "$ACTION" in
        "setup")
            setup_monitoring
            setup_log_rotation
            setup_monitoring_alerts
            create_stats_reporter
            ;;
        "start")
            sudo systemctl enable ssh-monitor.service
            sudo systemctl start ssh-monitor.service
            echo -e "${GREEN}✅ SSH monitoring service started${NC}"
            ;;
        "stop")
            sudo systemctl stop ssh-monitor.service
            sudo systemctl disable ssh-monitor.service
            echo -e "${GREEN}✅ SSH monitoring service stopped${NC}"
            ;;
        "status")
            sudo systemctl status ssh-monitor.service
            ;;
        "daemon")
            start_monitoring_daemon
            ;;
        "dashboard")
            generate_ssh_dashboard
            ;;
        "realtime")
            realtime_ssh_monitor
            ;;
        "analyze")
            analyze_ssh_logs
            ;;
        "report")
            ~/ssh_stats_reporter.sh daily
            ;;
        *)
            echo "Usage: $0 <setup|start|stop|status|daemon|dashboard|realtime|analyze|report>"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
EOF

chmod +x ~/ssh_monitoring_system.sh
```

### **Step 2: Setup SSH Monitoring**

```bash
# Setup monitoring infrastructure
./ssh_monitoring_system.sh setup

# Start monitoring service
./ssh_monitoring_system.sh start

# View real-time dashboard
./ssh_monitoring_system.sh dashboard
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🔄 **Backup & Recovery**

### **Step 1: Create SSH Configuration Backup System**

```bash
cat > ~/backup_ssh_config.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Configuration Backup System
# Section 5B: SSH Hardening & Port Configuration

set -e

BACKUP_TYPE="${1:-full}"
BACKUP_DIR="/home/$(whoami)/ssh_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TOWER_NAME="$(hostname)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to create backup directories
create_backup_dirs() {
    log_message "📁 Creating backup directories..."
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/configs"
    mkdir -p "$BACKUP_DIR/keys"
    mkdir -p "$BACKUP_DIR/logs"
    mkdir -p "$BACKUP_DIR/scripts"
    
    log_message "✅ Backup directories created"
}

# Function to backup SSH configurations
backup_ssh_configs() {
    log_message "⚙️ Backing up SSH configurations..."
    
    local config_backup="$BACKUP_DIR/configs/ssh_config_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    
    # Create temporary directory for configs
    local temp_dir=$(mktemp -d)
    local config_dir="$temp_dir/ssh_configs"
    mkdir -p "$config_dir"
    
    # Copy SSH daemon configuration
    sudo cp /etc/ssh/sshd_config "$config_dir/"
    
    # Copy SSH client configuration
    if [ -f "$HOME/.ssh/config" ]; then
        cp "$HOME/.ssh/config" "$config_dir/client_config"
    fi
    
    # Copy SSH banner
    if [ -f "/etc/ssh/banner" ]; then
        sudo cp /etc/ssh/banner "$config_dir/"
    fi
    
    # Copy fail2ban configurations
    if [ -d "/etc/fail2ban/jail.d" ]; then
        sudo cp -r /etc/fail2ban/jail.d "$config_dir/"
    fi
    
    # Copy UFW rules
    if [ -f "/etc/ufw/user.rules" ]; then
        sudo cp /etc/ufw/user.rules "$config_dir/"
    fi
    
    # Copy systemd overrides
    if [ -d "/etc/systemd/system/ssh.service.d" ]; then
        sudo cp -r /etc/systemd/system/ssh.service.d "$config_dir/"
    fi
    
    # Copy monitoring configurations
    if [ -f "/etc/ssh-monitor.conf" ]; then
        sudo cp /etc/ssh-monitor.conf "$config_dir/"
    fi
    
    # Create configuration backup
    cd "$temp_dir"
    tar -czf "$config_backup" ssh_configs/
    
    # Set proper permissions
    chmod 600 "$config_backup"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH configurations backed up: $config_backup"
}

# Function to backup SSH keys
backup_ssh_keys() {
    log_message "🔑 Backing up SSH keys..."
    
    local keys_backup="$BACKUP_DIR/keys/ssh_keys_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    
    # Create temporary directory for keys
    local temp_dir=$(mktemp -d)
    local keys_dir="$temp_dir/ssh_keys"
    mkdir -p "$keys_dir"
    
    # Copy host keys
    sudo cp -r /etc/ssh/ssh_host_* "$keys_dir/" 2>/dev/null || true
    
    # Copy user keys
    if [ -d "$HOME/.ssh" ]; then
        cp -r "$HOME/.ssh" "$keys_dir/user_ssh/"
    fi
    
    # Copy SSH CA keys (if they exist)
    if [ -d "/etc/ssh/ca" ]; then
        sudo cp -r /etc/ssh/ca "$keys_dir/"
    fi
    
    # Create keys backup
    cd "$temp_dir"
    tar -czf "$keys_backup" ssh_keys/
    
    # Set proper permissions
    chmod 600 "$keys_backup"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH keys backed up: $keys_backup"
}

# Function to backup SSH logs
backup_ssh_logs() {
    log_message "📊 Backing up SSH logs..."
    
    local logs_backup="$BACKUP_DIR/logs/ssh_logs_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    
    # Create temporary directory for logs
    local temp_dir=$(mktemp -d)
    local logs_dir="$temp_dir/ssh_logs"
    mkdir -p "$logs_dir"
    
    # Copy SSH-related logs
    sudo cp /var/log/auth.log "$logs_dir/" 2>/dev/null || true
    sudo cp /var/log/ssh.log "$logs_dir/" 2>/dev/null || true
    sudo cp /var/log/ssh-detailed.log "$logs_dir/" 2>/dev/null || true
    sudo cp /var/log/ssh-monitor.log "$logs_dir/" 2>/dev/null || true
    sudo cp /var/log/ssh-alerts.log "$logs_dir/" 2>/dev/null || true
    sudo cp /var/log/ssh-stats.log "$logs_dir/" 2>/dev/null || true
    
    # Copy fail2ban logs
    sudo cp /var/log/fail2ban.log "$logs_dir/" 2>/dev/null || true
    
    # Create logs backup
    cd "$temp_dir"
    tar -czf "$logs_backup" ssh_logs/
    
    # Set proper permissions
    chmod 600 "$logs_backup"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH logs backed up: $logs_backup"
}

# Function to backup SSH scripts
backup_ssh_scripts() {
    log_message "📋 Backing up SSH scripts..."
    
    local scripts_backup="$BACKUP_DIR/scripts/ssh_scripts_${TOWER_NAME}_${TIMESTAMP}.tar.gz"
    
    # Create temporary directory for scripts
    local temp_dir=$(mktemp -d)
    local scripts_dir="$temp_dir/ssh_scripts"
    mkdir -p "$scripts_dir"
    
    # Copy management scripts
    cp ~/ssh_key_manager.sh "$scripts_dir/" 2>/dev/null || true
    cp ~/ssh_hardening.sh "$scripts_dir/" 2>/dev/null || true
    cp ~/configure_ssh_ports.sh "$scripts_dir/" 2>/dev/null || true
    cp ~/setup_ssh_auth.sh "$scripts_dir/" 2>/dev/null || true
    cp ~/test_ssh_security.sh "$scripts_dir/" 2>/dev/null || true
    cp ~/ssh_monitoring_system.sh "$scripts_dir/" 2>/dev/null || true
    cp ~/backup_ssh_config.sh "$scripts_dir/" 2>/dev/null || true
    
    # Copy system scripts
    sudo cp /usr/local/bin/ssh-command-wrapper.sh "$scripts_dir/" 2>/dev/null || true
    sudo cp /usr/local/bin/ssh-alert.sh "$scripts_dir/" 2>/dev/null || true
    
    # Create scripts backup
    cd "$temp_dir"
    tar -czf "$scripts_backup" ssh_scripts/
    
    # Set proper permissions
    chmod 600 "$scripts_backup"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH scripts backed up: $scripts_backup"
}

# Function to create backup manifest
create_backup_manifest() {
    log_message "📋 Creating backup manifest..."
    
    local manifest_file="$BACKUP_DIR/backup_manifest_${TOWER_NAME}_${TIMESTAMP}.txt"
    
    cat > "$manifest_file" << MANIFEST_EOF
TwinTower SSH Configuration Backup Manifest
==========================================
Backup Date: $(date)
Tower Name: $TOWER_NAME
Backup Type: $BACKUP_TYPE
Backup Directory: $BACKUP_DIR

System Information:
------------------
Hostname: $(hostname)
OS Version: $(lsb_release -d | cut -f2)
SSH Version: $(ssh -V 2>&1)
Kernel Version: $(uname -r)
Tailscale Version: $(tailscale version | head -1)

SSH Configuration:
-----------------
SSH Port: $(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
SSH Service Status: $(sudo systemctl is-active ssh)
fail2ban Status: $(sudo systemctl is-active fail2ban 2>/dev/null || echo "Not installed")
UFW Status: $(sudo ufw status | head -1)

Backup Files:
------------
$(ls -la "$BACKUP_DIR"/*/*/*${TIMESTAMP}* 2>/dev/null || echo "No backup files found")

Verification:
------------
$(find "$BACKUP_DIR" -name "*${TIMESTAMP}*" -type f -exec sh -c 'echo "File: $1, Size: $(stat -c%s "$1"), MD5: $(md5sum "$1" | cut -d" " -f1)"' _ {} \;)

Recovery Instructions:
---------------------
1. Extract configuration backup: tar -xzf ssh_config_${TOWER_NAME}_${TIMESTAMP}.tar.gz
2. Extract keys backup: tar -xzf ssh_keys_${TOWER_NAME}_${TIMESTAMP}.tar.gz
3. Extract logs backup: tar -xzf ssh_logs_${TOWER_NAME}_${TIMESTAMP}.tar.gz
4. Extract scripts backup: tar -xzf ssh_scripts_${TOWER_NAME}_${TIMESTAMP}.tar.gz
5. Run restoration script: ./restore_ssh_config.sh

Notes:
------
- Always test SSH connectivity before fully committing to restored configuration
- Keep at least 3 backup copies in different locations
- Verify backup integrity before relying on them for recovery
- Update backup documentation when configuration changes

MANIFEST_EOF

    log_message "✅ Backup manifest created: $manifest_file"
}

# Function to cleanup old backups
cleanup_old_backups() {
    log_message "🧹 Cleaning up old backups..."
    
    # Keep last 10 backups of each type
    find "$BACKUP_DIR/configs" -name "ssh_config_${TOWER_NAME}_*.tar.gz" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true
    find "$BACKUP_DIR/keys" -name "ssh_keys_${TOWER_NAME}_*.tar.gz" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true
    find "$BACKUP_DIR/logs" -name "ssh_logs_${TOWER_NAME}_*.tar.gz" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true
    find "$BACKUP_DIR/scripts" -name "ssh_scripts_${TOWER_NAME}_*.tar.gz" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true
    
    # Keep last 30 manifest files
    find "$BACKUP_DIR" -name "backup_manifest_${TOWER_NAME}_*.txt" -type f | sort -r | tail -n +31 | xargs rm -f 2>/dev/null || true
    
    log_message "✅ Old backups cleaned up"
}

# Function to create automated backup service
create_backup_service() {
    log_message "⚙️ Creating automated backup service..."
    
    # Create backup service
    cat << SERVICE_EOF | sudo tee /etc/systemd/system/ssh-backup.service
[Unit]
Description=TwinTower SSH Configuration Backup Service
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/home/$(whoami)/backup_ssh_config.sh automated
StandardOutput=journal
StandardError=journal
SERVICE_EOF

    # Create backup timer
    cat << TIMER_EOF | sudo tee /etc/systemd/system/ssh-backup.timer
[Unit]
Description=Run TwinTower SSH Backup Daily
Requires=ssh-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ssh-backup.timer
    sudo systemctl start ssh-backup.timer
    
    log_message "✅ Automated backup service created"
}

# Main execution
main() {
    echo -e "${BLUE}💾 TwinTower SSH Configuration Backup${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME, Type: $BACKUP_TYPE${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    create_backup_dirs
    
    case "$BACKUP_TYPE" in
        "configs")
            backup_ssh_configs
            ;;
        "keys")
            backup_ssh_keys
            ;;
        "logs")
            backup_ssh_logs
            ;;
        "scripts")
            backup_ssh_scripts
            ;;
        "full")
            backup_ssh_configs
            backup_ssh_keys
            backup_ssh_logs
            backup_ssh_scripts
            create_backup_manifest
            cleanup_old_backups
            ;;
        "automated")
            backup_ssh_configs
            backup_ssh_keys
            create_backup_manifest
            cleanup_old_backups
            ;;
        "service")
            create_backup_service
            ;;
        *)
            echo "Usage: $0 <configs|keys|logs|scripts|full|automated|service>"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}🎉 SSH backup completed successfully!${NC}"
    echo -e "${YELLOW}📁 Backup location: $BACKUP_DIR${NC}"
}

# Execute main function
main "$@"
EOF

chmod +x ~/backup_ssh_config.sh
```

### **Step 2: Create SSH Configuration Restoration Script**

```bash
cat > ~/restore_ssh_config.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Configuration Restoration Script
set -e

BACKUP_FILE="${1}"
RESTORE_TYPE="${2:-configs}"
BACKUP_DIR="/home/$(whoami)/ssh_backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to display available backups
show_available_backups() {
    echo -e "${YELLOW}📁 Available SSH backups:${NC}"
    echo "=========================="
    
    echo -e "${BLUE}Configuration Backups:${NC}"
    ls -la "$BACKUP_DIR/configs/"*.tar.gz 2>/dev/null | tail -10 || echo "No configuration backups found"
    
    echo -e "${BLUE}Key Backups:${NC}"
    ls -la "$BACKUP_DIR/keys/"*.tar.gz 2>/dev/null | tail -10 || echo "No key backups found"
    
    echo -e "${BLUE}Log Backups:${NC}"
    ls -la "$BACKUP_DIR/logs/"*.tar.gz 2>/dev/null | tail -10 || echo "No log backups found"
    
    echo -e "${BLUE}Script Backups:${NC}"
    ls -la "$BACKUP_DIR/scripts/"*.tar.gz 2>/dev/null | tail -10 || echo "No script backups found"
}

# Function to restore SSH configurations
restore_ssh_configs() {
    local backup_file="$1"
    
    log_message "⚙️ Restoring SSH configurations from: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        log_message "❌ Backup file not found: $backup_file"
        return 1
    fi
    
    # Stop SSH service
    log_message "🛑 Stopping SSH service..."
    sudo systemctl stop ssh
    
    # Create temporary restore directory
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    # Extract backup
    tar -xzf "$backup_file"
    
    # Restore configurations
    if [ -f "ssh_configs/sshd_config" ]; then
        log_message "📄 Restoring SSH daemon configuration..."
        sudo cp ssh_configs/sshd_config /etc/ssh/
        sudo chmod 644 /etc/ssh/sshd_config
    fi
    
    if [ -f "ssh_configs/client_config" ]; then
        log_message "📄 Restoring SSH client configuration..."
        mkdir -p "$HOME/.ssh"
        cp ssh_configs/client_config "$HOME/.ssh/config"
        chmod 600 "$HOME/.ssh/config"
    fi
    
    if [ -f "ssh_configs/banner" ]; then
        log_message "📄 Restoring SSH banner..."
        sudo cp ssh_configs/banner /etc/ssh/
        sudo chmod 644 /etc/ssh/banner
    fi
    
    if [ -d "ssh_configs/jail.d" ]; then
        log_message "📄 Restoring fail2ban configurations..."
        sudo cp -r ssh_configs/jail.d/* /etc/fail2ban/jail.d/
    fi
    
    if [ -f "ssh_configs/user.rules" ]; then
        log_message "📄 Restoring UFW rules..."
        sudo cp ssh_configs/user.rules /etc/ufw/
        sudo ufw reload
    fi
    
    if [ -d "ssh_configs/ssh.service.d" ]; then
        log_message "📄 Restoring systemd overrides..."
        sudo cp -r ssh_configs/ssh.service.d /etc/systemd/system/
        sudo systemctl daemon-reload
    fi
    
    # Test SSH configuration
    log_message "🧪 Testing SSH configuration..."
    if sudo sshd -t; then
        log_message "✅ SSH configuration is valid"
    else
        log_message "❌ SSH configuration has errors"
        return 1
    fi
    
    # Start SSH service
    log_message "🚀 Starting SSH service..."
    sudo systemctl start ssh
    
    # Verify SSH service is running
    if sudo systemctl is-active --quiet ssh; then
        log_message "✅ SSH service restored successfully"
    else
        log_message "❌ SSH service failed to start"
        return 1
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH configuration restoration completed"
}

# Function to restore SSH keys
restore_ssh_keys() {
    local backup_file="$1"
    
    log_message "🔑 Restoring SSH keys from: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        log_message "❌ Backup file not found: $backup_file"
        return 1
    fi
    
    # Create temporary restore directory
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    # Extract backup
    tar -xzf "$backup_file"
    
    # Restore host keys
    if [ -f "ssh_keys/ssh_host_rsa_key" ]; then
        log_message "🔑 Restoring SSH host keys..."
        sudo cp ssh_keys/ssh_host_* /etc/ssh/
        sudo chmod 600 /etc/ssh/ssh_host_*
        sudo chmod 644 /etc/ssh/ssh_host_*.pub
    fi
    
    # Restore user keys
    if [ -d "ssh_keys/user_ssh" ]; then
        log_message "🔑 Restoring user SSH keys..."
        cp -r ssh_keys/user_ssh/.ssh "$HOME/"
        chmod 700 "$HOME/.ssh"
        chmod 600 "$HOME/.ssh"/* 2>/dev/null || true
        chmod 644 "$HOME/.ssh"/*.pub 2>/dev/null || true
    fi
    
    # Restore SSH CA keys
    if [ -d "ssh_keys/ca" ]; then
        log_message "🔑 Restoring SSH CA keys..."
        sudo cp -r ssh_keys/ca /etc/ssh/
        sudo chmod 600 /etc/ssh/ca/*
        sudo chmod 644 /etc/ssh/ca/*.pub
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH key restoration completed"
}

# Function to restore SSH logs
restore_ssh_logs() {
    local backup_file="$1"
    
    log_message "📊 Restoring SSH logs from: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        log_message "❌ Backup file not found: $backup_file"
        return 1
    fi
    
    # Create temporary restore directory
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    # Extract backup
    tar -xzf "$backup_file"
    
    # Restore logs (be careful not to overwrite current logs)
    if [ -d "ssh_logs" ]; then
        log_message "📊 Restoring SSH logs to /var/log/restored/..."
        sudo mkdir -p /var/log/restored
        sudo cp ssh_logs/* /var/log/restored/
        sudo chmod 640 /var/log/restored/*
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH log restoration completed"
}

# Function to restore SSH scripts
restore_ssh_scripts() {
    local backup_file="$1"
    
    log_message "📋 Restoring SSH scripts from: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        log_message "❌ Backup file not found: $backup_file"
        return 1
    fi
    
    # Create temporary restore directory
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    # Extract backup
    tar -xzf "$backup_file"
    
    # Restore user scripts
    if [ -d "ssh_scripts" ]; then
        log_message "📋 Restoring SSH management scripts..."
        cp ssh_scripts/ssh_*.sh "$HOME/" 2>/dev/null || true
        chmod +x "$HOME"/ssh_*.sh 2>/dev/null || true
    fi
    
    # Restore system scripts
    if [ -f "ssh_scripts/ssh-command-wrapper.sh" ]; then
        log_message "📋 Restoring SSH command wrapper..."
        sudo cp ssh_scripts/ssh-command-wrapper.sh /usr/local/bin/
        sudo chmod +x /usr/local/bin/ssh-command-wrapper.sh
    fi
    
    if [ -f "ssh_scripts/ssh-alert.sh" ]; then
        log_message "📋 Restoring SSH alert script..."
        sudo cp ssh_scripts/ssh-alert.sh /usr/local/bin/
        sudo chmod +x /usr/local/bin/ssh-alert.sh
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_message "✅ SSH script restoration completed"
}

# Function to perform emergency restoration
emergency_restore() {
    log_message "🚨 Performing emergency SSH restoration..."
    
    # Find the most recent backup
    local recent_config=$(ls -t "$BACKUP_DIR/configs/"*.tar.gz 2>/dev/null | head -1)
    local recent_keys=$(ls -t "$BACKUP_DIR/keys/"*.tar.gz 2>/dev/null | head -1)
    
    if [ -z "$recent_config" ]; then
        log_message "❌ No configuration backup found for emergency restore"
        return 1
    fi
    
    log_message "🔄 Using most recent backups:"
    log_message "  Config: $recent_config"
    log_message "  Keys: $recent_keys"
    
    # Restore configurations
    restore_ssh_configs "$recent_config"
    
    # Restore keys if available
    if [ -n "$recent_keys" ]; then
        restore_ssh_keys "$recent_keys"
    fi
    
    log_message "✅ Emergency restoration completed"
}

# Function to verify restored configuration
verify_restoration() {
    log_message "🔍 Verifying restored SSH configuration..."
    
    # Check SSH service
    if sudo systemctl is-active --quiet ssh; then
        log_message "✅ SSH service is running"
    else
        log_message "❌ SSH service is not running"
        return 1
    fi
    
    # Check SSH configuration
    if sudo sshd -t; then
        log_message "✅ SSH configuration is valid"
    else
        log_message "❌ SSH configuration has errors"
        return 1
    fi
    
    # Check SSH connectivity
    local ssh_port=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    if timeout 5 bash -c "</dev/tcp/localhost/$ssh_port"; then
        log_message "✅ SSH port $ssh_port is accessible"
    else
        log_message "❌ SSH port $ssh_port is not accessible"
        return 1
    fi
    
    # Check key permissions
    if [ -f "$HOME/.ssh/authorized_keys" ]; then
        local perms=$(stat -c %a "$HOME/.ssh/authorized_keys")
        if [ "$perms" = "600" ]; then
            log_message "✅ SSH key permissions are correct"
        else
            log_message "⚠️  SSH key permissions need adjustment"
            chmod 600 "$HOME/.ssh/authorized_keys"
        fi
    fi
    
    log_message "✅ Restoration verification completed"
}

# Main execution
main() {
    echo -e "${BLUE}🔄 TwinTower SSH Configuration Restoration${NC}"
    echo -e "${BLUE}===========================================${NC}"
    
    if [ -z "$BACKUP_FILE" ]; then
        show_available_backups
        echo
        echo "Usage: $0 <backup_file> <configs|keys|logs|scripts|full|emergency>"
        echo
        echo "Examples:"
        echo "  $0 /path/to/ssh_config_backup.tar.gz configs"
        echo "  $0 emergency"
        exit 1
    fi
    
    case "$RESTORE_TYPE" in
        "configs")
            restore_ssh_configs "$BACKUP_FILE"
            ;;
        "keys")
            restore_ssh_keys "$BACKUP_FILE"
            ;;
        "logs")
            restore_ssh_logs "$BACKUP_FILE"
            ;;
        "scripts")
            restore_ssh_scripts "$BACKUP_FILE"
            ;;
        "full")
            # Restore all components
            restore_ssh_configs "$BACKUP_FILE"
            restore_ssh_keys "$BACKUP_FILE"
            restore_ssh_scripts "$BACKUP_FILE"
            ;;
        "emergency")
            emergency_restore
            ;;
        *)
            echo "Invalid restore type: $RESTORE_TYPE"
            echo "Usage: $0 <backup_file> <configs|keys|logs|scripts|full|emergency>"
            exit 1
            ;;
    esac
    
    # Verify restoration
    verify_restoration
    
    echo -e "${GREEN}🎉 SSH configuration restoration completed!${NC}"
    echo -e "${YELLOW}📋 Important: Test SSH connectivity before closing current session${NC}"
    echo -e "${YELLOW}📋 Command: ssh -p $(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1) localhost${NC}"
}

# Execute main function
main "$@"
EOF

chmod +x ~/restore_ssh_config.sh
```

### **Step 3: Setup Automated Backup System**

```bash
# Create automated backup service
./backup_ssh_config.sh service

# Create a full backup now
./backup_ssh_config.sh full

# Test restoration (dry run)
echo "Testing restoration with most recent backup..."
RECENT_BACKUP=$(ls -t ~/ssh_backups/configs/*.tar.gz | head -1)
if [ -n "$RECENT_BACKUP" ]; then
    echo "Most recent backup: $RECENT_BACKUP"
    echo "To restore: ./restore_ssh_config.sh '$RECENT_BACKUP' configs"
fi
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🚀 **Next Steps**

### **Section 5B Completion Checklist**

Verify the following before proceeding to Section 5C:

- ✅ **SSH hardening configuration** applied on all towers
- ✅ **Custom port configuration** (2122/2222/2322) working
- ✅ **Key-based authentication** configured and tested
- ✅ **SSH security policies** implemented and verified
- ✅ **Monitoring and logging** system operational
- ✅ **Backup and recovery** system configured
- ✅ **Security testing** completed successfully

### **Quick Verification Commands**

```bash
# Final verification script
cat > ~/verify_section_5b.sh << 'EOF'
#!/bin/bash

echo "🔍 Section 5B Final Verification"
echo "================================="

# Check SSH service and port
SSH_PORT=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
echo "1. SSH Service & Port:"
sudo systemctl is-active ssh && echo "✅ SSH Running on port $SSH_PORT" || echo "❌ SSH Not running"

# Check SSH hardening
echo "2. SSH Hardening:"
grep -q "PasswordAuthentication no" /etc/ssh/sshd_config && echo "✅ Password auth disabled" || echo "❌ Password auth enabled"
grep -q "PermitRootLogin no" /etc/ssh/sshd_config && echo "✅ Root login disabled" || echo "❌ Root login enabled"

# Check SSH keys
echo "3. SSH Keys:"
[ -f "$HOME/.ssh/authorized_keys" ] && echo "✅ SSH keys configured" || echo "❌ SSH keys missing"

# Check firewall
echo "4. Firewall:"
sudo ufw status | grep -q "Status: active" && echo "✅ UFW active" || echo "❌ UFW inactive"

# Check fail2ban
echo "5. fail2ban:"
sudo systemctl is-active fail2ban && echo "✅ fail2ban active" || echo "❌ fail2ban inactive"

# Check monitoring
echo "6. Monitoring:"
[ -f "/var/log/ssh-monitor.log" ] && echo "✅ SSH monitoring configured" || echo "❌ SSH monitoring missing"

# Check backups
echo "7. Backups:"
[ -d "$HOME/ssh_backups" ] && echo "✅ Backup system configured" || echo "❌ Backup system missing"

echo "================================="
echo "✅ Section 5B verification complete!"
EOF

chmod +x ~/verify_section_5b.sh
./verify_section_5b.sh
```

### **SSH Connection Testing**

Test SSH connectivity with the new configuration:

```bash
# Test SSH connectivity between towers
SSH_PORT=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)

# Test local connection
ssh -p $SSH_PORT localhost

# Test Tailscale connections
ssh twinover1-worker  # Should use port 2122
ssh twinover2-worker  # Should use port 2222
ssh twinover3-primary # Should use port 2322
```

### **Security Dashboard Access**

Access your SSH security tools:

```bash
# SSH Security Dashboard
./ssh_security_dashboard.sh

# Real-time monitoring
./ssh_monitoring_system.sh realtime

# Security testing
./test_ssh_security.sh $(hostname) full

# View recent activity
./ssh_stats_reporter.sh daily
```

### **Preparing for Section 5C**

Section 5C will focus on **Firewall & Access Control** to complete your network security implementation.

**Expected outcomes for Section 5C:**
- 🔥 Advanced UFW firewall configuration
- 🌐 Network segmentation and access controls
- 🛡️ Intrusion detection and prevention
- 📊 Network traffic monitoring
- 🔒 Zero-trust network policies

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📝 **Section 5B Summary**

**What was accomplished:**
- ✅ **SSH hardening** with enterprise-grade security policies
- ✅ **Custom port configuration** (2122/2222/2322) for each tower
- ✅ **Key-based authentication** with centralized key management
- ✅ **Advanced access controls** with command restrictions
- ✅ **Comprehensive monitoring** and logging system
- ✅ **Automated backup** and recovery system
- ✅ **Security testing** and vulnerability assessment tools

**Security Architecture Created:**
```
Remote Access ←→ Tailscale Mesh ←→ Hardened SSH ←→ TwinTower Infrastructure
                                        ↓
    ┌─────────────────────────────────────────────────────────────────────┐
    │  🔐 Port 2122         🔐 Port 2222         🔐 Port 2322           │
    │  TwinTower1           TwinTower2           TwinTower3               │
    │  • Key Auth           • Key Auth           • Key Auth               │
    │  • fail2ban           • fail2ban           • fail2ban               │
    │  • Monitoring         • Monitoring         • Monitoring             │
    │  • Backup             • Backup             • Backup                 │
    └─────────────────────────────────────────────────────────────────────┘
```

**Management Tools Created:**
- `ssh_security_dashboard.sh` - Real-time security monitoring
- `test_ssh_security.sh` - Comprehensive security testing
- `ssh_monitoring_system.sh` - Automated monitoring and alerting
- `backup_ssh_config.sh` - Configuration backup system
- `restore_ssh_config.sh` - Emergency recovery system

**Ready for Section 5C:** Firewall & Access Control

**[⬆️ Back to TOC](#-table-of-contents)**${RED}❌ SSH connection test failed${NC}"
        FAILED=$((FAILED + 1))
    fi
    
    # Test SSH session limits
    MAX_SESSIONS=$(grep "MaxSessions" /etc/ssh/sshd_config | awk '{print $2}')
    echo -e "${YELLOW}📊 Max SSH sessions configured: $MAX_SESSIONS${NC}"
    
    # Test SSH startup limits
    MAX_STARTUPS=$(grep "MaxStartups" /etc/ssh/sshd_config | awk '{print $2}')
    echo -e "${YELLOW}📊 Max SSH startups configured: $MAX_STARTUPS${NC}"
}

# Generate Security Report
generate_security_report() {
    log_message "📋 Generating Security Report"
    echo "============================="
    
    REPORT_FILE="/tmp/ssh_security_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$REPORT_FILE" << REPORT_EOF
TwinTower SSH Security Report
=============================
Generated: $(date)
Tower: $TOWER_NAME
Test Mode: $TEST_MODE

Summary:
--------
Tests Passed: $PASSED
Tests Failed: $FAILED
Warnings: $WARNINGS
Total Tests: $((PASSED + FAILED))

Pass Rate: $(( PASSED * 100 / (PASSED + FAILED) ))%

Configuration Details:
---------------------
SSH Port: $(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
SSH Version: $(ssh -V 2>&1)
Tailscale IP: $(tailscale ip -4 2>/dev/null || echo "Not configured")
UFW Status: $(sudo ufw status | head -1)
fail2ban Status: $(sudo systemctl is-active fail2ban 2>/dev/null || echo "Not running")
Auditd Status: $(sudo systemctl is-active auditd 2>/dev/null || echo "Not running")

Security Features:
-----------------
$([ -f "/etc/ssh/banner" ] && echo "✅ SSH Banner: Configured" || echo "❌ SSH Banner: Not configured")
$([ -f "/usr/local/bin/ssh-command-wrapper.sh" ] && echo "✅ Command Wrapper: Configured" || echo "❌ Command Wrapper: Not configured")
$([ -f "/etc/ssh/ca/twintower_ca" ] && echo "✅ SSH CA: Configured" || echo "❌ SSH CA: Not configured")
$(grep -q "PasswordAuthentication no" /etc/ssh/sshd_config && echo "✅ Password Auth: Disabled" || echo "❌ Password Auth: Enabled")
$(grep -q "PermitRootLogin no" /etc/ssh/sshd_config && echo "✅ Root Login: Disabled" || echo "❌ Root Login: Enabled")

Recommendations:
---------------
$([ $FAILED -eq 0 ] && echo "✅ All security tests passed!" || echo "❌ $FAILED security tests failed - review configuration")
$([ -f "$HOME/.ssh/authorized_keys" ] || echo "⚠️  Consider setting up SSH key authentication")
$(sudo fail2ban-client status sshd >/dev/null 2>&1 || echo "⚠️  Consider enabling fail2ban SSH protection")
$([ "$(sudo ufw status | grep -c active)" -eq 0 ] && echo "⚠️  Consider enabling UFW firewall")

REPORT_EOF

    echo -e "${GREEN}✅ Security report generated: $REPORT_FILE${NC}"
    
    # Display report summary
    echo -e "${BLUE}📊 Report Summary:${NC}"
    cat "$REPORT_FILE" | grep -A 20 "Summary:"
}

# Main execution
main() {
    echo -e "${BLUE}🧪 TwinTower SSH Security Testing Suite${NC}"
    echo -e "${BLUE}Tower: $TOWER_NAME, Mode: $TEST_MODE${NC}"
    echo -e "${BLUE}=======================================${NC}"
    echo
    
    case "$TEST_MODE" in
        "quick")
            test_ssh_service
            test_ssh_connectivity
            ;;
        "security")
            test_ssh_hardening
            test_authentication
            test_firewall
            test_fail2ban
            test_ssh_security_features
            test_security_vulnerabilities
            ;;
        "performance")
            test_ssh_performance
            ;;
        "full")
            test_ssh_service
            test_ssh_hardening
            test_authentication
            test_firewall
            test_fail2ban
            test_ssh_connectivity
            test_ssh_logging
            test_ssh_security_features
            test_security_vulnerabilities
            test_ssh_performance
            ;;
        *)
            echo "Usage: $0 <tower_name> <quick|security|performance|full>"
            exit 1
            ;;
    esac
    
    echo
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}✅ Tests Passed: $PASSED${NC}"
    echo -e "${RED}❌ Tests Failed: $FAILED${NC}"
    echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
    echo -e "${BLUE}📊 Total Tests: $((PASSED + FAILED))${NC}"
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 All SSH security tests passed!${NC}"
    else
        echo -e "${RED}⚠️  $FAILED tests failed - review configuration${NC}"
    fi
    
    # Generate detailed report for full tests
    if [ "$TEST_MODE" = "full" ]; then
        generate_security_report
    fi
}

# Execute main function
main "$@"
EOF

chmod +x ~/test_ssh_security.sh
```

### **Step 2: Create SSH Penetration Testing Script**

```bash
cat > ~/ssh_penetration_test.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Penetration Testing Script
# IMPORTANT: Only use this on your own systems for security testing

set -e

TARGET_HOST="${1:-localhost}"
TARGET_PORT="${2:-22}"
TEST_MODE="${3:-safe}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to test SSH banner grabbing
test_ssh_banner() {
    log_message "🏷️ Testing SSH banner grabbing..."
    
    echo "Testing SSH banner disclosure:"
    timeout 10 nc -nv "$TARGET_HOST" "$TARGET_PORT" <<< "" 2>/dev/null | head -5 || echo "Banner grab failed"
    echo
}

# Function to test SSH version detection
test_ssh_version() {
    log_message "🔍 Testing SSH version detection..."
    
    echo "SSH version detection:"
    timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 "$TARGET_HOST" -p "$TARGET_PORT" 2>&1 | grep -E "(OpenSSH|SSH-)" || echo "Version detection failed"
    echo
}

# Function to test SSH cipher enumeration
test_ssh_ciphers() {
    log_message "🔐 Testing SSH cipher enumeration..."
    
    echo "Testing supported ciphers:"
    timeout 10 nmap --script ssh2-enum-algos -p "$TARGET_PORT" "$TARGET_HOST" 2>/dev/null | grep -A 20 "encryption_algorithms" || echo "Cipher enumeration failed (nmap required)"
    echo
}

# Function to test SSH authentication methods
test_ssh_auth_methods() {
    log_message "🔑 Testing SSH authentication methods..."
    
    echo "Testing authentication methods:"
    timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 -o PreferredAuthentications=none "$TARGET_HOST" -p "$TARGET_PORT" 2>&1 | grep -E "(password|publickey|keyboard-interactive)" || echo "Auth method detection failed"
    echo
}

# Function to test SSH brute force protection
test_ssh_brute_force() {
    log_message "🛡️ Testing SSH brute force protection..."
    
    if [ "$TEST_MODE" = "aggressive" ]; then
        echo "Testing brute force protection (3 attempts):"
        for i in {1..3}; do
            echo "Attempt $i:"
            timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 -o PasswordAuthentication=yes -o PubkeyAuthentication=no "nonexistent_user@$TARGET_HOST" -p "$TARGET_PORT" 2>&1 | grep -E "(Permission denied|Connection refused|timeout)" || echo "Attempt $i failed"
        done
    else
        echo "Brute force testing skipped in safe mode"
    fi
    echo
}

# Function to test SSH key authentication
test_ssh_key_auth() {
    log_message "🔐 Testing SSH key authentication..."
    
    echo "Testing key authentication:"
    if [ -f "$HOME/.ssh/twintower_keys/twintower_master_ed25519" ]; then
        timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$HOME/.ssh/twintower_keys/twintower_master_ed25519" -p "$TARGET_PORT" "$TARGET_HOST" 'echo "Key auth successful"' 2>/dev/null || echo "Key authentication failed"
    else
        echo "No SSH keys found for testing"
    fi
    echo
}

# Function to test SSH connection limits
test_ssh_limits() {
    log_message "⚡ Testing SSH connection limits..."
    
    echo "Testing connection limits:"
    # Test multiple simultaneous connections
    for i in {1..5}; do
        timeout 5 bash -c "echo > /dev/tcp/$TARGET_HOST/$TARGET_PORT" 2>/dev/null &
    done
    wait
    echo "Connection limit test completed"
    echo
}

# Function to test SSH tunneling capabilities
test_ssh_tunneling() {
    log_message "🌐 Testing SSH tunneling capabilities..."
    
    echo "Testing SSH tunneling:"
    if [ -f "$HOME/.ssh/twintower_keys/twintower_master_ed25519" ]; then
        timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$HOME/.ssh/twintower_keys/twintower_master_ed25519" -L 9999:localhost:22 -p "$TARGET_PORT" "$TARGET_HOST" -N 2>&1 | grep -E "(refused|denied|Permission)" || echo "Tunneling test inconclusive"
    else
        echo "No SSH keys available for tunneling test"
    fi
    echo
}

# Function to generate penetration test report
generate_pentest_report() {
    log_message "📋 Generating penetration test report..."
    
    REPORT_FILE="/tmp/ssh_pentest_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$REPORT_FILE" << REPORT_EOF
TwinTower SSH Penetration Test Report
====================================
Generated: $(date)
Target: $TARGET_HOST:$TARGET_PORT
Test Mode: $TEST_MODE

⚠️  IMPORTANT: This test was conducted on authorized systems only.

Test Results Summary:
--------------------
✅ SSH Banner: $(timeout 10 nc -nv "$TARGET_HOST" "$TARGET_PORT" <<< "" 2>/dev/null | head -1 | grep -q "SSH" && echo "Disclosed" || echo "Protected")
✅ SSH Version: $(timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 "$TARGET_HOST" -p "$TARGET_PORT" 2>&1 | grep -q "OpenSSH" && echo "Detected" || echo "Hidden")
✅ Password Auth: $(timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 -o PasswordAuthentication=yes -o PubkeyAuthentication=no "test@$TARGET_HOST" -p "$TARGET_PORT" 2>&1 | grep -q "Permission denied" && echo "Disabled" || echo "Enabled")
✅ Root Login: $(timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 "root@$TARGET_HOST" -p "$TARGET_PORT" 2>&1 | grep -q "Permission denied" && echo "Disabled" || echo "Enabled")

Security Recommendations:
------------------------
$(timeout 10 nc -nv "$TARGET_HOST" "$TARGET_PORT" <<< "" 2>/dev/null | head -1 | grep -q "SSH" && echo "⚠️  Consider disabling SSH banner" || echo "✅ SSH banner is properly configured")
$([ "$TARGET_PORT" = "22" ] && echo "⚠️  Consider changing SSH port from default" || echo "✅ SSH port is non-standard")
$(timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 -o PasswordAuthentication=yes -o PubkeyAuthentication=no "test@$TARGET_HOST" -p "$TARGET_PORT" 2>&1 | grep -q "Permission denied" || echo "⚠️  Consider disabling password authentication")

REPORT_EOF

    echo -e "${GREEN}✅ Penetration test report generated: $REPORT_FILE${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}🔍 TwinTower SSH Penetration Testing${NC}"
    echo -e "${BLUE}Target: $TARGET_HOST:$TARGET_PORT${NC}"
    echo -e "${BLUE}Mode: $TEST_MODE${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${RED}⚠️  ONLY USE ON AUTHORIZED SYSTEMS${NC}"
    echo
    
    # Check if target is reachable
    if ! timeout 5 bash -c "</dev/tcp/$TARGET_HOST/$TARGET_PORT" 2>/dev/null; then
        echo -e "${RED}❌ Target $TARGET_HOST:$TARGET_PORT is not reachable${NC}"
        exit 1
    fi
    
    test_ssh_banner
    test_ssh_version
    test_ssh_ciphers
    test_ssh_auth_methods
    test_ssh_brute_force
    test_ssh_key_auth
    test_ssh_limits
    test_ssh_tunneling
    
    generate_pentest_report
    
    echo -e "${GREEN}🎉 SSH penetration testing completed!${NC}"
    echo -e "${YELLOW}📋 Review the generated report for security recommendations${NC}"
}

# Execute main function
main "$@"
EOF

chmod +x ~/ssh_penetration_test.sh
```

### **Step 3: Execute Security Testing**

```bash
# Run comprehensive security tests
./test_ssh_security.sh $(hostname) full

# Run quick connectivity tests
./test_ssh_security.sh $(hostname) quick

# Run penetration tests (safe mode)
./ssh_penetration_test.sh localhost $(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1) safe
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📊 **Monitoring & Logging**

### **Step 1: Create SSH Monitoring System**

```bash
cat > ~/ssh_monitoring_system.sh << 'EOF'
#!/bin/bash

# TwinTower SSH Monitoring System
# Section 5B: SSH Hardening & Port Configuration

set -e

ACTION="${1:-start}"
MONITOR_INTERVAL="${2:-60}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LOG_FILE="/var/log/ssh-monitor.log"
ALERT_LOG="/var/log/ssh-alerts.log"
STATS_LOG="/var/log/ssh-stats.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | sudo tee -a "$LOG_FILE"
}

# Function to setup monitoring infrastructure
setup_monitoring() {
    log_message "🔧 Setting up SSH monitoring infrastructure..."
    
    # Create log files
    sudo touch "$LOG_FILE" "$ALERT_LOG" "$STATS_LOG"
    sudo chmod 640 "$LOG_FILE" "$ALERT_LOG" "$STATS_LOG"
    
    # Create monitoring scripts directory
    sudo mkdir -p /usr/local/bin/ssh-monitoring
    
    # Create systemd service for monitoring
    cat << SERVICE_EOF | sudo tee /etc/systemd/system/ssh-monitor.service
[Unit]
Description=TwinTower SSH Monitoring Service
After=network.target ssh.service

[Service]
Type=simple
User=root
ExecStart=/home/$(whoami)/ssh_monitoring_system.sh daemon $MONITOR_INTERVAL
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    # Create monitoring configuration
    cat << CONFIG_EOF | sudo tee /etc/ssh-monitor.conf
# TwinTower SSH Monitoring Configuration
MONITOR_INTERVAL=$MONITOR_INTERVAL
MAX_FAILED_ATTEMPTS=3
ALERT_THRESHOLD=5
LOG_RETENTION_DAYS=30
ENABLE_EMAIL_ALERTS=false
EMAIL_RECIPIENT=admin@localhost
ENABLE_SLACK_ALERTS=false
SLACK_WEBHOOK_URL=
CONFIG_EOF

    sudo systemctl daemon-reload
    log_message "✅ SSH monitoring infrastructure setup complete"
}

# Function to monitor SSH connections
monitor_ssh_connections() {
    local ssh_port=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    
    # Count active connections
    local active_connections=$(sudo netstat -tnp | grep ":$ssh_port " | grep ESTABLISHED | wc -l)
    
    # Count failed attempts in last hour
    local failed_attempts=$(sudo grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d %H')" | wc -l)
    
    # Count successful logins in last hour
    local successful_logins=$(sudo grep "Accepted publickey" /var/log/auth.log | grep "$(date '+%b %d %H')" | wc -l)
    
    # Log statistics
    echo "$(date '+%Y-%m-%d %H:%M:%S'),active_connections:$active_connections,failed_attempts:$failed_attempts,successful_logins:$successful_logins" | sudo tee -a "$STATS_LOG"
    
    # Check for alerts
    if [ "$failed_attempts" -gt 5 ]; then
        log_message "🚨 ALERT: High number of failed SSH attempts ($failed_attempts) detected"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - High failed attempts: $failed_attempts" | sudo tee -a "$ALERT_LOG"
    fi
    
    if [ "$active_connections" -gt 10 ]; then
        log_message "⚠️  WARNING: High number of active SSH connections ($active_connections)"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - High active connections: $active_connections" | sudo tee -a "$ALERT_LOG"
    fi
}

# Function to monitor SSH service health
monitor_ssh_health() {
    # Check if SSH service is running
    if ! sudo systemctl is-active --quiet ssh; then
        log_message "🚨 ALERT: SSH service is not running!"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - SSH service down" | sudo tee -a "$ALERT_LOG"
        
        # Attempt to restart SSH service
        log_message "🔄 Attempting to restart SSH service..."
        sudo systemctl restart ssh
        
        if sudo systemctl is-active --quiet ssh; then
            log_message "✅ SSH service restarted successfully"
        else
            log_message "❌ Failed to restart SSH service"
        fi
    fi
    
    # Check if SSH port is accessible
    local ssh_port=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    if ! timeout 5 bash -c "</dev/tcp/localhost/$ssh_port"; then
        log_message "🚨 ALERT: SSH port $ssh_port is not accessible!"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - SSH port inaccessible: $ssh_port" | sudo tee -a "$ALERT_LOG"
    fi
}

# Function to analyze SSH logs
analyze_ssh_logs() {
    log_message "📊 Analyzing SSH logs..."
    
    # Create analysis report
    ANALYSIS_FILE="/tmp/ssh_log_analysis_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$ANALYSIS_FILE" << ANALYSIS_EOF
SSH Log Analysis Report
======================
Generated: $(date)
Analysis Period: Last 24 hours

Connection Statistics:
---------------------
Total login attempts: $(sudo grep "ssh" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
Successful logins: $(sudo grep "Accepted" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
Failed attempts: $(sudo grep "Failed" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
Invalid users: $(sudo grep "Invalid user" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)

Top Source IPs:
--------------
$(sudo grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d')" | awk '{print $(NF-3)}' | sort | uniq -c | sort -nr | head -10)

Top Usernames Attempted:
-----------------------
$(sudo grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d')" | awk '{print $9}' | sort | uniq -c | sort -nr | head -10)

Recent Successful Logins:
------------------------
$(sudo grep "Accepted publickey" /var/log/auth.log | grep "$(date '+%b %d')" | tail -5)

Recent Failed Attempts:
----------------------
$(sudo grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d')" | tail -10)

fail2ban Activity:
-----------------
$(sudo fail2ban-client status sshd 2>/dev/null | grep -E "(Currently failed|Total failed|Currently banned|Total banned)" || echo "fail2ban not active")

ANALYSIS_EOF

    log_message "📋 SSH log analysis completed: $ANALYSIS_FILE"
}

# Function to generate SSH security dashboard
generate_ssh_dashboard() {
    local ssh_port=$(sudo ss -tlnp | grep sshd | awk '{print $4}' | cut -d: -f2 | head -1)
    
    clear
    echo -e "${BLUE}🔐 TwinTower SSH Security Dashboard${NC}"
    echo -e "${BLUE}====================================${NC}"
    echo
    
    # Service status
    echo -e "${YELLOW}📊 Service Status${NC}"
    echo "----------------"
    if sudo systemctl is-active --quiet ssh; then
        echo -e "SSH Service: ${GREEN}✅ Running${NC}"
    else
        echo -e "SSH Service: ${RED}❌ Stopped${NC}"
    fi
    echo -e "SSH Port: ${GREEN}$ssh_port${NC}"
    echo
    
    # Connection statistics
    echo -e "${YELLOW}🔗 Connection Statistics${NC}"
    echo "------------------------"
    local active_connections=$(sudo netstat -tnp | grep ":$ssh_port " | grep ESTABLISHED | wc -l)
    local failed_today=$(sudo grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
    local success_today=$(sudo grep "Accepted publickey" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
    
    echo -e "Active Connections: ${GREEN}$active_connections${NC}"
    echo -e "Failed Attempts Today: ${RED}$failed_today${NC}"
    echo -e "Successful Logins Today: ${GREEN}$success_today${NC}"
    echo
    
    # Security status
    echo -e "${YELLOW}🛡️ Security Status${NC}"
    echo "------------------"
    if sudo systemctl is-active --quiet fail2ban; then
        echo -e "fail2ban: ${GREEN}✅ Active${NC}"
        local banned_ips=$(sudo fail2ban-client status sshd 2>/dev/null | grep "Currently banned" | awk '{print $4}' || echo "0")
        echo -e "Banned IPs: ${RED}$banned_ips${NC}"
    else
        echo -e "
