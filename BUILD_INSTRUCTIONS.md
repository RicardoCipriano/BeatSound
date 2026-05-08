# Instruções para Build do SearchMusicBeat

## ⚠️ IMPORTANTE: Siga estas instruções EXATAMENTE para gerar o executável

### Configuração do Ambiente
- Python: C:\Users\Ricardo\AppData\Local\Programs\Python\Python313
- Virtual env: C:\projetos\SearchMusicBeat\venv

### Comando CORRETO para build (NUNCA use o comando simples)

```powershell
pyinstaller --clean --noconfirm --onefile --windowed --name BeatSoundSearch-Dj77-V7 --hidden-import tkinter --hidden-import customtkinter --hidden-import darkdetect --hidden-import PIL --hidden-import mutagen --hidden-import pygame --hidden-import yt_dlp --add-data "C:/Users/Ricardo/AppData/Local/Programs/Python/Python313/Lib/tkinter;tkinter" --add-data "C:/Users/Ricardo/AppData/Local/Programs/Python/Python313/tcl/tcl8.6;tcl" --add-data "C:/Users/Ricardo/AppData/Local/Programs/Python/Python313/tcl/tk8.6;tk" --add-data "assets;assets" --add-data "logo.png;." --add-data "beatsound.ico;." --add-data "music.db;." main.py