import customtkinter as ctk
import os
import threading
import webbrowser
from PIL import Image
from .multi_api_enhancer import MultiAPIEnhancer
from .spectrum_visualizer import SpectrumVisualizer
from .glow_button import GlowButton

class FlowButton(ctk.CTkFrame):
    def __init__(self, parent, title, icon_img, color, command=None):
        super().__init__(parent, fg_color="transparent", cursor="hand2")
        self.title = title
        self.icon_img = icon_img
        self.color = color
        self.command = command
        self.is_active = False
        
        # Main Circle
        self.circle = ctk.CTkFrame(self, width=100, height=100, corner_radius=50, fg_color="black")
        self.circle.pack()
        self.circle.pack_propagate(False)
        
        # Icon Label
        self.icon_label = ctk.CTkLabel(self.circle, text="", image=icon_img)
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Active State Overlay (Hidden by default)
        self.active_overlay = ctk.CTkFrame(self.circle, width=32, height=32, corner_radius=16, fg_color="white")
        # Visualizer inside active overlay
        self.visualizer = SpectrumVisualizer(self.active_overlay, width=18, height=12, bar_count=3, bar_color="black")
        self.visualizer.place(relx=0.5, rely=0.5, anchor="center")
        
        # Text Label
        self.label = ctk.CTkLabel(self, text=title, font=("Segoe UI", 12, "bold"), text_color="#b3b3b3")
        self.label.pack(pady=(8, 0))
        
        # Bind events
        for w in [self, self.circle, self.icon_label, self.label]:
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)
            w.bind("<Button-1>", self.on_click)
            
    def on_enter(self, e):
        if not self.is_active:
            self.circle.configure(fg_color="#2a2a2a")
            self.label.configure(text_color="white")
            
    def on_leave(self, e):
        if not self.is_active:
            self.circle.configure(fg_color="black")
            self.label.configure(text_color="#b3b3b3")
            
    def on_click(self, e):
        if self.command:
            self.command(self.title)
            
    def set_active(self, active):
        if self.is_active == active: return
        self.is_active = active
        if active:
            self.circle.configure(fg_color=self.color)
            self.active_overlay.place(relx=0.5, rely=0.5, anchor="center")
            self.visualizer.update_playback_status(True)
            self.icon_label.place_forget()
            self.label.configure(text_color="white")
            self.animate_pulse()
        else:
            self.circle.configure(fg_color="black", border_width=0)
            self.active_overlay.place_forget()
            self.visualizer.update_playback_status(False)
            self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
            self.label.configure(text_color="#b3b3b3")

    def animate_pulse(self):
        if not self.is_active:
            self.circle.configure(border_width=0)
            return
            
        import random
        bw = random.randint(2, 7)
        self.circle.configure(border_width=bw, border_color="#00ff00")
        self.after(120, self.animate_pulse)

class HomeView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        self.page = 1
        self.items_per_page = 20
        self.is_dashboard = True
        self.filter_path = None
        self.search_query = "" # Inicialização necessária
        self._loading_artists = set()
        self._loading_albums = set()
        self.api_enhancer = MultiAPIEnhancer(database=self.controller.db)
        
        # Controle de throttling para refreshes automáticos
        self._last_dash_load = 0
        self._load_lock = threading.Lock()
        
        self.setup_ui()
        
        # Carregar dashboard em background APÓS o setup_ui estar completo
        self._initial_load_job = self.after(100, self._trigger_initial_dashboard)
        
    def _trigger_initial_dashboard(self):
        """Dispara o carregamento inicial se ainda estivermos no dashboard"""
        if self.is_dashboard and hasattr(self, 'grid_area'):
            threading.Thread(target=self.load_dashboard, daemon=True).start()
        
    def setup_ui(self):
        # 1. Top Section (Similar to Image 1)
        self.top_section = ctk.CTkFrame(self, fg_color="transparent")
        self.top_section.pack(fill="x", padx=20, pady=20)
        
        # Search Entry Container
        self.search_container = ctk.CTkFrame(self.top_section, fg_color="#2b2b2b", corner_radius=10, height=45, width=400)
        self.search_container.pack(side="left", padx=(0, 10))
        self.search_container.pack_propagate(False)
        
        ctk.CTkLabel(self.search_container, text="   🔍 ", font=("Segoe UI", 16), text_color="#777").pack(side="left")
        self.search_entry = ctk.CTkEntry(self.search_container, placeholder_text="Pesquisar biblioteca...", 
                                         fg_color="transparent", border_width=0, text_color="white", height=40)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.apply_search())
        self.search_entry.bind("<KeyRelease>", self.on_search_type)
        self.search_entry.bind("<FocusOut>", lambda e: self.after(200, self.hide_autocomplete))
        
        # Buttons Row
        self.btn_search = GlowButton(self.top_section, text="Buscar", width=90, height=38, 
                                     command=self.apply_search)
        self.btn_search.pack(side="left", padx=5)
        
        self.btn_play_all = GlowButton(self.top_section, text="▶ Tudo", width=80, height=38,
                                       command=self.play_all_loaded)
        self.btn_play_all.pack(side="left", padx=5)

        self.btn_clear = GlowButton(self.top_section, text="✖ Limpar", width=90, height=38,
                                    command=self.clear_filters)
        self.btn_clear.pack(side="left", padx=5)

        self.btn_scan = GlowButton(self.top_section, text="🔄 Sincronizar", width=120, height=38,
                                   command=self.start_scan)
        self.btn_scan.pack(side="left", padx=5)
        
        self.lbl_status = ctk.CTkLabel(self.top_section, text="0 músicas", text_color="#777", font=("Segoe UI", 13, "bold"))
        self.lbl_status.pack(side="left", padx=15)
        
        # self.btn_caution = ctk.CTkButton(self.top_section, text="⚠️ 0 Pendências", width=120, height=38,
        #                                fg_color="transparent", border_width=1, border_color="#f1c40f",
        #                                text_color="#f1c40f", hover_color="#1a1a1a", 
        #                                command=lambda: self.controller.navigate_to("manager"))
        # # self.btn_caution.pack(side="left", padx=5) # Só aparece se houver pendência

        self.update_total_count()

        # 2. Body: grid_area + footer empilhados verticalmente
        # Usar um frame body para controlar o espaço sem side="bottom" quebrar o scroll
        self.body_content = ctk.CTkFrame(self, fg_color="transparent")
        self.body_content.pack(fill="both", expand=True)
        self.body_content.grid_rowconfigure(0, weight=1)
        self.body_content.grid_rowconfigure(1, weight=0)
        self.body_content.grid_columnconfigure(0, weight=1)

        self.grid_area = ctk.CTkScrollableFrame(
            self.body_content, fg_color="transparent", corner_radius=0)
        self.grid_area.grid(row=0, column=0, sticky="nsew", padx=20)

        # 3. Pagination Footer — fica na row=1, visível/invisível via grid/grid_remove
        self.footer = ctk.CTkFrame(self.body_content, fg_color="transparent", height=60)
        # Não adicionamos ao grid ainda; load_musics/load_dashboard vai controlar

        # Container centralizado para os controles de paginação
        self.pagination_container = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.pagination_container.pack(expand=True)

        self.btn_first_p = ctk.CTkButton(self.pagination_container, text="≪ Início", width=80, height=32,
                                         fg_color="transparent", border_width=1, border_color="#2b2b2b",
                                         hover_color="#1a1a1a", command=self.go_to_first_page)
        self.btn_first_p.pack(side="left", padx=10)

        self.btn_prev_p = ctk.CTkButton(self.pagination_container, text="← Anterior", width=90, height=32,
                                        fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.prev_page)
        self.btn_prev_p.pack(side="left", padx=10)

        ctk.CTkLabel(self.pagination_container, text="Página", font=("Segoe UI", 13, "bold"), text_color="#777").pack(side="left")

        self.page_entry = ctk.CTkEntry(self.pagination_container, width=50, height=32,
                                       fg_color="#1a1a1a", border_width=1, border_color="#333",
                                       justify="center", font=("Segoe UI", 13, "bold"), text_color="white")
        self.page_entry.insert(0, str(self.page))
        self.page_entry.pack(side="left", padx=5)
        self.page_entry.bind("<Return>", lambda e: self.go_to_page())

        self.btn_next_p = ctk.CTkButton(self.pagination_container, text="Próxima →", width=90, height=32,
                                        fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.next_page)
        self.btn_next_p.pack(side="left", padx=10)

        self.btn_last_p = ctk.CTkButton(self.pagination_container, text="Final ≫", width=80, height=32,
                                        fg_color="transparent", border_width=1, border_color="#2b2b2b",
                                        hover_color="#1a1a1a", command=self.go_to_last_page)
        self.btn_last_p.pack(side="left", padx=10)

        self._footer_visible = False

    # ------------------------------------------------------------------
    # Footer visibility helpers (usa grid para não quebrar o scroll)
    # ------------------------------------------------------------------
    def _show_footer(self):
        if not self._footer_visible:
            self.footer.grid(row=1, column=0, sticky="ew", pady=(4, 8), padx=20)
            self._footer_visible = True

    def _hide_footer(self):
        if self._footer_visible:
            self.footer.grid_remove()
            self._footer_visible = False

    def clear_filters(self):
        self.search_query = ""
        self.filter_path = None
        self.search_entry.delete(0, 'end')
        self.page = 1
        self.is_dashboard = True
        self.load_dashboard()

    def set_filter_path(self, path):
        self.filter_path = path
        self.search_query = ""
        self.page = 1
        self.load_musics()

    def hide_autocomplete(self, event=None):
        if hasattr(self, 'autocomplete_frame') and self.autocomplete_frame.winfo_exists():
            self.autocomplete_frame.withdraw()

    def select_autocomplete(self, text):
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, text)
        self.hide_autocomplete()
        self.apply_search()

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
            self.autocomplete_frame.configure(fg_color="#2b2b2b")
            
        for widget in self.autocomplete_frame.winfo_children():
            widget.destroy()
            
        for artist in artists:
            btn = ctk.CTkButton(self.autocomplete_frame, text=artist, fg_color="transparent", 
                                hover_color="#c3000d", text_color="white", anchor="w",
                                command=lambda a=artist: self.select_autocomplete(a))
            btn.pack(fill="x", padx=2, pady=2)
            
        # Posição logo abaixo do entry
        x = self.search_container.winfo_rootx()
        y = self.search_container.winfo_rooty() + self.search_container.winfo_height()
        width = self.search_container.winfo_width()
        
        self.autocomplete_frame.geometry(f"{width}x{len(artists)*35}+{x}+{y}")
        self.autocomplete_frame.deiconify()

    def on_search_type(self, event):
        if event.keysym in ('Return', 'Up', 'Down', 'Escape'): return
        query = self.search_entry.get().strip()
        if len(query) < 2:
            self.hide_autocomplete()
            return
            
        if hasattr(self, '_autocomplete_timer'):
            self.after_cancel(self._autocomplete_timer)
            
        self._autocomplete_timer = self.after(300, lambda: self.show_autocomplete(query))

    def apply_search(self):
        self.search_query = self.search_entry.get().strip()
        self.page = 1
        if not self.search_query:
            self.load_dashboard()
        else:
            self.load_musics()

    def update_total_count(self):
        """Atualiza a label com o total de músicas no banco"""
        try:
            total = self.controller.db.get_total_count()
            self.lbl_status.configure(text=f"📊 {total} músicas", text_color="#777")
            
            # Verificação de pendências removida a pedido do usuário
            pass
            # pendQuery = "SELECT COUNT(*) as Q FROM metadata_cache WHERE LOWER(artist) LIKE '%unknown%' OR LOWER(title) LIKE '%unknown%'"
            # p_count = self.controller.db.query(pendQuery)[0]['Q']
            # if p_count > 0:
            #     self.btn_caution.configure(text=f"⚠️ Pendências")
            #     self.btn_caution.pack(side="left", padx=5)
            # else:
            #     self.btn_caution.pack_forget()
        except: pass

    def start_scan(self):
        def run():
            from modules.scanner import LibraryScanner
            import os
            self.btn_scan.configure(state="disabled", text="Escaneando...")
            
            # Busca o caminho no gerenciador de configurações
            music_dir = self.controller.config_manager.get("music_dir")
            covers_dir = os.path.join(self.controller.db.root_dir, "assets", "covers")
            
            def update_progress(count, total, filename=""):
                if self.winfo_exists():
                    pct = (count / total) * 100 if total > 0 else 0
                    self.after(0, lambda: self.lbl_status.configure(
                        text=f"🔄 {pct:.1f}% ({count}/{total}) - {filename[:20]}", 
                        text_color="#c3000d"
                    ))
            
            try:
                scanner = LibraryScanner(self.controller.db)
                # Passo 1: Adicionar músicas novas/alteradas
                results = scanner.scan(music_dir, progress_callback=update_progress)
                
                # Passo 2: Remover músicas que foram deletadas do disco
                def update_prune_progress(i, total):
                    if self.winfo_exists():
                        self.after(0, lambda: self.lbl_status.configure(text=f"🧹 Limpando {i}/{total}...", text_color="#3498db"))
                
                removed_count = scanner.prune(progress_callback=update_prune_progress)
                
                if self.winfo_exists():
                    self.after(0, lambda: self.btn_scan.configure(state="normal", text="🔄 Sincronizar"))
                    self.after(0, self.update_total_count)
                    self.after(0, self.controller.notify_data_changed)
                    
                    # Notificação final
                    msg = f"Sincronização concluída: {results['processed']} novas, {removed_count} removidas."
                    if results['skipped'] > 0: msg += f" ({results['skipped']} inalteradas)"
                    
                    self.after(0, lambda m=msg: self.lbl_status.configure(text=m, text_color="#2ecc71"))
                    
                    # Lógica de pendências removida
                    pass
                    # if results.get('pendencies', 0) > 0:
                    #     self.after(0, lambda p=results['pendencies']: [
                    # self.btn_caution.configure(text=f"⚠️ Pendências"),
                    # self.btn_caution.pack(side="left", padx=5) if not self.btn_caution.winfo_ismapped() else None
                    #     ])
                    # else:
                    #     self.after(0, self.btn_caution.pack_forget)
            except Exception as e:
                print(f"Scan error: {e}")
                if self.winfo_exists():
                    self.after(0, lambda: self.btn_scan.configure(state="normal", text="🔄 Sincronizar"))
                    self.after(0, self.update_total_count)
        
        threading.Thread(target=run, daemon=True).start()

    def show_path_results(self, path):
        """Inicia a visão de lista filtrada por uma pasta física"""
        if hasattr(self, '_initial_load_job'):
            self.after_cancel(self._initial_load_job)
        
        self.search_entry.delete(0, 'end')
        self.filter_path = path
        self.is_dashboard = False
        self.page = 1
        self.load_musics()

    def load_dashboard(self, force=False):
        """Carrega a tela estilo Spotify com carrosséis de forma assíncrona"""
        self.is_dashboard = True
        
        # Throttling: evitar recargas seguidas (ex: pular 10 músicas rápido)
        import time
        now = time.time()
        if not force and now - self._last_dash_load < 5: # 5 segundos de silêncio
            return
        self._last_dash_load = now

        # Verificamos se já existe um dashboard carregado (cache visual)
        has_content = hasattr(self, "dashboard_container") and self.dashboard_container.winfo_exists()
        
        # Só limpamos e mostramos spinner se a tela estiver realmente vazia
        if not has_content:
            for widget in self.grid_area.winfo_children():
                widget.destroy()
            self._hide_footer()

            self._dash_loading = ctk.CTkLabel(
                self.grid_area, text="⏳ Carregando biblioteca...",
                font=("Segoe UI", 16), text_color="#b3b3b3"
            )
            self._dash_loading.pack(pady=80)

        # Removida a limpeza agressiva do cache de imagens para manter a fluidez na navegação de volta para a Home

        def _fetch():
            try:
                recent = self.controller.db.get_recently_played(limit=15)
                most_played = self.controller.db.get_most_played(limit=15)
                # get_top_artists já retorna aleatório ou podemos embaralhar aqui
                artists = self.controller.db.get_top_artists(limit=15)
                random_artists = self.controller.db.get_random_artists(limit=15)
                if self.winfo_exists():
                    self.after(0, lambda: self._render_dashboard_sections(
                        recent, most_played, artists, random_artists))
            except Exception as e:
                print(f"[HomeView] Erro no carregamento assíncrono: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_dashboard_sections(self, recent, most_played, artists, random_artists):
        """Renderiza as seções uma a uma para não engasgar a UI"""
        if not self.winfo_exists(): return
        if not self.is_dashboard: return 

        if hasattr(self, "_dash_loading") and self._dash_loading.winfo_exists():
            self._dash_loading.destroy()

        # Limpeza do dashboard antigo apenas no momento de renderizar o novo (elimina piscada preta)
        if hasattr(self, "dashboard_container") and self.dashboard_container.winfo_exists():
            self.dashboard_container.destroy()

        # Cria container principal para o dashboard
        self.dashboard_container = ctk.CTkFrame(self.grid_area, fg_color="transparent")
        self.dashboard_container.pack(fill="both", expand=True)

        self.row_widgets = {}
        self.music_cards = {}

        # Wrapper fixo para o Flow no topo (evita que mude de posição ao alternar modos)
        self.flow_wrapper = ctk.CTkFrame(self.dashboard_container, fg_color="transparent")
        self.flow_wrapper.pack(fill="x", side="top")

        # 1. Flow Section (Deezer Style)
        self.create_flow_section("Gêneros")

        # Embaralha a lista de artistas frequentes para variar a cada visita
        import random
        if artists:
            random.shuffle(artists)

        # Renderizar sequencialmente com pequenos delays
        if recent:
            self.create_carousel_section("Tocadas Recentemente / Adicionadas", recent)

        self.after(50, lambda: self._continue_render(most_played, artists, random_artists))

    def _continue_render(self, most_played, artists, random_artists):
        if not self.winfo_exists() or not self.is_dashboard: return
        if most_played:
            self.create_carousel_section("Suas Mais Tocadas", most_played)

        self.after(50, lambda: self._finish_render(artists, random_artists))

    def _finish_render(self, artists, random_artists):
        if not self.winfo_exists() or not self.is_dashboard: return
        if artists:
            self.create_carousel_section("Artistas mais frequentes", artists, is_artist=True)
        if random_artists:
            self.after(50, lambda: self.create_carousel_section("Descobrir Novos Artistas", random_artists, is_artist=True))

    def create_flow_section(self, mode="Gêneros"):
        # Limpar apenas o conteúdo interno do wrapper
        for widget in self.flow_wrapper.winfo_children():
            widget.destroy()

        self.flow_container = ctk.CTkFrame(self.flow_wrapper, fg_color="transparent")
        self.flow_container.pack(fill="x", pady=(10, 20), padx=20)
        
        header = ctk.CTkFrame(self.flow_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        
        title_cont = ctk.CTkFrame(header, fg_color="transparent")
        title_cont.pack(side="left")
        
        ctk.CTkLabel(title_cont, text="Flow: ouvir de acordo com seu beat", 
                     font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w")
        
        
        # Buttons Row (Scrollable Horizontal)
        buttons_frame = ctk.CTkScrollableFrame(self.flow_container, orientation="horizontal", fg_color="transparent", height=150, scrollbar_button_color="#333", scrollbar_button_hover_color="#c3000d")
        buttons_frame.pack(fill="x", expand=True)
        
        self.flow_buttons = []
        
        items = [
            {"title": "Flow", "icon": "flow.png", "color": "#c3000d"},
            {"title": "Sertanejo", "icon": "sertanejo.png", "color": "#e67e22"},
            {"title": "Forró", "icon": "forro.png", "color": "#e67e22"},
            {"title": "Samba", "icon": "samba.png", "color": "#f1c40f"},
            {"title": "Funk/Soul", "icon": "funk.png", "color": "#9b59b6"},
            {"title": "Flashback", "icon": "flashback.png", "color": "#e91e63"},
            {"title": "MPB", "icon": "mpb.png", "color": "#1abc9c"},
            {"title": "R&B", "icon": "rb.png", "color": "#d35400"},
            {"title": "Rock", "icon": "rock.png", "color": "#34495e"},
            {"title": "Jazz/Blues", "icon": "moods/jazz.png", "color": "#3498db"},
            {"title": "Ragga-Reggae", "icon": "moods/reggae.png", "color": "#2ecc71"},
            {"title": "Groove", "icon": "moods/groove.png", "color": "#f39c12"},
            {"title": "Eletronica", "icon": "moods/eletronica.png", "color": "#9b59b6"},
            {"title": "Hip-Hop", "icon": "moods/hiphop.png", "color": "#1abc9c"},
            {"title": "Amor", "icon": "moods/amor.png", "color": "#e91e63"},
            {"title": "Axé", "icon": "moods/axe.png", "color": "#95a5a6"},
        ]
        
        def handle_flow_click(title):
            for btn in self.flow_buttons:
                if btn.title == title:
                    btn.set_active(True)
                    if title == "Flow":
                        self.play_energetic_flow()
                    else:
                        self.play_flow_folder(title)
                else:
                    btn.set_active(False)

        icon_dir = os.path.join(self.controller.db.root_dir, "assets", "icons", "flow")
        
        for item in items:
            # Resolvido: Caminho do ícone de forma cross-platform (moods/feliz.png -> moods\feliz.png no Windows)
            parts = item["icon"].split("/")
            icon_path = os.path.join(icon_dir, *parts)
            
            img = None
            if os.path.exists(icon_path):
                try:
                    pil_img = Image.open(icon_path).convert("RGBA")
                    img = ctk.CTkImage(pil_img, size=(60, 60))
                except Exception as e:
                    print(f"[Flow Error] Falha ao carregar ícone {icon_path}: {e}")
            else:
                print(f"[Flow Warning] Ícone não encontrado: {icon_path}")
            
            btn = FlowButton(buttons_frame, item["title"], img, item["color"], command=handle_flow_click)
            btn.pack(side="left", padx=15)
            self.flow_buttons.append(btn)

    def play_flow_folder(self, title):
        """Lógica para tocar músicas de um gênero/pasta específica na nova estrutura /flow/"""
        # Mapeamento para as novas pastas que você está criando em C:\Users\Ricardo\Music\flow\
        # Usei nomes simplificados e sem acento para as pastas
        mapping = {
            "Sertanejo": ["Sertanejo"],
            "Forró": ["Forro"],
            "Samba": ["Samba"],
            "Funk/Soul": ["FunkSoul"],
            "Flashback": ["Flashback"],
            "MPB": ["Mpb"],
            "R&B": ["R&B"],
            "Rock": ["Rock"],
            
            "Jazz/Blues": ["JazzBlues"],
            "Ragga-Reggae": ["RaggaRaggae"],
            "Groove": ["Groove"],
            "Eletronica": ["Eletronica"],
            "Hip-Hop": ["HipHop"],
            "Amor": ["Amor"],
            "Axé": ["Axe"]
        }
        
        keywords = mapping.get(title, [title])
        print(f"[Flow Debug] Clique em: {title} -> Buscando na pasta: {keywords}")
        
        # Construir query focada na nova pasta /flow/
        conditions = []
        params = []
        for kw in keywords:
            conditions.append("LOWER(file_path) LIKE LOWER(?)")
            params.append(f"%/flow/{kw}/%")
        
        sql = f"SELECT * FROM metadata_cache WHERE ({' OR '.join(conditions)}) ORDER BY RANDOM() LIMIT 250"
        results = self.controller.db.query(sql, tuple(params))
        
        if results:
            import os
            valid_results = [r for r in results if os.path.exists(r.get('file_path'))]
            
            print(f"[Flow Debug] Encontrados no banco: {len(results)} | Válidos no disco: {len(valid_results)}")
            
            if valid_results:
                print(f"[Flow Debug] Iniciando reprodução de {valid_results[0].get('title')}")
                self.controller.play_song(valid_results[0], valid_results, flow_type=title)
                self.update_idletasks()
            else:
                print(f"[Flow Debug] AVISO: Músicas encontradas no banco, mas os arquivos não existem em {keywords}")
        else:
            print(f"[Flow Debug] Nenhuma música encontrada no banco para {keywords}")

    def play_energetic_flow(self):
        """Lógica para o botão principal do Flow: Tocar músicas agitadas (Vibe Astral)"""
        print("[Flow Debug] Clique em: Flow (Principal) -> Buscando mix de músicas de alta energia")
        
        # Pastas consideradas agitadas/alta energia
        energetic_folders = ["Eletronica", "FunkSoul", "Rock", "Axe", "Groove", "Samba", "HipHop"]
        
        conditions = []
        params = []
        for kw in energetic_folders:
            conditions.append("LOWER(file_path) LIKE LOWER(?)")
            params.append(f"%/flow/{kw}/%")
            
        # Adicionar também músicas que tenham 'remix', 'dance' ou 'ao vivo' no nome
        extra_keywords = ["remix", "dance", "ao vivo"]
        for kw in extra_keywords:
            conditions.append("LOWER(file_path) LIKE LOWER(?)")
            params.append(f"%{kw}%")
            
        sql = f"SELECT * FROM metadata_cache WHERE ({' OR '.join(conditions)}) AND file_path LIKE '%/flow/%' ORDER BY RANDOM() LIMIT 300"
        results = self.controller.db.query(sql, tuple(params))
        
        if results:
            import os
            valid_results = [r for r in results if os.path.exists(r.get('file_path'))]
            
            print(f"[Flow Debug] Encontrados no banco (Alta Energia): {len(results)} | Válidos no disco: {len(valid_results)}")
            
            if valid_results:
                print(f"[Flow Debug] Iniciando reprodução Vibe Astral: {valid_results[0].get('title')}")
                self.controller.play_song(valid_results[0], valid_results, flow_type="Flow")
                self.update_idletasks()
            else:
                print("[Flow Debug] AVISO: Músicas de alta energia encontradas no banco, mas os arquivos não existem.")
        else:
            print("[Flow Debug] Nenhuma música de alta energia encontrada no banco.")

    def play_all_loaded(self):
        """Lógica para o botão principal 'Flow' (Mix aleatório da biblioteca)"""
        print("[Flow] Iniciando Mix Geral...")
        results = self.controller.db.query(
            "SELECT * FROM metadata_cache ORDER BY RANDOM() LIMIT 250"
        )
        if results:
            self.controller.play_song(results[0], results)

    def switch_flow_mode(self, mode):
        self.create_flow_section(mode)

    def show_flow_mode_menu(self):
        import tkinter as tk
        m = tk.Menu(self, tearoff=0, bg="#1a1a1a", fg="white", activebackground="#c3000d")
        m.add_command(label="Ambientes", command=lambda: self.switch_flow_mode("Ambientes"))
        m.add_command(label="Gêneros", command=lambda: self.switch_flow_mode("Gêneros"))
        m.post(self.winfo_pointerx(), self.winfo_pointery())

    def create_carousel_section(self, title, items, is_artist=False):
        section = ctk.CTkFrame(self.dashboard_container, fg_color="transparent")
        section.pack(fill="x", pady=20, padx=10)
        
        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 22, "bold"), text_color="white").pack(side="left")
        
        # Botão Mostrar Tudo (Aumentado para 250 itens)
        btn_show = ctk.CTkButton(header, text="Mostrar tudo", text_color="#b3b3b3", fg_color="transparent", 
                                 hover_color="#1a1a1a", width=100, font=("Segoe UI", 12, "bold"), anchor="e")
        btn_show.pack(side="right", pady=5)

        content_area = ctk.CTkFrame(section, fg_color="transparent")
        content_area.pack(fill="x")

        def toggle():
            nonlocal items
            state = getattr(section, "expanded", False)
            
            # Limpeza ultra-rápida (em vez de loop em todos os filhos)
            if hasattr(content_area, "grid_container") and content_area.grid_container.winfo_exists():
                content_area.grid_container.destroy()
            
            for w in content_area.winfo_children():
                try: w.destroy()
                except: pass
            
            if not state:
                # MODO EXPANDIDO (GRID)
                section.expanded = True
                btn_show.configure(text="Carregando...")
                btn_show.configure(state="disabled")

                # Container para o grid (facilita a destruição rápida depois)
                grid_frame = ctk.CTkFrame(content_area, fg_color="transparent")
                grid_frame.pack(fill="x", expand=True, padx=5)
                content_area.grid_container = grid_frame
                
                # Configurar pesos das colunas para centralizar/distribuir
                cols = 5
                for i in range(cols):
                    grid_frame.grid_columnconfigure(i, weight=1)

                def load_item_data():
                    # Buscar dados em thread para não travar SQL longo (41k itens)
                    try:
                        full_list = items
                        # Re-verificação de títulos para garantir lista completa na expansão
                        if title == "Tocadas Recentemente / Adicionadas":
                            full_list = self.controller.db.get_recently_played(limit=250)
                        elif title == "Suas Mais Tocadas":
                            full_list = self.controller.db.get_most_played(limit=250)
                        elif title == "Artistas mais frequentes":
                            full_list = self.controller.db.get_top_artists(limit=250)
                        elif title == "Descobrir Novos Artistas":
                            full_list = self.controller.db.get_random_artists(limit=250)
                        
                        # Voltar para a main thread para renderizar a lista expandida
                        self.after(0, lambda: start_chunked_rendering(full_list))
                        
                    except Exception as e:
                        print(f"[HomeView] Erro ao carregar expansão: {e}")
                        self.after(0, lambda: btn_show.configure(state="normal", text="Mostrar tudo"))

                def start_chunked_rendering(all_items):
                    if not section.winfo_exists(): return
                    btn_show.configure(text="Mostrar menos", state="normal")
                    
                    # MODO GRID unificado (Cards para Artistas e Músicas)
                    grid_frame = ctk.CTkFrame(content_area, fg_color="transparent")
                    grid_frame.pack(fill="x", expand=True, padx=5)
                    content_area.grid_container = grid_frame
                    
                    cols = 5
                    for i in range(cols): grid_frame.grid_columnconfigure(i, weight=1)
                    
                    def render_grid_chunk(start_i):
                        if not section.winfo_exists() or not section.expanded: return
                        end_i = min(start_i + 15, len(all_items))
                        for i in range(start_i, end_i):
                            r, c = divmod(i, cols)
                            try:
                                item = all_items[i]
                                card = self.create_artist_card(item, grid_frame) if is_artist else self.create_music_card(item, grid_frame)
                                card.grid(row=r, column=c, padx=10, pady=15, sticky="n")
                            except Exception as e:
                                print(f"Erro ao renderizar card: {e}")
                        
                        if end_i < len(all_items):
                            self.after(20, lambda: render_grid_chunk(end_i))
                        else:
                            self._finish_toggle_btn(content_area, toggle)
                            
                    render_grid_chunk(0)

                threading.Thread(target=load_item_data, daemon=True).start()

            else:
                # MODO CARROSSEL (HORIZONTAL)
                section.expanded = False
                btn_show.configure(text="Mostrar tudo")
                
                try:
                    scroll = ctk.CTkScrollableFrame(content_area, orientation="horizontal", height=240, fg_color="transparent")
                except:
                    scroll = ctk.CTkScrollableFrame(content_area, height=240, fg_color="transparent")
                scroll.pack(fill="x")
                
                for item in items:
                    if is_artist:
                        card = self.create_artist_card(item, scroll)
                    else:
                        card = self.create_music_card(item, scroll)
                    card.pack(side="left", padx=10)

        btn_show.configure(command=toggle)
        section.expanded = True 
        toggle() # Começa colapsado (expanded=False)

    def _finish_toggle_btn(self, parent, cmd):
        try:
            btn_less = ctk.CTkButton(parent, text="Recolher lista", text_color="#b3b3b3", 
                                     fg_color="transparent", hover_color="#1a1a1a", width=140, 
                                     height=35, font=("Segoe UI", 12, "bold"), command=cmd)
            btn_less.pack(pady=(10, 30))
        except: pass

    def _create_music_row_exp(self, m, index, playlist, parent):
        path = m.get('file_path')
        row = ctk.CTkFrame(parent, fg_color="#1f1f1f" if index%2==0 else "#191919", height=45, corner_radius=6)
        row.pack(fill="x", pady=1, padx=15)
        
        row.grid_columnconfigure(0, weight=0, minsize=40)
        row.grid_columnconfigure(1, weight=6, uniform="c")
        row.grid_columnconfigure(2, weight=4, uniform="c")
        row.grid_columnconfigure(3, weight=2, uniform="c")
        
        lbl_num = ctk.CTkLabel(row, text=str(index), text_color="#555", width=30)
        lbl_num.grid(row=0, column=0, sticky="w")
        
        # Visualizador de Espectro
        visualizer = SpectrumVisualizer(row, width=25, height=20)
        visualizer.grid(row=0, column=0, sticky="w", padx=2)
        visualizer.grid_remove()
        
        title = m.get('title', 'Unknown')
        artist = m.get('artist', 'Unknown')
        dur = m.get('duration', 0)
        
        t_cont = ctk.CTkFrame(row, fg_color="transparent")
        t_cont.grid(row=0, column=1, sticky="ew", padx=15, pady=8)
        lbl_t = ctk.CTkLabel(t_cont, text=title, font=("Segoe UI", 13, "bold"), text_color="white", anchor="w")
        lbl_t.pack(side="left")
        
        lbl_art = ctk.CTkLabel(row, text=artist, font=("Segoe UI", 12), text_color="#b3b3b3", anchor="w")
        lbl_art.grid(row=0, column=2, sticky="ew", padx=5)
        
        mm, ss = divmod(int(dur or 0), 60)
        is_p = path in self.controller.played_songs
        dur_text = f"{mm}:{ss:02d}"
        if is_p: dur_text = "✅ " + dur_text
        
        lbl_dur = ctk.CTkLabel(row, text=dur_text, font=("Segoe UI", 11, "bold" if is_p else "normal"), 
                               text_color="#1DB954" if is_p else "#777", anchor="w")
        lbl_dur.grid(row=0, column=3, sticky="ew", padx=5)
        
        self.row_widgets[path] = {
            'num_lbl': lbl_num, 
            'visualizer': visualizer, 
            'title_lbl': lbl_t, 
            'dur_lbl': lbl_dur,
            'index': index
        }
        
        def on_enter(e):
            if self.controller.current_song and self.controller.current_song.get('file_path') == path:
                pass
            else:
                lbl_num.configure(text="▶", text_color="white")
            row.configure(fg_color="#2a2a2a")

        def on_leave(e):
            if self.controller.current_song and self.controller.current_song.get('file_path') == path:
                pass
            else:
                lbl_num.configure(text=str(index), text_color="#555")
            row.configure(fg_color="#1f1f1f" if index%2==0 else "#191919")

        for w in [row, lbl_t, lbl_art, lbl_dur, t_cont, lbl_num]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", lambda e: self.controller.play_song(m, playlist))
            w.configure(cursor="hand2")


    def create_artist_card(self, artist_data, parent):
        card = ctk.CTkFrame(parent, fg_color="transparent", width=140)
        
        # Round avatar for artists
        # Circular Label (Placeholder inicial com suporte a cache imediato)
        size = (120, 120)
        img_tk = None
        
        photo_path = self.controller.resolve_image_path(artist_data.get('artist_photo'))
        c_path = self.controller.resolve_image_path(artist_data.get('cover_path'))
        path_to_use = photo_path if photo_path else c_path
        
        if path_to_use and path_to_use in self.controller.image_cache:
            img_tk = self.controller.image_cache[path_to_use]
        
        art = ctk.CTkLabel(card, text="" if img_tk else "👤", image=img_tk, corner_radius=60, width=size[0], height=size[1], fg_color="transparent") 
        art.pack(pady=(0, 5))
        
        # Iniciar processamento da imagem em background se não estiver no cache
        if not img_tk:
            def process_circular_img():
                try:
                    from PIL import Image, ImageOps, ImageDraw
                    if path_to_use and os.path.exists(path_to_use):
                        pil_img = Image.open(path_to_use).convert("RGBA")
                        # Criar máscara circular
                        mask = Image.new('L', size, 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0) + size, fill=255)
                        # Redimensionar e aplicar máscara
                        pil_img = ImageOps.fit(pil_img, size, centering=(0.5, 0.5))
                        pil_img.putalpha(mask)
                        
                        # Atualiza na main thread e salva cache
                        if art.winfo_exists():
                            final_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                            self.controller.image_cache[path_to_use] = final_img
                            self.after(0, lambda: art.configure(image=final_img, text="", fg_color="transparent"))
                    else:
                        # Usar placeholder se não houver imagem
                        placeholder = Image.new('RGBA', size, (0, 0, 0, 0))
                        draw = ImageDraw.Draw(placeholder)
                        draw.ellipse((0, 0) + size, fill='#282828')
                        if art.winfo_exists():
                            final_img = ctk.CTkImage(light_image=placeholder, dark_image=placeholder, size=size)
                            self.after(0, lambda: art.configure(image=final_img, fg_color="transparent"))
                except: pass

            threading.Thread(target=process_circular_img, daemon=True).start()
        
        # Se não tiver foto REAL, inicia o enriquecimento (busca na internet)
        if not artist_data.get('artist_photo') and artist_data.get('artist'):
            self._start_async_enhancement(artist_data.get('artist'), 'artist', art, (120, 120), is_circular=True)
        
        name = artist_data.get('artist', 'Unknown')
        nlbl = ctk.CTkLabel(card, text=name, font=("Segoe UI", 13, "bold"), text_color="white", wraplength=110, height=35)
        nlbl.pack(pady=(2, 0))
        nlbl2 = ctk.CTkLabel(card, text="Artista", font=("Segoe UI", 11), text_color="#b3b3b3")
        nlbl2.pack()
        
        # Context Menu
        def show_menu(event):
            import tkinter as tk
            m = tk.Menu(self, tearoff=0, bg="#1a1a1a", fg="white", activebackground="#c3000d")
            # Artist options
            m.add_command(label=f"Editar {name} (Álbum Único)", command=lambda: self.send_to_editor(name, "single"))
            m.add_command(label=f"Editar {name} (Lote Variável)", command=lambda: self.send_to_editor(name, "variable"))
            m.post(event.x_root, event.y_root)

        # Hover Play Button (Premium Icon)
        play_icon_path = self.controller.resolve_image_path("assets/icons/play_premium.png")
        play_img = None
        if play_icon_path and os.path.exists(play_icon_path):
            try:
                pil_play = Image.open(play_icon_path).convert("RGBA")
                play_img = ctk.CTkImage(pil_play, size=(42, 42))
            except: pass

        if play_img:
            play_btn = ctk.CTkLabel(art, text="", image=play_img, cursor="hand2")
            play_btn.bind("<Button-1>", lambda e, n=name: self.play_artist_now(n))
        else:
            play_btn = ctk.CTkButton(art, text="▶", width=42, height=42, corner_radius=21, 
                                     fg_color="#1DB954", hover_color="#1ed760", 
                                     text_color="white", font=("Segoe UI", 16, "bold"),
                                     bg_color="transparent", border_width=0,
                                     command=lambda n=name: self.play_artist_now(n))
        
        # Unified bindings
        for w in [card, art, nlbl, nlbl2]:
            w.bind("<Button-1>", lambda e, n=name: self.controller.navigate_to("artist", n))
            w.bind("<Button-3>", show_menu)
            w.bind("<Enter>", lambda e: play_btn.place(relx=0.85, rely=0.85, anchor="center"))
            w.bind("<Leave>", lambda e: play_btn.place_forget())
            w.configure(cursor="hand2")
            
        return card

    def send_to_editor(self, artist_name, mode):
        """Envia todas as músicas de um artista para o batch editor"""
        songs = self.controller.db.search_by_artist(artist_name)
        if songs:
            self.controller.navigate_to("batch", {"mode": mode, "songs": songs})

    def play_artist_now(self, artist_name):
        """Busca todas as músicas do artista e toca agora"""
        songs = self.controller.db.search_by_artist(artist_name)
        if songs:
            self.controller.play_song(songs[0], songs)

    def play_genre_now(self, genre):
        """Toca a primeira música do gênero selecionado"""
        musics = self.controller.db.get_musics_by_genre(genre, limit=50)
        if musics:
            self.controller.play_song(musics[0], musics)

    def show_artist_view(self, artist):
        self.is_dashboard = False
        self.search_entry.delete(0, 'end')
        self.search_entry.insert(0, f"artist:{artist}")
        self.apply_search()

    def show_genre_view(self, genre):
        self.is_dashboard = False
        self.search_query = f"Genre: {genre}" # visual cue
        self.search_entry.delete(0, 'end')
        self.search_entry.insert(0, f"g:{genre}") # internal prefix
        self.apply_search()


    def load_musics(self):
        """Navega para um modo LISTA para resultados de busca/filtragem (Estilo Spotify)"""
        self.is_dashboard = False
        self._show_footer()
        
        if hasattr(self, "dashboard_container") and self.dashboard_container.winfo_exists():
            self.dashboard_container.destroy()
            
        for widget in self.grid_area.winfo_children():
            widget.destroy()

        self.row_widgets = {}

        try:
            offset = (self.page - 1) * self.items_per_page
            query = self.search_query
            
            if query.startswith("g:"):
                db_query = query[2:]
                musics = self.controller.db.get_musics_by_genre(db_query, limit=self.items_per_page, offset=offset)
            elif query.startswith("artist:"):
                db_query = query[7:]
                musics = self.controller.db.search_by_artist(db_query, limit=self.items_per_page)
            elif query and ("/" in query or query.lower() in ["hoje", "today"] or (len(query) == 4 and query.isdigit())):
                musics = self.controller.db.search_by_date(query)
            else:
                if query:
                    musics = self.controller.db.search_musics(query, limit=self.items_per_page, offset=offset)
                elif self.filter_path:
                    musics = self.controller.db.get_musics_by_path(self.filter_path, limit=self.items_per_page, offset=offset)
                else:
                    musics = self.controller.db.get_all_musics(limit=self.items_per_page, offset=offset)
            
            # Paginação
            total = self.controller.db.get_filtered_count(query, self.filter_path)
            last_page = (total + self.items_per_page - 1) // self.items_per_page if total > 0 else 1
            
            self.btn_first_p.configure(state="normal" if self.page > 1 else "disabled")
            self.btn_prev_p.configure(state="normal" if self.page > 1 else "disabled")
            self.btn_next_p.configure(state="normal" if self.page < last_page else "disabled")
            self.btn_last_p.configure(state="normal" if self.page < last_page else "disabled")
            self.update_page_entry()
            
            self.current_musics = musics
            if not musics:
                ctk.CTkLabel(self.grid_area, text="Nenhuma música encontrada.", font=("Segoe UI", 16)).pack(pady=100)
                return

            # Header
            h_row = ctk.CTkFrame(self.grid_area, fg_color="transparent")
            h_row.pack(fill="x", padx=15, pady=10)
            h_row.grid_columnconfigure(0, weight=0, minsize=40) # #
            h_row.grid_columnconfigure(1, weight=6, uniform="c") # Titulo
            h_row.grid_columnconfigure(2, weight=4, uniform="c") # Artista
            h_row.grid_columnconfigure(3, weight=2, uniform="c") # Tempo
            
            for i, txt in enumerate(["#", "TÍTULO", "ARTISTA", "TEMPO"]):
                ctk.CTkLabel(h_row, text=txt, font=("Segoe UI", 11, "bold"), text_color="#555", anchor="w").grid(row=0, column=i, sticky="ew", padx=10)

            # Rows
            for idx, m in enumerate(musics, 1):
                self._create_music_row(m, idx + offset, musics)
            
            if self.controller.current_song:
                self.update_playing_status(self.controller.current_song)

        except Exception as e:
            print("Error loading home list:", e)

    def _create_music_row(self, m, index, playlist):
        path = m.get('file_path')
        row = ctk.CTkFrame(self.grid_area, fg_color="#1f1f1f" if index%2==0 else "#191919", height=45, corner_radius=6)
        row.pack(fill="x", pady=1, padx=5)
        
        row.grid_columnconfigure(0, weight=0, minsize=40)
        row.grid_columnconfigure(1, weight=6, uniform="c")
        row.grid_columnconfigure(2, weight=4, uniform="c")
        row.grid_columnconfigure(3, weight=2, uniform="c")
        
        lbl_num = ctk.CTkLabel(row, text=str(index), text_color="#555", width=30)
        lbl_num.grid(row=0, column=0, sticky="w")
        
        # Visualizador de Espectro (inicialmente oculto)
        visualizer = SpectrumVisualizer(row, width=25, height=20)
        visualizer.grid(row=0, column=0, sticky="w", padx=2)
        visualizer.grid_remove()
        
        title = m.get('title', 'Unknown')
        artist = m.get('artist', 'Unknown')
        dur = m.get('duration', 0)
        
        t_cont = ctk.CTkFrame(row, fg_color="transparent")
        t_cont.grid(row=0, column=1, sticky="ew", padx=15, pady=8)
        
        # Mini Capa
        c_path = self.controller.resolve_image_path(m.get('cover_path'))
        cv_lbl = ctk.CTkLabel(t_cont, text="💿", width=32, height=32, fg_color="#2a2a2a", corner_radius=4)
        cv_lbl.pack(side="left", padx=(0, 10))
        
        if c_path and os.path.exists(c_path):
            def load():
                try:
                    from PIL import Image
                    p_img = Image.open(c_path).convert("RGB").resize((32, 32))
                    img_tk = ctk.CTkImage(p_img, size=(32, 32))
                    if cv_lbl.winfo_exists():
                        self.after(0, lambda: cv_lbl.configure(image=img_tk, text=""))
                except: pass
            threading.Thread(target=load, daemon=True).start()

        lbl_t = ctk.CTkLabel(t_cont, text=title, font=("Segoe UI", 13, "bold"), text_color="white", anchor="w")
        lbl_t.pack(side="left")
        
        lbl_art = ctk.CTkLabel(row, text=artist, font=("Segoe UI", 12), text_color="#b3b3b3", anchor="w")
        lbl_art.grid(row=0, column=2, sticky="ew", padx=5)
        
        mm, ss = divmod(int(dur or 0), 60)
        lbl_dur = ctk.CTkLabel(row, text=f"{mm}:{ss:02d}", font=("Segoe UI", 11), text_color="#777", anchor="w")
        lbl_dur.grid(row=0, column=3, sticky="ew", padx=5)
        
        self.row_widgets[path] = {'num_lbl': lbl_num, 'visualizer': visualizer, 'title_lbl': lbl_t, 'index': index}
        
        def on_enter(e):
            if self.controller.current_song and self.controller.current_song.get('file_path') == path:
                pass
            else:
                lbl_num.configure(text="▶", text_color="white")
            row.configure(fg_color="#2a2a2a")

        def on_leave(e):
            if self.controller.current_song and self.controller.current_song.get('file_path') == path:
                pass
            else:
                lbl_num.configure(text=str(index), text_color="#555")
            row.configure(fg_color="#1f1f1f" if index%2==0 else "#191919")

        for w in [row, lbl_t, lbl_art, lbl_dur, t_cont, lbl_num]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", lambda e: self.controller.play_song(m, playlist))
            w.bind("<Button-3>", lambda e: self.show_context_menu(e, m))
            w.configure(cursor="hand2")

    def play_all_loaded(self):
        if hasattr(self, 'current_musics') and self.current_musics:
            self.controller.play_song(self.current_musics[0], self.current_musics)

    def create_music_card(self, track, parent=None):
        target = parent if parent else self.grid_area
        card = ctk.CTkFrame(target, fg_color="transparent", width=160)
        c_path = self.controller.resolve_image_path(track.get('cover_path'))
        size = (150, 150)
        
        img_obj = None
        if c_path and c_path in self.controller.image_cache:
            img_obj = self.controller.image_cache[c_path]
        
        art = ctk.CTkLabel(card, text="🎵" if not img_obj else "", image=img_obj, 
                           corner_radius=12, width=size[0], height=size[1], fg_color="#222")
        art.pack(pady=(0, 10))
        
        if not img_obj and c_path and os.path.exists(c_path):
            def load_img():
                try:
                    from PIL import Image
                    path = c_path
                    if not os.path.exists(path): return
                    pil_img = Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                    final_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                    self.controller.image_cache[path] = final_img
                    if art.winfo_exists():
                        self.after(0, lambda: art.configure(image=final_img, text=""))
                except: pass
            threading.Thread(target=load_img, daemon=True).start()
        
        title = track.get('title', 'Sem Título')
        artist = track.get('artist', 'Desconhecido')
        
        tlbl = ctk.CTkLabel(card, text=title[:18], font=("Segoe UI", 14, "bold"), text_color="white", anchor="w")
        tlbl.pack(fill="x")
        albl = ctk.CTkLabel(card, text=artist[:20], font=("Segoe UI", 12), text_color="#b3b3b3", anchor="w")
        albl.pack(fill="x")
        
        path = track.get('file_path')
        self.music_cards[path] = {'title_lbl': tlbl, 'card_frame': card}
        
        # Highlight if already playing
        if self.controller.current_song and self.controller.current_song.get('file_path') == path:
            tlbl.configure(text_color="#1DB954")
            card.configure(border_width=2, border_color="#1DB954")

        def play_action(e=None): self.controller.play_song(track, []) 
        
        # Hover Play Button (Premium Icon)
        play_icon_path = self.controller.resolve_image_path("assets/icons/play_premium.png")
        play_img = None
        if play_icon_path and os.path.exists(play_icon_path):
            try:
                pil_play = Image.open(play_icon_path).convert("RGBA")
                play_img = ctk.CTkImage(pil_play, size=(44, 44))
            except: pass

        if play_img:
            play_btn = ctk.CTkLabel(art, text="", image=play_img, cursor="hand2")
            play_btn.bind("<Button-1>", lambda e: play_action())
        else:
            play_btn = ctk.CTkButton(art, text="▶", width=44, height=44, corner_radius=22, 
                                     fg_color="#1DB954", hover_color="#1ed760", 
                                     text_color="white", font=("Segoe UI", 18, "bold"),
                                     bg_color="transparent", border_width=0,
                                     command=play_action)
        
        def on_enter(e): play_btn.place(relx=0.8, rely=0.4, anchor="center")
        def on_leave(e): 
            x, y = card.winfo_pointerxy()
            widget = card.winfo_containing(x, y)
            if widget not in [card, art, tlbl, albl, play_btn]:
                play_btn.place_forget()

        for w in [card, art, tlbl, albl]:
            w.bind("<Button-1>", play_action)
            w.bind("<Button-3>", lambda e, d=track: self.show_context_menu(e, d))
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.configure(cursor="hand2")
        
        play_btn.bind("<Leave>", on_leave)
        return card

    def show_artist_context_menu(self, event, artist_name):
        """Menu de contexto específico para artistas (Alinhamento corrigido)"""
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#1a1a1a")
        menu.attributes("-topmost", True)
        
        def close(): menu.destroy()
        
        # Header - Alinhado à esquerda
        header_lbl = ctk.CTkLabel(menu, text=f"Artista: {artist_name}", font=("Segoe UI", 12, "bold"), text_color="#c3000d", anchor="w")
        header_lbl.pack(fill="x", pady=8, padx=15)
        
        # Opções - Alinhamento vertical 'w' (west) com padding consistente
        btn_opts = [
            ("▶ Tocar Artista", lambda: self.play_artist_now(artist_name)),
            ("🔍 Ver Músicas", lambda: self.show_artist_view(artist_name)),
        ]
        
        for text, cmd in btn_opts:
            btn = ctk.CTkButton(menu, text=text, fg_color="transparent", height=32, anchor="w", 
                                hover_color="#333", command=lambda c=cmd: [c(), close()])
            btn.pack(fill="x", padx=5)

        # Buscar uma música do artista para as opções de tags/playlist
        songs = self.controller.db.search_by_artist(artist_name, limit=1)
        if songs:
            track = songs[0]
            # Opção de Biografia Online
            bio_btn = ctk.CTkButton(menu, text="🌐 Ver Biografia no Last.fm", fg_color="transparent", height=32, anchor="w",
                                    hover_color="#333", command=lambda: [webbrowser.open(f"https://www.last.fm/music/{artist_name.replace(' ', '+')}"), close()])
            bio_btn.pack(fill="x", padx=5)
        
        menu.bind("<FocusOut>", lambda e: close())
        self.after(100, lambda: menu.focus_set())

    def show_context_menu(self, event, track):
        """Menu de contexto para músicas (Alinhamento corrigido)"""
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        # Largura fixa para garantir alinhamento
        menu.geometry(f"200x280+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#1a1a1a")
        menu.attributes("-topmost", True)
        
        def close(): menu.destroy()
        
        ctk.CTkLabel(menu, text="Opções da Música", font=("Segoe UI", 12, "bold"), text_color="#c3000d", anchor="w").pack(pady=10, padx=15, fill="x")
        
        # Função para favoritar sem sair da tela (Fix Tela Preta)
        def handle_favorite():
            self.controller.db.toggle_favorite(track['file_path'])
            close()
            if not self.is_dashboard:
                self.load_musics()
            # Se for dashboard, apenas fecha o menu. O estado muda no db mas não exige reload total.

        # Favoritar
        ctk.CTkButton(menu, text="❤ Favoritar", fg_color="transparent", height=35, anchor="w", 
                      hover_color="#333", command=handle_favorite).pack(fill="x", padx=5)
        
        # Editar Tags
        ctk.CTkButton(menu, text="📝 Editar Tags", fg_color="transparent", height=35, anchor="w",
                      hover_color="#333",
                      command=lambda: [self.controller.navigate_to("editor", track), close()]).pack(fill="x", padx=5)
        
        # Divisor
        ctk.CTkFrame(menu, height=1, fg_color="#333").pack(fill="x", padx=10, pady=5)
        
        # Playlists
        ctk.CTkLabel(menu, text="Adicionar à Playlist", font=("Segoe UI", 10, "bold"), text_color="#777", anchor="w").pack(pady=2, padx=15, fill="x")
        
        playlists = self.controller.db.get_playlists()
        if not playlists:
            ctk.CTkLabel(menu, text="Nenhuma playlist", font=("Segoe UI", 9), text_color="#555").pack()
        else:
            for p in playlists[:5]:
                p_btn = ctk.CTkButton(menu, text=f"📁 {p['name']}", fg_color="transparent", height=28, anchor="w",
                                     hover_color="#333",
                                     command=lambda pid=p['id']: [self.controller.db.add_to_playlist(pid, track['file_path']), close()])
                p_btn.pack(fill="x", padx=5)
        
        menu.bind("<FocusOut>", lambda e: close())
        # Tentar fechar se clicar fora
        self.after(100, lambda: menu.focus_set())

    def next_page(self):
        total = self.controller.db.get_filtered_count(self.search_query, self.filter_path)
        last_page = (total + self.items_per_page - 1) // self.items_per_page
        if self.page < last_page:
            self.page += 1
            self.update_page_entry()
            self.load_musics()
            self.grid_area._parent_canvas.yview_moveto(0)

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.update_page_entry()
            self.load_musics()
            self.grid_area._parent_canvas.yview_moveto(0)

    def go_to_page(self):
        try:
            val = int(self.page_entry.get())
            total = self.controller.db.get_filtered_count(self.search_query, self.filter_path)
            last_page = (total + self.items_per_page - 1) // self.items_per_page
            if 1 <= val <= last_page:
                self.page = val
                self.load_musics()
                self.grid_area._parent_canvas.yview_moveto(0)
            else:
                self.update_page_entry()
        except:
            self.update_page_entry()

    def go_to_first_page(self):
        self.page = 1
        self.update_page_entry()
        self.load_musics()
        self.grid_area._parent_canvas.yview_moveto(0)

    def go_to_last_page(self):
        try:
            total = self.controller.db.get_filtered_count(self.search_query, self.filter_path)
            last_page = (total + self.items_per_page - 1) // self.items_per_page
            if last_page > 0:
                self.page = last_page
                self.update_page_entry()
                self.load_musics()
                self.grid_area._parent_canvas.yview_moveto(0)
        except Exception as e:
            print(f"Error going to last page: {e}")

    def update_page_entry(self):
        self.page_entry.delete(0, 'end')
        self.page_entry.insert(0, str(self.page))

    def _start_async_enhancement(self, name, type_mode, target_lbl, size, is_circular=False, second_key=None):
        """
        type_mode: 'artist' or 'album'
        name: Artist Name or Album Name
        second_key: If album, this is the Artist Name
        """
        track_key = f"{type_mode}:{name}"
        if second_key: track_key += f":{second_key}"
        
        loading_set = self._loading_artists if type_mode == 'artist' else self._loading_albums
        if track_key in loading_set: return
        loading_set.add(track_key)
        
        def run():
            try:
                import requests
                from PIL import Image, ImageOps, ImageDraw
                from io import BytesIO
                
                # 1. Buscar URL via Enhancer
                if type_mode == 'artist':
                    info = self.api_enhancer.get_track_complete_info(name, "")
                    url = info.get('artist_photo_url') or info.get('cover_url') if info else None
                else:
                    info = self.api_enhancer.get_track_complete_info(second_key, name)
                    url = info.get('cover_url') or info.get('artist_photo_url') if info else None
                
                if not url: return
                
                # 2. Download Image
                resp = requests.get(url, timeout=7)
                if resp.status_code == 200:
                    img_data = resp.content
                    pil_img = Image.open(BytesIO(img_data)).convert("RGBA")
                    
                    # 3. Salvar localmente para cache persistente
                    assets_dir = os.path.join(self.controller.db.root_dir, "assets", "artists" if type_mode == 'artist' else "covers")
                    os.makedirs(assets_dir, exist_ok=True)
                    
                    safe_name = "".join([c for c in name if c.isalnum() or c == '_'])
                    if second_key:
                        safe_sec = "".join([c for c in second_key if c.isalnum() or c == '_'])
                        filename = f"{safe_sec}_{safe_name}.jpg"
                    else:
                        filename = f"{safe_name}.jpg"
                    
                    local_path = os.path.join(assets_dir, filename)
                    with open(local_path, 'wb') as f:
                        f.write(img_data)
                    
                    # 4. Atualizar Banco de Dados
                    db_rel_path = f"assets/{'artists' if type_mode == 'artist' else 'covers'}/{filename}"
                    if type_mode == 'artist':
                        self.controller.db.update_artist_photo(name, db_rel_path)
                    else:
                        self.controller.db.update_album_cover(second_key, name, db_rel_path)
                    
                    # 5. Atualizar UI se ainda existir e não foi destruído
                    try:
                        if self.winfo_exists() and target_lbl.winfo_exists():
                            if is_circular:
                                mask = Image.new('L', size, 0)
                                draw = ImageDraw.Draw(mask)
                                draw.ellipse((0, 0) + size, fill=255)
                                pil_img = ImageOps.fit(pil_img, size, centering=(0.5, 0.5))
                                pil_img.putalpha(mask)
                            else:
                                pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
                            
                            img_tk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                            # Usar after para garantir segurança da thread
                            self.after(0, lambda: target_lbl.configure(image=img_tk) if target_lbl.winfo_exists() else None)
                    except:
                        pass
            except Exception as e:
                print(f"[AsyncLoad] Erro em {name}: {e}")
            finally:
                if track_key in loading_set:
                    loading_set.remove(track_key)
        
        threading.Thread(target=run, daemon=True).start()

    def update_playing_status(self, current_song, is_playing=True):
        """Notifica tanto a lista de busca quanto os carrosséis sobre a música atual"""
        active_path = current_song.get('file_path') if current_song else None
        
        # 1. Update List (Search Results)
        if hasattr(self, 'row_widgets'):
            for path, widgets in self.row_widgets.items():
                try:
                    visualizer = widgets.get('visualizer')
                    # Update played status (checkmark)
                    is_p_song = path in self.controller.played_songs
                    dur_lbl = widgets.get('dur_lbl')
                    if dur_lbl:
                        curr = dur_lbl.cget("text")
                        if is_p_song and not curr.startswith("✅"):
                            dur_lbl.configure(text="✅ " + curr, text_color="white", font=("Segoe UI", 11, "bold"))

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
                        widgets['num_lbl'].configure(text=str(widgets['index']), text_color="#555")
                        widgets['title_lbl'].configure(text_color="white")
                except: pass

        # 2. Update Cards (Carousels/Grid)
        if hasattr(self, 'music_cards'):
            for path, widgets in self.music_cards.items():
                try:
                    is_active = (path == active_path)
                    widgets['title_lbl'].configure(text_color="#1DB954" if is_active else "white")
                    widgets['card_frame'].configure(border_width=2 if is_active else 0, border_color="#1DB954" if is_active else "transparent")
                except: pass

        # 3. Update Flow Buttons
        active_flow = getattr(self.controller, 'active_flow', None)
        if hasattr(self, 'flow_buttons'):
            for btn in self.flow_buttons:
                if btn.title == active_flow:
                    btn.set_active(True)
                else:
                    btn.set_active(False)

    def update_playing_info(self, track_data):
        pass

