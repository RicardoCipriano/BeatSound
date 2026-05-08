import time
from main import BeatSoundSearch
import os
import sys

class Profiler(BeatSoundSearch):
    def __init__(self):
        t0 = time.time()
        import customtkinter as ctk
        super(ctk.CTk, self).__init__()
        self.title("BeatSoundSearch - Dj77  V.0.0.2")
        self.geometry("800x600")
        
        t1 = time.time()
        print(f"ctk init: {t1-t0:.3f}s")
        
        from modules.config_manager import ConfigManager
        self.config_manager = ConfigManager()
        t2 = time.time()
        print(f"ConfigManager: {t2-t1:.3f}s")
        
        from modules.database import Database
        self.db = Database()
        t3 = time.time()
        print(f"Database: {t3-t2:.3f}s")
        
        from modules.multi_api_enhancer import MultiAPIEnhancer
        self.api_enhancer = MultiAPIEnhancer(database=self.db)
        t4 = time.time()
        print(f"MultiAPIEnhancer: {t4-t3:.3f}s")
        
        from modules.player import MusicPlayer
        self.player = MusicPlayer()
        t5 = time.time()
        print(f"MusicPlayer: {t5-t4:.3f}s")
        
        self.current_view = None
        self.image_cache = {}
        self.view_cache = {}
        t6 = time.time()
        print(f"Basic state: {t6-t5:.3f}s")
        
        self.setup_ui()
        t7 = time.time()
        print(f"setup_ui: {t7-t6:.3f}s")

if __name__ == '__main__':
    Profiler()
