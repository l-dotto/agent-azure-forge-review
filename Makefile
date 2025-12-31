.PHONY: help install test lint format clean

help:
	@echo "Azure Code Reviewer - Development Commands"
	@echo ""
	@echo "make install    - Install dependencies"
	@echo "make test       - Run tests with coverage"
	@echo "make lint       - Run linters (flake8, mypy)"
	@echo "make format     - Format code with black"
	@echo "make clean      - Remove generated files"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=scripts --cov-report=html --cov-report=term-missing

lint:
	flake8 scripts/ tests/
	mypy scripts/

format:
	black scripts/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf findings/*.json
	rm -f reviewResult.json
