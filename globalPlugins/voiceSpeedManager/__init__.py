import globalPluginHandler
import synthDriverHandler
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
        if VoiceSpeedSettingsPanel:
            try:
                gui.NVDASettingsDialog.categoryClasses.append(VoiceSpeedSettingsPanel)
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
            
            # Check for configuration using both "app" and "app.exe"
            app_config = conf.get_app_details(app_name)
            if not app_config:
                 app_config = conf.get_app_details(app_name + ".exe")
            
            if app_config:
                self._handle_app_focus(app_config)

        except Exception as e:
            log.error(f"VoiceSpeedManager: Error in event_gainFocus: {e}", exc_info=True)
        
        nextHandler()

    def _handle_app_focus(self, app_config):
        """
        Applies the language and rate settings based on the application's profile.
        """
        profiles = app_config.get("profiles", [])
        if not profiles:
            return

        # 1. Handle Auto-Switching
        # Find the first profile with auto_switch enabled
        auto_profile = next((p for p in profiles if p.get("auto_switch")), None)
        if auto_profile:
            self._set_language(auto_profile["language"])

        # 2. Handle Rate Adjustment
        synth = synthDriverHandler.getSynth()
        current_lang = getattr(synth, "language", "")
        
        # Find profile matching current language
        # Strategy: Exact Match -> Bidirectional Fuzzy Match
        
        # Exact match
        matched_profile = next((p for p in profiles if p["language"].lower() == current_lang.lower()), None)
        
        # Fuzzy match (if no exact match)
        if not matched_profile:
             # 1. Current starts with Profile (e.g. synth "en_US" matches profile "en")
             matched_profile = next((p for p in profiles if current_lang.lower().startswith(p["language"].lower())), None)
             
             # 2. Profile starts with Current (e.g. synth "en" matches profile "en_US")
             if not matched_profile:
                 matched_profile = next((p for p in profiles if p["language"].lower().startswith(current_lang.lower())), None)

        if matched_profile:
            self._set_rate(matched_profile["rate"])

    def _set_language(self, lang_code):
        """
        Robustly attempts to set the synthesizer language.
        1. Direct assignment (synth.language = code)
        2. availableLanguages search (fuzzy match)
        3. Voice switching (iterating availableVoices)
        """
        synth = synthDriverHandler.getSynth()
        current_lang = getattr(synth, "language", None)
        
        # Avoid redundant switching
        if current_lang == lang_code:
            return

        target_norm = lang_code.lower().replace("-", "_")

        # Method 1: Direct assignment
        try:
            synth.language = lang_code
            return
        except Exception:
            pass

        # Method 2: Search in availableLanguages
        try:
            available = getattr(synth, "availableLanguages", [])
            for lang in available:
                l_str = str(lang)
                l_norm = l_str.lower().replace("-", "_")
                
                # Bidirectional fuzzy match
                if (l_norm == target_norm or 
                    l_norm.startswith(target_norm + "_") or 
                    target_norm.startswith(l_norm + "_")):
                    synth.language = lang
                    return
        except Exception:
            pass

        # Method 3: Switch Voice (Fallback for SAPI5/OneCore)
        try:
            # Convert generator to list safely
            available_voices = list(getattr(synth, "availableVoices", []))
            
            # Pass A: Check 'language' attribute of voice objects
            for voice in available_voices:
                try:
                    v_lang = getattr(voice, "language", None)
                    if v_lang:
                        v_lang_norm = str(v_lang).lower().replace("-", "_")
                        if (v_lang_norm == target_norm or 
                            v_lang_norm.startswith(target_norm + "_") or 
                            target_norm.startswith(v_lang_norm + "_")):
                            
                            voice_id = getattr(voice, "id", voice)
                            synth.voice = voice_id
                            return
                except Exception:
                    continue
            
            # Pass B: Check ID or Name string for language code
            for voice in available_voices:
                try:
                    v_id = getattr(voice, "id", str(voice))
                    v_name = getattr(voice, "name", str(voice))
                    
                    v_id_norm = str(v_id).lower().replace("-", "_")
                    v_name_norm = str(v_name).lower().replace("-", "_")
                    
                    if target_norm in v_id_norm or target_norm in v_name_norm:
                         synth.voice = v_id
                         return
                except Exception:
                    continue

            log.warning(f"VoiceSpeedManager: Could not find a voice or language match for {lang_code}")

        except Exception as e:
            log.error(f"VoiceSpeedManager: Failed to switch voice/language to {lang_code}: {repr(e)}")

    def _set_rate(self, rate):
        synth = synthDriverHandler.getSynth()
        try:
            current_rate = getattr(synth, "rate", None)
            # Only set if significantly different to avoid jitter/spam
            if current_rate is not None and abs(current_rate - rate) > 0:
                synth.rate = rate
        except Exception as e:
            log.error(f"VoiceSpeedManager: Failed to set rate {rate}: {e}")
