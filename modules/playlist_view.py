import customtkinter as ctk
import os
from .spectrum_visualizer import SpectrumVisualizer

class PlaylistView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        
        # Left mini-sidebar (PLAYLISTS)
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color="#1a1a1a", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        self.sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.sidebar_scroll.pack(fill="both", expand=True)
        
        self.load_sidebar()
        
        ctk.CTkButton(self.sidebar, text="+ Nova Playlist", fg_color="#c3000d", text_color="white", hover_color="#9a000a",
                      command=self.create_playlist_prompt).pack(side="bottom", fill="x", padx=20, pady=20)

        # Main Area
        self.main = ctk.CTkFrame(self, fg_color="#121212", corner_radius=0)
        self.main.pack(side="right", fill="both", expand=True)
        
        # 1. HEADER (Design Sólido)
        from .ui_utils import UIUtils
        self.header = ctk.CTkFrame(self.main, height=250, fg_color="#121212", corner_radius=0)
        self.header.pack(side="top", fill="x")
        
        self.lbl_playlist_cover = ctk.CTkLabel(self.header, width=150, height=150, fg_color="#333", corner_radius=8, text="🎵")
        self.lbl_playlist_cover.pack(side="left", padx=30, pady=30)
        
        header_info = ctk.CTkFrame(self.header, fg_color="transparent")
        header_info.pack(side="left", pady=30, padx=(0, 30), fill="both", expand=True)
        
        self.lbl_playlist_type = ctk.CTkLabel(header_info, text="PLAYLIST", font=("Segoe UI", 12, "bold"), text_color="white")
        self.lbl_playlist_type.pack(anchor="w")
        
        self.lbl_playlist_name = ctk.CTkLabel(header_info, text="SELECIONE UMA PLAYLIST", font=("Segoe UI", 48, "bold"), text_color="white")
        self.lbl_playlist_name.pack(anchor="w", pady=(5, 10))
        
        self.lbl_playlist_stats = ctk.CTkLabel(header_info, text="0 músicas, 0 min", font=("Segoe UI", 14), text_color="#ccc")
        self.lbl_playlist_stats.pack(anchor="w", pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(header_info, fg_color="transparent")
        btn_frame.pack(anchor="w")
        ctk.CTkButton(btn_frame, text="TOCAR TUDO", width=120, fg_color="#c3000d", hover_color="#9a000a", command=self.play_playlist).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="EMBARALHAR", width=120, fg_color="transparent", border_width=1, border_color="white", command=self.shuffle_playlist).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="EXPORTAR", width=120, fg_color="transparent", border_width=1, border_color="white", command=self.export_playlist).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="EDITAR", width=120, fg_color="transparent", border_width=1, border_color="white", command=self.edit_playlist).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="EXCLUIR", width=120, fg_color="transparent", border_width=1, border_color="#c3000d", text_color="#c3000d", command=self.delete_playlist_ui).pack(side="left", padx=10)
        
        # Table Items
        self.table = ctk.CTkScrollableFrame(self.main, fg_color="#121212")
        self.table.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Load initial
        playlists = self.controller.db.get_playlists()
        if playlists:
            self.load_playlist(playlists[0])
        else:
            self.lbl_playlist_name.configure(text="NENHUMA PLAYLIST")

    def load_sidebar(self):
        for widget in self.sidebar_scroll.winfo_children():
            widget.destroy()
            
        ctk.CTkLabel(self.sidebar_scroll, text="PLAYLISTS", font=("Segoe UI", 12, "bold"), text_color="#b3b3b3").pack(anchor="w", padx=20, pady=20)
        
        playlists = self.controller.db.get_playlists()
        
        for p in playlists:
            icon = "🎵"
            n_low = p['name'].lower()
            if 'favorito' in n_low or 'favorite' in n_low: icon = "❤"
            elif 'electronic' in n_low: icon = "⚡"
            elif 'rock' in n_low: icon = "🎸"
            elif 'black' in n_low: icon = "🎶" 
            elif 'taste' in n_low: icon = "🔥"
            elif 'teste' in n_low: icon = "🛠"
            if 'black taste' in n_low: icon = "🎤"
            
            btn = ctk.CTkButton(self.sidebar_scroll, text=f"{icon} {p['name']}", anchor="w", fg_color="transparent", 
                                text_color="white", hover_color="#2b2b2b",
                                command=lambda pl=p: self.load_playlist(pl))
            btn.pack(fill="x", padx=10, pady=2)
            if hasattr(self, 'current_playlist') and self.current_playlist and self.current_playlist['id'] == p['id']:
                btn.configure(fg_color="#c3000d", hover_color="#9a000a")
        
    def create_playlist_prompt(self):
        dialog = ctk.CTkInputDialog(text="Digite o nome da nova playlist:", title="Nova Playlist")
        name = dialog.get_input()
        if name:
            pl_id = self.controller.db.create_playlist(name)
            if pl_id == -1:
                from tkinter import messagebox
                messagebox.showerror("Erro", "Já existe uma playlist com esse nome!")
            elif pl_id:
                self.load_sidebar()
                playlists = self.controller.db.get_playlists()
                new_pl = next((p for p in playlists if p['id'] == pl_id), None)
                if new_pl: self.load_playlist(new_pl)
            else:
                from tkinter import messagebox
                messagebox.showerror("Erro", "Não foi possível criar a playlist.")

    def load_playlist(self, playlist_obj):
        from .ui_utils import UIUtils
        self.current_playlist = playlist_obj
        pl_name = playlist_obj['name']
        self.lbl_playlist_name.configure(text=pl_name.upper())
        self.load_sidebar() # Update selection highlight

        # Atualizar Cores (Estilo Sólido solicitado)
        self.lbl_playlist_cover.configure(fg_color="#2a2a2a") # Fundo neutro para a capa

        for widget in self.table.winfo_children():
            widget.destroy()
            
        h_row = ctk.CTkFrame(self.table, fg_color="transparent")
        h_row.pack(fill="x", pady=(0, 10), padx=5)
        h_row.grid_columnconfigure(0, weight=0, minsize=40) # #
        h_row.grid_columnconfigure(1, weight=0, minsize=50) # Capa
        h_row.grid_columnconfigure(2, weight=6, uniform="music_col") # Título
        h_row.grid_columnconfigure(3, weight=4, uniform="music_col") # Artista
        h_row.grid_columnconfigure(4, weight=2, uniform="music_col") # Tempo
        h_row.grid_columnconfigure(5, weight=1, minsize=80)           # Ações

        ctk.CTkLabel(h_row, text="#", text_color="#555", font=("Segoe UI", 11, "bold"), width=30).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(h_row, text="", width=40).grid(row=0, column=1)
        ctk.CTkLabel(h_row, text="TÍTULO", text_color="#555", font=("Segoe UI", 11, "bold"), anchor="w").grid(row=0, column=2, sticky="ew", padx=10)
        ctk.CTkLabel(h_row, text="ARTISTA", text_color="#555", font=("Segoe UI", 11, "bold"), anchor="w").grid(row=0, column=3, sticky="ew")
        ctk.CTkLabel(h_row, text="TEMPO", text_color="#555", font=("Segoe UI", 11, "bold"), anchor="w").grid(row=0, column=4, sticky="ew")
        
        self.tracks = []
        for path in playlist_obj['songs']:
            m = self.controller.db.find_by_path(path)
            if m: self.tracks.append(m)
        
        # Calculate stats
        total_songs = len(self.tracks)
        total_seconds = sum(m.get('duration', 0) or 0 for m in self.tracks)
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        time_str = f"{hours}h {minutes}min" if hours > 0 else f"{minutes} min"
        self.lbl_playlist_stats.configure(text=f"{total_songs} músicas, cerca de {time_str}")
        
        self.update_composite_cover()
        
        if not self.tracks:
            ctk.CTkLabel(self.table, text="Sua playlist está vazia", text_color="#555", font=("Segoe UI", 16)).pack(pady=40)
            return

        # Pass the original track dicts to play_song
        playlist_tracks = self.tracks
        
        self.row_widgets = {} # Rastrear widgets para atualização de status
        
        for i, m in enumerate(self.tracks, 1):
            path = m.get('file_path')
            row = ctk.CTkFrame(self.table, fg_color="#1f1f1f" if i%2==0 else "#191919", height=55, corner_radius=6)
            row.pack(fill="x", pady=2, padx=5)
            
            row.grid_columnconfigure(0, weight=0, minsize=40) # #
            row.grid_columnconfigure(1, weight=0, minsize=50) # Capa
            row.grid_columnconfigure(2, weight=6, uniform="music_col") # Título
            row.grid_columnconfigure(3, weight=4, uniform="music_col") # Artista
            row.grid_columnconfigure(4, weight=2, uniform="music_col") # Tempo
            row.grid_columnconfigure(5, weight=1, minsize=80)           # Ações
            
            lbl_num = ctk.CTkLabel(row, text=str(i), text_color="#555", width=30)
            lbl_num.grid(row=0, column=0, sticky="w")
            
            # Visualizador de Espectro
            visualizer = SpectrumVisualizer(row, width=25, height=20)
            visualizer.grid(row=0, column=0, sticky="w", padx=2)
            visualizer.grid_remove()
            
            # Mini Cover
            lbl_mini = ctk.CTkLabel(row, text="💿", width=40, height=40, corner_radius=4, fg_color="#333")
            lbl_mini.grid(row=0, column=1, padx=5)
            
            def load_pl_mini(path_img=m.get('cover_path'), label=lbl_mini):
                try:
                    resolved = self.controller.resolve_image_path(path_img)
                    if not resolved: return
                    cache_key = f"mini_{path_img}"
                    if cache_key in self.controller.image_cache:
                        img_tk = self.controller.image_cache[cache_key]
                    else:
                        from PIL import Image
                        p_img = Image.open(resolved).convert("RGB").resize((40, 40))
                        img_tk = ctk.CTkImage(p_img, size=(40, 40))
                        self.controller.image_cache[cache_key] = img_tk
                    
                    if label.winfo_exists():
                        self.after(0, lambda: label.configure(image=img_tk, text=""))
                except: pass
            
            import threading
            threading.Thread(target=load_pl_mini, daemon=True).start()

            title_str = m.get('title') or "Unknown"
            q_text = ""
            br = m.get('bitrate', 0)
            ext = m.get('ext', '')
            if br > 0: q_text = f" • {ext} ({br}k)" if ext else f" • {br}k"

            title_container = ctk.CTkFrame(row, fg_color="transparent")
            title_container.grid(row=0, column=2, sticky="ew", padx=10, pady=8)
            
            lbl_title = ctk.CTkLabel(title_container, text=title_str, text_color="white", font=("Segoe UI", 13, "bold"), anchor="w")
            lbl_title.pack(side="left")
            
            if q_text:
                lbl_q = ctk.CTkLabel(title_container, text=q_text, font=("Segoe UI", 11), text_color="white", anchor="w")
                lbl_q.pack(side="left", padx=(5, 0))
            
            artist_str = m.get('artist') or "Unknown"
            lbl_art = ctk.CTkLabel(row, text=artist_str, text_color="#b3b3b3", font=("Segoe UI", 12), anchor="w")
            lbl_art.grid(row=0, column=3, sticky="ew")
            
            def fmt_time(s):
                m, s = divmod(int(s or 0), 60)
                return f"{m}:{s:02d}"

            dur_sec = m.get('duration', 0)
            is_p = path in self.controller.played_songs
            dur_text = fmt_time(dur_sec)
            if is_p: dur_text = "✅ " + dur_text
            
            lbl_dur = ctk.CTkLabel(row, text=dur_text, text_color="white" if is_p else "#777", 
                                   font=("Segoe UI", 11, "bold" if is_p else "normal"), anchor="w")
            lbl_dur.grid(row=0, column=4, sticky="ew")
            
            # Guardar widgets para atualização de status
            self.row_widgets[path] = {
                'num_lbl': lbl_num,
                'visualizer': visualizer,
                'title_lbl': lbl_title,
                'dur_lbl': lbl_dur,
                'row_frame': row,
                'index': i
            }
            
            def on_row_enter(e, p=path, l_num=lbl_num):
                active = self.controller.current_song
                is_playing = active and active.get('file_path') == p
                if not is_playing:
                    l_num.configure(text="▶", text_color="white")
                row.configure(fg_color="#2a2a2a")

            def on_row_leave(e, p=path, l_num=lbl_num, idx=i):
                active = self.controller.current_song
                is_playing = active and active.get('file_path') == p
                if is_playing:
                    # O status será gerenciado pelo update_playing_status global
                    pass
                else:
                    l_num.configure(text=str(idx), text_color="#555")
                row.configure(fg_color="#1f1f1f" if idx%2==0 else "#191919")

            # Bind events
            for widget in [row, lbl_num, lbl_mini, lbl_title, lbl_art, lbl_dur, title_container]:
                widget.bind("<Enter>", on_row_enter)
                widget.bind("<Leave>", on_row_leave)
                widget.bind("<Button-1>", lambda e, d=m: self.controller.play_song(d, playlist_tracks))
                widget.bind("<Button-3>", lambda e, d=m: self.show_context_menu(e, d))
                widget.configure(cursor="hand2")

        # Após carregar tudo, sincroniza o status inicial
        if hasattr(self.controller, 'current_song') and self.controller.current_song:
            self.update_playing_status(self.controller.current_song)

    def update_playing_status(self, current_song, is_playing=True):
        """Atualiza visualmente qual música está tocando na lista"""
        if not hasattr(self, 'row_widgets'): return
        
        active_path = current_song.get('file_path') if current_song else None
        
        for path, widgets in self.row_widgets.items():
            try:
                # Update played status
                is_p_song = path in self.controller.played_songs
                dur_lbl = widgets.get('dur_lbl')
                if dur_lbl:
                    curr = dur_lbl.cget("text")
                    if is_p_song and not curr.startswith("✅"):
                        dur_lbl.configure(text="✅ " + curr, text_color="white", font=("Segoe UI", 11, "bold"))

                visualizer = widgets.get('visualizer')
                if path == active_path:
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

    def update_composite_cover(self):
        """Creates a 2x2 grid cover from the playlist tracks"""
        from PIL import Image
        size = (150, 150)
        final_img = Image.new('RGB', size, color='#2b2b2b')
        
        # Get unique cover paths from tracks
        cover_paths = []
        for t in self.tracks:
            cp = t.get('cover_path')
            if cp and os.path.exists(cp) and cp not in cover_paths:
                cover_paths.append(cp)
            if len(cover_paths) >= 4: break
            
        if not cover_paths:
             self.lbl_playlist_cover.configure(image=None, text="🎵")
             return

        if len(cover_paths) < 4:
            # Just use the first one if not enough for 2x2
            try:
                img = Image.open(cover_paths[0]).resize(size, Image.Resampling.LANCZOS)
                self.cover_img_ref = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                self.lbl_playlist_cover.configure(image=self.cover_img_ref, text="")
            except:
                self.lbl_playlist_cover.configure(image=None, text="🎵")
            return

        # Create 2x2 mosaic
        sub_size = (75, 75)
        for i, cp in enumerate(cover_paths[:4]):
            try:
                img = Image.open(cp).resize(sub_size, Image.Resampling.LANCZOS)
                x = (i % 2) * 75
                y = (i // 2) * 75
                final_img.paste(img, (x, y))
            except: pass
            
        self.cover_img_ref = ctk.CTkImage(light_image=final_img, dark_image=final_img, size=size)
        self.lbl_playlist_cover.configure(image=self.cover_img_ref, text="")

    def update_playing_info(self, song_data):
        """Updates the header cover when a song is played from this view or elsewhere"""
        c_path = song_data.get('cover_path')
        if c_path:
            import os
            from PIL import Image
            possible_paths = [
                c_path,
                os.path.join(os.path.dirname(os.path.dirname(__file__)), c_path),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "covers", os.path.basename(c_path))
            ]
            valid_path = next((p for p in possible_paths if os.path.exists(p)), None)
            
            if valid_path:
                try:
                    pil_img = Image.open(valid_path)
                    w, h = pil_img.size
                    m_min = min(w, h)
                    pil_img = pil_img.crop(((w-m_min)/2, (h-m_min)/2, (w+m_min)/2, (h+m_min)/2))
                    self.cover_img_ref = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(150, 150))
                    self.lbl_playlist_cover.configure(image=self.cover_img_ref, text="")
                except: pass

    def play_playlist(self):
        if hasattr(self, 'tracks') and self.tracks:
            self.controller.play_song(self.tracks[0], self.tracks)
        else:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "A playlist está vazia. Adicione músicas primeiro!")

    def shuffle_playlist(self):
        if hasattr(self, 'tracks') and self.tracks:
            import random
            shuffled_tracks = self.tracks[:]
            random.shuffle(shuffled_tracks)
            random.shuffle(shuffled_tracks)
            self.controller.play_song(shuffled_tracks[0], shuffled_tracks)
        else:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "A playlist está vazia. Adicione músicas primeiro!")

    def export_playlist(self):
        if hasattr(self, 'tracks') and self.tracks:
            from tkinter import filedialog, messagebox
            f = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"{self.current_playlist['name']}.txt")
            if f:
                with open(f, 'w', encoding='utf-8') as out:
                    out.write(f"Playlist: {self.current_playlist['name']}\n\n")
                    for t in self.tracks:
                        out.write(f"{t.get('artist', 'Desconhecido')} - {t.get('title', 'Sem Título')} [{t.get('file_path')}]\n")
                messagebox.showinfo("Exportar", "Playlist exportada com sucesso!")

    def delete_playlist_ui(self):
        if not hasattr(self, 'current_playlist'): return
        
        from tkinter import messagebox
        if messagebox.askyesno("Excluir Playlist", f"Tem certeza que deseja excluir '{self.current_playlist['name']}'?"):
            if self.controller.db.delete_playlist(self.current_playlist['id']):
                self.load_sidebar()
                playlists = self.controller.db.get_playlists()
                if playlists:
                    self.load_playlist(playlists[0])
                else:
                    self.lbl_playlist_name.configure(text="NENHUMA PLAYLIST")
                    for widget in self.table.winfo_children(): widget.destroy()
            else:
                messagebox.showerror("Erro", "Não foi possível excluir a playlist.")

    def edit_playlist(self):
        if hasattr(self, 'current_playlist'):
            current_name = self.current_playlist['name']
            dialog = ctk.CTkInputDialog(text=f"Novo nome para {current_name}:", title="Editar Playlist")
            new_name = dialog.get_input()
            if new_name and new_name != current_name:
                success = self.controller.db.rename_playlist(self.current_playlist['id'], new_name)
                if success:
                    self.current_playlist['name'] = new_name
                    self.lbl_playlist_name.configure(text=new_name.upper())
                    self.load_sidebar()
                else:
                    from tkinter import messagebox
                    messagebox.showerror("Erro", "Não foi possível renomear a playlist.")

    def show_context_menu(self, event, track):
        """Menu de contexto moderno inspirado no Spotify"""
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#1a1a1a")
        menu.attributes("-topmost", True)
        
        def close(): menu.destroy()
        
        header_lbl = ctk.CTkLabel(menu, text="Opções da Música", font=("Segoe UI", 11, "bold"), text_color="#777")
        header_lbl.pack(pady=(8, 2), padx=20)
        
        # Separador visual
        ctk.CTkFrame(menu, height=1, fg_color="#333").pack(fill="x", padx=10, pady=5)
        
        # Ações
        ctk.CTkButton(menu, text="❤ Favoritar", fg_color="transparent", height=35, anchor="w",
                      hover_color="#333", command=lambda: [self.controller.db.toggle_favorite(track['file_path']), close()]).pack(fill="x", padx=5)
        
        ctk.CTkButton(menu, text="📝 Editar Tags (Metadados)", fg_color="transparent", height=35, anchor="w",
                      hover_color="#333", command=lambda: [self.controller.navigate_to("editor", track), close()]).pack(fill="x", padx=5)
        
        # Add a Playlists (sub-menu simplificado)
        ctk.CTkLabel(menu, text="Adicionar à Playlist:", font=("Segoe UI", 10), text_color="#555").pack(pady=(8, 2), padx=20, anchor="w")
        playlists = self.controller.db.get_playlists()
        for p in playlists[:6]:
            if hasattr(self, 'current_playlist') and p['id'] == self.current_playlist['id']:
                continue # Não oferecer adicionar à playlist onde já está
            ctk.CTkButton(menu, text=f"  + {p['name']}", fg_color="transparent", height=28, anchor="w", font=("Segoe UI", 11),
                          hover_color="#2b2b2b",
                          command=lambda pid=p['id']: [self.controller.db.add_to_playlist(pid, track['file_path']), close()]).pack(fill="x", padx=5)
        
        # Remover da playlist atual
        if hasattr(self, 'current_playlist'):
             ctk.CTkFrame(menu, height=1, fg_color="#333").pack(fill="x", padx=10, pady=5)
             ctk.CTkButton(menu, text="🗑 Remover desta Playlist", fg_color="transparent", height=35, anchor="w",
                          text_color="#ff4444", hover_color="#332222",
                          command=lambda: [self.controller.db.remove_from_playlist(self.current_playlist['id'], track['file_path']), self.load_playlist(self.current_playlist), close()]).pack(fill="x", padx=5)

        menu.bind("<FocusOut>", lambda e: close())
        # Pequeno delay para garantir foco
        self.after(100, lambda: menu.focus_set())

    def _scroll_to_active(self, row_widget):
        """Ajusta o scroll para manter o widget da música visível"""
        try:
            self.update_idletasks()
            y_pos = row_widget.winfo_y()
            canvas = self.table._parent_canvas
            total_h = canvas.bbox("all")[3]
            view_h = canvas.winfo_height()
            
            if total_h > view_h:
                target_fraction = max(0, (y_pos - (view_h / 2) + 30) / total_h)
                canvas.yview_moveto(target_fraction)
        except:
            pass
