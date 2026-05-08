import os
import base64
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sys

# Import the existing modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

from modules.database import Database
from modules.scanner import LibraryScanner
from modules.config_manager import ConfigManager

# Configuração de log para o servidor API
api_log = os.path.join(os.path.dirname(__file__), "..", "api_server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(api_log, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("API_Server")

app = FastAPI(title="BeatSound API Mirror")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()

@app.get("/api/stats")
def get_stats():
    """Returns database statistics for sync tracking"""
    try:
        total = db.get_total_count()
        return {"total_songs": total}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/user")
def get_user():
    """Returns the primary user profile"""
    try:
        user = db.query("SELECT * FROM users LIMIT 1")
        if user:
            return user[0]
        return {"username": "guest", "display_name": "Convidado"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/recent")
def get_recent_tracks(limit: int = 20, q: Optional[str] = None):
    """Returns recently added/played tracks, with optional filtering"""
    try:
        logger.info(f"Request /api/recent: q={q}, limit={limit}")
        if q and q.startswith("g:"):
            genre = q[2:]
            tracks = db.get_musics_by_genre(genre, limit=limit)
            logger.info(f"Genre filter '{genre}': {len(tracks)} found")
        elif q and q.startswith("p:"):
            path_fragment = q[2:]
            # Otimizado: busca por pasta com suporte a caminhos Windows/Linux
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Tenta padrão com barra comum e invertida
                pattern = f"%/flow/{path_fragment}/%"
                pattern_win = f"%\\flow\\{path_fragment}\\%"
                
                cursor.execute("""
                    SELECT * FROM metadata_cache 
                    WHERE (LOWER(file_path) LIKE LOWER(?) OR LOWER(file_path) LIKE LOWER(?))
                    ORDER BY RANDOM() 
                    LIMIT ?
                """, (pattern, pattern_win, limit))
                tracks = [dict(row) for row in cursor.fetchall()]
            logger.info(f"Path filter '{path_fragment}': {len(tracks)} found")
        else:
            tracks = db.get_recently_played(limit=limit)
            logger.info(f"No filter, returning recently played: {len(tracks)} found")
        return {"tracks": tracks}
    except Exception as e:
        logger.error(f"Error in /api/recent: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/search")
def search_tracks(q: str, filter_type: str = "Todos", limit: int = 50):
    """Search tracks with desktop-style filters"""
    try:
        tracks = db.search_musics(query=q, filter_type=filter_type, limit=limit)
        return {"tracks": tracks}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/flow-categories")
def get_flow_categories():
    """Returns available genres for the Flow bar"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT genre, COUNT(*) as count FROM metadata_cache WHERE genre IS NOT NULL AND genre != '' GROUP BY genre ORDER BY count DESC LIMIT 15")
            categories = [dict(row) for row in cursor.fetchall()]
        return {"categories": categories}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/random-artists")
def get_random_artists(limit: int = 15):
    """Returns random artists for discovery"""
    try:
        artists = db.get_random_artists(limit=limit)
        return {"artists": artists}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/most-played")
def get_most_played(limit: int = 15):
    """Returns most played tracks"""
    try:
        tracks = db.get_most_played(limit=limit)
        return {"tracks": tracks}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/top-artists")
def get_top_artists(limit: int = 15):
    """Returns most frequent artists"""
    try:
        artists = db.get_top_artists(limit=limit)
        return {"artists": artists}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/favorites")
def get_favorites():
    """Returns all favorite tracks"""
    try:
        tracks = db.get_favorites()
        return {"tracks": tracks}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/artist/{artist_name}")
def get_artist_detail(artist_name: str):
    """Returns full details for an artist including tracks, bio, and albums"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM artist_cache WHERE LOWER(artist_name) = LOWER(?)", (artist_name.strip(),))
            row = cursor.fetchone()
            artist_info = dict(row) if row else {"artist_name": artist_name}
            tracks = db.search_by_artist(artist_name, limit=10)
            cursor.execute("SELECT * FROM album_cache WHERE LOWER(artist_name) = LOWER(?)", (artist_name.strip(),))
            albums = [dict(r) for r in cursor.fetchall()]
        
        return {
            "info": artist_info,
            "tracks": tracks,
            "albums": albums
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/artist/favorite")
async def toggle_artist_favorite(data: dict):
    """Toggle favorite status for an artist"""
    try:
        artist_name = data.get("artist_name")
        if not artist_name:
            raise HTTPException(status_code=400, detail="artist_name required")
        
        db.toggle_artist_favorite(artist_name)
        # Retorna o novo estado e os dados atualizados
        return get_artist_info(artist_name)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/favorite")
async def toggle_favorite(data: dict):
    """Toggle favorite status for a track"""
    try:
        file_path = data.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path required")
        
        db.toggle_favorite(file_path)
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/playlists")
def get_playlists():
    """Returns all playlists"""
    try:
        playlists = db.get_playlists()
        return {"playlists": playlists}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/playlist/{playlist_id}")
def get_playlist_detail(playlist_id: int):
    """Returns all tracks for a specific playlist"""
    try:
        playlists = db.get_playlists()
        playlist = next((p for p in playlists if p['id'] == playlist_id), None)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
            
        # Get full metadata for each song path
        paths = playlist.get("songs", [])
        if not paths:
            return {"playlist": playlist, "tracks": []}
            
        tracks = []
        with db.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ', '.join(['?'] * len(paths))
            cursor.execute(f"SELECT * FROM metadata_cache WHERE file_path IN ({placeholders})", paths)
            resolved = {row['file_path']: dict(row) for row in cursor.fetchall()}
            
            for p in paths:
                if p in resolved:
                    tracks.append(resolved[p])
                    
        return {"playlist": playlist, "tracks": tracks}
    except Exception as e:
        logger.error(f"Error fetching playlist {playlist_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/playlist/add")
async def add_to_playlist_endpoint(data: dict):
    """Add a track to a playlist"""
    try:
        playlist_id = data.get("playlist_id")
        file_path = data.get("file_path")
        if not playlist_id or not file_path:
            raise HTTPException(status_code=400, detail="playlist_id and file_path required")
        
        db.add_to_playlist(playlist_id, file_path)
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/resolve-paths")
async def resolve_paths(data: dict):
    """Resolve a list of file paths into full metadata objects"""
    try:
        paths = data.get("paths", [])
        if not paths:
            return {"tracks": []}
            
        tracks = []
        with db.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ', '.join(['?'] * len(paths))
            cursor.execute(f"SELECT * FROM metadata_cache WHERE file_path IN ({placeholders})", paths)
            tracks = [dict(row) for row in cursor.fetchall()]
            
        return {"tracks": tracks}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/stream/{encoded_path}")
def stream_audio(encoded_path: str):
    """Stream audio file."""
    try:
        decoded_bytes = base64.urlsafe_b64decode(encoded_path)
        file_path = decoded_bytes.decode('utf-8')
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
            
        return FileResponse(file_path, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/cover/{encoded_path}")
def get_cover(encoded_path: str):
    """Serve cover art image."""
    try:
        decoded_bytes = base64.urlsafe_b64decode(encoded_path)
        file_path = decoded_bytes.decode('utf-8')
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Cover not found")
            
        return FileResponse(file_path, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/scan")
async def start_scan():
    """Trigger library scan mirroring desktop behavior"""
    try:
        config = ConfigManager()
        music_dir = config.get("music_dir")
        
        def run_async_scan():
            scanner = LibraryScanner(db)
            logger.info(f"Starting background scan in {music_dir}")
            results = scanner.scan(music_dir)
            scanner.prune()
            logger.info(f"Scan finished: {results}")

        import threading
        threading.Thread(target=run_async_scan, daemon=True).start()
        
        return {"success": True, "message": "Scan started in background"}
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
