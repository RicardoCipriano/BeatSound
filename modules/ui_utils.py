from PIL import Image, ImageDraw
import customtkinter as ctk

class UIUtils:
    @staticmethod
    def create_gradient_image(width, height, top_color_hex, bottom_color_hex):
        """Gera uma imagem CTkImage com degradê vertical 'premium' entre duas cores."""
        def hex_to_rgb(hex_str):
            hex_str = hex_str.lstrip('#')
            if len(hex_str) == 3:
                hex_str = ''.join([c*2 for c in hex_str])
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

        c1 = hex_to_rgb(top_color_hex)
        c2 = hex_to_rgb(bottom_color_hex)
        
        # Para um visual mais profissional, usamos 3-4 stops e interpolação não-linear
        canvas = Image.new('RGB', (1, height), c2)
        pixels = canvas.load()
        
        for y in range(height):
            # Curva de transição suave (Power scaling)
            # y/height vai de 0 a 1. 
            # ratio = (y/height)**1.5 mantém a cor do topo um pouco mais, depois desce suavemente.
            ratio = (y / height) ** 1.5
            
            # Interpolação ponderada: 
            # No topo, queremos a cor vibrante. 
            # No meio, queremos um 'glow' atenuado.
            # No final, queremos o fundo escuro absoluto.
            
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            pixels[0, y] = (r, g, b)
        
        # Redimensionar para a largura final com alta qualidade
        # Adiciona um pouco de largura extra para evitar artefatos de borda
        img = canvas.resize((width, height), Image.Resampling.BICUBIC)
        
        return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))

    @staticmethod
    def get_color_from_string(text):
        """Retorna uma cor de destaque baseada no hash de uma string."""
        colors = [
            "#1e3264", "#8d67ab", "#e8115b", "#f59b23", 
            "#503750", "#1db954", "#ff4632", "#477d95",
            "#af2896", "#509bf5", "#7d4b32", "#c3000d"
        ]
        import hashlib
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return colors[h % len(colors)]
