# Contributing to PArisNeoMCPServers

First off, thank you for considering contributing to PArisNeoMCPServers! We welcome contributions from everyone. Whether you're interested in adding a new MCP server, improving an existing one, fixing bugs, or enhancing documentation, your help is appreciated.

This document provides some guidelines for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements or New Servers](#suggesting-enhancements-or-new-servers)
  - [Your First Code Contribution](#your-first-code-contribution)
  - [Pull Requests](#pull-requests)
- [Development Setup](#development-setup)
- [Styleguides](#styleguides)
  - [Python Code](#python-code)
  - [Git Commit Messages](#git-commit-messages)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior. *(You will need to create a `CODE_OF_CONDUCT.md` file. The Contributor Covenant is a good template: https://www.contributor-covenant.org/)*

## How Can I Contribute?

### Reporting Bugs

If you find a bug in any of the MCP servers or example scripts, please ensure the bug was not already reported by searching on GitHub under [Issues](https://github.com/PArisNeoMCPServers/PArisNeoMCPServers/issues).

If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/PArisNeoMCPServers/PArisNeoMCPServers/issues/new). Be sure to include:
- A clear and descriptive title.
- A detailed description of the bug, including steps to reproduce it.
- The version of the specific MCP server you are using.
- Your Python version and operating system.
- Any relevant error messages or stack traces.
- Expected behavior vs. actual behavior.

### Suggesting Enhancements or New Servers

If you have an idea for a new MCP server or an enhancement to an existing one:
1.  Search the [Issues](https://github.com/PArisNeoMCPServers/PArisNeoMCPServers/issues) to see if the enhancement has already been suggested.
2.  If not, open a new issue. Provide:
    - A clear and descriptive title.
    - A detailed explanation of the enhancement or new server idea.
    - Why this feature would be useful.
    - (Optional) Any proposed implementation details.

### Your First Code Contribution

Unsure where to begin contributing?
- Look for issues tagged `good first issue` or `help wanted`.
- You can start by improving documentation, writing tests for existing servers, or picking up a small bug fix.

### Pull Requests

1.  **Fork the repository** on GitHub.
2.  **Clone your fork locally:**
    ```bash
    git clone https://github.com/YourUsername/PArisNeoMCPServers.git
    cd PArisNeoMCPServers
    ```
3.  **Create a new branch** for your changes:
    ```bash
    git checkout -b feature/my-new-mcp-server # or fix/bug-fix-description
    ```
    Please use a descriptive branch name (e.g., `feature/weather-mcp-server`, `fix/openai-tts-error-handling`).
4.  **Make your changes.** Ensure you follow the [Development Setup](#development-setup) and [Styleguides](#styleguides).
5.  **Test your changes thoroughly.**
    - If adding a new server, include an example script (e.g., `run_<new_server>_mcp_example.py`) in the root directory.
    - Ensure existing tests (if any) pass and add new tests for your changes where appropriate.
6.  **Commit your changes** with a clear commit message (see [Git Commit Messages](#git-commit-messages)).
    ```bash
    git add .
    git commit -m "feat(new-server): Add MyNewMCP Server with basic functionality"
    ```
7.  **Push your branch to your fork:**
    ```bash
    git push origin feature/my-new-mcp-server
    ```
8.  **Open a Pull Request (PR)** to the `main` branch of the `PArisNeoMCPServers/PArisNeoMCPServers` repository.
    - Provide a clear title and description for your PR.
    - Link to any relevant issues (e.g., "Closes #123").
    - Be prepared to discuss your changes and make adjustments if requested by maintainers.

## Development Setup

Each MCP server resides in its own subdirectory (e.g., `openai-mcp-server/`).
1.  Navigate to the specific server's directory.
2.  It's highly recommended to use a Python virtual environment:
    ```bash
    # Inside the server's directory, e.g., PArisNeoMCPServers/new-server/
    uv venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
3.  Install the project in editable mode along with its dependencies:
    ```bash
    uv pip install -e .
    ```
4.  If adding a new server, ensure it has:
    - Its own subdirectory within `PArisNeoMCPServers/`.
    - A `pyproject.toml` file.
    - A `README.md` explaining its setup and usage.
    - An `__init__.py` in its main package folder (e.g., `new_server_mcp_server/new_server_mcp_server/__init__.py`).
    - An example `.env.example` if it requires environment variables.
    - An example client script (e.g., `run_new_server_mcp_example.py`) in the root `PArisNeoMCPServers` directory.

## Styleguides

### Python Code

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use type hints for function signatures.
- Write clear and concise comments where necessary. Docstrings for public modules, classes, and functions are encouraged.
- Ensure your code is well-formatted. Consider using a formatter like Black or Ruff.

### Git Commit Messages

- Use conventional commit messages. This helps in understanding the history and automating changelogs.
  Format: `<type>(<scope>): <subject>`
  - `<type>`: `feat` (new feature), `fix` (bug fix), `docs` (documentation), `style` (formatting, missing semicolons, etc.; no code change), `refactor`, `test`, `chore` (updating build tasks, package manager configs, etc.; no production code change).
  - `<scope>` (optional): The part of the project affected (e.g., `openai-server`, `duckduckgo-wrapper`, `readme`).
  - `<subject>`: A concise description of the change.
- Example:
  ```
  feat(duckduckgo): Add timelimit parameter to search tool
  fix(openai-tts): Handle empty input text gracefully
  docs(readme): Update available servers list
  ```

## Community

If you have questions or want to discuss ideas, please open an [Issue](https://github.com/PArisNeoMCPServers/PArisNeoMCPServers/issues) on GitHub.

Thank you for contributing!