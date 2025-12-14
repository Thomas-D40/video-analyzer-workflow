"""
Utilitaire pour générer un rapport Markdown à partir des résultats d'analyse.

Supports bilingual output (French/English) based on source video language.
"""
from typing import Dict, List
import datetime
import json
from openai import OpenAI
from ..config import get_settings


def _get_access_icon(access_type: str) -> str:
    """
    Get the appropriate icon for the access type.

    Args:
        access_type: Type of access (open_access, abstract_only, full_data, metadata_only)

    Returns:
        Icon emoji representing the access type
    """
    access_icons = {
        "open_access": "🔓",
        "abstract_only": "📄",
        "full_data": "📊",
        "metadata_only": "📋",
        "paywall": "🔒"
    }
    return access_icons.get(access_type, "❓")


def _translate_to_french(text: str) -> str:
    """
    Translate English text to French using OpenAI.

    Args:
        text: English text to translate

    Returns:
        French translation
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return text

    client = OpenAI(api_key=settings.openai_api_key)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,  # gpt-4o-mini for fast translation
            messages=[
                {"role": "system", "content": "You are a translator. Translate the following text from English to French. Preserve markdown formatting and links. Return only the translated text."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR report_formatter] Translation error: {e}")
        return text


def generate_markdown_report(data: Dict) -> str:
    """
    Génère un rapport Markdown formaté à partir des données JSON.

    Supports bilingual output based on video language.
    Now supports tree structure with thesis → sub-arguments → evidence.

    Args:
        data: Dictionnaire contenant les résultats (video_id, arguments, language, argument_structure, etc.)

    Returns:
        Chaîne contenant le rapport Markdown complet
    """
    video_id = data.get("video_id", "Inconnu" if data.get("language") == "fr" else "Unknown")
    youtube_url = data.get("youtube_url", "")
    arguments = data.get("arguments", [])  # Enriched thesis arguments for backward compatibility
    argument_structure = data.get("argument_structure", {})  # Tree structure
    language = data.get("language", "en")  # Default to English

    # Language-specific strings
    if language == "fr":
        strings = {
            "title": f"# Rapport d'Analyse Vidéo : {video_id}",
            "date": "**Date**",
            "source": "**Source**",
            "arguments_analyzed": "**Arguments analysés**",
            "argument": "Argument",
            "position": "Position",
            "reliability": "Fiabilité",
            "high": "Élevée",
            "medium": "Moyenne",
            "low": "Faible",
            "no_sources": "⚠️ Aucune source trouvée",
            "critical_analysis": "Analyse Critique",
            "supporting_points": "✅ Points qui soutiennent l'argument",
            "contradicting_points": "❌ Points qui nuancent ou contredisent",
            "source_label": "Source",
            "sources_identified": "📚 Sources Identifiées",
            "scientific_sources": "Sources Scientifiques",
            "medical_sources": "Sources Médicales",
            "statistical_data": "Données Statistiques",
            "access_legend": "**Légende d'accès** : 🔓 Accès libre | 📄 Résumé uniquement | 📊 Données complètes | 📋 Métadonnées uniquement",
            "reasoning_structure": "### 🌳 Structure de l'Argumentation",
            "sub_arguments": "**Arguments Supports**",
            "counter_arguments": "**Contre-Arguments**",
            "evidence": "**Preuves/Exemples**"
        }
    else:  # English
        strings = {
            "title": f"# Video Analysis Report: {video_id}",
            "date": "**Date**",
            "source": "**Source**",
            "arguments_analyzed": "**Arguments Analyzed**",
            "argument": "Argument",
            "position": "Position",
            "reliability": "Reliability",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "no_sources": "⚠️ No sources found",
            "critical_analysis": "Critical Analysis",
            "supporting_points": "✅ Supporting Points",
            "contradicting_points": "❌ Contradicting or Nuancing Points",
            "source_label": "Source",
            "sources_identified": "📚 Identified Sources",
            "scientific_sources": "Scientific Sources",
            "medical_sources": "Medical Sources",
            "statistical_data": "Statistical Data",
            "access_legend": "**Access Legend**: 🔓 Open Access | 📄 Abstract Only | 📊 Full Data | 📋 Metadata Only",
            "reasoning_structure": "### 🌳 Reasoning Structure",
            "sub_arguments": "**Supporting Sub-Arguments**",
            "counter_arguments": "**Counter-Arguments**",
            "evidence": "**Evidence/Examples**"
        }
    
    # En-tête du rapport
    report = [
        strings["title"],
        f"{strings['date']} : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"{strings['source']} : [{youtube_url}]({youtube_url})",
        f"{strings['arguments_analyzed']} : {len(arguments)}",
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
        report.append(f"## {strings['argument']} {i}")
        report.append(f"> \"{argument_text}\"")
        report.append("")

        # Affichage de la fiabilité ou avertissement si aucune source utilisée
        if not has_analysis:
            # Aucune source n'a été réellement utilisée dans l'analyse
            report.append(f"**{strings['no_sources']}** | **{strings['position']}** : {stance}")
        else:
            # Indicateur visuel de fiabilité
            if reliability >= 0.7:
                rel_emoji = "🟢"
                rel_text = strings["high"]
            elif reliability >= 0.4:
                rel_emoji = "🟡"
                rel_text = strings["medium"]
            else:
                rel_emoji = "🔴"
                rel_text = strings["low"]

            report.append(f"**{strings['reliability']}** : {rel_emoji} {rel_text} ({reliability:.1f}/1.0) | **{strings['position']}** : {stance}")
        report.append("")
        
        # Analyse Pros/Cons
        analysis = arg.get("analysis", {})
        pros = analysis.get("pros", [])
        cons = analysis.get("cons", [])
        
        if pros or cons:
            report.append(f"### {strings['critical_analysis']}")

            if pros:
                report.append(f"#### {strings['supporting_points']}")
                for pro in pros:
                    claim = pro.get("claim", "")
                    # Translate to French if needed
                    if language == "fr" and claim:
                        claim = _translate_to_french(claim)
                    source = pro.get("source", "")
                    if source:
                        report.append(f"- {claim} ([{strings['source_label']}]({source}))")
                    else:
                        report.append(f"- {claim}")
                report.append("")

            if cons:
                report.append(f"#### {strings['contradicting_points']}")
                for con in cons:
                    claim = con.get("claim", "")
                    # Translate to French if needed
                    if language == "fr" and claim:
                        claim = _translate_to_french(claim)
                    source = con.get("source", "")
                    if source:
                        report.append(f"- {claim} ([{strings['source_label']}]({source}))")
                    else:
                        report.append(f"- {claim}")
                report.append("")
        
        # Sources (academic and official sources only)
        sources = arg.get("sources", {})
        scientific = sources.get("scientific", [])
        medical = sources.get("medical", [])
        statistical = sources.get("statistical", [])

        if scientific or medical or statistical:
            report.append(f"### {strings['sources_identified']}")
            report.append(strings["access_legend"])
            report.append("")

            if medical:
                report.append(f"**{strings['medical_sources']}**")
                for source in medical:
                    title = source.get("title", "Sans titre" if language == "fr" else "Untitled")
                    url = source.get("url", "#")
                    summary = (source.get("summary") or source.get("snippet") or "")[:150]
                    access_type = source.get("access_type", "")
                    access_icon = _get_access_icon(access_type) if access_type else ""

                    if summary:
                        report.append(f"- {access_icon} **[{title}]({url})**")
                        report.append(f"  > *{summary}...*")
                    else:
                        report.append(f"- {access_icon} [{title}]({url})")
                report.append("")

            if scientific:
                report.append(f"**{strings['scientific_sources']}**")
                for source in scientific:
                    title = source.get("title", "Sans titre" if language == "fr" else "Untitled")
                    url = source.get("url", "#")
                    summary = (source.get("summary") or source.get("snippet") or "")[:150]
                    access_type = source.get("access_type", "")
                    access_icon = _get_access_icon(access_type) if access_type else ""

                    if summary:
                        report.append(f"- {access_icon} **[{title}]({url})**")
                        report.append(f"  > *{summary}...*")
                    else:
                        report.append(f"- {access_icon} [{title}]({url})")
                report.append("")

            if statistical:
                report.append(f"**{strings['statistical_data']}**")
                for source in statistical:
                    title = source.get("title", "Sans titre" if language == "fr" else "Untitled")
                    url = source.get("url", "#")
                    access_type = source.get("access_type", "full_data")  # Statistical sources default to full_data
                    access_icon = _get_access_icon(access_type)
                    report.append(f"- {access_icon} [{title}]({url})")
                report.append("")
        
        report.append("---")
        report.append("")
        
    return "\n".join(report)
