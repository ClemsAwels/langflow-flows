# Sync Langflow

Un script Python pour synchroniser automatiquement les flows Langflow entre un dépôt Git et une instance Langflow.

## Fonctionnalités

- Détection automatique des flows ajoutés, modifiés et supprimés dans un dépôt Git
- Synchronisation bidirectionnelle entre le dépôt Git et l'instance Langflow
- Organisation des flows en dossiers basée sur la structure du dépôt
- Authentification via token API
- Logging détaillé des opérations
- Interface en ligne de commande flexible

## Prérequis

- Python 3.6+
- Git
- Une instance Langflow accessible

## Installation

1. Clonez ce dépôt :
```bash
git clone https://github.com/votre-utilisateur/sync-langflow.git
cd sync-langflow
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

### Configuration

Le script peut être configuré via des variables d'environnement ou des arguments de ligne de commande :

- `LANGFLOW_URL` : URL de l'instance Langflow (par défaut : http://localhost:7860)
- `LANGFLOW_API_TOKEN` : Token d'API pour l'authentification
- `REPO_PATH` : Chemin vers le dépôt Git local
- `BEFORE_COMMIT` : Commit de référence pour la comparaison (avant)
- `AFTER_COMMIT` : Commit de référence pour la comparaison (après)
- `VERBOSE` : Mode verbeux pour le logging

### Exécution

```bash
# Exécution basique avec les valeurs par défaut
python -m sync_langflow.sync_langflow

# Spécifier l'URL de Langflow et le token d'API
python -m sync_langflow.sync_langflow --langflow-url https://votre-instance-langflow.com --api-token votre-token-api

# Spécifier les commits à comparer
python -m sync_langflow.sync_langflow --before-commit abc123 --after-commit def456

# Activer le mode verbeux
python -m sync_langflow.sync_langflow --verbose
```

### Intégration avec GitHub Actions

Pour utiliser ce script dans un workflow GitHub Actions, créez un fichier `.github/workflows/sync-langflow.yml` avec le contenu suivant :

```yaml
name: Sync Langflow Flows

on:
  push:
    branches:
      - main
    paths:
      - 'flows/**'

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
          pip install -r requirements.txt

      - name: Sync Langflow flows
        run: python -m sync_langflow.sync_langflow
        env:
          LANGFLOW_URL: ${{ secrets.LANGFLOW_URL }}
          LANGFLOW_API_TOKEN: ${{ secrets.LANGFLOW_API_TOKEN }}
          BEFORE_COMMIT: ${{ github.event.before }}
          AFTER_COMMIT: ${{ github.sha }}
```

## Structure du projet

```
sync_langflow/
├── __init__.py          # Initialisation du package
├── config.py            # Configuration et gestion des arguments
├── git_manager.py       # Gestion des opérations Git
├── langflow_client.py   # Client API pour Langflow
├── flow_manager.py      # Gestion des flows
├── folder_manager.py    # Gestion des dossiers
├── utils.py             # Fonctions utilitaires
└── sync_langflow.py     # Script principal
```

## Développement

### Tests

Pour exécuter les tests :

```bash
# Créer un environnement de test
./setup_test_env.sh

# Exécuter le test de détection Git
python test_git_detection.py
```

### Contribution

1. Forkez le dépôt
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add some amazing feature'`)
4. Poussez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.
