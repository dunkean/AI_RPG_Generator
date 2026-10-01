"use strict";

const $ = (id) => document.getElementById(id),
  NS = "http://www.w3.org/2000/svg",
  fmt = (n) => Number(n ?? 0).toLocaleString("fr-FR");

const el = (tag, value, cls) => {
  const e = document.createElement(tag);
  e.textContent = value ?? "";
  if (cls) e.className = cls;
  return e;
};

const svg = (tag, attrs, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  parent.append(e);
  return e;
};

const error = (e) => {
  $("error").hidden = false;
  $("error").textContent = e.message ?? String(e);
};

const safely =
  (fn) =>
  async (...args) => {
    try {
      $("error").hidden = true;
      await fn(...args);
    } catch (e) {
      error(e);
    }
  };

let readArchive = null,
  worldEpoch = 0;

const api = async (path, payload) => {
  if (
    payload === undefined &&
    /^(world|overview|config|map|person|lineage|residence|residents|resident-atlas|distributions)([?]|$)/.test(
      path,
    ) &&
    !/[?&]archive=/.test(path)
  )
    path +=
      (path.includes("?") ? "&" : "?") +
      "archive=" +
      encodeURIComponent(readArchive);
  const r = await fetch(
    "/api/" + path,
    payload === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
  );
  if (!r.ok) {
    let message;
    try {
      message = (await r.json()).error;
    } catch {
      message = "Requête refusée (" + r.status + ")";
    }
    throw Error(message);
  }
  return r.json();
};

const clone = (v) => JSON.parse(JSON.stringify(v));

function checkForm() {
  for (const i of document.querySelectorAll(
    "#configView input:not([type=file])",
  )) {
    if (!i.checkValidity()) {
      configTab(i.closest(".configPanel").id.replace("config-", ""));
      i.reportValidity();
      throw Error("Corrigez le champ invalide avant de générer ou exporter.");
    }
  }
}

let submittedJob = null,
  openedJob = null;
let presets,
  config,
  world,
  loadedConfig,
  person = null,
  lineage = [],
  chosenPlace = null,
  counts = [],
  coordinates = new Map(),
  mapEpoch = 0,
  personEpoch = 0,
  view = { x: 0, y: 0, w: 800, h: 500 },
  pollTimer;

let activeTab = "config";
function tab(which) {
  activeTab = which;
  document.querySelector("#exploreView h2").textContent =
    which === "individual" ? "Habitants & lignées" : "Le monde en mouvement";
  $("configView").hidden = which !== "config";
  $("exploreView").hidden = which === "config";
  $("globalView").hidden = which !== "explore";
  $("individualView").hidden = which !== "individual";
  for (const [id, key] of [
    ["tabConfig", "config"],
    ["tabExplore", "explore"],
    ["tabIndividual", "individual"],
  ]) {
    $(id).classList.toggle("active", which === key);
    $(id).setAttribute("aria-current", which === key ? "page" : "false");
  }
  const dock = which === "individual" ? $("localMapDock") : $("globalMapDock");
  dock.append(document.querySelector(".mapCard"));
  requestAnimationFrame(() => {
    resizeMap();
    paintMap();
    if (world && which === "explore") chart();
    if (treeAutoFit) fitTree();
    else applyTreeView();
  });
}
function configTab(key) {
  for (const b of document.querySelectorAll("[data-config]")) {
    b.classList.toggle("active", b.dataset.config === key);
    b.setAttribute("aria-current", b.dataset.config === key ? "page" : "false");
  }
  for (const panel of document.querySelectorAll(".configPanel"))
    panel.hidden = panel.id !== "config-" + key;
}
for (const b of document.querySelectorAll("[data-config]"))
  b.onclick = () => configTab(b.dataset.config);
$("tabIndividual").onclick = () => tab("individual");
$("openVillage").onclick = () => tab("individual");

const basics = {
  seed: "seed",
  startYear: "start_year",
  founders: "initial_population",
  target: "target_population",
  generations: "generations",
  generationYears: "generation_years",
  exactYears: "years",
  places: "virtual_settlements",
  spacing: "virtual_spacing",
  snapshotInterval: "snapshot_interval",
  targetMode: "target_mode",
  layout: "spatial_layout",
  capacityMode: "capacity_mode",
};

const demographic = [
  ["demography", "female_infertility_rate", "Infertilité · femmes", 0.01],
  ["demography", "male_infertility_rate", "Infertilité · hommes", 0.01],
  ["society", "childfree_rate", "Choix de ne pas avoir d’enfants", 0.01],
  ["demography", "fertility_peak", "Pic de fécondité", 0.01],
  ["demography", "birth_spacing", "Espacement des naissances · ans", 1],
  ["demography", "infant_mortality", "Mortalité infantile", 0.01],
  ["demography", "child_mortality", "Mortalité enfant", 0.001],
  ["demography", "adult_mortality", "Mortalité adulte", 0.001],
  ["society", "marriage_rate", "Taux de nouvelles unions", 0.01],
  ["society", "divorce_rate", "Taux de divorce", 0.001],
  ["society", "migration_rate", "Taux de migration", 0.001],
  ["society", "marriage_radius", "Rayon des unions", 1],
  ["society", "migration_radius", "Rayon des migrations", 1],
  ["society", "distance_scale", "Atténuation par la distance", 1],
  ["society", "kinship_depth", "Contrôle de parenté · générations", 1],
];

function inputCell(
  row,
  value,
  update,
  { type = "number", wide = false, nullable = false, placeholder = "" } = {},
) {
  const td = document.createElement("td"),
    i = document.createElement("input");
  i.type = type;
  i.value = value ?? "";
  i.step = "any";
  i.placeholder = placeholder;
  i.required = type === "number" && !nullable;
  if (wide) i.className = "wide";
  i.onchange = safely(() => {
    try {
      update(
        type === "number"
          ? nullable && !i.value
            ? null
            : Number(i.value)
          : i.value,
      );
      i.setCustomValidity("");
    } catch (e) {
      i.setCustomValidity(e.message);
      throw e;
    }
    syncPreview();
  });
  const heading = row.closest("table")?.querySelectorAll("th")[
    row.children.length
  ]?.textContent;
  i.setAttribute("aria-label", heading || "Valeur de la ligne");
  td.append(i);
  row.append(td);
}

function removeCell(row, list, index) {
  const td = document.createElement("td"),
    b = el("button", "×", "icon");
  b.title = "Supprimer cette ligne";
  b.onclick = () => {
    list.splice(index, 1);
    renderProfiles();
    syncPreview();
  };
  td.append(b);
  row.append(td);
}

function selectCell(row, value, choices, update) {
  const td = el("td"),
    select = el("select");
  for (const name of new Set([value, ...choices])) {
    const option = el("option", name);
    option.value = name;
    select.append(option);
  }
  select.value = value;
  select.onchange = () => {
    update(select.value);
    syncPreview();
  };
  td.append(select);
  row.append(td);
}
function activityCell(row, profile) {
  const td = el("td"),
    details = el("details", "", "weightEditor"),
    summary = el("summary");
  details.append(summary);
  td.append(details);
  row.append(td);
  function render() {
    summary.textContent = Object.keys(profile.activities).length + " activités";
    details
      .querySelectorAll(".weightRow, .addWeight")
      .forEach((e) => e.remove());
    for (const [key, value] of Object.entries(profile.activities)) {
      const line = el("div", "", "weightRow"),
        name = el("input"),
        weight = el("input"),
        remove = el("button", "×", "icon");
      name.value = key;
      name.setAttribute("aria-label", "Activité");
      weight.type = "number";
      weight.min = 0;
      weight.step = "any";
      weight.required = true;
      weight.value = value;
      weight.setAttribute("aria-label", "Poids de l’activité");
      name.onchange = safely(() => {
        const next = name.value.trim();
        if (!next || (next !== key && next in profile.activities)) {
          name.setCustomValidity("Nom unique et non vide requis");
          throw Error("Activité : nom unique et non vide requis.");
        }
        name.setCustomValidity("");
        profile.activities[next] = profile.activities[key];
        if (next !== key) delete profile.activities[key];
        render();
        syncPreview();
      });
      weight.onchange = () => {
        profile.activities[key] = Number(weight.value);
        syncPreview();
      };
      remove.title = "Supprimer l’activité";
      remove.onclick = () => {
        delete profile.activities[key];
        render();
        syncPreview();
      };
      line.append(name, weight, remove);
      details.append(line);
    }
    const add = el("button", "+ Activité", "addWeight icon");
    add.onclick = () => {
      let i = 1;
      while ("activité_" + i in profile.activities) i++;
      profile.activities["activité_" + i] = 1;
      render();
      syncPreview();
    };
    details.append(add);
  }
  render();
}
function renameRace(race, next) {
  next = next.trim();
  if (!next || config.races.some((r) => r !== race && r.name === next))
    throw Error("Le nom du peuple doit être unique et non vide.");
  const old = race.name;
  for (const c of config.crossbreeding) {
    c.parents = c.parents.map((n) => (n === old ? next : n));
    if (old in c.offspring) {
      c.offspring[next] = c.offspring[old];
      delete c.offspring[old];
    }
  }
  for (const item of [...config.settlements, ...config.settlement_types]) {
    if (old in (item.races || {})) {
      item.races[next] = item.races[old];
      delete item.races[old];
    }
  }
  for (const event of config.events)
    event.races = event.races.map((n) => (n === old ? next : n));
  race.name = next;
  renderCrossSummary();
}
function renderCrossSummary() {
  $("crossSummary").replaceChildren(
    ...config.crossbreeding.map((r) =>
      el(
        "span",
        r.parents.join(" × ") +
          " → " +
          Object.keys(r.offspring).join(", ") +
          " · affinité " +
          r.marriage_affinity,
        "tag",
      ),
    ),
  );
}
function renderProfiles() {
  $("nationProfiles").replaceChildren();
  config.nations.forEach((n, index) => {
    const row = el("tr");
    inputCell(
      row,
      n.name,
      (v) => {
        const next = v.trim(),
          old = n.name;
        if (
          !next ||
          config.nations.some((item) => item !== n && item.name === next)
        )
          throw Error("Nom de nation unique et non vide requis.");
        for (const contact of config.nation_contacts)
          contact.nations = contact.nations.map((name) =>
            name === old ? next : name,
          );
        n.name = next;
        renderProfiles();
      },
      { type: "text", wide: true },
    );
    inputCell(row, n.founded, (v) => (n.founded = v));
    inputCell(row, n.dissolved, (v) => (n.dissolved = v), { nullable: true });
    inputCell(row, n.capital, (v) => (n.capital = v), { nullable: true });
    removeCell(row, config.nations, index);
    $("nationProfiles").append(row);
  });
  $("contactProfiles").replaceChildren();
  config.nation_contacts.forEach((n, index) => {
    const row = el("tr");
    for (let i = 0; i < 2; i++)
      selectCell(
        row,
        n.nations[i],
        config.nations.map((n) => n.name),
        (v) => (n.nations[i] = v),
      );
    inputCell(row, n.start_year, (v) => (n.start_year = v));
    inputCell(row, n.end_year, (v) => (n.end_year = v), { nullable: true });
    for (const key of ["marriage_factor", "migration_factor"])
      inputCell(row, n[key], (v) => (n[key] = v));
    removeCell(row, config.nation_contacts, index);
    $("contactProfiles").append(row);
  });
  $("placeProfiles").replaceChildren();
  config.settlement_types.forEach((p, index) => {
    const row = document.createElement("tr");
    inputCell(row, p.kind, (v) => (p.kind = v), { type: "text", wide: true });
    for (const field of [
      "share",
      "minimum_count",
      "capacity",
      "initial_weight",
    ])
      inputCell(row, p[field], (v) => (p[field] = v));
    activityCell(row, p);
    removeCell(row, config.settlement_types, index);
    $("placeProfiles").append(row);
  });

  $("raceProfiles").replaceChildren();
  config.races.forEach((r, index) => {
    const row = document.createElement("tr");
    inputCell(row, r.name, (v) => renameRace(r, v), {
      type: "text",
      wide: true,
    });
    inputCell(row, r.initial_weight, (v) => (r.initial_weight = v));
    for (const field of [
      "max_age",
      "fertility_peak",
      "birth_spacing",
      "female_infertility_rate",
      "male_infertility_rate",
    ])
      inputCell(
        row,
        r.demography[field],
        (v) => {
          if (v === null) delete r.demography[field];
          else r.demography[field] = v;
        },
        { nullable: true, placeholder: "Hérite : " + config.demography[field] },
      );
    const td = el("td"),
      remove = el("button", "×", "icon");
    remove.title = "Supprimer le peuple";
    remove.onclick = safely(() => {
      if (config.races.length === 1)
        throw Error("Conservez au moins un peuple.");
      if (
        config.crossbreeding.some(
          (c) => c.parents.includes(r.name) || r.name in c.offspring,
        ) ||
        [...config.settlements, ...config.settlement_types].some(
          (p) => r.name in (p.races || {}),
        ) ||
        config.events.some((e) => e.races.includes(r.name))
      )
        throw Error(
          "Ce peuple est référencé dans des croisements, lieux ou événements. Retirez ces références dans le JSON avant de le supprimer.",
        );
      config.races.splice(index, 1);
      renderProfiles();
      syncPreview();
    });
    td.append(remove);
    row.append(td);
    $("raceProfiles").append(row);
  });

  renderCrossSummary();

  $("eventProfiles").replaceChildren();
  config.events.forEach((e, index) => {
    const row = document.createElement("tr");
    inputCell(row, e.name, (v) => (e.name = v), { type: "text", wide: true });
    for (const field of [
      "start_year",
      "end_year",
      "extra_mortality",
      "fertility_factor",
      "migration_factor",
    ])
      inputCell(row, e[field], (v) => (e[field] = v));
    inputCell(
      row,
      e.settlements.join(", "),
      (v) =>
        (e.settlements = v.trim()
          ? v.split(",").map((x) => {
              if (!/^\d+$/.test(x.trim()))
                throw Error("IDs : nombres séparés par des virgules");
              return Number(x);
            })
          : []),
      { type: "text" },
    );
    removeCell(row, config.events, index);
    $("eventProfiles").append(row);
  });
}

function populate(source) {
  config = clone(source);
  for (const [id, key] of Object.entries(basics))
    $(id).value = config[key] ?? "";
  $("demographicFields").replaceChildren();
  for (const [group, key, label, step] of demographic) {
    const wrap = el("div", "", "field"),
      id = group + "_" + key,
      l = el("label", label),
      i = document.createElement("input");
    l.htmlFor = id;
    i.id = id;
    i.type = "number";
    i.step = step;
    i.value = config[group][key];
    i.required = true;
    i.onchange = () => {
      config[group][key] = Number(i.value);
      renderProfiles();
      syncPreview();
    };
    if (key.includes("infertility") || key === "childfree_rate") {
      i.min = 0;
      i.max = 1;
      i.title =
        "Part des individus recevant cet état à vie, de 0 à 1. Ce n’est pas un taux annuel. Les deux partenaires doivent pouvoir et vouloir procréer.";
      wrap.append(el("small", "Part à vie · 0 à 1", "small"));
    }
    if (key === "infant_mortality")
      i.title =
        "Probabilité de décès durant l’année de naissance. Voir l’indication de survie ci-dessous.";
    if (key === "child_mortality")
      i.title =
        "Probabilité annuelle après l’année de naissance, jusqu’à l’âge enfant maximal configuré.";
    if (key === "adult_mortality")
      i.title =
        "Risque annuel de base, augmenté avec l’âge par le modèle de vieillissement.";
    wrap.append(l, i);
    $("demographicFields").append(wrap);
  }
  renderProfiles();
  syncPreview();
}

function setJsonDirty(flag) {
  for (const e of document.querySelectorAll(
    "#configView input:not([type=file]),#configView select,#configView .icon,#configView .addWeight,#addPlace,#addEvent,#addRace,#addNation,#addContact",
  ))
    e.disabled = flag;
  if (flag)
    $("configValidated").textContent =
      "Édition JSON : appliquer ou annuler pour retrouver les contrôles.";
}
$("configJson").oninput = () => setJsonDirty(true);
$("discardJson").onclick = () => syncPreview();
function syncPreview() {
  setJsonDirty(false);
  renderMortalityHint();
  for (const [key, list] of [
    ["places", config.settlement_types],
    ["races", config.races],
    ["events", config.events],
    ["nations", config.nations],
  ])
    $("count-" + key).textContent = list.length;
  for (const table of document.querySelectorAll(".configPanel table"))
    for (const row of table.querySelectorAll("tbody tr"))
      [...row.children].forEach((cell, index) =>
        cell
          .querySelector("input,select")
          ?.setAttribute(
            "aria-label",
            table.querySelectorAll("th")[index]?.textContent || "Valeur",
          ),
      );
  const years = config.years ?? config.generations * config.generation_years;
  $("previewYear").min = config.start_year;
  $("previewYear").max = config.start_year + years;
  if (
    !$("previewYear").value ||
    Number($("previewYear").value) < config.start_year ||
    Number($("previewYear").value) > config.start_year + years
  )
    $("previewYear").value = config.start_year;
  $("durationPreview").textContent = fmt(years) + " ans";
  $("yearsPreview").textContent =
    config.start_year + " → " + (config.start_year + years);
  $("placesPreview").textContent =
    fmt(config.settlements.length || config.virtual_settlements) + " lieux";
  $("typesPreview").textContent =
    new Set(
      (config.settlements.length
        ? config.settlements
        : config.settlement_types
      ).map((p) => p.kind),
    ).size + " types";
  $("populationPreview").textContent = fmt(config.initial_population);
  $("targetPreview").textContent = config.target_population
    ? (config.target_mode === "report"
        ? "Fondateurs fixés · cible indicative "
        : "Plafond · un seul calcul · ") + fmt(config.target_population)
    : "Sans plafond · régulation inactive";
  $("mapNotice").textContent = config.settlements.length
    ? "Carte explicite : nombre virtuel et profils ignorés. Modifier la carte dans le JSON."
    : "Carte virtuelle. Distances dans votre unité ; une génération est une durée.";
  if (world)
    $("mapNotice").textContent +=
      " Archive actuellement affichée : " +
      world.settlements.length +
      " lieux. Le résultat sera ouvert automatiquement si vous restez sur cette vue.";
  $("configJson").value = JSON.stringify(config, null, 2);
  $("configValidated").textContent = "";
  clearTimeout(previewTimer);
  previewTimer = setTimeout(() => refreshPreview(), 250);
}

for (const [id, key] of Object.entries(basics)) {
  $(id).required = !["target", "exactYears", "capacityMode"].includes(id);
  $(id).onchange = () => {
    config[key] = ["capacityMode", "targetMode"].includes(id)
      ? $(id).value
      : ["target", "exactYears"].includes(id) && !$(id).value
        ? null
        : id === "layout"
          ? $(id).value
          : Number($(id).value);
    if (id === "generations" || id === "generationYears") {
      config.years = null;
      $("exactYears").value = "";
    }
    syncPreview();
  };
}

$("preset").onchange = () => populate(presets[$("preset").value]);
$("randomSeed").onclick = () => {
  $("seed").value = crypto.getRandomValues(new Uint32Array(1))[0];
  $("seed").onchange();
};

$("addRace").onclick = () => {
  let name = "peuple_" + (config.races.length + 1);
  while (config.races.some((r) => r.name === name)) name += "_";
  config.races.push({ name, initial_weight: 1, demography: {}, metadata: {} });
  renderProfiles();
  syncPreview();
};
$("addPlace").onclick = () => {
  let kind = "village",
    i = 2;
  while (config.settlement_types.some((p) => p.kind === kind))
    kind = "village_" + i++;
  config.settlement_types.push({
    kind,
    share: 10,
    minimum_count: 0,
    capacity: 600,
    initial_weight: 1,
    activities: { agriculture: 1 },
    races: {},
    metadata: {},
  });
  renderProfiles();
  syncPreview();
};

$("addEvent").onclick = () => {
  config.events.push({
    name: "Nouvelle crise",
    start_year: config.start_year + 10,
    end_year: config.start_year + 12,
    settlements: [],
    mortality_factor: 1,
    extra_mortality: 0.01,
    fertility_factor: 0.8,
    migration_factor: 1.5,
    capacity_factor: 1,
    min_age: 0,
    max_age: 2000,
    sex: "all",
    races: [],
    metadata: {},
  });
  renderProfiles();
  syncPreview();
};

$("applyJson").onclick = safely(async () => {
  const validated = await api("validate", {
    scenario: JSON.parse($("configJson").value),
  });
  populate(validated.scenario);
  $("configValidated").textContent = "Configuration valide ✓";
});

$("exportButton").onclick = safely(async () => {
  checkForm();
  const validated = await api("validate", {
      scenario: JSON.parse($("configJson").value),
    }),
    url = URL.createObjectURL(
      new Blob([JSON.stringify(validated.scenario, null, 2)], {
        type: "application/json",
      }),
    ),
    a = document.createElement("a");
  a.href = url;
  a.download = "atlas-seed-" + validated.scenario.seed + ".json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

$("importButton").onclick = () => $("importFile").click();
$("importFile").onchange = safely(async () => {
  const file = $("importFile").files[0];
  if (!file) return;
  const validated = await api("validate", { yaml: await file.text() });
  populate(validated.scenario);
  $("preset").value = "custom";
  $("importFile").value = "";
});

$("tabConfig").onclick = () => tab("config");
$("tabExplore").onclick = () => tab("explore");

async function catalogue() {
  const preferred = readArchive,
    list = await api("archives");
  $("archives").replaceChildren(
    ...list.archives.map((a) => {
      const option = el(
        "option",
        (a.id === "initial"
          ? "Monde initial"
          : "Graine " + a.seed + " / " + a.id.slice(-6)) +
          " · " +
          fmt(a.summary.population) +
          " habitants · " +
          a.summary.end_year,
      );
      option.value = a.id;
      option.title = a.name;
      return option;
    }),
  );
  $("archives").value = list.archives.some((a) => a.id === preferred)
    ? preferred
    : list.active;
}

let generationSubmitting = false;
async function poll() {
  let status;
  try {
    status = await api("job");
  } catch {
    $("progressText").textContent =
      "Connexion interrompue · nouvelle tentative…";
    pollTimer = setTimeout(() => safely(poll)(), 1500);
    return;
  }
  $("generate").disabled = generationSubmitting || status.state === "running";
  $("cancelGeneration").hidden = status.state !== "running";
  $("progressBox").hidden = status.state === "idle";
  $("progressBox").dataset.state = status.state;
  $("progress").value = status.progress ?? 0;
  if (status.state === "running") {
    const phase = status.phase;
    $("progressText").textContent = phase + " · année " + status.year;
    $("progressCount").textContent =
      fmt(status.population) +
      " habitants · " +
      Math.round(status.progress * 100) +
      " %";
    pollTimer = setTimeout(() => safely(poll)(), 650);
  } else if (status.state === "complete") {
    $("progressText").textContent =
      "Monde généré · " + fmt(status.summary.population) + " habitants";
    $("progressCount").textContent =
      Number(status.summary.total_seconds).toFixed(1) + " s";
    await catalogue();
    $("openResult").hidden = false;
    const open = async () => {
      await api("select", { id: status.archive });
      $("archives").value = status.archive;
      await loadWorld();
      tab("explore");
      openedJob = status.id;
    };
    $("openResult").onclick = safely(open);
    if (
      status.id === submittedJob &&
      openedJob !== status.id &&
      !$("configView").hidden
    )
      await open();
  } else if (status.state === "cancelled") {
    $("progressText").textContent = "Calcul arrêté · aucune archive publiée";
  } else if (status.state === "failed") {
    $("progressText").textContent = "Génération interrompue";
    error(Error(status.error));
  }
}

$("cancelGeneration").onclick = safely(async () => {
  await api("cancel", {});
});
$("generate").onclick = safely(async () => {
  if (generationSubmitting) return;
  generationSubmitting = true;
  $("generate").disabled = true;
  $("openResult").hidden = true;
  try {
    checkForm();
    const validated = await api("validate", {
      scenario: JSON.parse($("configJson").value),
    });
    populate(validated.scenario);
    const job = await api("generate", { scenario: config });
    submittedJob = job.id;
    generationSubmitting = false;
    clearTimeout(pollTimer);
    await poll();
  } catch (e) {
    generationSubmitting = false;
    $("generate").disabled = false;
    throw e;
  }
});

$("refreshWorld").onclick = safely(async () => {
  await api("select", { id: $("archives").value });
  await loadWorld();
  tab("explore");
});
$("reuseConfig").onclick = safely(async () => {
  configTab("start");
  populate(await api("config"));
  tab("config");
});

const place = (id) => world.settlements.find((p) => p.id === id),
  placeName = (id) => place(id)?.name ?? "Inconnu",
  raceName = (id) => world.races.find((r) => r.id === id)?.name ?? String(id),
  activityName = (id) =>
    world.activities.find((a) => a.id === id)?.name ?? String(id);

const kindLabels = {
    metropolis: "Métropole",
    city: "Ville",
    town: "Bourg",
    village: "Village",
    hamlet: "Hameau",
    mining_village: "Village minier",
    port: "Port",
  },
  kindColors = {
    metropolis: "#b87a3a",
    city: "#b7974f",
    town: "#5c8c78",
    village: "#7f9c72",
    hamlet: "#a7b099",
    port: "#6485b1",
    mining_village: "#947c95",
  };

const kindLabel = (k) => kindLabels[k] ?? k.replaceAll("_", " "),
  kindColor = (k) => kindColors[k] ?? "#719896";

const racePalette = [
  "#9a653b",
  "#697cb7",
  "#4d937b",
  "#a76999",
  "#ae9c40",
  "#468fa1",
];
const raceColor = (id) => racePalette[(id ?? 0) % racePalette.length];
function personButton(p) {
  const b = el("button", "", "chip personChip");
  b.dataset.person = p.id;
  if (p.sex !== undefined) b.dataset.sex = p.sex;
  if (p.race !== undefined) b.dataset.race = p.race;
  b.style.setProperty("--race-color", raceColor(p.race));
  b.classList.toggle("selected", p.id === person?.id);
  b.append(
    el("span", p.sex === undefined ? "·" : p.sex ? "♀" : "♂", "sexBadge"),
    el("b", "#" + p.id),
  );
  if (p.race !== undefined) b.append(el("span", raceName(p.race), "raceBadge"));
  if (p.birth !== undefined)
    b.append(
      el(
        "small",
        p.birth +
          (p.death !== undefined && p.death !== null ? "–" + p.death : ""),
      ),
    );
  b.title =
    "Ouvrir l’individu #" +
    p.id +
    (p.birth !== undefined ? " · né en " + p.birth : "");
  b.onclick = safely(async () => {
    tab("individual");
    await selectPerson(p.id);
  });
  return b;
}

let mapAutoFit = true;
function setupMap() {
  mapAutoFit = true;
  const xs = world.settlements.map((p) => p.x),
    ys = world.settlements.map((p) => p.y),
    xmin = Math.min(...xs),
    ymin = Math.min(...ys),
    dx = Math.max(...xs) - xmin,
    dy = Math.max(...ys) - ymin,
    s = Math.min(750 / (dx || 1), 450 / (dy || 1));
  coordinates = new Map(
    world.settlements.map((p) => [
      p.id,
      [400 + (p.x - xmin - dx / 2) * s, 250 + (p.y - ymin - dy / 2) * s],
    ]),
  );
  mapCells = voronoiCells([...coordinates.values()], [0, 0, 800, 500]);
  view = { x: 0, y: 0, w: 800, h: 500 };
  resetMapView();
}

let mapCells = [],
  mapPopulation = new Map(),
  mapNations = new Map(),
  initialPopulation = new Map(),
  mapDistributions = { groups: {}, flows: [] },
  mapLocation = null,
  hoverPlace = null;
function canvasPoints(canvas, places) {
  const xs = places.map((p) => p.x),
    ys = places.map((p) => p.y),
    xmin = Math.min(...xs),
    ymin = Math.min(...ys),
    dx = Math.max(...xs) - xmin,
    dy = Math.max(...ys) - ymin,
    scale = Math.min(
      (canvas.width - 35) / (dx || 1),
      (canvas.height - 35) / (dy || 1),
    );
  return new Map(
    places.map((p) => [
      p.id,
      [
        canvas.width / 2 + (p.x - xmin - dx / 2) * scale,
        canvas.height / 2 + (p.y - ymin - dy / 2) * scale,
      ],
    ]),
  );
}
let previewTimer,
  previewEpoch = 0;
async function refreshPreview() {
  const request = ++previewEpoch;
  try {
    const preview = await api("preview", {
      scenario: config,
      year: Number($("previewYear").value),
    });
    if (request !== previewEpoch) return;
    const c = $("previewMap"),
      ctx = c.getContext("2d"),
      points = canvasPoints(c, preview.settlements);
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.fillStyle = "#edf0e5";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.strokeStyle = "#a6b6a5";
    ctx.lineWidth = 0.5;
    for (const poly of voronoiCells(
      [...points.values()],
      [0, 0, c.width, c.height],
    )) {
      if (!poly) continue;
      ctx.beginPath();
      poly.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.closePath();
      ctx.stroke();
    }
    const kinds = {};
    for (const p of preview.settlements) {
      kinds[p.kind] = (kinds[p.kind] || 0) + 1;
      const [x, y] = points.get(p.id);
      ctx.beginPath();
      ctx.arc(
        x,
        y,
        Math.max(1.2, 6 / Math.sqrt(preview.settlements.length / 10)),
        0,
        Math.PI * 2,
      );
      ctx.fillStyle =
        $("previewLayer").value === "nations"
          ? nationColor(p.nation)
          : kindColor(p.kind);
      ctx.fill();
    }
    $("previewStatus").textContent =
      preview.settlements.length +
      " lieux · graine " +
      preview.seed +
      " · année " +
      preview.year +
      " · " +
      Object.entries(kinds)
        .map(([k, n]) => kindLabel(k) + " " + n)
        .join(" / ");
    c.dataset.places = preview.settlements.length;
  } catch (e) {
    if (request !== previewEpoch) return;
    $("previewMap").getContext("2d").clearRect(0, 0, 400, 250);
    $("previewStatus").textContent = "Aperçu invalide : " + e.message;
  }
}
function mapAspect() {
  const box = $("map").getBoundingClientRect();
  return box.width && box.height ? box.width / box.height : 1.6;
}
function resizeMap() {
  if (!world || $("map").getBoundingClientRect().width === 0) return;
  if (mapAutoFit) {
    resetMapView();
    return;
  }
  const centerY = view.y + view.h / 2;
  view.h = view.w / mapAspect();
  view.y = centerY - view.h / 2;
  paintMap();
}
new ResizeObserver(resizeMap).observe($("map"));
function applyView() {
  resizeMap();
  paintMap();
}
function resetMapView() {
  mapAutoFit = true;
  const aspect = mapAspect(),
    w = Math.max(800, 500 * aspect),
    h = w / aspect;
  view = { x: (800 - w) / 2, y: (500 - h) / 2, w, h };
  paintMap();
}
function focusPlace(id) {
  mapAutoFit = false;
  const point = coordinates.get(id);
  if (!point) return;
  view.w = 200;
  view.h = view.w / mapAspect();
  view.x = point[0] - 100;
  view.y = point[1] - view.h / 2;
  paintMap();
}
$("locatePerson").onclick = safely(async () => {
  if (!person) return;
  const id = mapLocation ?? person.birth_place;
  await residents(id);
  focusPlace(id);
});
function zoom(factor) {
  mapAutoFit = false;
  const w = Math.max(40, Math.min(1600, view.w * factor)),
    h = w / mapAspect();
  view.x += (view.w - w) / 2;
  view.y += (view.h - h) / 2;
  view.w = w;
  view.h = h;
  paintMap();
}
$("zoomIn").onclick = () => zoom(0.8);
$("zoomOut").onclick = () => zoom(1.25);
$("resetMap").onclick = resetMapView;
$("map").addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    zoom(e.deltaY > 0 ? 1.15 : 0.87);
  },
  { passive: false },
);
function hitPlace(e) {
  if (!world) return null;
  const box = $("map").getBoundingClientRect(),
    x = view.x + ((e.clientX - box.left) * view.w) / box.width,
    y = view.y + ((e.clientY - box.top) * view.h) / box.height;
  let nearest = null,
    distance = Infinity;
  for (const p of world.settlements) {
    const point = coordinates.get(p.id),
      d = Math.hypot(x - point[0], y - point[1]);
    if (d < distance) {
      distance = d;
      nearest = p.id;
    }
  }
  return distance < Math.max(8, view.w / 80) ? nearest : null;
}
let drag = null;
$("map").onpointerdown = (e) => {
  drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false };
  $("map").setPointerCapture(e.pointerId);
};
$("map").onpointermove = (e) => {
  if (drag) {
    const dx = e.clientX - drag.x,
      dy = e.clientY - drag.y;
    drag.moved ||= Math.hypot(dx, dy) > 4;
    if (drag.moved) {
      mapAutoFit = false;
      const box = $("map").getBoundingClientRect();
      view.x = drag.vx - (dx * view.w) / box.width;
      view.y = drag.vy - (dy * view.h) / box.height;
      paintMap();
    }
  } else {
    hoverPlace = hitPlace(e);
    const p = place(hoverPlace);
    $("mapHover").textContent = p
      ? p.name +
        " · " +
        kindLabel(p.kind) +
        " · " +
        fmt(mapPopulation.get(p.id)) +
        " habitants · ID " +
        p.id
      : "Survoler un lieu pour lire son effectif ; cliquer pour explorer.";
  }
};
$("map").onpointerup = safely(async (e) => {
  const moved = drag?.moved;
  drag = null;
  if (!moved) {
    const id = hitPlace(e);
    if (id !== null) {
      await residents(id);
      paintMap();
    }
  }
});
$("map").onpointercancel = () => (drag = null);
function paintMap() {
  if (!world || !$("map").getContext) return;
  const c = $("map"),
    ctx = c.getContext("2d"),
    screenWidth = c.clientWidth || 800,
    sx = c.width / view.w,
    sy = c.height / view.h;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = "#edf0e5";
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.setTransform(sx, 0, 0, sy, -view.x * sx, -view.y * sy);
  ctx.lineWidth = view.w / 1500;
  ctx.strokeStyle = "#a6b6a5";
  renderMapLegend();
  const layer = $("mapLayer").value,
    max = Math.max(...mapPopulation.values(), 1),
    origins = new Set(lineage.map((p) => p.birth_place));
  for (let i = 0; i < mapCells.length; i++) {
    const polygon = mapCells[i];
    if (!polygon) continue;
    const p = world.settlements[i],
      pop = mapPopulation.get(p.id) || 0;
    ctx.fillStyle =
      layer === "population"
        ? pop
          ? "hsl(153 30% " +
            (94 - (32 * Math.log1p(pop)) / Math.log1p(max)) +
            "%)"
          : "#e5e9df"
        : layer === "growth"
          ? pop < (initialPopulation.get(p.id) || 0)
            ? "#edceca"
            : "#c7e1df"
          : layer === "nations"
            ? nationColor(mapNations.get(p.id) ?? -1)
            : "#e5e9df";
    ctx.beginPath();
    polygon.forEach(([x, y], j) => (j ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }
  if (layer === "flows") {
    const maxFlow = Math.max(
      ...mapDistributions.flows.map((f) => f.population),
      1,
    );
    for (const f of mapDistributions.flows) {
      const a = coordinates.get(f.origin),
        b = coordinates.get(f.destination);
      if (!a || !b) continue;
      ctx.strokeStyle = "#6485b188";
      ctx.lineWidth =
        ((0.4 + (2 * f.population) / maxFlow) * view.w) / screenWidth;
      ctx.beginPath();
      ctx.moveTo(...a);
      ctx.lineTo(...b);
      ctx.stroke();
    }
  }
  if (person && selectedYear() >= person.birth) {
    const path = [
      person.birth_place,
      ...person.migrations
        .filter((m) => m.year <= selectedYear())
        .map((m) => m.destination),
    ];
    ctx.strokeStyle = "#244e54";
    ctx.lineWidth = (1.8 * view.w) / screenWidth;
    ctx.setLineDash([(4 * view.w) / screenWidth, (4 * view.w) / screenWidth]);
    ctx.beginPath();
    path.forEach((id, i) => {
      const point = coordinates.get(id);
      if (point) {
        if (i === 0) ctx.moveTo(...point);
        else ctx.lineTo(...point);
      }
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }
  const labels = [];
  for (const p of world.settlements) {
    const [x, y] = coordinates.get(p.id),
      pop = mapPopulation.get(p.id) || 0,
      r = Math.max(
        1.8,
        (3 + 11 * Math.sqrt(pop / max)) *
          Math.min(1, 8 / Math.sqrt(world.settlements.length)),
      ),
      relative = pop / Math.max(initialPopulation.get(p.id) || 0, 1) - 1;
    let color = kindColor(p.kind);
    if (layer === "population")
      color = pop
        ? "hsl(153 37% " +
          (82 - (46 * Math.log1p(pop)) / Math.log1p(max)) +
          "%)"
        : "#adb8aa";
    if (layer === "growth") color = relative < 0 ? "#bb6460" : "#398c93";
    ctx.fillStyle = color;
    ctx.beginPath();
    if (["city", "metropolis", "town"].includes(p.kind))
      ctx.rect(x - r, y - r, r * 2, r * 2);
    else ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
    if (origins.has(p.id) || p.id === chosenPlace || p.id === mapLocation) {
      ctx.strokeStyle = origins.has(p.id) ? "#cc7845" : "#203c40";
      ctx.lineWidth = (1.2 * view.w) / screenWidth;
      ctx.beginPath();
      ctx.arc(x, y, r + (2 * view.w) / screenWidth, 0, Math.PI * 2);
      ctx.stroke();
    }
    if (
      world.settlements.length <= 64 ||
      view.w < 170 ||
      p.id === chosenPlace ||
      p.id === mapLocation
    )
      labels.push({ p, x, y, r, pop });
  }
  const occupied = [],
    unit = view.w / screenWidth;
  labels.sort(
    (a, b) =>
      Number(b.p.id === chosenPlace) - Number(a.p.id === chosenPlace) ||
      b.pop - a.pop,
  );
  ctx.textAlign = "center";
  for (const { p, x, y, r, pop } of labels) {
    ctx.font = 10 * unit + "px system-ui";
    const width = Math.max(ctx.measureText(p.name).width, 28 * unit),
      top = y + r + 2 * unit;
    const box = {
      left: x - width / 2 - 3 * unit,
      right: x + width / 2 + 3 * unit,
      top,
      bottom: top + 27 * unit,
    };
    if (
      box.right < view.x ||
      box.left > view.x + view.w ||
      box.bottom < view.y ||
      box.top > view.y + view.h
    )
      continue;
    if (
      occupied.some(
        (b) =>
          box.left < b.right &&
          box.right > b.left &&
          box.top < b.bottom &&
          box.bottom > b.top,
      )
    )
      continue;
    occupied.push(box);
    ctx.fillStyle = "#263f40";
    ctx.fillText(p.name, x, y + r + 12 * unit);
    ctx.font = 9 * unit + "px system-ui";
    ctx.fillText(fmt(pop), x, y + r + 23 * unit);
  }
  c.dataset.places = world.settlements.length;
  c.dataset.year = selectedYear();
  c.dataset.population = [...mapPopulation.values()].reduce((a, b) => a + b, 0);
}
async function drawMap() {
  const request = ++mapEpoch,
    y = selectedYear(),
    race = $("raceFilter").value;
  const [data, distributions, baseline] = await Promise.all([
    api("map?year=" + y + (race !== "" ? "&race=" + race : "")),
    api("distributions?year=" + y),
    api(
      "map?year=" +
        loadedConfig.start_year +
        (race !== "" ? "&race=" + race : ""),
    ),
  ]);
  if (request !== mapEpoch) return;
  counts = data;
  mapNations = new Map(data.map((p) => [p.settlement, p.nation]));
  initialPopulation = new Map(
    baseline.map((p) => [p.settlement, p.population]),
  );
  mapPopulation = new Map(data.map((p) => [p.settlement, p.population]));
  mapDistributions = distributions;
  mapLocation = null;
  if (
    person &&
    y >= person.history_known_from &&
    y >= person.birth &&
    (person.death === null || y < person.death)
  ) {
    mapLocation = person.birth_place;
    for (const m of person.migrations) {
      if (m.year > y) break;
      mapLocation = m.destination;
    }
  }
  $("residence").textContent = person
    ? mapLocation === null
      ? "Absent du recensement en " + y
      : "Résidence en " + y + " : " + placeName(mapLocation)
    : "";
  $("yearText").textContent = y;
  const h = world.history.find((h) => h.year === y);
  const historyToDate = world.history.filter((row) => row.year <= y);
  const metricValues = [
    [h?.population, "Habitants vivants · " + y],
    ...["births", "deaths", "marriages"].map((key, index) => [
      historyToDate.reduce((sum, row) => sum + row[key], 0),
      ["Naissances", "Décès", "Unions"][index] + " · cumul",
    ]),
  ];
  [...$("worldMetrics").children].forEach((card, index) => {
    card.querySelector("b").textContent = fmt(metricValues[index][0]);
    card.querySelector("span").textContent = metricValues[index][1];
  });
  $("yearStats").textContent =
    fmt(h?.population) +
    " habitants dans le monde · " +
    fmt(h?.births) +
    " naissances · " +
    fmt(h?.deaths) +
    " décès sur " +
    (h?.span || 1) +
    " an(s)" +
    (race !== ""
      ? " · carte filtrée : " +
        raceName(Number(race)) +
        " (" +
        fmt([...mapPopulation.values()].reduce((a, b) => a + b, 0)) +
        ")"
      : "");
  paintMap();
  drawRanking(mapPopulation, y);
  drawDistributions(distributions, y);
  chart();
  if (chosenPlace !== null)
    $("globalSelection").textContent =
      placeName(chosenPlace) +
      " · " +
      fmt(mapPopulation.get(chosenPlace)) +
      " habitants en " +
      y;
}
$("mapLayer").onchange = paintMap;
$("raceFilter").onchange = safely(drawMap);
$("placePicker").onchange = safely(async () => {
  await residents(Number($("placePicker").value));
  focusPlace(chosenPlace);
  paintMap();
});
function drawDistributions(value, y) {
  const age = $("ageChart"),
    composition = $("composition");
  age.replaceChildren();
  composition.replaceChildren();
  $("distributionYear").textContent = y;
  if (!value.available) {
    composition.append(
      el(
        "p",
        "Agrégats indisponibles dans cette ancienne archive. Régénérez pour les obtenir.",
        "small",
      ),
    );
    return;
  }
  const maxBand = Math.max(
      ...(value.groups.age_male || []).map((r) => r.category),
      ...(value.groups.age_female || []).map((r) => r.category),
      0,
    ),
    bandSize = Math.max(1, Math.ceil((maxBand + 1) / 25));
  const aggregate = (rows) => {
    const result = new Map();
    for (const r of rows) {
      const key = Math.floor(r.category / bandSize);
      result.set(key, (result.get(key) || 0) + r.population);
    }
    return result;
  };
  const males = aggregate(value.groups.age_male || []),
    females = aggregate(value.groups.age_female || []),
    bands = [...new Set([...males.keys(), ...females.keys()])].sort(
      (a, b) => b - a,
    ),
    maximum = Math.max(...males.values(), ...females.values(), 1),
    height = Math.max(240, bands.length * 17 + 40);
  age.setAttribute("viewBox", `0 0 700 ${height}`);
  age.style.height = Math.min(450, height) + "px";
  const maleLabel = svg(
    "text",
    {
      x: 160,
      y: 18,
      "text-anchor": "middle",
      fill: "#6485b1",
      "font-size": 12,
    },
    age,
  );
  maleLabel.textContent = "Hommes";
  const femaleLabel = svg(
    "text",
    {
      x: 530,
      y: 18,
      "text-anchor": "middle",
      fill: "#287366",
      "font-size": 12,
    },
    age,
  );
  femaleLabel.textContent = "Femmes";
  bands.forEach((band, i) => {
    const yy = 34 + i * 17,
      m = males.get(band) || 0,
      f = females.get(band) || 0;
    for (const [n, x, color] of [
      [m, 330 - (m / maximum) * 275, "#6485b1"],
      [f, 370, "#287366"],
    ]) {
      const rect = svg(
        "rect",
        { x, y: yy, width: (n / maximum) * 275, height: 12, fill: color },
        age,
      );
      svg("title", {}, rect).textContent =
        band * bandSize * 5 +
        "–" +
        (band * bandSize * 5 + bandSize * 5 - 1) +
        " ans : " +
        fmt(n);
    }
    const label = svg(
      "text",
      {
        x: 350,
        y: yy + 10,
        "text-anchor": "middle",
        fill: "#6e8178",
        "font-size": 9,
      },
      age,
    );
    label.textContent =
      band * bandSize * 5 + "–" + (band * bandSize * 5 + bandSize * 5 - 1);
  });
  for (const [kind, label, name] of [
    ["nation", "Nations", (i) => nationName(i - 1)],
    ["race", "Peuples", raceName],
    ["status", "Niveaux sociaux", (i) => "Niveau " + i],
    ["activity", "Activités", activityName],
  ]) {
    const section = el("div");
    section.append(el("h3", label));
    const rows = value.groups[kind] || [],
      total = rows.reduce((n, r) => n + r.population, 0);
    for (const r of rows) {
      const item = el("div", "", "compositionRow"),
        track = el("span", "", "track"),
        fill = el("span", "", "fill");
      fill.style.width = (r.population / Math.max(total, 1)) * 100 + "%";
      fill.style.background = kind === "race" ? "#6485b1" : "#287366";
      track.append(fill);
      item.append(
        el("span", name(r.category)),
        track,
        el(
          "b",
          fmt(r.population) +
            " · " +
            ((r.population / Math.max(total, 1)) * 100).toFixed(1) +
            " %",
        ),
      );
      section.append(item);
    }
    composition.append(section);
  }
}
function drawRanking(pop, y) {
  $("rankingYear").textContent = y;
  $("ranking").replaceChildren();
  const sorted = [...world.settlements]
      .sort((a, b) => (pop.get(b.id) || 0) - (pop.get(a.id) || 0))
      .slice(0, 20),
    max = Math.max(...sorted.map((p) => pop.get(p.id) || 0), 1);
  for (const p of sorted) {
    const b = el("button", "", "rank"),
      track = el("span", "", "track"),
      fill = el("span", "", "fill");
    fill.style.width = ((pop.get(p.id) || 0) / max) * 100 + "%";
    fill.style.background = kindColor(p.kind);
    track.append(fill);
    b.append(el("span", p.name), track, el("b", fmt(pop.get(p.id))));
    b.onclick = safely(async () => {
      await residents(p.id);
      await drawMap();
    });
    $("ranking").append(b);
  }
}

let residentsEpoch = 0,
  residentRows = [],
  atlas = null,
  atlasScope = null;
let atlasView = { x: 0, y: 0, scale: 1 },
  atlasHits = [],
  atlasDrag = null,
  atlasHover = null;
// The resident visualization owns a full-width workspace, rather than a sidebar list.
document
  .querySelector(".individualMain")
  .prepend(document.querySelector(".residentsCard"));
function atlasZoom(factor, x, y) {
  const canvas = $("residentCanvas"),
    px = x ?? canvas.clientWidth / 2,
    py = y ?? canvas.clientHeight / 2;
  const scale = Math.max(0.3, Math.min(5, atlasView.scale * factor));
  atlasView.x = px - ((px - atlasView.x) * scale) / atlasView.scale;
  atlasView.y = py - ((py - atlasView.y) * scale) / atlasView.scale;
  atlasView.scale = scale;
  renderResidents();
}
function renderResidents() {
  if (!atlas) return;
  const canvas = $("residentCanvas"),
    width = canvas.clientWidth || 1000,
    height = canvas.clientHeight || 420,
    pixel = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * pixel);
  canvas.height = Math.round(height * pixel);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(pixel, 0, 0, pixel, 0, 0);
  ctx.fillStyle = "#f5f7f1";
  ctx.fillRect(0, 0, width, height);
  ctx.translate(atlasView.x, atlasView.y);
  ctx.scale(atlasView.scale, atlasView.scale);
  atlasHits = [];
  const chartWidth = Math.max(width, 650),
    left = 95,
    span = chartWidth - left - 35;
  const min = atlasScope?.min_age ?? 0,
    max =
      atlasScope?.max_age ?? Math.max(80, ...atlas.groups.map((g) => g.age)),
    range = Math.max(1, max - min + 1);
  const detailed =
    !atlas.sampled || (atlasScope && atlasScope.min_age === atlasScope.max_age);
  // In the broad view, exact counts take priority over rendering millions of dots.
  const individuals = detailed && (atlasScope !== null || atlas.matched <= 180);
  const bandSize = atlasScope
      ? Math.max(1, Math.ceil((range * 65) / span))
      : Math.max(5, Math.ceil((range * 65) / span / 5) * 5),
    groups = new Map();
  for (const g of atlas.groups) {
    const age = min + Math.floor((g.age - min) / bandSize) * bandSize,
      key = `${g.race}:${g.sex}:${age}`;
    if (!groups.has(key))
      groups.set(key, { race: g.race, sex: g.sex, age, count: 0 });
    groups.get(key).count += g.count;
  }
  const races = [...new Set(atlas.groups.map((g) => g.race))].sort(
      (a, b) => a - b,
    ),
    maxCount = Math.max(1, ...[...groups.values()].map((g) => g.count));
  const xAge = (age) => left + ((age - min + 0.5) / range) * span;
  ctx.font = "11px system-ui";
  ctx.fillStyle = "#75857c";
  const tick = Math.max(1, Math.ceil(range / 12));
  for (let age = min; age <= max; age += tick) {
    const x = xAge(age);
    ctx.textAlign = "center";
    ctx.fillText(age + " ans", x, 25);
    ctx.strokeStyle = "#dce3d7";
    ctx.beginPath();
    ctx.moveTo(x, 40);
    ctx.lineTo(x, height / atlasView.scale + Math.abs(atlasView.y));
    ctx.stroke();
  }
  let top = 60;
  for (const race of races) {
    ctx.textAlign = "left";
    ctx.fillStyle = raceColor(race);
    ctx.font = "bold 12px system-ui";
    ctx.fillText(raceName(race), 8, top + 12);
    top += 26;
    for (const sex of [0, 1]) {
      const people = residentRows.filter(
          (p) => p.race === race && p.sex === sex,
        ),
        selectedGroups = [...groups.values()].filter(
          (g) => g.race === race && g.sex === sex,
        );
      if (!selectedGroups.length) continue;
      ctx.fillStyle = sex ? "#a15c87" : "#42799b";
      ctx.font = "13px system-ui";
      ctx.fillText(sex ? "♀ Femmes" : "♂ Hommes", 8, top + 35);
      if (individuals) {
        const buckets = new Map(),
          columnWidth = span / range,
          cols = Math.max(1, Math.floor(columnWidth / 42));
        for (const p of people) {
          const age = atlas.year - p.birth;
          if (!buckets.has(age)) buckets.set(age, []);
          buckets.get(age).push(p);
        }
        let rows = 1;
        for (const [age, items] of buckets) {
          rows = Math.max(rows, Math.ceil(items.length / cols));
          items.forEach((p, i) => {
            const col = i % cols,
              row = Math.floor(i / cols),
              x =
                xAge(age) + (col - (Math.min(cols, items.length) - 1) / 2) * 42,
              y = top + 26 + row * 44;
            const r = 17,
              selected = p.id === person?.id;
            ctx.fillStyle = sex ? "#eed7e5" : "#d5e7f1";
            ctx.strokeStyle = selected ? "#287366" : raceColor(race);
            ctx.lineWidth = selected ? 3 : 1.5;
            ctx.beginPath();
            if (sex) ctx.arc(x, y, r, 0, Math.PI * 2);
            else ctx.roundRect(x - r, y - r, r * 2, r * 2, 4);
            ctx.fill();
            ctx.stroke();
            ctx.textAlign = "center";
            ctx.fillStyle = sex ? "#98587e" : "#386b8d";
            ctx.font = "bold 12px system-ui";
            ctx.fillText(sex ? "♀" : "♂", x, y + 4);
            if (atlasView.scale >= 1.4) {
              ctx.font = "9px system-ui";
              ctx.fillStyle = "#304843";
              ctx.fillText("#" + p.id, x, y + 25);
            }
            atlasHits.push({ x, y, r: 20, person: p, age });
          });
        }
        top += rows * 44 + 30;
      } else {
        for (const g of selectedGroups) {
          const x = xAge(g.age + (bandSize - 1) / 2),
            y = top + 34,
            r = 16 + 18 * Math.sqrt(g.count / maxCount);
          ctx.fillStyle = sex ? "#e4c1d5" : "#b5d2e4";
          ctx.strokeStyle = raceColor(race);
          ctx.lineWidth = 2;
          ctx.beginPath();
          if (sex) ctx.arc(x, y, r, 0, Math.PI * 2);
          else ctx.roundRect(x - r, y - r, r * 2, r * 2, 6);
          ctx.fill();
          ctx.stroke();
          ctx.fillStyle = "#28464a";
          ctx.font = "bold 11px system-ui";
          ctx.textAlign = "center";
          ctx.fillText(fmt(g.count), x, y + 4);
          atlasHits.push({
            x,
            y,
            r: r + 3,
            group: { ...g, max_age: Math.min(max, g.age + bandSize - 1) },
          });
        }
        top += 80;
      }
    }
    ctx.strokeStyle = "#d5dfd0";
    ctx.beginPath();
    ctx.moveTo(8, top);
    ctx.lineTo(chartWidth - 20, top);
    ctx.stroke();
    top += 20;
  }
  if (!atlas.matched) {
    ctx.fillStyle = "#73837d";
    ctx.textAlign = "left";
    ctx.font = "14px system-ui";
    ctx.fillText("Aucun habitant dans cette sélection.", left, 100);
  }
  canvas.dataset.matched = atlas.matched;
  canvas.dataset.mode = individuals ? "individuals" : "cohorts";
  canvas.dataset.points = atlasHits.length;
  $("residentCount").textContent =
    fmt(atlas.matched) +
    " habitants / " +
    fmt(atlas.total) +
    " dans le lieu · " +
    (individuals
      ? atlas.sampled
        ? fmt(residentRows.length) +
          " individus représentatifs · effectifs exacts"
        : "un marqueur par individu"
      : "cohortes exhaustives · taille = effectif") +
    (atlasScope
      ? " · sélection " + atlasScope.min_age + "–" + atlasScope.max_age + " ans"
      : "");
}
function atlasHit(e) {
  const box = $("residentCanvas").getBoundingClientRect(),
    x = (e.clientX - box.left - atlasView.x) / atlasView.scale,
    y = (e.clientY - box.top - atlasView.y) / atlasView.scale;
  return (
    [...atlasHits].reverse().find((p) => Math.hypot(x - p.x, y - p.y) <= p.r) ||
    null
  );
}
$("residentCanvas").addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    const b = $("residentCanvas").getBoundingClientRect();
    atlasZoom(
      e.deltaY > 0 ? 0.87 : 1.15,
      e.clientX - b.left,
      e.clientY - b.top,
    );
  },
  { passive: false },
);
$("residentCanvas").onpointerdown = (e) => {
  atlasDrag = {
    x: e.clientX,
    y: e.clientY,
    vx: atlasView.x,
    vy: atlasView.y,
    moved: false,
  };
  $("residentCanvas").setPointerCapture(e.pointerId);
};
$("residentCanvas").onpointermove = (e) => {
  if (atlasDrag) {
    const dx = e.clientX - atlasDrag.x,
      dy = e.clientY - atlasDrag.y;
    atlasDrag.moved ||= Math.hypot(dx, dy) > 4;
    if (atlasDrag.moved) {
      atlasView.x = atlasDrag.vx + dx;
      atlasView.y = atlasDrag.vy + dy;
      renderResidents();
    }
    return;
  }
  atlasHover = atlasHit(e);
  const t = $("residentTooltip");
  t.hidden = !atlasHover;
  if (atlasHover) {
    const hit = atlasHover,
      p = hit.person || hit.group;
    t.textContent =
      (hit.person
        ? "#" + p.id + " · " + hit.age + " ans"
        : fmt(p.count) + " habitants · " + p.age + "–" + p.max_age + " ans") +
      " · " +
      (p.sex ? "♀ Femmes" : "♂ Hommes") +
      " · " +
      raceName(p.race);
    const b = $("residentCanvas").getBoundingClientRect();
    t.style.left = Math.min(e.clientX - b.left + 12, b.width - 235) + "px";
    t.style.top = Math.max(4, e.clientY - b.top - 48) + "px";
    $("residentReadout").textContent =
      t.textContent +
      (hit.person
        ? " · cliquer pour ouvrir la fiche"
        : " · cliquer pour isoler cette cohorte");
  }
};
$("residentCanvas").onpointerleave = () => ($("residentTooltip").hidden = true);
$("residentCanvas").onpointercancel = () => (atlasDrag = null);
$("residentCanvas").onpointerup = safely(async (e) => {
  const moved = atlasDrag?.moved;
  atlasDrag = null;
  if (moved) return;
  const hit = atlasHit(e);
  if (!hit) return;
  if (hit.person) {
    await selectPerson(hit.person.id);
    document
      .querySelector(".personCard")
      .scrollIntoView({ behavior: "smooth", block: "nearest" });
  } else {
    atlasScope = { min_age: hit.group.age, max_age: hit.group.max_age };
    $("residentRace").value = hit.group.race;
    $("residentSex").value = hit.group.sex;
    await residents(chosenPlace, false, true);
  }
});
$("residentCanvas").onkeydown = (e) => {
  if (
    ["+", "=", "-", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(
      e.key,
    )
  )
    e.preventDefault();
  if (["+", "="].includes(e.key)) atlasZoom(1.2);
  else if (e.key === "-") atlasZoom(0.8);
  else {
    atlasView.x += { ArrowLeft: 40, ArrowRight: -40 }[e.key] || 0;
    atlasView.y += { ArrowUp: 40, ArrowDown: -40 }[e.key] || 0;
    renderResidents();
  }
};
$("atlasZoomIn").onclick = () => atlasZoom(1.25);
$("atlasZoomOut").onclick = () => atlasZoom(0.8);
$("atlasReset").onclick = safely(async () => {
  atlasScope = null;
  $("residentSex").value = "";
  $("residentRace").value = "";
  await residents(chosenPlace, false, true);
});
$("residentSex").onchange = $("residentRace").onchange = safely(() =>
  residents(chosenPlace, false, true),
);
$("residentSearch").onkeydown = safely(async (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    const text = $("residentSearch").value.trim();
    if (!/^#?\d+$/.test(text)) throw Error("Saisir un identifiant numérique.");
    await selectPerson(Number(text.replace("#", "")));
    document
      .querySelector(".personCard")
      .scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});
new ResizeObserver(() => renderResidents()).observe($("residentCanvas"));
async function residents(id, append = false, preserve = false) {
  const request = ++residentsEpoch;
  if (chosenPlace !== id || !preserve) {
    atlasScope = null;
    $("residentSex").value = "";
    $("residentRace").value = "";
    $("residentSearch").value = "";
  }
  chosenPlace = id;
  atlasView = { x: 0, y: 0, scale: 1 };
  $("residentTooltip").hidden = true;
  const query = new URLSearchParams({ place: id });
  for (const [key, value] of Object.entries({
    ...atlasScope,
    sex: $("residentSex").value,
    race: $("residentRace").value,
  }))
    if (value !== "" && value !== null && value !== undefined)
      query.set(key, value);
  $("residentCount").textContent = "Lecture de la population…";
  const result = await api("resident-atlas?" + query);
  if (request !== residentsEpoch) return;
  atlas = result;
  residentRows = result.people;
  $("placePicker").value = id;
  $("placeTitle").textContent = placeName(id);
  $("placeDetail").textContent =
    kindLabel(place(id).kind) +
    " · population au dernier recensement (" +
    atlas.year +
    ")";
  $("globalSelection").textContent =
    placeName(id) +
    " · " +
    fmt(mapPopulation.get(id)) +
    " habitants en " +
    selectedYear();
  renderResidents();
}

function fact(label, value) {
  const f = el("div");
  f.append(el("span", label, "small"), el("b", value));
  return f;
}

let personTrail = [],
  personCursor = -1;
$("personBack").onclick = safely(() =>
  selectPerson(personTrail[personCursor - 1], false, personCursor - 1),
);
$("personForward").onclick = safely(() =>
  selectPerson(personTrail[personCursor + 1], false, personCursor + 1),
);
async function selectPerson(id, remember = true, cursor = null) {
  const request = ++personEpoch,
    selected = await api("person?id=" + id);
  if (request !== personEpoch) return;
  person = selected;
  if (cursor !== null) personCursor = cursor;
  else if (remember && personTrail[personCursor] !== id) {
    personTrail.splice(personCursor + 1);
    personTrail.push(id);
    personCursor = personTrail.length - 1;
  }
  $("personBack").disabled = personCursor <= 0;
  $("personForward").disabled = personCursor >= personTrail.length - 1;
  $("identity").value = id;
  document.querySelector(".personHead").dataset.sex = person.sex;
  document
    .querySelector(".personHead")
    .style.setProperty("--race-color", raceColor(person.race));
  renderResidents();
  $("personTitle").textContent =
    "#" + id + " · " + (person.sex ? "Femme" : "Homme");
  $("personTag").textContent =
    raceName(person.race) + " · lignée #" + person.family;
  $("personFacts").replaceChildren(
    fact(
      person.founder ? "Naissance estimée" : "Naissance",
      person.birth + " · " + placeName(person.birth_place),
    ),
    fact(
      "Décès",
      person.death === null
        ? "Vivant en " + world.summary.end_year
        : person.death + " · " + placeName(person.death_place),
    ),
    fact("Activité", activityName(person.activity)),
    fact("Niveau social", person.status),
  );
  $("personFacts").append(
    fact(
      "Projet parental",
      person.childfree === true
        ? "Choix de ne pas avoir d’enfants · à vie"
        : person.childfree === false
          ? "Peut souhaiter des enfants"
          : "Non simulé dans ce monde",
    ),
    fact(
      "Fertilité biologique",
      person.infertile === true
        ? "Infertile · état à vie"
        : person.infertile === false
          ? "Fertile selon le modèle"
          : "Non simulée dans ce monde",
    ),
  );
  if (person.death !== null)
    $("personFacts").append(
      fact("Âge au décès", person.death - person.birth + " ans"),
    );
  $("parents").replaceChildren(
    ...[person.father, person.mother].map((pid) =>
      pid === null
        ? el("span", "Inconnu", "tag")
        : personButton({ id: pid, sex: pid === person.father ? 0 : 1 }),
    ),
  );
  $("children").replaceChildren(...person.children.map(personButton));
  if (!person.children.length)
    $("children").append(el("span", "Aucun enfant enregistré", "small"));

  const events = [
    {
      year: person.birth,
      label: person.founder ? "Naissance estimée" : "Naissance",
      place: person.birth_place,
    },
  ];
  for (const u of person.unions) {
    events.push({
      year: u.start,
      label:
        (u.start === world.summary.start_year
          ? "Union observée avec #"
          : "Union avec #") + (u.male === id ? u.female : u.male),
      place: u.place,
      person: u.male === id ? u.female : u.male,
    });
    if (u.end !== null)
      events.push({
        year: u.end,
        label: u.reason === "divorce" ? "Divorce" : "Fin de l’union · décès",
        place: null,
      });
  }
  for (const m of person.migrations)
    events.push({
      year: m.year,
      label: "Migration depuis " + placeName(m.origin),
      place: m.destination,
    });
  for (const c of person.children)
    events.push({
      year: c.birth,
      label: "Naissance de l’enfant #" + c.id,
      place: c.birth_place,
      person: c.id,
    });
  if (person.death !== null)
    events.push({
      year: person.death,
      label: "Décès",
      place: person.death_place,
    });
  events.sort((a, b) => a.year - b.year);
  $("timeline").replaceChildren();
  for (const e of events) {
    const row = el("div", "", "event"),
      date = el("button", e.year),
      body = el("span", e.label);
    body.append(el("small", e.place === null ? "" : placeName(e.place)));
    if (e.person !== undefined) {
      body.style.cursor = "pointer";
      body.onclick = safely(() => selectPerson(e.person));
    }
    date.onclick = safely(async () => {
      $("year").value = nearestSnapshot(e.year);
      if (e.place !== null) {
        await residents(e.place);
        focusPlace(e.place);
      }
      await drawMap();
    });
    row.append(date, body);
    $("timeline").append(row);
  }
  await drawTree();
  await drawMap();
}

// Layered pedigree layout: shared ancestors have one node; sweeps bring related
// branches together and enforce a minimum horizontal gap within every generation.
let treeAutoFit = true;
let treeEpoch = 0,
  treeBounds = { w: 850, h: 300 },
  treeView = { x: 0, y: 0, w: 850, h: 300 },
  treeDrag = null;
function applyTreeView() {
  const box = $("treeViewport").getBoundingClientRect();
  if (box.width && box.height) {
    const cy = treeView.y + treeView.h / 2;
    treeView.h = (treeView.w * box.height) / box.width;
    treeView.y = cy - treeView.h / 2;
  }
  $("tree").setAttribute(
    "viewBox",
    `${treeView.x} ${treeView.y} ${treeView.w} ${treeView.h}`,
  );
  $("treeZoomLabel").textContent =
    Math.round(((box.width || 850) / treeView.w) * 100) + " %";
}
function fitTree() {
  treeAutoFit = true;
  const box = $("treeViewport").getBoundingClientRect(),
    ratio = (box.width || 850) / (box.height || 440);
  treeView.w = Math.max(
    treeBounds.w,
    treeBounds.h * ratio,
    (box.width || 850) / 1.15,
  );
  treeView.h = treeView.w / ratio;
  treeView.x = (treeBounds.w - treeView.w) / 2;
  treeView.y = (treeBounds.h - treeView.h) / 2;
  applyTreeView();
}
function zoomTree(factor, clientX, clientY) {
  treeAutoFit = false;
  const box = $("tree").getBoundingClientRect();
  const rx = clientX === undefined ? 0.5 : (clientX - box.left) / box.width,
    ry = clientY === undefined ? 0.5 : (clientY - box.top) / box.height;
  const w = Math.max(180, Math.min(1000000, treeView.w * factor)),
    h = (treeView.h * w) / treeView.w;
  treeView.x += (treeView.w - w) * rx;
  treeView.y += (treeView.h - h) * ry;
  treeView.w = w;
  treeView.h = h;
  applyTreeView();
}
$("treeFit").onclick = fitTree;
$("treeZoomIn").onclick = () => zoomTree(0.8);
$("treeZoomOut").onclick = () => zoomTree(1.25);
$("tree").addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    zoomTree(e.deltaY > 0 ? 1.12 : 0.89, e.clientX, e.clientY);
  },
  { passive: false },
);
$("tree").onpointerdown = (e) => {
  treeDrag = {
    x: e.clientX,
    y: e.clientY,
    vx: treeView.x,
    vy: treeView.y,
    moved: false,
  };
  $("tree").setPointerCapture(e.pointerId);
};
$("tree").onpointermove = (e) => {
  if (!treeDrag) return;
  const box = $("tree").getBoundingClientRect(),
    dx = e.clientX - treeDrag.x,
    dy = e.clientY - treeDrag.y;
  treeDrag.moved ||= Math.hypot(dx, dy) > 4;
  if (treeDrag.moved) {
    treeAutoFit = false;
    treeView.x = treeDrag.vx - (dx * treeView.w) / box.width;
    treeView.y = treeDrag.vy - (dy * treeView.h) / box.height;
    applyTreeView();
  }
};
$("tree").onpointerup = safely(async (e) => {
  const moved = treeDrag?.moved;
  treeDrag = null;
  // Pointer capture retargets pointerup; hit-test the released position to select a node.
  if (!moved) {
    const node = document
      .elementFromPoint(e.clientX, e.clientY)
      ?.closest(".treeNode");
    if (node) await selectPerson(Number(node.dataset.person));
  }
});
$("tree").onpointercancel = () => (treeDrag = null);
$("treeViewport").onkeydown = (e) => {
  if (
    [
      "+",
      "=",
      "-",
      "ArrowLeft",
      "ArrowRight",
      "ArrowUp",
      "ArrowDown",
      "Home",
    ].includes(e.key)
  )
    e.preventDefault();
  if (["+", "="].includes(e.key)) zoomTree(0.8);
  else if (e.key === "-") zoomTree(1.25);
  else if (e.key === "Home") fitTree();
  else {
    const dx = { ArrowLeft: -1, ArrowRight: 1 }[e.key] || 0,
      dy = { ArrowUp: -1, ArrowDown: 1 }[e.key] || 0;
    treeView.x += dx * treeView.w * 0.08;
    treeView.y += dy * treeView.h * 0.08;
    applyTreeView();
  }
};
new ResizeObserver(() => {
  if (activeTab === "individual") {
    if (treeAutoFit) fitTree();
    else applyTreeView();
  }
}).observe($("treeViewport"));
async function drawTree() {
  if (!person) return;
  const request = ++treeEpoch,
    identity = person.id,
    result = await api(
      `lineage?id=${identity}&depth=${$("depth").value}&direction=${$("direction").value}`,
    );
  if (request !== treeEpoch || person.id !== identity) return;
  lineage = result.people;
  const all = [{ ...person, generation: 0 }, ...lineage],
    byId = new Map(all.map((p) => [p.id, p])),
    levels = new Map(),
    neighbors = new Map(all.map((p) => [p.id, []]));
  for (const p of all) {
    if (!levels.has(p.generation)) levels.set(p.generation, []);
    levels.get(p.generation).push(p);
    for (const pid of [p.father, p.mother])
      if (byId.has(pid)) {
        neighbors.get(p.id).push(pid);
        neighbors.get(pid).push(p.id);
      }
  }
  const ordered = [...levels.keys()].sort((a, b) => a - b),
    gap = 184,
    rowHeight = 110,
    maxGeneration = Math.max(...ordered),
    positions = new Map();
  const width = Math.max(
    700,
    ...[...levels.values()].map((l) => l.length * gap + 80),
  );
  for (const items of levels.values())
    items.forEach((p, i) =>
      positions.set(p.id, width / 2 + (i - (items.length - 1) / 2) * gap),
    );
  for (let pass = 0; pass < 8; pass++) {
    for (const generation of pass % 2 ? [...ordered].reverse() : ordered) {
      const items = levels.get(generation);
      const wanted = (p) => {
        const adjacent = neighbors
          .get(p.id)
          .filter((id) =>
            pass % 2
              ? byId.get(id).generation > generation
              : byId.get(id).generation < generation,
          );
        return adjacent.length
          ? adjacent.reduce((sum, id) => sum + positions.get(id), 0) /
              adjacent.length
          : positions.get(p.id);
      };
      const desired = new Map(items.map((p) => [p.id, wanted(p)]));
      items.sort(
        (a, b) =>
          desired.get(a.id) - desired.get(b.id) || a.sex - b.sex || a.id - b.id,
      );
      let previous = -Infinity;
      const packed = items.map((p) => {
        const x = Math.max(desired.get(p.id), previous + gap);
        previous = x;
        return x;
      });
      const offset =
        packed.reduce((sum, x, i) => sum + x - desired.get(items[i].id), 0) /
        items.length;
      items.forEach((p, i) => positions.set(p.id, packed[i] - offset));
    }
  }
  const minX = Math.min(...positions.values()) - 92,
    maxX = Math.max(...positions.values()) + 92;
  treeBounds = {
    w: Math.max(400, maxX - minX + 60),
    h: (maxGeneration + 1) * rowHeight + 40,
  };
  const t = $("tree");
  t.replaceChildren();
  const points = new Map(
    all.map((p) => [
      p.id,
      [
        positions.get(p.id) - minX + 30,
        ($("direction").value === "ancestors"
          ? maxGeneration - p.generation
          : p.generation) *
          rowHeight +
          60,
      ],
    ]),
  );
  for (const generation of ordered) {
    const y =
      ($("direction").value === "ancestors"
        ? maxGeneration - generation
        : generation) *
        rowHeight +
      18;
    const label = svg(
      "text",
      { x: 12, y, fill: "#8b978d", "font-size": 10 },
      t,
    );
    label.textContent = generation ? "G" + generation : "Individu choisi";
  }
  for (const p of all)
    for (const pid of [p.father, p.mother]) {
      if (!points.has(pid)) continue;
      const a = points.get(p.id),
        b = points.get(pid),
        down = b[1] > a[1] ? 1 : -1,
        start = a[1] + down * 34,
        end = b[1] - down * 34,
        mid = (start + end) / 2;
      svg(
        "path",
        {
          d: `M ${a[0]} ${start} C ${a[0]} ${mid}, ${b[0]} ${mid}, ${b[0]} ${end}`,
          fill: "none",
          stroke: pid === p.mother ? "#c496ad" : "#92aec1",
          "stroke-width": 1.5,
        },
        t,
      );
    }
  for (const p of all) {
    const [x, y] = points.get(p.id),
      g = svg(
        "g",
        {
          transform: `translate(${x},${y})`,
          class: "treeNode",
          "data-person": p.id,
          "data-sex": p.sex,
          tabindex: 0,
          role: "button",
          "aria-label": `Individu ${p.id}, ${p.sex ? "femme" : "homme"}, ${raceName(p.race)}, né en ${p.birth}`,
        },
        t,
      );
    svg(
      "rect",
      {
        x: -82,
        y: -34,
        width: 164,
        height: 68,
        rx: 7,
        fill: p.id === person.id ? "#e2eee6" : "#fffefa",
        stroke: p.id === person.id ? "#287366" : "#cad4c6",
        "stroke-width": p.id === person.id ? 2.5 : 1,
      },
      g,
    );
    svg(
      "rect",
      {
        x: -81,
        y: -27,
        width: 4,
        height: 54,
        rx: 2,
        fill: p.sex ? "#a15c87" : "#42799b",
      },
      g,
    );
    svg("circle", { cx: 70, cy: -20, r: 4, fill: raceColor(p.race) }, g);
    const name = svg(
      "text",
      { x: -68, y: -12, fill: "#243c40", "font-size": 12, "font-weight": 650 },
      g,
    );
    name.textContent = (p.sex ? "♀" : "♂") + " #" + p.id;
    const date = svg(
      "text",
      { x: -68, y: 5, fill: "#6b7d73", "font-size": 10 },
      g,
    );
    date.textContent =
      p.birth +
      "–" +
      (p.death ?? "vivant") +
      " · " +
      raceName(p.race).slice(0, 15);
    const location = svg(
      "text",
      { x: -68, y: 22, fill: "#87948b", "font-size": 10 },
      g,
    );
    location.textContent = placeName(p.birth_place).slice(0, 25);
    svg("title", {}, g).textContent =
      raceName(p.race) +
      " · " +
      placeName(p.birth_place) +
      " · naissance " +
      p.birth +
      " · décès " +
      (p.death ?? "inconnu / vivant");
    g.onkeydown = safely(async (e) => {
      if (["Enter", " "].includes(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        await selectPerson(p.id);
      }
    });
  }
  $("treeNote").textContent =
    fmt(all.length) +
    " individus · glisser / molette · ♂ bleu / ♀ mauve · point = peuple" +
    (result.truncated ? " · vue limitée à 1 000 personnes" : "") +
    " · parents des fondateurs inconnus";
  fitTree();
}

function chart() {
  const mode = $("chartMode").value,
    series =
      mode === "vital"
        ? [
            ["births", "Naissances · moyenne/an", "#287366"],
            ["deaths", "Décès · moyenne/an", "#b85353"],
          ]
        : mode === "movement"
          ? [
              ["divorces", "Divorces · moyenne/an", "#a76999"],
              ["marriages", "Unions · moyenne/an", "#b7974f"],
              ["migrations", "Déplacements · moyenne/an", "#6485b1"],
            ]
          : [["population", "Habitants", "#287366"]],
    from = Number($("chartFrom").value || 0),
    to = Number($("chartTo").value || world.history.length - 1),
    history = world.history.slice(Math.min(from, to), Math.max(from, to) + 1),
    firstYear = history[0].year,
    lastYear = history.at(-1).year,
    h = history.map((r) => ({
      ...r,
      ...Object.fromEntries(
        ["births", "deaths", "marriages", "divorces", "migrations"].map(
          (key) => [key, r[key] / (r.span || 1)],
        ),
      ),
    })),
    max = Math.max(...h.flatMap((r) => series.map(([key]) => r[key])), 1) * 1.1,
    c = $("chart"),
    right = Math.max(360, c.clientWidth || 900) - 25,
    plotWidth = right - 60;
  c.setAttribute("viewBox", `0 0 ${right + 25} 230`);
  c.replaceChildren();
  const x = (i) =>
      60 +
      ((h[i].year - firstYear) / Math.max(lastYear - firstYear, 1)) * plotWidth,
    y = (value) => 185 - (value / max) * 160;
  for (let i = 0; i <= 4; i++) {
    const yy = 185 - i * 40;
    svg("line", { x1: 60, y1: yy, x2: right, y2: yy, stroke: "#e1e5dc" }, c);
    const label = svg(
      "text",
      {
        x: 50,
        y: yy + 4,
        "text-anchor": "end",
        "font-size": 10,
        fill: "#819084",
      },
      c,
    );
    label.textContent = fmt(Math.round((max * i) / 4));
  }
  for (let i = 0; i <= 4; i++) {
    const index = Math.round(((h.length - 1) * i) / 4),
      label = svg(
        "text",
        {
          x: x(index),
          y: 211,
          "text-anchor": i === 0 ? "start" : i === 4 ? "end" : "middle",
          "font-size": 11,
          fill: "#819084",
        },
        c,
      );
    label.textContent = h[index].year;
  }

  const xYear = (year) =>
    60 + ((year - firstYear) / Math.max(lastYear - firstYear, 1)) * plotWidth;
  for (const event of loadedConfig.events) {
    const first = Math.max(firstYear, event.start_year),
      last = Math.min(lastYear, event.end_year);
    if (last < first) continue;
    const area = svg(
        "rect",
        {
          x: xYear(first),
          y: 25,
          width: Math.max(2, xYear(last) - xYear(first)),
          height: 160,
          fill: "#cf7840",
          opacity: 0.1,
        },
        c,
      ),
      title = svg("title", {}, area);
    title.textContent =
      event.name + " · " + event.start_year + "–" + event.end_year;
  }

  for (const [key, , color] of series) {
    const points = h.map((r, i) => [x(i), y(r[key])]);
    if (series.length === 1)
      svg(
        "polygon",
        {
          points: `60,185 ${points.map((p) => p.join(",")).join(" ")} ${right},185`,
          fill: color,
          opacity: 0.08,
        },
        c,
      );
    svg(
      "polyline",
      {
        points: points.map((p) => p.join(",")).join(" "),
        fill: "none",
        stroke: color,
        "stroke-width": 2.2,
      },
      c,
    );
  }
  const cursor = svg(
    "line",
    {
      x1: xYear(selectedYear()),
      x2: xYear(selectedYear()),
      y1: 25,
      y2: 185,
      stroke: "#244e54",
      "stroke-dasharray": "4 4",
      "pointer-events": "none",
    },
    c,
  );
  h.forEach((r, i) => {
    const hover = svg(
        "rect",
        {
          x: i === 0 ? 60 : (x(i - 1) + x(i)) / 2,
          y: 25,
          width: Math.max(
            4,
            (i === h.length - 1 ? right : (x(i) + x(i + 1)) / 2) -
              (i === 0 ? 60 : (x(i - 1) + x(i)) / 2),
          ),
          height: 160,
          fill: "transparent",
        },
        c,
      ),
      title = svg("title", {}, hover);
    title.textContent =
      r.year +
      " · " +
      series.map(([key, label]) => label + " : " + fmt(r[key])).join(" · ");
    const readout = title.textContent;
    hover.onpointerenter = () => {
      $("chartReadout").textContent = readout;
      cursor.setAttribute("x1", x(i));
      cursor.setAttribute("x2", x(i));
    };
    hover.setAttribute("tabindex", "0");
    hover.setAttribute("role", "button");
    hover.setAttribute("aria-label", readout + ", afficher sur la carte");
    hover.onfocus = hover.onpointerenter;
    hover.onkeydown = (e) => {
      if (["Enter", " "].includes(e.key)) {
        e.preventDefault();
        hover.onclick();
      }
    };
    hover.onclick = safely(async () => {
      $("year").value = world.history.findIndex((h) => h.year === r.year);
      await drawMap();
    });
  });
  $("chartLegend").replaceChildren();
  for (const [, label, color] of [
    ...series,
    ["", "Crises configurées", "#cf7840"],
  ]) {
    const span = el("span"),
      dot = el("i", "", "dot");
    dot.style.background = color;
    span.append(dot, el("span", label));
    $("chartLegend").append(span);
  }
}

async function loadWorld() {
  stopPlayback();
  const epoch = ++worldEpoch;
  readArchive = $("archives").value || readArchive;
  ++personEpoch;
  ++mapEpoch;
  ++treeEpoch;
  ++residentsEpoch;
  person = null;
  personTrail = [];
  personCursor = -1;
  lineage = [];
  const bundle = await api("world");
  if (epoch !== worldEpoch) return;
  world = bundle.overview;
  loadedConfig = bundle.config;
  presets.current = clone(loadedConfig);
  const s = world.summary;
  renderMortalityStats(s);
  $("tabExplore").textContent =
    "02 · Monde · " + world.settlements.length + " lieux";
  $("worldEyebrow").textContent =
    "Graine " +
    loadedConfig.seed +
    " / " +
    world.settlements.length +
    " lieux / " +
    world.races.length +
    " peuples";
  $("worldSubtitle").textContent =
    s.start_year +
    " → " +
    s.end_year +
    " · " +
    fmt(s.people_ever) +
    " vies conservées · " +
    (s.total_seconds ?? 0).toFixed(1) +
    " secondes de génération";
  $("worldMetrics").replaceChildren();
  for (const [value, label] of [
    [s.population, "Habitants vivants"],
    [s.births, "Naissances"],
    [s.deaths, "Décès"],
    [s.marriages, "Unions"],
  ]) {
    const card = el("div", "", "card");
    card.append(el("span", label, "small"), el("b", fmt(value)));
    $("worldMetrics").append(card);
  }
  $("year").min = 0;
  $("year").max = world.history.length - 1;
  $("year").value = world.history.length - 1;
  $("raceFilter").replaceChildren(el("option", "Tous les peuples"));
  $("raceFilter").firstChild.value = "";
  for (const r of world.races) {
    const o = el("option", r.name);
    o.value = r.id;
    $("raceFilter").append(o);
  }
  $("residentRace").replaceChildren(
    ...[...$("raceFilter").options].map((o) => o.cloneNode(true)),
  );
  for (const id of ["chartFrom", "chartTo"])
    $(id).replaceChildren(
      ...world.history.map((h, i) => {
        const o = el("option", h.year);
        o.value = i;
        return o;
      }),
    );
  $("chartFrom").value = 0;
  $("chartTo").value = world.history.length - 1;
  $("placePicker").replaceChildren(
    ...world.settlements.map((p) => {
      const o = el("option", p.id + " · " + p.name);
      o.value = p.id;
      return o;
    }),
  );
  initialPopulation = new Map(
    (await api("map?year=" + s.start_year)).map((p) => [
      p.settlement,
      p.population,
    ]),
  );
  setupMap();
  chart();
  await drawMap();
  if (epoch !== worldEpoch) return;
  const largest = [...counts].sort((a, b) => b.population - a.population)[0];
  await residents(largest?.settlement ?? world.settlements[0].id);
  if (epoch !== worldEpoch) return;
  let candidates = await api(
    "residents?place=" +
      chosenPlace +
      "&after=" +
      Math.max(loadedConfig.initial_population - 1, s.people_ever - 1000) +
      "&limit=1",
  );
  if (!candidates.length)
    candidates = await api("residents?place=" + chosenPlace + "&limit=1");
  if (epoch !== worldEpoch) return;
  await selectPerson(candidates[0]?.id ?? 0);
  if (epoch !== worldEpoch) return;
  $("diagnostics").textContent =
    (s.storage === "native-binary-memory-v1"
      ? "Mémoire binaire · aucune écriture · "
      : "Archive ") +
    (s.archive_bytes / 1024 / 1024).toFixed(2) +
    " Mio · " +
    fmt(s.migrations) +
    " déplacements · " +
    fmt(s.kinship_rejections) +
    " unions écartées pour parenté · " +
    Object.entries(s.population_by_race)
      .map(([r, n]) => r + " : " + fmt(n))
      .join(" / ") +
    (s.target_population
      ? " · cible " +
        fmt(s.target_population) +
        " ; écart " +
        (s.target_relative_error * 100).toFixed(1) +
        " %"
      : "") +
    ".";
  if (s.regulation?.enabled) {
    $("diagnostics").textContent +=
      " · Plancher " +
      fmt(s.regulation.floor) +
      " / plafond " +
      fmt(s.regulation.ceiling) +
      " · " +
      fmt(s.regulation.additional_births) +
      " naissances supplémentaires" +
      " · " +
      fmt(s.regulation.additional_deaths) +
      " décès de régulation" +
      " · " +
      fmt(s.regulation.below_floor_years) +
      " années sous le plancher";
  }
}

$("search").onsubmit = safely(async (e) => {
  e.preventDefault();
  tab("individual");
  await selectPerson(Number($("identity").value));
});
let yearTimer;
$("year").oninput = () => {
  stopPlayback();
  clearTimeout(yearTimer);
  yearTimer = setTimeout(() => safely(drawMap)(), 100);
};
$("chartMode").onchange = chart;
$("chartFrom").onchange = $("chartTo").onchange = () => {
  $("chartReadout").textContent =
    "Survoler un recensement · cliquer pour afficher sa carte.";
  chart();
};
$("resetChart").onclick = () => {
  $("chartFrom").value = 0;
  $("chartTo").value = world.history.length - 1;
  chart();
};
let playback;
function stopPlayback() {
  clearInterval(playback);
  playback = null;
  $("playYears").textContent = "▶";
}
$("playYears").onclick = () => {
  if (playback) {
    stopPlayback();
    return;
  }
  if (Number($("year").value) === world.history.length - 1) $("year").value = 0;
  $("playYears").textContent = "Ⅱ";
  playback = setInterval(
    safely(async () => {
      const next = Number($("year").value) + 1;
      if (next >= world.history.length) {
        stopPlayback();
        return;
      }
      $("year").value = next;
      await drawMap();
    }),
    900,
  );
  safely(drawMap)();
};
for (const [id, delta] of [
  ["prevYear", -1],
  ["nextYear", 1],
])
  $(id).onclick = safely(async () => {
    stopPlayback();
    $("year").value = Math.max(
      0,
      Math.min(world.history.length - 1, Number($("year").value) + delta),
    );
    await drawMap();
  });
$("depth").onchange = $("direction").onchange = safely(async () => {
  await drawTree();
  await drawMap();
});

safely(async () => {
  presets = await api("presets");
  for (const option of [...$("preset").options])
    option.disabled = !presets[option.value];
  await catalogue();
  await loadWorld();
  populate(presets.current);
  $("preset").value = "current";
  const status = await api("job");
  if (status.state !== "idle") await poll();
})();

function voronoiCells(points, bounds) {
  return Array.from(d3.Delaunay.from(points).voronoi(bounds).cellPolygons());
}

$("addNation").onclick = () => {
  let name = "nation_" + config.nations.length;
  while (config.nations.some((n) => n.name === name)) name += "_";
  config.nations.push({
    name,
    founded: config.start_year,
    dissolved: null,
    capital: null,
    metadata: {},
  });
  renderProfiles();
  syncPreview();
};
$("addContact").onclick = safely(() => {
  if (config.nations.length < 2)
    throw Error("Créer deux nations avant un contact.");
  config.nation_contacts.push({
    nations: config.nations.slice(0, 2).map((n) => n.name),
    start_year: config.start_year,
    end_year: null,
    marriage_factor: 1,
    migration_factor: 1,
    metadata: {},
  });
  renderProfiles();
  syncPreview();
});
const nationColor = (i) =>
  i < 0 ? "#c6cebd" : `hsl(${(i * 137.508) % 360} 38% 74%)`;
const nationName = (i) =>
  i < 0
    ? "Territoire indépendant"
    : loadedConfig.nations[i]?.name || "Nation " + i;

function renderMapLegend() {
  const layer = $("mapLayer").value;
  let entries = [];
  if (layer === "kind")
    entries = [...new Set(world.settlements.map((p) => p.kind))].map((k) => [
      kindColor(k),
      kindLabel(k),
    ]);
  if (layer === "population")
    entries = [
      ["#d5e6d9", "Faible effectif"],
      ["#397c62", "Fort effectif · échelle logarithmique"],
    ];
  if (layer === "growth")
    entries = [
      ["#bb6460", "Baisse depuis le début"],
      ["#398c93", "Hausse depuis le début"],
    ];
  if (layer === "flows")
    entries = [["#769a91", "150 principaux flux annuels · toutes ascendances"]];
  if (layer === "nations")
    entries = [...new Set(counts.map((r) => r.nation))].map((i) => [
      nationColor(i),
      nationName(i),
    ]);
  entries.push(
    ["#cf7840", "Origines familiales"],
    ["#287366", "Parcours individuel"],
  );
  $("mapLegend").replaceChildren(
    ...entries.map(([color, label]) => {
      const item = el("span"),
        dot = el("i", "", "dot");
      dot.style.background = color;
      item.append(dot, el("span", label));
      return item;
    }),
  );
}

function selectedYear() {
  return world.history[Number($("year").value)]?.year ?? world.summary.end_year;
}

function nearestSnapshot(year) {
  return world.history.reduce(
    (best, h, i) =>
      Math.abs(h.year - year) < Math.abs(world.history[best].year - year)
        ? i
        : best,
    0,
  );
}

$("previewLayer").onchange = $("previewYear").onchange = safely(refreshPreview);

function renderMortalityHint() {
  const d = config.demography,
    weights = [d.male_birth_probability, 1 - d.male_birth_probability],
    distribution = new Array(d.max_age + 1).fill(0);
  for (const sex of [0, 1]) {
    let survival = 1;
    for (let age = 0; age <= d.max_age; age++) {
      let q =
        age === 0
          ? d.infant_mortality
          : age <= d.child_max_age
            ? d.child_mortality
            : d.adult_mortality +
              d.aging_coefficient *
                Math.exp(Math.min(700, d.aging_exponent * age));
      q =
        age === d.max_age
          ? 1
          : Math.min(1, q * (sex === 0 ? d.male_mortality_factor : 1));
      distribution[age] += weights[sex] * survival * q;
      survival *= 1 - q;
    }
  }
  const mean = distribution.reduce((sum, p, age) => sum + p * age, 0),
    childhood = distribution.slice(0, 15).reduce((a, b) => a + b, 0);
  let cumulative = 0,
    median = 0;
  for (let age = 0; age < distribution.length; age++) {
    cumulative += distribution[age];
    if (cumulative >= 0.5) {
      median = age;
      break;
    }
  }
  $("mortalityHint").textContent =
    `Indication du modèle global : âge moyen au décès ${mean.toFixed(1)} ans · médiane ${median} ans · ${(childhood * 100).toFixed(1)} % meurent avant 15 ans. Calcul théorique avec mortalité par sexe, hors crises, maternité, régulation et variantes des peuples. L’âge maximal n’est pas l’espérance de vie. Les taux d’infertilité et de choix sans enfant sont des parts à vie, indépendantes, applicables aux deux partenaires.`;
}
function renderMortalityStats(summary) {
  const m = summary.mortality,
    metrics = $("mortalityMetrics");
  metrics.replaceChildren();
  $("deathBands").replaceChildren();
  if (!m) {
    $("mortalityDetail").textContent =
      "Ce monde antérieur ne contient pas ces statistiques. Relancez une génération pour les calculer.";
    return;
  }
  const percent = (n) => (n === null ? "—" : (n * 100).toFixed(1) + " %");
  for (const [label, value, hint] of [
    [
      "Âge moyen au décès",
      m.mean_age_at_death === null
        ? "—"
        : m.mean_age_at_death.toFixed(1) + " ans",
      "Décès observés, tous âges",
    ],
    [
      "Âge médian au décès",
      m.median_age_at_death === null
        ? "—"
        : fmt(m.median_age_at_death) + " ans",
      "La moitié des décès avant cet âge",
    ],
    [
      "Décès avant 15 ans",
      percent(m.deaths_under_15_fraction),
      fmt(m.deaths_under_15) + " / " + fmt(m.observed_deaths) + " décès",
    ],
    [
      "Enfants morts avant 15 ans",
      percent(m.completed_childhood_mortality),
      fmt(m.childhood_deaths_in_completed_cohort) +
        " / " +
        fmt(m.completed_childhood_cohort) +
        " naissances suivies ≥ 15 ans",
    ],
  ]) {
    const item = el("div");
    item.append(
      el("span", label, "small"),
      el("b", value),
      el("small", hint, "small"),
    );
    metrics.append(item);
  }
  for (const [age, n] of Object.entries(m.death_age_bands)) {
    const b = el("span", `${age} ans · ${fmt(n)} décès`, "tag");
    $("deathBands").append(b);
  }
  $("mortalityDetail").textContent =
    `Survie infantile : fondateurs exclus (${fmt(m.excluded_founders)}), leur enfance antérieure est inconnue. ${fmt(m.unresolved_childhood_cohort)} naissances trop récentes pour un suivi de 15 ans sont aussi exclues du taux des enfants. Les âges au décès incluent les fondateurs ; il s’agit de décès observés, pas d’une espérance de vie estimée.`;
}

new ResizeObserver(() => {
  if (world && $("chart").clientWidth) chart();
}).observe($("chart"));
