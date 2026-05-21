.PHONY: dev backend frontend install test eval clean

# Default password for local dev
export APP_PASSWORD ?= basis
export BACKEND_URL ?= http://localhost:8000

# Start both services for local development
dev:
	@echo "Starting backend and frontend..."
	@make backend &
	@make frontend

# Start Python backend
backend:
	cd backend && source .venv/bin/activate && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Start Next.js frontend
frontend:
	cd frontend && npm run dev

# Install dependencies
install:
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install

# Run Python tests
test:
	cd backend && source .venv/bin/activate && pytest ../tests/ -v

# Run eval suite (requires backend running)
eval:
	cd backend && source .venv/bin/activate && python ../eval/run_eval.py

# Build Docker images
build:
	docker compose build

# Run with Docker
docker:
	docker compose up

# Clean build artifacts
clean:
	cd frontend && rm -rf .next node_modules
	cd backend && rm -rf .venv __pycache__ src/**/__pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
