# Worldbuilder — Étude et plan de conception d’un moteur social (organisations, familles, réseaux, histoire)

> Objectif : générer un monde peuplé d’individus dont les familles, réseaux, organisations et institutions sont cohérents entre eux, ancrés dans la géographie et capables de produire une histoire plausible et interrogeable (« pourquoi cette personne est là ? »).

---

## 0) Résumé exécutif

Un **moteur social** crédible pour worldbuilding est généralement **hybride** :

- **Top‑down (contraintes macro)** : garantir la cohérence globale (démographie, capacité économique, tailles de villes, besoins en main‑d’œuvre, lois).
- **Bottom‑up (agents / micro‑dynamique)** : créer la texture sociale (alliances, inimitiés, mobilité sociale, conflits, réseaux) et faire émerger des récits.

La clé de la diversité ne vient pas seulement du hasard, mais de **templates sociétaux** (institutions, règles de parenté, stratification, religion, politique) + **géographie/économie** + **réseaux multiplexes** (famille, travail, religion, patronage, crime, etc.).

Recommandation centrale : représenter le monde comme un **graphe de propriétés temporel** (property graph + event sourcing), afin d’assurer :
- traçabilité (« pourquoi ? ») ;
- simulation sur plusieurs échelles ;
- extraction narrative (chroniques, biographies).

---

## 1) Périmètre, hypothèses et critères de réussite

### 1.1 Échelle et granularité
Choisir explicitement (même si paramétrable) :

- **Population simulée** : 10³ (local) → 10⁵ (région) → 10⁷ (royaume) → 10⁹ (planète).
- **Niveau d’agentivité** :
  - *individuel* (tout le monde est un agent) ;
  - *mixte* (agents seulement pour élites + échantillon ; le reste agrégé) ;
  - *agrégé* (classes/foyers/organisations).
- **Profondeur temporelle** :
  - snapshot (état figé) ;
  - 10–50 ans (dynamiques sociales visibles) ;
  - 100–500 ans (mythes, cycles politiques, dynasties, migrations).

### 1.2 Critères de réussite (concrets)
- **Coherence checks** :
  - ménages plausibles (parents/enfants, âge, taille) ;
  - marché du travail cohérent avec économie locale ;
  - organisations cohérentes (capacité, recrutement, hiérarchie) ;
  - institutions respectées (mariage, héritage, castes, citoyenneté).
- **Diversité contrôlée** :
  - styles sociaux distincts par régions/cultures ;
  - variations intra‑culture (classes, sous‑cultures, minorités).
- **Interrogeabilité** :
  - répondre à des requêtes (“qui est allié à qui ?”, “qui hérite ?”, “qui a motivé ce coup d’État ?”).
- **Narrativité** :
  - produire des biographies et chroniques lisibles et plausibles.

---

## 2) Synthèse des approches existantes (patterns réutilisables)

> Ici, l’idée n’est pas de « copier », mais d’identifier des patterns de conception.

### 2.1 PCG (Procedural Content Generation) : macro → micro
- Génération guidée par **grammaires**, **contraintes**, **recherche** (search‑based).
- Pattern fréquent : *générer le cadre (géographie, villes) puis remplir (institutions, population).*  
Référence : livre PCG (Shaker et al., 2016)  
Source : https://link.springer.com/book/10.1007/978-3-319-42716-4

### 2.2 Simulation multi‑agents / “generative social science” : micro → macro
- Règles simples → structures émergentes (migrations, inégalités, conflits).
- Pattern : *agents + environnement + règles d’interaction + chocs exogènes* → historique.  
Référence classique (Sugarscape) : Epstein & Axtell  
Source : https://jasss.soc.surrey.ac.uk/12/1/6/appendixB/EpsteinAxtell1996.html

### 2.3 Populations synthétiques : base réaliste contrôlable
- Méthodes pour générer une population/ménages qui matchent des contraintes statistiques (âge, sexe, taille des foyers, etc.).
- Très utile pour démarrer avec un état “plausible”, même dans un monde non‑Terre (vous choisissez vos distributions).  
Exemple accessible : revue/approches sur populations synthétiques  
Source : https://pmc.ncbi.nlm.nih.gov/articles/PMC2809743/

### 2.4 Institutions comme objets de 1er ordre (règles “en usage”)
- Les comportements dépendent fortement des règles (héritage, mariage, justice, taxe, mobilité).
- Pattern : encoder explicitement les règles (DSL ou schéma) et les utiliser en validation + simulation.  
Institutional Grammar (ADICO, IAD…) :  
Source : https://institutionalgrammar.org/wp-content/uploads/2024/04/IG-1.0-codebook.pdf

### 2.5 Systèmes sociaux orientés “drama”
- Pour générer des scènes sociales riches (rivalités, romance, réputation, statut), on peut utiliser une logique “règles sociales + valeurs”.
- Référence : “Prom Week” / Comme il Faut (CiF)  
Source : https://www.fdg2013.org/program/papers/paper13_mccoy_etal.pdf

### 2.6 Diversité culturelle et réseaux sociaux
- Diffusion culturelle localisée → clusters/polarisation (Axelrod).  
Source : https://journals.sagepub.com/doi/10.1177/0022002797041002001
- Homophilie : les liens sociaux se forment selon la similarité (classe, culture, religion, métiers…).  
Source : https://www.jstor.org/stable/2678628
- Petits mondes (small‑world) : structures fréquentes et utiles comme baseline.  
Source : https://www.nature.com/articles/30918

---

## 3) Proposition de cadre : “Social Stack” multi‑couches et multi‑échelles

### 3.1 Couches (et pourquoi elles sont séparées)
1. **Géographie & mobilité**  
   - friction de déplacement, routes, goulots, rivières, cols, saisons
2. **Peuplement & économie**  
   - villages/villes, hinterland, production, échanges
3. **Démographie**  
   - tables de mortalité/fertilité (par espèce), migrations
4. **Foyers & parenté**  
   - ménages, lignées, résidence post‑mariage, alliances
5. **Réseaux multiplexes**  
   - famille, voisinage, travail, religion, patronage, crime, politique
6. **Organisations**  
   - guildes, temples, armées, maisons nobles, entreprises, factions
7. **Institutions (règles)**  
   - droit, héritage, mariage, statut, castes, citoyenneté, justice
8. **Histoire / chroniques**  
   - événements datés, causalité, extraction narrative

Séparer ces couches permet :
- de **contrôler** certaines propriétés (macro) tout en laissant émerger le reste (micro) ;
- de re‑générer une couche sans casser tout le monde ;
- d’avoir des “modes” : *génération snapshot* vs *simulation historique*.

### 3.2 Principe clé : hybride top‑down / bottom‑up
- Top‑down : impose des “targets” (population par ville, emplois par industrie, taille des organisations, etc.).
- Bottom‑up : agents qui prennent décisions (mariage, carrière, alliances), sous contraintes.

---

## 4) Workflow recommandé de génération (end‑to‑end)

### Phase 0 — Templates sociétaux (diversité par les règles)
Définir un **template** = bundle paramétrique :

- parenté : patrilinéaire / matrilinéaire / bilatérale ; clans segmentaires
- mariage : mono/polygynie/polyandrie ; endogamie/exogamie ; interdits
- résidence : patrilocal / matrilocal / néolocal
- héritage : primogéniture / partage / restrictions de genre
- stratification : castes/classes ; esclavage/servage ; citoyenneté
- gouvernance : centralisé / féodal / cités‑états ; bureaucratie
- religion : monopole / pluralisme ; conversion ; tabous
- violence : vendetta permise ? duel légal ? justice privée ?

**Suggestion** : templates hiérarchiques :
- *species_template* (biologie + cognition + reproduction)
- *culture_template* (normes + règles + valeurs)
- *polity_template* (institutions publiques)

### Phase 1 — Géographie → villes → économie squelette
- générer ressources & contraintes (arable, mines, eau, risques)
- placer villes selon attracteurs (eau + routes + ressources)
- assigner profils économiques (agri / commerce / mine / port / pèlerinage)

### Phase 2 — Population synthétique cohérente (individus + ménages)
- générer individus (âge, sexe, espèce, culture, classe, traits)
- assembler en ménages via contraintes :
  - tailles de foyers
  - gaps d’âge conjoints
  - spacing naissances
  - veuvage / remariage

But : obtenir une base “statistiquement plausible” avant d’ajouter le drama.

### Phase 3 — Parenté étendue + héritage + alliances
- construire lignées/clans depuis les ménages
- créer actifs (terres, ateliers, titres) et liens d’héritage
- générer alliances matrimoniales selon règles + géographie (coût distance)

### Phase 4 — Réseaux multiplexes
Créer plusieurs graphes liés :
- **voisinage** : distance + triadic closure
- **affinité** : homophilie (culture, classe, religion, métier)
- **pouvoir** : patronage, clientélisme, hiérarchie orga
- **économie** : trade ties, dettes, contrats
- **crime** : complicité, rivalité

### Phase 5 — Organisations
- générer organisations à partir de l’économie + gouvernance :
  - temples, guildes, troupes, tribunaux, maisons nobles, marchés, écoles
- définir **rôles** (slots) et règles de recrutement
- assigner membres et hiérarchie

### Phase 6 — Simulation historique (optionnel mais puissant)
- exécuter 1–N années :
  - naissances/décès
  - mariages/divorces
  - promotions/déclassements
  - conflits locaux (vendetta, guerre, schisme)
  - chocs exogènes (famine, peste, découverte)

Output : graphe + événements + chroniques.

---

## 5) Représentation et architecture de données

### 5.1 Graphe temporel + event sourcing (recommandé)
**Nœuds** : Person, Household, Organization, Place, Asset, Event  
**Arêtes** (datées) : parent_of, married_to, member_of, employed_by, patron_of, allied_with, owns, rivals_with…

Pourquoi :
- les requêtes “sociales” sont naturellement des parcours de graphe ;
- la temporalité (évolution) est plus simple via événements ;
- on peut expliquer/justifier chaque état.

### 5.2 Multiplex
Éviter un “gros graphe unique” sans types :  
Chaque relation appartient à une **couche** (kinship, work, religion, politics, crime).  
On peut :
- stocker tout dans un seul graph store avec un champ `layer`
- ou stocker plusieurs graphes et des liens inter‑couches.

### 5.3 Institutions = règles explicites
Deux rôles :
- **validation** : empêcher incohérences (mariage illégal, héritage impossible…)
- **simulation** : déterminer transitions (qui peut entrer dans la guilde ? qui peut hériter ?)

Implémentation :
- DSL minimal (conditions → effets)
- ou schéma JSON “rule objects”.

---

## 6) Mécanismes clés pour “complexité + contrôle”

### 6.1 Trois “dials” de contrôle
1. **Contraintes dures** : capacité nourriture/logement, règles légales, mobilité.
2. **Distributions** : traits, préférences, aléas (soft constraints).
3. **Templates** : la diversité vient surtout des institutions.

### 6.2 Cohérence multi‑échelle
Toujours faire passer des objectifs macro vers micro :
- population par ville → ménages → individus ;
- emplois par industrie → organisations → rôles → affectations ;
- fiscalité/justice → institutions → incitations individuelles.

### 6.3 Patchs de stabilité
Sans précautions, les simulations dérivent. Prévoir :
- “rebalancing” (soft) : ajuster migrations/emplois vers targets ;
- “caps” : limiter explosivité (guerres trop fréquentes, natalité trop haute) ;
- “validation gates” : tests automatiques de plausibilité.

---

## 7) Évaluation (comme un vrai projet de recherche)

### 7.1 Métriques quantitatives
- démographie : pyramide des âges, ratios dépendance
- ménages : distribution tailles, gaps conjoints, multi‑génération
- réseaux : clustering, distance moyenne, distributions degré, homophilie
- organisations : tailles, turnover, vacance de rôles
- mobilité : flux vs distance/friction, taux urbanisation

### 7.2 Métriques qualitatives
- biographies cohérentes (événements explicables)
- chroniques lisibles (causalité)
- alignement récit ↔ institutions (ex : héritage motive conflits seulement si héritage “fait sens”)

---

## 8) Plan de travail (stades et livrables)

1. **Cadre + templates sociétaux (MVP concept)**  
   - schéma JSON templates  
   - 5–10 templates variés

2. **MVP population + ménages + parenté**  
   - génération snapshot  
   - requêtes kinship (héritiers, cousins, alliances)

3. **Institutions et règles minimales**  
   - mariage/héritage/citoyenneté (validation + transitions)

4. **Organisations et rôles**  
   - temples/guildes/armée + recrutement

5. **Réseaux multiplexes**  
   - voisinage + travail + patronage + religion

6. **Simulation historique et extraction narrative**  
   - event log + chroniques

7. **Harness de validation**  
   - suite métriques + tests de non‑régression

---

## 9) Risques et mitigations

- **Explosion combinatoire** (trop d’agents)  
  → multi‑scale : simuler individus seulement là où nécessaire (élites, zones actives) ; agrégation ailleurs.
- **Incohérences sociales** (règles contradictoires)  
  → institutions explicites + validation gates.
- **Uniformité** (tout se ressemble)  
  → diversité via templates + géographie + stratification + multiplex networks.
- **Manque de “sens”**  
  → event sourcing + justification (provenance, règles, incitations).

---

## 10) Annexes : recommandations d’implémentation (techniques)

### 10.1 Formats et stockage
- Snapshot : Parquet/Arrow (analytique), JSONL (debug), ou SQLite.
- Graphe : Neo4j, ArangoDB, ou stockage custom (adjacency + indices) si performance.

### 10.2 Debuggabilité
- logs d’événements (EventLog) = source de vérité
- seed aléatoire persisté
- “replay” d’une simulation pour reproduire un bug

### 10.3 Extraction narrative
- résumer une suite d’événements en “phrases” :
  - naissance → filiation → apprentissage → mariage → promotion → conflit → mort
- produire chroniques par niveau : village / ville / royaume

---

## Sources (ancrages)
- PCG book : https://link.springer.com/book/10.1007/978-3-319-42716-4  
- Sugarscape (Epstein & Axtell) : https://jasss.soc.surrey.ac.uk/12/1/6/appendixB/EpsteinAxtell1996.html  
- Synthetic populations : https://pmc.ncbi.nlm.nih.gov/articles/PMC2809743/  
- Institutional Grammar codebook : https://institutionalgrammar.org/wp-content/uploads/2024/04/IG-1.0-codebook.pdf  
- Prom Week / CiF : https://www.fdg2013.org/program/papers/paper13_mccoy_etal.pdf  
- Axelrod culture diffusion : https://journals.sagepub.com/doi/10.1177/0022002797041002001  
- Homophily : https://www.jstor.org/stable/2678628  
- Small-world : https://www.nature.com/articles/30918  

---
