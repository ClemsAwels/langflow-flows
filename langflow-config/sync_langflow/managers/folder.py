import logging
import os
from typing import Dict, List, Optional, Tuple, Any

from ..clients.langflow import LangflowClient
# Correction: Importer les deux fonctions utilitaires
from ..utils import extract_folder_name_from_path, extract_flow_name_from_path

logger = logging.getLogger("sync_app")

class FolderManager:
    """Gestionnaire pour les opérations sur les dossiers Langflow."""

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
        Récupère tous les dossiers (avec cache).
        
        Args:
            refresh: Si True, force la récupération des dossiers depuis l\"API.
            
        Returns:
            List[Dict[str, Any]]: Liste des dossiers.
        """
        if self._folders_cache is None or refresh:
            logger.debug("Mise à jour du cache des dossiers...")
            self._folders_cache = self.client.get_folders()
        return self._folders_cache
    
    def find_folder_by_name(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """
        Recherche un dossier par son nom (utilise le cache).
        
        Args:
            folder_name: Nom du dossier.
            
        Returns:
            Optional[Dict[str, Any]]: Données du dossier ou None si non trouvé.
        """
        folders = self._get_all_folders()
        
        for folder in folders:
            if folder.get("name") == folder_name:
                return folder
        
        # Si non trouvé dans le cache, rafraîchir et réessayer
        logger.debug(f"Dossier 	{folder_name}	 non trouvé dans le cache, rafraîchissement...")
        folders = self._get_all_folders(refresh=True)
        for folder in folders:
            if folder.get("name") == folder_name:
                return folder
                
        logger.debug(f"Dossier 	{folder_name}	 non trouvé même après rafraîchissement.")
        return None
    
    def create_folder(self, folder_name: str, description: str = "", flows_list: List[str] = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Crée un nouveau dossier.
        
        Args:
            folder_name: Nom du dossier.
            description: Description du dossier.
            flows_list: Liste des IDs de flows à ajouter au dossier.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict[str, Any]]]: Tuple contenant un booléen indiquant le succès,
            l\"ID du dossier créé et les données du dossier.
        """
        # Préparer les données du dossier
        folder_data = {
            "name": folder_name,
            "description": description,
            "flows": flows_list or []
        }
        
        try:
            # Créer le dossier
            result = self.client.create_folder(folder_data)
            
            if result and "id" in result:
                folder_id = result["id"]
                logger.info(f"Dossier créé avec succès: {folder_name} (ID: {folder_id})")
                
                # Invalider le cache des dossiers
                self._folders_cache = None
                
                return True, folder_id, result
            else:
                logger.error(f"Échec de la création du dossier: {folder_name}")
                return False, None, None
        except Exception as e:
            logger.error(f"Erreur lors de la création du dossier {folder_name}: {e}")
            return False, None, None
    
    def add_flows_to_folder(self, folder_id: str, flow_ids: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Ajoute ou met à jour les flows d\"un dossier existant.
        
        Args:
            folder_id: ID du dossier.
            flow_ids: Liste complète des IDs de flows pour ce dossier.
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: Tuple contenant un booléen indiquant le succès et les données du dossier.
        """
        try:
            # Mettre à jour les flows du dossier
            folder_data = {
                "flows": flow_ids
            }
            
            # Mettre à jour le dossier
            result = self.client.update_folder(folder_id, folder_data)
            
            if result:
                logger.info(f"Flows mis à jour dans le dossier avec succès (ID: {folder_id})")
                
                # Invalider le cache des dossiers
                self._folders_cache = None
                
                return True, result
            else:
                logger.error(f"Échec de la mise à jour des flows dans le dossier (ID: {folder_id})")
                return False, None
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des flows dans le dossier {folder_id}: {e}")
            return False, None
    
    def organize_flows_by_folder(self, flow_paths: List[str], processed_flows: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Organise les flows traités en dossiers, crée ou met à jour les dossiers dans Langflow.
        
        Args:
            flow_paths: Liste des chemins relatifs des flows traités (ajoutés/modifiés).
            processed_flows: Dictionnaire des flows traités (ID -> données).
            
        Returns:
            Dict[str, List[str]]: Dictionnaire des dossiers organisés (nom -> liste d\"IDs de flows).
        """
        organized_folders = {}
        
        # Récupérer tous les dossiers existants une seule fois
        existing_folders_map = {folder.get("name"): folder for folder in self._get_all_folders(refresh=True) if folder.get("name")}
        
        # Créer un dictionnaire pour mapper les noms de flows à leurs IDs
        flow_name_to_id = {}
        for flow_id, flow_data in processed_flows.items():
            flow_name = flow_data.get("name")
            if flow_name:
                flow_name_to_id[flow_name] = flow_id
            else:
                # Fallback si le nom n\"est pas dans les données (devrait être rare)
                for path in flow_paths:
                    if extract_flow_name_from_path(path) == os.path.basename(flow_data.get("file_path", "")).replace(".json", ""): # Approximation
                        flow_name_to_id[extract_flow_name_from_path(path)] = flow_id
                        break
        logger.debug(f"Mapping nom de flow -> ID: {flow_name_to_id}")

        # Regrouper les flows par dossier à partir des chemins Git
        folder_flows_from_git = {}
        for flow_path in flow_paths:
            folder_name = extract_folder_name_from_path(flow_path)
            # Correction: Utiliser la fonction importée
            flow_name = extract_flow_name_from_path(flow_path)
            logger.debug(f"Chemin: {flow_path}, Dossier extrait: {folder_name}, Flow extrait: {flow_name}")
            
            if folder_name:
                if folder_name not in folder_flows_from_git:
                    folder_flows_from_git[folder_name] = []
                
                # Trouver l\"ID du flow correspondant au nom
                flow_id = flow_name_to_id.get(flow_name)
                if flow_id:
                    if flow_id not in folder_flows_from_git[folder_name]:
                        folder_flows_from_git[folder_name].append(flow_id)
                        logger.debug(f"  -> Ajout du flow ID {flow_id} au dossier {folder_name}")
                else:
                    logger.warning(f"Impossible de trouver l\"ID pour le flow 	{flow_name}	 dans le dossier 	{folder_name}	")
            else:
                logger.debug(f"  -> Flow 	{flow_name}	 n\"appartient à aucun dossier spécifique.")

        logger.debug(f"Flows regroupés par dossier depuis Git: {folder_flows_from_git}")

        # Traiter chaque dossier identifié dans Git
        for folder_name, git_flow_ids in folder_flows_from_git.items():
            logger.info(f"Traitement du dossier: {folder_name}")
            existing_folder = existing_folders_map.get(folder_name)
            
            if existing_folder:
                folder_id = existing_folder["id"]
                logger.info(f"  -> Dossier existant trouvé (ID: {folder_id})")
                
                # Récupérer les flows actuels du dossier depuis Langflow
                current_folder_details = self.client.get_folder_by_id(folder_id)
                current_flow_ids = set(current_folder_details.get("flows", [])) if current_folder_details else set()
                logger.debug(f"  -> Flows actuels dans le dossier Langflow: {current_flow_ids}")
                
                # Combiner les flows de Git avec les flows existants non modifiés
                # Note: processed_flows contient uniquement les flows ajoutés/modifiés dans ce commit
                # Il faut s\"assurer que les flows existants qui n\"ont PAS été modifiés restent dans le dossier
                final_flow_ids = set(git_flow_ids) # Commencer avec les flows de ce commit
                
                # Ajouter les flows existants qui ne sont pas dans processed_flows (donc non modifiés)
                for existing_flow_id in current_flow_ids:
                    if existing_flow_id not in processed_flows:
                        final_flow_ids.add(existing_flow_id)
                        logger.debug(f"  -> Préservation du flow existant non modifié: {existing_flow_id}")
                
                # S\"assurer que les flows supprimés sont bien retirés (géré par la logique de suppression de flow)
                # Ici, on met juste à jour la liste des flows pour le dossier
                final_flow_ids_list = list(final_flow_ids)
                logger.debug(f"  -> Liste finale des flows pour le dossier: {final_flow_ids_list}")
                
                # Mettre à jour le dossier avec la liste finale des flows
                success, _ = self.add_flows_to_folder(folder_id, final_flow_ids_list)
                if success:
                    organized_folders[folder_name] = final_flow_ids_list
            else:
                logger.info(f"  -> Dossier inexistant. Création du dossier...")
                # Créer le dossier avec les flows identifiés dans Git
                success, folder_id, _ = self.create_folder(folder_name, flows_list=git_flow_ids)
                if success and folder_id:
                    organized_folders[folder_name] = git_flow_ids
                    # Mettre à jour la map des dossiers existants pour les itérations suivantes (si nécessaire)
                    existing_folders_map[folder_name] = {"id": folder_id, "name": folder_name} 
        
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
            
            # Récupérer les détails du dossier pour vérifier s\"il est vide
            folder_details = self.client.get_folder_by_id(folder_id)
            
            if not folder_details:
                logger.warning(f"Impossible de récupérer les détails du dossier 	{folder_name}	 (ID: {folder_id}) pour vérifier s\"il est vide.")
                continue
            
            # Vérifier si le dossier est vide (pas de flows ni de composants)
            has_flows = folder_details.get("flows", [])
            has_components = folder_details.get("components", [])
            
            if not has_flows and not has_components:
                logger.info(f"Dossier 	{folder_name}	 (ID: {folder_id}) est vide. Tentative de suppression...")
                # Supprimer le dossier vide
                success = self.client.delete_folder(folder_id)
                if success:
                    logger.info(f"Dossier vide 	{folder_name}	 (ID: {folder_id}) supprimé avec succès")
                    deleted_folders.append(folder_name)
                    self._folders_cache = None # Invalider le cache
                else:
                    logger.error(f"Échec de la suppression du dossier vide 	{folder_name}	 (ID: {folder_id})")
            else:
                logger.debug(f"Dossier 	{folder_name}	 (ID: {folder_id}) n\"est pas vide.")
        
        return deleted_folders

