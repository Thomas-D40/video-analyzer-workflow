"""
Client pour accéder aux ressources optimisées.

Permet aux agents d'accéder aux ressources via des références optimisées
plutôt que d'inclure tout le contenu dans les prompts, réduisant ainsi
la consommation de tokens.
"""
from typing import List, Dict, Optional
from .mcp_server import get_mcp_manager


class MCPClient:
    """
    Client pour accéder aux ressources MCP.
    
    Permet de récupérer des chunks de transcription, des résumés d'articles,
    etc., sans avoir à envoyer tout le contenu dans les prompts OpenAI.
    """
    
    def __init__(self):
        self.manager = get_mcp_manager()
    
    def get_transcript_for_analysis(self, video_id: str, max_chars: int = 8000) -> str:
        """
        Récupère une portion optimisée de la transcription pour l'analyse.
        
        Au lieu d'envoyer toute la transcription, on envoie:
        - Un résumé du début (contexte)
        - Les chunks les plus pertinents (si disponibles)
        - Un indicateur de la longueur totale
        
        Args:
            video_id: Identifiant de la vidéo
            max_chars: Nombre maximum de caractères à retourner
            
        Returns:
            Texte optimisé pour l'analyse
        """
        # Récupère un résumé de la transcription
        summary = self.manager.get_transcript_summary(video_id, max_length=max_chars)
        
        if summary:
            resource_id = f"transcript:{video_id}"
            resource = self.manager._resources.get(resource_id)
            
            if resource:
                total_chunks = resource.get("total_chunks", 0)
                total_length = len(resource.get("full_text", ""))
                
                # Ajoute une note sur la longueur totale
                if total_length > max_chars:
                    summary += f"\n\n[Note: Transcription complète de {total_length} caractères, {total_chunks} chunks disponibles]"
            
            return summary
        
        return ""
    
    def get_articles_for_analysis(self, argument_id: str) -> List[Dict]:
        """
        Récupère les articles résumés pour un argument.
        
        Les articles sont déjà résumés (snippets limités) pour réduire les tokens.
        
        Args:
            argument_id: Identifiant de l'argument
            
        Returns:
            Liste des articles résumés
        """
        articles = self.manager.get_articles_summary(argument_id)
        return articles or []
    
    def format_articles_context(self, articles: List[Dict], max_length: int = 5000) -> str:
        """
        Formate les articles en contexte optimisé pour les prompts.
        
        Args:
            articles: Liste des articles
            max_length: Longueur maximale du contexte
            
        Returns:
            Texte formaté optimisé
        """
        if not articles:
            return ""
        
        formatted = []
        current_length = 0
        
        for article in articles:
            article_text = f"Article: {article.get('title', '')}\nURL: {article.get('url', '')}\nRésumé: {article.get('summary', '')}\n\n"
            
            if current_length + len(article_text) > max_length:
                break
            
            formatted.append(article_text)
            current_length += len(article_text)
        
        result = "".join(formatted)
        
        if len(articles) > len(formatted):
            result += f"\n[Note: {len(articles) - len(formatted)} article(s) supplémentaire(s) disponible(s)]"
        
        return result
    
    def get_arguments_reference(self, video_id: str) -> str:
        """
        Retourne une référence aux arguments plutôt que les arguments complets.
        
        Args:
            video_id: Identifiant de la vidéo
            
        Returns:
            Référence formatée aux arguments
        """
        arguments = self.manager.get_arguments(video_id)
        
        if not arguments:
            return ""
        
        # Retourne seulement un résumé avec le nombre d'arguments
        # Les détails complets seront récupérés via MCP si nécessaire
        return f"[{len(arguments)} argument(s) disponible(s) pour cette vidéo]"


# Instance globale du client MCP
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Récupère l'instance globale du client MCP."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client

