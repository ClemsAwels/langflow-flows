"""
Fonctions utilitaires pour le traitement des fichiers, le logging, etc.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Optional

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
    logger = logging.getLogger("sync_langflow")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Supprimer les handlers existants
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Créer un handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Définir le format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Ajouter le handler au logger
    logger.addHandler(console_handler)
    
    return logger

def read_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Lit un fichier JSON et retourne son contenu.
    
    Args:
        file_path: Chemin du fichier JSON.
        
    Returns:
        Optional[Dict[str, Any]]: Contenu du fichier JSON ou None en cas d'erreur.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logging.error(f"Erreur de décodage JSON pour le fichier {file_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Erreur lors de la lecture du fichier {file_path}: {e}")
        return None

def write_json_file(file_path: str, data: Dict[str, Any]) -> bool:
    """
    Écrit des données dans un fichier JSON.
    
    Args:
        file_path: Chemin du fichier JSON.
        data: Données à écrire.
        
    Returns:
        bool: True si l'écriture a réussi, False sinon.
    """
    try:
        # Créer le répertoire parent si nécessaire
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Erreur lors de l'écriture du fichier {file_path}: {e}")
        return False

def extract_flow_name_from_path(file_path: str) -> str:
    """
    Extrait le nom du flow à partir du chemin du fichier.
    
    Args:
        file_path: Chemin du fichier de flow.
        
    Returns:
        str: Nom du flow.
    """
    return os.path.basename(file_path).replace(".json", "")

def extract_folder_name_from_path(file_path: str) -> Optional[str]:
    """
    Extrait le nom du dossier à partir du chemin du fichier.
    
    Args:
        file_path: Chemin du fichier de flow.
        
    Returns:
        Optional[str]: Nom du dossier ou None si le chemin ne contient pas de dossier.
    """
    path_parts = file_path.split(os.sep)
    if len(path_parts) >= 3 and path_parts[0] == "langflow-config" and path_parts[1] == "flows":
        return path_parts[2]  # langflow-config/flows/folder_name/...
    return None

def group_flows_by_folder(flow_paths: list) -> Dict[str, list]:
    """
    Regroupe les flows par dossier.
    
    Args:
        flow_paths: Liste des chemins de flows.
        
    Returns:
        Dict[str, list]: Dictionnaire des flows regroupés par dossier.
    """
    result = {}
    for path in flow_paths:
        folder_name = extract_folder_name_from_path(path)
        if folder_name:
            if folder_name not in result:
                result[folder_name] = []
            result[folder_name].append(path)
    return result
