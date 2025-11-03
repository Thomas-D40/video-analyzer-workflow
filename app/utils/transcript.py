"""
Utilitaire pour extraire la transcription d'une vidéo YouTube.

Utilise yt-dlp pour télécharger et parser la transcription automatique
ou manuelle de la vidéo.
"""
import yt_dlp
from typing import Optional
import tempfile
import os


def extract_transcript(youtube_url: str) -> Optional[str]:
    """
    Extrait la transcription d'une vidéo YouTube.
    
    Args:
        youtube_url: URL complète de la vidéo YouTube
        
    Returns:
        Transcription sous forme de texte, ou None si indisponible
    """
    # Configuration yt-dlp pour extraire uniquement la transcription
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['fr', 'en'],  # Priorité français puis anglais
        'skip_download': True,  # On ne télécharge pas la vidéo
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Récupération des informations de la vidéo
            info = ydl.extract_info(youtube_url, download=False)
            
            # Tentative d'extraction de la transcription
            # yt-dlp stocke les sous-titres dans 'subtitles' ou 'automatic_captions'
            subtitles_data = info.get('subtitles', {}) or info.get('automatic_captions', {})
            
            # Recherche de la meilleure langue disponible
            transcript_text = None
            for lang in ['fr', 'en']:
                if lang in subtitles_data:
                    # On utilise une approche alternative: télécharger les sous-titres dans un fichier temporaire
                    with tempfile.TemporaryDirectory() as tmpdir:
                        sub_opts = {
                            'writesubtitles': True,
                            'writeautomaticsub': False,
                            'subtitleslangs': [lang],
                            'skip_download': True,
                            'quiet': True,
                            'outtmpl': os.path.join(tmpdir, 'subtitle.%(ext)s'),
                        }
                        with yt_dlp.YoutubeDL(sub_opts) as sub_ydl:
                            try:
                                sub_ydl.download([youtube_url])
                                # Chercher le fichier de sous-titres généré
                                for ext in ['vtt', 'srt']:
                                    sub_file = os.path.join(tmpdir, f'subtitle.{ext}')
                                    if os.path.exists(sub_file):
                                        transcript_text = _parse_subtitle_file(sub_file)
                                        if transcript_text:
                                            return transcript_text
                            except Exception:
                                continue
            
            # Si aucune transcription n'est trouvée, on peut essayer de récupérer la description
            # qui contient parfois des informations utiles
            description = info.get('description', '')
            if description and len(description) > 100:
                return description[:5000]  # Limite à 5000 caractères
            
            return None
            
    except Exception as e:
        # En cas d'erreur, on retourne None
        print(f"Erreur lors de l'extraction de la transcription: {e}")
        return None


def _parse_subtitle_file(file_path: str) -> Optional[str]:
    """
    Parse un fichier de sous-titres (.vtt ou .srt) et extrait le texte.
    
    Args:
        file_path: Chemin vers le fichier de sous-titres
        
    Returns:
        Texte extrait des sous-titres
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parsing simple: on enlève les timestamps et les balises
        lines = content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # Ignorer les lignes vides, les timestamps, et les numéros de séquence
            if not line or '-->' in line or line.isdigit():
                continue
            # Enlever les balises HTML/VTT
            line = line.replace('<c>', '').replace('</c>', '')
            line = line.replace('<i>', '').replace('</i>', '')
            line = line.replace('<b>', '').replace('</b>', '')
            if line:
                text_lines.append(line)
        
        return ' '.join(text_lines)
    except Exception:
        return None

