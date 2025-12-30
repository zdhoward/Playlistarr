# **Playlistarr**

Playlistarr is a production-grade YouTube music-playlist automation engine.

It discovers official music videos for artists, applies filtering rules, and keeps YouTube playlists continuously in sync — while safely handling YouTube’s API quotas, OAuth limits, and partial-failure scenarios.

This project is built for people who want **hands-off, self-healing, always-up-to-date music playlists** without relying on third-party services.

---

## **What Playlistarr Does**

Playlistarr runs a multi-stage pipeline:

1. **Discovery**
   Finds official music videos for each artist using multiple heuristics:

   * Official Artist Channels
   * VEVO
   * Title classification
   * Channel trust rules
   * Version / remix / cover filtering

2. **Planning**
   Builds a deterministic invalidation plan that decides:

   * What to remove
   * What to keep
   * What to add

3. **Safe Mutation**
   Applies changes to your YouTube playlist using OAuth — but stops cleanly if quota is hit.

4. **Syncing**
   Ensures the playlist matches the discovery results without duplicates or drift.

5. **Quota-Aware Execution**
   Playlistarr automatically detects:

   * API key exhaustion
   * OAuth quota exhaustion
   * Invalid or expired OAuth tokens
     and stops safely instead of corrupting your playlist.

Everything is logged with rich, colorized output and full debug traces.

---

## **Who This Is For**

Playlistarr is for people who want:

* Automatically maintained YouTube playlists
* Canonical, official music videos only
* Artist-based collections
* Self-hosted, Docker-friendly tooling
* Deterministic, resumable, quota-safe runs

If you’ve ever wanted something like “Spotify smart playlists, but for YouTube” — this is that.

---

## **Project Layout**

```
Playlistarr/
├── src/                    # All Python source code
├── profiles/               # One folder per playlist profile
│   ├── muchloud.json
│   └── muchloud.csv
├── config/
│   └── .env                # Secrets & tunables
├── auth/                   # OAuth tokens (gitignored)
├── logs/
├── cache/
├── out/
├── playlistarr.py          # CLI entrypoint
├── runner.py               # Pipeline orchestrator
├── playlistarr.cmd         # Windows launcher
└── playlistarr.sh          # Linux/macOS launcher
```

Each **profile** represents one playlist and lives entirely in `/profiles`.

---

## **Profiles**

A profile is defined by:

```
profiles/muchloud.json
profiles/muchloud.csv
```

The JSON stores playlist ID and rules.
The CSV stores the artist list.

You run Playlistarr against a profile by name:

```bash
playlistarr sync muchloud
```

This loads:

```
profiles/muchloud.json
profiles/muchloud.csv
```

and runs the full pipeline for that playlist.

---

## **Getting Started**

### 1. Clone the repo

```bash
git clone https://github.com/yourname/playlistarr
cd playlistarr
```

### 2. Create your `.env`

Copy the template into `config/.env` and fill it in:

```bash
YOUTUBE_API_KEYS=key1,key2,key3
LOG_LEVEL=DEBUG
YT_SLEEP_SEC=0.2
CACHE_TTL_SECONDS=21600
```

### 3. Set up OAuth

Create a Google Cloud OAuth Desktop app and download:

```
auth/client_secrets.json
```

On first run you will be prompted to log in.

---

### 4. Create a profile

Example:

**profiles/muchloud.json**

```json
{
  "label": "MuchLoud",
  "playlist_id": "PLa73YkAc2TvLqEb9gqMHnmjoN30qpnPe3"
}
```

**profiles/muchloud.csv**

```csv
Artist
Linkin Park
Deftones
Korn
Nine Inch Nails
```

---

### 5. Run

```bash
playlistarr sync muchloud
```

You’ll get:

* Rich colored console output
* Full logs in `/logs`
* Safe stopping when quota is hit
* Resume-safe operation

---

## **Quota-Safe by Design**

Playlistarr uses:

* **Multiple API keys** for discovery
* **OAuth** for playlist mutation
* Automatic quota detection
* Automatic safe-stop when limits are hit

It will never:

* Partially delete playlists
* Leave you in an inconsistent state
* Hammer the API

You can run it daily, hourly, or from cron/Docker safely.

---

## **Contributing**

This is a single-developer project designed for clarity, not chaos.

If you want to contribute:

1. Fork the repo
2. Keep changes scoped to one concern
3. Preserve quota-safety and deterministic behavior
4. Don’t add side effects to config files
5. Prefer pure functions in `filters.py`

PRs that break quota handling or deterministic planning will not be accepted.

---

## **License**

MIT