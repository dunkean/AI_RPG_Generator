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
    /^(world|overview|config|map|person|lineage|residence|residents|distributions)([?]|$)/.test(
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
  lastResident = -1,
  counts = [],
  coordinates = new Map(),
  mapEpoch = 0,
  personEpoch = 0,
  view = { x: 0, y: 0, w: 800, h: 500 },
  pollTimer;

function tab(which) {
  $("configView").hidden = which !== "config";
  $("exploreView").hidden = which !== "explore";
  $("tabConfig").classList.toggle("active", which === "config");
  $("tabExplore").classList.toggle("active", which === "explore");
}

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

function weights(value) {
  const result = {};
  for (const entry of value.split(",")) {
    const [key, weight, ...rest] = entry.split(":");
    if (
      !key?.trim() ||
      !weight?.trim() ||
      rest.length ||
      !Number.isFinite(Number(weight))
    )
      throw Error("Activités : utiliser agriculture: 9, craft: 1");
    result[key.trim()] = Number(weight);
  }
  return result;
}

function renderProfiles() {
  $("nationProfiles").replaceChildren();
  config.nations.forEach((n, index) => {
    const row = el("tr");
    inputCell(row, n.name, (v) => (n.name = v), { type: "text", wide: true });
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
      inputCell(row, n.nations[i], (v) => (n.nations[i] = v), {
        type: "text",
        wide: true,
      });
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
    inputCell(
      row,
      Object.entries(p.activities)
        .map(([k, v]) => k + ": " + v)
        .join(", "),
      (v) => (p.activities = weights(v)),
      { type: "text", wide: true },
    );
    removeCell(row, config.settlement_types, index);
    $("placeProfiles").append(row);
  });

  $("raceProfiles").replaceChildren();
  config.races.forEach((r) => {
    const row = document.createElement("tr");
    row.append(el("td", r.name));
    inputCell(row, r.initial_weight, (v) => (r.initial_weight = v));
    for (const field of ["max_age", "fertility_peak", "birth_spacing"])
      inputCell(
        row,
        r.demography[field],
        (v) => {
          if (v === null) delete r.demography[field];
          else r.demography[field] = v;
        },
        { nullable: true, placeholder: "Hérite : " + config.demography[field] },
      );
    $("raceProfiles").append(row);
  });

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
    wrap.append(l, i);
    $("demographicFields").append(wrap);
  }
  renderProfiles();
  syncPreview();
}

function setJsonDirty(flag) {
  for (const e of document.querySelectorAll(
    "#configView input:not([type=file]),#configView select,#configView .icon,#addPlace,#addEvent",
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
    : "Sans population cible";
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

$("addPlace").onclick = () => {
  config.settlement_types.push({
    kind: "village",
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

function personButton(p) {
  const b = el("button", "#" + p.id + " · " + (p.birth ?? ""), "chip");
  b.onclick = safely(() => selectPerson(p.id));
  return b;
}

function setupMap() {
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
  applyView();
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
function applyView() {
  paintMap();
}
function zoom(factor) {
  const w = Math.max(40, Math.min(1600, view.w * factor)),
    h = (w * 500) / 800;
  view.x += (view.w - w) / 2;
  view.y += (view.h - h) / 2;
  view.w = w;
  view.h = h;
  paintMap();
}
$("zoomIn").onclick = () => zoom(0.8);
$("zoomOut").onclick = () => zoom(1.25);
$("resetMap").onclick = () => {
  view = { x: 0, y: 0, w: 800, h: 500 };
  paintMap();
};
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
      ctx.lineWidth = ((0.4 + (2 * f.population) / maxFlow) * view.w) / 800;
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
    ctx.lineWidth = (1.8 * view.w) / 800;
    ctx.setLineDash([(4 * view.w) / 800, (4 * view.w) / 800]);
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
      ctx.lineWidth = (1.2 * view.w) / 800;
      ctx.beginPath();
      ctx.arc(x, y, r + (2 * view.w) / 800, 0, Math.PI * 2);
      ctx.stroke();
    }
    if (
      world.settlements.length <= 64 ||
      view.w < 170 ||
      p.id === chosenPlace
    ) {
      ctx.font = (10 * view.w) / 800 + "px system-ui";
      ctx.fillStyle = "#263f40";
      ctx.textAlign = "center";
      ctx.fillText(p.name, x, y + r + (12 * view.w) / 800);
      ctx.font = (9 * view.w) / 800 + "px system-ui";
      ctx.fillText(fmt(pop), x, y + r + (23 * view.w) / 800);
    }
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
}
$("mapLayer").onchange = paintMap;
$("raceFilter").onchange = safely(drawMap);
$("placePicker").onchange = safely(async () => {
  await residents(Number($("placePicker").value));
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

let residentsEpoch = 0;

async function residents(id, append = false) {
  const request = ++residentsEpoch;
  if (!append) {
    chosenPlace = id;
    lastResident = -1;
    $("residents").replaceChildren();
  }
  const list = await api(`residents?place=${id}&after=${lastResident}`);
  if (request !== residentsEpoch) return;
  $("placePicker").value = id;
  $("placeTitle").textContent = placeName(id);
  $("placeDetail").textContent =
    kindLabel(place(id).kind) +
    " · habitants au dernier recensement (" +
    world.summary.end_year +
    ")";
  for (const p of list) $("residents").append(personButton(p));
  if (list.length) lastResident = list.at(-1).id;
  else if (!append)
    $("residents").append(
      el("span", "Aucun habitant vivant dans ce lieu.", "small"),
    );
  $("more").hidden = list.length < 100;
}

function fact(label, value) {
  const f = el("div");
  f.append(el("span", label, "small"), el("b", value));
  return f;
}

async function selectPerson(id) {
  const request = ++personEpoch,
    selected = await api("person?id=" + id);
  if (request !== personEpoch) return;
  person = selected;
  $("identity").value = id;
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
  $("parents").replaceChildren(
    ...[person.father, person.mother].map((pid) =>
      pid === null ? el("span", "Inconnu", "tag") : personButton({ id: pid }),
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
      if (e.place !== null) chosenPlace = e.place;
      await drawMap();
    });
    row.append(date, body);
    $("timeline").append(row);
  }
  await drawTree();
  await drawMap();
}

let treeEpoch = 0;

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
    levels = new Map();
  for (const p of all) {
    if (!levels.has(p.generation)) levels.set(p.generation, []);
    levels.get(p.generation).push(p);
  }
  const maxGeneration = Math.max(...levels.keys()),
    width = Math.max(850, ...[...levels.values()].map((l) => l.length * 165)),
    height = (maxGeneration + 1) * 98 + 35,
    t = $("tree");
  t.setAttribute("viewBox", `0 0 ${width} ${height}`);
  t.style.width = width + "px";
  t.style.height = height + "px";
  t.replaceChildren();
  const points = new Map();
  for (const [generation, items] of levels)
    items.forEach((p, i) =>
      points.set(p.id, [
        ((i + 0.5) * width) / items.length,
        $("direction").value === "ancestors"
          ? (maxGeneration - generation) * 98 + 45
          : generation * 98 + 45,
      ]),
    );
  for (const p of all)
    for (const pid of [p.father, p.mother]) {
      if (!points.has(pid)) continue;
      const a = points.get(p.id),
        b = points.get(pid),
        mid = (a[1] + b[1]) / 2;
      svg(
        "path",
        {
          d: `M ${a[0]} ${a[1]} V ${mid} H ${b[0]} V ${b[1]}`,
          fill: "none",
          stroke: "#c0cdbd",
          "stroke-width": 1.4,
        },
        t,
      );
    }
  for (const p of all) {
    const [x, y] = points.get(p.id),
      g = svg("g", { transform: `translate(${x},${y})`, class: "treeNode" }, t);
    svg(
      "rect",
      {
        x: -72,
        y: -27,
        width: 144,
        height: 54,
        rx: 7,
        fill: p.id === person.id ? "#e4efe5" : "#fffefa",
        stroke: p.id === person.id ? "#287366" : "#cad4c6",
      },
      g,
    );
    const name = svg(
      "text",
      {
        "text-anchor": "middle",
        y: -7,
        fill: "#243c40",
        "font-size": 12,
        "font-weight": 600,
      },
      g,
    );
    name.textContent = "#" + p.id + " · " + raceName(p.race);
    const date = svg(
      "text",
      { "text-anchor": "middle", y: 12, fill: "#7a8980", "font-size": 11 },
      g,
    );
    date.textContent = p.birth + " → " + (p.death ?? "vivant");
    g.onclick = safely(() => selectPerson(p.id));
  }
  $("treeNote").textContent =
    fmt(all.length) +
    " individus · cliquer pour ouvrir une fiche" +
    (result.truncated ? " · vue limitée à 1 000 personnes" : "") +
    " · parents des fondateurs inconnus";
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
              ["marriages", "Unions · moyenne/an", "#b7974f"],
              ["migrations", "Déplacements · moyenne/an", "#6485b1"],
            ]
          : [["population", "Habitants", "#287366"]],
    h = world.history.map((r) => ({
      ...r,
      ...Object.fromEntries(
        ["births", "deaths", "marriages", "divorces", "migrations"].map(
          (key) => [key, r[key] / (r.span || 1)],
        ),
      ),
    })),
    max = Math.max(...h.flatMap((r) => series.map(([key]) => r[key])), 1) * 1.1,
    c = $("chart");
  c.replaceChildren();
  const x = (i) =>
      60 +
      ((h[i].year - world.summary.start_year) /
        Math.max(world.summary.end_year - world.summary.start_year, 1)) *
        815,
    y = (value) => 185 - (value / max) * 160;
  for (let i = 0; i <= 4; i++) {
    const yy = 185 - i * 40;
    svg("line", { x1: 60, y1: yy, x2: 875, y2: yy, stroke: "#e1e5dc" }, c);
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
    60 +
    ((year - world.summary.start_year) /
      Math.max(world.summary.end_year - world.summary.start_year, 1)) *
      815;
  for (const event of loadedConfig.events) {
    const first = Math.max(world.summary.start_year, event.start_year),
      last = Math.min(world.summary.end_year, event.end_year);
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
          points: `60,185 ${points.map((p) => p.join(",")).join(" ")} 875,185`,
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
  h.forEach((r, i) => {
    const hover = svg(
        "rect",
        {
          x: x(i) - Math.max(2, 815 / h.length / 2),
          y: 25,
          width: Math.max(4, 815 / h.length),
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
  const epoch = ++worldEpoch;
  readArchive = $("archives").value || readArchive;
  ++personEpoch;
  ++mapEpoch;
  ++treeEpoch;
  ++residentsEpoch;
  person = null;
  lineage = [];
  const bundle = await api("world");
  if (epoch !== worldEpoch) return;
  world = bundle.overview;
  loadedConfig = bundle.config;
  presets.current = clone(loadedConfig);
  const s = world.summary;
  $("tabExplore").textContent =
    "02 · Explorer (" + world.settlements.length + " lieux)";
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
  await selectPerson(Number($("identity").value));
});
let yearTimer;
$("year").oninput = () => {
  clearTimeout(yearTimer);
  yearTimer = setTimeout(() => safely(drawMap)(), 100);
};
$("chartMode").onchange = chart;
$("depth").onchange = $("direction").onchange = safely(async () => {
  await drawTree();
  await drawMap();
});
$("more").onclick = safely(() => residents(chosenPlace, true));

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
  config.nations.push({
    name: "nation_" + config.nations.length,
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
