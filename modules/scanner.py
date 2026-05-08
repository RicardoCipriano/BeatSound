import os
import sqlite3
import logging
import time
from pathlib import Path
from typing import Optional
import mutagen
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TCON
from mutagen.mp3 import MP3
import hashlib
from io import BytesIO
from PIL import Image
import traceback

class LibraryScanner:
    def __init__(self, db):
        self.db = db
        self.supported_extensions = ['.mp3', '.m4a', '.flac', '.wav', '.ogg', '.wma']
        self.is_scanning = False

    def scan(self, directory, progress_callback=None):
        """Escanear diretório recursivamente e salvar metadados no cache com suporte incremental"""
        if self.is_scanning:
            return
        
        self.is_scanning = True
        print(f"[*] Iniciando scan em: {directory}")
        count = 0
        total_skipped = 0
        
        path_dir = Path(directory)
        
        # 1. Recuperar dados existentes para Scan Incremental (Skip rápido)
        print("[*] Recuperando cache para scan incremental...")
        try:
            existing_data = {row['file_path'].lower(): row['file_mtime'] for row in self.db.query("SELECT file_path, file_mtime FROM metadata_cache")}
        except:
            existing_data = {}
        
        # 2. Pre-count files for progress bar
        print("[*] Mapeando arquivos...")
        file_list = []
        for root, dirs, files in os.walk(directory, followlinks=True):
            if any(p in root.lower() for p in ['\\$', '.tmp', 'cache', 'appdata', 'temp']):
                continue
            for file in files:
                if Path(file).suffix.lower() in self.supported_extensions:
                    file_list.append(os.path.join(root, file))
        
        total_files = len(file_list)
        print(f"[*] {total_files} arquivos encontrados.")

        for i, file_path in enumerate(file_list):
            full_path = Path(file_path)
            file = full_path.name
            root = full_path.parent
            ext = full_path.suffix.lower()
            
            db_path = str(full_path).replace("\\", "/").lower()
            
            # SCAN INCREMENTAL: Se o arquivo não mudou, pula a extração pesada
            try:
                current_mtime = int(full_path.stat().st_mtime)
                if db_path in existing_data and existing_data[db_path] == current_mtime:
                    total_skipped += 1
                    if (i + 1) % 50 == 0 and progress_callback:
                        progress_callback(i + 1, total_files, file)
                    continue

                # Extração de Metadados
                audio_info = mutagen.File(str(full_path))
                if audio_info is None:
                    continue
                
                bitrate = 0
                if hasattr(audio_info, 'info') and hasattr(audio_info.info, 'bitrate'):
                    bitrate = int(audio_info.info.bitrate / 1000)

                # Metadados base
                metadata = {
                    'file_path': str(full_path).replace("\\", "/"),
                    'artist': 'Unknown Artist',
                    'title': full_path.stem,
                    'album': 'Unknown Album',
                    'year': None,
                    'genre': None,
                    'duration': int(audio_info.info.length) if hasattr(audio_info, 'info') else 0,
                    'cover_path': None,
                    'file_mtime': current_mtime,
                    'bitrate': bitrate,
                    'ext': ext.replace(".", "").upper()
                }

                # Extração por formato
                if ext == '.mp3':
                    try:
                        tags = ID3(str(full_path))
                        metadata['artist'] = str(tags.get('TPE1').text[0]) if tags.get('TPE1') else metadata['artist']
                        metadata['title'] = str(tags.get('TIT2').text[0]) if tags.get('TIT2') else metadata['title']
                        metadata['album'] = str(tags.get('TALB').text[0]) if tags.get('TALB') else metadata['album']
                        metadata['year'] = str(tags.get('TDRC').text[0]) if tags.get('TDRC') else None
                        metadata['genre'] = str(tags.get('TCON').text[0]) if tags.get('TCON') else None
                        metadata['cover_path'] = self.extract_cover(tags, metadata['artist'], metadata['album'])
                    except: pass
                elif ext == '.m4a':
                    try:
                        metadata['artist'] = str(audio_info.get('\xa9ART', [''])[0]) or metadata['artist']
                        metadata['title'] = str(audio_info.get('\xa9nam', [''])[0]) or metadata['title']
                        metadata['album'] = str(audio_info.get('\xa9alb', [''])[0]) or metadata['album']
                    except: pass
                elif ext in ['.flac', '.ogg']:
                    try:
                        metadata['artist'] = audio_info.get('artist', [''])[0] or metadata['artist']
                        metadata['title'] = audio_info.get('title', [''])[0] or metadata['title']
                        metadata['album'] = audio_info.get('album', [''])[0] or metadata['album']
                        metadata['year'] = audio_info.get('date', [None])[0]
                        metadata['genre'] = audio_info.get('genre', [None])[0]
                    except: pass

                # Fallback gênero
                if not metadata['genre']:
                    metadata['genre'] = Path(root).name

                # Fallback capa
                if not metadata['cover_path']:
                    for img_name in ['cover.jpg', 'folder.jpg', 'album.jpg']:
                        p = Path(root) / img_name
                        if p.exists():
                            metadata['cover_path'] = str(p).replace("\\", "/")
                            break

                metadata = self.clean_metadata(metadata, file)
                self.db.upsert_song(metadata)
                count += 1

                if (i + 1) % 20 == 0 and progress_callback:
                    progress_callback(i + 1, total_files, file)

            except Exception as e:
                logging.error(f"Erro em {file}: {e}")

        # 3. Finalizar e retornar status
        pendQuery = "SELECT COUNT(*) as Q FROM metadata_cache WHERE LOWER(artist) LIKE '%unknown%' OR LOWER(title) LIKE '%unknown%'"
        try:
            p_count = self.db.query(pendQuery)[0]['Q']
        except:
            p_count = 0

        self.is_scanning = False
        if progress_callback:
            progress_callback(total_files, total_files, "Finalizado")
            
        return {'processed': count, 'skipped': total_skipped, 'pendencies': p_count}

    def extract_cover(self, tags, artist, album):
        """Extrai capa embutida para pasta assets/covers"""
        try:
            data = None
            if isinstance(tags, ID3):
                for key in tags.keys():
                    if key.startswith('APIC'):
                        data = tags[key].data
                        break
            elif hasattr(tags, 'get') and 'covr' in tags:
                data = tags['covr'][0]
            
            if data:
                covers_dir = os.path.join(self.db.root_dir, "assets", "covers")
                os.makedirs(covers_dir, exist_ok=True)
                
                # Nome único baseado em artista/álbum ou hash
                name_seed = f"{artist}_{album}".encode('utf-8')
                safe_name = hashlib.md5(name_seed).hexdigest() + ".jpg"
                save_path = os.path.join(covers_dir, safe_name).replace("\\", "/")
                
                if not os.path.exists(save_path):
                    with open(save_path, "wb") as f:
                        f.write(data)
                return save_path
        except: pass
        return None

    def clean_metadata(self, metadata, file_name):
        """Usa o MetadataCleaner para aplicar todas as regras de limpeza solicitadas"""
        from modules.metadata_utils import MetadataCleaner
        
        # O smart_clean já cuida de:
        # 1. Separar Artista - Música se estiverem no mesmo campo
        # 2. Remover números (001, 02) com proteção para 2NOISE/50Cent
        # 3. Remover feat/ft
        # 4. Remover extensões, aspas e pontos residuais
        cleaned_title, cleaned_artist = MetadataCleaner.smart_clean(
            metadata['title'], 
            metadata['artist'], 
            file_name
        )
        
        metadata['title'] = cleaned_title
        metadata['artist'] = cleaned_artist
        return metadata

    def prune(self, progress_callback=None):
        """Remove arquivos que não existem mais no disco"""
        return self.db.prune_stale_songs(progress_callback)

    def scan_by_date(self, root_dir, target_date=None):
        """
        Escaneia apenas arquivos criados ou modificados em uma data específica (padrão: hoje).
        Ideal para indexar rapidamente músicas novas movidas manualmente.
        """
        import datetime
        # Se for madrugada (até as 05:00 AM), incluímos também os arquivos de ontem
        # para facilitar a vida de quem está organizando a biblioteca tarde da noite.
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        is_early_morning = datetime.datetime.now().hour < 5
        target_dates = [target_date] if target_date else ([today, yesterday] if is_early_morning else [today])
            
        print(f"[*] Buscando novidades: {', '.join(map(str, target_dates))}")
        
        root = Path(root_dir)
        new_files_count = 0
        updated_files_count = 0
        
        # Percorre a biblioteca (apenas a principal C:\Users\Ricardo\Music geralmente)
        for ext in ['*.mp3', '*.wav', '*.flac', '*.m4a']:
            for file_path in root.rglob(ext):
                try:
                    # Pega a data de modificação e criação
                    mtime = datetime.date.fromtimestamp(os.path.getmtime(file_path))
                    ctime = datetime.date.fromtimestamp(os.path.getctime(file_path))
                    
                    # Se o arquivo foi mexido ou criado em uma das datas alvo
                    if mtime in target_dates or ctime in target_dates:
                        # Verifica se já está no banco
                        current = self.db.find_by_path(str(file_path).replace("\\", "/"))
                        
                        if not current:
                            # Se não está no banco, indexa (lendo apenas as tags locais do arquivo)
                            # Não gasta API aqui porque o downloader já gravou as tags no MP3
                            self.scan_single_file(str(file_path))
                            new_files_count += 1
                except Exception as e:
                    print(f"Erro ao analisar arquivo por data {file_path}: {e}")
                    
        return {
            'new': new_files_count,
            'updated': updated_files_count
        }

    def scan_single_file(self, file_path):
        """Escaneia um único arquivo e adiciona ao banco de dados"""
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"[Scanner] Erro: Arquivo não encontrado: {file_path}")
            return None
            
        ext = full_path.suffix.lower()
        if ext not in self.supported_extensions:
            print(f"[Scanner] Erro: Extensão não suportada ({ext}): {file_path}")
            return None

        try:
            current_mtime = int(full_path.stat().st_mtime)
            audio_info = mutagen.File(str(full_path))
            if audio_info is None:
                print(f"[Scanner] Erro: Mutagen não reconheceu o arquivo: {file_path}")
                return None
            
            bitrate = 0
            if hasattr(audio_info, 'info') and hasattr(audio_info.info, 'bitrate'):
                bitrate = int(audio_info.info.bitrate / 1000)

            metadata = {
                'file_path': str(full_path).replace("\\", "/"),
                'artist': 'Unknown Artist',
                'title': full_path.stem,
                'album': 'Unknown Album',
                'year': None,
                'genre': None,
                'duration': int(audio_info.info.length) if hasattr(audio_info, 'info') else 0,
                'cover_path': None,
                'file_mtime': current_mtime,
                'bitrate': bitrate,
                'ext': ext.replace(".", "").upper()
            }

            if ext == '.mp3':
                try:
                    tags = ID3(str(full_path))
                    metadata['artist'] = str(tags.get('TPE1').text[0]) if tags.get('TPE1') else metadata['artist']
                    metadata['title'] = str(tags.get('TIT2').text[0]) if tags.get('TIT2') else metadata['title']
                    metadata['album'] = str(tags.get('TALB').text[0]) if tags.get('TALB') else metadata['album']
                    metadata['year'] = str(tags.get('TDRC').text[0]) if tags.get('TDRC') else None
                    metadata['genre'] = str(tags.get('TCON').text[0]) if tags.get('TCON') else None
                    metadata['cover_path'] = self.extract_cover(tags, metadata['artist'], metadata['album'])
                except: pass
            
            # Clean and Upsert
            metadata = self.clean_metadata(metadata, full_path.name)
            self.db.upsert_song(metadata)
            return metadata
        except Exception as e:
            print(f"[Scanner] Erro crítico ao escanear {file_path}: {e}")
            logging.error(f"Erro ao escanear arquivo único {file_path}: {e}")
            return None
