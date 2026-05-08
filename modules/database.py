import sqlite3
import os
import sys
from pathlib import Path
from contextlib import contextmanager
import queue
import threading
import time

class Database:
    def __init__(self, db_path=None):
        # 1. Determina a pasta do Executável (Raiz de persistência)
        if getattr(sys, 'frozen', False):
            self.root_dir = os.path.dirname(sys.executable)
            # Pasta interna do bundle (PyInstaller)
            bundle_dir = getattr(sys, '_MEIPASS', self.root_dir)
        else:
            self.root_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
            bundle_dir = self.root_dir

        # 2. Resolve o caminho do Banco de Dados
        if db_path is None:
            local_db = os.path.join(self.root_dir, 'music.db')
            bundle_db = os.path.join(bundle_dir, 'music.db')
            
            # Prefere o banco ao lado do .exe (persistente)
            if os.path.exists(local_db):
                self.db_path = local_db
            # Se não existe, vê se tem um no bundle (incluído no build)
            elif os.path.exists(bundle_db):
                self.db_path = bundle_db
            else:
                self.db_path = local_db # Fallback para criar um novo no local
        else:
            self.db_path = db_path
        
        # Ensure tables exist BEFORE starting the background worker
        self.ensure_schema()
        self.init_db()
        
        # Write Queue for thread safety during massive scans
        self.write_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def ensure_schema(self):
        """Garante que a estrutura base das tabelas exista"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            
            # 1. Tabela Principal (Estrutura Base)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    file_path TEXT PRIMARY KEY,
                    artist TEXT,
                    title TEXT,
                    album TEXT,
                    date TEXT,
                    genre TEXT,
                    duration INTEGER,
                    cover_path TEXT,
                    favorite BOOLEAN DEFAULT 0,
                    play_count INTEGER DEFAULT 0,
                    last_played TIMESTAMP,
                    file_mtime REAL,
                    bitrate INTEGER,
                    ext TEXT,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Garantir que colunas novas existam (para quem já tem o banco)
            cols = [
                ('file_mtime', 'REAL'), 
                ('bitrate', 'INTEGER'), 
                ('ext', 'TEXT'),
                ('label', 'TEXT') # PONTO: Suporte a Gravadoras
            ]
            cursor.execute("PRAGMA table_info(metadata_cache)")
            existing_cols = [row[1] for row in cursor.fetchall()]
            for col_name, col_type in cols:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE metadata_cache ADD COLUMN {col_name} {col_type}")
            
            # Criar índices para performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artist ON metadata_cache(artist)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON metadata_cache(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_genre ON metadata_cache(genre)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON metadata_cache(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_indexed_at ON metadata_cache(indexed_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lower_file_path ON metadata_cache(LOWER(file_path))")
            
            # 2. Tabelas Auxiliares
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlist_songs (
                    playlist_id INTEGER,
                    file_path TEXT,
                    position INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (playlist_id, file_path),
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                )
            """)

            # 4. Tabela de Usuários
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    display_name TEXT,
                    profile_photo TEXT,
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Garantir usuário padrão
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (username, display_name, bio) VALUES (?, ?, ?)", 
                               ("beatsound_fan", "Premium User", "Apaixonado por música e batidas premium."))
            
            # 3. Índices de Performance
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_artist ON metadata_cache(artist)",
                "CREATE INDEX IF NOT EXISTS idx_genre ON metadata_cache(genre)",
                "CREATE INDEX IF NOT EXISTS idx_play_count ON metadata_cache(play_count)",
                "CREATE INDEX IF NOT EXISTS idx_search ON metadata_cache(title, artist, album)",
                "CREATE INDEX IF NOT EXISTS idx_last_played ON metadata_cache(last_played)"
            ]
            for idx in indices:
                cursor.execute(idx)

            # 4. Tabelas de Cache de API
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artist_cache (
                    artist_name TEXT PRIMARY KEY,
                    bio TEXT,
                    cover_url TEXT,
                    followers INTEGER,
                    discography TEXT,
                    artist_photo TEXT,
                    favorite BOOLEAN DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Garantir favorite em artist_cache se a tabela já existir
            cursor.execute("PRAGMA table_info(artist_cache)")
            artist_cols = [row[1] for row in cursor.fetchall()]
            if "favorite" not in artist_cols:
                cursor.execute("ALTER TABLE artist_cache ADD COLUMN favorite BOOLEAN DEFAULT 0")
            
            # 5. Cache de Gravadoras (Labels)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS label_cache (
                    label_name TEXT PRIMARY KEY,
                    profile TEXT,
                    logo_url TEXT,
                    sublabels TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS album_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artist_name TEXT,
                    album_name TEXT,
                    album_cover TEXT,
                    album_year TEXT,
                    album_type TEXT,
                    FOREIGN KEY (artist_name) REFERENCES artist_cache(artist_name)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Retorna conexão com o banco com commit automático"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except sqlite3.DatabaseError as e:
                if "malformed" in str(e).lower():
                    print(f"\n[!!!] ERRO CRÍTICO: Banco de dados corrompido! ({e})")
                    print("[!] Sugestão: Delete o arquivo 'music.db' e reinicie o app.")
                conn.rollback()
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            if "malformed" in str(e).lower():
                print(f"\n[!!!] ERRO DE CONEXÃO: Banco de dados corrompido! ({e})")
            raise
    
    def init_db(self):
        """Executa migrações necessárias para colunas novas em bancos antigos"""
        print("[*] Verificando integridade do banco de dados...")
        cols_to_check = [
            ('indexed_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('play_count', 'INTEGER DEFAULT 0'),
            ('last_played', 'TIMESTAMP'),
            ('favorite', 'BOOLEAN DEFAULT 0'),
            ('duration', 'INTEGER'),
            ('cover_path', 'TEXT'),
            ('file_mtime', 'INTEGER'),
            ('bitrate', 'INTEGER'),
            ('ext', 'TEXT'),
            ('updated_at', 'TIMESTAMP'),
            ('indexed_at', 'TIMESTAMP'),
            # PONTO #4: foto do artista separada da capa do álbum
            ('artist_photo', 'TEXT'),
            # PONTO #5: quality score para ordenação inteligente dos cards
            ('quality_score', 'INTEGER DEFAULT 0'),
        ]
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(metadata_cache)")
                existing_cols = [row[1] for row in cursor.fetchall()]
                
                added = False
                for col_name, col_def in cols_to_check:
                    if col_name not in existing_cols:
                        print(f"[!] Migração: Adicionando coluna '{col_name}' ao banco...")
                        type_only = col_def.split('DEFAULT')[0].strip()
                        try:
                            cursor.execute(f"ALTER TABLE metadata_cache ADD COLUMN {col_name} {type_only}")
                            # Se tiver default, aplicar via UPDATE para evitar erro do SQLite
                            if 'DEFAULT' in col_def:
                                default_val = col_def.split('DEFAULT')[1].strip()
                                if 'CURRENT_TIMESTAMP' in default_val:
                                    cursor.execute(f"UPDATE metadata_cache SET {col_name} = CURRENT_TIMESTAMP WHERE {col_name} IS NULL")
                                else:
                                    cursor.execute(f"UPDATE metadata_cache SET {col_name} = {default_val} WHERE {col_name} IS NULL")
                            added = True
                        except Exception as e:
                            print(f"[!] Erro ao adicionar coluna {col_name}: {e}")
                
                if added: conn.commit()

                # Criar índices após garantir que as colunas existem
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON metadata_cache(updated_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mtime ON metadata_cache(file_mtime)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bitrate ON metadata_cache(bitrate)")
                
                # Check playlists columns
                cursor.execute("PRAGMA table_info(playlists)")
                existing_playlists = [col[1] for col in cursor.fetchall()]
                if 'description' not in existing_playlists:
                    cursor.execute("ALTER TABLE playlists ADD COLUMN description TEXT")
                if 'created_at' not in existing_playlists:
                    cursor.execute("ALTER TABLE playlists ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            print("[✓] Banco de dados pronto.")
        except Exception as e:
            print(f"[X] Erro na migração do banco: {e}")

    def _worker(self):
        """Thread worker to process database writes sequentially"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        while not self.stop_event.is_set():
            try:
                task = self.write_queue.get(timeout=1.0)
                if task is None: break # Shutdown signal
                
                sql, params = task
                try:
                    conn.execute(sql, params)
                    conn.commit()
                except Exception as e:
                    print(f"[-] Database Write Error: {e}")
                finally:
                    self.write_queue.task_done()
            except queue.Empty:
                continue
        conn.close()

    def execute(self, sql, params=()):
        """Executa um comando SQL diretamente (usar com cuidado fora do worker)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor

    def query(self, sql, params=()):
        """Executa um SELECT e retorna lista de dicionários"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error in query: {e}")
            return []

    def upsert_song(self, song_data):
        """Insere ou atualiza uma música no cache via fila"""
        sql = """
            INSERT INTO metadata_cache (
                file_path, artist, title, album, date, genre, duration, cover_path, file_mtime, bitrate, ext, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(file_path) DO UPDATE SET
                artist=excluded.artist,
                title=excluded.title,
                album=excluded.album,
                date=excluded.date,
                genre=excluded.genre,
                duration=excluded.duration,
                file_mtime=excluded.file_mtime,
                bitrate=excluded.bitrate,
                ext=excluded.ext,
                cover_path=COALESCE(metadata_cache.cover_path, excluded.cover_path),
                updated_at=CURRENT_TIMESTAMP
        """
        params = (
            song_data.get('file_path').lower().replace("\\", "/"),
            song_data.get('artist'),
            song_data.get('title'),
            song_data.get('album'),
            song_data.get('year'),
            song_data.get('genre'),
            song_data.get('duration'),
            song_data.get('cover_path'),
            song_data.get('file_mtime'),
            song_data.get('bitrate'),
            song_data.get('ext')
        )
        self.write_queue.put((sql, params))

    def prune_stale_songs(self, progress_callback=None):
        """Remove arquivos que não existem mais no disco"""
        print("[DB] Iniciando limpeza de registros órfãos...")
        paths_to_delete = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM metadata_cache")
            rows = cursor.fetchall()
            total = len(rows)
            
            for i, row in enumerate(rows):
                path = row['file_path']
                if not os.path.exists(path):
                    paths_to_delete.append(path)
                
                if progress_callback and i % 500 == 0:
                    progress_callback(i, total)
            
            if paths_to_delete:
                print(f"[DB] Removendo {len(paths_to_delete)} registros inexistentes...")
                # Deletar em lotes para evitar problemas de trava
                batch_size = 500
                for i in range(0, len(paths_to_delete), batch_size):
                    batch = paths_to_delete[i:i+batch_size]
                    placeholders = ', '.join(['?'] * len(batch))
                    cursor.execute(f"DELETE FROM metadata_cache WHERE file_path IN ({placeholders})", batch)
                conn.commit()
                
        print(f"[DB] Limpeza concluída. {len(paths_to_delete)} itens removidos.")
        return len(paths_to_delete)

    def get_total_count(self):
        """Retorna total de músicas"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metadata_cache")
            return cursor.fetchone()[0]

    def _get_new_music_condition(self):
        """Retorna a condição SQL para filtrar músicas 'novas' (hoje/ontem na madrugada)"""
        import datetime
        now = datetime.datetime.now()
        is_early_morning = now.hour < 5
        if is_early_morning:
            # Se for madrugada, 'novo' inclui ontem e hoje
            return "(date(indexed_at, 'localtime') = date('now', 'localtime') OR date(indexed_at, 'localtime') = date('now', '-1 day', 'localtime'))"
        else:
            return "date(indexed_at, 'localtime') = date('now', 'localtime')"

    def get_all_musics(self, limit=25, offset=0, only_new=False):
        """Retorna todas as músicas com paginação"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            where_clause = ""
            if only_new:
                where_clause = f"WHERE {self._get_new_music_condition()}"
                
            cursor.execute(f"""
                SELECT 
                    file_path, artist, title, album, date as year, genre, cover_path, 
                    COALESCE(favorite, 0) as favorite,
                    COALESCE(bitrate, 0) as bitrate, ext, duration, updated_at, indexed_at
                FROM metadata_cache
                {where_clause}
                ORDER BY updated_at DESC, artist, title
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def get_filtered_count(self, query, filter_path=None, only_new=False):
        """Retorna o total de músicas para uma determinada busca/filtro"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            new_cond = self._get_new_music_condition() if only_new else "1=1"
            
            # 1. Gênero (g:)
            if query.startswith("g:"):
                db_query = query[2:]
                cursor.execute(f"SELECT COUNT(*) FROM metadata_cache WHERE LOWER(genre) = LOWER(?) AND {new_cond}", (db_query,))
                return cursor.fetchone()[0]
            
            # 2. Artista (artist:)
            if query.startswith("artist:"):
                db_query = query[7:]
                search = f"%{db_query}%"
                cursor.execute(f"""
                    SELECT COUNT(*) FROM (
                        SELECT 1 FROM metadata_cache 
                        WHERE (artist LIKE ? OR LOWER(artist) LIKE LOWER(?) OR LOWER(file_path) LIKE LOWER(?))
                          AND {new_cond}
                        GROUP BY LOWER(title)
                    )
                """, (search, search, search))
                return cursor.fetchone()[0]
            
            # 3. Data (search_by_date tem limite interno de 150)
            if query and ("/" in query or query.lower() in ["hoje", "today"] or (len(query) == 4 and query.isdigit())):
                return len(self.search_by_date(query))
            
            # 4. Busca Geral (Deduplicada por Artista e Título)
            if query:
                search = f"%{query}%"
                cursor.execute(f"""
                    SELECT COUNT(*) FROM (
                        SELECT 1 FROM metadata_cache
                        WHERE (LOWER(artist) LIKE LOWER(?) OR LOWER(title) LIKE LOWER(?) OR LOWER(album) LIKE LOWER(?) OR LOWER(file_path) LIKE LOWER(?))
                          AND {new_cond}
                        GROUP BY LOWER(artist), LOWER(title)
                    )
                """, (search, search, search, search))
                return cursor.fetchone()[0]
                
            # 5. Caminho (Pasta)
            if filter_path:
                folder_search = filter_path.lower().replace("\\", "/")
                if not folder_search.endswith("/"): folder_search += "/"
                search = f"{folder_search}%"
                cursor.execute(f"SELECT COUNT(*) FROM metadata_cache WHERE LOWER(file_path) LIKE ? AND {new_cond}", (search,))
                return cursor.fetchone()[0]
                
            # 6. Todos (ou nenhum filtro)
            cursor.execute(f"SELECT COUNT(*) FROM metadata_cache WHERE {new_cond}")
            return cursor.fetchone()[0]
    
    def find_by_path(self, file_path):
        """Busca uma música específica pelo caminho"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path, artist, title, album, date as year, genre, cover_path, 
                       COALESCE(favorite, 0) as favorite, duration,
                       COALESCE(bitrate, 0) as bitrate, ext
                FROM metadata_cache WHERE LOWER(file_path) = LOWER(?)
            """, (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
    def search_musics(self, query, filter_type="Todos", limit=100, offset=0, only_new=False):
        """Busca músicas removendo duplicatas de Artista/Título (mantém a de melhor qualidade)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search = f"%{query}%"
            new_cond = self._get_new_music_condition() if only_new else "1=1"
            
            sql = f"""
                SELECT file_path, artist, title, album, date as year, genre, cover_path, favorite, bitrate, ext, duration
                FROM (
                    SELECT 
                        file_path, artist, title, album, date, genre, cover_path, 
                        COALESCE(favorite, 0) as favorite, COALESCE(bitrate, 0) as bitrate, ext,
                        duration,
                        ROW_NUMBER() OVER(PARTITION BY LOWER(artist), LOWER(title) ORDER BY bitrate DESC, file_mtime DESC) as rn
                    FROM metadata_cache
                    WHERE {new_cond} AND (
            """
            
            if filter_type == "Artista":
                sql += "LOWER(artist) LIKE LOWER(?)"
                params = (search,)
            elif filter_type == "Música":
                sql += "LOWER(title) LIKE LOWER(?)"
                params = (search,)
            elif filter_type == "Álbum":
                sql += "LOWER(album) LIKE LOWER(?)"
                params = (search,)
            elif filter_type == "Data":
                return self.search_by_date(query)
            else: # Todos
                sql += "(LOWER(artist) LIKE LOWER(?) OR LOWER(title) LIKE LOWER(?) OR LOWER(album) LIKE LOWER(?) OR LOWER(file_path) LIKE LOWER(?))"
                params = (search, search, search, search)
                
            sql += """
                )) t
                WHERE rn = 1
                ORDER BY artist, title
                LIMIT ? OFFSET ?
            """
            params += (limit, offset)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def search_by_date(self, val):
        """Busca músicas por data (Adição ou Lançamento)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            import datetime
            now = datetime.datetime.now()
            
            conditions = []
            params = []
            
            # Limpeza básica do input e suporte a outros separadores
            val = val.strip().lower()
            val_clean = val.replace("-", "/").replace(".", "/")
            
            # Casos Especiais
            if val in ["hoje", "today"]:
                is_early_morning = now.hour < 5
                if is_early_morning:
                    # Se for madrugada, 'hoje' inclui as músicas de ontem e hoje
                    conditions.append("(date(indexed_at, 'localtime') = date('now', 'localtime') OR date(indexed_at, 'localtime') = date('now', '-1 day', 'localtime'))")
                else:
                    conditions.append("date(indexed_at, 'localtime') = date('now', 'localtime')")
            elif val in ["ontem", "yesterday"]:
                conditions.append("date(indexed_at, 'localtime') = date('now', '-1 day', 'localtime')")
            elif val.isdigit() and len(val) == 4: # AAAA (Busca por Ano de Lançamento ou Adição)
                conditions.append("(date LIKE ? OR strftime('%Y', indexed_at, 'localtime') = ?)")
                params.extend([f"{val}%", val])
            elif "/" in val_clean:
                parts = val_clean.split('/')
                if len(parts) == 2: # DD/MM ou MM/AAAA
                    if len(parts[1]) == 4: # MM/AAAA
                        conditions.append("strftime('%m/%Y', indexed_at, 'localtime') = ?")
                        params.append(f"{parts[0].zfill(2)}/{parts[1]}")
                    else: # DD/MM (Ano Atual)
                        date_str = f"{now.year}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                        conditions.append("date(indexed_at, 'localtime') = ?")
                        params.append(date_str)
                elif len(parts) == 3: # DD/MM/AAAA
                    year = parts[2]
                    if len(year) == 2: year = f"20{year}"
                    date_str = f"{year}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                    conditions.append("date(indexed_at, 'localtime') = ?")
                    params.append(date_str)
            else:
                # Busca genérica em texto nas colunas de data
                conditions.append("(date LIKE ? OR indexed_at LIKE ?)")
                params.extend([f"%{val}%", f"%{val}%"])

            sql = f"""
                SELECT file_path, artist, title, album, date as year, genre, cover_path, 
                       COALESCE(favorite, 0) as favorite, duration,
                       COALESCE(bitrate, 0) as bitrate, ext
                FROM metadata_cache 
                WHERE {' OR '.join(conditions)}
                ORDER BY indexed_at DESC, updated_at DESC
                LIMIT 150
            """
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def search_by_artist(self, artist_name, limit=200):
        """Busca músicas EXATAS de um artista, evitando misturar com outros nomes parecidos."""
        if not artist_name: return []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Buscamos pelo nome exato (Title Case) para evitar falsos positivos do LIKE %...%
            # Mas mantemos um LIKE restrito apenas se não houver match exato.
            # Otimização: Particionamos por título E artista para não remover músicas de artistas diferentes com mesmo nome
            
            cursor.execute("""
                SELECT file_path, artist, title, album, year, genre, cover_path, favorite, duration, bitrate, ext
                FROM (
                    SELECT file_path, artist, title, album, date as year, genre, cover_path, 
                           COALESCE(favorite, 0) as favorite, duration,
                           COALESCE(bitrate, 0) as bitrate, ext,
                           ROW_NUMBER() OVER(PARTITION BY LOWER(artist), LOWER(title) ORDER BY bitrate DESC) as rn
                    FROM metadata_cache
                    WHERE (LOWER(artist) = LOWER(?)) 
                       OR (artist IS NULL AND LOWER(file_path) LIKE LOWER(?))
                ) t
                WHERE rn = 1
                ORDER BY album ASC, title ASC
                LIMIT ?
            """, (artist_name, f"%/{artist_name}/%", limit))
            
            results = [dict(row) for row in cursor.fetchall()]
            
            # Se a busca exata falhou (raro via card), tentamos a busca amigável (LIKE)
            if not results:
                search = f"%{artist_name}%"
                cursor.execute("""
                    SELECT file_path, artist, title, album, year, genre, cover_path, favorite, duration, bitrate, ext
                    FROM (
                        SELECT file_path, artist, title, album, date as year, genre, cover_path, 
                               COALESCE(favorite, 0) as favorite, duration,
                               COALESCE(bitrate, 0) as bitrate, ext,
                               ROW_NUMBER() OVER(PARTITION BY LOWER(title) ORDER BY bitrate DESC) as rn
                        FROM metadata_cache
                        WHERE LOWER(artist) LIKE LOWER(?)
                    ) t
                    WHERE rn = 1
                    ORDER BY artist ASC, album ASC, title ASC
                    LIMIT ?
                """, (search, limit))
                results = [dict(row) for row in cursor.fetchall()]
                
            return results

    def get_musics_by_path(self, path_prefix, limit=50, offset=0, only_new=False):
        """Retorna músicas cujos caminhos começam com o prefixo (pasta selecionada)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Normalizar para busca (garantir que termina com barra se não for arquivo)
            folder_search = path_prefix.lower().replace("\\", "/")
            if not folder_search.endswith("/"): folder_search += "/"
            
            search = f"{folder_search}%"
            new_cond = self._get_new_music_condition() if only_new else "1=1"
            
            cursor.execute(f"""
                SELECT 
                    file_path, artist, title, album, date as year, genre, cover_path, 
                    COALESCE(favorite, 0) as favorite,
                    COALESCE(bitrate, 0) as bitrate, ext, duration,
                    updated_at, indexed_at
                FROM metadata_cache
                WHERE LOWER(file_path) LIKE ? AND {new_cond}
                ORDER BY updated_at DESC, artist, title
                LIMIT ? OFFSET ?
            """, (search, limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    def get_musics_by_genre(self, genre, limit=50, offset=0):
        """Retorna músicas filtradas por gênero"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    file_path, artist, title, album, date as year, genre, cover_path, 
                    COALESCE(favorite, 0) as favorite,
                    COALESCE(bitrate, 0) as bitrate, ext, duration,
                    updated_at, indexed_at
                FROM metadata_cache
                WHERE LOWER(genre) = LOWER(?)
                ORDER BY updated_at DESC, artist, title
                LIMIT ? OFFSET ?
            """, (genre, limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def get_top_level_folders(self, root_path):
        """
        Extrai as pastas de 1º nível dentro do root_path de forma OTIMIZADA.
        Faz a extração e contagem diretamente no SQL para maior performance.
        """
        if not root_path: return []
        
        # Normalização rigorosa
        root_path = root_path.replace("\\", "/").rstrip("/") + "/"
        root_len = len(root_path)
        
        # SQLite Query para extrair o primeiro segmento da pasta após o root_path
        # 1. Pegamos a substring após o root_path
        # 2. Procuramos a primeira barra nessa substring
        # 3. Se houver barra, pegamos o texto até ela. Se não houver, é um arquivo na raiz (ignoramos ou tratamos)
        
        sql = f"""
            SELECT 
                SUBSTR(file_path, {root_len + 1}, INSTR(SUBSTR(file_path, {root_len + 1}), '/') - 1) as folder,
                COUNT(*) as count
            FROM metadata_cache 
            WHERE LOWER(file_path) LIKE ?
            GROUP BY folder
            HAVING folder IS NOT NULL AND folder != ''
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (f"{root_path.lower()}%",))
                
                result = []
                for row in cursor.fetchall():
                    folder_name = row['folder']
                    result.append({
                        'genre': folder_name,
                        'count': row['count'],
                        'path': f"{root_path}{folder_name}"
                    })
                
                # Ordenação final por nome de gênero
                result.sort(key=lambda x: str(x.get("genre", "")).lower())
                return result
        except Exception as e:
            print(f"[DB] Erro em get_top_level_folders: {e}")
            # Fallback para o método anterior (mais lento mas seguro) se houver erro de sintaxe SQL
            return self._get_top_level_folders_fallback(root_path)

    def _get_top_level_folders_fallback(self, root_path):
        """Método fallback para extração de pastas"""
        root_path = root_path.lower().replace("\\", "/").rstrip("/") + "/"
        root_len = len(root_path)
        folders_count = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM metadata_cache WHERE LOWER(file_path) LIKE ?", (f"{root_path}%",))
            for row in cursor.fetchall():
                path = row['file_path'].replace("\\", "/")
                relative = path[root_len:]
                if "/" in relative:
                    category = relative.split("/")[0]
                    if category:
                        folders_count[category] = folders_count.get(category, 0) + 1
            result = []
            for folder, count in sorted(folders_count.items()):
                result.append({'genre': folder, 'count': count, 'path': f"{root_path}{folder}"})
            return result

    def get_artist_info(self, artist_name):
        """Retorna informações de um artista"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT 
                    artist, 
                    album, 
                    date as year, 
                    genre,
                    COUNT(*) as song_count
                FROM metadata_cache
                WHERE artist LIKE ?
                GROUP BY album
                ORDER BY date
            """, (f"%{artist_name}%",))
            return [dict(row) for row in cursor.fetchall()]
    
    def create_playlist(self, name, description=""):
        """Cria uma nova playlist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO playlists (name, description) VALUES (?, ?)", (name, description))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Playlist with name {name} already exists.")
            return -1 # Specific code for duplicate
        except Exception as e:
            print(f"Error creating playlist: {e}")
            return None

    def delete_playlist(self, playlist_id):
        """Remove uma playlist permanentemente"""
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
                conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting playlist: {e}")
            return False

    def rename_playlist(self, playlist_id, new_name):
        """Altera o nome de uma playlist"""
        try:
            with self.get_connection() as conn:
                conn.execute("UPDATE playlists SET name = ? WHERE id = ?", (new_name, playlist_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error renaming playlist: {e}")
            return False

    def add_to_playlist(self, playlist_id, file_path):
        """Adiciona música a uma playlist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(position) FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
            res = cursor.fetchone()
            pos = (res[0] or 0) + 1
            try:
                cursor.execute("INSERT INTO playlist_songs (playlist_id, file_path, position) VALUES (?, ?, ?)", 
                               (playlist_id, file_path, pos))
                conn.commit()
                return True
            except: return False

    def get_playlists(self):
        """Retorna todas as playlists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se as tabelas existem
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playlists'")
            if not cursor.fetchone():
                return []
            
            cursor.execute("SELECT id, name FROM playlists ORDER BY name")
            playlists = []
            for row in cursor.fetchall():
                cursor.execute("""
                    SELECT file_path FROM playlist_songs 
                    WHERE playlist_id = ? ORDER BY position
                """, (row['id'],))
                songs = [r['file_path'] for r in cursor.fetchall()]
                playlists.append({
                    'id': row['id'],
                    'name': row['name'],
                    'songs': songs,
                    'song_count': len(songs)
                })
            return playlists
    
    def get_favorites(self):
        """Retorna músicas favoritas"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    file_path, artist, title, album, date as year, genre, cover_path, 
                    COALESCE(favorite, 0) as favorite,
                    COALESCE(bitrate, 0) as bitrate, ext, duration,
                    updated_at, indexed_at
                FROM metadata_cache
                WHERE favorite = 1
                ORDER BY updated_at DESC, artist, title
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_recently_played(self, limit=15):
        """
        Músicas tocadas ou adicionadas recentemente.
        OTIMIZADO: Busca os últimos 500 registros e então deduplica para evitar lentidão.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path, artist, title, album, year, genre, cover_path, bitrate, ext, favorite, updated_at, indexed_at, last_played
                FROM (
                    SELECT file_path, artist, title, album, date as year, genre, cover_path, 
                           COALESCE(bitrate, 0) as bitrate, ext,
                           COALESCE(favorite, 0) as favorite, updated_at, indexed_at, last_played,
                           MAX(COALESCE(last_played, '0000-00-00'), 
                               COALESCE(datetime(file_mtime, 'unixepoch'), '0000-00-00'), 
                               COALESCE(updated_at, '0000-00-00')) as event_time,
                           ROW_NUMBER() OVER(PARTITION BY LOWER(artist), LOWER(title) 
                                            ORDER BY CASE WHEN last_played IS NOT NULL THEN 1 ELSE 0 END DESC,
                                                     MAX(COALESCE(last_played, '0000-00-00'), 
                                                         COALESCE(datetime(file_mtime, 'unixepoch'), '0000-00-00'), 
                                                         COALESCE(updated_at, '0000-00-00')) DESC,
                                                     bitrate DESC) as rn
                    FROM (
                        SELECT * FROM metadata_cache 
                        ORDER BY COALESCE(last_played, updated_at, indexed_at) DESC
                        LIMIT 500
                    ) t_inner
                ) t
                WHERE rn = 1
                ORDER BY event_time DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_most_played(self, limit=15):
        """
        Músicas mais tocadas pelo usuário.
        OTIMIZADO: Filtra apenas músicas com play_count > 0 antes de deduplicar.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path, artist, title, album, year, genre, cover_path, favorite
                FROM (
                    SELECT file_path, artist, title, album, date as year, genre, cover_path, 
                           COALESCE(favorite, 0) as favorite, play_count,
                           ROW_NUMBER() OVER(PARTITION BY LOWER(artist), LOWER(title) ORDER BY play_count DESC, bitrate DESC) as rn
                    FROM metadata_cache
                    WHERE play_count > 0
                    ORDER BY play_count DESC
                    LIMIT 500
                ) t
                WHERE rn = 1
                ORDER BY play_count DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_suggested_genres(self, limit=100):
        """Gêneros populares"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT genre, COUNT(*) as count 
                FROM metadata_cache 
                WHERE genre IS NOT NULL AND genre != ''
                GROUP BY genre 
                ORDER BY count DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ─── PONTO #1: Lista de nomes descartáveis ───────────────────────────────
    _TRASH_ARTISTS = {
        '', 'unknown', 'unknown artist', 'various', 'various artists',
        'va', 'v.a.', 'v.a', 'artista desconhecido', 'artist unknown',
        'track', 'faixa', 'sem artista', 'no artist', 'undefined'
    }

    def _is_trash_artist(self, name):
        """Retorna True se o nome for lixo/genérico"""
        if not name: return True
        return name.strip().lower() in self._TRASH_ARTISTS

    def normalize_artists(self):
        """PONTO #1 — Normaliza capitalização e remove duplicatas de artista no banco.
        - Converte UPPER e lower para Title Case
        - Reactualiza quality_score de todos os registros
        Executa diretamente (não via fila) para ser chamado como manutenção."""
        print("[DB] Iniciando normalização de artistas...")
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Buscar todos os artistas únicos
            cursor.execute("SELECT DISTINCT artist FROM metadata_cache WHERE artist IS NOT NULL AND artist != ''")
            artists = [row[0] for row in cursor.fetchall()]

            updated = 0
            for raw in artists:
                if not raw: continue
                # Title Case simples (respeita acentos)
                normalized = raw.strip().title()
                if normalized != raw:
                    try:
                        cursor.execute(
                            "UPDATE metadata_cache SET artist = ?, updated_at = CURRENT_TIMESTAMP WHERE artist = ?",
                            (normalized, raw)
                        )
                        updated += cursor.rowcount
                    except Exception as e:
                        print(f"[DB] Erro ao normalizar artista '{raw}': {e}")

            # 2. Recalcular quality_score para todos
            cursor.execute("""
                UPDATE metadata_cache SET quality_score = (
                    CASE WHEN artist   IS NOT NULL AND artist != ''  THEN 20 ELSE 0 END +
                    CASE WHEN title    IS NOT NULL AND title  != ''  THEN 20 ELSE 0 END +
                    CASE WHEN album    IS NOT NULL AND album  != ''  THEN 20 ELSE 0 END +
                    CASE WHEN cover_path IS NOT NULL AND cover_path != '' THEN 25 ELSE 0 END +
                    CASE WHEN date     IS NOT NULL AND date   != ''  THEN 8  ELSE 0 END +
                    CASE WHEN genre    IS NOT NULL AND genre  != ''  THEN 7  ELSE 0 END
                )
            """)
            conn.commit()
            total_scored = cursor.rowcount
            print(f"[DB] Normalização concluída: {updated} artistas normalizados, {total_scored} quality_scores atualizados.")

    def get_top_artists(self, limit=12):
        """Artistas mais frequentes, filtrando lixo, deduplica case-insensitive,
        prioriza quem tem imagem e maior quality_score."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    MAX(artist) as artist,
                    COUNT(*) as song_count,
                    SUM(COALESCE(play_count, 0)) as total_plays,
                    MAX(artist_photo) as artist_photo,
                    COALESCE(MAX(artist_photo), MAX(cover_path)) as cover_path,
                    MAX(file_path) as file_path,
                    MAX(COALESCE(quality_score, 0)) as best_quality
                FROM metadata_cache
                WHERE
                    artist IS NOT NULL AND TRIM(artist) != ''
                    AND LOWER(TRIM(artist)) NOT IN (
                        'unknown', 'unknown artist', 'various', 'various artists',
                        'va', 'v.a.', 'v.a', 'artista desconhecido', 'artist unknown',
                        'track', 'faixa', 'sem artista', 'no artist', 'undefined'
                    )
                GROUP BY LOWER(TRIM(artist))
                ORDER BY total_plays DESC, song_count DESC, best_quality DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_random_artists(self, limit=12):
        """Artistas aleatórios para descoberta.
        Filtra lixo, prioriza quem tem imagem (cover ou artist_photo)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    MAX(artist) as artist,
                    COUNT(*) as song_count,
                    MAX(artist_photo) as artist_photo,
                    COALESCE(MAX(artist_photo), MAX(cover_path)) as cover_path,
                    MAX(COALESCE(quality_score, 0)) as best_quality
                FROM metadata_cache
                WHERE
                    artist IS NOT NULL AND TRIM(artist) != ''
                    AND LOWER(TRIM(artist)) NOT IN (
                        'unknown', 'unknown artist', 'various', 'various artists',
                        'va', 'v.a.', 'v.a', 'artista desconhecido', 'artist unknown',
                        'track', 'faixa', 'sem artista', 'no artist', 'undefined'
                    )
                GROUP BY LOWER(TRIM(artist))
                HAVING song_count >= 2
                ORDER BY
                    CASE WHEN MAX(artist_photo) IS NOT NULL THEN 0 ELSE 1 END,
                    CASE WHEN MAX(cover_path) IS NOT NULL THEN 0 ELSE 1 END,
                    RANDOM()
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_musics_by_genre(self, genre, limit=15, offset=0, only_new=False):
        """Músicas de um gênero específico com paginação (case-insensitive)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            new_cond = self._get_new_music_condition() if only_new else "1=1"
            
            cursor.execute(f"""
                SELECT file_path, artist, title, album, date as year, genre, cover_path, 
                       COALESCE(favorite, 0) as favorite, updated_at, indexed_at
                FROM metadata_cache 
                WHERE LOWER(genre) = LOWER(?) AND {new_cond}
                ORDER BY updated_at DESC, play_count DESC, title ASC
                LIMIT ? OFFSET ?
            """, (genre, limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def toggle_favorite(self, file_path):
        """Alterna status de favorito e retorna o novo valor via fila"""
        path = file_path.lower().replace("\\", "/")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT favorite FROM metadata_cache WHERE file_path = ?", (path,))
            res = cursor.fetchone()
            current = res[0] if res and res[0] is not None else 0
            new_val = 1 if current == 0 else 0
            
            sql = "UPDATE metadata_cache SET favorite = ? WHERE file_path = ?"
            self.write_queue.put((sql, (new_val, path)))
            return new_val == 1

    def update_play_stats(self, file_path):
        """Atualiza estatísticas de reprodução via fila"""
        path = file_path.lower().replace("\\", "/")
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = "UPDATE metadata_cache SET play_count = play_count + 1, last_played = ? WHERE file_path = ?"
        self.write_queue.put((sql, (now, path)))

    def remove_from_playlist(self, playlist_id, file_path):
        """Remove música de uma playlist via fila"""
        sql = "DELETE FROM playlist_songs WHERE playlist_id = ? AND file_path = ?"
        params = (playlist_id, file_path.lower().replace("\\", "/"))
        self.write_queue.put((sql, params))
        return True # Accepted for processing
    
    def get_stats(self):
        """Retorna estatísticas da biblioteca"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            stats = {}
            
            # Total
            cursor.execute("SELECT COUNT(*) FROM metadata_cache")
            stats['total'] = cursor.fetchone()[0]
            
            # Artistas únicos
            cursor.execute("SELECT COUNT(DISTINCT artist) FROM metadata_cache WHERE artist IS NOT NULL AND artist != ''")
            stats['artists'] = cursor.fetchone()[0]
            
            # Álbuns únicos
            cursor.execute("SELECT COUNT(DISTINCT album) FROM metadata_cache WHERE album IS NOT NULL AND album != ''")
            stats['albums'] = cursor.fetchone()[0]
            
            # Gêneros (top 5)
            cursor.execute("""
                SELECT genre, COUNT(*) as count 
                FROM metadata_cache 
                WHERE genre IS NOT NULL AND genre != ''
                GROUP BY genre 
                ORDER BY count DESC 
                LIMIT 5
            """)
            stats['top_genres'] = [dict(row) for row in cursor.fetchall()]

            # Décadas
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN date >= '2020' THEN '2020s'
                        WHEN date >= '2010' THEN '2010s'
                        WHEN date >= '2000' THEN '2000s'
                        WHEN date >= '1990' THEN '1990s'
                        WHEN date >= '1980' THEN '1980s'
                        ELSE 'Earlier'
                    END as decade,
                    COUNT(*) as count
                FROM metadata_cache 
                WHERE date IS NOT NULL AND date != '' AND LENGTH(date) >= 4
                GROUP BY decade
                ORDER BY decade
            """)
            stats['decades'] = [dict(row) for row in cursor.fetchall()]

            # Top Artistas (Ordenados por reproduções + volume)
            cursor.execute("""
                SELECT 
                    MAX(artist) as artist, 
                    COUNT(*) as count, 
                    SUM(COALESCE(play_count, 0)) as total_plays,
                    COALESCE(MAX(artist_photo), MAX(cover_path)) as cover_path
                FROM metadata_cache 
                WHERE artist IS NOT NULL AND TRIM(artist) != ''
                GROUP BY LOWER(TRIM(artist))
                ORDER BY total_plays DESC, count DESC 
                LIMIT 8
            """)
            stats['top_artists'] = [dict(row) for row in cursor.fetchall()]

            # Duração Total
            cursor.execute("SELECT SUM(duration) FROM metadata_cache")
            stats['total_duration'] = cursor.fetchone()[0] or 0

            # Total de Reproduções
            cursor.execute("SELECT SUM(play_count) FROM metadata_cache")
            stats['total_plays'] = cursor.fetchone()[0] or 0

            # Favoritos
            cursor.execute("SELECT COUNT(*) FROM metadata_cache WHERE favorite = 1")
            stats['favorites'] = cursor.fetchone()[0]
            
            return stats

    def get_top_genres(self, limit=5):
        """Retorna os gêneros mais comuns na biblioteca"""
        return self.query("""
            SELECT genre, COUNT(*) as count 
            FROM metadata_cache 
            WHERE genre IS NOT NULL AND genre != ''
            GROUP BY genre 
            ORDER BY count DESC 
            LIMIT ?
        """, (limit,))

    def get_count_by_genre(self, genre):
        """Retorna o número de músicas de um gênero específico"""
        res = self.query("SELECT COUNT(*) as Q FROM metadata_cache WHERE genre = ?", (genre,))
        return res[0]['Q'] if res else 0

    def update_song_metadata(self, file_path, data):
        """Atualiza metadados no banco de dados com suporte a updates parciais"""
        path = file_path.lower().replace("\\", "/")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = []
            params = []
            
            # Mapeamento do dicionário para as colunas do banco
            mappings = {
                'title': 'title',
                'artist': 'artist',
                'album': 'album',
                'year': 'date',
                'genre': 'genre',
                'cover_path': 'cover_path',
                'artist_photo': 'artist_photo',  # PONTO #4
                'bitrate': 'bitrate',
                'ext': 'ext',
                'favorite': 'favorite'
            }
            
            for key, col in mappings.items():
                if key in data and data[key] is not None:
                    fields.append(f"{col} = ?")
                    params.append(data[key])
            
            if not fields: return

            # PONTO #5 — Recalcular quality_score automaticamente
            fields.append("""
                quality_score = (
                    CASE WHEN COALESCE(title,  '') != '' THEN 20 ELSE 0 END +
                    CASE WHEN COALESCE(artist, '') != '' THEN 20 ELSE 0 END +
                    CASE WHEN COALESCE(album,  '') != '' THEN 20 ELSE 0 END +
                    CASE WHEN COALESCE(cover_path, '') != '' THEN 25 ELSE 0 END +
                    CASE WHEN COALESCE(date,   '') != '' THEN 8  ELSE 0 END +
                    CASE WHEN COALESCE(genre,  '') != '' THEN 7  ELSE 0 END
                )
            """)

            sql = f"UPDATE metadata_cache SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE file_path = ?"
            params.append(path)
            
            try:
                cursor.execute(sql, params)
                conn.commit()
                print(f"[DB] Sucesso ao atualizar metadados de: {os.path.basename(path)}")
            except Exception as e:
                print(f"[DB] Erro ao atualizar metadados: {e}")

    # --- MÉTODOS DE CACHE DE API ---
    
    def get_cached_artist(self, artist_name):
        """Busca informações rápidas pré-salvas do artista"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM artist_cache WHERE artist_name = ?", (artist_name,))
            artist = cursor.fetchone()
            if not artist: return None
            
            cursor.execute("SELECT album_name as name, album_cover as cover, album_year as year, album_type as type FROM album_cache WHERE artist_name = ?", (artist_name,))
            disco = [dict(row) for row in cursor.fetchall()]
            
            res = dict(artist)
            res['discography'] = disco
            res['cover'] = res['cover_url'] # Normalizar nome
            return res

    def save_artist_cache(self, artist_name, data):
        """Salva informações da API para acesso ultra-rápido no futuro"""
        sql_art = """
            INSERT INTO artist_cache (artist_name, bio, cover_url, followers, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(artist_name) DO UPDATE SET
                bio=excluded.bio, cover_url=excluded.cover_url,
                followers=excluded.followers, last_updated=CURRENT_TIMESTAMP
        """
        params_art = (artist_name, data.get('bio'), data.get('cover'), data.get('followers'))
        self.write_queue.put((sql_art, params_art))
        
        # Limpar discografia antiga e salvar nova
        self.write_queue.put(("DELETE FROM album_cache WHERE artist_name = ?", (artist_name,)))
        
        for album in data.get('discography', []):
            sql_alb = """
                INSERT INTO album_cache (artist_name, album_name, album_cover, album_year, album_type)
                VALUES (?, ?, ?, ?, ?)
            """
            params_alb = (artist_name, album.get('name'), album.get('cover'), album.get('year'), album.get('type'))
            self.write_queue.put((sql_alb, params_alb))
        
        print(f"[DB] Cache do artista '{artist_name}' salvo com sucesso!")

    def update_artist_photo(self, artist_name, photo_path):
        """Atualiza a foto de todas as músicas de um artista"""
        sql = "UPDATE metadata_cache SET artist_photo = ? WHERE artist = ?"
        self.write_queue.put((sql, (photo_path, artist_name)))

    def update_album_cover(self, artist_name, album_name, cover_path):
        """Atualiza a capa de todas as músicas de um álbum específico"""
        sql = "UPDATE metadata_cache SET cover_path = ? WHERE artist = ? AND album = ?"
        self.write_queue.put((sql, (cover_path, artist_name, album_name)))

    def get_cached_label(self, label_name):
        """Retorna informações salvas de uma gravadora"""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM label_cache WHERE label_name = ?", (label_name,)).fetchone()
            if row:
                import json
                data = dict(row)
                if data.get('sublabels'):
                    data['sublabels'] = json.loads(data['sublabels'])
                return data
        return None

    def save_label_cache(self, label_name, info):
        """Salva informações da gravadora no cache"""
        import json
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO label_cache 
                (label_name, profile, logo_url, sublabels, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                label_name,
                info.get('profile'),
                info.get('logo_url'),
                json.dumps(info.get('sublabels', []))
            ))
        print(f"[DB] Cache da gravadora '{label_name}' salvo com sucesso!")
    def toggle_artist_favorite(self, artist_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Garante que o artista existe no cache
            cursor.execute("INSERT OR IGNORE INTO artist_cache (artist_name) VALUES (?)", (artist_name,))
            cursor.execute("UPDATE artist_cache SET favorite = 1 - COALESCE(favorite, 0) WHERE artist_name = ?", (artist_name,))
            conn.commit()
            
    def is_artist_favorite(self, artist_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT favorite FROM artist_cache WHERE artist_name = ?", (artist_name,))
            row = cursor.fetchone()
            return bool(row[0]) if row else False
