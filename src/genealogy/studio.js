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
    /^(world|overview|config|map|person|lineage|residence|residents)([?]|$)/.test(
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
    ? "Fondateurs recalibrés · cible " + fmt(config.target_population)
    : "Sans population cible";
  $("mapNotice").textContent = config.settlements.length
    ? "Carte explicite : nombre virtuel et profils ignorés. Modifier la carte dans le JSON."
    : "Carte virtuelle. Distances dans votre unité ; une génération est une durée.";
  $("configJson").value = JSON.stringify(config, null, 2);
  $("configValidated").textContent = "";
}

for (const [id, key] of Object.entries(basics)) {
  $(id).required = !["target", "exactYears", "capacityMode"].includes(id);
  $(id).onchange = () => {
    config[key] =
      id === "capacityMode"
        ? $(id).value
        : ["target", "exactYears"].includes(id) && !$(id).value
          ? null
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
  $("generate").disabled = status.state === "running";
  $("progressBox").hidden = status.state === "idle";
  $("progress").value = status.progress ?? 0;
  if (status.state === "running") {
    $("progressText").textContent = status.phase + " · année " + status.year;
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
    $("openResult").onclick = safely(async () => {
      await api("select", { id: status.archive });
      $("archives").value = status.archive;
      await loadWorld();
      tab("explore");
    });
  } else if (status.state === "failed") {
    $("progressText").textContent = "Génération interrompue";
    error(Error(status.error));
  }
}

$("generate").onclick = safely(async () => {
  $("generate").disabled = true;
  $("openResult").hidden = true;
  try {
    checkForm();
    const validated = await api("validate", {
      scenario: JSON.parse($("configJson").value),
    });
    populate(validated.scenario);
    await api("generate", { scenario: config });
    clearTimeout(pollTimer);
    await poll();
  } catch (e) {
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
    s = Math.min(630 / (dx || 1), 345 / (dy || 1));
  coordinates = new Map(
    world.settlements.map((p) => [
      p.id,
      [400 + (p.x - xmin - dx / 2) * s, 245 + (p.y - ymin - dy / 2) * s],
    ]),
  );
  view = { x: 0, y: 0, w: 800, h: 500 };
  applyView();
  $("mapLegend").replaceChildren();
  for (const k of new Set(world.settlements.map((p) => p.kind))) {
    const item = el("span"),
      dot = el("i", "", "dot");
    dot.style.background = kindColor(k);
    item.append(dot, el("span", kindLabel(k)));
    $("mapLegend").append(item);
  }
  for (const [color, label] of [
    ["#cf7840", "Origines familiales"],
    ["#287366", "Parcours individuel"],
  ]) {
    const item = el("span"),
      dot = el("i", "", "dot");
    dot.style.background = color;
    item.append(dot, el("span", label));
    $("mapLegend").append(item);
  }
}

function applyView() {
  $("map").setAttribute("viewBox", `${view.x} ${view.y} ${view.w} ${view.h}`);
  document
    .querySelectorAll(".mapLabel")
    .forEach(
      (e) =>
        (e.style.display =
          world?.settlements.length > 64 && view.w > 350 ? "none" : ""),
    );
}

function zoom(factor) {
  const w = Math.max(160, Math.min(1600, view.w * factor)),
    h = (w * 500) / 800;
  view.x += (view.w - w) / 2;
  view.y += (view.h - h) / 2;
  view.w = w;
  view.h = h;
  applyView();
}

$("zoomIn").onclick = () => zoom(0.8);
$("zoomOut").onclick = () => zoom(1.25);
$("resetMap").onclick = () => {
  view = { x: 0, y: 0, w: 800, h: 500 };
  applyView();
};
$("map").addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    zoom(e.deltaY > 0 ? 1.15 : 0.87);
  },
  { passive: false },
);
let drag = null;
$("map").onpointerdown = (e) => {
  if (e.target.closest(".place")) return;
  drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
  $("map").setPointerCapture(e.pointerId);
};
$("map").onpointermove = (e) => {
  if (!drag) return;
  const box = $("map").getBoundingClientRect();
  view.x = drag.vx - ((e.clientX - drag.x) * view.w) / box.width;
  view.y = drag.vy - ((e.clientY - drag.y) * view.h) / box.height;
  applyView();
};
$("map").onpointerup = $("map").onpointercancel = () => (drag = null);

async function drawMap() {
  const request = ++mapEpoch,
    y = Number($("year").value),
    data = await api("map?year=" + y);
  if (request !== mapEpoch) return;
  counts = data;
  const pop = new Map(data.map((p) => [p.settlement, p.population])),
    m = $("map");
  m.replaceChildren();
  $("yearText").textContent = y;
  for (let x = 40; x < 800; x += 40)
    svg(
      "line",
      { x1: x, y1: 0, x2: x, y2: 500, stroke: "#dde4d5", "stroke-width": 0.6 },
      m,
    );
  for (let z = 20; z < 500; z += 40)
    svg(
      "line",
      { x1: 0, y1: z, x2: 800, y2: z, stroke: "#dde4d5", "stroke-width": 0.6 },
      m,
    );
  const label = svg(
    "text",
    { x: 24, y: 28, fill: "#7f927d", "font-size": 10, "letter-spacing": 2 },
    m,
  );
  label.textContent = "CARTE / " + y;

  if (person && y >= person.birth) {
    const path = [
      person.birth_place,
      ...person.migrations.filter((e) => e.year <= y).map((e) => e.destination),
    ];
    svg(
      "polyline",
      {
        points: path
          .map((p) => coordinates.get(p)?.join(","))
          .filter(Boolean)
          .join(" "),
        fill: "none",
        stroke: "#287366",
        "stroke-width": 2.5,
        "stroke-dasharray": "5 5",
        opacity: 0.8,
      },
      m,
    );
  }

  const origins = new Set(lineage.map((p) => p.birth_place));
  for (const p of world.settlements) {
    const [x, z] = coordinates.get(p.id),
      g = svg(
        "g",
        {
          class: "place",
          transform: `translate(${x},${z})`,
          tabindex: 0,
          role: "button",
          "aria-label": p.name + " " + fmt(pop.get(p.id)) + " habitants",
        },
        m,
      ),
      r =
        (6 + Math.min(23, Math.sqrt(pop.get(p.id) || 0) / 4)) *
        Math.min(1, 4 / Math.sqrt(world.settlements.length));
    if (origins.has(p.id))
      svg(
        "circle",
        { r: r + 5, fill: "none", stroke: "#cf7840", "stroke-width": 2 },
        g,
      );
    const attrs = {
      fill: kindColor(p.kind),
      stroke: p.id === chosenPlace ? "#243c40" : "#fffefa",
      "stroke-width": p.id === chosenPlace ? 3 : 1.5,
      class: "marker",
    };
    if (["city", "metropolis", "town"].includes(p.kind))
      svg(
        "rect",
        {
          x: -r,
          y: -r,
          width: r * 2,
          height: r * 2,
          rx: p.kind === "town" ? 5 : 2,
          ...attrs,
        },
        g,
      );
    else if (p.kind === "port")
      svg("polygon", { points: `0,${-r} ${r},${r} ${-r},${r}`, ...attrs }, g);
    else svg("circle", { r, ...attrs }, g);
    const title = svg("title", {}, g);
    title.textContent =
      p.name +
      " · " +
      kindLabel(p.kind) +
      "\n" +
      fmt(pop.get(p.id)) +
      " habitants · capacité initiale " +
      fmt(p.capacity);
    const name = svg(
      "text",
      {
        y: r + 17,
        "text-anchor": "middle",
        "font-size": 11,
        fill: "#243c40",
        "font-weight": 600,
        class: "mapLabel",
      },
      g,
    );
    name.textContent = p.name;
    const total = svg(
      "text",
      {
        y: r + 31,
        "text-anchor": "middle",
        "font-size": 10,
        fill: "#788575",
        class: "mapLabel",
      },
      g,
    );
    total.textContent = fmt(pop.get(p.id));
    g.onclick = safely(async () => {
      await residents(p.id);
      await drawMap();
    });
    g.onkeydown = (e) => {
      if (e.key === "Enter") g.onclick();
    };
  }

  applyView();
  const h = world.history.find((h) => h.year === y);
  $("yearStats").textContent =
    fmt(h?.population) +
    " habitants · " +
    fmt(h?.births) +
    " naissances · " +
    fmt(h?.deaths) +
    " décès · " +
    fmt(h?.migrations) +
    " déplacements";
  drawRanking(pop, y);
  if (person) {
    const location = await api(`residence?id=${person.id}&year=${y}`);
    if (request !== mapEpoch) return;
    $("residence").textContent =
      location === null
        ? "Absent du recensement en " + y
        : "Résidence en " + y + " : " + placeName(location);
    if (location !== null) {
      const [x, z] = coordinates.get(location);
      svg(
        "circle",
        {
          cx: x,
          cy: z,
          r: 4,
          fill: "#fffefa",
          stroke: "#287366",
          "stroke-width": 2,
        },
        m,
      );
    }
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
      $("year").value = Math.max(
        world.summary.start_year,
        Math.min(world.summary.end_year, e.year),
      );
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
            ["births", "Naissances", "#287366"],
            ["deaths", "Décès", "#b85353"],
          ]
        : mode === "movement"
          ? [
              ["marriages", "Unions", "#b7974f"],
              ["migrations", "Déplacements", "#6485b1"],
            ]
          : [["population", "Habitants", "#287366"]],
    h = world.history,
    max = Math.max(...h.flatMap((r) => series.map(([key]) => r[key])), 1) * 1.1,
    c = $("chart");
  c.replaceChildren();
  const x = (i) => 60 + (i / Math.max(h.length - 1, 1)) * 815,
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

  for (const event of loadedConfig.events) {
    const first = Math.max(0, event.start_year - world.summary.start_year),
      last = Math.min(h.length - 1, event.end_year - world.summary.start_year);
    if (last < first) continue;
    const area = svg(
        "rect",
        {
          x: x(first),
          y: 25,
          width: Math.max(2, x(last) - x(first)),
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
      $("year").value = r.year;
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
  $("year").min = s.start_year;
  $("year").max = s.end_year;
  $("year").value = s.end_year;
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
    "Archive " +
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
  const status = await api("job");
  if (status.state !== "idle") await poll();
})();
