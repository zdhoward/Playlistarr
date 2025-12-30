---
name: Bug Report
about: Report a bug or issue with Playlistarr
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear and concise description of what the bug is.

## Steps to Reproduce
Steps to reproduce the behavior:
1. Run command '...'
2. With configuration '...'
3. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Error Output
```
Paste the full error message here (with credentials redacted)
```

## Environment
- **OS**: [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- **Python Version**: [e.g., 3.10.5]
- **Install Method**: [pip, venv, conda, etc.]
- **Script**: [e.g., discover_music_videos.py, youtube_playlist_sync.py]

## Configuration
```python
# Relevant config settings (with API keys redacted)
MIN_DURATION_SEC = 120
MAX_DURATION_SEC = 450
# etc.
```

## Command Used
```bash
# Full command that triggered the bug
python discover_music_videos.py artists.csv --log-level DEBUG
```

## Logs
```
Paste relevant log output here (with credentials redacted)
```

## Artist/Video Details (if applicable)
- **Artist Name**: [e.g., "Taylor Swift"]
- **Video ID**: [e.g., "dQw4w9WgXcQ"]
- **Playlist ID**: [e.g., "PLxxxxxxxxxxxxxx"]

## Additional Context
- Does this happen consistently or intermittently?
- Did this work in a previous version?
- Any recent configuration changes?
- Screenshots (if UI-related)

## Attempted Solutions
What have you already tried to fix this?

## Checklist
- [ ] I've checked existing issues for duplicates
- [ ] I've included the full error message
- [ ] I've redacted all credentials from logs
- [ ] I've tested with the latest version
- [ ] I've included relevant configuration details
