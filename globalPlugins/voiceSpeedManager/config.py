import os
import json
import globalVars
from logHandler import log

CONFIG_FILENAME = "voiceSpeedManager.json"

DEFAULT_CONFIG = {
    "profiles": {
        "outlook.exe": {"language": "de"},
        "code.exe": {"language": "en"}
    },
    "rates": {
        "de": 40,
        "en": 20
    },
    "default_rate": 30
}

class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(globalVars.appArgs.configPath, CONFIG_FILENAME)
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.data.update(loaded)
                    # Ensure sub-dictionaries are also merged/present if missing in file
                    if "profiles" not in self.data: self.data["profiles"] = {}
                    if "rates" not in self.data: self.data["rates"] = {}
            else:
                self.save()
        except Exception as e:
            log.error(f"VoiceSpeedManager: Error loading config: {e}")

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            log.error(f"VoiceSpeedManager: Error saving config: {e}")

    def get_profile(self, app_name):
        return self.data["profiles"].get(app_name.lower())

    def get_rate(self, lang_code):
        # Try exact match, then short code (e.g. 'de-DE' -> 'de')
        if lang_code in self.data["rates"]:
            return self.data["rates"][lang_code]
        short_code = lang_code.split("_")[0].split("-")[0]
        return self.data["rates"].get(short_code)

    def set_profile(self, app_name, language):
        self.data["profiles"][app_name.lower()] = {"language": language}
        self.save()

    def set_rate(self, lang_code, rate):
        self.data["rates"][lang_code] = rate
        self.save()

# Global instance
conf = ConfigManager()
