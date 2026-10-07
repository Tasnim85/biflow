# BO1 — VERSION FINALE UNIQUE

Le projet final se trouve **directement dans ce dossier BO1**. `app.py`, `agents/`, `core/`, `data/` et `outputs/` constituent une seule application. Les anciennes versions et leurs copies sont conservées dans `.archive/`.

## Démarrage sur cette machine

1. **Double-cliquez sur `run_demo.bat`.**
2. Attendez le message `BO1 FINAL PRET`. Le navigateur s'ouvre automatiquement.
3. Cliquez sur **▶ Lancer le pipeline BO1** dans l'accueil.
4. Les résultats des cinq datasets apparaissent sur l'accueil. Les pages de gauche détaillent chaque DSO.

Les données de démonstration sont chargées automatiquement. **Aucune installation ni clé API n'est nécessaire sur cette machine.** Le lanceur vérifie les dépendances, démarre un serveur Windows en arrière-plan, attend sa réponse puis ouvre le navigateur. Un autre double-clic réutilise le serveur actif. Vous pouvez fermer la fenêtre du lanceur après son message de confirmation.

Le port préféré est **8501**. Si ce port est utilisé, un port disponible est choisi et le navigateur ouvre la bonne adresse. `logs/server.json` enregistre l'adresse active.

## Les quatre DSO connectés

| DSO | Fonction exécutée |
|---|---|
| **1** | Orchestrateur DAG, branches parallèles, dépendances, états, durées et erreurs ; choix asyncio ou LangGraph |
| **6** | Embeddings et cosine similarity, correspondances de colonnes, matrice, recommandations et réutilisation de recettes |
| **7** | 16 classes sémantiques, confiance heuristique et preuves par colonne |
| **5** | Plans de nettoyage, validation Pydantic, moteur contrôlé, code exporté, audit et comparaison avant/après |

Le mode par défaut utilise des embeddings locaux par hashing/concepts pour un démarrage rapide. MiniLM, installé localement dans `models/`, reste sélectionnable. L'application ne télécharge aucun modèle pendant l'exécution. L'option LLM utilise un plan JSON validé ; le Python reçu d'un LLM n'est jamais exécuté. En l'absence de clé API, les règles locales restent fonctionnelles.

## Données personnelles

Chargez un ou plusieurs CSV dans la barre latérale, puis cliquez sur **Load uploaded CSV files** et **Run BO1 Pipeline**. Les séparateurs virgule, point-virgule, tabulation et barre verticale sont reconnus. Les noms de colonnes doivent être uniques et le fichier doit contenir au moins une ligne de données. Les identifiants sont lus comme chaînes pour conserver leurs zéros initiaux.

Les CSV de démonstration sont dans `data/generated/`. Les fichiers nettoyés, plans, audits et rapports sont dans `outputs/`. Le bouton **Télécharger tous les résultats** exporte les résultats de la session courante.

## Vérifications

Le lanceur `.bat` a été exécuté, l'accueil a été vérifié dans un navigateur, et le pipeline a été lancé par son bouton principal. La démonstration de 200 clients traite cinq datasets et produit 600 transactions enrichies. Le temps varie selon la machine et le backend. Les neuf tests couvrent aussi les neuf pages, MiniLM, le repli local, la concurrence des tâches, les erreurs, les plans non autorisés et les recettes réutilisées.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Installation sur une autre machine

Python 3.11 ou supérieur est requis. Double-cliquez sur `installer.bat` une fois, puis sur `run_demo.bat`. L'installation des bibliothèques nécessite Internet. L'application fonctionne ensuite sans clé API, même sans poids MiniLM grâce au repli local.

Installation manuelle depuis ce dossier :

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Pour installer explicitement le modèle neural local :

```powershell
.\.venv\Scripts\python.exe download_embedding_model.py
```

`requirements-lock.txt` décrit l'environnement Windows/Python 3.12 vérifié. `.env.example` documente les variables facultatives ; `.env` n'est pas chargé automatiquement.

## Diagnostic

- `logs/server-error.log` : erreurs de démarrage du serveur.
- `logs/server.log` : sortie du serveur.
- `logs/last_pipeline_error.log` : détail d'une exception du pipeline, si elle survient.
- `.venv\Scripts\python.exe launcher.py --check` : vérification des dépendances.

Le lanceur affiche une erreur lisible au lieu d'ouvrir une page avant que le serveur soit prêt. Si une ancienne page reste ouverte, utilisez l'adresse indiquée par `run_demo.bat` et actualisez la page.

## Organisation finale

```text
BO1/
├── run_demo.bat           ← seul lanceur de l'application
├── installer.bat          ← installation uniquement si nécessaire
├── DEMARRAGE.txt
├── launcher.py
├── app.py
├── pipeline.py
├── data_generator.py
├── download_embedding_model.py
├── requirements.txt
├── requirements-lock.txt
├── README.md
├── agents/
├── core/
├── utils/
├── tests/
├── data/generated/
├── models/
├── outputs/
├── logs/
├── docs/ARCHITECTURE.md
├── .venv/
└── .archive/              ← anciennes versions, sauvegardées
```

L'architecture, les formules de qualité, les règles et limites sont détaillées dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Les noms de l'ancien dossier dans cette annexe désignent le projet désormais regroupé à la racine.

Limites principales : CSV en mémoire, règles de dates/currency liées aux conventions de la démonstration, similarité et confiance heuristiques, valeurs manquantes conservées. Les scores sont calculés et ne sont pas une garantie de vérité métier. L'appel OpenAI réel reste facultatif et n'a pas été testé sans clé.
