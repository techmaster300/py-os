import json
import os
import locale

LANG_DIR = os.path.join(os.path.dirname(__file__), "lang")
_TRANSLATION = None

def available_languages():
    langs = {}
    if not os.path.exists(LANG_DIR):
        return {"en": "English"}
    for f in sorted(os.listdir(LANG_DIR)):
        if f.endswith(".json"):
            code = f[:-5]
            name = code.upper()
            langs[code] = name
    if not langs:
        langs["en"] = "English"
    return langs

def detect_system_lang():
    try:
        code, _ = locale.getdefaultlocale()
        if code:
            code = code.split("_")[0]
            if code in available_languages():
                return code
    except Exception:
        pass
    return "en"

class Translation:
    def __init__(self, lang_code="en"):
        self.lang_code = lang_code
        self.strings = {}
        self._load()

    def _load(self):
        path = os.path.join(LANG_DIR, f"{self.lang_code}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.strings = json.load(f)
            except Exception:
                pass

    def get(self, key, **kwargs):
        val = self.strings.get(key, key)
        if kwargs and isinstance(val, str):
            try:
                return val.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return val

    def __call__(self, key, **kwargs):
        return self.get(key, **kwargs)

def set_language(lang_code):
    global _TRANSLATION
    _TRANSLATION = Translation(lang_code)

def _(key, **kwargs):
    global _TRANSLATION
    if _TRANSLATION is None:
        return key
    return _TRANSLATION.get(key, **kwargs)

def get_translation():
    global _TRANSLATION
    return _TRANSLATION
