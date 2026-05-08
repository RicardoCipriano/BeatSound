import customtkinter as ctk
from CTkTable import CTkTable
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np


class StatsView(ctk.CTkFrame):
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        
        # Usar ColorBlind para melhor compatibilidade
        plt.style.use('dark_background')
        
        # Header
        header = ctk.CTkLabel(self, text="📊 Estatísticas", font=("Segoe UI", 20, "bold"))
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        # Cards de resumo
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=15, pady=10)
        
        self.create_summary_cards(cards_frame)
        
        # Gráficos
        graphs_frame = ctk.CTkFrame(self)
        graphs_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Gráfico pizza (esquerda)
        left_frame = ctk.CTkFrame(graphs_frame, fg_color="#2d2d2d")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(left_frame, text="Distribuição por Gênero", font=("Segoe UI", 12, "bold")).pack(pady=10)
        self.create_pie_chart(left_frame)
        
        # Gráfico barras (direita)
        right_frame = ctk.CTkFrame(graphs_frame, fg_color="#2d2d2d")
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        ctk.CTkLabel(right_frame, text="Músicas por Década", font=("Segoe UI", 12, "bold")).pack(pady=10)
        self.create_bar_chart(right_frame)
        
        # Divisor
        ctk.CTkFrame(self, height=1, fg_color="#3d3d3d").pack(fill="x", pady=5)
        
        # Tabela "Mais Tocadas"
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(bottom_frame, text="🎵 Top 10 Músicas Mais Tocadas", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=10)
        
        table_scroll = ctk.CTkScrollableFrame(bottom_frame)
        table_scroll.pack(fill="both", expand=True)
        
        table_data = [
            ["#", "Título", "Artista", "Reproduções", "Horas"],
            ["1", "Hit Song 1", "Artist A", "2,145", "142h"],
            ["2", "Hit Song 2", "Artist B", "1,998", "133h"],
            ["3", "Hit Song 3", "Artist C", "1,876", "125h"],
            ["4", "Hit Song 4", "Artist D", "1,654", "110h"],
            ["5", "Hit Song 5", "Artist E", "1,523", "101h"],
            ["6", "Hit Song 6", "Artist F", "1,412", "94h"],
            ["7", "Hit Song 7", "Artist G", "1,301", "87h"],
            ["8", "Hit Song 8", "Artist H", "1,190", "79h"],
            ["9", "Hit Song 9", "Artist I", "1,087", "72h"],
            ["10", "Hit Song 10", "Artist J", "1,001", "67h"],
        ]
        
        self.table = CTkTable(table_scroll, values=table_data, command=self.table_callback)
        self.table.pack(fill="both", expand=True)
    
    def create_summary_cards(self, parent):
        """Criar cards de resumo com 4 colunas"""
        cards_data = [
            ("🎵 Total de Músicas", "1,247"),
            ("⏱️ Horas Tocadas", "2,156h"),
            ("🎤 Total de Artistas", "512"),
            ("💿 Total de Álbuns", "321")
        ]
        
        for title, value in cards_data:
            card = ctk.CTkFrame(parent, fg_color="#2d2d2d", corner_radius=8)
            card.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 10)).pack(pady=(10, 5), padx=10)
            ctk.CTkLabel(card, text=value, font=("Segoe UI", 16, "bold"), text_color="#2ecc71").pack(pady=(0, 10), padx=10)
    
    def create_pie_chart(self, parent):
        """Criar gráfico pizza com distribuição de gêneros"""
        fig = Figure(figsize=(5, 4), dpi=100, facecolor='#2d2d2d')
        ax = fig.add_subplot(111, facecolor='#2d2d2d')
        
        genres = ['Rock', 'Pop', 'Jazz', 'Clássico', 'Eletrônico', 'Outros']
        sizes = [30, 25, 15, 12, 10, 8]
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#95a5a6']
        
        ax.pie(sizes, labels=genres, autopct='%1.1f%%', colors=colors, startangle=90)
        ax.axis('equal')
        
        # Remover labels de cor padrão
        for text in ax.texts:
            text.set_color('white')
            text.set_fontsize(9)
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_bar_chart(self, parent):
        """Criar gráfico barras com músicas por década"""
        fig = Figure(figsize=(5, 4), dpi=100, facecolor='#2d2d2d')
        ax = fig.add_subplot(111, facecolor='#2d2d2d')
        
        decades = ['1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
        counts = [45, 120, 210, 320, 380, 172]
        
        bars = ax.bar(decades, counts, color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c'])
        
        # Configurar labels
        ax.set_ylabel('Número de Músicas', color='white', fontsize=10)
        ax.set_xlabel('Década', color='white', fontsize=10)
        ax.tick_params(colors='white')
        
        # Remover spines
        for spine in ax.spines.values():
            spine.set_color('#3d3d3d')
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def table_callback(self, value):
        print(f"Table clicked: {value}")
