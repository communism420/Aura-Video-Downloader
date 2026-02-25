<h1 align="center">✦ AURA VIDEO DOWNLOADER ✦</h1>

<p align="center">
  <b>All features of 4K Video Downloader Plus — free and forever.</b><br>
  Powered by yt-dlp + ffmpeg
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-blue?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/license-free-green" alt="Free">
  <img src="https://img.shields.io/badge/no_install-portable-orange" alt="Portable">
</p>

---

**🌍 Language / Язык:**  [English](#-english-guide) · [Русский](#-руководство-на-русском)

---

# 🇬🇧 English Guide

## 📋 Table of Contents

- [What Is This?](#what-is-this)
- [Supported Platforms](#supported-platforms)
- [What You Need Before Starting](#what-you-need-before-starting)
  - [Step 1: Download Aura](#step-1-download-aura)
  - [Step 2: Create a folder for dependencies](#step-2-create-a-folder-for-dependencies)
  - [Step 3: Install yt-dlp](#step-3-install-yt-dlp)
  - [Step 4: Install ffmpeg](#step-4-install-ffmpeg)
  - [Step 5: Install aria2c (optional but recommended)](#step-5-install-aria2c-optional-but-recommended)
  - [Step 6: Install Node.js (required for YouTube)](#step-6-install-nodejs-required-for-youtube)
  - [Step 7: Add the folder to PATH](#step-7-add-the-folder-to-path)
  - [Step 8: Verify Everything Works](#step-8-verify-everything-works)
- [How to Launch](#how-to-launch)
- [First Launch — Step by Step](#first-launch--step-by-step)
- [Using the Program](#using-the-program)
  - [Downloading a Video](#downloading-a-video)
  - [Downloading Audio Only](#downloading-audio-only)
  - [Downloading an Entire Channel or Playlist](#downloading-an-entire-channel-or-playlist)
  - [SponsorBlock (YouTube Only)](#sponsorblock-youtube-only)
- [Options Explained](#options-explained)
- [Presets](#presets)
- [Switching Platforms](#switching-platforms)
- [System Tray Icon](#system-tray-icon)
- [Updating Dependencies](#updating-dependencies)
- [Troubleshooting](#troubleshooting)

---

## What Is This?

**Aura Video Downloader** is a free, open-source program that lets you download videos and audio from 17+ websites — YouTube, TikTok, Instagram, VK, and many more.

It does everything that paid programs like "4K Video Downloader Plus" ($45) do, but completely free. Under the hood it uses **yt-dlp** (the download engine) and **ffmpeg** (the audio/video processor) — Aura just wraps them in a convenient, beautiful interface.

**No installation required** — Aura is a single `.exe` file. Just download and run.

---

## Supported Platforms

| Category | Platforms |
|----------|-----------|
| 🎬 Video | YouTube, VK Video, Rutube, Twitch, Dailymotion, Vimeo, Bilibili, OK.ru, Дзен |
| 📱 Social | TikTok, Instagram, Twitter/X, Facebook, Reddit |
| 🔞 Adult | Pornhub, XVideos, xHamster |

---

## What You Need Before Starting

Aura itself is just one `.exe` file — no installation needed. But it relies on helper programs that must be present on your computer:

| Program | Required? | What it does |
|---------|-----------|-------------|
| **yt-dlp** | ✅ Required | The engine — actually downloads videos from websites |
| **ffmpeg** | ✅ Required | Merges video + audio, converts formats |
| **Node.js** | ✅ Required for YouTube | JavaScript runtime needed by yt-dlp to solve YouTube challenges |
| **aria2c** | ⭐ Optional | Download accelerator — makes downloads significantly faster |

yt-dlp, ffmpeg, and aria2c are just `.exe` files — we'll put them all in **one folder** and tell Windows where to find it. Node.js has its own installer and installs separately.

> **⚠️ IMPORTANT:** yt-dlp, ffmpeg, and aria2c must be installed as **standalone programs** (`.exe` files in a folder on your disk), **NOT** as Python libraries. Aura calls them as external commands — they must be accessible from the command line.

---

### Step 1: Download Aura

1. Download `Aura_Video_Downloader.exe` from the [Releases](../../releases) page
2. Put it anywhere you like — for example, on your Desktop or in a `C:\Aura\` folder
3. That's it — Aura doesn't need installation

---

### Step 2: Create a folder for dependencies

We'll put all helper programs into **one folder**. We recommend calling it `aura_dependencies`, but you can name it anything you want.

1. Open File Explorer (the folder icon on your taskbar)
2. In the left panel, click **"This PC"**
3. Double-click on **"Local Disk (C:)"**
4. Right-click on an empty space → **New** → **Folder**
5. Name the folder **`aura_dependencies`** and press Enter

> **💡 Note:** The folder name doesn't matter — you can call it `tools`, `programs`, or whatever you like. What matters is that you add it to PATH (Step 6). We use `aura_dependencies` in this guide so it's easy to follow.

---

### Step 3: Install yt-dlp

1. Go to [github.com/yt-dlp/yt-dlp/releases/latest](https://github.com/yt-dlp/yt-dlp/releases/latest)
2. Scroll down to the **"Assets"** section (you may need to click the word "Assets" to expand it)
3. Find and download the file **`yt-dlp.exe`** (just click on it)
4. Move the downloaded `yt-dlp.exe` into **`C:\aura_dependencies`**

---

### Step 4: Install ffmpeg

1. Go to [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/)
2. Under **"Release builds"**, download **`ffmpeg-release-essentials.zip`**
3. Open the `.zip` file. Inside: a folder like `ffmpeg-7.1-essentials_build` → open it → open **`bin`**
4. You'll see three files: **`ffmpeg.exe`**, **`ffprobe.exe`**, **`ffplay.exe`**
5. Copy all three into **`C:\aura_dependencies`**

---

### Step 5: Install aria2c (optional but recommended)

aria2c is a download accelerator. When enabled, it splits files into multiple parts and downloads them simultaneously, making downloads **2–5× faster**. Aura works without it, but we highly recommend installing it.

1. Go to [github.com/aria2/aria2/releases/latest](https://github.com/aria2/aria2/releases/latest)
2. In the Assets section, download the file that ends with **`-win-64bit-build1.zip`** (for example, `aria2-1.37.0-win-64bit-build1.zip`)
3. Open the `.zip` file → inside you'll find `aria2c.exe`
4. Copy **`aria2c.exe`** into **`C:\aura_dependencies`**

---

✅ When done, the `C:\aura_dependencies` folder should contain these files:

```
C:\aura_dependencies\
  ├── yt-dlp.exe        ← required
  ├── ffmpeg.exe        ← required
  ├── ffprobe.exe       ← required
  ├── ffplay.exe        ← required
  └── aria2c.exe        ← optional (recommended)
```

---

### Step 6: Install Node.js (required for YouTube)

Node.js is a JavaScript runtime that yt-dlp needs to solve YouTube's anti-bot challenges. Without it, YouTube downloads may fail or have limited quality. If you only plan to download from other platforms (VK, TikTok, etc.), you can skip this step.

> **⚠️ Note:** Unlike the other tools above, Node.js has its own installer — you do **NOT** put it in the `aura_dependencies` folder. It installs system-wide and adds itself to PATH automatically.

1. Go to [nodejs.org](https://nodejs.org/)
2. Download the **LTS** version (the big green button on the left)
3. Run the downloaded installer
4. Click **"Next"** on each screen, keeping all default settings
5. **Make sure** the checkbox **"Automatically install the necessary tools"** is checked (if present)
6. Click **"Install"**, wait for it to finish, then click **"Finish"**

Node.js installs itself into `C:\Program Files\nodejs\` and **automatically adds itself to PATH** — no manual PATH setup needed.

---

### Step 7: Add the folder to PATH

PATH is a system setting that tells Windows where to look for programs. We need to add `C:\aura_dependencies` to PATH so that Aura can find yt-dlp, ffmpeg, and aria2c.

**Follow these steps carefully:**

1. Press **`Win + R`** on your keyboard (hold the Windows key and press the letter R)
2. A small "Run" window appears. Type **`sysdm.cpl`** and press **Enter**
3. A "System Properties" window opens. Click the **"Advanced"** tab at the top
4. Click the **"Environment Variables..."** button near the bottom
5. In the **bottom half** of the new window (the section called "System variables"), find the row that says **`Path`** and **double-click** on it
6. A list of folder paths appears. Click the **"New"** button
7. Type exactly: **`C:\aura_dependencies`**
8. Press **Enter**, then click **"OK"**
9. Click **"OK"** again to close the Environment Variables window
10. Click **"OK"** one last time to close System Properties

> **💡 Important:** After changing PATH, you must **close and re-open** any Command Prompt windows for the change to take effect.

> **💡 Custom folder name?** If you named your folder something other than `aura_dependencies`, type that path instead in step 7 (e.g., `C:\my_tools`).

---

### Step 8: Verify Everything Works

1. Press **`Win + R`**, type **`cmd`**, press **Enter** — a Command Prompt opens
2. Run these commands one by one:

```
yt-dlp --version
```
✅ Expected: a date like `2025.01.15`

```
ffmpeg -version
```
✅ Expected: version info starting with `ffmpeg version 7...`

```
aria2c --version
```
✅ Expected: version info starting with `aria2 version 1...` (if you installed it)

```
node --version
```
✅ Expected: a version like `v22.12.0` (if you installed it for YouTube)

**All commands work?** You're all set! Jump to [How to Launch](#how-to-launch).

❌ **See "is not recognized"?** PATH was not set correctly. Go back to [Step 7](#step-7-add-the-folder-to-path). Make sure:
- The folder `C:\aura_dependencies` exists and contains the `.exe` files
- You typed the path exactly right, with no typos
- You clicked "OK" on **all three** windows
- You opened a **new** Command Prompt after making the change

---

## How to Launch

Double-click **`Aura_Video_Downloader.exe`** — that's it!

No installation, no setup wizards, no admin rights needed. Aura will automatically check for yt-dlp, ffmpeg, and aria2c and show their status in the Dependencies section.

---

## First Launch — Step by Step

The very first time you run Aura, it will ask you four quick questions:

### 1️⃣ Language

Choose: **Русский** (Russian) or **English**. This affects all text in the program.

### 2️⃣ Settings Location

Choose where Aura saves your settings:

- **🏠 Home Folder** — standard location. **Recommended.**
- **📂 Custom Folder** — pick any folder (handy for USB portability)

### 3️⃣ Theme

Pick a visual style: light, dark, or a colored theme. Changeable anytime later.

### 4️⃣ Platform

Choose which website to download from. Each platform gets independent settings. Switch later with the **"🔄 Change platform"** button.

After these four steps — start downloading!

---

## Using the Program

### Downloading a Video

1. Make sure **📺 Video** mode is selected (default)
2. **Paste** the video URL into the field at the top (`Ctrl+V`)
3. Choose where to save — click **📂** to pick a folder
4. Pick video quality: 8K, 4K, 2K, 1080p, 720p, 480p, 360p, or "best available"
5. Click **▶ Start**
6. Done! The video is in a subfolder named after the platform (e.g., `YouTube/`)

### Downloading Audio Only

1. Switch to **🎵 Audio** mode
2. Pick the source: From video / From playlist / From channel
3. Pick format: MP3, FLAC, WAV, M4A, OGG, or OPUS
4. Pick quality: 128k, 192k, 256k, 320k, or Max
5. Paste the URL and click **▶ Start**

### Downloading an Entire Channel or Playlist

1. Switch to **📁 Channel** or **📋 Playlist** mode
2. Paste the URL
3. Pick quality
4. Useful options:
   - **📜 Use archive.txt** — re-running only grabs **new** videos
   - **📊 Oldest to newest** — chronological order
   - **🔢 No file numbering** — removes `00001_` prefix
   - **🔄 Restart after each video** — helps with unstable internet

### SponsorBlock (YouTube Only)

1. Check **☑ SponsorBlock**
2. Pick action: **Mark** (add chapters) or **Remove** (cut segments out)
3. Choose categories: sponsors, intros, outros, self-promotion, etc.

---

## Options Explained

| Option | What It Does |
|--------|-------------|
| 🔔 Notify on finish | Windows notification when downloads complete (only in background) |
| 📜 Use archive.txt | Tracks downloaded videos to skip re-downloads |
| 📊 Oldest to newest | Download in chronological order |
| 🔢 No file numbering | Remove `00001_` prefix from filenames |
| 🔄 Restart process | Restart yt-dlp after each video (fixes connection drops) |
| 📝 Subtitles | Download subtitles in your chosen language |
| 🚀 aria2c | Use the aria2c download accelerator (must be in PATH — see Step 5) |
| ⚡ Parallel downloads | Download 2–5 videos simultaneously |
| 🔒 Authentication | Use browser cookies for private/age-restricted content |
| 🌐 Proxy | Route downloads through a proxy server |

---

## Presets

- **💾 Save preset** — saves all current options under a name
- **📂 Load preset** — restores previously saved settings

---

## Switching Platforms

Click **🔄 Change platform** in "App Settings". Settings are saved automatically before switching. Each platform is fully independent.

---

## System Tray Icon

While running, Aura shows an icon near the clock:

- **Left-click** → bring the window to the front
- **Right-click** → menu: Reset settings / Close

---

## Updating Dependencies

If downloads stop working, yt-dlp usually needs an update:

1. Go to [github.com/yt-dlp/yt-dlp/releases/latest](https://github.com/yt-dlp/yt-dlp/releases/latest)
2. Download the new `yt-dlp.exe`
3. Replace the old file in `C:\aura_dependencies\`

Or click **"🔄 yt-dlp → master"** inside Aura.

ffmpeg and aria2c almost never need updating.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `'yt-dlp' is not recognized` | Not in PATH — redo [Step 7](#step-7-add-the-folder-to-path) |
| `'ffmpeg' is not recognized` | Not in PATH — make sure `ffmpeg.exe` is in `C:\aura_dependencies\` |
| Video has no audio | ffmpeg is missing or not in PATH |
| "n challenge solving failed" | Node.js is not installed — follow [Step 6](#step-6-install-nodejs-required-for-youtube) |
| "HTTP Error 403: Forbidden" | Set up Authentication → Browser cookies → pick your browser |
| "Private video" / "Sign in required" | Same — you need browser cookies |
| Very slow downloads | Install aria2c ([Step 5](#step-5-install-aria2c-optional-but-recommended)) and enable the 🚀 aria2c checkbox |
| Downloads suddenly stopped working | Update yt-dlp — see [Updating Dependencies](#updating-dependencies) |
| Program won't start | Check that your antivirus isn't blocking the `.exe` |

---
---

# 🇷🇺 Руководство на русском

## 📋 Содержание

- [Что это за программа?](#что-это-за-программа)
- [Поддерживаемые платформы](#поддерживаемые-платформы-1)
- [Что нужно для работы](#что-нужно-для-работы)
  - [Шаг 1: Скачайте Aura](#шаг-1-скачайте-aura)
  - [Шаг 2: Создайте папку для зависимостей](#шаг-2-создайте-папку-для-зависимостей)
  - [Шаг 3: Установите yt-dlp](#шаг-3-установите-yt-dlp)
  - [Шаг 4: Установите ffmpeg](#шаг-4-установите-ffmpeg)
  - [Шаг 5: Установите aria2c (необязательно, но рекомендуется)](#шаг-5-установите-aria2c-необязательно-но-рекомендуется)
  - [Шаг 6: Установите Node.js (обязательно для YouTube)](#шаг-6-установите-nodejs-обязательно-для-youtube)
  - [Шаг 7: Добавьте папку в PATH](#шаг-7-добавьте-папку-в-path)
  - [Шаг 8: Проверка](#шаг-8-проверка)
- [Как запустить](#как-запустить)
- [Первый запуск — по шагам](#первый-запуск--по-шагам-1)
- [Как пользоваться](#как-пользоваться)
  - [Скачать видео](#скачать-видео)
  - [Скачать только аудио](#скачать-только-аудио)
  - [Скачать весь канал или плейлист](#скачать-весь-канал-или-плейлист)
  - [SponsorBlock (только YouTube)](#sponsorblock-только-youtube-1)
- [Описание опций](#описание-опций)
- [Пресеты](#пресеты)
- [Смена платформы](#смена-платформы)
- [Иконка в трее](#иконка-в-трее)
- [Обновление зависимостей](#обновление-зависимостей)
- [Решение проблем](#решение-проблем)

---

## Что это за программа?

**Aura Video Downloader** — это бесплатная программа для скачивания видео и аудио с 17+ сайтов: YouTube, TikTok, ВКонтакте, Instagram и многих других.

Она делает всё то же, что платные программы вроде «4K Video Downloader Plus» (за $45), но совершенно бесплатно. Внутри работают **yt-dlp** (скачивает видео с сайтов) и **ffmpeg** (склеивает видео со звуком, конвертирует форматы) — а Aura даёт им красивый и понятный интерфейс.

**Установка не нужна** — Aura это один `.exe` файл. Скачали — запустили.

---

## Поддерживаемые платформы

| Категория | Платформы |
|-----------|-----------|
| 🎬 Видео | YouTube, VK Video, Rutube, Twitch, Dailymotion, Vimeo, Bilibili, OK.ru, Дзен |
| 📱 Соцсети | TikTok, Instagram, Twitter/X, Facebook, Reddit |
| 🔞 18+ | Pornhub, XVideos, xHamster |

---

## Что нужно для работы

Сама Aura — это один `.exe` файл, устанавливать его не надо. Но для работы ей нужны вспомогательные программы:

| Программа | Обязательно? | Что делает |
|-----------|-------------|-----------|
| **yt-dlp** | ✅ Обязательно | Движок — непосредственно скачивает видео с сайтов |
| **ffmpeg** | ✅ Обязательно | Склеивает видео и аудио, конвертирует форматы |
| **Node.js** | ✅ Обязательно для YouTube | JavaScript-движок, нужен yt-dlp для решения защиты YouTube |
| **aria2c** | ⭐ Необязательно | Ускоритель загрузки — скачивание становится в 2–5 раз быстрее |

yt-dlp, ffmpeg и aria2c — это просто `.exe` файлы. Мы положим их в **одну папку** и скажем Windows, где её искать. Node.js устанавливается отдельно через свой установщик.

> **⚠️ ВАЖНО:** yt-dlp, ffmpeg и aria2c — это **отдельные программы** (`.exe` файлы, которые нужно скачать и положить в папку), а **НЕ** библиотеки Python. Программа запускает их как внешние команды — они должны быть доступны из командной строки.

---

### Шаг 1: Скачайте Aura

1. Скачайте файл `Aura_Video_Downloader.exe` со страницы [Releases](../../releases)
2. Положите его куда хотите — например, на Рабочий стол или в папку `C:\Aura\`
3. Всё — установка не требуется

---

### Шаг 2: Создайте папку для зависимостей

Мы положим все вспомогательные программы в **одну папку**. Рекомендуем назвать её `aura_dependencies`, но можно дать любое название.

1. Откройте Проводник (иконка папки на панели задач)
2. В левой панели нажмите **«Этот компьютер»**
3. Дважды щёлкните на **«Локальный диск (C:)»**
4. Щёлкните правой кнопкой мыши на пустом месте → **«Создать»** → **«Папку»**
5. Назовите папку **`aura_dependencies`** и нажмите Enter

> **💡 Примечание:** Название папки не принципиально — можно назвать `tools`, `programs` или как угодно. Главное — потом добавить эту папку в PATH (Шаг 7). Мы используем `aura_dependencies` в этой инструкции для удобства.

---

### Шаг 3: Установите yt-dlp

1. Откройте сайт [github.com/yt-dlp/yt-dlp/releases/latest](https://github.com/yt-dlp/yt-dlp/releases/latest)
2. Прокрутите вниз до раздела **«Assets»** (возможно, нужно нажать на слово «Assets», чтобы раскрыть)
3. Найдите и скачайте файл **`yt-dlp.exe`** (просто нажмите на него)
4. Переместите скачанный `yt-dlp.exe` в папку **`C:\aura_dependencies`**

---

### Шаг 4: Установите ffmpeg

1. Зайдите на сайт [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/)
2. В разделе **«Release builds»** скачайте **`ffmpeg-release-essentials.zip`**
3. Откройте архив. Внутри: папка вроде `ffmpeg-7.1-essentials_build` → откройте её → откройте **`bin`**
4. Вы увидите три файла: **`ffmpeg.exe`**, **`ffprobe.exe`**, **`ffplay.exe`**
5. Скопируйте все три в **`C:\aura_dependencies`**

---

### Шаг 5: Установите aria2c (необязательно, но рекомендуется)

aria2c — это ускоритель загрузки. Он разбивает файл на несколько частей и скачивает их одновременно, что делает загрузку **в 2–5 раз быстрее**. Aura работает и без него, но мы настоятельно рекомендуем установить.

1. Зайдите на [github.com/aria2/aria2/releases/latest](https://github.com/aria2/aria2/releases/latest)
2. В разделе «Assets» скачайте файл, который заканчивается на **`-win-64bit-build1.zip`** (например, `aria2-1.37.0-win-64bit-build1.zip`)
3. Откройте архив — внутри найдёте файл `aria2c.exe`
4. Скопируйте **`aria2c.exe`** в папку **`C:\aura_dependencies`**

---

✅ Когда закончите, в папке `C:\aura_dependencies` должны быть такие файлы:

```
C:\aura_dependencies\
  ├── yt-dlp.exe        ← обязательно
  ├── ffmpeg.exe        ← обязательно
  ├── ffprobe.exe       ← обязательно
  ├── ffplay.exe        ← обязательно
  └── aria2c.exe        ← необязательно (рекомендуется)
```

---

### Шаг 6: Установите Node.js (обязательно для YouTube)

Node.js — это JavaScript-движок, который нужен программе yt-dlp для обхода защиты YouTube. Без него загрузка с YouTube может не работать или выдавать ограниченное качество. Если вы планируете скачивать только с других платформ (ВК, TikTok и т.д.) — этот шаг можно пропустить.

> **⚠️ Примечание:** В отличие от остальных программ, Node.js **НЕ** нужно класть в папку `aura_dependencies`. У него свой установщик, который всё сделает сам.

1. Зайдите на сайт [nodejs.org](https://nodejs.org/)
2. Скачайте версию **LTS** (большая зелёная кнопка слева)
3. Запустите скачанный установщик
4. На каждом экране нажимайте **«Next»** (Далее), оставляя все настройки по умолчанию
5. **Убедитесь**, что галочка **«Automatically install the necessary tools»** стоит (если она есть)
6. Нажмите **«Install»** (Установить), дождитесь окончания и нажмите **«Finish»** (Готово)

Node.js устанавливается в `C:\Program Files\nodejs\` и **автоматически добавляется в PATH** — вручную ничего настраивать не надо.

---

### Шаг 7: Добавьте папку в PATH

PATH — это системная настройка, которая говорит Windows, где искать программы. Нам нужно добавить папку `C:\aura_dependencies` в PATH, чтобы Aura могла найти yt-dlp, ffmpeg и aria2c.

**Следуйте этим шагам внимательно:**

1. Нажмите на клавиатуре **`Win + R`** (зажмите клавишу Windows и нажмите букву R). Появится окошко «Выполнить»
2. Введите **`sysdm.cpl`** и нажмите **Enter**
3. Откроется окно «Свойства системы». Нажмите на вкладку **«Дополнительно»** вверху
4. Нажмите кнопку **«Переменные среды...»** внизу окна
5. В **нижней части** нового окна (раздел «Системные переменные») найдите строку **`Path`** и **дважды щёлкните** по ней
6. Откроется список папок. Нажмите кнопку **«Создать»**
7. Введите точно: **`C:\aura_dependencies`**
8. Нажмите **Enter**, затем **«ОК»**
9. Нажмите **«ОК»** ещё раз, чтобы закрыть окно «Переменные среды»
10. Нажмите **«ОК»** последний раз, чтобы закрыть «Свойства системы»

> **💡 Важно:** После изменения PATH нужно **закрыть и заново открыть** все окна командной строки.

> **💡 Другое название папки?** Если вы назвали папку не `aura_dependencies`, впишите в шаге 7 ваш путь (например, `C:\мои_программы`).

---

### Шаг 8: Проверка

1. Нажмите **`Win + R`**, введите **`cmd`**, нажмите **Enter** — откроется командная строка
2. Введите по очереди:

```
yt-dlp --version
```
✅ Ожидаемый результат: дата, например `2025.01.15`

```
ffmpeg -version
```
✅ Ожидаемый результат: информация о версии, начинающаяся с `ffmpeg version 7...`

```
aria2c --version
```
✅ Ожидаемый результат: информация о версии, начинающаяся с `aria2 version 1...` (если устанавливали)

```
node --version
```
✅ Ожидаемый результат: версия вроде `v22.12.0` (если устанавливали для YouTube)

**Всё работает?** Поздравляем — переходите к [Как запустить](#как-запустить)!

❌ **Ошибка «не является внутренней или внешней командой»?** PATH настроен неправильно. Вернитесь к [Шагу 7](#шаг-7-добавьте-папку-в-path). Убедитесь, что:
- Папка `C:\aura_dependencies` реально существует и содержит `.exe` файлы
- Вы написали путь точно, без ошибок
- Вы нажали «ОК» во **всех трёх** окнах
- Вы открыли **новое** окно командной строки после изменений

---

## Как запустить

Дважды щёлкните по файлу **`Aura_Video_Downloader.exe`** — и всё!

Установка не нужна. Права администратора не нужны. Aura автоматически проверит наличие yt-dlp, ffmpeg и aria2c и покажет их статус в разделе «Зависимости».

---

## Первый запуск — по шагам

При самом первом запуске программа задаст четыре вопроса:

### 1️⃣ Язык

Выберите: **Русский** или **English**. От этого зависит весь текст в программе.

### 2️⃣ Расположение настроек

- **🏠 Домашняя папка** — стандартное место. **Рекомендуется.**
- **📂 Выбрать свою папку** — любая папка (удобно для флешки)

### 3️⃣ Тема

Светлая, тёмная или цветная. Можно сменить позже.

### 4️⃣ Платформа

Выберите сайт для скачивания. У каждой платформы свои настройки. Сменить можно в любой момент кнопкой **«🔄 Сменить платформу»**.

После этого — скачивайте!

---

## Как пользоваться

### Скачать видео

1. Убедитесь, что выбран режим **📺 Видео** (по умолчанию)
2. **Вставьте ссылку** на видео в поле URL (`Ctrl+V`)
3. Выберите папку — нажмите **📂**
4. Выберите качество: 8K, 4K, 2K, 1080p, 720p, 480p, 360p или «лучшее»
5. Нажмите **▶ Старт**
6. Видео сохранится в подпапке с именем платформы (например, `YouTube/`)

### Скачать только аудио

1. Переключитесь в **🎵 Аудио**
2. Выберите источник: Из видео / Из плейлиста / Из канала
3. Формат: MP3, FLAC, WAV, M4A, OGG или OPUS
4. Качество: 128k, 192k, 256k, 320k или «Максимум»
5. Вставьте ссылку и **▶ Старт**

### Скачать весь канал или плейлист

1. Режим **📁 Канал** или **📋 Плейлист**
2. Вставьте ссылку
3. Выберите качество
4. Полезные опции:
   - **📜 archive.txt** — при повторном запуске скачаются только **новые** видео
   - **📊 От старых к новым** — хронологический порядок
   - **🔢 Без нумерации** — убирает `00001_` из имён
   - **🔄 Перезапускать** — помогает при нестабильном интернете

### SponsorBlock (только YouTube)

1. Поставьте **☑ SponsorBlock**
2. Действие: **Отметить** (главы) или **Удалить** (вырезать)
3. Категории: спонсоры, интро, аутро, самореклама и т.д.

---

## Описание опций

| Опция | Что делает |
|-------|-----------|
| 🔔 Уведомление | Уведомление Windows по завершении (только если окно не активно) |
| 📜 archive.txt | Запоминает скачанные видео |
| 📊 От старых к новым | Хронологический порядок |
| 🔢 Без нумерации | Убирает `00001_` из имён |
| 🔄 Перезапуск | Перезапускает yt-dlp после каждого видео |
| 📝 Субтитры | Скачивает субтитры |
| 🚀 aria2c | Ускоритель загрузки (должен быть в PATH — см. Шаг 5) |
| ⚡ Параллельно | 2–5 видео одновременно |
| 🔒 Авторизация | Куки браузера для приватного контента |
| 🌐 Прокси | Скачивание через прокси |

---

## Пресеты

- **💾 Сохранить пресет** — сохраняет текущие настройки
- **📂 Загрузить пресет** — восстанавливает сохранённые

---

## Смена платформы

Нажмите **🔄 Сменить платформу** в «Настройках приложения». Настройки сохранятся автоматически. У каждой платформы независимые настройки.

---

## Иконка в трее

Рядом с часами:

- **Левый клик** → показать окно
- **Правый клик** → Сбросить настройки / Закрыть

---

## Обновление зависимостей

Если скачивание перестало работать — обновите yt-dlp:

1. Зайдите на [github.com/yt-dlp/yt-dlp/releases/latest](https://github.com/yt-dlp/yt-dlp/releases/latest)
2. Скачайте новый `yt-dlp.exe`
3. Замените старый файл в `C:\aura_dependencies\`

Или нажмите **«🔄 yt-dlp → master»** в программе.

ffmpeg и aria2c обновлять почти никогда не нужно.

---

## Решение проблем

| Проблема | Решение |
|----------|---------|
| `yt-dlp не является командой` | Не в PATH — повторите [Шаг 7](#шаг-7-добавьте-папку-в-path) |
| `ffmpeg не является командой` | Не в PATH — убедитесь, что `ffmpeg.exe` в `C:\aura_dependencies\` |
| Видео без звука | ffmpeg не найден |
| «n challenge solving failed» | Node.js не установлен — выполните [Шаг 6](#шаг-6-установите-nodejs-обязательно-для-youtube) |
| «HTTP Error 403» | Авторизация → Куки браузера → выберите браузер |
| «Приватное видео» | Тоже нужны куки |
| Медленная загрузка | Установите aria2c ([Шаг 5](#шаг-5-установите-aria2c-необязательно-но-рекомендуется)) и включите галочку 🚀 aria2c |
| Скачивание перестало работать | Обновите yt-dlp — см. [Обновление](#обновление-зависимостей) |
| Программа не запускается | Антивирус блокирует `.exe` |

---

<p align="center">
  <b>✦ AURA VIDEO DOWNLOADER ✦</b><br>
  Сделано с ❤️ — бесплатно и навсегда
</p>
