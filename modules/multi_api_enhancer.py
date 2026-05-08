import requests
import re
from config import LASTFM_API_KEY, DISCOGS_USER_TOKEN, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

class LastFMClient:
    def get_artist_info(self, artist_name):
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={artist_name}&api_key={LASTFM_API_KEY}&format=json"
        try:
            resp = requests.get(url, timeout=5).json()
            artist = resp.get('artist', {})
            
            # Tenta pegar a biografia completa (content) se o sumário for muito curto ou só um link
            bio_summary = artist.get('bio', {}).get('summary', '')
            bio_content = artist.get('bio', {}).get('content', '')
            
            # Escolhe a melhor fonte (preferência por sumário se for bom, senão o conteúdo completo limitado)
            final_bio = bio_summary if len(bio_summary) > 50 else bio_content
            
            if final_bio:
                # 1. Remove links HTML <a> e tags similares
                final_bio = re.sub(r'<a\s+href=.*?>.*?</a>', '', final_bio, flags=re.IGNORECASE)
                final_bio = re.sub(r'<.*?>', '', final_bio)
                
                # 2. Corta o texto se encontrar palavras chaves de discografia
                separators = ["Discography:", "Full discography", "Albums:", "EPs:", "Lançamentos:", "Discografia:"]
                for sep in separators:
                    if sep in final_bio:
                        final_bio = final_bio.split(sep)[0]
                
                # 3. Remover "Read more" de forma segura (apenas se for no final)
                if "Read more" in final_bio:
                    idx = final_bio.find("Read more")
                    if idx > 20: # Se houver algo antes do Read more, corta lá
                        final_bio = final_bio[:idx]
                    else: # Se o Read more for no começo, remove apenas a frase
                        final_bio = final_bio.replace("Read more on Last.fm", "").strip()
                
                final_bio = final_bio.strip()

            return {
                'bio': final_bio,
                'similar': [a.get('name') for a in artist.get('similar', {}).get('artist', [])]
            }
        except: return {}

    def get_track_info(self, artist, track):
        url = f"http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={LASTFM_API_KEY}&artist={artist}&track={track}&format=json"
        try:
            resp = requests.get(url, timeout=5).json()
            t = resp.get('track', {})
            return {
                'album': t.get('album', {}).get('title'),
                'genres': [tag.get('name') for tag in t.get('toptags', {}).get('tag', [])],
                'listeners': t.get('listeners')
            }
        except: return {}

class DeezerClient:
    def get_artist_info(self, artist_name):
        url = f"https://api.deezer.com/search/artist?q={artist_name}"
        try:
            resp = requests.get(url, timeout=5).json()
            data = resp.get('data', [])
            if data:
                return {'picture': data[0].get('picture_xl')}
        except: return {}

    def get_track_info(self, query):
        url = f"https://api.deezer.com/search?q={query}&limit=1"
        try:
            resp = requests.get(url, timeout=5).json()
            data = resp.get('data', [])
            if data:
                d = data[0]
                info = {
                    'album': d.get('album', {}).get('title'),
                    'cover_xl': d.get('album', {}).get('cover_xl'),
                    'track_position': d.get('track_position'),
                    'artist': d.get('artist', {}).get('name'),
                    'title': d.get('title')
                }
                album_id = d.get('album', {}).get('id')
                if album_id:
                    try:
                        alb_resp = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=2).json()
                        info['year'] = alb_resp.get('release_date', '')[:4]
                        genres = alb_resp.get('genres', {}).get('data', [])
                        if genres:
                            info['genre'] = genres[0].get('name')
                    except: pass
                return info
        except: return {}

class SpotifyClient:
    def __init__(self):
        self.token = None
        self.enabled = True # Circuit breaker
    
    def _get_token(self):
        try:
            url = "https://accounts.spotify.com/api/token"
            r = requests.post(url, data={'grant_type': 'client_credentials'}, 
                               auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET), timeout=5)
            if r.status_code == 200:
                self.token = r.json().get('access_token')
            else:
                print(f"[Spotify] Falha Token: Status {r.status_code}")
                if r.status_code == 403:
                    print("[Spotify] Bloqueio detectado (403). Desativando Spotify para esta sessão.")
                    self.enabled = False
        except Exception as e:
            print(f"[Spotify] ERRO Token: {e}")

    def search_artist(self, artist_name):
        if not self.enabled: return None
        if not self.token: self._get_token()
        if not self.token: return None
        url = "https://api.spotify.com/v1/search"
        params = {'q': artist_name, 'type': 'artist', 'limit': 1}
        for attempt in range(2):
            try:
                r = requests.get(url, params=params, headers={'Authorization': f'Bearer {self.token}'}, timeout=10)
                if r.status_code == 200:
                    resp = r.json()
                    artists = resp.get('artists', {}).get('items', [])
                    if artists:
                        a = artists[0]
                        return {
                            'id': a.get('id'),
                            'genres': a.get('genres'),
                            'popularity': a.get('popularity'),
                            'followers': a.get('followers', {}).get('total', 0),
                            'cover': a.get('images', [{}])[0].get('url') if a.get('images') else None
                        }
                    return None
                elif r.status_code == 401: # Token expirado
                    self._get_token()
                    continue
                elif r.status_code == 403:
                    print(f"[Spotify] Erro 403 (Permissão negada) para '{artist_name}'. Desativando Spotify nesta sessão para evitar lentidão.")
                    self.enabled = False
                    return None
            except: 
                if attempt == 1: print(f"[Spotify] Time out definitivo para {artist_name}")
        return None

    def get_artist_albums(self, artist_id):
        if not self.token or not artist_id: return []
        url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?limit=30&include_groups=album,single"
        try:
            resp = requests.get(url, headers={'Authorization': f'Bearer {self.token}'}, timeout=5).json()
            albums = []
            for item in resp.get('items', []):
                rel_date = item.get('release_date', '')
                year = rel_date[:4] if rel_date else 'N/A'
                album_type = item.get('album_group', item.get('album_type', 'album'))
                albums.append({
                    'name': item.get('name'),
                    'cover': item.get('images', [{}])[0].get('url') if item.get('images') else None,
                    'year': year,
                    'type': album_type.capitalize()
                })
            return albums
        except Exception as e:
            print(f"[Spotify] ERRO Álbuns: {e}")
            return []

    def search_track(self, artist, track):
        if not self.enabled: return {}
        if not self.token: self._get_token()
        if not self.token: return {}
        
        # Se não houver artista, faz busca global pelo título
        if not artist or artist.lower() == "unknown":
            q = f"track:{track}"
        else:
            q = f"track:{track} artist:{artist}"

        url = "https://api.spotify.com/v1/search"
        params = {'q': q, 'type': 'track', 'limit': 1}
        try:
            r = requests.get(url, params=params, headers={'Authorization': f'Bearer {self.token}'}, timeout=5)
            if r.status_code == 200:
                resp = r.json()
                tracks = resp.get('tracks', {}).get('items', [])
                if tracks:
                    t = tracks[0]
                    # Tenta capturar a capa do álbum direto do resultado
                    cover_url = None
                    album_images = t.get('album', {}).get('images', [])
                    if album_images:
                        cover_url = album_images[0].get('url')
                    return {
                        'title': t.get('name'),
                        'artist': t.get('artists', [{}])[0].get('name'),
                        'album': t.get('album', {}).get('name'),
                        'year': t.get('album', {}).get('release_date', '')[:4],
                        'track_number': t.get('track_number'),
                        'popularity': t.get('popularity'),
                        'cover_url': cover_url
                    }
                return {}
            elif r.status_code == 403:
                print(f"[Spotify] Erro 403 ao buscar faixa. Desativando Spotify nesta sessão para evitar log de erro.")
                self.enabled = False
                return {}
            elif r.status_code == 401:
                self._get_token()
                return {}
        except Exception as e:
            print(f"[Spotify] Erro na busca de faixa: {e}")
            return {}

    def get_album_cover(self, url):
        """Busca a URL da capa do álbum a partir de uma URL de busca já montada."""
        if not self.enabled: return None
        if not self.token: self._get_token()
        if not self.token: return None
        try:
            resp = requests.get(url, headers={'Authorization': f'Bearer {self.token}'}, timeout=5).json()
            albums = resp.get('albums', {}).get('items', [])
            if albums:
                images = albums[0].get('images', [])
                if images:
                    return images[0].get('url')
        except: pass
        return None



class DiscogsClient:
    def search_artist(self, artist_name):
        headers = {'User-Agent': 'MusicBeatSearchApp/2.0'}
        url = f"https://api.discogs.com/database/search?q={artist_name}&type=artist&token={DISCOGS_USER_TOKEN}"
        
        for attempt in range(2):
            try:
                print(f"[Discogs] Tentativa {attempt+1} para: {artist_name}")
                r = requests.get(url, timeout=12, headers=headers)
                if r.status_code != 200: continue
                resp = r.json()
                results = resp.get('results', [])
                if not results: return {}
                
                target = results[0]
                artist_id = target.get('id')
                
                # Releases
                rel_url = f"https://api.discogs.com/artists/{artist_id}/releases?sort=year&sort_order=desc&per_page=40&token={DISCOGS_USER_TOKEN}"
                rel_r = requests.get(rel_url, timeout=12, headers=headers)
                if rel_r.status_code != 200: continue
                rel_resp = rel_r.json()
                
                releases = []
                for r in rel_resp.get('releases', []):
                    if r.get('type') not in ['master', 'release']: continue
                    
                    fmt_str = r.get('format', '').lower()
                    is_single_ep = 'single' in fmt_str or 'ep' in fmt_str or 'maxi' in fmt_str

                    releases.append({
                        'name': r.get('title'),
                        'cover': r.get('thumb'),
                        'year': str(r.get('year', 'N/A')),
                        'type': 'Single ou EP' if is_single_ep else 'Album'
                    })
                return {'id': artist_id, 'releases': releases}
            except Exception as e:
                if attempt == 1: print(f"[Discogs] Falha definitiva: {e}")
        return {}

    def search_label(self, label_name):
        headers = {'User-Agent': 'MusicBeatSearchApp/2.0'}
        url = f"https://api.discogs.com/database/search?q={label_name}&type=label&token={DISCOGS_USER_TOKEN}"
        try:
            r = requests.get(url, timeout=10, headers=headers)
            if r.status_code != 200: return {}
            results = r.json().get('results', [])
            if not results: return {}
            
            label_id = results[0].get('id')
            label_url = f"https://api.discogs.com/labels/{label_id}"
            lr = requests.get(label_url, timeout=10, headers=headers)
            if lr.status_code == 200:
                data = lr.json()
                return {
                    'name': data.get('name'),
                    'profile': data.get('profile'),
                    'logo_url': data.get('images', [{}])[0].get('resource_url') if data.get('images') else None,
                    'sublabels': [s.get('name') for s in data.get('sublabels', [])]
                }
        except Exception as e:
            print(f"[Discogs] Erro ao buscar label: {e}")
        return {}

    def search_label_from_track(self, artist, title):
        """Tenta descobrir o nome da gravadora a partir do artista e título da música"""
        res = self.search_release(artist, title)
        return res.get('label')

    def search_release(self, artist, title):
        """Busca informações detalhadas da release (Ano, Gênero, Gravadora, Capa)"""
        headers = {'User-Agent': 'MusicBeatSearchApp/2.0'}
        # Limpeza básica para busca
        q_artist = artist.split('(')[0].split('-')[0].strip()
        q_title = title.split('(')[0].split('-')[0].strip()
        
        url = f"https://api.discogs.com/database/search?artist={q_artist}&track={q_title}&type=release&token={DISCOGS_USER_TOKEN}"
        try:
            r = requests.get(url, timeout=8, headers=headers)
            if r.status_code == 200:
                results = r.json().get('results', [])
                if results:
                    r0 = results[0]
                    # Discogs retorna 'Artist - Title' no campo title da busca
                    return {
                        'album': r0.get('title').split(' - ')[-1] if ' - ' in r0.get('title', '') else r0.get('title'),
                        'year': r0.get('year'),
                        'genre': r0.get('genre', [None])[0] if r0.get('genre') else None,
                        'label': r0.get('label', [None])[0] if r0.get('label') else None,
                        'cover_url': r0.get('thumb')
                    }
        except: pass
        return {}

class MultiAPIEnhancer:
    def __init__(self, database=None):
        self.db = database
        self.apis = {
            'discogs': DiscogsClient(),
            'lastfm': LastFMClient(),
            'spotify': SpotifyClient(),
            'deezer': DeezerClient()
        }
        
    def get_artist_complete_info(self, artist_name):
        if self.db:
            cached = self.db.get_cached_artist(artist_name)
            # Se tiver cache e ele tiver discografia, devolve
            if cached and cached.get('discography'):
                print(f"[Cache] Usando dados salvos para: {artist_name}")
                return cached

        print(f"\n[*] Varredura Online iniciada para: {artist_name}")
        result = {
            'name': artist_name, 'bio': None, 'genres': [], 'similar': [],
            'popularity': 0, 'discography': [], 'followers': 0, 'cover': None
        }
        
        # 1. Spotify (Prioridade 1 para discografia)
        clean_name = self._clean_query(artist_name, is_artist=True)
        spotify_info = self.apis['spotify'].search_artist(clean_name)
        if spotify_info:
            print(f"[API] Spotify OK para '{artist_name}'")
            result['genres'] = spotify_info.get('genres', [])
            result['followers'] = spotify_info.get('followers', 0)
            result['cover'] = spotify_info.get('cover')
            result['discography'] = self.apis['spotify'].get_artist_albums(spotify_info.get('id'))
        
        # 2. Discogs (Fallback total para discografia ou complemento)
        if not result['discography']:
            print(f"[API] Discogs: Spotify falhou, tentando discografia no Discogs...")
            discogs = self.apis['discogs'].search_artist(clean_name)
            if discogs:
                result['discography'] = discogs.get('releases', [])
                print(f"[API] Discogs: Capturados {len(result['discography'])} itens.")

        # 3. Last.fm (Biografia limpa)
        lastfm = self.apis['lastfm'].get_artist_info(clean_name)
        
        if not lastfm.get('bio') and artist_name != clean_name:
            # Fallback 1: tentar o nome original sem limpeza agressiva
            print(f"[API] Last.fm: Bio vazia para '{clean_name}', tentando original '{artist_name}'...")
            lastfm = self.apis['lastfm'].get_artist_info(artist_name)

        if not lastfm.get('bio'):
            # Fallback 2: tentar versão compacta (ex: L.T.D -> LTD)
            compact_name = artist_name.replace(".", "").replace(" ", "")
            if compact_name != artist_name and compact_name != clean_name:
                print(f"[API] Last.fm: Bio vazia, tentando versão compacta '{compact_name}'...")
                lastfm = self.apis['lastfm'].get_artist_info(compact_name)

        if lastfm:
            result['bio'] = lastfm.get('bio')
            result['similar'] = lastfm.get('similar', [])

        # 4. Deezer (Fallback Capa)
        if not result['cover']:
            deezer = self.apis['deezer'].get_artist_info(clean_name)
            if deezer: result['cover'] = deezer.get('picture')
        
        # Salvar se for válido
        if self.db and (result['bio'] or result['discography']):
            self.db.save_artist_cache(artist_name, result)
            
        return result
            
    def _clean_query(self, text, is_artist=False):
        """Limpeza profunda para garantir resultados nas APIs (Remove lixos de tags e nomes de arquivos)"""
        if not text: return ""
        text = str(text)
        
        # 1. Remover prefixos de números (01 - Nome, 1. Nome)
        if not is_artist:
            text = re.sub(r'^\d{1,3}[\s\-_.]+', '', text)
            
        # 2. Se for Artista e contiver ' - ', pegar apenas a primeira parte
        if is_artist and ' - ' in text:
            text = text.split(' - ')[0]

        # 3. Remover parênteses e colchetes e tudo dentro (Ex: (Remix), [Official Video], (High Quality))
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^]]*\]', '', text)
        
        # 4. Lista estendida de "sujeira" (palavras que poluem a busca)
        garbage_patterns = [
            # Colaboradores
            r'\bfeat\.?\b', r'\bft\.?\b', r'\bfeaturing\b', r'\bfeat\b', r'\bwith\b', 
            r'\bft\b', r'\bpres\.?\b', r'\bpresenting\b', r'\bparticipação\b', r'\bpart\.?\b',
            
            # Versões e Qualidade
            r'\bremix\b', r'\bmix\b', r'\bedit\b', r'\bextended\b', r'\bradio\b', r'\binstrumental\b', 
            r'\binstr\.?\b', r'\bversion\b', r'\bver\.?\b', r'\bhq\b', r'\bhd\b', r'\b4k\b', 
            r'\bhigh quality\b', r'\bhigh res\b', r'\b1080p\b', r'\b720p\b', r'\b320kbps\b',
            
            # Lixo de arquivos e collections
            r'\bofficial\b', r'\bvideo\b', r'\bclip\b', r'\blyrics\b', r'\bmv\b', r'\bexclusive\b',
            r'\bhit\b', r'\bhits\b', r'\bfesta\b', r'\bfunk\b', r'\b1 hit\b', r'\bsingle\b', r'\balbum\b',
            
            # Datas e Anos (Ex: 2002, 1998)
            r'\b(19|20)\d{2}\b',
            
            # Site e Promo
            r'\bwww\..*?\..*?\b', r'\.com\b', r'\.br\b', r'\bpromo\b', r'\bleak\b'
        ]
        
        # Aplicar remoção de cada padrão (Case Insensitive)
        for pattern in garbage_patterns:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
            
        # 5. Tratamento de Símbolos
        if not is_artist:
            # Em títulos de música, símbolos como & ou x as vezes separam artistas secundários
            text = text.replace('&', ' ').replace(' x ', ' ').replace(' vs ', ' ')
            
        # 6. Remover pontuação e caracteres especiais excessivos (mas manter espaços)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 7. Normalizar espaços
        text = " ".join(text.split()).strip()
        
        return text

    def get_track_complete_info(self, artist_name, track_name):
        """Busca metadados completos de uma faixa em múltiplas APIs com fallback robusto.
        Retorna também artist_photo_url (PONTO #4) — foto do artista separada da capa do álbum."""
        clean_track = self._clean_query(track_name)
        clean_artist = self._clean_query(artist_name) if artist_name else ""
        result = {
            'title': track_name, 'artist': artist_name, 'album': None,
            'year': None, 'genre': None, 'track_number': None,
            'cover_url': None,
            'artist_photo_url': None   # PONTO #4: foto do artista (não a capa)
        }

        # 1. Last.fm — Prioridade para GÊNERO (tags da comunidade são mais precisas)
        if clean_track:
            try:
                lastfm = self.apis['lastfm'].get_track_info(clean_artist, clean_track)
                if lastfm:
                    if lastfm.get('genres'):
                        # Filtra tags lixo e pega a primeira relevante
                        tags = [t for t in lastfm['genres'] if t.lower() not in ['seen live', 'favorites', 'awesome']]
                        if tags: result['genre'] = tags[0].title()
                    if not result['album'] and lastfm.get('album'):
                        result['album'] = lastfm['album']
            except: pass

        # 2. Spotify — Melhor fonte para metadados técnicos (Ano, Capa, Artista Oficial)
        try:
            if clean_track:
                spotify = self.apis['spotify'].search_track(clean_artist, clean_track)
                if spotify:
                    if spotify.get('title'):  result['title']  = spotify['title']
                    if spotify.get('artist'): result['artist'] = spotify['artist']
                    if spotify.get('album'):  result['album']  = spotify['album']
                    if spotify.get('year'):   result['year']   = spotify['year']
                    if spotify.get('track_number'): result['track_number'] = spotify['track_number']
                    if spotify.get('cover_url'):    result['cover_url']    = spotify['cover_url']
            
            # Se tivermos artista, busca info dele (Gênero e Foto)
            if clean_artist:
                sp_artist = self.apis['spotify'].search_artist(clean_artist)
                if sp_artist:
                    if not result['genre'] and sp_artist.get('genres'):
                        result['genre'] = sp_artist['genres'][0].title()
                    # PONTO #4: Captura foto do artista via Spotify
                    if not result['artist_photo_url'] and sp_artist.get('cover'):
                        result['artist_photo_url'] = sp_artist['cover']
        except Exception as e:
            print(f"[Spotify] Erro ao buscar info: {e}")

        # 3. Deezer — Excelente fonte para Capa e metadados (Especialmente se Spotify falhar)
        try:
            query = f"{clean_artist} {clean_track}".strip()
            if query:
                deezer = self.apis['deezer'].get_track_info(query)
                if deezer:
                    if not result['title']    and deezer.get('title'):     result['title']     = deezer['title']
                    if not result['artist']   and deezer.get('artist'):    result['artist']    = deezer['artist']
                    if not result['album']    and deezer.get('album'):     result['album']     = deezer['album']
                    if not result['cover_url'] and deezer.get('cover_xl'): result['cover_url'] = deezer['cover_xl']
                    if not result['year']     and deezer.get('year'):      result['year']      = deezer['year']
                    if not result['genre']    and deezer.get('genre'):     result['genre']     = deezer['genre']
        except: pass

        # 4. Discogs — Excelente para Ano, Gênero e Gravadora (Fallback ou Alternativa ao Spotify/Deezer)
        if not result['year'] or not result['genre'] or not result['cover_url']:
            try:
                discogs = self.apis['discogs'].search_release(clean_artist, clean_track)
                if discogs:
                    if not result['year']: result['year'] = discogs.get('year')
                    if not result['genre']: result['genre'] = discogs.get('genre')
                    if not result['album']: result['album'] = discogs.get('album')
                    if not result['cover_url']: result['cover_url'] = discogs.get('cover_url')
                    result['label'] = discogs.get('label')
            except: pass

        # 4. Deezer artista — fallback para CAPA e para FOTO DO ARTISTA
        if not result['cover_url'] or not result['artist_photo_url']:
            try:
                deezer_artist = self.apis['deezer'].get_artist_info(clean_artist)
                if deezer_artist and deezer_artist.get('picture'):
                    if not result['cover_url']:
                        result['cover_url'] = deezer_artist['picture']
                    # PONTO #4: salvar como artist_photo também
                    if not result['artist_photo_url']:
                        result['artist_photo_url'] = deezer_artist['picture']
            except: pass
        
        # 5. Se ainda assim não houver cover_url mas houver artist_photo_url, usa como fallback (e vice-versa)
        if not result['cover_url'] and result['artist_photo_url']:
            result['cover_url'] = result['artist_photo_url']
        if not result['artist_photo_url'] and result['cover_url']:
            result['artist_photo_url'] = result['cover_url']

        return result

    def get_label_complete_info(self, label_name, artist=None, title=None):
        """Busca informações completas da gravadora. 
        Se label_name não for fornecido, tenta descobrir via artista/título."""
        
        # 1. Se não temos o nome da gravadora, tenta descobrir no Discogs
        if (not label_name or label_name.lower() in ['unknown', 'n/a', 'varias', 'vários', 'independente']) and artist and title:
            print(f"[*] Identificando gravadora para: {artist} - {title}")
            label_name = self.apis['discogs'].search_label_from_track(artist, title)
            
        if not label_name or label_name.lower() in ['unknown', 'n/a', 'varias', 'vários', 'independente']:
            return {}
            
        if self.db:
            cached = self.db.get_cached_label(label_name)
            if cached: return cached

        print(f"[*] Buscando informações da gravadora: {label_name}")
        info = self.apis['discogs'].search_label(label_name)
        
        if info and self.db:
            self.db.save_label_cache(label_name, info)
            
        return info
