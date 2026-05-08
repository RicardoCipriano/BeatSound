import time
t0 = time.time()

import customtkinter as ctk
from modules.home_view import HomeView
from main import BeatSoundSearch

app = ctk.CTk()
app.main_area = ctk.CTkFrame(app)

class ControllerMock:
    def __init__(self):
        from modules.database import Database
        self.db = Database()
        from modules.multi_api_enhancer import MultiAPIEnhancer
        self.api_enhancer = MultiAPIEnhancer(self.db)
    def navigate_to(self, view):
        pass
controller = ControllerMock()

class ProfileHome(HomeView):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent, fg_color="#121212")
        self.controller = controller
        self.page = 1
        self.items_per_page = 20
        self.is_dashboard = True
        self.filter_path = None
        self.search_query = ""
        self._loading_artists = set()
        self._loading_albums = set()
        self.api_enhancer = controller.api_enhancer
        self._last_dash_load = 0
        import threading
        self._load_lock = threading.Lock()
        self.setup_ui_timed()

    def setup_ui_timed(self):
        t0 = time.time()
        self.top_section = ctk.CTkFrame(self, fg_color="transparent")
        self.top_section.pack(fill="x", padx=20, pady=20)
        
        self.search_container = ctk.CTkFrame(self.top_section, fg_color="#2b2b2b", corner_radius=10, height=45, width=400)
        self.search_container.pack(side="left", padx=(0, 10))
        self.search_container.pack_propagate(False)
        
        ctk.CTkLabel(self.search_container, text="   🔍 ", font=("Segoe UI", 16), text_color="#777").pack(side="left")
        self.search_entry = ctk.CTkEntry(self.search_container, placeholder_text="Pesquisar biblioteca...", fg_color="transparent", border_width=0, text_color="white", height=40)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_search = ctk.CTkButton(self.top_section, text="Buscar", width=90, height=38, fg_color="#c3000d", hover_color="#9a000a", command=self.apply_search)
        self.btn_search.pack(side="left", padx=10)
        
        t1 = time.time()
        print(f"Top 1: {t1-t0:.3f}")
        
        self.btn_play_all = ctk.CTkButton(self.top_section, text="▶ Tudo", width=80, height=38, fg_color="#27ae60", hover_color="#219150", command=self.play_all_loaded)
        self.btn_play_all.pack(side="left", padx=5)

        self.btn_clear = ctk.CTkButton(self.top_section, text="✖ Limpar", width=90, height=38, fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.clear_filters)
        self.btn_clear.pack(side="left", padx=5)

        self.btn_scan = ctk.CTkButton(self.top_section, text="🔄 Sincronizar", width=120, height=38, fg_color="transparent", border_width=1, border_color="#c3000d", text_color="white", hover_color="#1a1a1a", command=self.start_scan)
        self.btn_scan.pack(side="left", padx=5)
        
        self.lbl_status = ctk.CTkLabel(self.top_section, text="0 músicas", text_color="#777", font=("Segoe UI", 13, "bold"))
        self.lbl_status.pack(side="left", padx=15)
        
        self.btn_caution = ctk.CTkButton(self.top_section, text="⚠️ 0 Pendências", width=120, height=38, fg_color="transparent", border_width=1, border_color="#f1c40f", text_color="#f1c40f", hover_color="#1a1a1a", command=lambda: self.controller.navigate_to("manager"))

        t2 = time.time()
        print(f"Top 2: {t2-t1:.3f}")
        
        self.update_total_count()

        t3 = time.time()
        print(f"Update Total Count: {t3-t2:.3f}")

        self.body_content = ctk.CTkFrame(self, fg_color="transparent")
        self.body_content.pack(fill="both", expand=True)
        self.body_content.grid_rowconfigure(0, weight=1)
        self.body_content.grid_rowconfigure(1, weight=0)
        self.body_content.grid_columnconfigure(0, weight=1)

        self.grid_area = ctk.CTkScrollableFrame(self.body_content, fg_color="transparent", corner_radius=0)
        self.grid_area.grid(row=0, column=0, sticky="nsew", padx=20)

        t4 = time.time()
        print(f"Grid area: {t4-t3:.3f}")

        self.footer = ctk.CTkFrame(self.body_content, fg_color="transparent", height=60)
        self.pagination_container = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.pagination_container.pack(expand=True)

        self.btn_first_p = ctk.CTkButton(self.pagination_container, text="≪ Início", width=80, height=32, fg_color="transparent", border_width=1, border_color="#2b2b2b", hover_color="#1a1a1a", command=self.go_to_first_page)
        self.btn_prev = ctk.CTkButton(self.pagination_container, text="< Anterior", width=80, height=32, fg_color="transparent", border_width=1, border_color="#2b2b2b", hover_color="#1a1a1a", command=self.prev_page)
        self.lbl_page = ctk.CTkLabel(self.pagination_container, text="Página 1", font=("Segoe UI", 14))
        self.btn_next = ctk.CTkButton(self.pagination_container, text="Próxima >", width=80, height=32, fg_color="transparent", border_width=1, border_color="#2b2b2b", hover_color="#1a1a1a", command=self.next_page)
        
        t5 = time.time()
        print(f"Pagination buttons: {t5-t4:.3f}")

ProfileHome(app.main_area, controller)
