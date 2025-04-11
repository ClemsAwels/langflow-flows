import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple

# Import relatif
from .langflow_client import LangflowClient

logger = logging.getLogger(__name__)


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
            flow_name = os.path.basename(file_path).replace(".json", "")
            
            # Vérifier si le flow existe déjà
            existing_flow = self.find_flow_by_name(flow_name)
            if existing_flow:
                logger.warning(f"Le flow '{flow_name}' existe déjà. Utilisation de la méthode de mise à jour.")
                return self.update_flow(existing_flow["id"], flow_data)
            
            # S'assurer que le nom est défini dans les données
            if "name" not in flow_data:
                flow_data["name"] = flow_name
            
            # Créer le flow
            result = self.client.create_flow(flow_data)
            if result:
                logger.info(f"Flow '{flow_name}' créé avec succès (ID: {result.get('id')})")
                # Mettre à jour le cache
                self._flows_cache = None
                return True, result.get("id"), result
            else:
                return False, "Échec de la création du flow", None
        except json.JSONDecodeError as e:
            error_msg = f"Erreur de décodage JSON pour le fichier {file_path}: {e}"
            logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Erreur lors de l'ajout du flow {file_path}: {e}"
            logger.error(error_msg)
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
                logger.info(f"Flow '{flow_data.get('name', flow_id)}' mis à jour avec succès")
                # Mettre à jour le cache
                self._flows_cache = None
                return True, flow_id, result
            else:
                return False, f"Échec de la mise à jour du flow {flow_id}", None
        except Exception as e:
            error_msg = f"Erreur lors de la mise à jour du flow {flow_id}: {e}"
            logger.error(error_msg)
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
            flow_name = os.path.basename(flow_path).replace(".json", "")
            
            # Trouver le flow par son nom
            flow = self.find_flow_by_name(flow_name)
            if not flow:
                return False, f"Flow '{flow_name}' non trouvé"
            
            # Supprimer le flow
            flow_id = flow["id"]
            success = self.client.delete_flow(flow_id)
            if success:
                logger.info(f"Flow '{flow_name}' (ID: {flow_id}) supprimé avec succès")
                # Mettre à jour le cache
                self._flows_cache = None
                return True, f"Flow '{flow_name}' supprimé avec succès"
            else:
                return False, f"Échec de la suppression du flow '{flow_name}'"
        except Exception as e:
            error_msg = f"Erreur lors de la suppression du flow {flow_path}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    """
    Analyse et correction des problèmes dans la méthode process_added_flows et process_modified_flows
    """

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
                    logger.info(f"Flow supprimé avec succès: {flow_path}")
                else:
                    logger.error(f"Échec de la suppression du flow {flow_path}: {message}")
            except Exception as e:
                logger.error(f"Erreur lors du traitement du flow supprimé {flow_path}: {e}")
        
        return successful_deletions
    
    """
    Analyse et correction des problèmes dans la méthode organize_flows_by_folder
    """

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
        
        # Regrouper les flows modifiés/ajoutés par dossier
        folder_flows = {}
        
        # Créer un dictionnaire pour mapper les noms de flows à leurs IDs
        flow_name_to_id = {}
        for flow_id, flow_data in flow_ids.items():
            flow_name = flow_data.get("name")
            if flow_name:
                flow_name_to_id[flow_name] = flow_id
        
        # Regrouper les flows par dossier
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

