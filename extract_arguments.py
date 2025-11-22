"""
Script pour extraire et analyser les arguments d'une vidéo YouTube.

Ce script exécute le workflow complet:
1. Extraction de la transcription YouTube
2. Extraction des arguments avec OpenAI
3. Recherche de sources (Web, ArXiv, World Bank)
4. Analyse Pros/Cons
5. Calcul de fiabilité
6. Génération de rapports (JSON + Markdown)

Usage:
    python extract_arguments.py <youtube_url>

Exemple:
    python extract_arguments.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

Prérequis:
    - Variable d'environnement OPENAI_API_KEY doit être définie
    - Dépendances: voir requirements.txt
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
from app.agents.arguments import extract_arguments
from app.agents.research import search_literature
from app.agents.query_generator import generate_search_queries
from app.agents.scientific_research import search_arxiv
from app.agents.statistical_research import search_world_bank_data
from app.agents.pros_cons import extract_pros_cons
from app.agents.aggregate import aggregate_results
from app.utils.report_formatter import generate_markdown_report


def main():
    """Point d'entrée principal du script."""
    # Vérification de l'argument
    if len(sys.argv) < 2:
        print("❌ Usage: python extract_arguments.py <youtube_url>")
        print("\nExemple:")
        print('  python extract_arguments.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"')
        sys.exit(1)
    
    youtube_url = sys.argv[1]
    
    # Vérification de la clé API OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ Erreur: La variable d'environnement OPENAI_API_KEY n'est pas définie")
        print("\nOptions pour définir la clé API:")
        print("  1. Créer un fichier .env à la racine avec: OPENAI_API_KEY=votre_cle_ici")
        print("  2. Variable d'environnement:")
        print("     Windows (PowerShell): $env:OPENAI_API_KEY='votre_cle_ici'")
        print("     Windows (CMD): set OPENAI_API_KEY=votre_cle_ici")
        print("     Linux/Mac: export OPENAI_API_KEY='votre_cle_ici'")
        sys.exit(1)
    
    print(f"[INFO] Clé API OpenAI trouvée (longueur: {len(openai_key)} caractères)")
    
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
    
    # Étape 3: Extraction des arguments avec OpenAI
    print("🤖 Étape 3: Extraction des arguments avec OpenAI...")
    try:
        arguments = extract_arguments(transcript_text, video_id=video_id)
        
        if not arguments:
            print("⚠️  Aucun argument extrait de la transcription")
            sys.exit(0)
        
        print(f"✅ {len(arguments)} argument(s) extrait(s)\n")
        
        # Étape 4 & 5: Recherche et Analyse pour chaque argument
        print("🔎 Étape 4 & 5: Recherche et Analyse par argument...")
        
        enriched_arguments = []
        
        for i, arg_data in enumerate(arguments, 1):
            argument_text = arg_data["argument"]
            print(f"\n  👉 Traitement de l'argument {i}/{len(arguments)}: {argument_text[:50]}...")
            
            # Étape 4: Recherche bibliographique (Web + Science + Stats)
            print("     📚 Recherche de sources...")
            
            # 4.0 Génération de requêtes optimisées (Traduction)
            queries = {"arxiv": "", "world_bank": "", "web_query": ""}
            try:
                queries = generate_search_queries(argument_text)
            except Exception as e:
                print(f"     ⚠️ Erreur génération requêtes: {e}")

            # 4.1 Recherche Web (DuckDuckGo) - Avec requête optimisée et filtrage
            try:
                from app.utils.relevance_filter import filter_relevant_results
                
                web_query = queries.get("web_query") or argument_text
                # Récupération de 5 résultats pour filtrage
                raw_web_articles = search_literature(web_query, max_results=5)
                # Filtrage par pertinence : garde les 2 meilleurs
                web_articles = filter_relevant_results(
                    argument_text,
                    raw_web_articles,
                    min_score=0.2,
                    max_results=2
                )
                print(f"     🌍 Web: {len(web_articles)} article(s) pertinent(s)")
            except Exception as e:
                print(f"     ❌ Erreur Web: {e}")
                web_articles = []
                
            # 4.2 Recherche Scientifique (ArXiv) - Avec requête générée
            try:
                arxiv_query = queries.get("arxiv", "")
                if arxiv_query:
                    science_articles = search_arxiv(arxiv_query, max_results=3)
                    print(f"     🔬 Science: {len(science_articles)} article(s)")
                else:
                    science_articles = []
            except Exception as e:
                print(f"     ❌ Erreur Science: {e}")
                science_articles = []
                
            # 4.3 Recherche Statistique (World Bank) - Avec requête générée
            try:
                wb_query = queries.get("world_bank", "")
                if wb_query:
                    stats_data = search_world_bank_data(wb_query)
                    print(f"     📊 Stats: {len(stats_data)} indicateur(s)")
                else:
                    stats_data = []
            except Exception as e:
                print(f"     ❌ Erreur Stats: {e}")
                stats_data = []
                
            # Fusion des sources pour l'analyse
            all_sources = web_articles + science_articles
            
            # Étape 5: Analyse Pros/Cons
            print("     ⚖️  Analyse des pour et contre...")
            try:
                # On passe aussi les stats à l'analyse si possible, sinon on les garde juste en enrichissement
                analysis = extract_pros_cons(argument_text, all_sources)
                pros_count = len(analysis.get("pros", []))
                cons_count = len(analysis.get("cons", []))
                print(f"     ✅ Analyse terminée: {pros_count} pour, {cons_count} contre")
            except Exception as e:
                print(f"     ❌ Erreur analyse: {e}")
                analysis = {"pros": [], "cons": []}
            
            # Construction de l'objet enrichi
            enriched_arg = arg_data.copy()
            enriched_arg["sources"] = {
                "web": web_articles,
                "scientific": science_articles,
                "statistical": stats_data
            }
            enriched_arg["analysis"] = analysis
            enriched_arguments.append(enriched_arg)
            
        # Étape 6: Agrégation et Calcul de Fiabilité (Agent 5)
        print("\n🏆 Étape 6: Calcul des scores de fiabilité...")
        try:
            # Préparation des données pour l'agrégateur
            items_for_aggregation = []
            for arg in enriched_arguments:
                items_for_aggregation.append({
                    "argument": arg["argument"],
                    "pros": arg["analysis"].get("pros", []),
                    "cons": arg["analysis"].get("cons", []),
                    "stance": arg.get("stance", "affirmatif")
                })
            
            # Appel à l'agent d'agrégation
            aggregation_result = aggregate_results(items_for_aggregation, video_id=video_id)
            
            # Fusion des scores de fiabilité
            final_arguments = []
            aggregated_args_map = {a["argument"]: a for a in aggregation_result.get("arguments", [])}
            
            for original_arg in enriched_arguments:
                arg_text = original_arg["argument"]
                # On récupère le score calculé, ou 0.5 par défaut
                agg_data = aggregated_args_map.get(arg_text, {})
                reliability = agg_data.get("reliability", 0.5)
                
                original_arg["reliability_score"] = reliability
                final_arguments.append(original_arg)
                
            arguments = final_arguments
            print(f"✅ Scores calculés pour {len(arguments)} arguments")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'agrégation: {e}")
            # En cas d'erreur, on garde les arguments tels quels sans score (ou score par défaut)
            arguments = enriched_arguments

        print(f"\n✅ Traitement complet terminé pour {len(arguments)} arguments\n")
        
    except ValueError as e:
        print(f"❌ Erreur de configuration: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction des arguments: {e}")
        sys.exit(1)
    
    # Affichage de la transcription complète
    print("="*80)
    print("📝 TRANSCRIPTION COMPLÈTE")
    print("="*80)
    print("\n" + transcript_text)
    print("\n" + "="*80)
    
    # Création du dossier de sortie
    output_dir = os.path.join("output", video_id)
    os.makedirs(output_dir, exist_ok=True)
    print(f"📂 Dossier de sortie: {output_dir}")

    # Sauvegarde de la transcription dans un fichier texte
    output_file_txt = os.path.join(output_dir, f"transcript_{video_id}.txt")
    with open(output_file_txt, 'w', encoding='utf-8') as f:
        f.write(f"URL: {youtube_url}\n")
        f.write(f"Video ID: {video_id}\n")
        f.write(f"Longueur: {len(transcript_text)} caractères\n")
        f.write("="*80 + "\n\n")
        f.write(transcript_text)
    
    print(f"💾 Transcription sauvegardée dans: {output_file_txt}")
    print("="*80)
    # Sauvegarde JSON
    output_data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "arguments_count": len(arguments),
        "arguments": arguments
    }
    
    json_output_path = os.path.join(output_dir, f"arguments_{video_id}.json")
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"💾 Résultats sauvegardés dans: {json_output_path}")
    
    # Génération et sauvegarde du rapport Markdown
    print("📝 Génération du rapport Markdown...")
    markdown_report = generate_markdown_report(output_data)
    md_output_path = os.path.join(output_dir, f"report_{video_id}.md")
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)
        
    print(f"📄 Rapport Markdown sauvegardé dans: {md_output_path}")
    print("="*80)


if __name__ == "__main__":
    main()
