import logging
import os
import subprocess
from typing import Dict, List, Tuple

logger = logging.getLogger("sync_app")

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
            # Correction: Échapper les guillemets internes ou utiliser des guillemets simples
            command_str = " ".join(full_command)
            logger.debug(f"Exécution de la commande Git: 	{command_str}	 dans {self.repo_path}")
            
            # Exécuter la commande dans le répertoire du dépôt
            result = subprocess.run(
                full_command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False, # Ne pas lever d'exception automatiquement
                encoding="utf-8"
            )
            
            if result.returncode != 0:
                logger.error(f"Erreur lors de l'exécution de la commande Git: {result.stderr}")
                return False, result.stderr
            
            logger.debug(f"Sortie de la commande Git: {result.stdout[:200]}...") # Log tronqué
            return True, result.stdout
        except FileNotFoundError:
            logger.error("Erreur: La commande 'git' n'a pas été trouvée. Assurez-vous que Git est installé et dans le PATH.")
            return False, "Commande 'git' non trouvée"
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'exécution de la commande Git: {e}")
            return False, str(e)
    
    def detect_changes(self, before_commit: str, after_commit: str) -> Dict[str, List[str]]:
        """
        Détecte les fichiers ajoutés, modifiés et supprimés entre deux commits.
        
        Args:
            before_commit: Commit de référence pour la comparaison (avant).
            after_commit: Commit de référence pour la comparaison (après).
            
        Returns:
            Dict[str, List[str]]: Dictionnaire contenant les listes de fichiers ajoutés, modifiés et supprimés,
            ainsi que les listes spécifiques aux flows.
        """
        changes = {
            "added": [],
            "modified": [],
            "deleted": [],
            "flows_added": [],
            "flows_modified": [],
            "flows_deleted": []
        }
        
        # Commande Git pour obtenir les différences de statut entre les commits
        # --name-status : Affiche seulement le nom du fichier et son statut
        # -M : Détecte les renommages (considérés comme suppression + ajout)
        # before_commit..after_commit : La plage de commits à comparer
        git_command = ["diff", "--name-status", "-M", f"{before_commit}..{after_commit}"]
        
        success, diff_output = self._run_git_command(git_command)
        
        if not success:
            logger.error(f"Impossible de détecter les changements entre {before_commit} et {after_commit}.")
            return changes
        
        # Analyser la sortie de git diff
        for line in diff_output.splitlines():
            if not line:
                continue
            
            # Format: <status><tab><file_path> ou R<score><tab><old_path><tab><new_path>
            parts = line.split("\t")
            
            if not parts:
                continue
                
            status_part = parts[0]
            status = status_part[0] # Prendre le premier caractère du statut (A, M, D, R)
            
            # Gérer les renommages (R) comme une suppression de l'ancien chemin et un ajout du nouveau
            if status == 'R' and len(parts) == 3:
                old_path = parts[1]
                new_path = parts[2]
                logger.debug(f"Renommage détecté: {old_path} -> {new_path}")
                
                # Traiter comme suppression de l'ancien chemin
                changes["deleted"].append(old_path)
                if old_path.endswith(".json") and ("langflow-config/flows/" in old_path or "/flows/" in old_path):
                    changes["flows_deleted"].append(old_path)
                    
                # Traiter comme ajout du nouveau chemin
                changes["added"].append(new_path)
                if new_path.endswith(".json") and ("langflow-config/flows/" in new_path or "/flows/" in new_path):
                    changes["flows_added"].append(new_path)
                    
            elif len(parts) >= 2:
                file_path = parts[1]
                
                # Vérifier si le fichier est un flow Langflow (fichier JSON dans un dossier flows)
                is_flow = False
                # Logique plus flexible pour détecter les flows
                if file_path.endswith(".json") and ("langflow-config/flows/" in file_path or "/flows/" in file_path):
                    is_flow = True
                
                # Ajouter le fichier à la liste appropriée
                if status == "A":  # Ajouté
                    changes["added"].append(file_path)
                    if is_flow:
                        changes["flows_added"].append(file_path)
                elif status == "M":  # Modifié
                    changes["modified"].append(file_path)
                    if is_flow:
                        changes["flows_modified"].append(file_path)
                elif status == "D":  # Supprimé
                    changes["deleted"].append(file_path)
                    if is_flow:
                        changes["flows_deleted"].append(file_path)
            else:
                logger.warning(f"Ligne de diff ignorée (format inattendu): {line}")

        logger.debug(f"Changements détectés: Added({len(changes['added'])}), Modified({len(changes['modified'])}), Deleted({len(changes['deleted'])})")
        logger.debug(f"Changements de flows: Added({len(changes['flows_added'])}), Modified({len(changes['flows_modified'])}), Deleted({len(changes['flows_deleted'])})")
        return changes

