# TTRPG Content Generator

Générateur de suppléments de jeu de rôle : communautés, PNJ, activités, lieux,
biographies et illustrations. Le pipeline combine génération procédurale et
**OpenAI GPT-6 Luna** pour le texte, puis **ComfyUI / Qwen Image** pour les portraits
et les bâtiments. Il exporte le contenu JSON et un supplément HTML.

## Installation

Python 3.11 ou supérieur, depuis la racine du dépôt :

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

La clé OpenAI peut être définie par `OPENAI_API_KEY` dans `.env`, ou lue depuis
un fichier UTF-8 via `--api-key-file`. Ne stockez pas de clé dans les YAML.

## Génération

```powershell
.\.venv\Scripts\python.exe -m src.cli enclave --api-key-file D:\chemin\openai_token
.\.venv\Scripts\python.exe -m src.cli enclave --api-key-file D:\chemin\openai_token --no-images
```

Adaptez `config/projects/enclave.yaml`, ou créez `config/projects/<nom>.yaml` et
passez ce nom à la CLI. Les valeurs communes se trouvent dans `config/default.yaml`.
La sortie de l'exemple est dans `output/Enclave/`.

Par défaut, le texte utilise `gpt-6-luna`, l'API Responses, un effort de raisonnement
`low` et un budget de 16 384 tokens incluant le raisonnement. Modifiez
`provider.reasoning_effort` et `provider.max_tokens` dans le YAML si nécessaire.
La température n'est envoyée à Luna que lorsque l'effort est `none`.

La reprise est automatique. Une modification de la configuration textuelle
invalide le checkpoint ; changer uniquement les images conserve le texte.
Pour forcer une régénération complète, utilisez **`--no-resume --no-cache`**.
`--steps 1-4` permet une exécution initiale partielle ; les étapes suivantes
nécessitent le contenu des étapes précédentes.

## ComfyUI / Qwen Image

Démarrez ComfyUI sur `http://127.0.0.1:8188`, avec ces fichiers installés :

| Dossier ComfyUI | Fichier |
| --- | --- |
| `models/diffusion_models/` | `qwen_image_fp8_e4m3fn.safetensors` |
| `models/text_encoders/` | `qwen_2.5_vl_7b_fp8_scaled.safetensors` |
| `models/vae/` | `qwen_image_vae.safetensors` |

Les chemins, paramètres et profils sont configurables sous `image`.
`--model qwen` sélectionne Qwen ; `--model flux` permet de conserver Flux.
Les seeds des images sont dérivées de la seed du projet et du nom de chaque
illustration. Voir [le guide des images](docs/image_generation.md) pour le workflow,
les LoRA et le dépannage.

## Vérification et revue

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Les tests utilisent des réponses simulées et ne nécessitent ni clé ni serveur GPU.
Voir [la revue de génération](docs/revue_generation.md) pour les problèmes de
cohérence identifiés et les améliorations proposées.

## Population et généalogie spatialisées

Un prototype autonome simule les naissances, décès, unions, divorces et migrations
sur plusieurs générations, avec carte virtuelle, stockage SQLite compact et
explorateur local des filiations. Aucun LLM ni clé API n'est nécessaire.
Les peuples fantasy ont leurs propres cycles de vie et des croisements configurables.
Les proportions de métropoles, villes, bourgs, villages et hameaux, leurs capacités
et activités se règlent dans `settlement_types` ; des types supplémentaires sont libres.
Sous Windows, `explore_genealogy.cmd` génère la démo si nécessaire et lance le serveur.

```powershell
.\.venv\Scripts\python.exe -m src.genealogy.cli generate config/genealogy/fantasy.yaml --output output/genealogy/fantasy.sqlite
.\.venv\Scripts\python.exe -m src.genealogy.cli explore output/genealogy/fantasy.sqlite
```

Ouvrir `http://127.0.0.1:8765`. Voir [le guide de généalogie](docs/genealogy.md)
pour les règles, les cartes fournies, la population cible et les limites d'échelle,
ainsi que [la revue Sol/Opus](docs/genealogy_review.md).
