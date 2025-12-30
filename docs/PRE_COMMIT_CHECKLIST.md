Yes, this is a good idea, and you are right to bring it back now. What you had for 1.0 was solid, but the project has matured. The checklist should reflect how Playlistarr actually works today, including CI, pytest, pyproject.toml, modular auth, and logging.

Below is a **fully updated Pre-Commit Checklist** that stays true to your original style, but is current for 1.2 and onward. It is pragmatic, enforceable, and CI-aligned.

You can drop this directly into `PRE_COMMIT_CHECKLIST.md` or keep it as a living internal doc.

---

# Pre-Commit Checklist

This project favors correctness, safety, and long-term maintainability over speed. Before committing, make sure every applicable item below is satisfied.

---

## 🔒 Security

* [ ] No API keys in code or logs
* [ ] No OAuth tokens committed
* [ ] No personal data or playlist IDs leaked unintentionally
* [ ] `.env` is gitignored
* [ ] `auth/` directory is gitignored
* [ ] `cache/`, `out/`, `logs/` are gitignored
* [ ] No secrets in test fixtures
* [ ] No credentials printed to console or logs

Quick checks:

```bash
git diff --staged | grep -i "AIzaSy"
git diff --staged | grep -i "client_secrets"
git diff --staged | grep -i "oauth"
```

All should return nothing.

---

## 🧠 Architecture and Design

* [ ] No direct OAuth usage outside `auth/providers`
* [ ] Business logic does not depend on CLI parsing
* [ ] Logging initialized centrally, not ad hoc
* [ ] New behavior is deterministic and resumable
* [ ] Quota handling preserved or improved
* [ ] No hidden side effects introduced
* [ ] State transitions remain explicit and logged

If you changed behavior, ask:

* Can this stop cleanly?
* Can this resume?
* Can this be inspected after the fact?

---

## 📝 Code Quality

* [ ] Code formatted with Black
* [ ] No syntax errors
* [ ] No unused imports or variables
* [ ] Type hints added for new public functions
* [ ] Docstrings updated where behavior changed
* [ ] Comments explain intent, not mechanics
* [ ] No debug print statements
* [ ] No commented-out code
* [ ] No TODOs without a clear follow-up plan

Commands:

```bash
black .
flake8 src tests
```

---

## 🧪 Testing

* [ ] `pytest` passes locally
* [ ] Tests do not rely on real credentials
* [ ] Logger tests do not require API keys
* [ ] Auth tests use providers, not raw OAuth
* [ ] Failure modes tested where applicable
* [ ] No tests silently skipped

Command:

```bash
pytest -q
```

If CI would fail, do not commit.

---

## 📚 Documentation

* [ ] README updated if behavior or CLI changed
* [ ] CHANGELOG updated for user-visible changes
* [ ] Version bumped if appropriate
* [ ] CONTRIBUTING.md updated if workflow changed
* [ ] Examples still accurate

Documentation should describe reality, not intention.

---

## 🗂️ Files and Repo Hygiene

* [ ] No large files over 100KB
* [ ] No binary files unless explicitly required
* [ ] No IDE files (`.idea/`, `.vscode/`)
* [ ] No OS junk files (`.DS_Store`, `Thumbs.db`)
* [ ] Deleted dead code instead of ignoring it
* [ ] Removed temporary scripts and experiments

If it is not part of the product, it should not be in the repo.

---

## 🎯 Git Discipline

* [ ] Commit message is descriptive and scoped
* [ ] Commit message format: `Type: Description`

Types:

* Add
* Fix
* Update
* Remove
* Refactor
* Docs
* CI

Examples:

```
Fix: correct logger retention handling
Refactor: move OAuth logic into provider
Docs: update README for CLI changes
```

* [ ] No unrelated changes bundled together
* [ ] Branch name is descriptive
* [ ] No merge conflicts

---

## 🚨 Red Flags

Stop immediately if you see:

* Secrets in `git diff`
* CI-only failures you did not reproduce locally
* Tests passing locally but failing in GitHub Actions
* Silent behavior changes
* Removed logging without replacement

---

## ✅ Ready to Commit

```bash
git status
git add <files>
git commit -m "Type: Clear description"
git push
```

If you are unsure, do not commit yet. Investigate first.

---

## Philosophy

Playlistarr is designed to be:

* Safe to run unattended
* Predictable under failure
* Inspectable after the fact
* Boring in the best way

Commits should move the project in that direction, never away from it.

---

If you want, next we can:

* Turn this into an actual `pre-commit` hook
* Align it directly with CI checks
* Add a release checklist for 1.2
* Freeze a stable maintenance policy

Just say what you want to tackle next.
