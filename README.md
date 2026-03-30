<h1 align="center">✦ AURA VIDEO DOWNLOADER ✦</h1>

<p align="center">
  <b>All features of 4K Video Downloader Plus — free and forever.</b><br>
  Powered by yt-dlp + ffmpeg
</p>

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-137%20collected-brightgreen)
![Platforms](https://img.shields.io/badge/platforms-23-orange)

Aura Video Downloader 2.0 is a Windows-first desktop GUI built with Python, PySide6, yt-dlp, and ffmpeg. It wraps a powerful command-line stack in a structured multi-workspace interface with per-platform settings, inspection tools, queue/history management, subscription automation, crash recovery, and optional in-app browser/media-player features.

This repository is the modular 2.0 generation of Aura. The legacy single-file implementation is still present as [`old version.py`](./old%20version.py) for historical comparison, but the active application now lives in the `aura/` package.

## Table of Contents

- [What 2.0 Is](#what-20-is)
- [Version 2.0 Highlights](#version-20-highlights)
- [Supported Platforms](#supported-platforms)
- [Feature Map](#feature-map)
- [Installation](#installation)
- [First Launch Flow](#first-launch-flow)
- [Workspace Layout](#workspace-layout)
- [Detailed Feature Breakdown](#detailed-feature-breakdown)
- [Typical Workflows](#typical-workflows)
- [Data and File Layout](#data-and-file-layout)
- [Project Structure](#project-structure)
- [Testing and Quality](#testing-and-quality)
- [2.0 vs Legacy `old version.py`](#20-vs-legacy-old-versionpy)
- [Important Notes](#important-notes)
- [License](#license)

## What 2.0 Is

Aura 2.0 is no longer just a "pretty button row for yt-dlp". The application is organized around a few clear goals:

- Keep the main thread responsive while downloads, probing, preview extraction, dependency checks, and subscription scans run in background workers.
- Separate UI, workers, persistence, and pure business logic so the project is maintainable.
- Support more than one usage style: quick one-off downloads, detailed inspection, unattended queueing, recurring subscriptions, and crash-safe recovery.
- Store settings per platform, so switching from YouTube to VK or TikTok does not destroy your previous setup.
- Expose advanced yt-dlp behavior without forcing users to type command lines manually.

Aura remains a fully local desktop application. It does not provide a remote service, hosted downloader, or cloud account system.

## Version 2.0 Highlights

- Modular package architecture instead of one monolithic script.
- 23 supported platforms instead of 17.
- New Search mode in addition to single video, audio-only, playlist, and channel/profile modes.
- Dedicated dialogs for format inspection, metadata preview, item picking, dependency warnings, cookie login, discovery browsing, and playback.
- SQLite-backed downloads, subscriptions, and recovery sessions.
- Subscription automation with scheduler support.
- Full-state export/import for backup and migration.
- Per-download "Execution Blueprint" preview before launching yt-dlp.
- Advanced audio pipeline with language-aware selection, dubbed-audio export, and container/compatibility helpers.
- M3U manifest generation for multi-item downloads.
- Expanded parallel download control up to 7 workers.
- 137 collected automated tests covering runtime, UI smoke behavior, workers, persistence, and bootstrap flows.

## Supported Platforms

Aura 2.0 currently ships platform profiles for 23 sites/services:

| Category | Platforms |
| --- | --- |
| Video | YouTube, VK Video, Rutube, Twitch, Dailymotion, Vimeo, Bilibili / Bilibili TV, OK.ru, Dzen, Rumble, BitChute, Naver TV / Blog |
| Social / Media | SoundCloud, TikTok, Instagram, Twitter / X, Facebook, Reddit, Flickr, Tumblr |
| Adult | Pornhub, XVideos, xHamster |

Notes:

- Platform capabilities are not identical. Some support channels/profiles, some support playlists, and some expose search mode.
- Search mode is currently enabled on platforms that define an internal search backend in the app configuration: YouTube, Rumble, and BitChute.
- Actual extraction support still depends on yt-dlp and the current state of each website.

## Feature Map

| Area | What Aura 2.0 provides |
| --- | --- |
| Download modes | Single video/media, audio-only extraction, playlist, channel/profile/community, search-result download flows |
| Format inspection | Full format table with codec, resolution, FPS, bitrate, language, size, and notes |
| Metadata preview | Thumbnail, title, uploader, duration, approximate size, upload date, views, audio-track languages, subtitle languages, immersive profile hints |
| Manual item selection | Pick specific entries from playlists/channels/search results before downloading |
| Batch link import | Paste plain-text URLs or CSV-like input and queue many links at once |
| Audio pipeline | WAV / MP3 / M4A / OGG, bitrate controls, audio-language preference, source selection, dubbed-audio export |
| Subtitle pipeline | Subtitle language selection, auto-subtitle awareness, conversion, optional embedding |
| Auth | No auth, cookies.txt, or browser-cookie extraction from Chrome / Firefox / Edge / Brave / Opera / Chromium / Safari |
| Browser tools | Optional login browser for cookie capture, optional discovery browser for navigating media pages inside Aura |
| Performance | aria2c integration, unified speed graph, bandwidth controls, per-item restart mode, parallel workers up to 7 |
| Persistence | Per-platform JSON settings, presets, download archives, SQLite database, session snapshots |
| Automation | Presets, subscription monitoring, scheduler, background/tray behavior |
| Reliability | Atomic writes, `.bak` backups, subprocess tracking, atexit cleanup, crash recovery prompt |
| UX | Responsive layout, theme support, English/Russian UI, execution blueprint, queue/history pages, built-in player (optional multimedia module) |

## Installation

Aura can be used from source or from a packaged Windows release. The source layout is the authoritative reference in this repository.

### Requirements

| Component | Required | Why it matters |
| --- | --- | --- |
| Python 3.9+ | Yes | Base runtime for the app |
| PySide6 | Yes | Qt GUI toolkit |
| yt-dlp | Yes | Extraction/downloading engine |
| ffmpeg | Strongly recommended / effectively required for many workflows | Merging, remuxing, subtitle embedding, conversion, post-processing |
| Node.js | Recommended for YouTube, required for some YouTube scenarios | JavaScript runtime for yt-dlp YouTube handling |
| aria2c | Optional | Multi-connection acceleration |
| PySide6-WebEngine | Optional | In-app login browser and discovery browser |
| PySide6-Multimedia | Optional | Built-in media player |

### Install from source

```bash
git clone https://github.com/your-account/aura-video-downloader.git
cd aura-video-downloader
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install .
```

If you want the optional GUI browser and built-in player:

```bash
pip install ".[webengine,multimedia]"
```

If you want development tools:

```bash
pip install ".[dev]"
```

### External tools

Aura expects command-line tools to be available in `PATH`:
- `yt-dlp` (neccessary)
- `ffmpeg` (strongly recommended)
- `node`   (needed for YouTube)
- `aria2c` (optional, for faster download)

### Launch

Any of the following is valid:

```bash
python Aura_Video_Downloader.py
```

```bash
python -m aura
```

```bash
aura
```

If you launch a portable `.exe`

The app itself is also shipped as a portable executable, but the external helper tools still matter:

- keep `ffmpeg` available in `PATH`
- keep `node` available if you care about YouTube reliability
- keep `aria2c` available if you want accelerated downloads
- install `PySide6-WebEngine` / `PySide6-Multimedia` during packaging if  you want the optional GUI browser and built-in player

## First Launch Flow

On the first run, Aura 2.0 walks through a startup flow instead of dumping the user straight into the main window.

### 1. Language

Choose the interface language:

- English
- Russian

### 2. Settings Location

Choose where Aura stores its data:

- default home-based path
- custom folder for portable/self-contained usage

Aura keeps only a small pointer file in the home directory and stores the rest inside the selected settings root.

### 3. Theme

Choose one of the built-in themes:

- Light
- Gray
- Dark

### 4. Platform

Choose the active platform profile. Aura stores settings per platform, so switching later does not wipe previous selections.

## Workspace Layout

Aura 2.0 replaces the old long vertical control stack with a workspace-oriented layout.

### Setup

- Source: mode selection, URL/search input, search-result limit where supported
- Video: quality, metadata language, video-oriented extraction settings
- Audio Track: audio-only settings and preferred audio-language choices
- Extra Audio: dubbed/translated audio export options

### Download

- Options: queueing, ordering, subtitles, SponsorBlock, container, compatibility policies, restart behavior
- Files: output folders, cookies, login/browser actions, archives, file behavior
- Tools: bandwidth controls, speed graph, format inspection, preview, player, command blueprint

### Automation

- Presets: save/load/delete platform-specific presets and auto-apply behavior
- Subscriptions: monitor channels/playlists and queue new content automatically
- Session: crash recovery and background-session behavior

### Library

- Queue: pending download entries and priority handling
- History: completed/failed entries, filtering, sorting, cleanup

### Activity

- Real-time log view with optional log-file output

### System

- Dependency status, tool checks, install helpers, app settings, reset/export/import actions

## Detailed Feature Breakdown

### Download modes

Aura 2.0 currently supports five main operating modes:

1. Video
2. Audio-only
3. Playlist
4. Channel / profile / page / community (depending on platform)
5. Search

Important behavior:

- Search mode is available only on platforms that define a search backend.
- Multi-item modes can use manual selection before downloading.
- Playlist/channel/search downloads can run sequentially, restart item-by-item, or in parallel workers.
- Reverse order is supported for applicable multi-item modes.

### Execution Blueprint

Before launching a download, Aura builds an execution preview that summarizes:

- the current mode
- quality and pipeline choices
- platform and auth method
- whether the run will be parallel or restart-per-item
- warnings or missing dependencies
- the exact command line that will be executed

This is one of the most important 2.0 usability upgrades because it exposes advanced behavior without making users manually assemble yt-dlp commands.

### Format inspection

The format dialog is now a dedicated UI instead of an ad-hoc inline view. It shows:

- format ID
- extension
- stream kind
- language
- resolution
- FPS
- codec
- bitrate
- reported size
- extra notes

The dialog also warns about common pitfalls:

- video-only formats need an audio merge
- audio-only formats make more sense in audio mode
- WebM / VP9 / Opus combinations are usually safer with MKV or Auto container

### Metadata preview

The preview dialog collects and presents:

- title
- duration
- approximate size (when reported)
- uploader
- upload date
- view count
- immersive-media hints
- available audio-track languages
- available subtitles / auto-subtitles
- thumbnail preview

This lets users inspect content before committing to the download.

### Manual selection and batch import

Aura 2.0 has two separate tools for multi-item workflows:

- `BatchLinksDialog`: paste many links from plain text or CSV-style input
- `ItemPickerDialog`: choose exactly which playlist/channel/search items should be downloaded

These tools did not exist as dedicated dialogs in the legacy monolith.

### Audio and language handling

The audio pipeline is significantly more advanced in 2.0.

Supported user-facing choices include:

- audio-only extraction
- audio format choice: WAV / MP3 / M4A / OGG
- bitrate choice
- preferred audio language
- default/original/explicit language fallback behavior
- metadata language preference (where supported by yt-dlp/platform)
- "download all audio tracks" behavior for compatible scenarios

### Dubbed / translated audio export

2.0 adds a dedicated "Extra Audio" page for exporting dubbed or translated tracks as separate files after the main video download.

Depending on platform/media availability, Aura can:

- export selected dubbed tracks
- export custom language-code selections
- probe all available dubbed tracks for single-video workflows
- choose output format for these follow-up files

### Subtitles

Aura exposes subtitle handling in a structured way:

- subtitle enable/disable
- language selection
- auto-subtitle awareness
- subtitle conversion
- subtitle embedding

The UI keeps subtitle settings visible only when relevant and threads them into the final yt-dlp command.

### Auth, cookies, and browser helpers

Auth choices are broader in 2.0 and are separated from the main clutter.

Supported auth methods:

- none
- cookies.txt file
- cookies from Chrome
- cookies from Firefox
- cookies from Edge
- cookies from Brave
- cookies from Opera
- cookies from Chromium
- cookies from Safari

Optional WebEngine-powered browser tools:

- login browser for extracting cookies into Netscape format
- discovery browser for opening platform pages and continuing through related media without leaving Aura

Special notes:

- private YouTube lists such as Watch Later / Liked / History are supported as special targets
- proxies are supported and wired directly into the runtime command
- some platforms mark cookies as recommended rather than absolutely required

### Performance and concurrency

Aura 2.0 has more performance controls than the legacy build:

- up to 7 parallel workers for multi-item downloads
- aria2c acceleration
- bandwidth throttling
- restart-per-item mode for long queues
- real-time speed graph
- batched log flushing to reduce UI churn
- throttled progress updates to reduce repaint pressure

Parallel downloads also use per-worker archive handling to reduce duplicate-item race conditions.

### Queue, history, and manifests

Aura separates transient work from permanent history:

- `DownloadQueue` handles prioritized queued items
- the library queue page exposes pending entries
- the history page stores completed activity
- archive files prevent re-downloading already recorded items
- M3U manifests can be generated for playlist-like downloads

The app can also update subscription-related playlist manifests automatically after downloads finish.

### Subscriptions and scheduler

Subscriptions are one of the biggest functional jumps in 2.0.

You can:

- save channel or playlist subscriptions
- attach runtime preset payloads
- set per-subscription intervals
- limit how many new entries are queued
- enable/disable entries individually
- run checks manually or on a schedule
- process newly discovered items into the queue automatically

The scheduler is handled in the desktop app, not as an external service.

### Session recovery and background behavior

Aura 2.0 saves enough state to recover long-running work after interruption:

- active queue/session snapshots are written before risky work
- downloads are tracked in the SQLite session table
- subprocesses are tracked and cleaned up on exit
- startup can offer recovery after a previous crash or abrupt stop
- background/tray mode can keep the app alive without the main window staying visible

### Full-state export/import

The current app can export and import a fuller app snapshot than the legacy script:

- database-backed state
- queue/session information
- subscriptions
- related configuration state

This is useful for migration, backup, testing, and reproducing user setups.

### UI, localization, and responsiveness

Aura 2.0 is still intentionally desktop-focused, but the UI is much more structured:

- English and Russian translations
- themed dialogs with shared chrome helpers
- responsive workspace layouts
- compact labels in narrow widths
- dedicated hero/status cards
- sidebar quick actions
- separate pages for setup, automation, and library tasks

### Optional built-in player

If `PySide6-Multimedia` is installed, Aura can open downloaded files in its own player dialog. If the multimedia module is missing, the UI falls back gracefully and explains why the player is unavailable.

## Typical Workflows

### Download a single video

1. Choose the platform.
2. Select `Video` mode.
3. Paste the media URL.
4. Choose quality and container behavior.
5. Open `Preview` if you want metadata first.
6. Open `Formats` if you want to force a specific format ID.
7. Start the download.

### Extract audio only

1. Switch to `Audio` mode.
2. Choose output format and bitrate.
3. Choose audio source scope if relevant.
4. Optionally choose preferred audio language.
5. Start the download.

### Download only selected playlist items

1. Open a playlist/channel/search target.
2. Start the workflow.
3. When the item picker appears, select only the entries you want.
4. Continue with queue, parallelism, or restart-per-item settings.

### Inspect before downloading

Use the `Preview` and `Formats` tools together:

- `Preview` answers "what is this item?"
- `Formats` answers "which exact streams are available?"

### Use Search mode

On supported platforms:

1. Switch to `Search` mode.
2. Enter a text query instead of a direct URL.
3. Set result count.
4. Download directly or manually pick entries.

### Build recurring automation

1. Save a preset with your preferred output/auth/subtitle/quality settings.
2. Open the subscriptions page.
3. Add a channel or playlist subscription.
4. Attach the preset/runtime payload.
5. Set interval and limits.
6. Enable scheduler/background behavior if you want unattended checks.

### Recover after interruption

If Aura was closed during active work:

1. Relaunch the app.
2. Review the recovery prompt if it appears.
3. Restore queued items/session snapshot.
4. Continue or clear the previous state.

## Data and File Layout

Aura stores its working data in a dedicated settings directory. The exact root is selected by the user during first launch.

Typical contents:

```text
settings_dir/
├── general.json
├── config_<platform>.json
├── presets_<platform>.json
├── history_<platform>.json
├── archive_<platform>.txt
├── cookies_<platform>.txt
├── aura_downloads.db
├── yt-dlp.conf
└── *.bak
```

Important points:

- `general.json` stores shared app-level choices such as theme.
- `config_<platform>.json` stores platform-specific settings.
- `presets_<platform>.json` stores reusable presets.
- `archive_<platform>.txt` prevents duplicate downloads via yt-dlp archive logic.
- `aura_downloads.db` stores downloads, subscriptions, and session recovery data.
- `yt-dlp.conf` stores shared yt-dlp runtime config when needed.
- Atomic JSON writes create `.bak` safety copies.

## Project Structure

The 2.0 codebase is package-based and split by responsibility:

```text
aura/
├── app.py
├── main_window.py
├── constants.py
├── database.py
├── platforms.py
├── settings.py
├── themes.py
├── utils.py
├── core/
│   ├── download_queue.py
│   └── models.py
├── dialogs/
│   ├── batch_links_dialog.py
│   ├── config_location.py
│   ├── cookie_browser.py
│   ├── discovery_browser.py
│   ├── format_dialog.py
│   ├── item_picker.py
│   ├── missing_dependencies_dialog.py
│   ├── player_dialog.py
│   ├── preview_dialog.py
│   ├── selectors.py
│   └── ui_chrome.py
├── widgets/
│   └── speed_graph.py
├── workers/
│   ├── base.py
│   ├── deps.py
│   ├── download.py
│   ├── download_prep.py
│   ├── formats.py
│   ├── playlist_entries.py
│   ├── preview.py
│   └── subscriptions.py
├── translations/
│   ├── en.json
│   └── ru.json
└── tests/
```

The file that still carries most orchestration logic is `aura/main_window.py`, but the project is no longer a one-file application.

## Testing and Quality

Aura 2.0 includes automated coverage for:

- bootstrap/runtime wiring
- dialog smoke behavior
- worker parsing
- preview/format flows
- queue/session persistence
- responsive UI behavior
- dependency checks
- widget rendering sanity

Commands:

```bash
python -m pytest aura/tests -v
```

```bash
ruff check .
```

```bash
mypy
```

As of the current repository state, `pytest --collect-only` reports **137 collected tests**.

## 2.0 vs Legacy `old version.py`

This repository still includes the old monolithic script, which makes the upgrade path easy to inspect. The main differences are concrete and significant:

- Architecture moved from one large script to a modular package with dedicated `core`, `workers`, `dialogs`, `widgets`, `translations`, and persistence modules.
- Supported platform profiles expanded from **17** to **23**.
- Added platform profiles: **Rumble, BitChute, Naver TV / Blog, SoundCloud, Flickr, Tumblr**.
- Added **Search mode**; the legacy script exposed only channel, playlist, video, and audio flows.
- Parallel worker limit increased from **5** to **7**.
- Added a dedicated **SQLite database** for downloads, subscriptions, and recovery sessions.
- Added **subscription automation** and a scheduler-backed monitoring flow.
- Added **full-state export/import** instead of only history export.
- Added dedicated dialogs for **format inspection, metadata preview, item picking, batch link paste, dependency warnings, config location, cookie browser, discovery browsing, and playback**.
- Added **download-preparation workers** and richer runtime probing before launch.
- Added **dubbed-audio export**, **M3U manifest generation**, **immersive-media detection**, and more advanced compatibility/container handling.
- Added a much stronger automated regression suite.

## Important Notes

- Aura depends heavily on yt-dlp. If a website changes, extraction behavior may change until yt-dlp catches up.
- Some features are optional because the relevant Qt module is optional:
  - browser/login/discovery features need `PySide6-WebEngine`
  - the built-in player needs `PySide6-Multimedia`
- `ffmpeg` is not technically required for every trivial download, but many real-world workflows need it. Treat it as a practical requirement.
- YouTube behavior is the most sensitive to site-side changes. Keeping `yt-dlp` and Node.js current is strongly recommended.
- Platform support does not imply identical feature parity across sites. Some sites do not support playlists, channels, or search mode.
- The repository also contains legacy artifacts such as `old version.py`; those are reference material, not the active implementation.

## License

MIT. See [`LICENSE`](./LICENSE).
