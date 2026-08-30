"""Wrapper to run ansible-playbook with UTF-8 locale on Windows."""

import locale
import multiprocessing
import platform
import sys

# Monkey-patch locale to report UTF-8
_original_getlocale = locale.getlocale


def _patched_getlocale(*args, **kwargs):
    result = _original_getlocale(*args, **kwargs)
    if result and result[1] and result[1].lower() not in ("utf-8", "utf8"):
        return (result[0], "UTF-8")
    return result


locale.getlocale = _patched_getlocale

# Monkey-patch multiprocessing to use 'spawn' on Windows (fork is Unix-only)
if platform.system() == "Windows":
    _original_get_context = multiprocessing.get_context

    def _patched_get_context(method=None):
        if method == "fork":
            method = "spawn"
        return _original_get_context(method)

    multiprocessing.get_context = _patched_get_context

from ansible.cli.playbook import main

sys.argv = ["ansible-playbook"] + sys.argv[1:]
main()
