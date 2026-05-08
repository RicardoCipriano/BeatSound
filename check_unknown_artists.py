import sqlite3
import os

def check_unknown_artists():
    db_path = os.path.join(os.path.dirname(__file__), "music.db")
    if not os.path.exists(db_path):
        print(f"Erro: Banco de dados não encontrado em {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query para buscar artistas com 'unknown' no nome
        query = """
        SELECT DISTINCT artist, COUNT(*) as music_count 
        FROM metadata_cache 
        WHERE LOWER(artist) LIKE '%unknown%' 
        GROUP BY artist 
        ORDER BY music_count DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()

        print("\n=== Relatório de Artistas Desconhecidos (Unknown) ===")
        if not rows:
            print("Parabéns! Nenhuma música com descrição 'unknown' encontrada.")
        else:
            print(f"Encontrados {len(rows)} variações de artistas desconhecidos:\n")
            print(f"{'Artista':<40} | {'Qtd Músicas':<12}")
            print("-" * 55)
            for row in rows:
                print(f"{row['artist']:<40} | {row['music_count']:<12}")
        
        conn.close()
    except Exception as e:
        print(f"Erro ao acessar o banco: {e}")

if __name__ == "__main__":
    check_unknown_artists()
