@echo off
echo ========================================
echo Build do BeatSoundSearch-Dj77-V7 (MODO ONEDIR)
echo ========================================
echo.

echo Limpando builds anteriores...
rmdir /s /q build dist 2>nul
del *.spec 2>nul

echo.
echo Iniciando build...
echo.

pyinstaller --clean --noconfirm --onedir --windowed --name BeatSoundSearch-Dj77-V7 --hidden-import tkinter --hidden-import customtkinter --hidden-import darkdetect --hidden-import PIL --hidden-import mutagen --hidden-import pygame --hidden-import yt_dlp --add-data "C:/Users/Ricardo/AppData/Local/Programs/Python/Python313/Lib/tkinter;tkinter" --add-data "C:/Users/Ricardo/AppData/Local/Programs/Python/Python313/tcl/tcl8.6;tcl" --add-data "C:/Users/Ricardo/AppData/Local/Programs/Python/Python313/tcl/tk8.6;tk" --add-data "assets;assets" --add-data "logo.png;." --add-data "logoInicial.png;." --add-data "beatsound.ico;." --add-data "music.db;." main.py

echo.
echo ========================================
echo Build concluida!
echo Executavel em: dist\BeatSoundSearch-Dj77-V7\BeatSoundSearch-Dj77-V7.exe
echo ========================================
pause