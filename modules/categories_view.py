import customtkinter as ctk
import threading
import os
from PIL import Image
from .spectrum_visualizer import SpectrumVisualizer

CARD_HEIGHT = 130  # Altura fixa de todos os cards
CARD_COLS   = 4    # Número de colunas no grid
CARD_PAD    = 10   # Espaçamento entre cards

# Paleta moderna de tons Escuros, Chumbo e Cinza
DARK_PALETTE = [
    "#121212", "#18181b", "#1a1a1a", "#1F1F1F",
    "#0f172a", "#1c1c1c", "#242424", "#09090b"
]


class CategoriesView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        
        # Estados
        self.current_folder = None
        self.new_only_var = ctk.BooleanVar(value=False)
        
        self._setup_ui()
        # DB query em background para transição instantânea
        threading.Thread(target=self._fetch_data, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  UI base (aparece imediatamente)                                     #
    # ------------------------------------------------------------------ #
    def _setup_ui(self):
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=30, pady=(2, 0))

        self.lbl_category_prefix = ctk.CTkLabel(self.header, text="EXPLORAR",
                     font=("Segoe UI", 12, "bold"),
                     text_color="#c3000d")
        self.lbl_category_prefix.pack(anchor="w")
        
        self.lbl_title = ctk.CTkLabel(self.header, text="Gênero Categoria",
                     font=("Segoe UI", 30, "bold"),
                     text_color="white")
        self.lbl_title.pack(anchor="w", pady=(0, 2))

        # Contêiner para botões extras (voltar, filtro)
        self.header_actions = ctk.CTkFrame(self.header, fg_color="transparent")
        self.header_actions.pack(fill="x", pady=0)
        
        self.btn_back = ctk.CTkButton(self.header_actions, text="← Voltar para Categorias", 
                                      fg_color="transparent", text_color="#c3000d",
                                      hover_color="#1a1a1a", border_width=1, border_color="#c3000d",
                                      command=self._hide_folder_detail)
        # Começa oculto
        self.btn_back.pack_forget()

        self.sw_new = ctk.CTkSwitch(self.header_actions, text="Novidades de Hoje", 
                                    progress_color="#c3000d",
                                    variable=self.new_only_var,
                                    command=lambda: self._show_folder(self.current_folder))
        # Começa oculto
        self.sw_new.pack_forget()

        self.scroll_area = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        self.scroll_area.pack(fill="both", expand=True, padx=20, pady=0)

        # Spinner — visível até os cards chegarem
        self._spinner = ctk.CTkLabel(
            self.scroll_area,
            text="Carregando categorias...",
            font=("Segoe UI", 15),
            text_color="#888888")
        self._spinner.pack(pady=100)

    # ------------------------------------------------------------------ #
    #  Dados em background                                                 #
    # ------------------------------------------------------------------ #
    def _fetch_data(self, refresh=False):
        try:
            if not refresh and hasattr(self, '_categories_cache') and self._categories_cache:
                self.after(0, self._render_cards, self._categories_cache)
                return

            music_dir = ""
            if hasattr(self.controller, "config_manager"):
                music_dir = self.controller.config_manager.get("music_dir")

            if not music_dir:
                self.after(0, self._show_empty, "Diretório de músicas não configurado.")
                return

            folders = self.controller.db.get_top_level_folders(music_dir)

            if not folders:
                self.after(0, self._show_empty, "Nenhuma pasta encontrada.")
                return

            folders.sort(key=lambda x: str(x.get("genre", "")).lower())
            self._categories_cache = folders
            self.after(0, self._render_cards, folders)

        except Exception as e:
            print(f"[CategoriesView] Erro: {e}")
            self.after(0, self._show_empty, "Erro ao carregar categorias.")

    def _show_empty(self, msg):
        if self._spinner.winfo_exists():
            self._spinner.destroy()
        ctk.CTkLabel(self.scroll_area, text=msg,
                     font=("Segoe UI", 14), text_color="#888888").pack(pady=100)

    # ------------------------------------------------------------------ #
    #  Renderização estável (todos de uma vez na UI thread)                #
    # ------------------------------------------------------------------ #
    def _render_cards(self, folders):
        if not self.winfo_exists():
            return

        # Remove spinner
        if hasattr(self, "_spinner") and self._spinner.winfo_exists():
            self._spinner.destroy()

        # Limpa o grid se já existir (para quando for um refresh)
        for w in self.scroll_area.winfo_children():
            w.destroy()

        # Container externo com grid fixo
        grid = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 8))

        # Configura colunas com peso uniforme
        for c in range(CARD_COLS):
            grid.grid_columnconfigure(c, weight=1, uniform="col", pad=0)

        # Renderização em lotes (2ms entre cada card para manter fluidez)
        def render_batch(idx):
            if not grid.winfo_exists(): return
            if not self.winfo_exists() or idx >= len(folders):
                return

            # Renderizar um lote maior (ex: 20 cards por vez) para ser mais rápido
            for _ in range(20):
                if idx >= len(folders): break
                folder = folders[idx]
                name  = str(folder.get("genre", "")).title()
                display_name = name if len(name) <= 22 else name[:20] + "…"
                path  = folder.get("path", "")
                count = folder.get("count", 0)
                # Seleciona uma cor de fundo sutil da nossa paleta de tons escuros
                color = DARK_PALETTE[idx % len(DARK_PALETTE)]

                row = idx // CARD_COLS
                col = idx % CARD_COLS
                
                # Altura de linha fixa
                grid.grid_rowconfigure(row, minsize=CARD_HEIGHT + CARD_PAD * 2)
                self._make_card(grid, display_name, path, count, color, row, col)
                idx += 1
            
            # Agenda próximo lote com delay mínimo
            self.after(2, lambda: render_batch(idx))

        render_batch(0)

    def load_musics(self):
        """Método de compatibilidade para refresh via controller"""
        threading.Thread(target=lambda: self._fetch_data(refresh=True), daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Criação de um card individual                                        #
    # ------------------------------------------------------------------ #
    def _make_card(self, parent, name, path, count, bg_color, row, col):
        # Frame externo no grid
        outer = ctk.CTkFrame(parent, fg_color="transparent")
        outer.grid(row=row, column=col, sticky="nsew", padx=CARD_PAD, pady=CARD_PAD)
        outer.grid_propagate(False)
        outer.configure(width=280, height=CARD_HEIGHT) 

        # --- Interações ---
        def on_enter(e):
            try:
                card.configure(border_color="#c3000d", border_width=2)
                play_btn.place(relx=0.88, rely=0.8, anchor="center")
            except: pass

        def on_leave(e):
            try:
                card.configure(border_color="#333", border_width=1)
                play_btn.place_forget()
            except: pass

        def on_click(e, p=path):
            self._show_folder(p)

        # Card Moderno
        card = ctk.CTkFrame(outer, width=280, height=CARD_HEIGHT, fg_color=bg_color, corner_radius=12,
                            border_width=1, border_color="#333")
        card.pack(fill="both", expand=True)

        # Marca d'água sutil (Decoração musical)
        deco = ctk.CTkLabel(card, text="♫",
                            font=("Segoe UI", 80, "bold"),
                            text_color="#222",
                            anchor="center")
        deco.place(relx=0.9, rely=0.6, anchor="center")

        # Texto
        txt = ctk.CTkFrame(card, fg_color="transparent")
        txt.place(x=15, y=15, relwidth=0.7)

        lbl_name = ctk.CTkLabel(
            txt, text=name,
            font=("Segoe UI", 17, "bold"),
            text_color="white",
            anchor="w", justify="left")
        lbl_name.pack(anchor="w")

        # Badge de contagem
        badge_frame = ctk.CTkFrame(txt, fg_color="#2a2a2a", corner_radius=6)
        badge_frame.pack(anchor="w", pady=(8, 0))
        
        lbl_count = ctk.CTkLabel(
            badge_frame, text=f"{count} músicas",
            font=("Segoe UI", 10, "bold"),
            text_color="#888",
            padx=8, pady=2)
        lbl_count.pack()

        # Botão play moderno
        play_btn = ctk.CTkButton(
            card, text="▶",
            width=42, height=42, corner_radius=21,
            fg_color="#c3000d", hover_color="#e6000f",
            text_color="white", font=("Segoe UI", 16, "bold"),
            command=lambda p=path: self._play_folder(p))
        play_btn.place_forget()
        
        # Binds para o efeito de hover e clique
        for w in [card, txt, lbl_name, lbl_count, deco, badge_frame]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            w.configure(cursor="hand2")

        play_btn.bind("<Enter>", on_enter)
        play_btn.bind("<Leave>", on_leave)

    # ------------------------------------------------------------------ #
    #  Ações                                                               #
    # ------------------------------------------------------------------ #
    def _show_folder(self, folder_path):
        """Exibe as músicas da pasta selecionada dentro da própria aba de categorias."""
        self.current_folder = folder_path
        self.current_page = 1
        self.items_per_page = 30
        self.total_pages = 1
        
        # UI: Atualizar cabeçalho
        folder_name = os.path.basename(folder_path).title()
        self.lbl_title.configure(text=folder_name)
        self.lbl_category_prefix.configure(text="CATEGORIA")
        self.btn_back.pack(side="left", padx=(0, 20))
        self.sw_new.pack(side="left")
        
        self._load_folder_page()

    def _load_folder_page(self):
        # Limpar área de scroll
        for w in self.scroll_area.winfo_children():
            w.destroy()
            
        # Resetar scroll para o topo (corrige o bug de lista invisível até o scroll manual)
        try:
            self.scroll_area._parent_canvas.yview_moveto(0)
        except:
            pass

        # Spinner de carregamento de músicas
        self._spinner = ctk.CTkLabel(self.scroll_area, text="Carregando músicas...", font=("Segoe UI", 15), text_color="#888")
        self._spinner.pack(pady=80)
        self.update_idletasks()
        
        # Buscar músicas
        def _fetch():
            only_new = self.new_only_var.get()
            total = self.controller.db.get_filtered_count(query="", filter_path=self.current_folder, only_new=only_new)
            self.total_pages = max(1, (total + self.items_per_page - 1) // self.items_per_page)
            
            offset = (self.current_page - 1) * self.items_per_page
            musics = self.controller.db.get_musics_by_path(self.current_folder, limit=self.items_per_page, offset=offset, only_new=only_new)
            
            # Se only_new estiver ativado, ordenar para que as mais recentes fiquem em primeiro
            # (O banco já ordena por updated_at DESC, mas garantimos aqui se necessário)
            
            if self.winfo_exists():
                self.after(0, lambda: self._render_musics(musics))
                
        threading.Thread(target=_fetch, daemon=True).start()

    def _hide_folder_detail(self):
        """Volta para a lista de categorias."""
        self.current_folder = None
        self.new_only_var.set(False)
        self.lbl_title.configure(text="Gênero Categoria")
        self.lbl_category_prefix.configure(text="EXPLORAR")
        self.btn_back.pack_forget()
        self.sw_new.pack_forget()
        
        # Voltar para a lista de categorias usando o cache se disponível
        if hasattr(self, '_categories_cache') and self._categories_cache:
            self._render_cards(self._categories_cache)
        else:
            self.load_musics()

    def _render_musics(self, musics):
        if not self.winfo_exists(): return
        if self._spinner.winfo_exists(): self._spinner.destroy()
        
        if not musics:
            ctk.CTkLabel(self.scroll_area, text="Nenhuma música encontrada nesta aba/página.", 
                         font=("Segoe UI", 16)).pack(pady=100)
            self._render_pagination()
            return

        self.row_widgets = {} # Rastrear widgets
        
        # Header da Lista
        header_row = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        header_row.pack(fill="x", padx=15, pady=(0, 5))
        self.update_idletasks()
        header_row.grid_columnconfigure(0, weight=0, minsize=40)
        header_row.grid_columnconfigure(1, weight=6, uniform="music_col")
        header_row.grid_columnconfigure(2, weight=4, uniform="music_col")
        header_row.grid_columnconfigure(3, weight=2, uniform="music_col")
        
        for i, text in enumerate(["#", "TÍTULO", "ARTISTA", "TEMPO"]):
            ctk.CTkLabel(header_row, text=text, font=("Segoe UI", 11, "bold"), text_color="#555", anchor="w").grid(row=0, column=i, sticky="ew", padx=10)

        # Músicas (renderizadas em lotes maiores para não congelar UI mas carregar rápido)
        def render_batch(start_idx):
            if not self.winfo_exists(): return
            
            # Aumentado para 25 por lote para parecer mais instantâneo
            end_idx = min(start_idx + 25, len(musics))
            for i in range(start_idx, end_idx):
                m_data = musics[i]
                offset = (self.current_page - 1) * self.items_per_page
                self._create_music_row(m_data, i + 1 + offset, musics)
            
            if end_idx < len(musics):
                self.after(2, lambda: render_batch(end_idx))
            else:
                self._render_pagination()
                # Forçar atualização da região de scroll
                self.scroll_area._parent_canvas.yview_moveto(0)
                self.update_idletasks()
                if hasattr(self.controller, 'current_song') and self.controller.current_song:
                    self.update_playing_status(self.controller.current_song)

        render_batch(0)

    def _create_music_row(self, m, index, playlist):
        path = m.get('file_path')
        row = ctk.CTkFrame(self.scroll_area, fg_color="#1f1f1f" if index%2==0 else "#191919", height=45, corner_radius=6)
        row.pack(fill="x", pady=1, padx=10)
        
        row.grid_columnconfigure(0, weight=0, minsize=40) # #
        row.grid_columnconfigure(1, weight=6, uniform="music_col") # Título
        row.grid_columnconfigure(2, weight=4, uniform="music_col") # Artista
        row.grid_columnconfigure(3, weight=2, uniform="music_col") # Tempo
        
        lbl_num = ctk.CTkLabel(row, text=str(index), text_color="#555", width=30)
        lbl_num.grid(row=0, column=0, sticky="w")
        
        # Visualizador de Espectro
        visualizer = SpectrumVisualizer(row, width=25, height=20)
        visualizer.grid(row=0, column=0, sticky="w", padx=2)
        visualizer.grid_remove()
        
        title = m.get('title', 'Unknown')
        artist = m.get('artist', 'Unknown')
        dur = m.get('duration', 0)
        
        title_container = ctk.CTkFrame(row, fg_color="transparent")
        title_container.grid(row=0, column=1, sticky="ew", padx=15, pady=8)
        
        # Mini Capa
        c_path = m.get('cover_path')
        cv_lbl = ctk.CTkLabel(title_container, text="💿", width=32, height=32, fg_color="#2a2a2a", corner_radius=4)
        cv_lbl.pack(side="left", padx=(0, 10))
        
        if c_path and os.path.exists(c_path):
            def load():
                try:
                    p_img = Image.open(c_path).convert("RGB").resize((32, 32))
                    img_tk = ctk.CTkImage(p_img, size=(32, 32))
                    
                    # Store reference to prevent garbage collection
                    if path in self.row_widgets:
                        self.row_widgets[path]['img_ref'] = img_tk

                    if cv_lbl.winfo_exists():
                        self.after(0, lambda: cv_lbl.configure(image=img_tk, text=""))
                except: pass
            threading.Thread(target=load, daemon=True).start()

        lbl_t = ctk.CTkLabel(title_container, text=title, font=("Segoe UI", 13, "bold"), text_color="white", anchor="w")
        lbl_t.pack(side="left")
        
        # Add quality text (MP3 128k) in white
        q_text = ""
        try:
            br = int(m.get('bitrate') or 0)
            ext = str(m.get('ext') or '').upper()
            if not ext:
                path = m.get('file_path', '')
                ext = os.path.splitext(path)[1][1:].upper()
            if br > 0: q_text = f" • {ext} ({br}k)" if ext else f" • {br}k"
        except: pass
        if q_text:
            lbl_q = ctk.CTkLabel(title_container, text=q_text, font=("Segoe UI", 11), text_color="white", anchor="w")
            lbl_q.pack(side="left", padx=(5, 0))

        
        lbl_art = ctk.CTkLabel(row, text=artist, font=("Segoe UI", 12), text_color="#b3b3b3", anchor="w")
        lbl_art.grid(row=0, column=2, sticky="ew", padx=5)
        
        mm, ss = divmod(int(dur or 0), 60)
        is_p = path in self.controller.played_songs
        dur_text = f"{mm}:{ss:02d}"
        if is_p: dur_text = "✅ " + dur_text
        
        lbl_dur = ctk.CTkLabel(row, text=dur_text, font=("Segoe UI", 11, "bold" if is_p else "normal"), 
                               text_color="white" if is_p else "#777", anchor="w")
        lbl_dur.grid(row=0, column=3, sticky="ew", padx=5)
        
        self.row_widgets[path] = {
            'num_lbl': lbl_num,
            'visualizer': visualizer,
            'title_lbl': lbl_t,
            'dur_lbl': lbl_dur,
            'row_frame': row,
            'index': index
        }
        
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
            row.configure(fg_color="#1f1f1f" if index%2==0 else "#191919")

        def on_play(e=None):
            def _launch():
                only_new = self.new_only_var.get()
                full_musics = self.controller.db.get_musics_by_path(self.current_folder, limit=5000, offset=0, only_new=only_new)
                self.after(0, lambda: self.controller.play_song(m, full_musics))
            threading.Thread(target=_launch, daemon=True).start()

        for w in [row, lbl_t, lbl_art, lbl_dur, title_container, lbl_num]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_play)
            w.bind("<Button-3>", lambda e: self.show_context_menu(e, m))
            w.configure(cursor="hand2")



    def show_context_menu(self, event, track):
        """Menu de contexto moderno"""
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#1a1a1a")
        menu.attributes("-topmost", True)
        
        def close(): menu.destroy()
        
        header_lbl = ctk.CTkLabel(menu, text="Opções da Música", font=("Segoe UI", 11, "bold"), text_color="#777")
        header_lbl.pack(pady=(8, 2), padx=20)
        
        ctk.CTkFrame(menu, height=1, fg_color="#333").pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(menu, text="📝 Editar Tags (Metadados)", fg_color="transparent", height=35, anchor="w",
                      hover_color="#333", command=lambda: [self.controller.navigate_to("editor", track), close()]).pack(fill="x", padx=5)
        
        ctk.CTkButton(menu, text="❤ Favoritar", fg_color="transparent", height=35, anchor="w",
                      hover_color="#333", command=lambda: [self.controller.db.toggle_favorite(track['file_path']), close()]).pack(fill="x", padx=5)
        
        ctk.CTkLabel(menu, text="Adicionar à Playlist:", font=("Segoe UI", 10), text_color="#555").pack(pady=(8, 2), padx=20, anchor="w")
        playlists = self.controller.db.get_playlists()
        for p in playlists[:6]:
            ctk.CTkButton(menu, text=f"  + {p['name']}", fg_color="transparent", height=28, anchor="w", font=("Segoe UI", 11),
                          hover_color="#2b2b2b",
                          command=lambda pid=p['id']: [self.controller.db.add_to_playlist(pid, track['file_path']), close()]).pack(fill="x", padx=5)

        menu.bind("<FocusOut>", lambda e: close())
        self.after(100, lambda: menu.focus_set())

    def _play_folder(self, folder_path):
        """Toca a primeira música da pasta."""
        musics = self.controller.db.get_musics_by_path(folder_path, limit=200)
        if musics:
            self.controller.play_song(musics[0], musics)

    def shuffle_all(self):
        """Novo aleatório que percorre todas as páginas dentro do card (categoria)"""
        if hasattr(self, 'current_folder') and self.current_folder:
            import random
            # Pega as primeiras 1000 músicas da pasta (limite razoável para shuffle)
            all_tracks = self.controller.db.get_musics_by_path(self.current_folder, limit=1000)
            if all_tracks:
                shuffled = all_tracks[:]
                random.shuffle(shuffled)
                self.controller.play_song(shuffled[0], shuffled)
        elif hasattr(self, 'current_musics') and self.current_musics:
            # Fallback para o comportamento anterior caso não tenha a pasta
            import random
            shuffled = self.current_musics[:]
            random.shuffle(shuffled)
            self.controller.play_song(shuffled[0], shuffled)

    def _render_pagination(self):
        if hasattr(self, 'pagination_container') and self.pagination_container.winfo_exists():
            self.pagination_container.destroy()
            
        if getattr(self, 'total_pages', 1) <= 1:
            return
            
        self.pagination_container = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.pagination_container.pack(pady=20)
        
        btn_first = ctk.CTkButton(self.pagination_container, text="⏪ Primeira", width=90, height=32, 
                                fg_color="#333", hover_color="#444", 
                                command=lambda: self._change_page(1))
        btn_first.pack(side="left", padx=5)
        
        btn_prev = ctk.CTkButton(self.pagination_container, text="← Anterior", width=90, height=32, 
                                 fg_color="#333", hover_color="#444", 
                                 command=lambda: self._change_page(self.current_page - 1))
        btn_prev.pack(side="left", padx=5)
        
        lbl_page = ctk.CTkLabel(self.pagination_container, text=f"Página {self.current_page} de {self.total_pages}", 
                                font=("Segoe UI", 13, "bold"), text_color="white")
        lbl_page.pack(side="left", padx=15)
        
        btn_next = ctk.CTkButton(self.pagination_container, text="Próxima →", width=90, height=32, 
                                 fg_color="#333", hover_color="#444", 
                                 command=lambda: self._change_page(self.current_page + 1))
        btn_next.pack(side="left", padx=5)
        
        if self.current_page <= 1:
            btn_first.configure(state="disabled", text_color="#666")
            btn_prev.configure(state="disabled", text_color="#666")
        if self.current_page >= getattr(self, 'total_pages', 1):
            btn_next.configure(state="disabled", text_color="#666")

    def update_playing_status(self, current_song, is_playing=True):
        """Atualiza visualmente qual música está tocando na categoria"""
        if not hasattr(self, 'row_widgets'): return
        raw_path = current_song.get('file_path') if current_song else None
        if not raw_path: return
        
        # Normalização de caminho para comparação Windows segura
        active_path = raw_path.replace("\\", "/").lower()
        
        # Auto-navegação para a página do item se a música tocar fora da página atual
        if active_path and hasattr(self, 'current_folder') and self.current_folder:
            # Normalizar chaves dos widgets atuais para o check
            existing_paths = [p.replace("\\", "/").lower() for p in self.row_widgets.keys()]
            
            if active_path not in existing_paths:
                _folder = self.current_folder
                _only_new = self.new_only_var.get() if hasattr(self, 'new_only_var') else False
                _items_per_page = self.items_per_page
                _current_page = getattr(self, 'current_page', 1)
                
                def _auto_nav():
                    try:
                        all_tracks = self.controller.db.get_musics_by_path(_folder, limit=5000, only_new=_only_new)
                        # Normalizar toda a lista de caminhos para a busca
                        paths = [m.get('file_path', '').replace("\\", "/").lower() for m in all_tracks]
                        if active_path in paths:
                            idx = paths.index(active_path)
                            target_page = (idx // _items_per_page) + 1
                            
                            new_total = (len(paths) + _items_per_page - 1) // _items_per_page
                            
                            if target_page != _current_page:
                                def do_jump():
                                    self.total_pages = max(getattr(self, 'total_pages', 1), new_total)
                                    self._change_page(target_page)
                                self.after(10, do_jump)
                    except Exception as e:
                        print(f"[CategoriesView] Erro no auto_nav: {e}")
                
                import threading
                threading.Thread(target=_auto_nav, daemon=True).start()

        for widget_path, widgets in self.row_widgets.items():
            try:
                visualizer = widgets.get('visualizer')
                is_this_active = (widget_path.replace("\\", "/").lower() == active_path)
                
                # Checkmark status
                is_p_song = widget_path in self.controller.played_songs or widget_path.replace("\\", "/").lower() in [p.replace("\\", "/").lower() for p in self.controller.played_songs]
                dur_lbl = widgets.get('dur_lbl')
                if dur_lbl:
                    curr = dur_lbl.cget("text")
                    if is_p_song and not curr.startswith("✅"):
                        dur_lbl.configure(text="✅ " + curr, text_color="white", font=("Segoe UI", 11, "bold"))

                if is_this_active:
                    widgets['num_lbl'].grid_remove()
                    if visualizer:
                        visualizer.grid()
                        visualizer.update_playback_status(is_playing)
                    widgets['title_lbl'].configure(text_color="#1DB954")
                    
                    # Auto-scroll para manter a música na visão do usuário
                    self.after(100, lambda: self._scroll_to_active(widgets['row_frame']))
                else:
                    if visualizer:
                        visualizer.update_playback_status(False)
                        visualizer.grid_remove()
                    widgets['num_lbl'].grid()
                    widgets['num_lbl'].configure(text=str(widgets['index']), text_color="#555")
                    widgets['title_lbl'].configure(text_color="white")
            except: pass
            
    def _change_page(self, page):
        if 1 <= page <= getattr(self, 'total_pages', 1):
            self.current_page = page
            self._load_folder_page()

    def _scroll_to_active(self, row_widget):
        """Ajusta o scroll para manter o widget da música visível"""
        try:
            # Forçar atualização de geometria para pegar o y correto
            self.update_idletasks()
            
            y_pos = row_widget.winfo_y()
            canvas = self.scroll_area._parent_canvas
            
            # Altura total do conteúdo rolável
            total_h = canvas.bbox("all")[3]
            # Altura da janela visível
            view_h = canvas.winfo_height()
            
            if total_h > view_h:
                # Centralizar o item ou pelo menos trazê-lo para a visão
                # Calculamos a fração (0.0 a 1.0)
                # Subtraímos metade da visão para tentar centralizar
                target_fraction = max(0, (y_pos - (view_h / 2) + 30) / total_h)
                canvas.yview_moveto(target_fraction)
        except:
            pass
