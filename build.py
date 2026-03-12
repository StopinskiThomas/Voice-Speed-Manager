import zipfile
import os

ADDON_NAME = "voiceSpeedManager"
OUTPUT_FILE = f"{ADDON_NAME}.nvda-addon"

def create_addon():
    with zipfile.ZipFile(OUTPUT_FILE, 'w', zipfile.ZIP_DEFLATED) as addon:
        # Add manifest
        addon.write("manifest.ini")
        
        # Add globalPlugins
        for root, dirs, files in os.walk("globalPlugins"):
            for file in files:
                if file.endswith(".pyc") or file.endswith(".pyo"):
                    continue
                path = os.path.join(root, file)
                addon.write(path)
        
        # Add locale
        for root, dirs, files in os.walk("locale"):
            for file in files:
                path = os.path.join(root, file)
                addon.write(path)
        
        # Add doc
        for root, dirs, files in os.walk("doc"):
            for file in files:
                path = os.path.join(root, file)
                addon.write(path)
                
    print(f"Created {OUTPUT_FILE}")

if __name__ == "__main__":
    create_addon()
