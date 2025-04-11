"""
Module pour interagir avec Git et détecter les changements.
Identifie les fichiers ajoutés, modifiés et supprimés.
"""

import logging
import os
import subprocess
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


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
            logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"Erreur lors de l'exécution de la commande Git: {e}"
            logger.error(error_message)
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
    
    def get_file_content(self, file_path: str, commit: Optional[str] = None) -> Optional[str]:
        """
        Récupère le contenu d'un fichier à un commit spécifique.
        
        Args:
            file_path: Chemin du fichier.
            commit: Commit spécifique (optionnel, utilise HEAD par défaut).
            
        Returns:
            Optional[str]: Contenu du fichier ou None en cas d'erreur.
        """
        # Construire la commande Git
        command = ["show"]
        if commit:
            command.append(f"{commit}:{file_path}")
        else:
            command.append(f"HEAD:{file_path}")
        
        # Exécuter la commande
        success, output = self._run_git_command(command)
        if not success:
            logger.error(f"Impossible de récupérer le contenu du fichier {file_path}.")
            return None
        
        return output
    
    