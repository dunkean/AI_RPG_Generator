# Revue et mesures du moteur de généalogie

État du prototype au 30 septembre 2026. La cohérence des histoires enregistrées
est prioritaire sur une vitesse obtenue en inventant une ascendance après coup.
Le scénario « 1 M initial → 50 M final, 1 000 ans » reste une cible de développement,
pas une performance acquise.

## Architecture implémentée

- État en colonnes NumPy contiguës, identifiants denses et accès direct aux parents.
- Unions compilées par Numba, pools CSR par lieu/peuple, recherche bornée, sans
  désactivation du contrôle de parenté à grande échelle. Marques réutilisées entre
  années au lieu de remettre tout l’historique ancestral à zéro à chaque appariement.
- Déplacements des foyers par lots ; garde maternelle/paternelle et activités compatibles.
- Scénarios politiques datés, souveraineté séparée de la résidence et de l’ascendance.
- Lieux dispersés ou concentrés par graine, Voronoï local, rendu canvas pour 500 lieux
  et plus, navigation vers chaque lieu, couches effectifs/croissance/flux/nations.
- Recensements tous les 10 ans par défaut ; événements individuels exactement datés.
- Export binaire : 21 B/personne dans le cas courant, 15 B/union, 11 B/migration.
  Dates relatives, lieux par slots, IDs implicites, ascendants par accès mémoire mappée.

Les unions, divorces, veuvages, remariages, naissances et migrations restent des
événements réellement simulés. L’adultère n’est pas modélisé à cette étape. La
parenté est garantie seulement dans l’ascendance connue et la profondeur configurée.
Les taux sont des paramètres de fiction ; aucune calibration historique n’est revendiquée.

## Mesures locales complètes

Windows 11, Intel i7-10700K, 64 Go RAM, Python 3.12.13, NumPy 2.5.3, Numba 0.67.0.
GPU RTX 3090 disponible mais **non utilisé**. Temps incluent simulation et archive
SQLite indexée ; import initial de Python et audit après publication ne sont pas
inclus. La compilation est mise en cache ; ce ne sont pas des résultats CUDA.

| Fondateurs / lieux / durée | Vivants finaux | Personnes conservées | Simulation | Simulation + archive | Pic RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 M / 500 / 25 ans, dispersé v3 | 1 000 018 | 1 722 266 | 26,8 s | 44,0 s | 321,2 Mio |
| 100 k / 500 / 1 000 ans, dispersé v3 | 348 040 | 5 817 116 | 247,1 s | 336,0 s | 542,2 Mio |
| 2 M / 500 / 25 ans, grille v2 | 1 977 802 | 3 435 980 | 53,9 s | 84,8 s | 523,4 Mio |

Les topologies et versions diffèrent : la troisième ligne n’est pas une comparaison
à configuration identique. Les runs ont les mêmes paramètres démographiques de
base ; ils ne cherchent pas à faire croître artificiellement la population jusqu’à
50 millions. Reproduire avec `python -m src.genealogy.benchmark --population ...
--places 500 --years ... --output output/genealogy/nom.sqlite`.
Les rapports `.benchmark.json` sont des productions ignorées par Git.

L’archive SQL v3 du million occupe 156 319 744 octets. Son export complet compact,
avec 1 722 266 fiches, 535 174 unions et 395 778 déplacements, occupe **51 974 083
octets**. Le gain porte sur les données exportées, pas encore sur le coût d’écriture
SQL préalable. Les individus seuls représentent 36 167 586 octets.

## Revues demandées et corrections

GPT-6 Sol en xhigh a audité les invariants et le code. Claude Opus 5.5 a été lancé
localement pour revoir la stratégie, les noyaux et la prochaine architecture.

L’audit indépendant de l’archive 2 M a vérifié :

- 3 435 980 fiches : parents antérieurs aux enfants, dates ordonnées, lieux de décès.
- 1 435 980 naissances : parents vivants, sexes/âges admissibles, union active.
- 1 064 919 unions : pas de chevauchement, aucun ancêtre commun dans les 3 niveaux
  configurés. Les ancêtres des fondateurs restent inconnus.
- 771 143 déplacements : chaînes de résidence cohérentes et bilan de chaque lieu.
- 12 500 site-années : conservation exacte des effectifs et des flux.

Les corrections issues des revues incluent :

- capacité du pilote rapportée au nombre de fondateurs de la simulation complète,
  itération et convergence enregistrée ; une cible reste une estimation déclarée ;
- distribution d’âge fondatrice corrigée, différenciée selon la mortalité par sexe ;
- un seul appel aux règles de migration pour l’ensemble des membres adultes du foyer ;
- règles du pilote copiées pour ne pas transmettre leur état au run réel ;
- validation des âges de mariage des peuples contre chaque période effective ;
- croissance d’un peuple comparée à son propre recensement initial ;
- capitales implicites invariantes à l’ordre des lieux explicites ;
- territoires explicites ou overrides sur une partition implicite, au choix ;
- frontière de migration fermée respectée aussi pour les déplacements conjugaux ;
- parcours BFS des ascendants compacts, pour ne pas perdre une branche lors d’un
  effondrement de pedigree ;
- crise dessinée à sa date réelle, même entre deux recensements décennaux.

Les tests couvrent également 500 lieux réellement sauvegardés et affichés,
recensements finaux hors intervalle, moyennes annuelles/totaux de fenêtres,
annulation sans publication, champs compacts élargis et ouverture automatique
du monde demandé. Le contrôle navigateur utilise Edge headless, vérifie une
création de nation datée et l’absence d’erreurs JavaScript.

## Voie retenue pour 50 millions / 1 000 ans

Les revues convergent : les cohortes seules ne déterminent pas les familles.
Des parents tirés indépendamment à la lecture peuvent violer espacement, unions,
fratries et contrôle de parenté, même avec un hash reproductible. Cette méthode
n’est donc pas présentée comme une généalogie exacte.

Le prochain backend détaillé doit prendre les décisions familiales pendant la
simulation, stocker les unions/fratries en blocs, conserver les parents archivés
et séparer les champs actifs des vivants. Les décisions biologiques et politiques
restent enregistrées ; noms/descriptions peuvent être produits à la demande.
Un RNG adressable par personne/année/processus permettra les noyaux parallèles.
Le GPU devra être validé contre un oracle CPU sur les mêmes règles avant toute
promesse de performance. Les décisions de matching parallèles devront être
versionnées et comparées statistiquement au matching séquentiel actuel.

Une autre offre possible est un moteur macro par cohortes, avec marchés
matrimoniaux et foyers agrégés, puis des familles détaillées synthétiques
représentatives. Il devra être explicitement distinct du monde exhaustif. Un
échantillon devra garder une densité locale plausible et des entrants conformes
aux flux, et ne pas simplement disperser 1/1000 des habitants sur toute la carte.
**Ce moteur macro et ce couplage d’échantillonnage ne sont pas implémentés.**

Le mode détaillé actuel conserve encore tous les morts en RAM. Le studio utilise
désormais des buffers binaires en mémoire pour le calcul et l’exploration. Il ne démontre pas 50 millions sur un millénaire en une ou dix
minutes. Le benchmark 1 000 ans mesure une chronologie complète de 100 000
fondateurs, non un substitut au benchmark cible.


## Revue de la phase mémoire et optimisation CPU

Sol 6 xhigh et Claude Opus 5.5 (CLI local, lecture seule) ont revu la stratégie
et les changements. Les priorités retenues : éliminer les objets Python par
événement et SQLite pendant le calcul, conserver une interface d'exploration
équivalente, préserver l'ordre stable et les tirages aléatoires, mesurer le moteur
séparément des écritures. Les réductions entières du recensement sont parallèles ;
le matching reste séquentiel. Des empreintes de la version a92216d couvrent tous
les champs et événements humains/fantasy ; les tests RAM/SQLite vérifient les
fonctions d'exploration, y compris backend de référence, migrations et remariages.

Les remarques Opus corrigées comprennent le libellé de progression, le nombre
de mondes conservés en RAM, les colonnes temporaires flottantes, la libération
progressive des champs de travail, l'index des seuls résidents vivants, la lecture
de résidence sans reconstruction de toute la famille et l'index sans duplication
des valeurs triées. Le studio sans écriture est intentionnel ; la commande de
sauvegarde SQLite demeure explicite. Les premiers clics peuvent encore construire
un index de parents/unions/migrations ; ces index sont ensuite réutilisés.

Le cache technique de compilation ne constitue pas une archive de simulation.
Aucune promesse de performance à 50 millions sur 1 000 ans n'est faite à partir
des benchmarks réduits.


Mesures finales, graine 42 / 500 lieux : 1 million de fondateurs sur 25 ans en
10,16 s contre 44,0 s auparavant (×4,33), et 100 000 fondateurs sur 1 000 ans en
71,62 s contre 336,0 s (×4,69). Les populations finales sont respectivement
1 000 018 et 348 040, les historiques 1 722 266 et 5 817 116 personnes. Zéro
écriture de données de simulation. Le premier accès indexé à une personne prend
0,31 / 1,48 s ; ces coûts ne sont pas masqués dans les temps du calcul.

Validation : 236 tests Python, Ruff du module et tests dédiés, et parcours Edge
headless du studio final (graine, 500 lieux, chronologie, configuration, exploration,
mobile, protection contre les doubles soumissions). Les empreintes couvrent aussi
une carte explicite à IDs non triés, crise, migrations et divorces renforcés.
Les scénarios avec règles personnalisées, calibration et rétention du monde actif
sont comparés au chemin SQLite de compatibilité.


## Remplacement de la calibration par une régulation en un run

À la demande de l'utilisateur, les pilotes sont supprimés. Les fondateurs restent
fixes ; le plancher déclenche une natalité dynamique de récupération, et la cible
est un plafond strict régulé par les décès. Les crises peuvent faire passer sous
le plancher et leurs effets restent enregistrés. Sol a relu le contrôleur et a
signalé qu'une hausse de natalité pendant une crise pourrait annuler une baisse
partielle de fécondité : la compensation est donc suspendue pendant un événement
nuisible, puis reprend après. La hausse est plafonnée et garde les contraintes
biologiques. Le quota mortel conserve tous les décès naturels et ajoute seulement
le nombre nécessaire au plafond, avec risques pondérés et dates exactes.

Le CLI Opus 5.5 a été lancé pour cette nouvelle revue, mais a renvoyé 429 / quota
hebdomadaire atteint, sans consommer de tokens de revue. Cette version n'est donc
pas présentée comme relue par Opus. La validation principale couvre un run unique,
plafond strict, mortalité de crise conservée, récupération biologique, déterminisme,
compatibilité des anciens scénarios et l'explorateur. Les tests de la version
précédente restent pertinents pour le moteur sans régulation.
