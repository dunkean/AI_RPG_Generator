# Revue et mesures du prototype de généalogie

## Relectures demandées

Le prototype a été relu par **GPT-6 Sol, effort xhigh**, et par
**Claude Opus 5.5**, lancé avec le CLI local `claude`, en lecture seule.
Les deux ont d'abord critiqué la stratégie, puis relu l'implémentation.
Sol a aussi exécuté des scénarios et des contrôles indépendants ; Opus a
analysé le code, sans exécuter les tests. Les verdicts valent pour ce
prototype et ne constituent pas une validation démographique historique.

Les derniers verdicts n'identifient plus de défaut de correction bloquant.
Les quatre points mineurs de la dernière revue Opus ont été corrigés ou
explicités : flux aléatoires des extensions, départ des couples avec maturités
différentes, lecture répétée de la configuration et sens relatif des affinités.

## Corrections apportées à partir des revues

| Problème signalé | Réponse dans le prototype |
| --- | --- |
| Parenté désactivée au-delà de 200 000 personnes dans l'ancien hybride | Contrôle borné, toujours actif, accès direct aux parents |
| Population poussée artificiellement vers une cible | Pilote ajustant les fondateurs ; écart et statut de réussite explicites |
| Capacité d'une petite carte incompatible avec une cible massive | Capacités proportionnelles en mode `scale`, cartes fournies comprises ; mode `fixed` explicite |
| Couples séparés par migrations indépendantes | Un seul tirage de départ par couple, avec dépendants et garde maternelle |
| Recherche aléatoire pénalisant les peuples minoritaires | Bassins de candidats compatibles par lieu et peuple |
| Croisements impossibles à cause des écarts d'âge humains | Bornes par peuple et écart autorisé par paire |
| Mortalité et fécondité identiques pour elfes et humains | Tables et fenêtres par peuple, profils de longue vie configurables |
| Épidémies exemptant les personnes de plus de 120 ans | Borne par défaut à 2 000 ans ; filtres explicites |
| Confusion entre date négative et absence de décès | Sentinelle hors calendrier, convertie en `NULL` |
| Nouveau-nés exemptés du risque de décès annuel | Naissances avant mortalité et décès de même année conservés |
| Périodes réinitialisant les paramètres absents | Modifications partielles cumulatives, validées après fusion |
| Matrice dense des distances et scans annuels des morts | Graphe spatial creux ; indices vivants ; cases spatiales |
| Boucles sur tous les habitants pour compter par lieu | Slots internes et `bincount` |
| Attribution des activités et peuples en O(lieux × personnes) | Segments triés pour les groupes de fondateurs et activités |
| Objets Python permanents pour les enfants à charge | Index de gardiens trié dans des tableaux |
| Conversion scalaire lente avant stockage | Insertion de colonnes converties par lots |
| Réinitialisation des tirages aléatoires d'extension | Flux persistants pendant l'année, séparés par processus |
| Origines et unions anciennes des fondateurs présentées comme connues | Données estimées et frontière historique signalées |

## Validation exécutée

La suite complète contient **197 tests**, tous passants : 169 tests existants
et 28 nouveaux tests du moteur. Ruff passe sur `src/genealogy` et
`tests/test_genealogy.py`. Le contrôle global `ruff check .` conserve
263 signalements dans les fichiers préexistants et les archives historiques ;
ils n'ont pas été corrigés dans ce changement.

Les contrôles indépendants de Sol ont notamment comparé toutes les cartes
annuelles d'un scénario à la reconstruction des résidences depuis les
migrations, vérifié plusieurs seeds avec de petites populations, des lieux
à identifiants discontinus, des unions hybrides et une épidémie sur elfes âgés.
Le défaut de sélection des minorités a été reproduit, puis sa correction
mesurée sur les mêmes scénarios.

Les endpoints HTTP ont été testés sur un serveur temporaire : lecture seule,
fiche, profondeur limitée, absence d'individu et erreurs d'entrée. La syntaxe
JavaScript a été vérifiée avec Node. Un test de la logique sous Node, avec
DOM simulé et vraie API locale, a aussi couvert les fiches, peuples, arbres,
recensements et listes d'habitants. Aucun navigateur contrôlable n'était
disponible dans la session : **la mise en page n'a pas été vérifiée visuellement**.

## Mesures de génération

Mesures locales sous Windows, Python 3.12 et NumPy 2.5.3 ; durée réelle,
incluant simulation, écriture et indexation SQLite. Elles ne garantissent
pas une durée sur une autre machine ni une extrapolation linéaire.

| Run | Fondateurs | Années | Lieux | Personnes enregistrées | Population finale | Temps total | Taille archive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fantasy final | 4 000 | 200 | 16 | 25 042 | 5 408 | 7,03 s | 2,80 Mio |
| Final, humain | 100 000 | 25 | 100 | 171 914 | 98 962 | 20,24 s | 14,18 Mio |
| Final, humain | 1 000 000 | 25 | 100 | 1 728 633 | 995 657 | 968,14 s (16,14 min) | 145,28 Mio |
| Référence pendant développement, humain | 1 000 000 | 25 | 100 | 1 739 812 | 1 001 960 | 1 026,97 s | 146,34 Mio |

Le grand run de référence précède les dernières optimisations du déplacement
et l'initialisation de la phase d'accouchement des fondateurs. Les effectifs
diffèrent donc du code final avec la même seed. La mesure séparée sur la version finale confirme
une croissance du temps supérieure au seul rapport des effectifs sur cette
machine ; ne pas extrapoler linéairement depuis le run à 100 000. Un profilage
à grande échelle reste nécessaire avant d’annoncer des durées pour plusieurs
millions sur plusieurs siècles.

Le grand fichier de référence a passé `PRAGMA quick_check`. Les 1 739 812
personnes et les 1 001 960 vivants correspondent aux diagnostics ; aucun
parent ne référence un identifiant postérieur à l'enfant. Les requêtes
d'ascendance fonctionnent sur cette archive sans charger toute la population.

Le cœur occupe **58 octets par personne enregistrée**, avec une réserve
allouée de 116 Mo dans le run d'un million. L'archive de référence représente
environ **88 octets par personne enregistrée**, index et événements compris.
La mémoire totale du processus inclut aussi les tableaux temporaires et
les événements de l'année : la réserve des personnes n'est pas une mesure
du pic de RAM.

## Limites et prochaines étapes

- Les taux restent des paramètres de fiction ajustables. Une vraie validation
  exige des cohortes, des tables de vie, la fécondité réalisée et des scénarios
  historiques documentés. La moyenne observée d'âge au décès n'est pas
  l'espérance de vie à la naissance.
- La cible est estimée par un seul pilote ; densité et marchés matrimoniaux
  peuvent rendre la croissance non linéaire. L'écart final est conservé.
- Les ancêtres des fondateurs sont inconnus ; les premiers couples sont
  artificiellement moins apparentés qu'une population déjà établie.
- Le moteur garde tous les individus en RAM et fait les unions dans une
  boucle Python bornée. Une prochaine optimisation importante serait un
  état de vie séparé de l'archive parentale et un appariement par lots.
- Les distances ignorent relief et routes. Les lieux sont statiques ; les
  adoptions, unions non reproductives non déclarées, grossesses explicites,
  carrières historiques et familles préexistantes ne sont pas simulées.
- L'API de règles et les métadonnées permettent des extensions, mais ce
  prototype ne remplace pas encore la génération de PNJ de l'étape 5.

Le guide [`genealogy.md`](genealogy.md) décrit les conventions et les
configurations pour éviter de confondre une possibilité de réglage avec une
garantie de réalisme ou de précision de cible.
