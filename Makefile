.PHONY: test test-unit test-integration clean

test:
	pytest

test-unit:
	pytest tests/unit -m unit -v

test-integration:
	pytest tests/integration -m integration -v

test-fast:
	pytest -m "not slow"

test-cov:
	pytest --cov=scanner --cov=gui --cov-report=html --cov-report=term

clean:
	rm -rf .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -f test_*.xlsx test_*.csv
