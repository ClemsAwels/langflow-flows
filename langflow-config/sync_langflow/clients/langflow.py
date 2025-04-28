import requests
import logging
from typing import Dict, List, Any, Optional
from requests.exceptions import RequestException

logger = logging.getLogger("sync_app")

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
            error_msg = f"Erreur API Langflow ({response.url}): {e}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_msg = f"Erreur API Langflow ({response.url}): {error_data['detail']}"
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
            "size": "50" # TODO: Gérer la pagination si nécessaire
        }
        
        if folder_id:
            params["folder_id"] = folder_id
            params["get_all"] = "false"
        
        url = f"{self.base_url}/api/v1/flows/"
        
        try:
            logger.debug(f"GET {url} avec params: {params}")
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
            logger.debug(f"GET {url}")
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
            logger.debug(f"POST {url}")
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
            logger.debug(f"PATCH {url}")
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
            logger.debug(f"DELETE {url}")
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
            logger.debug(f"GET {url}")
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
            logger.debug(f"GET {url}")
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
            logger.debug(f"POST {url}")
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
            logger.debug(f"PATCH {url}")
            response = requests.patch(url, headers=self.headers, json=folder_data)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du dossier {folder_id}: {e}")
            return None

    def delete_folder(self, folder_id: str) -> bool:
        """
        Supprime un dossier.

        Args:
            folder_id: ID du dossier à supprimer.

        Returns:
            bool: True si la suppression a réussi, False sinon.
        """
        url = f"{self.base_url}/api/v1/folders/{folder_id}"
        try:
            logger.debug(f"DELETE {url}")
            response = requests.delete(url, headers=self.headers)
            if response.status_code in [200, 204]:
                return True
            else:
                logger.error(f"Échec de la suppression du dossier (ID: {folder_id}): {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du dossier (ID: {folder_id}): {e}")
            return False

