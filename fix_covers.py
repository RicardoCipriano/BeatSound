import os
import sqlite3
import re

db_path = r'C:\projetos\SearchMusicBeat\SearchMusic_Novo\music.db'
covers_dir = r'C:\projetos\SearchMusicBeat\SearchMusic_Novo\assets\covers'

conn = sqlite3.connect(db_path)
c = conn.cursor()

def clean_filename(name):
    if not name: return ""
    name = str(name)
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.replace(" ", "_")
    return name

c.execute("SELECT file_path, artist, album, title FROM metadata_cache")
rows = c.fetchall()

covers = set(os.listdir(covers_dir))

updates = []

for row in rows:
    fpath, artist, album, title = row
    
    found_cover = None
    
    if artist and album:
        p1 = f"{clean_filename(artist)}_{clean_filename(album)}.jpg"
        if p1 in covers:
            found_cover = os.path.join(covers_dir, p1)
            
    if not found_cover and artist and title:
        p2 = f"{clean_filename(artist)}_{clean_filename(title)}.jpg"
        if p2 in covers:
            found_cover = os.path.join(covers_dir, p2)
            
    if not found_cover and album:
        p3 = f"{clean_filename(album)}.jpg"
        if p3 in covers:
            found_cover = os.path.join(covers_dir, p3)
            
    # Maybe underscore replacements vary
    if not found_cover and artist and album:
        p4 = artist.replace(" ", "_") + "_" + album.replace(" ", "_") + ".jpg"
        # loose match check ignoring case
        for cover in covers:
            if cover.lower() == p4.lower():
                found_cover = os.path.join(covers_dir, cover)
                break
                
    # very loose substring match
    if not found_cover and artist:
        a_first_word = artist.split(' ')[0].lower() if artist else ""
        for cover in covers:
            if a_first_word and a_first_word in cover.lower():
                found_cover = os.path.join(covers_dir, cover)
                break

    if found_cover:
        updates.append((found_cover, fpath))

for cov, fp in updates:
    c.execute("UPDATE metadata_cache SET cover_path=? WHERE file_path=?", (cov, fp))

print(f"Updated {len(updates)} covers.")
conn.commit()
conn.close()
