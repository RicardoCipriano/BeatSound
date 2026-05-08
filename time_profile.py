import time

t0 = time.time()
print("Starting imports...")

import customtkinter as ctk
t1 = time.time()
print(f"customtkinter: {t1 - t0:.3f}s")

import pygame
t2 = time.time()
print(f"pygame: {t2 - t1:.3f}s")

from PIL import Image, ImageTk
t3 = time.time()
print(f"PIL: {t3 - t2:.3f}s")

from CTkMenuBar import *
t4 = time.time()
print(f"CTkMenuBar: {t4 - t3:.3f}s")

from CTkToolTip import *
t5 = time.time()
print(f"CTkToolTip: {t5 - t4:.3f}s")

from modules.database import Database
t6 = time.time()
print(f"Database: {t6 - t5:.3f}s")

from modules.multi_api_enhancer import MultiAPIEnhancer
t7 = time.time()
print(f"MultiAPIEnhancer: {t7 - t6:.3f}s")

from modules.player import MusicPlayer
t8 = time.time()
print(f"MusicPlayer: {t8 - t7:.3f}s")

print(f"Total import time: {t8 - t0:.3f}s")
