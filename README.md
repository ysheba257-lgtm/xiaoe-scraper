# xiaoe-scraper

**One-click batch downloader for course videos on xiaoe-tech (小鹅通) platforms.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Scrolling, password-protected, 68-video courses?  One command.  Done.

---

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [One-shot mode (recommended)](#one-shot-mode-recommended)
  - [Two-step mode](#two-step-mode)
- [How It Works](#how-it-works)
  - [Architecture](#architecture)
  - [Key challenges solved](#key-challenges-solved)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

```bash
# 1. launch Chrome with remote debugging
chrome --remote-debugging-port=9222

# 2. open your course page, log in

# 3. run
python -m xiaoe_scraper all "https://u3oz5.xetslk.com/s/xQK7I" \
    --password 1341 \
    --out ./videos/
```

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | ≥ 3.10 | `python --version` |
| Chrome / Edge | Recent | |
| ffmpeg | ≥ 4.0 | `ffmpeg -version` |

**ffmpeg** must be on your `PATH`.  Download from [ffmpeg.org](https://ffmpeg.org/) or install via your package manager.

---

## Installation

```bash
git clone https://github.com/<your-username>/xiaoe-scraper.git
cd xiaoe-scraper
pip install -e .
playwright install chromium
```

The editable install (`-e`) keeps the repo checkout live — useful if you want to tweak helpers.

> **Note:** you do *not* need to install a browser extension.  The tool speaks CDP (Chrome DevTools Protocol) directly to a Chrome instance you launch yourself.

---

## Usage

### One-shot mode (recommended)

```bash
python -m xiaoe_scraper all <COURSE_URL> \
    --password <PASSWORD> \
    --out <OUTPUT_DIR>
```

Extracts all video metadata, then downloads every video immediately (m3u8 signatures expire quickly).

### Two-step mode

Step 1 — extract metadata:

```bash
python -m xiaoe_scraper extract "https://..." --password 1234 -o items.json
```

Step 2 — download:

```bash
python -m xiaoe_scraper download items.json -o ./videos/
```

Useful when you want to inspect or edit the item list before downloading.

### Chrome setup

**Windows** — `Win+R` then:
```
chrome.exe --remote-debugging-port=9222
```

**macOS** — Terminal:
```bash
open -a "Google Chrome" --args --remote-debugging-port=9222
```

**Linux**:
```bash
google-chrome --remote-debugging-port=9222
```

Chrome 136+ requires a **non-default** profile directory when using `--remote-debugging-port`.  Add `--user-data-dir=/tmp/chrome-debug` if needed.

---

## How It Works

```
┌──────────────┐     CDP      ┌──────────────┐    ffmpeg    ┌──────────────┐
│   Chrome     │◄────────────►│  xiaoe-scraper│────────────►│   .mp4 files │
│ (debug port) │              │  (Playwright) │             │  (D: drive)  │
└──────────────┘              └──────────────┘             └──────────────┘
```

### Architecture

1. **Connect** to Chrome via CDP (no extension, no login token copying)
2. **Navigate** to the course page, auto-fill password
3. **Scroll** the virtual list repeatedly to trigger lazy-loading (xiaoe-tech renders ~8 items at a time; scrolling forces API pagination)
4. **Extract** resource IDs and titles from the Vue 2 component tree (`__vue__.$store.SingleItemList`)
5. **Navigate** to each video page, intercept the `.m3u8` network request, and immediately download with ffmpeg (signed URLs expire in ~10 minutes)

### Key challenges solved

| Challenge | Solution |
|-----------|----------|
| **Virtual scrolling** — only 8 of 68 items visible | Scroll `document.body` to bottom, wait for re-render, repeat until stable |
| **Vue SPA** — no `<a href>` links, click handlers | Read `__vue__.$store` component data directly |
| **Chinese text corruption** — Playwright JS eval mangles surrogates | Encode titles to base64 in the browser, decode in Python |
| **Short-lived m3u8 tokens** — sign param expires in minutes | Download *immediately* after capturing each URL |
| **Chrome 136+** — blocks `--remote-debugging-port` on default profile | Use non-default `--user-data-dir` (or use existing Chrome via the checkbox at `chrome://inspect/#remote-debugging`) |

---

## Project Structure

```
xiaoe-scraper/
├── xiaoe_scraper/
│   ├── __init__.py          # package metadata
│   ├── __main__.py          # python -m entry
│   ├── cli.py               # CLI (argparse)
│   ├── extractor.py         # course metadata extraction
│   └── downloader.py        # m3u8 capture + ffmpeg download
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
```

---

## Configuration

All configuration is done via CLI flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--password`, `-p` | `""` | Course unlock password |
| `--out`, `-o` | `./videos` | Output directory |
| `--cdp` | `http://localhost:9222` | Chrome DevTools Protocol endpoint |

Environment variables (optional):

| Variable | Purpose |
|----------|---------|
| `CDP_URL` | Override default CDP endpoint |

---

## FAQ

**Q: Do I need to be logged in?**

Yes.  Open the course page in the same Chrome instance you launched with `--remote-debugging-port`.  The tool reuses your existing session.

**Q: What platforms are supported?**

Any site built on xiaoe-tech (小鹅通) — recognizable by `h5.xet.pomoho.com`, `xetslk.com`, or `xiaoeknow.com` in the URL.

**Q: Can it download other content (PDFs, audio)?**

Currently video-only (resource_type=3).  The extractor captures all items; you can filter or extend the downloader for other types.

**Q: Why not just call the API directly?**

The API requires signed parameters that are generated client-side.  Driving the real browser is more robust against API changes.

**Q: How long do the m3u8 URLs last?**

~10 minutes.  That's why we download immediately rather than storing URLs.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Connection refused` on localhost:9222 | Chrome isn't running with remote debugging.  Re-launch with `--remote-debugging-port=9222` |
| Only 8 videos found | The list didn't scroll.  Make sure the catalog tab (目录) is active and try increasing scroll pauses |
| `ffmpeg: command not found` | Install ffmpeg and ensure it's on your `PATH` |
| `Protocol 'httpproxy' not on whitelist` | Added `httpproxy` to ffmpeg whitelist in v1.0.0.  If it persists, check Windows proxy settings |
| Videos downloaded but can't play | The m3u8 token likely expired before ffmpeg finished.  Large files (~1 GB) may need the downloader re-run for those specific items |
| Chinese characters garbled | This is a terminal display issue on Windows.  File names on disk should be correct.  Use `chcp 65001` before running |

---

## Contributing

Contributions welcome!  Areas that could use help:

- **Domain skills** — per-site playbooks for other xiaoe-tech-powered sites
- **Resume support** — persist progress so large courses can be resumed after interruption
- **Additional content types** — PDFs, audio, live replay downloads

Please open an issue before submitting a PR.

---

## License

MIT — see [LICENSE](LICENSE).
