#!/usr/bin/env python3
"""
sync_langflow.py - Script de synchronisation des flows Langflow

Ce script détecte les changements dans un dépôt Git et synchronise les flows Langflow
entre le dépôt et une instance Langflow. Il gère l'ajout, la modification et la suppression
de flows, ainsi que leur organisation en dossiers.

Utilisation:
    python sync_langflow.py [--langflow-url URL] [--api-token TOKEN] [--repo-path PATH]
                           [--before-commit COMMIT] [--after-commit COMMIT] [--verbose]
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import Dict, List, Any, Optional, Tuple

import requests
from requests.exceptions import RequestException

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

# Classe de configuration
class Config:
    """Classe de configuration pour la synchronisation Langflow."""

    def __init__(self):
        """Initialise la configuration avec les valeurs par défaut."""
        self.langflow_url = "http://localhost:7860"
        self.api_token = None
        self.repo_path = os.getcwd()
        self.before_commit = None
        self.after_commit = None
        self.verbose = False

    def load_from_env(self) -> None:
        """Charge la configuration à partir des variables d'environnement."""
        self.langflow_url = os.environ.get("LANGFLOW_URL", self.langflow_url)
        self.api_token = os.environ.get("LANGFLOW_API_TOKEN", self.api_token)
        self.repo_path = os.environ.get("REPO_PATH", self.repo_path)
        self.before_commit = os.environ.get("BEFORE_COMMIT", self.before_commit)
        self.after_commit = os.environ.get("AFTER_COMMIT", self.after_commit)
        self.verbose = os.environ.get("VERBOSE", "False").lower() == "true"

    def load_from_args(self, args: argparse.Namespace) -> None:
        """
        Charge la configuration à partir des arguments de ligne de commande.
        
        Args:
            args: Arguments de ligne de commande parsés.
        """
        if args.langflow_url:
            self.langflow_url = args.langflow_url
        if args.api_token:
            self.api_token = args.api_token
        if args.repo_path:
            self.repo_path = args.repo_path
        if args.before_commit:
            self.before_commit = args.before_commit
        if args.after_commit:
            self.after_commit = args.after_commit
        if args.verbose:
            self.verbose = args.verbose

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la configuration en dictionnaire.
        
        Returns:
            Dict[str, Any]: Configuration sous forme de dictionnaire.
        """
        return {
            "langflow_url": self.langflow_url,
            "api_token": "***" if self.api_token else None,
            "repo_path": self.repo_path,
            "before_commit": self.before_commit,
            "after_commit": self.after_commit,
            "verbose": self.verbose
        }

    def validate(self) -> Optional[str]:
        """
        Valide la configuration.
        
        Returns:
            Optional[str]: Message d'erreur si la configuration est invalide, None sinon.
        """
        if not self.langflow_url:
            return "L'URL de Langflow est requise"
        
        # Vérifier que le chemin du dépôt existe
        if not os.path.exists(self.repo_path):
            return f"Le chemin du dépôt '{self.repo_path}' n'existe pas"
        
        # Vérifier que le chemin du dépôt est un dépôt Git
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            return f"Le chemin '{self.repo_path}' n'est pas un dépôt Git"
        
        return None

# Client API Langflow
class LangflowClient:
    """Client pour interagir avec l'API Langflow."""

    def __init__(self, base_url: str, api_token: Optional[str] = None):
        """
        Initialise le client Langflow.
        
        Args:
            base_url: URL de base de l'API Langflow.
            api_token: Token d'API pour l'authentification (optionnel).
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Ajouter le token d'authentification s'il est fourni
        if api_token:
            self.headers["Authorization"] = f"Bearer {api_token}"
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Gère la réponse de l'API et lève une exception en cas d'erreur.
        
        Args:
            response: Réponse de l'API.
            
        Returns:
            Dict[str, Any]: Données de la réponse.
            
        Raises:
            Exception: Si la réponse contient une erreur.
        """
        try:
            response.raise_for_status()
            return response.json() if response.content else {}
        except RequestException as e:
            error_msg = f"Erreur API: {e}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_msg = f"Erreur API: {error_data['detail']}"
            except:
                pass
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def get_flows(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des flows.
        
        Args:
            folder_id: ID du dossier pour filtrer les flows (optionnel).
            
        Returns:
            List[Dict[str, Any]]: Liste des flows.
        """
        params = {
            "remove_example_flows": "true",
            "components_only": "false",
            "get_all": "true",
            "header_flows": "false",
            "page": "1",
            "size": "50"
        }
        
        if folder_id:
            params["folder_id"] = folder_id
            params["get_all"] = "false"
        
        url = f"{self.base_url}/api/v1/flows/"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des flows: {e}")
            return []
    
    def get_flow_by_id(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un flow par son ID.
        
        Args:
            flow_id: ID du flow.
            
        Returns:
            Optional[Dict[str, Any]]: Données du flow ou None si non trouvé.
        """
        url = f"{self.base_url}/api/v1/flows/{flow_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du flow {flow_id}: {e}")
            return None
    
    def create_flow(self, flow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crée un nouveau flow.
        
        Args:
            flow_data: Données du flow à créer.
            
        Returns:
            Optional[Dict[str, Any]]: Données du flow créé ou None en cas d'erreur.
        """
        url = f"{self.base_url}/api/v1/flows/"
        
        try:
            response = requests.post(url, headers=self.headers, json=flow_data)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la création du flow: {e}")
            return None
    
    def update_flow(self, flow_id: str, flow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Met à jour un flow existant.
        
        Args:
            flow_id: ID du flow à mettre à jour.
            flow_data: Nouvelles données du flow.
            
        Returns:
            Optional[Dict[str, Any]]: Données du flow mis à jour ou None en cas d'erreur.
        """
        url = f"{self.base_url}/api/v1/flows/{flow_id}"
        
        try:
            response = requests.patch(url, headers=self.headers, json=flow_data)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du flow {flow_id}: {e}")
            return None
    
    def delete_flow(self, flow_id: str) -> bool:
        """
        Supprime un flow.
        
        Args:
            flow_id: ID du flow à supprimer.
            
        Returns:
            bool: True si la suppression a réussi, False sinon.
        """
        url = f"{self.base_url}/api/v1/flows/{flow_id}"
        
        try:
            response = requests.delete(url, headers=self.headers)
            self._handle_response(response)
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la suppression du flow {flow_id}: {e}")
            return False
    
    def get_folders(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des dossiers.
        
        Returns:
            List[Dict[str, Any]]: Liste des dossiers.
        """
        url = f"{self.base_url}/api/v1/folders/"
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des dossiers: {e}")
            return []
    
    def get_folder_by_id(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un dossier par son ID.
        
        Args:
            folder_id: ID du dossier.
            
        Returns:
            Optional[Dict[str, Any]]: Données du dossier ou None si non trouvé.
        """
        url = f"{self.base_url}/api/v1/folders/{folder_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du dossier {folder_id}: {e}")
            return None
    
    def create_folder(self, folder_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crée un nouveau dossier.
        
        Args:
            folder_data: Données du dossier à créer.
            
        Returns:
            Optional[Dict[str, Any]]: Données du dossier créé ou None en cas d'erreur.
        """
        url = f"{self.base_url}/api/v1/folders/"
        
        try:
            response = requests.post(url, headers=self.headers, json=folder_data)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la création du dossier: {e}")
            return None
    
    def update_folder(self, folder_id: str, folder_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Met à jour un dossier existant.
        
        Args:
            folder_id: ID du dossier à mettre à jour.
            folder_data: Nouvelles données du dossier.
            
        Returns:
            Optional[Dict[str, Any]]: Données du dossier mis à jour ou None en cas d'erreur.
        """
        url = f"{self.base_url}/api/v1/folders/{folder_id}"
        
        try:
            response = requests.patch(url, headers=self.headers, json=folder_data)
            return self._handle_response(response)
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du dossier {folder_id}: {e}")
            return None

# Gestionnaire Git
class GitManager:
    """Gestionnaire pour interagir avec Git et détecter les changements."""

    def __init__(self, repo_path: str):
        """
        Initialise le gestionnaire Git.
        
        Args:
            repo_path: Chemin vers le dépôt Git local.
        """
        self.repo_path = repo_path
    
    def _run_git_command(self, command: List[str]) -> Tuple[bool, str]:
        """
        Exécute une commande Git et retourne le résultat.
        
        Args:
            command: Liste des arguments de la commande Git.
            
        Returns:
            Tuple[bool, str]: Tuple contenant un booléen indiquant le succès et la sortie de la commande.
        """
        try:
            # Préfixer la commande avec 'git'
            full_command = ["git"] + command
            
            # Exécuter la commande dans le répertoire du dépôt
            result = subprocess.run(
                full_command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_message = f"Erreur Git: {e.stderr.strip()}"
            logging.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"Erreur lors de l'exécution de la commande Git: {e}"
            logging.error(error_message)
            return False, error_message
    
    def detect_changes(self, before_commit: Optional[str], after_commit: Optional[str]) -> Dict[str, List[str]]:
        """
        Détecte les fichiers ajoutés, modifiés et supprimés entre deux commits.
        
        Args:
            before_commit: Commit de référence avant (optionnel).
            after_commit: Commit de référence après (optionnel).
            
        Returns:
            Dict[str, List[str]]: Dictionnaire contenant les listes de fichiers ajoutés, modifiés et supprimés.
        """
        # Initialiser le résultat
        changes = {
            "added": [],
            "modified": [],
            "deleted": [],
            "flows_added": [],
            "flows_modified": [],
            "flows_deleted": []
        }
        
        # Déterminer les commits à comparer
        if not before_commit:
            # Si before_commit n'est pas spécifié, utiliser HEAD~1 (commit précédent)
            success, before_commit = self._run_git_command(["rev-parse", "HEAD~1"])
            if not success:
                logging.error("Impossible de déterminer le commit précédent.")
                return changes
        
        if not after_commit:
            # Si after_commit n'est pas spécifié, utiliser HEAD (commit actuel)
            success, after_commit = self._run_git_command(["rev-parse", "HEAD"])
            if not success:
                logging.error("Impossible de déterminer le commit actuel.")
                return changes
        
        # Obtenir les changements entre les deux commits
        success, diff_output = self._run_git_command(["diff", "--name-status", before_commit, after_commit])
        if not success:
            logging.error(f"Impossible de détecter les changements entre {before_commit} et {after_commit}.")
            return changes
        
        # Analyser la sortie de git diff
        for line in diff_output.splitlines():
            if not line.strip():
                continue
            
            # Format: A/M/D<tab>file_path
            parts = line.split("\t", 1)
            if len(parts) != 2:
                logging.warning(f"Format de ligne inattendu: {line}")
                continue
            
            status, file_path = parts
            
            # Ajouter le fichier à la liste correspondante
            if status.startswith("A"):
                changes["added"].append(file_path)
                if file_path.startswith("langflow-config/flows/"):
                    changes["flows_added"].append(file_path)
            elif status.startswith("M"):
                changes["modified"].append(file_path)
                if file_path.startswith("langflow-config/flows/"):
                    changes["flows_modified"].append(file_path)
            elif status.startswith("D"):
                changes["deleted"].append(file_path)
                if file_path.startswith("langflow-config/flows/"):
                    changes["flows_deleted"].append(file_path)
        
        return changes

# Gestionnaire de flows
class FlowManager:
    """Gestionnaire pour les opérations sur les flows Langflow."""

    def __init__(self, client: LangflowClient):
        """
        Initialise le gestionnaire de flows.
        
        Args:
            client: Client API Langflow.
        """
        self.client = client
        self._flows_cache = None
    
    def _get_all_flows(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Récupère tous les flows depuis l'API Langflow.
        
        Args:
            refresh: Si True, force une nouvelle requête à l'API.
            
        Returns:
            List[Dict[str, Any]]: Liste des flows.
        """
        if self._flows_cache is None or refresh:
            self._flows_cache = self.client.get_flows()
        return self._flows_cache
    
    def find_flow_by_name(self, flow_name: str) -> Optional[Dict[str, Any]]:
        """
        Trouve un flow par son nom.
        
        Args:
            flow_name: Nom du flow à rechercher.
            
        Returns:
            Optional[Dict[str, Any]]: Flow trouvé ou None si non trouvé.
        """
        flows = self._get_all_flows()
        for flow in flows:
            if flow.get("name") == flow_name:
                return flow
        return None
    
    def add_flow(self, file_path: str, flow_content: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Ajoute un nouveau flow.
        
        Args:
            file_path: Chemin du fichier de flow.
            flow_content: Contenu JSON du flow.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict[str, Any]]]: 
                - Succès de l'opération
                - ID du flow créé ou message d'erreur
                - Données du flow créé
        """
        try:
            # Analyser le contenu JSON
            flow_data = json.loads(flow_content)
            
            # Extraire le nom du flow à partir du chemin du fichier
            # Utiliser uniquement le nom du fichier sans extension comme nom du flow
            flow_name = os.path.basename(file_path).replace(".json", "")
            
            # Vérifier si le flow existe déjà
            existing_flow = self.find_flow_by_name(flow_name)
            if existing_flow:
                logging.warning(f"Le flow '{flow_name}' existe déjà. Utilisation de la méthode de mise à jour.")
                return self.update_flow(existing_flow["id"], flow_data)
            
            # S'assurer que le nom est défini dans les données
            if "name" not in flow_data:
                flow_data["name"] = flow_name
            
            # Créer le flow
            result = self.client.create_flow(flow_data)
            if result:
                logging.info(f"Flow '{flow_name}' créé avec succès (ID: {result.get('id')})")
                # Mettre à jour le cache
                self._flows_cache = None
                return True, result.get("id"), result
            else:
                return False, "Échec de la création du flow", None
        except json.JSONDecodeError as e:
            error_msg = f"Erreur de décodage JSON pour le fichier {file_path}: {e}"
            logging.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Erreur lors de l'ajout du flow {file_path}: {e}"
            logging.error(error_msg)
            return False, error_msg, None
    
    def update_flow(self, flow_id: str, flow_data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Met à jour un flow existant.
        
        Args:
            flow_id: ID du flow à mettre à jour.
            flow_data: Nouvelles données du flow.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict[str, Any]]]: 
                - Succès de l'opération
                - ID du flow mis à jour ou message d'erreur
                - Données du flow mis à jour
        """
        try:
            result = self.client.update_flow(flow_id, flow_data)
            if result:
                logging.info(f"Flow '{flow_data.get('name', flow_id)}' mis à jour avec succès")
                # Mettre à jour le cache
                self._flows_cache = None
                return True, flow_id, result
            else:
                return False, f"Échec de la mise à jour du flow {flow_id}", None
        except Exception as e:
            error_msg = f"Erreur lors de la mise à jour du flow {flow_id}: {e}"
            logging.error(error_msg)
            return False, error_msg, None
    
    def delete_flow(self, flow_path: str) -> Tuple[bool, str]:
        """
        Supprime un flow.
        
        Args:
            flow_path: Chemin du fichier de flow supprimé.
            
        Returns:
            Tuple[bool, str]: Succès de l'opération et message.
        """
        try:
            # Extraire le nom du flow à partir du chemin du fichier
            # Utiliser uniquement le nom du fichier sans extension comme nom du flow
            flow_name = os.path.basename(flow_path).replace(".json", "")
            
            # Trouver le flow par son nom
            flow = self.find_flow_by_name(flow_name)
            if not flow:
                return False, f"Flow '{flow_name}' non trouvé"
            
            # Supprimer le flow
            flow_id = flow["id"]
            success = self.client.delete_flow(flow_id)
            if success:
                logging.info(f"Flow '{flow_name}' (ID: {flow_id}) supprimé avec succès")
                # Mettre à jour le cache
                self._flows_cache = None
                return True, f"Flow '{flow_name}' supprimé avec succès"
            else:
                return False, f"Échec de la suppression du flow '{flow_name}'"
        except Exception as e:
            error_msg = f"Erreur lors de la suppression du flow {flow_path}: {e}"
            logging.error(error_msg)
            return False, error_msg
    
    def process_added_flows(self, added_flows: List[str], repo_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Traite les flows ajoutés.
        
        Args:
            added_flows: Liste des chemins des flows ajoutés.
            repo_path: Chemin du dépôt Git.
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionnaire des flows ajoutés avec succès (ID -> données).
        """
        successful_flows = {}
        
        for flow_path in added_flows:
            try:
                # Construire le chemin complet du fichier
                full_path = os.path.join(repo_path, flow_path)
                
                # Vérifier si le fichier existe
                if not os.path.exists(full_path):
                    logging.warning(f"Le fichier {full_path} n'existe pas")
                    continue
                
                # Lire le contenu du fichier
                with open(full_path, "r", encoding="utf-8") as file:
                    flow_content = file.read()
                
                # Ajouter le flow
                success, flow_id, flow_data = self.add_flow(flow_path, flow_content)
                if success and flow_id and flow_data:
                    successful_flows[flow_id] = flow_data
                    logging.info(f"Flow ajouté avec succès: {flow_path} (ID: {flow_id})")
                else:
                    logging.error(f"Échec de l'ajout du flow {flow_path}: {flow_id}")
            except Exception as e:
                logging.error(f"Erreur lors du traitement du flow ajouté {flow_path}: {e}")
        
        return successful_flows
    
    def process_modified_flows(self, modified_flows: List[str], repo_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Traite les flows modifiés.
        
        Args:
            modified_flows: Liste des chemins des flows modifiés.
            repo_path: Chemin du dépôt Git.
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionnaire des flows mis à jour avec succès (ID -> données).
        """
        successful_flows = {}
        
        for flow_path in modified_flows:
            try:
                # Construire le chemin complet du fichier
                full_path = os.path.join(repo_path, flow_path)
                
                # Vérifier si le fichier existe
                if not os.path.exists(full_path):
                    logging.warning(f"Le fichier {full_path} n'existe pas")
                    continue
                
                # Extraire le nom du flow à partir du chemin du fichier
                # Utiliser uniquement le nom du fichier sans extension comme nom du flow
                flow_name = os.path.basename(flow_path).replace(".json", "")
                
                # Trouver le flow par son nom
                flow = self.find_flow_by_name(flow_name)
                if not flow:
                    logging.warning(f"Flow '{flow_name}' non trouvé, tentative d'ajout à la place")
                    # Si le flow n'existe pas, l'ajouter
                    with open(full_path, "r", encoding="utf-8") as file:
                        flow_content = file.read()
                    success, flow_id, flow_data = self.add_flow(flow_path, flow_content)
                    if success and flow_id and flow_data:
                        successful_flows[flow_id] = flow_data
                    continue
                
                # Lire le contenu du fichier
                with open(full_path, "r", encoding="utf-8") as file:
                    flow_content = file.read()
                
                # Analyser le contenu JSON
                flow_data = json.loads(flow_content)
                
                # Mettre à jour le flow
                success, flow_id, updated_flow = self.update_flow(flow["id"], flow_data)
                if success and flow_id and updated_flow:
                    successful_flows[flow_id] = updated_flow
                    logging.info(f"Flow mis à jour avec succès: {flow_path} (ID: {flow_id})")
                else:
                    logging.error(f"Échec de la mise à jour du flow {flow_path}: {flow_id}")
            except json.JSONDecodeError as e:
                logging.error(f"Erreur de décodage JSON pour le fichier {flow_path}: {e}")
            except Exception as e:
                logging.error(f"Erreur lors du traitement du flow modifié {flow_path}: {e}")
        
        return successful_flows
    
    def process_deleted_flows(self, deleted_flows: List[str]) -> List[str]:
        """
        Traite les flows supprimés.
        
        Args:
            deleted_flows: Liste des chemins des flows supprimés.
            
        Returns:
            List[str]: Liste des IDs des flows supprimés avec succès.
        """
        successful_deletions = []
        
        for flow_path in deleted_flows:
            try:
                # Supprimer le flow
                success, message = self.delete_flow(flow_path)
                if success:
                    # Extraire le nom du flow à partir du chemin du fichier
                    flow_name = os.path.basename(flow_path).replace(".json", "")
                    # Trouver l'ID du flow (avant suppression)
                    flow = self.find_flow_by_name(flow_name)
                    if flow:
                        successful_deletions.append(flow["id"])
                    logging.info(f"Flow supprimé avec succès: {flow_path}")
                else:
                    logging.error(f"Échec de la suppression du flow {flow_path}: {message}")
            except Exception as e:
                logging.error(f"Erreur lors du traitement du flow supprimé {flow_path}: {e}")
        
        return successful_deletions

# Gestionnaire de dossiers
class FolderManager:
    """Gestionnaire pour les dossiers Langflow."""

    def __init__(self, client: LangflowClient):
        """
        Initialise le gestionnaire de dossiers.
        
        Args:
            client: Client API Langflow.
        """
        self.client = client
        self._folders_cache = None
    
    def _get_all_folders(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Récupère tous les dossiers depuis l'API Langflow.
        
        Args:
            refresh: Si True, force une nouvelle requête à l'API.
            
        Returns:
            List[Dict[str, Any]]: Liste des dossiers.
        """
        if self._folders_cache is None or refresh:
            self._folders_cache = self.client.get_folders()
        return self._folders_cache
    
    def find_folder_by_name(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """
        Trouve un dossier par son nom.
        
        Args:
            folder_name: Nom du dossier à rechercher.
            
        Returns:
            Optional[Dict[str, Any]]: Dossier trouvé ou None si non trouvé.
        """
        folders = self._get_all_folders()
        for folder in folders:
            if folder.get("name") == folder_name:
                return folder
        return None
    
    def create_folder(self, folder_name: str, description: str = "", flows_list: List[str] = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Crée un nouveau dossier.
        
        Args:
            folder_name: Nom du dossier.
            description: Description du dossier.
            flows_list: Liste des IDs de flows à inclure dans le dossier.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict[str, Any]]]: 
                - Succès de l'opération
                - ID du dossier créé ou message d'erreur
                - Données du dossier créé
        """
        try:
            # Vérifier si le dossier existe déjà
            existing_folder = self.find_folder_by_name(folder_name)
            if existing_folder:
                logging.info(f"Le dossier '{folder_name}' existe déjà (ID: {existing_folder.get('id')})")
                return True, existing_folder.get("id"), existing_folder
            
            # Préparer les données du dossier
            folder_data = {
                "name": folder_name,
                "description": description or f"Dossier pour les flows {folder_name}",
                "components_list": [],
                "flows_list": flows_list or []
            }
            
            # Créer le dossier
            result = self.client.create_folder(folder_data)
            if result:
                logging.info(f"Dossier '{folder_name}' créé avec succès (ID: {result.get('id')})")
                # Mettre à jour le cache
                self._folders_cache = None
                return True, result.get("id"), result
            else:
                return False, "Échec de la création du dossier", None
        except Exception as e:
            error_msg = f"Erreur lors de la création du dossier {folder_name}: {e}"
            logging.error(error_msg)
            return False, error_msg, None
    
    def update_folder(self, folder_id: str, folder_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Met à jour un dossier existant.
        
        Args:
            folder_id: ID du dossier à mettre à jour.
            folder_data: Nouvelles données du dossier.
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: Succès de l'opération et données du dossier mis à jour.
        """
        try:
            result = self.client.update_folder(folder_id, folder_data)
            if result:
                logging.info(f"Dossier '{folder_data.get('name', folder_id)}' mis à jour avec succès")
                # Mettre à jour le cache
                self._folders_cache = None
                return True, result
            else:
                return False, None
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du dossier {folder_id}: {e}")
            return False, None
    
    def add_flows_to_folder(self, folder_id: str, flow_ids: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Ajoute des flows à un dossier existant.
        
        Args:
            folder_id: ID du dossier.
            flow_ids: Liste des IDs de flows à ajouter.
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: Succès de l'opération et données du dossier mis à jour.
        """
        try:
            # Récupérer le dossier actuel
            folder = self.client.get_folder_by_id(folder_id)
            if not folder:
                logging.error(f"Dossier avec ID {folder_id} non trouvé")
                return False, None
            
            # Mettre à jour la liste des flows
            update_data = {
                "flows": flow_ids
            }
            
            # Mettre à jour le dossier
            return self.update_folder(folder_id, update_data)
        except Exception as e:
            logging.error(f"Erreur lors de l'ajout de flows au dossier {folder_id}: {e}")
            return False, None
    
    def organize_flows_by_folder(self, flow_paths: List[str], flow_ids: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Organise les flows en dossiers basés sur leur chemin, en préservant les flows existants
        et en traitant chaque dossier indépendamment.
        
        Args:
            flow_paths: Liste des chemins de flows modifiés/ajoutés.
            flow_ids: Dictionnaire des flows ajoutés/modifiés (ID -> données).
            
        Returns:
            Dict[str, List[str]]: Dictionnaire des dossiers créés/mis à jour (nom -> liste d'IDs).
        """
        # Initialiser le résultat
        organized_folders = {}
        
        # Créer un dictionnaire pour mapper les noms de flows à leurs IDs
        flow_name_to_id = {}
        for flow_id, flow_data in flow_ids.items():
            flow_name = flow_data.get("name")
            if flow_name:
                flow_name_to_id[flow_name] = flow_id
        
        # Regrouper les flows par dossier
        folder_flows = {}
        for flow_path in flow_paths:
            # Extraire le nom du dossier à partir du chemin (exemple: langflow-config/flows/excel/flow.json -> excel)
            path_parts = flow_path.split(os.sep)
            if len(path_parts) >= 3 and path_parts[0] == "langflow-config" and path_parts[1] == "flows":
                folder_name = path_parts[2]  # langflow-config/flows/folder_name/...
                
                # Initialiser la liste des flows pour ce dossier si nécessaire
                if folder_name not in folder_flows:
                    folder_flows[folder_name] = []
                
                # Extraire le nom du flow à partir du chemin
                flow_name = os.path.basename(flow_path).replace(".json", "")
                
                # Ajouter le flow à la liste du dossier s'il existe dans flow_ids
                if flow_name in flow_name_to_id:
                    flow_id = flow_name_to_id[flow_name]
                    if flow_id not in folder_flows[folder_name]:  # Éviter les doublons
                        folder_flows[folder_name].append(flow_id)
        
        # Récupérer tous les dossiers existants une seule fois
        existing_folders = {folder.get("name"): folder for folder in self._get_all_folders(refresh=True) if folder.get("name")}
        
        # Créer ou mettre à jour chaque dossier indépendamment
        for folder_name, new_flow_ids in folder_flows.items():
            if not new_flow_ids:
                logging.warning(f"Aucun flow trouvé pour le dossier {folder_name}")
                continue
            
            # Vérifier si le dossier existe déjà
            existing_folder = existing_folders.get(folder_name)
            
            if existing_folder:
                # Récupérer les flows existants dans ce dossier
                folder_id = existing_folder["id"]
                folder_details = self.client.get_folder_by_id(folder_id)
                
                if folder_details and "flows" in folder_details:
                    # Récupérer les IDs des flows existants
                    existing_flow_ids = [flow["id"] for flow in folder_details["flows"]]
                    
                    # Combiner les flows existants avec les nouveaux flows
                    # en évitant les doublons
                    combined_flow_ids = list(set(existing_flow_ids + new_flow_ids))
                    
                    # Mettre à jour le dossier avec la liste combinée
                    success, _ = self.add_flows_to_folder(folder_id, combined_flow_ids)
                    if success:
                        logging.info(f"Flows ajoutés au dossier existant '{folder_name}' (ID: {folder_id}), préservant {len(existing_flow_ids)} flows existants")
                        organized_folders[folder_name] = combined_flow_ids
                    else:
                        logging.error(f"Échec de l'ajout des flows au dossier '{folder_name}'")
                else:
                    # Si nous ne pouvons pas récupérer les flows existants, utiliser uniquement les nouveaux
                    success, _ = self.add_flows_to_folder(folder_id, new_flow_ids)
                    if success:
                        logging.info(f"Flows ajoutés au dossier existant '{folder_name}' (ID: {folder_id})")
                        organized_folders[folder_name] = new_flow_ids
                    else:
                        logging.error(f"Échec de l'ajout des flows au dossier '{folder_name}'")
            else:
                # Créer un nouveau dossier
                success, folder_id, _ = self.create_folder(
                    folder_name,
                    description=f"Dossier pour les flows {folder_name}",
                    flows_list=new_flow_ids
                )
                if success and folder_id:
                    logging.info(f"Dossier '{folder_name}' créé avec les flows (ID: {folder_id})")
                    organized_folders[folder_name] = new_flow_ids
                else:
                    logging.error(f"Échec de la création du dossier '{folder_name}'")
        
        return organized_folders
    
    def delete_empty_folders(self) -> List[str]:
        """
        Supprime tous les dossiers vides dans Langflow.
        
        Returns:
            List[str]: Liste des noms des dossiers supprimés.
        """
        deleted_folders = []
        
        # Récupérer tous les dossiers
        folders = self._get_all_folders(refresh=True)
        
        for folder in folders:
            folder_id = folder.get("id")
            folder_name = folder.get("name")
            
            if not folder_id or not folder_name:
                continue
            
            # Récupérer les détails du dossier pour vérifier s'il est vide
            folder_details = self.client.get_folder_by_id(folder_id)
            
            if not folder_details:
                continue
            
            # Vérifier si le dossier est vide (pas de flows ni de composants)
            has_flows = folder_details.get("flows", [])
            has_components = folder_details.get("components", [])
            
            if not has_flows and not has_components:
                # Supprimer le dossier vide
                try:
                    url = f"{self.client.base_url}/api/v1/folders/{folder_id}"
                    response = requests.delete(url, headers=self.client.headers)
                    
                    if response.status_code in [200, 204]:
                        logging.info(f"Dossier vide '{folder_name}' (ID: {folder_id}) supprimé avec succès")
                        deleted_folders.append(folder_name)
                    else:
                        logging.error(f"Échec de la suppression du dossier vide '{folder_name}' (ID: {folder_id}): {response.status_code}")
                except Exception as e:
                    logging.error(f"Erreur lors de la suppression du dossier vide '{folder_name}' (ID: {folder_id}): {e}")
        
        return deleted_folders

# Fonctions utilitaires
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
        return path_parts[2]
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

def parse_args() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Arguments parsés.
    """
    parser = argparse.ArgumentParser(
        description="Synchronise les flows Langflow entre un dépôt Git et une instance Langflow."
    )
    parser.add_argument(
        "--langflow-url",
        help="URL de l'instance Langflow (par défaut: http://localhost:7860)",
    )
    parser.add_argument(
        "--api-token",
        help="Token d'API pour l'authentification Langflow",
    )
    parser.add_argument(
        "--repo-path",
        help="Chemin vers le dépôt Git local (par défaut: répertoire courant)",
    )
    parser.add_argument(
        "--before-commit",
        help="Commit de référence pour la comparaison (avant)",
    )
    parser.add_argument(
        "--after-commit",
        help="Commit de référence pour la comparaison (après)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Active le mode verbeux pour le logging",
    )
    return parser.parse_args()

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
    logger = setup_logging(config.verbose)
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
    
    # Supprimer les dossiers vides
    logger.info("Suppression des dossiers vides...")
    deleted_folders = folder_manager.delete_empty_folders()
    if deleted_folders:
        logger.info(f"Dossiers vides supprimés: {len(deleted_folders)}")
        for folder_name in deleted_folders:
            logger.info(f"  - {folder_name}")
    else:
        logger.info("Aucun dossier vide à supprimer")
    
    # Résumé des opérations
    logger.info("Résumé de la synchronisation:")
    logger.info(f"  - Flows ajoutés: {len(added_flows)}")
    logger.info(f"  - Flows modifiés: {len(modified_flows)}")
    logger.info(f"  - Flows supprimés: {len(deleted_flows)}")
    logger.info(f"  - Dossiers vides supprimés: {len(deleted_folders)}")
    
    logger.info("Synchronisation terminée avec succès")

if __name__ == "__main__":
    main()
