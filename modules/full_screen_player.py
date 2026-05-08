import customtkinter as ctk
from PIL import Image, ImageOps
import os

class FullScreenPlayer(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#121212", corner_radius=0)
        self.controller = controller
        self._image_refs = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header (Top)
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header.pack(fill="x", padx=30, pady=(20, 10))
        
        self.btn_back = ctk.CTkButton(self.header, text="⌄", font=("Segoe UI", 35), width=40, height=40,
                                     fg_color="transparent", hover_color="#2a2a2a", text_color="white",
                                     command=self.hide)
        self.btn_back.pack(side="left")
        
        # Novo botão de opções (três pontos)
        self.btn_options = ctk.CTkButton(self.header, text="•••", font=("Segoe UI", 25), width=40, height=40,
                                        fg_color="transparent", hover_color="#2a2a2a", text_color="white",
                                        command=self.show_options_menu)
        self.btn_options.pack(side="right")
        
        title_container = ctk.CTkFrame(self.header, fg_color="transparent")
        title_container.pack(side="left", expand=True)
        
        ctk.CTkLabel(title_container, text="TOCANDO AGORA", font=("Segoe UI", 11, "bold"), 
                     text_color="#1DB954").pack()
        self.lbl_header_artist = ctk.CTkLabel(title_container, text="BeatSound", font=("Segoe UI", 10), 
                                              text_color="white")
        self.lbl_header_artist.pack()
        
        # Footer (Bottom) - Packed before content to stay at bottom
        self.footer = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.footer.pack(fill="x", side="bottom", pady=(0, 30))
        
        self.lbl_context = ctk.CTkLabel(self.footer, text="🎧 Ouvindo BeatSound", font=("Segoe UI", 12, "bold"),
                                       fg_color="#181818", corner_radius=15, padx=20, pady=6)
        self.lbl_context.pack()

        # Main Content Area (Center) - Packed after footer to fill middle
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(expand=True, fill="both", padx=50)
        
        # 1. Album Cover
        self.cover_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.cover_container.pack(pady=(10, 10))
        
        self.lbl_cover = ctk.CTkLabel(self.cover_container, text="", width=380, height=380, 
                                     fg_color="#1a1a1a", corner_radius=15)
        self.lbl_cover.pack()
        
        # 2. Track Info & Favorite
        self.info_row = ctk.CTkFrame(self.content, fg_color="transparent")
        self.info_row.pack(fill="x", pady=(10, 5))
        
        self.text_container = ctk.CTkFrame(self.info_row, fg_color="transparent")
        self.text_container.pack(side="left", fill="x", expand=True)
        
        self.lbl_title = ctk.CTkLabel(self.text_container, text="Título da Música", font=("Segoe UI", 28, "bold"),
                                     text_color="white", anchor="w")
        self.lbl_title.pack(fill="x")
        
        self.lbl_artist = ctk.CTkLabel(self.text_container, text="Artista", font=("Segoe UI", 18),
                                      text_color="#b3b3b3", anchor="w")
        self.lbl_artist.pack(fill="x")
        
        self.btn_fav = ctk.CTkButton(self.info_row, text="🤍", font=("Segoe UI", 30), width=40,
                                    fg_color="transparent", hover_color="#121212",
                                    command=self.controller.toggle_favorite_current)
        self.btn_fav.pack(side="right")
        
        # 3. Progress Bar
        self.progress_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.progress_container.pack(fill="x", pady=10)
        
        self.seeker = ctk.CTkSlider(self.progress_container, height=15, progress_color="#1DB954", 
                                    fg_color="#333333", button_color="#1DB954", button_hover_color="#1ed760",
                                    from_=0, to=100, command=self.controller.seek_song)
        self.seeker.pack(fill="x")
        
        time_f = ctk.CTkFrame(self.progress_container, fg_color="transparent")
        time_f.pack(fill="x", pady=2)
        
        self.lbl_current_time = ctk.CTkLabel(time_f, text="0:00", font=("Segoe UI", 12), text_color="#b3b3b3")
        self.lbl_current_time.pack(side="left")
        
        self.lbl_total_time = ctk.CTkLabel(time_f, text="0:00", font=("Segoe UI", 12), text_color="#b3b3b3")
        self.lbl_total_time.pack(side="right")
        
        # 4. Controls
        self.controls_f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.controls_f.pack(fill="x", pady=10)
        
        self.btn_shuffle = ctk.CTkButton(self.controls_f, text="🔀", font=("Segoe UI", 22), width=50,
                                        fg_color="transparent", hover_color="#2a2a2a", text_color="#b3b3b3",
                                        command=self.controller.toggle_shuffle)
        self.btn_shuffle.pack(side="left", expand=True)
        
        self.btn_prev = ctk.CTkButton(self.controls_f, text="⏮", font=("Segoe UI", 35), width=60,
                                     fg_color="transparent", hover_color="#2a2a2a", text_color="white",
                                     command=self.controller.play_prev)
        self.btn_prev.pack(side="left", expand=True)
        
        self.btn_play_pause = ctk.CTkButton(self.controls_f, text="▶", font=("Segoe UI", 40), width=80, height=80,
                                           corner_radius=40, fg_color="#1DB954", hover_color="#1ed760",
                                           text_color="black", command=self.controller.toggle_play_pause)
        self.btn_play_pause.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.controls_f, text="⏭", font=("Segoe UI", 35), width=60,
                                     fg_color="transparent", hover_color="#2a2a2a", text_color="white",
                                     command=self.controller.play_next)
        self.btn_next.pack(side="left", expand=True)
        
        self.btn_repeat = ctk.CTkButton(self.controls_f, text="🔁", font=("Segoe UI", 22), width=50,
                                       fg_color="transparent", hover_color="#2a2a2a", text_color="#b3b3b3",
                                       command=self.controller.toggle_repeat)
        self.btn_repeat.pack(side="left", expand=True)
        
    def update_track(self, track):
        if not track: return
        self.lbl_title.configure(text=track.get('title', 'Unknown'))
        self.lbl_artist.configure(text=track.get('artist', 'Unknown'))
        self.lbl_header_artist.configure(text=track.get('artist', 'BeatSound'))
        
        # Update Cover
        c_path = self.controller.resolve_image_path(track.get('cover_path'))
        img_tk = None
        if c_path and os.path.exists(c_path):
            try:
                p_img = Image.open(c_path).convert("RGB")
                size = (380, 380)
                p_img = ImageOps.fit(p_img, size, centering=(0.5, 0.5))
                img_tk = ctk.CTkImage(p_img, size=size)
                self._image_refs = [img_tk] 
            except: pass
        self.lbl_cover.configure(image=img_tk, text="" if img_tk else "🎵")
        
        # Sync states
        self.update_favorite_state(track.get('file_path') in self.controller.favorites)
        self.update_shuffle_state(self.controller.player.shuffle)
        self.update_repeat_state(self.controller.player.repeat_mode)
        
        # Update dynamic context
        self.update_context(self.controller.active_flow)
        
    def update_context(self, flow):
        """Atualiza o texto dinâmico sobre a origem da música"""
        if not flow:
            text = "🎧 Ouvindo BeatSound"
        elif flow == "Favoritos":
            text = "🎧 Ouvindo Favoritos"
        elif flow.lower().startswith("playlist"):
            # Ex: "Playlist Pop" -> "Ouvindo playlist Pop"
            name = flow.replace("Playlist", "").replace("playlist", "").strip()
            text = f"🎧 Ouvindo playlist {name}"
        elif flow in ["Sertanejo", "Pop", "Rock", "Lofi", "Phonk", "Samba"]:
            text = f"🎧 Ouvindo {flow}"
        elif flow == "Busca":
            text = "🎧 Ouvindo resultados da busca"
        else:
            # Caso para artistas específicos ou outros
            text = f"🎧 Ouvindo {flow}"
            
        self.lbl_context.configure(text=text)
        
    def update_play_state(self, is_playing):
        self.btn_play_pause.configure(text="⏸" if is_playing else "▶")
        
    def update_favorite_state(self, is_fav):
        self.btn_fav.configure(text="💚" if is_fav else "🤍", text_color="#1DB954" if is_fav else "white")
        
    def update_shuffle_state(self, is_active):
        self.btn_shuffle.configure(text_color="#1DB954" if is_active else "#b3b3b3")
        
    def update_repeat_state(self, mode):
        if mode == 1:
            self.btn_repeat.configure(text="🔂", text_color="#1DB954")
        elif mode == 2:
            self.btn_repeat.configure(text="🔁", text_color="#1DB954")
        else:
            self.btn_repeat.configure(text="🔁", text_color="#b3b3b3")

    def update_progress(self, current, total):
        if total > 0:
            self.seeker.set((current / total) * 100)
            self.lbl_current_time.configure(text=self.format_time(current))
            self.lbl_total_time.configure(text=self.format_time(total))
            
    def format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"
        
    def show(self):
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        if self.controller.current_song:
            self.update_track(self.controller.current_song)
            
    def show_options_menu(self):
        """Exibe o menu de opções (três pontos) no estilo moderno Spotify com drill-down"""
        if hasattr(self, 'menu_popup') and self.menu_popup.winfo_exists():
            self.close_menu()
            return

        # Frame do Menu - Agora posicionado sem overlay para não esconder o player
        self.menu_popup = ctk.CTkFrame(self, fg_color="#282828", corner_radius=12, 
                                      border_width=1, border_color="#3e3e3e", width=240)
        
        # Posicionamento no canto superior direito
        self.menu_popup.place(relx=0.97, rely=0.08, anchor="ne")
        
        # Bind global para detectar cliques fora do menu e fechá-lo
        self._click_id = self.winfo_toplevel().bind("<Button-1>", self._on_click_outside, add="+")
        
        self.render_main_menu()

    def _on_click_outside(self, event):
        """Fecha o menu se o usuário clicar em qualquer lugar fora dele ou do submenu"""
        if not hasattr(self, 'menu_popup') or not self.menu_popup.winfo_exists():
            return

        x, y = event.x_root, event.y_root
        
        # Verifica Menu Principal
        mx, my = self.menu_popup.winfo_rootx(), self.menu_popup.winfo_rooty()
        mw, mh = self.menu_popup.winfo_width(), self.menu_popup.winfo_height()
        in_main = (mx <= x <= mx + mw and my <= y <= my + mh)

        # Verifica Submenu (se existir)
        in_sub = False
        if hasattr(self, 'submenu_popup') and self.submenu_popup.winfo_exists():
            sx, sy = self.submenu_popup.winfo_rootx(), self.submenu_popup.winfo_rooty()
            sw, sh = self.submenu_popup.winfo_width(), self.submenu_popup.winfo_height()
            in_sub = (sx <= x <= sx + sw and sy <= y <= sy + sh)

        if not in_main and not in_sub:
            self.after(10, self.close_menu)

    def render_main_menu(self):
        """Renderiza as opções principais do menu"""
        for widget in self.menu_popup.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.menu_popup, text="OPÇÕES", font=("Segoe UI", 10, "bold"), 
                     text_color="#888").pack(pady=(10, 5), padx=15, anchor="w")

        # Botão Sobre o Artista
        ctk.CTkButton(self.menu_popup, text="👤 Sobre o artista", font=("Segoe UI", 13),
                     anchor="w", fg_color="transparent", hover_color="#3e3e3e",
                     height=40, corner_radius=8, command=self.on_artist_about).pack(fill="x", padx=8, pady=2)

        # Botão Playlists (com indicador de seta para fly-out)
        self.btn_pl_menu = ctk.CTkButton(self.menu_popup, text="🎶 Minhas playlist        ▶", font=("Segoe UI", 13),
                                       anchor="w", fg_color="transparent", hover_color="#3e3e3e",
                                       height=40, corner_radius=8, command=self.show_playlists_submenu)
        self.btn_pl_menu.pack(fill="x", padx=8, pady=2)

        # Botão Favoritos
        ctk.CTkButton(self.menu_popup, text="💚 Meus favoritos", font=("Segoe UI", 13),
                     anchor="w", fg_color="transparent", hover_color="#3e3e3e",
                     height=40, corner_radius=8, command=self.on_my_favorites).pack(fill="x", padx=8, pady=2)
            
        # Rodapé do menu para fechar
        ctk.CTkButton(self.menu_popup, text="Fechar", font=("Segoe UI", 11),
                      fg_color="transparent", hover_color="#3e3e3e", text_color="#888",
                      height=30, command=self.close_menu).pack(fill="x", padx=8, pady=(10, 8))

    def show_playlists_submenu(self):
        """Exibe o submenu de playlists lateralmente (estilo fly-out) à ESQUERDA"""
        if hasattr(self, 'submenu_popup') and self.submenu_popup.winfo_exists():
            self.submenu_popup.destroy()
            return

        # Cria o frame do submenu lateral
        self.submenu_popup = ctk.CTkFrame(self, fg_color="#282828", corner_radius=12, 
                                         border_width=1, border_color="#3e3e3e", width=200)
        
        # Posicionamento aproximado: À esquerda do menu principal.
        # Largura do menu principal é 240. Usamos -242 para ficar quase encostado (2px de gap).
        self.submenu_popup.place(relx=0.97, rely=0.14, anchor="ne", x=-242)

        playlists = self.controller.db.get_playlists()
        if playlists:
            # Container para as playlists com ícone igual à imagem 2
            for pl in playlists:
                btn = ctk.CTkButton(self.submenu_popup, text=f"♫ {pl['name']}", font=("Segoe UI", 12),
                                   anchor="w", fg_color="transparent", hover_color="#3e3e3e",
                                   height=35, corner_radius=6,
                                   command=lambda p=pl: [self.on_play_playlist(p), self.close_menu()])
                btn.pack(fill="x", padx=5, pady=2)
        else:
            ctk.CTkLabel(self.submenu_popup, text="Vazio", font=("Segoe UI", 11), 
                         text_color="#888").pack(pady=20)

    def close_menu(self):
        """Fecha todos os menus (principal e submenus) e limpa binds"""
        if hasattr(self, '_click_id'):
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._click_id)
            except: pass
            
        # Destrói submenu se existir
        if hasattr(self, 'submenu_popup'):
            if self.submenu_popup and self.submenu_popup.winfo_exists():
                self.submenu_popup.destroy()
            
        # Destrói menu principal
        if hasattr(self, 'menu_popup'):
            if self.menu_popup and self.menu_popup.winfo_exists():
                self.menu_popup.destroy()

    def on_artist_about(self):
        if self.controller.current_song:
            artist = self.controller.current_song.get('artist')
            if artist:
                self.close_menu() # Fecha o menu antes de navegar
                self.hide()
                self.controller.navigate_to("artist", artist)

    def on_play_playlist(self, pl_obj):
        """Reproduz uma playlist selecionada no menu"""
        tracks = []
        for path in pl_obj.get('songs', []):
            m = self.controller.db.find_by_path(path)
            if m: tracks.append(m)
            
        if tracks:
            self.controller.play_song(tracks[0], tracks, flow_type=f"Playlist {pl_obj['name']}")
        else:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "A playlist selecionada está vazia!")

    def on_my_favorites(self):
        """Reproduz os favoritos do usuário"""
        favs = self.controller.db.get_favorites()
        if favs:
            self.close_menu()
            self.controller.play_song(favs[0], favs, flow_type="Favoritos")
        else:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Você ainda não tem músicas favoritas!")

    def hide(self):
        self.place_forget()
