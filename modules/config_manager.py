import json
import os
import sys

class ConfigManager:
    def __init__(self):
        # Determinar raiz do sistema (se executável ou script)
        if getattr(sys, 'frozen', False):
            # Se executável, a raiz é a pasta onde o .exe está
            self.root_dir = os.path.dirname(sys.executable)
        else:
            # Se script, a raiz é a pasta acima de 'modules'
            self.root_dir = os.path.dirname(os.path.dirname(__file__))
            
        self.config_path = os.path.join(self.root_dir, 'config.json')
        self.default_config = {
            "appearance_mode": "dark",
            "volume": 0.5,
            "theme_accent": "#c3000d",
            "music_dir": r"C:\Users\Ricardo\Music",
            "last_view": "home"
        }
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return {**self.default_config, **json.load(f)}
            except:
                return self.default_config
        return self.default_config

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            return True
        except:
            return False

    def get(self, key):
        return self.config.get(key, self.default_config.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()
