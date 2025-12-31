# **Playlistarr**

---
![CI](https://github.com/zdhoward/playlistarr/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/github/license/zdhoward/playlistarr)
![Last Commit](https://img.shields.io/github/last-commit/zdhoward/playlistarr)
![Status](https://img.shields.io/badge/status-beta-yellow)

### **Version:** 1.2.2

Playlistarr is a **production-grade YouTube playlist automation engine** for homelabbers and self-hosters.

It discovers official music videos for artists, applies deterministic filtering rules, and keeps YouTube playlists continuously in sync - **while being fully quota-aware, resumable, and log-driven**.

This is not a “download everything” scraper.
It is a **self-healing playlist maintenance system** designed to run safely over time with minimal supervision.

---

## **What Playlistarr Does**

Playlistarr runs a multi-stage pipeline every time you sync a playlist.

### 1. **Discovery**

Discovers candidate music videos per artist using:

* Official Artist Channels
* VEVO channels
* Channel trust heuristics
* Title classification
* Version / remix / live / cover exclusion rules

Discovery is read-only.
No playlist mutation happens at this stage.

---

### 2. **Planning**

Builds a deterministic invalidation plan:

* What should be removed
* What should be kept
* What should be added

This stage is **pure analysis**.
If a run stops here, nothing has changed.

---

### 3. **Safe Mutation**

Applies playlist changes using OAuth:

* Stops cleanly on quota exhaustion
* Never leaves the playlist in a partial state
* Applies changes incrementally and safely
* Always records exactly what happened

---

### 4. **Quota-Aware Execution**

Playlistarr automatically detects and categorizes:

* API key quota exhaustion
* OAuth quota exhaustion
* Invalid or expired OAuth credentials
* Clean success with no remaining work

Every run exits in a **known, inspectable state**.

Quota exhaustion is **expected behavior**, not failure.

---

## **Who This Is For**

Playlistarr is for people who want:

* Hands-off YouTube music playlists
* Canonical, official music videos only
* Artist-based collections
* Deterministic, resumable automation
* Self-hosted, cron / systemd / Docker-friendly tooling
* Full visibility via logs and CLI inspection

If you’ve ever wanted *Spotify-style smart playlists, but for YouTube* — this is that, without black boxes.

---

## **Project Layout**

```
Playlistarr/
├── src/
│   ├── playlistarr.py        # CLI entrypoint
│   ├── runner.py             # Pipeline orchestrator
│   ├── logger/               # Structured logging subsystem
│   ├── auth/                 # Provider-based OAuth system
│   └── cli/
│       ├── cli_sync.py
│       ├── cli_auth.py
│       ├── cli_profiles.py
│       ├── cli_runs.py
│       ├── cli_logs.py
│       └── common.py
├── profiles/                 # One profile = one playlist
│   ├── muchloud.json
│   └── muchloud.csv
├── auth/                     # OAuth credentials (gitignored)
├── logs/                     # Per-command, per-profile logs
├── cache/
├── out/
├── playlistarr.cmd           # Windows launcher
└── playlistarr.sh            # Linux / macOS launcher
```

Each **profile** represents exactly one playlist and is fully self-contained.

---

## **Profiles**

A profile consists of **two files**:

```
profiles/<name>.json
profiles/<name>.csv
```

### JSON — metadata and rules

```json
{
  "label": "MuchLoud",
  "playlist_id": "PLa73YkAc2TvLqEb9gqMHnmjoN30qpnPe3",
  "rules": {
    "min_duration_sec": 90,
    "max_duration_sec": 600
  }
}
```

### CSV — artist list

Single-column, header optional:

```csv
Linkin Park
Deftones
Korn
Nine Inch Nails
```

The CSV is treated as **authoritative input**.

---

## **Getting Started**

### 1. Clone

```bash
git clone https://github.com/zdhoward/playlistarr
cd playlistarr
```

---

### 2. Environment

Create a `.env` file (location depends on your setup):

```bash
YOUTUBE_API_KEYS=key1,key2,key3
LOG_LEVEL=INFO
YT_SLEEP_SEC=0.2
CACHE_TTL_SECONDS=21600
```

Environment variables are loaded silently and **never override existing shell values**.

---

### 3. OAuth Setup

Create a Google Cloud **Desktop OAuth application** and place:

```
auth/client_secrets.json
```

On first run, Playlistarr will prompt for authentication and cache credentials locally.

OAuth logic is fully provider-isolated.

---

### 4. Create a Profile

```bash
playlistarr profiles add muchloud --playlist PLa73YkAc2TvLqEb9gqMHnmjoN30qpnPe3
```

Edit the CSV to add artists.

---

## **Running Playlistarr**

### Sync a profile

```bash
playlistarr sync muchloud
```

### Explicit run (no saved profile)

```bash
playlistarr run --csv artists.csv --playlist PLAYLIST_ID
```

---

## **Inspecting Runs & Logs**

Playlistarr is **log-driven**.
Every run produces a timestamped log file.

### List runs

```bash
playlistarr runs list --profile muchloud
```

Shows:

* Run ID
* Outcome (`ok`, `api_quota`, `oauth_quota`, etc.)
* Timestamp
* Log size

---

### Inspect a run

```bash
playlistarr runs show 2025-12-29_23-56-24 --profile muchloud
```

### View logs directly

```bash
playlistarr logs list --profile muchloud
playlistarr logs show 2025-12-29_23-56-24 --profile muchloud --tail 50
```

Logs are the **source of truth**.

---

## **Run States**

Every run ends in exactly one state:

| State          | Meaning                          |
| -------------- | -------------------------------- |
| `ok`           | Fully synced, up to date         |
| `api_quota`    | API keys exhausted safely        |
| `oauth_quota`  | OAuth quota exhausted            |
| `auth_invalid` | OAuth requires re-authentication |
| `failed`       | Unexpected failure               |

Quota exhaustion is a **controlled stop**, not an error.

---

## **Design Principles**

* Deterministic planning
* Zero partial mutation
* Quota safety first
* Provider-isolated auth
* Log-driven introspection
* CLI-first ergonomics
* No silent behavior

If something happens, it is logged.

---

## **Contributing**

This is a single-developer project optimized for correctness and long-term operation.

If you contribute:

1. Keep changes tightly scoped
2. Do not weaken quota handling
3. Preserve deterministic behavior
4. Avoid hidden side effects
5. Prefer explicit logging over magic

PRs that reduce safety guarantees will be rejected.

---

## **License**

MIT
