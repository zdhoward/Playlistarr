# Release Checklist for v1.0.0

## Pre-Release Preparation

### 1. Code Cleanup
- [ ] Run `cleanup_for_release.ps1` (or equivalent)
- [ ] All Python files formatted with `black *.py`
- [ ] No syntax errors (`python -m py_compile *.py`)
- [ ] No debug print statements
- [ ] No commented-out code
- [ ] No TODO/FIXME without issues

### 2. Security Audit
- [ ] No API keys in code
- [ ] No OAuth tokens in code  
- [ ] No credentials in git history
- [ ] `.gitignore` comprehensive
- [ ] `auth/`, `cache/`, `out/` ignored
- [ ] `.env` ignored
- [ ] `config.py` loads from environment

### 3. Documentation
- [ ] README.md complete and accurate
- [ ] SETUP.md step-by-step guide done
- [ ] CONTRIBUTING.md written
- [ ] CHANGELOG.md up to date
- [ ] LICENSE file present (MIT)
- [ ] All docstrings complete
- [ ] Code comments explain "why"

### 4. Configuration Files
- [ ] `.env.example` provided
- [ ] `config.sample.py` provided
- [ ] `requirements.txt` complete
- [ ] `.gitignore` comprehensive
- [ ] No hardcoded secrets

### 5. GitHub Setup
- [ ] `.github/workflows/ci.yml` configured
- [ ] Issue templates created
  - [ ] `bug_report.md`
  - [ ] `feature_request.md`
- [ ] Repository description set
- [ ] Topics/tags added
- [ ] README badges updated with repo URL

### 6. Testing
- [ ] Manual end-to-end test completed
- [ ] Discovery works
- [ ] Sync works
- [ ] Invalidation works
- [ ] Resume capability works
- [ ] Quota exhaustion handled gracefully
- [ ] Error messages helpful

### 7. Cross-Platform
- [ ] Tested on Windows
- [ ] Path handling works for all OSes
- [ ] Line endings correct (LF for shell scripts)
- [ ] No hardcoded path separators

## GitHub Repository Creation

### 1. Create Repository
```bash
# On GitHub:
# - Create new repository: Playlistarr
# - Make it public
# - Don't initialize with README (we have our own)
```

### 2. Initial Commit
```bash
# Local setup
git init
git add .
git commit -m "Initial commit - v1.0.0

- Complete refactored codebase
- Quota-aware pipeline
- Comprehensive documentation
- Security hardened
- Cross-platform compatible

See CHANGELOG.md for full details"

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/Playlistarr.git

# Push
git branch -M main
git push -u origin main
```

### 3. Create Release
```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0 - Production Ready

First production-ready release with:
- Stateful, resumable discovery
- Quota-aware API management  
- Quality-based video replacement
- Comprehensive documentation
- Security hardened

See CHANGELOG.md for complete details"

# Push tags
git push origin v1.0.0
```

### 4. GitHub Release Page
- [ ] Go to Releases → Draft a new release
- [ ] Choose tag: v1.0.0
- [ ] Title: "v1.0.0 - Production Ready"
- [ ] Description from CHANGELOG.md
- [ ] Mark as latest release
- [ ] Publish release

## Post-Release

### 1. Repository Settings
- [ ] Enable Issues
- [ ] Enable Discussions (optional)
- [ ] Enable Wiki (optional)
- [ ] Set branch protection rules for `main`
- [ ] Require PR reviews
- [ ] Require status checks (CI)

### 2. README Updates
- [ ] Update badge URLs with actual repo
- [ ] Verify all links work
- [ ] Update screenshots if any
- [ ] Verify setup instructions

### 3. Community Files
- [ ] Add CODE_OF_CONDUCT.md (optional)
- [ ] Add SECURITY.md (optional)
- [ ] Add .github/FUNDING.yml (optional)

### 4. Promotion (Optional)
- [ ] Post to r/Python
- [ ] Post to r/DataHoarder
- [ ] Tweet announcement
- [ ] Share on Discord communities
- [ ] Add to awesome-python lists

### 5. Monitoring
- [ ] Watch for issues
- [ ] Monitor CI/CD
- [ ] Track stars/forks
- [ ] Respond to discussions

## Quick Commands

### Security Check
```bash
# Search for exposed secrets
grep -r "AIzaSy" . --exclude-dir=.git
grep -r "client_secret" . --exclude-dir=.git

# Should return nothing!
```

### Format and Lint
```bash
# Format
black *.py

# Lint
flake8 *.py

# Type check
mypy *.py --ignore-missing-imports
```

### Test Imports
```bash
python -c "import config; print('OK')"
python -c "import filters; print('OK')"  
python -c "import utils; print('OK')"
python -c "from client import get_youtube_client; print('OK')"
```

### Git Commands
```bash
# Check what will be committed
git status
git diff --staged

# Commit
git commit -m "Your message"

# Push
git push origin main

# Tag
git tag -a v1.0.0 -m "Release message"
git push origin v1.0.0
```

## Rollback Plan

If critical issues found after release:

1. Create hotfix branch
```bash
git checkout -b hotfix/v1.0.1
```

2. Fix the issue

3. Update CHANGELOG.md

4. Commit and tag
```bash
git commit -m "Fix: Critical issue description"
git tag -a v1.0.1 -m "Hotfix: Description"
```

5. Push and create new release
```bash
git push origin hotfix/v1.0.1
git push origin v1.0.1
```

## Support Channels

After release, monitor:
- GitHub Issues
- GitHub Discussions
- Pull Requests
- Email (if provided)

## Success Criteria

Release is successful when:
- [ ] CI passes
- [ ] No critical security issues
- [ ] Documentation is clear
- [ ] Setup guide works for new users
- [ ] At least one successful external user
- [ ] No exposed credentials

---

## Final Check

Before clicking "Publish Release":

1. ✅ All checklists above completed
2. ✅ Ran `cleanup_for_release.ps1` with no errors
3. ✅ Tested on clean machine
4. ✅ All credentials removed
5. ✅ Documentation reviewed
6. ✅ CHANGELOG.md updated
7. ✅ License file present
8. ✅ Ready for public scrutiny

**Once published, congratulations! 🎉**

Monitor issues and be ready to create a hotfix if needed.