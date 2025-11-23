"""
Utilitaire pour extraire la transcription d'une vidéo YouTube.

Utilise yt-dlp avec une stratégie en 2 phases pour gérer les cookies :
- Phase 1 : Extraction des métadonnées SANS cookies
- Phase 2 : Téléchargement des sous-titres AVEC cookies
"""
import yt_dlp
from typing import Optional
import tempfile
import os
import re
import uuid


def extract_transcript(youtube_url: str, youtube_cookies: str = None) -> Optional[str]:
    """
    Extrait la transcription d'une vidéo YouTube.
    
    Stratégie en 2 phases pour éviter l'erreur "Requested format is not available" :
    1. Récupérer les métadonnées et URLs de sous-titres SANS cookies
    2. Télécharger les sous-titres AVEC cookies si fournis
    
    Args:
        youtube_url: URL complète de la vidéo YouTube
        youtube_cookies: Cookies YouTube au format Netscape (optionnel)
        
    Returns:
        Transcription sous forme de texte, ou None si indisponible
    """
    # Créer un fichier temp pour les cookies si fournis
    cookie_file_path = None
    if youtube_cookies:
        cookie_file_path = f'/tmp/cookies_{uuid.uuid4().hex}.txt'
        try:
            with open(cookie_file_path, 'w') as f:
                f.write(youtube_cookies)
            print(f"[DEBUG] Cookie file created: {cookie_file_path}")
        except Exception as e:
            print(f"[WARN] Failed to create cookie file: {e}")
            cookie_file_path = None
    
    try:
        # PHASE 1: Extraction des métadonnées SANS cookies
        # Cela évite l'erreur "Requested format is not available"
        print("[INFO] Phase 1: Extracting metadata without cookies")
        
        metadata_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,  # On veut les métadonnées complètes
        }
        
        with yt_dlp.YoutubeDL(metadata_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
        
        # Récupérer les URLs des sous-titres depuis les métadonnées
        subtitles_data = info.get('subtitles', {})
        automatic_captions = info.get('automatic_captions', {})
        
        # PHASE 2: Téléchargement des sous-titres AVEC cookies si disponibles
        print(f"[INFO] Phase 2: Downloading subtitles WITH cookies={bool(cookie_file_path)}")
        
        # Prioriser les sous-titres manuels
        all_subtitles = [
            ('manual', subtitles_data),
            ('auto', automatic_captions)
        ]
        
        for subtitle_type, subs in all_subtitles:
            for lang in ['fr', 'en', 'fr-FR', 'en-US', 'en-GB']:
                if lang in subs:
                    # Récupérer l'URL du sous-titre
                    subtitle_info = subs[lang]
                    if isinstance(subtitle_info, list) and len(subtitle_info) > 0:
                        subtitle_info = subtitle_info[0]
                    
                    subtitle_url = None
                    if isinstance(subtitle_info, dict):
                        subtitle_url = subtitle_info.get('url')
                    elif isinstance(subtitle_info, str):
                        subtitle_url = subtitle_info
                    
                    if subtitle_url:
                        # Télécharger le sous-titre avec cookies si disponibles
                        transcript = _download_subtitle_with_cookies(
                            subtitle_url, 
                            cookie_file_path
                        )
                        
                        if transcript and len(transcript.strip()) > 100:
                            print(f"[INFO] Successfully extracted {subtitle_type} subtitle in {lang}")
                            return transcript.strip()
        
        # Si aucun sous-titre trouvé via URLs, essayer la méthode de téléchargement direct
        print("[INFO] Trying direct subtitle download with yt-dlp")
        return _download_subtitles_direct(youtube_url, cookie_file_path)
        
    except Exception as e:
        print(f"Erreur lors de l'extraction de la transcription: {e}")
        return None
    finally:
        # Nettoyer le fichier de cookies
        if cookie_file_path and os.path.exists(cookie_file_path):
            try:
                os.remove(cookie_file_path)
                print(f"[DEBUG] Cookie file cleaned up")
            except Exception as e:
                print(f"[WARN] Failed to cleanup cookie file: {e}")


def _download_subtitle_with_cookies(subtitle_url: str, cookie_file: str = None) -> Optional[str]:
    """
    Télécharge un sous-titre depuis une URL avec cookies si fournis.
    """
    try:
        import urllib.request
        
        req = urllib.request.Request(subtitle_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Si on a des cookies, les ajouter au header
        if cookie_file and os.path.exists(cookie_file):
            # Lire les cookies et les convertir en header Cookie
            with open(cookie_file, 'r') as f:
                cookie_lines = f.readlines()
            
            # Parser les cookies Netscape et créer le header Cookie
            cookies = []
            for line in cookie_lines:
                if line.strip() and not line.startswith('#'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        name = parts[5]
                        value = parts[6]
                        cookies.append(f"{name}={value}")
            
            if cookies:
                req.add_header('Cookie', '; '.join(cookies))
                print(f"[DEBUG] Added {len(cookies)} cookies to request")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
        
        return _parse_subtitle_content(content)
        
    except Exception as e:
        print(f"[WARN] Failed to download subtitle: {e}")
        return None


def _download_subtitles_direct(youtube_url: str, cookie_file: str = None) -> Optional[str]:
    """
    Télécharge les sous-titres directement avec yt-dlp.
    Utilise les cookies si fournis.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        download_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['fr', 'en'],
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
        }
        
        # Ajouter le cookiefile seulement pour le téléchargement
        if cookie_file and os.path.exists(cookie_file):
            download_opts['cookiefile'] = cookie_file
            print("[DEBUG] Using cookies for subtitle download")
        
        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([youtube_url])
            
            # Chercher les fichiers de sous-titres
            for file in os.listdir(tmpdir):
                if file.endswith(('.vtt', '.srt', '.ttml')):
                    filepath = os.path.join(tmpdir, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    transcript = _parse_subtitle_content(content)
                    if transcript and len(transcript.strip()) > 100:
                        return transcript.strip()
        
        except Exception as e:
            print(f"[WARN] Direct download failed: {e}")
        
        return None


def _parse_subtitle_content(content: str) -> Optional[str]:
    """Parse le contenu d'un fichier de sous-titres."""
    try:
        content_stripped = content.strip()
        
        # Format VTT
        if 'WEBVTT' in content_stripped[:100]:
            lines = content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                # Ignorer les lignes de timing et les lignes vides
                if not line or 'WEBVTT' in line or '-->' in line:
                    continue
                if not re.match(r'^\d{2}:\d{2}', line) and not line.isdigit():
                    # Nettoyer les balises HTML
                    line = re.sub(r'<[^>]+>', '', line)
                    if line:
                        text_lines.append(line)
            
            result = ' '.join(text_lines)
            result = re.sub(r'\s+', ' ', result).strip()
            return result if result else None
        
        # Format SRT
        if re.search(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', content):
            lines = content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                # Ignorer les numéros de séquence et les timestamps
                if not line or line.isdigit() or '-->' in line:
                    continue
                text_lines.append(line)
            
            result = ' '.join(text_lines)
            result = re.sub(r'\s+', ' ', result).strip()
            return result if result else None
        
        # Format TTML/XML
        if content_stripped.startswith('<?xml') or content_stripped.startswith('<tt'):
            text_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
            if not text_matches:
                text_matches = re.findall(r'<span[^>]*>(.*?)</span>', content, re.DOTALL | re.IGNORECASE)
            
            if text_matches:
                text_parts = []
                for match in text_matches:
                    clean_text = re.sub(r'<[^>]+>', '', match)
                    clean_text = clean_text.strip()
                    if clean_text:
                        text_parts.append(clean_text)
                
                result = ' '.join(text_parts)
                result = re.sub(r'\s+', ' ', result).strip()
                return result if result else None
        
        return None
        
    except Exception as e:
        print(f"[WARN] Failed to parse subtitle: {e}")
        return None
