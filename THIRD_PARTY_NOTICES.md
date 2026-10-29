# Third-party notices

FAUN is licensed under GPL-3.0-or-later (see `LICENSE`). It works with the programs and libraries below.
The licences listed are the ones I know of; check the version you actually use.

## Programs FAUN runs but does not contain

These are **not** part of FAUN's source or of the downloads in Releases. The Setup tab installs them from
their usual package managers (Homebrew on macOS, Chocolatey on Windows), or you install them yourself.
FAUN starts them as separate programs. FAUN is not affiliated with or endorsed by any of these projects.

| Program | Website | Licence |
|---|---|---|
| FFmpeg (ffmpeg, ffprobe) | https://ffmpeg.org | LGPL 2.1+ or GPL 2+, depending on how the build was compiled |
| yt-dlp | https://github.com/yt-dlp/yt-dlp | Unlicense (public domain) |
| mpv | https://mpv.io | GPL 2+ or LGPL 2.1+, depending on the build |
| deno (optional) | https://deno.com | MIT |

"FFmpeg" is a trademark of Fabrice Bellard, originator of the FFmpeg project.

## Libraries inside the app builds

The `.app` and `.exe` in Releases are made with PyInstaller and contain:

| Component | Website | Licence |
|---|---|---|
| Python (with tkinter / Tcl/Tk) | https://www.python.org | Python Software Foundation licence; Tcl/Tk: BSD-style |
| PyInstaller (runtime) | https://pyinstaller.org | GPL 2+ with an exception that allows bundling into programs under any licence |
| tkinterdnd2 (optional drag and drop) | https://github.com/Eliav2lar/tkinterdnd2 | MIT; includes the tkdnd extension (BSD-style) |

## Content from the web

FAUN can download content through yt-dlp. You are responsible for downloading only what you have the
right to download and for following the terms of the sites you use.
