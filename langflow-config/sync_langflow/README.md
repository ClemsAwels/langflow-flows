# Synchronisation Langflow et OpenWebUI (Application Modulaire)

Cette application Python permet de synchroniser automatiquement les flows Langflow entre un dépôt Git et une instance Langflow, ainsi que de mettre à jour les pipelines correspondants dans OpenWebUI. Elle détecte les changements dans les fichiers JSON des flows et les synchronise avec l\"instance Langflow, en gérant l\"ajout, la modification et la suppression de flows, ainsi que leur organisation en dossiers. Elle génère également des pipelines pour OpenWebUI basés sur ces flows.

Ce projet est structuré de manière modulaire pour faciliter la maintenance et l\"extension.

## Fonctionnalités

### Synchronisation Langflow
- Détection automatique des changements dans les fichiers de flows via Git
- Ajout, modification et suppression de flows dans Langflow
- Organisation des flows en dossiers basée sur la structure des dossiers dans le dépôt
- Préservation des flows existants non modifiés dans les dossiers
- Gestion correcte de plusieurs dossiers et flows
- Suppression des dossiers vides à la fin du processus
- Support complet pour la structure de dossiers `langflow-config/flows/`
- Logs détaillés pour faciliter le débogage

### Intégration OpenWebUI
- Extraction automatique des informations des flows Langflow (endpoint_name et name)
- Génération de pipelines OpenWebUI basés sur un template
- Téléchargement des pipelines vers OpenWebUI via l\"API
- Mise à jour des pipelines lorsque les flows correspondants sont modifiés
- Gestion des cas où les informations nécessaires sont manquantes

## Structure du Projet

L\"application est organisée en plusieurs modules :

- `sync_app/` : Répertoire principal du package
  - `__init__.py` : Initialisation du package
  - `main.py` : Point d\"entrée principal, orchestre les opérations
  - `config.py` : Gestion de la configuration (arguments CLI, variables d\"env)
  - `utils.py` : Fonctions utilitaires (logging, extraction de noms)
  - `clients/` : Modules pour interagir avec les API externes
    - `__init__.py`
    - `langflow.py` : Client pour l\"API Langflow
    - `openwebui.py` : Client pour l\"API OpenWebUI
  - `managers/` : Modules contenant la logique métier
    - `__init__.py`
    - `git.py` : Gestionnaire pour les opérations Git
    - `flow.py` : Gestionnaire pour les opérations sur les flows Langflow
    - `folder.py` : Gestionnaire pour les opérations sur les dossiers Langflow
    - `pipeline.py` : (Intégré dans `clients/openwebui.py` pour la génération/upload)

## Prérequis

- Python 3.7+
- Git
- Accès à une instance Langflow
- Accès à une instance OpenWebUI (optionnel)
- Dépendances Python : `requests`

## Installation

1. Clonez ce dépôt.
2. Installez les dépendances requises :

```bash
pip install requests
```

## Utilisation

### En ligne de commande

Exécutez l\"application comme un module Python depuis le répertoire parent du dossier `sync_app` :

```bash
python -m sync_app.main [--langflow-url URL] [--api-token TOKEN] [--repo-path PATH]
                       [--before-commit COMMIT] [--after-commit COMMIT] [--verbose]
                       [--openwebui-url URL] [--openwebui-api-key KEY] [--enable-openwebui]
                       [--openwebui-template-path PATH]
```

### Options

#### Options Langflow
- `--langflow-url` : URL de l\"instance Langflow (par défaut: http://localhost:7860)
- `--api-token` : Token d\"API pour l\"authentification Langflow
- `--repo-path` : Chemin vers le dépôt Git local (par défaut: répertoire courant)
- `--before-commit` : Commit de référence pour la comparaison (avant)
- `--after-commit` : Commit de référence pour la comparaison (après)
- `--verbose` : Active le mode verbeux pour le logging

#### Options OpenWebUI
- `--openwebui-url` : URL de l\"instance OpenWebUI (par défaut: http://localhost:3000)
- `--openwebui-api-key` : Clé API pour l\"authentification OpenWebUI
- `--enable-openwebui` : Active l\"intégration avec OpenWebUI
- `--openwebui-template-path` : Chemin vers le template de pipeline personnalisé

### Variables d\"environnement

Vous pouvez également configurer l\"application via des variables d\"environnement :

#### Variables Langflow
- `LANGFLOW_URL` : URL de l\"instance Langflow
- `LANGFLOW_API_TOKEN` : Token d\"API pour l\"authentification Langflow
- `REPO_PATH` : Chemin vers le dépôt Git local
- `BEFORE_COMMIT` : Commit de référence pour la comparaison (avant)
- `AFTER_COMMIT` : Commit de référence pour la comparaison (après)
- `VERBOSE` : Active le mode verbeux pour le logging (true/false)

#### Variables OpenWebUI
- `OPENWEBUI_URL` : URL de l\"instance OpenWebUI
- `OPENWEBUI_API_KEY` : Clé API pour l\"authentification OpenWebUI
- `ENABLE_OPENWEBUI` : Active l\"intégration avec OpenWebUI (true/false)
- `OPENWEBUI_TEMPLATE_PATH` : Chemin vers le template de pipeline personnalisé

## Intégration avec GitHub Actions

Vous pouvez intégrer cette application dans un workflow GitHub Actions pour synchroniser automatiquement les flows et les pipelines lorsque des modifications sont apportées au dépôt. Voici un exemple de configuration :

```yaml
name: Sync Langflow Flows and OpenWebUI Pipelines

on:
  push:
    branches:
      - main
    paths:
      - 'langflow-config/flows/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        with:
          fetch-depth: 2

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      # Assurez-vous que le code de l'application (le dossier sync_app)
      # est présent dans le répertoire de travail du workflow.
      # Vous pouvez soit l'inclure dans le même dépôt, soit le cloner.
      # Exemple si sync_app est dans le même dépôt :
      # - name: Check code structure
      #   run: ls -R

      - name: Sync Langflow flows and OpenWebUI pipelines
        # Exécuter comme un module
        run: python -m sync_app.main --enable-openwebui --verbose
        env:
          LANGFLOW_URL: ${{ secrets.LANGFLOW_URL }}
          LANGFLOW_API_TOKEN: ${{ secrets.LANGFLOW_API_TOKEN }}
          OPENWEBUI_URL: ${{ secrets.OPENWEBUI_URL }}
          OPENWEBUI_API_KEY: ${{ secrets.OPENWEBUI_API_KEY }}
          BEFORE_COMMIT: ${{ github.event.before }}
          AFTER_COMMIT: ${{ github.sha }}
          REPO_PATH: ${{ github.workspace }}
```

N\"oubliez pas de configurer les secrets GitHub pour `LANGFLOW_URL`, `LANGFLOW_API_TOKEN`, `OPENWEBUI_URL` et `OPENWEBUI_API_KEY` dans les paramètres de votre dépôt.

## Structure des dossiers

L\"application s\"attend à ce que les flows soient organisés dans la structure de dossiers suivante :

```
langflow-config/
└── flows/
    ├── DossierA/
    │   ├── Flow1.json
    │   └── Flow2.json
    └── DossierB/
        ├── Flow3.json
        └── Flow4.json
```

Chaque dossier sous `langflow-config/flows/` sera créé comme un dossier dans Langflow, et les flows JSON qu\"il contient seront ajoutés à ce dossier.

## Fonctionnement

### Synchronisation Langflow
1. Le script détecte les changements dans les fichiers de flows entre deux commits Git
2. Il traite les flows ajoutés, modifiés et supprimés
3. Il organise les flows en dossiers basés sur la structure des dossiers dans le dépôt
4. Il préserve les flows existants non modifiés dans les dossiers
5. Il supprime les dossiers vides à la fin du processus

### Intégration OpenWebUI
1. Pour chaque flow ajouté ou modifié, le script extrait l\"endpoint_name et le name
2. Il génère un fichier de pipeline basé sur un template, en remplaçant les placeholders par les valeurs extraites
3. Il télécharge le pipeline généré vers OpenWebUI via l\"API
4. Si l\"endpoint_name n\"est pas trouvé dans le flow, il utilise le nom du flow comme fallback

## Personnalisation du template de pipeline

Vous pouvez fournir votre propre template de pipeline en utilisant l\"option `--openwebui-template-path`. Le template doit contenir les placeholders suivants :
- `ENDPOINT_PLACEHOLDER` : Sera remplacé par l\"endpoint_name du flow
- `FLOW_NAME_PLACEHOLDER` : Sera remplacé par le nom du flow

Si aucun template personnalisé n\"est fourni, le script utilisera un template par défaut.

## Dépannage

Si vous rencontrez des problèmes avec l\"application, activez le mode verbeux avec l\"option `--verbose` ou en définissant la variable d\"environnement `VERBOSE=true`. Cela affichera des logs détaillés qui peuvent aider à identifier la source du problème.

### Problèmes courants

#### Extraction de l\"endpoint_name
Si le script ne parvient pas à extraire l\"endpoint_name d\"un flow, il utilisera le nom du flow (en minuscules et avec les espaces remplacés par des underscores) comme fallback. Vous verrez un message d\"avertissement dans les logs.

#### Téléchargement des pipelines
Si le téléchargement d\"un pipeline vers OpenWebUI échoue, vérifiez que :
- L\"URL de l\"instance OpenWebUI est correcte
- La clé API est valide
- L\"instance OpenWebUI est accessible depuis l\"environnement où le script s\"exécute

## Licence

Ce projet est sous licence MIT.

