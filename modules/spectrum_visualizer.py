import customtkinter as ctk
import random

class SpectrumVisualizer(ctk.CTkFrame):
    def __init__(self, master, width=30, height=20, bar_count=4, bar_color="#1DB954", animation_speed=50, **kwargs):
        """
        Visualizador de áudio animado (bars spectrum)
        :param master: Widget pai
        :param width: Largura total
        :param height: Altura total
        :param bar_count: Número de barras verticais
        :param bar_color: Cor das barras
        :param animation_speed: Velocidade do loop em ms
        """
        super().__init__(master, width=width, height=height, fg_color="transparent", **kwargs)
        
        self.bar_count = bar_count
        self.bar_color = bar_color
        self.animation_speed = animation_speed
        self.max_height = height
        self.min_height = 4
        self.is_playing = False
        self.animation_running = False
        
        self.bars = []
        self.current_heights = [self.min_height] * bar_count
        self.target_heights = [self.min_height] * bar_count
        
        # Cálculo de largura e espaçamento
        spacing = 2
        total_spacing = spacing * (bar_count - 1)
        bar_width = max(2, (width - total_spacing) // bar_count)
        
        for i in range(bar_count):
            bar = ctk.CTkFrame(
                self, 
                width=bar_width, 
                height=self.min_height, 
                fg_color=bar_color, 
                corner_radius=1
            )
            # Anchor "sw" faz crescer para cima a partir do fundo
            bar.place(x=i * (bar_width + spacing), y=height, anchor="sw")
            self.bars.append(bar)
            
    def update_playback_status(self, is_playing):
        """Ativa ou desativa a animação baseado no status do player"""
        self.is_playing = is_playing
        
        if is_playing:
            if not self.animation_running:
                self.animation_running = True
                self._animate()
        else:
            # Quando parado, as barras voltam ao tamanho mínimo
            self.animation_running = False
            for i, bar in enumerate(self.bars):
                bar.configure(height=self.min_height)
                self.current_heights[i] = self.min_height
                self.target_heights[i] = self.min_height
                
    def _animate(self):
        """Loop de animação suave"""
        if not self.is_playing or not self.winfo_exists():
            self.animation_running = False
            return
            
        for i in range(self.bar_count):
            # Se chegou perto do target, define um novo aleatório
            if abs(self.current_heights[i] - self.target_heights[i]) < 2:
                self.target_heights[i] = random.randint(self.min_height, self.max_height)
            
            # Interpolação simples para movimento suave
            step = (self.target_heights[i] - self.current_heights[i]) * 0.3
            self.current_heights[i] += step
            
            try:
                self.bars[i].configure(height=int(self.current_heights[i]))
            except: pass
            
        self.after(self.animation_speed, self._animate)

class SoundCloudVisualizer(ctk.CTkCanvas):
    def __init__(self, master, width=800, height=60, bar_color="#b3b3b3", progress_color="#ff5500", **kwargs):
        """
        Visualizador estilo SoundCloud com barras estáticas que mudam de cor com o progresso.
        """
        super().__init__(master, width=width, height=height, bg="#121212", highlightthickness=0, **kwargs)
        self.bar_color = bar_color
        self.progress_color = progress_color
        self.max_height = height
        self.bar_width = 3
        self.spacing = 2
        self.progress = 0 # 0.0 a 1.0
        
        self.waveform_data = [] # Alturas das barras
        self._generate_pseudo_waveform()
        
        self.bind("<Configure>", lambda e: self.redraw())

    def _generate_pseudo_waveform(self):
        # Gera alturas aleatórias mas suaves para simular uma música
        self.waveform_data = []
        last_h = random.randint(10, self.max_height - 10)
        for _ in range(300): # Máximo de barras possíveis
            h = last_h + random.randint(-8, 8)
            h = max(10, min(h, self.max_height - 5))
            self.waveform_data.append(h)
            last_h = h

    def set_progress(self, progress):
        """Define o progresso da barra (0.0 a 1.0)"""
        self.progress = max(0.0, min(1.0, progress))
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10: return
        
        num_bars = w // (self.bar_width + self.spacing)
        progress_limit = int(num_bars * self.progress)
        
        for i in range(num_bars):
            # Altura da barra principal
            bar_h = self.waveform_data[i % len(self.waveform_data)]
            
            # Cor baseada no progresso
            color = self.progress_color if i < progress_limit else self.bar_color
            
            x0 = i * (self.bar_width + self.spacing)
            x1 = x0 + self.bar_width
            
            # Desenha a barra superior (principal)
            y_top = (h * 0.7) - bar_h * 0.6
            y_bottom = h * 0.7
            self.create_rectangle(x0, y_top, x1, y_bottom, fill=color, outline="")
            
            # Desenha o reflexo inferior (menor e mais escuro)
            ref_h = bar_h * 0.3
            ry_top = h * 0.7 + 2
            ry_bottom = ry_top + ref_h
            
            # Cor do reflexo (um pouco mais transparente/escura)
            self.create_rectangle(x0, ry_top, x1, ry_bottom, fill=color, outline="", stipple="gray50" if i >= progress_limit else "")
