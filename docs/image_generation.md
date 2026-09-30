# Images avec ComfyUI et Qwen Image

## Installation et lancement

Le profil par défaut utilise **Qwen Image text-to-image**, avec modèles séparés.
Installez une version ComfyUI disposant des nœuds Qwen natifs, puis démarrez le
serveur local sur `http://127.0.0.1:8188`.

Placez les fichiers suivants dans votre installation ComfyUI :

| Dossier | Fichier du profil par défaut |
| --- | --- |
| `models/diffusion_models/` | `qwen_image_fp8_e4m3fn.safetensors` |
| `models/text_encoders/` | `qwen_2.5_vl_7b_fp8_scaled.safetensors` |
| `models/vae/` | `qwen_image_vae.safetensors` |

Les liens de téléchargement et le workflow de référence sont dans la
[documentation officielle ComfyUI](https://docs.comfy.org/tutorials/image/qwen/qwen-image).
Les variantes Edit, GGUF et les checkpoints personnalisés nécessitent un workflow
adapté ; ce profil cible les modèles split Qwen Image natifs.

```powershell
.\.venv\Scripts\python.exe -m src.cli enclave --api-key-file D:\chemin\openai_token --model qwen
```

`--no-images` désactive les illustrations. `--model` sélectionne uniquement le
modèle d'image ; le modèle textuel se configure sous `provider.model`.

## Configuration

Dans `config/default.yaml`, ou dans un fichier `config/projects/<nom>.yaml` :

```yaml
image:
  provider: comfyui
  model: qwen
  comfyui_url: "http://127.0.0.1:8188"
  comfyui_timeout: 600.0
  portrait_width: 768
  portrait_height: 1024
  building_width: 1024
  building_height: 768
  models:
    qwen:
      type: qwen
      params:
        unet: "qwen_image_fp8_e4m3fn.safetensors"
        clip: "qwen_2.5_vl_7b_fp8_scaled.safetensors"
        vae: "qwen_image_vae.safetensors"
        weight_dtype: default
        sampler: euler
        scheduler: simple
        steps: 20
        cfg_scale: 4.0
        shift: 3.1
```

Les noms doivent correspondre aux fichiers proposés par les chargeurs ComfyUI,
y compris leur sous-dossier éventuel. Ces paramètres concernent le modèle
original, sans LoRA d'accélération.

## Workflow et LoRA

Le graphe API utilise `UNETLoader`, `CLIPLoader` avec type `qwen_image`,
`VAELoader`, les encodeurs positif et négatif, `EmptySD3LatentImage`,
`ModelSamplingAuraFlow`, `KSampler`, `VAEDecode` et `SaveImage`.
Qwen prend en compte les prompts négatifs. Le texte du prompt est conservé tel
quel ; aucune conversion automatique vers un prompt de modèle Edit n'est faite.

Les LoRA Qwen sont injectés sur le modèle de diffusion avant le réglage du
sampling, avec `LoraLoaderModelOnly` ; l'encodeur de texte reste indépendant.
Ajoutez une liste `loras` au profil, au même niveau que `params` :

```yaml
loras:
  - name: "mon_style_qwen.safetensors"
    strength_model: 0.8
```

Installez ces fichiers dans `ComfyUI/models/loras/`. Pour une LoRA Lightning,
adaptez également steps/CFG selon son workflow officiel ; son activation seule
ne change pas ces paramètres dans ce générateur.

## Sorties, seeds et erreurs

Les images sont générées séquentiellement après le pipeline textuel : portraits
des figures importantes dans `output/<project_id>/portraits/`, illustrations des
sites dans `output/<project_id>/sites/`. Les prompts viennent des attributs des
PNJ et des descriptions d'architecture. Les défauts de raccordement entre étapes
identifiés dans [la revue](revue_generation.md) peuvent limiter ces données.

La CLI dérive une seed stable de `generation.seed`, du type d'image et du nom.
Même contenu, seed, modèle et environnement permettent de réutiliser les mêmes
paramètres ; une image identique n'est pas garantie entre versions matérielles
ou logicielles. Les appels directs avec `seed=-1` choisissent une seed aléatoire
pour Qwen. Il n'y a pas de cache d'images : une relance les régénère.

Le délai ComfyUI couvre l'ensemble soumission/attente/téléchargement. Une erreur
HTTP ou de nœud est remontée ; la CLI journalise l'échec de l'illustration puis
continue les suivantes. L'expiration n'annule pas le travail déjà mis en file
dans ComfyUI. Si le serveur est absent, vérifiez sa console et `comfyui_url`.

Flux, SDXL Turbo et le backend HuggingFace restent disponibles via leurs profils.
Les anciens champs `flux_comfyui` sont migrés vers le profil Flux.
