.PHONY: format lint test security clean

format:
	black src tests

lint:
	flake8 src tests
	mypy src

test:
	pytest -v --cov=gdpr_obfuscator --cov-report=html

security:
	bandit -r src -c .bandit
	pip-audit

all: format lint test security

clean:
	rm -rf .pytest_cache __pycache__ htmlcov .coverage
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -f function.zip