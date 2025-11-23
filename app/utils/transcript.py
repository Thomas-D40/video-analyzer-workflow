"""
Utilitaire pour extraire la transcription d'une vidéo YouTube.

Utilise youtube-transcript-api comme méthode principale (plus fiable),
avec yt-dlp comme fallback.
"""
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import yt_dlp
from typing import Optional
import tempfile
import os
import re
import uuid
import json


def extract_transcript(youtube_url: str, youtube_cookies: str = None) -> Optional[str]:
    """
    Extrait la transcription d'une vidéo YouTube.
    
    Stratégie :
    1. Créer un fichier de cookies temporaire si fourni
    2. Essayer youtube-transcript-api (avec cookies)
    3. Si échec, essayer yt-dlp (avec cookies)
    
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
            
            # DEBUG: Vérifier le contenu du fichier
            file_size = os.path.getsize(cookie_file_path)
            print(f"[DEBUG] Cookie file created: {cookie_file_path} (Size: {file_size} bytes)")
            with open(cookie_file_path, 'r') as f:
                head = [next(f) for _ in range(5)]
            print(f"[DEBUG] Cookie file head:\n{''.join(head)}")
            
        except Exception as e:
            print(f"[WARN] Failed to create cookie file: {e}")
            cookie_file_path = None
            
    try:
        # Extraire l'ID de la vidéo
        video_id = _extract_video_id(youtube_url)
        if not video_id:
            print("[ERROR] Impossible d'extraire l'ID de la vidéo")
            return None

        # Méthode 1: youtube-transcript-api
        try:
            print(f"[INFO] Tentative youtube-transcript-api pour {video_id} (cookies={bool(cookie_file_path)})")
            
            # On passe le chemin du fichier de cookies s'il existe
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['fr', 'en', 'fr-FR', 'en-US', 'en-GB'],
                cookies=cookie_file_path if cookie_file_path else None
            )
            
            # Assembler le texte
            transcript_text = ' '.join([entry['text'] for entry in transcript_list])
            
            if transcript_text and len(transcript_text.strip()) > 100:
                print(f"[INFO] Succès youtube-transcript-api ({len(transcript_text)} chars)")
                return transcript_text.strip()
                
        except Exception as e:
            import traceback
            print(f"[WARN] Echec youtube-transcript-api: {e}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            # On continue vers le fallback yt-dlp
            
        # Méthode 2: yt-dlp (Fallback)
        print(f"[INFO] Tentative fallback yt-dlp pour {youtube_url}")
        return _extract_transcript_ytdlp(youtube_url, cookie_file_path)
        
    finally:
        # Nettoyage du fichier cookies
        if cookie_file_path and os.path.exists(cookie_file_path):
            try:
                os.remove(cookie_file_path)
                print("[DEBUG] Cookie file cleaned up")
            except Exception as e:
                print(f"[WARN] Failed to cleanup cookie file: {e}")


def _extract_video_id(youtube_url: str) -> Optional[str]:
    """Extrait l'ID de la vidéo depuis une URL YouTube."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    
    return None


def _extract_transcript_ytdlp(youtube_url: str, cookie_file: str = None) -> Optional[str]:
    """
    Fallback: extraction via yt-dlp avec stratégie en 2 phases.
    """
    try:
        # Phase 1: Métadonnées SANS cookies (pour éviter erreur format)
        ydl_opts_info = {
            'quiet': False,  # Enable logs
            'verbose': True, # Enable verbose logs
            'no_warnings': False,
            'skip_download': True,
        }
        
        print("[DEBUG] Starting yt-dlp Phase 1 (Metadata)")
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
        # Phase 2: Téléchargement sous-titres AVEC cookies
        subtitles_data = info.get('subtitles', {})
        automatic_captions = info.get('automatic_captions', {})
        
        all_subtitles = [('manual', subtitles_data), ('auto', automatic_captions)]
        
        for _, subs in all_subtitles:
            for lang in ['fr', 'en', 'fr-FR', 'en-US', 'en-GB']:
                if lang in subs:
                    subtitle_info = subs[lang]
                    if isinstance(subtitle_info, list) and subtitle_info:
                        subtitle_info = subtitle_info[0]
                        
                    url = subtitle_info.get('url') if isinstance(subtitle_info, dict) else subtitle_info
                    
                    if url:
                        print(f"[DEBUG] Found subtitle URL for {lang}, downloading...")
                        # Télécharger avec cookies
                        transcript = _download_subtitle_url(url, cookie_file)
                        if transcript:
                            return transcript
                            
        print("[WARN] No suitable subtitles found in metadata")
        return None
        
    except Exception as e:
        print(f"[ERROR] yt-dlp fallback failed: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def _download_subtitle_url(url: str, cookie_file: str = None) -> Optional[str]:
    """Télécharge et parse un sous-titre depuis son URL."""
    try:
        import urllib.request
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        if cookie_file and os.path.exists(cookie_file):
            with open(cookie_file, 'r') as f:
                # Conversion basique Netscape -> Header Cookie
                cookies = []
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split('\t')
                        if len(parts) >= 7:
                            cookies.append(f"{parts[5]}={parts[6]}")
                if cookies:
                    req.add_header('Cookie', '; '.join(cookies))
        
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
        return _parse_subtitle_content(content)
    except Exception:
        return None


def _parse_subtitle_content(content: str) -> Optional[str]:
    """Parse le contenu (JSON, XML, VTT, SRT)."""
    try:
        content = content.strip()
        
        # JSON (YouTube format)
        if content.startswith(('[', '{')):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    events = data.get('events', []) or data.get('segments', [])
                    parts = []
                    for e in events:
                        segs = e.get('segs', [])
                        if segs:
                            parts.extend([s.get('utf8', '') for s in segs if 'utf8' in s])
                    return ' '.join(parts).strip()
            except:
                pass

        # XML/TTML
        if content.startswith(('<', '<?xml')):
            text = re.sub(r'<[^>]+>', ' ', content)
            return ' '.join(text.split()).strip()
            
        # VTT / SRT
        lines = content.splitlines()
        text_parts = []
        for line in lines:
            if '-->' in line or not line.strip() or line.strip().isdigit() or 'WEBVTT' in line:
                continue
            text_parts.append(line.strip())
        return ' '.join(text_parts).strip()
        
    except:
        return None
