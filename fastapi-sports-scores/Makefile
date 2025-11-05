# Makefile for FastAPI Sports Scores Project

.PHONY: build up down logs restart status ip

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose down && docker-compose up -d

status:
	docker-compose ps

# Get the local IP address for network access
ip:
	@echo "Local IP addresses:"
	@ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $$2}'
	@echo ""
	@echo "Access the API from other devices using:"
	@echo "http://[YOUR_IP]:8000/docs"

# Quick development mode (with logs)
dev:
	docker-compose up

# Clean up everything
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f