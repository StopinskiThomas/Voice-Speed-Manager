import os
import json
import globalVars
from logHandler import log

CONFIG_FILENAME = "voiceSpeedManager.json"

# New Default Config Structure
DEFAULT_CONFIG = {
    "apps": {}
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
                    # Simple validation/migration: if old format, reset or migrate?
                    # Old format had "profiles" (dict) and "rates" (dict).
                    # New format has "apps" (dict).
                    if "apps" in loaded:
                        self.data = loaded
                    else:
                        log.warning("VoiceSpeedManager: Old config format detected. Resetting to new structure.")
                        # Ideally we would migrate, but for this restructure we start fresh to ensure consistency.
                        self.data = DEFAULT_CONFIG.copy()
            else:
                self.save()
        except Exception as e:
            log.error(f"VoiceSpeedManager: Error loading config: {e}")
            self.data = DEFAULT_CONFIG.copy()

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            log.error(f"VoiceSpeedManager: Error saving config: {e}")

    # --- App Management ---
    def add_app(self, exe_name, full_path=""):
        exe_name = exe_name.lower()
        if exe_name not in self.data["apps"]:
            self.data["apps"][exe_name] = {
                "path": full_path,
                "profiles": []
            }
            self.save()
            return True
        return False

    def remove_app(self, exe_name):
        exe_name = exe_name.lower()
        if exe_name in self.data["apps"]:
            del self.data["apps"][exe_name]
            self.save()
            return True
        return False

    def get_apps(self):
        return self.data["apps"]

    def get_app_details(self, exe_name):
        return self.data["apps"].get(exe_name.lower())

    # --- Language Profile Management ---
    def add_profile(self, exe_name, language, rate, auto_switch=False):
        exe_name = exe_name.lower()
        if exe_name in self.data["apps"]:
            profiles = self.data["apps"][exe_name]["profiles"]
            # Remove existing profile for this language if it exists
            profiles = [p for p in profiles if p["language"] != language]
            
            new_profile = {
                "language": language,
                "rate": int(rate),
                "auto_switch": auto_switch
            }
            profiles.append(new_profile)
            self.data["apps"][exe_name]["profiles"] = profiles
            self.save()
            return True
        return False

    def remove_profile(self, exe_name, language):
        exe_name = exe_name.lower()
        if exe_name in self.data["apps"]:
            profiles = self.data["apps"][exe_name]["profiles"]
            initial_len = len(profiles)
            profiles = [p for p in profiles if p["language"] != language]
            if len(profiles) < initial_len:
                self.data["apps"][exe_name]["profiles"] = profiles
                self.save()
                return True
        return False

    def get_profiles(self, exe_name):
        exe_name = exe_name.lower()
        if exe_name in self.data["apps"]:
            return self.data["apps"][exe_name]["profiles"]
        return []

# Global instance
conf = ConfigManager()
