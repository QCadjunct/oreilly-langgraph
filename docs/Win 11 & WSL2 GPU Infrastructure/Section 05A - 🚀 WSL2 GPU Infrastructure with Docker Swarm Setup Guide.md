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
- Configuration files (/etc/tailscale/)
- Service files and overrides
- Network configuration
- Authentication state
- Management scripts
- System logs
INFO_EOF

# Create compressed backup
echo "📦 Creating compressed backup..."
cd "$TEMP_DIR"
tar -czf "$BACKUP_DIR/$BACKUP_FILE" "tailscale_backup_$TIMESTAMP/"

# Set proper permissions
chmod 600 "$BACKUP_DIR/$BACKUP_FILE"

# Cleanup temporary directory
rm -rf "$TEMP_DIR"

# Create backup log entry
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup created: $BACKUP_FILE" >> "$BACKUP_DIR/backup.log"

echo "✅ Backup completed successfully!"
echo "📁 Backup file: $BACKUP_DIR/$BACKUP_FILE"
echo "📊 Backup size: $(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)"

# Clean up old backups (keep last 5)
echo "🧹 Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t tailscale_backup_*.tar.gz | tail -n +6 | xargs rm -f 2>/dev/null || true

echo "🎉 Backup process completed!"
EOF

chmod +x ~/backup_tailscale.sh
```

### **Step 2: Create Recovery Script**

```bash
cat > ~/restore_tailscale.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Recovery Script
set -e

BACKUP_DIR="/home/$(whoami)/tailscale_backups"
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_DIR/$BACKUP_FILE"
    exit 1
fi

echo "🔄 Starting Tailscale recovery from backup..."
echo "📁 Backup file: $BACKUP_FILE"

# Stop Tailscale services
echo "🛑 Stopping Tailscale services..."
sudo systemctl stop tailscale-routing 2>/dev/null || true
sudo systemctl stop tailscaled 2>/dev/null || true

# Create temporary restore directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Extract backup
echo "📦 Extracting backup..."
tar -xzf "$BACKUP_DIR/$BACKUP_FILE"

# Find the backup directory
RESTORE_DIR=$(find . -name "tailscale_backup_*" -type d | head -n1)
if [ -z "$RESTORE_DIR" ]; then
    echo "❌ Invalid backup file structure"
    exit 1
fi

cd "$RESTORE_DIR"

# Restore configuration files
echo "📄 Restoring configuration files..."
if [ -d "tailscale" ]; then
    sudo cp -r tailscale /etc/
    sudo chown -R root:root /etc/tailscale
    sudo chmod -R 600 /etc/tailscale/*
fi

# Restore service files
echo "⚙️ Restoring service files..."
if [ -f "override.conf" ]; then
    sudo mkdir -p /etc/systemd/system/tailscaled.service.d
    sudo cp override.conf /etc/systemd/system/tailscaled.service.d/
fi

if [ -f "tailscale-routing.service" ]; then
    sudo cp tailscale-routing.service /etc/systemd/system/
fi

if [ -f "tailscale-routing.sh" ]; then
    sudo cp tailscale-routing.sh /usr/local/bin/
    sudo chmod +x /usr/local/bin/tailscale-routing.sh
fi

# Restore network configuration
echo "🌐 Restoring network configuration..."
if [ -f "iptables.rules" ]; then
    sudo iptables-restore < iptables.rules
    sudo netfilter-persistent save
fi

# Restore authentication state
echo "🔑 Restoring authentication state..."
if [ -f "tailscaled.state" ]; then
    sudo mkdir -p /var/lib/tailscale
    sudo cp tailscaled.state /var/lib/tailscale/
    sudo chown root:root /var/lib/tailscale/tailscaled.state
    sudo chmod 600 /var/lib/tailscale/tailscaled.state
fi

# Restore management scripts
echo "📋 Restoring management scripts..."
for script in install_tailscale.sh configure_tailscale.sh setup_routing.sh manage_auth.sh test_tailscale_mesh.sh monitor_tailscale.sh tailscale_dashboard.sh; do
    if [ -f "$script" ]; then
        cp "$script" ~/
        chmod +x ~/"$script"
    fi
done

# Reload systemd and restart services
echo "🔄 Reloading systemd and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable tailscaled
sudo systemctl enable tailscale-routing
sudo systemctl start tailscaled
sudo systemctl start tailscale-routing

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 5

# Verify restoration
echo "✅ Verifying restoration..."
if sudo systemctl is-active --quiet tailscaled; then
    echo "✅ Tailscale service is running"
else
    echo "❌ Tailscale service failed to start"
fi

# Show status
echo "📊 Current status:"
tailscale status

# Cleanup
rm -rf "$TEMP_DIR"

echo "🎉 Recovery completed successfully!"
echo "🔍 Run './test_tailscale_mesh.sh' to verify full functionality"
EOF

chmod +x ~/restore_tailscale.sh
```

### **Step 3: Create Automated Backup Service**

```bash
# Create automated backup service
cat > ~/setup_backup_service.sh << 'EOF'
#!/bin/bash

# TwinTower Tailscale Automated Backup Service Setup
set -e

echo "⚙️ Setting up automated backup service..."

# Create backup service
cat << 'SERVICE_EOF' | sudo tee /etc/systemd/system/tailscale-backup.service
[Unit]
Description=TwinTower Tailscale Backup Service
After=tailscaled.service

[Service]
Type=oneshot
User=root
ExecStart=/home/USER_HOME/backup_tailscale.sh
StandardOutput=journal
StandardError=journal
SERVICE_EOF

# Replace USER_HOME with actual user home
sudo sed -i "s/USER_HOME/$(whoami)/" /etc/systemd/system/tailscale-backup.service

# Create backup timer
cat << 'TIMER_EOF' | sudo tee /etc/systemd/system/tailscale-backup.timer
[Unit]
Description=Run TwinTower Tailscale Backup Daily
Requires=tailscale-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable tailscale-backup.timer
sudo systemctl start tailscale-backup.timer

echo "✅ Automated backup service configured"
echo "📅 Backups will run daily"
echo "🔍 Check timer status: sudo systemctl status tailscale-backup.timer"
EOF

chmod +x ~/setup_backup_service.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 🚀 **Next Steps**

### **Section 5A Completion Checklist**

Verify the following before proceeding to Section 5B:

- ✅ **Tailscale installed** on all three towers
- ✅ **Mesh network established** with all peers visible
- ✅ **Authentication completed** for all towers
- ✅ **Connectivity verified** between all towers
- ✅ **Management scripts** created and functional
- ✅ **Backup system** configured and tested
- ✅ **Monitoring tools** available and operational

### **Quick Status Verification**

Run this final verification on each tower:

```bash
# Final verification script
cat > ~/verify_section_5a.sh << 'EOF'
#!/bin/bash

echo "🔍 Section 5A Final Verification"
echo "================================="

# Check service status
echo "1. Service Status:"
sudo systemctl is-active tailscaled && echo "✅ Running" || echo "❌ Failed"

# Check connectivity
echo "2. Peer Connectivity:"
tailscale status | grep -E "(twinover[1-3]|online|offline)" || echo "❌ No peers"

# Check authentication
echo "3. Authentication:"
tailscale status | grep -q "logged in" && echo "✅ Authenticated" || echo "❌ Not authenticated"

# Check IP assignment
echo "4. IP Assignment:"
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "Not assigned")
echo "IP: $TAILSCALE_IP"

# Check scripts
echo "5. Management Scripts:"
ls -la ~/tailscale_dashboard.sh ~/backup_tailscale.sh ~/test_tailscale_mesh.sh | grep -q "rwx" && echo "✅ Scripts ready" || echo "❌ Scripts missing"

echo "================================="
echo "✅ Section 5A verification complete!"
EOF

chmod +x ~/verify_section_5a.sh
./verify_section_5a.sh
```

### **Preparing for Section 5B**

Section 5B will focus on **SSH Hardening & Port Configuration**. Your Tailscale mesh network is now ready for secure shell access configuration.

**Expected outcomes for Section 5B:**
- 🔐 SSH hardening with key-based authentication
- 🔢 Custom port configuration (2122/2222/2322)
- 🛡️ Enhanced security policies
- 🔑 Centralized key management
- 📡 Secure remote access protocols

### **Useful Commands for Daily Operations**

```bash
# Quick status check
tailscale status

# Dashboard access
./tailscale_dashboard.sh

# Connectivity test
./test_tailscale_mesh.sh

# Create backup
./backup_tailscale.sh

# Monitor network
./monitor_tailscale.sh
```

**[⬆️ Back to TOC](#-table-of-contents)**

---

## 📝 **Section 5A Summary**

**What was accomplished:**
- ✅ **Tailscale VPN mesh network** established across all three towers
- ✅ **Zero-trust networking** foundation with automatic encryption
- ✅ **Cross-platform compatibility** ensured for Windows/WSL2/Linux
- ✅ **Comprehensive testing suite** for network verification
- ✅ **Management and monitoring tools** for ongoing operations
- ✅ **Backup and recovery system** for configuration protection

**Network Architecture Created:**
```
Internet ←→ Tailscale Mesh Network ←→ TwinTower Infrastructure
                    ↓
    ┌─────────────────────────────────────────────────────┐
    │  twinover1-worker ←→ twinover2-worker ←→ twinover3-primary │
    │         ↕                    ↕                    ↕     │
    │    TwinTower1           TwinTower2           TwinTower3   │
    │   (RTX 4090)            (RTX 4090)          (2x RTX 5090) │
    └─────────────────────────────────────────────────────┘
```

**Ready for Section 5B:** SSH Hardening & Port Configuration

**[⬆️ Back to TOC](#-table-of-contents)**
