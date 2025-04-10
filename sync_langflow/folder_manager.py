"""
Module pour gérer les dossiers Langflow.
Crée des dossiers et organise les flows dans les dossiers.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Tuple

# Import relatif
from .langflow_client import LangflowClient

logger = logging.getLogger(__name__)


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
                logger.info(f"Le dossier '{folder_name}' existe déjà (ID: {existing_folder.get('id')})")
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
                logger.info(f"Dossier '{folder_name}' créé avec succès (ID: {result.get('id')})")
                # Mettre à jour le cache
                self._folders_cache = None
                return True, result.get("id"), result
            else:
                return False, "Échec de la création du dossier", None
        except Exception as e:
            error_msg = f"Erreur lors de la création du dossier {folder_name}: {e}"
            logger.error(error_msg)
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
                logger.info(f"Dossier '{folder_data.get('name', folder_id)}' mis à jour avec succès")
                # Mettre à jour le cache
                self._folders_cache = None
                return True, result
            else:
                return False, None
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du dossier {folder_id}: {e}")
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
                logger.error(f"Dossier avec ID {folder_id} non trouvé")
                return False, None
            
            # Mettre à jour la liste des flows
            update_data = {
                "flows": flow_ids
            }
            
            # Mettre à jour le dossier
            return self.update_folder(folder_id, update_data)
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de flows au dossier {folder_id}: {e}")
            return False, None
    
    def organize_flows_by_folder(self, flow_paths: List[str], flow_ids: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Organise les flows en dossiers basés sur leur chemin, en préservant les flows existants.
        
        Args:
            flow_paths: Liste des chemins de flows modifiés/ajoutés.
            flow_ids: Dictionnaire des flows ajoutés/modifiés (ID -> données).
            
        Returns:
            Dict[str, List[str]]: Dictionnaire des dossiers créés/mis à jour (nom -> liste d'IDs).
        """
        # Initialiser le résultat
        organized_folders = {}
        
        # Regrouper les flows modifiés/ajoutés par dossier
        folder_flows = {}
        for flow_path in flow_paths:
            # Extraire le nom du dossier à partir du chemin (exemple: flows/excel/flow.json -> excel)
            path_parts = flow_path.split(os.sep)
            if len(path_parts) >= 2:
                folder_name = path_parts[1]  # flows/folder_name/...
                
                # Initialiser la liste des flows pour ce dossier si nécessaire
                if folder_name not in folder_flows:
                    folder_flows[folder_name] = []
                
                # Extraire le nom du flow à partir du chemin
                flow_name = os.path.basename(flow_path).replace(".json", "")
                
                # Ajouter le flow à la liste du dossier
                for flow_id, flow_data in flow_ids.items():
                    if flow_data.get("name") == flow_name:
                        folder_flows[folder_name].append(flow_id)
                        break
        
        # Créer ou mettre à jour les dossiers
        for folder_name, new_flow_ids in folder_flows.items():
            if not new_flow_ids:
                logging.warning(f"Aucun flow trouvé pour le dossier {folder_name}")
                continue
            
            # Vérifier si le dossier existe déjà
            existing_folder = self.find_folder_by_name(folder_name)
            
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
