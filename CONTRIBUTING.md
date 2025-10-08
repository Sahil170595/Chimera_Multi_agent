# Contributing to Chimera Multi-agent

Thank you for your interest in contributing to Chimera Multi-agent! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Git
- Docker (optional, for containerized development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/Chimera_Multi_agent.git
   cd Chimera_Multi_agent
   ```

2. **Set up development environment**
   ```bash
   make setup-dev
   # or manually:
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .[dev]
   pre-commit install
   ```

3. **Configure environment**
   ```bash
   cp env.sample env.local
   # Edit env.local with your configuration
   ```

## 🛠️ Development Workflow

### Code Style
We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **pre-commit** hooks for automated checks

### Running Checks
```bash
make lint          # Run all linting checks
make format        # Format code
make test          # Run tests
make test-cov      # Run tests with coverage
make security-check # Run security checks
```

### Pre-commit Hooks
Pre-commit hooks run automatically on each commit. To run manually:
```bash
pre-commit run --all-files
```

## 📝 Making Changes

### Branch Naming
Use descriptive branch names:
- `feature/add-new-benchmark-type`
- `fix/resolve-memory-leak`
- `docs/update-readme`
- `refactor/simplify-agent-logic`

### Commit Messages
Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run all checks** locally
6. **Create a pull request** with a clear description

### PR Requirements
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No security issues
- [ ] Coverage maintained or improved

## 🧪 Testing

### Running Tests
```bash
make test                    # Run all tests
make test-cov              # Run with coverage
pytest tests/test_specific.py  # Run specific test file
```

### Writing Tests
- Place tests in the `tests/` directory
- Use descriptive test names
- Follow the `test_*` naming convention
- Include both unit and integration tests

### Benchmark Testing
```bash
make benchmark             # Run benchmark tests
make benchmark-all         # Run all benchmark types
```

## 🐳 Docker Development

### Building Images
```bash
make docker-build
```

### Running Services
```bash
make docker-up    # Start all services
make docker-down  # Stop all services
```

## 📊 Benchmarking

Chimera Multi-agent includes comprehensive benchmarking capabilities:

### Benchmark Types
- **Compilation Benchmarks**: Eager, JIT, Torch Compile, ONNX
- **Quantization Benchmarks**: INT8, FP8, QAT
- **Attention Mechanism Performance**: Standard, Flash Attention
- **Kernel Optimization**: PyTorch vs Flash Attention
- **System Performance**: GPU metrics, memory usage
- **Inference Performance**: Model-specific benchmarks

### Adding New Benchmarks
1. Create benchmark class in `schemas/benchmarks.py`
2. Implement benchmark logic
3. Add to `SimpleBenchmarkGenerator`
4. Update tests
5. Document in `BENCHMARK_IMPLEMENTATION_SUMMARY.md`

## 🔒 Security

### Security Checks
```bash
make security-check  # Run bandit and safety checks
```

### Reporting Security Issues
Please report security vulnerabilities privately to security@your-org.com

## 📚 Documentation

### Documentation Standards
- Use clear, concise language
- Include code examples
- Update README.md for user-facing changes
- Update docstrings for API changes

### Documentation Structure
- `README.md` - Project overview and quick start
- `plan.md` - Project roadmap and architecture
- `BENCHMARK_IMPLEMENTATION_SUMMARY.md` - Benchmark system details
- `CONTRIBUTING.md` - This file
- Docstrings in code

## 🐛 Bug Reports

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

## 💡 Feature Requests

For feature requests:
- Check existing issues first
- Provide clear use case
- Consider implementation complexity
- Discuss in issues before implementing

## 📞 Getting Help

- **Issues**: GitHub Issues for bugs and feature requests
- **Discussions**: GitHub Discussions for questions
- **Documentation**: Check existing docs first

## 🏆 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Muse Protocol! 🎉
