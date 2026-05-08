import customtkinter as ctk
import os
import threading
import tempfile
import time
import csv
from tkinter import filedialog
from pathlib import Path
from modules.downloader import MusicDownloader, SHAZAM_AVAILABLE
from modules.scanner import LibraryScanner
from modules.multi_api_enhancer import MultiAPIEnhancer

# Cores do sistema
RED_ACCENT = "#c3000d"
RED_HOVER = "#9a000a"
BG_COLOR = "#121212"
CARD_COLOR = "#181818"
TEXT_COLOR = "#ffffff"
TEXT_MUTED = "#b3b3b3"

class DownloadView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.db = controller.db
        
        default_path = r"C:\Users\Ricardo\Downloads\musicas"
        self.downloader = MusicDownloader(download_path=default_path)
        self.scanner = LibraryScanner(self.db)
        self.api_enhancer = MultiAPIEnhancer(self.db)
        
        # Inicializa variáveis de status para evitar erros de callback
        self.shazam_status = None
        
        self.is_recording = False
        self.stop_requested = False
        self.temp_audio_file = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Título da View
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 10))
        
        ctk.CTkLabel(title_frame, text="Download Music", font=("Segoe UI", 32, "bold"), text_color="white").pack(side="left")
        
        # Subtítulo/Status
        self.status_label = ctk.CTkLabel(self, text="Baixe músicas via URL, Nome ou Reconhecimento de Áudio", font=("Segoe UI", 14), text_color=TEXT_MUTED)
        self.status_label.pack(anchor="w", padx=35, pady=(0, 20))

        # Container Principal
        container = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=15)
        container.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Tab View
        self.tabview = ctk.CTkTabview(container, fg_color=CARD_COLOR, segmented_button_selected_color=RED_ACCENT, 
                                     segmented_button_selected_hover_color=RED_HOVER, text_color="white")
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tab_name = self.tabview.add("🔍 Por Nome")
        self.tab_url = self.tabview.add("🔗 Por URL")
        self.tab_mass = self.tabview.add("🚀 Massa (CSV)")
        
        self._setup_name_tab()
        self._setup_url_tab()
        self._setup_mass_tab()
        
        # Progress info (Shared)
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=30, pady=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, progress_color=RED_ACCENT, height=10)
        self.progress_bar.pack(fill="x", padx=20)
        self.progress_bar.set(0)
        
        self.percent_label = ctk.CTkLabel(self.progress_frame, text="Pronto para download", font=("Segoe UI", 12), text_color=TEXT_MUTED)
        self.percent_label.pack(pady=5)

        self.btn_stop = ctk.CTkButton(self.progress_frame, text="🛑 Parar Download", 
                                     fg_color="#333", hover_color="#555",
                                     height=35, font=("Segoe UI", 12, "bold"),
                                     command=self._stop_download)
        self.btn_stop.pack(pady=5)
        self.btn_stop.pack_forget()

        # Botões de Ferramentas de Biblioteca (Globais no rodapé)
        self.tools_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        self.tools_frame.pack(pady=10)

        self.btn_check_duplicates = ctk.CTkButton(self.tools_frame, text="🔗 Verificar Duplicados na Biblioteca", 
                                                 fg_color="#444", hover_color="#666",
                                                 height=40, width=250, font=("Segoe UI", 12, "bold"),
                                                 command=self._ui_check_duplicates)
        self.btn_check_duplicates.pack(side="left", padx=5)

        self.btn_sync_today = ctk.CTkButton(self.tools_frame, text="📦 Organizar Biblioteca (Novidades de Hoje)", 
                                           fg_color="#1E4D2B", hover_color="#2E6D3B",
                                           height=40, width=320, font=("Segoe UI", 12, "bold"),
                                           command=self._ui_organize_library)
        self.btn_sync_today.pack(side="left", padx=5)

    def _setup_name_tab(self):
        frame = self.tab_name
        
        ctk.CTkLabel(frame, text="Digite o nome da música e o artista:", font=("Segoe UI", 16)).pack(pady=(20, 5))
        
        self.name_entry = ctk.CTkEntry(frame, placeholder_text="Ex: Linkin Park - Numb", width=500, height=45, 
                                      font=("Segoe UI", 14), fg_color="#222", border_color="#333")
        self.name_entry.pack(pady=10)
        
        self.btn_name = ctk.CTkButton(frame, text="Buscar e Baixar", font=("Segoe UI", 16, "bold"), 
                                     fg_color=RED_ACCENT, hover_color=RED_HOVER, height=45, width=200,
                                     command=self._download_by_name)
        self.btn_name.pack(pady=20)

    def _setup_url_tab(self):
        frame = self.tab_url
        
        ctk.CTkLabel(frame, text="Cole a URL do YouTube, SoundCloud:", font=("Segoe UI", 16)).pack(pady=(20, 5))
        
        self.url_entry = ctk.CTkEntry(frame, placeholder_text="https://www.youtube.com/watch?v=...", width=600, height=45, 
                                     font=("Segoe UI", 14), fg_color="#222", border_color="#333")
        self.url_entry.pack(pady=10)
        
        self.btn_url = ctk.CTkButton(frame, text="Iniciar Download", font=("Segoe UI", 16, "bold"), 
                                    fg_color=RED_ACCENT, hover_color=RED_HOVER, height=45, width=200,
                                    command=self._download_by_url)
        self.btn_url.pack(pady=20)

    def _setup_mass_tab(self):
        frame = self.tab_mass
        
        # Ícone e Título
        ctk.CTkLabel(frame, text="📁", font=("Segoe UI", 60)).pack(pady=(30, 10))
        ctk.CTkLabel(frame, text="Download em Massa (Shazam CSV)", 
                     font=("Segoe UI", 20, "bold")).pack(pady=5)
        
        self.mass_info_label = ctk.CTkLabel(frame, 
                                           text="Exporte seu CSV no Shazam e selecione o arquivo aqui para baixar tudo automaticamente.", 
                                           font=("Segoe UI", 13), text_color=TEXT_MUTED, justify="center")
        self.mass_info_label.pack(pady=10)

        # Botão de Seleção
        self.btn_select_csv = ctk.CTkButton(frame, text="Selecionar Arquivo CSV", 
                                           fg_color=RED_ACCENT, hover_color=RED_HOVER,
                                           height=45, font=("Segoe UI", 14, "bold"),
                                           command=self._select_csv)
        self.btn_select_csv.pack(pady=20)

        # Status do Processo em Massa
        self.mass_status = ctk.CTkLabel(frame, text="", font=("Segoe UI", 14, "bold"), text_color="cyan")
        self.mass_status.pack(pady=5)
        
        self.mass_progress = ctk.CTkProgressBar(frame, width=400, height=15, progress_color="cyan")
        self.mass_progress.set(0)
        self.mass_progress.pack(pady=10)
        self.mass_progress.pack_forget()

    def _update_progress(self, percent):
        self.after(0, lambda: self.progress_bar.set(percent / 100))
        self.after(0, lambda: self.percent_label.configure(text=f"Baixando... {percent:.1f}%"))

    def _download_by_name(self):
        query = self.name_entry.get().strip()
        if not query: return
        
        self._start_process("Buscando no YouTube...")
        threading.Thread(target=self._proc_download_by_name, args=(query,), daemon=True).start()

    def _proc_download_by_name(self, query):
        # 1. Enriquecer metadados usando APIs (Spotify/Deezer)
        self.status_label.configure(text="Enriquecendo metadados oficiais...", text_color="cyan")
        
        # Tenta separar artista e música se houver ' - '
        art, track = "", query
        if ' - ' in query:
            parts = query.split(' - ')
            art, track = parts[0], parts[1]
            
        official_data = self.api_enhancer.get_track_complete_info(art, track)
        
        # 2. Se achou dados oficiais, usa para uma busca mais precisa no YouTube
        search_query = query
        if official_data.get('artist') and official_data.get('title'):
            search_query = f"{official_data['artist']} - {official_data['title']} (Official Audio)"
            
        url = self.downloader._search_youtube(search_query)
        if url:
            self._proc_download_by_url(url, metadata=official_data)
        else:
            self._finish_process("Não foi possível encontrar a música.")

    def _download_by_url(self):
        url = self.url_entry.get().strip()
        if not url: return
        
        self._start_process("Iniciando download...")
        threading.Thread(target=self._proc_download_by_url, args=(url,), daemon=True).start()

    def _proc_download_by_url(self, url, metadata=None):
        if self.stop_requested: return
        self.downloader.set_progress_callback(self._update_progress)
        
        # 1. Verificar se é um link externo (Spotify, Deezer, Tidal)
        if any(x in url.lower() for x in ['spotify.com', 'deezer.com', 'tidal.com']):
            self.status_label.configure(text="Identificando link externo...", text_color="cyan")
            ext_metadata = self.downloader.get_metadata_from_external_url(url)
            
            if ext_metadata:
                self.status_label.configure(text=f"Buscando: {ext_metadata.get('title')}...", text_color="white")
                query = f"{ext_metadata.get('artist')} - {ext_metadata.get('title')} (Official Audio)"
                search_url = self.downloader._search_youtube(query)
                if search_url:
                    url = search_url
                    metadata = ext_metadata
                else:
                    self._finish_process("Não foi possível encontrar a música no YouTube/SoundCloud.", success=False)
                    return
            else:
                self._finish_process("Não foi possível extrair metadados desse link.", success=False)
                return

        # 2. Iniciar Download
        filepath = self.downloader.download_from_youtube(url, metadata)
        
        if self.stop_requested:
            self._finish_process("Download cancelado pelo usuário.", success=False)
            return

        if filepath:
            self._after_download(filepath)
        else:
            self._finish_process("Erro ao realizar o download.")

    def _toggle_recording(self):
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        try:
            import sounddevice as sd
            import soundfile as sf
            
            self.is_recording = True
            self.btn_mic.configure(text="🛑 Parar (Ouvindo...)", fg_color="#333")
            self.shazam_status.configure(text="Gravando áudio por 10 segundos...")
            
            def record():
                duration = 10  # 10s is good for Shazam
                fs = 44100
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
                
                # Check if stopped mid-way
                start_time = time.time()
                while self.is_recording and time.time() - start_time < duration:
                    time.sleep(0.1)
                
                if not self.is_recording:
                    sd.stop()
                    return

                sd.wait()
                self.is_recording = False
                
                # Save to temp
                temp_dir = tempfile.gettempdir()
                self.temp_audio_file = os.path.join(temp_dir, f"shazam_{int(time.time())}.wav")
                sf.write(self.temp_audio_file, recording, fs)
                
                self.after(0, self._process_recognition)
            
            threading.Thread(target=record, daemon=True).start()
        except Exception as e:
            self._finish_process(f"Erro ao acessar microfone: {e}")

    def _stop_recording(self):
        self.is_recording = False
        self.btn_mic.configure(text="🎤 Ouvir Agora", fg_color=RED_ACCENT)

    def _process_recognition(self):
        self.shazam_status.configure(text="Identificando música...")
        self.btn_mic.configure(state="disabled")
        
        threading.Thread(target=self._proc_shazam, daemon=True).start()

    def _proc_shazam(self):
        if not self.temp_audio_file: return
        
        filepath = self.downloader.recognize_and_download(self.temp_audio_file)
        
        # Cleanup temp file
        try: os.unlink(self.temp_audio_file)
        except: pass
        
        if filepath:
            self._after_download(filepath)
        else:
            self._finish_process("Música não identificada ou não disponível.")
        
        self.after(0, lambda: self.btn_mic.configure(state="normal", text="🎤 Ouvir Agora"))

    def _after_download(self, filepath):
        # Indexar no banco
        music_data = self.scanner.scan_single_file(filepath)
        
        if music_data:
            msg = f"Sucesso! {music_data.get('title')} baixada."
            self._finish_process(msg)
            # Notificar main para atualizar views se estiverem abertas
            self.after(0, lambda: self.controller.notify_data_changed())
        else:
            self._finish_process("Música baixada, mas erro ao indexar.")

    def _start_process(self, msg):
        self.stop_requested = False
        self.status_label.configure(text=msg, text_color="white")
        self.progress_bar.set(0)
        self.percent_label.configure(text="Iniciando...")
        
        # Reset do botão de parar
        self.btn_stop.configure(text="🛑 Parar Download", state="normal")
        self.btn_stop.pack(pady=5)
        
        # Esconde as ferramentas da biblioteca
        if hasattr(self, 'tools_frame'): self.tools_frame.pack_forget()

    def _finish_process(self, message, success=True):
        self.is_downloading = False
        self.btn_stop.pack_forget()
        color = "green" if success else RED_ACCENT
        self.status_label.configure(text=message, text_color=color)
        
        # Mostra as ferramentas novamente
        if hasattr(self, 'tools_frame'): self.tools_frame.pack(pady=10)
        
        # Reativa os botões
        if hasattr(self, 'search_btn'): self.search_btn.configure(state="normal")
        if hasattr(self, 'url_btn'): self.url_btn.configure(state="normal")
        if hasattr(self, 'btn_select_csv'): self.btn_select_csv.configure(state="normal")
        
        # Limpa status de massa se necessário
        # try:
        #    if self.shazam_status and self.shazam_status.winfo_exists():
        #        self.after(0, lambda: self.shazam_status.configure(text=""))
        # except: pass

    def _select_csv(self):
        # Tenta o caminho padrão primeiro
        default_csv = r"C:\Users\Ricardo\Downloads\musicas\shazamlibrary.csv"
        
        if os.path.exists(default_csv):
            # Se o arquivo padrão existe, pergunta se quer usar ele
            from tkinter import messagebox
            if messagebox.askyesno("Shazam CSV Detectado", f"Deseja carregar o arquivo encontrado em:\n{default_csv}?"):
                threading.Thread(target=self._proc_mass_download, args=(default_csv,), daemon=True).start()
                return

        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo CSV do Shazam",
            filetypes=[("Arquivos CSV", "*.csv")]
        )
        if file_path:
            threading.Thread(target=self._proc_mass_download, args=(file_path,), daemon=True).start()

    def _proc_mass_download(self, file_path):
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            self.btn_select_csv.configure(state="disabled")
            self.mass_progress.pack(pady=10)
            self.mass_progress.set(0)
            
            tracks_to_download = []
            
            with open(file_path, mode='r', encoding='utf-8') as f:
                content = f.readlines()
                if content and "Shazam Library" in content[0]:
                    content = content[1:]
                
                reader = csv.DictReader(content)
                for row in reader:
                    # Garantia: se o valor for None, vira string vazia antes do strip
                    t_raw = row.get('Title') or ""
                    a_raw = row.get('Artist') or ""
                    
                    title = t_raw.strip()
                    artist = a_raw.strip()
                    
                    if title and artist:
                        tracks_to_download.append({'artist': artist, 'title': title})

            total = len(tracks_to_download)
            if total == 0:
                self.after(0, lambda: self.mass_status.configure(text="CSV vazio ou inválido.", text_color=RED_ACCENT))
                self.btn_select_csv.configure(state="normal")
                return

            self.after(0, lambda: [
                self.mass_status.configure(text=f"🚀 Turbo Ativado: Baixando {total} músicas...", text_color="cyan"),
                self.btn_stop.configure(text="🛑 Parar Download", state="normal"),
                self.btn_stop.pack(pady=5),
                self.tools_frame.pack_forget() if hasattr(self, 'tools_frame') else None
            ])
            
            completed = 0
            
            def download_task(track):
                nonlocal completed
                if self.stop_requested: return
                
                try:
                    # 1. Enriquecimento (API)
                    official_data = self.api_enhancer.get_track_complete_info(track['artist'], track['title'])
                    
                    if self.stop_requested: return
                    
                    # 2. Busca YouTube
                    search_query = f"{official_data['artist']} - {official_data['title']} (Official Audio)"
                    url = self.downloader._search_youtube(search_query)
                    
                    if url and not self.stop_requested:
                        # 3. Download Direto
                        filepath = self.downloader.download_from_youtube(url, official_data)
                        if filepath and not self.stop_requested:
                            self.scanner.scan_single_file(filepath)
                except Exception as e:
                    print(f"Erro na música {track['title']}: {e}")
                
                completed += 1
                progress = completed / total
                self.after(0, lambda p=progress, c=completed: [
                    self.mass_progress.set(p),
                    self.mass_status.configure(text=f"⚡ Processando {c}/{total}: {track['artist']} - {track['title']}" if not self.stop_requested else "🛑 Interrompendo...")
                ])

            self.after(0, lambda: self.btn_stop.pack(pady=5))

            # Roda 3 downloads simultâneos
            with ThreadPoolExecutor(max_workers=3) as executor:
                for _ in executor.map(download_task, tracks_to_download):
                    if self.stop_requested: break
            
            if self.stop_requested:
                self.after(0, lambda: [
                    self.mass_status.configure(text=f"🛑 Interrompido. {completed}/{total} músicas processadas.", text_color="orange"),
                    self.btn_select_csv.configure(state="normal"),
                    self.btn_stop.pack_forget()
                ])
                return

            self.after(0, lambda: [
                self.mass_status.configure(text=f"✅ Sucesso! {total} músicas processadas no modo Turbo.", text_color="green"),
                self.btn_select_csv.configure(state="normal"),
                self.btn_stop.pack_forget(),
                self.tools_frame.pack(pady=10) if hasattr(self, 'tools_frame') else None,
                self.controller.notify_data_changed()
            ])
            
        except Exception as e:
            self.after(0, lambda: self.mass_status.configure(text=f"Erro no Robô: {str(e)}", text_color=RED_ACCENT))
            self.btn_select_csv.configure(state="normal")

    # --- Lógica de De-para (Duplicados) ---

    def _ui_check_duplicates(self):
        """Abre uma janela para mostrar e deletar músicas que já existem na biblioteca"""
        download_dir = self.downloader.download_path
        
        # 1. Escaneia arquivos na pasta de download
        files = list(Path(download_dir).glob("*.mp3"))
        if not files:
            from tkinter import messagebox
            messagebox.showinfo("Limpeza", "Nenhum arquivo MP3 encontrado na pasta de downloads.")
            return

        duplicates = []
        
        def normalize(text):
            import re
            if not text: return ""
            text = text.lower()
            # Remove parênteses e colchetes (ex: (Official Video), [HQ])
            text = re.sub(r'\(.*?\)|\[.*?\]', '', text)
            # Remove termos comuns que variam
            text = re.sub(r'feat\.|ft\.|participação|part\.|prod\.|remix|original mix', '', text)
            # Remove tudo que não é letra ou número
            return re.sub(r'[^a-z0-9]', '', text)

        def split_name(name):
            # Tenta vários separadores comuns para dividir Artista - Título
            for sep in [" - ", " – ", " -", "- ", "-", "_"]:
                if sep in name:
                    parts = name.split(sep, 1)
                    return parts[0].strip(), parts[1].strip()
            return "", name

        for f in files:
            filename = f.stem
            artist_raw, title_raw = split_name(filename)
            
            # Digitais para comparação
            norm_artist = normalize(artist_raw)
            norm_title = normalize(title_raw)
            
            # Se não temos artista no nome do arquivo, a digital é só o título
            file_fingerprint = norm_artist + norm_title if norm_artist else norm_title
            
            # Busca no banco por Título ou Artista (mais abrangente)
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Buscamos por Título (costuma ser mais único)
                query = "SELECT file_path, artist, title FROM metadata_cache WHERE title LIKE ? OR artist LIKE ?"
                # Busca por parte do título (primeiros 5 caracteres) para ser rápido e certeiro
                search_term = f"%{title_raw[:5]}%" if len(title_raw) > 5 else f"%{title_raw}%"
                cursor.execute(query, (search_term, f"%{artist_raw[:5]}%" if artist_raw else "---")) 
                candidates = cursor.fetchall()
                
                for lib_path, lib_artist, lib_title in candidates:
                    # TRAVA DE SEGURANÇA 1: Ignora se o arquivo encontrado for o próprio arquivo na pasta de downloads
                    if "downloads" in lib_path.lower():
                        continue
                        
                    # Comparamos as digitais limpas
                    lib_norm_artist = normalize(lib_artist)
                    lib_norm_title = normalize(lib_title)
                    
                    # Checagem Dupla Progressiva
                    is_match = False
                    # 1. Digital completa bate 100%
                    if (norm_artist + norm_title) == (lib_norm_artist + lib_norm_title):
                        is_match = True
                    # 2. Título é idêntico e o Artista é pelo menos parecido (ou o arquivo não tem artista)
                    elif norm_title and norm_title == lib_norm_title:
                        if not norm_artist or norm_artist in lib_norm_artist or lib_norm_artist in norm_artist:
                            is_match = True

                    if is_match:
                        # Achamos uma duplicada REAL em outra pasta (fora do downloads)
                        duplicates.append({
                            'current_path': str(f).replace("\\", "/"),
                            'library_path': lib_path.replace("\\", "/"),
                            'name': filename
                        })
                        break
                    
                # Se após olhar todos os candidatos não achou uma duplicada real fora do downloads, o arquivo é novo!

        if not duplicates:
            from tkinter import messagebox
            messagebox.showinfo("Limpeza", "Parabéns! Nenhuma música repetida encontrada. Sua biblioteca está limpa.")
            return

        # 2. Abre Janela de Resultado
        self._show_duplicates_window(duplicates)

    def _show_duplicates_window(self, duplicates):
        win = ctk.CTkToplevel(self)
        win.title("De-para: Músicas Duplicadas Identificadas")
        # Header
        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(header, text="Músicas já existentes na sua Biblioteca", 
                     font=("Segoe UI", 16, "bold"), text_color="white").pack(side="left")
        
        # Contador em destaque
        count_badge = ctk.CTkFrame(header, fg_color=RED_ACCENT, corner_radius=15)
        count_badge.pack(side="left", padx=15)
        ctk.CTkLabel(count_badge, text=f"{len(duplicates)} DUPLICADAS", 
                     font=("Segoe UI", 12, "bold"), text_color="white", padx=10, pady=2).pack()
        
        # Container com Scroll
        scroll = ctk.CTkScrollableFrame(win, fg_color="#1a1a1a")
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Variáveis para as caixas de seleção
        self.duplicate_vars = []
        
        for i, dup in enumerate(duplicates):
            row = ctk.CTkFrame(scroll, fg_color="#252525", corner_radius=8)
            row.pack(fill="x", pady=2, padx=5)
            
            # Checkbox
            var = ctk.BooleanVar(value=True) # Marcamos por padrão
            cb = ctk.CTkCheckBox(row, text="", variable=var, width=30, checkbox_width=20, checkbox_height=20)
            cb.pack(side="left", padx=10)
            self.duplicate_vars.append((var, dup))
            
            # Info da Música
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, pady=5)
            
            filename = os.path.basename(dup['current_path'])
            ctk.CTkLabel(info, text=filename, font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            
            # Caminhos
            ctk.CTkLabel(info, text=f"🏠 Na Biblioteca: {dup['library_path']}", 
                         font=("Segoe UI", 11), text_color="#10b981", anchor="w").pack(fill="x")

        # Footer Actions
        footer = ctk.CTkFrame(win, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=20)
        
        def _delete_selected():
            to_delete = [dup for var, dup in self.duplicate_vars if var.get()]
            if not to_delete:
                from tkinter import messagebox
                messagebox.showwarning("Seleção", "Selecione ao menos uma música para excluir.", parent=win)
                return
                
            from tkinter import messagebox
            if messagebox.askyesno("Confirmar Exclusão", 
                                  f"Deseja excluir as {len(to_delete)} músicas selecionadas do Downloads?\nSua biblioteca oficial NÃO será alterada.",
                                  parent=win):
                count = 0
                for dup in to_delete:
                    try:
                        if os.path.exists(dup['current_path']):
                            os.remove(dup['current_path'])
                            count += 1
                    except: pass
                
                messagebox.showinfo("Sucesso", f"{count} músicas removidas com sucesso!", parent=win)
                win.destroy()

        ctk.CTkButton(footer, text=f"🗑️ Excluir Selecionadas do Downloads", 
                     fg_color=RED_ACCENT, hover_color="#8b111a",
                     height=40, font=("Segoe UI", 13, "bold"),
                     command=_delete_selected).pack(side="right")
        
        ctk.CTkButton(footer, text="Manter Todas", fg_color="transparent", border_width=1,
                     width=100, command=win.destroy).pack(side="right", padx=10)

    def _stop_download(self):
        """Sinaliza para que todos os processos de download parem"""
        self.stop_requested = True
        self.btn_stop.configure(text="⏳ Parando...", state="disabled")
        self.status_label.configure(text="Solicitando interrupção...", text_color="orange")
        self.mass_status.configure(text="🛑 Parando robô...", text_color="orange")

    def _ui_organize_library(self):
        """Dispara o scanner inteligente focado apenas em novidades do dia"""
        library_root = r"C:\Users\Ricardo\Music"
        
        self.mass_status.configure(text="📦 Escaneando novidades do dia na biblioteca oficial...", text_color="cyan")
        self.btn_sync_today.configure(state="disabled")
        
        def run_sync():
            try:
                # Chama o novo método que criamos no scanner
                results = self.scanner.scan_by_date(library_root)
                
                msg = f"Sincronização Concluída!\n\nNovas músicas indexadas: {results['new']}\nMetadados atualizados: {results['updated']}"
                from tkinter import messagebox
                self.after(0, lambda: messagebox.showinfo("📦 Organização Completa", msg))
                
                self.after(0, lambda: [
                    self.mass_status.configure(text=f"✅ Biblioteca Atualizada: +{results['new']} músicas.", text_color="green"),
                    self.btn_sync_today.configure(state="normal"),
                    self.controller.notify_data_changed()
                ])
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: [
                    self.mass_status.configure(text=f"Erro na sincronização: {err_msg}", text_color=RED_ACCENT),
                    self.btn_sync_today.configure(state="normal")
                ])

        threading.Thread(target=run_sync, daemon=True).start()
