"""MAJLISH Android bridge.

The Kotlin UI calls the functions in this file.  All PAK / Lua work is done by
majlish_core.py, which is your original tool code with the terminal screens removed.
Every function returns a JSON string so the Kotlin side stays simple.
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

from rich.console import Console as _RichConsole

import majlish_core as core

BASE = None          # workspace root (set by init)
_sink = None         # Kotlin object with log(String) / progress(int, int, String)

RESERVED_TOP = {"PAK", "UNPACK", "REPACK", "RESULT", "PAK TOOL", "EXE", "LUA TOOL"}


# ------------------------------------------------------------------ output plumbing
def _emit(text):
    s = _sink
    if s is None or text is None:
        return
    try:
        s.log(str(text))
    except Exception:
        pass


def _progress(done, total, label):
    s = _sink
    if s is None:
        return
    try:
        s.progress(int(done), int(total), str(label))
    except Exception:
        pass


class _ConsoleShim:
    """Stands in for rich's Console: renders markup/panels/tables to plain text for the app log."""

    def __init__(self):
        self._buf = io.StringIO()
        self._rc = _RichConsole(file=self._buf, force_terminal=False, color_system=None,
                                width=64, highlight=False, emoji=True, legacy_windows=False)

    def print(self, *objects, **kw):
        kw.pop("style", None)
        try:
            self._buf.seek(0)
            self._buf.truncate(0)
            self._rc.print(*objects, **kw)
            text = self._buf.getvalue()
        except Exception:
            text = re.sub(r"\[/?[^\]]*\]", "", " ".join(str(o) for o in objects)) + "\n"
        _emit(text.rstrip("\n"))

    def status(self, *a, **k):
        return contextlib.nullcontext()

    def input(self, *a, **k):
        return ""

    def clear(self, *a, **k):
        pass

    def rule(self, *a, **k):
        pass


class _FakeProgress:
    """Replaces rich.progress.Progress so unpack progress shows in the app's progress bar."""

    def __init__(self, *a, **k):
        self.total = 0
        self.done = 0
        self.desc = ""
        self._last = 0.0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        _progress(self.done, self.total, self.desc)
        return False

    def add_task(self, description="", total=None, **k):
        self.total = int(total or 0)
        self.desc = re.sub(r"\[/?[^\]]*\]", "", str(description))
        _progress(0, self.total, self.desc)
        return 0

    def update(self, task_id=0, advance=None, completed=None, description=None, total=None, **k):
        if total is not None:
            self.total = int(total)
        if completed is not None:
            self.done = int(completed)
        if advance:
            self.done += int(advance)
        if description:
            self.desc = re.sub(r"\[/?[^\]]*\]", "", str(description))
        now = time.time()
        if now - self._last > 0.25 or self.done >= self.total:
            self._last = now
            _progress(self.done, self.total, self.desc)


class _Writer:
    """Captures print()/traceback output while a task runs."""

    def write(self, s):
        if s and s.strip():
            _emit(s.rstrip("\n"))
        return len(s) if s else 0

    def flush(self):
        pass

    def isatty(self):
        return False


_answer = ""


def _safe_input(prompt=""):
    return _answer


def _android_sm4_encrypt_bulk(self, data):
    """Android-safe SM4 ECB path using the verified single-block primitive."""
    data = bytes(data)
    if len(data) % 16:
        raise ValueError("SM4 input length must be a multiple of 16 bytes")
    return b"".join(self.encrypt(data[i:i + 16]) for i in range(0, len(data), 16))


def _android_sm4_decrypt_bulk(self, data):
    """Android-safe SM4 ECB decrypt using the same block primitive as desktop."""
    data = bytes(data)
    if len(data) % 16:
        raise ValueError("SM4 input length must be a multiple of 16 bytes")
    return b"".join(self.decrypt(data[i:i + 16]) for i in range(0, len(data), 16))


def _patch_core():
    core.console = _ConsoleShim()
    # Android has no runtime gcc toolchain. Avoid the optional native/T-table
    # bulk path and use the same single-block SM4 primitive as the desktop tool.
    core.SM4.encrypt_bulk = _android_sm4_encrypt_bulk
    core.SM4.decrypt_bulk = _android_sm4_decrypt_bulk
    core.Progress = _FakeProgress
    for name in ("SpinnerColumn", "TextColumn", "BarColumn", "TaskProgressColumn",
                 "TimeElapsedColumn", "TimeRemainingColumn"):
        setattr(core, name, lambda *a, **k: None)
    core.safe_input = _safe_input
    # No C compiler on Android: skip the gcc attempt and use the built-in Python SM4.
    core._FAST_SM4_TRIED = True
    core._FAST_SM4_LIB = None


# ------------------------------------------------------------------ setup / listing
def init(base_dir):
    global BASE
    BASE = Path(base_dir)
    BASE.mkdir(parents=True, exist_ok=True)
    core.ensure_directories(BASE)
    _patch_core()
    return json.dumps({"ok": True, "base": str(BASE)})


def _size(n):
    return core.human_size(n)


def _dir_size(p):
    total = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _paks(d):
    if not d.exists():
        return []
    return sorted((p for p in d.iterdir() if p.is_file() and p.suffix.lower() == ".pak"),
                  key=lambda p: p.name.lower())


def list_items(kind):
    items = []
    if kind in ("pak", "toolpak"):
        d = BASE / "PAK" if kind == "pak" else BASE / "PAK TOOL" / "PAK"
        for p in _paks(d):
            items.append({"name": p.name, "path": str(p), "detail": _size(p.stat().st_size)})
    elif kind == "unpack":
        for p in core.detect_unpacked_paks(BASE):
            ed = p / "edited"
            n = 0
            if ed.exists():
                n = sum(1 for f in ed.rglob("*")
                        if f.is_file() and f.name not in core.SKIP_NAMES and not f.name.startswith("Debug_"))
            items.append({"name": p.name, "path": str(p), "detail": "%d edited file(s) ready" % n})
    elif kind == "result":
        for label, d in (("RESULT", BASE / "RESULT"), ("PAK TOOL/RESULT", BASE / "PAK TOOL" / "RESULT")):
            for p in _paks(d):
                items.append({"name": p.name, "path": str(p),
                              "detail": "%s  •  %s" % (label, _size(p.stat().st_size))})
    elif kind == "folders":
        cands = []
        for sub in ("UNPACK", "REPACK"):
            d = BASE / sub
            if d.exists():
                cands += [p for p in sorted(d.iterdir()) if p.is_dir()]
        if BASE.exists():
            cands += [p for p in sorted(BASE.iterdir()) if p.is_dir() and p.name not in RESERVED_TOP]
        for p in cands:
            items.append({"name": str(p.relative_to(BASE)), "path": str(p), "detail": _size(_dir_size(p))})
    elif kind in ("lua_org", "lua_edit"):
        d = core._lua_dirs(BASE)["org" if kind == "lua_org" else "edit"]
        d.mkdir(parents=True, exist_ok=True)
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() in (".lua", ".luac"):
                items.append({"name": p.name, "path": str(p), "detail": _size(p.stat().st_size)})
    return json.dumps(items)


# ------------------------------------------------------------------ tasks
def _result(ok, message=""):
    return {"ok": bool(ok), "message": message}


def t_unpack(pak_path):
    pak_file = Path(pak_path)
    core.console.print("[bold #00FFFF]🚀 Unpacking %s...[/bold #00FFFF]" % pak_file.name)
    pak = core.TencentPakFile(pak_file)
    unpack_path = BASE / "UNPACK" / pak_file.stem
    repack_path = BASE / "REPACK" / pak_file.stem
    pak.dump(unpack_path)
    log_path = unpack_path / ("Debug_%s.log" % pak_file.stem)
    core.dump_unpacking_log(pak, log_path)
    for dir_path, _ in pak._index.items():
        (repack_path / pak._mount_point / dir_path).mkdir(parents=True, exist_ok=True)
    edited_dir = unpack_path / "edited"
    edited_dir.mkdir(parents=True, exist_ok=True)
    try:
        n1 = core.write_pack_index_csv(pak, unpack_path / "index.csv")
        core.ensure_exe_index(BASE, pak, pak_file.stem)
        core.console.print("[dim]📄 index.csv: UNPACK/%s/index.csv (%d paths) + EXE/index.csv[/dim]" % (pak_file.stem, n1))
    except Exception as e:  # noqa
        core.console.print("⚠ index.csv warn: %s" % e)
    core.console.print("[bold #00FF88]✅ SUCCESS: Extracted to %s[/bold #00FF88]" % unpack_path)
    core.console.print("Edited folder: UNPACK/%s/edited/  (put your edited files here, then use REPACK)" % pak_file.stem)
    return _result(True, "Extracted to UNPACK/%s" % pak_file.stem)


def _repack_common(unpack_name, mode, target):
    global _answer
    _answer = mode or "1"
    started = time.time()
    entry = BASE / "UNPACK" / unpack_name
    core.do_repack_from_unpack(BASE, entry, force_target_path=target)
    out = core.find_original_pak_for_unpack(BASE, unpack_name)
    res = BASE / "RESULT" / (out.name if out else unpack_name + ".pak")
    ok = res.exists() and res.stat().st_mtime >= started - 1
    return _result(ok, ("Saved to RESULT/%s" % res.name) if ok else "Repack did not produce a PAK - see log")


def t_repack(unpack_name, mode):
    return _repack_common(unpack_name, mode, None)


def t_repack_to_path(unpack_name, target):
    target = (target or "").replace("\\", "/").strip("/")
    if not target:
        core.console.print("[bold #FF0055]❌ Invalid target path![/bold #FF0055]")
        return _result(False, "Invalid target path")
    return _repack_common(unpack_name, "1", target)


def _as_bool(value):
    """Parse the Kotlin/JSON choice without treating the string 'false' as True."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return True
        if v in ("0", "false", "no", "n", "off", ""):
            return False
    raise ValueError("Invalid SM4 encryption choice: %r" % (value,))


def _check_android_sm4():
    """Known-answer + bulk/block consistency test before touching any PAK."""
    key = bytes.fromhex("0123456789abcdeffedcba9876543210")
    plain = key
    expected = bytes.fromhex("077acbfdf01515d6135f18bbeb83db05")
    cipher = core.SM4(key)
    block_result = cipher.encrypt(plain)
    bulk_result = cipher.encrypt_bulk(plain)
    if block_result != expected or bulk_result != block_result:
        raise RuntimeError("Android SM4 encrypt self-test failed; no PAK was written")
    if cipher.decrypt(bulk_result) != plain or cipher.decrypt_bulk(bulk_result) != plain:
        raise RuntimeError("Android SM4 decrypt self-test failed; no PAK was written")


def t_inject(pak_path, encrypt):
    pak_file = Path(pak_path)
    tool = BASE / "PAK TOOL"
    edit_dir = tool / "EDIT"
    result_dir = tool / "RESULT"
    result_dir.mkdir(parents=True, exist_ok=True)
    if not edit_dir.exists() or not any(edit_dir.iterdir()):
        core.console.print("[bold #FF0055]❌ ERROR: No files in PAK TOOL/EDIT folder.[/bold #FF0055]")
        core.console.print("[#FFAA00]⚠ Place each file at its in-pak path (e.g. EDIT/Content/Lua/a.lua)[/#FFAA00]")
        return _result(False, "PAK TOOL/EDIT is empty")
    encrypt_enabled = _as_bool(encrypt)
    # Existing PAK entries may already be SM4 encrypted. Even when the user
    # chooses NO for newly-added files, replacements retain their original
    # encryption method and therefore still pass through SM4 during injection.
    _check_android_sm4()
    if encrypt_enabled:
        core.console.print("[bold #00FFFF]🔐 SM4 encryption: ON (Android block-safe engine)[/bold #00FFFF]")
    else:
        core.console.print("[bold #00FFFF]SM4 for new files: OFF; existing entry encryption is preserved[/bold #00FFFF]")
    core.console.print("[bold #00FFFF]🚀 Injecting files into %s...[/bold #00FFFF]" % pak_file.name)
    pak = core.TencentPakFile(pak_file)
    output_pak = result_dir / pak_file.name
    edited, added = core.inject_edit_files(pak, edit_dir, output_pak, protect_new=encrypt_enabled, sm4_type=47)
    core.console.print("[bold #00FF88]✅ Edited: %s files | Added: %s files[/bold #00FF88]" % (edited, added))
    core.console.print("[bold #00FF88]📦 Output: %s[/bold #00FF88]" % output_pak)
    return _result(True, "Edited %s, added %s  →  PAK TOOL/RESULT/%s" % (edited, added, output_pak.name))


def t_protect(pak_path):
    pak_file = Path(pak_path)
    result_dir = BASE / "PAK TOOL" / "RESULT"
    result_dir.mkdir(parents=True, exist_ok=True)
    core.console.print("[bold #FF00FF]🔒 Protecting %s...[/bold #FF00FF]" % pak_file.name)
    core.console.print("This can take a long time on very large paks. Keep the app open.")
    pak = core.TencentPakFile(pak_file)
    output_pak = result_dir / pak_file.name
    protected, skipped = core.protect_pak_file(pak, output_pak, sm4_type=47)
    core.console.print("[bold #00FF88]✅ PROTECTED: %s files re-encrypted (SM4)[/bold #00FF88]" % protected)
    core.console.print("Skipped (undecryptable/kept as-is): %s files" % skipped)
    core.console.print("[bold #00FF88]📦 Output: %s[/bold #00FF88]" % output_pak)
    return _result(True, "Protected %s files  →  PAK TOOL/RESULT/%s" % (protected, output_pak.name))


def t_delete(folder_path):
    p = Path(folder_path).resolve()
    base = BASE.resolve()
    if base not in p.parents or p == base or p.name in RESERVED_TOP and p.parent == base:
        return _result(False, "Refused: not a workspace folder")
    shutil.rmtree(p)
    core.console.print("[bold #00FF88]✅ Deleted: %s[/bold #00FF88]" % p.relative_to(base))
    return _result(True, "Deleted %s" % p.relative_to(base))


def t_export(src_path, dest_dir):
    src = Path(src_path)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / src.name
    i = 1
    while out.exists():
        out = dest / ("%s_%d%s" % (src.stem, i, src.suffix))
        i += 1
    core.console.print("Copying %s (%s)..." % (src.name, _size(src.stat().st_size)))
    shutil.copy2(src, out)
    core.console.print("[bold #00FF88]✅ Saved: %s[/bold #00FF88]" % out)
    return _result(True, str(out))


def _is_bytecode(data):
    return data[:4] == b"\x1bLua" or data[:3] == b"\x1bLJ"


def t_lua_to_standard(paths):
    d = core._lua_dirs(BASE)
    key = core._lua_load_key(d["base"])
    d["dec"].mkdir(parents=True, exist_ok=True)
    ok_n = 0
    for p in paths:
        f = Path(p)
        try:
            out = d["dec"] / (f.stem + ".luac")
            out.write_bytes(core.lua_process_file(f.read_bytes(), key, is_encrypt=False))
            core.console.print("[bold #00FF88]✅ %s  →  LUA TOOL/Lua_Decript/%s[/bold #00FF88]" % (f.name, out.name))
            ok_n += 1
        except Exception as e:  # noqa
            core.console.print("[bold #FF0055]❌ %s: %s[/bold #FF0055]" % (f.name, e))
    return _result(ok_n == len(paths) and ok_n > 0, "%d/%d converted" % (ok_n, len(paths)))


def t_lua_to_game(paths):
    d = core._lua_dirs(BASE)
    key = core._lua_load_key(d["base"])
    if not key:
        core.console.print("⚠ Lua XOR key missing: put HEX in LUA TOOL/lua_xor_key.txt")
        return _result(False, "Lua XOR key missing")
    d["res"].mkdir(parents=True, exist_ok=True)
    ok_n = 0
    for p in paths:
        f = Path(p)
        try:
            data = f.read_bytes()
            if not _is_bytecode(data):
                core.console.print("[bold #FFAA00]⚠ %s is Lua source text. Compile it to Lua 5.3 bytecode (.luac) first - "
                                   "Android has no luac compiler.[/bold #FFAA00]" % f.name)
                continue
            out = d["res"] / (f.stem + ".lua")
            out.write_bytes(core.lua_process_file(data, key, is_encrypt=True))
            core.console.print("[bold #00FF88]✅ %s  →  LUA TOOL/Lua_Rueslt/%s[/bold #00FF88]" % (f.name, out.name))
            ok_n += 1
        except Exception as e:  # noqa
            core.console.print("[bold #FF0055]❌ %s: %s[/bold #FF0055]" % (f.name, e))
    return _result(ok_n == len(paths) and ok_n > 0, "%d/%d converted" % (ok_n, len(paths)))


TASKS = {
    "unpack": t_unpack,
    "repack": t_repack,
    "repack_to_path": t_repack_to_path,
    "inject": t_inject,
    "protect": t_protect,
    "delete": t_delete,
    "export": t_export,
    "lua_to_standard": t_lua_to_standard,
    "lua_to_game": t_lua_to_game,
}


def run(task, args_json, sink):
    """Run one task. `sink` is a Kotlin object with log(String) and progress(Int, Int, String)."""
    global _sink
    _sink = sink
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = _Writer()
    t0 = time.time()
    try:
        res = TASKS[task](**json.loads(args_json))
    except Exception as e:  # noqa
        _emit("❌ %s: %s" % (type(e).__name__, e))
        _emit(traceback.format_exc())
        res = _result(False, "%s: %s" % (type(e).__name__, e))
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        _sink = None
    res["seconds"] = int(time.time() - t0)
    return json.dumps(res)
