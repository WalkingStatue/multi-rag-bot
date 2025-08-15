.PHONY: install run clean stop logs

# Install all dependencies
install:
	@echo "Installing backend dependencies..."
	@cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Dependencies installed successfully!"

# Start the entire application
run:
	@echo "Starting Multi-Bot RAG Platform..."
	@docker-compose up --build

# Stop the application
stop:
	@echo "Stopping application..."
	@docker-compose down

# View logs
logs:
	@docker-compose logs -f

# Clean up containers and volumes
clean:
	@echo "Cleaning up containers and volumes..."
	@docker-compose down -v
	@docker system prune -f