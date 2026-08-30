# mypy: disable-error-code="method-assign"
"""Wrapper to run ansible-playbook on Windows with necessary Unix stubs."""

import ctypes
import ctypes.util
import locale
import multiprocessing
import platform
import sys

# --- Patch 1: locale encoding ---
_original_getlocale = locale.getlocale


def _patched_getlocale(*args, **kwargs):
    result = _original_getlocale(*args, **kwargs)
    if result and result[1] and result[1].lower() not in ("utf-8", "utf8"):
        return (result[0], "UTF-8")
    return result


locale.getlocale = _patched_getlocale

# --- Patch 2: multiprocessing fork -> spawn ---
if platform.system() == "Windows":
    _original_get_context = multiprocessing.get_context

    def _patched_get_context(method=None):
        if method == "fork":
            method = "spawn"
        return _original_get_context(method)

    multiprocessing.get_context = _patched_get_context

# --- Patch 3: ctypes libc loading for Windows ---
if platform.system() == "Windows":
    _original_find_library = ctypes.util.find_library

    # Load msvcrt for wcwidth
    _msvcrt = ctypes.CDLL("msvcrt")

    def _patched_find_library(name):
        if name == "c":
            return "ucrtbase"
        return _original_find_library(name)

    ctypes.util.find_library = _patched_find_library

    # After Ansible loads _LIBC, we need wcwidth to come from msvcrt
    # Hook into ctypes.CDLL attribute access to inject wcwidth
    _orig_cdll_getattr = ctypes.CDLL.__getattr__  # type: ignore[attr-defined]

    def _patched_cdll_getattr(self, name):  # type: ignore[misc]
        if name == "wcwidth":
            return _msvcrt.wcwidth
        try:
            return _orig_cdll_getattr(self, name)
        except AttributeError:
            raise AttributeError(f"function '{name}' not found") from None

    ctypes.CDLL.__getattr__ = _patched_cdll_getattr  # type: ignore[attr-defined]

# --- Patch 4: Install Unix module stubs ---
if platform.system() == "Windows":
    import types

    _stub_modules = {
        "fcntl": {
            "F_SETFL": 4,
            "O_NONBLOCK": 2048,
            "fcntl": lambda *a, **kw: None,
            "ioctl": lambda *a, **kw: 0,
        },
        "termios": {
            "TCSANOW": 0,
            "TCSADRAIN": 1,
            "TCSAFLUSH": 2,
            "tcgetattr": lambda *a, **kw: [],
            "tcsetattr": lambda *a, **kw: None,
        },
        "resource": {
            "RLIMIT_NOFILE": 4,
            "getrlimit": lambda *a, **kw: (1024, 1024),
            "setrlimit": lambda *a, **kw: None,
        },
    }

    for mod_name, attrs in _stub_modules.items():
        if mod_name not in sys.modules:
            mod = types.ModuleType(mod_name)
            for k, v in attrs.items():
                setattr(mod, k, v)
            sys.modules[mod_name] = mod

# --- Run ansible-playbook ---
from ansible.cli.playbook import main

sys.argv = ["ansible-playbook"] + sys.argv[1:]
main()
