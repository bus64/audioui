# File: src/core/audio/presets/audio_presets_registry.py  © 2025 projectemergence. All rights reserved.

import pkgutil
import importlib
import inspect
import threading
import logging
import time

from core.audio.presets.base_preset import BasePreset
import core.audio.presets as presets_pkg

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class PresetRegistry:
    """
    Discovers and introspects all presets in core.audio.presets.
    No background polling—reload is entirely on-demand or manual.
    """
    def __init__(self):
        self.preset_map:  dict[str, type[BasePreset]]   = {}
        self.presets_sig: dict[str, inspect.Signature] = {}
        self.presets_meta: dict[str, dict[str, object]] = {}
        self._lock = threading.Lock()

        logger.debug("Initializing PresetRegistry")
        # initial load
        self._load_all_presets()

    def reload(self):
        """
        Manually trigger a full reload of all presets.
        Can be called at runtime from any external code.
        """
        logger.info("Manual reload of presets requested")
        self._load_all_presets()

    def _load_all_presets(self):
        """
        (Re)scan the presets package, import each module,
        pick a preset class, introspect its constructor,
        and update the registry maps. Thread-safe.
        """
        logger.debug("Loading presets from %s", presets_pkg.__path__)
        new_map, new_sigs, new_meta = {}, {}, {}

        for finder, name, ispkg in pkgutil.iter_modules(presets_pkg.__path__):
            if name.startswith("_"):
                logger.debug("  skipping internal module '%s'", name)
                continue

            mod_name = f"{presets_pkg.__name__}.{name}"
            try:
                logger.debug("  importing %s", mod_name)
                mod = importlib.reload(importlib.import_module(mod_name))
            except Exception as e:
                logger.exception("  failed to import %s: %s", mod_name, e)
                continue

            # 1) Prefer an explicit BasePreset subclass
            preset_cls = next(
                (c for _, c in inspect.getmembers(mod, inspect.isclass)
                 if issubclass(c, BasePreset) and c is not BasePreset),
                None
            )

            # 2) Fallback: first class defined in this module
            if not preset_cls:
                local = [
                    c for _, c in inspect.getmembers(mod, inspect.isclass)
                    if c.__module__ == mod_name
                ]
                if local:
                    preset_cls = local[0]
                    logger.debug("    fallback to local class %s in %s", preset_cls.__name__, name)

            if not preset_cls:
                logger.debug("    no class found for preset '%s'", name)
                continue

            # introspect constructor
            sig = inspect.signature(preset_cls.__init__)
            meta = {
                p.name: p.default
                for p in sig.parameters.values()
                if p.name != "self" and p.default is not inspect._empty
            }

            new_map[name]   = preset_cls
            new_sigs[name]  = sig
            new_meta[name]  = meta

            logger.info("Registered preset '%s' → %s(); params=%s",
                        name, preset_cls.__name__, list(meta.keys()))

        # swap in the new maps under lock
        with self._lock:
            self.preset_map.clear()
            self.preset_map.update(new_map)
            self.presets_sig.clear()
            self.presets_sig.update(new_sigs)
            self.presets_meta.clear()
            self.presets_meta.update(new_meta)

        logger.debug("PresetRegistry now contains: %s", list(self.preset_map.keys()))

    # no background thread or polling—_watch_loop is disabled
    def _watch_loop(self):
        return

# singleton instance
registry = PresetRegistry()
