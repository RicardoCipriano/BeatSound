import os
import sys
import ctypes

# ========== CORREÇÃO DE TELA (DPI + FULLSCREEN) ==========
# Desativa o DPI scaling do Windows (força 100% real)
# Isso faz com que a janela use a resolução REAL da tela em qualquer monitor/TV
def fix_dpi_awareness():
    """Força o Windows a usar DPI awareness para que a janela ocupe 100% da tela"""
    try:
        # Windows 10/11 - DPI_AWARENESS_SYSTEM_AWARE (1)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        print("[DPI] DPI Awareness ativado (System Aware)")
    except:
        try:
            # Fallback para Windows 8/7
            ctypes.windll.user32.SetProcessDPIAware()
            print("[DPI] DPI Awareness ativado (legacy)")
        except:
            print("[DPI] Não foi possível ativar DPI Awareness")

# Executa a correção ANTES de qualquer import do tkinter
fix_dpi_awareness()

# ========== RESTO DO CÓDIGO ==========
# 1. HIDE CONSOLE WINDOW IMMEDIATELY (Fail-safe for Windows)
def hide_console():
    if os.name == 'nt':
        # Get handle to the console window
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        hWnd = kernel32.GetConsoleWindow()
        if hWnd != 0:
            # Hide the window if it's there
            user32.ShowWindow(hWnd, 0) # 0 = SW_HIDE

# 2. Redirecionamento de Logs (Apenas quando congelado)
# Isso deve ser a PRIMEIRA coisa a rodar para capturar erros de inicialização
if getattr(sys, 'frozen', False):
    hide_console()
    try:
        exe_dir = os.path.dirname(sys.executable)
        log_dir = os.path.join(exe_dir, "logs")
        if not os.path.exists(log_dir): os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "runtime_error.log")
        # Abre o arquivo em modo 'w' para limpar cada vez que inicia ou 'a' para anexar
        sys.stdout = open(log_file, "a", encoding="utf-8")
        sys.stderr = sys.stdout
        print(f"\n{'='*50}")
        print(f"--- Inicializando App: {os.path.abspath(sys.executable)} ---")
        print(f"{'='*50}")
    except: pass

# Configuração de caminhos para o executável (Tkinter/Tcl/Tk Fix)
# TEM QUE SER ANTES DO IMPORT DO CUSTOMTKINTER e TKINTER!
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS 
    
    # 1. Definir caminhos candidatos (Python 3.13 / PyInstaller 6+)
    # Tenta tanto na raiz de _MEIPASS quanto em _internal/
    candidates = [
        os.path.join(base_path, '_internal'),
        base_path
    ]
    
    found_tcl = None
    found_tk = None
    
    # Nomes possíveis de pastas de biblioteca
    tcl_folders = ['_tcl_data', 'tcl8.6', 'tcl']
    tk_folders = ['_tk_data', 'tk8.6', 'tk']
    
    for c in candidates:
        if not os.path.exists(c): continue
        for folder in tcl_folders:
            p = os.path.join(c, folder)
            if os.path.exists(os.path.join(p, 'init.tcl')):
                found_tcl = p
                break
        for folder in tk_folders:
            p = os.path.join(c, folder)
            if os.path.exists(os.path.join(p, 'tk.tcl')):
                found_tk = p
                break
        if found_tcl and found_tk: break
            
    if found_tcl: 
        os.environ['TCL_LIBRARY'] = found_tcl
        print(f"[TCL] Path found: {found_tcl}")
    if found_tk: 
        os.environ['TK_LIBRARY'] = found_tk
        print(f"[TK] Path found: {found_tk}")

import customtkinter as ctk
import pygame
from PIL import Image, ImageTk
from CTkMenuBar import *
from CTkToolTip import *
from modules.full_screen_player import FullScreenPlayer

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            # Prioridade 1: Verifica em _internal (Modo onedir do PyInstaller 6+)
            internal_test = os.path.join(base_path, '_internal', relative_path)
            if os.path.exists(internal_path := internal_test):
                return internal_path
            # Prioridade 2: Verifica na raiz de _MEIPASS
            bundled_test = os.path.join(base_path, relative_path)
            if os.path.exists(bundled_test):
                return bundled_test
            # Prioridade 3: Verifica na raiz do EXE (arquivos externos)
            exe_dir = os.path.dirname(sys.executable)
            external_test = os.path.join(exe_dir, relative_path)
            if os.path.exists(external_test):
                return external_test
        else:
            base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
    except Exception as e:
        print(f"Error in resource_path for {relative_path}: {e}")
        return relative_path
    
    return relative_path


# Cores baseadas no design fornecido (Last.fm style)
BG_COLOR = "#121212"
SIDEBAR_COLOR = "#181818"
RED_ACCENT = "#c3000d"
RED_HOVER = "#9a000a"
TEXT_COLOR = "#ffffff"
TEXT_MUTED = "#b3b3b3"

# Cores sofisticadas do site BrasilCode (Seção 14) - Simplificadas por grupo
ICON_COLORS = {
    "home": "#C82647",      # Vermelho (Mesmo do Gênero Categoria)
    "search": "#C82647",    # Vermelho
    "categories": "#C82647", # Vermelho
    "playlists": "#C82647", # Vermelho
    "favorites": "#C82647", # Vermelho
    "stats": "#7F8C8D",     # Cinza (Mesmo de Configurações)
    "settings": "#7F8C8D",  # Cinza
    "editor": "#2ECC71",    # Verde (Mesmo de Download)
    "batch_single": "#2ECC71", # Verde
    "manager": "#2ECC71",   # Verde
    "batch_variable": "#2ECC71", # Verde
    "download": "#2ECC71"   # Verde
}

class SophisticatedSidebarButton(ctk.CTkButton):
    """Botão personalizado que implementa efeitos sofisticados de borda e preenchimento"""
    def __init__(self, master, accent_color, view_name, data=None, **kwargs):
        # Inicia com borda invisível (mesma cor da sidebar e largura 0)
        super().__init__(
            master,
            fg_color="transparent",
            border_color=SIDEBAR_COLOR,
            border_width=0,
            hover_color=accent_color,
            corner_radius=12,
            text_color="white",
            **kwargs
        )
        self.accent_color = accent_color
        self.view_name = view_name
        self.data = data
        self.is_active = False
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        # Só mostra a borda no hover se não estiver ativo
        if not self.is_active:
            self.configure(border_color=self.accent_color, border_width=3)

    def _on_leave(self, event=None):
        # Volta a esconder a borda se não estiver ativo
        if not self.is_active:
            self.configure(border_color=SIDEBAR_COLOR, border_width=0)

    def set_active(self, active):
        """Define o estado visual do botão quando clicado/selecionado"""
        self.is_active = active
        if active:
            # Mantém a borda visível e adiciona um fundo de destaque
            self.configure(border_color=self.accent_color, border_width=3, fg_color="#2b2b2b")
        else:
            # Reseta para o estado invisível padrão
            self.configure(border_color=SIDEBAR_COLOR, border_width=0, fg_color="transparent")

class BeatSoundSearch(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BeatSound - Dj77")
        # Obtém resolução da tela real
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        print(f"[TELA] Inicializando em: {screen_width}x{screen_height}")

        # Define geometria ocupando toda a tela inicialmente
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        # FORÇA a janela a aplicar a geometria e maximizar
        self.update_idletasks()
        
        # Maximiza a janela (garante 100% de preenchimento em qualquer monitor/TV)
        # O delay de 100ms garante que o Windows processe a janela antes de maximizar
        self.after(100, lambda: self.state('zoomed'))
        
        # Inicializar Configurações
        from modules.config_manager import ConfigManager
        self.config_manager = ConfigManager()
        
        ctk.set_appearance_mode(self.config_manager.get("appearance_mode"))
        self.configure(fg_color=BG_COLOR)
        ctk.set_widget_scaling(1.0)

        # Definir Ícone da Janela
        try:
            icon_path = resource_path("beatsound.ico")
            if os.path.exists(icon_path):
                self.after(200, lambda: self.iconbitmap(icon_path))
        except: pass
        
        # --- AUTO-INSTALADOR DE DADOS (BUNDLED -> RAIZ DO EXE) ---
        if getattr(sys, 'frozen', False):
            import shutil
            exe_root = os.path.dirname(sys.executable)
            bundle_root = sys._MEIPASS
            internal_root = os.path.join(bundle_root, "_internal")
            
            def sync_item(rel_path):
                # Tenta origem em _internal (Modo onedir do PyInstaller 6+) ou no bundle root
                src = os.path.join(internal_root, rel_path)
                if not os.path.exists(src):
                    src = os.path.join(bundle_root, rel_path)
                
                dst = os.path.join(exe_root, rel_path)
                
                # Sincroniza se a origem existe e o destino estiver ausente ou vazio
                if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
                    should_copy = not os.path.exists(dst)
                    if not should_copy and os.path.isdir(dst):
                        try: should_copy = len(os.listdir(dst)) == 0
                        except: should_copy = True
                    
                    if should_copy:
                        try:
                            if os.path.isdir(src):
                                if os.path.exists(dst): 
                                    try: shutil.rmtree(dst)
                                    except: pass
                                shutil.copytree(src, dst, dirs_exist_ok=True)
                            else:
                                shutil.copy2(src, dst)
                            print(f"[Auto-Installer] Sucesso ao sincronizar: {rel_path}")
                        except Exception as e:
                            print(f"[Auto-Installer] Erro ao sincronizar {rel_path}: {e}")

            # Sincroniza apenas os arquivos de marca (logo e ícone)
            for item in ["logo.png", "beatsound.ico"]:
                sync_item(item)
        
        # Inicializar banco de dados
        from modules.database import Database
        self.db = Database()
        
        # Inicializar API Enhancer para buscar dados extras de artistas/músicas (usado na sidebar de tocando agora)
        from modules.multi_api_enhancer import MultiAPIEnhancer
        self.api_enhancer = MultiAPIEnhancer(database=self.db)
        
        # Caches
        self.view_cache = {}
        self.image_cache = {}
        
        # Splash Screen Personalizado com Efeito de Zoom no Logo
        # Iniciamos esconder o logo e o label de texto conforme pedido
        self.logo_lbl = None
        self.after(10, self.show_logo_animation)
        
        # Efeito de Zoom (Logo cresce e diminui)
        def logo_zoom(step=0):
            if not hasattr(self, 'logo_lbl') or not self.logo_lbl: return
            
            # Frequência e intensidades do zoom: primeiro normal, segundo slow
            scales = [
                # 1° Zoom normal
                1.0, 1.2, 1.4, 1.2, 1.0,
                # 2° Zoom slow (mais frames para fluidez)
                1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35, 1.40,
                1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 1.05, 1.0
            ]
            if step < len(scales):
                scale = scales[step]
                base_w, base_h = self.logo_base_size
                new_w = int(base_w * scale)
                new_h = int(base_h * scale)
                
                if hasattr(self, 'logo_img_tk'):
                    self.logo_img_tk.configure(size=(new_w, new_h))
                
                # Se for o 1° zoom (0 a 4) rápido (80ms), do contrário (slow) frame com (50ms) e transição mais suave
                delay = 80 if step < 5 else 40
                self.after(delay, lambda: logo_zoom(step + 1))
            else:
                self.after(300, self._delayed_setup_final)
                
        self.logo_zoom_func = logo_zoom
        
    def show_logo_animation(self):
        """Exibe o logo e inicia animação de zoom"""
        try:
            logo_path = resource_path("logo.png")
            if os.path.exists(logo_path):
                from PIL import Image
                pil_img = Image.open(logo_path)
                w, h = pil_img.size
                max_size = 280
                nw, nh = (max_size, int(h*(max_size/w))) if w > h else (int(w*(max_size/h)), max_size)
                self.logo_base_size = (nw, nh)
                self.logo_img_tk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(nw, nh))
                self.logo_lbl = ctk.CTkLabel(self, image=self.logo_img_tk, text="")
                self.logo_lbl.pack(expand=True)
                
                # Inicia zoom
                self.after(100, lambda: self.logo_zoom_func(0))
            else:
                self.logo_lbl = ctk.CTkLabel(self, text="BEATSOUND", font=("Segoe UI", 48, "bold"), text_color="#c3000d")
                self.logo_lbl.pack(expand=True)
                self.after(1500, self._delayed_setup_final)
        except Exception as e:
            print(f"Error in splash: {e}")
            self.after(1000, self._delayed_setup_final)

    def _delayed_setup_final(self):
        if hasattr(self, 'logo_lbl'): self.logo_lbl.destroy()
        self._delayed_setup()
        
    def _delayed_setup(self):
        # 1. Banco e Configurações (Lazy)
        if not hasattr(self, 'db'):
            from modules.database import Database
            self.db = Database()
        
        # 2. API e Player
        from modules.multi_api_enhancer import MultiAPIEnhancer
        self.api_enhancer = MultiAPIEnhancer(database=self.db)
        
        from modules.player import MusicPlayer
        self.player = MusicPlayer()
        self.player.volume = self.config_manager.get("volume")
        
        from modules.now_playing_sidebar import NowPlayingSidebar
        self.now_playing_sidebar = None # Will init in setup_ui
        
        self.full_screen_player = FullScreenPlayer(self, self)
        
        # Estado
        self.current_view = None
        self.current_song = None
        self.playlists = []
        self.favorites = set()
        self.played_songs = set() # Track songs that were fully heard
        self.last_volume = self.player.volume if self.player.volume > 0 else 0.5
        self.is_muted = False
        self.mini_player_mode = False
        
        # Top Bar (Functional Menu)
        try:
            from CTkMenuBar import CTkMenuBar, CustomDropdownMenu
            self.menu = CTkMenuBar(master=self, bg_color="#c3000d") # Background Vermelho
            
            # Menus removidos para manter apenas a barra vermelha limpa
            pass
            
        except Exception as e:
            print(f"Error loading CTkMenuBar: {e}")
            # Fallback legacy frame if library fails
            self.menu_frame = ctk.CTkFrame(self, height=30, fg_color="#a82323", corner_radius=0)
            self.menu_frame.pack(side="top", fill="x")
            # Labels removidos para manter apenas a barra vermelha
            pass
        
        self.setup_ui()
        
    def resolve_image_path(self, path):
        """Resolve o caminho da imagem de forma portável (assets, covers, fotos)"""
        if not path: return None
        
        # 1. Se absoluto e existe, retorna
        if os.path.isabs(path) and os.path.exists(path):
            return path
            
        # 2. Tenta via root_dir (pasta do executável)
        base_dir = self.db.root_dir
            
        possible_paths = [
            os.path.join(base_dir, path),
            os.path.join(base_dir, "assets", "covers", os.path.basename(path)),
            os.path.join(base_dir, "assets", "artist_photos", os.path.basename(path)),
            os.path.join(base_dir, "assets", "icons", os.path.basename(path)),
            os.path.join(base_dir, "assets", os.path.basename(path)),
            path # Relativo ao CWD (último recurso)
        ]
        
        for p in possible_paths:
            try:
                if os.path.exists(p):
                    return p
            except: pass
            
        # 3. Tenta via resource_path (Pasta interna - _MEIPASS)
        try:
            internal_p = resource_path(path)
            if os.path.exists(internal_p):
                return internal_p
        except: pass

        return None

    def setup_ui(self):
        # Barra Superior Vermelha (Solicitada pelo usuário)
        self.top_bar = ctk.CTkFrame(self, height=4, fg_color="#a82323", corner_radius=0)
        self.top_bar.pack(side="top", fill="x")

        # Player Bar (Sempre no fundo)
        self.setup_player_bar()

        # View container to act as body (Área central que expande)
        self.body_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame.pack(side="top", fill="both", expand=True)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self.body_frame, width=220, fg_color=SIDEBAR_COLOR, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        # Logo Superior no Sidebar (Solicitado)
        try:
            logo_path = self.resolve_image_path("logoInicial.png")
            if logo_path:
                from PIL import Image
                pil_logo = Image.open(logo_path)
                # Cálculo de proporção para evitar distorção (logo original é 512x512)
                orig_w, orig_h = pil_logo.size
                max_display_w = 140
                max_display_h = 100
                
                # Manter proporção
                ratio = min(max_display_w / orig_w, max_display_h / orig_h)
                new_w = int(orig_w * ratio)
                new_h = int(orig_h * ratio)
                
                self.logo_ctk = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(new_w, new_h))
                self.logo_lbl = ctk.CTkLabel(self.sidebar, image=self.logo_ctk, text="")
                self.logo_lbl.pack(pady=(20, 15), padx=20)
        except Exception as e:
            print(f"[Main] Erro ao carregar logo sidebar: {e}")
        
        # Botões Principais com estilo sofisticado
        self.sidebar_btns = [] # Lista para rastrear os botões e atualizar o estado "ativo"
        
        main_buttons = [
            ("🏠 Principal", "home", ICON_COLORS["home"]),
            ("🔍 Buscar", "search", ICON_COLORS["search"]),
            ("📑 Gênero Categoria", "categories", ICON_COLORS["categories"]),
            ("📋 Playlists", "playlists", ICON_COLORS["playlists"]),
            ("⭐ Favoritos", "favorites", ICON_COLORS["favorites"]),
            ("📊 Estatísticas", "stats", ICON_COLORS["stats"]),
            ("⚙️ Configurações", "settings", ICON_COLORS["settings"])
        ]
        
        for text, view, color in main_buttons:
            btn = SophisticatedSidebarButton(
                self.sidebar,
                text=text,
                accent_color=color,
                view_name=view,
                anchor="w",
                font=("Segoe UI", 16),
                command=lambda v=view: self.navigate_to(v)
            )
            btn.pack(pady=5, padx=10, fill="x")
            self.sidebar_btns.append(btn)
            
        ctk.CTkLabel(self.sidebar, text="Ferramentas", font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=20, pady=(20, 5))
        
        # Botões de Ferramentas com estilo sofisticado
        tool_buttons = [
            ("✏️ Editor Tags", "editor", ICON_COLORS["editor"], None),
            ("📦 Álbum Único (Lote)", "batch", ICON_COLORS["batch_single"], {"mode": "single"}),
            ("🏛 Gestor Biblioteca", "manager", ICON_COLORS["manager"], None),
            ("🤖 Lote Variável (IA)", "batch", ICON_COLORS["batch_variable"], {"mode": "variable"}),
            ("🚀 Download Music", "download", ICON_COLORS["download"], None)
        ]

        for text, view, color, data in tool_buttons:
            font_style = ("Segoe UI", 14, "bold") if view == "download" else ("Segoe UI", 14)
            btn = SophisticatedSidebarButton(
                self.sidebar,
                text=text,
                accent_color=color,
                view_name=view,
                data=data,
                anchor="w",
                font=font_style,
                command=lambda v=view, d=data: self.navigate_to(v, data=d) if d else self.navigate_to(v)
            )
            btn.pack(pady=5, padx=10, fill="x")
            self.sidebar_btns.append(btn)

        
        # Área Principal
        self.main_area = ctk.CTkFrame(self.body_frame, fg_color=BG_COLOR, corner_radius=0)
        self.main_area.pack(side="left", fill="both", expand=True)
        
        # Now Playing Sidebar (Spotify style)
        from modules.now_playing_sidebar import NowPlayingSidebar
        self.now_playing_sidebar = NowPlayingSidebar(self.body_frame, self)
        # Initially hidden
        self.now_playing_sidebar.pack_forget()

        # Sidebar handle (Spotify style)
        # Handle hidden per user request, toggle will only rely on bottom player bar button
        # self.sidebar_handle = ctk.CTkButton(self, text="<", width=15, height=100,
        #                                     fg_color="transparent", hover_color="#1a1a1a",
        #                                     text_color="#1DB954", corner_radius=0,
        #                                     font=("Segoe UI", 16, "bold"),
        #                                     command=self.now_playing_sidebar.toggle)
        self.navigate_to("home")
        
    def setup_player_bar(self):
        
        self.player_bar = ctk.CTkFrame(self, height=100, fg_color="#181818", corner_radius=0)
        self.player_bar.pack(side="bottom", fill="x")
        
        # Seeker Slider (Thin and clean Spotify style)
        self.seeker = ctk.CTkSlider(self.player_bar, height=4, progress_color=RED_ACCENT, fg_color="#333333",
                                    button_color=RED_ACCENT, button_hover_color=RED_HOVER, from_=0, to=100,
                                    command=self.seek_song, button_length=0)
        self.seeker.pack(side="top", fill="x", padx=0, pady=(0, 2))
        self.seeker.set(0)
        
        controls = ctk.CTkFrame(self.player_bar, fg_color="transparent")
        controls.pack(fill="both", expand=True, padx=20)
        
        # Left: Cover and info
        left_info = ctk.CTkFrame(controls, fg_color="transparent", width=250)
        left_info.pack(side="left", fill="y", pady=10)
        self.lbl_cover = ctk.CTkLabel(left_info, text="", width=60, height=60, fg_color="#222", corner_radius=8)
        self.lbl_cover.pack(side="left")
        self.lbl_cover.bind("<Button-1>", lambda e: self.full_screen_player.show())
        
        info_texts = ctk.CTkFrame(left_info, fg_color="transparent")
        info_texts.pack(side="left", padx=15)
        self.lbl_title = ctk.CTkLabel(info_texts, text="-", font=("Segoe UI", 14, "bold"), text_color="white")
        self.lbl_title.pack(anchor="w")
        self.lbl_artist = ctk.CTkLabel(info_texts, text="-", font=("Segoe UI", 12), text_color=TEXT_MUTED)
        self.lbl_artist.pack(anchor="w")
        
        # Bindings for the texts area too
        self.lbl_title.bind("<Button-1>", lambda e: self.full_screen_player.show())
        self.lbl_artist.bind("<Button-1>", lambda e: self.full_screen_player.show())
        info_texts.bind("<Button-1>", lambda e: self.full_screen_player.show())
        
        # Center: Player controls
        center_ctrl = ctk.CTkFrame(controls, fg_color="transparent")
        center_ctrl.pack(side="left", expand=True)
        
        self.time_lbl = ctk.CTkLabel(center_ctrl, text="0:00 / 0:00", font=("Segoe UI", 11), text_color=TEXT_MUTED)
        self.time_lbl.pack(pady=(0, 5))
        
        btns = ctk.CTkFrame(center_ctrl, fg_color="transparent")
        btns.pack()
        

        
        self.btn_shuffle = ctk.CTkButton(btns, text="🔀", width=30, fg_color="transparent", 
                                         text_color="#555", font=("Segoe", 16), command=self.toggle_shuffle)
        self.btn_shuffle.pack(side="left", padx=5)
        
        self.btn_prev = ctk.CTkButton(btns, text="⏮", width=30, fg_color="transparent", 
                                         text_color="white", hover_color="#333", font=("Segoe", 18), command=self.play_prev)
        self.btn_prev.pack(side="left", padx=5)
        
        self.btn_play_pause = ctk.CTkButton(btns, text="▶", width=45, height=45, corner_radius=22, 
                                            fg_color=RED_ACCENT, hover_color=RED_HOVER, text_color="white",
                                            font=("Segoe", 18), command=self.toggle_play_pause)
        self.btn_play_pause.pack(side="left", padx=15)
        
        self.btn_next = ctk.CTkButton(btns, text="⏭", width=30, fg_color="transparent", 
                                         text_color="white", hover_color="#333", font=("Segoe", 18), command=self.play_next)
        self.btn_next.pack(side="left", padx=5)
        
        self.btn_repeat = ctk.CTkButton(btns, text="🔁", width=30, fg_color="transparent", 
                                        text_color="#555", font=("Segoe", 16), command=self.toggle_repeat)
        self.btn_repeat.pack(side="left", padx=5)
        
        # Right: Extra controls
        right_ctrl = ctk.CTkFrame(controls, fg_color="transparent")
        right_ctrl.pack(side="right", pady=10)
        
        self.btn_fav = ctk.CTkButton(right_ctrl, text="❤", width=30, fg_color="transparent", text_color="#555", 
                                    font=("Segoe UI", 20), command=self.toggle_favorite_current)
        self.btn_fav.pack(side="left", padx=10)
        
        self.btn_mute = ctk.CTkButton(right_ctrl, text="🔈", width=30, height=30, fg_color="transparent", 
                                      hover_color="#2a2a2a", text_color="white", font=("Segoe", 16), 
                                      command=self.toggle_mute)
        self.btn_mute.pack(side="left", padx=(5, 0))

        self.vol_slider = ctk.CTkSlider(right_ctrl, width=100, progress_color=RED_ACCENT, button_color=RED_ACCENT,
                                        button_hover_color=RED_HOVER, from_=0, to=1, command=self.set_volume)
        self.vol_slider.pack(side="left", padx=10)
        self.vol_slider.set(self.player.volume)
        
        # Toggle Sidebar button
        self.btn_sidebar = ctk.CTkButton(right_ctrl, text="📟", width=35, height=35,
                                         fg_color="transparent", text_color="#555",
                                         hover_color="#2a2a2a", font=("Segoe UI", 18),
                                         command=lambda: self.now_playing_sidebar.toggle())
        self.btn_sidebar.pack(side="left", padx=(10, 0))

        
        # Efeito Hover no Seeker (estilo Spotify)
        def on_enter_seeker(e):
            self.seeker.configure(height=8)
        def on_leave_seeker(e):
            self.seeker.configure(height=4)
        
        self.seeker.bind("<Enter>", on_enter_seeker)
        self.seeker.bind("<Leave>", on_leave_seeker)
        
        self.after(500, self.update_player_loop)
        
    def set_volume(self, value):
        self.player.set_volume(value)
        self.config_manager.set("volume", value)
        if value > 0:
            self.is_muted = False
            self.btn_mute.configure(text="🔈")
            self.last_volume = value

    def toggle_mute(self):
        if not self.is_muted:
            self.last_volume = self.vol_slider.get()
            self.set_volume(0)
            self.vol_slider.set(0)
            self.btn_mute.configure(text="🔇")
            self.is_muted = True
        else:
            vol = self.last_volume if self.last_volume > 0 else 0.5
            self.set_volume(vol)
            self.vol_slider.set(vol)
            self.btn_mute.configure(text="🔈")
            self.is_muted = False

    def seek_song(self, value):
        # value is 0-100 (percentage)
        dur = self.player.get_duration()
        if dur > 0:
            pos = (value / 100.0) * dur
            self.player.set_position(pos)

    def toggle_shuffle(self):
        self.player.shuffle = not self.player.shuffle
        color = "#2ecc71" if self.player.shuffle else "#b3b3b3"
        self.btn_shuffle.configure(text_color=color)
        if hasattr(self, 'full_screen_player'):
            self.full_screen_player.update_shuffle_state(self.player.shuffle)
        print(f"[Main] Shuffle: {self.player.shuffle}")

    def toggle_repeat(self):
        # Modes: 0 (off), 1 (song), 2 (all)
        self.player.repeat_mode = (self.player.repeat_mode + 1) % 3
        modes = ["🔁 Off", "🔂 One", "🔁 All"]
        color = "#2ecc71" if self.player.repeat_mode > 0 else "#b3b3b3"
        self.btn_repeat.configure(text=modes[self.player.repeat_mode], text_color=color)
        if hasattr(self, 'full_screen_player'):
            self.full_screen_player.update_repeat_state(self.player.repeat_mode)
        print(f"[Main] Repeat Mode: {self.player.repeat_mode}")

    def _sync_playing_status(self):
        """Notifica todas as views na cache para atualizar o status visual das listas de músicas"""
        active_song = self.current_song
        is_playing = self.player.playing and not self.player.paused
        if not active_song: return
        
        # Atualiza a view atual se ela tiver o método
        if hasattr(self, 'current_view') and hasattr(self.current_view, 'update_playing_status'):
            try:
                self.current_view.update_playing_status(active_song, is_playing)
            except TypeError:
                # Fallback para views não atualizadas ainda
                self.current_view.update_playing_status(active_song)
        
        # Opcionalmente: Atualizar todas em cache (pesado se forem muitas, mas garante consistência)
        # for v in self.view_cache.values():
        #     if hasattr(v, 'update_playing_status'):
        #         v.update_playing_status(active_song)

    def toggle_favorite_current(self):
        if self.current_song:
            path = self.current_song.get('file_path')
            # Now returns True/False
            is_fav = self.db.toggle_favorite(path)
            
            # Update internal state so it persists if we re-play
            self.current_song['favorite'] = 1 if is_fav else 0
            
            color = RED_ACCENT if is_fav else "#555"
            self.btn_fav.configure(text_color=color)
            
            # Sync with FullScreenPlayer
            if hasattr(self, 'full_screen_player'):
                self.full_screen_player.update_favorite_state(is_fav)
            
            # Notify current view if it's favorites
            if hasattr(self, 'current_view') and hasattr(self.current_view, 'load_musics'):
                if self.current_view.__class__.__name__ == "FavoritesView":
                    self.current_view.load_musics()

    def update_player_loop(self):
        if self.player.playing and not self.player.paused:
            import pygame
            if not pygame.mixer.music.get_busy():
                if self.current_song:
                    self.played_songs.add(self.current_song.get('file_path'))
                    self._sync_playing_status()
                self.play_next(auto=True)
            else:
                pos = self.player.get_position()
                dur = self.player.get_duration()
                
                if dur > 0:
                    pct = (pos / dur) * 100
                    self.seeker.set(pct)
                    
                    # Format time
                    def fmt(sec):
                        m, s = divmod(int(sec), 60)
                        return f"{m}:{s:02d}"
                    
                    self.time_lbl.configure(text=f"{fmt(pos)} / {fmt(dur)}")
                    
                    # Sync FullScreenPlayer
                    if self.full_screen_player.winfo_ismapped():
                        self.full_screen_player.update_progress(pos, dur)

                    # Sync Current View (como ArtistDetails)
                    if hasattr(self, 'current_view') and hasattr(self.current_view, 'update_progress'):
                        self.current_view.update_progress(pos, dur)
                
        self.after(1000, self.update_player_loop)

    def toggle_play_pause(self):
        if self.player.playing and not self.player.paused:
            self.player.pause()
            self.btn_play_pause.configure(text="▶")
        elif self.player.paused:
            self.player.play()
            self.btn_play_pause.configure(text="⏸")
        
        # Sincroniza barras de reprodução em todas as telas
        self.full_screen_player.update_play_state(self.player.playing and not self.player.paused)
        self._sync_playing_status()
            
    def play_next(self, auto=False):
        if not self.player.playlist: return
        
        # If repeat song is on and it's auto-next, just replay current
        if auto and self.player.repeat_mode == 1:
            self.player.set_position(0)
            self.player.play()
            return

        if self.player.shuffle and len(self.player.playlist) > 1:
            import random
            choices = [i for i in range(len(self.player.playlist)) if i != self.player.current_index]
            nxt_idx = random.choice(choices)
        elif self.player.shuffle:
            nxt_idx = 0
        else:
            nxt_idx = self.player.current_index + 1
            if nxt_idx >= len(self.player.playlist):
                if self.player.repeat_mode == 2: # Repeat all
                    nxt_idx = 0
                else:
                    self.player.stop()
                    self.btn_play_pause.configure(text="▶")
                    self.seeker.set(0)
                    self.time_lbl.configure(text="0:00 / 0:00")
                    return # Stop
        
        self.player.current_index = nxt_idx
        path = self.player.playlist[nxt_idx]
        m = self.db.find_by_path(path)
        if m: self.play_song(m, flow_type=self.active_flow)
                    
    def play_prev(self):
        if self.player.playlist:
            if self.player.current_index > 0:
                prv_idx = self.player.current_index - 1
            else:
                # If repeat all is on, go to last, else restart current
                if self.player.repeat_mode == 2:
                    prv_idx = len(self.player.playlist) - 1
                else:
                    prv_idx = 0
            
            path = self.player.playlist[prv_idx]
            m = self.db.find_by_path(path)
            if m: self.play_song(m, flow_type=self.active_flow)

    def play_song(self, song_data, items_list=None, flow_type=None):
        # Determine more descriptive flow_type if not provided
        if not flow_type:
            if hasattr(self, 'current_view'):
                view_name = self.current_view.__class__.__name__
                if "Favorites" in view_name: 
                    flow_type = "Favoritos"
                elif "Search" in view_name: 
                    flow_type = "Busca"
                elif "Artist" in view_name or "ArtistDetails" in view_name: 
                    # If we are in artist details, use artist name from view if available
                    if hasattr(self.current_view, 'artist_name'):
                        flow_type = self.current_view.artist_name
                    else:
                        flow_type = song_data.get('artist', 'Artista')
                elif "Playlist" in view_name: 
                    # If we are in playlist view, use playlist name
                    if hasattr(self.current_view, 'current_playlist') and self.current_view.current_playlist:
                        flow_type = f"Playlist {self.current_view.current_playlist.get('name', '')}"
                    else:
                        flow_type = "Playlist"
                else: 
                    flow_type = "BeatSound"
        
        self.active_flow = flow_type
        # song_data can be a dict (from DB) or just a file_path string (from playlist next)
        if isinstance(song_data, str):
            file_path = song_data
            # If it's a string, try to find full metadata in DB
            m = self.db.find_by_path(file_path)
            if m: song_data = m
            else:
                song_data = {'file_path': file_path, 'title': os.path.basename(file_path), 'artist': 'Unknown'}
        else:
            file_path = song_data.get('file_path')

        if not file_path: return
        
        try:
            # Reconstruct the paths-only playlist if needed
            if items_list:
                new_playlist = []
                for item in items_list:
                    try:
                        if isinstance(item, (list, tuple)) and len(item) >= 4:
                            # Handling the format used in PlaylistView/FavoritesView: (artist, title, color, data_dict)
                            # Actually line 341 had len(item) > 3, but len >= 4 is safer
                            path = item[3].get('file_path') if isinstance(item[3], dict) else None
                        elif isinstance(item, dict):
                            path = item.get('file_path')
                        else:
                            path = str(item)
                        if path:
                            new_playlist.append(path) 
                    except: continue
                if new_playlist:
                    self.player.playlist = new_playlist
            
            # Ensure we have a valid playlist and current index
            if not self.player.playlist:
                self.player.playlist = [file_path]
                self.player.current_index = 0
            elif file_path in self.player.playlist:
                self.player.current_index = self.player.playlist.index(file_path)
            else:
                # Append if not in list
                self.player.playlist.append(file_path)
                self.player.current_index = len(self.player.playlist) - 1
                
            self.player.load(file_path)
            self.player.play()
            self.current_song = song_data
            
            # Atualiza estatísticas no banco (Recentemente tocadas, mais tocadas)
            self.db.update_play_stats(file_path)
            
            # UI Updates
            title = str(song_data.get('title') or "Unknown Title")
            artist = str(song_data.get('artist') or "Unknown Artist")
            title = (title[:18] + '..') if len(title) > 20 else title
            artist = (artist[:18] + '..') if len(artist) > 20 else artist
            
            self.lbl_title.configure(text=title)
            self.lbl_artist.configure(text=artist)
            self.btn_play_pause.configure(text="⏸")
            self.full_screen_player.update_play_state(True)
            
            # Sync any view that shows the currently playing song's info
            if hasattr(self, 'current_view') and hasattr(self.current_view, 'update_playing_info'):
                self.current_view.update_playing_info(song_data)
            
            # Update favorite button state
            is_fav = song_data.get('favorite', 0)
            color = RED_ACCENT if is_fav else "#555"
            self.btn_fav.configure(text_color=color)
            
            # Notificar todas as views abertas para sincronizar o status de "tocando"
            self._sync_playing_status()
            self.full_screen_player.update_track(song_data)
            
            # Load cover
            c_path = song_data.get('cover_path')
            import os
            from PIL import Image
            
            def set_placeholder():
                self.lbl_cover.configure(image=None, text="🎵", font=("Segoe UI", 24))
            
            if c_path:
                # Try multiple resolution strategies
                base_dir = os.path.dirname(os.path.abspath(__file__))
                possible_paths = [
                    c_path,
                    os.path.join(base_dir, c_path) if not os.path.isabs(c_path) else c_path,
                    os.path.join(base_dir, "assets", "covers", os.path.basename(c_path))
                ]
                valid_path = None
                for p in possible_paths:
                    if os.path.exists(p):
                        valid_path = p
                        break
                
                if valid_path:
                    try:
                        pil_img = Image.open(valid_path).convert("RGBA")
                        # Crop to square
                        w, h = pil_img.size
                        m_min = min(w, h)
                        left = (w - m_min) / 2
                        top = (h - m_min) / 2
                        pil_img = pil_img.crop((left, top, left + m_min, top + m_min))
                        
                        self.current_cover_obj = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 60))
                        self.lbl_cover.configure(image=self.current_cover_obj, text="")
                    except Exception as img_err:
                        print(f"Error loading cover image: {img_err}")
                        set_placeholder()
                else:
                    set_placeholder()
            
            # Update Now Playing Sidebar if expanded
            if self.now_playing_sidebar and self.now_playing_sidebar.winfo_exists():
                if self.now_playing_sidebar.is_expanded:
                    self.now_playing_sidebar.update_track(song_data)
                # Highlight sidebar toggle button
                self.btn_sidebar.configure(text_color=RED_ACCENT if self.now_playing_sidebar.is_expanded else "#555")
            else:
                set_placeholder()

            # Sync cover with current active view (e.g. Favorites, Playlist)
            if hasattr(self, 'current_view') and hasattr(self.current_view, 'update_playing_info'):
                self.current_view.update_playing_info(song_data)

        except Exception as e:
            print("Error parsing file to play:", e)
            
    def set_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self.config_manager.set("appearance_mode", mode)
        print(f"[+] Tema alterado para: {mode}")

    def navigate_to(self, view_name, data=None):
        # Atualiza o estado visual dos botões do menu lateral
        if hasattr(self, 'sidebar_btns'):
            for btn in self.sidebar_btns:
                is_active = (btn.view_name == view_name)
                # Refinamento para botões que compartilham a mesma view (como batch)
                if is_active and data and btn.data:
                    if isinstance(data, dict) and isinstance(btn.data, dict):
                        is_active = (data.get('mode') == btn.data.get('mode'))
                btn.set_active(is_active)

        # Esconder a tela atual se existir (sem destruir)
        if hasattr(self, 'current_view') and self.current_view:
            self.current_view.pack_forget()
            
        # Determinar se devemos usar cache ou criar novo
        # Views que precisam ser sempre novas (editores, detalhes, buscas e telas com carga assíncrona)
        dynamic_views = ["batch", "editor", "artist", "search", "manager", "playlists", "download"]
        
        if view_name in self.view_cache and view_name not in dynamic_views:
            self.current_view = self.view_cache[view_name]
            self.current_view.pack(side="top", fill="both", expand=True)
            
            # Refresh stats whenever we navigate back to it
            if view_name == "stats" and hasattr(self.current_view, "load_stats"):
                self.current_view.load_stats()
        else:
            # Criar nova view
            from modules.home_view import HomeView
            from modules.search_view import SearchView
            from modules.categories_view import CategoriesView
            from modules.favorites_view import FavoritesView
            from modules.artist_details import ArtistDetails
            from modules.batch_editor import BatchEditor
            from modules.tag_editor import TagEditor
            
            # Se já existir uma dinâmica na cache que vamos sobrescrever, destrói
            if view_name in dynamic_views and view_name in self.view_cache:
                self.view_cache[view_name].destroy()

            if view_name == "home":
                v = HomeView(self.main_area, self)
            elif view_name == "search":
                v = SearchView(self.main_area, self)
            elif view_name == "categories":
                v = CategoriesView(self.main_area, self)
            elif view_name == "playlists":
                from modules.playlist_view import PlaylistView
                v = PlaylistView(self.main_area, self)
            elif view_name == "favorites":
                v = FavoritesView(self.main_area, self)
            elif view_name == "stats":
                from modules.stats_view import StatsView
                v = StatsView(self.main_area, self)
            elif view_name == "settings":
                from modules.settings_view import SettingsView
                v = SettingsView(self.main_area, self)
            elif view_name == "batch":
                # Se data for um dict {"mode": "xxx"}, extraímos o modo
                mode = data.get("mode", "single") if isinstance(data, dict) else (data or "single")
                songs = data.get("songs") if isinstance(data, dict) else None
                v = BatchEditor(self.main_area, self, mode=mode)
                if songs:
                    v.load_from_songs(songs)
            elif view_name == "editor":
                v = TagEditor(self.main_area, self, track=data)
            elif view_name == "artist":
                v = ArtistDetails(self.main_area, self, data)
            elif view_name == "manager":
                from modules.library_manager_view import LibraryManagerView
                v = LibraryManagerView(self.main_area, self, initial_folder=data)
            elif view_name == "download":
                from modules.download_view import DownloadView
                v = DownloadView(self.main_area, self)
            else:
                return

            v.pack(side="top", fill="both", expand=True)
            self.current_view = v
            # Guardar na cache
            self.view_cache[view_name] = v

        # --- Lógica de Visibilidade da Barra "Tocando Agora" ---
        views_sem_sidebar = ["home", "playlists", "artist", "editor", "batch", "manager", "download", "settings"]
        if hasattr(self, 'now_playing_sidebar') and self.now_playing_sidebar:
            if view_name in views_sem_sidebar:
                # Se estiver aberta, fecha antes de esconder
                if self.now_playing_sidebar.is_expanded:
                    self.now_playing_sidebar.toggle()
                
                # Esconde os gatilhos (handle e botão na barra do player)
                if hasattr(self, 'sidebar_handle'):
                    self.sidebar_handle.place_forget()
                if hasattr(self, 'btn_sidebar'):
                    self.btn_sidebar.pack_forget()
            else:
                # Restaura os gatilhos nas outras telas
                if hasattr(self, 'btn_sidebar') and not self.btn_sidebar.winfo_ismapped():
                    self.btn_sidebar.pack(side="left", padx=(10, 0))
                
                if hasattr(self, 'sidebar_handle'):
                    # Reposiciona o handle dependendo do estado da barra
                    rx = 0.64 if self.now_playing_sidebar.is_expanded else 0.99
                    self.sidebar_handle.place(relx=rx, rely=0.4, anchor="center")

    def notify_data_changed(self):
        """Notifica todas as abas que os dados mudaram (ex: após scan)"""
        # Se a aba atual tiver método de refresh, recarrega
        if hasattr(self, 'current_view'):
            if hasattr(self.current_view, 'is_dashboard') and self.current_view.is_dashboard:
                self.current_view.load_dashboard(force=True)
            elif hasattr(self.current_view, 'load_musics'):
                self.current_view.load_musics()
            
            if hasattr(self.current_view, 'load_stats'):
                self.current_view.load_stats()

if __name__ == "__main__":
    try:
        app = BeatSoundSearch()
        app.mainloop()
    except Exception as e:
        import traceback
        error_msg = f"CRITICAL STARTUP ERROR:\n{e}\n\n{traceback.format_exc()}"
        print(error_msg)
        
        # Tenta mostrar uma caixa de mensagem mesmo se o CustomTkinter falhar
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Erro de Inicialização", 
                                 f"O app encontrou um erro crítico e não pôde iniciar.\n\n"
                                 f"Detalhes salvos em: logs/runtime_error.log\n\n"
                                 f"Erro: {str(e)[:200]}...")
            root.destroy()
        except:
            pass
        sys.exit(1)
