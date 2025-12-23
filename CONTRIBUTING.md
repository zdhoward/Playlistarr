# Contributing to Playlistarr

Thank you for your interest in contributing! 🎵

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: How to trigger the bug
- **Expected vs Actual**: What should happen vs what does happen
- **Environment**: OS, Python version, etc.
- **Logs**: Relevant error messages (with credentials redacted)

### Suggesting Features

Feature requests are welcome! Please include:

- **Use Case**: Why this feature would be useful
- **Proposed Solution**: How you envision it working
- **Alternatives**: Other approaches you considered

### Pull Requests

We love pull requests! Here's the process:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly**: Ensure existing functionality still works
5. **Update documentation**: README, docstrings, etc.
6. **Commit with clear messages**: `git commit -m "Add: feature description"`
7. **Push and create PR**: `git push origin feature/your-feature-name`

### Code Style

- **Python**: Follow PEP 8
- **Type hints**: Use type annotations where possible
- **Docstrings**: Use Google-style docstrings
- **Comments**: Explain why, not what
- **Formatting**: Run `black` before committing

### Testing

Before submitting a PR:

```bash
# Format code
black *.py

# Type checking
mypy *.py --ignore-missing-imports

# Run any existing tests
pytest tests/
```

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Playlistarr.git
cd Playlistarr

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install black mypy pytest

# Set up credentials (don't commit these!)
cp .env.example .env
# Edit .env with your API keys
```

## Project Structure

```
.
├── config.py              # Configuration and constants
├── filters.py             # Pure filtering logic
├── utils.py               # Path and file utilities
├── api_manager.py         # API key management
├── client.py              # OAuth client
├── discover_music_videos.py
├── youtube_playlist_sync.py
├── playlist_invalidate.py
├── playlist_apply_invalidation.py
└── run.cmd               # Windows pipeline runner
```

## Areas Needing Help

- [ ] Linux/Mac shell script equivalent to `run.cmd`
- [ ] Unit tests for filters.py
- [ ] Integration tests with mocked API responses
- [ ] Web UI for reviewing discovered videos
- [ ] MusicBrainz integration for better channel resolution
- [ ] Parallel API requests for faster discovery
- [ ] Progress bars for long operations
- [ ] Database backend option (SQLite)

## Questions?

- Open a discussion on GitHub
- Check existing issues and PRs
- Review the documentation in `/docs`

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help newcomers feel welcome

## License

By contributing, you agree that your contributions will be licensed under the same license as this project (see LICENSE file).

---

Thank you for making Playlistarr better! 🎸