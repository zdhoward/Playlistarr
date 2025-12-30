# Pre-Commit Checklist

Before committing to the repository, ensure all these items are checked:

## 🔒 Security

- [ ] No API keys in code
- [ ] No OAuth tokens in code
- [ ] No personal data in code
- [ ] All credentials in `.gitignore`
- [ ] `.env` file not tracked
- [ ] `auth/` directory not tracked
- [ ] `cache/` directory not tracked
- [ ] `out/` directory not tracked

## 📝 Code Quality

- [ ] Code formatted with `black *.py`
- [ ] No syntax errors
- [ ] Type hints on new functions
- [ ] Docstrings on public functions
- [ ] Comments explain "why" not "what"
- [ ] No debug print statements
- [ ] No commented-out code blocks
- [ ] No TODO comments without issues

## 🧪 Testing

- [ ] Manual testing completed
- [ ] Edge cases considered
- [ ] Error handling tested
- [ ] Quota exhaustion handled
- [ ] Resume capability tested
- [ ] No regressions introduced

## 📚 Documentation

- [ ] README.md updated if needed
- [ ] CHANGELOG.md updated
- [ ] Docstrings added/updated
- [ ] Comments added where needed
- [ ] Examples updated if API changed

## 🗂️ Files

- [ ] No large files (>100KB)
- [ ] No binary files except images
- [ ] No IDE-specific files (`.vscode/`, `.idea/`)
- [ ] No OS-specific files (`.DS_Store`, `Thumbs.db`)
- [ ] File permissions correct (no 777)

## 🎯 Git

- [ ] Commit message is descriptive
- [ ] Commit message format: `Type: Description`
  - Types: Add, Fix, Update, Remove, Refactor, Docs
- [ ] Related issue referenced in commit
- [ ] Branch name is descriptive
- [ ] No merge conflicts

## 🔍 Quick Commands

```bash
# Security check
git diff --staged | grep -i "AIzaSy"  # Should return nothing!
git diff --staged | grep -i "client_secrets"  # Should return nothing!

# Format check
black --check *.py

# Type check
mypy *.py --ignore-missing-imports

# Git status
git status
```

## ⚠️ Red Flags

**STOP and fix immediately if you see:**
- API keys in `git diff`
- Large files in `git status`
- Merge conflicts
- Failing tests
- Import errors

## 🚀 Ready to Commit?

```bash
# Stage your changes
git add <files>

# Commit with good message
git commit -m "Add: Feature description"

# Push to your branch
git push origin your-branch-name
```

## 📞 Need Help?

- Check CONTRIBUTING.md
- Open a discussion
- Ask in existing issues