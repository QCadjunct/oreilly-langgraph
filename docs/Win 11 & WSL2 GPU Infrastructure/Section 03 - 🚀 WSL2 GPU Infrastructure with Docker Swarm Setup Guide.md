[⬆️ Back to TOC](#-table-of-contents)

---

## 🐳 Section 3: Docker Swarm and Container Infrastructure
> # Section 3 (Docker Swarm and Container Infrastructure) to set up orchestration across your tower cluster.

This section establishes a Docker Swarm cluster across your TwinTower infrastructure, enabling seamless GPU workload orchestration and resource management across multiple machines.

### Docker Installation and Configuration

**Step 1: Install Docker Engine in WSL2**

```bash
# Remove any existing Docker installations
sudo apt-get remove docker docker-engine docker.io containerd runc

# Update package database
sudo apt update

# Install prerequisites
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common

# Add Docker's official GPG key
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package database with Docker repo
sudo apt update

# Install Docker Engine, containerd, and Docker Compose
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker
```

**Step 2: Configure Docker Daemon for GPU Swarm**

```bash
# Create Docker daemon configuration for GPU and Swarm
sudo mkdir -p /etc/docker

sudo tee /etc/docker/daemon.json << 'EOF'
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    },
    "exec-opts": ["native.cgroupdriver=systemd"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "5"
    },
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.override_kernel_check=true"
    ],
    "live-restore": true,
    "userland-proxy": false,
    "experimental": false,
    "features": {
        "buildkit": true
    },
    "insecure-registries": ["172.16.0.0/12", "192.168.0.0/16"],
    "registry-mirrors": [],
    "dns": ["8.8.8.8", "1.1.1.1"],
    "metrics-addr": "0.0.0.0:9323",
    "experimental": true,
    "ipv6": false,
    "fixed-cidr": "172.17.0.0/16"
}
EOF

# Set proper permissions
sudo chmod 644 /etc/docker/daemon.json

# Restart Docker with new configuration
sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl enable docker

# Verify Docker installation
docker --version
docker compose version
```

**Step 3: Test Docker GPU Integration**

```bash
# Test basic Docker functionality
docker run hello-world

# Test GPU access with your CUDA 12.9.1 image
docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 nvidia-smi

# Verify Docker daemon configuration
docker system info | grep -A 10 "Runtimes"

# Check GPU resource detection
docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 \
    bash -c "echo 'GPUs available: '$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits)"
```

**Step 4: Configure Docker Network for Multi-Tower Setup**

```bash
# Create custom bridge network for local containers
docker network create --driver bridge \
    --subnet=172.20.0.0/16 \
    --gateway=172.20.0.1 \
    --opt com.docker.network.bridge.name=docker-gpu \
    gpu-local

# Verify network creation
docker network ls
docker network inspect gpu-local
```

[⬆️ Back to TOC](#-table-of-contents)

### Docker Swarm Cluster Setup

**Step 1: Initialize Docker Swarm on Primary Tower**

Execute this step **only on TwinTower3** (the primary tower with 2x RTX 5090):

```bash
# Load system configuration
source /opt/gpu-infrastructure/config/system-config.sh

# Get the primary IP address for Swarm
SWARM_IP=$(ip route get 1.1.1.1 | awk '{print $7}' | head -1)
echo "Primary Tower IP: $SWARM_IP"

# Initialize Docker Swarm (TwinTower3 as manager)
docker swarm init --advertise-addr $SWARM_IP

# Save the join tokens for worker nodes
docker swarm join-token worker > /opt/gpu-infrastructure/config/docker-swarm/worker-token.txt
docker swarm join-token manager > /opt/gpu-infrastructure/config/docker-swarm/manager-token.txt

# Display join commands for other towers
echo "=== Worker Join Command for TwinTower1 & TwinTower2 ==="
cat /opt/gpu-infrastructure/config/docker-swarm/worker-token.txt

# Create overlay network for multi-tower communication
docker network create --driver overlay --attachable gpu-cluster

# Label the manager node
docker node update --label-add tower=twintower3 --label-add role=primary --label-add gpu=rtx5090x2 $(docker node ls --format "{{.ID}}" --filter role=manager)
```

**Step 2: Join Worker Nodes (TwinTower1 & TwinTower2)**

Execute this step on **TwinTower1 and TwinTower2**:

```bash
# Load system configuration
source /opt/gpu-infrastructure/config/system-config.sh

echo "Joining $TOWER_NAME to Docker Swarm..."

# Replace <JOIN_COMMAND> with the actual command from TwinTower3
# Example: docker swarm join --token SWMTKN-1-... 192.168.1.100:2377
<COPY_JOIN_COMMAND_FROM_TWINTOWER3>

# After joining, label this node (run on TwinTower3)
# For TwinTower1:
# docker node update --label-add tower=twintower1 --label-add role=worker --label-add gpu=rtx4090x1 <NODE_ID>
# For TwinTower2:  
# docker node update --label-add tower=twintower2 --label-add role=worker --label-add gpu=rtx4090x1 <NODE_ID>
```

**Step 3: Configure Node Labels and Constraints (Run on TwinTower3)**

```bash
# Get node IDs and current status
docker node ls

# Label nodes based on their capabilities
# Replace <NODE_ID_TOWER1> and <NODE_ID_TOWER2> with actual node IDs

# Label TwinTower1
TOWER1_ID=$(docker node ls --format "{{.ID}} {{.Hostname}}" | grep -i tower1 | awk '{print $1}')
if [ ! -z "$TOWER1_ID" ]; then
    docker node update --label-add tower=twintower1 \
                       --label-add role=worker \
                       --label-add gpu=rtx4090x1 \
                       --label-add gpu_count=1 \
                       --label-add memory=128gb \
                       --label-add cpu_cores=16 $TOWER1_ID
fi

# Label TwinTower2  
TOWER2_ID=$(docker node ls --format "{{.ID}} {{.Hostname}}" | grep -i tower2 | awk '{print $1}')
if [ ! -z "$TOWER2_ID" ]; then
    docker node update --label-add tower=twintower2 \
                       --label-add role=worker \
                       --label-add gpu=rtx4090x1 \
                       --label-add gpu_count=1 \
                       --label-add memory=128gb \
                       --label-add cpu_cores=16 $TOWER2_ID
fi

# Label TwinTower3 (manager)
TOWER3_ID=$(docker node ls --format "{{.ID}} {{.Hostname}}" | grep -i tower3 | awk '{print $1}')
if [ ! -z "$TOWER3_ID" ]; then
    docker node update --label-add tower=twintower3 \
                       --label-add role=primary \
                       --label-add gpu=rtx5090x2 \
                       --label-add gpu_count=2 \
                       --label-add memory=256gb \
                       --label-add cpu_cores=16 $TOWER3_ID
fi

# Verify node labels
docker node ls
docker node inspect --pretty $(docker node ls --format "{{.ID}}")
```

**Step 4: Create Swarm Networks and Storage**

```bash
# Create overlay networks for different service types
docker network create --driver overlay --attachable \
    --subnet=10.0.1.0/24 \
    --opt encrypted=true \
    gpu-ai-workloads

docker network create --driver overlay --attachable \
    --subnet=10.0.2.0/24 \
    --opt encrypted=true \
    gpu-inference

docker network create --driver overlay --attachable \
    --subnet=10.0.3.0/24 \
    --opt encrypted=true \
    gpu-training

docker network create --driver overlay --attachable \
    --subnet=10.0.4.0/24 \
    gpu-monitoring

# Verify networks
docker network ls | grep overlay
```

[⬆️ Back to TOC](#-table-of-contents)

### Inter-Tower Networking

**Step 1: Configure Host Network Discovery**

Create network discovery script for automatic node detection:

```bash
# Create network discovery script
cat > /opt/gpu-infrastructure/scripts/discover-towers.sh << 'EOF'
#!/bin/bash

echo "=== TwinTower Network Discovery ==="

# Function to ping and identify towers
discover_tower() {
    local ip=$1
    local tower_name=$2
    
    if ping -c 1 -W 1 $ip &>/dev/null; then
        echo "✅ $tower_name ($ip) - Online"
        
        # Try to get hostname
        hostname=$(nslookup $ip 2>/dev/null | grep "name =" | awk '{print $4}' | sed 's/\.$//')
        if [ ! -z "$hostname" ]; then
            echo "   Hostname: $hostname"
        fi
        
        # Check if Docker is running (port 2376/2377)
        if nc -z $ip 2377 2>/dev/null; then
            echo "   🐳 Docker Swarm: Available"
        fi
        
        return 0
    else
        echo "❌ $tower_name ($ip) - Offline"
        return 1
    fi
}

# Common IP ranges to scan (adjust based on your network)
echo "Scanning common network ranges..."

# Typical home/office networks
for subnet in "192.168.1" "192.168.0" "10.0.0" "172.16.0"; do
    echo ""
    echo "🔍 Scanning ${subnet}.x network..."
    
    for i in {1..254}; do
        ip="${subnet}.${i}"
        
        # Quick ping test
        if ping -c 1 -W 0.5 $ip &>/dev/null; then
            # Get hostname if possible
            hostname=$(nslookup $ip 2>/dev/null | grep "name =" | awk '{print $4}' | sed 's/\.$//' | tr '[:upper:]' '[:lower:]')
            
            # Check if it's a TwinTower
            if [[ $hostname == *"tower"* ]] || [[ $hostname == *"twin"* ]]; then
                echo "🏗️  Found potential tower: $ip ($hostname)"
                
                # Test Docker connectivity
                if nc -z $ip 2377 2>/dev/null; then
                    echo "   🐳 Docker Swarm port open"
                fi
            fi
        fi
    done
done

echo ""
echo "=== Manual Tower Configuration ==="
echo "If automatic discovery failed, manually configure:"
echo "TwinTower1: ssh user@<TOWER1_IP>"
echo "TwinTower2: ssh user@<TOWER2_IP>"  
echo "TwinTower3: ssh user@<TOWER3_IP>"
echo ""
echo "Current node ($(hostname)):"
echo "IP: $(ip route get 1.1.1.1 | awk '{print $7}' | head -1)"
echo "Docker status: $(systemctl is-active docker)"
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/discover-towers.sh

# Run discovery
/opt/gpu-infrastructure/scripts/discover-towers.sh
```

**Step 2: Configure SSH Access Between Towers**

```bash
# Generate SSH key for inter-tower communication
ssh-keygen -t ed25519 -f ~/.ssh/twintower_cluster -N "" -C "twintower-cluster-$(hostname)"

# Display public key for sharing
echo "=== SSH Public Key for Other Towers ==="
echo "Copy this key to ~/.ssh/authorized_keys on other towers:"
echo ""
cat ~/.ssh/twintower_cluster.pub
echo ""

# Create SSH config for easy tower access
cat > ~/.ssh/config << 'EOF'
# TwinTower Cluster SSH Configuration

Host twintower1
    HostName <TWINTOWER1_IP>
    User ubuntu
    IdentityFile ~/.ssh/twintower_cluster
    Port 22
    StrictHostKeyChecking no

Host twintower2  
    HostName <TWINTOWER2_IP>
    User ubuntu
    IdentityFile ~/.ssh/twintower_cluster
    Port 22
    StrictHostKeyChecking no

Host twintower3
    HostName <TWINTOWER3_IP>
    User ubuntu
    IdentityFile ~/.ssh/twintower_cluster
    Port 22
    StrictHostKeyChecking no
EOF

echo "Update ~/.ssh/config with actual IP addresses, then test:"
echo "ssh twintower1"
echo "ssh twintower2"
echo "ssh twintower3"
```

**Step 3: Configure Docker Swarm Security**

```bash
# Configure Docker Swarm certificate rotation
docker swarm ca --rotate

# Create Docker secrets for sensitive data
echo "docker-registry-password" | docker secret create registry-password -
echo "gpu-cluster-api-key" | docker secret create gpu-api-key -

# Configure Docker Swarm logging
sudo mkdir -p /var/log/docker-swarm
sudo chown $USER:$USER /var/log/docker-swarm

# Create log rotation configuration
sudo tee /etc/logrotate.d/docker-swarm << 'EOF'
/var/log/docker-swarm/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
```

[⬆️ Back to TOC](#-table-of-contents)

### GPU-Aware Container Orchestration

**Step 1: Create GPU Resource Templates**

```bash
# Create GPU service templates directory
mkdir -p /opt/gpu-infrastructure/docker/templates

# Template for RTX 5090 workloads (TwinTower3)
cat > /opt/gpu-infrastructure/docker/templates/rtx5090-service.yml << 'EOF'
version: '3.8'

services:
  gpu-workload-5090:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    networks:
      - gpu-ai-workloads
    deploy:
      placement:
        constraints:
          - node.labels.gpu == rtx5090x2
          - node.role == manager
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 200G
          cpus: '14'
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=all
    volumes:
      - gpu-5090-data:/data
      - type: bind
        source: /opt/gpu-infrastructure/data/shared
        target: /shared

volumes:
  gpu-5090-data:
    driver: local

networks:
  gpu-ai-workloads:
    external: true
EOF

# Template for RTX 4090 workloads (TwinTower1/2)
cat > /opt/gpu-infrastructure/docker/templates/rtx4090-service.yml << 'EOF'
version: '3.8'

services:
  gpu-workload-4090:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    networks:
      - gpu-inference
    deploy:
      placement:
        constraints:
          - node.labels.gpu == rtx4090x1
          - node.role == worker
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 100G
          cpus: '14'
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=all
    volumes:
      - gpu-4090-data:/data
      - type: bind
        source: /opt/gpu-infrastructure/data/shared
        target: /shared

volumes:
  gpu-4090-data:
    driver: local

networks:
  gpu-inference:
    external: true
EOF

# Template for distributed training across all towers
cat > /opt/gpu-infrastructure/docker/templates/distributed-training.yml << 'EOF'
version: '3.8'

services:
  training-master:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    networks:
      - gpu-training
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower3
      replicas: 1
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 200G
          cpus: '14'
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - MASTER_ADDR=training-master
      - MASTER_PORT=29500
      - WORLD_SIZE=4
      - RANK=0
    command: |
      bash -c "
        echo 'Training Master Node (TwinTower3)'
        echo 'GPUs available: '$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits)
        nvidia-smi
        tail -f /dev/null
      "

  training-worker-1:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    networks:
      - gpu-training
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower1
      replicas: 1
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 100G
          cpus: '14'
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - MASTER_ADDR=training-master
      - MASTER_PORT=29500
      - WORLD_SIZE=4
      - RANK=1
    command: |
      bash -c "
        echo 'Training Worker 1 (TwinTower1)'
        echo 'GPUs available: '$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits)
        nvidia-smi
        tail -f /dev/null
      "

  training-worker-2:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    networks:
      - gpu-training
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower2
      replicas: 1
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 100G
          cpus: '14'
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - MASTER_ADDR=training-master
      - MASTER_PORT=29500
      - WORLD_SIZE=4
      - RANK=2
    command: |
      bash -c "
        echo 'Training Worker 2 (TwinTower2)'
        echo 'GPUs available: '$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits)
        nvidia-smi
        tail -f /dev/null
      "

networks:
  gpu-training:
    external: true
EOF
```

**Step 2: Create GPU Resource Management Scripts**

```bash
# Create GPU resource allocation script
cat > /opt/gpu-infrastructure/scripts/gpu-swarm-manager.sh << 'EOF'
#!/bin/bash

# GPU Swarm Resource Manager
source /opt/gpu-infrastructure/config/system-config.sh

show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  status                 - Show cluster GPU status"
    echo "  deploy [service]       - Deploy GPU service"
    echo "  scale [service] [n]    - Scale service to n replicas"  
    echo "  migrate [service] [tower] - Migrate service to specific tower"
    echo "  balance               - Balance GPU load across towers"
    echo ""
    echo "Services: ollama, training, inference"
    echo "Towers: twintower1, twintower2, twintower3"
}

show_cluster_status() {
    echo "=== TwinTower GPU Cluster Status ==="
    echo ""
    
    # Show node status
    echo "🏗️ Cluster Nodes:"
    docker node ls
    echo ""
    
    # Show GPU services
    echo "🎮 GPU Services:"
    docker service ls
    echo ""
    
    # Show network status
    echo "🌐 Overlay Networks:"
    docker network ls | grep overlay
    echo ""
    
    # Show GPU utilization per node
    echo "📊 GPU Utilization by Tower:"
    for node in $(docker node ls --format "{{.Hostname}}"); do
        echo "  $node:"
        docker node inspect $node --format "{{range .Spec.Labels}}{{.}}{{end}}" | grep -o "gpu=[^,]*"
    done
}

deploy_service() {
    local service=$1
    
    case $service in
        "ollama")
            echo "Deploying Ollama on TwinTower3 (RTX 5090x2)..."
            docker stack deploy -c /opt/gpu-infrastructure/docker/ollama/docker-compose.yml ollama-stack
            ;;
        "training")
            echo "Deploying distributed training across all towers..."
            docker stack deploy -c /opt/gpu-infrastructure/docker/templates/distributed-training.yml training-stack
            ;;
        "inference")
            echo "Deploying inference services on TwinTower1 & 2..."
            docker stack deploy -c /opt/gpu-infrastructure/docker/templates/rtx4090-service.yml inference-stack
            ;;
        *)
            echo "Unknown service: $service"
            show_usage
            ;;
    esac
}

scale_service() {
    local service=$1
    local replicas=$2
    
    if [ -z "$service" ] || [ -z "$replicas" ]; then
        echo "Error: Service and replica count required"
        show_usage
        return 1
    fi
    
    echo "Scaling $service to $replicas replicas..."
    docker service scale ${service}=${replicas}
}

balance_load() {
    echo "🔄 Balancing GPU load across TwinTower cluster..."
    
    # Get current service distribution
    echo "Current service distribution:"
    docker service ps $(docker service ls --format "{{.Name}}") --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"
    
    echo ""
    echo "Load balancing recommendations:"
    echo "- High-memory models: TwinTower3 (2x RTX 5090, 32GB each)"
    echo "- Inference workloads: TwinTower1/2 (RTX 4090, 24GB each)"
    echo "- Distributed training: All towers"
}

# Main command dispatcher
case $1 in
    "status")
        show_cluster_status
        ;;
    "deploy")
        deploy_service $2
        ;;
    "scale")
        scale_service $2 $3
        ;;
    "balance")
        balance_load
        ;;
    *)
        show_usage
        ;;
esac
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/gpu-swarm-manager.sh

# Test cluster status
/opt/gpu-infrastructure/scripts/gpu-swarm-manager.sh status
```

[⬆️ Back to TOC](#-table-of-contents)

### Service Templates and Deployment

**Step 1: Create Ollama AI Service for TwinTower3**

```bash
# Create Ollama service directory
mkdir -p /opt/gpu-infrastructure/docker/ollama

# Create Ollama Docker Compose for Swarm
cat > /opt/gpu-infrastructure/docker/ollama/docker-compose.yml << 'EOF'
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    networks:
      - gpu-ai-workloads
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower3
          - node.labels.gpu == rtx5090x2
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 180G
          cpus: '12'
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_MODELS=/models
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=all
    volumes:
      - ollama-models:/root/.ollama
      - ollama-data:/data
      - type: bind
        source: /opt/gpu-infrastructure/data/shared/models
        target: /models
    command: ollama serve

  ollama-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "8080:8080"
    networks:
      - gpu-ai-workloads
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower3
      resources:
        limits:
          memory: 4G
          cpus: '2'
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_SECRET_KEY=your-secret-key-here
    volumes:
      - ollama-webui-data:/app/backend/data
    depends_on:
      - ollama

volumes:
  ollama-models:
    driver: local
  ollama-data:
    driver: local
  ollama-webui-data:
    driver: local

networks:
  gpu-ai-workloads:
    external: true
  gpu-monitoring:
    external: true
EOF

# Deploy Ollama service
echo "Deploying Ollama service to TwinTower3..."
docker stack deploy -c /opt/gpu-infrastructure/docker/ollama/docker-compose.yml ollama-stack

# Verify deployment
docker service ls | grep ollama
docker service ps ollama-stack_ollama
```

**Step 2: Create Distributed Inference Service**

```bash
# Create inference service directory
mkdir -p /opt/gpu-infrastructure/docker/inference

# Create inference service for TwinTower1 & 2
cat > /opt/gpu-infrastructure/docker/inference/docker-compose.yml << 'EOF'
version: '3.8'

services:
  inference-worker-1:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    networks:
      - gpu-inference
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower1
          - node.labels.gpu == rtx4090x1
      replicas: 1
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 90G
          cpus: '14'
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=all
      - WORKER_ID=tower1
      - INFERENCE_PORT=8001
    volumes:
      - inference-data-1:/data
      - type: bind
        source: /opt/gpu-infrastructure/data/shared
        target: /shared
    command: |
      bash -c "
        echo 'Inference Worker 1 (TwinTower1) starting...'
        echo 'GPU: '$(nvidia-smi --query-gpu=name --format=csv,noheader)
    command: |
      bash -c "
        echo 'Inference Worker 1 (TwinTower1) starting...'
        echo 'GPU: '$(nvidia-smi --query-gpu=name --format=csv,noheader)
        echo 'Memory: '$(nvidia-smi --query-gpu=memory.total --format=csv,noheader)
        echo 'Starting inference server on port 8001...'
        python3 -m http.server 8001 &
        tail -f /dev/null
      "

  inference-worker-2:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    networks:
      - gpu-inference
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower2
          - node.labels.gpu == rtx4090x1
      replicas: 1
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
        limits:
          memory: 90G
          cpus: '14'
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=all
      - WORKER_ID=tower2
      - INFERENCE_PORT=8002
    volumes:
      - inference-data-2:/data
      - type: bind
        source: /opt/gpu-infrastructure/data/shared
        target: /shared
    command: |
      bash -c "
        echo 'Inference Worker 2 (TwinTower2) starting...'
        echo 'GPU: '$(nvidia-smi --query-gpu=name --format=csv,noheader)
        echo 'Memory: '$(nvidia-smi --query-gpu=memory.total --format=csv,noheader)
        echo 'Starting inference server on port 8002...'
        python3 -m http.server 8002 &
        tail -f /dev/null
      "

  inference-load-balancer:
    image: nginx:alpine
    ports:
      - "8000:80"
    networks:
      - gpu-inference
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower3
      replicas: 1
    configs:
      - source: nginx-inference-config
        target: /etc/nginx/nginx.conf
    depends_on:
      - inference-worker-1
      - inference-worker-2

volumes:
  inference-data-1:
    driver: local
  inference-data-2:
    driver: local

networks:
  gpu-inference:
    external: true
  gpu-monitoring:
    external: true

configs:
  nginx-inference-config:
    external: true
EOF

# Create NGINX load balancer configuration
docker config create nginx-inference-config - << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream inference_backend {
        server inference-worker-1:8001;
        server inference-worker-2:8002;
    }

    server {
        listen 80;
        location / {
            proxy_pass http://inference_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# Deploy inference service
echo "Deploying distributed inference service..."
docker stack deploy -c /opt/gpu-infrastructure/docker/inference/docker-compose.yml inference-stack

# Verify deployment
docker service ls | grep inference
```

[⬆️ Back to TOC](#-table-of-contents)

### Cluster Management and Monitoring

**Step 1: Create Cluster Monitoring Stack**

```bash
# Create monitoring directory
mkdir -p /opt/gpu-infrastructure/docker/monitoring

# Create comprehensive monitoring stack
cat > /opt/gpu-infrastructure/docker/monitoring/docker-compose.yml << 'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    networks:
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower3
      resources:
        limits:
          memory: 8G
          cpus: '4'
    volumes:
      - prometheus-data:/prometheus
      - type: bind
        source: /opt/gpu-infrastructure/docker/monitoring/prometheus.yml
        target: /etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    networks:
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower3
      resources:
        limits:
          memory: 4G
          cpus: '2'
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-piechart-panel

  nvidia-exporter-tower1:
    image: mindprince/nvidia_gpu_prometheus_exporter:latest
    ports:
      - "9445:9445"
    networks:
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower1
      resources:
        limits:
          memory: 512M
          cpus: '1'
    volumes:
      - /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:ro

  nvidia-exporter-tower2:
    image: mindprince/nvidia_gpu_prometheus_exporter:latest
    ports:
      - "9446:9445"
    networks:
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower2
      resources:
        limits:
          memory: 512M
          cpus: '1'
    volumes:
      - /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:ro

  nvidia-exporter-tower3:
    image: mindprince/nvidia_gpu_prometheus_exporter:latest
    ports:
      - "9447:9445"
    networks:
      - gpu-monitoring
    deploy:
      placement:
        constraints:
          - node.labels.tower == twintower3
      resources:
        limits:
          memory: 512M
          cpus: '1'
    volumes:
      - /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:ro

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    networks:
      - gpu-monitoring
    deploy:
      mode: global
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($|/)'

volumes:
  prometheus-data:
    driver: local
  grafana-data:
    driver: local

networks:
  gpu-monitoring:
    external: true
EOF

# Create Prometheus configuration
cat > /opt/gpu-infrastructure/docker/monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "gpu_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'nvidia-gpu-tower1'
    static_configs:
      - targets: ['nvidia-exporter-tower1:9445']
    scrape_interval: 5s

  - job_name: 'nvidia-gpu-tower2'
    static_configs:
      - targets: ['nvidia-exporter-tower2:9445']
    scrape_interval: 5s

  - job_name: 'nvidia-gpu-tower3'
    static_configs:
      - targets: ['nvidia-exporter-tower3:9445']
    scrape_interval: 5s

  - job_name: 'docker-swarm'
    static_configs:
      - targets: ['localhost:9323']

alerting:
  alertmanagers:
    - static_configs:
        - targets: []
EOF

# Deploy monitoring stack
echo "Deploying monitoring stack..."
docker stack deploy -c /opt/gpu-infrastructure/docker/monitoring/docker-compose.yml monitoring-stack

# Verify monitoring deployment
docker service ls | grep monitoring
```

**Step 2: Create Cluster Management Dashboard**

```bash
# Create cluster management script
cat > /opt/gpu-infrastructure/scripts/cluster-dashboard.sh << 'EOF'
#!/bin/bash

# TwinTower Cluster Management Dashboard
clear

show_header() {
    echo "════════════════════════════════════════════════════════════════════════════════"
    echo "🏗️  TwinTower GPU Cluster Management Dashboard"
    echo "════════════════════════════════════════════════════════════════════════════════"
    echo "Date: $(date)"
    echo "Manager: $(hostname)"
    echo "════════════════════════════════════════════════════════════════════════════════"
}

show_cluster_overview() {
    echo ""
    echo "🌐 CLUSTER OVERVIEW"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    # Node status
    echo "📊 Nodes Status:"
    docker node ls --format "table {{.ID}}\t{{.Hostname}}\t{{.Status}}\t{{.Availability}}\t{{.ManagerStatus}}"
    
    echo ""
    echo "🎮 GPU Resources by Tower:"
    
    # TwinTower3 (Manager)
    echo "  🏗️  TwinTower3 (Manager):"
    echo "    └── 2x RTX 5090 (32GB each) - Primary AI workloads"
    
    # TwinTower1 (Worker)
    echo "  🏗️  TwinTower1 (Worker):"
    echo "    └── 1x RTX 4090 (24GB) - Inference workloads"
    
    # TwinTower2 (Worker)
    echo "  🏗️  TwinTower2 (Worker):"
    echo "    └── 1x RTX 4090 (24GB) - Inference workloads"
    
    echo ""
    echo "📈 Total Cluster Resources:"
    echo "  └── GPUs: 4 total (2x RTX 5090 + 2x RTX 4090)"
    echo "  └── GPU Memory: 112GB total (64GB + 48GB)"
    echo "  └── CPU Cores: 48 total (16 per tower)"
    echo "  └── System Memory: 512GB total (256GB + 128GB + 128GB)"
}

show_services_status() {
    echo ""
    echo "🐳 SERVICES STATUS"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    # Check if services are running
    SERVICES=$(docker service ls --format "{{.Name}}" 2>/dev/null)
    
    if [ -z "$SERVICES" ]; then
        echo "  ❌ No services currently running"
        return
    fi
    
    echo "🏃 Running Services:"
    docker service ls --format "table {{.Name}}\t{{.Mode}}\t{{.Replicas}}\t{{.Image}}"
    
    echo ""
    echo "📍 Service Placement:"
    docker service ps $(docker service ls --format "{{.Name}}") --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}" 2>/dev/null || echo "  No services to display"
}

show_gpu_utilization() {
    echo ""
    echo "🎮 GPU UTILIZATION"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    # Check if nvidia-smi is available
    if ! command -v nvidia-smi &> /dev/null; then
        echo "  ❌ nvidia-smi not available on manager node"
        return
    fi
    
    echo "📊 Local GPU Status ($(hostname)):"
    nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader | \
    while IFS=, read -r index name util mem_used mem_total temp; do
        echo "  GPU $index: $name"
        echo "    ├── Utilization: $util"
        echo "    ├── Memory: $mem_used / $mem_total"
        echo "    └── Temperature: $temp"
    done
    
    echo ""
    echo "🌡️  Cluster GPU Summary:"
    echo "  └── Access Grafana dashboard: http://$(hostname):3000 (admin/admin)"
    echo "  └── Prometheus metrics: http://$(hostname):9090"
}

show_networking() {
    echo ""
    echo "🌐 NETWORKING"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    echo "🔗 Overlay Networks:"
    docker network ls --filter driver=overlay --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}"
    
    echo ""
    echo "🔌 Published Ports:"
    docker service ls --format "{{.Name}}\t{{.Ports}}" | grep -v "<none>" | \
    while read -r name ports; do
        if [ "$ports" != "<none>" ]; then
            echo "  $name: $ports"
        fi
    done
}

show_quick_actions() {
    echo ""
    echo "⚡ QUICK ACTIONS"
    echo "────────────────────────────────────────────────────────────────────────────────"
    echo "🚀 Deploy Services:"
    echo "  └── ./gpu-swarm-manager.sh deploy ollama    # Deploy Ollama on TwinTower3"
    echo "  └── ./gpu-swarm-manager.sh deploy inference # Deploy inference on TwinTower1/2"
    echo "  └── ./gpu-swarm-manager.sh deploy training  # Deploy distributed training"
    echo ""
    echo "📊 Monitoring:"
    echo "  └── Grafana: http://$(hostname):3000"
    echo "  └── Prometheus: http://$(hostname):9090"
    echo "  └── Ollama UI: http://$(hostname):8080"
    echo ""
    echo "🔧 Management:"
    echo "  └── ./gpu-swarm-manager.sh status          # Show detailed status"
    echo "  └── ./gpu-swarm-manager.sh balance         # Balance GPU workloads"
    echo "  └── docker service logs <service>          # View service logs"
}

# Main dashboard display
show_header
show_cluster_overview
show_services_status
show_gpu_utilization
show_networking
show_quick_actions

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "🔄 Dashboard refreshes every 30 seconds. Press Ctrl+C to exit."
echo "════════════════════════════════════════════════════════════════════════════════"
EOF

# Make dashboard executable
chmod +x /opt/gpu-infrastructure/scripts/cluster-dashboard.sh

# Create dashboard service
cat > /opt/gpu-infrastructure/scripts/start-dashboard.sh << 'EOF'
#!/bin/bash

# Start interactive cluster dashboard
while true; do
    /opt/gpu-infrastructure/scripts/cluster-dashboard.sh
    sleep 30
    clear
done
EOF

chmod +x /opt/gpu-infrastructure/scripts/start-dashboard.sh

# Run dashboard once
/opt/gpu-infrastructure/scripts/cluster-dashboard.sh
```

---

## ✅ Section 3 Complete

You have successfully configured Docker Swarm and container infrastructure across your TwinTower cluster. Your system now has:

- ✅ Docker Swarm cluster with TwinTower3 as manager, TwinTower1/2 as workers
- ✅ GPU-aware container orchestration with proper resource allocation
- ✅ Overlay networks for secure inter-tower communication
- ✅ Service templates for RTX 5090 and RTX 4090 workloads
- ✅ Ollama AI service deployed on TwinTower3
- ✅ Distributed inference service across TwinTower1/2
- ✅ Comprehensive monitoring with Prometheus and Grafana
- ✅ Cluster management dashboard and automation scripts

**Docker Swarm Configuration Summary:**
- **TwinTower3**: Manager node with 2x RTX 5090 for primary AI workloads
- **TwinTower1**: Worker node with 1x RTX 4090 for inference
- **TwinTower2**: Worker node with 1x RTX 4090 for inference
- **Networks**: Secure overlay networks for different workload types
- **Monitoring**: Real-time GPU and cluster monitoring across all towers

**Next Section**: Continue with Section 4 (Storage Management with VHDX) to configure persistent storage and data management.

[⬆️ Back to TOC](#-table-of-contents)# 🚀 WSL2 GPU Infrastructure with Docker Swarm Setup Guide

## 📋 Table of Contents

- [🔧 Section 1: System Prerequisites and WSL2 Setup](#-section-1-system-prerequisites-and-wsl2-setup)
  - [System Requirements](#system-requirements)
  - [Enable WSL2 Features](#enable-wsl2-features)
  - [Install Ubuntu 24.04](#install-ubuntu-2404)
  - [Configure WSL2 Resource Limits](#configure-wsl2-resource-limits)
  - [Initial Ubuntu Configuration](#initial-ubuntu-configuration)
  - [Verify Installation](#verify-installation)
- [🎮 Section 2: NVIDIA GPU Configuration](#-section-2-nvidia-gpu-configuration)
  - [Windows NVIDIA Driver Installation](#windows-nvidia-driver-installation)
  - [WSL2 CUDA Setup](#wsl2-cuda-setup)
  - [NVIDIA Container Toolkit](#nvidia-container-toolkit)
  - [GPU Detection and Verification](#gpu-detection-and-verification)
  - [Multi-GPU Configuration](#multi-gpu-configuration)
  - [Performance Optimization](#performance-optimization)
- [🐳 Section 3: Docker Swarm and Container Infrastructure](#-section-3-docker-swarm-and-container-infrastructure)
  - [Docker Installation and Configuration](#docker-installation-and-configuration)
  - [Docker Swarm Cluster Setup](#docker-swarm-cluster-setup)
  - [Inter-Tower Networking](#inter-tower-networking)
  - [GPU-Aware Container Orchestration](#gpu-aware-container-orchestration)
  - [Service Templates and Deployment](#service-templates-and-deployment)
  - [Cluster Management and Monitoring](#cluster-management-and-monitoring)

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

**Step 4: Verify CUDA Compatibility Matrix**

Before proceeding, verify that your NVIDIA driver supports CUDA 12.9.1:

```powershell
# Check current NVIDIA driver version
nvidia-smi

# CUDA 12.9.1 requires NVIDIA driver version 550.54.15 or newer
# RTX 4090/5090 recommendations:
# - Minimum: 550.54.15
# - Recommended: 560.x or newer (latest stable)

# If driver is too old, download latest from:
# https://www.nvidia.com/drivers
```

**CUDA Version Compatibility Reference:**
- **CUDA 12.9.1**: Requires driver ≥ 550.54.15
- **CUDA 12.6**: Requires driver ≥ 525.60.13  
- **Your Setup**: Host CUDA 12.6 + Container CUDA 12.9.1 = ✅ Compatible

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

---

## 🎮 Section 2: NVIDIA GPU Configuration

This section configures NVIDIA drivers and CUDA toolkit for optimal GPU performance across your TwinTower infrastructure. We'll set up GPU access for both WSL2 containers and Hyper-V VMs.

### Windows NVIDIA Driver Installation

**Step 1: Download Latest NVIDIA Drivers (Manual Process)**

**Important**: You **must** manually download and install the correct NVIDIA drivers for your specific GPU configuration.

**For TwinTower3 (RTX 5090 x2):**
1. Navigate to: https://www.nvidia.com/Download/index.aspx
2. Configure download settings:
   - **Product Type**: GeForce
   - **Product Series**: GeForce RTX 50 Series
   - **Product**: GeForce RTX 5090
   - **Operating System**: Windows 11
   - **Download Type**: Game Ready Driver (recommended) or Studio Driver
3. Click **"Search"** then **"Download"**

**For TwinTower1/2 (RTX 4090 x1 each):**
1. Navigate to: https://www.nvidia.com/Download/index.aspx
2. Configure download settings:
   - **Product Type**: GeForce
   - **Product Series**: GeForce RTX 40 Series
   - **Product**: GeForce RTX 4090
   - **Operating System**: Windows 11
   - **Download Type**: Game Ready Driver (recommended) or Studio Driver
3. Click **"Search"** then **"Download"**

**Alternative: Use NVIDIA App (Recommended)**
```powershell
# Download NVIDIA App for automated driver management
Start-Process "https://www.nvidia.com/en-us/software/nvidia-app/"

# The NVIDIA App provides:
# - Automatic driver detection and updates
# - Optimal settings for your specific GPU
# - Game and application optimization
```

**Verify Driver Requirements for CUDA 12.9.1:**
- **Minimum Required**: Driver version ≥ 550.54.15
- **Recommended**: Latest available (560.x+ series)
- **Check current**: Open Command Prompt and run `nvidia-smi`

**Step 2: Install NVIDIA Drivers with Custom Options**

**Critical Installation Steps:**

1. **Run as Administrator**: Right-click the downloaded `.exe` file → "Run as administrator"

2. **Choose Installation Type**: 
   - Select **"Custom (Advanced)"** installation
   - **DO NOT** use Express installation for development work

3. **Select Components** (Check ALL of the following):
   ```
   ✅ Display driver
   ✅ NVIDIA Control Panel  
   ✅ NVIDIA GeForce Experience (optional, but recommended)
   ✅ NVIDIA PhysX System Software
   ✅ NVIDIA HD Audio driver
   ✅ NVIDIA USB-C driver (if applicable)
   ✅ NVIDIA Broadcast (optional)
   ```

4. **Installation Options**:
   - ✅ **Check "Perform a clean installation"** (removes old drivers completely)
   - ✅ **Check "NVIDIA Graphics Driver and GeForce Experience"**

5. **Complete Installation**:
   - Click **"Install"** and wait for completion (5-10 minutes)
   - **Restart your computer when prompted** (critical step)

**Post-Installation Verification:**
```powershell
# After restart, verify installation
nvidia-smi

# Expected output should show:
# - Driver Version: 560.x or newer
# - CUDA Version: 12.6 or newer  
# - Your GPU(s): RTX 4090/5090
# - No error messages
```

**Troubleshooting Common Issues:**
```powershell
# If nvidia-smi fails:
# 1. Ensure Windows is fully updated
Get-WindowsUpdate -AcceptAll -Install

# 2. Check Device Manager for GPU detection
devmgmt.msc

# 3. Verify no driver conflicts
pnputil /enum-drivers | findstr NVIDIA
```

**Step 4: Verify Windows GPU Installation and Compatibility**

**Comprehensive Driver Verification:**

```powershell
# 1. Basic GPU Detection
nvidia-smi

# 2. Detailed GPU Information
nvidia-smi --query-gpu=index,name,driver_version,cuda_version,memory.total,power.max_limit --format=csv

# 3. Check CUDA Compatibility for 12.9.1
$DriverVersion = nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | Select-Object -First 1
$DriverMajor = [int]($DriverVersion -split '\.')[0]
$DriverMinor = [int]($DriverVersion -split '\.')[1]

Write-Host "Current Driver: $DriverVersion"
if (($DriverMajor -gt 550) -or (($DriverMajor -eq 550) -and ($DriverMinor -ge 54))) {
    Write-Host "✅ Driver supports CUDA 12.9.1" -ForegroundColor Green
} else {
    Write-Host "❌ Driver too old for CUDA 12.9.1 (need ≥550.54.15)" -ForegroundColor Red
    Write-Host "📥 Please download latest driver from nvidia.com" -ForegroundColor Yellow
}

# 4. Verify Multi-GPU Setup (for TwinTower3)
$GPUCount = nvidia-smi --query-gpu=count --format=csv,noheader,nounits
Write-Host "Detected GPUs: $GPUCount"

# 5. Check Windows GPU Recognition
Get-WmiObject Win32_VideoController | Where-Object {$_.Name -like "*NVIDIA*"} | Select-Object Name, DriverVersion, AdapterRAM

# 6. Verify GPU Power and Thermal Limits
nvidia-smi --query-gpu=index,name,temperature.gpu,power.draw,power.limit --format=csv
```

**Expected Results by Tower:**

**TwinTower3 (2x RTX 5090):**
```
Expected Output:
- GPU Count: 2
- GPU 0: NVIDIA GeForce RTX 5090, 32GB
- GPU 1: NVIDIA GeForce RTX 5090, 32GB  
- Driver: ≥550.54.15
- Power Limit: ~575W each
```

**TwinTower1/2 (1x RTX 4090 each):**
```
Expected Output:
- GPU Count: 1
- GPU 0: NVIDIA GeForce RTX 4090, 24GB
- Driver: ≥550.54.15  
- Power Limit: ~450W
```

**Troubleshooting Failed Installation:**
```powershell
# If installation failed or GPUs not detected:

# 1. Check Windows Update
Get-WindowsUpdate -AcceptAll -AutoReboot

# 2. Verify Secure Boot (should be disabled for some GPUs)
bcdedit /enum {current} | findstr -i "testsigning"

# 3. Check BIOS settings
# - Ensure "Above 4G Decoding" is enabled
# - Ensure "Re-Size BAR Support" is enabled  
# - Ensure all PCIe slots are set to Gen4/Gen5

# 4. Clean driver installation
# Download DDU (Display Driver Uninstaller)
# Boot to Safe Mode → Run DDU → Reinstall drivers

# 5. Check Event Viewer for errors
eventvwr.msc
# Navigate: Windows Logs → System → Filter for NVIDIA errors
```

**Step 3: Configure NVIDIA Control Panel for Development**

**Essential NVIDIA Control Panel Configuration:**

1. **Open NVIDIA Control Panel**:
   - Right-click desktop → "NVIDIA Control Panel"
   - Or: Start Menu → Search "NVIDIA Control Panel"

2. **Configure Global 3D Settings**:
   ```
   Navigate: 3D Settings → Manage 3D settings → Global Settings
   
   Key Settings for GPU Infrastructure:
   ✅ CUDA - GPUs: "All"
   ✅ Power management mode: "Prefer maximum performance"  
   ✅ Texture filtering - Quality: "High performance"
   ✅ Threaded optimization: "On"
   ✅ Virtual Reality pre-rendered frames: "1"
   ```

3. **Configure Program-Specific Settings**:
   ```
   Navigate: 3D Settings → Manage 3D settings → Program Settings
   
   Add programs:
   - docker.exe → Max performance, All GPUs
   - wsl.exe → Max performance, All GPUs
   - Any AI/ML applications you plan to use
   ```

4. **Multi-GPU Configuration** (TwinTower3 only):
   ```
   Navigate: 3D Settings → Set up multiple displays → Configure multi-GPU
   
   Settings:
   ✅ Enable "Maximize 3D performance"
   ✅ Set rendering mode: "Single display performance mode"
   ```

5. **Apply and Save**:
   - Click "Apply" for all changes
   - Restart computer to ensure settings take effect

**Verify NVIDIA Control Panel Settings:**
```powershell
# Check if settings applied correctly
nvidia-smi --query-gpu=index,name,persistence_mode,power.management --format=csv,noheader
```

[⬆️ Back to TOC](#-table-of-contents)

### WSL2 CUDA Setup

**Step 1: Verify WSL2 GPU Passthrough**

```bash
# In WSL2 Ubuntu, check if GPUs are visible
lspci | grep -i nvidia

# Expected output should show your NVIDIA GPUs
# If no output, GPU passthrough may not be working
```

**Step 2: Install CUDA Keyring and Repository**

```bash
# Remove any existing CUDA installations
sudo apt-get --purge remove "*cuda*" "*cublas*" "*cufft*" "*cufile*" "*curand*" "*cusolver*" "*cusparse*" "*npp*" "*nvjpeg*" "nsight*" "*nvvm*"

# Update package list
sudo apt update

# Install prerequisites
sudo apt install -y wget software-properties-common

# Download and install CUDA keyring
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb

# Update package list with CUDA repository
sudo apt update
```

**Step 3: Install CUDA Toolkit**

```bash
# Install CUDA toolkit (latest stable version)
sudo apt install -y cuda-toolkit-12-6

# Install additional CUDA libraries
sudo apt install -y cuda-drivers-fabricmanager-535 cuda-drivers-535
```

**Step 4: Configure CUDA Environment**

```bash
# Add CUDA to PATH and LD_LIBRARY_PATH
cat >> ~/.bashrc << 'EOF'

# CUDA Configuration
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# NVIDIA GPU Configuration
export NVIDIA_VISIBLE_DEVICES=all
export NVIDIA_DRIVER_CAPABILITIES=compute,utility
EOF

# Reload environment
source ~/.bashrc

# Verify CUDA installation
nvcc --version
```

[⬆️ Back to TOC](#-table-of-contents)

### NVIDIA Container Toolkit

**Step 1: Install Docker (if not already installed)**

```bash
# Update package index
sudo apt update

# Install dependencies
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
sudo apt update

# Install Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
```

**Step 2: Install NVIDIA Container Toolkit**

```bash
# Configure NVIDIA Container Toolkit repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
    && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Update package list
sudo apt update

# Install NVIDIA Container Toolkit
sudo apt install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker

# Restart Docker service
sudo systemctl restart docker
```

**Step 3: Configure Docker Daemon for GPU Support**

```bash
# Create Docker daemon configuration
sudo mkdir -p /etc/docker

# Configure Docker daemon with NVIDIA runtime
sudo tee /etc/docker/daemon.json << 'EOF'
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    },
    "exec-opts": ["native.cgroupdriver=systemd"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m"
    },
    "storage-driver": "overlay2"
}
EOF

# Restart Docker to apply configuration
sudo systemctl restart docker

**Step 4: Advanced Container Runtime Configuration**

Configure additional runtime options for optimal GPU container performance:

```bash
# Create advanced NVIDIA container runtime configuration
sudo tee /etc/nvidia-container-runtime/config.toml << 'EOF'
disable-require = false
swarm-resource = "DOCKER_RESOURCE_GPU"

[nvidia-container-cli]
environment = []
debug = "/var/log/nvidia-container-toolkit.log"
ldcache = "/etc/ld.so.cache"
load-kmods = true
no-cgroups = false
user = "root:video"

[nvidia-container-runtime]
debug = "/var/log/nvidia-container-runtime.log"
log-level = "info"

# Runtimes for different CUDA versions
[nvidia-container-runtime.runtimes.nvidia]
path = "nvidia-container-runtime"

[nvidia-container-runtime.runtimes.nvidia-legacy]
path = "nvidia-container-runtime-legacy"
EOF

# Set proper permissions
sudo chmod 644 /etc/nvidia-container-runtime/config.toml

# Update Docker daemon with additional GPU configurations
sudo tee /etc/docker/daemon.json << 'EOF'
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        },
        "nvidia-legacy": {
            "path": "nvidia-container-runtime-legacy",
            "runtimeArgs": []
        }
    },
    "exec-opts": ["native.cgroupdriver=systemd"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.override_kernel_check=true"
    ],
    "live-restore": true,
    "userland-proxy": false,
    "experimental": false,
    "features": {
        "buildkit": true
    }
}
EOF

# Restart Docker to apply advanced configuration
sudo systemctl restart docker

# Verify advanced runtime is working
docker info | grep -i runtime
```

**Step 5: Pre-pull and Verify CUDA Images**

```bash
# Pre-pull your specific CUDA image
echo "Pulling CUDA 12.9.1 with cuDNN development image..."
docker pull nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04

# Pull additional useful CUDA images for different purposes
docker pull nvidia/cuda:12.9.1-base-ubuntu24.04        # Minimal CUDA runtime
docker pull nvidia/cuda:12.9.1-runtime-ubuntu24.04     # CUDA runtime libraries
docker pull nvidia/cuda:12.9.1-devel-ubuntu24.04       # CUDA development (no cuDNN)

# Verify image layers and size
docker images | grep "nvidia/cuda.*12.9.1"

# Test the specific image you need
echo "Testing CUDA 12.9.1 cuDNN development environment..."
docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 bash -c "
    echo 'CUDA Version:' && nvcc --version && echo ''
    echo 'cuDNN Files:' && find /usr -name '*cudnn*' -type f | head -5 && echo ''
    echo 'GPU Detection:' && nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader && echo ''
    echo 'CUDA Samples:' && ls /usr/local/cuda/samples/ 2>/dev/null | head -3 || echo 'Samples not included in this image'
"
```

[⬆️ Back to TOC](#-table-of-contents)

### GPU Detection and Verification

**Step 1: Test NVIDIA GPU Access**

```bash
# Test nvidia-smi in WSL2
nvidia-smi

# Expected output should show:
# - Driver version
# - CUDA version
# - GPU(s) information (RTX 4090/5090)
# - Memory usage
# - Temperature and power consumption
```

**Step 2: Test Docker GPU Access**

```bash
# Test Docker with GPU support
docker run --rm --gpus all nvidia/cuda:12.6-base-ubuntu22.04 nvidia-smi

# Test specific GPU selection
docker run --rm --gpus device=0 nvidia/cuda:12.6-base-ubuntu22.04 nvidia-smi

# Test CUDA compute capability
docker run --rm --gpus all nvidia/cuda:12.6-devel-ubuntu22.04 nvcc --version
```

**Step 3: Create GPU Detection Script**

```bash
# Create comprehensive GPU detection script
cat > /opt/gpu-infrastructure/scripts/gpu-detection.sh << 'EOF'
#!/bin/bash

echo "=== GPU Infrastructure Detection ==="
echo "Date: $(date)"
echo "System: $(hostname)"
echo ""

# Load system configuration
source /opt/gpu-infrastructure/config/system-config.sh

echo "=== System Configuration ==="
echo "Tower: $TOWER_NAME"
echo "Expected GPUs: $GPU_COUNT x $GPU_TYPE"
echo "Role: $ROLE"
echo ""

echo "=== NVIDIA Driver Information ==="
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA Driver Version: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -1)"
    echo "CUDA Version: $(nvidia-smi --query-gpu=cuda_version --format=csv,noheader,nounits | head -1)"
else
    echo "NVIDIA drivers not found or not accessible"
fi
echo ""

echo "=== Detected GPUs ==="
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=index,name,memory.total,temperature.gpu,power.draw --format=csv,noheader
else
    echo "No GPUs detected"
fi
echo ""

echo "=== Docker GPU Support ==="
if command -v docker &> /dev/null; then
    echo "Docker Version: $(docker --version)"
    echo "Testing GPU access..."
    if docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 nvidia-smi --query-gpu=count --format=csv,noheader,nounits &>/dev/null; then
        GPU_COUNT_DOCKER=$(docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 nvidia-smi --query-gpu=count --format=csv,noheader,nounits | head -1)
        echo "Docker GPU Access: ✅ Success ($GPU_COUNT_DOCKER GPUs accessible)"
    else
        echo "Docker GPU Access: ❌ Failed"
    fi
else
    echo "Docker not installed"
fi
echo ""

echo "=== CUDA Toolkit ==="
if command -v nvcc &> /dev/null; then
    echo "NVCC Version: $(nvcc --version | grep release | awk '{print $6}' | cut -c2-)"
    echo "CUDA Installation: ✅ Success"
else
    echo "CUDA Toolkit: ❌ Not found"
fi
echo ""

echo "=== GPU Memory Usage ==="
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv
fi
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/gpu-detection.sh

# Run GPU detection
/opt/gpu-infrastructure/scripts/gpu-detection.sh
```

[⬆️ Back to TOC](#-table-of-contents)

### Multi-GPU Configuration

**Step 1: Configure Multi-GPU Docker Compose**

```bash
# Create multi-GPU test configuration
cat > /opt/gpu-infrastructure/docker/gpu-test.yml << 'EOF'
version: '3.8'

services:
  gpu-test-all:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    command: >
      bash -c "
        echo 'Testing all GPUs...' &&
        nvidia-smi &&
        echo 'CUDA device count:' &&
        python3 -c 'import torch; print(f\"PyTorch CUDA devices: {torch.cuda.device_count()}\")' 2>/dev/null || echo 'PyTorch not installed' &&
        echo 'cuDNN availability:' &&
        find /usr -name '*cudnn*' -type f | head -3 &&
        sleep 300
      "
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all

  gpu-test-specific:
    image: nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04
    command: >
      bash -c "
        echo 'Testing specific GPU...' &&
        nvidia-smi &&
        sleep 300
      "
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
EOF
```

**Step 4: Create Advanced GPU Testing Suite**

```bash
# Create comprehensive GPU testing with your specific CUDA version
cat > /opt/gpu-infrastructure/scripts/cuda-compatibility-test.sh << 'EOF'
#!/bin/bash

echo "=== CUDA 12.9.1 Compatibility Test Suite ==="
echo "Date: $(date)"
echo ""

# Test 1: Host NVIDIA Driver Compatibility
echo "🔍 Test 1: NVIDIA Driver Version Check"
if command -v nvidia-smi &> /dev/null; then
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -1)
    echo "  Current Driver: $DRIVER_VERSION"
    
    # Extract major version number
    DRIVER_MAJOR=$(echo $DRIVER_VERSION | cut -d'.' -f1)
    
    if [ "$DRIVER_MAJOR" -ge 550 ]; then
        echo "  ✅ Driver supports CUDA 12.9.1 (requires ≥550.54.15)"
    else
        echo "  ❌ Driver too old for CUDA 12.9.1 (requires ≥550.54.15)"
        echo "  📥 Download latest driver from: https://www.nvidia.com/drivers"
    fi
else
    echo "  ❌ NVIDIA driver not found"
fi

# Test 2: Container Runtime Test
echo ""
echo "🔍 Test 2: CUDA 12.9.1 Container Runtime"
if docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 nvidia-smi &>/dev/null; then
    echo "  ✅ CUDA 12.9.1 container runtime working"
    
    # Get container CUDA version
    CONTAINER_CUDA=$(docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 nvcc --version | grep "release" | awk '{print $6}' | cut -c2-)
    echo "  📊 Container CUDA version: $CONTAINER_CUDA"
else
    echo "  ❌ CUDA 12.9.1 container runtime failed"
fi

# Test 3: cuDNN Libraries Test
echo ""
echo "🔍 Test 3: cuDNN Libraries in Container"
CUDNN_FILES=$(docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 \
    bash -c "find /usr -name '*cudnn*' -type f 2>/dev/null | wc -l")

if [ "$CUDNN_FILES" -gt 0 ]; then
    echo "  ✅ cuDNN libraries found: $CUDNN_FILES files"
    
    # Show sample cuDNN files
    echo "  📁 Sample cuDNN files:"
    docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 \
        bash -c "find /usr -name '*cudnn*' -type f 2>/dev/null | head -3" | sed 's/^/    /'
else
    echo "  ❌ cuDNN libraries not found"
fi

# Test 4: GPU Memory and Compute Test
echo ""
echo "🔍 Test 4: GPU Compute Capability"
docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 bash -c "
    echo '  GPU Information:'
    nvidia-smi --query-gpu=index,name,compute_cap,memory.total --format=csv,noheader | sed 's/^/    /'
    echo ''
    echo '  CUDA Compute Test:'
    if command -v deviceQuery &>/dev/null; then
        deviceQuery | grep -E 'Device|CUDA Capability|Total amount' | sed 's/^/    /'
    else
        echo '    deviceQuery not available in this image'
    fi
"

# Test 5: Multi-GPU Test (if applicable)
echo ""
echo "🔍 Test 5: Multi-GPU Configuration"
GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits | head -1)
if [ "$GPU_COUNT" -gt 1 ]; then
    echo "  🔍 Testing $GPU_COUNT GPUs individually:"
    for ((i=0; i<GPU_COUNT; i++)); do
        if docker run --rm --gpus device=$i nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 \
            nvidia-smi --query-gpu=index,name --format=csv,noheader -i 0 &>/dev/null; then
            GPU_NAME=$(docker run --rm --gpus device=$i nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 \
                nvidia-smi --query-gpu=name --format=csv,noheader -i 0)
            echo "    ✅ GPU $i: $GPU_NAME"
        else
            echo "    ❌ GPU $i: Not accessible"
        fi
    done
else
    echo "  📊 Single GPU system detected"
fi

echo ""
echo "=== Test Summary ==="
echo "✅ CUDA 12.9.1 compatibility test complete"
echo "🔧 If any tests failed, check:"
echo "   1. NVIDIA driver version (≥550.54.15 required)"
echo "   2. NVIDIA Container Toolkit installation"
echo "   3. Docker daemon GPU runtime configuration"
echo "   4. WSL2 GPU passthrough setup"
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/cuda-compatibility-test.sh

# Run CUDA compatibility test
/opt/gpu-infrastructure/scripts/cuda-compatibility-test.sh
```

```bash
# Test all GPUs
docker compose -f /opt/gpu-infrastructure/docker/gpu-test.yml up gpu-test-all

# Test specific GPU
docker compose -f /opt/gpu-infrastructure/docker/gpu-test.yml up gpu-test-specific

# Clean up test containers
docker compose -f /opt/gpu-infrastructure/docker/gpu-test.yml down
```

**Step 3: Configure GPU Resource Allocation for CUDA 12.9.1**

```bash
# Update GPU resource allocation script for CUDA 12.9.1
cat > /opt/gpu-infrastructure/scripts/gpu-allocation-129.sh << 'EOF'
#!/bin/bash

# Load system configuration
source /opt/gpu-infrastructure/config/system-config.sh

echo "=== GPU Resource Allocation for $TOWER_NAME (CUDA 12.9.1) ==="

# Test CUDA 12.9.1 compatibility first
echo "🔍 Verifying CUDA 12.9.1 compatibility..."
if docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 nvcc --version &>/dev/null; then
    echo "  ✅ CUDA 12.9.1 runtime verified"
else
    echo "  ❌ CUDA 12.9.1 runtime failed - check driver compatibility"
    exit 1
fi

case $TOWER_ID in
    "3")
        echo ""
        echo "🏗️ TwinTower3 Configuration (2x RTX 5090):"
        echo "  - GPU 0: Primary workloads (Large model training, Ollama main)"
        echo "  - GPU 1: Secondary workloads (Inference, preprocessing)"
        echo ""
        echo "📋 Recommended Docker configurations:"
        echo "  Primary (GPU 0):   --gpus device=0 nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04"
        echo "  Secondary (GPU 1): --gpus device=1 nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04"
        echo "  All GPUs:          --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04"
        echo ""
        echo "⚡ RTX 5090 Specifications per GPU:"
        echo "  - CUDA Cores: 21,760"
        echo "  - RT Cores: 3rd Gen"
        echo "  - Memory: 32GB GDDR7"
        echo "  - Memory Bandwidth: ~1,500 GB/s"
        echo "  - Power: 575W max"
        ;;
    "1"|"2")
        echo ""
        echo "🏗️ TwinTower$TOWER_ID Configuration (1x RTX 4090):"
        echo "  - GPU 0: All workloads (optimized for single-GPU tasks)"
        echo ""
        echo "📋 Recommended Docker configurations:"
        echo "  Single GPU: --gpus device=0 nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04"
        echo "  All GPUs:   --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04"
        echo ""
        echo "⚡ RTX 4090 Specifications:"
        echo "  - CUDA Cores: 16,384"
        echo "  - RT Cores: 3rd Gen"
        echo "  - Memory: 24GB GDDR6X"
        echo "  - Memory Bandwidth: ~1,000 GB/s"
        echo "  - Power: 450W max"
        ;;
esac

echo ""
echo "🔧 CUDA 12.9.1 Specific Optimizations:"
echo "  - Tensor Core support: 4th Gen (RTX 5090) / 3rd Gen (RTX 4090)"
echo "  - Mixed precision training: FP16, BF16, INT8"
echo "  - cuDNN 9.x acceleration for deep learning"
echo "  - NVIDIA Transformer Engine compatibility"

echo ""
echo "📊 Current GPU Status:"
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv

echo ""
echo "🧪 Quick CUDA 12.9.1 Test:"
docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 bash -c "
    echo 'GPU Count: '$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits)
    echo 'CUDA Version: '$(nvcc --version | grep release | awk '{print \$6}' | cut -c2-)
    echo 'cuDNN Status: '$(find /usr -name '*cudnn*' -type f | wc -l)' files found'
"
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/gpu-allocation-129.sh

# Run allocation script
/opt/gpu-infrastructure/scripts/gpu-allocation-129.sh
```

```bash
# Create GPU resource allocation script
cat > /opt/gpu-infrastructure/scripts/gpu-allocation.sh << 'EOF'
#!/bin/bash

# Load system configuration
source /opt/gpu-infrastructure/config/system-config.sh

echo "=== GPU Resource Allocation for $TOWER_NAME ==="

case $TOWER_ID in
    "3")
        echo "TwinTower3 Configuration (2x RTX 5090):"
        echo "- GPU 0: Primary workloads (Ollama, Training)"
        echo "- GPU 1: Secondary workloads (Inference, Processing)"
        echo ""
        echo "Recommended Docker configurations:"
        echo "  Primary: --gpus device=0"
        echo "  Secondary: --gpus device=1"
        echo "  All GPUs: --gpus all"
        ;;
    "1"|"2")
        echo "TwinTower$TOWER_ID Configuration (1x RTX 4090):"
        echo "- GPU 0: All workloads"
        echo ""
        echo "Recommended Docker configurations:"
        echo "  Single GPU: --gpus device=0"
        echo "  All GPUs: --gpus all"
        ;;
esac

echo ""
echo "Current GPU Status:"
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/gpu-allocation.sh

# Run allocation script
/opt/gpu-infrastructure/scripts/gpu-allocation.sh
```

[⬆️ Back to TOC](#-table-of-contents)

### Performance Optimization

**Step 1: Configure GPU Performance Settings**

```bash
# Create GPU performance optimization script
cat > /opt/gpu-infrastructure/scripts/gpu-optimize.sh << 'EOF'
#!/bin/bash

echo "=== GPU Performance Optimization ==="

# Set GPU performance mode (requires root)
if command -v nvidia-smi &> /dev/null; then
    echo "Setting GPU performance mode..."
    
    # Set persistence mode (keeps driver loaded)
    sudo nvidia-smi -pm 1
    
    # Set power limit to maximum (adjust based on your PSU)
    # RTX 4090: 450W, RTX 5090: 575W
    GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits)
    
    for ((i=0; i<GPU_COUNT; i++)); do
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits -i $i)
        echo "Optimizing GPU $i: $GPU_NAME"
        
        if [[ $GPU_NAME == *"5090"* ]]; then
            sudo nvidia-smi -pl 575 -i $i  # RTX 5090 max power
        elif [[ $GPU_NAME == *"4090"* ]]; then
            sudo nvidia-smi -pl 450 -i $i  # RTX 4090 max power
        fi
        
        # Set compute mode to exclusive process
        sudo nvidia-smi -c 3 -i $i
    done
    
    echo "GPU optimization complete"
else
    echo "NVIDIA drivers not found"
fi

# Optimize system settings for GPU workloads
echo "Optimizing system settings..."

# Increase system limits for GPU workloads
sudo tee -a /etc/security/limits.conf << 'LIMITS'
# GPU Infrastructure limits
* soft memlock unlimited
* hard memlock unlimited
* soft nofile 1048576
* hard nofile 1048576
LIMITS

# Configure kernel parameters for GPU workloads
sudo tee -a /etc/sysctl.conf << 'SYSCTL'
# GPU Infrastructure optimizations
vm.max_map_count = 262144
kernel.shmmax = 68719476736
kernel.shmall = 4294967296
SYSCTL

# Apply sysctl changes
sudo sysctl -p

echo "System optimization complete"
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/gpu-optimize.sh

# Run optimization (will prompt for sudo)
/opt/gpu-infrastructure/scripts/gpu-optimize.sh
```

**Step 2: Configure Monitoring and Alerting**

```bash
# Create GPU monitoring script
cat > /opt/gpu-infrastructure/scripts/gpu-monitor.sh << 'EOF'
#!/bin/bash

LOGFILE="/opt/gpu-infrastructure/logs/gpu-monitoring.log"
ALERT_TEMP=85  # Alert if GPU temperature exceeds this
ALERT_MEM=90   # Alert if GPU memory usage exceeds this percentage

mkdir -p /opt/gpu-infrastructure/logs

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Get GPU metrics
    GPU_DATA=$(nvidia-smi --query-gpu=index,name,temperature.gpu,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader,nounits)
    
    echo "[$TIMESTAMP] GPU Status:" >> $LOGFILE
    echo "$GPU_DATA" >> $LOGFILE
    
    # Check for alerts
    while IFS=',' read -r index name temp mem_used mem_total util power; do
        # Remove leading/trailing spaces
        temp=$(echo $temp | xargs)
        mem_used=$(echo $mem_used | xargs)
        mem_total=$(echo $mem_total | xargs)
        
        # Calculate memory percentage
        if [ "$mem_total" -gt 0 ]; then
            mem_percent=$(( (mem_used * 100) / mem_total ))
        else
            mem_percent=0
        fi
        
        # Temperature alert
        if [ "$temp" -gt "$ALERT_TEMP" ]; then
            echo "[$TIMESTAMP] ALERT: GPU $index temperature high: ${temp}°C" >> $LOGFILE
        fi
        
        # Memory alert
        if [ "$mem_percent" -gt "$ALERT_MEM" ]; then
            echo "[$TIMESTAMP] ALERT: GPU $index memory high: ${mem_percent}%" >> $LOGFILE
        fi
        
    done <<< "$GPU_DATA"
    
    echo "" >> $LOGFILE
    sleep 60  # Monitor every minute
done
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/gpu-monitor.sh

# Create systemd service for GPU monitoring
sudo tee /etc/systemd/system/gpu-monitor.service << 'EOF'
[Unit]
Description=GPU Infrastructure Monitoring
After=multi-user.target

[Service]
Type=simple
User=ubuntu
ExecStart=/opt/gpu-infrastructure/scripts/gpu-monitor.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start monitoring service
sudo systemctl daemon-reload
sudo systemctl enable gpu-monitor.service
sudo systemctl start gpu-monitor.service

# Check service status
sudo systemctl status gpu-monitor.service
```

**Step 3: Create GPU Health Check Script**

```bash
# Create comprehensive GPU health check
cat > /opt/gpu-infrastructure/scripts/gpu-health-check.sh << 'EOF'
#!/bin/bash

echo "=== GPU Infrastructure Health Check ==="
echo "Date: $(date)"
echo "System: $(hostname)"
echo ""

# Load system configuration
source /opt/gpu-infrastructure/config/system-config.sh

ISSUES_FOUND=0

# Check NVIDIA driver
echo "🔍 Checking NVIDIA Driver..."
if command -v nvidia-smi &> /dev/null; then
    echo "  ✅ NVIDIA driver accessible"
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -1)
    echo "  📊 Driver version: $DRIVER_VERSION"
else
    echo "  ❌ NVIDIA driver not found"
    ((ISSUES_FOUND++))
fi

# Check GPU count
echo ""
echo "🔍 Checking GPU Count..."
if command -v nvidia-smi &> /dev/null; then
    DETECTED_GPUS=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits | head -1)
    if [ "$DETECTED_GPUS" -eq "$GPU_COUNT" ]; then
        echo "  ✅ Expected GPU count: $DETECTED_GPUS/$GPU_COUNT"
    else
        echo "  ❌ GPU count mismatch: $DETECTED_GPUS/$GPU_COUNT expected"
        ((ISSUES_FOUND++))
    fi
else
    echo "  ❌ Cannot check GPU count"
    ((ISSUES_FOUND++))
fi

# Check GPU temperatures
echo ""
echo "🔍 Checking GPU Temperatures..."
if command -v nvidia-smi &> /dev/null; then
    while IFS=',' read -r index temp; do
        temp=$(echo $temp | xargs)
        if [ "$temp" -lt 85 ]; then
            echo "  ✅ GPU $index: ${temp}°C (Normal)"
        elif [ "$temp" -lt 95 ]; then
            echo "  ⚠️  GPU $index: ${temp}°C (High)"
        else
            echo "  ❌ GPU $index: ${temp}°C (Critical)"
            ((ISSUES_FOUND++))
        fi
    done <<< "$(nvidia-smi --query-gpu=index,temperature.gpu --format=csv,noheader,nounits)"
fi

# Check Docker GPU access
echo ""
echo "🔍 Checking Docker GPU Access..."
if command -v docker &> /dev/null; then
    if docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 nvidia-smi --query-gpu=count --format=csv,noheader,nounits &>/dev/null; then
        echo "  ✅ Docker GPU access working"
        
        # Test cuDNN availability
        echo "  🔍 Checking cuDNN in containers..."
        CUDNN_CHECK=$(docker run --rm --gpus all nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04 \
            bash -c "find /usr -name '*cudnn*' -type f 2>/dev/null | wc -l")
        if [ "$CUDNN_CHECK" -gt 0 ]; then
            echo "  ✅ cuDNN libraries available in containers"
        else
            echo "  ⚠️  cuDNN libraries not found in containers"
        fi
    else
        echo "  ❌ Docker GPU access failed"
        ((ISSUES_FOUND++))
    fi
else
    echo "  ❌ Docker not found"
    ((ISSUES_FOUND++))
fi

# Check system resources
echo ""
echo "🔍 Checking System Resources..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

if (( $(echo "$MEMORY_USAGE < 90" | bc -l) )); then
    echo "  ✅ Memory usage: ${MEMORY_USAGE}%"
else
    echo "  ⚠️  Memory usage high: ${MEMORY_USAGE}%"
fi

if [ "$DISK_USAGE" -lt 90 ]; then
    echo "  ✅ Disk usage: ${DISK_USAGE}%"
else
    echo "  ⚠️  Disk usage high: ${DISK_USAGE}%"
fi

# Summary
echo ""
echo "=== Health Check Summary ==="
if [ "$ISSUES_FOUND" -eq 0 ]; then
    echo "🎉 All systems healthy! No issues found."
    exit 0
else
    echo "⚠️  Found $ISSUES_FOUND issue(s) that need attention."
    exit 1
fi
EOF

# Make script executable
chmod +x /opt/gpu-infrastructure/scripts/gpu-health-check.sh

# Run health check
/opt/gpu-infrastructure/scripts/gpu-health-check.sh
```

---

## ✅ Section 2 Complete

You have successfully configured NVIDIA GPU support for your WSL2 infrastructure. Your system now has:

- ✅ Latest NVIDIA drivers installed on Windows
- ✅ CUDA toolkit configured in WSL2
- ✅ NVIDIA Container Toolkit for Docker GPU support
- ✅ Multi-GPU configuration for TwinTower infrastructure
- ✅ Performance optimization and monitoring scripts
- ✅ Comprehensive GPU health checking

**GPU Configuration Summary:**
- **TwinTower3**: 2x RTX 5090 ready for containerized workloads
- **TwinTower1/2**: 1x RTX 4090 each ready for containerized workloads
- **Docker**: Full GPU passthrough support enabled
- **Monitoring**: Real-time GPU monitoring and alerting active

**Next Section**: Continue with Section 3 (Docker Swarm and Container Infrastructure) to set up orchestration across your tower cluster.

[⬆️ Back to TOC](#-table-of-contents)
