# FAUN - Find, Acquire, Unify, Normalize
# Copyright (C) 2026 Tomas Hajek
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
FAUN - a simple, clean front-end for ffmpeg, yt-dlp and mpv. Works on macOS and Windows.
FAUN = Find, Acquire, Unify, Normalize.
Created by Tomas Hajek, version 1.0.

It uses FFmpeg (LGPL / GPL), yt-dlp (Unlicense) and mpv (GPL / LGPL). These programs are not part of this
file: they are installed separately (Homebrew / Chocolatey) and only run by it. This project is not
affiliated with, or endorsed by, any of them. "FFmpeg" is a trademark of Fabrice Bellard.

Tabs: Setup / Browse / Quick download / Batch download / Files / Trim / Convert / Compress /
      Extract audio / Remove audio / Loudness
Needs: Python 3.8+ with tkinter, plus ffmpeg + ffprobe (+ yt-dlp for the download and Browse tabs,
       + mpv for the players). The Setup tab can install or update all of them.
  - Windows: winget install Gyan.FFmpeg yt-dlp.yt-dlp
             (or put ffmpeg.exe / ffprobe.exe / yt-dlp.exe next to this script or the .exe)
  - macOS:   brew install ffmpeg yt-dlp   (and brew install python-tk if tkinter is missing)
Optional: tkinterdnd2 for drag and drop (the Setup tab installs it when running from source).
GPU encoding is auto-detected: Apple VideoToolbox (Mac), NVIDIA NVENC / Intel QSV / AMD AMF (Windows).
Run:   python FAUN.py

How the file is organised (search for the "# ----" headers):
  1. Helpers          settings, notifications, ffmpeg command builders, loudness (two-pass loudnorm),
                      clean file names, download history, yt-dlp support, duplicate finder
  2. Czech interface  the CZ dictionary and the translation engine (tr, untr, TrVar, apply_language)
  3. run_gui()        the window. All tabs are built inside it, and the functions in it share the
                      widgets and a `state` dictionary. Long jobs run in background threads and
                      hand their result back with root.after(), because tkinter may only be touched
                      from the main thread.
"""

import base64
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import zlib
from urllib.parse import parse_qs, urlparse

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
BORDER_COLOR = "#8a8f96"  # the lines around the cover / tags panel (visible on light and dark backgrounds)
APP_NAME, APP_AUTHOR, APP_VERSION = "FAUN", "Tomas Hajek", "1.0"
APP_ACRONYM = "Find \u00b7 Acquire \u00b7 Unify \u00b7 Normalize"  # F A U N: what the app is for
# Shown on the Setup tab and in the About box. The programs are installed separately and only run by this app.
APP_CREDITS = ("Uses FFmpeg (LGPL/GPL), yt-dlp (Unlicense), mpv (GPL/LGPL),\n"
               "installed separately. Not affiliated with them.")
# The application logo (the icon, 140 px PNG) shown on the Setup tab.
APP_LOGO_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAIwAAACMCAYAAACuwEE+AAAx60lEQVR42u29eaxk2X3f9/mdc++t7W29b9OzbxySMyRnyCFNSRQX"
    "06RFUJIF2xEcKLJiBpYTwY6CIIhixYqDOIFgOEYQCTEix44RRUYQkTIly4pES5RIiuuQw2WGw1l7enp/3f3WWu5yzi9/nFtVt+pV"
    "1Xu9zXT3vNu4qOpX273nfM/3t/+O8MYfwu5xJYe+kT8e3QTg2AXMLQQieZ1/Q67ytV0QjP7/Sl67JRhGZjyXsef90wDCoUPhVe/f"
    "3IAxJkz8+fN9EPjysXpuBxC92RlmElAmAcNyAGEZDxTl6Xcly2wIlQs84gCGZRRwOwSS3myAmcUipnyMysccSMvXG3v27NmfJMlR"
    "W7MHBDmKmsauWKpMsPiuomdc6pazLDuzsrJyEeiWr9aAuHx/McZEjAHougBHriNYxhnFVFaFAm1AFg8duquVJE8aYz5ohMcRuQfY"
    "JyKI7Oq/E9GjiqoCXEL1Fa885b3/k3aWfXXt/PlXy/FtlePeZ2s/hXH0jQLMJFapMkpcPm4Ac0ePH/9gFJm/AfIRY8y+/kBUHsMN"
    "ququvlshhLCKBDD9BdV/9N5fAv1cUfjfPPPaa38CbALzJSjyKbrPNbGNXCdWMSP6SQDLJlC/4647PmnE/j1j7Xsqq8WjeGTwuV2E"
    "7FxUaX/sRGQAIu/c17y6f3rq1VOfBXrAXAmaqp7jr5Vt5BrBMi5+4vK1zSN3HPloHNd+xRjz3nI19C/a7ALkugLIA2KMMeU4fyXP"
    "0185e+rsH5agoQSOn8I2VwQae41g6TOKBeqlMls7ftddvxrF8f9ixNzh1btS5JhdsNwQ94UBRFW9qnoj5k5ro/9wYWFx3/ra2p+W"
    "bNPoA+taSUOuESx9wNSAjQPHDry1ETd/w0TRE945XxFXu8frd3gAY63xRfGNbt75W8unl58pdZu0IqL81TCNvU7Msnrg8OGPNurN"
    "z4ox93nnCsDKrtnzhrCOqop6Xxhj7ohs/NeSev3pzuZmHzTXxDT2GsBiSqpbP3rH0f8oSZLfFJE59d4hEu3O2xt+GPXeiUgriuxf"
    "m5trndpY3/h6qde4qwXNTgEzSQw1gLXDxw7/ZJzU/i8RMaqqiNjdubpZuEYM4EXEGmt/otGqf29zY/PpCmiu+LBXCZY60D106NBf"
    "SGr1fy0iiQbNdldfuTkVYxURjLEfb9TqX2q32ycqivB1A8y4e99WfCy6uLh4oDHX+h1jzMFdsNwyoKkbaz8o8NtpmnbK+ZwURpgq"
    "mswOfsiMsUsMuNbCwq9ba+9S1WIXLLeITqNaWGvvai0s/HopkuKKProjt4fdoSiyhJhQHdg4fOzw306S2n/qnSt2FdxbThEuoih6"
    "sNGsX9zc2PwS0JxgYl8RYGaKorm9c3e2mvP/svS97Lr1bz1FGECNse/xxv1O1s3Wy3n2OxFNZhuGqYqiBOjNNxd/wRizV1X9rii6"
    "ZUWTN8bsnW8u/gLBE5yMiaapRGCvACx+cXHxgUar+U9UNeE6uvn7Uevpi+LGkNis3329fY6v8xiIqmKMeViUf5um6eVynqdFtqcy"
    "jMwATNpcmPs5Y8wsb+EVDVAlz2PH793J+3f6fdfr+m7BMRDAG2PmmwtzP0cIGUxjGZnFMJPAEgMmSZIDcwvzvwrMqerV6y7b3rBu"
    "q3+pKlzloF3VYF9v0LzBYzCinwjH027vt51zPWbnz+yIYQa6y9LepQ9bY4+UPhe56tU0cVDKU3QsA1gnv6//7EpW25b36g7P4W9d"
    "N0a5zmNwlcARVVVr7JGlvUsfnqDLTGQYM8M6qrKMjeL4ozs1vWav6spXyIRfm3aOXLpeMWvopP+V3ykWJBIkkgmamV4bO0397FWO"
    "waTruvprU0DLubUzfDKDX45mMIz0FaEkSQ6KyJOlKDLXBhZG8vSk/EZjBLFS8UuGp94p6jQsIj9JTMjgd6YphlOvQcBEQpE5XOoR"
    "I8QNCwjqtPL2qyLVHY8BAlIdAxldW96PjYFWr2tnYzDDYhIReTJJkoNZlq2Vc16M4UCnAYYxsERA0ZxvPixijl6pOJo1URgwVjBx"
    "+DqXOzTVvp9gAAoTGaK6QT34QvFOxxIN9QoGTEc41Fgha+cs3d3iwEMLpOs5Z761gncem1i00C30dKWTstMxEAGXe1zqR0e4HANb"
    "MwE8ucf7ScC5KtCIqqqIOdqcbz6cXcq+1J9zpkS0oynMUi0NyWtJ7S3GmH6apb2mgTJhNdnEgChF6qjNRxx+bB8HHlpg7lAdaw1F"
    "5lg/0+X8M6tcemmTInNENYuJBJd5tDpoMwZseB1jYImEInW862fv5f1/92HqSzHq4NTXL/GHf/9p1k91kKgEzVWyzMwxsGBjg6IU"
    "aUEyF3PkbXs4+PACc4ca2MhQ5I6Ns10uPLvGxec3yLuOuG4xnisag20Ob4yxtaT2FuALFYesqVjDA86LZmjQhjqGHiJi7yvvWXc0"
    "ZpMGyvRFANiaoUgdrQN1Hvz4UR762FH2P7BA0oq2EEJ3LePCs2u8/PlzfP93T9FbK4jqhiL1VGoNRidUx5hq7M76YuiOd+/lw//g"
    "UVzmSDcKAO79wCE+8t8/xqc/9VUMijNbV/JOJmQWWEwUFkzec8wfafDWn7iDu3/4IPsfXKA2F28Zg95GzvlnVnnu907z4ufOkm1e"
    "4xiMfr8GP4+9D5Byzs12jrvJ5nRBAsjC0sLPGGPvL6Wo2f4aJgyUBRMHsLjMc+8HD/Gxf/RO3voTx2nureELT951FL3KmTpMJOy5"
    "q8W9P3qY408eYO1Uh5VXN4lqFvU6JaoxcxlgY4MrPO//ew9z8JFFss0CExnECGm7YM9dLV66sMHayTZxPq4wy/bOtB2AxeWeh/7y"
    "MT72j97BQx8/RnN/HV/o5DEwYQwe+ItHOPb4Xi6/ssnamU4YA9UJZojs3NknqIgYxS9vrG/8HsVAhxmvqtwCGDOmu0SlmRXNLy78"
    "jDH22E7SGKaLgBIshefJv/0AH/rlR6nNR6TrOb4IclsGp2DEIBK+r0gdeSesxof+8lHWT3e48MwaUd0G5VS3A82Q5SQKv9HaX+O9"
    "f+dB4poZmV9VpVa3XLrU5aVzG9TbQC+YusOKqZ3S/VYxFNWDqHni5+7nI//gUWzdjoyBEQl5T5XxAMIYdB2LdzR5+BPH6FzOOPfd"
    "VaJaNHPh7AA0KiLGe7+ysb7xmfJv1WK4EY1x3GAd12MAGojsK4EgOxdF5S+UZqutGYrM88R/fD/v+88eJt3IyboOsYKK4BVUBdRQ"
    "+IKe75L6DK8gYhErpJsFRaZ85Fce4/hHDlFkDpvIGIR1ZnRMjKAozf01kvmYogCvw1MVnIc9extIYnCHYgQdTKDO+o1pkJGh3pb3"
    "HG/7qbt4/3/+FrqrOXkvjIGIxSukPqPnuxS+ADWolmMjEhhws8AVyod++VEe+vHjFGlBVDNIOZNXen39MAEi+whJVUzxwwjhNib6"
    "YcaVX72C9TQQjNJXcONAwXe8ey/v/tT9dFbSwUD6vkPNQ+5zur7DnFniePwQB6PjqCpd3y6FoeAKh/fKB37pbURvmwMPpvQe6A4W"
    "vrGCKizd3SKej3GFQ6m43VFcoSwdbGCNwc8bJDEjo6KDO5zlkS3HoGK++8Jz6K2LvP8Xw4LxobIRVcp7VA5GxzkeP8ScWaLrO+Q+"
    "Bx/0Jq8KBlyh5N2C9/8XD9N4YhHvFVP6kMZBfQX+GR2bc9mpH2aL1aReUdlZ/GXw2+WFixEQJVmIeN/ffQtqBOcUY8MbVMGIwUc5"
    "c36JH5n7Se5MHqIuTRwFq8VFvtb9Q57pfoWa1EGEtOfYu6/OO3/mXr7wj5+ltexx4gffNw3KUtH9awvxQMyMms3gvCduWKLI4NVD"
    "IojzeKkMa1US6pRV3R8DITCphyc+dT9RM4ji/hj0tMdbG+/jPY2PshTtxxLR0w4nsx/wZ5ufoS0rGBfj+zaHQJ55Wq2Yv/DzD/H7"
    "//BpWqcLnNFgOV2F87cUazILLEzRR6a16bgiX+rAIkmC+froT9/NobcvkW7kiJGBCBARcjLWX0r46wu/yCO1J4klISdDUfZFh/nk"
    "/Kd4b+vjdH0HVBADva7j4Xfsp/62efJFgxlJttCZdyUGlu5qBZvSj4kkhKLwzC3VaC3EFALSDAqxWEFsXxcSTFRxtMn03zORUOSe"
    "A48scuzJ/aQbORgBFbq+w3tbH+eT859iX3QYRcnJiCXhkdqT/AdLv0hxoYUzBWhl3IzQaRe85bH93P9jx2i3hEjkWvyL24IFts+H"
    "2XGQUXWromesoF6ZP9bkoU/cQbrZB0tgK+8VGxu++u9O8kP2r3AwPsymXyut9/CzOSkdNvih1ic5Hj9Iz/dAhTx3zO2pcedDS3QO"
    "WqR0bG29Wh25KymvK1mIB9cxfnqvQUGNgp+ExGBiwUQEJ5uFvJPT28go0gKJZXIIowSn2OA5vuv9B4ibEa5U1Hu+x/H4QX6o9Uk6"
    "bJCXXVCEoGdt+jUO2MM8kf443/nSWWxigte3FE+qSuE87/rAUbivjtbNgIGuMni67bybCW9mm7/t+GfFCi73HHpsidahBkXmy7gH"
    "OKfUmzHf/MKr3LV0L3/pnT/Mml8jMtHYVxkUT0TEI433UHiHapD7iHD0ngW0ZdG9EeJ1crypfz3lCjSRkMzHIexQXk/19F4x1lBr"
    "RngFWgYbGWxpxkZ1ywOfOMY7fvZeDr9zD0W3GDDPFg2gvJ6objj49j24vK9bCIV3PNJ4DxFRpTdBxatqItZ1nQ8+9j7uXbyXi2dW"
    "iWKL9wzuP+t59h9tse+eebqHI8wIaK9YBd4WA2YblF1T8Lyv9B56+x5UwkT4PrNEhstnO5x5dZUPf+Rx8hkGu2BwFOyPjmGJcepR"
    "VZz31FsxYgS3N5rNLpUYVdSMaB2u43If7MZyxQ5OF5hvcX8d7zySmBBjEli6Z45P/saTfOyfvIsP/PLb+cl/9T7e/18/gpaKp4yB"
    "pg9Sm1iSeYtzHq/g1GOJ2R8dw1FsAUtVdTZEvOPtj/CtL75G2nUDY8GXYxDVLIeOzZEtGHQxqtr/10M87UgkXTPD9K2DqGZZuruF"
    "K4bs4r1iE8Ppl9Y5eNc8WI/K9uvAaRGU0D4b+DBweEXnDRrL7OVUsVhMZAYrdQvDlAptlAQxJ4nBNoJYes8vPMTBR/fQuZzRWc3I"
    "uo53/a0HePCvHCfv9R2A5WIZGz1f+Q0UvHqcFtuOpcMTtYRkLubCa5vYeHjtfZ3myH0LSGzwSxGi1wyU6VYmN+ooLRBbs0StKv0P"
    "9YRet+DA4QVOtl8h1S5myuV4PBExp9KXyXwGKsNcmL6n00o4dXtdK6pZTEUfmHbaKDj1fD3oKIffsYcjT+yjczEN6RAmKM3Zes6D"
    "P30n+s65YFGJbNFlvFPydoEKqHpQIfMZp9KXiYjxU2rKDIae73K6d4IDhxa5dLaNGFDvB/fvnae1kGCMoPMmKNQ36LhOgNHRwERF"
    "8bJ1QzxncU5HrBHvle5mRqNW50J6lu+0v8IcCzgKFB98IygOR40aG7rKtza/SEyCU48rZfiF19rBJJRtsnX6rKdK1LBEDTtQPr1u"
    "dd55hfl99fDRSLCJ4cDbljCxKcVBeA8Cee5Z2leneW+L9Hgc9AgzdNOKCEW3YOVEG6zgfRBJMQnf2vwiG7pKjRoON7hvxeMomGOB"
    "77a/woX0LPVajTxzI9dYHU+84psWanLDmq+a600rUn3e91e4CdSP0G3ntDczElPjc5c/zfd632CePSTUsURExMyxQK45n7n4L1jO"
    "zmNJ8GXwr9cteO251QETXIlkrlL6RLHklNZiuWpFiJoRi3e1UK9b3usKT9KM2LuvQTZn0IVRsaAlss49vYIvfPm7iiVhOTvPZy7+"
    "C3LNmWOBiBhLREKdefbwvd43+KOVT5OYGptrGUXhS/E8JFetBtQjhqL5BhDNdS5Cmxwa6Dv9+o49r4oYSDsFp19Y4/jDe+h2uvzr"
    "C7/OE3M/wltbj7MY7SPTlFO9l/ny+h9xLjtF3TRxGjy9tWbEie9c4sLJjRDlXneQVpU9GWE8KT13qsFpZ2sG329ho1sdkAPzWqFQ"
    "JVlKmDvSoCg9w9XPBA+ssOdgAy+g8wZZUdSE31NX6mxfWebSCxss3dOi6DrUKDVp8Fz7aX4j/x9538Jf5I76vSRSY624xDPtp/jG"
    "5p/hndKwDU4+t8LCvlpFtFfTVKclElxf5Fz3qsXB5ZW5Vj7zZG1HU0qHE0MKXdjf4PtfPsejHzqGtRGqyhfX/pCvrn+epmmRk9Nx"
    "m8QSU5MmrlR4xRh6nYKv/O5JjAhqwFwuIFeYpvj23fpeqe9JkNjgOsVEeR8U8xD7MVZwXjELlrgZ44tgEuvY+9XD4sFmgGnLDjML"
    "VPFOsBbStYJv/rMX+OD/9E6U4PlFPDVpciE7y/+7/M9p2jliYjq+Ta4ZNWkQJxGXznd4+emL/OhP348rdJQdgV7HDYOQWp0LeQNE"
    "ks5WDodIr7637AGaOrJ2XlKzH65epzQWYpZfa/PUH5wkaVm889RpYYno+A6FL2iYVmlKO5wL1lRcN/z5Z17h0ulNorqFTOFsFpjM"
    "j628vkky6NgJtjSRpznuFHDO05hPiOLARI29CVEzmMUjsacy/lQ4T3MxIrIGX5PALn2l2ntc5rGJ4bUvXOB7v/kyyVIc3AzO49Rh"
    "iWmYFoUv6PgOlog6wRttY+HLn3mFzkZG0oxwlXFUryVg8qDHiJQM5Hcwbzo2Tm8Aw4wH37RQeqs5WoqDvmLqvFJvRdRaEd//07Mc"
    "OdDk2HsPoLlSZMHPH3qHhjYmxgi1ZkSeev79v3qe5796gVojQi2YV1Jk3UE0gV3GvK6D1adb40hVmnSFkjQj4npEbz0jmo8xsaHI"
    "/Za8JNXgoGztqRPXbABAJFBU4luqA9B865+9SNHzPPpz94Wga8+FCR4wguBEiWsh2+Qr/+YEL33rIq2FhKQRBYYpA1V9F0B3Iw+M"
    "oqWCc4OO6AbiJcj3Qkk389JxN4ymOq/E9QhrQ9j+md96hQvfXeWuHzvG0qEGtioqBLKu4/mvL/OdPz7NpVNtkrpFY0EuFsiJdAws"
    "oylcwR8yjLPU99aCw85PSUrrG10+IMr7IOq0ZKVJNN/3LUWxoZe6oHh2hsqolk88wQ/0nX/+Ihe+v8aDP3sPxx5cJIrsqO+lUM6/"
    "uslTv3+S0z9YJa5bxBqixOD6LMqQJXudIly0Uyi0mutwCwBmoLUHytw81x3WBZWrusg98/tq1Odj8k5B4Q2nPn+el5+6yPwTSxy4"
    "ex5xYUJ7nYIzz6+xfHIDaw3JXIQakHM55pnORL1OxxyIwZkW3lTfXxuIkmkM432ZmmEN3ilmLir9HzpRkDsHSTNibk+NzmYGDQOr"
    "o8khwVoMEWWTWM5+cZkz319h70cOcujhRWJj+hFZzr+yzunn1/CFp9aKSFPHoYMNmosJLq8o62WYZfNyL9xfoQE0O05KuVkYxgdF"
    "EGDtRBuX60gWgC+UWitmbqnG8npO3vOBjC9kLH/2HK/uW8bP28Hk2MhQW0wCGDcKzGsZciYL/6/2HpgiigbR5tJNr36GSCJMgq1Z"
    "ak0bYks1i1eZ+hmvEMdClJQmfiQjqRAj46KK6ykmNpg1z+V/c45zX7mE3x+h5eeMEaKaJaoZ1MFcRzm+t4VJLHmnGIAfI6Rdx9qF"
    "XhCDPb3KZmRvIGAG4+QVscLGax16Gxk2tsEELV+L6zGH713g3IkNcsB2HEXhiTNl4VSOazrcYgRWUFegPkfWHGY5h0zD4Mpky1Eq"
    "GcpiZVCoJiKoKE59EC8zVqGJhLgRDe6jHyWe9Bn1ihjD3FLJXg2zJW9GdHSAfKZ4A9YLrVM5uubRfRFaCxUVbHqsh6YXTK4s3TeH"
    "p3INGpLTNi/12FxJMbFFV3PEBZNeboAj5roBRvrJSP2YgIZBNNbQWe7RWU6Zv7OFT3WoxxTKsYf38L0vnSVPPZJrqD0qPFoouumQ"
    "s9mg4rcfgFUrU83nfjoBlViORFKmJwgmMdT2JHg3m2FUFSuWuGYRCdHtvgU26TNappi29gQ/CZFMc4aPrSrwongBWSmQ1QJjQSKD"
    "TQRbt/iGIdlbY8+DC7i0X7kQxjcywtrFLlmnIF6IkU23NeZ6HXFzw2JJSimSBLK1nAtPr2BiQZ0fOPDytGDP0SZLBxr0TBAt2q90"
    "dCHlUk1pokbDs0/tW1z/UbijvJNTdAryblAEbd1iagaTGOJWRNyK8c6PxLYm5sWo4gqPiYR6K5psUo+938YGUQJLmHEJORYELv03"
    "6oFynr2Al1LBFlALRc+xeM8ctX01imw0pRSB08+tBebWwErTs8duKpE0FNZCxf1RytNzX7vIPZ84NjSvSxqvtSx3vm0v33qtja8L"
    "0mHo766mG84QHVJm5Hun2LrlwU/exdJDC6QrGaf+7DydCz2iZoxNhHguwjYsvhhaGrMSwuJatCXeNK0uwTtlbl8thBPikumczhyv"
    "/lipVOvutUyI79+fcOjJ/QOrSMrkZTFCZyPn3AtrRLFBC8W0XUgY11tIhxmxllxQ7i4/t87G6Q6tIw1c5gcR3aznuO/xA7zw9Qtk"
    "a554ELgblnZMHe8KWBSo7U147z98lEPv2osvgjVz30/cwff+jxdZ/tYK8VyMrQUl1m+TiBbYUUhaETYKPqB+sHKiYaUhVzluRGWm"
    "ISMp9JMd9LLVBVCJw0kcqjz3vW2Jg4/vJe8Ug/CGqpLULRdeWWP9Yo+4aWGlgI4Pv6s3JmJ9g0SSDOm2XGHpasZrnz8f0grc0Bvs"
    "ck9tPuaRHz1KrwFmUDKxg/zUfr1P6Y195G/ey8HH99Je7pGuZ/QuZ0hieOhv3EvteANbMyRL8fAa2N4DWmta4kZE3LDbijGvwRdj"
    "bSk6k3E9Syc6NyfeUxQYxCSG+3/qzjJgutUj/fJTy6WpL8jFHM39DdNfdgyYHbuXGXPJl34Yn3tMZHj1D86webYbJrhMvlYR0k7B"
    "fY8f5M73HaSdQBSbwH2mNC1EGf+HKBhFIvDes3j/PEd/9BDdyxkSGVQEIiHvOOpLCc3H93CxyKnvSQa5MH5CasP4aawJMaXI4Pz0"
    "9wUl3lObi6m3QoY/cRkALa8/ONn84PSV0EL/frABLKZmKXqOe3/8OPse20PWcShlErgProELJzZ47ZkV4roNQLmYl1URk8I2O5u/"
    "N0zprRTwhI4LInTO9jjxB2ewjbGYTKkAv+sTd7H4+B4y9cGzGZc9W2zZw8UMRRBlTxdTC7dw5IcOEM9HZfpAJc4iQXE9ePc863lB"
    "WlpL2yVPVSPWg5Yb273XhTTNUGQPxGbEWguR+3JYKpVfYir3EwtRIyLvFBz9wEHu+6njZBt5KZ5L4Pkgdp7/8/O43IdxupzDpiuD"
    "qXJD2OWGAGa8NLPf08TnHpMYXv39M6yf2Ay6hBvmljinGCM8+bMPsPT+/aFbQ6O0bqKKH6U8+yayiQ3JnpgDT+wNSeYDGT80dYvc"
    "s3ioSa0Zc3kjHUSKVWefnuDnqLWikDi1zWf65R9JIwqs0bTBwWZlUJlYLRXrg79/P7ZmsHVLkRYc/8hh3vqfPEiR6cjv+kKJ6hHn"
    "Xljn9LMluzhFXk0nNIKXW0WH2coy6oJF0LuU8uz//mKZqjhMZtYyc61Wj3ji5x/iyEeP4AuPiQXbspi6QRJBEsEkgVlswyCRsHD3"
    "HHPHWxSpG1D/4HtRnPPETUtrT3Cr+4rOMfUsV3LcjGguJojIMIl92lk6+Jp7kvC8Vl5rRABNVAKk3/EqLl+vG2zTgg1azb0/eZy3"
    "/Z0HwRAYU4a/gYG0k/P0vz0ZnIWxIJcKuFQE/5Te2O6fN8RKEpGBTOybjeLBZx5bt5z78kVe/vRJ7vvrd5OuZqHMs/TZ5JlDjPDY"
    "zz/I3gfmefnTr9E930NskOv9QKLYsCJVlcUH5zF1S1F1mY95YZOmpbGYhGuyBq9upidUVfBOiWtB6fWliJuVL9t37NnYBEdjzWDq"
    "JliKVoNjZRCuGLKOOsU7mLuzxQM/fTeH3rufvF2UuT9Dn5N6JWlFfPszJ1g72yFpRWEhvtLbYoXdqLaxr0PbdymV3747PIT4X/i/"
    "T7DwwDz7HttLtp5hIlOCJqzkrF1wx0eOsP+dezn/lYuc+/Iy7VMdXM+VObZC1CxLPx5eHDYb1CkmMsL8/gZZpxj+zWyn6AeP67bp"
    "EIymTDSWauH/DUs0F0Faeq59CToX8mBEhXghYvG+eY78yEEOPL6PeD4mW88HwO/H47xX6nMxr3xjmRNPLZM0LGpBXuzB5aKMXd34"
    "3sI3DDCTWEY9UIQ4h3ee7/zPz/Gu//btzN/VIt8sgqOrMiHpRo5tRdz5Y8c4+qHDbJzYZOX7a/QupXTPdXG5J2pY5u5qhY5MTC4+"
    "74ufpBWNiEHZdvJ1YPkoO/gMilOlUeYCO+cRG4CtZZ86W7MkCzHzd8/RONxg32NLzB1vYmNL0SvIN0MZbfU++sxy5rkVvvP7rwYn"
    "XSRwqYCXQ2pH9bpuZFPq12ljibL4c0wBTpdTvvH3v82j/+Uj7HvnXrK1LIgbM0xk8YWSlitu4f55Fh9eRJ1SdAqKToF6xbZCUtGs"
    "MIVzSmtvjbRdlBbP9mzRN1/rC3FQPMcZbCwS3V8UJjK41LN0/wL3/Ng+6gfqZTG+DkITUcuG+8tDNl7RK1lFhlFu9SH3JpmLOfnU"
    "Rb79e68iEnQfTT3ybAcG3bBunGX0ugGmyjID0USIm/gsgCZbz/nW//A97v+b93Lnx4/iui6YikZG8rlVQ3cmtBjoAHG/A0MxO/8j"
    "VAEEBbY+H1Ijt+TCyFbfmnOeuGFoLiXBDVBFTKl7jPTT63+maXnwA0d4+ENHy0i7joBAnQZTuZzh/nz3Y0P9xPG4ZlHgmf/vNV76"
    "8nmMkTIep8h327AZxPOoKJJbFzBbRdPwufZBExt86vnBrz3P2olN7v6rdzK3VKfoOZz3wwkZtCkdepEZ77w0nn8io/ktUd3S2lcP"
    "NVJ9lbc0hbN2jq3Z4KWt5K4Ya8CYAcNUXwPZ0lquyD2NpTr3//ARiszjx0A1zNOR0fSHvjVJKKCL6pbV021e+NOznP/BGnHdhqy/"
    "1CNPt0MYYAwsr8f+CK/bXkcjjQT7g+RCuWjwrRjOfPY0y8+scudfvZMjj+6l3ozwrkx3KJXmgayWyekDWvaeCeJv2BjQFUptLiZu"
    "RCFnuJIVKCKsne+ycLiBaUZDRdOFlqe1hXhQ6jto2C2QdQuiekh/GKYthBcHJSxGJhNfPwVEh7djE4sY6FxOee3pS5z8+jJF5oLu"
    "FQlczJFn2tD2QW/xQ2Z6vTbTiHY22Vzzpgij4gmk9L2ohuc4MInBvdLhhf/1eU6+fZ6D797PkUf2MLevXmbvl6EGVyoYE64zqlmy"
    "do6JQonIgIVkUPkykira//0ic0MHWfkZLRdwv81GNYHcxsKlVzfZe2eLpBmP9pkrRa9Uwt7KaLRTSteAMYKxoavn5ZMbnPnuZS48"
    "v1Z2yrTE8zGaeXi5By920SL4evCjgIdr7VR+kzHMJJ1GyoFVH5jDp4Ft4q7ivrbOyZfanLrzAgv3zXPg/kUWDzepNSJqCzEmsuM9"
    "oDFWWDvT5oU/OcNbPnac2lzQV0Z1k7E0y4qHFoa1PoPPGMEgI/gMdWtC+2KPhaNN4gnScYt+LBDVo8HnXe7orWWk7YKVk5ssv7DG"
    "xvkuvgi+qngxRnNFz2XIy120NJ3FmtFOJq/zNj2v+/Z7W0FTsldf9/CKM2EVJcsFurrJ2okul59ewe4LtUGtvTXq80noaashpNBY"
    "qrF5sceZb18KHSdTRzIXl1n+Y/rDhMnfuNClta9O3LBDhVgYruRqMjchX6W7npFu5jSWkmHX8In5OoFBTnz9Ai7zpBs53ZWUzuWU"
    "Ive43GPj4OSzxqIdB2d7yOkUXSsCgGMJeTBvIFjeEMBMFE99C6pMJBoCJ0xYtFwQrTj0bIbfE7E618PHIRqtVkZ8PVFikLJ+qK/G"
    "GJmSXdD/KQ+99bys9xlmCqKT6aKfK+MKT28jD89VMTLZyxwlhpWX2zz/udPBC2zKsIA1IcRhJeQoX8jgQo5cytFuiWrbV85lZszu"
    "tgbMJNAMijrHgUNIlCZXuOyRywVRLKGzZcNAy4bHKNQ3UQ8BuuxSih5pot7jt2l/4QpPngYT1e1EVysj8OlmQbqRB8bx5XVO8hhD"
    "aEYdG+K5GC7nIfaTeuh6WC8g9QE0nkHrkklAeSPB8oYCpnrjs4AT/B1DcaISwCO5g7ZDLuahy3hkkJoEV7wR3Go+UKrZZi8riUKu"
    "cZ46aiQ7Uh6LwpN3itBCdkb5CSLkXcfq6TZiDZp7zEtddK0YhMQHQtOUyet68wHlpgDMzoBTag1jvpVBgYLpF/wpxoUMPgXyzXyQ"
    "GrxdQZdznnQzx2WuEl6QmeExlzlc5uispAPxt7ULRChV6V5O6a6kmMTARoFvu9BX2JfNFHU6SG4WoNxUgJkNnAp4qgCqOrt8MI09"
    "IFkY/e65XkipVJ1uMpbRYJcGRTTvBcA43X4PjgAGQ3c1HbQq8+Od0L1ibcTKyQ2Kngue6culKCpN41CWe/MDpX/clNsIi8jgnB6b"
    "qjBQ3/PrFC1CbVOxWQy9s9OSnnxIES1ST5H5so2Gzk6u8gxykVVDnKu93AsOurFmQ6jgcuXySxtBv/Kgq/nIzorjYNn+3ncBs2Pw"
    "bB3EEjYVJ1w/bpNv5OWkzshpZZjGGSolZfj3aZ8p60zy1OHzEBdaeXF90NK9mq5JJGyc77B+ph1atnYcrLpBgFHGNpG4WUFyxSLJ"
    "o8HJdgO35L3acMPAM9LPt/EeYw3p5ZSiXWCbIcloWjGRESHvhYhx3itC4pQf24VhzLq2BEXW5R5bM6x/Z4X88f2Y+Tg0KSqDoyYy"
    "nPnmRXzuw84rZzK060KOTRk3Euk7E9/YsfXo7cEwV4YgBsXuPvP4fPtKRQWydh7SDFK3o9ITJfR66ddcped6vPp/vkzvQhfTsKHY"
    "H3j1C2e5/OJaYBen6JlssgZ9Cx3RrYyPkXruap8uBNd1ZBsFdmm6mTwo2e06VANwnG5Xcz2sVKQs7RWnrDx1mbXvrTL3gQOYIzXa"
    "J9t0LvawiYXEwNkULucDdrlZldrbGjBbgKLDJtg+dWQrGfU7Wzivk3N9ddiQRwCXlQ44ZWpmnapiELJ2gXqPEOE7oTt3sVlw+XfP"
    "oA+1MPsTovk4gPJijj7bGepbt/BxiwNmCgUQVr6rFK4zpUWHAtlmHkBjpbJ5+JSvL+uT8m4+SFz3haK9ckc1BzzThj1Z6JnbdcHd"
    "3/fg3sLscnsCpu8l9kp6oTfE0JQ4kvpgGhsj5J2irJWS2SIJQlZ/2SJMUx+6Lwz6iAHnsgGgJDJhY8RbHCy3H2Cq5rWHfDWbmfCt"
    "lXoiCN7bfvqmzhBJ/b68weWrIQZU6TZBpdqgel23OlhuX4YpA73FZoEvKPcmmDT7ofao6ARl1PV88K2wjdLrQ88WDAEsuR/ZzW+S"
    "rtJvLH2rH7ehDhNmVYyQLffCBlgzEsSLVMk2ygK4PnuwXQWCD+UgMpqPO8lIltsAJLclYCrZEKWlpLiux2dhv6PBHu9jH+pn8SOh"
    "OjN4frchsEJDQZ0RKNxwl4qxjXdvN7DcFo674aRUxECZ4FSsZuQrWeny3xoTQkK1gEvL7ZBTVymIm3H2R04IeSx+1nXx5mOYK+0h"
    "8vobRf1E60G3Y1CD6znyjYLk6IQIeLlBadEp8HnIJfZdh+sU2Hoy7HU7iWFyT9FzIQks84P4kqhMahF0ixiWb8bQQFWfUPA9R3q2"
    "g7ehe3a1AZAr0yGyzVA9KSKQK67cCGxqkyFCtp3mlQbPN7Br5a4O83qBxgUfSXq6W9m9bCtrpqvpIIFJM1/JoZmh+Fb1oUwnguZ2"
    "PW4LhhkWR1ZSHUpFtHeyjUv9sN3XYNsYGeT+DiykdkGxXuBFJrPLIH8mZNv1WenNdNwmImlCFWTZ3Cd9tUN6phsqDFwlp8VAtpGT"
    "roT9GykUbTuKtay0nvzkPnAS+gBr3t/ZQre/nl3A3MzQqTR+VvAbBWufO4c0bGgcXfrYJLGsP7eK65bb5nQ9PnUjbdR0xvZ+Ay9e"
    "6t9UDHP76jAARdhUYuMLy0gzYvEvHcE0LJo51p+7yMYL65i4TGZazyHzuHYxvXlQmR/sU1921RoGHXcBcwv6YyZ1icAFr+/aZ0/T"
    "/vol4g/swxWeYiULYEkk1AUtZyFyfSEkj/tBycEoYEDJ1rOhNfbmIpjbSySNdtWQkUk1zQh/IaP3x8u4iymmYUO6wUqBf64d6pgL"
    "xXfctsnjPveDMtpyP+Q3jZV0m4mkUSV0wDT92Y8EuVygX12H+ZBGyUZIU9B6WDtuM8cXfnI7g1J/cd0y9tTzQYcx7ALmdhBNA9Aw"
    "bO9BuWuZXio7QEUSmgsWClZwlzJcu0Ca0WRvr/MUG0VgJxf61gjckL2JblnAhFbnctOGBiZfs85UiLUvjCu9YABct8D1HFHZQHHL"
    "x/MyncFQJk551Ixm0t1K41Sd4zelWV1lmlkBwJHWGZWdWP1GQXExxZvQHavatFkNuE4RRJIVaLtdpXeCcdoT5dLY32454EwC0Ihi"
    "3C9RSR35hTS0oB+vgCQEK0MTxhB4HE9puFWdEOUc97abZzPlC6ql74Wqrt6uzCPV6n4funVnz6yNdUDs6z+QnekM21SVCvPtoL2U"
    "c1ww2k9UZwFmWqqZ815P3W75HSP3o0OxJLEhfXaN7Nk1zN5k+P6Gxa1mZKfaSGwgV7Q7LHvd8p232Fh4r6eYvB/tCC6iGTTVP0Wd"
    "O3E7W40D89uDSNg9ZPVfvsL8SkbtsSVAyJfbdL57OWTw1U2wsjYcYm59NVABde5ExS8xNU81mqG79P2YUZ7nL8S+ptx2jr6xxtOU"
    "3TwN6EbO2m+8TPToAvat87jV4N2VJOyBpCe65f44DNqw3qp6rHqveZ6/UOLBs3UP3Kk6jI4xjAfidtp+Rb0/Uwp8f3uyzOhdiwim"
    "aXHf36R4ahXxoVMVPYf/9mbobhmZke6ct+DhEUS9P9NO269AaAg6xjA6jWF0gjhygKFgxat+MxJzTNXr7coyMujsXe4uX3Zh0Je6"
    "uNNpqJEuvbvVuqNbWL9TEYNT900KVkrAuAliSasMo1PA4iuP5Fn+p5Vdhm9bBbjvtR0xuSMDmSIbDinCpqS3AVjC7Wo5t33GGZ37"
    "LdgwM3SX/mMB1Lrt9le9K25bsTRp3vvAkTJhPGyPzO0SN/II4l1xpttufxWolXM9DpoRhrEjC2t0V8Jy60osUPPebyZJ7YCNonep"
    "brc91S3vk9i5SX4LA0bEmCLL/59Op/PvS/UkBfLydOXpx0XSNEvLVz6UA/WN9fan1bk1bvP47Lh3eHbbtFvWkjbq3NrGevvTQH0W"
    "SCZZSTpDf3ElVRnnspN5XvyOGHPbWktvksOLMZLnxe84l50scVCMgcVPwMXM0IAbOzOgvrm+/lveuYsi1e0rd49bSxSJ8c5d3Fxf"
    "/62SXbIJ871taGAa0/QZJgfEOXe+l/Z+rVR+dXf8b0FxJEgv7f2ac+58qbPmExhmosfXTvJfVZ6bMQVYgFaeZj9IavW7bRTdj6q7"
    "nRXg2+xwYozNs+KPNlZW/7fSMuqUDJONAcfNspKYAJxxi6n6PMmz7KlarfbDxpi9TO6NsHvcfKLIeudOrK+s/pKqFqVVlI5ZR5OY"
    "ZibDyDamtgESVU3V++8mteSDIqaxC5qbX29R9avt9c3/Ks/zM+XfuyVYsglgmaif2u0szDHAVAHVKIrigiIvxkn8YRGJdkFzM4NF"
    "8/Zm57/pdbvfJoQA2mNgmaXHzATMLJapAgegWeT5a4i8EkXR+4wxNfrxp93j5tBZRKz3vt3tdP+7brv950AyBpYds8sswEz6/yTg"
    "eKCZZ9lL3ut3ojh6jzFmXncV4ZsCLMYY65y70N5s/1Kv0+m7/zdLkExiFz9Nd9mp0ssUsFT/pkDTFcX5Is+/GCXRPcZGx8qU+10R"
    "9QaIIEDEGOOK/KnNtfVfztL05TFm2U7RZdw62qkOw5QJHweOJ8Sb2r1O9/ORjdRG9pFSrxlk7u3O5Q0HCqVDNc976W+uraz+U+/9"
    "esn2VbBME0VT/S87AYzsADiMgSYCTJqmX/den46iaL8x5g4ZBmDcBPbaPa7FCRfG3Uh5OOe+1t5s/2pnc/PflfNblL6WlFAVMMsq"
    "mhpD2gkIpvljovJC4pLmklI2Vs9GeSFRs9l8ImnWf8pa+7iIKTsgqFbElezwWnbBMXzUPkgQQdXjnHsq6/R+u9PpfKMEgq2YzekU"
    "dnFTdBe9WsDMAk3/TMaA039eLx9zIGm0Go8ktfqHrLXvNsYcqmxFUk0n2I1NTT5MKW7KGSk7Znl/3jn39Szt/XG33X22BEJcPvYq"
    "4KgCJStBUlwpWK4EMIyBpp8n0wdNPMY44yCKy4tTa+2+Wq32gE2St0fWPCQiRxFZEpGayC7JTKSWwMopqquqeqZw/gcuy76bpukL"
    "zrlL5bxE5eIcB0c2wRqquv9n5vBeDWCmgcZMAE2fceIZj/TBU/5tPo7jJWvtgli714gk5VW/qdHTr3byqpk6d9k5t57n+SqwUQKg"
    "DxJKIGQzHosJYPFXCpYr1RtmgcaOial4whlNAJdURFG1Pc+bXa8Zn8BqLK//93EQFBUWyScwyjirXDFY4MrafSijGa1+7DUd07bd"
    "2I1UAdMHmak8VoOcb2bQ6ITH8XGtZkMWE0BTbAOUqwLLlQJmGmim5dBUb6gKlGiMmaqrR6Y4Dd+MgIHZWZB9ABRjwHETRI+bodxe"
    "UU5TdJU3JFNWQr86sroabMXM245ZZNfUnjimugOmmXSOM4qfwmJXrJdcpV421fQe13HGn1u25tnIFIZ5MwFHJ/x/Gsv4KQziJoBk"
    "ksms1zrp1wqcSUrxeB7N+N+2A8ubnWF2Appx5pkElGtilRuxciexDVMAMev/7AJmImCYAJjt/s/1YpUbSfUywwyfFfHeBcuVgWaa"
    "jjNNmdUbMcE3GjhMAccuWK4cNOyQRfRGTiyvM3iu5LU3O1i2A8INBckbOSlyE1zD7QakGw6S6mF3x/+2AMzrdvz/SfDrp7oWYRYA"
    "AAAASUVORK5CYII="
)

HERE = os.path.dirname(os.path.abspath(__file__))
NO_WINDOW = 0x08000000 if IS_WIN else 0  # hide console popups on Windows

# Text-mode settings for child processes (UTF-8 so non-English titles/paths survive on Windows)
TEXT = dict(text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)

# Fonts differ per platform
if IS_WIN:
    UI_FONT = "Segoe UI"
elif IS_MAC:
    UI_FONT = "Helvetica Neue"
else:
    UI_FONT = "DejaVu Sans"

# Common install locations (GUI-launched apps on macOS often don't see Homebrew in PATH)
EXTRA_BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]


# ------------------------------------------------------------------ helpers
def _search_dirs():
    """Folders where the helper programs (ffmpeg, yt-dlp, mpv) are looked for, besides PATH."""
    dirs = [HERE]
    if getattr(sys, "frozen", False):  # packaged app: also look next to the .exe
        dirs.insert(0, os.path.dirname(sys.executable))
    if IS_WIN:  # tools installed while the app is running aren't on its PATH yet
        choco = os.environ.get("ChocolateyInstall", r"C:\ProgramData\chocolatey")
        dirs.append(os.path.join(choco, "bin"))
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(os.path.join(local, "Microsoft", "WinGet", "Links"))
    return dirs


def find_tool(name):
    """Locate ffmpeg/ffprobe/yt-dlp. Only uses .exe files on Windows."""
    local_names = (name + ".exe", name) if IS_WIN else (name,)
    for d in _search_dirs():
        for n in local_names:
            p = os.path.join(d, n)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p

    found = shutil.which(name)
    if found:
        return found

    if not IS_WIN:
        for d in EXTRA_BIN_DIRS:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None


def resource_path(name):
    """Path of a bundled file: inside the PyInstaller bundle when packaged, next to the script otherwise."""
    return os.path.join(getattr(sys, "_MEIPASS", HERE), name)


def to_seconds(t):
    """'90', '1:30', '00:01:30.5' -> float seconds."""
    t = str(t).strip()
    if not t:
        return None
    parts = [float(x) for x in t.split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def fmt_time(s):
    """Seconds -> 'HH:MM:SS.ss'."""
    s = max(0, s or 0)
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def fmt_eta(sec):
    """Time left as 0:45 / 12:30 / 1:02:03."""
    sec = int(max(0, sec))
    h, m, s2 = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s2:02d}" if h else f"{m}:{s2:02d}"


def progress_text(base, speed="", eta=""):
    """'Downloading… 40 %' + speed + time left (the double spaces mark the extra part for the translator)."""
    if speed and eta:
        return f"{base}  ·  {speed}  ·  {eta} left"
    if eta:
        return f"{base}  ·  {eta} left"
    return base


def get_duration(path):
    """Length of a media file in seconds (via ffprobe), or None if it can't be read."""
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        return None
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, **TEXT).stdout.strip()
        return float(out)
    except Exception:
        return None


VIDEO_EXTS = ("mp4", "mov", "mkv", "avi", "webm", "m4v", "wmv", "flv", "ts", "mpg", "mpeg")
AUDIO_EXTS = ("mp3", "m4a", "aac", "wav", "flac", "ogg", "opus", "wma", "aiff", "aif")


def has_video_stream(path):
    """True: real video. False: audio only (cover art doesn't count). None: unknown."""
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        return None
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream_disposition=attached_pic", "-of", "csv=p=0", path],
            capture_output=True, **TEXT)
        if r.returncode != 0:
            return None
        return r.stdout.strip().split(",")[0] == "0"
    except Exception:
        return None


def tool_env():
    """Environment for child processes."""
    env = os.environ.copy()
    if not IS_WIN:  # make sure Homebrew tools are on PATH when launched from Finder
        env["PATH"] = os.pathsep.join(EXTRA_BIN_DIRS + [env.get("PATH", "")])
    env["PYTHONUTF8"] = "1"            # yt-dlp: print UTF-8 even when piped (Windows)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def kill_proc(p):
    """Stop a process (and its children, e.g. yt-dlp's ffmpeg, on Windows)."""
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           capture_output=True, creationflags=NO_WINDOW)
        else:
            p.terminate()
    except Exception:
        pass


# ---- settings (remembered between runs)
def settings_path():
    """Where the settings file lives (per user and per operating system)."""
    if IS_MAC:
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    elif IS_WIN:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    new, old = os.path.join(base, APP_NAME), os.path.join(base, "FFmpegUI")  # (the app was called FFmpegUI before)
    if not os.path.isdir(new) and os.path.isdir(old):
        try:
            shutil.copytree(old, new)  # take the old settings along once
        except OSError:
            pass
    return os.path.join(new, "settings.json")


def load_settings():
    """Read the saved settings; an empty dict if there are none or the file is damaged."""
    try:
        with open(settings_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(data):
    """Write the settings file; failures are ignored (settings are a convenience)."""
    try:
        p = settings_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ---- notifications + keep-awake (macOS and Windows)
def notify(title, message):
    """Notification + sound when a job finishes."""
    try:
        if IS_MAC:
            def esc(x):
                """Escape text for use inside an AppleScript string."""
                return str(x).replace("\\", "\\\\").replace('"', '\\"')
            script = (f'display notification "{esc(message)}" with title "{esc(title)}" '
                      f'sound name "Glass"')
            subprocess.Popen(["osascript", "-e", script])
        elif IS_WIN:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

            def q(x):
                """Escape text for use inside a single-quoted PowerShell string."""
                return str(x).replace("'", "''")
            ps = ("[Windows.UI.Notifications.ToastNotificationManager, "
                  "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;"
                  "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                  "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                  "$x=$t.GetElementsByTagName('text');"
                  f"$x.Item(0).AppendChild($t.CreateTextNode('{q(title)}')) | Out-Null;"
                  f"$x.Item(1).AppendChild($t.CreateTextNode('{q(message)}')) | Out-Null;"
                  "$n=[Windows.UI.Notifications.ToastNotification]::new($t);"
                  "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                  "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'"
                  ").Show($n)")
            subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                              "-Command", ps], creationflags=NO_WINDOW)
    except Exception:
        pass


def awake_on(pid):
    """Stop the computer from sleeping while a job runs.
    Mac: caffeinate bound to the process. Windows: must be released with awake_off()
    from the same thread."""
    try:
        if IS_MAC:
            subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(pid)])
        elif IS_WIN:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # CONTINUOUS|SYSTEM_REQUIRED
    except Exception:
        pass


def awake_off():
    """Let the computer sleep again after a long job (Windows; macOS ends its caffeinate helper elsewhere)."""
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # CONTINUOUS only
        except Exception:
            pass


# ---- encoding options
# ---------------------------------------------------------------- Czech interface
# English is the working language of the code; Czech is only a layer on top for what is shown.
LANG = {"cz": False}
_I18N = {"pats": None, "rev": None}
CZ = {
    # ---- window, tabs, setup
    "Dark mode": "Tmavý režim",
    "Open file…": "Otevřít soubor…",
    "No file selected": "Není vybrán žádný soubor",
    "Setup": "Nastavení",
    "Quick download": "Rychlé stažení",
    "Browse": "Procházet",
    "Batch download": "Dávkové stahování",
    "Trim": "Střih",
    "Convert": "Převod",
    "Compress": "Komprese",
    "Extract audio": "Extrakce zvuku",
    "Remove audio": "Odebrání zvuku",
    "Loudness": "Hlasitost",
    "Install": "Instalovat",
    "Verify": "Ověřit",
    "Update": "Aktualizovat",
    "Verify all": "Ověřit vše",
    "mpv  (player: pause, timeline)": "mpv  (přehrávač: pauza, časová osa)",
    "deno  (YouTube for yt-dlp)": "deno  (YouTube pro yt-dlp)",
    "Install / Update open an administrator window (Windows will ask for approval).\nPress Verify afterwards to refresh the status.":
        "Instalace a aktualizace otevřou okno správce (Windows požádá o souhlas).\nPo dokončení stiskněte Ověřit a obnovte stav.",
    "Homebrew installs in a Terminal window (it asks for your Mac password).\nffmpeg, yt-dlp, mpv and deno install here; the output is shown above.":
        "Homebrew se instaluje v okně Terminálu (zeptá se na heslo k Macu).\nffmpeg, yt-dlp, mpv a deno se instalují zde; výstup je vidět výše.",
    "✗ not installed": "✗ není nainstalováno",
    "checking…": "kontroluji…",
    "Check finished.\n": "Kontrola dokončena.\n",
    "Checking installed versions and available updates…\n": "Kontroluji nainstalované verze a dostupné aktualizace…\n",
    "Finished.\n": "Hotovo.\n",
    "Cancelled.\n": "Zrušeno.\n",
    "Failed (exit code {}).\n": "Selhalo (návratový kód {}).\n",
    "Could not run the command: {}\n": "Příkaz se nepodařilo spustit: {}\n",
    "Setup step finished": "Krok nastavení dokončen",
    "Setup step failed": "Krok nastavení selhal",
    "Busy": "Zaneprázdněno",
    "Wait for the current job to finish first.": "Nejdřív počkejte, až skončí aktuální úloha.",
    "Install Homebrew": "Instalace Homebrew",
    "A Terminal window will open and run the official Homebrew installer.\nFollow the prompts there (it asks for your Mac password).\n\nWhen it finishes, come back and press Verify.":
        "Otevře se okno Terminálu a spustí oficiální instalátor Homebrew.\nŘiďte se pokyny tam (zeptá se na heslo k Macu).\n\nAž skončí, vraťte se sem a stiskněte Ověřit.",
    "Opened Terminal for the Homebrew installer. Press Verify when it is done.\n":
        "Pro instalátor Homebrew se otevřel Terminál. Až skončí, stiskněte Ověřit.\n",
    "Could not open Terminal": "Terminál se nepodařilo otevřít",
    "Administrator approval needed": "Je potřeba souhlas správce",
    "Windows will ask for administrator approval, then a PowerShell window\nruns the Chocolatey command.\n\nWhen it finishes, close it and press Verify here.":
        "Windows požádá o souhlas správce a poté okno PowerShellu\nspustí příkaz Chocolatey.\n\nAž skončí, zavřete ho a stiskněte zde Ověřit.",
    "Opened an administrator PowerShell window. Press Verify when it is done.\n":
        "Otevřelo se okno PowerShellu správce. Až skončí, stiskněte Ověřit.\n",
    "Could not start PowerShell": "PowerShell se nepodařilo spustit",
    # ---- quick download
    "Paste": "Vložit",
    "Clear": "Vymazat",
    "Retry": "Znovu",
    "Keep retrying": "Opakovat dokola",
    "Video link": "Odkaz na video",
    "Quality": "Kvalita",
    "Choose…": "Vybrat…",
    "Save to": "Uložit do",
    "Exact cut (slower)": "Přesný střih (pomalejší)",
    "Only part (optional)": "Jen část (volitelné)",
    "One video per link. Leave 'Only part' empty to download all of it; examples: 1:30 to 2:45, or just a start / just an end.\nA playlist link is handed over to the Batch download tab (one row per video). A finished video is loaded into the other tabs.\nFile names: see 'Clean file names' at the bottom of the window.":
        "Jedno video na odkaz. Nechte „Jen část“ prázdné, chcete-li stáhnout celé video; příklady: 1:30 až 2:45, nebo jen začátek / jen konec.\nOdkaz na playlist se předá do záložky Dávkové stahování (jeden řádek na video). Hotové video se načte do ostatních záložek.\nNázvy souborů: viz „Čisté názvy souborů“ dole v okně.",
    "Type": "Typ", "Item": "Položka", "Status": "Stav",
    "Link": "Odkaz", "File": "Soubor", "Playlist": "Playlist",
    "Waiting": "Čeká", "Failed": "Selhalo", "Skipped": "Přeskočeno", "Cancelled": "Zrušeno",
    "Done": "Hotovo", "Ready": "Připraveno", "Starting…": "Spouštím…", "Retrying…": "Zkouším znovu…",
    "Downloading…": "Stahuji…", "Writing tags…": "Zapisuji značky…",
    "Already downloaded": "Už staženo", "Already downloaded · {}": "Už staženo · {}",
    "Checking for a playlist…": "Kontroluji, zda jde o playlist…",
    "Checking whether the link is a playlist…": "Kontroluji, zda je odkaz playlist…",
    "That link is a single video. Press Start to download it.": "Tento odkaz je jedno video. Stáhnete ho tlačítkem Start.",
    "Single video: press Start": "Jedno video: stiskněte Start",
    "Failed · retrying automatically": "Selhalo · zkouším automaticky znovu",
    "Failed · retry #{} in {} s": "Selhalo · pokus č. {} za {} s",
    "Downloading… {} %": "Stahuji… {} %",
    "Done · {} MB": "Hotovo · {} MB",
    "Done · {} MB · {}": "Hotovo · {} MB · {}",
    "Finished · {} MB": "Dokončeno · {} MB",
    "Downloaded · {} MB · ready to edit": "Staženo · {} MB · připraveno k úpravám",
    "Downloaded · {} MB · ready to edit · {}": "Staženo · {} MB · připraveno k úpravám · {}",
    "✓ Downloaded · {} MB": "✓ Staženo · {} MB",
    "Download finished · {} MB": "Stahování dokončeno · {} MB",
    "→ Batch download: {} videos": "→ Dávkové stahování: {} videí",
    "Playlist moved to the Batch download tab ({} added). Check the list and press Start.":
        "Playlist přesunut do záložky Dávkové stahování (přidáno: {}). Zkontrolujte seznam a stiskněte Start.",
    "Playlist moved to the Batch download tab ({} added, {} already there). Check the list and press Start.":
        "Playlist přesunut do záložky Dávkové stahování (přidáno: {}, již v seznamu: {}). Zkontrolujte seznam a stiskněte Start.",
    "Clipboard is empty": "Schránka je prázdná",
    "There is nothing to paste. Copy a video link first.": "Není co vložit. Nejdřív zkopírujte odkaz na video.",
    "No link": "Chybí odkaz",
    "Paste a full video link (starting with http).": "Vložte celý odkaz na video (začíná http).",
    "Folder error": "Chyba složky",
    "Bad time": "Špatný čas",
    "For 'Only part', End must be after Start (use formats like 90, 1:30 or 00:01:30).":
        "U „Jen část“ musí být konec za začátkem (použijte tvary jako 90, 1:30 nebo 00:01:30).",
    "End must be after Start.": "Konec musí být za začátkem.",
    "Big playlist": "Velký playlist",
    "This playlist has {} videos. Add all of them to the Batch download list?":
        "Tento playlist má {} videí. Přidat všechna do seznamu Dávkového stahování?",
    "This playlist has {} videos. Add all of them to the batch?": "Tento playlist má {} videí. Přidat všechna do dávky?",
    "Details": "Podrobnosti",
    "yt-dlp error": "Chyba yt-dlp", "Could not run yt-dlp": "yt-dlp se nepodařilo spustit",
    "ffmpeg error": "Chyba ffmpeg", "Could not run ffmpeg": "ffmpeg se nepodařilo spustit",
    "The download failed": "Stahování selhalo", "The job failed": "Úloha selhala",
    "Download failed.": "Stahování selhalo.", "Download failed": "Stahování selhalo",
    "{} missing": "{} chybí",
    "\n\nYou can also use the Setup tab.": "\n\nMůžete také použít záložku Nastavení.",
    "Put {}.exe next to this program, or install it with:\n  winget install {}":
        "Dejte {}.exe vedle tohoto programu, nebo ho nainstalujte příkazem:\n  winget install {}",
    "Install it with:  brew install {}": "Nainstalujte ho příkazem:  brew install {}",
    "Saved:\n{}\n\nOpen the folder?": "Uloženo:\n{}\n\nOtevřít složku?",
    "Job running": "Úloha běží",
    "A job is still running. Quit and cancel it?": "Úloha stále běží. Ukončit program a zrušit ji?",
    # ---- trim / convert / compress / audio / loudness
    "Start": "Začátek", "End": "Konec",
    "Frame-accurate (slower, re-encodes)": "Přesně na snímek (pomalejší, překóduje)",
    "Formats: 90  ·  1:30  ·  00:01:30.5": "Tvary zadání: 90  ·  1:30  ·  00:01:30.5",
    "Output format": "Výstupní formát", "Video codec": "Videokodek",
    "H.265 makes much smaller files (plays on Macs/iPhones, not every old player).\nGIF and WebM always use the CPU and ignore the codec setting.":
        "H.265 dělá mnohem menší soubory (hraje na Macích/iPhonech, ne v každém starém přehrávači).\nGIF a WebM vždy používají procesor a nastavení kodeku ignorují.",
    "Max resolution": "Maximální rozlišení", "Keep original": "Ponechat původní",
    "  MB   (optional)": "  MB   (volitelné)", "Target file size": "Cílová velikost souboru",
    "Fill in a target size (e.g. 25 for Discord or email) to override Quality.\nThe result is approximate (about ±10 %).":
        "Zadejte cílovou velikost (např. 25 pro Discord nebo e-mail), která přebije Kvalitu.\nVýsledek je přibližný (asi ±10 %).",
    "Audio format": "Formát zvuku",
    "Saves the video without its sound track (no quality loss).": "Uloží video bez zvukové stopy (bez ztráty kvality).",
    "Preset": "Předvolba", "Target level": "Cílová úroveň", "{} LUFS": "{} LUFS",
    "Pick a preset or drag the slider (or use − / +) for your own level in LUFS.\nCloser to 0 = louder. Very high levels (above about -12) get limited and can sound squashed.\nEvery video set to the same level plays at the same volume. The picture is copied\nuntouched (fast); only the sound is re-encoded. Keeps the first audio track.":
        "Vyberte předvolbu nebo posuňte jezdec (nebo použijte − / +) pro vlastní úroveň v LUFS.\nBlíž k 0 = hlasitěji. Velmi vysoké úrovně (nad asi -12) se omezují a mohou znít stlačeně.\nKaždé video nastavené na stejnou úroveň hraje stejně hlasitě. Obraz se kopíruje\nbeze změny (rychle); překóduje se jen zvuk. Zachová se první zvuková stopa.",
    "Analyzing loudness…": "Analyzuji hlasitost…", "Analyzing… ": "Analyzuji… ",
    "GPU / hardware encoder: detecting…": "GPU / hardwarový kodér: zjišťuji…",
    "Use GPU / hardware encoder ({})": "Použít GPU / hardwarový kodér ({})",
    "GPU encoder: not available (using CPU)": "GPU kodér: není k dispozici (použije se procesor)",
    "GPU encoder failed, retrying on CPU…": "GPU kodér selhal, zkouším znovu na procesoru…",
    "Clean file names": "Čisté názvy souborů",
    "Remove tags like (Official Video), (Audio)": "Odstranit značky jako (Official Video), (Audio)",
    "Also remove these tags:": "Odstranit i tyto značky:",
    "comma-separated, e.g.  OST, *soundtrack*   (* = anything)": "oddělené čárkou, např.  OST, *soundtrack*   (* = cokoli)",
    "Cancel": "Zrušit",
    "Audio only  ·  ": "Jen zvuk  ·  ", "Length {}  ·  {} MB": "Délka {}  ·  {} MB",
    "Loudness matched · {}": "Hlasitost srovnána · {}", "{} → {} LUFS": "{} → {} LUFS",
    "No file": "Žádný soubor", "Open a video or audio file first.": "Nejdřív otevřete video nebo zvukový soubor.",
    "No video": "Žádné video",
    "This file has no video, so this task doesn't apply.\nTry Trim, Convert, Extract audio or Loudness.":
        "Tento soubor nemá obraz, takže se úloha nepoužije.\nZkuste Střih, Převod, Extrakci zvuku nebo Hlasitost.",
    "Bad size": "Špatná velikost", "Target size must be a number, e.g. 25": "Cílová velikost musí být číslo, např. 25",
    "Unknown length": "Neznámá délka",
    "Can't read the video length (ffprobe missing?), so a target size can't be calculated.":
        "Nelze přečíst délku videa (chybí ffprobe?), proto nelze vypočítat cílovou velikost.",
    "Target too small": "Cíl je příliš malý",
    "That size is too small for a video of this length. Try a larger size.":
        "Tato velikost je pro video této délky příliš malá. Zkuste větší.",
    "Same file": "Stejný soubor", "Choose a different output file name.": "Zvolte jiný název výstupního souboru.",
    "No audio": "Žádný zvuk", "This file has no audio track to adjust.": "Tento soubor nemá zvukovou stopu k úpravě.",
    "Could not measure the loudness.": "Hlasitost se nepodařilo změřit.",
    "Silent audio": "Tichý zvuk", "The audio is silent, so there is no loudness to match.":
        "Zvuk je tichý, takže není co srovnávat.",
}
CZ.update({
    # ---- batch
    "Next to each original": "Vedle každého originálu", "Choose a folder…": "Vyberte složku…",
    "Skip current item": "Přeskočit aktuální",
    "Add files…": "Přidat soubory…", "Paste links": "Vložit odkazy", "Remove selected": "Odebrat vybrané",
    "Clear all": "Vymazat vše", "Redo all": "Vše znovu", "Retry failed": "Zopakovat selhané", "Retry skipped": "Zopakovat přeskočené",
    "There are no skipped items in the list.": "V seznamu nejsou žádné přeskočené položky.",
    "Steps:": "Kroky:", "Download": "Stáhnout", "Clean name": "Čistý název", "Write tags": "Zapsat značky",
    "Add to start of names": "Přidat na začátek názvů",
    "Number files (01, 02…)": "Očíslovat soubory (01, 02…)",
    "Download quality": "Kvalita stahování", "Downloads go to": "Stahovat do", "Keep processed files in a different folder": "Zpracované soubory ukládat do jiné složky",
    "Processed files go to": "Zpracované soubory do", "Reset": "Obnovit",
    "Delete the original once it has been processed": "Smazat originál po zpracování",
    "Skip videos I've already downloaded": "Přeskočit už stažená videa",
    "Forget history…": "Zapomenout historii…",
    "not used: the Download step isn't ticked": "nepoužije se: není zaškrtnut krok Stáhnout",
    "not used by the ticked steps": "zaškrtnuté kroky to nepoužijí",
    "Each item goes through the ticked steps in order, and only the final file is kept. Finished steps are skipped, so you can download now and tick Loudness later. Greyed-out steps can't be combined with the ticked ones.\nPlaylist links expand into one row per video; videos downloaded before are skipped (Forget history… resets that).\nAdd to start of names: 'Band' gives 'Band - Song'. Number files gives '01 - Band - Song' (list order). Write tags puts Artist (that text), Title and Track number into the files.\nClean name needs a free file name: use a separate 'Processed files go to' folder, or tick 'Delete the original'.":
        "Každá položka projde zaškrtnutými kroky popořadě a ponechá se jen výsledný soubor. Hotové kroky se přeskočí, takže můžete teď stáhnout a Hlasitost zaškrtnout později. Zašedlé kroky nelze kombinovat se zaškrtnutými.\nOdkazy na playlist se rozbalí na jeden řádek na video; dříve stažená videa se přeskočí (Zapomenout historii… to vynuluje).\nPřidat na začátek názvů: „Kapela“ dá „Kapela - Skladba“. Očíslování dá „01 - Kapela - Skladba“ (podle pořadí v seznamu). Zapsat značky vloží do souborů Interpreta (tento text), Název a Číslo stopy.\nČistý název potřebuje volný název souboru: použijte samostatnou složku „Zpracované soubory do“, nebo zaškrtněte „Smazat originál“.",
    "Added {} file(s) to the batch": "Do dávky přidáno souborů: {}",
    "Added {} link(s) to the batch": "Do dávky přidáno odkazů: {}",
    "Playlist expanded: {} video(s) added": "Playlist rozbalen, přidáno videí: {}",
    "Nothing to retry": "Není co opakovat", "There are no failed items in the list.": "V seznamu nejsou žádné selhané položky.",
    "No links found": "Nenalezeny žádné odkazy",
    "Copy one or more video links first (one per line works well), then press Paste links.":
        "Nejdřív zkopírujte jeden či více odkazů na videa (nejlépe jeden na řádek) a pak stiskněte Vložit odkazy.",
    "Forget downloaded videos": "Zapomenout stažená videa",
    "Forget which videos you have downloaded before?\n\nPlaylists will then download everything again.":
        "Zapomenout, která videa jste už stáhli?\n\nPlaylisty se pak stáhnou celé znovu.",
    "Download history cleared": "Historie stahování smazána",
    "Skipping the current item…": "Přeskakuji aktuální položku…",
    "Item {} of {}": "Položka {} z {}",
    "Still checking": "Ještě kontroluji",
    "Some links are still being checked for playlists. Try again in a moment.":
        "Některé odkazy se ještě kontrolují, zda jde o playlisty. Zkuste to za chvíli.",
    "No steps": "Žádné kroky", "Tick at least one step to run.": "Zaškrtněte alespoň jeden krok ke spuštění.",
    "These steps don't fit together": "Tyto kroky k sobě nepasují",
    "Nothing new to download": "Není co nového stáhnout",
    "All {} video(s) in the list were downloaded before.\n\nUntick 'Skip videos I've already downloaded' to download them again.":
        "Všechna videa v seznamu ({}) jste už stáhli.\n\nOdškrtněte „Přeskočit už stažená videa“, abyste je stáhli znovu.",
    "Nothing to do": "Není co dělat", "Add files or paste links first.": "Nejdřív přidejte soubory nebo vložte odkazy.",
    "Everything you ticked is already done for every item (or doesn't apply to local files).\n\nTick another step, or press Redo all to run them again.":
        "Vše zaškrtnuté je u každé položky už hotovo (nebo se nepoužije u místních souborů).\n\nZaškrtněte jiný krok, nebo stiskněte Vše znovu.",
    "On the Compress tab, target size must be a number, e.g. 25 (or leave it empty).":
        "V záložce Komprese musí být cílová velikost číslo, např. 25 (nebo nechte prázdné).",
    "Batch finished": "Dávka dokončena",
    "Batch finished: {}": "Dávka dokončena: {}",
    "Batch download: {} item(s)…": "Dávkové stahování: položek {}…",
    "{} done": "hotovo: {}", "{} already downloaded": "již staženo: {}",
    "\nDouble-click a failed item to see why.": "\nDvojklikem na selhanou položku zjistíte proč.",
    "could not rename: {}": "nelze přejmenovat: {}", "Nothing to rename yet": "Zatím není co přejmenovat",
    "Could not rename the file: {}": "Soubor se nepodařilo přejmenovat: {}",
    "Nothing to tag yet": "Zatím není co označit", "Could not write the tags: {}": "Značky se nepodařilo zapsat: {}",
    "Not downloaded yet: tick the Download step": "Ještě nestaženo: zaškrtněte krok Stáhnout",
    "File not found: {}": "Soubor nenalezen: {}",
    "This file has no video, so {} doesn't apply": "Soubor nemá obraz, takže „{}“ se nepoužije",
    # ---- browse
    "Search on:": "Hledat na:", "Sites…": "Weby…", "Search for:": "Hledat:", "Channel shows:": "Kanál zobrazuje:",
    "Search": "Hledat", "◀ Back": "◀ Zpět", "Title": "Název", "Live": "Živě", "Channel": "Kanál",
    "Length": "Délka", "Views": "Zhlédnutí",
    "Play": "Přehrát", "Pause": "Pauza", "Resume": "Pokračovat", "Stop": "Stop",
    "Add to batch": "Přidat do dávky", "Copy link": "Kopírovat odkaz", "Load more": "Načíst další",
    "● LIVE": "● ŽIVĚ", "soon": "brzy", "LIVE NOW": "TEĎ ŽIVĚ",
    "▶ Playlist: ": "▶ Playlist: ", "👤 Channel: ": "👤 Kanál: ", "Channel: ": "Kanál: ", "Playlist: ": "Playlist: ",
    "Searching…": "Hledám…", "Loading more…": "Načítám další…",
    "Type something to search for, or paste a link.": "Napište, co hledat, nebo vložte odkaz.",
    "Nothing found: {}": "Nic nenalezeno: {}", "No videos found.": "Nenalezena žádná videa.",
    "{} result{}. Click one to see the details.": "Výsledků: {}{}. Kliknutím zobrazíte podrobnosti.",
    "{} selected. Add to batch adds all of them (Shift or Cmd/Ctrl-click to choose).":
        "Vybráno: {}. Přidat do dávky přidá všechny (výběr: Shift nebo Cmd/Ctrl-klik).",
    "Double-click to open it.": "Dvojklikem to otevřete.",
    "Loading the description…": "Načítám popis…", "(no description)": "(bez popisu)",
    "Link copied.": "Odkaz zkopírován.", "{} links copied.": "Zkopírováno odkazů: {}.",
    "Checking the list… its videos appear in the Batch download tab.":
        "Kontroluji seznam… jeho videa se objeví v záložce Dávkové stahování.",
    "Added to the Batch download list.": "Přidáno do seznamu Dávkového stahování.",
    "That one is already in the Batch download list.": "Toto už v seznamu Dávkového stahování je.",
    "That list is already in the Batch download list.": "Tento seznam už v Dávkovém stahování je.",
    "Added {} to the Batch download list": "Do seznamu Dávkového stahování přidáno: {}",
    "Added {} to the Batch download list ({} already there)": "Do seznamu Dávkového stahování přidáno: {} (již tam: {})",
    "Added {} to the Batch download list. Playlists are being expanded.":
        "Do seznamu Dávkového stahování přidáno: {}. Playlisty se rozbalují.",
    "Added {} to the Batch download list ({} already there). Playlists are being expanded.":
        "Do seznamu Dávkového stahování přidáno: {} (již tam: {}). Playlisty se rozbalují.",
    "No mpv or VLC found, so it was opened in your web browser.": "Nenalezen mpv ani VLC, proto se otevřelo ve webovém prohlížeči.",
    "Starting the player…": "Spouštím přehrávač…", "Playing.": "Přehrává se.",
    "Playing in VLC (Pause / Stop here only work with mpv).": "Přehrává se ve VLC (Pauza / Stop zde fungují jen s mpv).",
    "Stopped.": "Zastaveno.",
    "Could not reach the player: {}": "Přehrávač není dostupný: {}", "Could not play it: {}": "Nelze přehrát: {}",
    "{} has no search here: paste a link to a channel, playlist or video.":
        "{} zde nemá hledání: vložte odkaz na kanál, playlist nebo video.",
    "{}: 'Find' accepts part of a name; the other choice needs the exact name (or paste a link).":
        "{}: „Najít“ stačí část názvu; druhá možnost vyžaduje přesný název (nebo vložte odkaz).",
    "Paste a link": "Vložte odkaz",
    "Search sites": "Hledací weby", "Name": "Název", "Search address": "Adresa hledání", "Add": "Přidat", "Close": "Zavřít",
    "Add a site to search from the Browse tab. In the address, write {q} where the\nsearch words go, for example:  https://prehraj.to/hledej/{q}\nThe site must be one yt-dlp can read; otherwise the status line shows its message.":
        "Přidejte web, ve kterém půjde hledat v záložce Procházet. Do adresy napište {q} tam, kam\npatří hledaná slova, např.:  https://prehraj.to/hledej/{q}\nWeb musí umět číst yt-dlp; jinak stavový řádek ukáže jeho hlášení.",
    "Give the site a name, and an address that contains {q} where the search words go, for example:\nhttps://prehraj.to/hledej/{q}":
        "Zadejte název webu a adresu, která obsahuje {q} tam, kam patří hledaná slova, např.:\nhttps://prehraj.to/hledej/{q}",
    "'{}' is already in the list. Use a different name.": "„{}“ už v seznamu je. Použijte jiný název.",
    "Added '{}'. Pick it in the 'Search on' list.": "Přidáno „{}“. Vyberte ho v seznamu „Hledat na“.",
    "Find channel": "Najít kanál", "Channel videos": "Videa kanálu", "Channel clips": "Klipy kanálu",
    "Videos": "Videa", "Channels": "Kanály", "Playlists": "Playlisty", "Tracks": "Skladby",
    # ---- misc tool status
    "Install Homebrew first (top row).": "Nejdřív nainstalujte Homebrew (horní řádek).",
    "Install Chocolatey first (top row).": "Nejdřív nainstalujte Chocolatey (horní řádek).",
    "Homebrew is already installed.": "Homebrew je už nainstalován.",
    "Chocolatey is already installed.": "Chocolatey je už nainstalován.",
    "Homebrew is not installed. Press Install first.": "Homebrew není nainstalován. Nejdřív stiskněte Instalovat.",
    "Chocolatey is not installed. Press Install first.": "Chocolatey není nainstalován. Nejdřív stiskněte Instalovat.",
}
)
CZ_SUBS = [("restart the app", "restartuj aplikaci"), ("update available", "dostupná aktualizace"), ("up to date", "aktuální"),
           ("(also works)", "(také funguje)"), (" installed", " nainstalováno")]

CZ.update({
    "High (bigger file)": "Vysoká (větší soubor)", "Medium": "Střední", "Low (smallest file)": "Nízká (nejmenší soubor)",
    "H.264 (most compatible)": "H.264 (nejkompatibilnější)", "H.265 / HEVC (smaller files)": "H.265 / HEVC (menší soubory)",
    "Best available (mp4)": "Nejlepší dostupná (mp4)", "Up to 1080p (mp4)": "Až 1080p (mp4)",
    "Up to 720p (mp4)": "Až 720p (mp4)", "Up to 480p (mp4)": "Až 480p (mp4)", "Audio only (mp3)": "Jen zvuk (mp3)",
    "Ready": "Připraveno",
})


CZ.update({
    # ---- explanatory texts (shown only for ticked options)
    "One video per link. Leave 'Only part' empty to download all of it; examples: 1:30 to 2:45, or just a start / just an end.":
        "Jedno video na odkaz. Nechte „Jen část“ prázdné, chcete-li stáhnout celé; příklady: 1:30 až 2:45, nebo jen začátek / jen konec.",
    "A playlist link is handed over to the Batch download tab (one row per video). A finished video is loaded into the other tabs.":
        "Odkaz na playlist se předá na kartu Dávkové stahování (jeden řádek na video). Hotové video se načte do ostatních karet.",
    "Keep retrying: if the connection drops or the site refuses, the download is tried again by itself until it works.":
        "Opakovat dokola: když spojení vypadne nebo stránka odmítne, stahování se samo zkouší znovu, dokud se nepovede.",
    "Exact cut: the part is re-encoded so it starts and ends exactly at your times (without it, the cut can be a second or two off).":
        "Přesný střih: část se překóduje, takže začíná a končí přesně ve vámi zadaných časech (bez toho se může střih lišit o vteřinu dvě).",
    "Tick the steps you want. Each item goes through them in order and only the final file is kept; finished steps are skipped.":
        "Zaškrtněte kroky, které chcete. Každá položka jimi projde popořadě a zachová se jen výsledný soubor; hotové kroky se přeskočí.",
    "Each item goes through the ticked steps in order, and only the final file is kept; finished steps are skipped.":
        "Každá položka projde zaškrtnutými kroky popořadě a zachová se jen výsledný soubor; hotové kroky se přeskočí.",
    "Download: saves each link in the quality chosen below. A playlist link becomes one row per video.":
        "Stáhnout: uloží každý odkaz v kvalitě zvolené níže. Odkaz na playlist se rozdělí na jeden řádek na video.",
    "Convert: changes the format (and codec) as set on the Convert tab.":
        "Převod: změní formát (a kodek) podle nastavení na kartě Převod.",
    "Compress: makes the file smaller using the quality, resolution and target size from the Compress tab.":
        "Komprese: zmenší soubor podle kvality, rozlišení a cílové velikosti z karty Komprese.",
    "Remove audio: saves the video without sound (picture untouched). Can't be combined with Loudness or Extract audio.":
        "Odebrání zvuku: uloží video bez zvuku (obraz zůstane nedotčený). Nejde kombinovat s Hlasitostí ani s Extrakcí zvuku.",
    "Extract audio: keeps only the sound, in the format from the Extract audio tab.":
        "Extrakce zvuku: ponechá jen zvuk, ve formátu z karty Extrakce zvuku.",
    "Loudness: sets every file to the same volume (level from the Loudness tab). The picture is copied, only the sound is re-encoded.":
        "Hlasitost: nastaví všem souborům stejnou hlasitost (úroveň z karty Hlasitost). Obraz se zkopíruje, překóduje se jen zvuk.",
    "Clean name: tidies the file name (removes tags like (Official Video)). Needs a free name: use a separate 'Processed files go to' folder or tick 'Delete the original'.":
        "Čistý název: uklidí název souboru (odstraní značky jako (Official Video)). Potřebuje volný název: použijte samostatnou složku „Zpracované soubory do“ nebo zaškrtněte „Smazat originál“.",
    "Write tags: puts Artist (the text from 'Add to start of names'), Title and Track number into the files.":
        "Zapsat značky: zapíše do souborů Interpreta (text z „Přidat na začátek názvů“), Název a Číslo stopy.",
    "Greyed-out steps can't be combined with the ticked ones.":
        "Zašedlé kroky nejdou kombinovat se zaškrtnutými.",
    "Add to start of names: 'Band' gives 'Band - Song'.":
        "Přidat na začátek názvů: „Kapela“ dá „Kapela - Písnička“.",
    "Number files: gives '01 - Band - Song' (in list order).":
        "Očíslovat soubory: dá „01 - Kapela - Písnička“ (podle pořadí v seznamu).",
    "Delete the original: the first download is removed once the processed copy is saved.":
        "Smazat originál: původní stažený soubor se smaže, jakmile se uloží zpracovaná kopie.",
    "Skip videos I've already downloaded: they are left out (Forget history… resets that).":
        "Přeskočit už stažená videa: vynechají se (Zapomenout historii… to vynuluje).",
    "Saves the part between Start and End as a new file. Formats: 90  ·  1:30  ·  00:01:30.5":
        "Uloží část mezi Začátkem a Koncem jako nový soubor. Formáty: 90  ·  1:30  ·  00:01:30.5",
    "Frame-accurate: the part is re-encoded so the cut is exactly where you set it (slower). Without it the cut is instant but can be a second or two off.":
        "Přesně na snímek: část se překóduje, takže střih je přesně tam, kde jste ho nastavili (pomalejší). Bez toho je střih okamžitý, ale může být o vteřinu dvě vedle.",
    "Converts the loaded file to another format; the Quality setting trades file size against picture quality.\nH.265 makes much smaller files (plays on Macs/iPhones, not every old player).\nGIF and WebM always use the CPU and ignore the codec setting.":
        "Převede načtený soubor do jiného formátu; Kvalita určuje poměr velikosti souboru a kvality obrazu.\nH.265 dělá mnohem menší soubory (přehraje se na Macu/iPhonu, ne v každém starém přehrávači).\nGIF a WebM vždy používají procesor a kodek ignorují.",
    "Makes the loaded video smaller. Max resolution scales the picture down (never up).\nFill in a target size (e.g. 25 for Discord or email) to override Quality.\nThe result is approximate (about ±10 %).":
        "Zmenší načtené video. Maximální rozlišení obraz zmenší (nikdy nezvětší).\nZadejte cílovou velikost (např. 25 pro Discord nebo e-mail), která přebije Kvalitu.\nVýsledek je přibližný (asi ±10 %).",
    "Saves only the sound of the loaded video.\nmp3 plays everywhere  ·  m4a is smaller at the same quality  ·  wav is lossless but very large.":
        "Uloží jen zvuk z načteného videa.\nmp3 hraje všude  ·  m4a je při stejné kvalitě menší  ·  wav je bezztrátový, ale velmi velký.",
    "Saves the video without its sound track. The picture is copied untouched (no quality loss, very fast).":
        "Uloží video bez zvukové stopy. Obraz se zkopíruje beze změny (bez ztráty kvality, velmi rychle).",
    "GPU / hardware encoder: encodes on the graphics chip, usually several times faster (slightly larger files at the same quality).":
        "GPU / hardwarový kodér: kóduje na grafickém čipu, obvykle několikrát rychleji (při stejné kvalitě o něco větší soubory).",
    "Clean file names: tidies names of downloaded and saved files (underscores, double spaces, stray symbols).":
        "Čisté názvy souborů: uklidí názvy stažených a uložených souborů (podtržítka, dvojité mezery, zbytečné znaky).",
    "Remove tags: cuts bracketed extras like (Official Video) or [Audio] from names.":
        "Odstranit značky: vystřihne ze jmen závorky jako (Official Video) nebo [Audio].",
})

CZ.update({
    "One video per link. Leave 'Only part' empty to download all of it (examples: 1:30 to 2:45, or just a start / just an end). A playlist link goes to the Batch download tab.":
        "Jedno video na odkaz. Nechte „Jen část“ prázdné, chcete-li stáhnout celé (příklady: 1:30 až 2:45, nebo jen začátek / jen konec). Odkaz na playlist se předá na kartu Dávkové stahování.",
    "If the connection drops or the site refuses, the download is tried again by itself.":
        "Když spojení vypadne nebo stránka odmítne, stahování se samo zkusí znovu.",
    "Exact cut": "Přesný střih",
    "Re-encodes the part so it starts and ends exactly at your times (slower).":
        "Část se překóduje, takže začíná a končí přesně ve vámi zadaných časech (pomalejší).",
    "Each item goes through the ticked steps in order, and only the final file is kept; finished steps are skipped.":
        "Každá položka projde zaškrtnutými kroky popořadě a zachová se jen výsledný soubor; hotové kroky se přeskočí.",
    "Tick the steps you want to run.": "Zaškrtněte kroky, které se mají provést.",
    "Saves each link in the quality chosen below. A playlist link becomes one row per video.":
        "Uloží každý odkaz v kvalitě zvolené níže. Odkaz na playlist se rozdělí na jeden řádek na video.",
    "Changes the format and codec, as set on the Convert tab.": "Změní formát a kodek podle nastavení na kartě Převod.",
    "Makes the file smaller (quality, resolution and target size from the Compress tab).":
        "Zmenší soubor (kvalita, rozlišení a cílová velikost z karty Komprese).",
    "Saves the video without sound. Can't be combined with Loudness or Extract audio.":
        "Uloží video bez zvuku. Nejde kombinovat s Hlasitostí ani s Extrakcí zvuku.",
    "Keeps only the sound, in the format from the Extract audio tab.": "Ponechá jen zvuk, ve formátu z karty Extrakce zvuku.",
    "Sets every file to the same volume (level from the Loudness tab); only the sound is re-encoded.":
        "Nastaví všem souborům stejnou hlasitost (úroveň z karty Hlasitost); překóduje se jen zvuk.",
    "Tidies the file name. Needs a free name: use a separate 'Processed files go to' folder or tick 'Delete the original'.":
        "Uklidí název souboru. Potřebuje volný název: použijte samostatnou složku „Zpracované soubory do“ nebo zaškrtněte „Smazat originál“.",
    "Writes Artist (from 'Artist - Title' in the name, or the text from 'Add to start of names'), Title, Album (your text, else the name of the folder) and Track number into the files.":
        "Zapíše do souborů Interpreta (z „Interpret - Název“ v názvu, nebo text z „Přidat na začátek názvů“), Název, Album (váš text, jinak název složky) a Číslo stopy.",
    "'Band' gives 'Band - Song'.": "„Kapela“ dá „Kapela - Písnička“.",
    "Number files": "Očíslovat soubory",
    "Gives '01 - Band - Song' (in list order).": "Dá „01 - Kapela - Písnička“ (podle pořadí v seznamu).",
    "Delete the original": "Smazat originál",
    "Removed once the processed copy is saved.": "Smaže se, jakmile se uloží zpracovaná kopie.",
    "They are left out (Forget history… resets that).": "Vynechají se (Zapomenout historii… to vynuluje).",
    "Frame-accurate": "Přesně na snímek",
    "Re-encodes so the cut is exactly where you set it (slower). Without it the cut is instant but can be a second or two off.":
        "Překóduje, takže střih je přesně tam, kde jste ho nastavili (pomalejší). Bez toho je střih okamžitý, ale může být o vteřinu dvě vedle.",
    "GPU / hardware encoder": "GPU / hardwarový kodér",
    "Encodes on the graphics chip, usually several times faster (slightly larger files).":
        "Kóduje na grafickém čipu, obvykle několikrát rychleji (o něco větší soubory).",
    "Tidies names of downloaded and saved files (underscores, double spaces, stray symbols).":
        "Uklidí názvy stažených a uložených souborů (podtržítka, dvojité mezery, zbytečné znaky).",
    "Remove tags": "Odstranit značky",
    "Cuts bracketed extras like (Official Video) or [Audio] from names.":
        "Vystřihne z názvů závorky jako (Official Video) nebo [Audio].",
})

CZ.update({
    # ---- time estimates, batch summary
    "{}  ·  {}  ·  {} left": "{}  ·  {}  ·  zbývá {}",
    "{}  ·  {} left": "{}  ·  zbývá {}",
    "{} failed": "selhalo: {}", "{} skipped": "přeskočeno: {}", "{} cancelled": "zrušeno: {}",
    "Took {}": "Trvalo {}",
    "Done ({})": "Hotovo ({})", "Failed ({})": "Selhalo ({})",
    "Skipped ({})": "Přeskočeno ({})", "Cancelled ({})": "Zrušeno ({})",
    "Already downloaded earlier: {} (left out)": "Dříve už staženo: {} (vynecháno)",
    "Copy": "Kopírovat",
    "Double-click a failed item in the list to see the full error.":
        "Dvojklikem na selhanou položku v seznamu zobrazíte celou chybu.",
})

CZ.update({
    "Analyzing… {} %": "Analyzuji… {} %", "Downloading {} %": "Stahuji {} %", "Tags {} %": "Značky {} %",
    "Convert {} %": "Převod {} %", "Compress {} %": "Komprese {} %", "Remove audio {} %": "Odebrání zvuku {} %",
    "Extract audio {} %": "Extrakce zvuku {} %", "Loudness {} %": "Hlasitost {} %",
    "Trim {} %": "Střih {} %",
})

CZ.update({
    # ---- trim timeline, cover art
    "▶ Preview": "▶ Náhled",
    "Set start here": "Nastavit začátek sem", "Set end here": "Nastavit konec sem",
    "Install mpv on the Setup tab to use the preview": "Pro náhled nainstalujte mpv na kartě Nastavení",
    "Open a video or audio file to see its timeline": "Otevřete video nebo zvukový soubor, aby se zobrazila časová osa",
    "Enter a valid Start time first.": "Nejdřív zadejte platný čas začátku.",
    "Could not start the player: {}": "Přehrávač se nepodařilo spustit: {}",
    "Start must be before End.": "Začátek musí být před koncem.",
    "End must be after Start.": "Konec musí být po začátku.",
    "Drag the green (start) and red (end) markers on the timeline, or type the times. Preview plays the part in mpv; while it plays, Set start here / Set end here take the current position. Time formats: 90  ·  1:30  ·  00:01:30.5":
        "Přetáhněte zelený (začátek) a červený (konec) znak na časové ose, nebo časy napište. Náhled přehraje vybranou část v mpv; během přehrávání tlačítka Nastavit začátek / konec sem převezmou aktuální pozici. Formáty času: 90  ·  1:30  ·  00:01:30.5",
    "Embed cover art (mp3 / m4a)": "Vložit obal alba (mp3 / m4a)",
    "Embed cover art": "Vložit obal alba",
    "Puts the video's thumbnail into downloaded audio (mp3). Extract audio (mp3 / m4a) uses the file's own picture, or a frame from the video.":
        "Vloží náhled videa do staženého zvuku (mp3). Extrakce zvuku (mp3 / m4a) použije obrázek ze souboru, nebo snímek z videa.",
    "Preparing cover art…": "Připravuji obal alba…",
})

CZ.update({
    "Next ▶": "Další ▶", "Play next automatically": "Automaticky přehrát další",
    "That was the last video in the list.": "To bylo poslední video v seznamu.",
    "That was the last video in the list. Press Load more to continue.":
        "To bylo poslední video v seznamu. Pokračujte tlačítkem Načíst další.",
    "Playing next: {}": "Přehrávám další: {}",
})

CZ.update({
    "Releases": "Vydání",
    "Files": "Soubory", "Recent ▾": "Nedávné ▾", "(nothing yet)": "(zatím nic)", "Clear this list": "Vymazat seznam",
    "◀ Up": "◀ Nahoru", "Refresh": "Obnovit", "Go to:": "Přejít na:", "Only video and audio": "Jen video a audio",
    "Size": "Velikost", "Modified": "Změněno", "Use in:": "Použít v:", "Use in: ": "Použít v: ",
    "Rename…": "Přejmenovat…",
    "Search:": "Hledat:", "Created by Tomas Hajek": "Vytvořil Tomas Hajek", "Version 1.0": "Verze 1.0", "Bars": "Sloupce", "Needle": "Ručička",
    "Album (tag)": "Album (značka)",
    "Empty: the name of the folder · Artist and title: from the name (Artist - Title) or the text above":
        "Prázdné: název složky · Interpret a název: z názvu souboru (Interpret - Název) nebo z textu výše",
    "Select a file to see its cover and tags": "Vyberte soubor, uvidíte jeho obal a značky",
    "Artist": "Interpret", "Album": "Album",
    "Find duplicates…": "Najít duplikáty…", "Duplicate files": "Duplicitní soubory",
    "Folder:": "Složka:", "Include subfolders": "Včetně podsložek", "Scan again": "Hledat znovu",
    "File": "Soubor", "Action": "Akce", "In folder": "Ve složce", "files": "souborů",
    "same content": "stejný obsah", "same song, different file": "stejná skladba, jiný soubor",
    "✗ remove": "✗ smazat", "✓ keep": "✓ ponechat",
    "Click a file to switch between keep and remove. Removed files go to the Trash.":
        "Kliknutím na soubor přepnete mezi ponechat a smazat. Smazané soubory jdou do koše.",
    "Move marked to Trash": "Označené do koše", "Select automatically": "Vybrat automaticky",
    "Move these files to the Trash?": "Přesunout tyto soubory do koše?",
    "No duplicates found.": "Žádné duplikáty nenalezeny.",
    "Keep at least one file of each group.": "Z každé skupiny ponechte alespoň jeden soubor.",
    "Searching…": "Hledám…",
    "{} group(s) of duplicates. {} file(s) marked for the Trash ({}).":
        "Skupin duplikátů: {}. Souborů označených do koše: {} ({}).",
    "Moved {} duplicate file(s) to the Trash.": "Duplicitních souborů přesunuto do koše: {}.",
    "Measure and make preview": "Změřit a vytvořit ukázku",
    "  (15 s sample; empty = from the middle)": "  (15s ukázka; prázdné = od poloviny)",
    "▶ Original": "▶ Originál", "▶ Adjusted": "▶ Upravené",
    "Measuring the loudness…": "Měřím hlasitost…",
    "Open a video or audio file first.": "Nejprve otevřete video nebo audio soubor.",
    "This file has no audio track to adjust.": "Soubor nemá zvukovou stopu k úpravě.",
    "The audio is silent, so there is no loudness to match.": "Zvuk je tichý, není co sjednocovat.",
    "This file: {} LUFS (peak {} dBTP). Target {} LUFS: {} dB. Listen to {} from {}, as it is and adjusted.":
        "Tento soubor: {} LUFS (špička {} dBTP). Cíl {} LUFS: {} dB. Poslechněte si {} od {}, původní i upravený.",
    "No player found: install mpv from the Setup tab to listen to the preview.":
        "Přehrávač nenalezen: pro poslech nainstalujte mpv v záložce Nastavení.",
    "Preview": "Náhled", "from": "od", "Make preview": "Vytvořit náhled",
    "  (10 s sample; empty = from the middle)": "  (10s ukázka; prázdné = od poloviny)",
    "Making the preview…": "Vytvářím náhled…",
    "Open a video file first.": "Nejprve otevřete video.",
    "Preview failed: {}": "Náhled se nepovedl: {}",
    "Preview of {} from {}: {}. The whole video would be about {} (original {}, {} % smaller).":
        "Náhled {} od {}: {}. Celé video by mělo asi {} (originál {}, o {} % menší).",
    "Preview of {} from {}: {}. The whole video would be about {} (original {}, {} % larger).":
        "Náhled {} od {}: {}. Celé video by mělo asi {} (originál {}, o {} % větší).",
    "Preview of {} from {}: {}.": "Náhled {} od {}: {}.",
    "No player found: install mpv from the Setup tab to watch the preview.":
        "Přehrávač nenalezen: pro náhled nainstalujte mpv v záložce Nastavení.",
    "Loading more videos…": "Načítám další videa…",
    "There are no video or audio files in the selection.": "Ve výběru nejsou žádné video ani audio soubory.",
    "◀ Prev": "◀ Předch.",
    "Folders: {} · Files: {}": "Složky: {} · Soubory: {}",
    "Folders: {} · Files: {} · Selected: {}": "Složky: {} · Soubory: {} · Vybráno: {}",
    "That was the first file in the folder.": "To byl první soubor ve složce.",
    "That was the first video in the list.": "To bylo první video v seznamu.",
    "Playing previous: ": "Přehrává se předchozí: ",
    "That was the last file in the folder.": "To byl poslední soubor ve složce.",
    "Playing in VLC (Pause, Stop and the time line only work with mpv).":
        "Přehrává se ve VLC (Pauza, Stop a časová osa fungují jen s mpv).",
    "Copy": "Kopírovat", "Cut": "Vyjmout", "Paste": "Vložit", "New folder…": "Nová složka…",
    "New folder": "Nová složka", "Name of the new folder:": "Název nové složky:",
    "Copy → other side": "Kopírovat → vedle", "Move → other side": "Přesunout → vedle",
    "Release to copy into:": "Pusť pro zkopírování do:", "hold Shift to move": "s klávesou Shift přesun",
    "Drag the file onto a tab (Trim, Convert, …) or the other folder.":
        "Přetáhni soubor na kartu (Střih, Převod, …) nebo do druhé složky.",
    "Drop the file onto a tab (Trim, Convert, …) or into the other folder.":
        "Pusť soubor na kartu (Střih, Převod, …) nebo do druhé složky.",
    "Wait for the current copy to finish.": "Počkej, až skončí probíhající kopírování.",
    "Release on a tab to use the file there:": "Pusť na kartu, kde chceš soubor použít:",
    "Drag the file onto a tab (Trim, Convert, …).": "Přetáhni soubor na kartu (Střih, Převod, …).",
    "Only video and audio files can be dragged onto a tab.": "Na kartu jde přetáhnout jen video a audio soubory.",
    "Drop the file onto a tab (Trim, Convert, …) to use it there.": "Pusť soubor na kartu (Střih, Převod, …), kde ho chceš použít.",
    "The visualizer needs mpv; VLC plays the file normally.": "Vizualizace vyžaduje mpv; VLC přehraje soubor normálně.", "Move to Trash": "Do koše", "Show in Finder": "Zobrazit ve Finderu",
    "Show in Explorer": "Zobrazit v Průzkumníku", "Show in folder": "Zobrazit ve složce",
    "Rename": "Přejmenovat", "New name:": "Nový název:", "Save folder (Quick download)": "Složka pro stahování",
    "Home": "Domů", "Downloads": "Stažené", "Desktop": "Plocha", "Movies": "Filmy", "Music": "Hudba",
    "That folder does not exist.": "Tato složka neexistuje.",
    "Dropping files onto the window needs one extra package: install tkinterdnd2 on the Setup tab, then restart.":
        "Přetahování souborů do okna vyžaduje jeden balíček navíc: nainstaluj tkinterdnd2 na kartě Nastavení a restartuj aplikaci.",
    "tkinterdnd2  (drag & drop of files)": "tkinterdnd2  (přetahování souborů)",
    "That name has characters a file name cannot have.": "Název obsahuje znaky, které soubor mít nemůže.",
    "A file with that name already exists.": "Soubor s tímto názvem už existuje.", "Shorts": "Shorts",
    "This channel has no Videos tab, so its albums and singles are shown instead.":
        "Tento kanál nemá kartu Videa, proto se zobrazují jeho alba a singly.",
    "This channel has no Videos tab, so its playlists are shown instead.":
        "Tento kanál nemá kartu Videa, proto se zobrazují jeho playlisty.",
    "This channel has no Videos tab, so its tabs are shown instead.":
        "Tento kanál nemá kartu Videa, proto se zobrazují jeho karty.",
})

CZ.update({
    "Visualizer": "Vizualizace", "Fractal": "Fraktál", "Kaleidoscope": "Kaleidoskop",
    "Waves": "Vlny", "Spectrum": "Spektrum", "Golden spiral": "Zlatá spirála", "Mix": "Mix",
    "My YouTube – signed in with:": "Můj YouTube – přihlášen přes:", "Show:": "Zobrazit:",
    "Recommended": "Doporučené", "Subscriptions (new videos)": "Odběry (nová videa)",
    "Subscribed channels": "Odebírané kanály", "My playlists": "Moje playlisty",
    "Watch later": "Podívat se později", "Liked videos": "Označená „To se mi líbí“", "History": "Historie",
    "Open": "Otevřít", "Open in browser": "Otevřít v prohlížeči", "Opened in your web browser.": "Otevřeno v prohlížeči.",
    "Opened in your web browser: use Save there to add it to Watch later or a playlist.":
        "Otevřeno v prohlížeči: tlačítkem Uložit tam přidáš video do Podívat se později nebo do playlistu.", "Ready: press Start": "Připraveno: stiskni Start",
    "Added to the Batch download list.":
        "Přidáno do seznamu hromadného stahování. Vyber kvalitu a složku a stiskni Start.",
    "macOS blocks reading that browser's cookies. Give Terminal (or the app running this) Full Disk Access in System Settings → Privacy & Security, restart it, or choose Firefox / Chrome instead of Safari.":
        "macOS brání čtení cookies z toho prohlížeče. Dej Terminálu (nebo aplikaci, ze které to běží) Úplný přístup k disku v Nastavení systému → Soukromí a zabezpečení, restartuj ji, nebo místo Safari zvol Firefox / Chrome.", "None": "Žádný",
    "Choose the browser you are signed in to YouTube with (the login is read from it; close nothing, type no password).":
        "Vyber prohlížeč, ve kterém jsi přihlášen k YouTube (přihlášení se přečte z něj, žádné heslo se nezadává).",
})

def _i18n_build():
    """Build the lookup tables for translation: Czech -> English, and the '{}' patterns."""
    pats, rev = [], {}
    for en, cz in CZ.items():
        rev.setdefault(cz, en)
        if "{}" in en:
            pats.append((re.compile("^" + re.escape(en).replace(r"\{\}", "(.+?)") + "$", re.S), cz))
    pats.sort(key=lambda p: -len(p[0].pattern))  # the most specific pattern first
    _I18N["pats"], _I18N["rev"] = pats, rev


def tr(s):
    """The Czech text for an English one (unchanged when Czech is off or there is no translation)."""
    if not LANG["cz"] or not isinstance(s, str) or not s.strip():
        return s
    if _I18N["pats"] is None:
        _i18n_build()
    if s in CZ:
        return CZ[s]
    for rx, cz in _I18N["pats"]:
        m = rx.match(s)
        if m:
            parts = cz.split("{}")
            out = parts[0]
            for i, g in enumerate(m.groups()):
                out += tr(g) + (parts[i + 1] if i + 1 < len(parts) else "")
            return out
    if s.startswith("✓ ") and " → " in s:  # "✓ Download → Loudness"
        return "✓ " + " → ".join(tr(x) for x in s[2:].split(" → "))
    out = s
    for old, new in CZ_SUBS:
        out = out.replace(old, new)
    return out


def untr(s):
    """The English text for a Czech one (for things the code compares or stores)."""
    if _I18N["rev"] is None:
        _i18n_build()
    return _I18N["rev"].get(s, s) if isinstance(s, str) else s


class XD(dict):
    """A dict whose keys are shown to the user: a Czech label finds the same entry as its English one."""

    def __missing__(self, key):
        """Look a key up by its Czech label as well: the Czech text finds the English entry."""
        en = untr(key)
        if en != key and dict.__contains__(self, en):
            return dict.__getitem__(self, en)
        raise KeyError(key)


QUALITY = XD({"High (bigger file)": 20, "Medium": 26, "Low (smallest file)": 32})
RESOLUTIONS = XD({"Keep original": None, "1080p": 1080, "720p": 720, "480p": 480})
CODECS = XD({"H.264 (most compatible)": "h264", "H.265 / HEVC (smaller files)": "h265"})
AUDIO_FORMATS = {"mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
                 "m4a": ["-c:a", "aac", "-b:a", "192k"],
                 "wav": ["-c:a", "pcm_s16le"]}
VIDEO_FORMATS = ["mp4", "mkv", "mov", "webm", "gif"]

# Hardware encoders by kind
GPU_KINDS = {
    "videotoolbox": {"label": "Apple VideoToolbox", "h264": "h264_videotoolbox",
                     "h265": "hevc_videotoolbox", "hwaccel": ["-hwaccel", "videotoolbox"]},
    "nvenc": {"label": "NVIDIA NVENC", "h264": "h264_nvenc",
              "h265": "hevc_nvenc", "hwaccel": ["-hwaccel", "auto"]},
    "qsv": {"label": "Intel Quick Sync", "h264": "h264_qsv",
            "h265": "hevc_qsv", "hwaccel": ["-hwaccel", "auto"]},
    "amf": {"label": "AMD AMF", "h264": "h264_amf",
            "h265": "hevc_amf", "hwaccel": ["-hwaccel", "auto"]},
}


def _test_encoder(ffmpeg, encoder):
    """Try a tiny real encode: an encoder can be listed yet unusable without the hardware."""
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "color=c=black:s=256x256:r=25:d=0.5", "-frames:v", "5",
             "-c:v", encoder, "-f", "null", "-"],
            capture_output=True, timeout=20, **TEXT)
        return r.returncode == 0
    except Exception:
        return False


def detect_gpu():
    """Return the key of the first usable hardware encoder in GPU_KINDS, or None."""
    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        return None
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-encoders"],
                             capture_output=True, **TEXT).stdout
    except Exception:
        return None
    candidates = ["videotoolbox"] if IS_MAC else (["nvenc", "qsv", "amf"] if IS_WIN else [])
    for kind in candidates:
        enc = GPU_KINDS[kind]["h264"]
        if enc not in out:
            continue
        if kind == "videotoolbox" or _test_encoder(ffmpeg, enc):
            return kind
    return None


def _gpu_rate_args(kind, crf, codec, kbps):
    """Quality / bitrate arguments for a hardware encoder."""
    cq = crf + (5 if codec == "h265" else 0)  # HEVC needs a higher number for similar quality
    if kind == "videotoolbox":
        if kbps:
            return ["-b:v", f"{kbps}k"]
        return ["-q:v", str(max(1, min(100, round(100 - crf * 1.7))))]
    if kind == "nvenc":
        if kbps:
            return ["-preset", "p5", "-rc", "vbr", "-b:v", f"{kbps}k",
                    "-maxrate", f"{int(kbps * 1.5)}k", "-bufsize", f"{kbps * 2}k"]
        return ["-preset", "p5", "-rc", "vbr", "-cq", str(cq), "-b:v", "0"]
    if kind == "qsv":
        if kbps:
            return ["-b:v", f"{kbps}k"]
        return ["-global_quality", str(cq)]
    if kind == "amf":
        if kbps:
            return ["-quality", "quality", "-rc", "vbr_peak", "-b:v", f"{kbps}k",
                    "-maxrate", f"{int(kbps * 1.5)}k"]
        qp = ["-qp_i", str(cq), "-qp_p", str(cq)]
        if codec == "h264":
            qp += ["-qp_b", str(cq)]
        return ["-quality", "quality", "-rc", "cqp"] + qp
    return []


def v_encode(opt, crf, preset="medium", codec="h264", mp4=True, kbps=None):
    """Video encoder args.
    opt["gpu"] is None (CPU: libx264/libx265) or a key of GPU_KINDS (hardware encoder).
    kbps: target video bitrate (used for 'target file size')."""
    kind = opt.get("gpu")
    if kind:
        args = ["-c:v", GPU_KINDS[kind][codec]] + _gpu_rate_args(kind, crf, codec, kbps)
    else:
        args = ["-c:v", "libx265" if codec == "h265" else "libx264"]
        if kbps:
            args += ["-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.5)}k",
                     "-bufsize", f"{kbps * 2}k"]
        else:
            args += ["-crf", str(crf + (5 if codec == "h265" else 0))]
        args += ["-preset", preset]
        if codec == "h265":
            args += ["-x265-params", "log-level=error"]
    args += ["-pix_fmt", "nv12" if kind == "qsv" else "yuv420p"]
    if codec == "h265" and mp4:
        args += ["-tag:v", "hvc1"]  # lets QuickTime / Apple devices play it
    return args


def target_video_kbps(target_mb, duration, audio_kbps=128):
    """Video bitrate (kbps) needed to land near target_mb. None if impossible."""
    if not duration or target_mb <= 0:
        return None
    total_kbit = target_mb * 1024 * 1024 * 8 / 1000
    kbps = int(total_kbit / duration * 0.95 - audio_kbps)  # 5% container overhead
    return kbps if kbps >= 100 else None


# ---- Setup tab: install / verify / update tools
PKG = {"ffmpeg": "ffmpeg", "ytdlp": "yt-dlp", "mpv": "mpv", "deno": "deno", "dnd": "tkinterdnd2"}
_DND = {"active": False}  # True once tkinterdnd2 was loaded when the app started
PIP_DND_SCRIPT = (
    "import subprocess, sys\n"
    "base = [sys.executable, '-m', 'pip', 'install', '--upgrade', 'tkinterdnd2']\n"
    "for extra in (['--user'], ['--user', '--break-system-packages'], [], ['--break-system-packages']):\n"
    "    print('$ pip install ' + ' '.join(extra) + ' tkinterdnd2', flush=True)\n"
    "    if subprocess.call(base + extra) == 0:\n"
    "        sys.exit(0)\n"
    "sys.exit(1)\n")
BREW_INSTALL = ('/bin/bash -c "$(curl -fsSL '
                'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
CHOCO_INSTALL_PS = "; ".join([
    "Set-ExecutionPolicy Bypass -Scope Process -Force",
    "[System.Net.ServicePointManager]::SecurityProtocol = "
    "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072",
    "iex ((New-Object System.Net.WebClient).DownloadString("
    "'https://community.chocolatey.org/install.ps1'))",
    "Write-Host ''",
    "Write-Host 'Finished. Close this window, then press Verify in FAUN.'",
])


def _choco_ps(choco, args):
    """PowerShell command that runs a Chocolatey action and tells the user to press Verify when done."""
    path = choco.replace("'", "''")
    return (f"& '{path}' {args}; Write-Host ''; "
            "Write-Host 'Finished. Close this window, then press Verify in FAUN.'")


def tool_command(key, action):
    """What to run for a Setup button. key: pm / ffmpeg / ytdlp; action: install / update.
    Returns (kind, payload):
      ("stream", argv)      run inside the app and show the output
      ("terminal", shell)   open macOS Terminal (installers that need a password)
      ("elevated", ps)      run in an administrator PowerShell window (Windows)
      (None, message)       nothing to run; show the message"""
    if key == "dnd":  # a Python package: installed with this Python's own pip
        if getattr(sys, "frozen", False):
            return (None, "This packaged app cannot install packages. Rebuild it with PyInstaller using "
                          "--collect-all tkinterdnd2, or run the .py file instead.")
        return ("stream", [sys.executable, "-c", PIP_DND_SCRIPT])
    if IS_MAC:
        brew = find_tool("brew")
        if key == "pm":
            if action == "install":
                if brew:
                    return (None, "Homebrew is already installed.")
                return ("terminal", BREW_INSTALL)
            if not brew:
                return (None, "Homebrew is not installed. Press Install first.")
            return ("stream", [brew, "update"])
        if not brew:
            return (None, "Install Homebrew first (top row).")
        return ("stream", [brew, "install" if action == "install" else "upgrade", PKG[key]])
    if IS_WIN:
        choco = find_tool("choco")
        if key == "pm":
            if action == "install":
                if choco:
                    return (None, "Chocolatey is already installed.")
                return ("elevated", CHOCO_INSTALL_PS)
            if not choco:
                return (None, "Chocolatey is not installed. Press Install first.")
            return ("elevated", _choco_ps(choco, "upgrade chocolatey -y"))
        if not choco:
            if key == "ytdlp" and action == "update" and find_tool("yt-dlp"):
                return ("stream", [find_tool("yt-dlp"), "-U"])
            return (None, "Install Chocolatey first (top row).")
        verb = "install" if action == "install" else "upgrade"
        return ("elevated", _choco_ps(choco, f"{verb} {PKG[key]} -y"))
    return (None, "The Setup tab supports macOS and Windows only.")


def open_in_terminal_mac(shell_cmd):
    """Run a shell command in a new macOS Terminal window (for installers that need a password)."""
    esc = shell_cmd.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.Popen(["osascript",
                      "-e", f'tell application "Terminal" to do script "{esc}"',
                      "-e", 'tell application "Terminal" to activate'])


def run_elevated_ps(script):
    """Run a PowerShell script in a new administrator window (Windows asks for approval)."""
    b64 = base64.b64encode(script.encode("utf-16-le")).decode()
    ps = ("Start-Process powershell -Verb RunAs -ArgumentList "
          f"'-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-EncodedCommand','{b64}'")
    subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], creationflags=NO_WINDOW)


def _first_line(cmd, timeout=30):
    """Run a command and return the first line of its output, or None if it fails."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, env=tool_env(), **TEXT)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    lines = (r.stdout or r.stderr or "").strip().splitlines()
    return lines[0].strip() if lines else ""


def probe_tools(full=False):
    """Installed state of the package manager, ffmpeg and yt-dlp.
    full=True also asks the package manager which of them have updates (needs network)."""
    pm = find_tool("choco" if IS_WIN else "brew")
    info = {"pm": {"path": pm, "version": None, "outdated": None},
            "ffmpeg": {"path": find_tool("ffmpeg"), "version": None, "outdated": None},
            "ytdlp": {"path": find_tool("yt-dlp"), "version": None, "outdated": None},
            "mpv": {"path": find_tool("mpv"), "version": None, "outdated": None},
            # yt-dlp needs a JavaScript runtime for YouTube; deno is the usual one (node / bun also work)
            "deno": {"path": find_tool("deno") or find_tool("node") or find_tool("bun"),
                     "version": None, "outdated": None}}
    if pm:
        v = _first_line([pm, "--version"])
        if v:
            info["pm"]["version"] = ("v" + v) if IS_WIN else v
    if info["ffmpeg"]["path"]:
        m = re.search(r"version\s+(\S+)", _first_line([info["ffmpeg"]["path"], "-version"]) or "")
        info["ffmpeg"]["version"] = m.group(1) if m else None
    if info["ytdlp"]["path"]:
        info["ytdlp"]["version"] = _first_line([info["ytdlp"]["path"], "--version"]) or None
    if info["mpv"]["path"]:
        ver = None
        if IS_MAC:
            # mpv is a Cocoa program: even "mpv --version" makes macOS flash a Dock icon. A Homebrew
            # install has its version in the path (…/Cellar/mpv/0.40.0_1/bin/mpv), so read it from there.
            m = re.search(r"/mpv/(\d+(?:\.\d+)+)", os.path.realpath(info["mpv"]["path"]))
            ver = m.group(1) if m else None
            if not ver and full:  # not a Homebrew path: only the explicit "Verify all" runs it
                m = re.search(r"mpv\s+v?(\S+)", _first_line([info["mpv"]["path"], "--version"]) or "")
                ver = m.group(1) if m else None
            info["mpv"]["version"] = ver or ("installed" if not full else None)
        else:
            m = re.search(r"mpv\s+v?(\S+)", _first_line([info["mpv"]["path"], "--version"]) or "")
            info["mpv"]["version"] = m.group(1) if m else None
    try:  # the drag & drop package (a Python package, not a program)
        import importlib
        import importlib.util
        import site
        try:  # a package installed while the app runs: its folder may be new to this Python
            usp = site.getusersitepackages()
            if os.path.isdir(usp) and usp not in sys.path:
                sys.path.append(usp)
        except Exception:
            pass
        importlib.invalidate_caches()
        spec = importlib.util.find_spec("tkinterdnd2")
        info["dnd"] = {"path": spec.origin if spec else None, "version": None, "outdated": None}
        if spec:
            from importlib import metadata
            try:
                info["dnd"]["version"] = metadata.version("tkinterdnd2")
            except Exception:
                pass
            if not _DND["active"]:
                info["dnd"]["version"] = ((info["dnd"]["version"] or "installed") + "  ·  restart the app")
    except Exception:
        info["dnd"] = {"path": None, "version": None, "outdated": None}
    if info["deno"]["path"]:
        name = os.path.splitext(os.path.basename(info["deno"]["path"]))[0].lower()
        line = _first_line([info["deno"]["path"], "--version"]) or ""
        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", line)
        ver = m.group(1) if m else None
        info["deno"]["version"] = ver if name == "deno" else f"{name} {ver or ''}".strip() + " (also works)"

    if full and pm:
        names, ok = set(), True
        try:
            if IS_WIN:
                r = subprocess.run([pm, "outdated", "-r"], capture_output=True, timeout=180,
                                   env=tool_env(), **TEXT)
                for ln in (r.stdout or "").splitlines():
                    if "|" in ln:
                        names.add(ln.split("|")[0].strip().lower())
            else:
                subprocess.run([pm, "update", "--quiet"], capture_output=True, timeout=300,
                               env=tool_env(), **TEXT)
                r = subprocess.run([pm, "outdated", "--quiet"], capture_output=True,
                                   timeout=120, env=tool_env(), **TEXT)
                for ln in (r.stdout or "").splitlines():
                    if ln.strip():
                        names.add(ln.split()[0].split("/")[-1].lower())
        except Exception:
            ok = False
        if ok:
            for k, n in (("ffmpeg", "ffmpeg"), ("ytdlp", "yt-dlp"), ("mpv", "mpv"), ("deno", "deno")):
                if info[k]["path"]:
                    info[k]["outdated"] = n in names
            if IS_WIN:
                info["pm"]["outdated"] = "chocolatey" in names
    return info


def format_status(entry, full=False):
    """Human text for the status of a tool: version, 'not installed', 'update available'."""
    if not entry["path"]:
        return "✗ not installed"
    s = "✓ " + (entry["version"] or "installed")
    if entry.get("outdated") is True:
        s += "  ·  update available"
    elif entry.get("outdated") is False and full:
        s += "  ·  up to date"
    return s


# ---- loudness matching (EBU R128 "loudnorm", two passes)
NORM_TARGETS = {  # label -> (integrated loudness in LUFS, loudness range)
    "-14 LUFS  (YouTube, Spotify)": (-14.0, 11),
    "-16 LUFS  (phones, podcasts)": (-16.0, 11),
    "-18 LUFS  (movies, gentler)": (-18.0, 18),
    "-23 LUFS  (EBU broadcast)": (-23.0, 15),
}
NORM_TP = -1.5  # true-peak ceiling in dBTP
NORM_MIN, NORM_MAX = -30.0, -10.0  # slider range (LUFS)
NORM_CUSTOM_LRA = 11


def norm_label(value):
    """Preset name matching this LUFS value, or 'Custom'."""
    for label, (target, _lra) in NORM_TARGETS.items():
        if abs(target - value) < 1e-6:
            return label
    return "Custom"


def norm_params(value):
    """(target LUFS snapped to 0.5, loudness range) for a slider value."""
    v = max(NORM_MIN, min(NORM_MAX, round(float(value) * 2) / 2))
    for target, lra in NORM_TARGETS.values():
        if abs(target - v) < 1e-6:
            return v, lra
    return v, NORM_CUSTOM_LRA


def build_norm_analysis(src, target, lra):
    """Pass 1: measure the first audio track (nothing is written)."""
    return ["-y", "-hide_banner", "-i", src, "-map", "0:a:0", "-vn", "-sn", "-dn",
            "-af", f"loudnorm=I={target:g}:TP={NORM_TP:g}:LRA={lra}:print_format=json",
            "-progress", "pipe:1", "-nostats", "-f", "null", "-"]


def norm_filter(target, lra, m):
    """The loudnorm filter of pass 2 (with the values measured in pass 1)."""
    return (f"loudnorm=I={target:g}:TP={NORM_TP:g}:LRA={lra}"
            f":measured_I={m['input_i']:.2f}:measured_TP={m['input_tp']:.2f}"
            f":measured_LRA={m['input_lra']:.2f}:measured_thresh={m['input_thresh']:.2f}"
            f":offset={m['target_offset']:.2f}:linear=true")


def build_norm_apply(src, dst, target, lra, m):
    """Pass 2: apply the measured values. Video is copied; only the sound is re-encoded."""
    ext = os.path.splitext(dst)[1].lower()
    audio_only = {".mp3": ["-c:a", "libmp3lame", "-q:a", "2"], ".wav": ["-c:a", "pcm_s16le"],
                  ".flac": ["-c:a", "flac"], ".m4a": ["-c:a", "aac", "-b:a", "192k"],
                  ".aac": ["-c:a", "aac", "-b:a", "192k"],
                  ".ogg": ["-c:a", "libopus", "-b:a", "160k"],
                  ".opus": ["-c:a", "libopus", "-b:a", "160k"],
                  ".aiff": ["-c:a", "pcm_s16be"], ".aif": ["-c:a", "pcm_s16be"]}
    if ext in audio_only:
        ac = audio_only[ext]
    elif ext == ".webm":
        ac = ["-c:a", "libopus", "-b:a", "160k"]
    elif ext == ".avi":
        ac = ["-c:a", "libmp3lame", "-b:a", "192k"]
    else:
        ac = ["-c:a", "aac", "-b:a", "192k"]
    flt = norm_filter(target, lra, m)
    args = ["-y", "-hide_banner", "-i", src, "-map", "0:v?", "-map", "0:a:0", "-sn",
            "-c:v", "copy", "-af", flt] + ac
    args += ["-ar", "48000"]  # loudnorm otherwise outputs 192 kHz audio
    if ext in (".mp4", ".mov", ".m4v"):
        args += ["-movflags", "+faststart"]
    return args + ["-progress", "pipe:1", "-nostats", dst]


def parse_loudnorm(text):
    """Read the JSON block loudnorm prints at the end of pass 1. None if not found."""
    found = None
    for found in re.finditer(r'\{[^{}]*"input_i"[^{}]*\}', text, re.S):
        pass  # keep the last match
    if not found:
        return None
    try:
        raw = json.loads(found.group(0))
        return {k: float(raw[k]) for k in
                ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    except (ValueError, KeyError):
        return None


# ---- batch helpers
BATCH_STEPS = ["Download", "Convert", "Compress", "Remove audio", "Extract audio", "Loudness", "Clean name",
               "Write tags"]  # run in this order


# steps that can't be combined (the later one would have nothing to work on); the UI greys them out
STEP_CONFLICTS = {
    "Remove audio": {"Loudness", "Extract audio"},
    "Loudness": {"Remove audio"},
    "Extract audio": {"Compress", "Remove audio"},
    "Compress": {"Extract audio"},
}


def batch_steps_problem(steps):
    """Safety net only (the checkboxes can't be combined that way): a message if steps clash."""
    s = set(steps)
    for a in steps:
        clash = STEP_CONFLICTS.get(a, set()) & s
        if clash:
            return f"{a} can't be combined with {', '.join(sorted(clash))}."
    return None


def pending_steps(item, steps):
    """The ticked steps still to run for this batch item, in order."""
    out = []
    for s in steps:
        if s in item["done"]:
            continue
        if s == "Download" and item["kind"] == "file":
            continue  # nothing to download for a local file
        out.append(s)
    return out
URL_RE = re.compile(r"https?://[^\s<>\"']+")


def extract_urls(text):
    """All distinct http(s) links in a block of text, in order."""
    seen, out = set(), []
    for u in URL_RE.findall(text or ""):
        u = u.rstrip(".,;")
        if u.endswith(")") and u.count("(") < u.count(")"):
            u = u[:-1]
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def is_youtube_channel(url):
    """True for a YouTube channel link (@name, /channel/ID, /c/name, /user/name; Videos / Releases / Playlists tab)."""
    try:
        path = urlparse(url).path.lower()
    except ValueError:
        return False
    return bool(re.match(r"^/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)(/(videos|releases|playlists))?/?$", path))


def needs_probe(url):
    """True if this link may be a playlist / album (worth asking yt-dlp). A video link that
    merely carries a playlist id (watch?v=...&list=...) counts as one video, as on the Download tab."""
    try:
        p = urlparse(url)
    except ValueError:
        return False
    host, path, q = p.netloc.lower(), p.path.lower(), parse_qs(p.query)
    if "youtu.be" in host:
        return False
    if "youtube.com" in host:
        if is_youtube_channel(url):
            return True
        return path.startswith("/playlist") and "list" in q
    return any(tok in path for tok in ("/playlist", "/sets/", "/album", "/series", "/season"))


def probe_playlist(ytdlp, url, timeout=120):
    """[(video_url, title), ...] if the link is a playlist or a channel, else None (also None on any problem).
    A channel is read from its Videos tab; a channel without videos (e.g. an artist's 'Topic' channel
    that only has albums) from its Releases / Playlists tab, album by album."""
    if is_youtube_channel(url):
        # the same reading as the Browse tab uses (it copes with tabs inside tabs and with Topic channels)
        base = re.sub(r"/(videos|releases|playlists)/?$", "", url.split("?")[0].rstrip("/"), flags=re.I)
        for tab in ("videos", "releases", "playlists", ""):
            rows, _err = _browse_ytdlp(ytdlp, base + ("/" + tab if tab else ""), 1, 5000, max(timeout, 180))
            vids = [(r["url"], r["title"]) for r in rows if not r["is_list"]]
            if vids:
                return vids
            out, seen = [], set()
            for r in [r for r in rows if r["is_list"] and not r["is_channel"]][:60]:  # albums / playlists
                sub, _e = _browse_ytdlp(ytdlp, r["url"], 1, 5000, timeout)
                for r2 in sub:
                    if not r2["is_list"] and r2["url"] not in seen:
                        seen.add(r2["url"])
                        out.append((r2["url"], r2["title"]))
            if out:
                return out
        return None
    return _probe_flat(ytdlp, url, timeout)


def _is_list_url(u):
    """True for a link that opens a playlist / album, not one video."""
    return "/playlist?" in u or ("list=" in u and "watch?v=" not in u)


def _probe_flat(ytdlp, url, timeout=120, keep_lists=False):
    """The entries of one yt-dlp listing as [(url, title)] (None if there are none)."""
    try:
        r = subprocess.run([ytdlp] + cookie_args() + ["--flat-playlist", "--dump-single-json", "--no-warnings",
                            "--ignore-errors", url],
                           capture_output=True, timeout=timeout, env=tool_env(), **TEXT)
        data = json.loads(r.stdout)
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("_type") != "playlist":
        return None
    out = []
    for e in data.get("entries") or []:
        if not isinstance(e, dict) or (e.get("_type") == "playlist" and not keep_lists):
            continue
        u = e.get("url") or e.get("webpage_url")
        if not u or not str(u).startswith("http"):  # some entries only carry a video id
            vid = e.get("id") or u
            is_yt = str(e.get("ie_key") or "").lower().startswith("youtube")
            u = f"https://www.youtube.com/watch?v={vid}" if is_yt and vid else None
        if u:
            out.append((u, e.get("title") or u))
    return out or None


# ---- clean final names
WORK_SUFFIX_RE = re.compile(r"^(?P<base>.*?)(?:_(?:norm|conv|small|audio|mute|trim))+(?: \(\d+\))?$")
NOISE_TAGS = {"text", "audio", "official audio", "official video", "official music video", "music video",
              "lyrics", "lyric video", "official lyric video", "official lyrics", "visualizer",
              "official visualizer", "video", "hd", "hq", "4k", "hd video", "hq audio", "audio only",
              "soundtrack", "original soundtrack", "original game soundtrack", "official soundtrack", "ost"}
_BRACKETS = re.compile(r"\s*[\(\[]([^\)\]]*)[\)\]]")


def strip_work_suffixes(stem):
    """'Song_conv_norm (2)' -> 'Song'. Only removes the suffixes this app adds."""
    stem = re.sub(r"\s*\[clip\]$", "", stem) or stem   # marker added to partial downloads
    m = WORK_SUFFIX_RE.match(stem)
    return m.group("base") if m and m.group("base") else stem


def parse_tag_list(text):
    """'OST, *soundtrack*;Live' -> ['ost', '*soundtrack*', 'live'] (lower case, spaces collapsed)."""
    items = (re.sub(r"\s+", " ", x).strip().lower() for x in re.split(r"[,;\n]", text or ""))
    return [x for x in items if x]


def _tag_matches(inner, phrase):
    """Whole-bracket match; a '*' in the phrase stands for any text."""
    if "*" in phrase:
        return re.fullmatch(".*".join(re.escape(p) for p in phrase.split("*")), inner) is not None
    return inner == phrase


_ID_TAIL = re.compile(r"\s*\[([A-Za-z0-9_-]{11})\]\s*$")


def _looks_like_video_id(code):
    """YouTube ids are 11 characters of letters, digits, '_' and '-'. A plain word such as
    [Remastered] must not count, so an id needs a digit, a '_' / '-', or capitals inside it."""
    return (any(c.isdigit() or c in "_-" for c in code)
            or (code[1:] != code[1:].lower() and code != code.upper()))


def strip_noise_tags(text, extra=()):
    """Drop bracketed tags like (Official Video), (Audio), [HD] and any phrases in `extra`;
    all other brackets are kept. A bracket is only removed if its whole content matches."""
    def repl(m):
        """Replacement function for one bracket: drop it if it is a known noise tag, keep it otherwise."""
        inner = re.sub(r"\s+", " ", m.group(1)).strip().lower()
        if inner in NOISE_TAGS or any(_tag_matches(inner, p) for p in extra):
            return ""
        return m.group(0)
    out = re.sub(r"\s{2,}", " ", _BRACKETS.sub(repl, text)).strip()
    m = _ID_TAIL.search(out)
    if m and m.start() > 0 and _looks_like_video_id(m.group(1)):
        out = out[:m.start()].strip()  # the "[YPI6ugKmYag]" yt-dlp puts at the end of a file name
    return re.sub(r"\s*[-–—]\s*$", "", out).strip()


def safe_filename(name):
    """Make text usable as a file name on Mac and Windows."""
    name = name.replace("/", "-").replace("\\", "-").replace(":", " -")
    name = re.sub(r'[<>"|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s{2,}", " ", name).strip(" .")
    return name[:150].strip(" .")


def apply_name_prefix(stem, prefix):
    """Put `prefix` in front of a file name (without extension).
    'Band' -> 'Band - Song'. If the prefix itself ends with a space, dash, underscore or colon it is
    used exactly as typed ('Band - ' -> 'Band - Song'). Nothing is added if the name already starts
    with the prefix as a whole word."""
    raw = (prefix or "").lstrip()
    core = raw.strip(" -–—_:")
    if not core:
        return stem
    if stem.lower().startswith(core.lower()) and (len(stem) == len(core) or not stem[len(core)].isalnum()):
        return stem
    sep = "" if raw[-1] in " -–—_:" else " - "
    return safe_filename(raw + sep + stem) or stem


def prefix_target_path(path, prefix):
    """Path with the name prefix ('Band - ') put in front of the file name."""
    stem, ext = os.path.splitext(os.path.basename(path))
    return os.path.join(os.path.dirname(path), apply_name_prefix(stem, prefix) + ext)


def clean_name_for(orig_stem, strip_tags=True, extra_tags=()):
    """The final file name (no extension): the original title, optionally without junk tags
    like (Official Video) or (Audio)."""
    name = strip_noise_tags(orig_stem, extra_tags) if strip_tags else orig_stem
    return safe_filename(name) or orig_stem


def clean_target_path(src, strip_tags=True, extra_tags=()):
    """Where `src` should be renamed to (same folder): its name without the suffixes this app adds."""
    stem, ext = os.path.splitext(os.path.basename(src))
    new_stem = clean_name_for(strip_work_suffixes(stem), strip_tags, extra_tags)
    return os.path.join(os.path.dirname(src), new_stem + ext)


def rename_if_free(src, target):
    """Rename src -> target unless that would overwrite another file. Returns (path, note)."""
    if os.path.abspath(target) == os.path.abspath(src):
        return src, ""
    if os.path.exists(target) and not os.path.samefile(src, target):
        return src, f"name kept: \u201c{os.path.basename(target)}\u201d already exists"
    os.rename(src, target)
    return target, ""


def cleanup_download_partials(folder, since):
    """Remove what an interrupted yt-dlp download left behind (only files made since `since`)."""
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for n in names:
        p = os.path.join(folder, n)
        try:
            if (os.path.isfile(p) and os.path.getmtime(p) >= since - 1
                    and (n.endswith(".ytdl") or re.search(r"\.part(-Frag\d+)?$", n)
                         or re.search(r"\.f\d+\.[A-Za-z0-9]+$", n))):
                os.remove(p)
        except OSError:
            pass


def unique_path(path):
    """path, or 'name (2).ext', 'name (3).ext'... so a batch never overwrites a file."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def short_error(text, limit=80):
    """One readable line from an error log (prefers a line that mentions 'error')."""
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    if not lines:
        return "unknown error"
    pick = next((ln for ln in reversed(lines) if "error" in ln.lower()), lines[-1])
    return pick if len(pick) <= limit else pick[:limit - 1] + "…"


# ---- download history, list numbers, tags, saved batch list
_HISTORY = None
_HISTORY_LOCK = threading.Lock()


def history_path():
    """Where the list of already downloaded videos is stored."""
    return os.path.join(os.path.dirname(settings_path()), "download_history.json")


def _history():
    """The download history (loaded from disk on first use, then kept in memory)."""
    global _HISTORY
    if _HISTORY is None:
        try:
            with open(history_path(), encoding="utf-8") as f:
                data = json.load(f)
            _HISTORY = data if isinstance(data, dict) else {}
        except Exception:
            _HISTORY = {}
    return _HISTORY


def _write_json_atomic(path, data):
    """Write a JSON file safely: to a temporary file first, then swap it in."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except Exception:
        pass


def video_key(url):
    """A stable identity for a video link, so the same video is recognised whatever the link looks like."""
    url = (url or "").strip()
    try:
        p = urlparse(url)
    except ValueError:
        return url
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    q = parse_qs(p.query)
    if host == "youtu.be" and p.path.strip("/"):
        return "youtube:" + p.path.strip("/").split("/")[0]
    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if q.get("v"):
            return "youtube:" + q["v"][0]
        m = re.match(r"^/(?:shorts|embed|live|v)/([^/?#]+)", p.path)
        if m:
            return "youtube:" + m.group(1)
    return host + p.path.rstrip("/") + (("?" + p.query) if p.query else "")


def history_known(url):
    """The history entry for this video ({'file','title','when'}) or None."""
    with _HISTORY_LOCK:
        return _history().get(video_key(url))


def record_download(url, path, title=None):
    """Remember that a video was downloaded (so it can be skipped next time)."""
    with _HISTORY_LOCK:
        _history()[video_key(url)] = {"file": path, "title": title or os.path.basename(path),
                                      "when": time.strftime("%Y-%m-%d %H:%M")}
        _write_json_atomic(history_path(), _history())


def forget_history():
    """Clear the whole download history."""
    global _HISTORY
    with _HISTORY_LOCK:
        _HISTORY = {}
        _write_json_atomic(history_path(), _HISTORY)


_LEAD_NUM = re.compile(r"^\s*\d{1,3}\s*[-–—._)]\s*")


def strip_leading_number(stem):
    """'03 - Song' -> 'Song' (a list number replaces an existing track number)."""
    out = _LEAD_NUM.sub("", stem, count=1)
    return out if out.strip() else stem


def build_download_name(stem, prefix="", number=None, width=2):
    """File name (no extension) of a downloaded item: the list number first (optional), then the
    text from 'Add to start of names', then the title -> '01 - Band - Song'."""
    if number is not None:
        stem = strip_leading_number(stem)
    name = apply_name_prefix(stem, prefix)
    if number is not None:
        name = f"{number:0{width}d} - {name}"
    return name


def download_target_path(path, prefix="", number=None, width=2):
    """Path of a downloaded file after the prefix / numbering has been applied."""
    stem, ext = os.path.splitext(os.path.basename(path))
    return os.path.join(os.path.dirname(path), build_download_name(stem, prefix, number, width) + ext)


def tag_artist(prefix):
    """The artist for the tags is the text from 'Add to start of names' (without separators)."""
    return (prefix or "").strip().strip(" -–—_:")


GENERIC_FOLDERS = {"downloads", "download", "desktop", "documents", "music", "movies", "videos", "home",
                   "tmp", "temp", "users", "volumes"}


def folder_album(path):
    """Album name taken from the folder a file is in (the folder it ends up in); '' for general folders
    like Downloads, Music or the home folder, where a folder name would make no sense as an album."""
    name = os.path.basename(os.path.dirname(os.path.abspath(path))).strip()
    if not name or name.lower() in GENERIC_FOLDERS or name.lower() == os.path.basename(os.path.expanduser("~")).lower():
        return ""
    return name


def read_media_tags(path):
    """Title, artist and album written in a media file (ffprobe), as a dict of strings ('' = not set)."""
    out = {"title": "", "artist": "", "album": ""}
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        return out
    try:
        r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format_tags", "-of", "json", path],
                           capture_output=True, timeout=20, env=tool_env(), **TEXT)
        tags = (json.loads(r.stdout or "{}").get("format") or {}).get("tags") or {}
        low = {str(k).lower(): str(v) for k, v in tags.items()}
        for k in out:
            out[k] = low.get(k, "").strip()
    except Exception:
        pass
    return out


def vu_analyze(ffmpeg, path, data, stop):
    """Background job for the VU meter: read the loudness of a file in 50 ms steps (much faster than
    playing it). Appends (left_rms, right_rms, left_peak, right_peak) in dB to data."""
    filt = ("aresample=8000,asetnsamples=n=400:p=0,astats=metadata=1:reset=1:"
            "measure_perchannel=Peak_level+RMS_level:measure_overall=none,ametadata=mode=print:file=-")
    for f_ in (filt, filt.replace("measure_perchannel=Peak_level+RMS_level:measure_overall=none,", ",").replace(":,", ",")):
        try:
            proc = subprocess.Popen([ffmpeg, "-v", "error", "-nostdin", "-i", path, "-vn", "-ac", "2", "-af", f_,
                                     "-f", "null", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, env=tool_env(), creationflags=NO_WINDOW)
        except OSError:
            return
        stop["proc"] = proc
        cur = {}

        def flush():
            """Store the level values collected for one audio frame, then reset for the next one."""
            if cur:
                g = lambda k: cur.get(k, -90.0)
                data.append((g("1.RMS_level"), g("2.RMS_level") if "2.RMS_level" in cur else g("1.RMS_level"),
                             g("1.Peak_level"), g("2.Peak_level") if "2.Peak_level" in cur else g("1.Peak_level")))
                cur.clear()
        for raw in proc.stdout:
            if stop.get("stop"):
                break
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("frame:"):
                flush()
            elif line.startswith("lavfi.astats."):
                k, _, v = line[len("lavfi.astats."):].partition("=")
                try:
                    cur[k] = max(-90.0, float(v))
                except ValueError:
                    cur[k] = -90.0  # "-inf" = silence
        flush()
        try:
            proc.kill()
        except OSError:
            pass
        if data or stop.get("stop"):
            break
    stop["done"] = True


def plain_text(text):
    """Lower-case text without accents, for searching ('Dvořák' is found by 'dvorak')."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).lower()) if not unicodedata.combining(c))


def read_cover_png(path, size=112, real_video=False):
    """The picture of a file as PNG bytes scaled into size x size: the cover inside an audio file, or a
    frame of a video. None if the file has no picture."""
    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        return None
    cmd = [ffmpeg, "-v", "error"] + (["-ss", "1"] if real_video else []) + ["-i", path, "-map", "0:v:0",
           "-frames:v", "1", "-vf",  # a wide picture is cropped to a centred square, like an album cover
           f"crop='min(iw,ih)':'min(iw,ih)',scale={size}:{size}",
           "-f", "image2pipe", "-c:v", "png", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=25, env=tool_env(), stdin=subprocess.DEVNULL,
                           creationflags=NO_WINDOW)
        return r.stdout if r.returncode == 0 and r.stdout[:4] == b"\x89PNG" else None
    except Exception:
        return None


def guess_artist(stem, strip_tags=True, extra=()):
    """The artist from a name like 'Artist - Title' (an app suffix and a leading list number are ignored);
    '' if the name has no such pattern."""
    t = strip_work_suffixes(stem)
    t = _LEAD_NUM.sub("", t, count=1) or t
    if strip_tags:
        t = strip_noise_tags(t, extra)
    m = re.match(r"^\s*(.{1,60}?)\s+[-–—]\s+(\S.*)$", t)
    return m.group(1).strip() if m else ""


def tag_title_from_stem(stem, artist="", strip_tags=True, extra=()):
    """The song title for the Title tag, taken from a final file name: this app's suffixes, a
    leading list number and a leading 'Artist - ' are removed."""
    t = strip_work_suffixes(stem)
    t = _LEAD_NUM.sub("", t, count=1) or t
    if artist:
        m = re.match(re.escape(artist) + r"\s*[-–—:_]\s*", t, re.IGNORECASE)
        if m and t[m.end():].strip():
            t = t[m.end():]
    if strip_tags:
        t = strip_noise_tags(t, extra)
    return t.strip() or stem


def make_cover_image(ffmpeg, src, duration=None):
    """A JPEG to use as cover art: the picture already inside the file if it has one, otherwise a
    frame from the video. Returns the temp file path, or None (audio without a picture, or a failure)."""
    import tempfile
    out = os.path.join(tempfile.gettempdir(), "faun_cover_%d_%d.jpg" % (os.getpid(), int(time.time() * 1000)))
    scale = ["-vf", "scale='min(1000,iw)':-2", "-frames:v", "1", "-q:v", "3"]
    try:
        probe = subprocess.run([ffmpeg, "-hide_banner", "-i", src], capture_output=True, timeout=30, **TEXT).stderr or ""
        pic = re.search(r"Stream #0:(\d+)[^\n]*Video:[^\n]*\(attached pic\)", probe)
        if pic:
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
                   "-map", "0:" + pic.group(1)] + scale + [out]
        elif re.search(r"Stream #0:\d+[^\n]*Video:", probe):
            at = min((duration or 0) * 0.1, 120) if duration else 1
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", src,
                   "-map", "0:v:0"] + scale + [out]
        else:
            return None
        subprocess.run(cmd, capture_output=True, timeout=60, **TEXT)
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            return out
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        os.remove(out)
    except OSError:
        pass
    return None


def build_tag_command(src, tmp, tags, all_streams=True):
    """Copy the file without re-encoding, adding/replacing tags (ffmpeg arguments without the program)."""
    ext = os.path.splitext(tmp)[1].lower()
    args = ["-y", "-hide_banner", "-i", src]
    args += ["-map", "0"] if all_streams else ["-map", "0:v?", "-map", "0:a?"]
    args += ["-c", "copy"]
    for key, value in tags.items():
        args += ["-metadata", f"{key}={value}"]
    if ext == ".mp3":
        args += ["-id3v2_version", "3", "-write_id3v1", "1"]  # v1 as well: car radios and old players read it
    if ext in (".mp4", ".m4v", ".mov", ".m4a"):
        args += ["-movflags", "+faststart"]
    return args + ["-progress", "pipe:1", "-nostats", tmp]


def batch_list_path():
    """Where the Batch list is stored between sessions."""
    return os.path.join(os.path.dirname(settings_path()), "batch_list.json")


SAVED_ITEM_KEYS = ("kind", "value", "title", "status", "error", "output", "note", "file", "base",
                   "downloaded")
STABLE_STATUS = ("Waiting", "Failed", "Skipped", "Cancelled", "✓", "Already downloaded")


def save_batch_list(items):
    """Save the Batch list to disk (only the fields that matter for resuming)."""
    rows = []
    for it in items:
        d = {k: it.get(k) for k in SAVED_ITEM_KEYS}
        d["done"] = sorted(it.get("done", []))
        rows.append(d)
    _write_json_atomic(batch_list_path(), {"version": 1, "items": rows})


def load_batch_list():
    """Load the Batch list saved by an earlier session; invalid rows are dropped."""
    try:
        with open(batch_list_path(), encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("items", []) if isinstance(data, dict) else []
        return [r for r in rows if isinstance(r, dict) and r.get("kind") in ("link", "file") and r.get("value")]
    except Exception:
        return []


# ---- yt-dlp support
def _dl_fmt(height=None):
    """yt-dlp format arguments for 'best video up to this height (or best overall) + best audio'."""
    sel = "bv*+ba/b" if not height else f"bv*[height<={height}]+ba/b[height<={height}]"
    return ["-f", sel, "-S", "res,ext:mp4:m4a", "--merge-output-format", "mp4"]


DL_QUALITY = XD({
    "Best available (mp4)": _dl_fmt(),
    "Up to 1080p (mp4)": _dl_fmt(1080),
    "Up to 720p (mp4)": _dl_fmt(720),
    "Up to 480p (mp4)": _dl_fmt(480),
    "Audio only (mp3)": ["-x", "--audio-format", "mp3", "--audio-quality", "0"],
})


def _num(x):
    """Number as short text without trailing zeros."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def build_download_command(ytdlp, ffmpeg, url, folder, quality, section=None, exact=False,
                           single_item=False, cover=False):
    """section: (start_seconds, end_seconds_or_None) to download only part of the video.
    cover: put the video's thumbnail into the file as cover art."""
    name = "%(title).150B.%(ext)s"
    extra = []
    if cover:
        extra += ["--embed-thumbnail", "--convert-thumbnails", "jpg"]
    if section:
        s, e = section
        extra += ["--download-sections", f"*{_num(s)}-{'inf' if e is None else _num(e)}"]
        if exact:
            extra += ["--force-keyframes-at-cuts"]
        name = "%(title).150B [clip].%(ext)s"
    return ([ytdlp] + cookie_args() + ["--no-playlist", "--no-mtime", "--newline", "--progress",
             "--ffmpeg-location", os.path.dirname(ffmpeg),
             "--progress-template",
             "download:PROG %(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
             "--print", "after_move:FILEPATH=%(filepath)s",
             "--no-simulate",
             "-o", os.path.join(folder, name)]
            + DL_QUALITY[quality] + extra + (["--playlist-items", "1"] if single_item else [])
            + [url])


def newest_file(folder, since):
    """Fallback: newest finished file in folder modified since the given time."""
    best = None
    for n in os.listdir(folder):
        p = os.path.join(folder, n)
        if (os.path.isfile(p) and not n.endswith((".part", ".ytdl"))
                and os.path.getmtime(p) >= since - 1):
            if best is None or os.path.getmtime(p) > os.path.getmtime(best):
                best = p
    return best


def build_command(task, src, dst, opt):
    """Return ffmpeg argument list (without the ffmpeg path) for a task."""
    args = ["-y", "-hide_banner"]

    # Hardware decoding (only helps when re-encoding; harmless otherwise)
    kind = opt.get("gpu")
    reencodes = (task in ("Convert", "Compress")
                 or (task == "Trim" and opt.get("precise")))
    hw = GPU_KINDS[kind]["hwaccel"] if kind and reencodes else []

    if task == "Trim":
        args += hw + ["-ss", opt["start"], "-to", opt["end"], "-i", src]
        if opt.get("precise"):
            args += v_encode(opt, 18, "fast") + ["-c:a", "aac"]
        else:
            args += ["-c", "copy", "-avoid_negative_ts", "make_zero"]

    elif task == "Convert":
        fmt = opt["format"]
        crf = QUALITY[opt["conv_quality"]]
        # GIF / WebM have no hardware encoder -> always CPU
        if fmt in ("gif", "webm"):
            hw = []
        args += hw + ["-i", src]
        if fmt == "gif":
            args += ["-vf", "fps=12,scale=480:-1:flags=lanczos,split[a][b];"
                            "[a]palettegen[p];[b][p]paletteuse", "-loop", "0"]
        elif fmt == "webm":
            args += ["-c:v", "libvpx-vp9", "-crf", str(crf + 8), "-b:v", "0",
                     "-c:a", "libopus"]
        else:
            mp4like = fmt in ("mp4", "mov")
            args += v_encode(opt, crf, "medium", opt["codec"], mp4=mp4like)
            args += ["-c:a", "aac", "-b:a", "160k"]
            if mp4like:
                args += ["-movflags", "+faststart"]

    elif task == "Compress":
        sample = opt.get("sample")  # (start, length): a short piece for the preview
        args += hw + (["-ss", f"{sample[0]:.3f}", "-t", f"{sample[1]:.3f}"] if sample else []) + ["-i", src]
        args += v_encode(opt, QUALITY[opt["quality"]], "medium", opt["codec"],
                         mp4=True, kbps=opt.get("video_kbps"))
        args += ["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
        h = RESOLUTIONS[opt["resolution"]]
        if h:
            args += ["-vf", f"scale=-2:'min({h},ih)'"]

    elif task == "Extract audio":
        cover = opt.get("cover") if opt["format"] in ("mp3", "m4a") else None
        if cover:  # a picture goes in as the album cover
            args += ["-i", src, "-i", cover, "-map", "0:a:0", "-map", "1:v:0", "-c:v", "copy"]
            args += AUDIO_FORMATS[opt["format"]]
            if opt["format"] == "mp3":
                args += ["-id3v2_version", "3", "-metadata:s:v", "title=Album cover",
                         "-metadata:s:v", "comment=Cover (front)"]
            else:
                args += ["-disposition:v:0", "attached_pic"]
        else:
            args += ["-i", src, "-vn"] + AUDIO_FORMATS[opt["format"]]

    elif task == "Remove audio":
        args += ["-i", src, "-c:v", "copy", "-an"]

    else:
        raise ValueError(task)

    args += ["-progress", "pipe:1", "-nostats", dst]
    return args


def output_ext(task, src, opt):
    """File extension the result of a task gets."""
    if task == "Convert":
        return "." + opt["format"]
    if task == "Extract audio":
        return "." + opt["format"]
    if task == "Compress":
        return ".mp4"
    return os.path.splitext(src)[1] or ".mp4"


def suggested_output(task, src, opt):
    """The suggested output path: the source name plus a suffix for the task (_trim, _norm …)."""
    base = os.path.splitext(src)[0]
    suffix = {"Trim": "_trim", "Convert": "_conv", "Compress": "_small",
              "Extract audio": "_audio", "Remove audio": "_mute",
              "Loudness": "_norm"}[task]
    return base + suffix + output_ext(task, src, opt)


# ------------------------------------------------------------------ GUI
# ---- Browse tab (search / list pages through yt-dlp)
BROWSE_PAGE = 24


def _browse_thumb(e):
    """The best thumbnail address for a search result (yt-dlp entry)."""
    thumbs = [t for t in (e.get("thumbnails") or []) if isinstance(t, dict) and t.get("url")]
    good = [t for t in thumbs if (t.get("width") or 0) >= 300 and not str(t["url"]).endswith(".webp")]
    pick = e.get("thumbnail") or (good[0]["url"] if good else (thumbs[-1]["url"] if thumbs else None))
    if pick:
        return "https:" + pick if str(pick).startswith("//") else pick
    if str(e.get("ie_key") or "").lower().startswith("youtube") and e.get("id"):
        return f"https://i.ytimg.com/vi/{e['id']}/mqdefault.jpg"
    return None


# Signing in to YouTube: yt-dlp reads the login cookies from a browser the person is already signed in with
# (nothing is typed into or stored by this app).
YT_ACCOUNT = {"browser": ""}
YT_BROWSERS = ["None", "Chrome", "Firefox", "Safari", "Edge", "Brave", "Chromium", "Opera", "Vivaldi"]
YT_FEEDS = XD({"Recommended": ":ytrec", "Subscriptions (new videos)": ":ytsubs",
               "Subscribed channels": "https://www.youtube.com/feed/channels",
               "My playlists": "https://www.youtube.com/feed/playlists", "Watch later": ":ytwatchlater",
               "Liked videos": "https://www.youtube.com/playlist?list=LL", "History": ":ythis"})


def cookie_args():
    """yt-dlp options that use the browser's YouTube login (none if no browser is chosen)."""
    b = YT_ACCOUNT.get("browser") or ""
    return ["--cookies-from-browser", b] if b else []


BROWSE_SECTIONS = {"Videos": "videos", "Shorts": "shorts", "Live": "streams", "Playlists": "playlists",
                   "Releases": "releases"}
_YT_CHANNEL_RE = re.compile(
    r"^(https?://(?:www\.|m\.)?youtube\.com/(?:@[^/?#]+|channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+))/?(?:[?#].*)?$",
    re.I)


# Search sources. {n} = number of results, {raw} = the words as typed, {q} = the words URL-encoded.
# Sites in the Browse tab: name -> {what to search for: search address / yt-dlp search prefix}.
# None = YouTube's own handling. An empty dict = no search here: paste a link to a profile / list page.
BROWSE_SITES = {
    "YouTube": {"Videos": None, "Channels": None, "Playlists": None},
    "prehraj.to": {"Videos": "html:https://prehraj.to/hledej/{q}"},
    "SoundCloud": {"Tracks": "scsearch{n}:{raw}"},
    "Twitch": {"Find channel": "find:twitch:{raw}",
               "Channel videos": "https://www.twitch.tv/{name}/videos",
               "Channel clips": "https://www.twitch.tv/{name}/clips"},
}
# Readers kept for later (not in the list for now): Bilibili "bilisearch{n}:{raw}", Niconico
# "nicosearch{n}:{raw}", Dailymotion "dailymotion:{raw}", Mixcloud "mixcloud:{raw}",
# Rumble / Bandcamp via "html:" pages, and find:vimeo / find:tiktok / find:instagram.
BROWSE_KINDS = {"Videos": "EgIQAQ%3D%3D", "Channels": "EgIQAg%3D%3D", "Playlists": "EgIQAw%3D%3D"}


def browse_query(text, count, section="videos", kind="Videos", template=None):
    """A link is used as it is (a bare YouTube channel link opens its Videos / Shorts / ... list);
    @name opens that channel; anything else is a YouTube search (for videos, channels or playlists)."""
    from urllib.parse import quote
    text = (text or "").strip()
    if text.startswith(":yt"):  # yt-dlp's own account feeds (:ytrec, :ytsubs, ...)
        return text
    if re.fullmatch(r"@[\w.\-]+", text) and not template:
        text = "https://www.youtube.com/" + text
    if re.match(r"https?://", text):
        m = _YT_CHANNEL_RE.match(text)
        if re.match(r"https?://(www\.)?prehraj\.to/hledej/", text) or re.match(
                r"https?://(www\.)?(rumble\.com/search/|bandcamp\.com/search)", text):
            return "html:" + text  # these search pages are read by the app itself
        return f"{m.group(1)}/{section}" if m else text
    if not text:
        return ""
    if template:  # another site: its own search address / search prefix
        name = re.sub(r"[^\w.\-]", "", text.lstrip("@"))  # a channel / user name has no spaces
        return (template.replace("{n}", str(count)).replace("{q}", quote(text))
                .replace("{raw}", text).replace("{name}", name))
    if kind in ("Channels", "Playlists"):
        return f"https://www.youtube.com/results?search_query={quote(text)}&sp={BROWSE_KINDS[kind]}"
    return f"ytsearch{count}:{text}"


def browse_is_channel(url):
    """True if the link points to a YouTube channel."""
    return bool(_YT_CHANNEL_RE.match(str(url)))


def browse_is_list(url):
    """True for a link that opens a playlist (not one video)."""
    u = str(url)
    return "/playlist?" in u or ("list=" in u and "watch?v=" not in u and "youtu.be/" not in u)


def _browse_flat(entries, depth=0):
    """Flatten what yt-dlp returns: tabs of a channel (playlists inside playlists) become one list of videos."""
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        if e.get("_type") == "playlist" and e.get("entries") is not None and depth < 2:
            yield from _browse_flat(e.get("entries"), depth + 1)  # a tab of a channel: use its videos
        else:
            yield e


def browse_entries(data):
    """Plain dicts for the list, from yt-dlp's --flat-playlist JSON."""
    rows = []
    for e in _browse_flat((data or {}).get("entries")):
        u = e.get("webpage_url") or e.get("url")
        if not u or not str(u).startswith("http"):
            vid = e.get("id") or u
            is_yt = str(e.get("ie_key") or "").lower().startswith("youtube")
            u = f"https://www.youtube.com/watch?v={vid}" if is_yt and vid else None
        if not u:
            continue
        rows.append({"url": u, "title": e.get("title") or u, "is_channel": browse_is_channel(u),
                     "is_list": browse_is_list(u) or browse_is_channel(u),
                     "channel": e.get("channel") or e.get("uploader") or "",
                     "duration": e.get("duration"), "views": e.get("view_count"),
                     "date": e.get("upload_date") or "", "thumb": _browse_thumb(e),
                     "desc": e.get("description") or "",
                     "live": e.get("live_status") == "is_live" or e.get("is_live") is True,
                     "soon": e.get("live_status") == "is_upcoming"})
    return rows


# Sites read from their web page: host -> what the path of one item's page looks like.
BROWSE_HTML_SITES = {
    "prehraj.to": r"/[^/]+/[0-9a-f]{12,}",
    "rumble.com": r"/v[0-9a-z]{4,8}-[^/]+\.html",
    "bandcamp.com": r"/(?:track|album)/[^/]+",
}


def _curl_text(url, timeout=40):
    """(text, error) of a web page / API answer, loaded with curl (on every Mac and Windows 10+)."""
    curl = find_tool("curl") or "curl"
    try:
        r = subprocess.run([curl, "-sL", "--max-time", str(timeout), "-A",
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15", url],
                           capture_output=True, timeout=timeout + 10, env=tool_env(), **TEXT)
    except (subprocess.TimeoutExpired, OSError) as ex:
        return "", f"Could not load the page: {ex}"
    if not r.stdout or r.returncode != 0:
        return "", short_error(r.stderr or "The page did not load.", 160)
    return r.stdout, ""


def _date_digits(v):
    """'2024-01-31T..' or an epoch number -> '20240131' (or '')."""
    try:
        if isinstance(v, (int, float)):
            return time.strftime("%Y%m%d", time.gmtime(v))
        return re.sub(r"\D", "", str(v))[:8]
    except (ValueError, OverflowError, OSError):
        return ""


def browse_api_fetch(kind, text, start, end):
    """(rows, error) from a site's public search API: 'dailymotion' or 'mixcloud'."""
    from urllib.parse import quote
    n = end - start + 1
    if kind == "dailymotion":
        url = ("https://api.dailymotion.com/videos?search=" + quote(text) +
               "&fields=id,title,url,duration,views_total,created_time,owner.screenname,"
               f"thumbnail_360_url,thumbnail_240_url&limit={n}&page={(start - 1) // n + 1}")
    else:
        url = ("https://api.mixcloud.com/search/?q=" + quote(text) +
               f"&type=cloud&limit={n}&offset={start - 1}")
    body, err = _curl_text(url)
    if err:
        return [], err
    try:
        data = json.loads(body)
    except ValueError:
        return [], "The site did not answer with a result list."
    rows = []
    if kind == "dailymotion":
        for it in data.get("list") or []:
            u = it.get("url") or f"https://www.dailymotion.com/video/{it.get('id')}"
            rows.append({"url": u, "title": it.get("title") or u, "is_channel": False, "is_list": False,
                         "channel": it.get("owner.screenname") or "", "duration": it.get("duration"),
                         "views": it.get("views_total"), "date": _date_digits(it.get("created_time")),
                         "thumb": it.get("thumbnail_360_url") or it.get("thumbnail_240_url"), "desc": ""})
    else:
        for it in data.get("data") or []:
            pics = it.get("pictures") or {}
            rows.append({"url": it.get("url") or "", "title": it.get("name") or it.get("url") or "",
                         "is_channel": False, "is_list": False,
                         "channel": (it.get("user") or {}).get("name") or "",
                         "duration": it.get("audio_length"), "views": it.get("play_count"),
                         "date": _date_digits(it.get("created_time")),
                         "thumb": pics.get("large") or pics.get("medium") or pics.get("320wx320h"),
                         "desc": ""})
        rows = [r for r in rows if r["url"]]
    return rows, ("" if rows else "No results.")


class _VideoLinkParser:
    """Finds video-page links (with title, picture, length) in a site's search page."""

    def __init__(self, base):
        """Set up the page reader for sites without a yt-dlp search (e.g. prehraj.to): remember which links are videos."""
        from html.parser import HTMLParser
        host = urlparse(base).netloc.lower()
        self.site = next((k for k in BROWSE_HTML_SITES if host.endswith(k)), None)
        outer = self
        self.base, self.items, self._cur = base, {}, None

        class P(HTMLParser):
            """HTML parser that collects links to video pages with their thumbnail and title text."""
            def handle_starttag(self, tag, attrs):
                """A link starts a candidate video; an image inside it supplies the thumbnail."""
                a = dict(attrs)
                if tag == "a" and a.get("href"):
                    outer._open(a)
                elif outer._cur is not None and tag == "img":
                    src = a.get("data-src") or a.get("src") or ""
                    if src and not src.startswith("data:") and not outer._cur["thumb"]:
                        outer._cur["thumb"] = src
                    if a.get("alt") and not outer._cur["title"]:
                        outer._cur["title"] = a["alt"]

            def handle_endtag(self, tag):
                """The end of a link finishes the candidate."""
                if tag == "a":
                    outer._cur = None

            def handle_data(self, data):
                """Text inside a link becomes part of the title."""
                if outer._cur is not None and data.strip():
                    outer._cur["text"].append(data.strip())
        self.parser = P(convert_charrefs=True)

    def _open(self, a):
        """Start collecting a candidate if the link looks like a video page of this site."""
        from urllib.parse import urljoin
        href = urljoin(self.base, a["href"])
        path = urlparse(href).path
        # a video page of this site (prehraj.to: /name/<long hex id>, ...)
        host = urlparse(href).netloc.lower()
        if (not self.site or not re.fullmatch(BROWSE_HTML_SITES[self.site], path)
                or not host.endswith(self.site)):
            self._cur = None
            return
        self._cur = self.items.setdefault(href.split("?")[0], {"title": a.get("title") or "", "thumb": "",
                                                                "text": []})
        if a.get("title") and not self._cur["title"]:
            self._cur["title"] = a["title"]

    def feed(self, html):
        """Read a result page and return the list of videos found in it."""
        self.parser.feed(html)
        rows = []
        for url, it in self.items.items():
            text = " ".join(it["text"])
            dur = re.search(r"\b(\d{1,2}:)?\d{1,2}:\d{2}\b", text)
            bare = re.sub(r"\b(\d{1,2}:)?\d{1,2}:\d{2}\b", "", text)  # the length is not part of the title
            title = it["title"] or re.sub(r"\s+", " ", bare).strip() or url
            thumb = it["thumb"]
            if thumb:
                from urllib.parse import urljoin
                thumb = urljoin(self.base, thumb)
            secs = None
            if dur:
                parts = [int(x) for x in dur.group(0).split(":")]
                secs = sum(v * 60 ** i for i, v in enumerate(reversed(parts)))
            rows.append({"url": url, "title": title, "is_channel": False,
                         "is_list": "/album/" in url,  # a Bandcamp album: opens its track list
                         "channel": "", "duration": secs, "views": None, "date": "", "thumb": thumb or None,
                         "desc": ""})
        return rows


def browse_html_fetch(url, timeout=40):
    """(rows, error): for sites yt-dlp cannot list. Reads the search page and picks out the item links."""
    body, err = _curl_text(url, timeout)
    if err:
        return [], err
    rows = _VideoLinkParser(url).feed(body)
    return rows, ("" if rows else "Nothing found on that page (the site may have changed).")


_TWITCH_RE = re.compile(r"^https?://(?:www\.)?twitch\.tv/([\w.\-]+)/(?:videos|clips)\b", re.I)


def browse_twitch_extras(ytdlp, query, start, rows):
    """Twitch lists only past broadcasts: fill in the channel name, and put the live stream first
    when the channel is on air right now."""
    m = _TWITCH_RE.match(query)
    if not m:
        return rows
    name = m.group(1)
    for r in rows:
        if not r["channel"]:
            r["channel"] = name
    if start == 1:
        try:
            p = subprocess.run([ytdlp, "-J", "--no-playlist", "--no-warnings", f"https://www.twitch.tv/{name}"],
                               capture_output=True, timeout=30, env=tool_env(), **TEXT)
            d = json.loads(p.stdout)
        except Exception:
            d = None
        if isinstance(d, dict) and (d.get("is_live") or d.get("live_status") == "is_live"):
            rows.insert(0, {"url": f"https://www.twitch.tv/{name}", "title": d.get("title") or f"{name} (live)",
                            "is_channel": False, "is_list": False, "channel": d.get("uploader") or name,
                            "duration": None, "views": d.get("view_count"), "date": "",
                            "thumb": d.get("thumbnail"), "desc": d.get("description") or "",
                            "live": True, "soon": False, "desc_full": True})
    return rows


# ---- finding a channel / user by part of its name (Twitch, TikTok, Instagram, Vimeo)
FIND_SITES = {  # site: (web domain, what a profile page address looks like, the list address to open)
    "twitch": ("twitch.tv", r"/([A-Za-z0-9_]{3,25})", "https://www.twitch.tv/{n}/videos"),
    "tiktok": ("tiktok.com", r"/@([\w.]{2,40})", "https://www.tiktok.com/@{n}"),
    "instagram": ("instagram.com", r"/([\w.]{2,30})/?", "https://www.instagram.com/{n}/"),
    "vimeo": ("vimeo.com", r"/([A-Za-z0-9_\-]{3,40})", "https://vimeo.com/{n}"),
}
_FIND_RESERVED = {"directory", "search", "videos", "downloads", "jobs", "store", "p", "explore", "reel",
                  "reels", "stories", "accounts", "about", "legal", "help", "login", "signup", "settings",
                  "turbo", "subs", "friends", "tv", "t", "tag", "music", "upload", "watch",
                  "categories", "stock", "features", "enterprise", "solutions", "blog"}
TWITCH_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # the public key twitch.tv's own web page uses
_TWITCH_QUERIES = (
    'query($q:String!){searchFor(userQuery:$q,platform:"web",options:{targets:[{index:CHANNEL}]})'
    '{channels{items{... on User{login displayName followers{totalCount} stream{viewersCount title}}}}}}',
    'query($q:String!){searchUsers(userQuery:$q){edges{node{login displayName followers{totalCount} '
    'stream{viewersCount title}}}}}',
)


def _walk_users(obj):
    """Walk through nested JSON and yield every object that has a 'login' (a user)."""
    if isinstance(obj, dict):
        if obj.get("login"):
            yield obj
        for v in obj.values():
            yield from _walk_users(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_users(v)


def _twitch_find(text):
    """(rows, error) from Twitch's own search (the same one the website uses)."""
    curl = find_tool("curl") or "curl"
    err = ""
    for q in _TWITCH_QUERIES:
        body = json.dumps({"query": q, "variables": {"q": text}})
        try:
            r = subprocess.run([curl, "-s", "--max-time", "25", "-X", "POST",
                                "-H", "Client-ID: " + TWITCH_CLIENT_ID,
                                "-H", "Content-Type: text/plain;charset=UTF-8",
                                "--data-binary", body, "https://gql.twitch.tv/gql"],
                               capture_output=True, timeout=35, env=tool_env(), **TEXT)
            data = json.loads(r.stdout)
        except Exception as ex:
            err = str(ex)
            continue
        users = {}
        for u in _walk_users(data):
            users.setdefault(u["login"].lower(), u)
        if users:
            rows = []
            for u in sorted(users.values(), key=lambda u: -((u.get("followers") or {}).get("totalCount") or 0)):
                login = u["login"]
                st = u.get("stream") or None
                fol = (u.get("followers") or {}).get("totalCount")
                rows.append({"url": f"https://www.twitch.tv/{login}/videos", "title": u.get("displayName") or login,
                             "is_channel": True, "is_list": True, "channel": login, "duration": None,
                             "views": None, "date": "", "thumb": None, "live": bool(st), "soon": False,
                             "desc": (f"{fol:,} followers" if isinstance(fol, int) else "")
                                     + (f"\nLIVE: {st.get('title')}" if st and st.get("title") else "")})
            return rows, ""
        errs = data.get("errors") if isinstance(data, dict) else None
        if errs:
            err = str(errs[0].get("message") if isinstance(errs[0], dict) else errs[0])[:120]
    return [], err


def _web_find(site, text):
    """(rows, error): profile pages found through a web search (site:<domain> <words>)."""
    from html.parser import HTMLParser
    from urllib.parse import quote, unquote
    domain, path_re, list_url = FIND_SITES[site]
    body, err = _curl_text("https://html.duckduckgo.com/html/?q=" + quote(f"site:{domain} {text}"))
    if err:
        return [], err
    hits = []

    class P(HTMLParser):
        """HTML parser for the web search results page (collects result links and titles)."""
        cur = None

        def handle_starttag(self, tag, attrs):
            """A result link starts a new hit."""
            a = dict(attrs)
            if tag == "a" and "result__a" in (a.get("class") or ""):
                self.cur = [a.get("href") or "", ""]

        def handle_data(self, data):
            """Text inside a result link is the hit's title."""
            if self.cur is not None:
                self.cur[1] += data

        def handle_endtag(self, tag):
            """End of a result link: store the hit."""
            if tag == "a" and self.cur is not None:
                hits.append(self.cur)
                self.cur = None
    P().feed(body)
    rows, seen = [], set()
    for href, title in hits:
        m = re.search(r"uddg=([^&]+)", href)
        link = unquote(m.group(1)) if m else href
        pu = urlparse(link)
        if not pu.netloc.lower().endswith(domain):
            continue
        pm = re.fullmatch(path_re, pu.path)
        if not pm or pm.group(1).lower() in _FIND_RESERVED or pm.group(1).lower() in seen:
            continue
        name = pm.group(1)
        seen.add(name.lower())
        rows.append({"url": list_url.format(n=name), "title": re.sub(r"\s+", " ", title).strip() or name,
                     "is_channel": True, "is_list": True, "channel": name, "duration": None, "views": None,
                     "date": "", "thumb": None, "live": False, "soon": False, "desc": ""})
    return rows, ("" if rows else "No matching channel found.")


def browse_find_channels(site, text):
    """Channels / users whose name is close to what was typed."""
    if site == "twitch":
        rows, err = _twitch_find(text)
        if rows:
            return rows, ""
        rows2, err2 = _web_find(site, text)
        return rows2, ("" if rows2 else (err or err2))
    return _web_find(site, text)


def browse_fetch(ytdlp, query, start, end, timeout=90):
    """(rows, error_text). Items start..end (1-based) of the search / list page."""
    if query.startswith("find:"):  # find:<site>:<words>
        _, site, words = query.split(":", 2)
        return ([], "") if start > 1 else browse_find_channels(site, words)
    for api in ("dailymotion", "mixcloud"):
        if query.startswith(api + ":"):
            return browse_api_fetch(api, query[len(api) + 1:], start, end)
    if query.startswith("html:"):  # a site read directly from its web page (one page only)
        return ([], "") if start > 1 else browse_html_fetch(query[5:])
    browse_fetch.note = ""
    rows, err = _browse_ytdlp(ytdlp, query, start, end, timeout)
    if not rows:
        # "Artist - Topic" channels (YouTube's automatic music channels) have no Videos tab, only
        # releases and playlists: show those instead of an empty list
        m = re.match(r"^(https?://(?:www\.|m\.)?youtube\.com/(?:channel|@|c|user)[^?#]*?)/videos$", query)
        if m:
            for tab, what in (("releases", "albums and singles"), ("playlists", "playlists"), ("", "tabs")):
                alt = m.group(1) + ("/" + tab if tab else "")
                rows2, _err2 = _browse_ytdlp(ytdlp, alt, start, end, timeout)
                if rows2:
                    browse_fetch.note = f"This channel has no Videos tab, so its {what} are shown instead."
                    return rows2, ""
        pl = re.match(r"^https?://(?:www\.)?youtube\.com/playlist\?list=([\w\-]+)", query)
        if pl:  # some automatic music playlists only open through YouTube Music
            rows2, _err2 = _browse_ytdlp(ytdlp, "https://music.youtube.com/playlist?list=" + pl.group(1),
                                         start, end, timeout)
            if rows2:
                return rows2, ""
    return rows, err


browse_fetch.note = ""


def _browse_ytdlp(ytdlp, query, start, end, timeout):
    """(rows, error_text) for one yt-dlp list address."""
    try:
        r = subprocess.run([ytdlp] + cookie_args() + ["--flat-playlist", "--dump-single-json", "--no-warnings",
                            "--ignore-errors", "--playlist-items", f"{start}:{end}", query],
                           capture_output=True, timeout=timeout, env=tool_env(), **TEXT)
    except subprocess.TimeoutExpired:
        return [], "yt-dlp took too long. Try again."
    except OSError as ex:
        return [], str(ex)
    try:
        data = json.loads(r.stdout)
    except ValueError:
        return [], short_error(r.stderr or "yt-dlp returned nothing for this link.", 200)
    return browse_twitch_extras(ytdlp, query, start, browse_entries(data)), ""


def browse_details(ytdlp, url, timeout=60):
    """The full description of one video ('' if it can't be read)."""
    try:
        r = subprocess.run([ytdlp] + cookie_args() + ["--dump-single-json", "--no-playlist", "--no-warnings", url],
                           capture_output=True, timeout=timeout, env=tool_env(), **TEXT)
        return (json.loads(r.stdout).get("description") or "").strip()
    except Exception:
        return ""


def browse_thumb_files(ffmpeg, url):
    """(small_png, big_png) in a temp folder, made by ffmpeg (so JPEG / WebP both work); None on failure."""
    import hashlib
    import tempfile
    folder = os.path.join(tempfile.gettempdir(), "faun_thumbs")
    os.makedirs(folder, exist_ok=True)
    h = hashlib.md5(url.encode("utf-8")).hexdigest()
    small, big = os.path.join(folder, h + "_s3.png"), os.path.join(folder, h + "_b4.png")
    if os.path.isfile(small) and os.path.isfile(big):
        return small, big
    try:
        r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", url,
                            "-frames:v", "1", "-vf", "scale=288:162:force_original_aspect_ratio=decrease:flags=lanczos", big,
                            "-frames:v", "1", "-vf", "scale=128:72:force_original_aspect_ratio=decrease:flags=lanczos", small],
                           capture_output=True, timeout=30, env=tool_env(), **TEXT)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return (small, big) if r.returncode == 0 and os.path.isfile(small) and os.path.isfile(big) else None


def mpv_ipc(sock, messages, wait_id=None, timeout=2.0, wait_ids=None):
    """Send JSON commands to a running mpv (--input-ipc-server). Returns the 'data' of the reply
    with request_id == wait_id (or None); with wait_ids a {request_id: data} dict of all the replies.
    Unix socket on macOS / Linux, named pipe on Windows."""
    payload = b"".join(json.dumps(m).encode("utf-8") + b"\n" for m in messages)
    if IS_WIN:
        f = open(sock, "r+b", buffering=0)
        read = f.readline
        write, close = f.write, f.close
    else:
        import socket as _socket
        c = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        c.settimeout(timeout)
        c.connect(sock)
        fh = c.makefile("rb")
        read = fh.readline
        write, close = c.sendall, c.close
    try:
        write(payload)
        end = time.time() + timeout
        got = {}
        while wait_ids and time.time() < end and len(got) < len(wait_ids):
            try:
                line = read()
            except OSError:  # no (complete) answer in time
                break
            if not line:
                break
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("request_id") in wait_ids:
                got[msg["request_id"]] = msg.get("data")
        if wait_ids:
            return got
        while wait_id is not None and time.time() < end:
            line = read()
            if not line:
                break
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("request_id") == wait_id:
                return msg.get("data")
    finally:
        try:
            close()
        except OSError:
            pass
    return None


# ---- audio visualizer (drawn by mpv from the audio it plays, with ffmpeg's filters)
VIS_STYLES = XD({"Fractal": 1, "Golden spiral": 5, "Kaleidoscope": 2, "Waves": 3, "Spectrum": 4, "Mix": 6})
VIS_W, VIS_H, VIS_S = 960, 540, 540
_VIS_PSEUDO = {}


def ffmpeg_has_pseudocolor():
    """True when ffmpeg has the 'magma' colour map (ffmpeg 5+); it colours the spectrum bars."""
    if "v" not in _VIS_PSEUDO:
        ok = False
        ff = find_tool("ffmpeg")
        if ff:
            try:
                r = subprocess.run([ff, "-hide_banner", "-h", "filter=pseudocolor"],
                                   capture_output=True, timeout=15, **TEXT)
                ok = "magma" in ((r.stdout or "") + (r.stderr or ""))
            except (OSError, subprocess.SubprocessError):
                pass
        _VIS_PSEUDO["v"] = ok
    return _VIS_PSEUDO["v"]


PHI = (1 + 5 ** 0.5) / 2

def spiral_squares(m=15, steps=22):
    """Rectangles of the golden-spiral (Fibonacci) squares, used to build the spiral visualizer."""
    x, y, w, h = 0.0, 0.0, PHI ** (m + 1), PHI ** m
    out = []
    for i in range(steps):
        d = ("left", "top", "right", "bottom")[i % 4]
        if d == "left":
            s = h; sq = (x, y); x += s; w -= s
        elif d == "top":
            s = w; sq = (x, y); y += s; h -= s
        elif d == "right":
            s = h; sq = (x + w - s, y); w -= s
        else:
            s = w; sq = (x, y + h - s); h -= s
        out.append((sq[0], sq[1], s, ("br", "bl", "tl", "tr")[i % 4]))
    return out, (x + w / 2, y + h / 2)

def _png16(path, w, h, vals):
    """16-bit grey PNG; vals = list of ints (row-major)."""
    raw = bytearray()
    for yy in range(h):
        raw.append(0)
        raw += struct.pack(">%dH" % w, *vals[yy * w:(yy + 1) * w])
    def chunk(tag, data):
        """One PNG chunk (length, type, data, checksum)."""
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))

def spiral_maps(xpath, ypath, size=960, sw=1024, sh=256, kappa=0.33):
    """Two 16-bit grey pictures for ffmpeg's remap filter that bend a strip picture (sw*2 x sh) along ONE golden
    spiral (quarter arcs of the Fibonacci squares, ending in the pole): left-to-right = along the spiral,
    up-down = across it; the band narrows by phi every quarter turn."""
    squares, (px, py) = spiral_squares()
    c = size / 2
    n = size * size
    best = [9.0] * n
    xm = [0] * n
    ym = [0] * n
    arcs = []
    for (x, y, s, corner) in squares:
        cx, cy = {"tl": (x, y), "tr": (x + s, y), "br": (x + s, y + s), "bl": (x, y + s)}[corner]
        a0 = {"tl": 0, "tr": 90, "br": 180, "bl": 270}[corner]
        k0 = size / 1120.0
        arcs.append([(cx - px) * k0, (cy - py) * k0, s * k0, a0])
    # direction of travel: the end of each arc is the point it shares with the next arc
    def pt(a, k):
        """Point on the spiral for quarter turn k."""
        r = math.radians(a[3] + 90 * k)
        return a[0] + a[2] * math.cos(r), a[1] + a[2] * math.sin(r)
    for i, a in enumerate(arcs):
        if i + 1 < len(arcs):
            nb = arcs[i + 1]
            e1 = pt(a, 1)
            d_end = min(math.dist(e1, pt(nb, 0)), math.dist(e1, pt(nb, 1)))
            a.append(d_end < 1e-3 * a[2])  # True: arc runs a0 -> a0+90
        else:
            a.append(arcs[-2][4])
    # the direction must chain: start of arc i+1 = end of arc i
    for i in range(1, len(arcs)):
        prev_end = pt(arcs[i - 1], 1 if arcs[i - 1][4] else 0)
        forward = math.dist(prev_end, pt(arcs[i], 0)) < math.dist(prev_end, pt(arcs[i], 1))
        arcs[i][4] = forward
    for a in arcs:
        cx, cy, s, a0, fwd = a
        if s < 1.5 or s > size * 4:
            continue
        hmax = kappa * s
        steps_t = int(math.pi / 2 * (s + hmax) * 1.6) + 4
        steps_v = int(hmax * 2 * 1.6) + 4
        for it in range(steps_t + 1):
            f = it / steps_t                       # 0..1 along the quarter arc (angle order)
            ang = math.radians(a0 + 90 * f)
            ca, sa = math.cos(ang), math.sin(ang)
            frac = f if fwd else 1 - f             # 0 at the arc's start, 1 at its end
            h = kappa * s * PHI ** (-frac)
            u = int(frac * (sw * 2 - 1))
            for iv in range(steps_v + 1):
                off = -h + 2 * h * iv / steps_v     # across the line
                r = s + off
                X = int(round(c + cx + r * ca))
                Y = int(round(c + cy + r * sa))
                if 0 <= X < size and 0 <= Y < size:
                    k = Y * size + X
                    q = abs(off) / h
                    if q < best[k]:
                        best[k] = q
                        xm[k] = u
                        ym[k] = int((sh - 1) * (0.5 + 0.5 * off / h))
    _png16(xpath, size, size, xm)
    _png16(ypath, size, size, ym)


GOLD_X, GOLD_Y = "faun_spiral3_x.png", "faun_spiral3_y.png"


GOLD_LX, GOLD_LY = "faun_spiral3l_x.png", "faun_spiral3l_y.png"  # half-size maps for Mix


def golden_folder():
    """The temp folder holding the spiral maps (made on first use); mpv runs from there."""
    import tempfile
    folder = tempfile.gettempdir()
    if not (os.path.isfile(os.path.join(folder, GOLD_LX)) and os.path.isfile(os.path.join(folder, GOLD_LY))):
        spiral_maps(os.path.join(folder, GOLD_LX), os.path.join(folder, GOLD_LY), size=480, sw=512, sh=128)
    if not (os.path.isfile(os.path.join(folder, GOLD_X)) and os.path.isfile(os.path.join(folder, GOLD_Y))):
        spiral_maps(os.path.join(folder, GOLD_X), os.path.join(folder, GOLD_Y))
    return folder


def _vis_fractal_level(inp, out, s, tag):
    """Three half-size copies of the picture in a triangle (one step of a Sierpinski-like pattern)."""
    h = s // 2
    return (f"[{inp}]split=3[{tag}a][{tag}b][{tag}c];"
            f"[{tag}a]scale={h}:{h},pad={s}:{s}:{s // 4}:0[{tag}x];"
            f"[{tag}b]scale={h}:{h},pad={s}:{s}:0:{h}[{tag}y];"
            f"[{tag}c]scale={h}:{h},pad={s}:{s}:{h}:{h}[{tag}z];"
            f"[{tag}x][{tag}y]blend=all_mode=lighten[{tag}xy];"
            f"[{tag}xy][{tag}z]blend=all_mode=lighten[{out}]")


MIX_ORDER = ("Fractal", "Kaleidoscope", "Waves", "Spectrum", "Golden spiral")
MIX_SECONDS = 12  # how long one style takes to flow into the next


def _vis_mix_graph(pseudo=True):
    """All the styles at once, each fading in and out in turn so the picture flows from one into the next.
    A style's weight is a raised cosine of its distance (in styles) from the current position in the cycle."""
    import re
    n = len(MIX_ORDER)
    parts = [f"[aid1]asplit={n + 1}[ao]" + "".join(f"[m{k}]" for k in range(n)) + ";"]
    for k, name in enumerate(MIX_ORDER):
        g = visualizer_graph(name, pseudo, light=True).replace("[aid1]asplit[ao][a];", "")
        g = re.sub(r"\[(\w+)\]", lambda m: f"[{'m%d' % k if m.group(1) == 'a' else m.group(1) + '_%d' % k}]", g)
        parts.append(g + ";")
    def w(k):
        """Weight (0..1) of visualizer k in the 'Mix' style: a smooth fade between neighbours over time."""
        d = f"min(abs(mod(t/{MIX_SECONDS},{n})-{k}),{n}-abs(mod(t/{MIX_SECONDS},{n})-{k}))"
        return f"if(lt({d},1),0.5+0.5*cos(PI*{d}),0)"
    for k in range(n):  # dim each style to its weight (black stays black), then add them up
        parts.append(f"[vo_{k}]eq=contrast='{w(k)}':brightness='0.5*({w(k)})-0.5':saturation='{w(k)}':"
                     f"eval=frame,format=gbrp[z{k}];")
    parts.append("[z0][z1]blend=all_mode=addition[x1];")
    for k in range(2, n):
        parts.append(f"[x{k - 1}][z{k}]blend=all_mode=addition[x{k}];")
    parts.append(f"[x{n - 1}]format=yuv420p,scale={VIS_W}:{VIS_H}:flags=bilinear[vo]")
    return "".join(parts)


def visualizer_graph(style, pseudo=True, light=False):
    """mpv --lavfi-complex graph: plays the audio and shows moving patterns made from it."""
    if style == "Mix":
        return _vis_mix_graph(pseudo)
    W, H, s = (VIS_W // 2, VIS_H // 2, VIS_S // 2) if light else (VIS_W, VIS_H, VIS_S)  # light = half size, for Mix
    base = (f"avectorscope=s={s}x{s}:mode=lissajous:draw=line:zoom=1.3:"
            f"rc=90:gc=25:bc=160:rf=55:gf=45:bf=70:af=40:scale=sqrt,format=yuv420p")
    tail = f"pad={W}:{H}:{(W - s) // 2}:0,format=yuv420p"
    head = "[aid1]asplit[ao][a];"
    if style == "Golden spiral":
        # The audio waveform is drawn as a strip (plus smaller copies of itself, tiled) and bent along ONE
        # golden spiral, so the spiral's line is the waveform. Turning the picture by 90 degrees looks the
        # same as zooming by 1.618, so the spiral keeps winding into its centre without end.
        q = 2 if light else 1  # light: every picture in the chain is half size
        gx, gy = (GOLD_X, GOLD_Y) if not light else (GOLD_LX, GOLD_LY)
        return head + (
            f"[a]showwaves=s={1024 // q}x{256 // q}:mode=cline:rate=20:colors=0xffd25a|0xff5aa0,format=gbrp,split[w1][w2];"
            "[w1]hflip[w1f];[w2][w1f]hstack,split[s0][s1];"
            f"[s1]scale={683 // q}:{85 // q},split=3[t1][t2][t3];"
            f"[t1][t2][t3]hstack=3,pad={2048 // q + 1}:{256 // q}:0:{85 // q}:black,crop={2048 // q}:{256 // q}:0:0,format=gbrp[f1];"
            "[s0][f1]blend=all_mode=lighten,scroll=h=0.012,hue=h=t*30,format=gbrp,split[g][h2];"
            f"[h2]scale={512 // q}:{64 // q},gblur=sigma=2,scale={2048 // q}:{256 // q},eq=contrast=1.4:saturation=1.8,format=gbrp[gl];"
            "[g][gl]blend=all_mode=screen,format=rgb24[st];"
            f"movie={gx},format=gray16le[mx];movie={gy},format=gray16le[my];"
            "[st][mx][my]remap=format=color,format=yuv420p,"
            f"rotate=a=-PI/2*t/2.6:ow={W}:oh={H}:c=black,format=yuv420p[vo]")
    if style == "Spectrum":
        color = "format=yuv444p,pseudocolor=preset=magma," if pseudo else ""
        return head + (f"[a]showcqt=s={W}x{H}:fps=30:bar_v=20:bar_g=2:sono_h=0:axis_h=0,"
                       f"{color}hue=h=t*25,format=yuv420p[vo]")
    if style == "Waves":
        return head + (f"[a]avectorscope=s={H}x{H}:mode=lissajous_xy:draw=line:zoom=1.8:"
                       f"rc=40:gc=150:bc=110:rf=45:gf=40:bf=55:af=35:scale=sqrt,"
                       f"hue=h=t*35,pad={W}:{H}:{(W - H) // 2}:0,format=yuv420p[vo]")
    if style == "Kaleidoscope":
        h = s // 2
        return head + (f"[a]{base},crop={h}:{h}:0:0,split=2[k1][k2];"
                       f"[k2]hflip[k3];[k1][k3]hstack,split=2[k4][k5];[k5]vflip[k6];"
                       f"[k4][k6]vstack,hue=h=t*30,{tail}[vo]")
    return head + (f"[a]{base},split=2[f0][g0];"  # Fractal
                   + _vis_fractal_level("g0", "g1", s, "p") + ";"
                   + _vis_fractal_level("g1", "g2", s, "q") + ";"
                   + _vis_fractal_level("g2", "g3", s, "r") + ";"
                   + f"[f0][g3]blend=all_mode=lighten,hue=h=t*30,{tail}[vo]")


def is_media_path(p):
    """True if the file name ends with a video or audio extension."""
    return os.path.splitext(p)[1].lower().lstrip(".") in VIDEO_EXTS + AUDIO_EXTS


def _quick_hash(path, size):
    """A fingerprint of a file: all of it when small, otherwise the start, middle and end."""
    import hashlib
    h = hashlib.sha1(str(size).encode())
    with open(path, "rb") as f:
        if size <= 64 * 1024 * 1024:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        else:
            for pos in (0, size // 2, max(0, size - 1024 * 1024)):
                f.seek(pos)
                h.update(f.read(1024 * 1024))
    return h.hexdigest()


def _song_key(path):
    """Same song, ignoring what this app adds (_norm …) and what downloads leave behind ([id], (Official Video))."""
    stem, ext = os.path.splitext(os.path.basename(path))
    name = clean_name_for(strip_work_suffixes(stem))
    return (os.path.dirname(path), re.sub(r"\s+", " ", name).strip().lower(), ext.lower())


def find_duplicate_groups(folder, recursive=True, media_only=True, cancelled=lambda: False):
    """Groups (lists of file dicts) of files that are the same: identical content, or the same song
    under a slightly different name in one folder. Each file: {"path", "size", "mtime"}."""
    files = []
    for dp, dn, fn in os.walk(folder):
        dn[:] = sorted(x for x in dn if not x.startswith("."))
        for f in sorted(fn):
            p = os.path.join(dp, f)
            if f.startswith(".") or (media_only and not is_media_path(p)):
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            files.append({"path": p, "size": st.st_size, "mtime": st.st_mtime})
        if not recursive:
            break
        if cancelled():
            return []
    parent = list(range(len(files)))

    def find(i):
        """Union-find: the set a file belongs to."""
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        """Union-find: join two sets."""
        parent[find(a)] = find(b)
    reasons = {}
    by_size = {}
    for i, f in enumerate(files):
        if f["size"] > 0:
            by_size.setdefault(f["size"], []).append(i)
    for idxs in by_size.values():  # same size: compare the content
        if len(idxs) < 2:
            continue
        seen = {}
        for i in idxs:
            if cancelled():
                return []
            try:
                seen.setdefault(_quick_hash(files[i]["path"], files[i]["size"]), []).append(i)
            except OSError:
                pass
        for same in seen.values():
            for j in same[1:]:
                union(same[0], j)
                reasons[find(same[0])] = reasons.get(find(same[0]), set()) | {"same content"}
    by_song = {}
    for i, f in enumerate(files):
        by_song.setdefault(_song_key(f["path"]), []).append(i)
    for idxs in by_song.values():
        for j in idxs[1:]:
            union(idxs[0], j)
    groups = {}
    for i, f in enumerate(files):
        groups.setdefault(find(i), []).append(f)
    out = [g for g in groups.values() if len(g) > 1]
    for g in out:  # why they belong together
        hashes = set()
        for f in g:
            try:
                hashes.add(_quick_hash(f["path"], f["size"]))
            except OSError:
                hashes.add(f["path"])
        g[0]["why"] = "same content" if len(hashes) == 1 else "same song, different file"
    out.sort(key=lambda g: os.path.basename(g[0]["path"]).lower())
    return out


def pick_keeper(group):
    """Index of the file to keep: the one that already has a clean name, then the newest."""
    def score(i):
        """Ranking of a file to keep: clean name first, then newest, then biggest."""
        f = group[i]
        stem = os.path.splitext(os.path.basename(f["path"]))[0]
        clean = (strip_work_suffixes(stem) == stem and clean_name_for(stem) == stem)
        return (clean, f["mtime"], f["size"])
    return max(range(len(group)), key=score)


def move_to_trash(path):
    """Move a file / folder to the Trash / Recycle Bin (so it can be got back)."""
    path = os.path.abspath(path)
    if IS_WIN:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCT(ctypes.Structure):
            """Windows structure for the shell call that moves a file to the Recycle Bin."""
            _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                        ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort),
                        ("fAnyOperationsAborted", wintypes.BOOL), ("hNameMappings", ctypes.c_void_p),
                        ("lpszProgressTitle", wintypes.LPCWSTR)]
        # FO_DELETE, with FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        op = SHFILEOPSTRUCT(None, 3, path + "\0", None, 0x40 | 0x10 | 0x4 | 0x400, False, None, None)
        if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) != 0 or op.fAnyOperationsAborted:
            raise OSError("Windows could not move it to the Recycle Bin.")
        return
    if IS_MAC:
        esc = path.replace("\\", "\\\\").replace('"', '\\"')
        r = subprocess.run(["osascript", "-e", f'tell application "Finder" to delete (POSIX file "{esc}" as alias)'],
                           capture_output=True, timeout=30, **TEXT)
        if r.returncode == 0:
            return
        raise OSError(short_error(r.stderr or "Finder could not move it to the Trash.", 160))
    trash = os.path.expanduser("~/.local/share/Trash/files")
    os.makedirs(trash, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    dest, n = os.path.join(trash, stem + ext), 1
    while os.path.exists(dest):
        dest, n = os.path.join(trash, f"{stem} {n}{ext}"), n + 1
    shutil.move(path, dest)


def reveal_in_folder(path):
    """Show a file in Finder / Explorer / the file manager."""
    if IS_WIN:
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    elif IS_MAC:
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", path if os.path.isdir(path) else os.path.dirname(path)])


def human_size(n):
    """Size in bytes as text (B / KB / MB / GB)."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0


FM_PLACES = XD({"Save folder (Quick download)": "", "Home": "~", "Downloads": "~/Downloads",
                "Desktop": "~/Desktop", "Movies": "~/Movies", "Videos": "~/Videos", "Music": "~/Music"})


def ask_name(root, tk, ttk, title, label, initial):
    """A small 'new name' window. Only the part before the extension is selected, so typing keeps the
    extension. Returns the text, or None if cancelled."""
    win = tk.Toplevel(root)
    win.title(title)
    win.transient(root)
    out = {"v": None}
    var = tk.StringVar(value=initial)
    ttk.Label(win, text=label).pack(anchor="w", padx=14, pady=(14, 4))
    ent = ttk.Entry(win, textvariable=var, width=52)
    ent.pack(padx=14)

    def ok(_e=None):
        """OK pressed: remember the text and close."""
        out["v"] = var.get()
        win.destroy()

    def cancel(_e=None):
        """Cancel pressed: close without a result."""
        win.destroy()
    f = ttk.Frame(win)
    f.pack(anchor="e", padx=14, pady=12)
    ttk.Button(f, text="Cancel", command=cancel).pack(side="left", padx=(0, 6))
    ttk.Button(f, text="OK", command=ok).pack(side="left")
    win.bind("<Return>", ok)
    win.bind("<Escape>", cancel)
    ent.focus_set()
    ent.select_range(0, len(os.path.splitext(initial)[0]))
    ent.icursor(len(os.path.splitext(initial)[0]))
    try:
        win.geometry("+%d+%d" % (root.winfo_rootx() + 80, root.winfo_rooty() + 120))
        win.grab_set()
    except Exception:
        pass
    root.wait_window(win)
    return out["v"]


def find_player():
    """('mpv'|'vlc', path) of an installed player, or None."""
    p = find_tool("mpv")
    if p:
        return "mpv", p
    cands = (["/Applications/VLC.app/Contents/MacOS/VLC"] if IS_MAC else
             [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"]
             if IS_WIN else [])
    for c in cands:
        if os.path.isfile(c):
            return "vlc", c
    v = find_tool("vlc")
    return ("vlc", v) if v else None


def fmt_length(sec):
    """Seconds as 'm:ss' or 'h:mm:ss'."""
    sec = int(sec or 0)
    h, m, s2 = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s2:02d}" if h else f"{m}:{s2:02d}"


def fmt_views(n):
    """View count as short text (1.2K, 3M …)."""
    if not isinstance(n, (int, float)):
        return ""
    for lim, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= lim:
            return f"{n / lim:.1f}".rstrip("0").rstrip(".") + suf
    return str(int(n))


def fmt_upload_date(s):
    """yt-dlp date 'YYYYMMDD' as 'YYYY-MM-DD' (empty if not a date)."""
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else ""


def windows_prefers_dark():
    """True when Windows is set to dark mode for apps (first-run default of the Dark mode checkbox)."""
    if not IS_WIN:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except Exception:
        return False


DARK = {"bg": "#202124", "fg": "#e8eaed", "field": "#2b2d31", "btn": "#35383d",
        "btn_hot": "#464a50", "border": "#4a4d52", "accent": "#2f6fd6", "hint": "#9aa0a6",
        "off": "#6f737a"}


def run_gui():
    """Build and run the whole window. Everything below (all tabs, players, lists) lives inside this function as closures that share the widgets and the `state` dictionary; the module-level functions above are the pure helpers (ffmpeg commands, yt-dlp, names, settings)."""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    if IS_WIN:  # crisp text on high-DPI screens (window size adapts to content below)
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    root.title(APP_NAME)
    try:  # dropping files onto the window needs the optional package tkinterdnd2
        import tkinterdnd2
        tkinterdnd2.TkinterDnD._require(root)
        dnd_ok = _DND["active"] = True
    except Exception:
        tkinterdnd2, dnd_ok = None, False

    if IS_WIN:
        ico = resource_path("FAUN.ico")
        if not os.path.isfile(ico):
            ico = resource_path("icon.ico")
        if os.path.isfile(ico):
            try:
                root.iconbitmap(ico)
            except Exception:
                pass

    style = ttk.Style()
    for theme in ("aqua", "vista", "clam"):
        if theme in style.theme_names():
            style.theme_use(theme)
            break
    style.configure("Title.TLabel", font=(UI_FONT, 14, "bold"))
    style.configure("Hint.TLabel", foreground="#666")
    style.configure("HintB.TLabel", foreground="#666", font=(UI_FONT, 9, "bold"))
    style.configure("Go.TButton", font=(UI_FONT, 10, "bold"), padding=6)

    state = {"proc": None, "duration": None, "has_video": None, "cancelled": False, "busy": False,
             "gpu_kind": None, "gpu_ready": False, "setup_checked": False,
             "skip": False, "skip_until": 0.0, "batch_running": False}
    src_var = tk.StringVar()
    recent_files = []  # the files opened last, newest first
    tr_vars = []

    class TrVar(tk.StringVar):
        """A text variable that shows Czech when Czech is on, and remembers the English original."""

        def __init__(self, *a, **k):
            """Variable that remembers its English text, so it can be translated again on a language switch."""
            super().__init__(*a, **k)
            self._en = self.get()
            tr_vars.append(self)

        def set(self, value):
            """Set the text (given in English) and show it translated."""
            self._en = value
            super().set(tr(value))

        def retranslate(self):
            """Show the remembered English text in the current language."""
            super().set(tr(self._en))

    class HelpVar(tk.StringVar):
        """Explanatory lines (English originals); shown in Czech when Czech is on."""

        def __init__(self):
            """Variable holding several lines of English text (translated line by line)."""
            super().__init__()
            self._en = []
            tr_vars.append(self)

        def set_lines(self, lines):
            """Set the lines (English) and show them translated."""
            self._en = [x for x in lines if x]
            self.retranslate()

        def retranslate(self):
            """Show all lines in the current language."""
            super().set("\n".join(tr(x) for x in self._en))

    info_hook = {"show": lambda path, force=False: None}  # filled in where the bottom panel is built

    class HelpBox(ttk.Frame):
        """Explanations 'Name – what it does', one line per ticked option, in a small box that scrolls
        by itself, so many ticked options never make the whole window taller."""

        def __init__(self, parent, wrap=800, lines=4):
            """The scrollable help box: a Text widget with a scrollbar that appears only when the content needs it."""
            super().__init__(parent)
            self.items, self.max_lines = [], lines
            self.columnconfigure(0, weight=1)
            self.txt = tk.Text(self, height=1, width=max(40, int(wrap / 7.2)), wrap="word", relief="flat",
                               borderwidth=0, highlightthickness=1, padx=6, pady=3, cursor="arrow",
                               takefocus=0, font=(UI_FONT, 9), state="disabled")
            self.sb = ttk.Scrollbar(self, orient="vertical", command=self.txt.yview)
            self.txt.configure(yscrollcommand=self._sb_set)
            self.txt.grid(row=0, column=0, sticky="ew")
            tr_vars.append(self)

        def _sb_set(self, first, last):
            """Scrollbar callback: show the scrollbar only if the text does not fit."""
            self.sb.set(first, last)
            try:
                if float(first) <= 0.0 and float(last) >= 1.0:
                    self.sb.grid_remove()
                else:
                    self.sb.grid(row=0, column=1, sticky="ns")
            except (ValueError, tk.TclError):
                pass

        def set_items(self, items):
            """Replace the (name, description) items shown; redraw only if they changed."""
            new = [tuple(x) for x in items if x]
            if new != self.items:
                self.items = new
                self.retranslate()

        def _colours(self):
            """Colours of the box for the current theme: background, text, name, border."""
            try:
                dark = IS_WIN and dark_var.get()
            except NameError:
                dark = False
            if IS_WIN:
                bg, fg, name_fg, edge = ((DARK["field"], DARK["hint"], DARK["fg"], DARK["border"]) if dark
                                         else ("SystemWindow", "#666666", "#222222", "#c8c8c8"))
            else:  # macOS / Linux: the field colours follow the system look by themselves
                bg, fg, name_fg, edge = None, "#808080", None, "#b5b5b5"
            return bg, fg, name_fg, edge

        def retranslate(self):
            """Rewrite the text of the box in the current language, and size it (up to the maximum lines)."""
            bg, fg, name_fg, edge = self._colours()
            t_ = self.txt
            t_.config(state="normal")
            t_.delete("1.0", "end")
            t_.tag_configure("name", font=(UI_FONT, 9, "bold"))
            t_.tag_configure("desc")
            if name_fg:
                t_.tag_configure("name", foreground=name_fg)
            t_.tag_configure("desc", foreground=fg)
            if bg:
                t_.config(bg=bg)
            t_.config(highlightbackground=edge, highlightcolor=edge)
            for n_, (name_, text_) in enumerate(self.items):
                if n_:
                    t_.insert("end", "\n")
                if name_:
                    t_.insert("end", tr(name_) + "  –  ", "name")
                t_.insert("end", tr(text_), "desc")
            t_.config(state="disabled")
            if not self.items:
                t_.grid_remove()
                self.sb.grid_remove()
                return
            t_.grid(row=0, column=0, sticky="ew")
            n_lines = 1
            try:
                self.update_idletasks()
                c_ = t_.count("1.0", "end", "displaylines")
                n_lines = int(c_[0]) if c_ else 1
            except (tk.TclError, TypeError, ValueError, IndexError):
                n_lines = len(self.items)
            t_.config(height=max(1, min(self.max_lines, n_lines)))
            t_.yview_moveto(0)

    info_var = TrVar(value="No file selected")
    status_var = TrVar(value="Ready")
    clean_var = tk.BooleanVar(value=False)           # one naming setting for the whole app
    cover_var = tk.BooleanVar(value=False)           # embed cover art in mp3 / m4a files
    strip_tags_var = tk.BooleanVar(value=True)
    extra_tags_var = tk.StringVar(value="")          # your own phrases, comma-separated

    # The whole window content sits in a scrollable area, so it stays usable on small screens.
    outer = ttk.Frame(root)
    outer.pack(fill="both", expand=True)
    scroll_cv = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
    vbar = ttk.Scrollbar(outer, orient="vertical", command=scroll_cv.yview)
    hbar = ttk.Scrollbar(outer, orient="horizontal", command=scroll_cv.xview)
    scroll_cv.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(0, weight=1)
    scroll_cv.grid(row=0, column=0, sticky="nsew")
    vbar.grid(row=0, column=1, sticky="ns")
    hbar.grid(row=1, column=0, sticky="ew")
    vbar.grid_remove()
    hbar.grid_remove()
    main = ttk.Frame(scroll_cv, padding=14)
    main_win = scroll_cv.create_window(0, 0, window=main, anchor="nw")
    bars = {"v": False, "h": False}

    def fit_scroll_area(_event=None):
        """Size the content to at least the window, show scrollbars only when something is cut off."""
        ow, oh = outer.winfo_width(), outer.winfo_height()
        if ow < 50 or oh < 50:
            return
        rw, rh = main.winfo_reqwidth(), main.winfo_reqheight()
        bw, bh = vbar.winfo_reqwidth(), hbar.winfo_reqheight()
        need_v, need_h = rh > oh, rw > ow
        if need_v:
            need_h = rw > ow - bw
        if need_h:
            need_v = rh > oh - bh
        vw = ow - (bw if need_v else 0)
        vh = oh - (bh if need_h else 0)
        if need_h != bars["h"]:
            bars["h"] = need_h
            hbar.grid() if need_h else hbar.grid_remove()
        if need_v != bars["v"]:
            bars["v"] = need_v
            vbar.grid() if need_v else vbar.grid_remove()
        cw, ch = max(vw, rw), max(vh, rh)
        scroll_cv.itemconfigure(main_win, width=cw, height=ch)
        scroll_cv.configure(scrollregion=(0, 0, cw, ch))

    outer.bind("<Configure>", fit_scroll_area)
    main.bind("<Configure>", fit_scroll_area)

    def on_wheel(e):
        """Mouse wheel scrolls the whole window, except over widgets that scroll themselves."""
        try:
            if e.widget.winfo_toplevel() is not root:
                return
            if e.widget.winfo_class() in ("Treeview", "Text", "Listbox", "TCombobox", "TScale"):
                return  # these scroll themselves
        except tk.TclError:
            return
        if e.num == 4 or e.delta > 0:
            n = -1
        elif e.num == 5 or e.delta < 0:
            n = 1
        else:
            return
        if IS_MAC and e.delta:
            n = -e.delta
        shift = bool(e.state & 0x1)
        (scroll_cv.xview_scroll if shift else scroll_cv.yview_scroll)(n, "units")

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.bind_all(seq, on_wheel, add="+")

    dark_var = tk.BooleanVar(value=windows_prefers_dark())
    f_title = ttk.Frame(main)
    f_title.pack(fill="x")
    ttk.Label(f_title, text=APP_NAME, style="Title.TLabel").pack(side="left")
    lang_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(f_title, text="Čeština", variable=lang_var,
                    command=lambda: apply_language()).pack(side="right")
    if IS_WIN:  # macOS follows the system look by itself; Windows needs this switch
        ttk.Checkbutton(f_title, text="Dark mode", variable=dark_var,
                        command=lambda: apply_theme(dark_var.get())).pack(side="right", padx=(0, 12))

    # --- input file
    f_in = ttk.Frame(main)
    f_in.pack(fill="x", pady=(10, 2))
    # the buttons are placed first (at the right edge) and the text box takes whatever room is left,
    # so longer button texts (Czech) make the box shorter instead of making the window wider
    recent_btn = ttk.Button(f_in, text="Recent ▾", command=lambda: recent_menu())
    recent_btn.pack(side="right", padx=(4, 0))
    ttk.Button(f_in, text="Open file…", command=lambda: browse()).pack(side="right", padx=(6, 0))
    src_entry = ttk.Entry(f_in, textvariable=src_var, width=1)
    src_entry.pack(side="left", fill="x", expand=True)
    ttk.Label(main, textvariable=info_var, style="Hint.TLabel").pack(anchor="w")

    # --- task tabs
    nb = ttk.Notebook(main)
    nb.pack(fill="both", expand=True, pady=(10, 0))

    TAB_CZ = {"Quick download": "Stažení", "Batch download": "Dávka", "Extract audio": "Získat zvuk",
              "Remove audio": "Bez zvuku"}
    tab_en = {}  # tab widget -> its English name (what the code compares with)

    def tab(name):
        """Create a tab of the notebook and remember its English name."""
        fr = ttk.Frame(nb, padding=12)
        nb.add(fr, text=name)
        tab_en[str(fr)] = name
        return fr

    def row(parent, r, label, widget):
        """Place a label and its widget on one row of a tab."""
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 10))
        widget.grid(row=r, column=1, sticky="w", pady=4)

    def hint(parent, r, text):
        """Place a small grey explanation text under the controls of a tab."""
        ttk.Label(parent, text=text, style="Hint.TLabel", justify="left").grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def combo(parent, var, values, width=22):
        """A read-only dropdown."""
        return ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=width)

    # Setup (install / verify / update tools)
    t = tab("Setup")
    tool_status = {k: TrVar(value="—") for k in ("pm", "ffmpeg", "ytdlp", "mpv", "deno", "dnd")}
    setup_btns = []
    mono = "Menlo" if IS_MAC else ("Consolas" if IS_WIN else "DejaVu Sans Mono")
    rows = (("pm", "Chocolatey" if IS_WIN else "Homebrew"), ("ffmpeg", "ffmpeg"), ("ytdlp", "yt-dlp"),
            ("mpv", "mpv  (player: pause, timeline)"), ("deno", "deno  (YouTube for yt-dlp)"),
            ("dnd", "tkinterdnd2  (drag & drop of files)"))
    for i, (key, label) in enumerate(rows):
        ttk.Label(t, text=label).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 10))
        ttk.Label(t, textvariable=tool_status[key], width=34).grid(
            row=i, column=1, sticky="w", padx=(0, 10))
        for c, (txt, act) in enumerate((("Install", "install"), ("Verify", "verify"),
                                        ("Update", "update")), start=2):
            b = ttk.Button(t, text=txt, width=8, command=lambda k=key, a=act: tool_action(k, a))
            b.grid(row=i, column=c, padx=2, pady=2)
            setup_btns.append(b)
    b_all = ttk.Button(t, text="Verify all", command=lambda: verify(list(tool_status), True))
    b_all.grid(row=6, column=2, columnspan=3, sticky="e", pady=(4, 0))
    setup_btns.append(b_all)
    f_log = ttk.Frame(t)
    f_log.grid(row=7, column=0, columnspan=5, sticky="nsew", pady=(8, 0))
    log_text = tk.Text(f_log, height=6, width=74, wrap="word", state="disabled",
                       font=(mono, 9))
    log_sb = ttk.Scrollbar(f_log, command=log_text.yview)
    log_text.config(yscrollcommand=log_sb.set)
    log_sb.pack(side="right", fill="y")
    log_text.pack(side="left", fill="both", expand=True)
    ttk.Label(t, text=("Install / Update open an administrator window (Windows will ask for approval).\n"
                       "Press Verify afterwards to refresh the status." if IS_WIN else
                       "Homebrew installs in a Terminal window (it asks for your Mac password).\n"
                       "ffmpeg, yt-dlp, mpv and deno install here; the output is shown above."),
              style="Hint.TLabel", justify="left").grid(
        row=8, column=0, columnspan=5, sticky="w", pady=(6, 0))

    setup_tab = t
    t.columnconfigure(5, weight=1)
    about_area = ttk.Frame(t)  # the free space right of the tools: the about card is built further down
    about_area.grid(row=0, column=5, rowspan=10, sticky="nsew", padx=(30, 0))
    t.rowconfigure(9, weight=1)  # an empty last row takes the spare height, so the area is as tall as the tab
    about_below = ttk.Frame(t)  # the free space under the tools: used when there is no room at the right
    about_below.grid(row=9, column=0, columnspan=6, sticky="nsew")

    # Download (yt-dlp)
    download_tab = t = tab("Quick download")
    url_var = tk.StringVar()
    dl_dir_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
    dl_q_var = tk.StringVar(value=list(DL_QUALITY)[0])
    sec_start_var, sec_end_var = tk.StringVar(), tk.StringVar()
    exact_var = tk.BooleanVar(value=False)
    f_url = ttk.Frame(t)
    ttk.Entry(f_url, textvariable=url_var, width=38).pack(side="left")
    ttk.Button(f_url, text="Paste", width=7, command=lambda: paste_url()).pack(
        side="left", padx=(6, 0))
    ttk.Button(f_url, text="Clear", width=7, command=lambda: url_var.set("")).pack(
        side="left", padx=(4, 0))
    retry_btn = ttk.Button(f_url, text="Retry", width=7, state="disabled", command=lambda: quick_retry())
    retry_btn.pack(side="left", padx=(4, 0))
    auto_retry_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(f_url, text="Keep retrying", variable=auto_retry_var,
                    command=lambda: auto_retry_changed()).pack(side="left", padx=(8, 0))
    row(t, 0, "Video link", f_url)
    row(t, 1, "Quality", combo(t, dl_q_var, list(DL_QUALITY)))
    f_dir = ttk.Frame(t)
    ttk.Entry(f_dir, textvariable=dl_dir_var, width=40).pack(side="left")
    ttk.Button(f_dir, text="Choose…", command=lambda: choose_dir()).pack(side="left", padx=(6, 0))
    row(t, 2, "Save to", f_dir)
    f_sec = ttk.Frame(t)
    ttk.Entry(f_sec, textvariable=sec_start_var, width=10).pack(side="left")
    ttk.Label(f_sec, text="  to  ").pack(side="left")
    ttk.Entry(f_sec, textvariable=sec_end_var, width=10).pack(side="left")
    ttk.Checkbutton(f_sec, text="Exact cut (slower)", variable=exact_var).pack(
        side="left", padx=(12, 0))
    row(t, 3, "Only part (optional)", f_sec)
    quick_help = HelpBox(t)
    quick_help.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def update_quick_help(*_):
        """Update the help box of the Quick download tab to match the ticked options."""
        quick_help.set_items([
            ("", "One video per link. Leave 'Only part' empty to download all of it (examples: 1:30 to 2:45, or just a start / just an end). "
                 "A playlist link goes to the Batch download tab."),
            ("Keep retrying", "If the connection drops or the site refuses, the download is tried again by itself.")
            if auto_retry_var.get() else None,
            ("Exact cut", "Re-encodes the part so it starts and ends exactly at your times (slower).")
            if exact_var.get() else None])

    auto_retry_var.trace_add("write", update_quick_help)
    exact_var.trace_add("write", update_quick_help)
    update_quick_help()

    # the link started on this tab: a single row (same columns as the Batch list)
    f_qd = ttk.Frame(t)
    f_qd.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    t.columnconfigure(1, weight=1)  # the box grows with the window
    qd_tree = ttk.Treeview(f_qd, columns=("type", "item", "status"), show="headings",
                           height=1, selectmode="browse")
    qd_tree.heading("type", text="Type")
    qd_tree.heading("item", text="Item")
    qd_tree.heading("status", text="Status")
    qd_tree.column("type", width=60, stretch=False)
    qd_tree.column("item", width=440, stretch=True)      # takes any extra width
    qd_tree.column("status", width=300, stretch=False)
    qd_tree.pack(side="left", fill="x", expand=True)

    split_trees = []

    def split_columns(tv, fixed, event=None):
        """Item and Status share the room 50 / 50. The room comes from the WINDOW width, not from the
        list itself: a list's own width is the sum of its columns, so measuring that would make the
        window unable to shrink again after it has been wide (e.g. on a bigger monitor)."""
        try:
            free = outer.winfo_width() - 130 - fixed
            if free > 300:
                tv.column("item", width=free // 2, stretch=False)
                tv.column("status", width=free - free // 2, stretch=False)
        except tk.TclError:
            pass

    def split_all(event=None):
        """Re-split the Item / Status columns of the lists after the window size changed."""
        for tv_, fx_ in split_trees:
            split_columns(tv_, fx_)
    outer.bind("<Configure>", lambda e: split_all(), add="+")
    split_trees.append((qd_tree, 60))
    split_all()
    qd_tree.bind("<Double-1>", lambda e: qd_show_error())

    # Browse (search YouTube / list pages of other sites, with thumbnails)
    browse_tab = t = tab("Browse")
    t.columnconfigure(0, weight=1)
    t.rowconfigure(1, weight=1)
    br_query_var = tk.StringVar()
    br_status_var = status_var  # Browse messages use the status line at the bottom of the window
    br = {"gen": 0, "rows": {}, "query": "", "count": 0, "imgs": {}, "big": {}, "loading": False,
          "more": True, "hist": [], "live_n": 0}
    br_section_var = tk.StringVar(value="Videos")
    br_kind_var = tk.StringVar(value="Videos")
    f_bq = ttk.Frame(t)
    f_bq.grid(row=0, column=0, sticky="ew")
    br_entry = ttk.Entry(f_bq, textvariable=br_query_var)
    br_entry.pack(fill="x")
    f_bq2 = ttk.Frame(f_bq)
    f_bq2.pack(fill="x", pady=(6, 0))
    br_site_var = tk.StringVar(value="YouTube")
    ttk.Label(f_bq2, text="Search on:").pack(side="left")
    br_site_combo = combo(f_bq2, br_site_var, list(BROWSE_SITES), 12)
    br_site_combo.pack(side="left", padx=(4, 0))
    ttk.Button(f_bq2, text="Sites…", width=6, command=lambda: browse_sites_dialog()).pack(
        side="left", padx=(4, 0))
    ttk.Label(f_bq2, text="Search for:").pack(side="left", padx=(14, 0))
    br_kind_combo = combo(f_bq2, br_kind_var, list(BROWSE_KINDS), 9)
    br_kind_combo.pack(side="left", padx=(4, 0))
    ttk.Label(f_bq2, text="Channel shows:").pack(side="left", padx=(14, 0))
    br_section_combo = combo(f_bq2, br_section_var, list(BROWSE_SECTIONS), 9)
    br_section_combo.pack(side="left", padx=(4, 0))
    br_kind_combo.bind("<<ComboboxSelected>>", lambda e: browse_kind_changed())
    br_site_combo.bind("<<ComboboxSelected>>", lambda e: browse_site_changed())
    br_search_btn = ttk.Button(f_bq2, text="Search", width=7, command=lambda: browse_search())
    br_search_btn.pack(side="left", padx=(16, 0))
    ttk.Button(f_bq2, text="Paste", width=6, command=lambda: browse_paste()).pack(side="left", padx=(4, 0))
    br_back_btn = ttk.Button(f_bq2, text="◀ Back", width=6, state="disabled", command=lambda: browse_back())
    br_back_btn.pack(side="left", padx=(4, 0))

    f_bq3 = ttk.Frame(f_bq)  # my YouTube account (login taken from a browser)
    f_bq3.pack(fill="x", pady=(6, 0))
    yt_browser_var = tk.StringVar(value="None")
    yt_feed_var = tk.StringVar(value="Recommended")
    ttk.Label(f_bq3, text="My YouTube – signed in with:").pack(side="left")
    yt_browser_combo = combo(f_bq3, yt_browser_var, YT_BROWSERS, 10)
    yt_browser_combo.pack(side="left", padx=(4, 0))
    ttk.Label(f_bq3, text="Show:").pack(side="left", padx=(14, 0))
    combo(f_bq3, yt_feed_var, list(YT_FEEDS), 24).pack(side="left", padx=(4, 0))
    ttk.Button(f_bq3, text="Open", width=6, command=lambda: yt_open_feed()).pack(side="left", padx=(8, 0))
    yt_browser_combo.bind("<<ComboboxSelected>>", lambda e: yt_browser_set())

    f_bmid = ttk.Frame(t)
    f_bmid.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
    f_bmid.columnconfigure(0, weight=3)
    f_bmid.columnconfigure(1, weight=2)
    f_bmid.rowconfigure(0, weight=1)
    style.configure("Browse.Treeview", rowheight=78)
    f_bl = ttk.Frame(f_bmid)
    f_bl.grid(row=0, column=0, sticky="nsew")
    br_tree = ttk.Treeview(f_bl, columns=("title", "live", "channel", "len", "views"), height=3, selectmode="extended",
                           style="Browse.Treeview")
    br_tree.heading("#0", text="")
    br_tree.heading("title", text="Title")
    br_tree.heading("live", text="Live")
    br_tree.heading("channel", text="Channel")
    br_tree.heading("len", text="Length")
    br_tree.heading("views", text="Views")
    br_tree.column("#0", width=140, stretch=False)
    br_tree.column("title", width=240, stretch=True)
    br_tree.column("live", width=62, stretch=False, anchor="center")
    br_tree.column("channel", width=110, stretch=False)
    br_tree.column("len", width=60, stretch=False, anchor="e")
    br_tree.column("views", width=60, stretch=False, anchor="e")
    br_sb = ttk.Scrollbar(f_bl, command=br_tree.yview)
    br_tree.config(yscrollcommand=br_sb.set)
    br_sb.pack(side="right", fill="y")
    br_tree.pack(side="left", fill="both", expand=True)
    f_bd = ttk.Frame(f_bmid)
    f_bd.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    f_bd.rowconfigure(3, weight=1)
    f_bd.columnconfigure(0, weight=1)
    br_big = ttk.Label(f_bd, anchor="center")
    br_big.grid(row=0, column=0, sticky="ew")
    br_title_var = tk.StringVar()
    ttk.Label(f_bd, textvariable=br_title_var, wraplength=290, justify="left",
              font=(UI_FONT, 10, "bold")).grid(row=1, column=0, sticky="w", pady=(6, 0))
    br_meta_var = tk.StringVar()
    ttk.Label(f_bd, textvariable=br_meta_var, style="Hint.TLabel", wraplength=290,
              justify="left").grid(row=2, column=0, sticky="w")
    f_bdesc = ttk.Frame(f_bd)
    f_bdesc.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
    br_desc = tk.Text(f_bdesc, height=3, width=36, wrap="word", state="disabled", font=(UI_FONT, 9))
    br_dsb = ttk.Scrollbar(f_bdesc, command=br_desc.yview)
    br_desc.config(yscrollcommand=br_dsb.set)
    br_dsb.pack(side="right", fill="y")
    br_desc.pack(side="left", fill="both", expand=True)

    f_bb2 = ttk.Frame(t)
    f_bb2.grid(row=2, column=0, sticky="ew", pady=(8, 0))
    f_bb2a = ttk.Frame(f_bb2)  # two rows of buttons: the player controls, then what to do with the video
    f_bb2a.pack(fill="x")
    f_bb2b = ttk.Frame(f_bb2)
    f_bb2b.pack(fill="x", pady=(4, 0))
    br_play_btn = ttk.Button(f_bb2a, text="Play", width=8, command=lambda: browse_play())
    br_play_btn.pack(side="left")
    br_pause_btn = ttk.Button(f_bb2a, text="Pause", width=8, state="disabled",
                              command=lambda: browse_pause())
    br_pause_btn.pack(side="left", padx=(4, 0))
    br_stop_btn = ttk.Button(f_bb2a, text="Stop", width=6, state="disabled",
                             command=lambda: browse_stop())
    br_stop_btn.pack(side="left", padx=(4, 0))
    br_prev_btn = ttk.Button(f_bb2a, text="◀ Prev", width=7, state="disabled",
                             command=lambda: browse_play_next(True, -1))
    br_prev_btn.pack(side="left", padx=(4, 0))
    br_next_btn = ttk.Button(f_bb2a, text="Next ▶", width=8, state="disabled",
                             command=lambda: browse_play_next(True))
    br_next_btn.pack(side="left", padx=(4, 0))
    br_auto_var = tk.BooleanVar(value=True)  # always on: the next video of the list plays when one ends
    br_audio_var = tk.BooleanVar(value=False)
    br_dl_btn = ttk.Button(f_bb2b, text="Download", width=10, command=lambda: browse_to_quick())
    br_dl_btn.pack(side="left")
    br_batch_btn = ttk.Button(f_bb2b, text="Add to batch", width=12, command=lambda: browse_to_batch())
    br_batch_btn.pack(side="left", padx=(4, 0))
    br_copy_btn = ttk.Button(f_bb2b, text="Copy link", width=10, command=lambda: browse_copy())
    br_copy_btn.pack(side="left", padx=(4, 0))
    br_web_btn = ttk.Button(f_bb2b, text="Open in browser", width=15, command=lambda: browse_open_web())
    br_web_btn.pack(side="left", padx=(4, 0))  # save it to Watch later / a playlist on the site itself
    br_more_btn = ttk.Button(f_bb2a, text="Load more", width=10, state="disabled",
                             command=lambda: browse_more())
    br_more_btn.pack(side="right")
    f_bt = ttk.Frame(t)  # position bar of what is playing: click or drag to jump
    f_bt.grid(row=3, column=0, sticky="ew", pady=(6, 0))
    br_pos_lbl = ttk.Label(f_bt, text="0:00", width=7, anchor="e")
    br_pos_lbl.pack(side="left")
    br_scale = ttk.Scale(f_bt, from_=0, to=1, orient="horizontal")
    br_scale.pack(side="left", fill="x", expand=True, padx=8)
    br_dur_lbl = ttk.Label(f_bt, text="0:00", width=7)
    br_dur_lbl.pack(side="left")
    br_vis_var = tk.BooleanVar(value=False)       # trippy patterns drawn from the playing audio
    br_vis_style_var = tk.StringVar(value="Fractal")
    ttk.Checkbutton(f_bt, text="Visualizer", variable=br_vis_var,
                    command=lambda: browse_vis_changed()).pack(side="left", padx=(12, 0))
    br_vis_combo = combo(f_bt, br_vis_style_var, list(VIS_STYLES), 14)
    br_vis_combo.pack(side="left", padx=(4, 0))
    br_vis_combo.bind("<<ComboboxSelected>>", lambda e: browse_vis_changed())
    br_scale.state(["disabled"])
    br_actions = (br_play_btn, br_dl_btn, br_batch_btn, br_copy_btn, br_web_btn)
    br_entry.bind("<Return>", lambda e: browse_search())
    nb.insert(nb.index(download_tab), browse_tab)  # Browse sits before Quick download

    # Batch
    batch_tab = t = tab("Batch download")
    t.columnconfigure(0, weight=1)
    t.rowconfigure(2, weight=1)
    batch_step_vars = {s: (clean_var if s == "Clean name"
                           else tk.BooleanVar(value=(s in ("Download", "Loudness")))) for s in BATCH_STEPS}
    batch_save_var = tk.StringVar(value=dl_dir_var.get())  # Batch has its own "Save to"
    batch_out_var = tk.StringVar(value="")
    batch_out_text = tk.StringVar(value="")
    batch_del_var = tk.BooleanVar(value=True)
    batch_split_var = tk.BooleanVar(value=False)  # processed files in a folder of their own
    numbering_var = tk.BooleanVar(value=False)       # number downloaded files in list order
    skip_known_var = tk.BooleanVar(value=True)       # skip videos downloaded in an earlier session

    f_top = ttk.Frame(t)
    f_top.grid(row=0, column=0, sticky="w")
    ttk.Label(f_top, text="Steps:").pack(side="left", padx=(0, 8))
    batch_step_cbs = {}
    for s_ in BATCH_STEPS:
        batch_step_cbs[s_] = ttk.Checkbutton(f_top, text=s_, variable=batch_step_vars[s_])
        batch_step_cbs[s_].pack(side="left", padx=(0, 8))

    f_bb = ttk.Frame(t)
    f_bb.grid(row=1, column=0, sticky="ew", pady=(8, 6))
    skip_btn = ttk.Button(f_bb, text="Skip current item", state="disabled",
                          command=lambda: batch_skip())
    skip_btn.pack(side="right")  # only active while a batch is running
    for text_, cmd_ in (("Add files…", lambda: batch_add_files()),
                        ("Paste links", lambda: batch_paste_links()),
                        ("Remove selected", lambda: batch_remove()),
                        ("Clear all", lambda: batch_clear()),
                        ("Redo all", lambda: batch_redo()),
                        ("Retry failed", lambda: batch_retry_failed()),
                        ("Retry skipped", lambda: batch_retry_skipped())):
        b_ = ttk.Button(f_bb, text=text_, command=cmd_)
        b_.pack(side="left", padx=(0, 6))
        setup_btns.append(b_)  # disabled while a job runs, like the Setup buttons
    ttk.Checkbutton(f_bb, text="Keep retrying", variable=auto_retry_var).pack(
        side="left", padx=(2, 0))  # same setting as on Quick download

    f_tree = ttk.Frame(t)
    f_tree.grid(row=2, column=0, sticky="nsew")
    tree = ttk.Treeview(f_tree, columns=("type", "item", "status"), show="headings",
                        height=7, selectmode="extended")
    tree.heading("type", text="Type")
    tree.heading("item", text="Item")
    tree.heading("status", text="Status")
    tree.column("type", width=55, stretch=False)
    tree.column("item", width=340)
    tree.column("status", width=260, stretch=False)
    split_trees.append((tree, 55))
    split_all()
    tree_sb = ttk.Scrollbar(f_tree, command=tree.yview)
    tree.config(yscrollcommand=tree_sb.set)
    tree_sb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    tree.bind("<Double-1>", lambda e: batch_show_error())

    def batch_row_selected(_e=None):
        """A batch row was selected: show the cover and tags of its file (if it is a file on disk)."""
        sel_ = tree.selection()
        if not sel_:
            sel_ = tree.focus() and (tree.focus(),) or ()
        for iid_ in sel_[:1]:
            for it_ in batch_items:
                if it_["iid"] == iid_:
                    cands_ = [it_.get("file"), it_.get("output"), it_.get("base"),
                              it_["value"] if it_["kind"] == "file" else None]
                    for p_ in cands_:
                        if p_ and os.path.isfile(p_):
                            info_hook["show"](p_)
                            return
    tree.bind("<<TreeviewSelect>>", batch_row_selected, add="+")
    tree.bind("<ButtonRelease-1>", lambda e: root.after(50, batch_row_selected), add="+")
    tree.bind("<KeyRelease-Up>", lambda e: root.after(50, batch_row_selected), add="+")
    tree.bind("<KeyRelease-Down>", lambda e: root.after(50, batch_row_selected), add="+")

    f_out = ttk.Frame(t)
    f_out.grid(row=3, column=0, sticky="w", pady=(8, 0))
    batch_dl_note = TrVar()
    batch_out_note = TrVar()
    prefix_var = tk.StringVar(value="")  # not remembered: it belongs to one batch (e.g. one band)
    album_var = tk.StringVar(value="")   # the Album tag: also belongs to one batch
    ttk.Label(f_out, text="Add to start of names").grid(row=0, column=0, sticky="w", pady=2)
    prefix_entry = ttk.Entry(f_out, textvariable=prefix_var, width=46)
    prefix_entry.grid(row=0, column=1, padx=(8, 6), pady=2)
    numbering_cb = ttk.Checkbutton(f_out, text="Number files (01, 02…)", variable=numbering_var)
    numbering_cb.grid(row=0, column=2, columnspan=3, padx=(8, 0), sticky="w")
    ttk.Label(f_out, text="Album (tag)").grid(row=1, column=0, sticky="w", pady=2)
    album_entry = ttk.Entry(f_out, textvariable=album_var, width=46)
    album_entry.grid(row=1, column=1, padx=(8, 6), pady=2)
    ttk.Label(f_out, text="Empty: the name of the folder · Artist and title: from the name (Artist - Title) or the text above",
              style="Hint.TLabel").grid(row=1, column=2, columnspan=3, padx=(8, 0), sticky="w")
    ttk.Label(f_out, text="Download quality").grid(row=2, column=0, sticky="w", pady=2)
    # the very same setting as "Quality" on the Download tab (shared variable)
    dl_quality_combo = combo(f_out, dl_q_var, list(DL_QUALITY), 44)
    dl_quality_combo.grid(row=2, column=1, padx=(8, 6), pady=2, sticky="w")
    ttk.Label(f_out, text="Save to").grid(row=3, column=0, sticky="w", pady=2)
    dl_entry = ttk.Entry(f_out, textvariable=batch_save_var, width=46)
    dl_entry.grid(row=3, column=1, padx=(8, 6), pady=2)
    dl_choose = ttk.Button(f_out, text="Choose…", command=lambda: batch_choose_save())
    dl_choose.grid(row=3, column=2, pady=2)
    ttk.Label(f_out, textvariable=batch_dl_note, style="Hint.TLabel").grid(
        row=3, column=3, padx=(8, 0), sticky="w")
    split_cb = ttk.Checkbutton(f_out, text="Keep processed files in a different folder",
                               variable=batch_split_var, command=lambda: apply_batch_row_state())
    split_cb.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))
    out_label = ttk.Label(f_out, text="Processed files go to")
    out_label.grid(row=5, column=0, sticky="w", pady=2)
    out_entry = ttk.Entry(f_out, textvariable=batch_out_text, width=46, state="readonly")
    out_entry.grid(row=5, column=1, padx=(8, 6), pady=2)
    out_choose = ttk.Button(f_out, text="Choose…", command=lambda: batch_choose_out())
    out_choose.grid(row=5, column=2, pady=2)
    out_note_lbl = ttk.Label(f_out, textvariable=batch_out_note, style="Hint.TLabel")
    out_note_lbl.grid(
        row=5, column=4, padx=(8, 0), sticky="w")
    f_opts = ttk.Frame(t)
    f_opts.grid(row=4, column=0, sticky="w", pady=(6, 0))
    del_cb = ttk.Checkbutton(f_opts, text="Delete the original once it has been processed",
                             variable=batch_del_var)
    del_cb.pack(side="left")
    known_cb = ttk.Checkbutton(f_opts, text="Skip videos I've already downloaded", variable=skip_known_var)
    known_cb.pack(side="left", padx=(16, 0))
    forget_btn = ttk.Button(f_opts, text="Forget history…", command=lambda: forget_downloads())
    forget_btn.pack(side="left", padx=(8, 0))
    setup_btns.append(forget_btn)

    def apply_batch_row_state(*_):
        """Grey out whatever the ticked steps don't use."""
        steps = [s for s, v in batch_step_vars.items() if v.get()]
        downloading = "Download" in steps
        processing = any(s not in ("Download", "Clean name", "Write tags") for s in steps)
        naming = "Clean name" in steps
        tagging = "Write tags" in steps
        idle = not state["busy"]
        dl_on, out_on = downloading and idle, processing and idle
        name_on = (downloading or tagging) and idle
        dl_entry.config(state="normal" if idle else "disabled")  # always usable between batches
        dl_choose.config(state="normal" if idle else "disabled")
        dl_quality_combo.config(state="readonly" if dl_on else "disabled")
        prefix_entry.config(state="normal" if name_on else "disabled")
        album_entry.config(state="normal" if tagging and idle else "disabled")
        numbering_cb.config(state="normal" if name_on else "disabled")
        known_cb.config(state="normal" if dl_on else "disabled")
        can_skip = state["busy"] and state["batch_running"] and time.time() >= state["skip_until"]
        skip_btn.config(state="normal" if can_skip else "disabled")
        for w_ in (out_label, out_entry, out_choose, out_note_lbl):  # only with the checkbox ticked
            (w_.grid if batch_split_var.get() else w_.grid_remove)()
        out_entry.config(state="readonly" if out_on else "disabled")
        out_choose.config(state="normal" if out_on else "disabled")
        del_cb.config(state="normal" if ((processing or naming) and idle) else "disabled")
        strip_cb.config(state="normal" if (naming and idle) else "disabled")
        extra_on = naming and idle and strip_tags_var.get()
        extra_entry.config(state="normal" if extra_on else "disabled")
        batch_dl_note.set("")
        batch_out_note.set("" if processing else "not used by the ticked steps")
        ticked = set(steps)
        for st_, cb_ in batch_step_cbs.items():
            blocked = (not batch_step_vars[st_].get()) and bool(STEP_CONFLICTS.get(st_, set()) & ticked)
            cb_.config(state="normal" if (idle and not blocked) else "disabled")

    def resolve_step_conflicts():
        """Settings saved earlier may tick steps that can't go together: keep the earlier step."""
        kept = set()
        for st_ in BATCH_STEPS:
            if batch_step_vars[st_].get():
                if STEP_CONFLICTS.get(st_, set()) & kept:
                    batch_step_vars[st_].set(False)
                else:
                    kept.add(st_)

    for v_ in list(batch_step_vars.values()) + [strip_tags_var]:
        v_.trace_add("write", apply_batch_row_state)

    batch_help = HelpBox(t, 840)
    batch_help.grid(row=5, column=0, sticky="w", pady=(6, 0))
    STEP_HELP = {
        "Download": "Saves each link in the quality chosen below. A playlist link becomes one row per video.",
        "Convert": "Changes the format and codec, as set on the Convert tab.",
        "Compress": "Makes the file smaller (quality, resolution and target size from the Compress tab).",
        "Remove audio": "Saves the video without sound. Can't be combined with Loudness or Extract audio.",
        "Extract audio": "Keeps only the sound, in the format from the Extract audio tab.",
        "Loudness": "Sets every file to the same volume (level from the Loudness tab); only the sound is re-encoded.",
        "Clean name": "Tidies the file name. Needs a free name: use a separate 'Processed files go to' folder or tick 'Delete the original'.",
        "Write tags": "Writes Artist (from 'Artist - Title' in the name, or the text from 'Add to start of names'), Title, Album (your text, else the name of the folder) and Track number into the files."}

    def update_batch_help(*_):
        """Update the help box of the Batch tab: what each ticked step does."""
        ticked_ = [s_ for s_ in BATCH_STEPS if batch_step_vars[s_].get()]
        items = [("", "Each item goes through the ticked steps in order, and only the final file is kept; finished steps are skipped."
                  if ticked_ else "Tick the steps you want to run.")]
        items += [(s_, STEP_HELP[s_]) for s_ in ticked_ if s_ in STEP_HELP]
        if prefix_var.get().strip():
            items.append(("Add to start of names", "'Band' gives 'Band - Song'."))
        if numbering_var.get():
            items.append(("Number files", "Gives '01 - Band - Song' (in list order)."))
        if batch_del_var.get():
            items.append(("Delete the original", "Removed once the processed copy is saved."))
        if skip_known_var.get():
            items.append(("Skip videos I've already downloaded", "They are left out (Forget history… resets that)."))
        batch_help.set_items(items)

    for v_ in list(batch_step_vars.values()) + [numbering_var, batch_del_var, skip_known_var, prefix_var]:
        v_.trace_add("write", update_batch_help)
    update_batch_help()

    def update_batch_out():
        """Show the chosen folder for processed files (shortened) in its read-only box."""
        d = batch_out_var.get().strip()
        batch_out_text.set(("…" + d[-35:]) if len(d) > 36 else d) if d else \
            batch_out_text.set("")

    # Trim
    trim_tab = t = tab("Trim")
    start_var, end_var = tk.StringVar(value="00:00:00"), tk.StringVar(value="00:00:10")
    precise_var = tk.BooleanVar()
    t.columnconfigure(1, weight=1)

    # timeline with a start and an end marker (and, while previewing in mpv, the playhead)
    tl = {"pos": None, "drag": None, "proc": None, "sock": None, "paused": False, "busy": False,
          "stop_at": None, "mpv": None, "mpv_checked": 0.0}
    TL_M = 16
    trim_cv = tk.Canvas(t, height=58, highlightthickness=0, borderwidth=0)
    trim_cv.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 2))
    f_pv = ttk.Frame(t)
    f_pv.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))
    tl_play_btn = ttk.Button(f_pv, text="▶ Preview", width=10, command=lambda: trim_preview())
    tl_play_btn.pack(side="left")
    tl_pause_btn = ttk.Button(f_pv, text="Pause", width=8, command=lambda: trim_pause())
    tl_pause_btn.pack(side="left", padx=(4, 0))
    tl_stop_btn = ttk.Button(f_pv, text="Stop", width=6, command=lambda: trim_stop())
    tl_stop_btn.pack(side="left", padx=(4, 0))
    tl_pos_var = tk.StringVar()
    ttk.Label(f_pv, textvariable=tl_pos_var, width=18).pack(side="left", padx=(12, 0))
    tl_note_var = TrVar()
    ttk.Label(f_pv, textvariable=tl_note_var, style="Hint.TLabel").pack(side="left", padx=(8, 0))

    f_ts = ttk.Frame(t)
    ttk.Entry(f_ts, textvariable=start_var, width=14).pack(side="left")
    tl_set_s = ttk.Button(f_ts, text="Set start here", command=lambda: trim_set_here("start"))
    tl_set_s.pack(side="left", padx=(8, 0))
    row(t, 2, "Start", f_ts)
    f_te = ttk.Frame(t)
    ttk.Entry(f_te, textvariable=end_var, width=14).pack(side="left")
    tl_set_e = ttk.Button(f_te, text="Set end here", command=lambda: trim_set_here("end"))
    tl_set_e.pack(side="left", padx=(8, 0))
    row(t, 3, "End", f_te)
    ttk.Checkbutton(t, text="Frame-accurate (slower, re-encodes)",
                    variable=precise_var).grid(row=4, column=1, sticky="w", pady=4)
    trim_help = HelpBox(t)
    trim_help.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def update_trim_help(*_):
        """Update the help box of the Trim tab."""
        trim_help.set_items([
            ("", "Drag the green (start) and red (end) markers on the timeline, or type the times. "
                 "Preview plays the part in mpv; while it plays, Set start here / Set end here take the current position. "
                 "Time formats: 90  ·  1:30  ·  00:01:30.5"),
            ("Frame-accurate", "Re-encodes so the cut is exactly where you set it (slower). Without it the cut is instant but can be a second or two off.")
            if precise_var.get() else None])

    precise_var.trace_add("write", update_trim_help)
    update_trim_help()

    def tl_dur():
        """Length of the loaded file in seconds (0 if unknown)."""
        d = state.get("duration")
        return float(d) if d else 0.0

    def tl_times():
        """Start and end time from the two text fields, as seconds (None for an invalid one)."""
        out = []
        for v_ in (start_var, end_var):
            try:
                out.append(to_seconds(v_.get()))
            except ValueError:
                out.append(None)
        return out[0], out[1]

    def tl_x(sec, w, dur):
        """Timeline: x pixel of a time."""
        return TL_M + sec / dur * (w - 2 * TL_M)

    def tl_sec(x, w, dur):
        """Timeline: time of an x pixel (kept within the file)."""
        return min(dur, max(0.0, (x - TL_M) / max(1, w - 2 * TL_M) * dur))

    def short_t(sec):
        """Time as short text for the markers."""
        sec = max(0.0, sec)
        h, m, s2 = int(sec // 3600), int(sec % 3600 // 60), sec % 60
        return f"{h}:{m:02d}:{s2:04.1f}" if h else f"{m}:{s2:04.1f}"

    def trim_draw(*_):
        """Redraw the timeline: track, selected part, start / end markers and the playing position."""
        cv = trim_cv
        cv.delete("all")
        dark = dark_var.get()
        bg = DARK["bg"] if dark else (style.lookup("TFrame", "background") or root.cget("bg"))
        track, sel = (DARK["btn"], "#4a86e8") if dark else ("#cfd3d9", "#8fb4f2")
        dim, play = (DARK["off"], "#ffffff") if dark else ("#888888", "#222222")
        cv.config(bg=bg)
        w, dur = max(cv.winfo_width(), 240), tl_dur()
        if dur <= 0:
            cv.create_text(w / 2, 29, text=tr("Open a video or audio file to see its timeline"),
                           fill=dim, font=(UI_FONT, 10))
            return
        cv.create_rectangle(TL_M, 22, w - TL_M, 32, fill=track, outline="")
        step = next((x for x in (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200)
                     if x >= dur / 8), 7200)
        for k in range(int(dur // step) + 1):
            x = tl_x(k * step, w, dur)
            cv.create_line(x, 32, x, 37, fill=dim)
            cv.create_text(x, 47, text=fmt_length(k * step), fill=dim, font=(UI_FONT, 8))
        s_, e_ = tl_times()
        if s_ is not None and e_ is not None and 0 <= s_ < e_:
            xs, xe = tl_x(min(s_, dur), w, dur), tl_x(min(e_, dur), w, dur)
            cv.create_rectangle(xs, 22, xe, 32, fill=sel, outline="")
            cv.create_line(xs, 10, xs, 36, fill="#2e9e4f", width=3)
            cv.create_polygon(xs, 8, xs + 11, 8, xs, 19, fill="#2e9e4f", outline="")
            cv.create_line(xe, 10, xe, 36, fill="#d64545", width=3)
            cv.create_polygon(xe, 8, xe - 11, 8, xe, 19, fill="#d64545", outline="")
        if tl["pos"] is not None:
            x = tl_x(min(tl["pos"], dur), w, dur)
            cv.create_line(x, 14, x, 40, fill=play, width=2)

    def tl_hit(x):
        """Which part of the timeline a mouse press is on: the start marker, the end marker, or the track."""
        w, dur = max(trim_cv.winfo_width(), 240), tl_dur()
        if dur <= 0:
            return None
        s_, e_ = tl_times()
        near = sorted((abs(x - tl_x(v_, w, dur)), n_) for v_, n_ in ((s_, "start"), (e_, "end"))
                      if v_ is not None)
        return near[0][1] if near and near[0][0] <= 9 else "play"

    def tl_move(event):
        """Dragging on the timeline: move the marker (or the playing position) and update the time fields."""
        kind, dur = tl["drag"], tl_dur()
        if not kind or dur <= 0:
            return
        sec = round(tl_sec(event.x, max(trim_cv.winfo_width(), 240), dur), 2)
        s_, e_ = tl_times()
        if kind == "start":
            start_var.set(fmt_time(min(sec, (e_ - 0.1) if e_ is not None else sec)))
        elif kind == "end":
            end_var.set(fmt_time(max(sec, (s_ + 0.1) if s_ is not None else sec)))
        else:
            tl["pos"] = sec
            trim_draw()

    def tl_press(event):
        """Mouse pressed on the timeline."""
        tl["drag"] = tl_hit(event.x)
        tl_move(event)

    def tl_release(event):
        """Mouse released on the timeline: seek the preview to the new position or marker."""
        tl_move(event)
        kind, tl["drag"] = tl["drag"], None
        if kind == "play" and tl["pos"] is not None:
            tl["stop_at"] = None  # free playing after you click somewhere
            trim_seek(tl["pos"])
        elif kind == "start":
            trim_seek(tl_times()[0])

    trim_cv.bind("<Button-1>", tl_press)
    trim_cv.bind("<B1-Motion>", tl_move)
    trim_cv.bind("<ButtonRelease-1>", tl_release)
    trim_cv.bind("<Configure>", trim_draw)
    start_var.trace_add("write", trim_draw)
    end_var.trace_add("write", trim_draw)

    def trim_alive():
        """True while the preview player (mpv) is running."""
        p = tl["proc"]
        return bool(p and p.poll() is None)

    def trim_send(messages, wait_ids=None, then=None):
        """Talk to the running mpv in a thread; then(result) runs in the window thread."""
        def work():
            """Send the commands to mpv in the background and hand over its answers."""
            res = None
            try:
                res = mpv_ipc(tl["sock"], messages, wait_ids=wait_ids, timeout=1.0)
            except OSError:
                pass
            if then:
                root.after(0, lambda: then(res))
        if trim_alive() and tl["sock"]:
            threading.Thread(target=work, daemon=True).start()

    def trim_seek(sec):
        """Jump the preview to a time."""
        if sec is not None:
            trim_send([{"command": ["seek", float(sec), "absolute+exact"]}])

    def trim_preview():
        """Play the chosen part in mpv (starts mpv, or jumps to the start if it is already open)."""
        src = src_var.get()
        s_, e_ = tl_times()
        if not os.path.isfile(src) or s_ is None:
            status_var.set("Enter a valid Start time first.")
            return
        tl["stop_at"], tl["pos"], tl["paused"] = e_, s_, False
        if trim_alive():  # already open: jump to the start and play
            trim_send([{"command": ["seek", float(s_), "absolute+exact"]},
                       {"command": ["set_property", "pause", False]}])
            trim_draw()
            return
        mpv = find_tool("mpv")
        if not mpv:
            return
        import tempfile
        sock = (r"\\.\pipe\faun-trim-%d" % os.getpid() if IS_WIN else
                os.path.join(tempfile.gettempdir(), "faun-trim-%d.sock" % os.getpid()))
        if not IS_WIN:
            try:
                os.remove(sock)
            except OSError:
                pass
        cmd = [mpv, "--input-ipc-server=" + sock, "--keep-open=yes", "--force-window=yes",
               "--no-terminal", "--title=Trim preview", f"--start={s_:.3f}", src]
        try:
            tl["proc"] = subprocess.Popen(cmd, env=tool_env(), creationflags=NO_WINDOW,
                                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL)
            tl["sock"] = sock
        except OSError as ex:
            status_var.set(f"Could not start the player: {ex}")
        trim_draw()

    def compress_preview():
        """Compress a short piece with the current settings, report the size it comes to (and what the
        whole video would be) and play it, so the quality can be judged before the real run."""
        if comp_prev["busy"]:
            return
        src = src_var.get()
        ffmpeg = find_tool("ffmpeg")
        if not os.path.isfile(src) or not ffmpeg:
            messagebox.showwarning("No file", "Open a video file first.")
            return
        if state["has_video"] is False:
            messagebox.showwarning("No video", "This file has no video, so this task doesn't apply.")
            return
        dur = state["duration"] or 0
        n_ = 10.0 if not dur else min(10.0, dur)
        try:
            at_ = to_seconds(prev_at_var.get())
        except ValueError:
            messagebox.showwarning("Bad time", "Enter the start as seconds or m:ss, e.g. 1:30.")
            return
        if at_ is None:
            at_ = max(0.0, (dur - n_) / 2)
        at_ = max(0.0, min(at_, max(0.0, dur - n_))) if dur else at_
        opt = options("Compress")
        if target_var.get().strip():  # the bitrate that the whole video would get
            try:
                mb_ = float(target_var.get().strip().replace(",", "."))
            except ValueError:
                messagebox.showwarning("Bad size", "Target size must be a number, e.g. 25")
                return
            opt["video_kbps"] = target_video_kbps(mb_, dur) if dur else None
            if not opt["video_kbps"]:
                messagebox.showwarning("Target too small", "That size is too small for a video of this length. "
                                                           "Try a larger size.")
                return
        opt["sample"] = (at_, n_)
        import tempfile
        out = os.path.join(tempfile.gettempdir(), f"faun-preview-{os.getpid()}.mp4")
        try:
            os.remove(out)
        except OSError:
            pass
        cmd = [ffmpeg] + build_command("Compress", src, out, opt)
        comp_prev["busy"] = True
        prev_btn.config(state="disabled")
        prev_info.set("Making the preview…")

        def work():
            """Background job: compress the sample with ffmpeg and report back to the window."""
            err = ""
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=900, env=tool_env(),
                                   stdin=subprocess.DEVNULL, **TEXT)  # (TEXT already hides the console window)
                if r.returncode != 0 or not os.path.isfile(out):
                    err = short_error(r.stderr or "ffmpeg failed.", 160)
            except Exception as ex:
                err = str(ex)
            root.after(0, lambda: compress_preview_done(err, out, at_, n_, dur, os.path.getsize(src)))
        threading.Thread(target=work, daemon=True).start()

    def compress_preview_done(err, out, at_, n_, dur, orig):
        """The preview sample is ready: show its size, the estimate for the whole video and play it."""
        comp_prev["busy"] = False
        prev_btn.config(state="normal")
        if err:
            prev_info.set(f"Preview failed: {err}")
            return
        size = os.path.getsize(out)
        whole = size * dur / n_ if dur else 0
        if whole:
            pct = round(100 * (1 - whole / orig)) if orig else 0
            prev_info.set(f"Preview of {fmt_length(n_)} from {fmt_length(at_)}: {human_size(size)}. "
                          f"The whole video would be about {human_size(whole)} "
                          f"(original {human_size(orig)}, "
                          + (f"{pct} % smaller)." if pct >= 0 else f"{-pct} % larger). "
                             "The video is already compressed well: try H.265, a target size or a lower resolution."))
        else:
            prev_info.set(f"Preview of {fmt_length(n_)} from {fmt_length(at_)}: {human_size(size)}.")
        pl = find_player()
        try:
            if pl and pl[0] == "mpv":
                subprocess.Popen([pl[1], out, "--keep-open=yes", "--force-window=yes",
                                  "--title=Compression preview"], env=tool_env(), creationflags=NO_WINDOW,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif pl:
                subprocess.Popen([pl[1], out], creationflags=NO_WINDOW)
            else:
                status_var.set("No player found: install mpv from the Setup tab to watch the preview.")
        except OSError as ex:
            status_var.set(f"Could not start the player: {ex}")

    def trim_pause():
        """Pause / resume the preview."""
        def done(res):
            """Remember the pause state mpv reports."""
            if isinstance(res, dict) and isinstance(res.get(2), bool):
                tl["paused"] = res[2]
        trim_send([{"command": ["cycle", "pause"], "request_id": 1},
                   {"command": ["get_property", "pause"], "request_id": 2}], wait_ids=[1, 2], then=done)

    def trim_stop():
        """Close the preview player."""
        if trim_alive():
            trim_send([{"command": ["quit"]}])
            try:
                tl["proc"].terminate()
            except OSError:
                pass
        tl.update(proc=None, paused=False, stop_at=None)
        trim_ui()

    def trim_set_here(which):
        """Take the current playing position as the start or end time (when 'Set start / end here' is pressed)."""
        def apply(sec):
            """Store the time in the matching field, keeping start before end."""
            if not isinstance(sec, (int, float)):
                sec = tl["pos"]
            if sec is None:
                return
            sec = round(max(0.0, min(float(sec), tl_dur() or float(sec))), 2)
            s_, e_ = tl_times()
            if which == "start":
                if e_ is not None and sec >= e_ - 0.05:
                    status_var.set("Start must be before End.")
                    return
                start_var.set(fmt_time(sec))
            else:
                if s_ is not None and sec <= s_ + 0.05:
                    status_var.set("End must be after Start.")
                    return
                end_var.set(fmt_time(sec))
                if tl["stop_at"] is not None:
                    tl["stop_at"] = sec
        if trim_alive():
            trim_send([{"command": ["get_property", "time-pos"], "request_id": 1}], wait_ids=[1],
                      then=lambda res: apply(res.get(1) if isinstance(res, dict) else None))
        else:
            apply(tl["pos"])

    def trim_apply_progress(res):
        """Apply what mpv reported: playing position and pause state (moves the playhead on the timeline)."""
        tl["busy"] = False
        if not isinstance(res, dict) or not trim_alive():
            return
        pos, paused = res.get(1), res.get(2)
        if isinstance(paused, bool):
            tl["paused"] = paused
        if isinstance(pos, (int, float)) and not tl["drag"]:
            tl["pos"] = float(pos)
            if tl["stop_at"] is not None and pos >= tl["stop_at"] - 0.02 and not tl["paused"]:
                trim_send([{"command": ["set_property", "pause", True]},
                           {"command": ["seek", float(tl["stop_at"]), "absolute+exact"]}])
                tl["stop_at"], tl["paused"] = None, True
            trim_draw()

    def trim_ask():
        """Ask mpv for its position and pause state (runs in a background thread)."""
        res = None
        try:
            res = mpv_ipc(tl["sock"], [{"command": ["get_property", "time-pos"], "request_id": 1},
                                       {"command": ["get_property", "pause"], "request_id": 2}],
                          wait_ids=[1, 2], timeout=1.0)
        except OSError:
            pass
        root.after(0, lambda: trim_apply_progress(res))

    def trim_ui():
        """Enable / disable the preview buttons according to the player state."""
        has_file = tl_dur() > 0 and os.path.isfile(src_var.get())
        alive = trim_alive()
        now = time.time()
        if now - tl["mpv_checked"] > 4:
            tl["mpv"], tl["mpv_checked"] = find_tool("mpv"), now
        tl_play_btn.config(state="normal" if (has_file and tl["mpv"]) else "disabled")
        tl_pause_btn.config(state="normal" if alive else "disabled",
                            text=tr("Resume") if (alive and tl["paused"]) else tr("Pause"))
        tl_stop_btn.config(state="normal" if alive else "disabled")
        can_set = has_file and (alive or tl["pos"] is not None)
        for b_ in (tl_set_s, tl_set_e):
            b_.config(state="normal" if can_set else "disabled")
        tl_note_var.set("" if tl["mpv"] else "Install mpv on the Setup tab to use the preview")
        tl_pos_var.set(f"{short_t(tl['pos'])} / {short_t(tl_dur())}" if (has_file and tl["pos"] is not None) else "")

    def trim_poll():
        """Every half second: notice that the player was closed, ask for its position, refresh the buttons."""
        try:
            if tl["proc"] is not None and not trim_alive():  # the player window was closed
                tl.update(proc=None, paused=False, stop_at=None)
            if trim_alive() and tl["sock"] and not tl["busy"] and not tl["drag"]:
                tl["busy"] = True
                threading.Thread(target=trim_ask, daemon=True).start()
            trim_ui()
        finally:
            root.after(300, trim_poll)

    import atexit
    atexit.register(lambda: tl["proc"].terminate() if trim_alive() else None)
    root.after(300, trim_poll)

    # Convert
    t = tab("Convert")
    conv_var = tk.StringVar(value="mp4")
    conv_q_var = tk.StringVar(value="Medium")
    conv_codec_var = tk.StringVar(value=list(CODECS)[0])
    row(t, 0, "Output format", combo(t, conv_var, VIDEO_FORMATS, 10))
    row(t, 1, "Quality", combo(t, conv_q_var, list(QUALITY)))
    row(t, 2, "Video codec", combo(t, conv_codec_var, list(CODECS), 28))
    hint(t, 3, "Converts the loaded file to another format; the Quality setting trades file size against picture quality.\n"
               "H.265 makes much smaller files (plays on Macs/iPhones, not every old player).\n"
               "GIF and WebM always use the CPU and ignore the codec setting.")

    # Compress
    t = tab("Compress")
    qual_var = tk.StringVar(value="Medium")
    res_var = tk.StringVar(value="Keep original")
    comp_codec_var = tk.StringVar(value=list(CODECS)[0])
    target_var = tk.StringVar()
    row(t, 0, "Quality", combo(t, qual_var, list(QUALITY)))
    row(t, 1, "Max resolution", combo(t, res_var, list(RESOLUTIONS)))
    row(t, 2, "Video codec", combo(t, comp_codec_var, list(CODECS), 28))
    f_tgt = ttk.Frame(t)
    ttk.Entry(f_tgt, textvariable=target_var, width=8).pack(side="left")
    ttk.Label(f_tgt, text="  MB   (optional)").pack(side="left")
    row(t, 3, "Target file size", f_tgt)
    hint(t, 4, "Makes the loaded video smaller. Max resolution scales the picture down (never up).\n"
               "Fill in a target size (e.g. 25 for Discord or email) to override Quality.\n"
               "The result is approximate (about ±10 %).")
    comp_prev = {"busy": False}
    prev_at_var = tk.StringVar()
    prev_info = TrVar(value="")
    f_prev = ttk.Frame(t)
    ttk.Label(f_prev, text="from").pack(side="left")
    ttk.Entry(f_prev, textvariable=prev_at_var, width=8).pack(side="left", padx=(4, 6))
    prev_btn = ttk.Button(f_prev, text="Make preview", command=lambda: compress_preview())
    prev_btn.pack(side="left")
    ttk.Label(f_prev, text="  (10 s sample; empty = from the middle)", style="Hint.TLabel").pack(side="left")
    row(t, 5, "Preview", f_prev)
    ttk.Label(t, textvariable=prev_info, style="Hint.TLabel", justify="left").grid(
        row=6, column=0, columnspan=2, sticky="w")

    # Extract audio
    t = tab("Extract audio")
    aud_var = tk.StringVar(value="mp3")
    row(t, 0, "Audio format", combo(t, aud_var, list(AUDIO_FORMATS), 10))
    hint(t, 1, "Saves only the sound of the loaded video.\n"
               "mp3 plays everywhere  ·  m4a is smaller at the same quality  ·  wav is lossless but very large.")

    # Remove audio
    t = tab("Remove audio")
    ttk.Label(t, text="Saves the video without its sound track. The picture is copied untouched (no quality loss, very fast).",
              style="Hint.TLabel").grid(row=0, column=0, sticky="w")

    # Files: two folders side by side (like Total Commander) with copy / cut / paste, new folder,
    # drag and drop between the folders and onto the task tabs
    files_tab = t = tab("Files")
    nb.insert(nb.index(trim_tab), files_tab)  # sits before the editing tabs
    t.columnconfigure(0, weight=1, uniform="fmcols")
    t.columnconfigure(1, weight=1, uniform="fmcols")
    t.rowconfigure(0, weight=1)
    fm_media_var = tk.BooleanVar(value=True)
    fm_dups = set()  # files the duplicate finder found: shown in orange in the lists
    fm_clip = {"paths": [], "cut": False}  # what Copy / Cut put aside, for Paste
    fm_job = {"busy": False}
    fm_active = {"p": None}
    panes = []
    PANE_ON, PANE_OFF = "#2f7de1", "#8a8a8a"
    DRAG_TABS = ("Trim", "Convert", "Compress", "Extract audio", "Remove audio", "Loudness", "Batch download")
    fm_drag = {"press": None, "rows": [], "active": False, "ghost": None, "clicked": None, "src": None}

    def is_media_file(p):
        """True for video and audio files."""
        return os.path.splitext(p)[1].lower().lstrip(".") in VIDEO_EXTS + AUDIO_EXTS

    class FPane:
        """One folder view: path bar, list, and the actions that work on its selection."""

        def __init__(self, col, start):
            """Build one folder pane: path bar, 'Go to' list, file list with columns and the counts line."""
            self.dir, self.rows, self.sort, self.rev, self.gen = "", {}, "name", False, 0
            self.dur = {}
            self.dir_var = tk.StringVar(value=start)
            self.place_var = tk.StringVar(value="")
            self.box = tk.Frame(t, highlightthickness=2, highlightbackground=PANE_OFF, bd=0)
            self.box.grid(row=0, column=col, sticky="nsew", padx=(0, 4) if col == 0 else (4, 0))
            inner = ttk.Frame(self.box, padding=4)
            inner.pack(fill="both", expand=True)
            inner.columnconfigure(0, weight=1)
            inner.rowconfigure(2, weight=1)
            top = ttk.Frame(inner)
            top.grid(row=0, column=0, columnspan=2, sticky="ew")
            ttk.Button(top, text="◀ Up", width=6, command=self.up).pack(side="left")
            self.entry = ttk.Entry(top, textvariable=self.dir_var)
            self.entry.pack(side="left", fill="x", expand=True, padx=4)
            self.entry.bind("<Return>", lambda e: self.go(self.dir_var.get()))
            ttk.Button(top, text="Choose…", command=self.choose).pack(side="left")
            ttk.Button(top, text="Refresh", width=8, command=lambda: self.refresh()).pack(
                side="left", padx=(4, 0))
            f2 = ttk.Frame(inner)
            f2.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 4))
            f2.columnconfigure(1, weight=1, uniform="fm_row2")  # the drop-down and the search box share
            f2.columnconfigure(3, weight=1, uniform="fm_row2")  # the free width equally
            ttk.Label(f2, text="Go to:").grid(row=0, column=0, sticky="w")
            self.place_combo = combo(f2, self.place_var, [n_ for n_, p_ in FM_PLACES.items()
                                                          if not p_ or os.path.isdir(os.path.expanduser(p_))], 8)
            self.place_combo.grid(row=0, column=1, sticky="ew", padx=(4, 12))
            self.place_combo.bind("<<ComboboxSelected>>", lambda e: self.place())
            # search: only the names containing the typed words are listed (no case / accents needed)
            self.search_var = tk.StringVar(value="")
            ttk.Label(f2, text="Search:").grid(row=0, column=2, sticky="e")
            self.search_entry = ttk.Entry(f2, textvariable=self.search_var, width=6)
            self.search_entry.grid(row=0, column=3, sticky="ew", padx=(4, 4))
            ttk.Button(f2, text="✕", width=2, command=lambda: self.search_var.set("")).grid(row=0, column=4)
            self.search_entry.bind("<Escape>", lambda e: self.search_var.set(""))
            self.search_entry.bind("<Return>", lambda e: self.tree.focus_set())
            self.search_job = [None]

            def search_changed(*_a):
                """Filter the list shortly after the typing stops."""
                if self.search_job[0]:
                    root.after_cancel(self.search_job[0])
                self.search_job[0] = root.after(200, lambda: self.refresh(keep=True))
            self.search_var.trace_add("write", search_changed)
            self.tree = ttk.Treeview(inner, columns=("name", "len", "size", "date"), show="headings",
                                     height=9, selectmode="extended")
            for col_, head_, w_, st_ in (("name", "Name", 190, True), ("len", "Length", 62, False),
                                         ("size", "Size", 72, False), ("date", "Modified", 118, False)):
                self.tree.heading(col_, text=head_, command=lambda c=col_: self.sort_by(c))
                self.tree.column(col_, width=w_, stretch=st_, anchor="w" if col_ in ("name", "date") else "e")
            sb = ttk.Scrollbar(inner, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=sb.set)
            self.tree.grid(row=2, column=0, sticky="nsew")
            sb.grid(row=2, column=1, sticky="ns")
            self.count_var = TrVar(value="")
            ttk.Label(inner, textvariable=self.count_var, style="Hint.TLabel").grid(
                row=3, column=0, columnspan=2, sticky="w", pady=(3, 0))
            self.tree.tag_configure("dup", foreground="#e08a00")
            self.tree.bind("<<TreeviewSelect>>", lambda e: fm_update_buttons())
            self.tree.bind("<Double-1>", lambda e: fm_open_row())
            self.tree.bind("<Return>", lambda e: fm_open_row())
            self.tree.bind("<BackSpace>", lambda e: self.up())
            self.tree.bind("<FocusIn>", lambda e: fm_set_active(self), add="+")
            self.tree.bind("<ButtonPress-1>", lambda e: fm_press(self, e))
            self.tree.bind("<B1-Motion>", lambda e: fm_motion_ev(self, e))
            self.tree.bind("<ButtonRelease-1>", lambda e: fm_release(self, e), add="+")
            for seq_ in (("<Button-2>", "<Button-3>", "<Control-Button-1>") if IS_MAC else ("<Button-3>",)):
                self.tree.bind(seq_, lambda e: fm_popup(self, e))
            panes.append(self)

        def selected(self):
            """The selected rows as (path, is_folder) pairs."""
            return [(self.rows[i]["path"], self.rows[i]["dir"]) for i in self.tree.selection() if i in self.rows]

        def update_count(self):
            """Refresh the 'Folders: N · Files: M · Selected: K' line."""
            nd = sum(1 for r in self.rows.values() if r["dir"])
            nf = len(self.rows) - nd
            ns = len(self.selected())
            self.count_var.set(f"Folders: {nd} · Files: {nf}" + (f" · Selected: {ns}" if ns else ""))

        def go(self, folder, select=None):
            """Show a folder in this pane."""
            folder = os.path.abspath(os.path.expanduser(folder or "."))
            if not os.path.isdir(folder):
                status_var.set("That folder does not exist.")
                return
            if folder != self.dir:
                self.search_var.set("")  # a new folder starts without a search
            self.dir = folder
            self.dir_var.set(folder)
            self.refresh(select)

        def up(self):
            """Go to the parent folder (and select the folder just left)."""
            parent = os.path.dirname(self.dir or self.dir_var.get())
            if parent and parent != self.dir:
                self.go(parent, select=self.dir)

        def choose(self):
            """Choose a folder with the folder dialog."""
            p = filedialog.askdirectory(initialdir=self.dir or None)
            if p:
                self.go(p)

        def place(self):
            """Jump to one of the 'Go to' places (Home, Downloads, Music …)."""
            name = self.place_var.get()
            try:
                target = FM_PLACES[name]  # (a Czech label finds its English entry)
            except KeyError:
                target = ""
            self.go(dl_dir_var.get() if not target else os.path.expanduser(target))

        def sort_by(self, col):
            """Sort by a column; the same column again reverses the order."""
            self.rev = (not self.rev) if self.sort == col else False
            self.sort = col
            self.refresh(keep=True)

        def refresh(self, select=None, keep=False):
            """Read the folder again and fill the list (duration lookups continue in the background)."""
            folder = self.dir or os.path.abspath(os.path.expanduser(self.dir_var.get() or "~"))
            if not os.path.isdir(folder):
                return
            self.dir = folder
            keep_sel = {self.rows[i]["path"] for i in self.tree.selection() if i in self.rows} if keep else set()
            self.gen += 1
            gen = self.gen
            entries = []
            words_ = plain_text(self.search_var.get()).split()  # every typed word must be in the name
            try:
                with os.scandir(folder) as it:
                    for e in it:
                        if e.name.startswith("."):
                            continue
                        try:
                            st = e.stat()
                            isdir = e.is_dir()
                        except OSError:
                            continue
                        if not isdir and fm_media_var.get() and not is_media_file(e.name):
                            continue
                        if words_ and not all(w_ in plain_text(e.name) for w_ in words_):
                            continue
                        entries.append({"path": e.path, "name": e.name, "dir": isdir,
                                        "size": 0 if isdir else st.st_size, "mtime": st.st_mtime})
                        if len(entries) >= 3000:
                            break
            except OSError as ex:
                status_var.set(f"Could not read that folder: {ex}")
                return
            keyf = {"name": lambda r: r["name"].lower(), "size": lambda r: r["size"],
                    "date": lambda r: r["mtime"],
                    "len": lambda r: self.dur.get(r["path"], (0, 0))[1] or 0}[self.sort]
            entries.sort(key=keyf, reverse=self.rev)
            entries.sort(key=lambda r: not r["dir"])  # folders first
            self.tree.delete(*self.tree.get_children())
            self.rows = {}
            todo = []
            for r in entries:
                cached = self.dur.get(r["path"])
                dur = cached[1] if cached and cached[0] == r["mtime"] else None
                ext = os.path.splitext(r["name"])[1].lower().lstrip(".")
                icon = "📁 " if r["dir"] else ("🎬 " if ext in VIDEO_EXTS else ("🎵 " if ext in AUDIO_EXTS else "      "))
                iid = self.tree.insert("", "end", values=(
                    icon + r["name"], fmt_length(dur) if dur else "", "" if r["dir"] else human_size(r["size"]),
                    time.strftime("%Y-%m-%d %H:%M", time.localtime(r["mtime"]))),
                    tags=("dup",) if r["path"] in fm_dups else ())
                self.rows[iid] = r
                if (r["path"] in keep_sel) or (select and os.path.abspath(select) == r["path"]):
                    self.tree.selection_add(iid)
                    self.tree.see(iid)
                if not r["dir"] and dur is None and is_media_file(r["name"]):
                    todo.append((iid, r))
            fm_update_buttons()
            self.update_count()
            if fm_active["p"] is self:
                status_var.set(f"{len(entries)} item(s) in {folder}")
            if todo:
                threading.Thread(target=self.durations, args=(gen, todo[:400]), daemon=True).start()

        def durations(self, gen, todo):
            """Read the lengths of the media files in the background and fill the Length column."""
            for iid, r in todo:
                if gen != self.gen:
                    return
                d = get_duration(r["path"])
                self.dur[r["path"]] = (r["mtime"], d or 0)
                root.after(0, lambda i=iid, d=d, g=gen: (self.tree.set(i, "len", fmt_length(d))
                                                         if g == self.gen and self.tree.exists(i) and d else None))

    saved_files = load_settings()
    _dl0 = os.path.join(os.path.expanduser("~"), "Downloads")

    def _start_dir(key, fallback):
        """Folder remembered in the settings, or a fallback if it no longer exists."""
        p = saved_files.get(key) or ""
        return p if p and os.path.isdir(p) else fallback

    pane_l = FPane(0, _start_dir("files_dir", _dl0))
    pane_r = FPane(1, _start_dir("files_dir2", os.path.expanduser("~")))
    fm_active["p"] = pane_l

    def fm_other():
        """The pane that is not active (the target of 'Copy / Move to the other side')."""
        return pane_r if fm_active["p"] is pane_l else pane_l

    def fm_set_active(p):
        """Make a pane the active one (blue frame); the buttons act on it."""
        fm_active["p"] = p
        for q in panes:
            try:
                q.box.config(highlightbackground=PANE_ON if q is p else PANE_OFF)
            except tk.TclError:
                pass
        fm_update_buttons()

    def fm_refresh_all(select=None):
        """Re-read both folders (after copy, move, rename, delete)."""
        for q in panes:
            q.refresh(select=select if q is fm_active["p"] else None, keep=True)

    # ---- buttons (they act on the pane that was used last)
    f_fb0 = ttk.Frame(t)
    f_fb0.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    fm_copy_btn = ttk.Button(f_fb0, text="Copy", width=7, command=lambda: fm_clip_set(False))
    fm_cut_btn = ttk.Button(f_fb0, text="Cut", width=6, command=lambda: fm_clip_set(True))
    fm_paste_btn = ttk.Button(f_fb0, text="Paste", width=7, command=lambda: fm_paste())
    fm_mkdir_btn = ttk.Button(f_fb0, text="New folder…", width=12, command=lambda: fm_mkdir())
    fm_copyto_btn = ttk.Button(f_fb0, text="Copy → other side", width=17, command=lambda: fm_to_other(False))
    fm_moveto_btn = ttk.Button(f_fb0, text="Move → other side", width=17, command=lambda: fm_to_other(True))
    for b_ in (fm_copy_btn, fm_cut_btn, fm_paste_btn, fm_mkdir_btn, fm_copyto_btn, fm_moveto_btn):
        b_.pack(side="left", padx=(0, 4))
    ttk.Checkbutton(f_fb0, text="Only video and audio", variable=fm_media_var,
                    command=lambda: fm_refresh_all()).pack(side="right")

    f_fb1 = ttk.Frame(t)
    f_fb1.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
    ttk.Label(f_fb1, text="Use in:").pack(side="left")
    fm_send_btns = []
    for tn_ in ("Trim", "Convert", "Compress", "Extract audio", "Remove audio", "Loudness"):
        b_ = ttk.Button(f_fb1, text=tn_, command=lambda n=tn_: fm_send(n))
        b_.pack(side="left", padx=(4, 0))
        fm_send_btns.append(b_)
    f_fb2 = ttk.Frame(t)
    f_fb2.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
    fm_batch_btn = ttk.Button(f_fb2, text="Add to batch", width=12, command=lambda: fm_to_batch())
    fm_rename_btn = ttk.Button(f_fb2, text="Rename…", width=9, command=lambda: fm_rename())
    fm_delete_btn = ttk.Button(f_fb2, text="Move to Trash", width=14, command=lambda: fm_delete())
    fm_show_btn = ttk.Button(f_fb2, text="Show in Finder" if IS_MAC else (
        "Show in Explorer" if IS_WIN else "Show in folder"), command=lambda: fm_reveal())
    fm_dup_btn = ttk.Button(f_fb2, text="Find duplicates…", width=16, command=lambda: fm_dups_dialog())
    for b_ in (fm_batch_btn, fm_rename_btn, fm_delete_btn, fm_show_btn, fm_dup_btn):
        b_.pack(side="left", padx=(0, 4))
    fm_vis_var = tk.BooleanVar(value=False)  # patterns drawn from the audio while a file plays (mpv)
    fm_vis_style_var = tk.StringVar(value="Fractal")
    fm_vis_combo = combo(f_fb2, fm_vis_style_var, list(VIS_STYLES), 14)
    fm_vis_combo.pack(side="right")
    fm_vis_combo.bind("<<ComboboxSelected>>", lambda e: fm_vis_changed())
    ttk.Checkbutton(f_fb2, text="Visualizer", variable=fm_vis_var,
                    command=lambda: fm_vis_changed()).pack(side="right", padx=(8, 4))
    f_fb3 = ttk.Frame(t)  # player controls and the clickable time line
    f_fb3.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(6, 0))
    fm_play_btn = ttk.Button(f_fb3, text="Play", width=8, command=lambda: fm_play())
    fm_prev_btn = ttk.Button(f_fb3, text="◀ Prev", width=7, state="disabled", command=lambda: fm_next(True, -1))
    fm_pause_btn = ttk.Button(f_fb3, text="Pause", width=8, state="disabled", command=lambda: fm_pause())
    fm_stop_btn = ttk.Button(f_fb3, text="Stop", width=7, state="disabled", command=lambda: fm_stop())
    fm_next_btn = ttk.Button(f_fb3, text="Next ▶", width=8, state="disabled", command=lambda: fm_next(True))
    for b_ in (fm_play_btn, fm_pause_btn, fm_stop_btn, fm_prev_btn, fm_next_btn):
        b_.pack(side="left", padx=(0, 4))
    fm_pos_lbl = ttk.Label(f_fb3, text="0:00", width=7, anchor="e")
    fm_pos_lbl.pack(side="left", padx=(6, 0))
    fm_scale = ttk.Scale(f_fb3, from_=0, to=1, orient="horizontal")
    fm_scale.pack(side="left", fill="x", expand=True, padx=8)
    fm_dur_lbl = ttk.Label(f_fb3, text="0:00", width=7)
    fm_dur_lbl.pack(side="left")
    if not dnd_ok:
        ttk.Label(t, text="Dropping files onto the window needs one extra package: install tkinterdnd2 on the Setup tab, then restart.",
                  style="Hint.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
    fm_menu_last = {"m": None}  # the right-click menu is made when it is needed (see fm_popup)

    def fm_selected():
        """Selection of the active pane."""
        return fm_active["p"].selected()

    def fm_media_files(deep=False):
        """Selected video / audio files; deep=True also takes everything inside the selected folders."""
        out = []
        for p, d in fm_selected():
            if not d:
                if is_media_file(p):
                    out.append(p)
            elif deep:
                for dp, dn, fn in os.walk(p):
                    dn[:] = sorted(x for x in dn if not x.startswith("."))
                    out.extend(os.path.join(dp, f) for f in sorted(fn, key=str.lower)
                               if not f.startswith(".") and is_media_file(os.path.join(dp, f)))
        return out

    def fm_update_buttons(*_):
        """Enable / disable the buttons according to what is selected."""
        for q_ in panes:
            q_.update_count()
        sel = fm_selected()
        files = [p for p, d in sel if not d]
        one = len(files) == 1 and len(sel) == 1
        for b_ in fm_send_btns:
            b_.config(state="normal" if (one and is_media_file(files[0])) else "disabled")
        if one and is_media_file(files[0]):
            info_hook["show"](files[0])
        fm_play_btn.config(state="normal" if one else "disabled")
        fm_batch_btn.config(state="normal" if any(d or is_media_file(p) for p, d in sel) else "disabled")
        fm_rename_btn.config(state="normal" if len(sel) == 1 else "disabled")
        fm_delete_btn.config(state="normal" if sel else "disabled")
        fm_show_btn.config(state="normal" if len(sel) == 1 else "disabled")
        for b_ in (fm_copy_btn, fm_cut_btn, fm_copyto_btn, fm_moveto_btn):
            b_.config(state="normal" if sel else "disabled")
        fm_paste_btn.config(state="normal" if fm_clip["paths"] else "disabled")

    # ---- copy / cut / paste / new folder
    def fm_unique(folder, name, is_dir):
        """A free path in the folder: 'name copy', 'name copy 2' … if the name is taken."""
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            return path
        stem, ext = (name, "") if is_dir else os.path.splitext(name)
        n = 1
        while True:
            cand = os.path.join(folder, f"{stem} copy{'' if n == 1 else ' ' + str(n)}{ext}")
            if not os.path.exists(cand):
                return cand
            n += 1

    def fm_transfer(paths, dest_dir, move):
        """Copy or move paths into dest_dir in the background; an existing name is never overwritten."""
        if fm_job["busy"]:
            status_var.set("Wait for the current copy to finish.")
            return
        paths = [p for p in paths if os.path.exists(p)]
        if not paths:
            return
        fm_job["busy"] = True
        verb = "Moving" if move else "Copying"

        def worker():
            """Background job: copy or move the files one by one, with progress in the status line."""
            made, failed, moved = [], [], {}
            dest_abs = os.path.abspath(dest_dir)
            for i, p in enumerate(paths, 1):
                name = os.path.basename(p.rstrip("/\\"))
                root.after(0, lambda i=i, n=name: status_var.set(f"{verb} {n}  ({i} of {len(paths)})…"))
                try:
                    pa = os.path.abspath(p)
                    isdir = os.path.isdir(pa)
                    if isdir and (dest_abs + os.sep).startswith(pa + os.sep):
                        raise OSError("a folder cannot go into itself")
                    if move and os.path.dirname(pa) == dest_abs:
                        continue  # already there
                    dest = fm_unique(dest_dir, name, isdir)
                    if move:
                        shutil.move(pa, dest)
                        moved[pa] = dest
                    elif isdir:
                        shutil.copytree(pa, dest)
                    else:
                        shutil.copy2(pa, dest)
                    made.append(dest)
                except (OSError, shutil.Error) as ex:
                    failed.append(f"{name}: {ex}")

            def done():
                """Back in the window: update the lists, the open file and the recent list for moved files, show the result."""
                fm_job["busy"] = False
                for old, new in moved.items():
                    if src_var.get() == old:
                        src_var.set(new)
                    if old in recent_files:
                        recent_files[recent_files.index(old)] = new
                for q in panes:
                    q.refresh(select=made[0] if (made and os.path.abspath(q.dir) == dest_abs) else None, keep=True)
                msg = f"{'Moved' if move else 'Copied'} {len(made)} item(s)."
                status_var.set(msg + (f"  {len(failed)} failed." if failed else ""))
                if failed:
                    messagebox.showerror("Files", "Could not finish:\n" + "\n".join(failed[:6]))
            root.after(0, done)
        threading.Thread(target=worker, daemon=True).start()

    def fm_clip_set(cut):
        """Copy or Cut: put the selection aside for Paste."""
        sel = fm_selected()
        if not sel:
            return
        fm_clip["paths"], fm_clip["cut"] = [p for p, _d in sel], cut
        status_var.set(f"{len(sel)} item(s) {'cut' if cut else 'copied'}: choose the other folder and press Paste.")
        fm_update_buttons()

    def fm_paste():
        """Paste what was copied or cut into the active folder."""
        if not fm_clip["paths"]:
            return
        paths, cut = list(fm_clip["paths"]), fm_clip["cut"]
        if cut:
            fm_clip["paths"] = []
        fm_transfer(paths, fm_active["p"].dir, cut)
        fm_update_buttons()

    def fm_to_other(move):
        """Copy or move the selection into the other pane's folder."""
        sel = fm_selected()
        if sel:
            fm_transfer([p for p, _d in sel], fm_other().dir, move)

    def fm_mkdir():
        """Create a new folder in the active pane."""
        p = fm_active["p"]
        try:
            new = ask_name(root, tk, ttk, tr("New folder"), tr("Name of the new folder:"), tr("New folder"))
            if not new or not new.strip():
                return
            new = new.strip()
            if any(c in new for c in '/\\:*?"<>|') or new in (".", ".."):
                messagebox.showwarning("New folder", "That name has characters a file name cannot have.")
                return
            dest = os.path.join(p.dir, new)
            if os.path.exists(dest):
                messagebox.showwarning("New folder", "A file with that name already exists.")
                return
            os.mkdir(dest)
        except Exception as ex:
            messagebox.showerror("New folder", f"Could not create it: {ex}")
            return
        status_var.set(f"Created {new}")
        p.refresh(select=dest)

    # ---- the other actions
    def fm_send(tab_name):
        """Send the selected file to a tool tab (Trim, Convert …)."""
        files = [p for p, d in fm_selected() if not d]
        if len(files) != 1 or not is_media_file(files[0]):
            return
        set_source(files[0])
        for path_, en_ in tab_en.items():
            if en_ == tab_name:
                nb.select(path_)
                break

    vu_clock_hook = [None]

    def vu_clock_set(pos, paused, t_meas=None):
        """Tell the VU meter where the Files player is (called with every position report)."""
        if vu_clock_hook[0]:
            vu_clock_hook[0](pos, paused, t_meas or time.monotonic())
    fm_player = {"proc": None, "sock": None, "paused": False, "path": None, "pane": None,
                 "hold": 0.0, "unpause_until": 0.0}
    fm_seek = {"drag": False, "busy": False, "dur": 0}

    def fm_alive():
        """True while the Files player (mpv) is running."""
        p_ = fm_player["proc"]
        return bool(p_) and p_.poll() is None

    def fm_player_ui():
        """Enable / disable the Files player's position slider according to the player state."""
        alive = fm_alive()
        if alive:
            fm_scale.state(["!disabled"])
        else:
            fm_scale.state(["disabled"])
            fm_scale.config(to=1)
            fm_scale.set(0)
            fm_pos_lbl.config(text="0:00")
            fm_dur_lbl.config(text="0:00")
        fm_pause_btn.config(state="normal" if alive else "disabled",
                            text=tr("Resume") if (alive and fm_player["paused"]) else tr("Pause"))
        fm_stop_btn.config(state="normal" if alive else "disabled")
        fm_next_btn.config(state="normal" if alive else "disabled")
        fm_prev_btn.config(state="normal" if alive else "disabled")

    def fm_play():
        """Play the selected file in mpv (a selected folder is opened instead)."""
        sel = fm_selected()
        if len(sel) != 1:
            return
        p, isdir = sel[0]
        if isdir:
            fm_active["p"].go(p)
            return
        player = find_player()
        try:
            if player and player[0] == "mpv":
                fm_start_mpv(player[1], p)
            elif player:  # VLC: plays, but cannot be controlled from here
                subprocess.Popen([player[1], p], creationflags=NO_WINDOW, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=tool_env())
                status_var.set("Playing in VLC (Pause, Stop and the time line only work with mpv).")
            elif IS_WIN:
                os.startfile(p)
            else:
                subprocess.Popen(["open" if IS_MAC else "xdg-open", p])
        except OSError as ex:
            status_var.set(f"Could not play it: {ex}")

    def fm_start_mpv(exe, p):
        """Start mpv for the Files tab with a control socket (and the sound visualiser if it is ticked)."""
        import tempfile
        browse_stop(quiet=True)  # one thing plays at a time
        fm_stop(quiet=True)
        sock = (r"\\.\pipe\faun-mpv-files-%d" % os.getpid() if IS_WIN else
                os.path.join(tempfile.gettempdir(), "faun-mpv-files-%d.sock" % os.getpid()))
        cmd = [exe, "--input-ipc-server=" + sock, "--keep-open=yes"]
        if fm_vis_var.get():  # patterns drawn from the sound
            golden_folder()  # makes the pictures the spiral style needs
            cmd += ["--lavfi-complex=" + visualizer_graph(untr(fm_vis_style_var.get()), ffmpeg_has_pseudocolor()),
                    "--force-window=yes"]
        cmd.append(p)
        proc = subprocess.Popen(cmd, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=tool_env(), cwd=tempfile.gettempdir())
        fm_player.update(proc=proc, sock=sock, paused=False, path=p, pane=fm_active["p"], hold=0.0,
                         unpause_until=0.0)
        fm_seek["dur"] = 0
        status_var.set("Playing " + os.path.basename(p))
        fm_player_ui()

    def fm_stop(quiet=False):
        """Close the Files player."""
        if fm_alive():
            try:
                mpv_ipc(fm_player["sock"], [{"command": ["quit"]}])
            except OSError:
                pass
            try:
                fm_player["proc"].terminate()
            except OSError:
                pass
            if not quiet:
                status_var.set("Stopped.")
        fm_player["proc"], fm_player["paused"] = None, False
        fm_player_ui()

    def fm_pause():
        """Pause / resume the Files player."""
        if not fm_alive():
            return
        fm_player["unpause_until"] = 0.0  # the user decides now: no more automatic "play again"

        def work():
            """Toggle pause in mpv from a background thread and read the new state back."""
            try:
                now = mpv_ipc(fm_player["sock"], [{"command": ["cycle", "pause"], "request_id": 1},
                                                  {"command": ["get_property", "pause"], "request_id": 2}],
                              wait_id=2)
                fm_player["paused"] = bool(now)
            except OSError as ex:
                root.after(0, lambda msg=str(ex): status_var.set(f"Could not reach the player: {msg}"))
            root.after(0, fm_player_ui)
        threading.Thread(target=work, daemon=True).start()

    def fm_next(manual=False, delta=1):
        """Play the next (delta -1: the previous) video / audio file in the folder list."""
        if not fm_alive():
            return
        q = fm_player["pane"] or fm_active["p"]
        kids = list(q.tree.get_children())
        cur = next((i for i in kids if i in q.rows and q.rows[i]["path"] == fm_player["path"]), None)
        if delta > 0:
            cand = kids[(kids.index(cur) + 1 if cur is not None else 0):]
        else:
            cand = list(reversed(kids[:kids.index(cur)])) if cur is not None else []
        nxt = next((i for i in cand if i in q.rows and not q.rows[i]["dir"]
                    and is_media_file(q.rows[i]["path"])), None)
        if not nxt and delta < 0:
            status_var.set("That was the first file in the folder.")
            return
        if not nxt:
            status_var.set("That was the last file in the folder.")
            fm_player["hold"] = time.time() + 3600  # nothing more to start; don't ask again
            return
        path_ = q.rows[nxt]["path"]
        fm_player.update(path=path_, hold=0.0, paused=False, unpause_until=time.time() + 3)
        fm_seek["dur"] = 0
        q.tree.selection_set(nxt)
        q.tree.see(nxt)
        status_var.set(("Playing " if delta > 0 else "Playing previous: ") + os.path.basename(path_))

        def work():
            """Load the chosen file in mpv, then make sure it plays (mpv stays paused after a file ends)."""
            try:
                mpv_ipc(fm_player["sock"], [{"command": ["loadfile", path_, "replace"]}])
                time.sleep(0.6)  # mpv keeps itself paused after the end of a file: say play again
                if time.time() < fm_player["unpause_until"]:  # not if the user paused meanwhile
                    mpv_ipc(fm_player["sock"], [{"command": ["set_property", "pause", False]}])
            except OSError as ex:
                root.after(0, lambda msg=str(ex): status_var.set(f"Could not reach the player: {msg}"))
        threading.Thread(target=work, daemon=True).start()

    def fm_progress_apply(res):
        """Apply what mpv reported: position, length, pause state; go to the next file when this one ended."""
        fm_seek["busy"] = False
        if not res or not fm_alive():
            return
        pos, dur, paused = res.get(1), res.get(2), res.get(3)
        if isinstance(pos, (int, float)):
            vu_clock_set(float(pos), paused is True, fm_player.get("t_meas"))  # keeps the VU meter in step with the sound
        if res.get(4) is True and time.time() > fm_player["hold"]:
            fm_next()  # this file ended: the next one follows
            return
        if paused is True and time.time() < fm_player["unpause_until"] and res.get(4) is not True:
            fm_player["paused"] = False  # the next file was loaded paused: start it
            threading.Thread(target=lambda: mpv_ipc(fm_player["sock"], [
                {"command": ["set_property", "pause", False]}]), daemon=True).start()
            paused = False
        if isinstance(paused, bool) and paused != fm_player["paused"]:
            fm_player["paused"] = paused
            fm_player_ui()
        if isinstance(dur, (int, float)) and dur > 0:
            fm_seek["dur"] = dur
            fm_scale.config(to=dur)
            fm_dur_lbl.config(text=fmt_length(dur))
        if isinstance(pos, (int, float)) and not fm_seek["drag"]:
            fm_scale.set(pos)
            fm_pos_lbl.config(text=fmt_length(pos))

    def fm_progress_ask():
        """Ask mpv for position, length, pause and end-of-file state (runs in a background thread)."""
        t_send = time.monotonic()
        try:
            res = mpv_ipc(fm_player["sock"], [{"command": ["get_property", "time-pos"], "request_id": 1},
                                              {"command": ["get_property", "duration"], "request_id": 2},
                                              {"command": ["get_property", "pause"], "request_id": 3},
                                              {"command": ["get_property", "eof-reached"], "request_id": 4}],
                          wait_ids=[1, 2, 3, 4], timeout=1.0)
        except OSError:
            res = None
        fm_player["t_meas"] = (t_send + time.monotonic()) / 2  # when mpv really answered (not when the main thread got to it)
        root.after(0, lambda: fm_progress_apply(res))

    def fm_player_poll():
        """Every half second: refresh the Files player controls and ask mpv for its position."""
        fm_player_ui()
        if fm_alive() and fm_player["sock"] and not fm_seek["busy"] and not fm_seek["drag"]:
            fm_seek["busy"] = True
            threading.Thread(target=fm_progress_ask, daemon=True).start()
        root.after(500, fm_player_poll)

    def fm_scale_set(event):
        """Move the Files position slider to where the mouse is."""
        if not fm_alive() or not fm_seek["dur"]:
            return "break"
        frac = min(1.0, max(0.0, event.x / max(1, fm_scale.winfo_width())))
        fm_scale.set(frac * fm_seek["dur"])
        fm_pos_lbl.config(text=fmt_length(frac * fm_seek["dur"]))
        return "break"

    def fm_scale_press(event):
        """Mouse pressed on the position slider: start dragging."""
        fm_seek["drag"] = True
        return fm_scale_set(event)

    def fm_scale_release(event):
        """Mouse released on the position slider: jump the player to that time."""
        fm_scale_set(event)
        fm_seek["drag"] = False
        if fm_alive() and fm_seek["dur"]:
            target = float(fm_scale.get())

            def do_seek():
                """Seek mpv to the position chosen on the slider."""
                try:
                    mpv_ipc(fm_player["sock"], [{"command": ["seek", target, "absolute"]}])
                except OSError:
                    pass
            threading.Thread(target=do_seek, daemon=True).start()
        return "break"
    fm_scale.bind("<Button-1>", fm_scale_press)
    fm_scale.bind("<B1-Motion>", fm_scale_set)
    fm_scale.bind("<ButtonRelease-1>", fm_scale_release)

    def fm_vis_changed():
        """Visualizer ticked / style changed: switch it on the running player at once."""
        if not fm_alive() or not fm_player["sock"]:
            return
        on, style = fm_vis_var.get(), untr(fm_vis_style_var.get())

        def work():
            """Apply the visualizer setting to the running mpv player."""
            try:
                if on:
                    golden_folder()
                graph = visualizer_graph(style, ffmpeg_has_pseudocolor()) if on else ""
                msgs = [{"command": ["set_property", "lavfi-complex", graph]}]
                if on:
                    msgs.insert(0, {"command": ["set_property", "force-window", "yes"]})
                mpv_ipc(fm_player["sock"], msgs)
            except OSError as ex:
                root.after(0, lambda msg=str(ex): status_var.set(f"Could not reach the player: {msg}"))
        threading.Thread(target=work, daemon=True).start()

    import atexit
    atexit.register(lambda: fm_player["proc"].terminate() if fm_alive() else None)

    def fm_set_batch_folder(sel_, pane_):
        """Adding from the Files tab: "Save to" of the Batch tab becomes the folder you picked from,
        unless items are still waiting in the list (their plan is not changed under your hands)."""
        if any(not it_["done"] for it_ in batch_items):  # items still waiting: keep their folder
            return
        dirs_ = [p for p, d in sel_ if d]
        folder_ = dirs_[0] if (len(sel_) == 1 and dirs_) else (pane_.dir if pane_ else "")
        if folder_ and os.path.isdir(folder_):
            batch_save_var.set(folder_)

    def fm_to_batch():
        """Send the selected files (folders are searched too) to the Batch tab."""
        files = fm_media_files(deep=True)
        if not files:
            status_var.set("There are no video or audio files in the selection.")
            return
        # leftovers of an earlier run ("Song [id]_norm.mp3" next to "Song [id].mp3") would end up as two
        # items with one clean name: keep one file per song, the one without the app's own suffix
        def has_suffix(p_):
            """True if the file name carries one of the app's own work suffixes (e.g. _norm)."""
            st_ = os.path.splitext(os.path.basename(p_))[0]
            return strip_work_suffixes(st_) != st_
        best = {}
        for p in files:
            key = clean_target_path(p).lower()
            if key not in best or (has_suffix(best[key]) and not has_suffix(p)):
                best[key] = p
        keep = set(best.values())
        dup = sum(1 for p in files if p not in keep)
        files = [p for p in files if p in keep]
        fm_set_batch_folder(fm_selected(), fm_active["p"])
        added = sum(1 for p in files if batch_add("file", p))
        status_var.set(f"Added {added} file(s) to the Batch download list"
                       + (f" ({dup} leftover copies of the same song left out)" if dup else "")
                       + (f" ({len(files) - added} already there)" if added < len(files) else "") + ".")

    def fm_rename():
        """Rename the selected file or folder."""
        sel = fm_selected()
        if len(sel) != 1:
            return
        p = sel[0][0]
        try:
            new = ask_name(root, tk, ttk, tr("Rename"), tr("New name:"), os.path.basename(p))
            if new is None:
                return
            new = new.strip()
            if not new or new == os.path.basename(p):
                return
            if not sel[0][1] and not os.path.splitext(new)[1]:  # typed without an extension: keep the old one
                new += os.path.splitext(p)[1]
            if any(c in new for c in '/\\:*?"<>|') or new in (".", ".."):
                messagebox.showwarning("Rename", "That name has characters a file name cannot have.")
                return
            dest = os.path.join(os.path.dirname(p), new)
            if os.path.exists(dest):
                messagebox.showwarning("Rename", "A file with that name already exists.")
                return
            os.rename(p, dest)
        except Exception as ex:
            messagebox.showerror("Rename", f"Could not rename it: {ex}")
            return
        if src_var.get() == p:
            src_var.set(dest)
        if p in recent_files:
            recent_files[recent_files.index(p)] = dest
        status_var.set(f"Renamed to {new}")
        fm_refresh_all(select=dest)

    def fm_delete():
        """Move the selected files to the Trash after asking."""
        sel = fm_selected()
        if not sel:
            return
        names = "\n".join(os.path.basename(p) for p, _ in sel[:8]) + ("\n…" if len(sel) > 8 else "")
        if not messagebox.askyesno("Move to Trash", f"Move to the Trash?\n\n{names}"):
            return
        failed = []
        for p, _d in sel:
            try:
                move_to_trash(p)
                if p in recent_files:
                    recent_files.remove(p)
            except (OSError, subprocess.SubprocessError) as ex:
                failed.append(f"{os.path.basename(p)}: {ex}")
        fm_refresh_all()
        if failed:
            messagebox.showerror("Move to Trash", "Could not move:\n" + "\n".join(failed[:5]))
        else:
            status_var.set(f"Moved {len(sel)} item(s) to the Trash.")

    def fm_dups_dialog():
        """Find files that exist twice in the active folder (same content, or the same song under a
        slightly different name such as 'Song_norm' / 'Song [id]'), and move the extra copies to the Trash."""
        p0 = fm_active["p"]
        folder = p0.dir if p0 else ""
        if not folder or not os.path.isdir(folder):
            return
        win = tk.Toplevel(root)
        win.title(tr("Duplicate files"))
        win.transient(root)
        try:
            win.geometry("+%d+%d" % (root.winfo_rootx() + 60, root.winfo_rooty() + 60))
        except tk.TclError:
            pass
        f = ttk.Frame(win, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=tr("Folder:") + " " + folder, style="Hint.TLabel").pack(anchor="w")
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(6, 6))
        rec_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text=tr("Include subfolders"), variable=rec_var,
                        command=lambda: scan()).pack(side="left")
        ttk.Button(top, text=tr("Scan again"), command=lambda: scan()).pack(side="left", padx=(12, 0))
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        dt = ttk.Treeview(box, columns=("mark", "size", "date", "where"), show="tree headings",
                          selectmode="browse", height=14)
        dt.heading("#0", text=tr("File"))
        dt.heading("mark", text=tr("Action"))
        dt.heading("size", text=tr("Size"))
        dt.heading("date", text=tr("Modified"))
        dt.heading("where", text=tr("In folder"))
        dt.column("#0", width=380, stretch=True)
        dt.column("mark", width=90, stretch=False)
        dt.column("size", width=80, stretch=False, anchor="e")
        dt.column("date", width=130, stretch=False)
        dt.column("where", width=140, stretch=False)
        sb_ = ttk.Scrollbar(box, command=dt.yview)
        dt.config(yscrollcommand=sb_.set)
        sb_.pack(side="right", fill="y")
        dt.pack(side="left", fill="both", expand=True)
        dt.tag_configure("rm", foreground="#c0392b")
        dt.tag_configure("keep", foreground="#2e8b57")
        info = TrVar(value="")
        ttk.Label(f, textvariable=info, style="Hint.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(f, text=tr("Click a file to switch between keep and remove. Removed files go to the Trash."),
                  style="Hint.TLabel").pack(anchor="w")
        bt = ttk.Frame(f)
        bt.pack(fill="x", pady=(8, 0))
        trash_btn = ttk.Button(bt, text=tr("Move marked to Trash"), command=lambda: trash_marked())
        trash_btn.pack(side="left")
        ttk.Button(bt, text=tr("Select automatically"), command=lambda: auto_pick()).pack(side="left", padx=(8, 0))
        ttk.Button(bt, text=tr("Show in folder"), command=lambda: show_sel()).pack(side="left", padx=(8, 0))
        ttk.Button(bt, text=tr("Close"), command=win.destroy).pack(side="right")
        st = {"groups": [], "files": {}, "marks": {}, "kids": {}, "busy": False, "closed": False}
        win.bind("<Destroy>", lambda e: st.update(closed=True) if e.widget is win else None)
        win.bind("<Escape>", lambda e: win.destroy())

        def summary():
            """Update the summary line of the duplicate finder (groups, files marked, space that would be freed)."""
            rm = [i for i, v in st["marks"].items() if v]
            size = sum(st["files"][i]["size"] for i in rm)
            if st["busy"]:
                info.set("Searching…")
            elif not st["groups"]:
                info.set("No duplicates found.")
            else:
                info.set(f"{len(st['groups'])} group(s) of duplicates. "
                         f"{len(rm)} file(s) marked for the Trash ({human_size(size)}).")
            trash_btn.config(state="normal" if rm and not st["busy"] else "disabled")

        def paint(iid):
            """Show a row as '✓ keep' or '✗ remove'."""
            dt.set(iid, "mark", tr("✗ remove") if st["marks"][iid] else tr("✓ keep"))
            dt.item(iid, tags=("rm" if st["marks"][iid] else "keep",))

        def fill(groups):
            """Fill the duplicate list with the groups found and mark the suggested copies for removal."""
            st["busy"] = False
            if st["closed"]:
                return
            dt.delete(*dt.get_children())
            st.update(groups=groups, files={}, marks={}, kids={})
            fm_dups.clear()
            for g in groups:
                keep = pick_keeper(g)
                why = g[0].get("why", "")
                head = dt.insert("", "end", text=f"{os.path.basename(g[keep]['path'])}  ·  {len(g)} " + tr("files")
                                 + "  ·  " + tr(why), open=True)
                st["kids"][head] = []
                for i, fl in enumerate(g):
                    rel = os.path.relpath(os.path.dirname(fl["path"]), folder)
                    iid = dt.insert(head, "end", text=os.path.basename(fl["path"]), values=(
                        "", human_size(fl["size"]), time.strftime("%Y-%m-%d %H:%M", time.localtime(fl["mtime"])),
                        "." if rel == "." else rel))
                    st["files"][iid] = fl
                    st["marks"][iid] = (i != keep)
                    st["kids"][head].append(iid)
                    paint(iid)
                    fm_dups.add(fl["path"])
            fm_refresh_all()
            summary()

        def scan():
            """Search the folder for duplicates in the background."""
            if st["busy"]:
                return
            st["busy"] = True
            summary()
            rec = rec_var.get()

            def work():
                """Search the folder for duplicates in the background and show the groups when done."""
                try:
                    groups = find_duplicate_groups(folder, rec, True, lambda: st["closed"])
                except Exception:
                    groups = []
                root.after(0, lambda: fill(groups))
            threading.Thread(target=work, daemon=True).start()

        def toggle(event):
            """Click on the mark column: switch between keep and remove (one file of every group always stays)."""
            iid = dt.identify_row(event.y)
            if iid not in st["marks"]:
                return
            head = dt.parent(iid)
            new = not st["marks"][iid]
            if new and all(st["marks"][k] for k in st["kids"][head] if k != iid):
                info.set("Keep at least one file of each group.")
                return
            st["marks"][iid] = new
            paint(iid)
            summary()
        dt.bind("<ButtonRelease-1>", toggle)

        def auto_pick():
            """Mark everything except the best copy of each group."""
            for head, kids in st["kids"].items():
                g = [st["files"][k] for k in kids]
                keep = pick_keeper(g)
                for i, k in enumerate(kids):
                    st["marks"][k] = (i != keep)
                    paint(k)
            summary()

        def show_sel():
            """Show the selected duplicate in the file manager."""
            sel = dt.selection()
            if sel and sel[0] in st["files"]:
                reveal_in_folder(st["files"][sel[0]]["path"])

        def trash_marked():
            """Move the files marked for removal to the Trash."""
            rm = [i for i, v in st["marks"].items() if v]
            if not rm:
                return
            names = "\n".join(os.path.basename(st["files"][i]["path"]) for i in rm[:8]) + ("\n…" if len(rm) > 8 else "")
            if not messagebox.askyesno(tr("Move to Trash"), tr("Move these files to the Trash?") + f"\n\n{names}",
                                       parent=win):
                return
            failed = []
            for i in rm:
                pth = st["files"][i]["path"]
                try:
                    move_to_trash(pth)
                    if pth in recent_files:
                        recent_files.remove(pth)
                except (OSError, subprocess.SubprocessError) as ex:
                    failed.append(f"{os.path.basename(pth)}: {ex}")
            if failed:
                messagebox.showerror(tr("Move to Trash"), "Could not move:\n" + "\n".join(failed[:5]), parent=win)
            else:
                status_var.set(f"Moved {len(rm) - len(failed)} duplicate file(s) to the Trash.")
            fm_refresh_all()
            scan()
        scan()

    def fm_reveal():
        """Show the selected file in the file manager (Finder / Explorer)."""
        sel = fm_selected()
        if len(sel) == 1:
            reveal_in_folder(sel[0][0])

    def fm_open_row(_e=None):
        """Double-click on a row: open a folder, or play a file."""
        sel = fm_selected()
        if len(sel) == 1:
            if sel[0][1]:
                fm_active["p"].go(sel[0][0])
            else:
                fm_play()

    def fm_popup(p, event):
        """Right-click menu of the file lists (items depend on the selection)."""
        fm_set_active(p)
        row_ = p.tree.identify_row(event.y)
        if row_ and row_ not in p.tree.selection():
            p.tree.selection_set(row_)
        # a new menu each time: a Menu created at startup is a window of its own, and on macOS it
        # showed up as a small empty pill on the desktop
        if fm_menu_last["m"] is not None:
            try:
                fm_menu_last["m"].destroy()
            except tk.TclError:
                pass
        fm_menu = fm_menu_last["m"] = tk.Menu(root, tearoff=0)
        sel = fm_selected()
        one_media = len(sel) == 1 and not sel[0][1] and is_media_file(sel[0][0])
        if one_media:
            for tn_ in ("Trim", "Convert", "Compress", "Extract audio", "Remove audio", "Loudness"):
                fm_menu.add_command(label=tr("Use in: ") + tr(tn_), command=lambda n=tn_: fm_send(n))
            fm_menu.add_separator()
        if len(sel) == 1:
            fm_menu.add_command(label=tr("Play") if not sel[0][1] else tr("Open"), command=fm_open_row)
        if any(d or is_media_file(p) for p, d in sel):
            fm_menu.add_command(label=tr("Add to batch"), command=fm_to_batch)
        if sel:
            fm_menu.add_command(label=tr("Copy"), command=lambda: fm_clip_set(False))
            fm_menu.add_command(label=tr("Cut"), command=lambda: fm_clip_set(True))
        if fm_clip["paths"]:
            fm_menu.add_command(label=tr("Paste"), command=fm_paste)
        fm_menu.add_command(label=tr("New folder…"), command=fm_mkdir)
        if len(sel) == 1:
            fm_menu.add_command(label=tr("Rename…"), command=fm_rename)
            fm_menu.add_command(label=fm_show_btn.cget("text"), command=fm_reveal)
        if sel:
            fm_menu.add_command(label=tr("Move to Trash"), command=fm_delete)
        if fm_menu.index("end") is not None:
            fm_menu.tk_popup(event.x_root, event.y_root)

    # keyboard: copy / cut / paste, new folder, delete, switch side
    for q_ in panes:
        for mod_ in ("Control", "Command"):
            for key_, fn_ in (("c", lambda e: fm_clip_set(False)), ("x", lambda e: fm_clip_set(True)),
                              ("v", lambda e: fm_paste())):
                try:
                    q_.tree.bind(f"<{mod_}-{key_}>", fn_)
                except tk.TclError:
                    pass
        q_.tree.bind("<F5>", lambda e: fm_to_other(False))
        q_.tree.bind("<F6>", lambda e: fm_to_other(True))
        q_.tree.bind("<F7>", lambda e: fm_mkdir())
        q_.tree.bind("<Delete>", lambda e: fm_delete())
        q_.tree.bind("<Tab>", lambda e: (fm_set_active(fm_other()), fm_active["p"].tree.focus_set(), "break")[-1])

    # ---- dragging with the mouse: onto the other folder / a folder row, or onto a task tab
    def fm_inside(w, xr, yr):
        """True if the screen point is inside the widget (worked out from its position and size)."""
        try:
            x0, y0 = w.winfo_rootx(), w.winfo_rooty()
            return x0 <= xr < x0 + w.winfo_width() and y0 <= yr < y0 + w.winfo_height()
        except (tk.TclError, TypeError, ValueError):
            return False

    def fm_tab_under(xr, yr):
        """(tab widget path, English name) of the notebook tab label under the screen point, or None."""
        try:
            rx, ry = xr - nb.winfo_rootx(), yr - nb.winfo_rooty()
            tabs_ = nb.tabs()
            el = str(nb.identify(rx, ry))
            if not el or "client" in el:  # not on the row of tab labels
                return None
            idx = int(nb.index(f"@{rx},{ry}"))
            path_ = tabs_[idx] if 0 <= idx < len(tabs_) else None
        except (tk.TclError, IndexError, TypeError, ValueError):
            return None
        if path_ is None:
            return None
        return (path_, tab_en.get(str(path_), "")) if str(path_) in tab_en else None

    def fm_pane_target(xr, yr):
        """(pane, folder) under the screen point: a folder row of a pane, else that pane's own folder."""
        for q in panes:
            if fm_inside(q.box, xr, yr):
                row_ = ""
                if fm_inside(q.tree, xr, yr):
                    try:
                        row_ = q.tree.identify_row(yr - q.tree.winfo_rooty())
                    except tk.TclError:
                        row_ = ""
                r = q.rows.get(row_)
                return (q, r["path"] if (r and r["dir"]) else q.dir)
        return None

    def fm_ghost_show(text, xr, yr):
        """Show or move the small label that follows the mouse while dragging files."""
        g = fm_drag["ghost"]
        if g is None:
            try:
                g = tk.Toplevel(root)
                g.wm_overrideredirect(True)
                try:
                    g.wm_attributes("-topmost", True)
                except tk.TclError:
                    pass
                ttk.Label(g, text=text, padding=(8, 4), relief="solid").pack()
                fm_drag["ghost"] = g
            except tk.TclError:
                return
        try:
            g.geometry(f"+{xr + 14}+{yr + 14}")
        except tk.TclError:
            pass

    def fm_drag_end():
        """End a drag: remove the label."""
        g = fm_drag["ghost"]
        fm_drag["ghost"] = None
        if g is not None:
            try:
                g.destroy()
            except tk.TclError:
                pass
        try:
            root.config(cursor="")
        except tk.TclError:
            pass
        fm_drag["active"] = False

    def fm_press(p, event):
        """Mouse pressed on a file row: remember it, a drag starts after a few pixels of movement."""
        fm_set_active(p)
        row_ = p.tree.identify_row(event.y)
        fm_drag.update(press=(event.x_root, event.y_root), rows=[], active=False, src=p, clicked=None)
        if not row_ or row_ not in p.rows or (event.state & 0x000D):  # a modifier click only selects
            fm_drag["press"] = None
            return None
        sel = list(p.tree.selection())
        if row_ in sel and len(sel) > 1:  # keep a multiple selection to drag it
            fm_drag["rows"], fm_drag["clicked"] = sel, row_
            return "break"
        fm_drag["rows"] = [row_]
        return None

    def fm_motion_ev(p, event):
        """Mouse moved with the button down. Dragging a row drags the FILE, it never selects the rows it
        passes over; selecting several by dragging over them needs Shift held (Cmd/Ctrl-click also works)."""
        if fm_drag["press"] is None and not fm_drag["active"]:
            return None if (event.state & 0x0001) else "break"
        fm_motion(p, event)
        return "break"

    def fm_motion(p, event):
        """Mouse moved while the button is down: start the drag and mark the folder under the mouse."""
        if not fm_drag["press"] or not fm_drag["rows"] or fm_drag["src"] is not p:
            return
        if not fm_drag["active"]:
            if abs(event.x_root - fm_drag["press"][0]) + abs(event.y_root - fm_drag["press"][1]) < 8:
                return
            fm_drag["active"] = True
            if fm_drag["clicked"] is None and fm_drag["rows"][0] not in p.tree.selection():
                p.tree.selection_set(fm_drag["rows"][0])
            try:
                root.config(cursor="hand2")
            except tk.TclError:
                pass
        names = [os.path.basename(p.rows[i]["path"]) for i in fm_drag["rows"] if i in p.rows]
        fm_ghost_show(names[0] if len(names) == 1 else f"{len(names)} files", event.x_root, event.y_root)
        hit = fm_tab_under(event.x_root, event.y_root)
        tgt = fm_pane_target(event.x_root, event.y_root)
        if hit and hit[1] in DRAG_TABS:
            status_var.set(tr("Release on a tab to use the file there:") + " " + tr(hit[1]))
        elif tgt and not (tgt[0] is p and tgt[1] == p.dir):
            status_var.set(tr("Release to copy into:") + " " + tgt[1] + "   (" + tr("hold Shift to move") + ")")
        else:
            status_var.set(tr("Drag the file onto a tab (Trim, Convert, …) or the other folder."))

    def fm_release(p, event):
        """Mouse released: drop the dragged rows onto a folder or the other pane (copy / move)."""
        was = fm_drag["active"]
        rows_ = [p.rows[i] for i in fm_drag["rows"] if i in p.rows]
        clicked = fm_drag.get("clicked")
        fm_drag.update(press=None, rows=[], clicked=None)
        fm_drag_end()
        if not was or fm_drag["src"] is not p:
            if clicked and not was:  # a plain click on one row of a multiple selection
                p.tree.selection_set(clicked)
            return
        paths = [r["path"] for r in rows_]
        files = [r["path"] for r in rows_ if not r["dir"] and is_media_file(r["path"])]
        if fm_tab_under(event.x_root, event.y_root) and fm_tab_under(event.x_root, event.y_root)[1] == "Batch download":
            files = fm_media_files(deep=True) if set(r["path"] for r in rows_) == set(p_ for p_, _ in fm_selected()) else files
        hit = fm_tab_under(event.x_root, event.y_root)
        tgt = fm_pane_target(event.x_root, event.y_root)
        if hit and hit[1] in DRAG_TABS:
            if not files:
                status_var.set("Only video and audio files can be dragged onto a tab.")
            elif hit[1] == "Batch download":
                fm_set_batch_folder([(r["path"], r["dir"]) for r in rows_], p)
                added = sum(1 for f_ in files if batch_add("file", f_))
                nb.select(hit[0])
                status_var.set(f"Added {added} file(s) to the batch.")
            else:
                set_source(files[0])
                nb.select(hit[0])
                status_var.set(f"{os.path.basename(files[0])} loaded."
                               + (" Only the first file is used here: use Batch download for several."
                                  if len(files) > 1 else ""))
        elif tgt and not (tgt[0] is p and tgt[1] == p.dir):
            fm_transfer(paths, tgt[1], bool(event.state & 0x0001))  # copy; Shift = move
        elif fm_inside(src_entry, event.x_root, event.y_root) and files:
            set_source(files[0])
            status_var.set(f"{os.path.basename(files[0])} loaded.")
        else:
            status_var.set("Drop the file onto a tab (Trim, Convert, …) or into the other folder.")

    def fm_on_tab():
        """Files tab opened: show the folders of both panes."""
        if task() == "Files":
            for q in panes:
                if not q.dir or not os.path.isdir(q.dir):
                    q.go(q.dir_var.get() if os.path.isdir(os.path.expanduser(q.dir_var.get())) else dl_dir_var.get())
                else:
                    q.refresh(keep=True)
            fm_set_active(fm_active["p"])

    # Loudness
    t = tab("Loudness")
    norm_var = tk.StringVar(value=list(NORM_TARGETS)[1])
    norm_val_var = tk.DoubleVar(value=-16.0)
    norm_text_var = tk.StringVar()
    norm_combo = combo(t, norm_var, list(NORM_TARGETS), 30)
    row(t, 0, "Preset", norm_combo)

    SCALE_LEN, SCALE_PAD = 340, 10
    f_sl = ttk.Frame(t)
    ttk.Button(f_sl, text="−", width=2, command=lambda: nudge_norm(-0.5)).grid(
        row=0, column=0, padx=(0, 6))
    norm_scale = ttk.Scale(f_sl, from_=NORM_MIN, to=NORM_MAX, orient="horizontal",
                           length=SCALE_LEN, variable=norm_val_var,
                           command=lambda v: on_norm_slide(v))
    norm_scale.grid(row=0, column=1)
    ttk.Button(f_sl, text="+", width=2, command=lambda: nudge_norm(0.5)).grid(
        row=0, column=2, padx=(6, 0))
    ttk.Label(f_sl, textvariable=norm_text_var, width=11).grid(row=0, column=3, padx=(10, 0))
    ticks = ttk.Frame(f_sl, width=SCALE_LEN, height=18)
    ticks.grid(row=1, column=1, sticky="w")
    for mark in range(int(NORM_MIN), int(NORM_MAX) + 1, 5):
        frac = (mark - NORM_MIN) / (NORM_MAX - NORM_MIN)
        x = SCALE_PAD + frac * (SCALE_LEN - 2 * SCALE_PAD)
        ttk.Label(ticks, text=str(mark), style="Hint.TLabel").place(x=int(x), y=0, anchor="n")
    row(t, 1, "Target level", f_sl)
    hint(t, 2, "Pick a preset or drag the slider (or use − / +) for your own level in LUFS.\n"
               "Closer to 0 = louder. Very high levels (above about -12) get limited and can sound squashed.\n"
               "Every video set to the same level plays at the same volume. The picture is copied\n"
               "untouched (fast); only the sound is re-encoded. Keeps the first audio track.")

    loud_prev = {"busy": False, "orig": None, "adj": None, "proc": None, "meas": {}}
    lp_at_var = tk.StringVar()
    lp_info = TrVar(value="")
    f_lp = ttk.Frame(t)
    ttk.Label(f_lp, text="from").pack(side="left")
    ttk.Entry(f_lp, textvariable=lp_at_var, width=8).pack(side="left", padx=(4, 6))
    lp_make_btn = ttk.Button(f_lp, text="Measure and make preview", command=lambda: loudness_preview())
    lp_make_btn.pack(side="left")
    ttk.Label(f_lp, text="  (15 s sample; empty = from the middle)", style="Hint.TLabel").pack(side="left")
    row(t, 3, "Preview", f_lp)
    f_lp2 = ttk.Frame(t)
    lp_orig_btn = ttk.Button(f_lp2, text="▶ Original", width=12, state="disabled",
                             command=lambda: loudness_play("orig"))
    lp_orig_btn.pack(side="left")
    lp_adj_btn = ttk.Button(f_lp2, text="▶ Adjusted", width=12, state="disabled",
                            command=lambda: loudness_play("adj"))
    lp_adj_btn.pack(side="left", padx=(6, 0))
    ttk.Button(f_lp2, text="Stop", width=6, command=lambda: loudness_play(None)).pack(side="left", padx=(6, 0))
    f_lp2.grid(row=4, column=1, sticky="w", pady=(2, 0))
    ttk.Label(t, textvariable=lp_info, style="Hint.TLabel", justify="left").grid(
        row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def loudness_preview():
        """Measure the loaded file, then cut a short piece twice (as it is / with the new level) so the
        two can be compared by ear."""
        if loud_prev["busy"]:
            return
        src = src_var.get()
        ffmpeg = find_tool("ffmpeg")
        if not os.path.isfile(src) or not ffmpeg:
            messagebox.showwarning("No file", "Open a video or audio file first.")
            return
        dur = state["duration"] or 0
        n_ = 15.0 if not dur else min(15.0, dur)
        try:
            at_ = to_seconds(lp_at_var.get())
        except ValueError:
            messagebox.showwarning("Bad time", "Enter the start as seconds or m:ss, e.g. 1:30.")
            return
        if at_ is None:
            at_ = max(0.0, (dur - n_) / 2)
        at_ = max(0.0, min(at_, max(0.0, dur - n_))) if dur else at_
        target, lra = norm_params(norm_val_var.get())
        loudness_play(None)
        loud_prev["busy"] = True
        lp_make_btn.config(state="disabled")
        lp_orig_btn.config(state="disabled")
        lp_adj_btn.config(state="disabled")
        lp_info.set("Measuring the loudness…")
        import tempfile
        tmp = tempfile.gettempdir()
        o_path = os.path.join(tmp, f"faun-loud-orig-{os.getpid()}.wav")
        a_path = os.path.join(tmp, f"faun-loud-adj-{os.getpid()}.wav")
        key = (src, os.path.getmtime(src))

        def run(args):
            """Run ffmpeg with the given arguments and return the finished process."""
            return subprocess.run([ffmpeg] + args, capture_output=True, timeout=900, env=tool_env(),
                                  stdin=subprocess.DEVNULL, **TEXT)  # (TEXT already hides the console window)

        def work():
            """Measure the loudness (or reuse the cached result), cut the sample files, then report back."""
            err, m = "", loud_prev["meas"].get(key)
            try:
                if not m:
                    r = run(build_norm_analysis(src, target, lra))
                    text = (r.stderr or "") + (r.stdout or "")
                    m = parse_loudnorm(text)
                    if r.returncode != 0 or not m:
                        raise RuntimeError("This file has no audio track to adjust."
                                           if "matches no streams" in text.lower() else
                                           short_error(text or "Could not measure the loudness.", 160))
                    loud_prev["meas"][key] = m
                if not math.isfinite(m["input_i"]):
                    raise RuntimeError("The audio is silent, so there is no loudness to match.")
                seg = ["-y", "-hide_banner", "-ss", f"{at_:.3f}", "-t", f"{n_:.3f}", "-i", src,
                       "-map", "0:a:0", "-vn", "-sn", "-dn"]
                for path_, extra in ((o_path, []),
                                     (a_path, ["-af", norm_filter(target, lra, m), "-ar", "48000"])):
                    try:
                        os.remove(path_)
                    except OSError:
                        pass
                    r = run(seg + extra + ["-c:a", "pcm_s16le", path_])
                    if r.returncode != 0 or not os.path.isfile(path_):
                        raise RuntimeError(short_error(r.stderr or "ffmpeg failed.", 160))
            except Exception as ex:
                err = str(ex)
            root.after(0, lambda: loudness_preview_done(err, m, target, o_path, a_path, at_, n_))
        threading.Thread(target=work, daemon=True).start()

    def loudness_preview_done(err, m, target, o_path, a_path, at_, n_):
        """The loudness preview files are ready: show the gain that would be applied and enable the playback buttons."""
        loud_prev["busy"] = False
        lp_make_btn.config(state="normal")
        if err:
            lp_info.set(f"Preview failed: {err}")
            return
        gain = target - m["input_i"]
        loud_prev.update(orig=o_path, adj=a_path)
        lp_orig_btn.config(state="normal")
        lp_adj_btn.config(state="normal")
        lp_info.set(f"This file: {m['input_i']:.1f} LUFS (peak {m['input_tp']:.1f} dBTP). "
                    f"Target {target:g} LUFS: {gain:+.1f} dB. "
                    f"Listen to {fmt_length(n_)} from {fmt_length(at_)}, as it is and adjusted.")

    def loudness_play(which):
        """Play the original or the adjusted sample (None: just stop what is playing)."""
        p_ = loud_prev.get("proc")
        if p_ and p_.poll() is None:
            try:
                p_.terminate()
            except OSError:
                pass
        loud_prev["proc"] = None
        path_ = loud_prev.get(which) if which else None
        if not path_ or not os.path.isfile(path_):
            return
        pl = find_player()
        try:
            if pl and pl[0] == "mpv":
                loud_prev["proc"] = subprocess.Popen(
                    [pl[1], path_, "--keep-open=yes", "--force-window=yes",
                     "--title=" + ("Original" if which == "orig" else "Adjusted")],
                    env=tool_env(), creationflags=NO_WINDOW, stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif pl:
                loud_prev["proc"] = subprocess.Popen([pl[1], path_], creationflags=NO_WINDOW)
            else:
                status_var.set("No player found: install mpv from the Setup tab to listen to the preview.")
        except OSError as ex:
            status_var.set(f"Could not start the player: {ex}")

    def update_norm_label():
        """Show the chosen loudness target as text and as a preset name."""
        v = norm_params(norm_val_var.get())[0]
        norm_text_var.set(f"{v:.1f} LUFS")
        norm_var.set(norm_label(v))

    def on_norm_slide(val):
        """Loudness slider moved: snap to half steps."""
        v = norm_params(val)[0]
        if v != norm_val_var.get():
            norm_val_var.set(v)  # snap to 0.5 steps
        update_norm_label()

    def on_norm_preset(_event=None):
        """Loudness preset chosen: move the slider to its value."""
        entry = NORM_TARGETS.get(norm_var.get())
        if entry:
            norm_val_var.set(entry[0])
        update_norm_label()

    def nudge_norm(delta):
        """Move the loudness target by a step (the +/- buttons)."""
        norm_val_var.set(norm_params(float(norm_val_var.get()) + delta)[0])
        update_norm_label()

    norm_combo.bind("<<ComboboxSelected>>", on_norm_preset)

    nb.select(setup_tab)  # the app always opens on the Setup tab

    # --- GPU option (detected in the background: VideoToolbox / NVENC / QSV / AMF)
    gpu_var = tk.BooleanVar(value=False)
    f_bottom = ttk.Frame(main)  # options on the left, the file's cover and tags on the right
    f_bottom.pack(fill="x")

    def panel_colours(dark):
        """(panel background, caption, text, window background, line) of the cover/tags panel.
        The panel has the colour of the tab area; the corners outside it have the window colour."""
        if IS_WIN:
            bg_ = win_ = DARK["bg"] if dark else "SystemButtonFace"
        else:
            try:  # macOS: the tab area is a little lighter than the window in dark mode
                r_, g_, b_ = root.winfo_rgb("systemWindowBackgroundColor")
                dark = (r_ + g_ + b_) / 3 < 32768
                win_ = "systemWindowBackgroundColor"
                bg_ = "#232323" if dark else win_
            except (tk.TclError, ValueError):
                win_ = "#1e1e1e" if dark else "#ececec"
                bg_ = "#232323" if dark else "#ececec"
        return (bg_, "#c4c4c4" if dark else "#444444", "#ffffff" if dark else "#000000",
                win_, "#4a4a4a" if dark else "#c0c0c0")
    vu_hook = [lambda: None]  # redraws the VU meter after a colour change (set where the meter is built)
    bordered_frames = []  # rounded boxes (canvases), recoloured with the theme: (canvas, on_window)

    def bordered(parent, on_window=False, radius=10, lift=False, **kw):
        """A box with rounded corners and a thin line, like the tab area (a canvas drawing the shape)."""
        w_, h_ = kw.pop("width") + 2, kw.pop("height") + 2
        cv_ = tk.Canvas(parent, width=w_, height=h_, highlightthickness=0, borderwidth=0, **kw)

        def reshape(w2, h2=None):
            """Draw the rounded box again for a new size (the panel gets narrower in a small window)."""
            h2 = h2 or int(cv_.cget("height"))
            cv_.configure(width=w2, height=h2)
            cv_.delete("box")
            r2, x1, y1, x2, y2 = radius, 1, 1, w2 - 1, h2 - 1
            pts = [x1 + r2, y1, x2 - r2, y1, x2, y1, x2, y1 + r2, x2, y2 - r2, x2, y2, x2 - r2, y2,
                   x1 + r2, y2, x1, y2, x1, y2 - r2, x1, y1 + r2, x1, y1]
            cv_.create_polygon(pts, smooth=True, tags="box", fill=cv_.box_fill, outline=cv_.box_line)
            cv_.tag_lower("box")
        cv_.box_fill, cv_.box_line = "", ""
        cv_.reshape = reshape
        reshape(w_, h_)
        bordered_frames.append((cv_, on_window, lift))
        return cv_
    f_info = bordered(f_bottom, on_window=True, radius=12, width=430, height=150)  # fixed size and place: never moves with the text
    f_info.place(relx=1.0, x=0, y=0, anchor="ne")  # exact spot is set by place_info_panel()
    f_info.pack_propagate(False)
    f_info.grid_propagate(False)
    f_bottom.grid_rowconfigure(0, minsize=40)  # room for the panel, which is placed (not gridded)
    INFO_H = 150 + 2  # panel height (with border)
    # on macOS the tab area is drawn about 17 px inside its widget; the gap above/below is the visible one
    NB_INSET, INFO_GAP = (17, 16) if IS_MAC else (0, 10)

    INFO_W_now = [0]

    def place_info_panel(_e=None):
        """Right edge of the panel = right edge of the tab area; same gap above (to the tab area)
        and below (to the progress bar)."""
        try:
            root.update_idletasks()
            right_off = ((f_bottom.winfo_rootx() + f_bottom.winfo_width())
                         - (nb.winfo_rootx() + nb.winfo_width()) + NB_INSET)
            nb_bottom = nb.winfo_rooty() + nb.winfo_height()
            y_ = max(0, INFO_GAP - NB_INSET - (f_bottom.winfo_rooty() - nb_bottom))
            if f_bottom.winfo_width() < 50:  # not laid out yet
                return
            # the free space right of the options is shared: the tags panel (250 - 430 px) and, if there is
            # room for it (at least 190 px), the VU meter left of it
            gap_ = 12
            free_ = f_bottom.winfo_width() - max(0, right_off) - f_left.winfo_reqwidth() - gap_
            vu_min_ = 190
            if free_ >= 250 + gap_ + vu_min_:
                pw_ = max(250, min(430, free_ - gap_ - vu_min_))
                vw_ = min(460, free_ - pw_ - gap_)
            else:
                pw_, vw_ = max(250, min(430, free_)), 0
            if pw_ + 2 != INFO_W_now[0]:
                INFO_W_now[0] = pw_ + 2
                f_info.reshape(pw_ + 2)
                fw_ = pw_ - 122 - 8
                for fc_ in info_fields:
                    fc_.reshape(fw_ + 2)
            f_info.place_configure(relx=1.0, x=-max(0, right_off), y=y_, anchor="ne")
            if vw_:
                if vw_ + 2 != int(f_vu.cget("width")):
                    f_vu.reshape(vw_ + 2)
                    vu_build()
                f_vu.place_configure(relx=1.0, x=-(max(0, right_off) + pw_ + 2 + gap_), y=y_, anchor="ne")
            else:
                f_vu.place_forget()
            top_vis_ = y_ + (f_bottom.winfo_rooty() - nb_bottom) + NB_INSET  # visible gap above the panel
            need_ = max(40, y_ + INFO_H + top_vis_)  # the same gap below it
            if int(f_bottom.grid_rowconfigure(0)["minsize"]) != need_:
                f_bottom.grid_rowconfigure(0, minsize=need_)
        except (tk.TclError, ValueError):
            pass
    f_bottom.bind("<Configure>", lambda e: root.after_idle(place_info_panel))
    nb.bind("<Configure>", lambda e: root.after_idle(place_info_panel), add="+")
    f_bottom.grid_columnconfigure(0, weight=1)
    f_left = ttk.Frame(f_bottom)
    f_left.grid(row=0, column=0, sticky="nw")
    gpu_cb = ttk.Checkbutton(f_left, text="GPU / hardware encoder: detecting…",
                             variable=gpu_var, state="disabled")
    gpu_cb.pack(anchor="w", pady=(0, 6))

    # --- naming: ONE setting for the whole app (Download tab, Batch, and every Save dialog)
    f_name = ttk.Frame(f_left)
    f_name.pack(anchor="w", pady=(0, 6))
    ttk.Checkbutton(f_name, text="Clean file names", variable=clean_var).pack(side="left")
    strip_cb = ttk.Checkbutton(f_name, text="Remove tags like (Official Video), (Audio)",
                               variable=strip_tags_var)
    strip_cb.pack(side="left", padx=(12, 0))
    ttk.Checkbutton(f_name, text="Embed cover art (mp3 / m4a)", variable=cover_var).pack(
        side="left", padx=(12, 0))
    f_name2 = ttk.Frame(f_left)
    f_name2.pack(anchor="w", pady=(0, 6))
    extra_label = ttk.Label(f_name2, text="Also remove these tags:")
    extra_label.pack(side="left")
    extra_entry = ttk.Entry(f_name2, textvariable=extra_tags_var, width=24)
    extra_entry.pack(side="left", padx=(8, 8))
    ttk.Label(f_name2, text="comma-separated, e.g.  OST, *soundtrack*   (* = anything)",
              style="Hint.TLabel", wraplength=250, justify="left").pack(side="left")

    opt_help = HelpBox(f_left, wrap=600)  # no wider than the tick boxes above it (room for the VU meter)
    opt_help_lbl = opt_help

    def update_opt_help(*_):
        """Fill the explanation boxes for the options that are ticked."""
        items = []
        if gpu_var.get() and gpu_cb.cget("state") != "disabled":
            items.append(("GPU / hardware encoder", "Encodes on the graphics chip, usually several times faster (slightly larger files)."))
        if clean_var.get():
            items.append(("Clean file names", "Tidies names of downloaded and saved files (underscores, double spaces, stray symbols)."))
        if clean_var.get() and strip_tags_var.get():
            items.append(("Remove tags", "Cuts bracketed extras like (Official Video) or [Audio] from names."))
        if cover_var.get():
            items.append(("Embed cover art", "Puts the video's thumbnail into downloaded audio (mp3). Extract audio (mp3 / m4a) uses the file's own picture, or a frame from the video."))
        opt_help.set_items(items)
        lines = items
        if lines and not opt_help_shown[0]:
            opt_help_lbl.pack(anchor="w", pady=(0, 6))
            opt_help_shown[0] = True
        elif not lines and opt_help_shown[0]:
            opt_help_lbl.pack_forget()
            opt_help_shown[0] = False

    pb_ref, opt_help_shown = [], [False]
    for v_ in (gpu_var, clean_var, strip_tags_var, cover_var):
        v_.trace_add("write", update_opt_help)

    # --- progress + buttons
    pb = ttk.Progressbar(main, mode="determinate", maximum=100)
    pb_ref.append(pb)
    pb.pack(fill="x")
    f_btn = ttk.Frame(main)
    f_btn.pack(fill="x", pady=(8, 0))
    ttk.Label(f_btn, textvariable=status_var, style="Hint.TLabel").pack(side="left")
    cancel_btn = ttk.Button(f_btn, text="Cancel", state="disabled", command=lambda: cancel())
    cancel_btn.pack(side="right")
    go_btn = ttk.Button(f_btn, text="Start", style="Go.TButton", command=lambda: start())
    go_btn.pack(side="right", padx=6)

    # --- the cover and the tags of the file you are looking at (right of the options)
    info_title_var, info_artist_var, info_album_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
    info_hint_var = tk.StringVar(value="Select a file to see its cover and tags")
    info_state = {"gen": 0, "path": None, "stamp": None, "img": None, "cache": {}}
    info_blank = tk.PhotoImage(width=100, height=100)
    f_cov = bordered(f_info, radius=8, width=104, height=104)  # the cover, in its own frame
    f_cov.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(8, 8), pady=(8, 0))
    f_cov.grid_propagate(False)
    info_fields = []  # the three boxes of Title / Artist / Album (they get narrower with the window)
    panel_labels = []  # plain Tk labels (they take the panel colours reliably); (label, is_caption)

    def panel_label(parent, caption=False, lift=False, **kw):
        """Make a plain Tk label for the info panel and remember it so the theme can recolour it."""
        lb_ = tk.Label(parent, borderwidth=0, highlightthickness=0, padx=0, pady=0, **kw)
        panel_labels.append((lb_, caption, lift))
        return lb_
    info_cover = panel_label(f_cov, image=info_blank)
    info_cover.place(relx=0.5, rely=0.5, anchor="center")
    info_cover.image = info_blank
    for r_, (cap_, var_) in enumerate((("Title", info_title_var), ("Artist", info_artist_var),
                                       ("Album", info_album_var))):
        f_ = bordered(f_info, radius=8, width=292, height=34)  # one frame per field
        info_fields.append(f_)
        f_.grid(row=r_, column=1, sticky="nw", pady=(8 if r_ == 0 else 3, 0))
        f_.grid_propagate(False)
        panel_label(f_, caption=True, text=cap_, font=(UI_FONT, 9)).place(x=8, y=1)
        panel_label(f_, textvariable=var_,
                    font=(UI_FONT, 11, "bold") if r_ == 0 else (UI_FONT, 11)).place(x=8, y=15)
    panel_label(f_info, caption=True, textvariable=info_hint_var, font=(UI_FONT, 9)).grid(
        row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(3, 0))


    # --- VU meter: the loudness of what the Files player is playing (between the options and the tags)
    f_vu = bordered(f_bottom, on_window=True, radius=12, width=300, height=150)
    f_vu.grid_propagate(False)
    vu = {"path": None, "data": [], "stop": {}, "clock": (0.0, 0.0, False), "disp": [-60.0, -60.0],
          "peak": [-60.0, -60.0], "peak_t": [0.0, 0.0], "last": 0.0, "w": 0, "segs": [], "marks": [],
          "txt": None, "shown": False}
    VU_LO = -48.0  # the bottom of the scale in dB (0 dB = full scale)

    vu_style_var = tk.StringVar(value="Bars")  # "Bars" or "Needle" (remembered)

    vu_style_var.trace_add("write", lambda *_a: vu_build())  # also when the remembered style is loaded

    def vu_set_style(name):
        """Switch between the lit bars and the analogue needles."""
        if vu_style_var.get() != name:
            vu_style_var.set(name)

    def vu_build(*_a):
        """Draw the scale and the meter again, e.g. after a resize, a colour change or a style switch."""
        bg_, cap_, txt_, win_, line_ = panel_colours(IS_WIN and dark_var.get())
        dark_ = cap_ == "#c4c4c4"
        w_ = int(f_vu.cget("width"))
        style_ = vu_style_var.get() if vu_style_var.get() in ("Bars", "Needle") else "Bars"
        f_vu.delete("vu")
        vu["style"] = style_
        vu["off"] = "#343434" if dark_ else "#d0d0d0"
        f_vu.create_text(14, 16, text="VU", anchor="w", fill=txt_, font=(UI_FONT, 11, "bold"), tags="vu")
        for k_, (nm_, xx_) in enumerate((("Bars", 40), ("Needle", 82))):  # the two clickable style names
            on_ = nm_ == style_
            t_ = f_vu.create_text(xx_, 16, text=tr(nm_), anchor="w", fill=txt_ if on_ else cap_,
                                  font=(UI_FONT, 9, "bold" if on_ else "normal", "underline") if not on_ else
                                  (UI_FONT, 9, "bold"), tags=("vu", "vusw"))
            f_vu.tag_bind(t_, "<Button-1>", lambda e, n=nm_: vu_set_style(n))
            f_vu.tag_bind(t_, "<Enter>", lambda e: f_vu.configure(cursor="pointinghand" if IS_MAC else "hand2"))
            f_vu.tag_bind(t_, "<Leave>", lambda e: f_vu.configure(cursor=""))
        vu["txt"] = f_vu.create_text(w_ - 14, 16, text="", anchor="e", fill=cap_, font=(UI_FONT, 8 if w_ < 280 else 9), tags="vu")
        vu["w"] = w_
        vu["txt_last"] = ""
        vu["narrow"] = w_ < 280  # little room: show only the louder channel so the style names stay clickable
        vu["disp"], vu["peak"] = [-60.0, -60.0], [-60.0, -60.0]
        if style_ == "Bars":
            x0, x1 = 34, w_ - 16
            n = max(10, (x1 - x0) // 8)
            vu["n"], vu["x0"], vu["x1"] = n, x0, x1
            vu["segs"], vu["marks"] = [], []
            for ch, (yy, name) in enumerate(((38, "L"), (84, "R"))):
                f_vu.create_text(14, yy + 14, text=name, anchor="w", fill=cap_, font=(UI_FONT, 10, "bold"), tags="vu")
                row = []
                for i in range(n):
                    xa = x0 + (x1 - x0) * i / n
                    xb = x0 + (x1 - x0) * (i + 1) / n - 2
                    row.append(f_vu.create_rectangle(xa, yy, xb, yy + 28, fill=vu["off"], outline="", tags="vu"))
                vu["segs"].append(row)
                vu["marks"].append(f_vu.create_rectangle(x0, yy - 3, x0 + 3, yy + 31, fill="#ffffff", outline="",
                                                         tags="vu"))
            for db in (-48, -36, -24, -12, -6, 0):  # the scale below the bars
                xx = x0 + (x1 - x0) * (db - VU_LO) / (0 - VU_LO)
                f_vu.create_text(min(xx, x1), 130, text=str(db), fill=cap_, font=(UI_FONT, 8), tags="vu")
            vu["lit"] = [[None] * n, [None] * n]
        else:  # two analogue dials, one for each channel
            vu["dials"], vu["needles"], vu["pmarks"] = [], [], []
            dw = (w_ - 3 * 14) / 2
            r = max(30, min(dw / 1.64 - 4, 76))  # the dial spans about 1.64 radii across
            cy = 118
            for ch, name in enumerate(("L", "R")):
                cx = 14 + dw / 2 + ch * (dw + 14)
                vu["dials"].append((cx, cy, r))
                for lo, hi, col in ((VU_LO, -18, "#35c759"), (-18, -9, "#ffd60a"), (-9, 0, "#ff453a")):
                    a0 = 145 - 110 * (lo - VU_LO) / (0 - VU_LO)  # angle of the start of this colour zone
                    a1 = 145 - 110 * (hi - VU_LO) / (0 - VU_LO)
                    f_vu.create_arc(cx - r, cy - r, cx + r, cy + r, start=a1, extent=a0 - a1, style="arc",
                                    outline=col, width=5, tags="vu")
                for db in (-48, -36, -24, -12, -6, 0):  # ticks and numbers
                    ang = math.radians(145 - 110 * (db - VU_LO) / (0 - VU_LO))
                    f_vu.create_line(cx + (r - 8) * math.cos(ang), cy - (r - 8) * math.sin(ang),
                                     cx + (r + 1) * math.cos(ang), cy - (r + 1) * math.sin(ang),
                                     fill=cap_, width=1, tags="vu")
                    if db in (-36, -12, 0):
                        f_vu.create_text(cx + (r - 18) * math.cos(ang), cy - (r - 18) * math.sin(ang), text=str(db),
                                         fill=cap_, font=(UI_FONT, 8), tags="vu")
                f_vu.create_text(cx, cy + 14, text=name, fill=cap_, font=(UI_FONT, 10, "bold"), tags="vu")
                vu["pmarks"].append(f_vu.create_line(cx, cy, cx, cy, fill="#ffffff", width=2, tags="vu"))
                vu["needles"].append(f_vu.create_line(cx, cy, cx, cy - r, fill=txt_, width=2, capstyle="round",
                                                      tags="vu"))
                f_vu.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=txt_, outline="", tags="vu")
    vu_hook[0] = vu_build

    def vu_colour(i, n):
        """Colour of the lit segment number i: green, then yellow, then red near full scale."""
        db = VU_LO + (0 - VU_LO) * (i + 1) / n
        return "#35c759" if db < -18 else ("#ffd60a" if db < -9 else "#ff453a")

    def vu_draw():
        """Light the segments up to the current levels (or swing the needles) and move the peak markers."""
        txt_now = (((("%.1f dB" % max(vu["disp"])) if vu.get("narrow") else
                     "L %5.1f   R %5.1f dB" % (vu["disp"][0], vu["disp"][1])))
                   if vu["disp"][0] > -59 or vu["disp"][1] > -59 else "")
        t_now = time.monotonic()
        if txt_now != vu.get("txt_last") and t_now - vu.get("txt_t", 0.0) > 0.12:  # the numbers: ~8 times a second
            vu["txt_last"], vu["txt_t"] = txt_now, t_now
            f_vu.itemconfigure(vu["txt"], text=txt_now)
        if vu.get("style") == "Needle":
            for ch in (0, 1):
                cx, cy, r = vu["dials"][ch]
                for key_, db_, r0_, r1_ in (("needles", vu["disp"][ch], 0, r - 3), ("pmarks", vu["peak"][ch], r - 14, r + 2)):
                    fr_ = min(1.0, max(0.0, (db_ - VU_LO) / (0 - VU_LO)))
                    ang = math.radians(145 - 110 * fr_)
                    f_vu.coords(vu[key_][ch], cx + r0_ * math.cos(ang), cy - r0_ * math.sin(ang),
                                cx + r1_ * math.cos(ang), cy - r1_ * math.sin(ang))
                f_vu.itemconfigure(vu["pmarks"][ch], state="normal" if vu["peak"][ch] > VU_LO else "hidden")
            return
        n, x0, x1 = vu["n"], vu["x0"], vu["x1"]
        for ch in (0, 1):
            frac = min(1.0, max(0.0, (vu["disp"][ch] - VU_LO) / (0 - VU_LO)))
            lit_n = int(round(frac * n))
            for i in range(n):
                col = vu_colour(i, n) if i < lit_n else vu["off"]
                if vu["lit"][ch][i] != col:
                    vu["lit"][ch][i] = col
                    f_vu.itemconfigure(vu["segs"][ch][i], fill=col)
            pf = min(1.0, max(0.0, (vu["peak"][ch] - VU_LO) / (0 - VU_LO)))
            xx = x0 + (x1 - x0) * pf
            yy = (38, 84)[ch]
            f_vu.coords(vu["marks"][ch], xx - 3, yy - 3, xx, yy + 31)
            f_vu.itemconfigure(vu["marks"][ch], state="normal" if pf > 0.02 else "hidden")

    def vu_stop():
        """Stop reading the levels of the previous file."""
        vu["stop"]["stop"] = True
        pr_ = vu["stop"].get("proc")
        if pr_:
            try:
                pr_.kill()
            except OSError:
                pass

    def vu_start(path):
        """Start reading the levels of the file that is playing now."""
        vu_stop()
        ffmpeg_ = find_tool("ffmpeg")
        vu["path"], vu["data"], vu["stop"] = path, [], {}
        vu["clock"] = (0.0, time.monotonic(), False)
        if ffmpeg_ and path:
            threading.Thread(target=vu_analyze, args=(ffmpeg_, path, vu["data"], vu["stop"]), daemon=True).start()

    def vu_tick():
        """About 25 times a second: move the meter to the loudness at the current playing position."""
        now = time.monotonic()
        try:
            if not vu["shown"]:
                return
            dt = min(0.2, now - vu["last"]) if vu["last"] else 0.04
            vu["last"] = now
            target = [-60.0, -60.0]
            tpk = [-60.0, -60.0]
            if fm_alive() and fm_player["path"]:
                if fm_player["path"] != vu["path"]:
                    vu_start(fm_player["path"])
                pos0, t0, paused_ = vu["clock"]
                pos = pos0 if paused_ else pos0 + (now - t0)
                idx = int(max(0.0, pos) / 0.05)
                d_ = vu["data"]
                if 0 <= idx < len(d_) and not paused_:
                    lr, rr, lp, rp = d_[idx]
                    target, tpk = [max(-60.0, lr), max(-60.0, rr)], [max(-60.0, lp), max(-60.0, rp)]
            for ch in (0, 1):
                vu["disp"][ch] = target[ch] if target[ch] > vu["disp"][ch] else max(target[ch], vu["disp"][ch] - 70 * dt)
                if tpk[ch] >= vu["peak"][ch]:
                    vu["peak"][ch], vu["peak_t"][ch] = tpk[ch], now
                elif now - vu["peak_t"][ch] > 0.8:
                    vu["peak"][ch] = max(-60.0, vu["peak"][ch] - 30 * dt)
            vu_draw()
        except (tk.TclError, KeyError, IndexError):
            pass
        finally:
            root.after(33, vu_tick)
    def vu_clock_update(pos, paused_, t_meas):
        """A new position report: correct the meter's clock gently (no jumps), or at once after a seek / pause."""
        old_pos, old_t, old_paused = vu["clock"]
        est = old_pos + (t_meas - old_t)
        if paused_ or old_paused or abs(pos - est) > 0.35:
            vu["clock"] = (pos, t_meas, paused_)
        else:
            vu["clock"] = (est + 0.4 * (pos - est), t_meas, False)  # a small step towards the real position
    vu_clock_hook[0] = vu_clock_update
    f_vu.bind("<Map>", lambda e: vu.update(shown=True))
    f_vu.bind("<Unmap>", lambda e: vu.update(shown=False))
    atexit_vu = lambda: vu_stop()
    import atexit as _atexit
    _atexit.register(atexit_vu)
    vu_build()
    root.after(500, vu_tick)


    # --- the about card on the Setup tab: logo, name, author, version
    f_card = bordered(setup_tab, lift=True, radius=16, width=340, height=330)
    f_card.grid_propagate(False)
    logo_img = tk.PhotoImage(data=APP_LOGO_B64)
    lb_logo = panel_label(f_card, lift=True, image=logo_img)
    lb_logo.image = logo_img
    lb_logo.place(relx=0.5, y=18, anchor="n")
    panel_label(f_card, lift=True, text=APP_NAME, font=(UI_FONT, 24, "bold")).place(relx=0.5, y=164, anchor="n")
    panel_label(f_card, caption=True, lift=True, text=APP_ACRONYM, font=(UI_FONT, 10)).place(
        relx=0.5, y=202, anchor="n")
    panel_label(f_card, lift=True, text="Created by " + APP_AUTHOR, font=(UI_FONT, 12)).place(
        relx=0.5, y=230, anchor="n")
    panel_label(f_card, caption=True, lift=True, text="Version " + APP_VERSION, font=(UI_FONT, 11)).place(
        relx=0.5, y=252, anchor="n")
    panel_label(f_card, caption=True, lift=True, text=APP_CREDITS, font=(UI_FONT, 9), wraplength=320,
                justify="center").place(relx=0.5, y=282, anchor="n")

    def place_card(_e=None):
        """Put the card in the free space at the right of the tools, else under them; hide it if there is no room."""
        for fr_, w_min, h_min in ((about_area, 340, 335), (about_below, 340, 335)):
            if fr_.winfo_width() >= w_min and fr_.winfo_height() >= h_min:
                f_card.place(in_=fr_, relx=0.5, rely=0.42 if fr_ is about_area else 0.5, anchor="center")
                f_card.lift()
                return
        f_card.place_forget()
    about_area.bind("<Configure>", place_card)
    about_below.bind("<Configure>", place_card)

    def clip(text, n):
        """Cut a long text to n characters (…), so a field never grows."""
        text = " ".join(str(text).split())
        return text if len(text) <= n else text[:n - 1] + "…"

    def info_show(path, force=False):
        """Show the cover, title, artist and album of a media file in the panel (read in the background)."""
        if not path or not os.path.isfile(path):
            return
        try:
            stamp = (os.path.getmtime(path), os.path.getsize(path))
        except OSError:
            return
        if not force and info_state["path"] == path and info_state["stamp"] == stamp:
            return
        info_state.update(path=path, stamp=stamp, gen=info_state["gen"] + 1)
        threading.Thread(target=info_worker, args=(path, stamp, info_state["gen"]), daemon=True).start()

    def info_worker(path, stamp, gen):
        """Background job: read the tags and the picture of the file."""
        key = (path, stamp)
        data = info_state["cache"].get(key)
        if data is None:
            real_video = has_video_stream(path) is True
            data = (read_media_tags(path), read_cover_png(path, 100, real_video))
            if len(info_state["cache"]) > 60:
                info_state["cache"].clear()
            info_state["cache"][key] = data
        root.after(0, lambda: info_apply(gen, path, data))

    def info_apply(gen, path, data):
        """Show what was read, unless another file was chosen in the meantime."""
        if gen != info_state["gen"]:
            return
        tags, png = data
        info_title_var.set(clip(tags["title"] or "–", 36))
        info_artist_var.set(clip(tags["artist"] or "–", 36))
        info_album_var.set(clip(tags["album"] or "–", 36))
        info_hint_var.set(clip(os.path.basename(path), 56))
        img = None
        if png:
            try:
                img = tk.PhotoImage(data=base64.b64encode(png))
            except tk.TclError:
                img = None
        img = img or info_blank
        info_cover.configure(image=img)
        info_cover.image = img
        info_state["img"] = img

    info_hook["show"] = info_show

    # --- remembered settings
    persist = {
        "dl_dir": (dl_dir_var, None), "dl_quality": (dl_q_var, list(DL_QUALITY)),
        "dl_exact": (exact_var, None),
        "conv_format": (conv_var, VIDEO_FORMATS), "conv_quality": (conv_q_var, list(QUALITY)),
        "conv_codec": (conv_codec_var, list(CODECS)),
        "comp_quality": (qual_var, list(QUALITY)), "comp_res": (res_var, list(RESOLUTIONS)),
        "comp_codec": (comp_codec_var, list(CODECS)), "comp_target": (target_var, None),
        "aud_format": (aud_var, list(AUDIO_FORMATS)),
        "precise": (precise_var, None), "norm_value": (norm_val_var, None),
        **{f"batch_step_{s_}": (v_, None) for s_, v_ in batch_step_vars.items()},
        "batch_out": (batch_out_var, None), "batch_save": (batch_save_var, None), "batch_split": (batch_split_var, None),
        "strip_tags": (strip_tags_var, None), "extra_tags": (extra_tags_var, None),
        "batch_delete": (batch_del_var, None),
        "numbering": (numbering_var, None), "skip_known": (skip_known_var, None),
        "cover_art": (cover_var, None), "vu_style": (vu_style_var, ["Bars", "Needle"]),
        "browse_vis": (br_vis_var, None), "files_vis": (fm_vis_var, None), "files_vis_style": (fm_vis_style_var, list(VIS_STYLES)), "yt_browser": (yt_browser_var, YT_BROWSERS), "yt_feed": (yt_feed_var, list(YT_FEEDS)), "browse_vis_style": (br_vis_style_var, list(VIS_STYLES)),
        "dark_mode": (dark_var, None), "lang_cz": (lang_var, None),
    }
    saved = load_settings()
    recent_files[:] = [p for p in saved.get("recent_files", []) if isinstance(p, str)][:15]
    for key, (var, allowed) in persist.items():
        if key in saved and (allowed is None or saved[key] in allowed):
            try:
                var.set(saved[key])
            except tk.TclError:
                pass
    if "batch_save" not in saved:
        batch_save_var.set(dl_dir_var.get())  # first start with the separate field: begin with the old folder
    if "batch_split" not in saved and str(saved.get("batch_out", "")).strip():
        batch_split_var.set(True)  # settings from before the checkbox existed: a folder was chosen
    _yb = yt_browser_var.get()  # use the YouTube login of the browser chosen last time
    YT_ACCOUNT["browser"] = "" if untr(_yb) == "None" else _yb.lower()

    light_theme = style.theme_use()  # the look the app started with

    paint_last = [None]

    def paint_panel(dark):
        """Colour the cover/tags panel like the tab area, with clearly readable text."""
        bg_, cap_, txt_, win_, line_ = panel_colours(dark)
        if paint_last[0] == (bg_, cap_, txt_, win_, line_, ttk.Style().theme_use()):
            return  # nothing changed: no repaint (styles and the VU meter stay untouched)
        paint_last[0] = (bg_, cap_, txt_, win_, line_, ttk.Style().theme_use())
        style.configure("Panel.TLabel", background=bg_, foreground=txt_)
        style.configure("PanelHint.TLabel", background=bg_, foreground=cap_)
        vu_hook[0]()
        card_ = "#2c2c2c" if cap_ == "#c4c4c4" else "#f7f7f7"  # the about card is a little lighter
        for lb_, is_cap_, lift_ in panel_labels:
            try:
                lb_.configure(bg=card_ if lift_ else bg_, fg=cap_ if is_cap_ else txt_)
            except tk.TclError:
                pass
        for cv_, on_win_, lift_ in bordered_frames:
            try:
                cv_.configure(bg=win_ if on_win_ else bg_)
                fill_ = card_ if lift_ else bg_
                cv_.box_fill, cv_.box_line = fill_, line_
                cv_.itemconfigure("box", fill=fill_, outline=line_)
            except tk.TclError:
                pass
    paint_panel(False)
    app_look = {"dark": None}

    def appearance_check():
        """macOS / Linux: when the system switches between light and dark, repaint our own drawn boxes."""
        try:
            if not IS_WIN:
                dark_now = panel_colours(False)[1] == "#c4c4c4"
                if dark_now != app_look["dark"]:
                    app_look["dark"] = dark_now
                    paint_panel(False)
        except tk.TclError:
            pass

    def appearance_poll():
        """Check every 10 s as well (cheap), in case the system's own signal never arrives."""
        appearance_check()
        root.after(10000, appearance_poll)  # a slow safety net; the real triggers are below
    root.after(300, appearance_poll)
    root.bind("<FocusIn>", lambda e: root.after(200, appearance_check) if e.widget is root else None, add="+")
    for ev_ in ("<<TkSysAppearanceChanged>>",):  # (not <<ThemeChanged>>: our own style changes would trigger it again)
        try:
            root.bind(ev_, lambda e: root.after(100, appearance_check), add="+")
        except tk.TclError:
            pass

    def apply_theme(dark):
        """Windows: switch between the normal look and a dark one (needs the 'clam' theme to recolour)."""
        c = DARK
        style.theme_use("clam" if dark else light_theme)
        if dark:
            style.configure(".", background=c["bg"], foreground=c["fg"], fieldbackground=c["field"],
                            bordercolor=c["border"], lightcolor=c["btn"], darkcolor=c["border"],
                            troughcolor=c["field"], insertcolor=c["fg"], focuscolor=c["bg"])
            style.map(".", foreground=[("disabled", c["off"])])
            style.configure("TButton", background=c["btn"], foreground=c["fg"], padding=(8, 3))
            style.map("TButton", background=[("disabled", c["bg"]), ("pressed", c["accent"]),
                                             ("active", c["btn_hot"])])
            style.configure("TCheckbutton", indicatorbackground=c["field"], indicatorforeground=c["fg"])
            style.map("TCheckbutton", background=[("active", c["bg"])],
                      indicatorbackground=[("disabled", c["bg"])])
            style.configure("TEntry", fieldbackground=c["field"], foreground=c["fg"])
            style.configure("TCombobox", fieldbackground=c["field"], background=c["btn"],
                            foreground=c["fg"], arrowcolor=c["fg"],
                            selectbackground=c["field"], selectforeground=c["fg"])
            style.map("TCombobox", fieldbackground=[("readonly", c["field"]), ("disabled", c["bg"])],
                      foreground=[("readonly", c["fg"]), ("disabled", c["off"])],
                      background=[("active", c["btn_hot"])])
            style.configure("TNotebook", background=c["bg"], bordercolor=c["border"])
            style.configure("TNotebook.Tab", background=c["btn"], foreground=c["fg"], padding=(10, 4))
            style.map("TNotebook.Tab", background=[("selected", c["bg"]), ("active", c["btn_hot"])])
            style.configure("Treeview", background=c["field"], fieldbackground=c["field"],
                            foreground=c["fg"])
            style.map("Treeview", background=[("selected", c["accent"])],
                      foreground=[("selected", "#ffffff")])
            style.configure("Treeview.Heading", background=c["btn"], foreground=c["fg"], relief="flat")
            style.map("Treeview.Heading", background=[("active", c["btn_hot"])])
            style.configure("TProgressbar", background=c["accent"], troughcolor=c["field"],
                            lightcolor=c["accent"], darkcolor=c["accent"], bordercolor=c["border"])
            style.configure("TScrollbar", background=c["btn"], troughcolor=c["bg"],
                            arrowcolor=c["fg"], bordercolor=c["bg"])
            style.map("TScrollbar", background=[("active", c["btn_hot"])])
            style.configure("TScale", background=c["btn"], troughcolor=c["field"])
            style.configure("Hint.TLabel", foreground=c["hint"])
            style.configure("HintB.TLabel", foreground=c["hint"], font=(UI_FONT, 9, "bold"))
            style.configure("Go.TButton", font=(UI_FONT, 10, "bold"), padding=6,
                            background=c["accent"], foreground="#ffffff")
            style.map("Go.TButton", background=[("disabled", c["btn"]), ("active", "#4a86e8")])
            root.configure(bg=c["bg"])
            scroll_cv.configure(bg=c["bg"])
            log_text.configure(bg=c["field"], fg=c["fg"], insertbackground=c["fg"],
                               selectbackground=c["accent"], selectforeground="#ffffff")
            br_desc.configure(bg=c["field"], fg=c["fg"], selectbackground=c["accent"],
                              selectforeground="#ffffff")
            root.option_add("*TCombobox*Listbox.background", c["field"])
            root.option_add("*TCombobox*Listbox.foreground", c["fg"])
            root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])
            root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        else:
            style.configure("Hint.TLabel", foreground="#666")
            style.configure("HintB.TLabel", foreground="#666", font=(UI_FONT, 9, "bold"))
            style.configure("Go.TButton", font=(UI_FONT, 10, "bold"), padding=6)
            root.configure(bg="SystemButtonFace")
            scroll_cv.configure(bg="SystemButtonFace")
            log_text.configure(bg="SystemWindow", fg="SystemWindowText",
                               insertbackground="SystemWindowText",
                               selectbackground="SystemHighlight",
                               selectforeground="SystemHighlightText")
            br_desc.configure(bg="SystemWindow", fg="SystemWindowText",
                              selectbackground="SystemHighlight",
                              selectforeground="SystemHighlightText")
            root.option_add("*TCombobox*Listbox.background", "SystemWindow")
            root.option_add("*TCombobox*Listbox.foreground", "SystemWindowText")
            root.option_add("*TCombobox*Listbox.selectBackground", "SystemHighlight")
            root.option_add("*TCombobox*Listbox.selectForeground", "SystemHighlightText")
        style.configure("Title.TLabel", font=(UI_FONT, 14, "bold"))
        style.configure("Browse.Treeview", rowheight=78)
        for hb_ in list(tr_vars):  # the info boxes pick up the new colours
            if isinstance(hb_, HelpBox):
                hb_.retranslate()
        paint_panel(dark)

        def recolour_dropdowns(w):  # the pop-up lists of comboboxes that already exist
            """Give the already existing drop-down lists the colours of the current theme."""
            for child in w.winfo_children():
                if child.winfo_class() == "TCombobox":
                    try:
                        # only a pop-up that exists already: creating one just to colour it makes
                        # macOS flash a small empty window (new pop-ups get the colours from option_add)
                        pop = str(child) + ".popdown"
                        if not int(root.tk.call("winfo", "exists", pop)):
                            continue
                        root.tk.call(f"{pop}.f.l", "configure",
                                     "-background", c["field"] if dark else "SystemWindow",
                                     "-foreground", c["fg"] if dark else "SystemWindowText",
                                     "-selectbackground", c["accent"] if dark else "SystemHighlight",
                                     "-selectforeground", "#ffffff" if dark else "SystemHighlightText")
                    except tk.TclError:
                        pass
                recolour_dropdowns(child)
        recolour_dropdowns(root)
        try:
            root.after_idle(trim_draw)  # the timeline paints itself
        except NameError:
            pass
        try:  # dark title bar (Windows 10 build 18985+ / 11)
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            val = ctypes.c_int(1 if dark else 0)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), 4)
        except Exception:
            pass

    if IS_WIN:
        apply_theme(dark_var.get())

    try:  # keep the remembered loudness value valid, then sync the label / preset box
        norm_val_var.set(norm_params(norm_val_var.get())[0])
    except (tk.TclError, ValueError):
        norm_val_var.set(-16.0)
    update_norm_label()
    update_batch_out()
    resolve_step_conflicts()
    apply_batch_row_state()

    # --- Czech interface: re-translate everything that is on screen
    txt_en = {}   # widget path -> its English text
    txt_shown = {}  # widget path -> the text this function put on it last
    w0 = {}       # widget path -> its original width
    heading_en = {}
    combo_en = {}
    # drop-downs whose list of choices changes with the chosen site: translated afresh each time
    dyn_combo = {str(br_kind_combo): lambda: list(browse_site_kinds()) or ["Paste a link"],
                 str(br_section_combo): lambda: list(BROWSE_SECTIONS)}
    for name_ in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel"):
        def _wrap(orig=getattr(messagebox, name_)):
            """Return a message box function that translates its title and message first."""
            def w(title=None, message=None, **kw):
                """Translate the title and message, then call the original message box."""
                return orig(tr(title), tr(message), **kw)
            return w
        setattr(messagebox, name_, _wrap())

    _label_classes = ("TLabel", "TButton", "TCheckbutton", "TRadiobutton", "TLabelframe",
                      "Label", "Button", "Checkbutton", "Radiobutton", "Labelframe")
    _tree_widgets = (qd_tree, tree, br_tree, pane_l.tree, pane_r.tree)
    _combo_dicts = set(QUALITY) | set(RESOLUTIONS) | set(CODECS) | set(DL_QUALITY) | set(VIS_STYLES) | set(YT_FEEDS) | set(FM_PLACES)

    def translate_subtree(widget):
        """Translate every label, button and tab below a widget (English text stays in a hidden attribute)."""
        for w in widget.winfo_children():
            try:
                cls = w.winfo_class()
                path = str(w)
                if cls in _label_classes and not str(w.cget("textvariable")):
                    cur = str(w.cget("text"))
                    if cur:
                        en = txt_en.get(path)
                        if en is None or cur not in (en, txt_shown.get(path)):  # first time, or the code changed it
                            en = untr(cur)
                            txt_en[path] = en
                        new = tr(en)
                        txt_shown[path] = new
                        if cur != new:
                            w.configure(text=new)
                        if cls in ("TButton", "TCheckbutton", "Button", "Checkbutton"):
                            try:
                                base = w0.setdefault(path, int(w.cget("width") or 0))
                                if base:
                                    w.configure(width=max(base, len(new) + 2) if LANG["cz"] else base)
                            except (tk.TclError, ValueError):
                                pass
                elif cls == "TCombobox":
                    vals = dyn_combo[path]() if path in dyn_combo else combo_en.get(path)
                    if vals is None:
                        cur_vals = [untr(v) for v in w.cget("values")]
                        vals = cur_vals if cur_vals and all(v in _combo_dicts for v in cur_vals) else []
                        combo_en[path] = vals
                    if vals:
                        cur = untr(w.get())
                        w.configure(values=[tr(v) for v in vals])
                        w.set(tr(cur))
                        base = w0.setdefault(path, int(w.cget("width") or 0))
                        w.configure(width=max(base, max(len(tr(v)) for v in vals) + 2) if LANG["cz"] else base)
            except tk.TclError:
                pass
            translate_subtree(w)

    def apply_language():
        """Switch the whole window between English and Czech."""
        LANG["cz"] = bool(lang_var.get())
        translate_subtree(root)
        if info_state["path"] is None:  # the placeholder of the cover / tags panel
            info_hint_var.set(tr("Select a file to see its cover and tags"))
        go_btn.configure(text="Spustit" if LANG["cz"] else "Start")  # "Start" also means 'beginning' in Trim
        for path_, en_ in tab_en.items():
            try:
                # shorter Czech names on the tab strip, so that all the tabs fit the window width
                nb.tab(path_, text=TAB_CZ.get(en_, tr(en_)) if LANG["cz"] else tr(en_))
            except tk.TclError:
                pass
        for v_ in tr_vars:
            v_.retranslate()
        for tv_ in _tree_widgets:
            for col_ in tv_["columns"]:
                en_ = heading_en.setdefault((str(tv_), col_), untr(tv_.heading(col_, "text")))
                tv_.heading(col_, text=tr(en_))
        for it_ in batch_items:
            tree.set(it_["iid"], "status", tr(it_["status"]))
            tree.set(it_["iid"], "type", tr("Link" if it_["kind"] == "link" else "File"))
        for iid_, r_ in qd_rows.items():
            qd_tree.set(iid_, "status", tr(r_.get("st_en", "")))
            qd_tree.set(iid_, "type", tr(r_.get("kind_en", "Link")))
        if state["gpu_ready"]:
            gpu_cb.config(text=tr(f"Use GPU / hardware encoder ({GPU_KINDS[state['gpu_kind']]['label']})")
                          if state["gpu_kind"] else tr("GPU encoder: not available (using CPU)"))
        browse_player_ui()
        root.update_idletasks()
        fit_scroll_area()

    # --- window size: big enough for the content on any platform / DPI
    def size_window():
        """Size the window at start: saved size, but never larger than the screen."""
        root.update_idletasks()
        req_w, req_h = main.winfo_reqwidth(), main.winfo_reqheight()
        w, h = 920, 640
        if isinstance(saved.get("size"), str) and re.fullmatch(r"\d+x\d+", saved["size"]):
            w, h = (int(x) for x in saved["size"].split("x"))
        # never open bigger than the screen; whatever doesn't fit can be scrolled to
        max_w, max_h = root.winfo_screenwidth() - 40, root.winfo_screenheight() - 110
        for widget_, rows_ in ((tree, 5), (log_text, 4), (br_tree, 2), (tree, 3), (log_text, 3), (br_desc, 3)):
            if main.winfo_reqheight() <= max_h:  # fits already
                break
            widget_.config(height=rows_)
            root.update_idletasks()
        req_w, req_h = main.winfo_reqwidth(), main.winfo_reqheight()
        root.geometry(f"{min(max(w, req_w, 920), max_w)}x{min(max(h, req_h), max_h)}")
        root.minsize(min(640, max_w), min(420, max_h))
        # Tk limits a window to the size of the main screen unless told otherwise; with a bigger
        # monitor attached the window must be allowed to grow beyond it
        root.maxsize(20000, 20000)

    def reset_window_size(_event=None):
        """Ctrl / Cmd + 0: back to a normal size on the screen the window is on, in its top-left corner."""
        try:
            root.attributes("-fullscreen", False)
        except tk.TclError:
            pass
        sw_, sh_ = root.winfo_screenwidth(), root.winfo_screenheight()
        w_, h_ = min(1000, sw_ - 80), min(720, sh_ - 140)
        root.geometry(f"{w_}x{h_}+{root.winfo_x() if 0 <= root.winfo_x() < sw_ - 200 else 40}"
                      f"+{root.winfo_y() if 0 <= root.winfo_y() < sh_ - 200 else 40}")
        return "break"
    fit_job = {"id": None}
    size_log = {"last": None}

    def mac_screens():
        """macOS: x, y (counted downwards from the top of the main screen, as Tk does), width and height
        of every monitor. Tk itself only knows the main one. Asked from CoreGraphics inside this process:
        an osascript helper would show up as a flashing icon every time."""
        try:
            import ctypes

            class CGPoint(ctypes.Structure):
                _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

            class CGSize(ctypes.Structure):
                _fields_ = [("w", ctypes.c_double), ("h", ctypes.c_double)]

            class CGRect(ctypes.Structure):
                _fields_ = [("origin", CGPoint), ("size", CGSize)]

            cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
            cg.CGGetActiveDisplayList.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32),
                                                  ctypes.POINTER(ctypes.c_uint32)]
            cg.CGGetActiveDisplayList.restype = ctypes.c_int32
            cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
            cg.CGDisplayBounds.restype = CGRect
            ids = (ctypes.c_uint32 * 16)()
            n = ctypes.c_uint32(0)
            if cg.CGGetActiveDisplayList(16, ids, ctypes.byref(n)) != 0:
                return []
            out = []
            for i in range(n.value):
                r = cg.CGDisplayBounds(ids[i])
                out.append((r.origin.x, r.origin.y, r.size.w, r.size.h))
            return out
        except Exception:
            return []

    def fit_to_main_screen():
        """Back on a smaller monitor after being on a bigger one: shrink a window that is wider or
        taller than the screen it sits on (macOS only shrinks the height by itself)."""
        fit_job["id"] = None
        try:
            if root.state() != "normal":
                return
            try:
                if root.attributes("-fullscreen"):
                    return  # full screen: the system sizes the window, never touch it
            except tk.TclError:
                pass
            x_, y_, w_, h_ = root.winfo_x(), root.winfo_y(), root.winfo_width(), root.winfo_height()
            sw_, sh_, sx_ = root.winfo_screenwidth(), root.winfo_screenheight(), 0
            if IS_MAC and w_ < 1100 and h_ < 640:
                return  # no screen is smaller than that: nothing to check
            if IS_MAC:
                cx_ = x_ + min(w_, 400) // 2  # the monitor under the left part of the window's title bar
                cy_ = y_ + 30
                scr_ = mac_screens()
                # a window exactly as big as one of the monitors is full screen (the green button), also
                # while another app takes over a second monitor and the reported position is not reliable
                if any(abs(w_ - ow_) <= 2 and h_ >= oh_ - 40 and h_ <= oh_ + 2 for _x, _y, ow_, oh_ in scr_):
                    return
                found_ = False
                if scr_:
                    for ox_, top_, ow_, oh_ in scr_:  # already counted downwards, as Tk does
                        if ox_ <= cx_ < ox_ + ow_ and top_ <= cy_ < top_ + oh_:
                            sx_, sw_, sh_, found_ = int(ox_), int(ow_), int(oh_), True
                            break
                if not found_:
                    return  # unknown: better to leave the window alone
            elif not (0 <= x_ + w_ // 2 < sw_ and 0 <= y_ + 40 < sh_):
                return  # the window is on another monitor
            if w_ > sw_ or h_ > sh_:  # (exactly the screen size = full screen: leave it)
                nw_, nh_ = min(w_, sw_ - 40), min(h_, sh_ - 110)
                nx_ = max(sx_, min(x_, sx_ + sw_ - nw_))
                root.geometry(f"{nw_}x{nh_}+{nx_}+{y_}")
        except tk.TclError:
            pass

    squeeze = {"fixed": 0.0, "tries": 0, "job": None}

    def watch_squeeze(w_, h_, x_, y_):
        """macOS: a full-screen window on a second monitor is shrunk to the size of the main screen when
        another window (the visualizer) goes full screen or is minimized / restored on the other monitor.
        Notice that (a window at the corner of another monitor, narrower than it, exactly the size of the
        main screen) and, if it is still in full screen, switch full screen off and on again, which is
        what restores it by hand."""
        scr_ = mac_screens()
        if len(scr_) < 2:
            return
        main_w, main_h = scr_[0][2], scr_[0][3]
        for ox_, oy_, ow_, oh_ in scr_[1:]:
            if (abs(x_ - ox_) <= 2 and oy_ - 2 <= y_ <= oy_ + 70 and w_ < ow_ - 20
                    and abs(w_ - main_w) <= 2 and h_ >= main_h - 5 and (ow_, oh_) != (main_w, main_h)):
                if squeeze["job"]:
                    root.after_cancel(squeeze["job"])
                squeeze["job"] = root.after(500, lambda: refullscreen(w_, h_, ow_, oh_))
                return

    def refullscreen(w_, h_, ow_, oh_):
        """Switch full screen off and on again if the window is still in full screen but squeezed;
        then look again whether it worked (a second squeeze right after the first one is possible)."""
        squeeze["job"] = None
        try:
            if time.time() - squeeze["fixed"] < 2:
                squeeze["job"] = root.after(1500, lambda: refullscreen(w_, h_, ow_, oh_))
                return
            if not root.attributes("-fullscreen") or root.winfo_width() != w_ or root.winfo_height() != h_:
                return
            squeeze["fixed"] = time.time()
            root.attributes("-fullscreen", False)
            root.after(700, lambda: root.attributes("-fullscreen", True))
            root.after(2500, lambda: squeeze_check(ow_, oh_))
        except tk.TclError:
            pass

    def squeeze_check(ow_, oh_):
        """Still squeezed after the repair (full screen again, but not the size of the monitor)? Repeat."""
        try:
            if root.attributes("-fullscreen") and root.winfo_width() < ow_ - 20 and squeeze["tries"] < 3:
                squeeze["tries"] += 1
                refullscreen(root.winfo_width(), root.winfo_height(), ow_, oh_)
            else:
                squeeze["tries"] = 0
        except tk.TclError:
            pass

    def schedule_fit(event=None):
        """Fit the window to the screen it was moved to, once the dragging has stopped."""
        if event is not None and event.widget is not root:
            return
        if event is not None:
            cur_ = (event.width, event.height, event.x, event.y)
            if cur_ != size_log["last"]:
                size_log["last"] = cur_
                if IS_MAC:
                    watch_squeeze(*cur_)
        if fit_job["id"]:
            root.after_cancel(fit_job["id"])
        fit_job["id"] = root.after(700, fit_to_main_screen)  # once the dragging has stopped
    root.bind("<Configure>", schedule_fit, add="+")

    for seq_ in ("<Control-Key-0>", "<Command-Key-0>"):
        try:
            root.bind_all(seq_, reset_window_size)
        except tk.TclError:
            pass  # "Command" only exists on macOS

    size_window()

    def save_settings_now():
        """Write the settings to the settings file."""
        data = {}
        for key, (var, _) in persist.items():
            try:
                val = var.get()
                data[key] = untr(val) if isinstance(val, str) else val
            except tk.TclError:
                pass
        if state["gpu_ready"]:
            data["gpu"] = bool(gpu_var.get()) if state["gpu_kind"] else saved.get("gpu", True)
        elif "gpu" in saved:
            data["gpu"] = saved["gpu"]
        data["size"] = root.geometry().split("+")[0]
        data["browse_sites"] = [list(x) for x in br_sites]
        data["recent_files"] = list(recent_files)
        data["files_dir"] = pane_l.dir_var.get()
        data["files_dir2"] = pane_r.dir_var.get()
        save_settings(data)

    def gpu_detected(kind):
        """The graphics chip has been detected: enable or disable the GPU checkbox."""
        state["gpu_kind"], state["gpu_ready"] = kind, True
        if kind:
            gpu_cb.config(state="normal",
                          text=tr(f"Use GPU / hardware encoder ({GPU_KINDS[kind]['label']})"))
            gpu_var.set(bool(saved.get("gpu", True)))
        else:
            gpu_var.set(False)
            gpu_cb.config(state="disabled", text=tr("GPU encoder: not available (using CPU)"))

    def detect_worker():
        """Look for a hardware encoder in the background."""
        kind = detect_gpu()
        try:
            root.after(0, lambda: gpu_detected(kind))
        except Exception:
            pass

    threading.Thread(target=detect_worker, daemon=True).start()

    # --- logic
    def recent_add(path):
        """Put a file at the top of the recent files list."""
        path = os.path.abspath(path)
        if path in recent_files:
            recent_files.remove(path)
        recent_files.insert(0, path)
        del recent_files[15:]

    def recent_menu():
        """Pop-up menu with the recent files."""
        m = tk.Menu(root, tearoff=0)
        shown = [p for p in recent_files if os.path.isfile(p)]
        for p in shown:
            m.add_command(label=f"{os.path.basename(p)}   —   {os.path.basename(os.path.dirname(p))}",
                          command=lambda p=p: set_source(p))
        if not shown:
            m.add_command(label=tr("(nothing yet)"), state="disabled")
        else:
            m.add_separator()
            m.add_command(label=tr("Clear this list"), command=lambda: recent_files.clear())
        m.tk_popup(recent_btn.winfo_rootx(), recent_btn.winfo_rooty() + recent_btn.winfo_height())

    def set_source(path):
        """Make a file the current source: show its length and size, remember it in the recent list."""
        src_var.set(path)
        recent_add(path)
        info_hook["show"](path)
        d = get_duration(path)
        state["duration"] = d
        state["has_video"] = has_video_stream(path)
        size = os.path.getsize(path) / 1024 / 1024
        prefix = "Audio only  ·  " if state["has_video"] is False else ""
        info_var.set(prefix + (f"Length {fmt_time(d)}  ·  {size:.1f} MB" if d else f"{size:.1f} MB"))
        trim_stop()
        tl["pos"] = None
        start_var.set("00:00:00")
        if d:
            end_var.set(fmt_time(d))
        trim_draw()

    def browse():
        # Pass patterns as a tuple: macOS's native dialog is picky about space-separated ones.
        """Choose a source file with the file dialog."""
        vid = tuple("*." + e for e in VIDEO_EXTS)
        aud = tuple("*." + e for e in AUDIO_EXTS)
        p = filedialog.askopenfilename(filetypes=[
            ("Video and audio", vid + aud), ("Video", vid), ("Audio", aud),
            ("All files", "*.*")])
        if p:
            set_source(p)

    def task():
        """English name of the tab that is open."""
        return tab_en.get(str(nb.select()), "")

    def options(tn=None):
        """The settings of the current tab as one dictionary for the command builder."""
        tn = tn or task()
        codec_var = conv_codec_var if tn == "Convert" else comp_codec_var
        return {"start": start_var.get(), "end": end_var.get(), "precise": precise_var.get(),
                "format": conv_var.get() if tn == "Convert" else aud_var.get(),
                "conv_quality": conv_q_var.get(), "quality": qual_var.get(),
                "resolution": res_var.get(), "codec": CODECS[codec_var.get()],
                "gpu": state["gpu_kind"] if gpu_var.get() else None, "video_kbps": None,
                "norm": norm_params(norm_val_var.get())}

    def set_setup_buttons(enabled):
        """Enable / disable the buttons of the Setup tab."""
        for b in setup_btns:
            b.config(state="normal" if enabled else "disabled")

    def busy(on):
        """Switch the window between 'working' and 'idle' (Start / Cancel buttons, other buttons)."""
        state["busy"] = on
        go_btn.config(state="disabled" if on else "normal")
        cancel_btn.config(state="normal" if on else "disabled")
        set_setup_buttons(not on)
        apply_batch_row_state()
        update_retry_btn()
        browse_update_buttons()

    def pb_indeterminate(on):
        """Switch the progress bar between a moving 'busy' bar and a normal one."""
        if on:
            pb.config(mode="indeterminate")
            pb.start(12)
        else:
            pb.stop()
            pb.config(mode="determinate", value=0)

    def missing_tool(name, brew, winget):
        """Tell the user that a program is missing and how to install it."""
        txt = (f"Put {name}.exe next to this program, or install it with:\n  winget install {winget}"
               if IS_WIN else f"Install it with:  brew install {brew}")
        messagebox.showerror(f"{name} missing", txt + "\n\nYou can also use the Setup tab.")

    def suggested_name(tk_name, src, opt):
        """Save-dialog suggestion: the clean name when 'Clean file names' is on and that name is
        free, otherwise the usual suffixed name (so nothing is ever overwritten by suggestion)."""
        fallback = suggested_output(tk_name, src, opt)
        if not clean_var.get():
            return fallback
        target = clean_target_path(src, strip_tags_var.get(), parse_tag_list(extra_tags_var.get()))
        stem = os.path.splitext(os.path.basename(target))[0]
        cand = os.path.join(os.path.dirname(src), stem + output_ext(tk_name, src, opt))
        if os.path.exists(cand) or os.path.abspath(cand) == os.path.abspath(src):
            return fallback
        return cand

    def start():
        """The Start button: do what the open tab is for (trim, convert, download, batch …)."""
        if task() == "Setup":  # Start on the Setup tab = verify everything
            verify(list(tool_status), True)
            return
        if task() == "Batch download":
            start_batch()
            return
        if task() == "Browse":
            browse_search()
            return
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            missing_tool("ffmpeg", "ffmpeg", "Gyan.FFmpeg")
            return
        if task() == "Quick download":
            start_download(ffmpeg)
            return
        src = src_var.get()
        if not os.path.isfile(src):
            messagebox.showwarning("No file", "Open a video or audio file first.")
            return
        tk_name, opt = task(), options()

        if state["has_video"] is False and (
                tk_name in ("Compress", "Remove audio")
                or (tk_name == "Convert" and opt["format"] == "gif")):
            messagebox.showwarning("No video",
                                   "This file has no video, so this task doesn't apply.\n"
                                   "Try Trim, Convert, Extract audio or Loudness.")
            return

        total = state["duration"]
        if tk_name == "Trim":
            try:
                s, e = to_seconds(opt["start"]), to_seconds(opt["end"])
                if e is None or s is None or e <= s:
                    raise ValueError
                total = e - s
            except ValueError:
                messagebox.showwarning("Bad time", "End must be after Start.")
                return

        if tk_name == "Compress" and target_var.get().strip():
            try:
                mb = float(target_var.get().strip().replace(",", "."))
            except ValueError:
                messagebox.showwarning("Bad size", "Target size must be a number, e.g. 25")
                return
            if not state["duration"]:
                messagebox.showwarning("Unknown length",
                                       "Can't read the video length (ffprobe missing?), "
                                       "so a target size can't be calculated.")
                return
            kbps = target_video_kbps(mb, state["duration"])
            if kbps is None:
                messagebox.showwarning("Target too small",
                                       "That size is too small for a video of this length. "
                                       "Try a larger size.")
                return
            opt["video_kbps"] = kbps

        ext = output_ext(tk_name, src, opt)
        dst = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(src),
            initialfile=os.path.basename(suggested_name(tk_name, src, opt)),
            defaultextension=ext, filetypes=[(ext.upper()[1:], "*" + ext), ("All", "*.*")])
        if not dst:
            return
        if os.path.abspath(dst) == os.path.abspath(src):
            messagebox.showwarning("Same file", "Choose a different output file name.")
            return

        if tk_name == "Loudness":
            target, lra = opt["norm"]
            save_settings_now()
            state["cancelled"] = False
            busy(True)
            pb["value"] = 0
            status_var.set("Analyzing loudness…")
            threading.Thread(target=norm_worker,
                             args=(ffmpeg, src, dst, target, lra, state["duration"]),
                             daemon=True).start()
            return

        state["cover_tmp"] = None
        if tk_name == "Extract audio" and cover_var.get() and opt["format"] in ("mp3", "m4a"):
            status_var.set("Preparing cover art…")
            root.update_idletasks()
            opt["cover"] = state["cover_tmp"] = make_cover_image(ffmpeg, src, state["duration"])

        # Preferred command, plus an automatic CPU fallback if the GPU encoder fails
        args = build_command(tk_name, src, dst, opt)
        cmds = [[ffmpeg] + args]
        if opt.get("gpu"):
            cpu_args = build_command(tk_name, src, dst, dict(opt, gpu=None))
            if cpu_args != args:
                cmds.append([ffmpeg] + cpu_args)

        save_settings_now()
        state["cancelled"] = False
        busy(True)
        pb["value"] = 0
        status_var.set(f"{tk_name}…")
        try:
            orig_mb = os.path.getsize(src) / 1024 / 1024 if tk_name == "Compress" else 0
        except OSError:
            orig_mb = 0
        threading.Thread(target=worker, args=(cmds, dst, total, orig_mb), daemon=True).start()

    def stopped():
        """True when the running job should stop: Cancel (the whole job) or Skip (one batch item)."""
        return state["cancelled"] or state["skip"]

    def default_report(pct, text, info=None):
        """Default progress reporter: progress bar and status line."""
        root.after(0, lambda: (pb.config(value=pct), status_var.set(text)))

    def run_ffmpeg(cmd, total, span=(0, 100), label="", report=None):
        """Run one ffmpeg command. Returns (returncode, stderr lines).
        span: part of the bar this command fills; label: text before the percentage;
        report(pct, text): progress callback (default: the main progress bar + status line)."""
        report = report or default_report
        log = []
        t_start, speed = time.time(), None
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **TEXT)
        state["proc"] = proc
        awake_on(proc.pid)
        try:
            err_thread = threading.Thread(target=lambda: log.extend(proc.stderr), daemon=True)
            err_thread.start()
            for line in proc.stdout:
                ms = re.match(r"speed=\s*([\d.]+)x", line)
                if ms:
                    speed = float(ms.group(1)) or None
                    continue
                m = re.match(r"out_time_us=(\d+)", line)
                if m and total:
                    done_s = int(m.group(1)) / 1e6
                    pct = min(100, done_s / total * 100)
                    shown = span[0] + (span[1] - span[0]) * pct / 100
                    speed_txt = eta_txt = ""
                    if speed:
                        speed_txt = f"{speed:.1f}×"
                        eta_txt = fmt_eta(max(0.0, total - done_s) / speed)
                    elif pct > 3 and time.time() - t_start > 3:
                        eta_txt = fmt_eta((time.time() - t_start) * (100 - pct) / pct)
                    report(shown, progress_text(f"{label}{shown:.0f} %", speed_txt, eta_txt),
                           (speed_txt, eta_txt))
            proc.wait()
            err_thread.join(timeout=2)
        finally:
            awake_off()
        return proc.returncode, log

    def worker(cmds, dst, total, orig_mb=0):
        """Background job: run ffmpeg (retrying on the CPU if the GPU encoder fails) and report back."""
        try:
            log = []
            for i, cmd in enumerate(cmds):
                if i > 0:
                    root.after(0, lambda: (pb.config(value=0),
                                           status_var.set("GPU encoder failed, retrying on CPU…")))
                rc, log = run_ffmpeg(cmd, total)
                if state["cancelled"]:
                    try:
                        if os.path.exists(dst):
                            os.remove(dst)  # drop the partial output
                    except OSError:
                        pass
                    root.after(0, lambda: status_var.set("Cancelled"))
                    return
                if rc == 0:
                    size = os.path.getsize(dst) / 1024 / 1024
                    bigger = (f" · bigger than the original ({orig_mb:.1f} MB): it was already compressed "
                              "well, try H.265, a target size or a lower resolution") if orig_mb and size > orig_mb else ""
                    root.after(0, lambda: (pb.config(value=100),
                                           status_var.set(f"Done · {size:.1f} MB" + bigger),
                                           notify(APP_NAME, f"Finished · {size:.1f} MB")))
                    root.after(0, lambda: ask_open(dst))
                    return
            err = "".join(log[-15:])
            root.after(0, lambda: (status_var.set("Failed"),
                                   notify(APP_NAME, "The job failed"),
                                   messagebox.showerror("ffmpeg error", err[-1500:])))
        except OSError as ex:
            msg = str(ex)
            root.after(0, lambda: (status_var.set("Failed"),
                                   messagebox.showerror("Could not run ffmpeg", msg)))
        finally:
            state["proc"] = None
            if state.get("cover_tmp"):
                try:
                    os.remove(state["cover_tmp"])
                except OSError:
                    pass
                state["cover_tmp"] = None
            root.after(0, lambda: busy(False))

    def loudness_core(ffmpeg, src, dst, target, lra, total, report=None):
        """Two-pass loudness match. Returns ("ok", note) | ("cancelled", "") |
        ("error", (title, message)). Used by the Loudness tab and by Batch."""
        # pass 1: measure
        rc, log = run_ffmpeg([ffmpeg] + build_norm_analysis(src, target, lra), total,
                             (0, 45), "Analyzing… ", report)
        if stopped():
            return "cancelled", ""
        text = "".join(log)
        m = parse_loudnorm(text)
        if rc != 0 or not m:
            low = text.lower()
            if "matches no streams" in low or "does not contain any stream" in low:
                return "error", ("No audio", "This file has no audio track to adjust.")
            return "error", ("ffmpeg error", text[-1500:] or "Could not measure the loudness.")
        if not math.isfinite(m["input_i"]):
            return "error", ("Silent audio", "The audio is silent, so there is no loudness to match.")

        # pass 2: apply
        note = f"{m['input_i']:.1f} → {target:g} LUFS"
        rc, log = run_ffmpeg([ffmpeg] + build_norm_apply(src, dst, target, lra, m), total,
                             (45, 100), note + " · ", report)
        if stopped():
            try:
                if os.path.exists(dst):
                    os.remove(dst)  # drop the partial output
            except OSError:
                pass
            return "cancelled", ""
        if rc != 0:
            return "error", ("ffmpeg error", "".join(log[-15:])[-1500:])
        return "ok", note

    def norm_worker(ffmpeg, src, dst, target, lra, total):
        """Background job: two-pass loudness normalisation of one file."""
        def fail(title, msg):
            """Report a failed job on the main thread: status line, notification and error box."""
            root.after(0, lambda: (status_var.set("Failed"),
                                   notify(APP_NAME, "The job failed"),
                                   messagebox.showerror(title, msg)))
        try:
            status, info = loudness_core(ffmpeg, src, dst, target, lra, total)
            if status == "cancelled":
                root.after(0, lambda: status_var.set("Cancelled"))
            elif status == "error":
                fail(*info)
            else:
                size = os.path.getsize(dst) / 1024 / 1024
                root.after(0, lambda: (pb.config(value=100),
                                       status_var.set(f"Done · {size:.1f} MB · {info}"),
                                       notify(APP_NAME, f"Loudness matched · {info}")))
                root.after(0, lambda: ask_open(dst))
        except OSError as ex:
            msg = str(ex)
            fail("Could not run ffmpeg", msg)
        finally:
            state["proc"] = None
            root.after(0, lambda: busy(False))

    # --- downloads
    def paste_url():
        """Paste button: put the clipboard text into the link box (mouse-only friendly)."""
        try:
            clip = root.clipboard_get().strip()
        except tk.TclError:
            clip = ""
        if not clip:
            messagebox.showinfo("Clipboard is empty",
                                "There is nothing to paste. Copy a video link first.")
            return
        url_var.set(clip.splitlines()[0].strip())  # first line only
        quick_paste_check(url_var.get())

    qd_checked = set()  # links already looked at (a playlist is checked only once)
    quick_titles = {}  # link -> video name, for links sent here from Browse

    def quick_paste_check(url):
        """A pasted playlist link is verified at once and moved to Batch download (no Start needed)."""
        url = (url or "").strip()
        ytdlp = find_tool("yt-dlp")
        if (not ytdlp or url in qd_checked or state["busy"] or not re.match(r"https?://", url)
                or not needs_probe(url)):
            return
        qd_checked.add(url)
        iid = qd_add(url, "Link", "Checking for a playlist…")
        busy(True)
        pb["value"] = 0
        status_var.set("Checking whether the link is a playlist…")
        state["cancelled"] = False

        def work():
            """Check the link for a playlist in the background, then continue on the main thread."""
            entries = probe_playlist(ytdlp, url)

            def done():
                """Close the busy state and start the playlist or single download once the check is done."""
                busy(False)
                if state["cancelled"]:
                    status_var.set("Cancelled")
                    qd_set(iid, "Cancelled")
                elif entries:
                    handover_playlist(url, entries, None, iid)
                else:
                    status_var.set("That link is a single video. Press Start to download it.")
                    qd_set(iid, "Single video: press Start")
            root.after(0, done)
        threading.Thread(target=work, daemon=True).start()

    qd_pending = {"id": None}

    def quick_url_changed(*_):
        """Typing or Cmd+V in the link box: look again shortly after the text stops changing."""
        if qd_pending["id"]:
            root.after_cancel(qd_pending["id"])
        qd_pending["id"] = root.after(700, lambda: quick_paste_check(url_var.get()))
    url_var.trace_add("write", quick_url_changed)

    def choose_dir():
        """Choose the download folder."""
        d = filedialog.askdirectory(initialdir=dl_dir_var.get() or os.path.expanduser("~"))
        if d:
            dl_dir_var.set(d)

    def start_download(ffmpeg):
        """Start a quick download of the link in the box."""
        ytdlp = find_tool("yt-dlp")
        if not ytdlp:
            missing_tool("yt-dlp", "yt-dlp", "yt-dlp.yt-dlp")
            return
        url = url_var.get().strip()
        if not re.match(r"https?://", url):
            messagebox.showwarning("No link", "Paste a full video link (starting with http).")
            return
        folder = dl_dir_var.get().strip() or os.path.expanduser("~/Downloads")
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as ex:
            messagebox.showerror("Folder error", str(ex))
            return

        section = None
        s_txt, e_txt = sec_start_var.get().strip(), sec_end_var.get().strip()
        if s_txt or e_txt:
            try:
                s = to_seconds(s_txt) or 0.0
                e = to_seconds(e_txt)
                if e is not None and e <= s:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Bad time",
                                       "For 'Only part', End must be after Start "
                                       "(use formats like 90, 1:30 or 00:01:30).")
                return
            section = (s, e)

        qd_checked.add(url)
        iid = qd_add(quick_titles.get(url, url), "Link",
                     "Checking for a playlist…" if needs_probe(url) else "Starting…")
        begin_quick(ytdlp, ffmpeg, url, folder, section, dl_q_var.get(), exact_var.get(), iid)

    def finish_download(path, note="", iid=None):
        """A download is finished: make it the current file and show its size."""
        set_source(path)
        size = os.path.getsize(path) / 1024 / 1024
        pb.config(value=100)
        status_var.set(f"Downloaded · {size:.1f} MB · ready to edit" + (f" · {note}" if note else ""))
        if iid is not None:
            qd_set(iid, f"✓ Downloaded · {size:.1f} MB" + (f" · {note}" if note else ""),
                   item=os.path.basename(path))
        notify(APP_NAME, f"Download finished · {size:.1f} MB")

    # --- quick download: the list on its tab, playlist hand-over, one video per link
    qd_rows = {}  # row id -> {"error": details}

    def qd_add(item, kind="Link", status="Waiting"):
        """Add a row to the Quick download box (it shows only the latest item)."""
        qd_clear()  # the box shows one item: the latest
        iid = qd_tree.insert("", "end", values=(tr(kind), item, tr(status)))
        qd_rows[iid] = {"error": "", "st_en": status, "kind_en": kind}
        qd_tree.see(iid)
        return iid

    def qd_set(iid, status=None, item=None, kind=None, error=None, retry=None):
        """Update a row from any thread."""
        if error is not None and iid in qd_rows:
            qd_rows[iid]["error"] = error
        if retry is not None and iid in qd_rows:
            qd_rows[iid]["retry"] = retry
            root.after(0, update_retry_btn)

        def _w():
            """Apply the requested changes to the row on the main thread."""
            if iid not in qd_rows:
                return
            if status is not None:
                qd_rows[iid]["st_en"] = status
                qd_tree.set(iid, "status", tr(status))
            if item is not None:
                qd_tree.set(iid, "item", item)
            if kind is not None:
                qd_rows[iid]["kind_en"] = kind
                qd_tree.set(iid, "type", tr(kind))
        root.after(0, _w)

    def qd_clear():
        """Empty the Quick download box."""
        for iid in list(qd_rows):
            qd_tree.delete(iid)
        qd_rows.clear()
        update_retry_btn()

    def update_retry_btn():
        """Retry is available when the last quick download failed or was cancelled and nothing is running."""
        can = (not state["busy"]) and any(r.get("retry") for r in qd_rows.values())
        retry_btn.config(state="normal" if can else "disabled")

    def quick_retry():
        """Retry button: repeat the download that failed or was cancelled, with the same settings."""
        if state["busy"]:
            return
        iid = next((i for i, r in qd_rows.items() if r.get("retry") and r.get("job")), None)
        if iid is None:
            return
        qd_set(iid, "Retrying…", error="")
        begin_quick(*qd_rows[iid]["job"], iid)

    AUTO_RETRY_WAIT = 1  # seconds between automatic attempts

    def auto_retry_schedule(iid, seconds=AUTO_RETRY_WAIT):
        """After a failure with 'Keep retrying' ticked: count down in the status box, then retry."""
        row_ = qd_rows.get(iid)
        if row_ is None:
            return
        row_["attempts"] = row_.get("attempts", 0) + 1
        auto_retry_tick(iid, seconds)

    def auto_retry_tick(iid, left):
        """Countdown for automatic retries of a failed download."""
        row_ = qd_rows.get(iid)
        if row_ is None or not row_.get("retry"):
            return  # link cleared, or a manual Retry already started it
        if not auto_retry_var.get():
            row_["st_en"] = "Failed: " + short_error(row_.get("error", ""))
            qd_tree.set(iid, "status", tr("Failed") + row_["st_en"][6:])
            return
        if state["busy"]:  # something else is running: look again shortly
            row_["after"] = root.after(1000, lambda: auto_retry_tick(iid, left))
            return
        if left <= 0:
            quick_retry()
            return
        row_["st_en"] = f"Failed · retry #{row_.get('attempts', 1)} in {left} s"
        qd_tree.set(iid, "status", tr(row_["st_en"]))
        row_["after"] = root.after(1000, lambda: auto_retry_tick(iid, left - 1))

    def auto_retry_changed():
        """Auto-retry was ticked or unticked: start or stop the retry loop."""
        if not auto_retry_var.get():
            return  # the pending tick notices and stops by itself
        for iid, r in qd_rows.items():  # ticked while a failed download is waiting: start looping
            if r.get("retry") and r.get("job") and not state["busy"]:
                auto_retry_schedule(iid, 0)

    def begin_quick(ytdlp, ffmpeg, url, folder, section, quality, exact, iid):
        """Start (or restart) one quick download. Its settings are remembered so Retry can repeat it."""
        qd_rows[iid]["job"] = (ytdlp, ffmpeg, url, folder, section, quality, exact)
        qd_rows[iid]["retry"] = False
        update_retry_btn()
        state["cancelled"] = False
        if needs_probe(url):  # a playlist page: ask yt-dlp, then hand it over to Batch
            busy(True)
            pb["value"] = 0
            status_var.set("Checking whether the link is a playlist…")
            qd_set(iid, "Checking for a playlist…")
            threading.Thread(target=quick_probe_worker,
                             args=(ytdlp, ffmpeg, url, folder, section, quality, exact, iid),
                             daemon=True).start()
            return
        launch_quick_download(ytdlp, ffmpeg, url, folder, section, quality, exact, iid)

    def qd_show_error():
        """Show the full error text of the selected failed row."""
        for iid in qd_tree.selection():
            if qd_rows.get(iid, {}).get("error"):
                messagebox.showinfo("Details", qd_rows[iid]["error"][-1500:])
                return

    def on_url_changed(*_):
        """Link box changed: an empty box also empties the status list."""
        if not url_var.get().strip():
            qd_clear()  # clearing the link also empties the status box
    url_var.trace_add("write", on_url_changed)

    def handover_playlist(url, entries, section, iid):
        """A playlist link was pasted on Quick download: send one row per video to the Batch tab."""
        if len(entries) > 25 and not messagebox.askyesno(
                "Big playlist", f"This playlist has {len(entries)} videos. "
                                "Add all of them to the Batch download list?"):
            qd_set(iid, "Cancelled")
            status_var.set("Cancelled")
            return
        added = sum(1 for u, t_ in entries if batch_add("link", u, title=t_))
        batch_step_vars["Download"].set(True)  # the rows are links: they need the Download step
        nb.select(batch_tab)
        qd_set(iid, f"→ Batch download: {len(entries)} videos", kind="Playlist")
        msg = (f"Playlist moved to the Batch download tab ({added} added"
               + (f", {len(entries) - added} already there" if added < len(entries) else "")
               + "). Check the list and press Start.")
        if section:
            msg += " 'Only part' isn't used in Batch download."
        status_var.set(msg)

    def quick_probe_worker(ytdlp, ffmpeg, url, folder, section, quality, exact, iid):
        """Background job: check whether the link is a playlist before downloading."""
        entries = probe_playlist(ytdlp, url)

        def done():
            """Continue on the main thread once the playlist check is finished."""
            busy(False)
            if state["cancelled"]:
                status_var.set("Cancelled")
                qd_set(iid, "Cancelled", retry=True)
            elif entries:
                handover_playlist(url, entries, section, iid)
            else:  # a single video after all (or the check failed): download just that one
                launch_quick_download(ytdlp, ffmpeg, url, folder, section, quality, exact, iid)
        root.after(0, done)

    def launch_quick_download(ytdlp, ffmpeg, url, folder, section, quality, exact, iid):
        """Start yt-dlp for one video."""
        cmd = build_download_command(ytdlp, ffmpeg, url, folder, quality,
                                     section, exact, single_item=True,
                                     cover=cover_var.get() and "-x" in DL_QUALITY[quality])
        save_settings_now()
        state["cancelled"] = False
        busy(True)
        pb["value"] = 0
        if section:
            pb_indeterminate(True)  # partial downloads don't report a percentage
        status_var.set("Downloading…")
        qd_set(iid, "Downloading…")
        naming = (clean_var.get(), strip_tags_var.get(), parse_tag_list(extra_tags_var.get()))
        threading.Thread(target=dl_worker, args=(cmd, folder, bool(section), naming, iid, url),
                         daemon=True).start()

    def run_ytdlp(cmd, folder, indeterminate=False, report=None):
        """Run yt-dlp. Returns (returncode, downloaded file path or None, stderr lines).
        Used by the Download tab and by Batch."""
        report = report or default_report
        log, found = [], []
        t0 = time.time()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=tool_env(), **TEXT)
        state["proc"] = proc
        awake_on(proc.pid)
        try:
            err_thread = threading.Thread(target=lambda: log.extend(proc.stderr), daemon=True)
            err_thread.start()
            for line in proc.stdout:
                m = re.search(r"PROG\s+([\d.]+)%(?:\|([^|]*)\|(.*))?", line)
                if m and not indeterminate:
                    pct = min(100.0, float(m.group(1)))
                    speed_txt = (m.group(2) or "").strip()
                    eta_txt = (m.group(3) or "").strip()
                    if not re.match(r"[\d.]+\s*[KMGT]?i?B/s", speed_txt):
                        speed_txt = ""
                    if not re.match(r"\d+(:\d+)*$", eta_txt):
                        eta_txt = ""
                    report(pct, progress_text(f"Downloading… {pct:.0f} %", speed_txt, eta_txt),
                           (speed_txt, eta_txt))
                elif line.startswith("FILEPATH="):
                    found.append(line[len("FILEPATH="):].strip())
            proc.wait()
            err_thread.join(timeout=2)
        finally:
            awake_off()
        path = found[-1] if found else None
        if not (path and os.path.isfile(path)):
            path = newest_file(folder, t0)
        return proc.returncode, path, log

    def dl_worker(cmd, folder, indeterminate, naming=(False, True, ()), iid=None, url=None):
        """Background job: run yt-dlp, then rename / clean up the result and report back."""
        report = (lambda pct, text, info=None: (default_report(pct, text), qd_set(iid, text))) if iid else None
        try:
            rc, path, log = run_ytdlp(cmd, folder, indeterminate, report)
            if indeterminate:
                root.after(0, lambda: pb_indeterminate(False))
            if state["cancelled"]:
                root.after(0, lambda: status_var.set("Cancelled"))
                qd_set(iid, "Cancelled", retry=True)
            elif rc == 0 and path:
                final, note = path, ""
                if naming[0]:  # "Clean file names" is on: rename the download itself
                    try:
                        final, note = rename_if_free(path, clean_target_path(path, naming[1], naming[2]))
                    except OSError as ex:
                        note = f"could not rename: {ex}"
                if url:
                    record_download(url, final)  # so a later playlist run skips this video
                root.after(0, lambda: finish_download(final, note, iid))
            else:
                err = "".join(log[-15:]) or "Download failed."
                qd_set(iid, "Failed: " + short_error(err), error=err, retry=True)
                if iid and auto_retry_var.get():  # loop mode: no dialog, try again by itself
                    root.after(0, lambda: (status_var.set("Failed · retrying automatically"),
                                           auto_retry_schedule(iid)))
                else:
                    root.after(0, lambda: (status_var.set("Failed"),
                                           notify(APP_NAME, "The download failed"),
                                           messagebox.showerror("yt-dlp error", err[-1500:])))
        except OSError as ex:
            msg = str(ex)
            if indeterminate:
                root.after(0, lambda: pb_indeterminate(False))
            qd_set(iid, "Failed: " + short_error(msg), error=msg, retry=True)
            root.after(0, lambda: (status_var.set("Failed"),
                                   messagebox.showerror("Could not run yt-dlp", msg)))
        finally:
            state["proc"] = None
            root.after(0, lambda: busy(False))

    # --- batch tab logic
    batch_items = []

    def set_item(it, status, error=None):
        """Set the status (and optionally the error text) of a batch item and update the list."""
        it["status"] = status
        if error is not None:
            it["error"] = error
        root.after(0, lambda: tree.set(it["iid"], "status", tr(status)))

    def show_item_name(it):
        """Show the item's current file name (a link turns into its downloaded file's name)."""
        name = os.path.basename(it["file"]) if it.get("file") else (it.get("title") or it["value"])
        root.after(0, lambda: tree.set(it["iid"], "item", name))

    def done_label(it):
        """The text of a finished item: the steps done, the size and a note."""
        steps = " → ".join(s for s in BATCH_STEPS if s in it["done"])
        try:
            extra = f"  ·  {os.path.getsize(it['file']) / 1024 / 1024:.1f} MB"
        except (OSError, TypeError):
            extra = ""
        note = f"  ·  {it['note']}" if it.get("note") else ""
        return f"✓ {steps}{extra}{note}"

    save_pending = {"on": False}

    def save_batch_items():
        """Save the batch list so that it survives a restart."""
        save_batch_list(batch_items)

    def schedule_save():
        """Save the list a moment after the last change (and always when the app closes)."""
        if save_pending["on"]:
            return
        save_pending["on"] = True

        def _do():
            """Write the batch list to disk once the short delay has passed."""
            save_pending["on"] = False
            save_batch_items()
        root.after(400, _do)

    def known_label(entry):
        """Status text for a link that was downloaded before."""
        return "Already downloaded · " + str(entry.get("when", ""))[:10]

    def is_known(it):
        """A link downloaded in an earlier session (and not being redone in this list)."""
        return (it["kind"] == "link" and skip_known_var.get() and not it["done"]
                and not it.get("file") and not it.get("force")
                and history_known(it["value"]) is not None)

    def refresh_known_flags():
        """Mark (or unmark) the links that are already in the download history."""
        for it in batch_items:
            if it["kind"] != "link" or it["done"] or it.get("probing"):
                continue
            entry = (history_known(it["value"])
                     if (skip_known_var.get() and not it.get("file") and not it.get("force")) else None)
            if entry:
                set_item(it, known_label(entry))
            elif it["status"].startswith("Already downloaded"):
                set_item(it, "Waiting")

    def forget_downloads():
        """Clear the download history after asking."""
        if not messagebox.askyesno(
                "Forget downloaded videos",
                "Forget which videos you have downloaded before?\n\n"
                "Playlists will then download everything again."):
            return
        forget_history()
        refresh_known_flags()
        status_var.set("Download history cleared")

    def batch_add(kind, value, title=None, status="Waiting", pos=None):
        """Add a row (at the end, or at position pos). Returns the item, or None if it is already listed."""
        if any(it["value"] == value for it in batch_items):
            return None
        if kind == "link" and status == "Waiting" and skip_known_var.get():
            entry = history_known(value)
            if entry:
                status = known_label(entry)  # downloaded before: shown, but not downloaded again
        shown = title or (value if kind == "link" else os.path.basename(value))
        iid = tree.insert("", "end" if pos is None else pos,
                          values=(tr("Link" if kind == "link" else "File"), shown, tr(status)))
        it = {"kind": kind, "value": value, "title": title, "iid": iid, "status": status,
              "error": "", "output": None, "done": set(), "probing": False, "note": "",
              "file": value if kind == "file" else None,   # the item's current file
              "base": value if kind == "file" else None,   # where it started
              "downloaded": False}
        if pos is None:
            batch_items.append(it)
        else:
            batch_items.insert(pos, it)
        schedule_save()
        return it

    def restore_batch_items():
        """Bring back the list from the last session."""
        for d in load_batch_list():
            it = batch_add(d["kind"], d["value"], title=d.get("title"))
            if not it:
                continue
            it["done"] = {x for x in d.get("done", []) if x in BATCH_STEPS}
            for key in ("error", "output", "note", "file", "base", "downloaded"):
                if d.get(key) is not None:
                    it[key] = d[key]
            status = d.get("status") or "Waiting"
            if it["done"]:
                status = done_label(it)
            elif not status.startswith(STABLE_STATUS):
                status = "Waiting"  # it was in the middle of something when the app closed
            set_item(it, status)
            show_item_name(it)
        refresh_known_flags()

    def batch_retry_failed():
        """Run only the items that failed."""
        failed = [it for it in batch_items if it["status"].startswith("Failed")]
        if not failed:
            messagebox.showinfo("Nothing to retry", "There are no failed items in the list.")
            return
        for it in failed:
            it["error"] = ""
            set_item(it, "Waiting")
        start_batch(only=failed)

    def batch_retry_skipped():
        """Run only the items that were skipped (Skip current item)."""
        skipped = [it for it in batch_items if it["status"].startswith("Skipped")]
        if not skipped:
            messagebox.showinfo("Nothing to retry", "There are no skipped items in the list.")
            return
        for it in skipped:
            set_item(it, "Waiting")
        start_batch(only=skipped)

    def batch_add_files():
        """Add files to the batch list."""
        vid = tuple("*." + e for e in VIDEO_EXTS)
        aud = tuple("*." + e for e in AUDIO_EXTS)
        paths = filedialog.askopenfilenames(filetypes=[
            ("Video and audio", vid + aud), ("Video", vid), ("Audio", aud), ("All files", "*.*")])
        added = sum(1 for p in paths if batch_add("file", p))
        if added:
            status_var.set(f"Added {added} file(s) to the batch")

    def batch_paste_links():
        """Add the links in the clipboard (or typed in) to the batch list."""
        try:
            clip = root.clipboard_get()
        except tk.TclError:
            clip = ""
        urls = extract_urls(clip)
        if not urls:
            messagebox.showinfo("No links found",
                                "Copy one or more video links first (one per line works well), "
                                "then press Paste links.")
            return
        ytdlp = find_tool("yt-dlp")
        added, to_probe = 0, []
        for u in urls:
            check = bool(ytdlp) and needs_probe(u)
            it = batch_add("link", u, status="Checking for a playlist…" if check else "Waiting")
            if it:
                added += 1
                if check:
                    it["probing"] = True
                    to_probe.append(it)
        status_var.set(f"Added {added} link(s) to the batch")
        if to_probe:
            threading.Thread(target=probe_worker, args=(to_probe, ytdlp), daemon=True).start()

    def probe_worker(pending, ytdlp):
        """Background job: check the links added to the batch list for playlists and fill in their titles."""
        for it in pending:
            entries = probe_playlist(ytdlp, it["value"])
            root.after(0, lambda it=it, entries=entries: apply_probe_result(it, entries))

    def apply_probe_result(it, entries):
        """Runs on the main thread: replace a playlist link by one row per video."""
        it["probing"] = False
        if it not in batch_items:
            return  # the user removed it meanwhile
        if not entries:
            set_item(it, "Waiting")  # a single video (or the check failed): keep it as one link
            return
        if len(entries) > 25 and not messagebox.askyesno(
                "Big playlist", f"This playlist has {len(entries)} videos. Add all of them to the batch?"):
            batch_items.remove(it)
            tree.delete(it["iid"])
            schedule_save()
            return
        pos = batch_items.index(it)
        tree.delete(it["iid"])
        batch_items.remove(it)
        added = 0
        for url, title in entries:
            if batch_add("link", url, title=title, pos=pos + added):
                added += 1
        status_var.set(f"Playlist expanded: {added} video(s) added")

    def batch_remove():
        """Remove the selected items from the batch list."""
        chosen = set(tree.selection())
        for iid in chosen:
            tree.delete(iid)
        batch_items[:] = [it for it in batch_items if it["iid"] not in chosen]
        schedule_save()

    def batch_clear():
        """Empty the batch list."""
        for it in batch_items:
            tree.delete(it["iid"])
        batch_items.clear()
        schedule_save()

    def batch_redo():
        """Forget what has been done so the ticked steps can run again from the start.
        A downloaded original is kept (and not downloaded again) if it still exists."""
        for it in batch_items:
            it["done"], it["error"], it["output"], it["note"] = set(), "", None, ""
            it["force"] = True  # redo means redo: the download history must not skip it
            if it["kind"] == "file":
                it["file"] = it["value"]
            elif it.get("base") and os.path.isfile(it["base"]):
                it["file"] = it["base"]
                it["done"].add("Download")
            else:
                it["file"] = it["base"] = None
                it["downloaded"] = False
            set_item(it, "Waiting")
            show_item_name(it)
        refresh_known_flags()
        schedule_save()

    def batch_show_error():
        """Show the full error text of the selected failed item."""
        for iid in tree.selection():
            for it in batch_items:
                if it["iid"] == iid and it["error"]:
                    messagebox.showinfo("Details", it["error"][-1500:])
                    return

    def batch_choose_save():
        """Choose the batch 'Save to' folder."""
        d = filedialog.askdirectory(initialdir=batch_save_var.get() or os.path.expanduser("~"))
        if d:
            batch_save_var.set(d)

    def batch_choose_out():
        """Choose the folder for processed files."""
        d = filedialog.askdirectory(initialdir=batch_out_var.get() or os.path.expanduser("~"))
        if d:
            batch_out_var.set(d)
            update_batch_out()

    def batch_reset_out():
        """Forget the chosen folder for processed files."""
        batch_out_var.set("")
        update_batch_out()

    def cleanup_partial(path):
        """Delete the half-finished files a cancelled download leaves behind."""
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    def run_cmds(cmds, total, report):
        """Run ffmpeg commands in order until one succeeds (GPU command first, CPU fallback)."""
        log = []
        for cmd in cmds:
            rc, log = run_ffmpeg(cmd, total, (0, 100), "", report)
            if stopped():
                return "cancelled", ""
            if rc == 0:
                return "ok", ""
        return "error", "".join(log[-15:])[-1500:]

    def run_step(step, src, dst, opt, duration, report, ffmpeg):
        """One processing step. Returns ("ok", note) | ("cancelled", "") | ("error", message)."""
        if step == "Loudness":
            target, lra = opt["norm"]
            status, info = loudness_core(ffmpeg, src, dst, target, lra, duration, report)
            return (status, info[1]) if status == "error" else (status, info)
        if step == "Compress" and target_var.get().strip():
            kbps = target_video_kbps(float(target_var.get().strip().replace(",", ".")), duration)
            if kbps is None:
                return "error", "The target size is too small for this video (or its length is unknown)"
            opt["video_kbps"] = kbps
        args = build_command(step, src, dst, opt)
        cmds = [[ffmpeg] + args]
        if opt.get("gpu"):
            cpu_args = build_command(step, src, dst, dict(opt, gpu=None))
            if cpu_args != args:
                cmds.append([ffmpeg] + cpu_args)
        return run_cmds(cmds, duration, report)

    def clean_rename(it, src, delete_dl, opts=None, clean=True):
        """Give the item's current file its final name: cleaned (if `clean`), with the text from
        'Add to start of names' and the list number in front (if set; this is what makes them work for
        files that were added from disk instead of downloaded). Returns (new path, note)."""
        target = (clean_target_path(src, strip_tags_var.get(), parse_tag_list(extra_tags_var.get()))
                  if clean else src)
        if opts:
            number = it.get("number") if opts["numbering"] else None
            if opts["prefix"].strip() or number is not None:
                target = download_target_path(target, opts["prefix"], number, opts["width"])
        if os.path.abspath(target) == os.path.abspath(src):
            return src, ""
        if os.path.exists(target) and not os.path.samefile(src, target):
            is_original = (it.get("base")  # the downloaded video or the file that was added to the list
                           and os.path.abspath(it["base"]) == os.path.abspath(target))
            if is_original and delete_dl:
                os.replace(src, target)  # the processed version replaces the downloaded original
                it["base"], it["downloaded"] = None, False
                return target, ""
            if delete_dl and os.path.isfile(target):
                # an older copy of the same song holds the clean name (e.g. left by an earlier run):
                # with "Delete the original" ticked the freshly processed file takes its place
                os.replace(src, target)
                return target, "replaced an older file of the same name"
        return rename_if_free(src, target)

    def batch_skip():
        """Skip button: drop the item being worked on and carry on with the next one."""
        if (not (state["busy"] and state["batch_running"]) or state["skip"]
                or time.time() < state["skip_until"]):
            return
        state["skip"] = True
        state["skip_until"] = time.time() + 1.2  # a quick double-click must not skip two items
        status_var.set("Skipping the current item…")
        apply_batch_row_state()
        root.after(1300, apply_batch_row_state)
        p = state["proc"]
        if p:
            kill_proc(p)

    def process_item(it, idx, n, steps, out_dir, delete_dl, ffmpeg, opts):
        """Run the ticked steps (that aren't done yet) on one item, in order.
        Returns "ok" | "failed" | "skipped" | "cancelled"."""
        pending = pending_steps(it, steps)
        k = max(1, len(pending))

        def stop_result():
            """The item was stopped: Skip -> 'skipped' (the batch goes on), Cancel -> 'cancelled'."""
            if state["skip"] and not state["cancelled"]:
                set_item(it, "Skipped")
                return "skipped"
            set_item(it, "Cancelled")
            return "cancelled"

        def rep_for(j, verb):
            """Build the progress reporter of one batch item."""
            def rep(pct, _text=None, info=None):
                """Update the progress bar and status text for this item and for the whole batch."""
                item_pct = 100.0 * j / k + pct / k
                overall = (idx + item_pct / 100) / n * 100
                speed_txt, eta_txt = info if info else ("", "")
                left = ""
                waited = time.time() - state.get("batch_t0", time.time())
                if overall >= 2 and waited > 5:  # whole-batch estimate from the pace so far
                    left = fmt_eta(waited * (100 - overall) / overall)
                top = progress_text(f"Item {idx + 1} of {n}", speed_txt, left)
                row_txt = progress_text(f"{verb} {pct:.0f} %", "", eta_txt)
                root.after(0, lambda: (pb.config(value=overall),
                                       status_var.set(top),
                                       tree.set(it["iid"], "status", tr(row_txt))))
            return rep

        def fail(text):
            """Mark the item as failed with the reason."""
            set_item(it, "Failed: " + short_error(text), error=text)
            return "failed"

        created = []  # files this run made; all but the last one are intermediate
        for j, step in enumerate(pending):
            if stopped():
                return stop_result()

            if step == "Download":
                ytdlp = find_tool("yt-dlp")
                folder = batch_save_var.get().strip() or os.path.join(os.path.expanduser("~"), "Downloads")
                os.makedirs(folder, exist_ok=True)
                audio_dl = "-x" in DL_QUALITY[dl_q_var.get()]
                cmd = build_download_command(ytdlp, ffmpeg, it["value"], folder, dl_q_var.get(),
                                             single_item=True,
                                             cover=cover_var.get() and (audio_dl or "Extract audio" in steps))
                set_item(it, "Downloading…")
                t_start = time.time()
                rc, path, log = run_ytdlp(cmd, folder, False, rep_for(j, "Downloading"))
                if stopped():
                    cleanup_download_partials(folder, t_start)  # no half-downloaded leftovers
                    return stop_result()
                if rc != 0 or not path:
                    return fail("".join(log[-15:]) or "Download failed")
                note = ""
                number = it.get("number") if opts["numbering"] else None
                if opts["prefix"].strip() or number is not None:  # "Add to start of names" / numbering
                    try:
                        path, note = rename_if_free(
                            path, download_target_path(path, opts["prefix"], number, opts["width"]))
                    except OSError as ex:
                        note = f"could not rename: {ex}"
                it["file"] = it["base"] = path
                it["note"] = note
                it["downloaded"] = True
                record_download(it["value"], path, it.get("title"))  # remembered for next time
                it["done"].add("Download")
                show_item_name(it)
                continue

            if step == "Clean name":
                src = it.get("file")
                if not src or not os.path.isfile(src):
                    return fail("Nothing to rename yet" if not src else "File not found: " + os.path.basename(src))
                try:
                    final, note = clean_rename(it, src, delete_dl, opts)
                except OSError as ex:
                    return fail(f"Could not rename the file: {ex}")
                it["done"].add(step)
                it["note"] = note
                if src in created:
                    created[created.index(src)] = final
                it["file"] = it["output"] = final
                show_item_name(it)
                continue

            if step == "Write tags":
                src = it.get("file")
                if not src or not os.path.isfile(src):
                    return fail("Nothing to tag yet" if not src else "File not found: " + os.path.basename(src))
                if "Clean name" not in steps:  # no cleaning, but the prefix / number still go in front
                    try:
                        final, note = clean_rename(it, src, delete_dl, opts, clean=False)
                    except OSError as ex:
                        return fail(f"Could not rename the file: {ex}")
                    if final != src:
                        if src in created:
                            created[created.index(src)] = final
                        src = it["file"] = it["output"] = final
                        it["note"] = note
                        show_item_name(it)
                stem, ext = os.path.splitext(os.path.basename(src))
                artist_ = opts["artist"] or guess_artist(stem, opts["strip_tags"], opts["extra"])
                tags = {"title": tag_title_from_stem(stem, artist_, opts["strip_tags"], opts["extra"])}
                if artist_:
                    tags["artist"] = artist_
                album_ = opts.get("album") or folder_album(src)  # your text, else the name of its folder
                if album_:
                    tags["album"] = album_
                    if artist_:
                        tags["album_artist"] = artist_
                if opts["numbering"] and it.get("number"):
                    tags["track"] = str(it["number"])
                tmp = os.path.join(os.path.dirname(src), "." + stem + ".tagging" + ext)
                cmds = [[ffmpeg] + build_tag_command(src, tmp, tags),
                        [ffmpeg] + build_tag_command(src, tmp, tags, all_streams=False)]
                set_item(it, "Writing tags…")
                status, info = run_cmds(cmds, get_duration(src), rep_for(j, "Tags"))
                if status == "cancelled":
                    cleanup_partial(tmp)
                    return stop_result()
                if status == "error":
                    cleanup_partial(tmp)
                    return fail("Could not write the tags: " + info)
                try:
                    os.replace(tmp, src)
                except OSError as ex:
                    cleanup_partial(tmp)
                    return fail(f"Could not write the tags: {ex}")
                it["done"].add(step)
                continue

            src = it.get("file")
            if not src:
                return fail("Not downloaded yet: tick the Download step")
            if not os.path.isfile(src):
                return fail("File not found: " + os.path.basename(src))
            duration = get_duration(src)
            opt = options(step)
            if has_video_stream(src) is False and (
                    step in ("Compress", "Remove audio")
                    or (step == "Convert" and opt["format"] == "gif")):
                return fail(f"This file has no video, so {step} doesn't apply")
            if out_dir:
                try:
                    os.makedirs(out_dir, exist_ok=True)
                except OSError as ex:
                    return fail(f"Could not create the folder {out_dir}: {ex}")
            dst = unique_path(os.path.join(out_dir or os.path.dirname(src),
                                           os.path.basename(suggested_output(step, src, opt))))
            set_item(it, f"{step}…")
            if step == "Extract audio" and opts.get("cover") and opt["format"] in ("mp3", "m4a"):
                opt["cover"] = make_cover_image(ffmpeg, src, duration)  # None: nothing to embed
            try:
                status, info = run_step(step, src, dst, opt, duration, rep_for(j, step), ffmpeg)
            finally:
                cleanup_partial(opt.get("cover"))
            if status == "cancelled":
                cleanup_partial(dst)
                return stop_result()
            if status == "error":
                cleanup_partial(dst)
                return fail(info)
            it["done"].add(step)
            if src in created:  # the previous step's output is now just an intermediate
                cleanup_partial(src)
                created.remove(src)
            created.append(dst)
            it["file"] = it["output"] = dst
            show_item_name(it)

        if delete_dl and it.get("base") and it["file"] != it["base"]:
            cleanup_partial(it["base"])  # remove the original download
            it["base"], it["downloaded"] = None, False
        set_item(it, done_label(it))
        if it.get("file"):
            root.after(0, lambda p_=it["file"]: info_hook["show"](p_, True))  # show what was written
        return "ok"

    def auto_retry_wait(it, attempt):
        """Pause before retrying a failed batch item. Returns retry | skip | cancel | off."""
        error = it.get("error", "")
        end = time.time() + AUTO_RETRY_WAIT
        while time.time() < end:
            if state["cancelled"]:
                return "cancel"
            if state["skip"]:
                return "skip"
            if not auto_retry_var.get():
                set_item(it, "Failed: " + short_error(error), error=error)
                return "off"
            set_item(it, f"Failed · retry #{attempt} in {max(1, int(end - time.time() + 0.99))} s")
            time.sleep(0.2)
        if state["cancelled"]:
            return "cancel"
        if state["skip"]:
            return "skip"
        return "retry"

    def show_batch_summary(counts, results, known, elapsed):
        """A window listing what was done, skipped and failed (with the reason), and how long it took."""
        win = tk.Toplevel(root)
        win.title(tr("Batch finished"))
        win.transient(root)
        f = ttk.Frame(win, padding=12)
        f.pack(fill="both", expand=True)
        bits = [f"{counts['ok']} done"]
        for key in ("failed", "skipped", "cancelled"):
            if counts[key]:
                bits.append(f"{counts[key]} {key}")
        if known:
            bits.append(f"{known} already downloaded")
        ttk.Label(f, text="  ·  ".join(tr(b) for b in bits), style="Title.TLabel").pack(anchor="w")
        ttk.Label(f, text=tr(f"Took {fmt_eta(elapsed)}"), style="Hint.TLabel").pack(anchor="w", pady=(0, 8))
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        txt = tk.Text(box, width=84, height=min(18, max(6, len(results) + 6)), wrap="word",
                      font=(UI_FONT, 10), relief="flat", padx=6, pady=4)
        sb = ttk.Scrollbar(box, command=txt.yview)
        txt.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        if dark_var.get():
            txt.config(bg=DARK["field"], fg=DARK["fg"], insertbackground=DARK["fg"])
        txt.tag_configure("head", font=(UI_FONT, 10, "bold"), spacing1=6)
        txt.tag_configure("bad", foreground="#c0392b" if not dark_var.get() else "#ff8a80")
        lines = []
        marks = {"ok": ("Done", "✓", ""), "failed": ("Failed", "✗", "bad"),
                 "skipped": ("Skipped", "–", ""), "cancelled": ("Cancelled", "–", "")}
        for key in ("failed", "ok", "skipped", "cancelled"):
            rows_ = [r for r in results if r[0] == key]
            if not rows_:
                continue
            title_, mark_, tag_ = marks[key]
            txt.insert("end", tr(f"{title_} ({len(rows_)})") + "\n", "head")
            lines.append(tr(f"{title_} ({len(rows_)})"))
            for _res, name_, detail_ in rows_:
                line_ = f"  {mark_} {name_}" + (f"  —  {detail_}" if detail_ else "")
                txt.insert("end", line_ + "\n", tag_)
                lines.append(line_)
        if known:
            txt.insert("end", tr(f"Already downloaded earlier: {known} (left out)") + "\n", "head")
        txt.config(state="disabled")
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(8, 0))

        def copy():
            """Copy the text of the batch log to the clipboard."""
            root.clipboard_clear()
            root.clipboard_append("\n".join(lines))

        ttk.Button(bar, text="Copy", width=8, command=copy).pack(side="left")
        if counts["failed"]:
            ttk.Label(bar, text="Double-click a failed item in the list to see the full error.",
                      style="Hint.TLabel").pack(side="left", padx=10)
        ttk.Button(bar, text="Close", width=8, command=win.destroy).pack(side="right")
        translate_subtree(win)
        win.update_idletasks()
        win.geometry("+%d+%d" % (root.winfo_rootx() + 60, root.winfo_rooty() + 60))

    def batch_worker(todo, steps, out_dir, delete_dl, ffmpeg, opts, known=0):
        """Background job: process the batch items one by one (download, edit, rename, tag)."""
        counts = {"ok": 0, "failed": 0, "skipped": 0, "cancelled": 0}
        results = []  # (outcome, item name, detail) for the summary window
        n = len(todo)
        state["batch_t0"] = time.time()

        def item_name(it_):
            """Name of the item as shown in messages."""
            return os.path.basename(it_["file"]) if it_.get("file") else (it_.get("title") or it_["value"])

        def detail_for(it_, res_):
            """One-line description of what the batch will do with an item."""
            if res_ == "ok":
                try:
                    return f"{os.path.getsize(it_['file']) / 1024 / 1024:.1f} MB"
                except (OSError, TypeError):
                    return ""
            if res_ == "failed":
                return short_error(it_.get("error", ""), 140)
            return ""
        try:
            for idx, it in enumerate(todo):
                if state["cancelled"]:
                    for rest in todo[idx:]:
                        set_item(rest, "Cancelled")
                        counts["cancelled"] += 1
                        results.append(("cancelled", item_name(rest), ""))
                    break
                state["skip"] = False  # a Skip pressed earlier must not hit this item
                attempt = 0
                while True:
                    try:
                        res = process_item(it, idx, n, steps, out_dir, delete_dl, ffmpeg, opts)
                    except Exception as ex:  # one bad item must not stop the whole queue
                        set_item(it, "Failed: " + short_error(str(ex)), error=str(ex))
                        res = "failed"
                    if res == "failed" and auto_retry_var.get():  # 'Keep retrying' is ticked
                        attempt += 1
                        verdict = auto_retry_wait(it, attempt)
                        if verdict == "retry":
                            continue
                        if verdict == "skip":
                            set_item(it, "Skipped")
                            res = "skipped"
                        elif verdict == "cancel":
                            set_item(it, "Cancelled")
                            res = "cancelled"
                    break
                state["skip"] = False
                counts[res] += 1
                results.append((res, item_name(it), detail_for(it, res)))
                root.after(0, lambda v=(idx + 1) / n * 100: pb.config(value=v))
                root.after(0, schedule_save)
        finally:
            state["proc"] = None
            state["batch_running"] = False
            state["skip"] = False
            parts = [f"{counts['ok']} done"]
            for key in ("failed", "skipped", "cancelled"):
                if counts[key]:
                    parts.append(f"{counts[key]} {key}")
            if known:
                parts.append(f"{known} already downloaded")
            summary = "Batch finished: " + ", ".join(parts)
            elapsed = time.time() - state.get("batch_t0", time.time())
            root.after(0, lambda: (busy(False), status_var.set(summary),
                                   notify(APP_NAME, summary)))
            root.after(0, lambda: show_batch_summary(counts, results, known, elapsed))

    def start_batch(only=None):
        """Start the batch: read the options, mark the items and start the background job."""
        if state["busy"]:
            return
        if any(it.get("probing") for it in batch_items):
            messagebox.showinfo("Still checking",
                                "Some links are still being checked for playlists. "
                                "Try again in a moment.")
            return
        steps = [s for s in BATCH_STEPS if batch_step_vars[s].get()]
        if not steps:
            messagebox.showwarning("No steps", "Tick at least one step to run.")
            return
        problem = batch_steps_problem(steps)
        if problem:
            messagebox.showwarning("These steps don't fit together", problem)
            return
        pool = batch_items if only is None else only
        def known(it):
            """Download history entry of the item's link, if it was downloaded before."""
            return "Download" in steps and is_known(it)
        todo = [it for it in pool if pending_steps(it, steps) and not known(it)]
        n_known = sum(1 for it in pool if known(it) and pending_steps(it, steps))
        if not todo:
            if n_known:
                messagebox.showinfo(
                    "Nothing new to download",
                    f"All {n_known} video(s) in the list were downloaded before.\n\n"
                    "Untick 'Skip videos I've already downloaded' to download them again.")
            else:
                messagebox.showinfo(
                    "Nothing to do",
                    "Add files or paste links first." if not batch_items else
                    "Everything you ticked is already done for every item "
                    "(or doesn't apply to local files).\n\n"
                    "Tick another step, or press Redo all to run them again.")
            return
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            missing_tool("ffmpeg", "ffmpeg", "Gyan.FFmpeg")
            return
        if any("Download" in pending_steps(it, steps) for it in todo) and not find_tool("yt-dlp"):
            missing_tool("yt-dlp", "yt-dlp", "yt-dlp.yt-dlp")
            return
        if "Compress" in steps and target_var.get().strip():
            try:
                float(target_var.get().strip().replace(",", "."))
            except ValueError:
                messagebox.showwarning("Bad size", "On the Compress tab, target size must be a "
                                                   "number, e.g. 25 (or leave it empty).")
                return
        # processed files: the "Save to" folder, or their own folder when the checkbox is ticked
        # (and a folder was chosen there)
        out_dir = ((batch_out_var.get().strip() if batch_split_var.get() else "")
                   or batch_save_var.get().strip()) or None
        if out_dir:
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as ex:
                messagebox.showerror("Folder error", str(ex))
                return
        save_settings_now()
        state["cancelled"] = False
        state["skip"] = False
        state["batch_running"] = True
        busy(True)
        pb["value"] = 0
        status_var.set(f"Batch download: {len(todo)} item(s)…"
                       + (f" ({n_known} already downloaded, skipped)" if n_known else ""))
        for pos, it in enumerate(batch_items, 1):  # list order = playlist order
            it["number"] = pos
        prefix = prefix_var.get()
        opts = {"prefix": prefix, "numbering": numbering_var.get(),
                "width": max(2, len(str(len(batch_items)))), "artist": tag_artist(prefix),
                "album": album_var.get().strip(),
                "strip_tags": strip_tags_var.get(), "extra": parse_tag_list(extra_tags_var.get()),
                "cover": cover_var.get()}
        threading.Thread(target=batch_worker,
                         args=(todo, steps, out_dir, batch_del_var.get(), ffmpeg, opts, n_known),
                         daemon=True).start()

    # --- setup tab logic
    def log_write(text):
        """Write a line to the batch log."""
        def _w():
            """Append the text to the log box (runs on the main thread)."""
            log_text.config(state="normal")
            log_text.insert("end", text)
            log_text.see("end")
            log_text.config(state="disabled")
        root.after(0, _w)

    def apply_probe(info, keys, full):
        """Apply the result of a playlist check to the batch list."""
        for k in keys:
            tool_status[k].set(format_status(info[k], full))
        if full:
            log_write("Check finished.\n")
        if not state["busy"]:
            set_setup_buttons(True)

    def verify(keys, full):
        """Check which tools (ffmpeg, yt-dlp, mpv) are installed and show it on the Setup tab."""
        if state["busy"]:
            return
        set_setup_buttons(False)
        for k in keys:
            tool_status[k].set("checking…")
        if full:
            log_write("Checking installed versions and available updates…\n")

        def work():
            """Probe the installed tools in the background, then show the result on the main thread."""
            info = probe_tools(full)
            root.after(0, lambda: apply_probe(info, keys, full))
        threading.Thread(target=work, daemon=True).start()

    def tool_stream_worker(cmd):
        """Background job: run an install / update command and show its output on the Setup tab."""
        try:
            log_write("$ " + " ".join(cmd) + "\n")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, env=tool_env(), **TEXT)
            state["proc"] = proc
            awake_on(proc.pid)
            try:
                for line in proc.stdout:
                    log_write(line)
                proc.wait()
            finally:
                awake_off()
            if state["cancelled"]:
                log_write("Cancelled.\n")
                root.after(0, lambda: status_var.set("Cancelled"))
            elif proc.returncode == 0:
                log_write("Finished.\n")
                root.after(0, lambda: (status_var.set("Done"),
                                      notify(APP_NAME, "Setup step finished")))
            else:
                log_write(f"Failed (exit code {proc.returncode}).\n")
                root.after(0, lambda: (status_var.set("Failed"),
                                       notify(APP_NAME, "Setup step failed")))
        except OSError as ex:
            log_write(f"Could not run the command: {ex}\n")
            root.after(0, lambda: status_var.set("Failed"))
        finally:
            state["proc"] = None
            root.after(0, lambda: (pb_indeterminate(False), busy(False),
                                   verify(list(tool_status), False)))

    def tool_action(key, action):
        """Install, update or remove a tool, depending on the button."""
        if action == "verify":
            verify([key], True)
            return
        if state["busy"]:
            messagebox.showwarning("Busy", "Wait for the current job to finish first.")
            return
        kind, payload = tool_command(key, action)
        if kind is None:
            messagebox.showinfo("Setup", payload)
            return
        if kind == "terminal":
            if not messagebox.askokcancel(
                    "Install Homebrew",
                    "A Terminal window will open and run the official Homebrew installer.\n"
                    "Follow the prompts there (it asks for your Mac password).\n\n"
                    "When it finishes, come back and press Verify."):
                return
            try:
                open_in_terminal_mac(payload)
                log_write("Opened Terminal for the Homebrew installer. Press Verify when it is done.\n")
            except OSError as ex:
                messagebox.showerror("Could not open Terminal", str(ex))
        elif kind == "elevated":
            if not messagebox.askokcancel(
                    "Administrator approval needed",
                    "Windows will ask for administrator approval, then a PowerShell window\n"
                    "runs the Chocolatey command.\n\n"
                    "When it finishes, close it and press Verify here."):
                return
            try:
                run_elevated_ps(payload)
                log_write("Opened an administrator PowerShell window. Press Verify when it is done.\n")
            except OSError as ex:
                messagebox.showerror("Could not start PowerShell", str(ex))
        else:  # stream
            state["cancelled"] = False
            busy(True)
            pb["value"] = 0
            pb_indeterminate(True)
            status_var.set(f"{PKG.get(key, 'Homebrew')}: {action}…")
            threading.Thread(target=tool_stream_worker, args=(payload,), daemon=True).start()

    # ---- Browse tab logic
    def browse_paste():
        """Paste a link from the clipboard into the Browse search box."""
        try:
            clip = root.clipboard_get().strip()
        except tk.TclError:
            clip = ""
        if clip:
            br_query_var.set(clip.splitlines()[0].strip())

    def browse_selected():
        """The selected row of the Browse list."""
        sel = br_tree.selection()
        return br["rows"].get(sel[0]) if sel else None

    br_sites = []  # your own sites: [name, search address with {q}]

    def browse_site_kinds(name=None):
        """{what to search for: address} of the chosen site (empty: it has no search here)."""
        name = name or br_site_var.get()
        if name in BROWSE_SITES:
            return BROWSE_SITES[name]
        for n_, t_ in br_sites:
            if n_ == name:
                return {"Videos": t_}
        return {}

    def browse_site_template():
        """Search address / prefix for the chosen site and kind, or None for YouTube."""
        if br_site_var.get() == "YouTube":
            return None
        return browse_site_kinds().get(untr(br_kind_var.get()))

    def browse_site_changed():
        """The 'Search for' list follows the chosen site."""
        kinds = list(browse_site_kinds())
        if kinds:
            br_kind_combo.config(values=[tr(k_) for k_ in kinds])
            if untr(br_kind_var.get()) not in kinds:
                br_kind_var.set(tr(kinds[0]))
            if any("{name}" in str(t_) for t_ in browse_site_kinds().values()):
                br_status_var.set(f"{br_site_var.get()}: 'Find' accepts part of a name; the other choice "
                                  "needs the exact name (or paste a link).")
        else:
            br_kind_combo.config(values=[tr("Paste a link")])
            br_kind_var.set(tr("Paste a link"))
            br_status_var.set(f"{br_site_var.get()} has no search here: paste a link to a "
                              "channel, playlist or video.")
        browse_kind_changed()

    def browse_kind_changed():
        """Grey out what does not apply to the chosen site."""
        site, kinds = br_site_var.get(), browse_site_kinds()
        br_kind_combo.config(state="readonly" if len(kinds) > 1 else "disabled")
        br_section_combo.config(
            state="readonly" if (site == "YouTube" and untr(br_kind_var.get()) == "Channels") else "disabled")

    def browse_refresh_sites():
        """Refresh the list of sites in the Browse drop-down."""
        br_site_combo.config(values=list(BROWSE_SITES) + [n_ for n_, _ in br_sites])
        if br_site_var.get() not in br_site_combo.cget("values"):
            br_site_var.set("YouTube")
        browse_site_changed()

    def browse_sites_dialog():
        """Dialog for adding and removing the sites in the Browse drop-down."""
        win = tk.Toplevel(root)
        win.title(tr("Search sites"))
        win.transient(root)
        f = ttk.Frame(win, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=("Add a site to search from the Browse tab. In the address, write {q} where the\n"
                           "search words go, for example:  https://prehraj.to/hledej/{q}\n"
                           "The site must be one yt-dlp can read; otherwise the status line shows its message."),
                  style="Hint.TLabel", justify="left").grid(row=0, column=0, columnspan=2, sticky="w")
        lb = tk.Listbox(f, height=6, width=70, exportselection=False)
        lb.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=8)
        name_var, addr_var = tk.StringVar(), tk.StringVar()
        ttk.Label(f, text="Name").grid(row=2, column=0, sticky="w")
        ttk.Entry(f, textvariable=name_var, width=24).grid(row=2, column=1, sticky="w")
        ttk.Label(f, text="Search address").grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(f, textvariable=addr_var, width=58).grid(row=3, column=1, sticky="w", pady=(4, 0))
        msg = tk.StringVar()
        ttk.Label(f, textvariable=msg, style="Hint.TLabel").grid(row=5, column=0, columnspan=2, sticky="w")

        def fill():
            """Fill the list of sites in the dialog."""
            lb.delete(0, "end")
            for n_, t_ in br_sites:
                lb.insert("end", f"{n_}   —   {t_}")

        def add():
            """Add a site (name and address) to the Browse drop-down."""
            n_, a_ = name_var.get().strip(), addr_var.get().strip()
            if a_ and not re.match(r"https?://", a_):
                a_ = "https://" + a_
            if "{q}" not in a_ and a_.endswith(("/", "=")):
                a_ += "{q}"  # "https://site/search/" -> the search words are added at the end
            if not n_ or "{q}" not in a_:
                messagebox.showwarning("Search sites", "Give the site a name, and an address that contains "
                                       "{q} where the search words go, for example:\n"
                                       "https://prehraj.to/hledej/{q}", parent=win)
                return
            if n_ in BROWSE_SITES or any(x == n_ for x, _ in br_sites):
                messagebox.showwarning("Search sites", f"'{n_}' is already in the list. "
                                       "Use a different name.", parent=win)
                return
            br_sites.append([n_, a_])
            name_var.set("")
            addr_var.set("")
            msg.set(f"Added '{n_}'. Pick it in the 'Search on' list.")
            fill()
            browse_refresh_sites()
            save_settings_now()

        def remove():
            """Remove the selected site from the Browse drop-down."""
            for i in reversed(lb.curselection()):
                del br_sites[i]
            fill()
            browse_refresh_sites()
            save_settings_now()

        bar = ttk.Frame(f)
        bar.grid(row=4, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(bar, text="Add", width=8, command=add).pack(side="left")
        ttk.Button(bar, text="Remove selected", command=remove).pack(side="left", padx=4)
        ttk.Button(bar, text="Close", width=8, command=win.destroy).pack(side="left")
        fill()
        translate_subtree(win)

    def browse_selected_rows():
        """All selected rows of the Browse list."""
        return [br["rows"][i] for i in br_tree.selection() if i in br["rows"]]

    def browse_update_buttons():
        """Enable / disable the Browse buttons according to the selection and the player state."""
        n = len(br_tree.selection())
        has = n > 0
        for b in br_actions:
            b.config(state="normal" if has else "disabled")
        br_play_btn.config(state="normal" if n == 1 else "disabled")  # one video at a time
        # downloading needs the app to be idle (it starts a job); the others always work
        br_dl_btn.config(state="normal" if (has and not state["busy"]) else "disabled")
        br_search_btn.config(state="disabled" if br["loading"] else "normal")
        br_back_btn.config(state="normal" if br["hist"] else "disabled")
        br_more_btn.config(state="normal" if (br["more"] and br["count"] and not br["loading"])
                           else "disabled")

    def browse_back():
        """Go back to the previous Browse list."""
        if br["hist"]:
            br_query_var.set(br["hist"].pop())
            browse_search(remember=False)

    def browse_open_list(_event=None):
        """Double-click / Enter on a playlist row: open it."""
        if len(br_tree.selection()) != 1:
            return
        r = browse_selected()
        if r and r.get("is_list"):
            browse_search(open_url=r["url"])
        elif r:
            browse_play()

    def browse_search(remember=True, open_url=None):
        """Search the chosen site (or open a link) and show the results."""
        if open_url:
            if br["query"]:
                br["hist"].append(br["query"])
            br_query_var.set(open_url)
        elif remember and br["query"] and br_query_var.get().strip() != br["query"]:
            br["hist"].append(br["query"])
        text = br_query_var.get().strip()
        if not text:
            br_status_var.set("Type something to search for, or paste a link.")
            return
        if not find_tool("yt-dlp"):
            missing_tool("yt-dlp", "yt-dlp", "yt-dlp.yt-dlp")
            return
        if not re.match(r"https?://", text) and not text.startswith(":yt") and not browse_site_kinds() and not (
                br_site_var.get() == "YouTube" and re.fullmatch(r"@[\w.\-]+", text)):
            br_status_var.set(f"{br_site_var.get()} has no search here: paste a link to a channel, "
                              "playlist or video.")
            return
        br["gen"] += 1
        br["query"], br["count"], br["more"], br["rows"], br["live_n"] = text, 0, True, {}, 0
        br["imgs"], br["big"] = {}, {}
        br_tree.delete(*br_tree.get_children())
        browse_show(None)
        browse_load(1, BROWSE_PAGE)

    def yt_browser_set():
        """Remember which browser's cookies yt-dlp uses for YouTube."""
        b = yt_browser_var.get()
        YT_ACCOUNT["browser"] = "" if untr(b) == "None" else b.lower()

    def yt_open_feed():
        """Open the YouTube home page / subscriptions with the browser's cookies."""
        yt_browser_set()
        if not YT_ACCOUNT["browser"]:
            br_status_var.set("Choose the browser you are signed in to YouTube with (the login is read "
                              "from it; close nothing, type no password).")
            return
        br_site_var.set("YouTube")
        br_kind_var.set(tr("Videos"))
        br_query_var.set(YT_FEEDS[yt_feed_var.get()])
        browse_search()

    def browse_more():
        """Load more results into the Browse list."""
        if br["query"] and not br["loading"]:
            browse_load(br["count"] + 1, br["count"] + BROWSE_PAGE)

    def browse_load(start_i, end_i):
        """Start loading a page of results in the background."""
        br["loading"] = True
        br_status_var.set("Searching…" if start_i == 1 else "Loading more…")
        browse_update_buttons()
        q = browse_query(br["query"], end_i, BROWSE_SECTIONS.get(untr(br_section_var.get()), "videos")
                         if untr(br_kind_var.get()) == "Channels" else "videos", untr(br_kind_var.get()),
                         browse_site_template())
        threading.Thread(target=browse_fetch_worker,
                         args=(find_tool("yt-dlp"), q, start_i, end_i, br["gen"]), daemon=True).start()

    def browse_fetch_worker(ytdlp, q, a, b, gen):
        """Background job: ask yt-dlp for the list of videos."""
        rows, err = browse_fetch(ytdlp, q, a, b)
        root.after(0, lambda: browse_loaded(rows, err, a, b, gen))

    def browse_loaded(rows, err, a, b, gen):
        """The list is loaded: fill the Browse list (new rows are added after the old ones when loading more)."""
        if gen != br["gen"]:
            return
        br["loading"] = False
        if err and not rows:
            if "Operation not permitted" in err and "ookies" in err:
                br_status_var.set("macOS blocks reading that browser's cookies. Give Terminal (or the app "
                                  "running this) Full Disk Access in System Settings → Privacy & Security, "
                                  "restart it, or choose Firefox / Chrome instead of Safari.")
            else:
                br_status_var.set(f"Nothing found: {err}")
            br["more"] = False
            br_player["continue"] = None
            browse_update_buttons()
            return
        ffmpeg = find_tool("ffmpeg")
        for r in rows:
            iid = br_tree.insert("", br["live_n"] if r.get("live") else "end", text="", values=(
                (tr("👤 Channel: ") if r.get("is_channel") else tr("▶ Playlist: ") if r.get("is_list") else "") + r["title"],
                tr("● LIVE") if r.get("live") else (tr("soon") if r.get("soon") else ""), r["channel"],
                fmt_length(r["duration"]) if r["duration"] else "", fmt_views(r["views"])))
            if r.get("live"):
                br["live_n"] += 1  # live streams always sit at the top of the list
            br["rows"][iid] = r
            if ffmpeg and r["thumb"]:
                browse_thumbs_queue.append((gen, iid, r["thumb"], ffmpeg))
        br["count"] = b if rows else br["count"]
        br["more"] = len(rows) >= (b - a + 1)
        total = len(br["rows"])
        br_status_var.set(browse_fetch.note if (browse_fetch.note and total) else
                          f"{total} result{'s' if total != 1 else ''}. Click one to see the details."
                          if total else "No videos found.")
        browse_update_buttons()
        browse_kick_thumbs()
        cont = br_player.get("continue")
        if cont:  # autoplay was waiting for this page
            br_player["continue"] = None
            if browse_player_alive() and br_player.get("iid") == cont:
                br_player["hold"] = 0.0
                browse_play_next(True)

    browse_thumbs_queue = []
    browse_thumb_workers = {"n": 0}

    def browse_kick_thumbs():
        """Start the thumbnail loading for the visible rows."""
        while browse_thumb_workers["n"] < 3 and browse_thumbs_queue:
            browse_thumb_workers["n"] += 1
            threading.Thread(target=browse_thumb_worker, daemon=True).start()

    def browse_thumb_worker():
        """Background job: download the thumbnails one by one."""
        try:
            while browse_thumbs_queue:
                try:
                    gen, iid, url, ffmpeg = browse_thumbs_queue.pop(0)
                except IndexError:
                    break
                if gen != br["gen"]:
                    continue
                files = browse_thumb_files(ffmpeg, url)
                if files:
                    root.after(0, lambda g=gen, i=iid, f=files: browse_thumb_ready(g, i, f))
        finally:
            browse_thumb_workers["n"] -= 1

    def browse_thumb_ready(gen, iid, files):
        """A thumbnail is ready: show it in the list."""
        if gen != br["gen"] or iid not in br["rows"]:
            return
        try:
            small = tk.PhotoImage(file=files[0])
            br["imgs"][iid] = small
            br["big"][iid] = files[1]
            br_tree.item(iid, image=small)
            if br_tree.selection() == (iid,):
                browse_show(br["rows"][iid])
        except tk.TclError:
            pass

    big_ref = {"img": None}

    def browse_show(r, iid=None):
        """Fill the right-hand panel for the selected video."""
        if r is None:
            br_title_var.set("")
            br_meta_var.set("")
            br_big.config(image="")
            big_ref["img"] = None
            browse_set_desc("")
            browse_update_buttons()
            return
        br_title_var.set(r["title"])
        bits = [x for x in (tr("LIVE NOW") if r.get("live") else "", r["channel"], fmt_length(r["duration"]) if r["duration"] else "",
                            (fmt_views(r["views"]) + " views") if r["views"] else "",
                            fmt_upload_date(r["date"])) if x]
        br_meta_var.set("  ·  ".join(bits))
        sel = br_tree.selection()
        path = br["big"].get(sel[0]) if sel else None
        if path:
            try:
                big_ref["img"] = tk.PhotoImage(file=path)
                br_big.config(image=big_ref["img"])
            except tk.TclError:
                br_big.config(image="")
        else:
            br_big.config(image="")
        browse_set_desc(r["desc"] or ("Double-click to open it." if r.get("is_list")
                                      else "Loading the description…"))
        browse_update_buttons()

    def browse_set_desc(text):
        """Show a description text under the list."""
        br_desc.config(state="normal")
        br_desc.delete("1.0", "end")
        br_desc.insert("1.0", tr(text))
        br_desc.config(state="disabled")

    def browse_on_select(_event=None):
        """A row was selected: show its thumbnail and load the description."""
        r = browse_selected()
        browse_show(r)
        n = len(br_tree.selection())
        if n > 1:
            br_status_var.set(f"{n} selected. Add to batch adds all of them (Shift or Cmd/Ctrl-click to choose).")
        if r and not r.get("desc_full") and not r.get("is_list"):
            threading.Thread(target=browse_desc_worker, args=(find_tool("yt-dlp"), r, br["gen"]),
                             daemon=True).start()

    def browse_desc_worker(ytdlp, r, gen):
        """Background job: ask yt-dlp for the description of the video."""
        if not ytdlp:
            return
        d = browse_details(ytdlp, r["url"])
        root.after(0, lambda: browse_desc_ready(r, d, gen))

    def browse_desc_ready(r, d, gen):
        """The description is ready: show it if the same video is still selected."""
        if gen != br["gen"]:
            return
        r["desc_full"] = True
        if d:
            r["desc"] = d
        elif not r["desc"]:
            r["desc"] = "(no description)"
        if browse_selected() is r:
            browse_set_desc(r["desc"])

    br_tree.bind("<<TreeviewSelect>>", browse_on_select)
    br_sites[:] = [list(x) for x in (saved.get("browse_sites") or [])
                   if isinstance(x, (list, tuple)) and len(x) == 2]
    browse_refresh_sites()  # starts on YouTube / Videos, so "Channel shows" begins greyed out
    br_tree.bind("<Double-1>", browse_open_list)
    for seq_ in ("<Command-a>", "<Control-a>"):  # select everything in the list
        br_tree.bind(seq_, lambda e: (br_tree.selection_set(br_tree.get_children()), "break")[1])
    br_tree.bind("<Return>", browse_open_list)
    browse_update_buttons()

    def browse_open_web():
        """Open the selected video / list in the web browser (to use Save → Watch later / a playlist there)."""
        import webbrowser
        rows_ = browse_selected_rows()[:5]  # a few at most, so the browser is not flooded with tabs
        for r in rows_:
            webbrowser.open(r["url"])
        if rows_:
            yt_ = any("youtube.com" in r["url"] or "youtu.be" in r["url"] for r in rows_)
            br_status_var.set("Opened in your web browser: use Save there to add it to Watch later or a playlist."
                              if yt_ else "Opened in your web browser.")

    def browse_copy():
        """Copy the link of the selected video to the clipboard."""
        rows_ = browse_selected_rows()
        if rows_:
            root.clipboard_clear()
            root.clipboard_append("\n".join(r["url"] for r in rows_))
            br_status_var.set("Link copied." if len(rows_) == 1 else f"{len(rows_)} links copied.")

    def browse_to_quick():
        """Send the selected video to the Quick download tab."""
        r = browse_selected()
        if not r:
            return
        if len(br_tree.selection()) > 1 or r.get("is_channel"):  # several / a whole channel: Batch download
            browse_to_batch(go=True)
            return
        qd_checked.add(r["url"])  # Quick download checks playlists itself when it starts
        url_var.set(r["url"])  # only load the link: quality and folder are chosen there, then Start
        quick_titles[r["url"]] = r.get("title") or r["url"]
        qd_add(quick_titles[r["url"]], "Link", "Waiting")
        nb.select(download_tab)
        status_var.set("Link loaded. Choose the quality and folder, then press Start.")

    def browse_to_batch(go=False):
        """Send the selected videos to the Batch tab."""
        rows_ = browse_selected_rows()
        if not rows_:
            return
        ytdlp = find_tool("yt-dlp")
        added, dup, probing = 0, 0, []
        for r in rows_:
            if r.get("is_list") and ytdlp:  # a playlist / channel: check it, one row per video
                url = browse_query(r["url"], 0, "videos") if r.get("is_channel") else r["url"]
                label = ("Channel: " if r.get("is_channel") else "Playlist: ") + r["title"]
                it = batch_add("link", url, label, status="Checking for a playlist…")
                if it:
                    it["probing"] = True
                    probing.append(it)
            else:
                it = batch_add("link", r["url"], r["title"])
            if it:
                added += 1
            else:
                dup += 1
        if probing:
            batch_step_vars["Download"].set(True)  # the rows are links: they need the Download step
            threading.Thread(target=probe_worker, args=(probing, ytdlp), daemon=True).start()
        if len(rows_) == 1:
            br_status_var.set(("Checking the list… its videos appear in the Batch download tab."
                               if probing else "Added to the Batch download list.") if added
                              else "That one is already in the Batch download list.")
        else:
            br_status_var.set(f"Added {added} to the Batch download list"
                              + (f" ({dup} already there)" if dup else "")
                              + (". Playlists are being expanded." if probing else "."))
        if go and added:
            nb.select(batch_tab)

    def browse_play():
        """Play the selected video in mpv (without downloading it)."""
        r = browse_selected()
        if not r:
            return
        if r.get("is_list"):
            browse_search(open_url=r["url"])
            return
        player = find_player()
        if not player:
            import webbrowser
            webbrowser.open(r["url"])
            br_status_var.set("No mpv or VLC found, so it was opened in your web browser.")
            return
        kind, path = player
        br_status_var.set("Starting the player…")
        browse_stop(quiet=True)  # one thing plays at a time
        fm_stop(quiet=True)
        br_player["iid"], br_player["hold"] = br_tree.selection()[0], 0.0
        br_player["idle_n"], br_player["continue"] = 0, None
        vis_style = untr(br_vis_style_var.get()) if br_vis_var.get() else None
        threading.Thread(target=browse_play_worker, args=(kind, path, r["url"], br_audio_var.get(), vis_style),
                         daemon=True).start()

    br_player = {"proc": None, "sock": None, "paused": False, "iid": None, "hold": 0.0, "unpause_until": 0.0}

    def browse_explain_skip(bad, now_playing):
        """A video was skipped: ask yt-dlp in the background why, and say so in the status line
        (age-restricted and members-only videos need a login, private and deleted ones can't be played)."""
        url = bad.get("url")
        ytdlp = find_tool("yt-dlp")
        if not url or not ytdlp or br_player.get("explaining"):
            return
        br_player["explaining"] = True
        title = bad.get("title") or url

        def work():
            """Find out in the background why yt-dlp cannot play this item, then show the reason."""
            reason = ""
            try:
                r_ = subprocess.run([ytdlp] + cookie_args() + ["--simulate", "--no-playlist", "--no-warnings", url],
                                    capture_output=True, timeout=40, env=tool_env(), **TEXT)
                if r_.returncode != 0:
                    reason = short_error(r_.stderr or "", 130).replace("ERROR: ", "")
            except Exception:
                reason = ""
            finally:
                br_player["explaining"] = False
            if not reason:
                return
            low = reason.lower()
            hint = ""
            if any(w in low for w in ("sign in", "log in", "login", "age", "members", "cookies")) \
                    and not YT_ACCOUNT.get("browser"):
                hint = "  \u2192 choose your browser at 'My YouTube – signed in with' to play it"
            root.after(0, lambda: br_status_var.set(
                f"Skipped \u201c{title[:50]}\u201d: {reason[:110]}{hint}"
                if browse_player_alive() else br_status_var.get()))
        threading.Thread(target=work, daemon=True).start()

    def browse_play_next(manual=False, delta=1, skipped=False):
        """Play the next (delta -1: the previous) video of the list; skips playlists / channels.
        At the end of the loaded list the next page is loaded and the playing carries on."""
        iid = br_player.get("iid")
        kids = list(br_tree.get_children())
        if not browse_player_alive() or iid not in kids:
            return

        def playable(k):
            """Is this row a video that can be played?"""
            return (k in br["rows"] and not br["rows"][k].get("is_list")
                    and not br["rows"][k].get("is_channel"))
        cand = kids[kids.index(iid) + 1:] if delta > 0 else list(reversed(kids[:kids.index(iid)]))
        nxt = next((k for k in cand if playable(k)), None)
        if not nxt and delta < 0:
            br_status_var.set("That was the first video in the list.")
            return
        if not nxt and br["more"] and br["query"]:
            br_player["continue"] = iid  # the next page is loaded, then the playing goes on
            br_player["hold"] = time.time() + 3600
            br_status_var.set("Loading more videos…")
            if not br["loading"]:
                browse_more()
            return
        if not nxt:
            br_status_var.set("That was the last video in the list.")
            br_player["hold"] = time.time() + 3600  # nothing more to start; don't ask again
            return
        if delta > 0 and br["more"] and br["query"] and not br["loading"] \
                and not any(playable(k) for k in kids[kids.index(nxt) + 1:]):
            browse_more()  # the last loaded video starts: fetch the following page already
        r = br["rows"][nxt]
        br_player.update(iid=nxt, hold=time.time() + 4, paused=False, unpause_until=time.time() + 3)
        seek["dur"] = 0
        br_tree.selection_set(nxt)
        br_tree.see(nxt)
        br_player["idle_n"] = 0
        no_login = " (age-restricted or private videos need your YouTube login: choose your browser at 'My YouTube – signed in with')"
        br_status_var.set(("Skipped an unavailable video" + ("" if YT_ACCOUNT.get("browser") else no_login) + ". "
                           if skipped else "")
                          + ("Playing next: " if delta > 0 else "Playing previous: ") + (r.get("title") or r["url"]))
        if skipped:
            browse_explain_skip(br["rows"].get(iid, {}), r)

        def work():
            """Load the item in mpv and make sure it plays (mpv stays paused after a file ends)."""
            try:
                mpv_ipc(br_player["sock"], [{"command": ["loadfile", r["url"], "replace"]},
                                            {"command": ["set_property", "pause", False]}])
                time.sleep(0.6)  # mpv keeps itself paused after the end of a file: say play again
                if time.time() < br_player["unpause_until"]:  # not if the user paused meanwhile
                    mpv_ipc(br_player["sock"], [{"command": ["set_property", "pause", False]}])
            except OSError as ex:
                root.after(0, lambda msg=str(ex): br_status_var.set(f"Could not reach the player: {msg}"))
        threading.Thread(target=work, daemon=True).start()

    def browse_player_alive():
        """True while the Browse player (mpv) is running."""
        p = br_player["proc"]
        return bool(p) and p.poll() is None

    def browse_player_ui():
        """Enable / disable the Browse position slider according to the player state."""
        alive = browse_player_alive()
        if alive:
            br_scale.state(["!disabled"])
        else:
            br_scale.state(["disabled"])
            br_scale.config(to=1)
            br_scale.set(0)
            br_pos_lbl.config(text="0:00")
            br_dur_lbl.config(text="0:00")
        br_pause_btn.config(state="normal" if alive else "disabled",
                            text=tr("Resume") if (alive and br_player["paused"]) else tr("Pause"))
        br_stop_btn.config(state="normal" if alive else "disabled")
        br_next_btn.config(state="normal" if alive else "disabled")
        br_prev_btn.config(state="normal" if alive else "disabled")

    seek = {"drag": False, "busy": False, "dur": 0}

    def browse_progress_apply(res):
        """Apply what mpv reported; go to the next video when this one ended or cannot be played."""
        seek["busy"] = False
        if not res or not browse_player_alive():
            return
        pos, dur, paused = res.get(1), res.get(2), res.get(3)
        if res.get(4) is True and br_auto_var.get() and time.time() > br_player["hold"]:
            browse_play_next()  # this video ended
            return
        br_player["idle_n"] = br_player.get("idle_n", 0) + 1 if res.get(5) is True else 0
        if (br_player["idle_n"] >= 3 and br_auto_var.get() and time.time() > br_player["hold"]
                and br_player.get("iid")):
            browse_play_next(skipped=True)  # the video could not be played (deleted, private…): next one
            return
        if paused is True and time.time() < br_player["unpause_until"] and res.get(4) is not True:
            br_player["paused"] = False  # the next video was loaded paused: start it
            threading.Thread(target=lambda: mpv_ipc(br_player["sock"], [
                {"command": ["set_property", "pause", False]}]), daemon=True).start()
            paused = False
        if isinstance(paused, bool) and paused != br_player["paused"]:
            br_player["paused"] = paused
            browse_player_ui()
        if isinstance(dur, (int, float)) and dur > 0:
            seek["dur"] = dur
            br_scale.config(to=dur)
            br_dur_lbl.config(text=fmt_length(dur))
        if isinstance(pos, (int, float)) and not seek["drag"]:
            br_scale.set(pos)
            br_pos_lbl.config(text=fmt_length(pos))

    def browse_progress_ask():
        """Ask mpv for position, length, pause and end-of-file state (runs in a background thread)."""
        sock = br_player["sock"]
        try:
            res = mpv_ipc(sock, [{"command": ["get_property", "time-pos"], "request_id": 1},
                                 {"command": ["get_property", "duration"], "request_id": 2},
                                 {"command": ["get_property", "pause"], "request_id": 3},
                                 {"command": ["get_property", "eof-reached"], "request_id": 4},
                                 {"command": ["get_property", "idle-active"], "request_id": 5}],
                          wait_ids=[1, 2, 3, 4, 5], timeout=1.0)
        except OSError:
            res = None
        root.after(0, lambda: browse_progress_apply(res))

    def browse_player_poll():
        """Every half second: refresh the Browse player controls and ask mpv for its position."""
        browse_player_ui()
        if browse_player_alive() and br_player["sock"] and not seek["busy"] and not seek["drag"]:
            seek["busy"] = True
            threading.Thread(target=browse_progress_ask, daemon=True).start()
        root.after(500, browse_player_poll)

    def browse_scale_set(event):
        """Move the Browse position slider to where the mouse is."""
        if not browse_player_alive() or not seek["dur"]:
            return "break"
        w = max(1, br_scale.winfo_width())
        frac = min(1.0, max(0.0, event.x / w))
        br_scale.set(frac * seek["dur"])
        br_pos_lbl.config(text=fmt_length(frac * seek["dur"]))
        return "break"

    def browse_scale_press(event):
        """Mouse pressed on the position slider: start dragging."""
        seek["drag"] = True
        return browse_scale_set(event)

    def browse_scale_release(event):
        """Mouse released on the position slider: jump the player to that time."""
        browse_scale_set(event)
        seek["drag"] = False
        if browse_player_alive() and seek["dur"]:
            target = float(br_scale.get())
            def do_seek():
                """Seek mpv to the position chosen on the slider."""
                try:
                    mpv_ipc(br_player["sock"], [{"command": ["seek", target, "absolute"]}])
                except OSError:
                    pass
            threading.Thread(target=do_seek, daemon=True).start()
        return "break"

    br_scale.bind("<Button-1>", browse_scale_press)
    br_scale.bind("<B1-Motion>", browse_scale_set)
    br_scale.bind("<ButtonRelease-1>", browse_scale_release)

    def browse_pause():
        """Pause / resume the Browse player."""
        if not browse_player_alive():
            return
        br_player["unpause_until"] = 0.0  # the user decides now: no more automatic "play again"

        def work():
            """Toggle pause in mpv from a background thread and read the new state back."""
            try:
                state_now = mpv_ipc(br_player["sock"],
                                    [{"command": ["cycle", "pause"], "request_id": 1},
                                     {"command": ["get_property", "pause"], "request_id": 2}],
                                    wait_id=2)
                br_player["paused"] = bool(state_now)
            except OSError as ex:
                root.after(0, lambda msg=str(ex): br_status_var.set(f"Could not reach the player: {msg}"))
            root.after(0, browse_player_ui)
        threading.Thread(target=work, daemon=True).start()

    def browse_stop(quiet=False):
        """Close the Browse player."""
        if browse_player_alive():
            try:
                mpv_ipc(br_player["sock"], [{"command": ["quit"]}])
            except OSError:
                pass
            try:
                br_player["proc"].terminate()
            except OSError:
                pass
            if not quiet:
                br_status_var.set("Stopped.")
        br_player["proc"], br_player["paused"] = None, False
        browse_player_ui()

    import atexit
    atexit.register(lambda: br_player["proc"].terminate() if browse_player_alive() else None)

    def browse_vis_changed():
        """Visualizer ticked / style changed: switch it on the running player at once."""
        if not browse_player_alive() or not br_player["sock"]:
            return
        on, style = br_vis_var.get(), untr(br_vis_style_var.get())

        def work():
            """Apply the visualizer setting to the running mpv player."""
            try:
                if on:
                    golden_folder()  # makes the spiral picture the 'Golden spiral' style needs
                graph = visualizer_graph(style, ffmpeg_has_pseudocolor()) if on else ""
                msgs = [{"command": ["set_property", "lavfi-complex", graph]}]
                if on:
                    msgs.insert(0, {"command": ["set_property", "force-window", "yes"]})
                mpv_ipc(br_player["sock"], msgs)
            except OSError as ex:
                root.after(0, lambda msg=str(ex): br_status_var.set(f"Could not reach the player: {msg}"))
        threading.Thread(target=work, daemon=True).start()

    def browse_play_worker(kind, path, url, audio_only=False, vis_style=None):
        """Background job: start mpv for the Browse tab (or load the next video into the open one)."""
        try:
            if kind == "mpv":  # mpv understands the page link (uses yt-dlp itself)
                import tempfile
                sock = (r"\\.\pipe\faun-mpv-%d" % os.getpid() if IS_WIN else
                        os.path.join(tempfile.gettempdir(), "faun-mpv-%d.sock" % os.getpid()))
                cmd = [path, "--input-ipc-server=" + sock, "--keep-open=yes", "--idle=yes"]
                if YT_ACCOUNT.get("browser"):  # mpv's own yt-dlp uses the same YouTube login
                    cmd += ["--ytdl-raw-options=cookies-from-browser=" + YT_ACCOUNT["browser"]]
                if vis_style:
                    cmd += ["--lavfi-complex=" + visualizer_graph(vis_style, ffmpeg_has_pseudocolor()),
                            "--force-window=yes"]
                elif audio_only:
                    cmd += ["--no-video"]
                cmd += [url]
                import tempfile as _tf
                if vis_style:
                    golden_folder()
                proc = subprocess.Popen(cmd, env=tool_env(), creationflags=NO_WINDOW,
                                        cwd=_tf.gettempdir())  # the visualizer reads its pictures from here
                br_player.update(proc=proc, sock=sock, paused=False)
                seek["dur"] = 0
                root.after(0, lambda: (br_pause_btn.config(text="Pause"), browse_player_ui()))
            else:
                ytdlp = find_tool("yt-dlp")
                r = subprocess.run([ytdlp] + cookie_args() + ["-g", "-f", "b/best", "--no-playlist", url],
                                   capture_output=True, timeout=60, env=tool_env(), **TEXT)
                stream = (r.stdout or "").strip().splitlines()
                if not stream:
                    raise RuntimeError(short_error(r.stderr or "yt-dlp gave no stream.", 160))
                subprocess.Popen([path, stream[0]], creationflags=NO_WINDOW)
            root.after(0, lambda: br_status_var.set(
                "Playing." if kind == "mpv" else "Playing in VLC (Pause / Stop here only work with mpv)."))
        except Exception as ex:
            root.after(0, lambda msg=str(ex): br_status_var.set(f"Could not play it: {msg}"))

    def on_tab_changed(_event=None):
        """Tab changed: update the buttons and start the tab's own refresh."""
        fm_on_tab()
        if task() == "Setup" and not state["setup_checked"]:
            state["setup_checked"] = True
            verify(list(tool_status), False)  # quick local check, no network

    nb.bind("<<NotebookTabChanged>>", on_tab_changed)
    browse_player_poll()
    fm_player_poll()

    def cancel():
        """Cancel the running job (ffmpeg, yt-dlp or the batch)."""
        state["cancelled"] = True
        p = state["proc"]
        if p:
            kill_proc(p)

    def ask_open(path):
        """Ask the user for a source file for the tab that needs one."""
        if messagebox.askyesno("Done", f"Saved:\n{path}\n\nOpen the folder?"):
            folder = os.path.dirname(path)
            if IS_WIN:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif IS_MAC:
                subprocess.Popen(["open", "-R", path])  # reveal file in Finder
            else:
                subprocess.Popen(["xdg-open", folder])

    def on_close():
        """Window closing: stop the players and the running job, save the settings."""
        if state["busy"]:
            if not messagebox.askyesno("Job running", "A job is still running. Quit and cancel it?"):
                return
            cancel()
        save_settings_now()
        save_batch_items()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    if IS_MAC:
        root.createcommand("tk::mac::Quit", on_close)  # Cmd+Q

    skip_known_var.trace_add("write", lambda *a: refresh_known_flags())
    restore_batch_items()
    apply_language()  # Czech on if it was on last time
    if LANG["cz"]:
        size_window()  # the Czech texts are longer

    # "Open with" / drag file onto the .py icon or .exe
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        set_source(sys.argv[1])

    def on_drop(event):
        """Files dropped on the window: on Files go to their folder, on Batch they join the list,
        elsewhere the first one becomes the source file."""
        try:
            paths = [p for p in root.tk.splitlist(event.data) if p]
        except tk.TclError:
            return "copy"
        if not paths:
            return "copy"
        here = task()
        if here == "Files":
            p0 = paths[0]
            tgt_ = fm_pane_target(event.x_root, event.y_root) if hasattr(event, "x_root") else None
            q_ = tgt_[0] if tgt_ else fm_active["p"]
            fm_set_active(q_)
            if os.path.isdir(p0):
                q_.go(p0)
            else:
                q_.go(os.path.dirname(p0), select=p0)
            return "copy"
        files = []
        for p in paths:
            if os.path.isdir(p):
                files += [os.path.join(p, f) for f in sorted(os.listdir(p))
                          if is_media_file(f) and os.path.isfile(os.path.join(p, f))]
            elif os.path.isfile(p):
                files.append(p)
        if not files:
            return "copy"
        if here == "Batch download":
            added = sum(1 for p in files if batch_add("file", p))
            status_var.set(f"Added {added} file(s) to the batch.")
        else:
            set_source(files[0])
            status_var.set("Loaded " + os.path.basename(files[0])
                           + ("  (several files were dropped: use the Batch download tab for all of them)"
                              if len(files) > 1 else ""))
        return "copy"

    def register_drop(widget):
        """Allow dropping files and links onto a widget (drag and drop)."""
        try:
            widget.drop_target_register(tkinterdnd2.DND_FILES)
            widget.dnd_bind("<<Drop>>", on_drop)
        except Exception:
            pass
        for ch in widget.winfo_children():
            register_drop(ch)
    if dnd_ok:
        register_drop(root)

    def show_about(*_):
        """The 'About' entry of the macOS application menu."""
        win = tk.Toplevel(root)
        win.title("About " + APP_NAME)
        win.transient(root)
        win.resizable(False, False)
        f = ttk.Frame(win, padding=(40, 28))
        f.pack()
        ttk.Label(f, text=APP_NAME, style="Title.TLabel").pack()
        ttk.Label(f, text=APP_ACRONYM, style="Hint.TLabel").pack(pady=(4, 0))
        ttk.Label(f, text="Created by " + APP_AUTHOR).pack(pady=(10, 2))
        ttk.Label(f, text="Version " + APP_VERSION, style="Hint.TLabel").pack()
        ttk.Label(f, text=APP_CREDITS, style="Hint.TLabel", wraplength=320, justify="center").pack(pady=(10, 0))
        ttk.Button(f, text="OK", width=8, command=win.destroy).pack(pady=(18, 0))
        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Return>", lambda e: win.destroy())
        try:
            win.update_idletasks()
            win.geometry("+%d+%d" % (root.winfo_rootx() + (root.winfo_width() - win.winfo_width()) // 2,
                                     root.winfo_rooty() + 120))
        except tk.TclError:
            pass
    try:
        root.createcommand("tkAboutDialog", show_about)  # replaces the standard macOS About panel
    except tk.TclError:
        pass

    root.mainloop()


if __name__ == "__main__":
    run_gui()
