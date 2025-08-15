# Contributing to Multi-Bot RAG Platform

Thank you for your interest in contributing to the Multi-Bot RAG Platform! We welcome contributions from developers of all skill levels. This document provides comprehensive guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Community](#community)

## 🤝 Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. By participating, you agree to:

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome newcomers and help them get started
- **Be collaborative**: Work together to improve the project
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone is learning

## 🚀 Getting Started

### Prerequisites

Before contributing, make sure you have:

- **Git** installed and configured
- **Docker Desktop** for containerized development
- **Node.js 18+** for frontend development
- **Python 3.11+** for backend development
- A **GitHub account** for submitting contributions

### Setting Up Your Development Environment

1. **Fork the repository**
   ```bash
   # Click the "Fork" button on GitHub, then clone your fork
   git clone https://github.com/YOUR-USERNAME/multi-bot-rag-platform.git
   cd multi-bot-rag-platform
   ```

2. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/ORIGINAL-OWNER/multi-bot-rag-platform.git
   ```

3. **Set up the development environment**
   ```bash
   # Copy environment configuration
   cp config/.env.example config/.env
   
   # Start development services
   docker-compose up -d
   
   # Run database migrations
   docker-compose exec backend alembic upgrade head
   ```

4. **Verify the setup**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

For detailed setup instructions, see [DEVELOPMENT.md](docs/DEVELOPMENT.md).

## 🛠️ How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **🐛 Bug fixes**: Fix issues and improve stability
- **✨ New features**: Add new functionality
- **📚 Documentation**: Improve docs, guides, and examples
- **🎨 UI/UX improvements**: Enhance user interface and experience
- **⚡ Performance optimizations**: Make the platform faster
- **🧪 Tests**: Add or improve test coverage
- **🔧 DevOps**: Improve deployment and infrastructure
- **🌐 Translations**: Add support for new languages

## 🔄 Development Workflow

### Branch Strategy

We use a simplified Git flow:

- **`main`**: Production-ready code
- **`develop`**: Integration branch for features
- **`feature/feature-name`**: Individual feature branches
- **`bugfix/bug-description`**: Bug fix branches
- **`hotfix/critical-fix`**: Critical production fixes

### Workflow Steps

1. **Create a feature branch**
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/amazing-new-feature
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Follow coding standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run backend tests
   docker-compose exec backend pytest
   
   # Run frontend tests
   cd frontend && npm test
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing new feature"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/amazing-new-feature
   # Create pull request on GitHub
   ```

### Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(auth): add OAuth2 integration
fix(chat): resolve WebSocket connection issues
docs(api): update authentication examples
```

## 📝 Coding Standards

### Python (Backend)

- Follow **PEP 8** style guide
- Use **Black** for code formatting (line length: 100)
- Use **type hints** for all functions
- Write **Google-style docstrings**

```python
def create_bot(
    name: str, 
    description: str, 
    llm_provider: str = "openai"
) -> Bot:
    """Create a new bot instance.
    
    Args:
        name: The name of the bot
        description: A brief description of the bot's purpose
        llm_provider: The LLM provider to use (default: "openai")
        
    Returns:
        Bot: The created bot instance
        
    Raises:
        ValidationError: If the input parameters are invalid
    """
    # Implementation here
    pass
```

### TypeScript (Frontend)

- Use **ESLint** with TypeScript rules
- Use **Prettier** for code formatting
- Follow **React** best practices
- Define **comprehensive types**

```typescript
interface BotListProps {
  onBotSelect: (bot: Bot) => void;
  searchQuery?: string;
}

export const BotList: React.FC<BotListProps> = ({ 
  onBotSelect, 
  searchQuery = '' 
}) => {
  // Component implementation
};
```

## 🧪 Testing Guidelines

### Backend Testing

```python
# tests/test_bot_service.py
import pytest
from src.services.bot_service import BotService

class TestBotService:
    def test_create_bot_success(self):
        """Test successful bot creation."""
        # Test implementation
        pass
```

### Frontend Testing

```typescript
// components/__tests__/BotList.test.tsx
import { render, screen } from '@testing-library/react';
import { BotList } from '../BotList';

describe('BotList', () => {
  it('renders bot list', () => {
    // Test implementation
  });
});
```

### Test Coverage Targets

- **Backend**: 80%+ overall
- **Frontend**: 70%+ overall
- **Integration**: Cover all major workflows

## 📚 Documentation

### Code Documentation

- Write clear inline comments for complex logic
- Use OpenAPI/Swagger annotations for API endpoints
- Update README.md for new features
- Always update CHANGELOG.md

### API Documentation

```python
@router.post("/bots", response_model=BotResponse, status_code=201)
async def create_bot(
    bot_data: CreateBotRequest,
    current_user: User = Depends(get_current_user)
) -> BotResponse:
    """
    Create a new bot for the authenticated user.
    
    This endpoint allows users to create a new AI bot with custom configuration.
    """
    # Implementation here
    pass
```

## 🔄 Pull Request Process

### Before Submitting

1. **Sync with upstream**
   ```bash
   git checkout main
   git pull upstream main
   git rebase main
   ```

2. **Run all tests**
   ```bash
   docker-compose exec backend pytest
   cd frontend && npm test
   ```

3. **Update documentation**

### PR Template

```markdown
## Description
Brief description of the changes and their purpose.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] All existing tests pass

## Checklist
- [ ] Code follows coding standards
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## 🐛 Issue Guidelines

### Bug Reports

```markdown
**Bug Description**
Clear description of the bug.

**To Reproduce**
Steps to reproduce the behavior.

**Expected Behavior**
What you expected to happen.

**Environment:**
- OS: [e.g. Windows 10]
- Browser: [e.g. Chrome 96]
- Version: [e.g. 1.0.0]
```

### Feature Requests

```markdown
**Problem Description**
What problem does this solve?

**Proposed Solution**
What you want to happen.

**Alternatives Considered**
Other solutions you've considered.
```

## 🌟 Community

### Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check the docs/ directory first

### Recognition

- Contributors are listed in the README
- Significant contributions mentioned in release notes
- Special recognition for outstanding contributors

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You

Thank you for contributing to the Multi-Bot RAG Platform! Your contributions help make this project better for everyone.

Happy coding! 🚀