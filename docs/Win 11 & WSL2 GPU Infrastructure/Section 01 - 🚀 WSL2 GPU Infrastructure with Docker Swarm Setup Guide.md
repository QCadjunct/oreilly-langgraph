# 🚀 WSL2 GPU Infrastructure with Docker Swarm Setup Guide

## 📋 Table of Contents

- [🔧 Section 1: System Prerequisites and WSL2 Setup](#-section-1-system-prerequisites-and-wsl2-setup)
  - [System Requirements](#system-requirements)
  - [Enable WSL2 Features](#enable-wsl2-features)
  - [Install Ubuntu 24.04](#install-ubuntu-2404)
  - [Configure WSL2 Resource Limits](#configure-wsl2-resource-limits)
  - [Initial Ubuntu Configuration](#initial-ubuntu-configuration)
  - [Verify Installation](#verify-installation)

---

## 🔧 Section 1: System Prerequisites and WSL2 Setup

### System Requirements

Before proceeding, ensure your system meets these requirements:

- **Operating System**: Windows 11 Pro (Build 26100 or later)
- **Hardware Configuration**:
  - **TwinTower3** (Primary GPU Server):
    - 256GB+ RAM 
    - AMD Ryzen 9 3950X (16 cores, 32 threads)
    - NVIDIA RTX 5090 (2x) GPUs
    - 4TB NVMe SSD (boot drive)
    - 4TB NVMe SSD (containerization)
    - 8TB SATA drive (data storage)
  - **TwinTower1 & TwinTower2** (Secondary GPU Servers):
    - 128GB+ RAM each
    - AMD Ryzen 9 3950X (16 cores, 32 threads) each
    - NVIDIA RTX 4090 (1x) GPU each
    - 4TB NVMe SSD (boot drive) each
    - 4TB NVMe SSD (containerization) each
    - 8TB SATA drive (data storage) each
- **Windows Features**: 
  - Hyper-V capabilities (for full virtualization and VM management)
  - Virtualization enabled in BIOS (UEFI mode)
  - Windows Subsystem for Linux support
  - Virtual Machine Platform (for WSL2 backend)

### Enable WSL2 Features

We need to enable both WSL2 and Hyper-V features for maximum flexibility. WSL2 will handle containerized workloads while Hyper-V provides full VM capabilities.

**Step 1: Open PowerShell as Administrator**

Press `Win + X` and select "Windows PowerShell (Admin)" or "Windows Terminal (Admin)".

**Step 2: Enable Required Windows Features**

```powershell
# Enable Windows Subsystem for Linux
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform (required for WSL2)
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Enable Hyper-V Platform (lightweight virtualization for WSL2)
dism.exe /online /enable-feature /featurename:HypervisorPlatform /all /norestart

# Enable full Hyper-V (for traditional VMs and advanced virtualization)
dism.exe /online /enable-feature /featurename:Microsoft-Hyper-V-All /all /norestart

# Enable Windows Hypervisor Platform (for compatibility)
dism.exe /online /enable-feature /featurename:HypervisorPlatform /all /norestart
```

**Step 3: Verify Feature Status**

```powershell
# Check which features are enabled
dism.exe /online /get-featureinfo /featurename:Microsoft-Windows-Subsystem-Linux
dism.exe /online /get-featureinfo /featurename:VirtualMachinePlatform
dism.exe /online /get-featureinfo /featurename:Microsoft-Hyper-V-All
```

**Step 3: Restart Your Computer**

```powershell
# Restart to apply changes
shutdown /r /t 5 /c "Restarting to enable WSL2 and Hyper-V features"
```

**Step 4: Post-Restart Verification**

After restart, open PowerShell as Administrator again and verify:

```powershell
# Verify virtualization is enabled
systeminfo | findstr /i "hyper-v"

# Check WSL status
wsl --status
```

**Step 5: Set WSL2 as Default Version**

Now configure WSL2 as the default version:

```powershell
# Set WSL2 as the default version
wsl --set-default-version 2

# Update WSL kernel (if needed)
wsl --update
```

[⬆️ Back to TOC](#-table-of-contents)

### Install Ubuntu 24.04

**Step 1: Install Ubuntu 24.04 LTS**

```powershell
# Install Ubuntu 24.04
wsl --install -d Ubuntu-24.04

# Alternative: Download from Microsoft Store if command fails
# Visit: https://apps.microsoft.com/store/detail/ubuntu-2404-lts/9NZ3KLHXDJP5
```

**Step 2: Initial Ubuntu Setup**

When Ubuntu starts for the first time, you'll be prompted to create a user account:

**Step 5: Configure User Environment**

```bash
# Follow the prompts to create:
# - Username (e.g., 'gpuadmin')
# - Password (use a strong password)
# - Confirm password
```

**Step 3: Verify WSL2 Installation**

Back in PowerShell, verify the installation:

```powershell
# Check WSL installations
wsl --list --verbose

# Expected output:
# NAME            STATE           VERSION
# Ubuntu-24.04    Running         2
```

[⬆️ Back to TOC](#-table-of-contents)

### Configure WSL2 Resource Limits

**Step 1: Create WSL Configuration File**

Create a `.wslconfig` file in your Windows user profile directory:

```powershell
# Navigate to user profile
cd $env:USERPROFILE

# Create .wslconfig file
New-Item -ItemType File -Name ".wslconfig" -Force
```

**Step 2: Configure Resource Limits**

Edit the `.wslconfig` file with the following content:

```ini
[wsl2]
# Memory allocation (TwinTower3: 256GB, TwinTower1/2: 128GB)
memory=120GB

# CPU allocation (AMD Ryzen 9 3950X: 16 cores, 32 threads)
processors=16

# Swap file size
swap=16GB

# Enable localhost forwarding
localhostForwarding=true

# Enable nested virtualization for Docker
nestedVirtualization=true

# Disable page reporting for better performance
pageReporting=false

# Set kernel command line options
kernelCommandLine=cgroup_enable=memory swapaccount=1

# GUI support
guiApplications=false

# Network mode
networkingMode=bridged

# Debug console
debugConsole=true
```

**Step 3: Apply Configuration**

```powershell
# Shutdown WSL to apply changes
wsl --shutdown

# Wait 10 seconds
Start-Sleep -Seconds 10

# Restart Ubuntu
wsl -d Ubuntu-24.04
```

[⬆️ Back to TOC](#-table-of-contents)

### Initial Ubuntu Configuration

**Step 1: Update System Packages**

```bash
# Update package lists
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    nano \
    vim \
    htop \
    neofetch \
    tree \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
```

**Step 2: Configure System Settings**

```bash
# Set timezone (adjust for your location)
sudo timedatectl set-timezone America/New_York

# Configure locale
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8

# Update hostname (use appropriate tower name)
sudo hostnamectl set-hostname $(echo $HOSTNAME | tr '[:upper:]' '[:lower:]')-gpu-infra

# Add hostname to hosts file
echo "127.0.0.1 $(hostname)" | sudo tee -a /etc/hosts
```

**Step 3: Create Directory Structure**

```bash
# Create main infrastructure directory
sudo mkdir -p /opt/gpu-infrastructure

# Create subdirectories
sudo mkdir -p /opt/gpu-infrastructure/{docker,data,scripts,config,logs}
sudo mkdir -p /opt/gpu-infrastructure/docker/{gpu-nodes,ollama,git-server,monitoring}
sudo mkdir -p /opt/gpu-infrastructure/data/{shared,gpu1,gpu2,gpu3}
sudo mkdir -p /opt/gpu-infrastructure/data/shared/{models,datasets,results}
sudo mkdir -p /opt/gpu-infrastructure/scripts/{startup,monitoring,maintenance}
sudo mkdir -p /opt/gpu-infrastructure/config/{tailscale,ssh,docker-swarm}

# Set ownership
sudo chown -R $USER:$USER /opt/gpu-infrastructure

# Display directory structure
tree /opt/gpu-infrastructure
```

**Step 4: Configure Multi-Tower Environment**

```bash
# Detect current system and configure accordingly
SYSTEM_NAME=$(cmd.exe /c "echo %COMPUTERNAME%" 2>/dev/null | tr -d '\r' | tr '[:upper:]' '[:lower:]')

# Create system-specific configuration
cat > /opt/gpu-infrastructure/config/system-config.sh << EOF
#!/bin/bash
# System Configuration for $SYSTEM_NAME

export TOWER_NAME="$SYSTEM_NAME"
export TOWER_ID=\$(echo \$TOWER_NAME | sed 's/twintower//')

# Hardware configuration based on tower
case \$TOWER_ID in
    "3")
        export GPU_COUNT=2
        export GPU_TYPE="RTX5090"
        export MEMORY_GB=256
        export CPU_CORES=16
        export STORAGE_BOOT="4TB_NVME"
        export STORAGE_CONTAINER="4TB_NVME"
        export STORAGE_DATA="8TB_SATA"
        export ROLE="primary"
        ;;
    "1"|"2")
        export GPU_COUNT=1
        export GPU_TYPE="RTX4090"
        export MEMORY_GB=128
        export CPU_CORES=16
        export STORAGE_BOOT="4TB_NVME"
        export STORAGE_CONTAINER="4TB_NVME"
        export STORAGE_DATA="8TB_SATA"
        export ROLE="secondary"
        ;;
    *)
        echo "Unknown tower configuration"
        exit 1
        ;;
esac

echo "Configured for \$TOWER_NAME (\$ROLE role)"
echo "- GPUs: \$GPU_COUNT x \$GPU_TYPE"
echo "- Memory: \$MEMORY_GB GB"
echo "- CPU Cores: \$CPU_CORES"
EOF

# Make configuration executable
chmod +x /opt/gpu-infrastructure/config/system-config.sh

# Load system configuration
source /opt/gpu-infrastructure/config/system-config.sh

# Add to .bashrc for persistent loading
echo "source /opt/gpu-infrastructure/config/system-config.sh" >> ~/.bashrc
```

```bash
# Add useful aliases to .bashrc
cat >> ~/.bashrc << 'EOF'

# GPU Infrastructure Aliases
alias gpu-status='nvidia-smi'
alias docker-gpu='docker run --gpus all'
alias swarm-status='docker node ls'
alias gpu-logs='tail -f /opt/gpu-infrastructure/logs/*.log'
alias gpu-restart='sudo systemctl restart docker'

# Navigation aliases
alias gpu-home='cd /opt/gpu-infrastructure'
alias gpu-docker='cd /opt/gpu-infrastructure/docker'
alias gpu-data='cd /opt/gpu-infrastructure/data'
alias gpu-logs-dir='cd /opt/gpu-infrastructure/logs'

# System monitoring
alias gpu-mem='free -h'
alias gpu-disk='df -h'
alias gpu-temp='sensors 2>/dev/null || echo "Install lm-sensors: sudo apt install lm-sensors"'

EOF

# Reload .bashrc
source ~/.bashrc
```

[⬆️ Back to TOC](#-table-of-contents)

### Verify Installation

**Step 1: System Information**

```bash
# Display system information
neofetch

# Check WSL version
cat /proc/version

# Check available resources
echo "=== CPU Information ==="
lscpu | grep -E "CPU\(s\)|Model name|Thread"

echo "=== Memory Information ==="
free -h

echo "=== Disk Information ==="
df -h

echo "=== Network Information ==="
ip addr show
```

**Step 2: Test Basic Functionality**

```bash
# Test internet connectivity
ping -c 3 google.com

# Test DNS resolution
nslookup github.com

# Test package manager
sudo apt list --installed | head -5

# Test directory permissions
ls -la /opt/gpu-infrastructure
```

**Step 3: Create System Status Script**

```bash
# Create system status script
cat > /opt/gpu-infrastructure/scripts/system-status.sh << 'EOF'
#!/bin/bash

echo "=== GPU Infrastructure System Status ==="
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p)"
echo ""

echo "=== WSL2 Information ==="
echo "WSL Version: $(cat /proc/version | cut -d' ' -f3)"
echo "Kernel: $(uname -r)"
echo ""

echo "=== System Hardware Configuration ==="
echo "Tower: $TOWER_NAME"
echo "Role: $ROLE"
echo "GPUs: $GPU_COUNT x $GPU_TYPE"
echo "Memory: $MEMORY_GB GB"
echo "CPU Cores: $CPU_CORES"
echo ""

echo "=== Storage Configuration ==="
echo "Boot Drive: $STORAGE_BOOT"
echo "Container Drive: $STORAGE_CONTAINER"
echo "Data Drive: $STORAGE_DATA"
echo ""

echo "=== Resource Usage ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $5 " used of " $2}')"
echo ""
echo "IP Address: $(ip route get 1.1.1.1 | awk '{print $7}' | head -1)"
echo "Internet: $(ping -c 1 -W 1 google.com &>/dev/null && echo "Connected" || echo "Disconnected")"
echo ""

echo "=== Network Status ==="
if command -v docker &> /dev/null; then
    echo "Docker: $(docker --version)"
    echo "Docker Status: $(systemctl is-active docker)"
else
    echo "Docker: Not installed"
fi
echo ""

echo "=== Docker Status ==="
echo "1. Install NVIDIA drivers and CUDA toolkit"
echo "2. Configure Docker with GPU support"
echo "3. Set up Docker Swarm"
echo "4. Configure storage with VHDX"
echo "5. Install Tailscale for secure networking"
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/system-status.sh

# Run system status
/opt/gpu-infrastructure/scripts/system-status.sh
```

**Step 4: Configure Automatic Startup**

```bash
# Create startup script for WSL2
cat > /opt/gpu-infrastructure/scripts/wsl-startup.sh << 'EOF'
#!/bin/bash

# WSL2 Startup Script for GPU Infrastructure
echo "Starting GPU Infrastructure WSL2 environment..."

# Mount shared directories (will be configured in storage section)
echo "Mounting shared directories..."
# sudo mount -a

# Start system services
echo "Starting system services..."
sudo systemctl start ssh

# Log startup
echo "WSL2 startup completed at $(date)" >> /opt/gpu-infrastructure/logs/startup.log

echo "WSL2 environment ready!"
EOF

# Make startup script executable
chmod +x /opt/gpu-infrastructure/scripts/wsl-startup.sh

# Create log directory
mkdir -p /opt/gpu-infrastructure/logs

# Test startup script
/opt/gpu-infrastructure/scripts/wsl-startup.sh
```

---

## ✅ Section 1 Complete

You have successfully completed the WSL2 setup and basic configuration. Your system now has:

- ✅ WSL2 enabled with Ubuntu 24.04
- ✅ Optimized resource allocation (128GB RAM for TwinTower1/2, 256GB for TwinTower3)
- ✅ Multi-tower configuration detection and setup
- ✅ Essential packages installed
- ✅ Directory structure created
- ✅ System monitoring scripts configured
- ✅ User environment optimized for AMD Ryzen 9 3950X

**Hardware Configuration Detected:**
- **TwinTower3**: 2x RTX 5090, 256GB RAM, Primary role
- **TwinTower1/2**: 1x RTX 4090 each, 128GB RAM each, Secondary role

**Next Section**: Continue with Section 2 (NVIDIA GPU Configuration) to install GPU drivers and CUDA toolkit.

[⬆️ Back to TOC](#-table-of-contents)
