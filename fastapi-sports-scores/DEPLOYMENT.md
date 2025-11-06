# DigitalOcean Deployment Guide

This guide will help you deploy the Sports API to DigitalOcean using GitHub Actions.

## Prerequisites

1. **DigitalOcean Account**: Create a droplet (Ubuntu 20.04+ recommended)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Domain Name** (optional): For custom domain and SSL

## Step 1: Prepare Your DigitalOcean Droplet

### Create a Droplet
1. Log in to DigitalOcean
2. Create a new droplet:
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: Basic plan, $12/month (2GB RAM, 1 vCPU) minimum
   - **Region**: Choose closest to your users
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: sports-api (or your preference)

### Setup the Droplet
1. SSH into your droplet:
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. Run the setup script:
   ```bash
   curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/scripts/setup-digitalocean.sh | bash
   ```

   Or manually copy and run the `scripts/setup-digitalocean.sh` script.

## Step 2: Configure GitHub Secrets

In your GitHub repository, go to Settings → Secrets and variables → Actions, and add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DO_HOST` | Your droplet's IP address | `164.90.XXX.XXX` |
| `DO_USERNAME` | SSH username (use 'deploy') | `deploy` |
| `DO_SSH_KEY` | Your private SSH key | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DO_PORT` | SSH port (usually 22) | `22` |

### Generating SSH Key for Deployment

If you don't have an SSH key specifically for deployment:

```bash
# Generate a new SSH key pair
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""

# Add the public key to your droplet
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@YOUR_DROPLET_IP

# Copy the private key content for GitHub secrets
cat ~/.ssh/deploy_key
```

## Step 3: Configure Your Application

### Environment Variables

The deployment supports these environment variables:

- `ENV`: Set to "production" for production deployment
- `REDIS_URL`: Redis connection URL (defaults to `redis://cache:6379`)

### SSL/HTTPS Setup (Optional)

To enable HTTPS:

1. Get SSL certificates (Let's Encrypt recommended):
   ```bash
   # Install certbot
   sudo apt install certbot

   # Get certificate (replace yourdomain.com)
   sudo certbot certonly --standalone -d yourdomain.com
   ```

2. Update the nginx configuration in the GitHub Action to use SSL:
   ```nginx
   ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
   ```

## Step 4: Deploy

1. **Push to main branch**: The GitHub Action will trigger automatically
2. **Monitor deployment**: Check the Actions tab in your GitHub repository
3. **Verify deployment**: Visit `http://YOUR_DROPLET_IP` to see your API

## Step 5: Monitoring and Maintenance

### Set up monitoring cron job
```bash
# SSH into your droplet
ssh deploy@YOUR_DROPLET_IP

# Make monitoring script executable
chmod +x /opt/sports-api/scripts/monitor.sh

# Add to crontab to run every 5 minutes
crontab -e
# Add this line:
*/5 * * * * /opt/sports-api/scripts/monitor.sh
```

### Useful Commands

```bash
# View application logs
docker-compose -f /opt/sports-api/docker-compose.prod.yml logs -f

# Restart services
docker-compose -f /opt/sports-api/docker-compose.prod.yml restart

# Check service status
docker-compose -f /opt/sports-api/docker-compose.prod.yml ps

# Update to latest version
docker-compose -f /opt/sports-api/docker-compose.prod.yml pull
docker-compose -f /opt/sports-api/docker-compose.prod.yml up -d

# Clean up old Docker images
docker system prune -af
```

## Troubleshooting

### Common Issues

1. **Port 8000 not accessible**:
   - Check firewall: `sudo ufw status`
   - Ensure Docker containers are running: `docker ps`

2. **GitHub Action fails**:
   - Verify all secrets are correctly set
   - Check SSH key has correct permissions
   - Ensure droplet has enough resources

3. **Application not responding**:
   - Check logs: `docker-compose logs`
   - Verify Redis is running: `docker-compose exec cache redis-cli ping`
   - Check disk space: `df -h`

4. **Memory issues**:
   - Monitor with: `htop`
   - Consider upgrading droplet size
   - Check for memory leaks in logs

### Log Locations

- Application logs: `docker-compose logs fastapi`
- Nginx logs: `docker-compose logs nginx`
- Redis logs: `docker-compose logs cache`
- System logs: `/var/log/syslog`
- Monitoring logs: `/var/log/sports-api-monitor.log`

## Performance Optimization

### For Production Traffic

1. **Scale up**: Upgrade to larger droplet
2. **Load balancing**: Use DigitalOcean Load Balancer
3. **Database**: Consider managed Redis or PostgreSQL
4. **CDN**: Use DigitalOcean Spaces + CDN for static assets
5. **Monitoring**: Set up DigitalOcean Monitoring alerts

### Cost Optimization

1. **Reserved instances**: For predictable workloads
2. **Auto-scaling**: Scale down during low traffic
3. **Resource monitoring**: Right-size your droplet

## Security Best Practices

1. **Regular updates**: Keep OS and Docker updated
2. **Firewall**: Only open necessary ports
3. **SSH security**: Use key-based auth, disable root login
4. **SSL/TLS**: Use HTTPS in production
5. **Secrets management**: Never commit secrets to git
6. **Monitoring**: Set up intrusion detection

## Backup Strategy

1. **Application data**: Backup persistent volumes
2. **Database snapshots**: Regular Redis backups
3. **Configuration**: Version control all configs
4. **Droplet snapshots**: DigitalOcean automatic backups

## Support

- **GitHub Issues**: Report bugs and feature requests
- **DigitalOcean Docs**: [Official documentation](https://docs.digitalocean.com/)
- **Community**: DigitalOcean Community tutorials