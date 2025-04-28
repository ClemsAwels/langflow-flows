import logging
import os
import sys

# Configuration du logging
def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure et retourne un logger.
    
    Args:
        verbose: Si True, active le mode verbeux (DEBUG).
        
    Returns:
        logging.Logger: Logger configuré.
    """
    # Créer le logger
    logger = logging.getLogger("sync_app") # Nom du logger mis à jour
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Supprimer les handlers existants pour éviter les doublons
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Créer un handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Définir le format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    
    # Ajouter le handler au logger
    logger.addHandler(console_handler)
    
    return logger

def extract_flow_name_from_path(flow_path: str) -> str:
    """
    Extrait le nom du flow à partir du chemin du fichier.
    
    Args:
        flow_path: Chemin du fichier de flow.
        
    Returns:
        str: Nom du flow (sans extension).
    """
    return os.path.basename(flow_path).replace(".json", "")

def extract_folder_name_from_path(flow_path: str) -> str | None:
    """
    Extrait le nom du dossier à partir du chemin du fichier.
    La structure attendue est "langflow-config/flows/folder_name/flow_name.json"
    ou "flows/folder_name/flow_name.json".
    
    Args:
        flow_path: Chemin du fichier de flow.
        
    Returns:
        str | None: Nom du dossier ou None si non trouvé.
    """
    try:
        # Normaliser le chemin pour utiliser les séparateurs corrects
        normalized_path = os.path.normpath(flow_path)
        path_parts = normalized_path.split(os.sep)
        
        # Chercher l'index de "flows"
        try:
            flows_index = path_parts.index("flows")
        except ValueError:
            # Si "flows" n'est pas trouvé, le chemin n'est pas valide
            return None
        
        # Le nom du dossier est l'élément après "flows"
        if flows_index + 1 < len(path_parts) - 1: # S'assurer qu'il y a un dossier et un fichier
            return path_parts[flows_index + 1]
        else:
            # Si le flow est directement dans "flows" ou "langflow-config/flows"
            return None
            
    except Exception as e:
        logging.error(f"Erreur lors de l'extraction du nom de dossier pour {flow_path}: {e}")
        return None

