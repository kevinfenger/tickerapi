#!/bin/bash

# DigitalOcean Droplet Setup Script
# Run this script on your DigitalOcean droplet to prepare for deployment

set -e

echo "🚀 Setting up DigitalOcean droplet for Sports API deployment..."

# Update system
echo "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create deploy user
echo "👤 Creating deploy user..."
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Setup SSH for deploy user
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/ || echo "No authorized_keys found, please add your SSH key manually"
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /opt/sports-api
chown deploy:deploy /opt/sports-api

# Install useful tools
echo "🛠️ Installing additional tools..."
apt-get install -y curl wget git htop nano vim ufw

# Setup firewall
echo "🔒 Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80
ufw allow 443
ufw --force enable

# Install fail2ban for security
echo "🛡️ Installing fail2ban..."
apt-get install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Create swap file (recommended for small droplets)
echo "💾 Setting up swap file..."
if [ ! -f /swapfile ]; then
    fallocate -l 1G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
fi

# Setup log rotation
echo "📝 Configuring log rotation..."
cat > /etc/logrotate.d/docker-logs << EOF
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=1M
    missingok
    delaycompress
    copytruncate
}
EOF

echo "✅ DigitalOcean droplet setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add your SSH public key to /home/deploy/.ssh/authorized_keys"
echo "2. Set up GitHub secrets in your repository:"
echo "   - DO_HOST: Your droplet's IP address"
echo "   - DO_USERNAME: deploy"
echo "   - DO_SSH_KEY: Your private SSH key"
echo "   - DO_PORT: 22 (or your custom SSH port)"
echo "3. Push your code to trigger the deployment"
echo ""
echo "🔧 Useful commands:"
echo "   - View logs: docker-compose -f /opt/sports-api/docker-compose.prod.yml logs -f"
echo "   - Restart services: docker-compose -f /opt/sports-api/docker-compose.prod.yml restart"
echo "   - Check status: docker-compose -f /opt/sports-api/docker-compose.prod.yml ps"