import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
from tkinter import messagebox
import os
import threading
matplotlib.use("TkAgg")

class StatsView(ctk.CTkScrollableFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#0a0a0a", corner_radius=0)
        self.controller = controller
        self.setup_ui()
        self.load_stats()
        
    def setup_ui(self):
        # Header Section
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=40, pady=(30, 20))
        
        info_f = ctk.CTkFrame(self.header, fg_color="transparent")
        info_f.pack(side="left")
        
        ctk.CTkLabel(info_f, text="Insights da Biblioteca", 
                     font=("Segoe UI", 36, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(info_f, text="Visualize tendências, gêneros e o perfil da sua coleção musical", 
                     font=("Segoe UI", 15), text_color="#71717a").pack(anchor="w")
        
        # Action Buttons
        actions_f = ctk.CTkFrame(self.header, fg_color="transparent")
        actions_f.pack(side="right", pady=10)
        
        self.btn_export = ctk.CTkButton(actions_f, text="📤 Exportar Relatório", width=140, height=35,
                                        fg_color="transparent", border_width=1, border_color="#2b2b2b",
                                        hover_color="#1a1a1a", command=self.export_stats)
        self.btn_export.pack(side="right", padx=10)
        
        self.btn_refresh = ctk.CTkButton(actions_f, text="🔄 Atualizar Dashboard", width=140, height=35, 
                                        fg_color="#c3000d", hover_color="#9a000a", 
                                        font=("Segoe UI", 13, "bold"), command=self.load_stats)
        self.btn_refresh.pack(side="right")
        
        # Separation Line
        ctk.CTkFrame(self, height=1, fg_color="#2b2b2b").pack(fill="x", padx=40, pady=10)
        
        # Grid System for Stats
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=40, pady=(10, 40))
        
    def load_stats(self):
        # Clean container before reload
        for widget in self.main_container.winfo_children():
            widget.destroy()
            
        stats = self.controller.db.get_stats()
        
        # 1. Metric Cards Row (Shadcn style)
        cards_f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        cards_f.pack(fill="x", pady=(0, 25))
        
        hrs = int(stats['total_duration'] // 3600)
        
        metrics = [
            ("Tracklist", f"{stats['total']:,}", "🎧", "músicas catalogadas"),
            ("Artistas", f"{stats['artists']:,}", "🎤", "autores únicos"),
            ("Álbuns", f"{stats['albums']:,}", "💿", "discos na coleção"),
            ("Favoritas", f"{stats['favorites']:,}", "❤️", "músicas marcadas"),
            ("Reproduções", f"{stats['total_plays']:,}", "📈", "total de plays"),
            ("Playtime", f"{hrs}h", "🕒", "estimado")
        ]
        
        for title, val, icon, desc in metrics:
            card = self.create_metric_card(cards_f, title, val, icon, desc)
            card.pack(side="left", fill="both", expand=True, padx=6)

        # 2. Charts Layout (Side by Side)
        charts_r1 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        charts_r1.pack(fill="x", pady=5)
        
        # Decade Distribution (Bar Chart) - Occupies 55%
        self.create_decade_chart(charts_r1, stats['decades']).pack(side="left", fill="both", expand=True, padx=(0, 12))
        
        # Genre Distribution (Pie Chart) - Occupies 45%
        self.create_genre_chart(charts_r1, stats['top_genres']).pack(side="left", fill="both", expand=True)
        
        # 3. Artist Leaderboard (Full Width)
        self.create_top_artists_chart(self.main_container, stats['top_artists']).pack(fill="both", expand=True, pady=(20, 0))

    def create_metric_card(self, parent, title, value, icon, desc):
        card = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=12, border_width=1, border_color="#2b2b2b")
        
        # Content with padding
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(padx=20, pady=20, fill="both")
        
        top = ctk.CTkFrame(content, fg_color="transparent")
        top.pack(fill="x")
        
        ctk.CTkLabel(top, text=title, font=("Segoe UI", 13, "bold"), text_color="#b3b3b3").pack(side="left")
        ctk.CTkLabel(top, text=icon, font=("Segoe UI", 16)).pack(side="right")
        
        ctk.CTkLabel(content, text=value, font=("Segoe UI", 32, "bold"), text_color="white").pack(anchor="w", pady=(8, 2))
        ctk.CTkLabel(content, text=desc, font=("Segoe UI", 11), text_color="#71717a").pack(anchor="w")
        
        return card

    def create_decade_chart(self, parent, data):
        frame = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=12, border_width=1, border_color="#2b2b2b")
        ctk.CTkLabel(frame, text="Cronologia Musical", font=("Segoe UI", 18, "bold"), text_color="white").pack(pady=(20, 5))
        ctk.CTkLabel(frame, text="Distribuição de faixas por década de lançamento", font=("Segoe UI", 12), text_color="#71717a").pack()
        
        if not data:
            ctk.CTkLabel(frame, text="Nenhum dado de data encontrado", text_color="#555").pack(pady=80)
            return frame

        labels = [d['decade'] for d in data]
        values = [d['count'] for d in data]
        
        fig, ax = plt.subplots(figsize=(5, 3.5), dpi=100)
        fig.patch.set_facecolor('#121212')
        ax.set_facecolor('#121212')
        
        bars = ax.bar(labels, values, color='#c3000d', alpha=0.9, width=0.6,
                      edgecolor='#ffffff', linewidth=0.3)
        
        ax.tick_params(axis='x', colors='#a1a1aa', labelsize=9)
        ax.tick_params(axis='y', colors='#a1a1aa', labelsize=8)
        
        ax.spines['bottom'].set_color('#2b2b2b')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#2b2b2b')
        ax.yaxis.grid(True, linestyle='--', alpha=0.1, color='white')
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)
        plt.close(fig)
        
        return frame

    def create_genre_chart(self, parent, data):
        frame = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=12, border_width=1, border_color="#2b2b2b")
        ctk.CTkLabel(frame, text="DNA de Gênero", font=("Segoe UI", 18, "bold"), text_color="white").pack(pady=(20, 5))
        ctk.CTkLabel(frame, text="Seus 5 estilos mais presentes", font=("Segoe UI", 12), text_color="#71717a").pack()
        
        if not data:
            ctk.CTkLabel(frame, text="Nenhum gênero identificado", text_color="#555").pack(pady=80)
            return frame

        labels = [d['genre'] for d in data]
        values = [d['count'] for d in data]
        
        # Modern red palette
        colors = ['#c3000d', '#a0000a', '#7d0008', '#5a0006', '#370004']
        
        fig, ax = plt.subplots(figsize=(4, 3.5), dpi=100)
        fig.patch.set_facecolor('#121212')
        
        # Donut Chart
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.0f%%', 
                                         startangle=140, colors=colors, pctdistance=0.8,
                                         textprops={'color':"w", 'fontsize': 9, 'weight': 'bold'},
                                         wedgeprops={'width': 0.4, 'edgecolor': '#121212'})
        
        # Center text
        # ax.text(0, 0, f"TOP\nGENRES", ha='center', va='center', color='white', font=("Segoe UI", 10, "bold"))
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)
        plt.close(fig)
        
        return frame

    def create_top_artists_chart(self, parent, data):
        frame = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=12, border_width=1, border_color="#2b2b2b")
        ctk.CTkLabel(frame, text="Artistas Dominantes", font=("Segoe UI", 20, "bold"), text_color="white").pack(pady=(25, 5))
        ctk.CTkLabel(frame, text="Ranking por reproduções e volume de faixas na biblioteca", font=("Segoe UI", 13), text_color="#71717a").pack()
        
        if not data:
            return frame

        container = ctk.CTkFrame(frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Decide qual métrica usar para a barra (prioriza plays)
        max_plays = max([d.get('total_plays', 0) for d in data]) if data else 0
        if max_plays > 0:
            max_val = max_plays
            metric_key = 'total_plays'
        else:
            max_val = max([d.get('count', 0) for d in data]) if data else 1
            metric_key = 'count'
        
        for i, artist_data in enumerate(data):
            row = ctk.CTkFrame(container, fg_color="transparent")
            row.pack(fill="x", pady=6)
            
            # 1. Mini Capa (Círculo ou Quadrado Arredondado)
            img_size = (36, 36)
            c_path = artist_data.get('cover_path')
            
            # Placeholder/Cache check (Usamos sufixo _small para não conflitar com capas grandes)
            cache_key = f"{c_path}_small"
            img_obj = None
            if c_path and cache_key in self.controller.image_cache:
                img_obj = self.controller.image_cache[cache_key]
            
            art_lbl = ctk.CTkLabel(row, text="🎤" if not img_obj else "", image=img_obj,
                                   width=img_size[0], height=img_size[1])
            art_lbl.pack(side="left", padx=(0, 15))
            
            if not img_obj and c_path and isinstance(c_path, str):
                def load_img(path, lbl, key):
                    resolved_path = self.controller.resolve_image_path(path)
                    if not resolved_path: return
                    from PIL import Image
                    try:
                        pil_img = Image.open(resolved_path).convert("RGBA")
                        pil_img = pil_img.resize(img_size, Image.Resampling.LANCZOS)
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=img_size)
                        self.controller.image_cache[key] = ctk_img
                        if lbl.winfo_exists():
                            self.after(0, lambda: lbl.configure(image=ctk_img, text=""))
                    except: pass
                
                threading.Thread(target=load_img, args=(c_path, art_lbl, cache_key), daemon=True).start()

            # 2. Nome do Artista
            name_lbl = ctk.CTkLabel(row, text=artist_data['artist'], font=("Segoe UI", 14, "bold"), 
                                    text_color="white", width=200, anchor="w")
            name_lbl.pack(side="left")
            
            # 3. Barra de Progresso (Representação visual do volume)
            progress_f = ctk.CTkFrame(row, fg_color="transparent")
            progress_f.pack(side="left", fill="x", expand=True, padx=20)
            
            ratio = artist_data.get(metric_key, 0) / max_val
            bar = ctk.CTkProgressBar(progress_f, height=8, fg_color="#1a1a1a", progress_color="#c3000d")
            bar.pack(fill="x")
            bar.set(ratio)
            
            # 4. Contador (Plays + Faixas)
            plays = artist_data.get('total_plays', 0)
            count_lbl = ctk.CTkLabel(row, text=f"{plays} plays • {artist_data['count']} faixas", 
                                     font=("Segoe UI", 12), text_color="#71717a", width=150, anchor="e")
            count_lbl.pack(side="right")
            
            # Separator except for last
            if i < len(data) - 1:
                ctk.CTkFrame(container, height=1, fg_color="#1a1a1a").pack(fill="x", pady=4)
        
        return frame

    def export_stats(self):
        messagebox.showinfo("Exportar", "Esta funcionalidade será ativada na próxima versão (Relatório PDF).")
