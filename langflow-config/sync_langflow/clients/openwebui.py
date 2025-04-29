import logging
import os
import json
import re
import requests
from typing import Dict, List, Any, Optional, Tuple
from requests.exceptions import RequestException

logger = logging.getLogger("sync_app")

class OpenWebUIManager:
    """Gestionnaire pour l'intégration avec OpenWebUI."""

    def __init__(self, base_url: str, api_key: str, template_path: Optional[str] = None, valve_langflow_api_url: str = None):
        """
        Initialise le gestionnaire OpenWebUI.
        
        Args:
            base_url: URL de base de l'API OpenWebUI.
            api_key: Clé API pour l'authentification OpenWebUI.
            template_path: Chemin vers le template de pipeline (optionnel).
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.template_path = template_path
        self.template_content = None
        self.valve_langflow_api_url = valve_langflow_api_url
        
        # Charger le template s'il est spécifié
        if template_path and os.path.exists(template_path):
            try:
                with open(template_path, "r", encoding="utf-8") as file:
                    self.template_content = file.read()
                logger.info(f"Template de pipeline chargé depuis {template_path}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du template de pipeline: {e}")
                # Utiliser le template par défaut en cas d'erreur de chargement
                self.template_content = self._get_default_template()
                logger.warning("Utilisation du template de pipeline par défaut suite à une erreur de chargement.")
        else:
            # Utiliser le template par défaut
            self.template_content = self._get_default_template()
            logger.info("Utilisation du template de pipeline par défaut")
    
    def _get_default_template(self) -> str:
        """
        Retourne le template de pipeline par défaut.
        
        Returns:
            str: Contenu du template par défaut.
        """
        # Template complet avec les placeholders
        return '''from typing import List, Union, Generator, Iterator, Annotated, Any, Optional, Callable, Awaitable
from pydantic import BaseModel
import requests
import json
import os 

class Pipeline:
    class Valves(BaseModel):
        BASE_API_URL: str = "VALVE_LANGFLOW_API_URL_PLACEHOLDER"
        ENDPOINT: str = "ENDPOINT_PLACEHOLDER"  # The endpoint name of the flow
        # Default tweaks for the Langflow components
        TWEAKS: dict = {}

    def __init__(self):
        self.name = "FLOW_NAME_PLACEHOLDER"
        self.valves = self.Valves()
        
    async def on_startup(self):
        print(f"on_startup:{__name__}")

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        
    def emit_event_safe(self, message):
        event_data = {
            "type": "message",
            "data": {"content": message + "\\n"},
        }
        try:
            self.event_emitter(event_data)
        except Exception as e:
            print("Error emitting event:", e)

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")

        # Extract the latest user message
        if messages and len(messages) > 0:
            user_message = messages[-1].get("content", "")
        
        print(f"Processing user message: {user_message}")
        
        # Call the Langflow API
        try:
            response = self.run_flow(
                message=user_message,
                endpoint=self.valves.ENDPOINT or self.valves.FLOW_ID,
                tweaks=self.valves.TWEAKS
            )
            
            print(f"Langflow response received")
            
            # Extract the response content
            if body.get("stream"):
                # For streaming responses
                text = self.extract_text_from_response(response)
                if text:
                    print(f"Streaming text extracted: {text[:100]}...")
                    yield text
                else:
                    print("No text found in streaming response")
                    yield json.dumps(response, indent=2)
            else:
                # For non-streaming responses
                text = self.extract_text_from_response(response)
                if text:
                    print(f"Text extracted: {text[:100]}...")
                    return text
                else:
                    print("No text found in response")
                    return json.dumps(response, indent=2)
                
        except Exception as e:
            error_message = f"Error calling Langflow API: {str(e)}"
            print(error_message)
            return error_message
    
    def extract_text_from_response(self, response_json):
        """
        Extracts the text content from the response JSON.
        """
        try:
            # Navigate through the nested JSON structure
            if "outputs" in response_json:
                outputs = response_json["outputs"]
                if outputs and len(outputs) > 0:
                    inner_outputs = outputs[0].get("outputs", [])
                    if inner_outputs and len(inner_outputs) > 0:
                        results = inner_outputs[0].get("results", {})
                        message = results.get("message", {})
                        data = message.get("data", {})
                        
                        # Get the raw text content
                        text = data.get("text", "")
                        
                        # If the text starts with "extract only text" or similar prefixes, remove them
                        if text.lower().startswith("extract only text"):
                            # Find the position after this prefix
                            pos = text.lower().find("extract only text") + len("extract only text")
                            # Return everything after this position, trimming whitespace
                            return text[pos:].strip()
                        
                        return text
            
            # If we can't find the text in the expected structure, try a more flexible approach
            return self.find_text_in_json(response_json)
        except Exception as e:
            print(f"Error extracting text: {e}")
            return None
    
    def find_text_in_json(self, json_obj):
        """
        Recursively search for a 'text' key in a nested JSON object and extract only what follows.
        """
        if isinstance(json_obj, dict):
            # If this is a dictionary, check if it has a 'text' key
            if "text" in json_obj:
                text = json_obj["text"]
                # If the text starts with "extract only text" or similar prefixes, remove them
                if text.lower().startswith("extract only text"):
                    # Find the position after this prefix
                    pos = text.lower().find("extract only text") + len("extract only text")
                    # Return everything after this position, trimming whitespace
                    return text[pos:].strip()
                return text
            
            # Otherwise, search in all values
            for value in json_obj.values():
                result = self.find_text_in_json(value)
                if result:
                    return result
        
        # If this is a list, search in all elements
        elif isinstance(json_obj, list):
            for item in json_obj:
                result = self.find_text_in_json(item)
                if result:
                    return result
        
        # If we didn't find anything, return None
        return None
    
    def run_flow(self, 
                message: str,
                endpoint: str,
                output_type: str = "chat",
                input_type: str = "chat",
                tweaks: Optional[dict] = None,
                api_key: Optional[str] = None) -> dict:
        """
        Run a Langflow workflow with a given message and optional tweaks.

        :param message: The message to send to the flow
        :param endpoint: The ID or the endpoint name of the flow
        :param output_type: The output type (default: chat)
        :param input_type: The input type (default: chat)
        :param tweaks: Optional tweaks to customize the flow
        :param api_key: Optional API key for authentication
        :return: The JSON response from the flow
        """
        api_url = f"{self.valves.BASE_API_URL}/api/v1/run/{endpoint}"

        payload = {
            "input_value": message,
            "output_type": output_type,
            "input_type": input_type,
        }
        
        headers = {"Content-Type": "application/json"}
        
        if tweaks:
            payload["tweaks"] = tweaks
            
        if api_key:
            headers["x-api-key"] = api_key
            
        print(f"Calling Langflow API at {api_url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(api_url, json=payload, headers=headers)
        
        # Check if the request was successful
        response.raise_for_status()
        
        return response.json()
'''
    
    def extract_flow_info(self, flow_data: Dict[str, Any], flow_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrait les informations nécessaires d'un flow Langflow.
        
        Args:
            flow_data: Données du flow.
            flow_path: Chemin du fichier de flow.
            
        Returns:
            Tuple[Optional[str], Optional[str]]: Tuple contenant endpoint_name et name.
        """
        # Extraire le nom du flow
        flow_name = flow_data.get("name")
        
        # Si le nom n'est pas disponible, utiliser le nom du fichier
        if not flow_name:
            flow_name = os.path.basename(flow_path).replace(".json", "")

        endpoint_name = flow_data.get("endpoint_name")
        if not endpoint_name:
            # Si endpoint_name n'est pas disponible, utiliser le nom du flow
            endpoint_name = flow_name.lower().replace(" ", "_")
            logger.warning(f"Endpoint name non trouvé pour le flow '{flow_name}', utilisation de '{endpoint_name}' comme fallback")
        
        return endpoint_name, flow_name
    
    def generate_pipeline(self, endpoint_name: str, flow_name: str, output_dir: str) -> Optional[str]:
        """
        Génère un fichier de pipeline basé sur le template.
        
        Args:
            endpoint_name: Nom de l'endpoint du flow.
            flow_name: Nom du flow.
            output_dir: Répertoire de sortie pour le fichier généré.
            
        Returns:
            Optional[str]: Chemin du fichier généré ou None en cas d'erreur.
        """
        if not self.template_content:
            logger.error("Template de pipeline non disponible pour la génération.")
            return None
        
        try:
            # Remplacer les placeholders dans le template
            pipeline_content = self.template_content.replace("ENDPOINT_PLACEHOLDER", endpoint_name)
            pipeline_content = pipeline_content.replace("FLOW_NAME_PLACEHOLDER", flow_name)

            # Utiliser self.valve_langflow_api_url ou la valeur par défaut
            api_url = self.valve_langflow_api_url or "http://langflowaa:7860"
            pipeline_content = pipeline_content.replace("VALVE_LANGFLOW_API_URL_PLACEHOLDER", api_url)
            
            # Créer le nom du fichier
            # Convertir le nom du flow en un nom de fichier valide
            file_name = flow_name.lower().replace(" ", "_").replace("-", "_")
            # S'assurer que le nom de fichier est valide (supprimer les caractères non alphanumériques)
            file_name = "".join(c for c in file_name if c.isalnum() or c == '_')
            if not file_name:
                file_name = "default_pipeline" # Fallback si le nom devient vide
                
            if not file_name.endswith(".py"):
                file_name += ".py"
            
            # Créer le chemin complet du fichier
            file_path = os.path.join(output_dir, file_name)
            
            # Écrire le contenu dans le fichier
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(pipeline_content)
            logger.info(f"Pipeline généré: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Erreur lors de la génération du pipeline pour {flow_name}: {e}")
            return None
    
    def upload_pipeline(self, pipeline_path: str, url_idx: int = 1) -> bool:
        """
        Télécharge un pipeline vers OpenWebUI.
        
        Args:
            pipeline_path: Chemin du fichier de pipeline.
            url_idx: Index de l'URL (par défaut: 1).
            
        Returns:
            bool: True si le téléchargement a réussi, False sinon.
        """
        if not os.path.exists(pipeline_path):
            logger.error(f"Le fichier de pipeline {pipeline_path} n'existe pas pour le téléchargement.")
            return False
        
        # Préparer l'URL de l'API
        api_url = f"{self.base_url}/api/v1/pipelines/upload"
        
        # Préparer les en-têtes
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        # Préparer les fichiers
        file_name = os.path.basename(pipeline_path)
        try:
            with open(pipeline_path, "rb") as file_content:
                files = {
                    "file": (file_name, file_content),
                }
                
                # Préparer les données
                data = {
                    "urlIdx": url_idx
                }
                
                logger.info(f"Téléchargement du pipeline {file_name} vers {api_url}...")
                # Envoyer la requête
                response = requests.post(api_url, headers=headers, files=files, data=data)
                
                # Vérifier si la requête a réussi
                if response.status_code == 200:
                    logger.info(f"Pipeline {file_name} téléchargé avec succès vers OpenWebUI")
                    logger.debug(f"Réponse: {response.json()}")
                    return True
                else:
                    logger.error(f"Erreur {response.status_code} lors du téléchargement du pipeline {file_name}: {response.text}")
                    return False
        except RequestException as e:
            logger.error(f"Erreur réseau lors du téléchargement du pipeline {file_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors du téléchargement du pipeline {file_name}: {e}")
            return False
        
    def delete_unused_pipelines(self, used_endpoints: List[str]) -> Tuple[int, List[str]]:
        """
        Supprime les pipelines dans OpenWebUI qui ont des endpoints qui ne sont pas utilisés 
        par les flows Langflow.
        
        Args:
            used_endpoints: Liste des endpoints actuellement utilisés par les flows Langflow.
            
        Returns:
            Tuple[int, List[str]]: Nombre de pipelines supprimés et liste de leurs noms.
        """
        deleted_pipelines = []
        deleted_count = 0
        
        # Récupérer tous les pipelines existants
        all_pipelines = self.get_all_pipelines()
        
        if not all_pipelines:
            logger.warning("Aucun pipeline trouvé dans OpenWebUI ou erreur lors de la récupération.")
            return 0, []
        
        # Création d'un ensemble pour les recherches plus rapides
        used_endpoints_set = set(used_endpoints)
        
        for pipeline in all_pipelines:
            pipeline_id = pipeline.get("id")
            pipeline_name = pipeline.get("name", "")
            pipeline_file = pipeline.get("filepath", "")
            
            # Extraire l'endpoint du fichier de pipeline
            pipeline_endpoint = None
            try:
                if pipeline_file and os.path.exists(pipeline_file):
                    with open(pipeline_file, "r", encoding="utf-8") as file:
                        content = file.read()
                        endpoint_match = re.search(r'ENDPOINT\s*=\s*["\']([^"\']+)["\']', content)
                        if endpoint_match:
                            pipeline_endpoint = endpoint_match.group(1)
            except Exception as e:
                logger.error(f"Erreur lors de la lecture du fichier pipeline '{pipeline_file}': {e}")
            
            # Si nous n'avons pas pu extraire l'endpoint du fichier, essayer depuis les métadonnées
            if not pipeline_endpoint and "metadata" in pipeline:
                metadata = pipeline.get("metadata", {})
                pipeline_endpoint = metadata.get("endpoint")
            
            # Si nous avons un endpoint et qu'il n'est pas dans la liste des endpoints utilisés
            if pipeline_endpoint and pipeline_endpoint not in used_endpoints_set:
                logger.info(f"Suppression du pipeline '{pipeline_name}' avec endpoint '{pipeline_endpoint}' non utilisé.")
                if self.delete_pipeline(pipeline_id):
                    deleted_count += 1
                    deleted_pipelines.append(f"{pipeline_name} (endpoint: {pipeline_endpoint})")
        
        return deleted_count, deleted_pipelines

    def get_all_pipelines(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste de tous les pipelines depuis OpenWebUI.
        
        Returns:
            List[Dict[str, Any]]: Liste des pipelines avec leurs informations.
        """
        # Préparer l'URL de l'API
        api_url = f"{self.base_url}/api/v1/pipelines"
        
        # Préparer les en-têtes
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        try:
            logger.info(f"Récupération de tous les pipelines depuis {api_url}...")
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                pipelines = response.json()
                logger.info(f"Récupération réussie de {len(pipelines)} pipelines depuis OpenWebUI")
                return pipelines
            else:
                logger.error(f"Erreur {response.status_code} lors de la récupération des pipelines: {response.text}")
                return []
        except RequestException as e:
            logger.error(f"Erreur réseau lors de la récupération des pipelines: {e}")
            return []
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération des pipelines: {e}")
            return []

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """
        Supprime un pipeline spécifique dans OpenWebUI.
        
        Args:
            pipeline_id: ID du pipeline à supprimer.
            
        Returns:
            bool: True si la suppression a réussi, False sinon.
        """
        if not pipeline_id:
            logger.error("ID de pipeline non fourni pour la suppression.")
            return False
        
        # Préparer l'URL de l'API
        api_url = f"{self.base_url}/api/v1/pipelines/{pipeline_id}"
        
        # Préparer les en-têtes
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        try:
            logger.info(f"Suppression du pipeline avec ID {pipeline_id}...")
            response = requests.delete(api_url, headers=headers)
            
            if response.status_code in [200, 204]:
                logger.info(f"Pipeline {pipeline_id} supprimé avec succès")
                return True
            else:
                logger.error(f"Erreur {response.status_code} lors de la suppression du pipeline {pipeline_id}: {response.text}")
                return False
        except RequestException as e:
            logger.error(f"Erreur réseau lors de la suppression du pipeline {pipeline_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression du pipeline {pipeline_id}: {e}")
            return False

