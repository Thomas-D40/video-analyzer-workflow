"""
Gestionnaire de ressources pour optimiser la consommation de tokens.

Ce module permet d'accéder aux transcriptions, articles et arguments
via des références optimisées plutôt que d'envoyer tout le contenu dans les prompts,
réduisant ainsi la consommation de tokens.

Note: Utilise le concept de MCP (Model Context Protocol) pour la gestion
efficace des ressources, mais implémenté de manière simplifiée en mémoire.
"""
from typing import Dict, List, Optional, Any
import json
import hashlib


class MCPServerManager:
    """
    Gestionnaire du serveur MCP pour les ressources du workflow.
    
    Stocke les ressources en mémoire avec des identifiants uniques,
    permettant aux agents d'y accéder via des références plutôt que
    d'inclure tout le contenu dans les prompts.
    """
    
    def __init__(self):
        self._resources: Dict[str, Dict[str, Any]] = {}
    
    def register_transcript(self, video_id: str, transcript: str, chunk_size: int = 5000) -> str:
        """
        Enregistre une transcription et la divise en chunks.
        
        Args:
            video_id: Identifiant de la vidéo
            transcript: Texte complet de la transcription
            chunk_size: Taille des chunks en caractères
            
        Returns:
            URI de la ressource principale
        """
        resource_id = f"transcript:{video_id}"
        
        # Division en chunks pour accès sélectif
        chunks = []
        for i in range(0, len(transcript), chunk_size):
            chunk = transcript[i:i + chunk_size]
            chunks.append({
                "index": len(chunks),
                "text": chunk,
                "start_char": i,
                "end_char": min(i + chunk_size, len(transcript))
            })
        
        self._resources[resource_id] = {
            "type": "transcript",
            "video_id": video_id,
            "full_text": transcript,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
        
        return f"mcp://transcript/{video_id}"
    
    def get_transcript_chunk(self, video_id: str, chunk_index: int) -> Optional[str]:
        """
        Récupère un chunk spécifique de la transcription.
        
        Args:
            video_id: Identifiant de la vidéo
            chunk_index: Index du chunk (0-based)
            
        Returns:
            Texte du chunk ou None si non trouvé
        """
        resource_id = f"transcript:{video_id}"
        resource = self._resources.get(resource_id)
        
        if not resource or resource["type"] != "transcript":
            return None
        
        chunks = resource.get("chunks", [])
        if 0 <= chunk_index < len(chunks):
            return chunks[chunk_index]["text"]
        
        return None
    
    def get_transcript_summary(self, video_id: str, max_length: int = 2000) -> Optional[str]:
        """
        Récupère un résumé de la transcription (premiers caractères).
        
        Args:
            video_id: Identifiant de la vidéo
            max_length: Longueur maximale du résumé
            
        Returns:
            Résumé de la transcription
        """
        resource_id = f"transcript:{video_id}"
        resource = self._resources.get(resource_id)
        
        if not resource or resource["type"] != "transcript":
            return None
        
        full_text = resource.get("full_text", "")
        if len(full_text) <= max_length:
            return full_text
        
        # Retourne le début + indication de troncature
        return full_text[:max_length] + "\n\n[... transcription tronquée ...]"
    
    def register_articles(self, argument_id: str, articles: List[Dict]) -> str:
        """
        Enregistre une liste d'articles pour un argument.
        
        Args:
            argument_id: Identifiant unique de l'argument
            articles: Liste d'articles avec title, url, snippet
            
        Returns:
            URI de la ressource
        """
        resource_id = f"articles:{argument_id}"
        
        # Création de résumés pour chaque article (limite les tokens)
        summarized_articles = []
        for article in articles[:10]:  # Limite à 10 articles
            summarized_articles.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "summary": article.get("snippet", "")[:300]  # Limite à 300 caractères
            })
        
        self._resources[resource_id] = {
            "type": "articles",
            "argument_id": argument_id,
            "articles": summarized_articles,
            "count": len(summarized_articles)
        }
        
        return f"mcp://articles/{argument_id}"
    
    def get_articles_summary(self, argument_id: str) -> Optional[List[Dict]]:
        """
        Récupère les résumés des articles pour un argument.
        
        Args:
            argument_id: Identifiant de l'argument
            
        Returns:
            Liste des articles résumés
        """
        resource_id = f"articles:{argument_id}"
        resource = self._resources.get(resource_id)
        
        if not resource or resource["type"] != "articles":
            return None
        
        return resource.get("articles", [])
    
    def register_arguments(self, video_id: str, arguments: List[Dict]) -> str:
        """
        Enregistre les arguments extraits pour une vidéo.
        
        Args:
            video_id: Identifiant de la vidéo
            arguments: Liste des arguments extraits
            
        Returns:
            URI de la ressource
        """
        resource_id = f"arguments:{video_id}"
        
        self._resources[resource_id] = {
            "type": "arguments",
            "video_id": video_id,
            "arguments": arguments,
            "count": len(arguments)
        }
        
        return f"mcp://arguments/{video_id}"
    
    def get_arguments(self, video_id: str) -> Optional[List[Dict]]:
        """
        Récupère les arguments pour une vidéo.
        
        Args:
            video_id: Identifiant de la vidéo
            
        Returns:
            Liste des arguments
        """
        resource_id = f"arguments:{video_id}"
        resource = self._resources.get(resource_id)
        
        if not resource or resource["type"] != "arguments":
            return None
        
        return resource.get("arguments", [])
    
    def clear_resources(self, video_id: Optional[str] = None):
        """
        Nettoie les ressources, optionnellement pour une vidéo spécifique.
        
        Args:
            video_id: Si fourni, nettoie uniquement les ressources de cette vidéo
        """
        if video_id:
            keys_to_remove = [
                key for key in self._resources.keys()
                if video_id in key
            ]
            for key in keys_to_remove:
                del self._resources[key]
        else:
            self._resources.clear()


# Instance globale du gestionnaire MCP
_mcp_manager: Optional[MCPServerManager] = None


def get_mcp_manager() -> MCPServerManager:
    """Récupère l'instance globale du gestionnaire MCP."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPServerManager()
    return _mcp_manager

