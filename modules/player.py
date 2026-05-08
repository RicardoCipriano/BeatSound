import pygame
import threading
import time
from mutagen import File

class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_file = None
        self.playing = False
        self.paused = False
        self.volume = 0.7
        pygame.mixer.music.set_volume(self.volume)
        self.position = 0
        self.duration = 0
        self.callbacks = []
        self.playlist = []
        self.current_index = -1
        self.shuffle = False
        self.repeat_mode = 0  # 0: Off, 1: Repeat One, 2: Repeat All
        self._tracking_thread = None
        
    def get_duration(self, filepath=None):
        fp = filepath or self.current_file
        if not fp: return self.duration
        try:
            audio = File(fp)
            if audio is not None and audio.info is not None:
                return audio.info.length
        except Exception:
            pass
        return 0
        
    def load(self, filepath):
        import os
        if not os.path.exists(filepath):
            normalized = os.path.normpath(filepath)
            if os.path.exists(normalized):
                filepath = normalized
            else:
                filename = os.path.basename(filepath)
                possible_path = os.path.join(os.path.expanduser("~"), "Music", filename)
                if os.path.exists(possible_path):
                    filepath = possible_path
                else:
                    raise Exception(f"Arquivo não encontrado: {filepath}")
        
        self.current_file = filepath
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(filepath)
            self.duration = self.get_duration(filepath)
            self.position = 0
            self.start_time = 0 
            print(f"[Player] Carregado: {filepath}")
        except Exception as e:
            raise Exception(f"Erro ao carregar áudio: {e}")
        
    def play(self, start_pos=None):
        if self.current_file:
            if start_pos is not None:
                pygame.mixer.music.play(start=start_pos)
                self.start_time = start_pos
            elif self.paused:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.play()
                self.start_time = 0
                
            self.playing = True
            self.paused = False
            
    def stop(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload() # Libera o arquivo para escrita
        self.playing = False
        self.paused = False
        self.current_file = None

    def pause(self):
        if self.playing and not self.paused:
            pygame.mixer.music.pause()
            self.paused = True
            
    def set_position(self, seconds):
        if self.current_file:
            self.play(start_pos=seconds)
            
    def get_position(self):
        if not self.playing: return 0
        # pygame get_pos returns ms since play() started
        return self.start_time + (pygame.mixer.music.get_pos() / 1000.0)

    def set_volume(self, value):
        self.volume = value
        pygame.mixer.music.set_volume(value)
            
    def next(self):
        if self.playlist and self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.load(self.playlist[self.current_index])
            self.play()
            
    def prev(self):
        if self.playlist and self.current_index > 0:
            self.current_index -= 1
            self.load(self.playlist[self.current_index])
            self.play()
