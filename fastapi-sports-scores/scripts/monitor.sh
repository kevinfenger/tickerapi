#!/bin/bash

# Monitoring script for Sports API deployment
# Run this on your DigitalOcean droplet to monitor the application

COMPOSE_FILE="/opt/sports-api/docker-compose.prod.yml"
LOG_FILE="/var/log/sports-api-monitor.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_services() {
    log_message "Checking service status..."
    
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_message "❌ Some services are down. Attempting restart..."
        docker-compose -f "$COMPOSE_FILE" up -d
        sleep 30
    fi
}

check_health() {
    log_message "Checking application health..."
    
    # Check FastAPI health endpoint
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        log_message "✅ FastAPI health check passed"
    else
        log_message "❌ FastAPI health check failed"
        return 1
    fi
    
    # Check Redis
    if docker-compose -f "$COMPOSE_FILE" exec -T cache redis-cli ping >/dev/null 2>&1; then
        log_message "✅ Redis health check passed"
    else
        log_message "❌ Redis health check failed"
        return 1
    fi
}

check_disk_space() {
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 85 ]; then
        log_message "⚠️ High disk usage: ${DISK_USAGE}%"
        # Clean up Docker
        docker system prune -f
    fi
}

check_memory() {
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$MEMORY_USAGE" -gt 90 ]; then
        log_message "⚠️ High memory usage: ${MEMORY_USAGE}%"
    fi
}

# Main monitoring loop
log_message "🔍 Starting monitoring check..."

check_services
if check_health; then
    log_message "✅ All health checks passed"
else
    log_message "❌ Health checks failed, restarting services..."
    docker-compose -f "$COMPOSE_FILE" restart
    sleep 60
    if check_health; then
        log_message "✅ Services recovered after restart"
    else
        log_message "❌ Services still failing after restart - manual intervention required"
    fi
fi

check_disk_space
check_memory

# Show current status
log_message "📊 Current status:"
docker-compose -f "$COMPOSE_FILE" ps | tee -a "$LOG_FILE"

log_message "🏁 Monitoring check complete"