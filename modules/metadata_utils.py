import re
import os

class MetadataCleaner:
    @staticmethod
    def clean_text(text):
        """Limpeza profunda de strings.
        Protege nomes de artistas como '50 Cent' e '2NOISE'."""
        if not text: return ""
        t = str(text).strip()
        
        # 1. Remover extensões comuns
        t = re.sub(r'\.(mp3|flac|wav|m4a|ogg|wma)$', '', t, flags=re.IGNORECASE)
        
        # 2. Loop para limpeza seletiva
        for _ in range(3):
            # A. Remover números que começam com ZERO (quase sempre faixa: 01, 002)
            t = re.sub(r'^0\d+\s*[.\-_]?\s*', '', t)
            
            # B. Remover números seguidos de SEPARADOR explícito (Ex: "1 - Artista" ou "1. Artista")
            # Mas PROTEGE "5 Seconds of Summer" ou "50 Cent" (que não têm . ou - logo após o número)
            t = re.sub(r'^\d+\s*[.\-_]\s*', '', t)
            
            # C. Remover aspas envolventes
            t = t.strip().strip("'\"").strip()
            
            # D. Remover pontos e espaços residuais nas extremidades
            t = t.strip(". ")
            
        return t

    @classmethod
    def smart_clean(cls, title, artist, filename=""):
        """Inteligência completa para separar Artista/Música e limpar assinaturas."""
        junk_patterns = [
            "R I C A R D O", "Dj 77", "RICARDO", "R.I.C.A.R.D.O", 
            "www.", ".com", ".br", "Download", "Baixar", "By Ricard"
        ]
        
        # 0. Fallback para filename se campos estiverem vazios
        if (not title or str(title).lower() in ["unknown", "n/a", ""]) and filename:
             title = filename.rsplit('.', 1)[0]

        cleaned_artist = str(artist) if artist else ""
        cleaned_title = str(title) if title else ""
        
        # 1. Identificar se o Artista é "Lixo" (Apenas números, assinaturas ou vazio)
        # Se o campo artista for só "002" ou "02", tratamos como junk para buscar no título/filename
        is_only_numbers = cleaned_artist.strip().isdigit()
        is_artist_junk = is_only_numbers or any(p.lower() in cleaned_artist.lower() for p in junk_patterns) or len(cleaned_artist.strip()) < 2
        
        separators = [" - ", " – ", " — ", "  -  "]
        split_done = False
        
        # 2. Tentar detectar Artista - Música dentro do campo Título
        for sep in separators:
            if sep in cleaned_title:
                parts = cleaned_title.split(sep, 1)
                new_artist = parts[0].strip()
                new_title = parts[1].strip()
                
                if is_artist_junk:
                    cleaned_artist = new_artist
                    cleaned_title = new_title
                    split_done = True
                    break
                elif new_artist.lower() in cleaned_artist.lower():
                    cleaned_title = new_title
                    split_done = True
                    break

        # 2. Extração via Filename se necessário
        if (is_artist_junk or not split_done) and filename:
            fname_no_ext = filename.rsplit('.', 1)[0]
            for sep in separators:
                if sep in fname_no_ext:
                    parts = fname_no_ext.split(sep, 1)
                    if is_artist_junk:
                        cleaned_artist = parts[0].strip()
                    if not split_done or len(cleaned_title) < 3:
                        cleaned_title = parts[1].strip()
                    break

        # 3. Remover lixo estático (assinaturas)
        for p in junk_patterns:
            cleaned_artist = re.sub(re.escape(p), "", cleaned_artist, flags=re.IGNORECASE).strip()
            cleaned_title = re.sub(re.escape(p), "", cleaned_title, flags=re.IGNORECASE).strip()

        # 4. NOVO: Remover participações (feat, ft, featuring, part) do ARTISTA
        # Isso garante que a busca na API seja feita apenas pelo artista principal
        feat_patterns = [r'\s+feat\.?\s+.*$', r'\s+ft\.?\s+.*$', r'\s+featuring\s+.*$', r'\s+part\.?\s+.*$']
        for fp in feat_patterns:
            cleaned_artist = re.sub(fp, "", cleaned_artist, flags=re.IGNORECASE).strip()

        # 5. Aplicação das Regras de Limpeza de Caracteres (Números, Aspas, Pontos)
        cleaned_artist = cls.clean_text(cleaned_artist)
        cleaned_title = cls.clean_text(cleaned_title)

        return cleaned_title, cleaned_artist
