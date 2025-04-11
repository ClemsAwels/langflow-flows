"""
Module de configuration pour la synchronisation Langflow.
Gère les variables d'environnement et les paramètres de configuration.
"""

import os
import argparse
from typing import Dict, Any, Optional


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
