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
        self._last_app = None
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
                gui.NVDASettingsDialog.categoryClasses.remove(VoiceSpeedSettingsPanel)
            except ValueError:
                pass

    def event_gainFocus(self, obj, nextHandler):
        try:
            if not obj or not obj.appModule:
                nextHandler()
                return

            app_name = obj.appModule.appName
            # Normalize to .exe for config matching if needed, or just use appName
            # Config uses "outlook.exe", appName is "outlook"
            # We'll check both "outlook" and "outlook.exe"
            
            # 1. App-based Language Switch
            target_lang = None
            profile = conf.get_profile(app_name)
            if not profile:
                 profile = conf.get_profile(app_name + ".exe")
            
            if profile and "language" in profile:
                target_lang = profile["language"]
                self._set_language(target_lang)
            
            # 2. Language-based Speed Adjustment
            # We do this always on focus, or only if we switched? 
            # Better to do it always to ensure consistency if user Alt-Tabs back
            self._adjust_rate_for_current_language(target_lang)

        except Exception as e:
            log.error(f"VoiceSpeedManager: Error in event_gainFocus: {e}")
        
        nextHandler()

    def _set_language(self, lang_code):
        synth = synthDriverHandler.getSynth()
        current_lang = synth.language
        
        # Avoid redundant switching which might interrupt speech
        if current_lang == lang_code:
            return

        try:
            # 1. Try direct assignment (most robust if synth supports it)
            synth.language = lang_code
            log.info(f"VoiceSpeedManager: Switched language to {lang_code}")
            return
        except Exception:
            pass
        
        # 2. Fallback: Search in availableLanguages
        try:
            available = synth.availableLanguages
            # normalized comparison
            target = lang_code.lower().replace("-", "_")
            
            for lang in available:
                l = lang.lower().replace("-", "_")
                if l == target or l.startswith(target + "_"):
                    synth.language = lang
                    log.info(f"VoiceSpeedManager: Switched language to {lang} (matched from {lang_code})")
                    return
            
            log.warning(f"VoiceSpeedManager: Could not find language match for {lang_code}")

        except Exception as e:
            log.error(f"VoiceSpeedManager: Failed to set language {lang_code}: {e}")

    def _adjust_rate_for_current_language(self, forced_lang=None):
        synth = synthDriverHandler.getSynth()
        # If we just forced a language, use that. Otherwise ask synth.
        lang = forced_lang if forced_lang else synth.language
        
        rate = conf.get_rate(lang)
        if rate is not None:
            # Only set if different to avoid jitter?
            # But synth.rate might be float, config is int.
            if abs(synth.rate - rate) > 1:
                synth.rate = rate
                log.info(f"VoiceSpeedManager: Adjusted rate to {rate} for language {lang}")
