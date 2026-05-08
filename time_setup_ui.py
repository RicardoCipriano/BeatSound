import time
print("Starting...")

t0 = time.time()
from main import BeatSoundSearch
t1 = time.time()
print(f"Import main time: {t1 - t0:.3f}s")

app = BeatSoundSearch()
t2 = time.time()
print(f"BeatSoundSearch instantiation: {t2 - t1:.3f}s")

# Let's see what happens if we wait 5s and don't loop
time.sleep(1)
print("Done!")
