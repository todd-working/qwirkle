.PHONY: build run dev stop clean test help

# Build frontend and backend
build:
	docker compose run --rm frontend-dev sh -c "npm install && npm run build"
	docker compose build backend

# Run production (backend serves static files)
run: build
	docker compose up backend

# Run development with hot reload
dev:
	docker compose --profile dev up frontend-dev

# Stop all containers
stop:
	docker compose down

# Clean up containers, images, and build artifacts
clean:
	docker compose down --rmi local --volumes
	rm -rf src/web/frontend/dist
	rm -rf src/web/frontend/node_modules

# Run tests
test:
	docker compose run --rm frontend-dev sh -c "npm install && npm test"

# Show help
help:
	@echo "Available targets:"
	@echo "  build  - Build frontend and backend"
	@echo "  run    - Build and run production server (localhost:8000)"
	@echo "  dev    - Run frontend dev server with hot reload (localhost:5173)"
	@echo "  stop   - Stop all containers"
	@echo "  clean  - Remove containers, images, and build artifacts"
	@echo "  test   - Run tests"
