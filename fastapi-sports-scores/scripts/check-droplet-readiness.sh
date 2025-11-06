#!/bin/bash

# DigitalOcean Droplet Readiness Check
# Run this script on your droplet to see what's needed for deployment

echo "🔍 Checking DigitalOcean droplet readiness for Sports API deployment..."
echo "=================================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
READY=true

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo -e "✅ ${GREEN}$1 is installed${NC}"
        return 0
    else
        echo -e "❌ ${RED}$1 is NOT installed${NC}"
        READY=false
        return 1
    fi
}

check_service() {
    if systemctl is-active --quiet "$1" 2>/dev/null; then
        echo -e "✅ ${GREEN}$1 service is running${NC}"
        return 0
    else
        echo -e "❌ ${RED}$1 service is NOT running${NC}"
        READY=false
        return 1
    fi
}

check_permission() {
    if groups "$USER" | grep -q "$1"; then
        echo -e "✅ ${GREEN}User '$USER' is in $1 group${NC}"
        return 0
    else
        echo -e "❌ ${RED}User '$USER' is NOT in $1 group${NC}"
        READY=false
        return 1
    fi
}

# System Information
echo "📋 System Information:"
echo "   OS: $(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "   Kernel: $(uname -r)"
echo "   Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "   Disk: $(df -h / | awk 'NR==2 {print $4 " available"}')"
echo "   User: $USER"
echo ""

# Docker Check
echo "🐳 Docker Requirements:"
check_command "docker"
if command -v docker >/dev/null 2>&1; then
    echo "   Docker version: $(docker --version)"
    check_service "docker"
    check_permission "docker"
else
    echo -e "   ${YELLOW}Docker needs to be installed${NC}"
fi
echo ""

# Docker Compose Check
echo "🔧 Docker Compose Requirements:"
check_command "docker-compose"
if command -v docker-compose >/dev/null 2>&1; then
    echo "   Docker Compose version: $(docker-compose --version)"
else
    echo -e "   ${YELLOW}Docker Compose needs to be installed${NC}"
fi
echo ""

# Network & Ports
echo "🌐 Network & Port Requirements:"
if command -v ss >/dev/null 2>&1; then
    if ss -tuln | grep -q ":80 "; then
        echo -e "⚠️  ${YELLOW}Port 80 is already in use${NC}"
    else
        echo -e "✅ ${GREEN}Port 80 is available${NC}"
    fi
    
    if ss -tuln | grep -q ":443 "; then
        echo -e "⚠️  ${YELLOW}Port 443 is already in use${NC}"
    else
        echo -e "✅ ${GREEN}Port 443 is available${NC}"
    fi
else
    echo -e "⚠️  ${YELLOW}Cannot check port availability (ss command not found)${NC}"
fi
echo ""

# Firewall Check
echo "🔒 Security & Firewall:"
if command -v ufw >/dev/null 2>&1; then
    UFW_STATUS=$(ufw status | head -1)
    echo "   UFW Status: $UFW_STATUS"
    if echo "$UFW_STATUS" | grep -q "active"; then
        echo -e "✅ ${GREEN}UFW firewall is active${NC}"
    else
        echo -e "⚠️  ${YELLOW}UFW firewall is inactive${NC}"
    fi
else
    echo -e "⚠️  ${YELLOW}UFW firewall not installed${NC}"
fi
echo ""

# Directory Permissions
echo "📁 Directory & Permissions:"
TARGET_DIR="/opt/sports-api"
if [ -d "$TARGET_DIR" ]; then
    echo -e "✅ ${GREEN}$TARGET_DIR exists${NC}"
    if [ -w "$TARGET_DIR" ]; then
        echo -e "✅ ${GREEN}$TARGET_DIR is writable${NC}"
    else
        echo -e "❌ ${RED}$TARGET_DIR is NOT writable${NC}"
        READY=false
    fi
else
    echo -e "⚠️  ${YELLOW}$TARGET_DIR does not exist (will be created)${NC}"
    # Check if we can create it
    if [ -w "/opt" ] || sudo -n mkdir -p "$TARGET_DIR" 2>/dev/null; then
        echo -e "✅ ${GREEN}Can create $TARGET_DIR${NC}"
        sudo rmdir "$TARGET_DIR" 2>/dev/null
    else
        echo -e "❌ ${RED}Cannot create $TARGET_DIR${NC}"
        READY=false
    fi
fi
echo ""

# SSH & GitHub Container Registry
echo "🔑 SSH & Registry Access:"
if command -v curl >/dev/null 2>&1; then
    if curl -s https://ghcr.io >/dev/null; then
        echo -e "✅ ${GREEN}Can reach GitHub Container Registry${NC}"
    else
        echo -e "❌ ${RED}Cannot reach GitHub Container Registry${NC}"
        READY=false
    fi
else
    echo -e "⚠️  ${YELLOW}curl not available to test registry access${NC}"
fi
echo ""

# Overall Status
echo "📊 Overall Readiness:"
if [ "$READY" = true ]; then
    echo -e "🎉 ${GREEN}Your droplet appears ready for deployment!${NC}"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Set up GitHub secrets (DO_HOST, DO_USERNAME, DO_SSH_KEY, DO_PORT)"
    echo "   2. Push your code to trigger deployment"
else
    echo -e "⚠️  ${YELLOW}Your droplet needs some setup before deployment${NC}"
    echo ""
    echo "🔧 Recommended actions:"
    if ! command -v docker >/dev/null 2>&1; then
        echo "   - Install Docker: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    fi
    if ! command -v docker-compose >/dev/null 2>&1; then
        echo "   - Install Docker Compose: curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose"
    fi
    if ! groups "$USER" | grep -q "docker"; then
        echo "   - Add user to docker group: sudo usermod -aG docker $USER && newgrp docker"
    fi
    if ! systemctl is-active --quiet docker 2>/dev/null; then
        echo "   - Start Docker service: sudo systemctl enable docker && sudo systemctl start docker"
    fi
    echo ""
    echo "💡 Or run the full setup script: ./scripts/setup-digitalocean.sh"
fi

echo ""
echo "=================================================================="