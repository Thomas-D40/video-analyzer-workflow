"""
Agent de recherche statistique utilisant la Banque Mondiale (World Bank).

Cet agent recherche des indicateurs et des données statistiques officielles
pour étayer ou vérifier des arguments économiques.
"""
from typing import List, Dict, Any
import wbgapi as wb

def search_world_bank_data(argument: str) -> List[Dict[str, Any]]:
    """
    Recherche des données de la Banque Mondiale pertinentes pour l'argument.
    
    Args:
        argument: Texte de l'argument
        
    Returns:
        Liste d'indicateurs avec leurs valeurs récentes pour la France (et Monde).
    """
    if not argument or len(argument.strip()) < 5:
        return []
        
    data_points = []
    
    # Si l'argument est court et semble être une requête générée (anglais/mots-clés)
    # On essaie de l'utiliser directement si l'heuristique échoue ou si c'est explicite
    query = None
    
    # Mots-clés pour la recherche d'indicateurs
    # Heuristique: chercher des mots clés économiques dans l'argument
    keywords = []
    economic_terms = [
        "impôt", "taxe", "pib", "gdp", "richesse", "wealth", "inégalité", "inequality",
        "revenu", "income", "chômage", "unemployment", "dette", "debt", "croissance", "growth"
    ]
    
    arg_lower = argument.lower()
    
    # Si l'argument est court (< 50 chars), on suppose que c'est une requête optimisée
    if len(argument) < 50:
        query = argument
    else:
        for term in economic_terms:
            if term in arg_lower:
                # Mapping français -> anglais pour l'API WB
                if term in ["impôt", "taxe"]: keywords.append("tax")
                elif term in ["pib"]: keywords.append("gdp")
                elif term in ["richesse"]: keywords.append("wealth")
                elif term in ["inégalité"]: keywords.append("gini") # Gini index
                elif term in ["revenu"]: keywords.append("income")
                elif term in ["chômage"]: keywords.append("unemployment")
                elif term in ["dette"]: keywords.append("debt")
                elif term in ["croissance"]: keywords.append("growth")
                else: keywords.append(term)
                
        if keywords:
            query = keywords[0] # On prend le premier terme trouvé pour simplifier
            
    if not query:
        return []
    
    print(f"     📊 Recherche World Bank pour: '{query}'")
    
    try:
        # 1. Trouver des indicateurs pertinents
        indicators = wb.series.info(q=query)
        
        # On prend les 3 premiers indicateurs trouvés
        relevant_codes = []
        count = 0
        for row in indicators:
            relevant_codes.append(row['id'])
            count += 1
            if count >= 3: break
            
        if not relevant_codes:
            return []
            
        # 2. Récupérer les données pour la France (FRA) et le Monde (WLD)
        # Pour les 5 dernières années disponibles
        data = wb.data.DataFrame(relevant_codes, ['FRA', 'WLD'], mrv=1)
        
        # Formatage des résultats
        if not data.empty:
            # Reset index pour avoir les codes pays et indicateurs en colonnes
            df = data.reset_index()
            
            # Convertir en dictionnaire
            records = df.to_dict('records')
            
            for record in records:
                # Le format de wbgapi peut varier, on essaie de structurer
                economy = record.get('economy', '')
                
                # On itère sur les clés qui ressemblent à des codes indicateurs
                for key, value in record.items():
                    if key in relevant_codes and value is not None:
                        # Récupérer le nom de l'indicateur
                        ind_name = wb.series.get(key)['value']
                        
                        data_points.append({
                            "indicator": ind_name,
                            "indicator_code": key,
                            "region": "France" if economy == "FRA" else "Monde",
                            "value": value,
                            "source": "World Bank"
                        })
                        
    except Exception as e:
        print(f"     ❌ Erreur World Bank: {e}")
        
    return data_points
