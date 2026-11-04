# FAUN

<p align="center"><img src="docs/mascot.png" alt="FAUN mascot" width="360"></p>

**F**ind · **A**cquire · **U**nify · **N**ormalize

A simple, clean desktop front-end for **ffmpeg**, **yt-dlp** and **mpv**. Works on macOS and Windows.
Trim, convert, compress and tidy video and audio files, download from many sites, and play your files
with a live VU meter, without typing a single command.

Created by Tomas Hajek · Version 1.1

> FAUN is an independent project. It is **not affiliated with or endorsed by** the FFmpeg, yt-dlp
> or mpv projects. "FFmpeg" is a trademark of Fabrice Bellard.

---

## What FAUN stands for

- **Find**: search and browse sites, channels and playlists.
- **Acquire**: download videos and music, one link or a whole list.
- **Unify**: clean file names, number files, write tags and cover art so a folder looks the same.
- **Normalize**: even out the loudness.

It also trims, converts and compresses files.

## What it does

| Tab | What you can do |
|---|---|
| **Setup** | Check, install and update the helper programs (ffmpeg, yt-dlp, mpv, deno, drag & drop support). |
| **Browse** | Search YouTube and other sites, open channels and playlists, play a video or song, add it to the batch. |
| **Quick download** | Paste one link and download it (video or audio, a part of it if you want). Playlist and channel links are handed over to Batch. |
| **Batch download** | A list of links and files. Each item goes through the steps you tick: Download, Convert, Compress, Remove audio, Extract audio, Loudness, Clean name, Write tags. Add an artist to the start of names, number the files, set the album tag. |
| **Files** | Two folders side by side: copy, cut, paste, rename, move to Trash, find duplicates, search in each folder, play files, send them to the other tabs. |
| **Trim** | Cut a part of a video or audio file, with a preview. |
| **Convert** | Change format, quality or codec. |
| **Compress** | Make files smaller (by quality, resolution or target size). |
| **Extract audio / Remove audio** | Save only the sound, or the picture without sound. |
| **Loudness** | Even out the volume of a file. |

Also:

- **Cover and tags panel** at the bottom of every tab: the cover, title, artist and album of the file you select.
- **VU meter** next to it, for the Files tab player: lit bars or analogue needles (click *Bars* / *Needle* to switch).
- **Clean file names**, tag writing (ID3v2.3 + ID3v1 for mp3, so car radios read them), embedded cover art.
- **Dark and light mode**, English and Czech (switch in the top right corner).
- GPU / hardware encoding when your computer supports it (VideoToolbox, NVENC, QSV, AMF).

---

## Download

Get the latest version from the [Releases page](https://github.com/t0mashajek/FAUN/releases/latest).

| Your computer | Download |
|---|---|
| Windows | `FAUN-windows.zip` (unzip it, then run `FAUN.exe`) |
| Mac with **macOS 27 or later** (main build) | `FAUN-mac.zip` |
| Mac with an **older macOS** | `FAUN-mac-legacy.zip` (also runs on newer macOS, with a slightly older look) |

**First start.** The apps are not signed with a paid certificate, so your computer warns you once.

- **Windows:** if SmartScreen appears, click *More info*, then *Run anyway*.
- **macOS 15 (Sequoia) and newer, including 26 and 27:**
  1. Open FAUN. macOS says it cannot verify the app.
  2. Go to *System Settings → Privacy & Security*, scroll down and click **Open Anyway**.
  3. Confirm (password or Touch ID). It does not ask again.
- **macOS 14 (Sonoma) and older:** right-click (or Control-click) the app, choose **Open**, then **Open** again.
- If macOS says the app is "damaged" (any version), run `xattr -cr /Applications/FAUN.app` in Terminal
  (change the path if the app is elsewhere) and open it again.

**Full Disk Access (macOS, only for Safari sign-in).** In the Browse tab, *My YouTube – signed in with*
lets FAUN use your YouTube account (for example Recommended) by reading your browser's cookies. macOS only
lets an app read Safari's cookies if it has Full Disk Access: *System Settings → Privacy & Security →
Full Disk Access*, switch **FAUN** on (click **+** and add FAUN.app if it is not in the list), then quit and
open FAUN again. If you run FAUN from source, give that permission to Terminal instead. Choosing Firefox there does not need it.
Chrome asks for access to your Keychain instead (a password prompt, mentioning Chrome's stored password);
allow it and sign-in works. Normal searching and playing in Browse work without any of this.

Then open the **Setup** tab to install the helper programs.

---

## Requirements

- To run from source: **Python 3.8 or newer** with tkinter (included with the python.org installers). The downloads above need no Python.
- **ffmpeg** (with ffprobe). **yt-dlp** is needed for the download and Browse tabs, **mpv** for playing files.
- Optional: `tkinterdnd2` for drag and drop of files, **deno** (helps yt-dlp with YouTube).

The **Setup** tab installs or updates all of them for you (Homebrew on macOS, Chocolatey on Windows).
You can also install them yourself.

## Run from source

```bash
python3 FAUN.py
```

## Build an app

**macOS.** Put `FAUN.py`, `FAUN.icns` and `build_mac.command` in one folder and run:

```bash
cd ~/FAUN
bash build_mac.command
```

This builds `dist/FAUN-mac-legacy.zip` with the Python from [python.org](https://www.python.org/downloads/macos/)
(3.12 or 3.13, universal2 installer). That app runs on older macOS versions too.

For the main build, give the script another Python, for example the Homebrew one:

```bash
cd ~/FAUN
bash build_mac.command /opt/homebrew/bin/python3
```

This builds `dist/FAUN-mac.zip`. That app only runs on the macOS version its Python was built for or newer
(macOS 27 or later with Homebrew's Python 3.15), but it has the newer look.

The script clears `dist` each time, so move the first zip somewhere safe before building the second one.
At the end it prints the oldest macOS the app needs: a low number such as 10.13 or 11.0 is a legacy build,
27 is the main build.

**Windows.** Install Python from [python.org](https://www.python.org/downloads/windows/) (3.12 or 3.13, with
*tcl/tk and IDLE* ticked), put `FAUN.py`, `FAUN.ico` and `build_windows.bat` in one folder and double-click
`build_windows.bat` (or run it in a Command Prompt). The result is `dist\FAUN.exe`.

---

## Settings and data

The app remembers its settings and the batch list in a small folder of its own:

- macOS: `~/Library/Application Support/FAUN/`
- Windows: `%APPDATA%\FAUN\`

Delete that folder to start from scratch. (Earlier versions, called FFmpegUI, used a folder of that name; FAUN copies its settings once.) Files are never changed without you pressing a button; the
"Delete the original" option in Batch only removes a file after its processed copy has been saved.

## Privacy

FAUN has no account, no tracking and sends nothing to its author. It connects to the internet only
when you download, browse or install tools (through yt-dlp, Homebrew or Chocolatey). If you pick a
browser in the sign-in setting, yt-dlp reads that browser's cookies on your computer, for example for
age-restricted videos.

---

## Third-party software

FAUN does **not** contain these programs. It starts them as separate programs that you install
yourself (the Setup tab can do it). Their licences apply to them.

| Program | Used for | Licence (check the version you install) |
|---|---|---|
| [FFmpeg](https://ffmpeg.org) | converting, trimming, analysing, writing tags | LGPL 2.1+ or GPL, depending on how your build was compiled |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | downloads and Browse | Unlicense |
| [mpv](https://mpv.io) | playing files | GPL 2+ or LGPL 2.1+, depending on the build |
| [deno](https://deno.com) (optional) | JavaScript runtime for yt-dlp | MIT |
| [tkinterdnd2](https://github.com/Eliav2lar/tkinterdnd2) (optional) | drag and drop | MIT |

Please download only content you have the right to download, and follow the terms of the sites you use.

## Licence

FAUN is free software, released under the **GNU General Public License, version 3 or (at your option)
any later version** (GPL-3.0-or-later). See [LICENSE](LICENSE). You may use, study, change and share it;
if you share a changed version, it must stay under the same licence with its source code.

Notices for the programs and libraries FAUN works with are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Copyright © 2026 Tomas Hajek
