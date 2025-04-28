import argparse
import logging
import os
import tempfile
import sys

from .config import Config
from .utils import setup_logging, extract_flow_name_from_path
from .clients.langflow import LangflowClient
from .clients.openwebui import OpenWebUIManager
from .managers.git import GitManager
from .managers.flow import FlowManager
from .managers.folder import FolderManager

def parse_arguments() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(description="Synchronise les flows Langflow et les pipelines OpenWebUI.")
    
    # Arguments Langflow
    parser.add_argument("--langflow-url", help="URL de l\"instance Langflow")
    parser.add_argument("--api-token", help="Token d\"API pour l\"authentification Langflow")
    parser.add_argument("--repo-path", help="Chemin vers le dépôt Git local")
    parser.add_argument("--before-commit", help="Commit de référence pour la comparaison (avant)")
    parser.add_argument("--after-commit", help="Commit de référence pour la comparaison (après)")
    parser.add_argument("--verbose", action="store_true", help="Active le mode verbeux pour le logging")
    
    # Arguments OpenWebUI
    parser.add_argument("--openwebui-url", help="URL de l\"instance OpenWebUI")
    parser.add_argument("--openwebui-api-key", help="Clé API pour l\"authentification OpenWebUI")
    parser.add_argument("--enable-openwebui", action="store_true", help="Active l\"intégration avec OpenWebUI")
    parser.add_argument("--openwebui-template-path", help="Chemin vers le template de pipeline personnalisé")
    
    return parser.parse_args()

def main():
    """Point d\"entrée principal du script."""
    args = parse_arguments()
    
    # Initialiser la configuration
    config = Config()
    config.load_from_env()
    config.load_from_args(args)
    
    # Valider la configuration
    error = config.validate()
    if error:
        print(f"Erreur de configuration: {error}", file=sys.stderr)
        sys.exit(1)
        
    # Configurer le logging
    logger = setup_logging(config.verbose)
    logger.info("Configuration chargée:")
    # Utiliser des variables temporaires pour éviter les erreurs de syntaxe f-string
    log_config = config.to_dict()
    langflow_url = log_config["langflow_url"]
    api_token = log_config["api_token"]
    repo_path = log_config["repo_path"]
    before_commit = log_config["before_commit"]
    after_commit = log_config["after_commit"]
    verbose = log_config["verbose"]
    enable_openwebui = log_config["enable_openwebui"]
    openwebui_url = log_config["openwebui_url"]
    openwebui_api_key = log_config["openwebui_api_key"]
    openwebui_template_path = log_config["openwebui_template_path"]
    
    logger.info(f"  Langflow URL: {langflow_url}")
    logger.info(f"  API Token: {api_token}")
    logger.info(f"  Repo Path: {repo_path}")
    logger.info(f"  Before Commit: {before_commit}")
    logger.info(f"  After Commit: {after_commit}")
    logger.info(f"  Verbose: {verbose}")
    logger.info(f"  Enable OpenWebUI: {enable_openwebui}")
    if config.enable_openwebui:
        logger.info(f"  OpenWebUI URL: {openwebui_url}")
        logger.info(f"  OpenWebUI API Key: {openwebui_api_key}")
        logger.info(f"  OpenWebUI Template Path: {openwebui_template_path}")

    # Initialiser les clients
    try:
        langflow_client = LangflowClient(config.langflow_url, config.api_token)
        openwebui_manager = None
        if config.enable_openwebui:
            openwebui_manager = OpenWebUIManager(
                config.openwebui_url,
                config.openwebui_api_key,
                config.openwebui_template_path
            )
    except Exception as e:
        logger.error(f"Erreur lors de l\"initialisation des clients: {e}")
        sys.exit(1)

    # Initialiser les gestionnaires
    git_manager = GitManager(config.repo_path)
    flow_manager = FlowManager(langflow_client)
    folder_manager = FolderManager(langflow_client)

    logger.info("Démarrage de la synchronisation Langflow...")

    # 1. Détecter les changements Git
    logger.info("Détection des changements Git...")
    if not config.before_commit or not config.after_commit:
        logger.error("Les commits de référence (before et after) sont requis pour détecter les changements.")
        sys.exit(1)
        
    changes = git_manager.detect_changes(config.before_commit, config.after_commit)
    logger.info("Changements détectés:")
    # Correction: Utiliser des variables temporaires pour les longueurs
    num_flows_added = len(changes["flows_added"])
    num_flows_modified = len(changes["flows_modified"])
    num_flows_deleted = len(changes["flows_deleted"])
    logger.info(f"  - Flows ajoutés: {num_flows_added}")
    logger.info(f"  - Flows modifiés: {num_flows_modified}")
    logger.info(f"  - Flows supprimés: {num_flows_deleted}")

    # 2. Traiter les flows supprimés
    if changes["flows_deleted"]:
        logger.info("Traitement des flows supprimés...")
        deleted_flow_ids = flow_manager.process_deleted_flows(changes["flows_deleted"])
        logger.info(f"Flows supprimés avec succès: {len(deleted_flow_ids)}")

    # 3. Traiter les flows ajoutés
    processed_added_flows = {}
    if changes["flows_added"]:
        logger.info("Traitement des flows ajoutés...")
        processed_added_flows = flow_manager.process_added_flows(changes["flows_added"], config.repo_path)
        logger.info(f"Flows ajoutés traités (ajoutés/mis à jour dans Langflow): {len(processed_added_flows)}")

    # 4. Traiter les flows modifiés
    processed_modified_flows = {}
    if changes["flows_modified"]:
        logger.info("Traitement des flows modifiés...")
        processed_modified_flows = flow_manager.process_modified_flows(changes["flows_modified"], config.repo_path)
        logger.info(f"Flows modifiés traités (ajoutés/mis à jour dans Langflow): {len(processed_modified_flows)}")

    # 5. Combiner les flows ajoutés et modifiés pour l\"organisation et OpenWebUI
    all_processed_flows = {**processed_added_flows, **processed_modified_flows}
    all_processed_flow_paths = changes["flows_added"] + changes["flows_modified"]

    # 6. Organiser les flows en dossiers
    if all_processed_flow_paths:
        logger.info("Organisation des flows en dossiers...")
        folder_manager.organize_flows_by_folder(all_processed_flow_paths, all_processed_flows)

    # 7. Intégration OpenWebUI (si activée)
    if config.enable_openwebui and openwebui_manager and all_processed_flows:
        logger.info("Intégration OpenWebUI...")
        # Créer un répertoire temporaire pour les pipelines générés
        with tempfile.TemporaryDirectory() as temp_dir:
            pipelines_uploaded = 0
            for flow_id, flow_data in all_processed_flows.items():
                # Trouver le chemin correspondant pour extraire le nom de fichier original si nécessaire
                flow_path_for_name = None
                flow_name_from_data = flow_data.get("name")
                if flow_name_from_data:
                     for path in all_processed_flow_paths:
                         if extract_flow_name_from_path(path) == flow_name_from_data:
                             flow_path_for_name = path
                             break
                if not flow_path_for_name:
                     # Fallback si on ne trouve pas le chemin exact (devrait être rare)
                     logger.warning(f"Impossible de trouver le chemin exact pour le flow ID {flow_id}, utilisation d\"un nom par défaut.")
                     flow_path_for_name = f"unknown_flow_{flow_id}.json"

                logger.debug(f"Traitement du flow {flow_id} pour OpenWebUI...")
                endpoint_name, flow_name = openwebui_manager.extract_flow_info(flow_data, flow_path_for_name)
                
                if endpoint_name and flow_name:
                    logger.info(f"  -> Génération du pipeline pour 	{flow_name}	 (Endpoint: {endpoint_name})")
                    pipeline_path = openwebui_manager.generate_pipeline(endpoint_name, flow_name, temp_dir)
                    
                    if pipeline_path:
                        logger.info(f"  -> Téléchargement du pipeline {os.path.basename(pipeline_path)} vers OpenWebUI...")
                        success = openwebui_manager.upload_pipeline(pipeline_path)
                        if success:
                            pipelines_uploaded += 1
                        # Le fichier temporaire sera supprimé automatiquement à la sortie du bloc `with`
                    else:
                        logger.error(f"  -> Échec de la génération du pipeline pour {flow_name}")
                else:
                    logger.warning(f"  -> Informations insuffisantes (endpoint ou nom) pour générer le pipeline pour le flow ID {flow_id}")
            logger.info(f"Pipelines OpenWebUI téléchargés/mis à jour: {pipelines_uploaded}")

    # 8. Supprimer les dossiers vides
    logger.info("Suppression des dossiers vides...")
    deleted_folders = folder_manager.delete_empty_folders()
    if deleted_folders:
        logger.info(f"Dossiers vides supprimés: {len(deleted_folders)}")
        for folder_name in deleted_folders:
            logger.info(f"  - {folder_name}")
    else:
        logger.info("Aucun dossier vide à supprimer")

    logger.info("Synchronisation terminée.")

if __name__ == "__main__":
    main()

