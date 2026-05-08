import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk
import math

class GlowBase(tk.Frame):
    """Base class for rainbow glow animated widgets with global frame caching."""
    _frame_cache = {}  # Global cache: (w, h, glow, radius) -> [PhotoImage, ...]

    def __init__(self, master, width, height, glow_size=6, corner_radius=10, on_enter=None, on_leave=None, **kwargs):
        # Base size is button/card + glow space
        self.glow_size = glow_size
        self.btn_width = width
        self.btn_height = height
        self.corner_radius = corner_radius
        self.on_enter_callback = on_enter
        self.on_leave_callback = on_leave
        
        # Use standard tk.Frame to avoid CTk interference with the canvas
        bg_color = self._get_parent_bg(master)
        super().__init__(master, bg=bg_color, width=width + glow_size*2, height=height + glow_size*2)
        
        self.is_hovered = False
        self.animation_step = 0
        
        self.canvas = tk.Canvas(self, width=width + glow_size*2, 
                               height=height + glow_size*2, 
                               bg=bg_color, 
                               highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        
        # Check cache before generating
        cache_key = (width, height, glow_size, corner_radius)
        if cache_key not in GlowBase._frame_cache:
            self._generate_frames(cache_key)
        self.glow_images = GlowBase._frame_cache[cache_key]

    def _get_parent_bg(self, curr):
        """Resolves the actual background color, even if parents are transparent."""
        while curr:
            try:
                if hasattr(curr, "_fg_color"):
                    color = curr._fg_color
                    if isinstance(color, (list, tuple)):
                        color = color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
                    if color and color != "transparent" and not str(color).startswith("trans"):
                        return color
                try:
                    color = curr.cget("fg_color")
                    if color and color != "transparent" and not str(color).startswith("trans"):
                        if isinstance(color, (list, tuple)):
                            color = color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
                        return color
                except: pass
                color = curr.cget("bg")
                if color and color != "transparent" and not str(color).startswith("trans"):
                    return color
            except: pass
            try: curr = curr.master
            except: break
        return "#121212"

    def _generate_frames(self, cache_key):
        w, h = self.btn_width + self.glow_size*2, self.btn_height + self.glow_size*2
        colors = [(255, 0, 0), (255, 115, 0), (255, 251, 0), (72, 255, 0), (0, 255, 213), (0, 43, 255), (122, 0, 255), (255, 0, 200)]
        num_frames = 12 # Slightly fewer frames for even better performance
        frames = []
        for frame_idx in range(num_frames):
            scale = 2
            img_w, img_h = w * scale, h * scale
            rainbow = Image.new("RGBA", (img_w, img_h))
            r_draw = ImageDraw.Draw(rainbow)
            offset = (frame_idx / num_frames) * img_w
            for i in range(img_w):
                # Garante que pos está entre 0 e 1
                pos = max(0.0, min(0.9999, ((i - offset) % img_w) / img_w))
                color_pos = pos * len(colors)
                idx1 = int(color_pos) % len(colors)
                idx2 = (idx1 + 1) % len(colors)
                f = color_pos - int(color_pos)
                
                c1 = colors[idx1]
                c2 = colors[idx2]
                rgb = tuple(int(c1[j] + (c2[j] - c1[j]) * f) for j in range(3))
                r_draw.line([(i, 0), (i, img_h)], fill=rgb + (255,))
            
            # Simple mask: just a rounded rectangle for the whole glow area
            mask = Image.new("L", (img_w, img_h), 0)
            m_draw = ImageDraw.Draw(mask)
            m_draw.rounded_rectangle([4, 4, img_w-4, img_h-4], 
                                     radius=self.corner_radius*scale + self.glow_size*scale, 
                                     fill=255)
            
            glow_img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
            glow_img.paste(rainbow, (0, 0), mask)
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=self.glow_size * 1.0)) # More blur
            final_frame = glow_img.resize((w, h), Image.Resampling.LANCZOS)
            frames.append(ImageTk.PhotoImage(final_frame))
        GlowBase._frame_cache[cache_key] = frames

    def _animate(self):
        if not self.is_hovered or not self.winfo_exists(): return
        self.animation_step = (self.animation_step + 1) % len(self.glow_images)
        self.canvas.delete("all")
        self.canvas.create_image((self.btn_width + self.glow_size*2)//2, 
                                 (self.btn_height + self.glow_size*2)//2, 
                                 image=self.glow_images[self.animation_step])
        self.after(50, self._animate)

class GlowButton(GlowBase):
    def __init__(self, master, text, command=None, width=120, height=38, corner_radius=10, font=("Segoe UI", 13, "bold"), **kwargs):
        super().__init__(master, width, height, glow_size=6, corner_radius=corner_radius)
        self.command = command
        # Content button
        self.button = ctk.CTkButton(self, text=text, width=width, height=height,
                                   fg_color="black", hover_color="#111",
                                   text_color="white", corner_radius=corner_radius,
                                   font=font, command=command, **kwargs)
        self.button.place(relx=0.5, rely=0.5, anchor="center")
        self.button.bind("<Enter>", self._on_enter)
        self.button.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.is_hovered = True
        self._animate()

    def _on_leave(self, e):
        self.is_hovered = False
        self.canvas.delete("all")

    def configure(self, **kwargs):
        if 'text' in kwargs: self.button.configure(text=kwargs['text'])
        if 'command' in kwargs: self.command = kwargs['command']; self.button.configure(command=kwargs['command'])

class GlowCard(GlowBase):
    """A container frame that glows on hover."""
    def __init__(self, master, width, height, corner_radius=12, fg_color=None, on_enter=None, on_leave=None, **kwargs):
        # Cards need a bit more glow space and intensity
        super().__init__(master, width, height, glow_size=12, corner_radius=corner_radius, 
                         on_enter=on_enter, on_leave=on_leave)
        
        self.content = ctk.CTkFrame(self, width=width, height=height, 
                                   fg_color=fg_color, corner_radius=corner_radius,
                                   **kwargs)
        self.content.place(relx=0.5, rely=0.5, anchor="center")
        self.content.pack_propagate(False)

    def bind_all_children(self, widget=None):
        """Recursively binds hover events to all children for a seamless effect."""
        if widget is None:
            # Bind main containers first
            for w in [self, self.canvas, self.content]:
                w.bind("<Enter>", self._on_enter, add="+")
                w.bind("<Leave>", self._on_leave, add="+")
            target = self.content
        else:
            target = widget
            if not isinstance(target, (ctk.CTkButton, tk.Button)):
                target.bind("<Enter>", self._on_enter, add="+")
                target.bind("<Leave>", self._on_leave, add="+")
            
        for child in target.winfo_children():
            self.bind_all_children(child)

    def _on_enter(self, e):
        if not self.is_hovered:
            self.is_hovered = True
            if self.on_enter_callback:
                self.on_enter_callback(e)
            self._animate()

    def _on_leave(self, e):
        self.is_hovered = False
        self.after(100, self._check_really_left)

    def _check_really_left(self):
        if not self.is_hovered:
            if self.on_leave_callback:
                self.on_leave_callback(None)
            self.canvas.delete("all")

    def configure(self, **kwargs):
        if 'text' in kwargs:
            self.button.configure(text=kwargs['text'])
        if 'command' in kwargs:
            self.command = kwargs['command']
            self.button.configure(command=kwargs['command'])
        # Add other pass-throughs as needed
