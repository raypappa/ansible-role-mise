"""Wrapper to run ansible-playbook with UTF-8 locale on Windows."""

import locale
import sys

# Monkey-patch locale to report UTF-8
_original_getlocale = locale.getlocale


def _patched_getlocale(*args, **kwargs):
    result = _original_getlocale(*args, **kwargs)
    if result and result[1] and result[1].lower() not in ("utf-8", "utf8"):
        return (result[0], "UTF-8")
    return result


locale.getlocale = _patched_getlocale

from ansible.cli.playbook import main

sys.argv = ["ansible-playbook"] + sys.argv[1:]
main()
