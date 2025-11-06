# Contributing to sqlmeta

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/sqlmeta.git
cd sqlmeta

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev,all]"

# Run tests
pytest

# Run type checking
mypy sqlmeta

# Format code
black sqlmeta tests
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Code Style

- Follow PEP 8
- Use Black for formatting
- Add type hints
- Write docstrings
