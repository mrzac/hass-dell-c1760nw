"""Rend les modules purs (api/, models) importables sans Home Assistant.

Le `__init__.py` du composant importe Home Assistant ; on enregistre donc le paquet
« à vide » (chemin seul) pour que seuls les sous-modules testés soient exécutés.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for name, path in (
    ("custom_components", ROOT / "custom_components"),
    ("custom_components.dell_c1760nw", ROOT / "custom_components" / "dell_c1760nw"),
):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
