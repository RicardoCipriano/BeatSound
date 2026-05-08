import customtkinter as ctk
import os
import threading
import requests
from io import BytesIO
from PIL import Image
from .database import Database
from .multi_api_enhancer import MultiAPIEnhancer
from .metadata_utils import MetadataCleaner
import mutagen
from tkinter import filedialog, messagebox
from config import LASTFM_API_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

class BatchEditor(ctk.CTkFrame):
    def __init__(self, parent, controller, mode="single"):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        self.db = controller.db
        self.api_enhancer = MultiAPIEnhancer()
        self.selected_files = []
        self.folder_path = ""
        self.mode = mode # "single" ou "variable"
        self.is_processing = False
        self._stop_scan = False

        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#181818", height=80, corner_radius=0)
        header.pack(fill="x", side="top")
        
        title_text = "📦 Álbum Único (Lote)" if self.mode == "single" else "🤖 Lote Variável (IA)"
        ctk.CTkLabel(header, text=title_text, 
                      font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left", padx=30, pady=20)

        # Botão Normalizar (No Header para máxima visibilidade)
        self.btn_normalize = ctk.CTkButton(header, text="🧹 Normalizar Biblioteca", 
                                           fg_color="black", border_width=1, border_color="#c3000d",
                                           text_color="white", hover_color="#1a1a1a",
                                           width=180, height=42, font=("Segoe UI", 12, "bold"),
                                           command=self.normalize_library)
        self.btn_normalize.pack(side="right", padx=30, pady=20)
        
        # Main Content
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=30, pady=20)

        # Left: Files List
        self.left_panel = ctk.CTkFrame(self.main_container, fg_color="#181818", width=400, corner_radius=12)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 15))

        self.top_ctrl = ctk.CTkFrame(self.left_panel, fg_color="transparent", height=70)
        self.top_ctrl.pack(fill="x", padx=15, pady=10)
        self.top_ctrl.pack_propagate(False) 
        
        self.btn_select_folder = ctk.CTkButton(self.top_ctrl, text="📁 Selecionar Pasta", 
                                                fg_color="black", border_width=1, border_color="#c3000d",
                                                text_color="white", hover_color="#1a1a1a",
                                                width=160, height=45, font=("Segoe UI", 13, "bold"),
                                                command=self.select_folder)
        self.btn_select_folder.pack(side="left", padx=10, pady=10)

        self.lbl_folder = ctk.CTkLabel(self.top_ctrl, text="Nenhuma pasta selecionada", 
                                        font=("Segoe UI", 12), text_color="#777")
        self.lbl_folder.pack(side="left", padx=15)
        
        # Botão Parar (Lado Direito)
        self.btn_stop_scan = ctk.CTkButton(self.top_ctrl, text="🛑 Parar", fg_color="black", 
                                          border_width=1, border_color="#c3000d", text_color="white",
                                          hover_color="#1a1a1a", width=100, height=45, font=("Segoe UI", 12, "bold"),
                                          command=self.stop_variable_scan)
        self.btn_stop_scan.pack(side="right", padx=10, pady=10)
        self.btn_stop_scan.configure(state="disabled")

        self.files_list = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.files_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Right Panel
        self.right_panel = ctk.CTkFrame(self.main_container, fg_color="#181818", width=350, corner_radius=12)
        self.right_panel.pack(side="right", fill="both", padx=(15, 0))
        
        if self.mode == "single":
            self.setup_single_mode_ui()
        else:
            self.setup_variable_mode_ui()

    def create_api_status_row(self, parent):
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(pady=(2, 10), padx=30, fill="x")
        
        apis = [
            ("Spotify", bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)),
            ("Deezer", True), # Deezer API Pública
            ("Last.fm", bool(LASTFM_API_KEY))
        ]
        
        for name, active in apis:
            color = "#1DB954" if active else "#ff4444"
            status_text = "Ativo" if active else "Inativo"
            lbl = ctk.CTkLabel(status_frame, text=f" ● {name}: {status_text}", 
                              font=("Segoe UI", 10, "bold"), text_color=color)
            lbl.pack(side="left", padx=5)

    def setup_single_mode_ui(self):
        ctk.CTkLabel(self.right_panel, text="Tags do Álbum", font=("Segoe UI", 18, "bold"), 
                      text_color="white").pack(pady=(15, 2))
        
        self.create_api_status_row(self.right_panel)

        self.entries = {}
        fields = [
            ("artist", "Artista"),
            ("album", "Álbum"),
            ("year", "Ano"),
            ("genre", "Gênero"),
        ]

        for key, label in fields:
            lbl = ctk.CTkLabel(self.right_panel, text=label, font=("Segoe UI", 13), text_color="#b3b3b3")
            lbl.pack(anchor="w", padx=30, pady=(5, 0))
            entry = ctk.CTkEntry(self.right_panel, placeholder_text=f"Mesmo {label} para todos...",
                                  width=280, height=35, fg_color="#2b2b2b", border_width=0)
            entry.pack(padx=30, pady=(2, 6))
            self.entries[key] = entry

        # Actions
        self.btn_apply = ctk.CTkButton(self.right_panel, text="Aplicar em Todas", 
                                        height=45, fg_color="black", border_width=1, border_color="#c3000d",
                                        font=("Segoe UI", 14, "bold"), text_color="white",
                                        hover_color="#1a1a1a", command=self.apply_batch)
        self.btn_apply.pack(pady=(15, 10), padx=30, fill="x")
        
        self.btn_auto = ctk.CTkButton(self.right_panel, text="🪄 Identificar Álbum (API)", 
                                       height=35, fg_color="black", border_width=1, border_color="#c3000d",
                                       text_color="white", hover_color="#1a1a1a",
                                       command=self.auto_identify)
        self.btn_auto.pack(pady=5, padx=30, fill="x")

        self.lbl_auto_status = ctk.CTkLabel(self.right_panel, text="", font=("Segoe UI", 11), text_color="#1DB954")
        self.lbl_auto_status.pack(pady=2)

        self.preserve_artist = ctk.CTkCheckBox(self.right_panel, text="Preservar Artistas Originais",
                                              font=("Segoe UI", 12), fg_color="#c3000d", text_color="white")
        self.preserve_artist.pack(pady=5, padx=30, anchor="w")
        
        self.info_tip_frame = ctk.CTkFrame(self.right_panel, fg_color="#1a1a1a", corner_radius=8)
        self.info_tip_frame.pack(pady=20, padx=30, fill="x")

        info_tip = ctk.CTkLabel(self.info_tip_frame, 
                                text="💡 Dica: Se deixar Artista vazio, o app\ntentará extrair 'Artista - Título'\ndo nome do arquivo.", 
                                font=("Segoe UI", 12), text_color="#cccccc", justify="left")
        info_tip.pack(pady=10, padx=15)

    def setup_variable_mode_ui(self):
        ctk.CTkLabel(self.right_panel, text="Scanner IA por Faixa", font=("Segoe UI", 18, "bold"), 
                      text_color="white").pack(pady=(15, 2))
        
        self.create_api_status_row(self.right_panel)
        
        desc = ("Este modo escaneia cada arquivo\nindividualmente usando as APIs.\n"
                "Ideal para pastas mistas com\nvários artistas e estilos.")
        ctk.CTkLabel(self.right_panel, text=desc, font=("Segoe UI", 12), 
                      text_color="#aaaaaa", justify="center").pack(pady=10, padx=20)

        # Progress info
        self.progress_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=30, pady=10)

        self.lbl_status = ctk.CTkLabel(self.progress_frame, text="Aguardando início...", font=("Segoe UI", 12), text_color="#aaa")
        self.lbl_status.pack(pady=2)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, fg_color="#2b2b2b", progress_color="#c3000d")
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)

        self.btn_start_scan = ctk.CTkButton(self.right_panel, text="🤖 Iniciar Escaneamento IA",
                                             height=50, fg_color="black", border_width=1, border_color="#c3000d",
                                             text_color="white", hover_color="#1a1a1a",
                                             font=("Segoe UI", 14, "bold"),
                                             command=self.start_variable_scan)
        self.btn_start_scan.pack(pady=(10, 6), padx=30, fill="x")
        
        self.btn_go_manager = ctk.CTkButton(self.right_panel, text="🔍 Ver Pendências desta Pasta",
                                             height=40, fg_color="black", border_width=1, border_color="#c3000d",
                                             text_color="white", hover_color="#1a1a1a",
                                             font=("Segoe UI", 12, "bold"),
                                             command=lambda: self.controller.navigate_to("manager", self.folder_path))
        
        self.log_box = ctk.CTkTextbox(self.right_panel, height=200, fg_color="#121212", border_width=1, border_color="#333", font=("Consolas", 11))
        self.log_box.pack(padx=20, pady=10, fill="both", expand=True)
        self.log_box.configure(state="disabled")

        ctk.CTkLabel(self.right_panel, 
                     text="ℹ️ Use o botão 'Normalizar' no topo para\npadronizar artistas e scores no banco.",
                     font=("Segoe UI", 10), text_color="#888888").pack(pady=(5, 15))

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path = folder
            self.lbl_folder.configure(text=os.path.basename(folder))
            self.load_files(folder)

    def load_files(self, folder):
        for w in self.files_list.winfo_children():
            w.destroy()
        
        self.selected_files = []
        valid_exts = [".mp3", ".flac", ".m4a", ".ogg", ".wav"]
        
        files = [f for f in os.listdir(folder) if any(f.lower().endswith(e) for e in valid_exts)]
        files.sort()

        if not files:
            ctk.CTkLabel(self.files_list, text="Nenhuma música encontrada nesta pasta.", text_color="#777").pack(pady=20)
            return

        for i, f in enumerate(files):
            full_path = os.path.join(folder, f)
            self.selected_files.append(full_path)
            
            f_row = ctk.CTkFrame(self.files_list, fg_color="#1a1a1a" if i % 2 == 0 else "transparent", corner_radius=6)
            f_row.pack(fill="x", pady=1, padx=2)
            
            icon = "🎵 " if f.lower().endswith((".mp3", ".flac")) else "📄 "
            lbl = ctk.CTkLabel(f_row, text=f"{icon} {f}", font=("Segoe UI", 12), anchor="w", text_color="#ccc")
            lbl.pack(side="left", padx=10, pady=5)
            
            ext = os.path.splitext(f)[1][1:].upper()
            ctk.CTkLabel(f_row, text=ext, font=("Segoe UI", 9, "bold"), text_color="#555", 
                          fg_color="#333", corner_radius=4, width=35).pack(side="right", padx=10)

        # Sugestão pragmática de tags baseada no primeiro arquivo (apenas p/ Single mode)
        if self.mode == "single" and self.selected_files:
            try:
                audio = mutagen.File(self.selected_files[0], easy=True)
                if audio:
                    for k, entry_k in [('artist', 'artist'), ('album', 'album'), ('date', 'year'), ('genre', 'genre')]:
                        if k in audio and audio[k]:
                             self.entries[entry_k].delete(0, 'end')
                             self.entries[entry_k].insert(0, str(audio[k][0]))
            except: pass

    def load_from_songs(self, songs):
        """Carrega uma lista de músicas vinda de outra view (ex: Home/Artistas)"""
        if not songs: return
        
        for w in self.files_list.winfo_children():
            w.destroy()
        
        self.selected_files = []
        self.folder_path = ""
        
        # Se for um único artista, podemos inferir a "pasta" ou pelo menos o nome do artista
        first_artist = songs[0].get('artist', 'Unknown')
        self.lbl_folder.configure(text=f"Artista: {first_artist}")
        
        for i, s in enumerate(songs):
            path = s.get('file_path')
            if not path or not os.path.exists(path): continue
            
            self.selected_files.append(path)
            filename = os.path.basename(path)
            
            f_row = ctk.CTkFrame(self.files_list, fg_color="#1a1a1a" if i % 2 == 0 else "transparent", corner_radius=6)
            f_row.pack(fill="x", pady=1, padx=2)
            
            icon = "🎵 " if filename.lower().endswith((".mp3", ".flac")) else "📄 "
            lbl = ctk.CTkLabel(f_row, text=f"{icon} {filename}", font=("Segoe UI", 12), anchor="w", text_color="#ccc")
            lbl.pack(side="left", padx=10, pady=5)
            
            ext = os.path.splitext(filename)[1][1:].upper()
            ctk.CTkLabel(f_row, text=ext, font=("Segoe UI", 9, "bold"), text_color="#555", 
                          fg_color="#333", corner_radius=4, width=35).pack(side="right", padx=10)

        # Preencher campos se for Single Mode
        if self.mode == "single" and songs:
            try:
                # Usa os dados do primeiro item da lista (já vêm do banco)
                s = songs[0]
                for k in ['artist', 'album', 'year', 'genre']:
                    if s.get(k) and k in self.entries:
                        self.entries[k].delete(0, 'end')
                        self.entries[k].insert(0, str(s[k]))
            except: pass

    def normalize_library(self):
        """PONTO #1 — Normaliza artistas e calcula quality_score em thread separada."""
        if self.is_processing:
            messagebox.showwarning("Aviso", "Aguarde o término do escaneamento atual.")
            return
        if not messagebox.askyesno(
            "Normalizar Biblioteca",
            "Isso irá:\n• Padronizar nomes de artistas (Title Case)\n• Calcular quality_score de todas as 41k músicas\n\nPode levar 30-60 segundos. Continuar?"
        ):
            return

        self.btn_normalize.configure(state="disabled", text="⏳ Normalizando...")
        self.log("🧹 Iniciando normalização da biblioteca...")

        def run():
            try:
                self.db.normalize_artists()
                self.log("✅ Normalização concluída! Nomes padronizados e quality_score calculado.")
                self.after(0, lambda: self.btn_normalize.configure(state="normal", text="🧹 Normalizar Biblioteca"))
                self.after(0, lambda: self.controller.notify_data_changed())
                self.after(0, lambda: messagebox.showinfo("Normalização", "Biblioteca normalizada com sucesso!\n\nArtistas padronizados e scores calculados.\nRecarregue a tela inicial para ver os resultados."))
            except Exception as e:
                self.log(f"❌ Erro na normalização: {e}")
                self.after(0, lambda: self.btn_normalize.configure(state="normal", text="🧹 Normalizar Biblioteca"))

        threading.Thread(target=run, daemon=True).start()

    def start_variable_scan(self):

        if not self.selected_files:
            messagebox.showwarning("Aviso", "Nenhuma música carregada.")
            return

        if self.is_processing:
            return

        if not messagebox.askyesno("Iniciar", f"Deseja escanear {len(self.selected_files)} arquivos individualmente?\nIsso pode levar alguns minutos."):
            return

        self._stop_scan = False
        self.is_processing = True
        self.btn_start_scan.configure(state="disabled")
        # Ativa o botão de parar que já está no topo
        self.btn_stop_scan.configure(state="normal", text="🛑 Parar")
        threading.Thread(target=self.run_variable_scan, daemon=True).start()

    def stop_variable_scan(self):
        if self.is_processing:
            self._stop_scan = True
            self.btn_stop_scan.configure(state="disabled", text="⏳ Parando... (aguarde a faixa atual)")
            self.lbl_status.configure(text="⛔ Interrompendo...")

    def run_variable_scan(self):
        success_count = 0
        total = len(self.selected_files)
        
        self.log(f"--- Iniciando Escaneamento de {total} arquivos ---")
        
        for i, path in enumerate(self.selected_files):
            if self._stop_scan:
                self.log("⛔ Escaneamento interrompido pelo usuário.")
                break
            try:
                filename = os.path.basename(path)
                self.lbl_status.configure(text=f"Processando {i+1}/{total}: {filename[:25]}...")
                self.progress_bar.set((i + 1) / total)
                
                # 1. Identificar tags atuais ou extrair do nome
                audio = mutagen.File(path, easy=True)
                if not audio: continue
                
                cur_title = audio.get('title', [None])[0]
                cur_artist = audio.get('artist', [None])[0]
                
                # NOVO: Aplicar limpeza profunda solicitada pelo usuário (remove números, pontos, aspas, redundâncias)
                cur_title, cur_artist = MetadataCleaner.smart_clean(cur_title, cur_artist, filename)

                # 2. Chamar API IA
                # SEGURO: Se artista == título, buscamos de forma global para não induzir a API ao erro
                search_artist = cur_artist
                if cur_artist and cur_title and cur_artist.lower() == cur_title.lower():
                    self.log(f"⚠️ Redundância detectada em '{cur_title}'. Buscando globalmente...")
                    search_artist = ""

                self.log(f"🔍 Buscando: {search_artist if search_artist else '(Global)'} - {cur_title}")
                info = self.api_enhancer.get_track_complete_info(search_artist, cur_title)

                has_useful_info = info and (info.get('album') or info.get('year') or
                                            info.get('genre') or info.get('cover_url'))

                if has_useful_info:
                    # 3. Aplicar Metadados no Arquivo
                    if info.get('title'):  audio['title']  = info['title']
                    if info.get('artist'): audio['artist'] = info['artist']
                    if info.get('album'):  audio['album']  = info['album']
                    if info.get('year'):   audio['date']   = str(info['year'])
                    if info.get('genre'):  audio['genre']  = info['genre'].title()
                    if info.get('track_number'): audio['tracknumber'] = str(info['track_number'])
                    audio.save()
                else:
                    self.log(f"❓ Sem info precisa para: {filename}")

                # 4. Baixar Capa se encontrada
                final_cover_data = None
                cover_url = info.get('cover_url') if info else None
                if cover_url:
                    try:
                        resp = requests.get(cover_url, timeout=8)
                        if resp.status_code == 200:
                            final_cover_data = resp.content
                            cover_dir = os.path.join(self.db.root_dir, "assets", "covers")
                            os.makedirs(cover_dir, exist_ok=True)

                            safe_album = "".join([c for c in info.get('album', cur_artist) if c.isalnum() or c == '_'])
                            safe_artist = "".join([c for c in cur_artist if c.isalnum() or c == '_'])
                            cover_name = f"{safe_artist}_{safe_album}.jpg" if safe_album else f"{safe_artist}.jpg"
                            local_cover_path = os.path.join(cover_dir, cover_name)

                            with open(local_cover_path, 'wb') as f:
                                f.write(final_cover_data)

                            # Persistir capa no arquivo físico
                            try:
                                if filename.lower().endswith(".mp3"):
                                    from mutagen.id3 import ID3, APIC, error as ID3Error
                                    try:
                                        tags = ID3(path)
                                    except ID3Error:
                                        tags = ID3()
                                    tags.delall("APIC")
                                    tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='', data=final_cover_data))
                                    tags.save(path, v2_version=3)
                                elif filename.lower().endswith(".flac"):
                                    from mutagen.flac import Picture
                                    flac = mutagen.File(path)
                                    flac.clear_pictures()
                                    pic = Picture()
                                    pic.data = final_cover_data
                                    pic.type = 3
                                    pic.mime = "image/jpeg"
                                    flac.add_picture(pic)
                                    flac.save()
                                os.utime(path, None)
                                self.log(f"🖼️ Capa incorporada: {filename}")
                            except Exception as embed_err:
                                self.log(f"⚠️ Erro ao incorporar capa: {embed_err}")
                    except Exception as e:
                        self.log(f"⚠️ Erro ao baixar capa: {e}")

                # 5. Atualizar Banco de Dados — SEMPRE que tiver info útil
                if has_useful_info:
                    br = 0
                    ext = os.path.splitext(path)[1][1:].upper()
                    try:
                        tech = mutagen.File(path)
                        if hasattr(tech, 'info'):
                            br = int(tech.info.bitrate / 1000)
                    except: pass

                    db_data = {
                        'title':   audio.get('title',  [cur_title])[0],
                        'artist':  audio.get('artist', [cur_artist])[0],
                        'album':   audio.get('album',  [''])[0],
                        'year':    str(audio.get('date', [''])[0]) if audio.get('date') else '',
                        'genre':   audio.get('genre',  [''])[0],
                        'bitrate': br,
                        'ext':     ext
                    }
                    if final_cover_data and local_cover_path:
                        db_data['cover_path'] = f"assets/covers/{os.path.basename(local_cover_path)}"

                    # PONTO #4 — Baixar e salvar foto do artista (separada da capa)
                    artist_photo_url = info.get('artist_photo_url') if info else None
                    if artist_photo_url:
                        try:
                            ar = requests.get(artist_photo_url, timeout=8)
                            if ar.status_code == 200:
                                artist_dir = os.path.join(self.db.root_dir, "assets", "artists")
                                os.makedirs(artist_dir, exist_ok=True)
                                safe_art = "".join([c for c in cur_artist if c.isalnum() or c == '_'])
                                artist_photo_path = os.path.join(artist_dir, f"{safe_art}.jpg")
                                with open(artist_photo_path, 'wb') as af:
                                    af.write(ar.content)
                                db_data['artist_photo'] = f"assets/artists/{safe_art}.jpg"
                                self.log(f"👤 Foto do artista salva: {cur_artist}")
                        except Exception as ap_err:
                            self.log(f"⚠️ Erro ao baixar foto do artista: {ap_err}")

                    self.db.update_song_metadata(path, db_data)
                    cover_status = "🖼️+📝" if final_cover_data else "📝"
                    self.log(f"✅ {cover_status} Atualizado: {db_data['title']} — {db_data['album'] or 'sem álbum'}")
                    success_count += 1

            except Exception as e:
                self.log(f"❌ Erro em {filename}: {e}")



        stopped_early = self._stop_scan
        self.log(f"\n--- Fim do Processo: {success_count} arquivos enriquecidos ---")
        self.is_processing = False
        self._stop_scan = False
        self.btn_start_scan.configure(state="normal")
        self.btn_stop_scan.configure(state="disabled", text="🛑 Parar")
        
        # Só mostra o botão se houveram falhas (pendências)
        if success_count < total:
            # Pack it before the log box
            self.btn_go_manager.pack(pady=(0, 10), padx=30, fill="x", before=self.log_box)

        if stopped_early:
            self.lbl_status.configure(text="⛔ Interrompido pelo usuário")
            messagebox.showwarning("Scanner IA", f"Escaneamento interrompido!\n{success_count} de {total} arquivos processados até o momento.")
        else:
            self.lbl_status.configure(text="✅ Concluído!")
            messagebox.showinfo("Scanner IA", f"Concluído!\n{success_count} de {total} arquivos atualizados.")

        self.controller.notify_data_changed()

    def auto_identify(self):
        artist = self.entries['artist'].get()
        album = self.entries['album'].get()
        if not artist and not album and self.selected_files:
             parts = os.path.basename(self.folder_path).split(" - ")
             if len(parts) == 2:
                 artist, album = parts[0], parts[1]
        
        if not artist or not album:
            messagebox.showwarning("Aviso", "Preencha pelo menos Artista ou Álbum.")
            return

        # Feedback visual de início
        self.btn_auto.configure(state="disabled", text="🔍 Buscando na Nuvem...")
        self.lbl_auto_status.configure(text="Consultando bases Spotify/Deezer...", text_color="#aaa")
        self.update_idletasks()

        def run_search():
            try:
                info = self.api_enhancer.get_track_complete_info(artist, album)
                if info and info.get('album'):
                    self.update_entries({
                        'artist': info.get('artist'),
                        'album': info.get('album'),
                        'year': info.get('year'),
                        'genre': info.get('genre')
                    })
                    self.lbl_auto_status.configure(text="✨ Álbum identificado com sucesso!", text_color="#1DB954")
                else:
                    self.lbl_auto_status.configure(text="❌ Nenhuma informação encontrada.", text_color="#ff4444")
            except Exception as e:
                self.lbl_auto_status.configure(text=f"❌ Erro na busca: {str(e)[:20]}", text_color="#ff4444")
            finally:
                self.btn_auto.configure(state="normal", text="🪄 Identificar Álbum (API)")
        
        # Executa em thread para não travar a UI
        threading.Thread(target=run_search, daemon=True).start()

    def update_entries(self, data):
        for key, val in data.items():
            if val and key in self.entries:
                self.entries[key].delete(0, 'end')
                self.entries[key].insert(0, str(val))

    def apply_batch(self):
        if not self.selected_files:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Nenhuma música carregada. Selecione uma pasta primeiro.")
            return
        tags = {k: v.get() for k, v in self.entries.items() if v.get()}
        if not tags and not self.preserve_artist.get():
            messagebox.showwarning("Aviso", "Nenhuma tag definida.")
            return

        success_count = 0
        for path in self.selected_files:
            try:
                audio = mutagen.File(path, easy=True)
                if not audio: continue
                
                filename = os.path.basename(path)
                fname_no_ext = os.path.splitext(filename)[0]
                
                file_artist, file_title = None, None
                if " - " in fname_no_ext:
                    parts = fname_no_ext.split(" - ", 1)
                    file_artist, file_title = parts[0].strip(), parts[1].strip()

                if 'artist' in tags and not self.preserve_artist.get():
                     audio['artist'] = tags['artist']
                elif not self.preserve_artist.get() and file_artist:
                     audio['artist'] = file_artist

                if 'album' in tags: audio['album'] = tags['album']
                if 'year' in tags: audio['date'] = str(tags['year'])
                if 'genre' in tags: audio['genre'] = tags['genre']
                
                if file_title and (not audio.get('title') or audio['title'][0].lower() == "unknown"):
                     audio['title'] = file_title

                audio.save()
                
                br = 0
                ext = os.path.splitext(path)[1][1:].upper()
                try:
                    tech = mutagen.File(path)
                    if hasattr(tech, 'info'): br = int(tech.info.bitrate / 1000)
                except: pass

                self.db.update_song_metadata(path, {
                    'artist': audio.get('artist', [tags.get('artist', 'Unknown')])[0],
                    'album': audio.get('album', [tags.get('album', '')])[0],
                    'year': audio.get('date', [tags.get('year', '')])[0],
                    'genre': audio.get('genre', [tags.get('genre', '')])[0],
                    'title': audio.get('title', [file_title or filename])[0],
                    'bitrate': br, 'ext': ext
                })
                success_count += 1
            except Exception as e: print(f"Error: {e}")

        messagebox.showinfo("Sucesso", f"Concluído: {success_count} arquivos!")
        self.controller.notify_data_changed()
