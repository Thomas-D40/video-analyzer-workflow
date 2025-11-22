"""
Utilitaire pour générer un rapport Markdown à partir des résultats d'analyse.
"""
from typing import Dict, List
import datetime

def generate_markdown_report(data: Dict) -> str:
    """
    Génère un rapport Markdown formaté à partir des données JSON.
    
    Args:
        data: Dictionnaire contenant les résultats (video_id, arguments, etc.)
        
    Returns:
        Chaîne contenant le rapport Markdown complet
    """
    video_id = data.get("video_id", "Inconnu")
    youtube_url = data.get("youtube_url", "")
    arguments = data.get("arguments", [])
    
    # En-tête du rapport
    report = [
        f"# Rapport d'Analyse Vidéo : {video_id}",
        f"**Date** : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Source** : [{youtube_url}]({youtube_url})",
        f"**Arguments analysés** : {len(arguments)}",
        "",
        "---",
        ""
    ]
    
    # Traitement de chaque argument
    for i, arg in enumerate(arguments, 1):
        argument_text = arg.get("argument", "")
        stance = arg.get("stance", "Neutre")
        reliability = arg.get("reliability_score", 0.5)
        
        # Vérifier si l'analyse a réellement utilisé des sources
        analysis = arg.get("analysis", {})
        pros = analysis.get("pros", [])
        cons = analysis.get("cons", [])
        has_analysis = bool(pros or cons)
        
        # En-tête de l'argument
        report.append(f"## Argument {i}")
        report.append(f"> \"{argument_text}\"")
        report.append("")
        
        # Affichage de la fiabilité ou avertissement si aucune source utilisée
        if not has_analysis:
            # Aucune source n'a été réellement utilisée dans l'analyse
            report.append(f"**⚠️ Aucune source trouvée** | **Position** : {stance}")
        else:
            # Indicateur visuel de fiabilité
            if reliability >= 0.7:
                rel_emoji = "🟢"
                rel_text = "Élevée"
            elif reliability >= 0.4:
                rel_emoji = "🟡"
                rel_text = "Moyenne"
            else:
                rel_emoji = "🔴"
                rel_text = "Faible"
            
            report.append(f"**Fiabilité** : {rel_emoji} {rel_text} ({reliability:.1f}/1.0) | **Position** : {stance}")
        report.append("")
        
        # Analyse Pros/Cons
        analysis = arg.get("analysis", {})
        pros = analysis.get("pros", [])
        cons = analysis.get("cons", [])
        
        if pros or cons:
            report.append("### Analyse Critique")
            
            if pros:
                report.append("#### ✅ Points qui soutiennent l'argument")
                for pro in pros:
                    claim = pro.get("claim", "")
                    source = pro.get("source", "")
                    if source:
                        report.append(f"- {claim} ([Source]({source}))")
                    else:
                        report.append(f"- {claim}")
                report.append("")
                
            if cons:
                report.append("#### ❌ Points qui nuancent ou contredisent")
                for con in cons:
                    claim = con.get("claim", "")
                    source = con.get("source", "")
                    if source:
                        report.append(f"- {claim} ([Source]({source}))")
                    else:
                        report.append(f"- {claim}")
                report.append("")
        
        # Sources
        sources = arg.get("sources", {})
        scientific = sources.get("scientific", [])
        statistical = sources.get("statistical", [])
        web = sources.get("web", [])
        
        if scientific or statistical or web:
            report.append("### 📚 Sources Identifiées")
            
            if scientific:
                report.append("**Sources Scientifiques (ArXiv)**")
                for source in scientific:
                    title = source.get("title", "Sans titre")
                    url = source.get("url", "#")
                    summary = (source.get("summary") or source.get("snippet") or "")[:150] + "..."
                    report.append(f"- **[{title}]({url})**")
                    report.append(f"  > *{summary}*")
                report.append("")
                
            if statistical:
                report.append("**Données Statistiques (World Bank)**")
                for source in statistical:
                    title = source.get("title", "Sans titre")
                    url = source.get("url", "#")
                    report.append(f"- [{title}]({url})")
                report.append("")
                
            if web:
                report.append("**Sources Web**")
                for source in web:
                    title = source.get("title", "Sans titre")
                    url = source.get("url", "#")
                    report.append(f"- [{title}]({url})")
                report.append("")
        
        report.append("---")
        report.append("")
        
    return "\n".join(report)
