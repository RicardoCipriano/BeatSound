import os
import threading
from pathlib import Path
from typing import Optional, Callable
import yt_dlp
import asyncio
try:
    from shazamio import Shazam
    SHAZAM_AVAILABLE = True
except ImportError:
    SHAZAM_AVAILABLE = False
    class Shazam: pass # Placeholder
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, TCON, TDRC

class MusicDownloader:
    def __init__(self, download_path: str = "downloads"):
        # Garante que o caminho não tenha espaços extras nas pontas
        self.download_path = Path(download_path.strip())
        self.download_path.mkdir(exist_ok=True, parents=True)
        self.shazam = Shazam()
        self.progress_callback: Optional[Callable] = None
        
    def set_progress_callback(self, callback: Callable):
        """Callback para atualizar barra de progresso na UI"""
        self.progress_callback = callback
    
    def download_from_youtube(self, url: str, metadata: dict = None) -> Optional[str]:
        """
        Baixa áudio do YouTube usando yt-dlp
        
        Args:
            url: URL do YouTube
            metadata: Dicionário com title, artist, album (opcional)
        
        Returns:
            Caminho do arquivo baixado ou None se falhar
        """
        
        # Gera um nome de arquivo seguro: Artista - Título ou o Titulo do Youtube
        safe_filename = "%(title)s"
        if metadata and metadata.get('artist') and metadata.get('title'):
            # Remove caracteres proibidos no Windows para o nome do arquivo
            raw_name = f"{metadata['artist']} - {metadata['title']}"
            safe_filename = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_', '.')]).strip()

        # Configuração do yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'restrictfilenames': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': str(self.download_path / f"{safe_filename}.%(ext)s"),
            'progress_hooks': [self._progress_hook],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_color': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        # Removido cookiesfrombrowser por instabilidade no Python 3.13 / Windows
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Caso seja uma Playlist
                if 'entries' in info:
                    files_processed = []
                    for entry in info['entries']:
                        if not entry: continue
                        
                        try:
                            # O yt-dlp pode mudar o nome do arquivo após o processamento (ex: .mp3)
                            base_filename = ydl.prepare_filename(entry)
                            filename = os.path.splitext(base_filename)[0] + ".mp3"
                            
                            # Se o arquivo não existir com .mp3, tenta o original (caso não tenha convertido)
                            if not os.path.exists(filename) and os.path.exists(base_filename):
                                filename = base_filename

                            # Adiciona metadados se o arquivo existir
                            if os.path.exists(filename):
                                # Para playlists, usamos os metadados extraídos de cada item (entry)
                                self._add_metadata(filename, {}, entry)
                                files_processed.append(filename.replace("\\", "/"))
                        except Exception as e:
                            print(f"Erro ao processar item da playlist: {e}")
                            continue
                    
                    return files_processed[0] if files_processed else None

                # Caso seja vídeo único
                else:
                    base_filename = ydl.prepare_filename(info)
                    filename = os.path.splitext(base_filename)[0] + ".mp3"
                    
                    if not os.path.exists(filename) and os.path.exists(base_filename):
                        filename = base_filename

                    if os.path.exists(filename):
                        self._add_metadata(filename, metadata or {}, info)
                    
                    return filename.replace("\\", "/")
                
        except Exception as e:
            error_msg = str(e).lower()
            print(f"Erro ao baixar do YouTube: {e}")
            
            # SE FALHAR POR BOT/FORMATO E TIVERMOS METADADOS, TENTA SOUNDCLOUD AUTOMATICAMENTE
            if metadata and ("sign in" in error_msg or "bot" in error_msg or "format" in error_msg):
                print(f"[*] YouTube falhou. Tentando baixar '{metadata.get('title')}' via SoundCloud como plano B...")
                search_query = f"{metadata.get('artist', '')} {metadata.get('title', '')}"
                sc_url = self._search_youtube_fallback_only_sc(search_query)
                if sc_url:
                    return self.download_from_youtube(sc_url, metadata) # Recursivo para o novo link
            
            return None

    def _search_youtube_fallback_only_sc(self, query: str) -> Optional[str]:
        """Busca apenas no SoundCloud para casos de falha do YouTube"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'nocheckcertificate': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"scsearch1:{query}", download=False)
                if 'entries' in info and info['entries']:
                    return info['entries'][0]['url']
        except: pass
        return None
    
    def _progress_hook(self, d):
        """Hook de progresso para o yt-dlp"""
        if self.progress_callback and d['status'] == 'downloading':
            try:
                if 'total_bytes' in d and d['total_bytes'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    self.progress_callback(percent)
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                    self.progress_callback(percent)
            except:
                pass
    
    def _add_metadata(self, filepath: str, metadata: dict, youtube_info: dict):
        """Adiciona tags ID3 ao arquivo com fallback inteligente para evitar nomes de uploaders ruins"""
        try:
            audio = MP3(filepath, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            
            # --- 1. TÍTULO ---
            # Prioridade: 1. API Oficial | 2. Info do YouTube | 3. Metadados passados
            title = metadata.get('title') or youtube_info.get('track') or youtube_info.get('title')
            
            # --- 2. ARTISTA (Aqui está o segredo para evitar "DJSoul832") ---
            # Prioridade: 1. API Oficial | 2. Info do YouTube (Musician field) | 3. Nome passado na busca
            artist = metadata.get('artist') or youtube_info.get('artist')
            
            # Se ainda não tiver artista ou se o artista for igual ao uploader (muitas vezes lixo)
            uploader = youtube_info.get('uploader', '')
            if not artist or artist.lower() == uploader.lower():
                # Tenta pegar da nossa metadata de busca original
                artist = metadata.get('artist')
                
            # Fallback final: se ainda assim o artista parecer um nome de canal (tem DJ, Vevo, Canal, etc)
            if not artist or any(x in artist.lower() for x in ['channel', 'vevo', 'topic', 'official', 'dj']):
                # Se o título do vídeo tem " - ", o primeiro pedaço geralmente é o artista real
                if ' - ' in youtube_info.get('title', ''):
                    artist = youtube_info['title'].split(' - ')[0].strip()

            # Grava as tags
            if title: audio.tags.add(TIT2(encoding=3, text=title))
            if artist: audio.tags.add(TPE1(encoding=3, text=artist))
            
            # 3. Álbum
            album = metadata.get('album')
            if album: audio.tags.add(TALB(encoding=3, text=album))
            
            # 4. Gênero
            genre = metadata.get('genre')
            if genre: audio.tags.add(TCON(encoding=3, text=genre))

            # 5. Ano
            year = metadata.get('year') or (youtube_info.get('upload_date')[:4] if youtube_info.get('upload_date') else None)
            if year: audio.tags.add(TDRC(encoding=3, text=str(year)))

            # 6. Capa
            thumbnails = youtube_info.get('thumbnails', [])
            cover_url = metadata.get('cover_url')
            
            if not cover_url:
                if thumbnails:
                    # Ordena por resolução (largura x altura) e pega a maior
                    best_thumb = sorted(thumbnails, key=lambda x: (x.get('width', 0) or 0) * (x.get('height', 0) or 0), reverse=True)[0]
                    cover_url = best_thumb.get('url')
                else:
                    cover_url = youtube_info.get('thumbnail')
            
            # Otimização para SoundCloud: Pegar a capa original em alta resolução
            if cover_url and 'sndcdn.com' in cover_url:
                # SoundCloud thumbnails geralmente terminam em -large.jpg ou -t500x500.jpg
                original_url = cover_url.replace('-large', '-original').replace('-t500x500', '-original')
                try:
                    # Verifica rapidamente se a versão original existe
                    if requests.head(original_url, timeout=2).status_code == 200:
                        cover_url = original_url
                    else:
                        cover_url = cover_url.replace('-large', '-t500x500')
                except:
                    cover_url = cover_url.replace('-large', '-t500x500')

            if cover_url:
                self._add_cover_art(audio, cover_url)
            
            # Salva com v2_version=3 (ID3v2.3) para máxima compatibilidade com Windows Explorer e Players
            audio.save(v2_version=3)
        except Exception as e:
            print(f"Erro ao adicionar metadados: {e}")
    
    def _add_cover_art(self, audio, cover_url: str):
        """Baixa e incorpora capa do álbum com suporte a WebP e detecção de MIME type"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            response = requests.get(cover_url, headers=headers, timeout=10)
            if response.status_code == 200:
                img_data = response.content
                mime_type = 'image/jpeg'
                
                # Suporte a WebP: Converter para JPEG (yt-dlp e SoundCloud usam muito webp hoje)
                try:
                    from PIL import Image
                    from io import BytesIO
                    img = Image.open(BytesIO(img_data))
                    
                    if img.format == 'WEBP' or img.mode == 'RGBA':
                        # Converte para RGB (JPEG não aceita transparência)
                        img = img.convert('RGB')
                        output = BytesIO()
                        img.save(output, format='JPEG', quality=95)
                        img_data = output.getvalue()
                        mime_type = 'image/jpeg'
                    elif img.format == 'PNG':
                        mime_type = 'image/png'
                except Exception as e:
                    print(f"[*] Aviso na conversão de imagem: {e}")

                audio.tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=img_data
                ))
        except Exception as e:
            print(f"Erro ao adicionar capa: {e}")
    
    async def recognize_song(self, audio_file_path: str) -> Optional[dict]:
        """
        Reconhece uma música usando ShazamIO
        """
        try:
            result = await self.shazam.recognize_song(audio_file_path)
            
            if 'track' in result:
                track = result['track']
                return {
                    'title': track.get('title', ''),
                    'artist': track.get('subtitle', ''),
                    'album': track.get('sections', [{}])[0].get('metadata', [{}])[0].get('text', '') if 'sections' in track else '',
                    'cover_url': track.get('images', {}).get('coverart', ''),
                    'year': track.get('sections', [{}])[0].get('metadata', [{}])[2].get('text', '') if len(track.get('sections', [{}])[0].get('metadata', [])) > 2 else None
                }
            return None
            
        except Exception as e:
            print(f"Erro no reconhecimento: {e}")
            return None
    
    def recognize_and_download(self, audio_path: str) -> Optional[str]:
        """
        Reconhece música pelo áudio e baixa do YouTube
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            track_info = loop.run_until_complete(self.recognize_song(audio_path))
            loop.close()
            
            if track_info and track_info.get('title'):
                query = f"{track_info['title']} {track_info['artist']}"
                youtube_url = self._search_youtube(query)
                if youtube_url:
                    return self.download_from_youtube(youtube_url, track_info)
        except Exception as e:
            print(f"Erro recognize_and_download: {e}")
        
        return None
    
    def _search_youtube(self, query: str) -> Optional[str]:
        """Busca URL no YouTube com fallback para SoundCloud"""
        # TENTATIVA 1: YouTube
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if 'entries' in info and info['entries']:
                    url = info['entries'][0]['url']
                    # Verifica se é uma URL de música (não playlist)
                    if 'youtube.com' in url or 'youtu.be' in url:
                        print(f"[*] Sugestão YouTube encontrada.")
                        return url
        except Exception as e:
            error_msg = str(e).lower()
            if "sign in" in error_msg or "bot" in error_msg or "confirm your age" in error_msg:
                print(f"[*] YouTube bloqueou a busca por segurança. Tentando SoundCloud...")
            else:
                print(f"[*] Erro na busca YouTube: {e}. Tentando SoundCloud...")
            
        # TENTATIVA 2: Fallback para SoundCloud (Plano B)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Removido cookiesfrombrowser por instabilidade no Python 3.13
                info = ydl.extract_info(f"scsearch1:{query}", download=False)
                if 'entries' in info and info['entries']:
                    print("[✓] Música encontrada no SoundCloud!")
                    return info['entries'][0]['url']
        except Exception as e:
            print(f"[*] SoundCloud também falhou: {e}")
            
        return None

    def get_metadata_from_external_url(self, url: str) -> Optional[dict]:
        """
        Extrai metadados de links do Spotify, Deezer ou Tidal para download via YouTube
        """
        import re
        import html
        url = url.strip()
        
        # 0. Limpeza e extração de URL de iframes/embeds
        if not url.startswith('http'):
            url_match = re.search(r'src="(https?://.*?)"', url)
            if url_match:
                url = url_match.group(1)
            else:
                return None

        # Converte links de embed para links normais para facilitar o scraping
        url = url.replace('embed.tidal.com', 'tidal.com').replace('open.spotify.com/embed', 'open.spotify.com')
        # Remove parâmetros de query extras
        url = url.split('?')[0]

        try:
            # User-Agent de Bot costuma receber o HTML com Meta Tags sem ser redirecionado para Login
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
            
            # 1. DEEZER (Tratamento de links curtos e API)
            if 'deezer.page.link' in url or 'deezer.com' in url:
                # Se for link curto, resolve o redirecionamento
                if 'deezer.page.link' in url:
                    r = requests.get(url, allow_redirects=True, timeout=5)
                    url = r.url
                
                match = re.search(r'track/(\d+)', url)
                if match:
                    track_id = match.group(1)
                    api_url = f"https://api.deezer.com/track/{track_id}"
                    resp = requests.get(api_url, timeout=5).json()
                    if 'title' in resp:
                        return {
                            'title': html.unescape(resp.get('title')),
                            'artist': html.unescape(resp.get('artist', {}).get('name')),
                            'album': html.unescape(resp.get('album', {}).get('title')),
                            'cover_url': resp.get('album', {}).get('cover_xl'),
                            'year': resp.get('release_date', '')[:4]
                        }

            # 2. SPOTIFY / TIDAL (Scraping de Meta Tags)
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                html_content = resp.text
                
                # Tenta pegar via OpenGraph (mais confiável)
                og_title = re.search(r'<meta property="og:title" content="(.*?)"', html_content)
                og_image = re.search(r'<meta property="og:image" content="(.*?)"', html_content)
                
                if og_title:
                    title = html.unescape(og_title.group(1))
                    artist = "Unknown Artist"
                    
                    if 'spotify.com' in url:
                        # Spotify format: "Song Title · Artist · Album"
                        if " · " in title:
                            parts = title.split(" · ")
                            title = parts[0]
                            artist = parts[1]
                        elif " - song by " in title:
                            parts = title.split(" - song by ")
                            title = parts[0]
                            artist = parts[1]
                    elif 'tidal.com' in url:
                        # Tidal format: "Song Title by Artist on TIDAL" ou "Artist - Song Title"
                        if " by " in title:
                            parts = title.split(" by ")
                            title = parts[0]
                            artist = parts[1].replace(" on TIDAL", "").split(" on ")[0]
                        elif " - " in title:
                            parts = title.split(" - ")
                            if len(parts) >= 2:
                                artist = parts[0]
                                title = parts[1]
                            
                    return {
                        'title': title.strip(),
                        'artist': artist.strip(),
                        'cover_url': og_image.group(1) if og_image else None
                    }

        except Exception as e:
            print(f"[*] Erro ao extrair metadados da URL externa: {e}")
        
        return None
