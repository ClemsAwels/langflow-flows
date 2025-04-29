import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Any # Ajout de Any

from ..clients.langflow import LangflowClient
from ..utils import extract_flow_name_from_path

logger = logging.getLogger("sync_app")

class FlowManager:
    """Gestionnaire pour les opérations sur les flows Langflow."""

    def __init__(self, client: LangflowClient):
        """
        Initialise le gestionnaire de flows.
        
        Args:
            client: Client API Langflow.
        """
        self.client = client
        self._flows_cache = None # Cache pour find_flow_by_name

    def _get_all_flows(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Récupère tous les flows (avec cache).
        
        Args:
            refresh: Si True, force la récupération des flows depuis l\"API.
            
        Returns:
            List[Dict[str, Any]]: Liste des flows.
        """
        if self._flows_cache is None or refresh:
            logger.debug("Mise à jour du cache des flows...")
            self._flows_cache = self.client.get_flows()
        return self._flows_cache

    def add_flow(self, flow_path: str, repo_path: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Ajoute un flow à Langflow.
        
        Args:
            flow_path: Chemin relatif du fichier de flow dans le dépôt.
            repo_path: Chemin absolu du dépôt Git.
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict[str, Any]]]: Tuple contenant un booléen indiquant le succès,
            l\"ID du flow créé et les données du flow.
        """
        # Construire le chemin complet du fichier
        full_path = os.path.join(repo_path, flow_path)
        
        # Vérifier que le fichier existe
        if not os.path.exists(full_path):
            logger.error(f"Le fichier de flow {full_path} n\"existe pas")
            return False, None, None
        
        try:
            # Lire le contenu du fichier
            with open(full_path, "r", encoding="utf-8") as file:
                flow_data = json.load(file)
            
            # Créer le flow
            result = self.client.create_flow(flow_data)
            
            if result and "id" in result:
                flow_id = result["id"]
                logger.info(f"Flow ajouté avec succès: {flow_path} (ID: {flow_id})")
                self._flows_cache = None # Invalider le cache
                return True, flow_id, result # Retourner les données complètes du flow créé
            else:
                logger.error(f"Échec de l\"ajout du flow: {flow_path}")
                return False, None, None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON pour le flow {flow_path}: {e}")
            return False, None, None
        except Exception as e:
            logger.error(f"Erreur lors de l\"ajout du flow {flow_path}: {e}")
            return False, None, None
    
    def update_flow(self, flow_id: str, flow_path: str, repo_path: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Met à jour un flow existant.
        
        Args:
            flow_id: ID du flow à mettre à jour.
            flow_path: Chemin relatif du fichier de flow dans le dépôt.
            repo_path: Chemin absolu du dépôt Git.
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: Tuple contenant un booléen indiquant le succès et les données du flow.
        """
        # Construire le chemin complet du fichier
        full_path = os.path.join(repo_path, flow_path)
        
        # Vérifier que le fichier existe
        if not os.path.exists(full_path):
            logger.error(f"Le fichier de flow {full_path} n\"existe pas")
            return False, None
        
        try:
            # Lire le contenu du fichier
            with open(full_path, "r", encoding="utf-8") as file:
                flow_data = json.load(file)
            
            # Mettre à jour le flow
            result = self.client.update_flow(flow_id, flow_data)
            
            if result:
                logger.info(f"Flow mis à jour avec succès: {flow_path} (ID: {flow_id})")
                self._flows_cache = None # Invalider le cache
                return True, result # Retourner les données complètes du flow mis à jour
            else:
                logger.error(f"Échec de la mise à jour du flow: {flow_path} (ID: {flow_id})")
                return False, None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON pour le flow {flow_path}: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du flow {flow_path} (ID: {flow_id}): {e}")
            return False, None
    
    def delete_flow(self, flow_id: str) -> bool:
        """
        Supprime un flow.
        
        Args:
            flow_id: ID du flow à supprimer.
            
        Returns:
            bool: True si la suppression a réussi, False sinon.
        """
        try:
            # Supprimer le flow
            result = self.client.delete_flow(flow_id)
            
            if result:
                logger.info(f"Flow supprimé avec succès (ID: {flow_id})")
                self._flows_cache = None # Invalider le cache
                return True
            else:
                logger.error(f"Échec de la suppression du flow (ID: {flow_id})")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du flow (ID: {flow_id}): {e}")
            return False
    
    def find_flow_by_name(self, flow_name: str) -> Optional[Dict[str, Any]]:
        """
        Recherche un flow par son nom (utilise le cache).
        
        Args:
            flow_name: Nom du flow.
            
        Returns:
            Optional[Dict[str, Any]]: Données du flow ou None si non trouvé.
        """
        try:
            # Utiliser le cache
            flows = self._get_all_flows()
            
            # Rechercher le flow par son nom
            for flow in flows:
                if flow.get("name") == flow_name:
                    return flow
            
            # Si non trouvé dans le cache, rafraîchir et réessayer
            logger.debug(f"Flow 	{flow_name}	 non trouvé dans le cache, rafraîchissement...")
            flows = self._get_all_flows(refresh=True)
            for flow in flows:
                if flow.get("name") == flow_name:
                    return flow
                    
            logger.debug(f"Flow 	{flow_name}	 non trouvé même après rafraîchissement.")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche du flow {flow_name}: {e}")
            return None
    
    def process_added_flows(self, flow_paths: List[str], repo_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Traite les flows ajoutés.
        
        Args:
            flow_paths: Liste des chemins relatifs des flows ajoutés.
            repo_path: Chemin absolu du dépôt Git.
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionnaire des flows ajoutés ou mis à jour (ID -> données).
        """
        processed_flows = {}
        
        for flow_path in flow_paths:
            flow_name = extract_flow_name_from_path(flow_path)
            logger.debug(f"Traitement du flow ajouté: {flow_path} (Nom extrait: {flow_name})")
            
            existing_flow = self.find_flow_by_name(flow_name)
            
            if existing_flow:
                flow_id = existing_flow["id"]
                logger.info(f"Flow 	{flow_name}	 (ajouté dans Git) existe déjà dans Langflow (ID: {flow_id}). Mise à jour...")
                success, flow_data = self.update_flow(flow_id, flow_path, repo_path)
                if success and flow_data:
                    processed_flows[flow_id] = flow_data
            else:
                logger.info(f"Flow 	{flow_name}	 (ajouté dans Git) n\"existe pas dans Langflow. Ajout...")
                success, flow_id, flow_data = self.add_flow(flow_path, repo_path)
                if success and flow_id and flow_data:
                    processed_flows[flow_id] = flow_data
        
        return processed_flows
    
    def process_modified_flows(self, flow_paths: List[str], repo_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Traite les flows modifiés.
        
        Args:
            flow_paths: Liste des chemins relatifs des flows modifiés.
            repo_path: Chemin absolu du dépôt Git.
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionnaire des flows modifiés ou ajoutés (ID -> données).
        """
        processed_flows = {}
        
        for flow_path in flow_paths:
            flow_name = extract_flow_name_from_path(flow_path)
            logger.debug(f"Traitement du flow modifié: {flow_path} (Nom extrait: {flow_name})")
            
            existing_flow = self.find_flow_by_name(flow_name)
            
            if existing_flow:
                flow_id = existing_flow["id"]
                logger.info(f"Flow 	{flow_name}	 (modifié dans Git) existe dans Langflow (ID: {flow_id}). Mise à jour...")
                success, flow_data = self.update_flow(flow_id, flow_path, repo_path)
                if success and flow_data:
                    processed_flows[flow_id] = flow_data
            else:
                logger.warning(f"Flow 	{flow_name}	 (modifié dans Git) n\"existe pas dans Langflow. Tentative d\"ajout...")
                success, flow_id, flow_data = self.add_flow(flow_path, repo_path)
                if success and flow_id and flow_data:
                    processed_flows[flow_id] = flow_data
        
        return processed_flows
    
    def process_deleted_flows(self, flow_paths: List[str]) -> List[str]:
        """
        Traite les flows supprimés.
        
        Args:
            flow_paths: Liste des chemins relatifs des flows supprimés.
            
        Returns:
            List[str]: Liste des IDs des flows supprimés avec succès.
        """
        deleted_flow_ids = []
        
        for flow_path in flow_paths:
            flow_name = extract_flow_name_from_path(flow_path)
            logger.debug(f"Traitement du flow supprimé: {flow_path} (Nom extrait: {flow_name})")
            
            existing_flow = self.find_flow_by_name(flow_name)
            
            if existing_flow:
                flow_id = existing_flow["id"]
                logger.info(f"Flow 	{flow_name}	 (supprimé dans Git) existe dans Langflow (ID: {flow_id}). Suppression...")
                success = self.delete_flow(flow_id)
                if success:
                    deleted_flow_ids.append(flow_id)
            else:
                logger.warning(f"Flow 	{flow_name}	 (supprimé dans Git) n\"existe pas dans Langflow. Suppression ignorée.")
        
        return deleted_flow_ids

