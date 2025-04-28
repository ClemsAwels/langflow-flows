import argparse
import os
from typing import Dict, Any, Optional

class Config:
    """Classe de configuration pour la synchronisation Langflow et OpenWebUI."""

    def __init__(self):
        """Initialise la configuration avec les valeurs par défaut."""
        # Configuration Langflow
        self.langflow_url = "http://localhost:7860"
        self.api_token = None
        self.repo_path = os.getcwd()
        self.before_commit = None
        self.after_commit = None
        self.verbose = False
        
        # Configuration OpenWebUI
        self.openwebui_url = "http://localhost:3000"
        self.openwebui_api_key = None
        self.enable_openwebui = False
        self.openwebui_template_path = None

    def load_from_env(self) -> None:
        """Charge la configuration à partir des variables d'environnement."""
        # Configuration Langflow
        self.langflow_url = os.environ.get("LANGFLOW_URL", self.langflow_url)
        self.api_token = os.environ.get("LANGFLOW_API_TOKEN", self.api_token)
        self.repo_path = os.environ.get("REPO_PATH", self.repo_path)
        self.before_commit = os.environ.get("BEFORE_COMMIT", self.before_commit)
        self.after_commit = os.environ.get("AFTER_COMMIT", self.after_commit)
        self.verbose = os.environ.get("VERBOSE", "False").lower() == "true"
        
        # Configuration OpenWebUI
        self.openwebui_url = os.environ.get("OPENWEBUI_URL", self.openwebui_url)
        self.openwebui_api_key = os.environ.get("OPENWEBUI_API_KEY", self.openwebui_api_key)
        self.enable_openwebui = os.environ.get("ENABLE_OPENWEBUI", "False").lower() == "true"
        self.openwebui_template_path = os.environ.get("OPENWEBUI_TEMPLATE_PATH", self.openwebui_template_path)

    def load_from_args(self, args: argparse.Namespace) -> None:
        """
        Charge la configuration à partir des arguments de ligne de commande.
        
        Args:
            args: Arguments de ligne de commande parsés.
        """
        # Configuration Langflow
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
        
        # Configuration OpenWebUI
        if args.openwebui_url:
            self.openwebui_url = args.openwebui_url
        if args.openwebui_api_key:
            self.openwebui_api_key = args.openwebui_api_key
        if args.enable_openwebui:
            self.enable_openwebui = args.enable_openwebui
        if args.openwebui_template_path:
            self.openwebui_template_path = args.openwebui_template_path

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la configuration en dictionnaire.
        
        Returns:
            Dict[str, Any]: Configuration sous forme de dictionnaire.
        """
        return {
            # Configuration Langflow
            "langflow_url": self.langflow_url,
            "api_token": "***" if self.api_token else None,
            "repo_path": self.repo_path,
            "before_commit": self.before_commit,
            "after_commit": self.after_commit,
            "verbose": self.verbose,
            
            # Configuration OpenWebUI
            "openwebui_url": self.openwebui_url,
            "openwebui_api_key": "***" if self.openwebui_api_key else None,
            "enable_openwebui": self.enable_openwebui,
            "openwebui_template_path": self.openwebui_template_path
        }

    def validate(self) -> Optional[str]:
        """
        Valide la configuration.
        
        Returns:
            Optional[str]: Message d'erreur si la configuration est invalide, None sinon.
        """
        # Validation Langflow
        if not self.langflow_url:
            return "L'URL de Langflow est requise"
        
        # Vérifier que le chemin du dépôt existe
        if not os.path.exists(self.repo_path):
            return f"Le chemin du dépôt '{self.repo_path}' n'existe pas"
        
        # Vérifier que le chemin du dépôt est un dépôt Git
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            return f"Le chemin '{self.repo_path}' n'est pas un dépôt Git"
        
        # Validation OpenWebUI
        if self.enable_openwebui:
            if not self.openwebui_url:
                return "L'URL d'OpenWebUI est requise lorsque l'intégration est activée"
            
            if not self.openwebui_api_key:
                return "La clé API d'OpenWebUI est requise lorsque l'intégration est activée"
            
            if self.openwebui_template_path and not os.path.exists(self.openwebui_template_path):
                return f"Le chemin du template OpenWebUI '{self.openwebui_template_path}' n'existe pas"
        
        return None

