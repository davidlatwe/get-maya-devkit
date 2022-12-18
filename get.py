"""

MIT License

Copyright (c) 2022 David Lai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import os
import re
import sys
import zipfile
import tarfile
import platform
import argparse
import subprocess
try:
    from urllib import request
except ImportError:
    import urllib as request  # py2


__author__ = "davidlatwe"
__version__ = "0.1.0"


ROOT = os.path.dirname(os.path.abspath(__file__))


SITE = (
    "https://www.autodesk.com/content/autodesk/global/en/"
    "developer-network/platform-technologies/maya.html"
)


def _log(message):
    sys.__stdout__.write(message + "\n")
    sys.__stdout__.flush()


def extract(file_path, dest):
    _log("-- Unzipping:   %s" % file_path)
    if not os.path.isdir(dest):
        os.makedirs(dest)

    if platform.system() == "Windows":
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(dest)
        return

    if platform.system() == "Linux":
        # TODO: not tested yet
        with tarfile.TarFile(file_path, "r") as tar_ref:
            tar_ref.extractall(dest)
        return

    if platform.system() == "Darwin":
        # TODO: not tested yet
        subprocess.check_call(["7z", "x", "-oFRED", "--", file_path],
                              cwd=dest)
        return


def download(url):
    _log("-- Downloading: %s" % url)
    base_name = os.path.basename(url)
    file_path = os.path.join(ROOT, base_name)
    request.urlretrieve(url, file_path)
    return file_path


def obtain(url, maya_ver, update_num):
    dest = os.path.join(ROOT, "%s.%s" % (maya_ver, update_num))
    if not os.path.isdir(dest):
        file_path = download(url)
        extract(file_path, dest)


def parse_links(lines):
    p = (r'.*<a href="(https://.*\.amazonaws.com/.*/Maya/devkit+.*'
         r'/.*Maya.*[.dmg zip tgz])".*>.*')
    p = re.compile(p.encode())
    return [
        matched.group(1).decode()
        for matched in [p.match(ln) for ln in lines] if matched
    ]


def parse_maya_version(url):
    url = url.replace("%20", "+")
    p = r'.*/devkit\+(20[12][0-9])/.*'
    p = re.compile(p)
    return p.match(url).group(1)


def parse_update_version(url, maya_ver):
    base_name = os.path.basename(url)
    chaotic = {
        "2016": {
            "Maya2016_DEVKIT": 0,
            "Maya2016.1_DEVKIT": 1,
            "Maya2016ext2_DEVKIT": 2,
        },
        "2017": {
            "Maya2017_DEVKIT": 0,
            "Maya2017u3_DEVKIT": 3,
            "Maya2017u4_DEVKIT": 4,
        },
        "2018": {
            "Maya2018-DEVKIT": 0,
            "Maya2018_DEVKIT": 0,
            "Maya2018u3_DEVKIT": 3,
            "Maya2018u4_DEVKIT": 4,
        },
    }.get(maya_ver, {})

    for prefix, num in chaotic.items():
        if base_name.startswith(prefix):
            return num
    else:
        prefix = "Autodesk_Maya_%s_DEVKIT" % maya_ver
        if base_name.startswith(prefix):
            return 0

        for i in range(1, 10):
            prefix = "Autodesk_Maya_%s_%d_Update_DEVKIT" % (maya_ver, i)
            if base_name.startswith(prefix):
                return i

        raise Exception("Cannot parse update version: %s" % base_name)


def parse_platform(url):
    base_name = os.path.basename(url).lower()
    if "windows" in base_name:
        return "Windows"
    if "linux" in base_name:
        return "Linux"
    if "macos" in base_name or "mac" in base_name:
        return "Mac"


def parse(maya, platform_):
    maya, update = (maya.split(".") + [""])[:2]
    update = -1 if update == "*" else int(update or 0)

    hdr = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.11 (KHTML, like Gecko) "
                      "Chrome/23.0.1271.64 Safari/537.11",
    }
    req = request.Request(SITE, headers=hdr)
    try:
        response = request.urlopen(req)
        if response.code == 200:
            url_list = parse_links(response.readlines())
        else:
            _log("%d returned from: %s" % (response.code, SITE))
            sys.exit(1)

    except Exception as e:
        _log(str(e))
        sys.exit(1)

    else:
        found = []
        for r in url_list:
            maya_ver = parse_maya_version(r)
            update_num = parse_update_version(r, maya_ver)

            if maya and maya != maya_ver:
                continue
            if update >= 0 and update != update_num:
                continue
            if platform_ and platform_ != parse_platform(r):
                continue

            found.append((r, maya_ver, update_num))

        return found


def main(maya, platform_, dryrun):
    found = parse(maya, platform_)
    if found:
        for data in found:
            if dryrun:
                _log(data[0])
            else:
                obtain(*data)
    else:
        _log(
            "No link for Maya %s %s\n"
            "Can you find it there? %s" % (maya, platform_, SITE)
        )
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="get.py",
        description="Get Maya Devkit. "
                    "Parse Maya devkit archive link from Autodesk website "
                    "and download specified.",
        epilog="Example Usage: "
               "python ./get.py --dryrun --maya 2020.2",
    )
    parser.add_argument("--maya",
                        help="Maya version. 2020 or 2020.0 will get first "
                             "released version. 2020.1 will get update 1. "
                             "And 2020.* will get all.")
    parser.add_argument("--platform", default=platform.system(),
                        help="Default value is current platform: "
                             "%s. Available options are: Windows, Linux, Mac."
                             % platform.system())
    parser.add_argument("--dryrun", default=False, action="store_true",
                        help="If set, only list out URLs.")

    args = parser.parse_args(sys.argv[1:])
    main(args.maya, args.platform, args.dryrun)
