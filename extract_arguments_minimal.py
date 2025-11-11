"""
Script minimal pour extraire les arguments d'une vidéo YouTube.

Ce script exécute uniquement la première étape du workflow:
1. Extraction de la transcription YouTube
2. Extraction des arguments avec l'agent OpenAI

Usage:
    python extract_arguments_minimal.py <youtube_url>

Exemple:
    python extract_arguments_minimal.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

Prérequis:
    - Variable d'environnement OPENAI_API_KEY doit être définie
    - Dépendances: yt-dlp, openai, pydantic-settings
"""
import sys
import os
import json
from typing import Optional

# Configuration de l'encodage UTF-8 pour Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ajout du chemin du projet pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Chargement du fichier .env si présent
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"[INFO] Fichier .env chargé depuis: {env_path}")
except ImportError:
    # python-dotenv n'est pas installé, on continue sans
    pass

# Configuration simplifiée pour le mode minimal (sans DB/Redis)
# On définit des valeurs par défaut pour database_url et redis_url
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://dummy:dummy@localhost:5432/dummy")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Import des modules du projet
from app.utils.youtube import extract_video_id
from app.utils.transcript import extract_transcript
# TEMPORAIRE : Import commenté
# from app.agents.arguments import extract_arguments


def main():
    """Point d'entrée principal du script."""
    # Vérification de l'argument
    if len(sys.argv) < 2:
        print("❌ Usage: python extract_arguments_minimal.py <youtube_url>")
        print("\nExemple:")
        print('  python extract_arguments_minimal.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"')
        sys.exit(1)
    
    youtube_url = sys.argv[1]
    
    # TEMPORAIRE : Vérification de la clé API OpenAI commentée
    # openai_key = os.getenv("OPENAI_API_KEY")
    # if not openai_key:
    #     print("❌ Erreur: La variable d'environnement OPENAI_API_KEY n'est pas définie")
    #     print("\nOptions pour définir la clé API:")
    #     print("  1. Créer un fichier .env à la racine avec: OPENAI_API_KEY=votre_cle_ici")
    #     print("  2. Variable d'environnement:")
    #     print("     Windows (PowerShell): $env:OPENAI_API_KEY='votre_cle_ici'")
    #     print("     Windows (CMD): set OPENAI_API_KEY=votre_cle_ici")
    #     print("     Linux/Mac: export OPENAI_API_KEY='votre_cle_ici'")
    #     sys.exit(1)
    # 
    # print(f"[INFO] Clé API OpenAI trouvée (longueur: {len(openai_key)} caractères)")
    
    print("="*80)
    print("🎬 EXTRACTION DE TRANSCRIPTION D'UNE VIDÉO YOUTUBE")
    print("="*80)
    print(f"\n📺 URL: {youtube_url}\n")
    
    # Étape 1: Extraction de l'ID de la vidéo
    print("🔍 Étape 1: Extraction de l'ID de la vidéo...")
    video_id = extract_video_id(youtube_url)
    
    if not video_id:
        print("❌ Erreur: Impossible d'extraire l'ID de la vidéo depuis l'URL")
        print("   Vérifiez que l'URL est valide (format: https://www.youtube.com/watch?v=...)")
        sys.exit(1)
    
    print(f"✅ ID de la vidéo: {video_id}\n")
    
    # Étape 2: Extraction de la transcription
    print("📝 Étape 2: Extraction de la transcription...")
    try:
        transcript_text = extract_transcript(youtube_url)
        
        if not transcript_text or len(transcript_text.strip()) < 50:
            print("❌ Erreur: Transcription introuvable ou trop courte")
            print("   La vidéo doit avoir des sous-titres activés (automatiques ou manuels)")
            sys.exit(1)
        
        print(f"✅ Transcription extraite ({len(transcript_text)} caractères)\n")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction de la transcription: {e}")
        sys.exit(1)
    
    # TEMPORAIRE : Étape 3 commentée (extraction des arguments avec OpenAI)
    # print("🤖 Étape 3: Extraction des arguments avec OpenAI...")
    # try:
    #     arguments = extract_arguments(transcript_text, video_id=video_id)
    #     
    #     if not arguments:
    #         print("⚠️  Aucun argument extrait de la transcription")
    #         sys.exit(0)
    #     
    #     print(f"✅ {len(arguments)} argument(s) extrait(s)\n")
    #     
    # except ValueError as e:
    #     print(f"❌ Erreur de configuration: {e}")
    #     sys.exit(1)
    # except Exception as e:
    #     print(f"❌ Erreur lors de l'extraction des arguments: {e}")
    #     sys.exit(1)
    
    # Affichage de la transcription complète
    print("="*80)
    print("📝 TRANSCRIPTION COMPLÈTE")
    print("="*80)
    print("\n" + transcript_text)
    print("\n" + "="*80)
    
    # Sauvegarde de la transcription dans un fichier texte
    output_file = f"transcript_{video_id}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"URL: {youtube_url}\n")
        f.write(f"Video ID: {video_id}\n")
        f.write(f"Longueur: {len(transcript_text)} caractères\n")
        f.write("="*80 + "\n\n")
        f.write(transcript_text)
    
    print(f"💾 Transcription sauvegardée dans: {output_file}")
    print("="*80)
    
    # TEMPORAIRE : Sauvegarde JSON commentée
    # output_file = f"arguments_{video_id}.json"
    # output_data = {
    #     "video_id": video_id,
    #     "youtube_url": youtube_url,
    #     "arguments_count": len(arguments),
    #     "arguments": arguments
    # }
    # 
    # with open(output_file, 'w', encoding='utf-8') as f:
    #     json.dump(output_data, f, ensure_ascii=False, indent=2)
    # 
    # print(f"💾 Résultats sauvegardés dans: {output_file}")
    # print("="*80)


if __name__ == "__main__":
    main()

