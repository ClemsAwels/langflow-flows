"""
Script principal qui orchestre le processus de synchronisation.
Point d'entrée pour l'exécution du script.
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Any, Optional

# Importer les modules du projet avec imports relatifs
from .config import Config, parse_args
from .git_manager import GitManager
from .langflow_client import LangflowClient
from .flow_manager import FlowManager
from .folder_manager import FolderManager
from . import utils

def main():
    """
    Fonction principale qui orchestre le processus de synchronisation.
    """
    # Analyser les arguments de ligne de commande
    args = parse_args()
    
    # Initialiser la configuration
    config = Config()
    config.load_from_env()
    config.load_from_args(args)
    
    # Valider la configuration
    error = config.validate()
    if error:
        print(f"Erreur de configuration: {error}")
        sys.exit(1)
    
    # Configurer le logging
    logger = utils.setup_logging(config.verbose)
    logger.info("Démarrage de la synchronisation Langflow")
    logger.debug(f"Configuration: {config.to_dict()}")
    
    # Initialiser le client API Langflow
    client = LangflowClient(config.langflow_url, config.api_token)
    
    # Initialiser les gestionnaires
    git_manager = GitManager(config.repo_path)
    flow_manager = FlowManager(client)
    folder_manager = FolderManager(client)
    
    # Détecter les changements
    logger.info("Détection des changements Git...")
    changes = git_manager.detect_changes(config.before_commit, config.after_commit)
    
    # Afficher les changements détectés
    logger.info(f"Changements détectés:")
    logger.info(f"  - Flows ajoutés: {len(changes['flows_added'])}")
    logger.info(f"  - Flows modifiés: {len(changes['flows_modified'])}")
    logger.info(f"  - Flows supprimés: {len(changes['flows_deleted'])}")
    
    if config.verbose:
        if changes['flows_added']:
            logger.debug("Flows ajoutés:")
            for flow in changes['flows_added']:
                logger.debug(f"  - {flow}")
        
        if changes['flows_modified']:
            logger.debug("Flows modifiés:")
            for flow in changes['flows_modified']:
                logger.debug(f"  - {flow}")
        
        if changes['flows_deleted']:
            logger.debug("Flows supprimés:")
            for flow in changes['flows_deleted']:
                logger.debug(f"  - {flow}")
    
    # Traiter les flows ajoutés
    added_flows = {}
    if changes['flows_added']:
        logger.info("Traitement des flows ajoutés...")
        added_flows = flow_manager.process_added_flows(changes['flows_added'], config.repo_path)
        logger.info(f"Flows ajoutés avec succès: {len(added_flows)}")
    
    # Traiter les flows modifiés
    modified_flows = {}
    if changes['flows_modified']:
        logger.info("Traitement des flows modifiés...")
        modified_flows = flow_manager.process_modified_flows(changes['flows_modified'], config.repo_path)
        logger.info(f"Flows modifiés avec succès: {len(modified_flows)}")
    
    # Traiter les flows supprimés
    deleted_flows = []
    if changes['flows_deleted']:
        logger.info("Traitement des flows supprimés...")
        deleted_flows = flow_manager.process_deleted_flows(changes['flows_deleted'])
        logger.info(f"Flows supprimés avec succès: {len(deleted_flows)}")
    
    # Combiner les flows ajoutés et modifiés pour l'organisation en dossiers
    all_processed_flows = {**added_flows, **modified_flows}
    
    # Organiser les flows en dossiers
    if all_processed_flows and (changes['flows_added'] or changes['flows_modified']):
        logger.info("Organisation des flows en dossiers...")
        all_flow_paths = changes['flows_added'] + changes['flows_modified']
        organized_folders = folder_manager.organize_flows_by_folder(all_flow_paths, all_processed_flows)
        logger.info(f"Dossiers organisés: {len(organized_folders)}")
        
        if config.verbose and organized_folders:
            logger.debug("Dossiers organisés:")
            for folder_name, flows in organized_folders.items():
                logger.debug(f"  - {folder_name}: {len(flows)} flows")
    
    # Résumé des opérations
    logger.info("Résumé de la synchronisation:")
    logger.info(f"  - Flows ajoutés: {len(added_flows)}")
    logger.info(f"  - Flows modifiés: {len(modified_flows)}")
    logger.info(f"  - Flows supprimés: {len(deleted_flows)}")
    
    logger.info("Synchronisation terminée avec succès")

# Point d'entrée pour l'exécution directe du script
if __name__ == "__main__":
    # Ajuster le chemin d'importation pour permettre l'exécution directe
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Importer les modules sans le préfixe relatif pour l'exécution directe
    from sync_langflow.config import Config, parse_args
    from sync_langflow.git_manager import GitManager
    from sync_langflow.langflow_client import LangflowClient
    from sync_langflow.flow_manager import FlowManager
    from sync_langflow.folder_manager import FolderManager
    import sync_langflow.utils as utils
    
    main()
