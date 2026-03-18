import globalPluginHandler
import synthDriverHandler
import ui
import gui
from logHandler import log
from .config import conf

# Try to import Settings UI, but don't fail the whole plugin if it breaks
try:
    from .settings_ui import VoiceSpeedSettingsPanel
except Exception as e:
    log.error(f"VoiceSpeedManager: Failed to import Settings UI module: {e}")
    VoiceSpeedSettingsPanel = None

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super(GlobalPlugin, self).__init__()
        log.info("VoiceSpeedManager: GlobalPlugin Initialized")
        
        if VoiceSpeedSettingsPanel:
            try:
                gui.NVDASettingsDialog.categoryClasses.append(VoiceSpeedSettingsPanel)
                log.info("VoiceSpeedManager: Settings Panel registered")
            except Exception as e:
                log.error(f"VoiceSpeedManager: Failed to register settings panel: {e}")

    def terminate(self):
        super(GlobalPlugin, self).terminate()
        if VoiceSpeedSettingsPanel:
            try:
                if VoiceSpeedSettingsPanel in gui.NVDASettingsDialog.categoryClasses:
                    gui.NVDASettingsDialog.categoryClasses.remove(VoiceSpeedSettingsPanel)
            except ValueError:
                pass

    def event_gainFocus(self, obj, nextHandler):
        try:
            if not obj or not obj.appModule:
                nextHandler()
                return

            app_name = obj.appModule.appName
            # Check both "outlook" and "outlook.exe"
            app_config = conf.get_app_details(app_name)
            if not app_config:
                 app_config = conf.get_app_details(app_name + ".exe")
            
            if app_config:
                self._handle_app_focus(app_config)

        except Exception as e:
            log.error(f"VoiceSpeedManager: Error in event_gainFocus: {e}", exc_info=True)
        
        nextHandler()

    def _handle_app_focus(self, app_config):
        profiles = app_config.get("profiles", [])
        if not profiles:
            return

        # 1. Handle Auto-Switching
        # Find the first profile with auto_switch enabled
        auto_profile = next((p for p in profiles if p.get("auto_switch")), None)
        if auto_profile:
            self._set_language(auto_profile["language"])

        # 2. Handle Rate Adjustment
        # Get current language (it might have just changed)
        synth = synthDriverHandler.getSynth()
        current_lang = getattr(synth, "language", "")
        
        # Find profile matching current language
        # We try exact match, then fuzzy match (e.g. "en-US" matches "en")
        matched_profile = None
        
        # Exact match
        matched_profile = next((p for p in profiles if p["language"].lower() == current_lang.lower()), None)
        
        # Fuzzy match (if no exact match)
        if not matched_profile:
             # Try matching start (e.g. profile "en" matches synth "en-US")
             matched_profile = next((p for p in profiles if current_lang.lower().startswith(p["language"].lower())), None)

        if matched_profile:
            self._set_rate(matched_profile["rate"])

    def _set_language(self, lang_code):
        synth = synthDriverHandler.getSynth()
        current_lang = getattr(synth, "language", None)
        
        if current_lang == lang_code:
            return

        try:
            synth.language = lang_code
            log.info(f"VoiceSpeedManager: Switched language to {lang_code}")
        except Exception as e:
            log.error(f"VoiceSpeedManager: Failed to set language {lang_code}: {e}")

    def _set_rate(self, rate):
        synth = synthDriverHandler.getSynth()
        try:
            current_rate = getattr(synth, "rate", None)
            if current_rate is not None and abs(current_rate - rate) > 0:
                synth.rate = rate
                log.info(f"VoiceSpeedManager: Adjusted rate to {rate}")
        except Exception as e:
            log.error(f"VoiceSpeedManager: Failed to set rate {rate}: {e}")
