import customtkinter as ctk

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#121212")
        self.controller = controller
        self.config = controller.config_manager
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=30, pady=20)
        
        lbl = ctk.CTkLabel(self.header, text="⚙️ Configurações", font=("Segoe UI", 32, "bold"), text_color="white")
        lbl.pack(side="left")
        
        # Save Button
        ctk.CTkButton(self.header, text="Salvar Alterações", fg_color="#c3000d", hover_color="#9a000a",
                      corner_radius=8, height=40, font=("Segoe UI", 14, "bold"), command=self.save_settings).pack(side="right")

        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="#181818", segmented_button_selected_color="#c3000d",
                                     segmented_button_unselected_hover_color="#2b2b2b")
        self.tabview.pack(padx=30, pady=10, expand=True, fill="both")
        
        self.tabview.add("Geral")
        self.tabview.add("Aparência")
        self.tabview.add("Bibliotecas")
        
        # Tab Appearance
        app_tab = self.tabview.tab("Aparência")
        ctk.CTkLabel(app_tab, text="Tema do Aplicativo", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        current_mode = self.config.get("appearance_mode").capitalize()
        self.theme_menu = ctk.CTkOptionMenu(app_tab, values=["Dark", "Light"], 
                                          fg_color="#2b2b2b", button_color="#c3000d", button_hover_color="#9a000a",
                                          command=self.change_theme_instant)
        self.theme_menu.pack(anchor="w", padx=20, pady=5)
        self.theme_menu.set(current_mode)
        
        # Tab Geral
        gen_tab = self.tabview.tab("Geral")
        ctk.CTkLabel(gen_tab, text="Volume Padrão", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        self.vol_slider = ctk.CTkSlider(gen_tab, from_=0, to=1, progress_color="#c3000d",
                                        button_color="#c3000d")
        self.vol_slider.pack(anchor="w", padx=20, pady=5)
        self.vol_slider.set(self.config.get("volume"))
        
        # Backup Area
        ctk.CTkLabel(gen_tab, text="Backup e Migração (JSON)", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(40, 10))
        b_frame = ctk.CTkFrame(gen_tab, fg_color="transparent")
        b_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(b_frame, text="📤 Exportar Backup", width=180, fg_color="#2ecc71", hover_color="#27ae60",
                      command=self.export_backup).pack(side="left", padx=5)
        ctk.CTkButton(b_frame, text="📥 Importar Backup", width=180, fg_color="#3498db", hover_color="#2980b9",
                      command=self.import_backup).pack(side="left", padx=5)

        # Libraries Tab
        lib_tab = self.tabview.tab("Bibliotecas")
        ctk.CTkLabel(lib_tab, text="Caminhos de Música", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        path_frame = ctk.CTkFrame(lib_tab, fg_color="#2b2b2b", corner_radius=8)
        path_frame.pack(fill="x", padx=20, pady=5)
        
        current_path = self.config.get("music_dir")
        self.lbl_path = ctk.CTkLabel(path_frame, text=current_path, padx=15, pady=10)
        self.lbl_path.pack(side="left")
        
        ctk.CTkButton(path_frame, text="Mapear", width=80, height=32, fg_color="#c3000d", hover_color="#9a000a",
                      command=self.browse_music_dir).pack(side="right", padx=10)

    def browse_music_dir(self):
        from tkinter import filedialog
        new_dir = filedialog.askdirectory(initialdir=self.config.get("music_dir"))
        if new_dir:
            self.config.set("music_dir", new_dir)
            self.lbl_path.configure(text=new_dir)
            print(f"[+] Novo diretório de música: {new_dir}")

    def change_theme_instant(self, mode):
        self.controller.set_theme(mode.lower())

    def save_settings(self):
        vol = self.vol_slider.get()
        self.config.set("volume", vol)
        self.controller.player.set_volume(vol)
        print("[+] Configurações salvas.")

    def export_backup(self):
        # Placeholder for export logic
        import json, os
        from tkinter import filedialog
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if file:
            data = self.controller.db.get_all_musics(limit=1000000)
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"[+] Backup exportado: {file}")

    def import_backup(self):
        # Placeholder for import logic
        from tkinter import filedialog
        file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if file:
            print(f"[+] Backup importado de: {file}")
            # Logic to merge with DB would go here
