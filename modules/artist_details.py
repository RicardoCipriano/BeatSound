import customtkinter as ctk
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps
from .multi_api_enhancer import MultiAPIEnhancer
from .spectrum_visualizer import SpectrumVisualizer, SoundCloudVisualizer
import threading

class ArtistDetails(ctk.CTkFrame):
    def __init__(self, parent, controller, artist_name=None):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        self.artist_name = artist_name if artist_name else "Bicep"
        self.enhancer = MultiAPIEnhancer(database=self.controller.db)
        
        self._image_refs = []
        self.disco_expanded = False
        self.songs_expanded = False
        self.current_filter = "album" # album ou single
        self.online_data = {}
        self.local_songs = []
        
        # Navigation
        self.setup_header_controls()
        
        # Body Scrollable
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)
        
        # Carregamento inicial
        self.local_songs = self.controller.db.search_by_artist(self.artist_name)
        self._render_initial_ui()
        self.start_async_loading()

    def setup_header_controls(self):
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.place(relx=0, rely=0, relwidth=1, y=20, anchor="nw")
        self.nav_frame.lift()
        self.back_btn = ctk.CTkButton(self.nav_frame, text="<", width=35, height=35, corner_radius=20,
                                     fg_color="#000000", hover_color="#333", text_color="white",
                                     command=lambda: self.controller.navigate_to("home"))
        self.back_btn.pack(side="left", padx=30)

    def _render_initial_ui(self):
        for widget in self.body.winfo_children():
            widget.destroy()

        # 1. HEADER com Degradê
        self.header_frame = ctk.CTkFrame(self.body, height=400, fg_color="#121212", corner_radius=0)
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)
        
        # Canvas para o Degradê
        self.bg_canvas = ctk.CTkCanvas(self.header_frame, highlightthickness=0, bg="#121212")
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.header_content = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_content.pack(side="bottom", fill="x", padx=30, pady=40)
        
        # Foto Redonda
        self.profile_lbl = ctk.CTkLabel(self.header_content, text="", width=230, height=230, fg_color="transparent")
        self.profile_lbl.pack(side="left", padx=(0, 25))
        
        self.artist_title = ctk.CTkLabel(self.header_content, text=self.artist_name, font=("Segoe UI", 82, "bold"), text_color="white")
        self.artist_title.pack(side="left", anchor="s")

        # 2. ACTION BAR
        action_bar = ctk.CTkFrame(self.body, fg_color="transparent")
        action_bar.pack(fill="x", padx=30, pady=25)

        ctk.CTkButton(action_bar, text="▶", width=56, height=56, corner_radius=28,
                     fg_color="#1DB954", hover_color="#1ed760", text_color="black",
                     font=("Segoe UI", 24, "bold"),
                     command=lambda: self.play_artist_all(self.local_songs)).pack(side="left")

        # Contador de músicas encontradas em verde
        song_count = len(self.local_songs)
        count_text = f"🎵  Músicas encontradas: {song_count}"
        ctk.CTkLabel(action_bar, text=count_text,
                     font=("Segoe UI", 14, "bold"),
                     text_color="#1DB954").pack(side="left", padx=20)

        # 3. POPULARES (Com Botão Mostrar Tudo)
        pop_header = ctk.CTkFrame(self.body, fg_color="transparent")
        pop_header.pack(fill="x", padx=30, pady=(20, 10))
        ctk.CTkLabel(pop_header, text="Populares", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")

        self.songs_toggle_btn = ctk.CTkButton(pop_header, text="Mostrar tudo", text_color="#b3b3b3",
                                             fg_color="transparent", hover_color="#121212", font=("Segoe UI", 12, "bold"),
                                             command=self.toggle_songs)
        self.songs_toggle_btn.pack(side="right")

        # Visualizador de Espectro SoundCloud (Fixo entre Header e Lista)
        self.sc_visualizer = SoundCloudVisualizer(self.body, height=80, progress_color="#ff5500", bar_color="#444")
        self.sc_visualizer.pack(fill="x", padx=30, pady=(10, 20))
        # Ocultar inicialmente, mostrar apenas se o artista atual for o que está tocando
        self.sc_visualizer.pack_forget()

        self.songs_list_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self.songs_list_frame.pack(fill="x", padx=15)
        self._draw_songs_list()

        # Container para discografia/bio vindos da web
        self.extra_container = ctk.CTkFrame(self.body, fg_color="transparent")
        self.extra_container.pack(fill="x")

    def _apply_gradient(self, color_rgb):
        """Preenche o cabeçalho com fundo sólido preto conforme solicitado"""
        try:
            self.bg_canvas.delete("grad")
            w = self.header_frame.winfo_width()
            if w < 10: w = 1200
            # Preenche com preto sólido
            self.bg_canvas.configure(bg="#121212")
            self.bg_canvas.create_rectangle(0, 0, w, 400, fill="#121212", outline="", tags="grad")
        except:
            pass

    def toggle_songs(self):
        self.songs_expanded = not self.songs_expanded
        self.songs_toggle_btn.configure(text="Mostrar menos" if self.songs_expanded else "Mostrar tudo")
        self._draw_songs_list()

    def _draw_songs_list(self):
        for widget in self.songs_list_frame.winfo_children():
            widget.destroy()
        
        self.row_widgets = {} # Rastrear widgets
        
        limit = len(self.local_songs) if self.songs_expanded else 5
        for i, song in enumerate(self.local_songs[:limit], 1):
            self._create_song_row(song, i, self.local_songs, self.songs_list_frame)
            
        if self.songs_expanded and len(self.local_songs) > 5:
            btn_less = ctk.CTkButton(self.songs_list_frame, text="Recolher lista", text_color="#b3b3b3", 
                                     fg_color="transparent", hover_color="#1a1a1a", width=140, 
                                     height=35, font=("Segoe UI", 12, "bold"), command=self.toggle_songs)
            btn_less.pack(pady=20)
        
        # Sincroniza status inicial se houver música tocando
        if hasattr(self.controller, 'current_song') and self.controller.current_song:
            self.update_playing_status(self.controller.current_song)

    def start_async_loading(self):
        threading.Thread(target=self._fetch_data_worker, daemon=True).start()

    def _fetch_data_worker(self):
        try:
            # Limpar dados antigos ANTES de buscar novos (Evita misturar artistas)
            self.online_data = {}
            self._image_refs = []
            
            data = self.enhancer.get_artist_complete_info(self.artist_name)
            self.online_data = data
            self.after(0, self._update_ui_with_online_data)
        except Exception as e:
            print(f"[UI] Erro no worker de carregamento: {e}")

    def _update_ui_with_online_data(self):
        if not self.online_data or not hasattr(self, 'extra_container'): return
        
        for widget in self.extra_container.winfo_children():
            widget.destroy()
            
        # Pega a cor predominante e aplica o degradê destacado
        rgb = self._get_dominant_color(self.online_data.get('cover'))
        self.after(50, lambda: self._apply_gradient(rgb))
        
        # Foto Principal (Grande e Redonda)
        prof = self._get_circular_image(self.online_data.get('cover'), (230, 230))
        self._image_refs.append(prof)
        self.profile_lbl.configure(image=prof)

        for widget in self.extra_container.winfo_children():
            widget.destroy()

        self._render_discography_section()
        self._render_about_section()

    def _render_discography_section(self):
        disco_data = self.online_data.get('discography', [])
        if not disco_data: return

        self.disco_header = ctk.CTkFrame(self.extra_container, fg_color="transparent")
        self.disco_header.pack(fill="x", padx=30, pady=(40, 5))
        ctk.CTkLabel(self.disco_header, text="Discografia", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
        
        self.disco_toggle_btn = ctk.CTkButton(self.disco_header, text="Mostrar tudo", text_color="#b3b3b3", 
                                             fg_color="transparent", hover_color="#121212", font=("Segoe UI", 12, "bold"),
                                             command=self.toggle_discography)
        self.disco_toggle_btn.pack(side="right")
        
        self.tabs_frame = ctk.CTkFrame(self.extra_container, fg_color="transparent")
        self.tabs_frame.pack(fill="x", padx=30, pady=10)
        
        self.btn_pop = self._create_filter_button(self.tabs_frame, "Lançamentos populares", "album")
        self.btn_singles = self._create_filter_button(self.tabs_frame, "Singles e EPs", "single")
        
        self.disco_grid = ctk.CTkFrame(self.extra_container, fg_color="transparent")
        self.disco_grid.pack(fill="x", padx=20, pady=10)
        self._draw_album_cards()

    def _create_filter_button(self, parent, text, type_filter):
        is_active = self.current_filter == type_filter
        btn = ctk.CTkButton(parent, text=text, corner_radius=16, 
                           fg_color="white" if is_active else "#2a2a2a",
                           text_color="black" if is_active else "white",
                           font=("Segoe UI", 12, "bold"), height=32,
                           command=lambda: self.change_filter(type_filter))
        btn.pack(side="left", padx=(0, 10))
        return btn

    def change_filter(self, new_filter):
        self.current_filter = new_filter
        self._draw_album_cards()
        # Atualizar cores dos botões
        self.btn_pop.configure(fg_color="white" if new_filter=="album" else "#2a2a2a", text_color="black" if new_filter=="album" else "white")
        self.btn_singles.configure(fg_color="white" if new_filter=="single" else "#2a2a2a", text_color="black" if new_filter=="single" else "white")

    def toggle_discography(self):
        self.disco_expanded = not self.disco_expanded
        self.disco_toggle_btn.configure(text="Mostrar menos" if self.disco_expanded else "Mostrar tudo")
        self._draw_album_cards()

    def _draw_album_cards(self):
        for widget in self.disco_grid.winfo_children():
            widget.destroy()
            
        all_disco = self.online_data.get('discography', [])
        filtered = [a for a in all_disco if self.current_filter.lower() in a.get('type', 'album').lower()]
        
        if not filtered and self.current_filter == "album": filtered = all_disco[:10]
        
        limit = len(filtered) if self.disco_expanded else 6
        
        if self.disco_expanded:
            # Grid Vertical
            for i, album in enumerate(filtered[:limit]):
                self._create_album_card(album, self.disco_grid, grid_pos=(i//4, i%4))
            
            # Botão recolher no final
            if len(filtered) > 6:
                btn_less = ctk.CTkButton(self.disco_grid, text="Recolher discografia", text_color="#b3b3b3", 
                                         fg_color="transparent", hover_color="#1a1a1a", width=140, 
                                         height=35, font=("Segoe UI", 12, "bold"), command=self.toggle_discography)
                btn_less.grid(row=(len(filtered)//4)+1, column=0, columnspan=4, pady=25)
        else:
            # Scroll Horizontal
            scroll = ctk.CTkScrollableFrame(self.disco_grid, fg_color="transparent", orientation="horizontal", height=280)
            scroll.pack(fill="x")
            for album in filtered[:6]:
                self._create_album_card(album, scroll)

    def _create_album_card(self, album, parent, grid_pos=None):
        card = ctk.CTkFrame(parent, fg_color="transparent", width=180, height=260, cursor="hand2")
        if grid_pos: card.grid(row=grid_pos[0], column=grid_pos[1], padx=10, pady=10)
        else: card.pack(side="left", padx=10)
        card.pack_propagate(False)
        
        card.bind("<Enter>", lambda e: card.configure(fg_color="#181818"))
        card.bind("<Leave>", lambda e: card.configure(fg_color="transparent"))
        
        # Album Cover
        cv_l = ctk.CTkLabel(card, text="💿", width=160, height=160, fg_color="#181818", corner_radius=8)
        cv_l.pack(pady=(5, 10))
        
        cover_url = album.get('cover')
        if cover_url:
            def load():
                try:
                    # Discogs e Spotify exigem User-Agent para imagens
                    headers = {'User-Agent': 'MusicBeatSearchApp/2.0'}
                    r = requests.get(cover_url, timeout=10, headers=headers)
                    if r.status_code == 200:
                        pi = Image.open(BytesIO(r.content)).convert("RGB").resize((160, 160))
                        tk = ctk.CTkImage(pi, size=(160, 160))
                        self._image_refs.append(tk)
                        self.after(0, lambda: cv_l.configure(image=tk, text=""))
                except Exception as e:
                    print(f"[UI] Erro ao carregar capa: {e}")
            threading.Thread(target=load, daemon=True).start()
        
        ctk.CTkLabel(card, text=album.get('name', '')[:22], font=("Segoe UI", 14, "bold"), text_color="white", wraplength=160, justify="left").pack(anchor="w", padx=10)
        year_str = album.get('year', 'N/A')
        ctk.CTkLabel(card, text=f"{year_str} • {album.get('type','Álbum')}", font=("Segoe UI", 12), text_color="#b3b3b3").pack(anchor="w", padx=10)

    def _render_about_section(self):
        ctk.CTkLabel(self.extra_container, text="Sobre", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=30, pady=(40, 15))
        about_box = ctk.CTkFrame(self.extra_container, fg_color="#242424", corner_radius=12)
        about_box.pack(fill="x", padx=30, pady=(0, 100))
        inner = ctk.CTkFrame(about_box, fg_color="transparent")
        inner.pack(fill="x", padx=30, pady=30)
        
        bio = self.online_data.get('bio', "Sem biografia disponível no momento.")
        # Bio já vem limpa do enhancer, mas garantimos aqui também
        if bio:
            bio = bio.split("Read more")[0].split("Discography:")[0].strip()
        
        ctk.CTkLabel(inner, text=bio, font=("Segoe UI", 15), text_color="#b3b3b3", 
                     wraplength=650, justify="left", anchor="nw").pack(side="left", padx=(0, 30))
        
        stats = ctk.CTkFrame(inner, fg_color="transparent")
        stats.pack(side="right", anchor="ne")
        circ = self._get_circular_image(self.online_data.get('cover'), (150, 150))
        self._image_refs.append(circ)
        ctk.CTkLabel(stats, text="", image=circ).pack()
        ctk.CTkLabel(stats, text=f"{self.online_data.get('followers', 0):,} ouvintes".replace(",", "."), 
                     font=("Segoe UI", 14, "bold"), text_color="white").pack(pady=10)

    def _create_song_row(self, song, index, playlist, parent):
        path = song.get('file_path')
        row = ctk.CTkFrame(parent, fg_color="transparent", height=56, cursor="hand2")
        row.pack(fill="x", pady=1)
        
        row.grid_columnconfigure(0, weight=0, minsize=45)
        row.grid_columnconfigure(1, weight=0)
        row.grid_columnconfigure(2, weight=1)
        row.grid_columnconfigure(3, weight=0)

        lbl_num = ctk.CTkLabel(row, text=str(index), width=35, font=("Segoe UI", 14), text_color="#b3b3b3")
        lbl_num.grid(row=0, column=0, sticky="w", padx=5)
        
        # Visualizador de Espectro
        visualizer = SpectrumVisualizer(row, width=25, height=20)
        visualizer.grid(row=0, column=0, sticky="w", padx=8)
        visualizer.grid_remove()
        
        c_path = song.get('cover_path')
        img_tk = None
        if c_path:
            try:
                p_img = Image.open(c_path).convert("RGB").resize((40, 40))
                img_tk = ctk.CTkImage(p_img, size=(40, 40))
                self._image_refs.append(img_tk)
            except: pass
        
        cv_lbl = ctk.CTkLabel(row, text="" if img_tk else "💿", image=img_tk, width=40, height=40)
        cv_lbl.grid(row=0, column=1, sticky="w")
        
        lbl_t = ctk.CTkLabel(row, text=song.get('title', 'Unknown'), font=("Segoe UI", 14, "bold"), text_color="white")
        lbl_t.grid(row=0, column=2, sticky="w", padx=15)
        
        dur_sec = int(song.get('duration', 0) or 0)
        mm, ss = divmod(dur_sec, 60)
        dur_text = f"{mm}:{ss:02d}"
        is_p = path in self.controller.played_songs
        if is_p: dur_text = "✅ " + dur_text
        
        lbl_d = ctk.CTkLabel(row, text=dur_text, font=("Segoe UI", 14, "bold" if is_p else "normal"), 
                             text_color="#1DB954" if is_p else "#b3b3b3")
        lbl_d.grid(row=0, column=3, sticky="e", padx=30)
        
        # Guardar widgets para atualização
        self.row_widgets[path] = {
            'num_lbl': lbl_num,
            'visualizer': visualizer,
            'title_lbl': lbl_t,
            'dur_lbl': lbl_d,
            'row_frame': row,
            'index': index
        }

        # Hover logic
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
                pass
            else:
                l_num.configure(text=str(idx), text_color="#b3b3b3")
            row.configure(fg_color="transparent")

        for w in [row, cv_lbl, lbl_t, lbl_num]:
            w.bind("<Button-1>", lambda e: self.controller.play_song(song, playlist))
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def update_playing_status(self, current_song, is_playing=True):
        """Atualiza visualmente qual música está tocando na lista do artista"""
        if not hasattr(self, 'row_widgets'): return
        active_path = current_song.get('file_path') if current_song else None
        
        for path, widgets in self.row_widgets.items():
            try:
                visualizer = widgets.get('visualizer')
                # Update played status
                is_played_song = path in self.controller.played_songs
                dur_lbl = widgets.get('dur_lbl')
                if dur_lbl:
                    curr = dur_lbl.cget("text")
                    if is_played_song and not curr.startswith("✅"):
                        dur_lbl.configure(text="✅ " + curr, text_color="#1DB954", font=("Segoe UI", 14, "bold"))

                if path == active_path:
                    widgets['num_lbl'].grid_remove()
                    if visualizer:
                        visualizer.grid()
                        visualizer.update_playback_status(is_playing)
                    widgets['title_lbl'].configure(text_color="#1DB954")
                else:
                    if visualizer:
                        visualizer.update_playback_status(False)
                        visualizer.grid_remove()
                    widgets['num_lbl'].grid()
                    widgets['num_lbl'].configure(text=str(widgets['index']), text_color="#b3b3b3")
                    widgets['title_lbl'].configure(text_color="white")
            except: pass
        
        # Atualiza o visualizador grande se a música for desse artista
        if active_path:
            # Verifica se a música atual pertence a este artista
            belongs_to_artist = any(s.get('file_path') == active_path for s in self.local_songs)
            if belongs_to_artist:
                self.sc_visualizer.pack(fill="x", padx=30, pady=(10, 20), before=self.songs_list_frame)
            else:
                self.sc_visualizer.pack_forget()
        else:
            self.sc_visualizer.pack_forget()

    def update_progress(self, current_pos, duration):
        """Atualiza o progresso no visualizador SoundCloud"""
        if duration > 0:
            progress = current_pos / duration
            self.sc_visualizer.set_progress(progress)

    def _get_dominant_color(self, url):
        """Extrai a cor predominante da imagem (RGB)"""
        if not url: return (30, 30, 30)
        try:
            r = requests.get(url, timeout=3)
            img = Image.open(BytesIO(r.content)).convert("RGB").resize((1, 1))
            return img.getpixel((0, 0))
        except: return (30, 30, 30)

    def _get_circular_image(self, url, size):
        try:
            if url:
                r = requests.get(url, timeout=5)
                pi = Image.open(BytesIO(r.content)).convert("RGBA")
            else:
                pi = Image.new('RGBA', size, (40, 40, 40, 255))
            mask = Image.new('L', size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0) + size, fill=255)
            pi = ImageOps.fit(pi, size)
            pi.putalpha(mask)
            return ctk.CTkImage(pi, size=size)
        except:
            return ctk.CTkImage(Image.new('RGBA', size, (30,30,30,255)), size=size)

    def play_artist_all(self, playlist):
        if playlist: self.controller.play_song(playlist[0], playlist)
