import customtkinter as ctk
import os
from PIL import Image
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TCON
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
import mutagen
from tkinter import filedialog, messagebox
import requests
import hashlib
import time
import traceback
from io import BytesIO
from .multi_api_enhancer import MultiAPIEnhancer
from .metadata_utils import MetadataCleaner

class TagEditor(ctk.CTkFrame):
    def __init__(self, parent, controller, track=None):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        self.track = track
        self.entries = {}
        self.api_enhancer = MultiAPIEnhancer()
        self.temp_cover_img = None
        self.temp_cover_data = None

        
        self.content_frame = ctk.CTkFrame(self, fg_color="#181818", corner_radius=12)
        self.content_frame.pack(fill="both", expand=True, padx=80, pady=40)
        
        # Header Modulo
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(20, 10))
        ctk.CTkLabel(header, text="Editor de Tags Avançado", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
        
        self.body = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=30, pady=10)
        
        # UI Structure
        self.setup_ui()
        
        if self.track:
            self.load_track_data(self.track)
        elif self.controller.current_song:
            self.load_track_data(self.controller.current_song)
            
    def setup_ui(self):
        # Column container
        cols = ctk.CTkFrame(self.body, fg_color="transparent")
        cols.pack(fill="both", expand=True)
        
        # Left: Cover
        self.left_col = ctk.CTkFrame(cols, width=300, fg_color="transparent")
        self.left_col.pack(side="left", fill="y", padx=20)
        
        self.cover_label = ctk.CTkLabel(self.left_col, text="🎵", font=("Segoe UI", 120), 
                                      width=250, height=250, fg_color="#121212", corner_radius=12)
        self.cover_label.pack(pady=10)
        
        self.lbl_filename = ctk.CTkLabel(self.left_col, text="Nenhum arquivo selecionado", 
                                        font=("Segoe UI", 11), text_color="#777", wraplength=250)
        self.lbl_filename.pack(pady=5)
        
        ctk.CTkButton(self.left_col, text="Alterar Capa", fg_color="black", 
                      border_width=1, border_color="#c3000d", text_color="white",
                      hover_color="#1a1a1a", font=("Segoe UI", 12, "bold"),
                      command=self.change_artwork).pack(pady=10, fill="x")

        # Info Técnica
        self.info_frame = ctk.CTkFrame(self.left_col, fg_color="#1a1a1a", corner_radius=8)
        self.info_frame.pack(fill="x", pady=10)
        self.lbl_bitrate = ctk.CTkLabel(self.info_frame, text="Bitrate: --- kbps", font=("Segoe UI", 11), text_color="#aaa")
        self.lbl_bitrate.pack(pady=2)
        self.lbl_format = ctk.CTkLabel(self.info_frame, text="Qualidade: ---", font=("Segoe UI", 11, "bold"), text_color="#777")
        self.lbl_format.pack(pady=2)
        
        # Right: Form
        self.right_col = ctk.CTkFrame(cols, fg_color="transparent")
        self.right_col.pack(side="left", fill="both", expand=True, padx=10)
        
        fields = [
            ("title", "Título"),
            ("artist", "Artista"),
            ("album", "Álbum"),
            ("year", "Ano"),
            ("genre", "Gênero"),
            ("tracknumber", "Nº da Faixa"),
        ]
        
        for key, lbl in fields:
            f = ctk.CTkFrame(self.right_col, fg_color="transparent")
            f.pack(fill="x", pady=8)
            ctk.CTkLabel(f, text=lbl, width=100, anchor="w", text_color="#b3b3b3").pack(side="left")
            entry = ctk.CTkEntry(f, placeholder_text=f"Digite o {lbl}...", fg_color="#2b2b2b", 
                                border_width=0, height=35)
            entry.pack(side="left", fill="x", expand=True)
            self.entries[key] = entry

        # Footer Actions
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", padx=30, pady=20)
        
        ctk.CTkButton(footer, text="Descartar", fg_color="black", border_width=1, border_color="#555",
                      text_color="white", hover_color="#1a1a1a", width=120, 
                      command=lambda: self.controller.navigate_to("home")).pack(side="left")
        
        self.btn_save = ctk.CTkButton(footer, text="Salvar Alterações", fg_color="black", 
                                     border_width=1, border_color="#c3000d", text_color="white",
                                     hover_color="#1a1a1a", width=180, font=("Segoe UI", 14, "bold"),
                                     command=self.save_tags)
        self.btn_save.pack(side="right", padx=10)
        
        self.check_rename = ctk.CTkCheckBox(footer, text="Renomear Arquivo Autom.", font=("Segoe UI", 11),
                                           fg_color="#c3000d", border_color="#555")
        self.check_rename.pack(side="right", padx=20)
        self.check_rename.select() # Marcado por padrão
        
        ctk.CTkButton(footer, text="Auto-Preencher (API)", fg_color="black", border_width=1, 
                     border_color="#c3000d", text_color="white", hover_color="#1a1a1a",
                     command=self.fetch_api_data).pack(side="right")

    def smart_clean_metadata(self, title, artist, filename=""):
        """Chama o utilitário centralizado de limpeza"""
        return MetadataCleaner.smart_clean(title, artist, filename)

    def load_track_data(self, track):
        self.track = track
        filename = os.path.basename(track['file_path'])
        self.lbl_filename.configure(text=filename)
        
        # Pegar dados brutos
        raw_title = str(track.get('title') or '')
        raw_artist = str(track.get('artist') or '')
        
        # --- APLICA LIMPEZA INTELIGENTE ---
        title, artist = self.smart_clean_metadata(raw_title, raw_artist, filename)
        # ----------------------------------
        
        # Set UI fields
        self.entries['title'].delete(0, 'end')
        self.entries['title'].insert(0, title)
        self.entries['artist'].delete(0, 'end')
        self.entries['artist'].insert(0, artist)
        
        self.entries['album'].delete(0, 'end')
        self.entries['album'].insert(0, str(track.get('album') or ''))
        self.entries['year'].delete(0, 'end')
        self.entries['year'].insert(0, str(track.get('year') or ''))
        self.entries['genre'].delete(0, 'end')
        self.entries['genre'].insert(0, str(track.get('genre') or ''))
        
        # Load cover if exists
        c_path = track.get('cover_path')
        if c_path and os.path.exists(c_path):
            try:
                img = Image.open(c_path)
                ctk_img = ctk.CTkImage(img, size=(250, 250))
                self.cover_label.configure(image=ctk_img, text="")
            except:
                self.cover_label.configure(image=None, text="🎵")

        # Info Técnica
        try:
            audio = mutagen.File(track['file_path'])
            if audio and hasattr(audio, 'info'):
                br = int(audio.info.bitrate / 1000)
                self.lbl_bitrate.configure(text=f"Bitrate: {br} kbps")
                q = "Excelente" if br >= 320 else "Boa" if br >= 192 else "Regular"
                self.lbl_format.configure(text=f"Qualidade: {q}", text_color="#4CAF50" if br >= 192 else "#FFC107")
        except: pass

    def change_artwork(self):
        file_path = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg *.png *.jpeg")])
        if file_path:
            img = Image.open(file_path)
            ctk_img = ctk.CTkImage(img, size=(250, 250))
            self.cover_label.configure(image=ctk_img, text="")
            self.new_cover_path = file_path

    def save_tags(self):
        if not self.track: return
        
        path = self.track['file_path']
        if not os.path.exists(path):
            messagebox.showerror("Erro", "Arquivo não encontrado no disco.")
            return
            
        # AUTO-STOP: Evitar erro de permissão se a música estiver tocando
        if self.controller.player.current_file and os.path.abspath(self.controller.player.current_file) == os.path.abspath(path):
            self.controller.player.stop()

        try:
            # 1. Update Physical File
            audio = mutagen.File(path)
            if audio is None:
                messagebox.showerror("Erro", "Formato de áudio não suportado ou arquivo corrompido.")
                return

            new_title = self.entries['title'].get()
            new_artist = self.entries['artist'].get()
            new_album = self.entries['album'].get()
            new_year = self.entries['year'].get()
            new_genre = self.entries['genre'].get()

            # 1. Carregar dados da capa (Prioridade para manual, depois API)
            final_cover_data = None
            if hasattr(self, 'new_cover_path') and self.new_cover_path:
                with open(self.new_cover_path, "rb") as f:
                    final_cover_data = f.read()
            elif hasattr(self, 'temp_cover_data') and self.temp_cover_data:
                final_cover_data = self.temp_cover_data

            # 2. Handle MP3 (ID3)
            if isinstance(audio, MP3) or path.lower().endswith(".mp3"):
                try:
                    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, APIC
                    try:
                        tags = ID3(path)
                    except:
                        audio = MP3(path)
                        if audio.tags is None: audio.add_tags()
                        tags = ID3(path)
                    
                    tags["TIT2"] = TIT2(encoding=3, text=new_title)
                    tags["TPE1"] = TPE1(encoding=3, text=new_artist)
                    tags["TALB"] = TALB(encoding=3, text=new_album)
                    tags["TDRC"] = TDRC(encoding=3, text=new_year)
                    tags["TCON"] = TCON(encoding=3, text=new_genre)
                    
                    if final_cover_data:
                        tags.delall("APIC") # Limpa tudo antes
                        tags.add(APIC(
                            encoding=3, mime='image/jpeg', type=3, 
                            desc=u'', data=final_cover_data
                        ))
                    
                    tags.save(path, v2_version=3)
                    # Forçar atualização da miniatura no Windows Explorer
                    os.utime(path, None)
                    print(f"[Editor] MP3 Tags e Capa persistidas em: {path}")
                except Exception as id3_err:
                    print(f"Error saving ID3: {id3_err}")
                    raise id3_err
            
            # Handle FLAC
            elif isinstance(audio, FLAC):
                audio['title'] = new_title
                audio['artist'] = new_artist
                audio['album'] = new_album
                audio['date'] = new_year
                audio['genre'] = new_genre
                
                if final_cover_data:
                    audio.clear_pictures() # Remove anteriores
                    pic = Picture()
                    pic.data = final_cover_data
                    pic.type = 3
                    pic.mime = u"image/jpeg"
                    audio.add_picture(pic)
                audio.save()

            # Handle Vorbis (Explícito para Opus/OGG)
            else:
                audio['title'] = [new_title]
                audio['artist'] = [new_artist]
                audio['album'] = [new_album]
                audio['date'] = [new_year]
                audio['genre'] = [new_genre]
                audio.save()

            # 2. Update Database Cache and Local Cover Cache
            db_data = {
                'title': new_title,
                'artist': new_artist,
                'album': new_album,
                'year': new_year,
                'genre': new_genre,
                'cover_path': self.track.get('cover_path') # Default
            }
            
            # Info Técnica
            try:
                temp_audio = mutagen.File(path)
                if hasattr(temp_audio, 'info'):
                    db_data['bitrate'] = int(temp_audio.info.bitrate / 1000)
                    db_data['ext'] = os.path.splitext(path)[1][1:].upper()
            except: pass

            # Se houve mudança de capa, salva em assets/covers para cache de UI
            if final_cover_data:
                covers_dir = os.path.join(self.controller.db.root_dir, "assets", "covers")
                os.makedirs(covers_dir, exist_ok=True)
                safe_name = hashlib.md5(path.encode()).hexdigest() + ".jpg"
                save_path = os.path.join(covers_dir, safe_name).replace("\\", "/")
                with open(save_path, "wb") as f:
                    f.write(final_cover_data)
                db_data['cover_path'] = save_path

            # 3. RENOMEAÇÃO FÍSICA (Opcional)
            # 3. RENOMEAÇÃO FÍSICA NO WINDOWS (Opcional)
            if self.check_rename.get():
                try:
                    ext = os.path.splitext(path)[1]
                    # Sanitização para Windows
                    def clean(t): return "".join([c for c in t if c not in r'\/:*?#|"<>']).strip()
                    new_filename = f"{clean(new_artist)} - {clean(new_title)}{ext}"
                    new_path = os.path.join(os.path.dirname(path), new_filename).replace("\\", "/")
                    
                    if os.path.abspath(path).lower() != os.path.abspath(new_path).lower():
                        if os.path.exists(new_path):
                            new_path = os.path.join(os.path.dirname(path), f"{clean(new_artist)} - {clean(new_title)}_{int(time.time())}{ext}").replace("\\", "/")
                        
                        os.rename(path, new_path)
                        print(f"[Editor] Arquivo renomeado no disco: {new_path}")
                        
                        # ATENÇÃO: A tabela correta é 'metadata_cache'
                        old_p = path.lower().replace("\\", "/")
                        new_p = new_path.lower().replace("\\", "/")
                        self.controller.db.execute("UPDATE metadata_cache SET file_path = ? WHERE LOWER(file_path) = ?", (new_p, old_p))
                        path = new_path # Atualiza para o update_song_metadata() final
                except Exception as ren_err:
                    print(f"Erro ao renomear: {ren_err}")

            self.controller.db.update_song_metadata(path, db_data)
            
            messagebox.showinfo("Sucesso", f"Música atualizada!\nCaminho: {os.path.basename(path)}")
            self.controller.notify_data_changed()
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar as tags: {e}")

    def fetch_api_data(self):
        artist = self.entries['artist'].get()
        title = self.entries['title'].get()
        
        if not artist or not title:
            messagebox.showwarning("Aviso", "Preencha Título e Artista para buscar dados.")
            return
            
        # Feedback visual
        self.btn_save.configure(state="disabled")
        
        try:
            # Mostrar que está processando
            self.lbl_filename.configure(text="Buscando metadados online...")
            
            # Buscar informações
            info = self.api_enhancer.get_track_complete_info(artist, title)
            
            if info:
                # Atualizar campos se eles estiverem vazios ou se os novos forem melhores
                if info.get('album'):
                    self.entries['album'].delete(0, 'end')
                    self.entries['album'].insert(0, info['album'])
                
                if info.get('year'):
                    self.entries['year'].delete(0, 'end')
                    self.entries['year'].insert(0, str(info['year']))
                
                if info.get('genre'):
                    gen = info['genre'].title()
                    self.entries['genre'].delete(0, 'end')
                    self.entries['genre'].insert(0, gen)

                # Sugestão: Limpar o título e artista se vierem nomes melhores/profissionais
                if info.get('title') and info['title'].lower() != title.lower():
                    self.entries['title'].delete(0, 'end')
                    self.entries['title'].insert(0, info['title'])
                if info.get('artist') and info['artist'].lower() != artist.lower():
                    self.entries['artist'].delete(0, 'end')
                    self.entries['artist'].insert(0, info['artist'])
                
                if info.get('track_number'):
                    val = str(info['track_number'])
                    self.entries['tracknumber'].delete(0, 'end')
                    self.entries['tracknumber'].insert(0, val)


                # Baixar e mostrar capa se disponível
                if info.get('cover_url'):
                    resp = requests.get(info['cover_url'], timeout=10)
                    if resp.status_code == 200:
                        img_data = BytesIO(resp.content)
                        img = Image.open(img_data)
                        ctk_img = ctk.CTkImage(img, size=(250, 250))
                        self.cover_label.configure(image=ctk_img, text="")
                        
                        # Salvar temporariamente para o save_tags usar depois se quiser
                        # Por enquanto apenas mostra a prévia. 
                        # O usuário precisa salvar para persistir no arquivo/banco.
                        self.temp_cover_data = resp.content
                
                messagebox.showinfo("Sucesso", "Dados recuperados com sucesso!")
            else:
                messagebox.showinfo("API", "Nenhuma informação extra encontrada.")
                
        except Exception as e:
            messagebox.showerror("Erro API", f"Falha ao buscar dados: {e}")
        finally:
            self.lbl_filename.configure(text=os.path.basename(self.track['file_path']))
            self.btn_save.configure(state="normal")

