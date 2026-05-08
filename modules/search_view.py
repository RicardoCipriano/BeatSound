import customtkinter as ctk
import os
from PIL import Image
from .spectrum_visualizer import SpectrumVisualizer, SoundCloudVisualizer

class SearchView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        self._image_refs = []
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(2, 0))
        
        ctk.CTkLabel(header, text="🔍 Buscar Músicas", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
        
        # Search Box
        search_container = ctk.CTkFrame(self, fg_color="#1f1f1f", corner_radius=12)
        search_container.pack(fill="x", padx=30, pady=2)
        
        self.entry = ctk.CTkEntry(search_container, placeholder_text="O que você quer ouvir?", 
                                 height=45, fg_color="transparent", border_width=0, font=("Segoe UI", 16))
        self.entry.pack(side="left", fill="x", expand=True, padx=20)
        self.entry.bind("<Return>", lambda e: self.perform_search())
        self.entry.bind("<KeyRelease>", self.on_search_type)
        self.entry.bind("<FocusOut>", lambda e: self.after(200, self.hide_autocomplete))
        
        # Filter and Folder Row
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=30, pady=(2, 0))
        
        # Filter Radios
        self.filter_var = ctk.StringVar(value="Todos")
        filters = ["Todos", "Artista", "Música", "Álbum"]
        for f in filters:
            ctk.CTkRadioButton(filter_frame, text=f, variable=self.filter_var, value=f, 
                              fg_color="#c3000d", hover_color="#9a000a").pack(side="left", padx=(0, 15))
        
        
        from .glow_button import GlowButton
        
        # Botão Buscar
        self.btn_search = GlowButton(filter_frame, text="Buscar", width=120, height=35,
                                    command=self.perform_search)
        self.btn_search.pack(side="right")
        
        # Botão Tocar Todas (ao lado esquerdo do Buscar)
        self.btn_play_all = GlowButton(filter_frame, text="▶ Tocar Todas", width=140, height=35,
                                       command=self.play_all_results)
        self.btn_play_all.pack(side="right", padx=10)
        self.btn_play_all.pack_forget() 
        
        # Visualizador SoundCloud (Compacto)
        self.sc_visualizer = SoundCloudVisualizer(self, height=45, progress_color="#ff5500", bar_color="#444")
        self.sc_visualizer.pack(fill="x", padx=30, pady=(0, 2))
        self.sc_visualizer.pack_forget() 
        
        # Results area header
        self.results_header_labels = ctk.CTkFrame(self, fg_color="transparent")
        self.results_header_labels.pack(fill="x", padx=35, pady=(2, 0))
        
        # Grid weights for header alignment: Title(4), Artist(3), Album(3), Dur(1), Actions(1)
        self.results_header_labels.grid_columnconfigure(0, weight=6, uniform="music_col") # Música
        self.results_header_labels.grid_columnconfigure(1, weight=4, uniform="music_col") # Artista
        self.results_header_labels.grid_columnconfigure(2, weight=3, uniform="music_col") # Álbum
        self.results_header_labels.grid_columnconfigure(3, weight=2, uniform="music_col") # Tempo
        self.results_header_labels.grid_columnconfigure(4, weight=1, minsize=80)           # Ações

        headers = ["MÚSICA", "ARTISTA", "ÁLBUM", "TEMPO", ""]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.results_header_labels, text=h, font=("Segoe UI", 11, "bold"), text_color="#555", anchor="w").grid(row=0, column=i, sticky="ew", padx=10)

        # Results scroll area
        self.results_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=30, pady=(2, 10))
        
        self.lbl_no_results = ctk.CTkLabel(self.results_frame, text="Digite algo ou selecione uma pasta para começar...", 
                                          font=("Segoe UI", 14), text_color="#555")
        self.lbl_no_results.pack(pady=50)

    def hide_autocomplete(self, event=None):
        if hasattr(self, 'autocomplete_frame') and self.autocomplete_frame.winfo_exists():
            self.autocomplete_frame.withdraw()

    def select_autocomplete(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.hide_autocomplete()
        self.perform_search()

    def show_autocomplete(self, query):
        sql = "SELECT DISTINCT artist FROM metadata_cache WHERE artist LIKE ? LIMIT 6"
        results = self.controller.db.query(sql, (f"%{query}%",))
        artists = [r['artist'] for r in results if r.get('artist')]
        
        if not artists:
            self.hide_autocomplete()
            return
            
        if not hasattr(self, 'autocomplete_frame') or not self.autocomplete_frame.winfo_exists():
            self.autocomplete_frame = ctk.CTkToplevel(self)
            self.autocomplete_frame.overrideredirect(True)
            self.autocomplete_frame.attributes("-topmost", True)
            self.autocomplete_frame.configure(fg_color="#1f1f1f")
            
        for widget in self.autocomplete_frame.winfo_children():
            widget.destroy()
            
        for artist in artists:
            btn = ctk.CTkButton(self.autocomplete_frame, text=artist, fg_color="transparent", 
                                hover_color="#c3000d", text_color="white", anchor="w",
                                command=lambda a=artist: self.select_autocomplete(a))
            btn.pack(fill="x", padx=2, pady=2)
            
        # Posição
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        
        self.autocomplete_frame.geometry(f"{width}x{len(artists)*35}+{x}+{y}")
        self.autocomplete_frame.deiconify()

    def on_search_type(self, event):
        if event.keysym in ('Return', 'Up', 'Down', 'Escape'): return
        query = self.entry.get().strip()
        if len(query) < 2:
            self.hide_autocomplete()
            return
            
        if hasattr(self, '_autocomplete_timer'):
            self.after_cancel(self._autocomplete_timer)
            
        self._autocomplete_timer = self.after(300, lambda: self.show_autocomplete(query))

    def perform_search(self):
        query = self.entry.get().strip()
        if not query: return
        
        # Clear results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self._image_refs = [] # Limpar referências de imagem
        self.row_widgets = {} # Rastrear widgets
            
        filter_type = self.filter_var.get()
        results = self.controller.db.search_musics(query, filter_type=filter_type, limit=100)
            
        self.current_results = results
        
        if not results:
            self.btn_play_all.pack_forget()
            ctk.CTkLabel(self.results_frame, text="Nenhum resultado encontrado.", font=("Segoe UI", 16)).pack(pady=50)
            return
            
        self.display_results(results)

    def create_music_row(self, m, playlist, index):
        path = m.get('file_path')
        row = ctk.CTkFrame(self.results_frame, fg_color="#1f1f1f", height=45, corner_radius=6)
        row.pack(fill="x", pady=2, padx=5)
        
        # Column weights for alignment
        row.grid_columnconfigure(0, weight=0, minsize=40) # #
        row.grid_columnconfigure(1, weight=6, uniform="music_col") # Música
        row.grid_columnconfigure(2, weight=4, uniform="music_col") # Artista
        row.grid_columnconfigure(3, weight=3, uniform="music_col") # Álbum
        row.grid_columnconfigure(4, weight=2, uniform="music_col") # Tempo
        row.grid_columnconfigure(5, weight=1, minsize=80)          # Ações
        
        lbl_num = ctk.CTkLabel(row, text=str(index), text_color="#555", width=30)
        lbl_num.grid(row=0, column=0, sticky="w")
        
        # Visualizador de Espectro
        visualizer = SpectrumVisualizer(row, width=25, height=20)
        visualizer.grid(row=0, column=0, sticky="w", padx=2)
        visualizer.grid_remove()
        
        title = str(m.get('title', 'Unknown'))
        artist = str(m.get('artist', 'Unknown'))
        album = str(m.get('album', 'Unknown'))
        dur_sec = m.get('duration', 0)
        
        def fmt(s):
            if not s: return "0:00"
            mm, ss = divmod(int(s), 60)
            return f"{mm}:{ss:02d}"

        # Info Técnica Formatada
        q_text = ""
        br = m.get('bitrate', 0)
        ext = m.get('ext', '')
        if br > 0:
            q_text = f" • {ext} ({br}k)" if ext else f" • {br}k"

        # Container para Título + Info Técnica
        title_container = ctk.CTkFrame(row, fg_color="transparent")
        title_container.grid(row=0, column=1, sticky="ew", padx=15, pady=8)
        
        # Mini Capa
        c_path = m.get('cover_path')
        cv_lbl = ctk.CTkLabel(title_container, text="💿", width=32, height=32, 
                                fg_color="#2a2a2a", corner_radius=4)
        cv_lbl.pack(side="left", padx=(0, 10))

        def load_row_img():
            try:
                resolved = self.controller.resolve_image_path(c_path)
                if not resolved: return
                cache_key = f"mini_{c_path}"
                if cache_key in self.controller.image_cache:
                    img_tk = self.controller.image_cache[cache_key]
                else:
                    from PIL import Image
                    p_img = Image.open(resolved).convert("RGB").resize((32, 32))
                    img_tk = ctk.CTkImage(p_img, size=(32, 32))
                    self.controller.image_cache[cache_key] = img_tk
                
                if cv_lbl.winfo_exists():
                    self.after(0, lambda: cv_lbl.configure(image=img_tk, text=""))
            except: pass

        import threading
        threading.Thread(target=load_row_img, daemon=True).start()

        lbl_t = ctk.CTkLabel(title_container, text=title, font=("Segoe UI", 13, "bold"), text_color="white", anchor="w")
        lbl_t.pack(side="left")
        
        if q_text:
            lbl_q = ctk.CTkLabel(title_container, text=q_text, font=("Segoe UI", 11), text_color="white", anchor="w")
            lbl_q.pack(side="left", padx=(5, 0))
        
        lbl_art = ctk.CTkLabel(row, text=artist, font=("Segoe UI", 12), text_color="#b3b3b3", anchor="w")
        lbl_art.grid(row=0, column=2, sticky="ew", padx=5)
        
        lbl_alb = ctk.CTkLabel(row, text=album, font=("Segoe UI", 11), text_color="#888", anchor="w")
        lbl_alb.grid(row=0, column=3, sticky="ew", padx=5)
        
        def fmt_ptr(s):
            m, s = divmod(int(s or 0), 60)
            return f"{m}:{s:02d}"

        dur_sec = m.get('duration', 0)
        is_p = path in self.controller.played_songs
        dur_text = fmt_ptr(dur_sec)
        if is_p: dur_text = "✅ " + dur_text
        
        lbl_dur = ctk.CTkLabel(row, text=dur_text, font=("Segoe UI", 11, "bold" if is_p else "normal"), 
                               text_color="white" if is_p else "#777", anchor="w")
        lbl_dur.grid(row=0, column=4, sticky="ew", padx=5)
        
        btn_play = ctk.CTkButton(row, text="▶", width=30, height=30, fg_color="transparent", 
                                hover_color="#333", command=lambda: self.controller.play_song(m, playlist))
        btn_play.grid(row=0, column=5, sticky="e", padx=15)
        
        # Guardar widgets
        self.row_widgets[path] = {
            'num_lbl': lbl_num,
            'visualizer': visualizer,
            'title_lbl': lbl_t,
            'dur_lbl': lbl_dur,
            'row_frame': row,
            'index': index
        }
        
        # Interactivity
        def on_enter(e, p=path, l_num=lbl_num):
            active = self.controller.current_song
            is_playing = active and active.get('file_path') == p
            if not is_playing:
                l_num.configure(text="▶", text_color="white")
            row.configure(fg_color="#2a2a2a")

        def on_leave(e, p=path, l_num=lbl_num, idx=index):
            active = self.controller.current_song
            is_playing = active and active.get('file_path') == p
            if is_playing:
                # O status será gerenciado pelo update_playing_status global
                pass
            else:
                l_num.configure(text=str(idx), text_color="#555")
            row.configure(fg_color="#1f1f1f")

        def on_click(e): self.controller.play_song(m, playlist)
        
        widgets_to_bind = [row, lbl_t, lbl_art, lbl_alb, lbl_dur, title_container, lbl_num]
        if q_text:
            widgets_to_bind.append(lbl_q)
            
        for widget in widgets_to_bind:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)
            widget.bind("<Button-3>", lambda e: self.show_context_menu(e, m))
            widget.configure(cursor="hand2")


    def play_all_results(self):
        if hasattr(self, 'current_results') and self.current_results:
            self.controller.play_song(self.current_results[0], self.current_results)


    def display_results(self, results):
        self.current_results = results
        # Clear previous
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self._image_refs = [] 
        self.row_widgets = {}
            
        if not results:
            self.btn_play_all.pack_forget()
            ctk.CTkLabel(self.results_frame, text="Nenhum resultado encontrado.", 
                         font=("Segoe UI", 14), text_color="#555").pack(pady=50)
            return
            
        # Update header or show count
        count = len(results)
        msg = f"Exibindo {count} resultados" + (" (limitado a 150)" if count >= 150 else "")
        ctk.CTkLabel(self.results_frame, text=msg, font=("Segoe UI", 11), text_color="#777").pack(pady=5)
        
        self.btn_play_all.pack(side="right", padx=10)
        
        for i, m in enumerate(results, 1):
            self.create_music_row(m, results, i)
            
        if hasattr(self.controller, 'current_song') and self.controller.current_song:
            self.update_playing_status(self.controller.current_song)

    def update_playing_status(self, current_song, is_playing=True):
        """Atualiza visualmente qual música está tocando na pesquisa"""
        if not hasattr(self, 'row_widgets'): return
        active_path = current_song.get('file_path') if current_song else None
        
        for path, widgets in self.row_widgets.items():
            try:
                visualizer = widgets.get('visualizer')
                # Update played status
                is_played = path in self.controller.played_songs
                dur_lbl = widgets.get('dur_lbl')
                if dur_lbl:
                    curr = dur_lbl.cget("text")
                    if is_played and not curr.startswith("✅"):
                        dur_lbl.configure(text="✅ " + curr, text_color="white", font=("Segoe UI", 11, "bold"))

                if path == active_path:
                    widgets['num_lbl'].grid_remove()
                    if visualizer:
                        visualizer.grid()
                        visualizer.update_playback_status(is_playing)
                    widgets['title_lbl'].configure(text_color="#1DB954")
                    self.after(100, lambda: self._scroll_to_active(widgets['row_frame']))
                else:
                    if visualizer:
                        visualizer.update_playback_status(False)
                        visualizer.grid_remove()
                    widgets['num_lbl'].grid()
                    widgets['num_lbl'].configure(text=str(widgets['index']), text_color="#555")
                    widgets['title_lbl'].configure(text_color="white")
            except: pass
            
        # Atualiza o visualizador SoundCloud se a música atual estiver nos resultados da busca
        if active_path:
            belongs_to_search = any(m.get('file_path') == active_path for m in self.current_results) if hasattr(self, 'current_results') else False
            if belongs_to_search:
                self.sc_visualizer.pack(fill="x", padx=30, pady=(0, 2), before=self.results_header_labels)
            else:
                self.sc_visualizer.pack_forget()
        else:
            self.sc_visualizer.pack_forget()

    def update_progress(self, current_pos, duration):
        """Atualiza o progresso no visualizador SoundCloud"""
        if hasattr(self, 'sc_visualizer') and duration > 0:
            progress = current_pos / duration
            self.sc_visualizer.set_progress(progress)

    def show_context_menu(self, event, track):
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#1a1a1a")
        menu.attributes("-topmost", True)
        
        def close(): menu.destroy()
        
        ctk.CTkLabel(menu, text="Opções", font=("Segoe UI", 11, "bold")).pack(pady=5, padx=10)
        ctk.CTkButton(menu, text="❤ Favoritar", fg_color="transparent", height=30, 
                      command=lambda: [self.controller.db.toggle_favorite(track['file_path']), close()]).pack(fill="x")
        
        ctk.CTkButton(menu, text="📝 Editar Tags", fg_color="transparent", height=30,
                      command=lambda: [self.controller.navigate_to("editor", track), close()]).pack(fill="x")
        
        ctk.CTkLabel(menu, text="Add à Playlist:", font=("Segoe UI", 10), text_color="#777").pack(pady=2)
        playlists = self.controller.db.get_playlists()
        for p in playlists[:4]:
            ctk.CTkButton(menu, text=p['name'], fg_color="transparent", height=24, anchor="w",
                          command=lambda pid=p['id']: [self.controller.db.add_to_playlist(pid, track['file_path']), close()]).pack(fill="x")
        
        menu.bind("<FocusOut>", lambda e: close())
        self.after(100, lambda: menu.focus_set())


    def _scroll_to_active(self, row_widget):
        """Ajusta o scroll para manter o widget da música visível"""
        try:
            self.update_idletasks()
            y_pos = row_widget.winfo_y()
            canvas = self.results_frame._parent_canvas
            total_h = canvas.bbox("all")[3]
            view_h = canvas.winfo_height()
            
            if total_h > view_h:
                target_fraction = max(0, (y_pos - (view_h / 2) + 30) / total_h)
                canvas.yview_moveto(target_fraction)
        except:
            pass
