"""
Client API pour interagir avec l'API Langflow.
Encapsule toutes les opérations API (GET, POST, PATCH, DELETE).
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Union, Tuple

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


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
            logger.error(error_msg)
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
            logger.error(f"Erreur lors de la récupération des flows: {e}")
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
            logger.error(f"Erreur lors de la récupération du flow {flow_id}: {e}")
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
            logger.error(f"Erreur lors de la création du flow: {e}")
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
            logger.error(f"Erreur lors de la mise à jour du flow {flow_id}: {e}")
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
            logger.error(f"Erreur lors de la suppression du flow {flow_id}: {e}")
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
            logger.error(f"Erreur lors de la récupération des dossiers: {e}")
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
            logger.error(f"Erreur lors de la récupération du dossier {folder_id}: {e}")
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
            logger.error(f"Erreur lors de la création du dossier: {e}")
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
            logger.error(f"Erreur lors de la mise à jour du dossier {folder_id}: {e}")
            return None
    
    def upload_flow_file(self, file_path: str, folder_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Télécharge un fichier de flow.
        
        Args:
            file_path: Chemin vers le fichier de flow.
            folder_id: ID du dossier cible (optionnel).
            
        Returns:
            Optional[Dict[str, Any]]: Données du flow téléchargé ou None en cas d'erreur.
        """
        url = f"{self.base_url}/api/v1/flows/upload/"
        
        if folder_id:
            url += f"?folder_id={folder_id}"
        
        headers = {
            "accept": "application/json",
        }
        
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        try:
            with open(file_path, "rb") as file:
                files = {"file": (os.path.basename(file_path), file, "application/json")}
                response = requests.post(url, headers=headers, files=files)
                return self._handle_response(response)
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement du fichier {file_path}: {e}")
            return None
