import time
import customtkinter as ctk

app = ctk.CTk()
app.main_area = ctk.CTkFrame(app)

t0 = time.time()
top_section = ctk.CTkFrame(app.main_area, fg_color="transparent")
t1 = time.time()
print(f"CTkFrame: {t1-t0:.3f}")

search_container = ctk.CTkFrame(top_section, fg_color="#2b2b2b", corner_radius=10, height=45, width=400)
t2 = time.time()
print(f"CTkFrame 2: {t2-t1:.3f}")

lbl = ctk.CTkLabel(search_container, text="   🔍 ", font=("Segoe UI", 16), text_color="#777")
t3 = time.time()
print(f"CTkLabel: {t3-t2:.3f}")

entry = ctk.CTkEntry(search_container, placeholder_text="Pesquisar...", fg_color="transparent", border_width=0, text_color="white", height=40)
t4 = time.time()
print(f"CTkEntry: {t4-t3:.3f}")

btn = ctk.CTkButton(top_section, text="Buscar", width=90, height=38, fg_color="#c3000d", hover_color="#9a000a")
t5 = time.time()
print(f"CTkButton: {t5-t4:.3f}")
