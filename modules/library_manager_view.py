import customtkinter as ctk
import os
from PIL import Image
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, APIC
import hashlib
import time
import requests
from io import BytesIO
from .multi_api_enhancer import MultiAPIEnhancer
from .metadata_utils import MetadataCleaner

class LibraryManagerView(ctk.CTkFrame):
    def __init__(self, parent, controller, initial_folder=None):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        self.api_enhancer = MultiAPIEnhancer(database=controller.db)
        self.current_tracks = []
        self.selected_track_idx = None
        self.temp_cover_data = None
        self.selection_states = {} # Map track file_path to bool
        self.is_scanning = False
        self._stop_scanning = False
        
        # Layout Principal: Esquerda (Sidebar Editor) | Direita (Tabela)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 1. SIDEBAR DE EDIÇÃO (Inspirada no Mp3tag)
        self.setup_sidebar()
        
        # 2. ÁREA DA TABELA
        self.setup_table_area()
        
        # Carregar dados iniciais (Músicas com problemas por padrão)
        if initial_folder:
            self.search_entry.insert(0, str(initial_folder))
            self.filter_menu.set("Pendentes") # Prioriza pendências se veio do lote
            
            # SÓ dispara o carregamento se houver uma pasta inicial (vindo do Lote IA)
            self.after(300, self.load_data)

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=320, fg_color="#181818", corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=1)
        self.sidebar.grid_propagate(False)
        
        scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=20)
        
        ctk.CTkLabel(scroll, text="Editor Individual", font=("Segoe UI", 18, "bold")).pack(pady=10, anchor="w")
        
        self.fields = {}
        field_configs = [
            ("title", "Título"),
            ("artist", "Artista"),
            ("album", "Álbum"),
            ("year", "Ano"),
            ("track", "Nº Faixa"),
            ("genre", "Gênero"),
            ("albumartist", "Artista do Álbum"),
            ("composer", "Compositor"),
        ]
        
        for key, label in field_configs:
            lbl = ctk.CTkLabel(scroll, text=label, font=("Segoe UI", 12), text_color="#b3b3b3")
            lbl.pack(anchor="w", pady=(10, 2))
            entry = ctk.CTkEntry(scroll, placeholder_text=f"---", fg_color="#2b2b2b", border_width=0, height=32)
            entry.pack(fill="x", pady=(0, 5))
            self.fields[key] = entry

        # Área da Capa
        ctk.CTkLabel(scroll, text="Capa do Álbum", font=("Segoe UI", 12), text_color="#b3b3b3").pack(anchor="w", pady=(15, 5))
        self.cover_preview = ctk.CTkLabel(scroll, text="🎵", width=250, height=250, fg_color="#121212", corner_radius=8)
        self.cover_preview.pack(pady=5)
        
        # Botões de Ação na Sidebar
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        
        self.btn_auto = ctk.CTkButton(btn_frame, text="🤖 Auto-Sugestão (IA)", 
                                     fg_color="black", border_width=1, border_color="#c3000d",
                                     text_color="white", hover_color="#1a1a1a",
                                     font=("Segoe UI", 12, "bold"),
                                     command=self.auto_suggest_api)
        self.btn_auto.pack(fill="x", pady=5)
        
        self.btn_save = ctk.CTkButton(btn_frame, text="💾 Salvar Alterações", 
                                     fg_color="black", border_width=1, border_color="#c3000d",
                                     text_color="white", hover_color="#1a1a1a",
                                     font=("Segoe UI", 13, "bold"),
                                     command=self.save_current_edit)
        self.btn_save.pack(fill="x", pady=5)

    def setup_table_area(self):
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Header da Tabela com Filtros
        ctrl_bar = ctk.CTkFrame(self.main_content, fg_color="transparent")
        ctrl_bar.pack(fill="x", pady=10)
        
        title_lbl = ctk.CTkLabel(ctrl_bar, text="Gestão Global da Biblioteca", font=("Segoe UI", 24, "bold"))
        title_lbl.pack(side="left")
        
        # Contador de Pendências removido para evitar travamentos
        self.lbl_pending_count = ctk.CTkLabel(ctrl_bar, text="", font=("Segoe UI", 14), 
                                              text_color="#c3000d", fg_color="transparent", 
                                              width=1, height=1)
        # self.lbl_pending_count.pack(side="left", padx=15)

        # Botão Processar Selecionados (Círculo/Botão Verde sugerido)
        self.btn_batch_process = ctk.CTkButton(ctrl_bar, text="🤖 Processar Selecionados (IA)", 
                                                fg_color="black", border_width=1, border_color="#c3000d",
                                                text_color="white", hover_color="#1a1a1a",
                                                font=("Segoe UI", 12, "bold"), height=35,
                                                command=self.start_batch_ai_scan)
        self.btn_batch_process.pack(side="left", padx=5)
        
        self.filter_var = ctk.StringVar(value="Tudo")
        self.filter_menu = ctk.CTkSegmentedButton(ctrl_bar, values=["Tudo", "Pendentes", "Sem Capa"],
                                                  selected_color="#c3000d", selected_hover_color="#9a000a",
                                                  command=self.load_data)
        self.filter_menu.pack(side="right", padx=10)
        self.filter_menu.set("Tudo")

        # Busca por Pasta
        self.search_folder_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(ctrl_bar, placeholder_text="Filtrar por pasta...", 
                                        width=200, fg_color="#1a1a1a", border_width=1, border_color="#333")
        self.search_entry.pack(side="right", padx=10)
        self.search_entry.bind("<Return>", lambda e: self.load_data())

        # Tabela (Scrollable Frame para simular linhas)
        self.table_header = ctk.CTkFrame(self.main_content, fg_color="#1a1a1a", height=35)
        self.table_header.pack(fill="x")
        
        # Checkbox Selecionar Todos
        self.master_check = ctk.CTkCheckBox(self.table_header, text="", width=20, height=20, 
                                            command=self.toggle_all_selection)
        self.master_check.place(relx=0, rely=0.5, anchor="w", x=10)

        columns = [("Nome do Arquivo", 0.35), ("Título", 0.25), ("Artista", 0.2), ("Status", 0.15)]
        for text, weight in columns:
            lbl = ctk.CTkLabel(self.table_header, text=text, font=("Segoe UI", 12, "bold"), text_color="#777")
            # Rel x começa em 0.05 para dar espaço ao checkbox master
            rel_x = 0.05 + sum([c[1] for c in columns[:columns.index((text, weight))]])
            lbl.place(relx=rel_x, rely=0.5, anchor="w", x=15)

        self.table_body = ctk.CTkScrollableFrame(self.main_content, fg_color="transparent", corner_radius=0)
        self.table_body.pack(fill="both", expand=True)
        
        self.row_widgets = []

    def load_data(self, filter_mode=None):
        if not filter_mode: filter_mode = self.filter_menu.get()
        
        # Limpar tabela
        for w in self.table_body.winfo_children():
            w.destroy()
        self.row_widgets = []
        
        # Buscar do banco com Limite e Filtro de Pasta (Normalizando barras para consistência DB/Windows)
        folder_filter = self.search_entry.get().strip().replace("\\", "/")
        folder_clause = f" AND file_path LIKE '%{folder_filter}%'" if folder_filter else ""
        
        if filter_mode == "Pendentes":
            query = f"SELECT * FROM metadata_cache WHERE (LOWER(artist) LIKE '%unknown%' OR LOWER(title) LIKE '%unknown%' OR artist IS NULL OR artist = '' OR album IS NULL OR album = ''){folder_clause} LIMIT 500"
        elif filter_mode == "Sem Capa":
            query = f"SELECT * FROM metadata_cache WHERE (cover_path IS NULL OR cover_path = ''){folder_clause} LIMIT 200"
        else:
            where = f"WHERE file_path LIKE '%{folder_filter}%'" if folder_filter else ""
            query = f"SELECT * FROM metadata_cache {where} LIMIT 200"
            
        self.current_tracks = self.controller.db.query(query)
        self.row_checkboxes = []
        
        for i, track in enumerate(self.current_tracks):
            row = ctk.CTkFrame(self.table_body, fg_color="transparent", height=40, cursor="hand2")
            row.pack(fill="x", pady=1)
            
            # Checkbox de seleção Individual
            path = track['file_path']
            is_selected = self.selection_states.get(path, False)
            chk = ctk.CTkCheckBox(row, text="", width=20, height=20, command=lambda p=path: self.on_checkbox_click(p))
            if is_selected: chk.select()
            chk.place(relx=0, rely=0.5, anchor="w", x=10)
            self.row_checkboxes.append(chk)

            # Highlight on click (Clique na linha ainda funciona, mas não desvia o checkbox)
            row.bind("<Button-1>", lambda e, idx=i: self.on_row_select(idx))
            
            # Content
            filename = os.path.basename(track['file_path'])
            title = track.get('title') or '---'
            artist = track.get('artist') or '---'
            status = "⚠️ Pendente" if filter_mode != "Tudo" else "✅ OK"
            st_color = "#FFC107" if "⚠️" in status else "#4CAF50"

            # Visual Clean for Filename Column
            display_filename = MetadataCleaner.clean_text(filename)

            lbl_f = ctk.CTkLabel(row, text=display_filename, font=("Segoe UI", 12), anchor="w")
            lbl_f.place(relx=0.05, rely=0.5, anchor="w", relwidth=0.35, x=15)
            lbl_f.bind("<Button-1>", lambda e, idx=i: self.on_row_select(idx))
            
            lbl_t = ctk.CTkLabel(row, text=title, font=("Segoe UI", 12), anchor="w")
            lbl_t.place(relx=0.4, rely=0.5, anchor="w", relwidth=0.25, x=15)
            lbl_t.bind("<Button-1>", lambda e, idx=i: self.on_row_select(idx))

            lbl_a = ctk.CTkLabel(row, text=artist, font=("Segoe UI", 12), anchor="w")
            lbl_a.place(relx=0.65, rely=0.5, anchor="w", relwidth=0.2, x=15)
            lbl_a.bind("<Button-1>", lambda e, idx=i: self.on_row_select(idx))

            lbl_s = ctk.CTkLabel(row, text=status, font=("Segoe UI", 11, "bold"), text_color=st_color)
            lbl_s.place(relx=0.85, rely=0.5, anchor="w", relwidth=0.15, x=15)
            lbl_s.bind("<Button-1>", lambda e, idx=i: self.on_row_select(idx))

            self.row_widgets.append(row)
        
        # self.update_pending_badge()

    def on_row_select(self, index):
        # Deselect previous
        if self.selected_track_idx is not None:
            self.row_widgets[self.selected_track_idx].configure(fg_color="transparent")
            
        self.selected_track_idx = index
        self.row_widgets[index].configure(fg_color="#222") # Cor de destaque
        
        track = self.current_tracks[index]
        self.load_track_into_editor(track)

    def load_track_into_editor(self, track):
        self.temp_cover_data = None
        
        # Limpa campos
        for k in self.fields:
            self.fields[k].delete(0, 'end')
            val = str(track.get(k) or '')
            self.fields[k].insert(0, val)
            
        # Carregar capa
        c_path = track.get('cover_path')
        if c_path and os.path.exists(c_path):
            try:
                img = Image.open(c_path)
                ctk_img = ctk.CTkImage(img, size=(250, 250))
                self.cover_preview.configure(image=ctk_img, text="")
            except:
                self.cover_preview.configure(image=None, text="🎵")
        else:
            self.cover_preview.configure(image=None, text="🎵")

    def auto_suggest_api(self):
        if self.selected_track_idx is None: return
        
        track = self.current_tracks[self.selected_track_idx]
        filename = os.path.basename(track['file_path'])
        
        # Tenta limpar o nome do arquivo para busca
        fname_clean = filename.rsplit('.', 1)[0]
        self.btn_auto.configure(state="disabled", text="Buscando...")
        
        def run_task():
            try:
                info = self.api_enhancer.get_track_complete_info("", fname_clean)
                if info:
                    self.after(0, lambda: self.apply_suggested_info(info))
                else:
                    self.after(0, lambda: self.btn_auto.configure(state="normal", text="🤖 Sem resultados"))
                    self.after(1500, lambda: self.btn_auto.configure(text="🤖 Auto-Sugestão (IA)"))
            except:
                self.after(0, lambda: self.btn_auto.configure(state="normal", text="🤖 Auto-Sugestão (IA)"))

        import threading
        threading.Thread(target=run_task, daemon=True).start()

    def apply_suggested_info(self, info):
        mapping = {
            'title': 'title',
            'artist': 'artist',
            'album': 'album',
            'year': 'year',
            'genre': 'genre'
        }
        for field_key, info_key in mapping.items():
            if info.get(info_key):
                self.fields[field_key].delete(0, 'end')
                self.fields[field_key].insert(0, str(info[info_key]))
        
        if info.get('cover_url'):
            try:
                resp = requests.get(info['cover_url'], timeout=5)
                if resp.status_code == 200:
                    self.temp_cover_data = resp.content
                    img = Image.open(BytesIO(resp.content))
                    ctk_img = ctk.CTkImage(img, size=(250, 250))
                    self.cover_preview.configure(image=ctk_img, text="")
            except: pass
            
        self.btn_auto.configure(state="normal", text="✅ Sugestão Aplicada")
        self.after(2000, lambda: self.btn_auto.configure(text="🤖 Auto-Sugestão (IA)"))

    def save_current_edit(self):
        if self.selected_track_idx is None: return
        
        track = self.current_tracks[self.selected_track_idx]
        path = track['file_path']
        
        data = {k: self.fields[k].get() for k in self.fields}
        
        try:
            audio = mutagen.File(path)
            if audio is None: return

            if path.lower().endswith(".mp3"):
                try: tags = ID3(path)
                except: 
                    audio = MP3(path); audio.add_tags(); tags = ID3(path)
                
                tags["TIT2"] = TIT2(encoding=3, text=data['title'])
                tags["TPE1"] = TPE1(encoding=3, text=data['artist'])
                tags["TALB"] = TALB(encoding=3, text=data['album'])
                tags["TDRC"] = TDRC(encoding=3, text=data['year'])
                tags["TCON"] = TCON(encoding=3, text=data['genre'])
                
                if self.temp_cover_data:
                    tags.delall("APIC")
                    tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'', data=self.temp_cover_data))
                tags.save(path, v2_version=3)
            else:
                audio['title'] = [data['title']]
                audio['artist'] = [data['artist']]
                audio['album'] = [data['album']]
                audio.save()

            db_update = {
                'title': data['title'],
                'artist': data['artist'],
                'album': data['album'],
                'year': data['year'],
                'genre': data['genre']
            }
            
            if self.temp_cover_data:
                covers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "covers")
                os.makedirs(covers_dir, exist_ok=True)
                safe_name = hashlib.md5(path.encode()).hexdigest() + ".jpg"
                save_path = os.path.join(covers_dir, safe_name).replace("\\", "/")
                with open(save_path, "wb") as f:
                    f.write(self.temp_cover_data)
                db_update['cover_path'] = save_path
                
            self.controller.db.update_song_metadata(path, db_update)
            
            self.btn_save.configure(fg_color="#27ae60", text="✔ Salvo com Sucesso", border_width=0)
            self.after(2000, lambda: self.btn_save.configure(fg_color="black", text="💾 Salvar Alterações", border_width=1, border_color="#c3000d"))
            
            # Atualiza lista local e recarrega
            self.current_tracks[self.selected_track_idx].update(db_update)
            self.load_data()
            # self.update_pending_badge()
            
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            self.btn_save.configure(fg_color="red", text="❌ Erro ao Salvar")

    def update_pending_badge(self):
        # Desativado para evitar travamentos
        pass
        # try:
        #     query = "SELECT COUNT(*) as count FROM metadata_cache WHERE (LOWER(artist) LIKE '%unknown%' OR LOWER(title) LIKE '%unknown%' OR artist IS NULL OR artist = '' OR album IS NULL OR album = '')"
        #     res = self.controller.db.query(query)
        #     count = res[0]['count'] if res else 0
        #     self.lbl_pending_count.configure(text=f"{count} pendentes")
        # except: pass

    def on_checkbox_click(self, path):
        # Inverte estado
        current = self.selection_states.get(path, False)
        self.selection_states[path] = not current

    def toggle_all_selection(self):
        val = self.master_check.get()
        # Aplica a todas as visíveis
        for track in self.current_tracks:
            self.selection_states[track['file_path']] = bool(val)
        
        # Atualiza checkboxes da tela
        for chk in self.row_checkboxes:
            if val: chk.select()
            else: chk.deselect()

    def start_batch_ai_scan(self):
        selected_paths = [p for p, sel in self.selection_states.items() if sel]
        if not selected_paths:
            import messagebox
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Selecione pelo menos uma música para processar.")
            return

        if self.is_scanning:
            self._stop_scanning = True
            return

        self.is_scanning = True
        self._stop_scanning = False
        self.btn_batch_process.configure(text="⏳ Parar Processo", fg_color="black", border_width=1, border_color="#c3000d")
        
        import threading
        threading.Thread(target=self.run_batch_ai_task, args=(selected_paths,), daemon=True).start()

    def run_batch_ai_task(self, paths):
        total = len(paths)
        for i, path in enumerate(paths):
            if self._stop_scanning: break
            
            filename = os.path.basename(path)
            self.after(0, lambda v=i: self.btn_batch_process.configure(text=f"🤖 {v+1}/{total} - Processando..."))
            
            try:
                # Extrai nome base para busca
                fname_clean = filename.rsplit('.', 1)[0]
                info = self.api_enhancer.get_track_complete_info("", fname_clean)
                
                if info and (info.get('artist') or info.get('album')):
                    # Aplicar metadados no arquivo físico e banco
                    self.apply_info_to_file_and_db(path, info)
                    # Remove da seleção se concluído com sucesso
                    self.selection_states[path] = False
                    # Atualiza o contador em tempo real
                    # self.after(0, self.update_pending_badge)
            except Exception as e:
                print(f"Erro no batch AI {filename}: {e}")
                
        self.is_scanning = False
        self.after(0, self.finish_batch_scan)

    def apply_info_to_file_and_db(self, path, info):
        # Lógica simplificada de salvamento (similar ao save_current_edit)
        try:
            audio = mutagen.File(path, easy=True)
            if audio is not None:
                if info.get('title'): audio['title'] = info['title']
                if info.get('artist'): audio['artist'] = info['artist']
                if info.get('album'): audio['album'] = info['album']
                if info.get('year'): audio['date'] = str(info['year'])
                if info.get('genre'): audio['genre'] = info['genre'].title()
                audio.save()
            
            db_update = {
                'title': info.get('title', ''),
                'artist': info.get('artist', ''),
                'album': info.get('album', ''),
                'year': str(info.get('year', '')),
                'genre': info.get('genre', '')
            }
            # Se tiver capa, o MultiAPIEnhancer já pode ter retornado cover_url
            # Para simplificar o batch, focamos em texto. Capas podem ser processadas individualmente ou em v2.
            self.controller.db.update_song_metadata(path, db_update)
        except: pass

    def finish_batch_scan(self):
        self.btn_batch_process.configure(text="🤖 Processar Selecionados (IA)", fg_color="black", border_width=1, border_color="#c3000d")
        self.load_data()
        # self.update_pending_badge()
        self.controller.notify_data_changed()
        from tkinter import messagebox
        messagebox.showinfo("Scanner Batch", "Processamento em lote concluído!")

