"""
Utilitaire pour extraire la transcription d'une vidéo YouTube.

Utilise yt-dlp pour télécharger et parser la transcription automatique
ou manuelle de la vidéo.
"""
import yt_dlp
from typing import Optional
import tempfile
import os
import re
import time
import json


def extract_transcript(youtube_url: str) -> Optional[str]:
    """
    Extrait la transcription d'une vidéo YouTube.
    
    Args:
        youtube_url: URL complète de la vidéo YouTube
        
    Returns:
        Transcription sous forme de texte, ou None si indisponible
    """
    # Configuration yt-dlp pour extraire uniquement la transcription
    # On supprime les warnings en redirigeant les logs
    import logging
    logger = logging.getLogger('yt_dlp')
    logger.setLevel(logging.ERROR)
    
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['fr', 'en', 'fr-FR', 'en-US', 'en-GB'],  # Plus de variantes
        'skip_download': True,  # On ne télécharge pas la vidéo
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'retries': 3,  # Nombre de tentatives en cas d'erreur
        'fragment_retries': 3,
        'extractor_args': {'youtube': {'skip': ['dash', 'hls']}},  # Éviter certains formats problématiques
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Récupération des informations de la vidéo
            info = ydl.extract_info(youtube_url, download=False)
            
            # Tentative d'extraction de la transcription
            # yt-dlp stocke les sous-titres dans 'subtitles' ou 'automatic_captions'
            subtitles_data = info.get('subtitles', {}) or info.get('automatic_captions', {})
            
            # Méthode alternative : essayer d'extraire directement depuis les données de la vidéo
            # Certaines vidéos ont les sous-titres directement dans les métadonnées
            if not subtitles_data:
                # Essayer de récupérer depuis request_subtitles si disponible
                try:
                    if 'requested_subtitles' in info:
                        subtitles_data = info.get('requested_subtitles', {})
                except:
                    pass
            
            # NOUVELLE MÉTHODE : Récupérer les sous-titres directement depuis les URLs dans les métadonnées
            # Cela évite de passer par le téléchargement de fichiers et réduit les risques d'erreur 429
            # Essayer d'abord les sous-titres manuels, puis automatiques
            all_subtitles_sources = []
            
            # Ajouter les sous-titres manuels
            manual_subtitles = info.get('subtitles', {})
            if manual_subtitles:
                all_subtitles_sources.append(('manual', manual_subtitles))
            
            # Ajouter les sous-titres automatiques
            auto_subtitles = info.get('automatic_captions', {})
            if auto_subtitles:
                all_subtitles_sources.append(('auto', auto_subtitles))
            
            # Essayer de récupérer les sous-titres directement depuis les URLs
            for source_type, subtitles_data in all_subtitles_sources:
                for lang in ['fr', 'en', 'fr-FR', 'en-US', 'en-GB']:
                    if lang in subtitles_data:
                        subtitle_info = subtitles_data[lang]
                        # subtitle_info peut être une liste de formats ou un dict
                        if isinstance(subtitle_info, list) and len(subtitle_info) > 0:
                            # Prendre le premier format disponible (généralement le meilleur)
                            subtitle_info = subtitle_info[0]
                        
                        # Chercher l'URL du sous-titre
                        subtitle_url = None
                        if isinstance(subtitle_info, dict):
                            subtitle_url = subtitle_info.get('url')
                        elif isinstance(subtitle_info, str):
                            subtitle_url = subtitle_info
                        
                        if subtitle_url:
                            # Télécharger directement depuis l'URL
                            try:
                                import urllib.request
                                import urllib.error
                                
                                req = urllib.request.Request(subtitle_url)
                                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                                
                                with urllib.request.urlopen(req, timeout=10) as response:
                                    subtitle_content = response.read().decode('utf-8', errors='ignore')
                                
                                # Parser le contenu directement
                                transcript_text = _parse_subtitle_content(subtitle_content)
                                if transcript_text and len(transcript_text.strip()) > 100:
                                    return transcript_text
                            except Exception as e:
                                # Si ça échoue, continuer avec les autres méthodes
                                pass
            
            # Si pas de sous-titres trouvés via les URLs, on essaie de les télécharger directement
            # (Cette partie est maintenant un fallback si la méthode directe échoue)
            # On continue avec les méthodes de téléchargement de fichiers
            # Essai avec toutes les langues disponibles (avec gestion d'erreur 429)
            with tempfile.TemporaryDirectory() as tmpdir:
                sub_opts = {
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['fr', 'en'],  # Limiter pour éviter trop de requêtes
                    'skip_download': True,
                    'quiet': True,
                    'no_warnings': True,
                    'retries': 2,
                    'fragment_retries': 2,
                    'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
                }
                with yt_dlp.YoutubeDL(sub_opts) as sub_ydl:
                    try:
                        sub_ydl.download([youtube_url])
                        # Chercher tous les fichiers de sous-titres générés
                        for file in os.listdir(tmpdir):
                            if file.endswith(('.vtt', '.srt', '.ttml')):
                                sub_file = os.path.join(tmpdir, file)
                                transcript_text = _parse_subtitle_file(sub_file)
                                if transcript_text and len(transcript_text.strip()) > 100:
                                    return transcript_text
                    except yt_dlp.utils.DownloadError as e:
                        # Si erreur 429, attendre un peu avant de continuer
                        if '429' in str(e) or 'Too Many Requests' in str(e):
                            time.sleep(2)  # Attendre 2 secondes
                        # Continuer avec les autres méthodes
                        pass
                    except Exception:
                        pass
            
            # Recherche de la meilleure langue disponible dans les métadonnées
            transcript_text = None
            # Essayer d'abord les sous-titres manuels, puis automatiques
            for lang in ['fr', 'en', 'fr-FR', 'en-US', 'en-GB']:
                if lang in subtitles_data:
                    # Télécharger les sous-titres dans un fichier temporaire
                    with tempfile.TemporaryDirectory() as tmpdir:
                        sub_opts = {
                            'writesubtitles': True,
                            'writeautomaticsub': False,
                            'subtitleslangs': [lang],
                            'skip_download': True,
                            'quiet': True,
                            'no_warnings': True,
                            'retries': 2,
                            'fragment_retries': 2,
                            'outtmpl': os.path.join(tmpdir, 'subtitle.%(ext)s'),
                        }
                        with yt_dlp.YoutubeDL(sub_opts) as sub_ydl:
                            try:
                                sub_ydl.download([youtube_url])
                                # Chercher le fichier de sous-titres généré
                                for ext in ['vtt', 'srt', 'ttml']:
                                    sub_file = os.path.join(tmpdir, f'subtitle.{ext}')
                                    if os.path.exists(sub_file):
                                        transcript_text = _parse_subtitle_file(sub_file)
                                        if transcript_text and len(transcript_text.strip()) > 100:
                                            return transcript_text
                            except yt_dlp.utils.DownloadError as e:
                                # Si erreur 429, attendre un peu avant de continuer
                                if '429' in str(e) or 'Too Many Requests' in str(e):
                                    time.sleep(2)  # Attendre 2 secondes
                                continue
                            except Exception:
                                continue
                    # Ajouter un petit délai entre les tentatives pour éviter 429
                    time.sleep(0.5)
            
            # Essayer aussi les sous-titres automatiques si pas de sous-titres manuels
            auto_captions = info.get('automatic_captions', {})
            for lang in ['fr', 'en', 'fr-FR', 'en-US', 'en-GB']:
                if lang in auto_captions:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        sub_opts = {
                            'writesubtitles': False,
                            'writeautomaticsub': True,
                            'subtitleslangs': [lang],
                            'skip_download': True,
                            'quiet': True,
                            'no_warnings': True,
                            'retries': 2,
                            'fragment_retries': 2,
                            'outtmpl': os.path.join(tmpdir, 'subtitle.%(ext)s'),
                        }
                        with yt_dlp.YoutubeDL(sub_opts) as sub_ydl:
                            try:
                                sub_ydl.download([youtube_url])
                                for ext in ['vtt', 'srt', 'ttml']:
                                    sub_file = os.path.join(tmpdir, f'subtitle.{ext}')
                                    if os.path.exists(sub_file):
                                        transcript_text = _parse_subtitle_file(sub_file)
                                        if transcript_text and len(transcript_text.strip()) > 100:
                                            return transcript_text
                            except yt_dlp.utils.DownloadError as e:
                                # Si erreur 429, attendre un peu avant de continuer
                                if '429' in str(e) or 'Too Many Requests' in str(e):
                                    time.sleep(2)  # Attendre 2 secondes
                                continue
                            except Exception:
                                continue
                    # Ajouter un petit délai entre les tentatives pour éviter 429
                    time.sleep(0.5)
            
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


def _parse_subtitle_content(content: str) -> Optional[str]:
    """
    Parse le contenu d'un fichier de sous-titres directement depuis une chaîne.
    Supporte VTT, SRT, TTML/XML, et JSON (format YouTube avec utf8/tOffsetMs).
    
    Args:
        content: Contenu du fichier de sous-titres (VTT, SRT, TTML, JSON, etc.)
        
    Returns:
        Texte extrait des sous-titres
    """
    try:
        # Détecter le format JSON (YouTube retourne parfois du JSON avec utf8, tOffsetMs, etc.)
        content_stripped = content.strip()
        if content_stripped.startswith('[') or content_stripped.startswith('{'):
            try:
                # Essayer de parser comme JSON
                json_data = json.loads(content)
                
                # Si c'est une liste d'objets avec "utf8"
                if isinstance(json_data, list):
                    text_parts = []
                    for item in json_data:
                        if isinstance(item, dict):
                            # Extraire le texte depuis "utf8" ou "text" ou similaire
                            # YouTube utilise souvent "utf8" pour le texte des sous-titres
                            text = item.get('utf8') or item.get('text') or item.get('content') or item.get('t') or ''
                            if text:
                                # Nettoyer le texte (enlever les espaces en début/fin)
                                text_clean = str(text).strip()
                                if text_clean:
                                    text_parts.append(text_clean)
                        elif isinstance(item, str):
                            text_clean = item.strip()
                            if text_clean:
                                text_parts.append(text_clean)
                    
                    # Joindre tous les textes en une seule chaîne
                    result = ' '.join(text_parts)
                    # Nettoyer les espaces multiples mais garder les espaces simples entre mots
                    result = re.sub(r'\s+', ' ', result).strip()
                    return result if result else None
                
                # Si c'est un objet avec une liste d'événements
                elif isinstance(json_data, dict):
                    # Chercher des clés communes pour les sous-titres JSON
                    events = json_data.get('events') or json_data.get('segments') or json_data.get('subtitles') or []
                    if events:
                        text_parts = []
                        for event in events:
                            if isinstance(event, dict):
                                text = event.get('utf8') or event.get('text') or event.get('content') or event.get('segs')
                                if isinstance(text, list):
                                    # Si text est une liste, extraire les utf8 de chaque élément
                                    for seg in text:
                                        if isinstance(seg, dict):
                                            seg_text = seg.get('utf8') or seg.get('text') or ''
                                            if seg_text:
                                                text_parts.append(seg_text.strip())
                                        elif isinstance(seg, str):
                                            text_parts.append(seg.strip())
                                elif text:
                                    text_parts.append(str(text).strip())
                            elif isinstance(event, str):
                                text_parts.append(event.strip())
                        
                        result = ' '.join(text_parts)
                        result = ' '.join(result.split())
                        return result if result else None
                    
                    # Si l'objet contient directement du texte
                    text = json_data.get('utf8') or json_data.get('text') or json_data.get('content')
                    if text:
                        return str(text).strip()
                        
            except (json.JSONDecodeError, ValueError):
                # Ce n'est pas du JSON valide, continuer avec les autres formats
                pass
        
        # Détecter le format (TTML/XML commence par <?xml ou <tt)
        if content_stripped.startswith('<?xml') or content_stripped.startswith('<tt'):
            # Format TTML/XML - parser avec regex pour extraire le texte
            # Les sous-titres TTML sont généralement dans des balises <p> ou <span>
            text_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
            if not text_matches:
                text_matches = re.findall(r'<span[^>]*>(.*?)</span>', content, re.DOTALL | re.IGNORECASE)
            if not text_matches:
                # Dernier recours : extraire tout le texte entre balises
                text_matches = re.findall(r'>([^<]+)<', content)
            
            # Nettoyer chaque match
            text_lines = []
            for match in text_matches:
                text = re.sub(r'<[^>]+>', '', match)  # Enlever les balises restantes
                text = text.strip()
                if text:
                    text_lines.append(text)
            
            result = ' '.join(text_lines)
            result = ' '.join(result.split())  # Nettoyer les espaces multiples
            return result if result else None
        
        # Format VTT ou SRT - parsing ligne par ligne
        lines = content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # Ignorer les lignes vides, les timestamps, et les numéros de séquence
            if not line or '-->' in line or line.isdigit():
                continue
            # Ignorer les en-têtes VTT (WEBVTT, etc.)
            if line.upper().startswith('WEBVTT') or line.upper().startswith('NOTE'):
                continue
            # Ignorer les lignes de style VTT
            if line.startswith('STYLE') or line.startswith('::cue'):
                continue
            # Enlever les balises HTML/VTT (plus complet)
            # Supprimer les balises HTML/VTT
            line = re.sub(r'<[^>]+>', '', line)
            # Supprimer les balises de positionnement VTT
            line = re.sub(r'[0-9]+:[0-9]+:[0-9]+[.,][0-9]+', '', line)
            # Supprimer les identifiants de cue VTT (ex: 00:00:00.000 --> 00:00:05.000)
            line = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}', '', line)
            line = line.strip()
            if line:
                text_lines.append(line)
        
        result = ' '.join(text_lines)
        # Nettoyer les espaces multiples
        result = ' '.join(result.split())
        return result if result else None
    except Exception as e:
        print(f"Erreur lors du parsing du contenu de sous-titres: {e}")
        return None


def _parse_subtitle_file(file_path: str) -> Optional[str]:
    """
    Parse un fichier de sous-titres (.vtt, .srt ou .ttml) et extrait le texte.
    
    Args:
        file_path: Chemin vers le fichier de sous-titres
        
    Returns:
        Texte extrait des sous-titres
    """
    try:
        # Essayer plusieurs encodages
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        content = None
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if not content:
            return None
        
        # Parsing simple: on enlève les timestamps et les balises
        lines = content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # Ignorer les lignes vides, les timestamps, et les numéros de séquence
            if not line or '-->' in line or line.isdigit():
                continue
            # Ignorer les en-têtes VTT (WEBVTT, etc.)
            if line.upper().startswith('WEBVTT') or line.upper().startswith('NOTE'):
                continue
            # Enlever les balises HTML/VTT (plus complet)
            # Supprimer les balises HTML/VTT
            line = re.sub(r'<[^>]+>', '', line)
            # Supprimer les balises de positionnement VTT
            line = re.sub(r'[0-9]+:[0-9]+:[0-9]+[.,][0-9]+', '', line)
            line = line.strip()
            if line:
                text_lines.append(line)
        
        result = ' '.join(text_lines)
        # Nettoyer les espaces multiples
        result = ' '.join(result.split())
        return result if result else None
    except Exception as e:
        print(f"Erreur lors du parsing du fichier de sous-titres: {e}")
        return None

