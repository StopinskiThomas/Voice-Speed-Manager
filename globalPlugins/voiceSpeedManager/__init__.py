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
            log.info(f"VoiceSpeedManager: Focus entered. App: {app_name}")
            
            # Check both "outlook" and "outlook.exe"
            app_config = conf.get_app_details(app_name)
            if not app_config:
                 log.debug(f"VoiceSpeedManager: No config for '{app_name}', trying '{app_name}.exe'")
                 app_config = conf.get_app_details(app_name + ".exe")
            
            if app_config:
                log.info(f"VoiceSpeedManager: Found config for {app_name}: {app_config}")
                self._handle_app_focus(app_config)
            else:
                log.debug(f"VoiceSpeedManager: No configuration found for {app_name}")

        except Exception as e:
            log.error(f"VoiceSpeedManager: Error in event_gainFocus: {e}", exc_info=True)
        
        nextHandler()

    def _handle_app_focus(self, app_config):
        profiles = app_config.get("profiles", [])
        if not profiles:
            log.debug("VoiceSpeedManager: No profiles defined for this app.")
            return

        # 1. Handle Auto-Switching
        # Find the first profile with auto_switch enabled
        auto_profile = next((p for p in profiles if p.get("auto_switch")), None)
        if auto_profile:
            log.info(f"VoiceSpeedManager: Auto-switching enabled. Target: {auto_profile['language']}")
            self._set_language(auto_profile["language"])

        # 2. Handle Rate Adjustment
        # Get current language (it might have just changed)
        synth = synthDriverHandler.getSynth()
        current_lang = getattr(synth, "language", "")
        log.info(f"VoiceSpeedManager: Current synth language: {current_lang}")
        
        # Find profile matching current language
        # We try exact match, then fuzzy match (e.g. "en-US" matches "en")
        matched_profile = None
        
        # Exact match
        matched_profile = next((p for p in profiles if p["language"].lower() == current_lang.lower()), None)
        
        # Fuzzy match (if no exact match)
        if not matched_profile:
             # Try matching start (e.g. profile "en" matches synth "en-US")
             log.debug(f"VoiceSpeedManager: No exact match for {current_lang}. Trying fuzzy match...")
             matched_profile = next((p for p in profiles if current_lang.lower().startswith(p["language"].lower())), None)

        if matched_profile:
            log.info(f"VoiceSpeedManager: Matched profile: {matched_profile}. Applying rate: {matched_profile['rate']}")
            self._set_rate(matched_profile["rate"])
        else:
            log.info(f"VoiceSpeedManager: No matching profile found for language {current_lang} in {profiles}")

    def _set_language(self, lang_code):
        synth = synthDriverHandler.getSynth()
        current_lang = getattr(synth, "language", None)
        
        # Avoid redundant switching if we are already confident
        if current_lang == lang_code:
            return

        target_norm = lang_code.lower().replace("-", "_")

        # 1. Try direct assignment (some synths support this)
        try:
            synth.language = lang_code
            log.info(f"VoiceSpeedManager: Switched language to {lang_code} via property")
            return
        except Exception as e:
            log.debug(f"VoiceSpeedManager: Direct assignment of language '{lang_code}' failed: {e}")

        # 2. Fallback: Search in availableLanguages (for synths that expose languages but require specific strings)
        try:
            available = getattr(synth, "availableLanguages", [])
            for lang in available:
                l_str = str(lang)
                l_norm = l_str.lower().replace("-", "_")
                
                if l_norm == target_norm or l_norm.startswith(target_norm + "_"):
                    synth.language = lang
                    log.info(f"VoiceSpeedManager: Switched language to {lang} (matched from {lang_code})")
                    return
        except Exception as e:
            log.debug(f"VoiceSpeedManager: availableLanguages search failed: {e}")

        # 3. Fallback: Switch Voice (essential for OneCore and others)
        try:
            log.debug(f"VoiceSpeedManager: Attempting voice switch for language {lang_code}...")
            available_voices = getattr(synth, "availableVoices", [])
            
            # First pass: Exact language match
            for voice in available_voices:
                try:
                    # voice.language might be None or a string
                    v_lang = getattr(voice, "language", "")
                    if v_lang:
                        v_lang_norm = v_lang.lower().replace("-", "_")
                        if v_lang_norm == target_norm or v_lang_norm.startswith(target_norm + "_"):
                            synth.voice = voice.id
                            log.info(f"VoiceSpeedManager: Switched voice to {voice.name} for language {lang_code}")
                            return
                except Exception:
                    continue
            
            # Second pass: Match language in voice name (less reliable but useful fallback)
            for voice in available_voices:
                try:
                    v_name_norm = voice.name.lower()
                    # simplistic check: if "german" or "english" or "de" / "en" in name? 
                    # Too risky for short codes.
                    # But often voice names contain the code, e.g. "Microsoft Hedda Desktop - German"
                    # We can try to map some common codes to names if needed, but let's stick to 'language' property first.
                    pass
                except Exception:
                    continue

            log.warning(f"VoiceSpeedManager: Could not find a voice or language match for {lang_code}")

        except Exception as e:
            log.error(f"VoiceSpeedManager: Failed to switch voice/language to {lang_code}: {repr(e)}")

    def _set_rate(self, rate):
        synth = synthDriverHandler.getSynth()
        try:
            current_rate = getattr(synth, "rate", None)
            if current_rate is not None and abs(current_rate - rate) > 0:
                synth.rate = rate
                log.info(f"VoiceSpeedManager: Adjusted rate to {rate}")
        except Exception as e:
            log.error(f"VoiceSpeedManager: Failed to set rate {rate}: {e}")
