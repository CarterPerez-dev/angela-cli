.PHONY: install uninstall dev-setup clean test lint format

# Installation
install:
	@echo "Installing Angela CLI..."
	bash scripts/install.sh

uninstall:
	@echo "Uninstalling Angela CLI..."
	bash scripts/uninstall.sh

# Development
dev-setup:
	@echo "Setting up development environment..."
	pip install -e ".[dev]"
	@echo "Development environment set up successfully!"

# Testing
test:
	@echo "Running tests..."
	pytest

# Linting and formatting
lint:
	@echo "Running linters..."
	flake8 angela tests
	mypy angela tests

format:
	@echo "Formatting code..."
	black angela tests
	isort angela tests

# Cleaning
clean:
	@echo "Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete!"

# Help
help:
	@echo "Angela CLI Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make install      Install Angela CLI"
	@echo "  make uninstall    Uninstall Angela CLI"
	@echo "  make dev-setup    Set up development environment"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo "  make clean        Clean up build artifacts"
	@echo "  make help         Show this help message"

# Default target
.DEFAULT_GOAL := help
