import time
import customtkinter as ctk

app = ctk.CTk()
app.main_area = ctk.CTkFrame(app)

t0 = time.time()
lbl1 = ctk.CTkLabel(app.main_area, text="No emoji", font=("Segoe UI", 16))
print(f"No emoji: {time.time()-t0:.3f}")

t1 = time.time()
lbl2 = ctk.CTkLabel(app.main_area, text="🔍", font=("Segoe UI", 16))
print(f"Emoji 1: {time.time()-t1:.3f}")

t2 = time.time()
lbl3 = ctk.CTkLabel(app.main_area, text="⚠️", font=("Segoe UI", 16))
print(f"Emoji 2: {time.time()-t2:.3f}")
