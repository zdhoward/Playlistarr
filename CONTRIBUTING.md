Here’s a **clean, current-state rewrite** of `CONTRIBUTING.md` that matches where Playlistarr is *now* (v1.2), keeps your **solo-dev / pragmatic tone**, and avoids outdated structure or tooling.

It’s intentionally firm but welcoming — optimized for correctness, not drive-by PRs.

You can replace your existing file wholesale with this.

---

# Contributing to Playlistarr

Thanks for your interest in contributing to Playlistarr.

Playlistarr is a **deterministic, quota-aware automation tool** designed to run unattended in homelab environments.
Contributions are welcome — but correctness, safety, and observability always come first.

---

## Project Philosophy

Before contributing, it’s important to understand a few non-negotiables:

* **Quota exhaustion is not a failure**
* **No partial mutation** — playlists must never end in an indeterminate state
* **Logs are the source of truth**
* **Explicit behavior beats clever abstractions**
* **Provider logic must remain isolated**

Changes that weaken these guarantees will not be accepted.

---

## Ways to Contribute

### 🐛 Reporting Bugs

Please open an issue with:

* **Clear description** of the problem
* **Exact command used**
* **Expected vs actual behavior**
* **Relevant log output** (redact credentials)
* **Environment details**:

  * OS
  * Python version
  * Playlistarr version

If there’s no log output, that’s a bug.

---

### 💡 Suggesting Features

Feature requests are welcome if they include:

* **Real-world use case**
* **Why this belongs in Playlistarr**
* **How it interacts with quotas**
* **Failure modes and exit states**

Requests that require hidden state, silent behavior, or implicit mutation will be declined.

---

## Pull Requests

### Workflow

1. Fork the repository
2. Create a focused branch

   ```bash
   git checkout -b feature/short-descriptive-name
   ```
3. Make your changes
4. Run tests locally
5. Update documentation **if behavior changes**
6. Open a PR with a clear description of intent and impact

Small, scoped PRs are strongly preferred.

---

## Development Setup

Playlistarr uses **`pyproject.toml`** for dependency management.

```bash
# Clone your fork
git clone https://github.com/zdhoward/Playlistarr.git
cd Playlistarr

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .

# Install dev tools (if not included already)
pip install pytest black mypy
```

### Environment

Create a `.env` file (or set env vars directly):

```bash
YOUTUBE_API_KEYS=key1,key2
LOG_LEVEL=INFO
```

OAuth credentials **must never** be committed.

---

## Testing

Tests are intentionally lightweight but meaningful.

Before submitting a PR:

```bash
# Run tests
pytest

# Format check
black .

# Optional type checking
mypy src --ignore-missing-imports
```

If you add new behavior, add or update tests accordingly.

---

## Code Style & Expectations

* **Python 3.10+**
* **Explicit over implicit**
* **Type hints where practical**
* **Log important decisions**
* **Explain *why* in comments, not *what***

Avoid:

* Silent fallbacks
* Global mutable state
* Implicit retries
* Provider-specific logic outside providers

---

## Project Structure (Current)

```
src/
├── playlistarr.py          # CLI entrypoint
├── runner.py               # Pipeline orchestration
├── logger/                 # Structured logging system
├── paths.py                # Centralized path resolution
├── auth/
│   ├── registry.py         # Provider registry
│   └── providers/
│       └── youtube.py
├── cli/
│   ├── cli_sync.py
│   ├── cli_profiles.py
│   ├── cli_runs.py
│   └── cli_logs.py
└── utils/
```

If you’re unsure where something belongs, ask before coding.

---

## Areas That Welcome Help

* Additional auth providers
* More test coverage (especially edge cases)
* Improved Docker / container docs
* CLI ergonomics (without hiding behavior)
* Documentation clarity

Large architectural changes should start as an issue or discussion.

---

## Code of Conduct

* Be respectful
* Be precise
* Critique code, not people
* Assume good intent

---

## License

By contributing, you agree that your work will be licensed under the project’s MIT license.

---

If you’re unsure whether a change fits the project, open an issue first.
That’s always the fastest path to a good PR.

Thanks for helping make Playlistarr better.
