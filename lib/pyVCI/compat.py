# -*- coding: utf-8 -*-
"""
pyVCI.compat
Shared helpers for pyVCI tools. Start this module small and only add to it
what a real tool actually needs (same convention as pyNBT's own
lib/pyNBT/compat.py) - do not pre-build Revit-version-compat helpers nobody
is using yet.

Right now this only carries what the Update tool needs: a pyRevit reload
helper plus HTTP/zip/mirror-sync helpers that survive Revit 2025+'s .NET 8
(CoreCLR) runtime, where System.Net.WebClient and System.IO.Compression's
ZipFile do not resolve the same way on every Revit version. Ported directly
from pyNBT's compat.py (verified working there since pyNBT's Update v3).
"""
import os
import shutil


def try_reload_pyrevit():
    """Attempt to trigger a full pyRevit session reload (reloads every
    extension, including this one) so a freshly-downloaded update becomes
    active immediately, without the user having to click pyRevit's own
    Reload button by hand.

    The reload entry point is an internal pyRevit API that has moved
    across pyRevit versions, so this tries a few known locations in turn
    and returns False (instead of raising) if none of them work - the
    caller should then tell the user to reload manually via the pyRevit
    tab's own Reload button."""
    try:
        from pyrevit.loader.sessionmgr import reload_pyrevit
        reload_pyrevit()
        return True
    except Exception:
        pass
    try:
        from pyrevit.session import reload_pyrevit
        reload_pyrevit()
        return True
    except Exception:
        pass
    try:
        from pyrevit.loader import sessionmgr
        sessionmgr.reload_pyrevit()
        return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# HTTP download + zip extraction helpers.
#
# Revit 2025+ runs on .NET 8 (CoreCLR) instead of .NET Framework, which
# changes which BCL assemblies are auto-loaded/importable - System.Net's
# WebClient and System.IO.Compression's ZipFile do not resolve the same
# way on every Revit version. Both helpers below try Python's own stdlib
# first (pure Python, no CLR assembly involved, most portable), then fall
# back through a few different CLR assembly names.
# ---------------------------------------------------------------------------

def download_file(url, dest_path):
    """Download the file at `url` to `dest_path`, trying a few different
    HTTP mechanisms in turn until one works."""
    try:
        import urllib
        urllib.urlretrieve(url, dest_path)
        return
    except Exception:
        pass

    import clr
    for assembly_name in ("System.Net.Requests", "System", "System.Net"):
        try:
            clr.AddReference(assembly_name)
            from System.Net import WebClient
            WebClient().DownloadFile(url, dest_path)
            return
        except Exception:
            continue

    try:
        clr.AddReference('System.Net.Http')
        from System.Net.Http import HttpClient
        from System import Uri
        from System.IO import File
        response_bytes = HttpClient().GetByteArrayAsync(Uri(url)).Result
        File.WriteAllBytes(dest_path, response_bytes)
        return
    except Exception as ex:
        raise Exception(
            "Could not download {} - tried urllib, WebClient and "
            "HttpClient, all failed. Last error: {}".format(url, str(ex))
        )


def extract_zip(zip_path, extract_to_dir):
    """Extract the zip file at `zip_path` into `extract_to_dir`, trying
    Python's built-in zipfile module first, falling back to .NET's
    ZipFile if this IronPython build's zlib support is unavailable."""
    try:
        import zipfile
        zf = zipfile.ZipFile(zip_path, 'r')
        try:
            zf.extractall(extract_to_dir)
        finally:
            zf.close()
        return
    except Exception:
        pass

    import clr
    for assembly_name in ("System.IO.Compression.FileSystem",
                           "System.IO.Compression.ZipFile",
                           "System.IO.Compression"):
        try:
            clr.AddReference(assembly_name)
            from System.IO.Compression import ZipFile
            ZipFile.ExtractToDirectory(zip_path, extract_to_dir)
            return
        except Exception:
            continue

    raise Exception(
        "Could not extract {} - tried Python zipfile and .NET ZipFile, "
        "all failed.".format(zip_path)
    )


def fetch_text(url):
    """Fetch the text content at `url` and return it as a string (stripped
    of surrounding whitespace/newlines), trying a few different HTTP
    mechanisms in turn. Used for small, lightweight checks (e.g. reading a
    one-line VERSION file) where downloading to a temp file first, like
    download_file() does, would be wasteful."""
    try:
        import urllib2
        return urllib2.urlopen(url).read().strip()
    except Exception:
        pass

    import clr
    for assembly_name in ("System.Net.Requests", "System", "System.Net"):
        try:
            clr.AddReference(assembly_name)
            from System.Net import WebClient
            return WebClient().DownloadString(url).strip()
        except Exception:
            continue

    try:
        clr.AddReference('System.Net.Http')
        from System.Net.Http import HttpClient
        from System import Uri
        return HttpClient().GetStringAsync(Uri(url)).Result.strip()
    except Exception as ex:
        raise Exception(
            "Could not fetch {} - tried urllib2, WebClient and HttpClient, "
            "all failed. Last error: {}".format(url, str(ex))
        )


# ---------------------------------------------------------------------------
# GitHub Releases API support.
#
# The GitHub REST API requires a User-Agent header on every request (it
# rejects requests without one), which plain urllib2.urlopen(url) does not
# send by default - so this needs an explicit Request object with headers,
# unlike the simpler fetch_text() above.
# ---------------------------------------------------------------------------

def fetch_json(url):
    """Fetch `url` and parse the response body as JSON, returning a plain
    dict/list. Used to read the GitHub Releases API (which returns JSON,
    not plain text). Tries the same cascading HTTP mechanisms as
    fetch_text()/download_file(), each with an explicit User-Agent header
    since the GitHub API rejects requests that don't send one."""
    import json

    try:
        import urllib2
        request = urllib2.Request(url, headers={"User-Agent": "pyVCI-Update"})
        raw_text = urllib2.urlopen(request).read()
        return json.loads(raw_text)
    except Exception:
        pass

    import clr
    for assembly_name in ("System.Net.Requests", "System", "System.Net"):
        try:
            clr.AddReference(assembly_name)
            from System.Net import WebClient
            client = WebClient()
            client.Headers.Add("User-Agent", "pyVCI-Update")
            raw_text = client.DownloadString(url)
            return json.loads(raw_text)
        except Exception:
            continue

    try:
        clr.AddReference('System.Net.Http')
        from System.Net.Http import HttpClient
        from System import Uri
        http_client = HttpClient()
        http_client.DefaultRequestHeaders.Add("User-Agent", "pyVCI-Update")
        raw_text = http_client.GetStringAsync(Uri(url)).Result
        return json.loads(raw_text)
    except Exception as ex:
        raise Exception(
            "Could not fetch {} - tried urllib2, WebClient and HttpClient, "
            "all failed. Last error: {}".format(url, str(ex))
        )


def mirror_sync_tree(source_dir, dest_dir, protect_names=None):
    """Make `dest_dir` match `source_dir` EXACTLY: copy every file from
    source_dir into dest_dir (creating folders, overwriting existing
    files), then delete any file/folder in dest_dir that does NOT exist
    in source_dir. This is what makes a tool removed on GitHub actually
    disappear from every machine on the next Update, instead of lingering
    forever (copy-only never used to clean up removed tools/panels).

    `protect_names` is a set of TOP-LEVEL entry names inside dest_dir
    (e.g. {'.git'}) that are never inspected or deleted, no matter what -
    this is what keeps this safe to run on a machine where dest_dir is
    also a git working folder: the .git folder (and anything in it) is
    completely untouched by this function.

    Returns (copied_count, removed_count)."""
    protect_names = set(protect_names or [])

    # 1) Collect every relative file path that exists in source_dir - this
    #    is the "truth" dest_dir must end up matching.
    source_files = set()
    for root, _dirs, files in os.walk(source_dir):
        rel_root = os.path.relpath(root, source_dir)
        for file_name in files:
            rel_path = (file_name if rel_root == "."
                        else os.path.join(rel_root, file_name))
            source_files.add(rel_path)

    # 2) Copy phase - same behavior as a plain copy-overwrite.
    copied_count = 0
    for root, _dirs, files in os.walk(source_dir):
        rel_root = os.path.relpath(root, source_dir)
        dest_folder = dest_dir if rel_root == "." else os.path.join(dest_dir, rel_root)
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
        for file_name in files:
            src_file = os.path.join(root, file_name)
            dst_file = os.path.join(dest_folder, file_name)
            shutil.copy2(src_file, dst_file)
            copied_count += 1

    # 3) Delete phase - remove anything under dest_dir that isn't in
    #    source_files, never descending into a protected top-level entry.
    removed_count = 0
    for root, dirs, files in os.walk(dest_dir, topdown=True):
        rel_root = os.path.relpath(root, dest_dir)
        if rel_root == ".":
            dirs[:] = [d for d in dirs if d not in protect_names]
        else:
            top_level = rel_root.split(os.sep)[0]
            if top_level in protect_names:
                dirs[:] = []
                continue
        for file_name in files:
            rel_path = (file_name if rel_root == "."
                        else os.path.join(rel_root, file_name))
            if rel_path not in source_files:
                try:
                    os.remove(os.path.join(root, file_name))
                    removed_count += 1
                except Exception:
                    pass

    # 4) Prune folders left empty by the delete phase (e.g. a removed
    #    tool's now-empty .pushbutton/.panel folders), again skipping
    #    anything under a protected top-level entry.
    for root, _dirs, _files in os.walk(dest_dir, topdown=False):
        if root == dest_dir:
            continue
        rel_root = os.path.relpath(root, dest_dir)
        top_level = rel_root.split(os.sep)[0]
        if top_level in protect_names:
            continue
        try:
            if not os.listdir(root):
                os.rmdir(root)
        except Exception:
            pass

    return copied_count, removed_count


def find_single_subdir(path):
    """Return the full path of the ONE subdirectory inside `path`, or None
    if there isn't exactly one. A GitHub zip download (branch archive or
    release zipball) always extracts to a single top-level folder, but its
    exact name varies (e.g. 'pyVCI-main' for a branch, 'ksnguyentrungkt-
    pyVCI-<shortsha>' for a release zipball) - this avoids hard-coding that
    name and breaking if the naming pattern ever changes."""
    try:
        entries = [
            name for name in os.listdir(path)
            if os.path.isdir(os.path.join(path, name))
        ]
    except Exception:
        return None
    if len(entries) == 1:
        return os.path.join(path, entries[0])
    return None
