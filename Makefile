.PHONY: build build-no-cache up down logs clean dev run shell rebuild push

# Production build and run
build:
	docker compose build

build-no-cache:
	docker compose build --no-cache

up:
	docker compose up -d

# Production run with built frontend and backend
run:
	@echo "Building frontend for production..."
	@cd react && npx vite build
	@echo "Starting production server..."
	@cd server && python3 -m pip install -r requirements.txt --break-system-packages --user
	@cd server && python3 main.py --port 57988

# Quick rebuild (reuse cached layers)
rebuild: build up
rebuild-no-cache: build-no-cache up
publish: build push

# Development mode  
dev:
	@echo "Starting development mode locally..."
	@echo "Starting backend server..."
	@echo "Installing backend dependencies..."
	@cd server && python3 -m pip install -r requirements.txt --break-system-packages --user
	@cd server && python3 main.py --port 57988 &
# 	@sleep 3
	@echo "Starting frontend dev server..."
	@cd react && npm run dev -- --host

# Push image to Docker Hub
push:
	@echo "Tagging and pushing image to Docker Hub..."
	@docker tag jaaz:latest skynono/jaaz:latest
	@docker push skynono/jaaz:latest
	@echo "Getting version tag..."
	@VERSION=$$(git describe --tags --always --dirty) && \
		docker tag jaaz:latest skynono/jaaz:$$VERSION && \
		docker push skynono/jaaz:$$VERSION && \
		echo "✅ Image pushed successfully to skynono/jaaz:$$VERSION"
	@echo "✅ Image pushed successfully to skynono/jaaz:latest"

# Management
down:
	docker compose down

logs:
	docker compose logs -f jaaz

shell:
	docker compose exec jaaz bash

# Cleanup
clean:
	docker compose down -v --remove-orphans
	docker system prune -f