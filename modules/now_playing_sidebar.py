import customtkinter as ctk
from PIL import Image, ImageOps, ImageDraw
import os
import threading

class NowPlayingSidebar(ctk.CTkFrame):
    def __init__(self, parent, controller):
        # Increased width to 500 for a more robust sidebar expansion
        super().__init__(parent, fg_color="#121212", width=500, corner_radius=0)
        self.controller = controller
        self.is_expanded = False
        self._image_refs = []
        self.current_width = 500
        
        # Fundamental for sidebar: don't let children shrink the width
        self.pack_propagate(False)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        
        self.title_lbl = ctk.CTkLabel(self.header, text="Tocando Agora", font=("Segoe UI", 16, "bold"), text_color="white")
        self.title_lbl.pack(side="left")
        
        btns_f = ctk.CTkFrame(self.header, fg_color="transparent")
        btns_f.pack(side="right")
        
        # User requested to hide the close button ">"
        # self.btn_close = ctk.CTkButton(btns_f, text=">", width=32, height=32, corner_radius=16,
        #                                fg_color="transparent", hover_color="#2a2a2a",
        #                                text_color="#1DB954", font=("Segoe UI", 24, "bold"),
        #                                command=self.toggle)
        # self.btn_close.pack(side="right")
        
        # Scrollable area
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll.pack(fill="both", expand=True)
        
        # Container for content
        self.content_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True)
        
        self.empty_lbl = ctk.CTkLabel(self.content_container, text="Selecione uma música\npara ver os detalhes", 
                                      text_color="#555", font=("Segoe UI", 14))
        self.empty_lbl.pack(pady=150)
        
    def update_track(self, track):
        if not track: return
        
        for w in self.content_container.winfo_children():
            w.destroy()
        self._image_refs = []
        
        # Content spacing
        margin = 30
        available_width = self.current_width - (margin * 2) - 30 # Account for scrollbar space
        if available_width < 100: available_width = 440 # Safety fallback
        
        # 1. Main Cover (Ensuring it's fully visible and not clipped)
        c_path = self.controller.resolve_image_path(track.get('cover_path'))
        img_tk = None
        if c_path and os.path.exists(c_path):
            try:
                p_img = Image.open(c_path).convert("RGB")
                size = (available_width, available_width)
                p_img = ImageOps.fit(p_img, size, centering=(0.5, 0.5))
                img_tk = ctk.CTkImage(p_img, size=size)
                self._image_refs.append(img_tk)
            except: pass
            
        cover_lbl = ctk.CTkLabel(self.content_container, text="" if img_tk else "🎵", image=img_tk, 
                                 width=available_width, height=available_width, corner_radius=12, fg_color="#1a1a1a")
        cover_lbl.pack(pady=(0, 20), padx=margin)
        
        # 2. Track Title and Artist
        info_f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        info_f.pack(fill="x", padx=margin)
        
        title_text = track.get('title', 'Unknown')
        title_font_size = 24 if len(title_text) < 20 else (20 if len(title_text) < 40 else 18)
        
        t_lbl = ctk.CTkLabel(info_f, text=title_text, font=("Segoe UI", title_font_size, "bold"), 
                             text_color="white", anchor="w", wraplength=available_width, justify="left")
        t_lbl.pack(fill="x")
        
        artist_text = track.get('artist', 'Unknown')
        a_lbl = ctk.CTkLabel(info_f, text=artist_text, font=("Segoe UI", 17), 
                             text_color="#b3b3b3", anchor="w", cursor="hand2")
        a_lbl.pack(fill="x", pady=(5, 0))
        a_lbl.bind("<Button-1>", lambda e: self.controller.navigate_to("artist", artist_text))
        
        # 3. About Artist Section
        self.render_about_box(artist_text, available_width)
        
        # 3.1 About Label Section (PONTO)
        # 3.1 About Label Section (PONTO)
        label_text = track.get('label')
        if not label_text:
            try:
                sql = "SELECT label FROM metadata_cache WHERE file_path = ?"
                with self.controller.db.get_connection() as conn:
                    row = conn.execute(sql, (track.get('file_path'),)).fetchone()
                    if row and row[0]: label_text = row[0]
            except: pass
            
        # Chamamos sempre, o render_label_box vai decidir se mostra ou busca
        self.render_label_box(label_text, available_width, artist_text, title_text)
        
        # 4. Discography
        self.render_discography(artist_text, available_width)

    def render_about_box(self, artist_name, width):
        ctk.CTkLabel(self.content_container, text="Sobre o artista", font=("Segoe UI", 18, "bold"), 
                     text_color="white", anchor="w").pack(fill="x", padx=30, pady=(30, 10))
                     
        box = ctk.CTkFrame(self.content_container, fg_color="#1e1e1e", corner_radius=15)
        box.pack(fill="x", padx=30, pady=5)
        
        header_f = ctk.CTkFrame(box, fg_color="transparent")
        header_f.pack(fill="x", padx=15, pady=15)
        
        # Removing gray background: fg_color="transparent" as requested
        self.artist_photo = ctk.CTkLabel(header_f, text="🎤", font=("Segoe UI", 20), width=50, height=50, 
                                    fg_color="transparent", corner_radius=25)
        self.artist_photo.pack(side="left")
        
        ctk.CTkLabel(header_f, text=artist_name, font=("Segoe UI", 15, "bold"), text_color="white").pack(side="left", padx=15)
        
        bio_lbl = ctk.CTkLabel(box, text="Buscando informações...", font=("Segoe UI", 13), 
                               text_color="#b3b3b3", anchor="w", justify="left", wraplength=width-50)
        bio_lbl.pack(fill="x", padx=20, pady=(0, 25))
        
        def fetch_info():
            try:
                if hasattr(self.controller, 'api_enhancer'):
                    # Mudamos para get_artist_complete_info para trazer a BIO e usar o CACHE do banco
                    info = self.controller.api_enhancer.get_artist_complete_info(artist_name)
                    bio = info.get('bio', "Não há informações biográficas no momento.")
                    if bio and len(bio) > 1000: bio = bio[:1000] + "..."
                    
                    if bio_lbl.winfo_exists():
                        self.after(0, lambda: bio_lbl.configure(text=bio if bio else "Não há informações biográficas no momento."))
                    
                    # No get_artist_complete_info, a foto vem na chave 'cover' ou 'artist_photo_url'
                    photo_url = info.get('artist_photo_url') or info.get('cover')
                    if photo_url:
                        import requests
                        from io import BytesIO
                        # Adicionamos User-Agent para evitar bloqueio de algumas APIs
                        headers = {'User-Agent': 'MusicBeatSearchApp/2.0'}
                        resp = requests.get(photo_url, timeout=5, headers=headers)
                        if resp.status_code == 200:
                            p_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                            size = (120, 120) if self.current_width > 400 else (50, 50)
                            p_img = ImageOps.fit(p_img, size, centering=(0.5, 0.5))
                            mask = Image.new('L', size, 0)
                            draw = ImageDraw.Draw(mask)
                            draw.ellipse((0, 0) + size, fill=255)
                            p_img.putalpha(mask)
                            tk_p = ctk.CTkImage(p_img, size=size)
                            self._image_refs.append(tk_p)
                            if self.artist_photo.winfo_exists():
                                self.after(0, lambda: self.artist_photo.configure(image=tk_p, text="", width=size[0], height=size[1]))
            except Exception as e:
                print(f"[Sidebar] Erro ao buscar info do artista: {e}")
                    
        threading.Thread(target=fetch_info, daemon=True).start()

    def render_label_box(self, label_name, width, artist_name=None, track_title=None):
        # Se não temos nem o nome nem os dados para buscar, não mostra nada
        if not label_name and (not artist_name or not track_title): return

        # Container principal da seção (label "Gravadora" + box)
        self.label_section = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.label_section.pack(fill="x")

        ctk.CTkLabel(self.label_section, text="Gravadora", font=("Segoe UI", 18, "bold"), 
                     text_color="white", anchor="w").pack(fill="x", padx=30, pady=(30, 10))
                     
        box = ctk.CTkFrame(self.label_section, fg_color="#1a1a1a", corner_radius=15, border_width=1, border_color="#333")
        box.pack(fill="x", padx=30, pady=5)
        
        header_f = ctk.CTkFrame(box, fg_color="transparent")
        header_f.pack(fill="x", padx=15, pady=15)
        
        label_logo = ctk.CTkLabel(header_f, text="💿", font=("Segoe UI", 20), width=50, height=50, 
                                     fg_color="#222", corner_radius=8)
        label_logo.pack(side="left")
        
        name_lbl = ctk.CTkLabel(header_f, text=label_name if label_name else "Identificando...", 
                                font=("Segoe UI", 14, "bold"), text_color="#1DB954")
        name_lbl.pack(side="left", padx=15)
        
        prof_lbl = ctk.CTkLabel(box, text="Buscando história da gravadora...", font=("Segoe UI", 12), 
                                 text_color="#888", anchor="w", justify="left", wraplength=width-60)
        prof_lbl.pack(fill="x", padx=20, pady=(0, 20))
        
        def fetch_label():
            try:
                if hasattr(self.controller, 'api_enhancer'):
                    info = self.controller.api_enhancer.get_label_complete_info(label_name, artist=artist_name, title=track_title)
                    
                    if not info or not info.get('name'):
                        # Se não encontrou nada, remove a seção inteira da UI
                        if self.label_section.winfo_exists():
                            self.after(0, self.label_section.destroy)
                        return

                    profile = info.get('profile', "História da gravadora não disponível.")
                    if profile and len(profile) > 500: profile = profile[:500] + "..."
                    
                    if prof_lbl.winfo_exists():
                        self.after(0, lambda: prof_lbl.configure(text=profile if profile else "História da gravadora não disponível."))
                    if name_lbl.winfo_exists():
                        self.after(0, lambda: name_lbl.configure(text=info.get('name')))
                    
                    logo_url = info.get('logo_url')
                    if logo_url:
                        import requests
                        from io import BytesIO
                        headers = {'User-Agent': 'MusicBeatSearchApp/2.0'}
                        resp = requests.get(logo_url, timeout=5, headers=headers)
                        if resp.status_code == 200:
                            p_img = Image.open(BytesIO(resp.content)).convert("RGBA")
                            size = (50, 50)
                            p_img = p_img.resize(size, Image.Resampling.LANCZOS)
                            tk_p = ctk.CTkImage(p_img, size=size)
                            self._image_refs.append(tk_p)
                            if label_logo.winfo_exists():
                                self.after(0, lambda: label_logo.configure(image=tk_p, text=""))
            except Exception as e:
                print(f"[Sidebar] Erro ao buscar label: {e}")
                if self.label_section.winfo_exists():
                    self.after(0, self.label_section.destroy)
                    
        threading.Thread(target=fetch_label, daemon=True).start()

    def render_discography(self, artist_name, width):
        ctk.CTkLabel(self.content_container, text="Populares deste artista", font=("Segoe UI", 18, "bold"), 
                     text_color="white", anchor="w").pack(fill="x", padx=30, pady=(30, 10))
        
        songs = self.controller.db.search_by_artist(artist_name, limit=10)
        if not songs: return
        
        for s in songs:
            row = ctk.CTkFrame(self.content_container, fg_color="transparent", height=64, cursor="hand2")
            row.pack(fill="x", pady=4, padx=15)
            
            s_c_path = self.controller.resolve_image_path(s.get('cover_path'))
            s_img = None
            if s_c_path and os.path.exists(s_c_path):
                try:
                    p = Image.open(s_c_path).convert("RGB").resize((48, 48))
                    s_img = ctk.CTkImage(p, size=(48, 48))
                    self._image_refs.append(s_img)
                except: pass
                
            # Check if played
            is_p = s.get('file_path') in self.controller.played_songs
            
            # Removing gray background: fg_color="transparent"
            ctk.CTkLabel(row, text="" if s_img else "🎵", image=s_img, width=48, height=48, corner_radius=6, fg_color="transparent").pack(side="left", padx=15)
            
            txt_f = ctk.CTkFrame(row, fg_color="transparent")
            txt_f.pack(side="left", fill="both", expand=True)
            
            title = s.get('title', 'Unknown')
            if is_p: title = "✅ " + title
            
            ctk.CTkLabel(txt_f, text=title[:35] + ("..." if len(title)>35 else ""), font=("Segoe UI", 14, "bold"), 
                         text_color="#1DB954" if is_p else "white", anchor="w").pack(fill="x", pady=(10,0))
            ctk.CTkLabel(txt_f, text=artist_name[:40], font=("Segoe UI", 12), text_color="#b3b3b3", anchor="w").pack(fill="x")
            
            def play(e, track=s): self.controller.play_song(track, songs)
            row.bind("<Button-1>", play)
            for w in row.winfo_children(): 
                if isinstance(w, ctk.CTkFrame):
                    for cw in w.winfo_children(): cw.bind("<Button-1>", play)
                w.bind("<Button-1>", play)
            
            def on_e(e, r=row): r.configure(fg_color="#2a2a2a")
            def on_l(e, r=row): r.configure(fg_color="transparent")
            row.bind("<Enter>", on_e)
            row.bind("<Leave>", on_l)

    def toggle(self):
        if self.is_expanded:
            self.pack_forget()
            self.is_expanded = False
            if hasattr(self.controller, 'btn_sidebar'):
                self.controller.btn_sidebar.configure(text_color="#555")
            if hasattr(self.controller, 'sidebar_handle'):
                self.controller.sidebar_handle.configure(text="<")
                self.controller.sidebar_handle.place(relx=0.99, rely=0.4, anchor="center")
        else:
            # Explicitly force width using configurations
            self.configure(width=500)
            self.pack(side="right", fill="both", expand=False)
            self.is_expanded = True
            
            if hasattr(self.controller, 'btn_sidebar'):
                self.controller.btn_sidebar.configure(text_color="#c3000d")
            
            if hasattr(self.controller, 'sidebar_handle'):
                self.controller.sidebar_handle.configure(text=">")
                # Adjust handle position for 500px width
                self.controller.sidebar_handle.place(relx=0.64, rely=0.4, anchor="center")
            
            if self.controller.current_song:
                self.update_track(self.controller.current_song)
