# Contributing to PostMortemIQ

Thank you for your interest in contributing to PostMortemIQ! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

**Positive behaviors include:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors include:**
- Harassment, trolling, or discriminatory comments
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by opening an issue or contacting the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- Git
- API keys: Groq, OpenAI (optional), HuggingFace (optional)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/postmortemiq.git
   cd postmortemiq
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/postmortemiq.git
   ```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
make install
# Or manually:
pip install -r requirements.txt
pip install -e .
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Start Services

```bash
# Start TigerGraph and Redis
make docker-up

# In another terminal, start the API
make run

# In another terminal, start the dashboard
make dashboard
```

### 5. Run Tests

```bash
make test
```

---

## How to Contribute

### Types of Contributions

We welcome contributions in many forms:

1. **Bug Fixes** - Fix issues reported in GitHub Issues
2. **New Features** - Implement new functionality
3. **Documentation** - Improve or add documentation
4. **Tests** - Add or improve test coverage
5. **Performance** - Optimize existing code
6. **Examples** - Add usage examples or tutorials

### Contribution Workflow

1. **Check existing issues** - Look for open issues or create a new one
2. **Discuss your approach** - Comment on the issue to discuss your proposed solution
3. **Create a branch** - Use a descriptive branch name
4. **Make your changes** - Follow coding standards
5. **Write tests** - Add tests for new functionality
6. **Update documentation** - Update relevant docs
7. **Submit a pull request** - Follow the PR template

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length:** 120 characters (not 79)
- **Indentation:** 4 spaces (no tabs)
- **Quotes:** Double quotes for strings, single quotes for dict keys
- **Imports:** Grouped and sorted (stdlib, third-party, local)

### Code Formatting

We use automated formatters:

```bash
# Format code
make format

# Check formatting
make lint
```

**Tools:**
- `black` - Code formatter
- `isort` - Import sorter
- `flake8` - Linter
- `mypy` - Type checker

### Type Hints

Use type hints for all function signatures:

```python
def analyze_incident(incident_id: str, max_hops: int = 2) -> Dict[str, Any]:
    """
    Analyze an incident using GraphRAG.
    
    Args:
        incident_id: Unique identifier for the incident
        max_hops: Maximum graph traversal hops (default: 2)
    
    Returns:
        Dictionary containing analysis results
    
    Raises:
        ValueError: If incident_id is invalid
        TimeoutError: If analysis exceeds timeout
    """
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_cost(tokens: int, model: str = "llama-3.3-70b-versatile") -> float:
    """
    Calculate the cost of an LLM API call.
    
    Args:
        tokens: Total number of tokens (input + output)
        model: Model name (default: llama-3.3-70b-versatile)
    
    Returns:
        Cost in USD
    
    Example:
        >>> calculate_cost(1000, "llama-3.3-70b-versatile")
        0.0008
    """
    pass
```

### Error Handling

Always handle errors gracefully:

```python
try:
    result = await pipeline.analyze(incident_id)
except TimeoutError:
    logger.error(f"Pipeline timeout for {incident_id}")
    return {"error": "timeout", "incident_id": incident_id}
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return {"error": str(e), "incident_id": incident_id}
```

### Logging

Use structured logging:

```python
from utils.logger import StructuredLogger

logger = StructuredLogger("my_module")

logger.info("Processing incident", extra={
    "incident_id": incident_id,
    "pipeline": "graphrag",
    "tokens": 380
})
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── conftest.py           # Pytest fixtures
├── test_pipelines.py     # Pipeline tests
├── test_comparator.py    # Comparator tests
├── test_graph.py         # Graph client tests
└── test_llm.py           # LLM client tests
```

### Writing Tests

Use pytest with fixtures:

```python
import pytest
from pipelines.graphrag import GraphRAGPipeline

@pytest.fixture
def mock_graph_client(mocker):
    """Mock TigerGraph client"""
    client = mocker.Mock()
    client.query.return_value = {"context": "test context"}
    return client

def test_graphrag_pipeline_success(mock_graph_client):
    """Test GraphRAG pipeline with successful response"""
    pipeline = GraphRAGPipeline(graph_client=mock_graph_client)
    
    result = await pipeline.analyze("incident_1")
    
    assert result["total_tokens"] < 500
    assert result["cost_usd"] < 0.001
    assert "rca_report" in result
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_pipelines.py

# Run with coverage
make test-coverage

# Run specific test
pytest tests/test_pipelines.py::test_graphrag_pipeline_success
```

### Test Coverage

Aim for **>80% code coverage**. Check coverage:

```bash
make test-coverage
# Opens coverage report in browser
```

---

## Pull Request Process

### Before Submitting

1. ✅ All tests pass (`make test`)
2. ✅ Code is formatted (`make format`)
3. ✅ Linting passes (`make lint`)
4. ✅ Documentation is updated
5. ✅ CHANGELOG.md is updated (if applicable)
6. ✅ Commit messages are clear and descriptive

### PR Title Format

Use conventional commits:

```
feat: Add support for custom graph queries
fix: Resolve timeout issue in GraphRAG pipeline
docs: Update installation instructions
test: Add tests for comparator module
refactor: Simplify error handling in LLM client
perf: Optimize graph traversal performance
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- Change 1
- Change 2
- Change 3

## Testing
How was this tested?

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Tests pass
- [ ] Code is formatted
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

### Review Process

1. **Automated checks** - CI/CD must pass
2. **Code review** - At least one maintainer approval required
3. **Testing** - Reviewer tests changes locally
4. **Merge** - Maintainer merges after approval

---

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
A clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. See error

**Expected behavior**
What should happen

**Actual behavior**
What actually happens

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.5]
- PostMortemIQ version: [e.g., 1.0.0]

**Logs**
Paste relevant logs
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
Clear description of desired functionality

**Describe alternatives you've considered**
Other approaches you've thought about

**Additional context**
Any other relevant information
```

---

## Community

### Communication Channels

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General questions and discussions
- **Pull Requests** - Code contributions

### Getting Help

- Check the [README.md](README.md) for basic usage
- Read the [PROJECT_DEEP_DIVE.md](PROJECT_DEEP_DIVE.md) for architecture details
- Search existing issues before creating new ones
- Ask questions in GitHub Discussions

### Recognition

Contributors will be recognized in:
- README.md Contributors section
- Release notes
- Project documentation

---

## Development Tips

### Useful Commands

```bash
# Development
make install          # Install dependencies
make run              # Start API server
make dashboard        # Start Streamlit dashboard
make docker-up        # Start Docker services
make docker-down      # Stop Docker services

# Testing
make test             # Run all tests
make test-coverage    # Run tests with coverage
make lint             # Run linters
make format           # Format code

# Data
make generate-data    # Generate synthetic incidents
make ingest           # Ingest real data
make eval             # Run accuracy evaluation

# Cleanup
make clean            # Remove build artifacts
make clean-all        # Remove all generated files
```

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
make run
```

Use Python debugger:

```python
import pdb; pdb.set_trace()
```

### Performance Profiling

```bash
# Profile API endpoint
python -m cProfile -o profile.stats main.py

# Analyze profile
python -m pstats profile.stats
```

---

## License

By contributing to PostMortemIQ, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, please:
1. Check this document first
2. Search existing issues and discussions
3. Create a new discussion if needed

Thank you for contributing to PostMortemIQ! 🎉
