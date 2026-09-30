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

Depuis la racine du dépôt, sous PowerShell :

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Exemple humain : six générations conventionnelles de 25 ans, avec crises.
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

La cible n'ajoute pas des naissances artificielles. Un pilote estime le rapport
population finale/fondateurs, puis ajuste **le nombre initial de personnes**.
Cette estimation reste approximative, surtout si les petits marchés matrimoniaux,
capacités fixes ou fortes crises rendent la croissance non linéaire.
`calibration_population` augmente la taille du pilote ; `target_tolerance`
fixe la tolérance de rapport, par défaut 10 %. L'archive indique l'écart réel
et `target_status: within_tolerance` ou `outside_tolerance`. Elle ne prétend
pas réussir une cible manquée. Un pilote qui s'effondre presque entièrement
est refusé avant la génération complète.

Si `target_population` est renseigné, `initial_population` devient une
estimation remplacée par le pilote. Pour imposer les fondateurs, laisser la
cible vide et constater la population obtenue. Une extinction est un résultat
possible, conservé avec toute son histoire.

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
| `census`, `settlement_census` | Effectifs et événements par année et lieu |
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
enregistrées. Les unions restent une boucle Python à tentatives bornées.
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
Les mêmes règles s'appliquent au pilote et au run complet. Définir un
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
