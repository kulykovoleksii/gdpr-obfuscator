.PHONY: format lint test security clean install

install:
	pip install --upgrade pip
	pip install -e .
	pip install -r requirements-dev.txt

format:
	black src tests

lint:
	flake8 src tests
	mypy src

test:
	pytest -v --cov=gdpr_obfuscator --cov-report=html

security:
	@echo "Running bandit security scan..."
	@bandit -r src -c .bandit
	@echo "Running pip-audit dependency scan..."
	@pip-audit --skip-editable --ignore-vuln GHSA-4xh5-x5gv-qwph || echo "pip-audit found vulnerabilities"

all: format lint test security

clean:
	rm -rf .pytest_cache __pycache__ htmlcov .coverage
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -f function.zip