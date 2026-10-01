# Prototype de population et généalogie spatialisées

Le module `src/genealogy/` simule une population année par année, sans LLM,
clé API ni service externe. Il conserve chaque personne née, ses parents,
ses épisodes d'union, ses lieux de naissance et de décès, et ses migrations
datées. On peut consulter ses ascendants et descendants et afficher les
recensements sur une carte virtuelle ou une carte fournie sous forme de lieux.

Les paramètres médiévaux sont **des choix de worldbuilding**, pas une
reconstitution historique validée. L'objectif de ce prototype est de produire
une histoire cohérente, mesurable et ajustable avant d'y greffer le monde.

## Lancer et explorer

Sous Windows, double-cliquer sur `explore_genealogy.cmd`, puis ouvrir
http://127.0.0.1:8768. Le lanceur démarre une petite population de démonstration
**en RAM**, sans produire de fichier ni d'archive SQLite. Garder sa fenêtre
ouverte. Le scénario « civilisation » permet ensuite de configurer un calcul massif.
Les mondes sont éphémères : le serveur garde le monde actif et deux alternatives
récentes ; fermer le serveur libère les données. La graine et la configuration
permettent de refaire le calcul.

Le lanceur exige `.venv` : `python -m venv .venv`, puis
`.venv\Scripts\python.exe -m pip install -e ".[dev]"`.
Un chemin d'archive SQLite passé au lanceur charge cette archive en lecture seule ;
les nouveaux calculs du studio restent en mémoire. L'HTML utilise le serveur local.

La page s'ouvre sur **Configurer & générer** : choisir un scénario médiéval,
fantasy ou les paramètres par défaut, saisir une graine et ajuster la population,
la cible facultative, les générations ou la durée exacte. Les types de lieux,
capacités, activités, taux démographiques, migrations, peuples et crises sont
éditables dans les tableaux et contrôles. Une cellule biologique de peuple vide
hérite du réglage global. Le JSON complet donne accès aux croisements, périodes,
cartes explicites et métadonnées ; pendant son édition, les contrôles sont
verrouillés jusqu'à application ou annulation pour préserver les changements.

**Générer ce monde** lance un calcul en arrière-plan. La page indique la
régulation démographique, l'année courante, la population et la progression. Un
seul calcul peut tourner par serveur. À la fin, le résultat s’ouvre automatiquement si cet onglet est resté sur la configuration. Si une exploration est en cours, **Explorer le résultat** permet de basculer explicitement.
Chaque nouveau calcul garde des tableaux binaires NumPy propriétaires en RAM,
avec identifiants denses, événements datés et index d'exploration. Il ne passe pas
par SQLite et ne sauvegarde pas automatiquement les données. La configuration
et la graine sont conservées dans le monde. `generate --output ...` reste une
commande de sauvegarde SQLite explicite pour compatibilité.

L'import accepte YAML et JSON ; l'export télécharge un scénario JSON réutilisable.
Les champs et configurations sont validés avant le calcul. La vue **Explorer**
dispose d'une carte déplaçable et zoomable, d'un curseur annuel, d'un classement
des lieux, de courbes de population / naissances-décès / unions-migrations et
d'un arbre familial cliquable. Les lectures sont liées à un identifiant de monde
pour garder les onglets indépendants. Les listes d'habitants concernent toujours
le recensement final, même si la carte affiche une date antérieure.

Vérification optionnelle du parcours dans un navigateur sans interface visible :

```powershell
npm.cmd install --prefix tmp/studio_qa playwright --no-save --no-package-lock
node tests/browser/genealogy_studio.cjs
```

Ce test utilise Edge installé sous Windows, un serveur déjà lancé sur le port
8765 et génère une petite archive de test. `STUDIO_URL` et `STUDIO_BROWSER`
permettent de changer le serveur et l'exécutable. Les captures desktop/mobile
restent dans `output/genealogy/screenshots/`, hors Git.

Depuis la racine du dépôt, sous PowerShell :

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Studio sans écriture de données ; petite démo immédiate.
.\.venv\Scripts\python.exe -m src.genealogy.cli studio --port 8768

# Calcul exact en RAM, affiche ses statistiques puis libère le monde.
.\.venv\Scripts\python.exe -m src.genealogy.cli simulate config/genealogy/civilization.yaml --years 25 --quiet

# Benchmark sans écriture ; population, lieux, durée et threads configurables.
.\.venv\Scripts\python.exe -m src.genealogy.benchmark --population 1000000 --places 500 --years 25 --threads 4

# Sauvegarde SQLite explicitement demandée, hors parcours du studio.
.\.venv\Scripts\python.exe -m src.genealogy.cli generate config/genealogy/medieval.yaml --output output/genealogy/medieval.sqlite

# Humains, elfes, nains et demi-elfes ; croisements explicites et rares.
.\.venv\Scripts\python.exe -m src.genealogy.cli generate config/genealogy/fantasy.yaml --output output/genealogy/fantasy.sqlite

# Carte, courbe démographique, chronologie et arbre de filiation cliquable.
.\.venv\Scripts\python.exe -m src.genealogy.cli explore output/genealogy/fantasy.sqlite
# Ouvrir http://127.0.0.1:8765 ; Ctrl+C arrête le serveur.

# Informations, ascendants ou descendants d'un individu.
.\.venv\Scripts\python.exe -m src.genealogy.cli person output/genealogy/fantasy.sqlite 4500 --depth 6
.\.venv\Scripts\python.exe -m src.genealogy.cli person output/genealogy/fantasy.sqlite 42 --direction descendants --year 1100
.\.venv\Scripts\python.exe -m src.genealogy.cli stats output/genealogy/fantasy.sqlite
```

L'installation fournit aussi `ttrpg-population`, avec les mêmes sous-commandes.
Choisir un nouveau chemin de sortie pour chaque génération : le moteur refuse
d'écraser une archive. Les fichiers de simulation sous `output/` restent hors Git.

L'explorateur distingue les recensements historiques des listes d'habitants,
qui portent sur le dernier recensement. Cliquer sur une date situe l'événement
sur la carte ; cliquer sur un parent, enfant ou nœud ouvre sa fiche.
Les origines des ascendants et le parcours de l'individu apparaissent sur la carte.
Le serveur est limité à `127.0.0.1` et les archives sont ouvertes en lecture seule.

## Diversité des lieux

La carte virtuelle utilise `settlement_types`, une liste extensible de profils.
Par défaut : métropoles, villes, bourgs, villages et hameaux. Le scénario fantasy
ajoute ports et villages miniers. Chaque profil configure `kind`, `share`,
`minimum_count`, `capacity`, `initial_weight`, `activities`, `races` et `metadata`.
Les types et positions sont répartis selon la graine du scénario. `spatial_layout: dispersed` (défaut) disperse les lieux, `clustered` crée des bassins de peuplement ; `grid` reste une option de comparaison. La carte et l’aperçu utilisent des cellules de Voronoï.

`minimum_count` réserve d'abord des lieux ; les places restantes sont distribuées
proportionnellement à `share`, arrondies par les plus grands restes. La somme
finale vaut exactement `virtual_settlements`.
On peut aussi fixer tous les nombres par `minimum_count` avec `share: 0`.
Plusieurs profils peuvent partager un `kind` tout en ayant des métiers différents.
Ces proportions comptent des lieux, pas des habitants : le poids initial d'un
lieu vaut `capacity * initial_weight`.
La capacité économique n'impose donc pas sa population initiale. Une grande ville
peut commencer peu peuplée. `capacity_mode: fixed` conserve les capacités ;
`scale` les augmente si nécessaire pour soutenir la taille demandée du monde.

```yaml
virtual_settlements: 100
settlement_types:
  - kind: metropolis
    share: 1
    minimum_count: 1
    capacity: 50000
    activities: {trade: 5, craft: 4, administration: 1}
  - kind: city
    share: 4
    capacity: 10000
    activities: {trade: 3, craft: 5, agriculture: 2}
  - kind: village
    share: 70
    capacity: 600
    activities: {agriculture: 9, craft: 1}
  - kind: hamlet
    share: 25
    capacity: 100
    activities: {agriculture: 1}
```

Une carte explicite via `settlements` conserve les types et réglages de chaque
lieu ; le catalogue virtuel n'est alors pas utilisé. Les lieux restent fixes
pendant une simulation : fondation de villes et changement de type sont à venir.
Sur cette carte explicite, `initial_weight` est un poids **absolu** par lieu,
égal à 1 par défaut : renseigner ces poids pour répartir les fondateurs selon
les tailles voulues. Il ne s'agit pas du multiplicateur des profils virtuels.
Les `races` locales remplacent complètement les poids globaux pour les fondateurs
du lieu ; les catégories omises y sont absentes au départ. La composition globale
est donc le résultat des distributions locales, puis des unions et migrations.
Les IDs virtuels désignent des lieux de la distribution : changer la graine ou le
catalogue peut changer les types touchés par un événement ciblant ces IDs.

## Temps, fondateurs et filiations

`years` prend priorité sur `generations * generation_years`. Une génération
est ici une durée de simulation conventionnelle, pas une cohorte synchrone :
parents et enfants peuvent appartenir à plusieurs classes d'âge.

Le recensement initial est à `start_year`, puis viennent les années
`start_year + 1` à `start_year + duration`. Le cycle annuel est :

1. Naissances dans les unions existantes, avec espacement et risque maternel.
2. Décès, y compris ceux des nouveau-nés de cette année ; fermeture des unions.
3. Divorces, puis nouvelles unions ; délai minimal avant remariage.
4. Migrations des ménages et adaptation des activités incompatibles avec le lieu.
5. Recensement de fin d'année.

Une personne est présente au recensement `y` si `birth <= y` et
`death IS NULL OR death > y`. Une naissance et un décès peuvent partager une
année. La mère et le père sont vivants au début de l'année de naissance ;
ils peuvent mourir cette même année. Une migration ne se produit pas après
le décès. Les années négatives sont possibles : le marqueur interne « vivant »
est distinct des années de calendrier, puis devient `NULL` dans SQLite.

Les fondateurs ont des âges tirés d'une courbe de survie stationnaire. Leurs
parents sont inconnus ; leur lieu initial sert d'origine supposée, et leurs
unions initiales sont **observées à la frontière de simulation**, sans date
de formation antérieure inventée. Les fiches indiquent cette incertitude.
L'historique de résidence n'est pas connu avant `start_year` pour ces personnes.
La phase de leur dernier accouchement supposé est répartie pour atténuer
le pic artificiel de naissances au démarrage, sans inventer d'enfants historiques.

Les filiations produites après le départ sont complètes jusqu'aux fondateurs.
`family` identifie une lignée paternelle, pas un ménage : les ménages sont
reconstitués à partir des partenaires et des enfants. Le contrôle de parenté
compare les ascendants des deux candidats, personnes elles-mêmes incluses,
jusqu'à `kinship_depth`. Il n'est jamais désactivé à grande population.

## Configurer les règles

Les modèles Pydantic refusent les options inconnues, références inexistantes,
probabilités hors intervalle et bornes d'âge inversées. Les probabilités sont
annuelles, sauf `maternal_mortality`, qui est **par accouchement**.

| Paramètres | Sens |
| --- | --- |
| `infant_mortality` | Risque de décès dans l'année de naissance ; valeur de base féminine |
| `child_mortality`, `child_max_age` | Risque annuel entre 1 an et la borne incluse |
| `adult_mortality`, `aging_coefficient`, `aging_exponent` | Risque de fond + augmentation exponentielle avec l'âge |
| `male_mortality_factor` | Facteur appliqué aux risques masculins, nouveau-nés compris |
| `max_age` | Limite de vie absolue ; décès assuré à cette borne |
| `fertility_peak`, âge du pic, largeur | Risque conditionnel d'accouchement pour une femme en union et disponible |
| `birth_spacing` | Intervalle minimal entre deux années d'accouchement |
| `marriage_rate` | Participation annuelle à la recherche pour chaque sexe ; ce n'est pas le taux d'union réalisé |
| `founder_match_participation` | Participation à la constitution des unions initiales |
| `max_age_gap`, `status_affinity` | Filtres d'écart d'âge et d'affinité de niveau social |
| `marriage_radius`, `migration_radius`, `distance_scale` | Portée et décroissance avec la distance |
| `local_marriage_weight`, `max_neighbors` | Préférence locale et limite de voisins considérés |
| `status_weights`, `status_inheritance` | Répartition des niveaux et stabilité intergénérationnelle |
| `activity_inheritance` | Transmission d'une activité parentale si le lieu la permet |

La natalité réalisée est inférieure à la somme de la courbe de fertilité :
celle-ci ne s'applique qu'aux femmes en union, dans la fenêtre fertile, hors
espacement, et dépend de la pression économique. Elle n'est donc pas un TFR
annoncé à tort. Les niveaux sociaux sont des codes ordonnés configurables,
sans liste de métiers ou rangs intrinsèques aux peuples.

Les destinations d'union combinent distance, préférence locale, quantité
tempérée de candidats compatibles et affinité de peuple. Le nombre de
tentatives est borné. Les couples deviennent co-résidents. Les migrations
concernent un couple ou adulte seul, avec les enfants non mariés à charge.
La garde suit la mère vivante co-résidente, sinon le père vivant co-résident.
Les orphelins restent dans leur lieu. Après divorce, les ex-conjoints peuvent
continuer à résider dans le même lieu ; leurs déplacements sont indépendants.

Les activités doivent appartenir à l'économie du lieu. Une activité soutenue
est conservée lors d'un déplacement ; une activité incompatible est réattribuée.
Le champ `activity` est l'activité actuelle, ou celle au décès, pas un journal
complet de carrière. Il constitue une spécialité héritée dès la naissance,
sans prétendre que le nourrisson exerce déjà un métier.

## Peuples fantasy et croisements

Voir le scénario complet [`fantasy.yaml`](../config/genealogy/fantasy.yaml).
Chaque `race` est une catégorie de peuple/espèce fictive avec un code compact,
un poids initial, des métadonnées et des paramètres démographiques particuliers.
Les elfes peuvent vivre plusieurs siècles, atteindre une maturité tardive et
avoir une natalité annuelle plus faible ; les nains ont une autre courbe.
Ces valeurs sont les règles du monde, sans dépendance à un système de jeu.

```yaml
races:
  - name: human
    initial_weight: 80
  - name: elf
    initial_weight: 20
    marriage_min_age: 60
    marriage_max_age: 350
    max_age_gap: 100
    demography:
      max_age: 600
      adult_mortality: 0.0008
      aging_coefficient: 0.000001
      aging_exponent: 0.018
      fertility_min_age: 60
      fertility_max_age: 300
      fertility_peak_age: 150
      fertility_width: 75
      fertility_peak: 0.035
      birth_spacing: 12
  - name: half_elf
    initial_weight: 0
crossbreeding:
  - parents: [human, elf]
    marriage_affinity: 0.025
    max_age_gap: 180
    fertility_factor: 0.6
    offspring: {half_elf: 1}
```

`marriage_affinity` est un **poids relatif de préférence**, pas une garantie
que 2,5 % des unions seront mixtes. Leur fréquence dépend aussi des effectifs,
âges, niveaux et voisinages. Les candidats sont regroupés par peuple compatible,
ce qui évite de condamner artificiellement les minorités à rester célibataires.
Lorsque seuls des partenaires d'un autre peuple sont disponibles, ce poids
relatif ne garantit pas que les unions mixtes restent rares. Pour les interdire,
utiliser une affinité nulle ou ne pas déclarer la paire.

Une paire non déclarée entre peuples différents ne forme pas d'union dans ce
prototype. Par défaut, une paire du même peuple produit ce peuple. Une règle
explicite peut aussi modifier ce cas, pour des règles de descendance particulières.
Les règles sont symétriques dans l'ordre des parents. `fertility_factor: 0`
autorise une union infertile ; `offspring` peut donner plusieurs résultats
pondérés. Les retours vers les peuples parentaux doivent être déclarés, comme
humain/demi-elfe et elfe/demi-elfe dans l'exemple complet.

L'ascendance est conservée comme des parents réels avec leurs propres codes
de peuple. Aucun vecteur génétique ou pourcentage d'ascendance n'est stocké
par personne : il peut être calculé à la demande à partir de la généalogie.
Les classes d'âge du recensement restent des **années chronologiques**
(`0–14`, `15–49`, `50+`) ; `50+` ne signifie pas « âgé » pour un elfe.

## Carte fournie, capacité et population cible

Remplacer `virtual_settlements` par `settlements` :

```yaml
settlements:
  - id: 100
    name: Port des Brumes
    x: 0
    y: 20
    kind: port
    initial_weight: 8
    capacity: 8000
    activities: {fishing: 4, trade: 4, craft: 2}
    races: {human: 9, elf: 1}
    metadata: {region: western_coast}
  - id: 250
    name: Hautes Mines
    x: 35
    y: 40
    kind: mining
    initial_weight: 2
    capacity: 2000
    activities: {mining: 8, agriculture: 2}
```

Les identifiants de lieu peuvent être discontinus et désordonnés. Les
coordonnées et les rayons utilisent la même unité libre, par exemple le km.
Les distances sont euclidiennes : obstacles, mers, routes et temps de trajet
ne sont pas encore modélisés. Les lieux ne changent pas pendant ce prototype.
Les poids de peuple du lieu remplacent la répartition globale pour ses fondateurs.

`capacity` est un support économique, pas une limite administrative.
Au-dessus de la capacité, le risque de fertilité est diminué par
`min(1, capacity / residents)` appliqué au hasard cumulatif. La capacité
augmente selon `capacity_growth` et peut être affectée temporairement par
des événements. Les destinations de migration dépendent du support par habitant.

`capacity_mode: scale` (défaut) augmente proportionnellement les capacités
si leur somme est inférieure à 1,5 fois le maximum entre fondateurs et cible.
Cela fonctionne pour la carte virtuelle **et pour les lieux fournis**.
`capacity_mode: fixed` préserve exactement les capacités fournies : choisir
cette option pour une économie contrainte, et examiner les écarts à la cible.
Les capacités effectives sont sauvegardées dans la table `settlements`.

```powershell
.\.venv\Scripts\python.exe -m src.genealogy.cli generate config/genealogy/medieval.yaml --target 1000000 --output output/genealogy/kingdom.sqlite
```

La stratégie `target_mode: bounded` est désormais le défaut : **un seul run**,
avec une population initiale fixe qui sert de plancher de récupération et une
`target_population` qui sert de plafond, non d'objectif final obligatoire. Sans
plafond renseigné, la simulation suit ses règles naturelles. `report` conserve
un mode libre, avec comparaison indicative à la cible.

La natalité est ajustée chaque année si la population est près du plancher ou en
dessous. Le contrôleur estime les pertes naturelles et la survie des nouveau-nés,
puis renforce les probabilités des seules mères biologiquement admissibles. Les
âges fertiles, couples, stérilité, croisements et espacements restent effectifs.
La hausse conserve le profil d'âge et est bornée : facteur maximal 4 et probabilité
annuelle maximale 0,85 par défaut, sans diminuer une probabilité biologique déjà
supérieure. Les probabilités nulles restent nulles.

Une crise nuisible active suspend cette compensation ; ses décès et sa baisse
de natalité sont conservés. La population peut passer sous le plancher. Après
la crise, la compensation reprend progressivement ; elle ne peut garantir un
rétablissement si aucun parent fertile ne survit ou si la simulation s'éteint.
Aucune personne n'est ressuscitée, aucun parent ou enfant fictif n'est injecté.

Le plafond est strict au recensement annuel. Si les décès naturels ne suffisent
pas, des décès supplémentaires sont échantillonnés parmi les survivants, avec
pondération par leurs risques de mortalité (âge, sexe, peuple et événements).
Les décès naturels/maternels sont toujours conservés. Le quota conditionnel
respecte exactement le plafond tout en réutilisant le flux aléatoire annuel.
La population transitoire après les naissances, avant les décès de l'année, peut
être plus élevée ; elle n'est pas publiée comme un recensement annuel.

Réglages JSON : `regulation_response_years` (3), `regulation_buffer` (0,02),
`regulation_max_fertility_factor` (4), `regulation_max_birth_probability` (0,85).
Le contrôleur est séparé dans `regulation.py` pour permettre des accélérations
et politiques par peuple/nation/période par la suite. Le résumé fournit les
naissances/décès supplémentaires, les années sous le plancher et les facteurs
aux dates de recensement. Le modèle régulé est versionné `csr-soa-bounded-v4`.

Les anciens scénarios `calibrate_founders` sont interprétés comme `bounded`.
`calibration_population` et les anciens callbacks restent acceptés pour charger
les configurations existantes, mais n'exécutent aucun pilote. Le nombre initial
n'est jamais recalculé. Un plafond inférieur au plancher est refusé.

## Périodes et événements

Les périodes sont des modifications cumulatives : les champs absents restent
inchangés. Un paramètre propre à un peuple a priorité sur le paramètre global
modifié par une période.

```yaml
periods:
  - start_year: 1120
    demography: {infant_mortality: 0.15}
    society: {marriage_min_age: 22}
events:
  - name: Guerre des Marches
    start_year: 1060
    end_year: 1064
    settlements: [100, 250]
    races: [human]
    min_age: 18
    max_age: 60
    sex: male
    extra_mortality: 0.05
    migration_factor: 3
    capacity_factor: 0.7
```

Les intervalles sont inclusifs. Une liste de lieux ou peuples vide signifie
tous ; la borne d'âge par défaut inclut les peuples longévifs. Les filtres
d'âge, sexe et peuple concernent les risques individuels. La capacité est
une propriété des lieux ciblés et concerne tous leurs habitants.
Le facteur de fertilité est évalué sur la mère : un événement limité aux
hommes agit sur leurs décès et départs, puis sur les unions encore disponibles,
mais ne multiplie pas directement le risque d'accouchement des femmes.

Les facteurs de mortalité et de fertilité multiplient le hasard cumulatif :
`q' = 1 - (1 - q)^factor`. La mortalité supplémentaire se compose par
`1 - (1 - q') * (1 - extra)`. Les effets simultanés se combinent.
`migration_factor` multiplie la probabilité annuelle de départ, bornée à 1.
Pour un couple, le facteur le plus élevé des partenaires est utilisé :
le résultat ne dépend pas de celui qui a le plus petit identifiant.

## Stockage et performances

Le cœur utilise des identifiants denses, des tableaux NumPy de **58 octets
par personne enregistrée**, plus un tableau d'identifiants des vivants.
Les recherches d'ascendants accèdent directement aux parents par identifiant.
La boucle annuelle parcourt les vivants, pas tous les morts. Les lieux
utilisent des indices internes contigus et des comptes vectorisés.
Les dépendants sont un index trié de tableaux, sans dictionnaire permanent
par enfant. Les paramètres et tables de mortalité sont mis en cache par période.

L'archive SQLite normalise les tables :

| Table | Contenu |
| --- | --- |
| `people` | Sexe, années, parents, lieux, lignée, niveau, spécialité, peuple |
| `unions` | Partenaires, début, fin, motif, lieu de formation/observation |
| `migrations` | Personne, année, origine, destination, motif |
| `census`, `settlement_census` | Recensements espacés ; événements de la fenêtre entre recensements |
| `population_census`, `settlement_race_census` | Âges, sexes, activités, peuples et nations aux dates de recensement |
| `migration_flows` | Flux agrégés sur la fenêtre entre recensements |
| `settlements`, `races`, `activities` | Catalogues partagés |
| `metadata`, `person_annotations` | Configuration, diagnostics, métadonnées facultatives |

Les identifiants SQLite sont des clés entières ; les inconnus sont `NULL`.
Les personnes sont insérées par lots de 10 000, les événements au fil des
années, et les index sont créés à la fin. Une archive incomplète porte le
suffixe `.sqlite.partial` ; elle n'est pas publiée comme un résultat complet.
Le serveur ne charge jamais un JSON de toute la population. Les habitants
sont paginés et les arbres ont un plafond de nœuds et de profondeur.

**Limites d'échelle :** tous les enregistrements de personnes restent en RAM
jusqu'à la fin, pour garder un accès direct aux ascendants. Le tableau grandit
par doublement : sa capacité peut atteindre presque deux fois les données,
avec un pic temporaire plus élevé lors d'une réallocation. Dix millions de
personnes enregistrées représentent déjà 580 Mo de données de base, avant
réserve, tableaux temporaires et événements de l'année. Quelques millions
de vivants sur plusieurs siècles peuvent représenter beaucoup plus de personnes
enregistrées. L’appariement utilise un noyau Numba natif sur des pools CSR ; le contrôle exact de parenté n’est pas désactivé pour gagner du temps. Les migrations de foyers sont appliquées par lots. `backend: reference` conserve le chemin Python pour comparaison ; les tirages diffèrent entre backends.
La limite d'identifiants est `2**31 - 1`. Le graphe est creux en mémoire, mais
la construction peut encore faire beaucoup de comparaisons si tous les lieux
sont géographiquement concentrés.

Les mesures réalisées pendant le développement et les corrections issues
des deux revues sont détaillées dans [la revue technique](genealogy_review.md).

## Extension depuis Python

Ajouter de nouveaux métiers, peuples, lieux, événements ou périodes se fait
en YAML. `metadata` accueille les régions, cultures et identifiants du futur
worldbuilder. Les attributs individuels supplémentaires peuvent aller dans
`person_annotations` plutôt que grossir chaque ligne de millions de personnes.

Pour une règle de risque propre au monde :

```python
from pathlib import Path
from src.genealogy.config import load_scenario
from src.genealogy.engine import generate

class MagicWinter:
    descriptor = {"name": "magic_winter", "version": 1, "fertility_factor": 0.5}

    def apply(self, engine, process, ids, hazards):
        if process == "births" and 1100 <= engine.year <= 1110:
            hazards["fertility"] *= 0.5

generate(load_scenario(Path("config/genealogy/fantasy.yaml")),
         Path("output/genealogy/magic.sqlite"), rules=[MagicWinter()])
```

Le protocole est défini dans `src/genealogy/rules.py`. Les tableaux de risque
sont alignés sur `ids`, sauf `capacity`, aligné sur le catalogue des lieux.
Les groupes sont différents suivant le processus ; une règle doit être sans
effet secondaire, car elle peut être appelée plusieurs fois par année.
`engine.stream("nom_unique", process)` fournit un flux reproductible par année
et processus, qui avance entre les appels au lieu de recommencer les tirages.
Les règles s’appliquent au run unique. Définir un
`descriptor` sérialisable avec nom, version et paramètres pour rendre leur
provenance exploitable ; sans lui, seul le type Python est enregistré.

Le registre des champs compacts (`schema.py`) pilote le dtype, les colonnes
SQLite et l'insertion. Un nouvel attribut du cœur exige encore une règle
d'initialisation et d'héritage ; ne pas en ajouter un pour une information
rare qui convient mieux aux annotations.

Ce module est autonome : il ne remplace pas encore l'étape 5 du générateur
de suppléments. Le rapprochement se fera à partir des personnes, unions et
lieux réels, en générant ensuite noms et descriptions à la demande. Les
prochaines extensions structurantes sont les routes/obstacles, fondations
de lieux, adoptions, foyers préexistants, carrières historiques, et un stockage
séparant les parents archivés des champs nécessaires uniquement aux vivants.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src/genealogy tests/test_genealogy.py
```

Les tests utilisent des seeds fixes, des archives temporaires et aucun service
externe. Ils couvrent notamment conservation annuelle des effectifs,
non-chevauchement des unions, parents vivants à la naissance, espacement,
mortalité néonatale, contrôle des proches parents, garde et migrations,
calendriers négatifs, peuples minoritaires, hybrides, périodes partielles,
archives en lecture seule et réponses de l'API locale.


## Recensements espacés, événements exacts

`snapshot_interval: 10` enregistre les recensements tous les dix ans, ainsi que
les dates initiale et finale. Valeurs 1, 25, 50, 100… possibles. La simulation
reste annuelle : les dates individuelles de naissance, décès, union et migration
ne sont ni arrondies ni supprimées. Un run de 1 000 ans / 500 lieux sauvegarde
101 recensements et 50 500 effectifs locaux, au lieu de 1 001 / 500 500.

`census.span` est la durée de la fenêtre précédente ; naissances, décès,
unions et déplacements sont les totaux de cette fenêtre. Les courbes affichent
leur moyenne par an. Le curseur parcourt les recensements disponibles ; cliquer
une date individuelle affiche le recensement le plus proche, sans modifier cette
date. Les données agrégées d’une année absente ne sont pas inventées.

## Nations, frontières et filiations

Les nations sont des identités politiques indépendantes des races :

```yaml
nations:
  - {name: Valdorie, founded: 1000, dissolved: 1300, capital: 0}
  - {name: Marches, founded: 1100, capital: 20}
territory_mode: nearest_capital
foreign_marriage_factor: 0
foreign_migration_factor: 0
nation_contacts:
  - nations: [Valdorie, Marches]
    start_year: 1150
    end_year: 1250
    marriage_factor: 0.2
    migration_factor: 0.5
```

Les intervalles sont `[début, fin)` ; la disparition est effective dès son année.
Avec `nearest_capital`, les lieux suivent la capitale active la plus proche.
`territories` fournit des revendications datées qui remplacent localement cette
répartition. `territory_mode: explicit` laisse les lieux non revendiqués
indépendants. Les capitales implicites sont déterministes indépendamment de
l’ordre des IDs fournis. Les revendications qui se chevauchent sont rejetées.

Un contact règle séparément les unions et les migrations ; un facteur de migration
nul interdit aussi un déplacement conjugal. Les lieux indépendants restent ouverts.
L’annexion d’un lieu change la souveraineté de ses résidents sans créer une migration.
Ce sont des changements politiques **configurés**, pas une émergence endogène de
conquêtes/scissions. Les frontières sont une première couche spatiale, sans routes,
relief, obstacles ni modèle de connexité territoriale.

Les divorces, veuvages et remariages sont simulés : `divorce_rate`,
`remarriage_delay`, dates/motifs de fermeture des unions, demi-fratries et garde
maternelle puis paternelle. **L’adultère et une filiation reconnue distincte de la
filiation biologique ne sont pas encore modélisés**. Le père biologique est
actuellement le conjoint de la mère à la naissance. Le contrôle de parenté porte
sur les ancêtres connus jusqu’à `kinship_depth` ; ceux des fondateurs restent inconnus.

## Export binaire compact

```powershell
.\.venv\Scripts\python.exe -m src.genealogy.cli compact output/genealogy/world.sqlite --output output/genealogy/world_compact
```

L’export produit des fichiers NumPy `.npy` accessibles par mémoire mappée :
IDs implicites, dates relatives sur 16 bits, parents sur 32 bits, lieux par indices
sur 16 bits, sexe/niveau compactés, catalogues partagés. **21 octets/personne**
dans le cas courant ; les catalogues plus grands élargissent les champs nécessaires.
La lignée patrilinéaire se déduit des parents au lieu d’être répétée dans chaque fiche.
Les unions (15 octets/épisode), migrations (11 octets/déplacement), annotations et
recensements espacés restent séparés. Les événements et dates sont conservés sans
perte ; aucune généalogie n’est inventée à la lecture. Les inconnus ont des sentinelles.

`CompactArchive` permet une lecture directe d’un individu et de ses ascendants.
Le serveur utilise encore SQLite pour ses index et sa pagination. Cet export ne
supprime donc **pas encore** le coût initial d’insertion/indexation SQL : le futur
backend massif devra écrire directement ces blocs et séparer les vivants des morts.
50 millions de fiches courantes représenteraient 1,05 Go de personnes, mais les
ancêtres décédés, unions et déplacements augmentent ce total. Le seuil de 50 millions
sur 1 000 ans en une ou dix minutes n’est pas démontré.

## Optimisation du calcul et mémoire binaire

Les décisions restent annuelles et individuelles. Les mariages gardent le même
matching séquentiel avec contrôle de parenté ; ses dépendances interdisent une
parallélisation naïve. Les tris par catégories sont remplacés par des tris comptage
natifs stables, les professions sont tirées en lots avec exactement les mêmes
nombres aléatoires, et les événements restent des blocs numériques. Le chemin
sans événement actif évite les gros tableaux temporaires. Le recensement utilise
une réduction entière native, parallèle à partir de 250 000 vivants lorsque
`compute_threads > 1` (défaut 4, configurable dans le JSON).

Les champs historiques des personnes occupent 38 octets par enregistrement en RAM,
les épisodes d'union 25 octets, les déplacements 17 octets. Les compteurs/cartes
sont conservés aux recensements espacés par `snapshot_interval`, avec date finale
incluse. Les événements gardent leurs dates exactes. Ces tailles concernent les
buffers binaires, hors catalogues, index et capacité temporaire du simulateur.
Les buffers ont des types et sentinelles définis dans `schema.py`, `memory.py` et
`events.py` ; aucune instance Python par personne n'est stockée. Les données sont
libérées progressivement lors de la finalisation pour éviter une copie globale
avec tous les champs de travail encore présents.

Les tests vérifient l'égalité exacte des personnes, unions, fermetures, migrations
et recensements avec la version antérieure a92216d, et comparent chaque fonction
d'exploration du backend RAM à SQLite. Les paramètres de races, événements, pays,
périodes, divorce et remariage restent ceux du scénario. La compilation native
peut alimenter le cache technique de Numba ; « sans écriture » désigne ici les
données de simulation, sans archive ni sauvegarde automatique.

Mesures finales sur i7-10700K, Windows, Python 3.12.13, NumPy 2.5.3,
Numba 0.67.0, graine 42, 500 lieux dispersés, moteur natif préchauffé,
recensements décennaux. Calculs lancés successivement, cible sans calibration.

| Scénario | Ancien SQLite | Nouveau RAM | Accélération |
| --- | ---: | ---: | ---: |
| 1 million de fondateurs, 25 ans | 44,0 s | 10,16 s | ×4,33 |
| 100 000 fondateurs, 1 000 ans | 336,0 s | 71,62 s | ×4,69 |

Le premier monde contient 1 722 266 personnes historiques et 1 000 018 vivants,
535 174 unions et 395 778 déplacements. Son historique binaire occupe 85,55 Mo
(hors index/catalogues), avec pic mémoire du processus ≈277 Mio. Le premier accès
à une personne, qui construit des index réutilisables, prend 0,31 s.

Le second contient 5 817 116 personnes historiques et 348 040 vivants,
2 168 095 unions et 3 427 502 déplacements. Son historique binaire occupe
333,52 Mo, avec pic mémoire ≈649 Mio, index du premier accès compris ; celui-ci
prend 1,48 s. Le retrait des écritures transfère les événements en RAM : le pic
peut donc dépasser celui du backend qui les écrit progressivement en SQLite.

Ces résultats sont identiques aux résultats démographiques précédents. Les
empreintes de compatibilité vérifient en plus toutes les identités et tous les
événements de scénarios humains, fantasy et d'une carte à IDs non triés. Les
noyaux de sélection des personnes fertiles, chefs de foyer et gardiens de mineurs
fusionnent les filtres, sans changer l'ordre des individus ni les tirages.

Ces mesures ne sont pas celles d'un monde final de 50 millions. Le simulateur
conserve encore tous les ancêtres en RAM pendant le calcul ; le benchmark cible
50 millions / 1 000 ans reste à faire. Le temps de la première compilation et
aucun essai de calibration n'est exécuté.


Validation du nouveau contrôleur : 3 000 fondateurs, plafond 3 600, peste de 40 %
en 1010 avec fécondité divisée par quatre : population minimale 1 822, remontée
au-dessus de 3 000 et respect du plafond sur 80 ans. Un test de 100 000 fondateurs,
500 lieux, plafond 105 000 et durée 100 ans a pris 4,13 s en RAM, un seul run,
sans franchissement du plancher ni modification des fondateurs. Ces scénarios
ne prouvent pas la performance sur 50 millions / 1 000 ans.


## Atelier : configuration, monde et individus

Le lanceur `explore_genealogy.cmd` ouvre le serveur sur `http://127.0.0.1:8772`.
La configuration se parcourt par sept rubriques compactes : départ/carte, types
de lieux, démographie, peuples, événements, nations/contacts et JSON. Les activités
se modifient par nom et poids, avec ajout/suppression de lignes. Les peuples sont
éditables ; leur renommage met à jour les références. Une suppression référencée
est refusée avec une explication. Les contacts proposent les noms des nations.
L'édition JSON conserve la protection appliquer/annuler et la validation du scénario.

L'onglet Monde réunit carte, statistiques et graphiques. Survoler un recensement
montre ses valeurs ; cliquer affiche sa carte. Une plage de dates restreint le
graphique aux recensements conservés. La lecture automatique, les flèches et
le curseur parcourent les mêmes recensements, sans interpoler de données annuelles.
Le panneau de mortalité couvre toute la simulation, pas uniquement la date affichée.

L'onglet Individus conserve la carte, la date et le lieu sélectionnés. L’atlas visuel des résidents au **dernier recensement** distingue sexe et peuple.
Ses filtres portent sur toute la population du lieu. Les parents, enfants,
unions, divorces et migrations ouvrent les personnes liées ; une date de chronologie
synchronise la carte avec le recensement conservé le plus proche. Les flèches de la
recherche permettent de revenir aux individus consultés. Le lieu de résidence ou
de naissance peut être recentré. L'arbre déduplique les ancêtres communs, rapproche
les branches et garde un espacement minimal. Molette/boutons : zoom ; glisser/flèches :
déplacement ; Ajuster/Home : cadrage ; Entrée/Espace sur un nœud : ouvrir sa fiche.

## Infertilité, choix sans enfant et mortalité

Trois probabilités configurables représentent des **parts à vie**, et non des
risques annuels : `demography.female_infertility_rate` (défaut 0,06),
`demography.male_infertility_rate` (0,04) et `society.childfree_rate` (0,03).
Ces valeurs sont des hypothèses modifiables du prototype, pas des prévalences
cliniques ou historiques validées. Les taux d'infertilité peuvent être surchargés
par peuple ; les trois paramètres peuvent évoluer par période.

Deux canaux de hash indépendants fixent les états par graine et identifiant :
infertilité biologique permanente et choix permanent de ne pas procréer. Ils
peuvent coexister. Les paramètres effectifs à la naissance sont employés ; les
fondateurs reçoivent ceux du début de simulation, périodes antérieures comprises.
Les états ne changent pas lors d'une migration ou d'un remariage. Les deux
partenaires doivent être fertiles et souhaiter procréer pour qu'une naissance
soit possible ; la régulation ne contourne jamais cette contrainte. D'autres
raisons peuvent conduire à une absence d'enfants : union absente, hasard, âge,
décès précoce ou événements. Le projet parental affiché ne promet pas de naissance.

Le calcul ajoute un seul octet temporaire par personne (59 octets de colonnes
runtime). Les états sont reconstruits lors de l'exploration : les champs
historiques binaires restent à 38 octets, sans nouvelle colonne SQLite. La version
`reproductive_traits_version=1` distingue les nouveaux mondes ; les anciennes
archives ne reçoivent pas d'états inventés. Les graines produisent donc une nouvelle
histoire lorsque ces probabilités non nulles sont utilisées. Les tests de
compatibilité historiques désactivent explicitement ces nouveaux paramètres.

La rubrique Démographie affiche une indication théorique d'âge moyen et médian
au décès et de mortalité avant 15 ans. Elle utilise le modèle global par sexe,
hors événements, mortalité maternelle, régulation et surcharges des peuples.
L'âge maximal n'est pas l'espérance de vie.

Le panneau Monde et les fiches affichent les décès effectivement simulés : moyenne,
médiane, tranches d'âge et proportion des décès avant 15 ans. Le risque de mourir
avant 15 ans parmi les naissances utilise uniquement celles suivies jusqu'au
15e anniversaire : fondateurs et cohortes récentes sont exclus. Une absence de
cohorte complète donne une valeur inconnue, jamais 0 %. Le calcul agrège les
colonnes par blocs d'un million et un petit histogramme, sans trier tous les morts.
Ces moyennes observées ne sont pas une estimation d'espérance de vie.


### Atlas visuel des habitants

Le panneau habitants est maintenant un canevas central de grande largeur, et non
une liste paginée. L'axe horizontal représente l'âge ; les lignes regroupent les
peuples et sexes. Les hommes sont carrés, les femmes circulaires, avec contours
colorés par peuple. Les cohortes montrent les effectifs exacts de **tous** les
résidents du lieu au dernier recensement. Un clic isole une cohorte ; des clics
successifs affinent la tranche d'âge jusqu'aux individus. Le zoom et le déplacement
permettent de parcourir les groupes ; un survol identifie le marqueur, un clic
ouvre la fiche et la généalogie. Les individus occupent des marqueurs de 34 pixels
au zoom initial, dans le panneau central. Le moteur de génération est inchangé.

Le filtre porte sur toute la population du lieu. L'API de lecture `resident-atlas`
aggrège les âges, sexes et peuples, puis retourne au maximum 1 200 individus
réels répartis de manière déterministe dans la sélection. Si celle-ci dépasse
cette limite, l'échantillon de marqueurs est explicitement signalé ; les effectifs
restent exhaustifs. On peut toujours ouvrir un identifiant exact avec la recherche.
Aucune pagination n'est présentée, aucune simulation supplémentaire n'est lancée.


La réduction du nombre de lieux virtuels conserve les capitales dont l'ID existe
encore. Les capitales supprimées passent en placement automatique déterministe,
avec un avis visible dans la configuration. Le champ capitale affiche la plage
d'IDs autorisée ; une valeur vide signifie automatique. Les cartes explicites et
le JSON restent validés strictement, sans modifier leurs références silencieusement.
