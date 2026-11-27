// Build presentation/MergeMap_Demo.pptx, the 10-minute demo deck.
//
// Every number comes from assets/deck_data.json, which make_visuals.py writes
// from the latest pipeline run. Run from the project root:
//
//     python presentation/make_visuals.py
//     node presentation/build_deck.js
//
// Story: a film in four acts. Act I the world, Act II the twist (merges),
// Act III the kingmakers (hubs), Act IV the blast radius (reach), epilogue.

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");

const HERE = __dirname;
const ASSETS = path.join(HERE, "assets");
const D = JSON.parse(fs.readFileSync(path.join(ASSETS, "deck_data.json"), "utf8"));
const OUT = process.env.DECK_OUT || path.join(HERE, "MergeMap_Demo.pptx");   // DECK_OUT: build a copy elsewhere

// ---------------------------------------------------------------------------
// Palette, fonts, helpers
// ---------------------------------------------------------------------------
const HEX = {
  bg: "1B1C20", panel: "25272D", panel2: "2E3037", line: "3A3D45",
  white: "FFFFFF", muted: "A9ADB6", dim: "6B7079",
  amber: "F5A524", steel: "6FA8DC", teal: "4FC3A1", rose: "E57373", lavender: "B39DDB",
};
const THEME = {
  name: "MergeMap Cinematic",
  headFontFace: "Bahnschrift SemiBold",
  bodyFontFace: "Segoe UI",
  colors: {
    dk1: HEX.bg, lt1: HEX.white, dk2: HEX.panel, lt2: HEX.muted,
    accent1: HEX.amber, accent2: HEX.steel, accent3: HEX.teal, accent4: HEX.rose,
    accent5: HEX.lavender, accent6: HEX.dim, hlink: HEX.amber, folHlink: HEX.steel,
  },
};
const FAMILY = { mistral: HEX.amber, llama: HEX.steel, qwen: HEX.teal, gemma: HEX.rose, unknown: "5C616A" };

const W = 13.333, H = 7.5, M = 0.6;            // canvas and side margin, inches
const fmt = (n) => Math.round(n).toLocaleString("en-US");
const pct = (x, d = 1) => (100 * x).toFixed(d) + "%";
const shortName = (s) => s.split("/").pop();

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "MergeMap: when AI models have children together";
pres.subject = "COMP 6917 Complex Networks project demo";
pres.author = "Md Minhajul Abedin";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };

// Speaker notes come from speaker_script_new.txt when it exists, so the script can be
// edited as plain text: "Slide N: title" on one line, the notes on the lines after it,
// a blank line between slides. A slide missing from the file keeps the notes written below.
function loadScript(file) {
  if (!fs.existsSync(file)) return {};
  const notes = {};
  let current = null;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const head = line.match(/^Slide (\d+):/);
    if (head) { current = Number(head[1]); notes[current] = []; continue; }
    if (current !== null && line.trim()) notes[current].push(line.trim());
  }
  return Object.fromEntries(Object.entries(notes).filter(([, l]) => l.length).map(([n, l]) => [n, l.join(" ")]));
}
const SCRIPT = loadScript(path.join(HERE, "speaker_script_new.txt"));
let slideNo = 0;
const addSlideOriginal = pres.addSlide.bind(pres);
pres.addSlide = (opts) => {
  const slide = addSlideOriginal(opts);
  const n = ++slideNo;
  const addNotesOriginal = slide.addNotes.bind(slide);
  slide.addNotes = (text) => addNotesOriginal(SCRIPT[n] !== undefined ? SCRIPT[n] : text);
  return slide;
};

const C = pres.SchemeColor;
const COL = {
  bg: C.text1, white: C.background1, panel: C.text2, muted: C.background2,
  amber: C.accent1, steel: C.accent2, teal: C.accent3, rose: C.accent4, dim: C.accent6,
};

const shadow = () => ({ type: "outer", color: "000000", blur: 14, offset: 5, angle: 90, opacity: 0.5 });
const softShadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.4 });

async function icon(IconComponent, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color: "#" + color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

// ---------------------------------------------------------------------------
// Layouts: a cover frame and a content frame (act label, title, footer, number)
// ---------------------------------------------------------------------------
pres.defineSlideMaster({
  title: "MM_COVER",
  background: { color: HEX.bg },
  objects: [],
});
pres.defineSlideMaster({
  title: "MM_CONTENT",
  background: { color: HEX.bg },
  margin: [0.5, M, 0.5, M],
  objects: [
    { placeholder: { options: { name: "act", type: "body", x: M, y: 0.42, w: 9, h: 0.34, fontSize: 12, bold: true,
        color: COL.amber, charSpacing: 4, margin: 0, valign: "middle" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.78, w: W - 2 * M, h: 1.0, fontSize: 40,
        color: COL.white, fontFace: THEME.headFontFace, margin: 0, valign: "top", align: "left" }, text: "" } },
    { text: { text: "MergeMap  ·  COMP 6917", options: { x: M, y: H - 0.42, w: 4, h: 0.28, fontSize: 10,
        color: COL.dim, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: H - 0.42, w: 0.6, h: 0.28, fontSize: 10, color: HEX.dim, align: "right" },
});

function contentSlide(section, act, title, notes) {
  const s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: section });
  s.addText(act, { placeholder: "act" });
  s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(notes);
  return s;
}

// A card: rounded panel with a soft shadow, the deck's recurring 3D motif.
function card(s, x, y, w, h, name, fill = COL.panel) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.14, fill: { color: fill },
    line: { color: HEX.line, width: 0.75 }, shadow: shadow(), objectName: name });
}

// Big number with a label underneath.
function stat(s, x, y, w, value, label, name, color = COL.white, size = 40) {
  s.addText(value, { x, y, w, h: size / 60, fontSize: size, bold: true, color, fontFace: THEME.headFontFace,
    margin: 0, isTextBox: true, objectName: name + " value" });
  s.addText(label, { x, y: y + size / 60 + 0.04, w, h: 0.6, fontSize: 14, color: COL.muted, margin: 0,
    valign: "top", isTextBox: true, objectName: name + " label" });
}

// Icon inside a coloured circle.
function badge(s, data, x, y, d, fill, name) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, width: 0 },
    shadow: softShadow(), objectName: name + " circle" });
  s.addImage({ data, x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, objectName: name + " icon" });
}

const chartBase = () => ({
  catAxisLabelColor: HEX.muted, valAxisLabelColor: HEX.muted, catAxisLabelFontFace: "+mn-lt",
  valAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  valGridLine: { color: HEX.line, size: 0.5 }, catGridLine: { style: "none" },
  catAxisLineShow: false, valAxisLineShow: false,
  legendColor: HEX.muted, legendFontFace: "+mn-lt", legendFontSize: 12,
  dataLabelColor: HEX.white, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 11,
  plotArea: { fill: { color: HEX.bg } },
});

async function main() {
  const ICON = {
    db: await icon(fa.FaDatabase, HEX.white), branch: await icon(fa.FaCodeBranch, HEX.white),
    tag: await icon(fa.FaTags, HEX.white), broom: await icon(fa.FaBroom, HEX.white),
    shield: await icon(fa.FaShieldHalved, HEX.white), copy: await icon(fa.FaCopy, HEX.bg),
    users: await icon(fa.FaUsers, HEX.bg), crown: await icon(fa.FaCrown, HEX.bg),
    bridge: await icon(fa.FaBridge, HEX.bg), check: await icon(fa.FaCheck, HEX.bg),
    play: await icon(fa.FaPlay, HEX.bg), clock: await icon(fa.FaClock, HEX.white),
    seedling: await icon(fa.FaSeedling, HEX.white), magnify: await icon(fa.FaMagnifyingGlass, HEX.white),
    pen: await icon(fa.FaUserPen, HEX.white), question: await icon(fa.FaCircleQuestion, HEX.white),
    link: await icon(fa.FaLink, HEX.white), camera: await icon(fa.FaCamera, HEX.white),
    cubes: await icon(fa.FaCubes, HEX.white),
  };
  const hero = D.image_size.hero_network, sky = D.image_size.skyline;

  // =========================================================================
  // 1. Cover
  // =========================================================================
  pres.addSection({ title: "Prologue" });
  let s = pres.addSlide({ masterName: "MM_COVER", sectionTitle: "Prologue" });
  {
    const iw = 8.2, ih = iw * hero.h / hero.w;
    s.addImage({ path: path.join(ASSETS, "hero_network.png"), x: W - iw + 1.2, y: (H - ih) / 2 + 0.35, w: iw, h: ih,
      altText: "3D cocitation network of the 260 most-cited merge parents, coloured by family", objectName: "hero network" });
    s.addText("COMP 6917  ·  COMPLEX NETWORKS  ·  FALL 2026", { x: M, y: 1.0, w: 7, h: 0.35, fontSize: 12, bold: true,
      color: COL.amber, charSpacing: 4, margin: 0, isTextBox: true, objectName: "eyebrow" });
    s.addText("MergeMap", { x: M, y: 1.45, w: 7.5, h: 1.6, fontSize: 96, color: COL.white, fontFace: THEME.headFontFace,
      margin: 0, isTextBox: true, objectName: "title" });
    s.addText("When AI models have children together", { x: M, y: 3.1, w: 5.0, h: 1.0, fontSize: 26, color: COL.white,
      margin: 0, valign: "top", isTextBox: true, objectName: "subtitle" });
    s.addText("A network analysis of model merging on Hugging Face", { x: M, y: 4.2, w: 5.6, h: 0.75, fontSize: 16,
      color: COL.muted, margin: 0, isTextBox: true, objectName: "tagline" });
    s.addText("Md Minhajul Abedin  ·  25 November 2026", { x: M, y: H - 1.1, w: 6, h: 0.35, fontSize: 14,
      color: COL.muted, margin: 0, isTextBox: true, objectName: "author" });
    s.addNotes(
      "[0:00-0:25] Hugging Face hosts over three million AI models. Most are built from a few base models, so they " +
      "form family trees. A merged model blends two or more parents, so it can join different trees. This project asks " +
      "what merges do to those families. Behind me: real merge parents, coloured by family.");
  }

  // =========================================================================
  // 2. Act I: the world
  // =========================================================================
  pres.addSection({ title: "Act I: the world" });
  s = contentSlide("Act I: the world", "ACT I  ·  THE WORLD", "3.2 million models. Most have a parent.",
    `[0:25-0:55] One snapshot of Hugging Face: ${(D.models / 1e6).toFixed(1)} million models. ` +
    `${pct(D.declaring_base / D.models, 0)} declare a parent, which gives a graph of ${fmt(D.graph_nodes)} models. ` +
    "Almost all edges are fine-tunes, adapters and quantized copies. Merges, in amber, are a thin slice, and the " +
    "story is about that slice.");
  {
    const cards = [
      [fmt(D.models), "public models in the snapshot", `Hugging Face, ${D.snapshot.date}`],
      [fmt(D.declaring_base), "declare a base model", `${pct(D.declaring_base / D.models, 0)} of all models`],
      [fmt(D.graph_nodes), "models in our lineage graph", `${fmt(D.graph_edges)} parent links`],
    ];
    const cw = (W - 2 * M - 2 * 0.35) / 3;
    cards.forEach(([v, l, sub], i) => {
      const x = M + i * (cw + 0.35);
      card(s, x, 2.05, cw, 2.1, `stat card ${i + 1}`);
      stat(s, x + 0.35, 2.3, cw - 0.7, v, l, `stat ${i + 1}`, i === 2 ? COL.amber : COL.white, 44);
      s.addText(sub, { x: x + 0.35, y: 3.62, w: cw - 0.7, h: 0.3, fontSize: 12, color: COL.dim, margin: 0,
        isTextBox: true, objectName: `stat ${i + 1} source` });
    });
    // Relation mix as one stacked bar built from shapes.
    const rel = D.edges_by_relation;
    const order = [["finetune", "fine-tune", "4A5C78"], ["adapter", "adapter", "5B7290"],
                   ["quantized", "quantized", "7C8DA6"], ["merge", "merge", HEX.amber]];
    const total = order.reduce((a, [k]) => a + rel[k], 0);
    s.addText("WHAT THE EDGES ARE", { x: M, y: 4.6, w: 6, h: 0.3, fontSize: 12, bold: true, color: COL.muted,
      charSpacing: 3, margin: 0, isTextBox: true, objectName: "edge mix label" });
    let x = M;
    const bw = W - 2 * M;
    order.forEach(([k, label, color], i) => {
      const w = bw * rel[k] / total;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 5.0, w: Math.max(w - 0.03, 0.02), h: 0.55,
        fill: { color }, line: { color, width: 0 }, objectName: `edge bar ${label}` });
      const isMerge = k === "merge";
      s.addText([{ text: label + "  ", options: { color: isMerge ? COL.amber : COL.white, bold: true } },
                 { text: `${fmt(rel[k])}  ·  ${pct(rel[k] / total)}`, options: { color: COL.muted } }],
        { x: isMerge ? W - M - 3.2 : x, y: isMerge ? 4.6 : 5.68, w: isMerge ? 3.2 : Math.max(w - 0.1, 2.2), h: 0.35,
          fontSize: 13, margin: 0, align: isMerge ? "right" : "left", isTextBox: true, objectName: `edge label ${label}` });
      x += w;
    });
  }

  // =========================================================================
  // 3. Act I: the graph model
  // =========================================================================
  s = contentSlide("Act I: the world", "ACT I  ·  THE WORLD", "Every model points to the model it came from",
    "[0:55-1:35] A node is a model; an edge points to the model it was built from. Only merges have more than " +
    "one parent, so without them the graph is a forest of separate trees. Each tree gets a family from its root's " +
    `name, from a list of ${D.families}. Impossible links were removed; deleted parents are kept so families stay whole.`);
  {
    // Diagram on the left: two families and one merge between them.
    const node = (x, y, w, label, sub, fill, lineColor, name) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.78, rectRadius: 0.12, fill: { color: fill },
        line: { color: lineColor, width: 1.5 }, shadow: shadow(), objectName: name });
      s.addText([{ text: label, options: { bold: true, color: COL.white, breakLine: true } },
                 { text: sub, options: { color: COL.muted, fontSize: 11 } }],
        { x, y, w, h: 0.78, fontSize: 15, align: "center", valign: "middle", margin: 0, isTextBox: true,
          objectName: name + " text" });
    };
    const arrow = (x1, y1, x2, y2, color, name) => s.addShape(pres.shapes.LINE, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, flipV: y2 < y1, line: { color, width: 2, endArrowType: "triangle" }, objectName: name });
    node(1.0, 2.15, 2.4, "Llama base", "root · family llama", HEX.panel2, HEX.steel, "llama root");
    node(4.6, 2.15, 2.4, "Mistral base", "root · family mistral", HEX.panel2, HEX.amber, "mistral root");
    node(0.6, 3.75, 1.75, "fine-tune", "1 parent", HEX.panel, HEX.line, "finetune node");
    node(2.55, 3.75, 1.75, "quantized", "1 parent", HEX.panel, HEX.line, "quantized node");
    node(5.4, 3.75, 1.75, "adapter", "1 parent", HEX.panel, HEX.line, "adapter node");
    node(2.9, 5.35, 2.4, "merge", "2 parents, 2 families", "3A2C12", HEX.amber, "merge node");
    arrow(1.48, 3.75, 1.9, 2.93, HEX.dim, "edge finetune");
    arrow(3.42, 3.75, 2.6, 2.93, HEX.dim, "edge quantized");
    arrow(6.27, 3.75, 6.0, 2.93, HEX.dim, "edge adapter");
    arrow(3.5, 5.35, 1.48, 4.53, HEX.amber, "edge merge 1");
    arrow(4.7, 5.35, 6.27, 4.53, HEX.amber, "edge merge 2");
    // Rules on the right, icon rows.
    const rows = [
      [ICON.db, "Pinned snapshot", `commit ${D.snapshot.commit} · hash checked every run`],
      [ICON.branch, "Edge = child → parent", "in-degree counts children; only merges have 2+ parents"],
      [ICON.tag, `${D.families} named families`, "matched on root names; the rest are “unknown”"],
      [ICON.broom, "Cleaned, not trimmed", "self-loops and impossible dates removed; ghost parents kept"],
    ];
    rows.forEach(([ic, head, body], i) => {
      const y = 2.15 + i * 1.08;
      badge(s, ic, 8.0, y, 0.62, HEX.panel2, `rule ${i + 1}`);
      s.addText([{ text: head, options: { bold: true, color: COL.white, fontSize: 17, breakLine: true } },
                 { text: body, options: { color: COL.muted, fontSize: 13 } }],
        { x: 8.85, y: y - 0.05, w: W - M - 8.85, h: 0.9, margin: 0, valign: "top", isTextBox: true,
          objectName: `rule ${i + 1} text` });
    });
  }

  // =========================================================================
  // 4. Act II: the twist, merges fuse the families
  // =========================================================================
  pres.addSection({ title: "Act II: the twist" });
  s = contentSlide("Act II: the twist", "ACT II  ·  THE TWIST",
    `${pct(D.merge_share_of_linked)} of models fuse the families together`,
    `[1:35-2:15] RQ1: do merges connect families? Merges are only ${pct(D.merge_share_of_linked)} of models. ` +
    `Without them, the largest group has ${fmt(D.largest_without)} models; with them, ${fmt(D.largest_with)}: ` +
    `${(D.largest_with / D.largest_without).toFixed(1)} times bigger, with ${D.families_in_giant} families in one piece. ` +
    `Lineages grow from ${D.depth_without} to ${D.depth_with} generations. But one merge is enough to join two trees, ` +
    "so this shows connection, not strength.");
  {
    const maxW = 5.6;
    const bars = [["without merges", D.largest_without, "5B7290"], ["with merges", D.largest_with, HEX.amber]];
    bars.forEach(([label, v, color], i) => {
      const y = 2.35 + i * 1.55;
      s.addText(label.toUpperCase(), { x: M, y, w: 4, h: 0.3, fontSize: 12, bold: true, color: COL.muted,
        charSpacing: 3, margin: 0, isTextBox: true, objectName: `component label ${i + 1}` });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: y + 0.4, w: Math.max(maxW * v / D.largest_with, 0.12),
        h: 0.62, rectRadius: 0.08, fill: { color }, line: { color, width: 0 }, shadow: shadow(),
        objectName: `component bar ${i + 1}` });
      s.addText(fmt(v), { x: M + Math.max(maxW * v / D.largest_with, 0.12) + 0.2, y: y + 0.32, w: 3.2, h: 0.8,
        fontSize: 34, bold: true, color: i ? COL.amber : COL.white, fontFace: THEME.headFontFace, margin: 0,
        valign: "middle", isTextBox: true, objectName: `component value ${i + 1}` });
    });
    s.addText("models in the largest connected group", { x: M, y: 5.45, w: 7, h: 0.35, fontSize: 14,
      color: COL.muted, margin: 0, isTextBox: true, objectName: "component caption" });
    const side = [
      [(D.largest_with / D.largest_without).toFixed(1) + "×", "bigger largest group"],
      [`${D.depth_without} → ${D.depth_with}`, "generations in the deepest lineage"],
      [`${D.families_in_giant}`, "named families in one connected group"],
    ];
    card(s, W - M - 3.6, 2.05, 3.6, 3.95, "side card");
    side.forEach(([v, l], i) => stat(s, W - M - 3.25, 2.3 + i * 1.2, 2.9, v, l, `side stat ${i + 1}`,
      i === 0 ? COL.amber : COL.white, 32));
  }

  // =========================================================================
  // 5. Act II: merging stays in the family
  // =========================================================================
  s = contentSlide("Act II: the twist", "ACT II  ·  THE TWIST", "But merging stays inside the family",
    "[2:15-2:50] RQ2: who merges with whom? Two models are linked when merges use them together. The clusters " +
    `are families, with few lines between them. Assortativity is ${D.assort_named.toFixed(2)}, where 1 means never ` +
    "crossing a family. Merges stay in the family, because different architectures cannot be averaged.");
  {
    const iw = 7.6, ih = iw * hero.h / hero.w;
    s.addImage({ path: path.join(ASSETS, "hero_network.png"), x: M - 0.2, y: 2.0, w: iw, h: ih,
      altText: "Cocitation network: clusters by family with few links between them", objectName: "network" });
    const legendFamilies = ["mistral", "llama", "qwen", "gemma", "unknown"].filter((f) => D.network_families.includes(f));
    legendFamilies.forEach((f, i) => {
      s.addShape(pres.shapes.OVAL, { x: M + i * 1.35, y: 6.55, w: 0.18, h: 0.18, fill: { color: FAMILY[f] },
        line: { color: FAMILY[f], width: 0 }, objectName: `legend dot ${f}` });
      s.addText(f, { x: M + i * 1.35 + 0.26, y: 6.47, w: 1.0, h: 0.32, fontSize: 12, color: COL.muted, margin: 0,
        isTextBox: true, objectName: `legend ${f}` });
    });
    card(s, 8.55, 2.05, W - M - 8.55, 4.2, "assortativity card");
    stat(s, 8.9, 2.35, 3.5, D.assort_named.toFixed(2), "family assortativity among named families (1 = never cross)",
      "assortativity", COL.amber, 54);
    stat(s, 8.9, 4.3, 3.5, pct(D.same_label_share), "of parent pairs used together share a family",
      "same family", COL.white, 40);
  }

  // =========================================================================
  // 6. Act II: inbreeding
  // =========================================================================
  s = contentSlide("Act II: the twist", "ACT II  ·  THE TWIST", "Close relatives merge 2× as often as chance",
    "[2:50-3:35] Are the parents of a merge close relatives? Here is one real merge. B is an adapter trained on " +
    "A, and the merge blends A with B, so A is both parent and grandparent. " +
    `${pct(D.inbred["1"])} of merges join parents this close. Rewiring the merges 100 times within families gives ` +
    `only ${pct(D.inbred_within_family["1"])}. So close relatives merge twice as often as chance.`);
  {
    // Family tree of one inbred merge, cut to what the story needs: the parents of the
    // inbred parent (context), the inbred parent A, its descendant B, and the merge M of A and B.
    const T = D.inbred_tree;
    const byRole = (r) => T.nodes.find((n) => n.role === r);
    const A = byRole("inbred"), B = byRole("parent"), Mg = byRole("merge");
    const ctxIds = T.edges.filter((e) => e.child === A.id).map((e) => e.parent);
    const ctx = T.nodes.filter((n) => ctxIds.includes(n.id));
    const boxW = 4.5, boxH = 0.66, colX = M + 1.3, rowY = [2.0, 3.25, 4.4, 5.55];
    const pos = {};
    const ctxW = 2.95, ctxGap = 0.3, ctxLeft = colX + boxW / 2 - (ctx.length * ctxW + (ctx.length - 1) * ctxGap) / 2;
    ctx.forEach((n, i) => { pos[n.id] = { x: ctxLeft + i * (ctxW + ctxGap), y: rowY[0], w: ctxW }; });
    pos[A.id] = { x: colX, y: rowY[1], w: boxW };
    pos[B.id] = { x: colX, y: rowY[2], w: boxW };
    pos[Mg.id] = { x: colX, y: rowY[3], w: boxW };
    const clip = (t, k) => (t.length <= k ? t : t.slice(0, Math.ceil(k * 0.55)) + "…" + t.slice(-(k - 1 - Math.ceil(k * 0.55))));
    const kids = (n) => `${fmt(n.children)} ${n.children === 1 ? "child" : "children"}`;

    const line = (x1, y1, x2, y2, color, width, arrow, name) => s.addShape(pres.shapes.LINE, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.001), h: Math.max(Math.abs(y2 - y1), 0.001),
      flipH: x2 < x1, flipV: y2 < y1,
      line: Object.assign({ color, width }, arrow ? { endArrowType: "triangle" } : {}), objectName: name });
    const up = (child, parent, color, width, name) => {
      const c = pos[child], q = pos[parent];
      line(c.x + c.w / 2, c.y, q.x + q.w / 2, q.y + (q === pos[A.id] ? boxH : 0.62) + 0.02, color, width, true, name);
    };
    ctx.forEach((n, i) => up(A.id, n.id, HEX.dim, 1.25, `edge context ${i + 1}`));
    up(B.id, A.id, HEX.amber, 2.5, "edge B to A");
    up(Mg.id, B.id, HEX.steel, 2.0, "edge M to B");
    // M to A skips B, so it goes round the right side.
    const rail = colX + boxW + 0.45, yM = pos[Mg.id].y + boxH / 2, yA = pos[A.id].y + boxH / 2;
    line(colX + boxW, yM, rail, yM, HEX.amber, 2.5, false, "edge M to A out");
    line(rail, yM, rail, yA, HEX.amber, 2.5, false, "edge M to A up");
    line(rail, yA, colX + boxW + 0.02, yA, HEX.amber, 2.5, true, "edge M to A in");

    const node = (n, style, sub, name) => {
      const q = pos[n.id], h = n === A || n === B || n === Mg ? boxH : 0.62;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: q.x, y: q.y, w: q.w, h, rectRadius: 0.1,
        fill: { color: style.fill }, line: { color: style.line, width: style.lw }, shadow: softShadow(), objectName: name });
      s.addText([{ text: clip(n.label, q.w > 3.5 ? 40 : 26), options: { bold: true, color: style.head, fontSize: q.w > 3.5 ? 13 : 11, breakLine: true } },
                 { text: sub, options: { color: style.sub, fontSize: 10 } }],
        { x: q.x, y: q.y, w: q.w, h, align: "center", valign: "middle", margin: 0, isTextBox: true,
          objectName: name + " text", altText: n.name });
    };
    ctx.forEach((n, i) => node(n, { fill: HEX.panel, line: HEX.line, lw: 0.75, head: COL.muted, sub: COL.dim },
      `${n.relation} · ${kids(n)}`, `context node ${i + 1}`));
    node(A, { fill: "3A2C12", line: HEX.amber, lw: 2, head: COL.white, sub: COL.muted }, `A · ${A.relation} · ${kids(A)}`, "node A");
    node(B, { fill: HEX.panel2, line: HEX.steel, lw: 2, head: COL.white, sub: COL.muted }, `B · ${B.relation} trained on A · ${kids(B)}`, "node B");
    node(Mg, { fill: HEX.amber, line: HEX.amber, lw: 2, head: COL.bg, sub: COL.bg }, `merge of A + B · ${kids(Mg)}`, "node merge");
    s.addText("A is both a parent\nand a grandparent", { x: rail + 0.15, y: (yA + yM) / 2 - 0.35, w: 1.9, h: 0.7, fontSize: 13,
      bold: true, color: COL.amber, margin: 0, valign: "middle", isTextBox: true, objectName: "inbred label" });
    s.addText([{ text: "One real merge.  ", options: { bold: true, color: COL.white } },
               { text: "Each arrow points to the model it was built from. B is an adapter trained on A, and the merge blends A with B.",
                 options: { color: COL.muted } }],
      { x: M, y: 6.5, w: 8.3, h: 0.45, fontSize: 12, margin: 0, valign: "top", isTextBox: true, objectName: "tree caption" });

    card(s, 9.2, 2.05, W - M - 9.2, 4.2, "inbreeding card");
    stat(s, 9.5, 2.35, 3.0, pct(D.inbred["1"]), "of merges join parents within one generation", "inbred observed",
      COL.amber, 54);
    stat(s, 9.5, 4.25, 3.0, pct(D.inbred_within_family["1"]), "expected by chance within families (100 random runs)",
      "inbred baseline", COL.steel, 36);
  }

  // =========================================================================
  // 7. Act II: copying
  // =========================================================================
  s = contentSlide("Act II: the twist", "ACT II  ·  THE TWIST", "Recipes get copied",
    "[3:35-4:15] Why so inbred? Copying, as in the vertex-copying model from the lecture. " +
    `${pct(D.copying.share_copying)} of merges reuse at least half of an earlier merge's parents; chance gives ` +
    `${pct(D.copying_within_family)}. One recipe was used ${D.top_recipe.merges} times by one author: that is the ` +
    `dense amber cluster. Another was copied by ${D.crowd_recipe.authors} different people.`);
  {
    const rows = [["observed", D.copying.share_copying, HEX.amber],
                  ["random, within families", D.copying_within_family, HEX.steel],
                  ["random, any parents", D.copying_shuffled, "5C616A"]];
    s.addText("MERGES THAT REUSE MOST OF AN EARLIER MERGE'S PARENTS", { x: M, y: 2.05, w: 7.4, h: 0.3, fontSize: 12,
      bold: true, color: COL.muted, charSpacing: 2, margin: 0, isTextBox: true, objectName: "copy label" });
    const maxW = 5.2;
    rows.forEach(([label, v, color], i) => {
      const y = 2.6 + i * 1.05;
      s.addText(label, { x: M, y, w: 6, h: 0.3, fontSize: 14, color: COL.white, margin: 0, isTextBox: true,
        objectName: `copy row ${i + 1} label` });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: y + 0.36, w: Math.max(maxW * v / 0.5, 0.1), h: 0.42,
        rectRadius: 0.06, fill: { color }, line: { color, width: 0 }, shadow: softShadow(), objectName: `copy bar ${i + 1}` });
      s.addText(pct(v), { x: M + Math.max(maxW * v / 0.5, 0.1) + 0.15, y: y + 0.3, w: 1.6, h: 0.55, fontSize: 24,
        bold: true, color: i === 0 ? COL.amber : COL.white, fontFace: THEME.headFontFace, margin: 0, valign: "middle",
        isTextBox: true, objectName: `copy row ${i + 1} value` });
    });
    s.addText(`${pct(D.copying.share_exact_repeat)} repeat an earlier parent set exactly`, { x: M, y: 5.95, w: 7.4,
      h: 0.4, fontSize: 15, color: COL.muted, margin: 0, isTextBox: true, objectName: "exact repeat" });
    const recipeCards = [
      [ICON.copy, `${D.top_recipe.merges} merges`, `one author, the same parent set every time`],
      [ICON.users, `${D.crowd_recipe.authors} authors`,
        `copied one recipe ${D.crowd_recipe.merges} times: ${D.crowd_recipe.parents.split(" + ").map(shortName).join(" + ")}`],
    ];
    recipeCards.forEach(([ic, head, body], i) => {
      const y = 2.05 + i * 2.2;
      card(s, 8.35, y, W - M - 8.35, 1.95, `recipe card ${i + 1}`);
      badge(s, ic, 8.65, y + 0.32, 0.7, HEX.amber, `recipe ${i + 1}`);
      s.addText([{ text: head, options: { bold: true, color: COL.white, fontSize: 24, fontFace: THEME.headFontFace,
          breakLine: true } }, { text: body, options: { color: COL.muted, fontSize: 13 } }],
        { x: 9.55, y: y + 0.25, w: W - M - 9.85, h: 1.5, margin: 0, valign: "top", isTextBox: true,
          objectName: `recipe ${i + 1} text` });
    });
  }

  // =========================================================================
  // 8. Act III: the kingmakers
  // =========================================================================
  pres.addSection({ title: "Act III: the kingmakers" });
  s = contentSlide("Act III: the kingmakers", "ACT III  ·  THE KINGMAKERS", "A few base models hold the kingdom",
    "[4:15-4:55] RQ3: hubs and bridges. The hubs are official base models: FLUX, small Qwen models, Gemma. " +
    `Just ${D.top_0_01_models} models hold ${pct(D.top_0_01_share)} of all edges. The bridges are different: merges ` +
    `are ${pct(D.merge_share_nodes)} of models but hold ${pct(D.merge_share_betweenness)} of betweenness, because they ` +
    "sit on the paths between generations.");
  {
    card(s, M, 2.05, 6.6, 4.65, "hubs card");
    badge(s, ICON.crown, M + 0.3, 2.3, 0.62, HEX.amber, "hubs");
    s.addText("HUBS  ·  MOST CHILDREN", { x: M + 1.1, y: 2.42, w: 4.5, h: 0.4, fontSize: 13, bold: true,
      color: COL.muted, charSpacing: 3, margin: 0, isTextBox: true, objectName: "hubs heading" });
    const maxKids = D.hubs[0].children;
    D.hubs.forEach((h, i) => {
      const y = 3.05 + i * 0.56;
      s.addText(shortName(h.model), { x: M + 0.35, y, w: 3.0, h: 0.4, fontSize: 15, color: COL.white, margin: 0,
        isTextBox: true, objectName: `hub ${i + 1} name` });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M + 3.4, y: y + 0.08, w: 1.9 * h.children / maxKids, h: 0.26,
        rectRadius: 0.05, fill: { color: i === 0 ? HEX.amber : "5B7290" }, line: { width: 0, color: HEX.panel },
        objectName: `hub ${i + 1} bar` });
      s.addText(fmt(h.children), { x: M + 5.35, y, w: 1.1, h: 0.4, fontSize: 14, color: COL.muted, margin: 0,
        align: "right", isTextBox: true, objectName: `hub ${i + 1} value` });
    });
    // The concentration figure the speaker quotes, so the audience can see it too.
    s.addText([{ text: `${D.top_0_01_models} models`, options: { bold: true, color: COL.amber } },
               { text: ` (the top 0.01%) hold `, options: { color: COL.muted } },
               { text: `${pct(D.top_0_01_share)} of all edges`, options: { bold: true, color: COL.amber } }],
      { x: M + 0.35, y: 5.95, w: 6.0, h: 0.5, fontSize: 14, margin: 0, valign: "middle", isTextBox: true,
        objectName: "hub concentration" });
    card(s, 7.55, 2.05, W - M - 7.55, 4.65, "bridges card");
    badge(s, ICON.bridge, 7.85, 2.3, 0.62, HEX.amber, "bridges");
    s.addText("BRIDGES  ·  BETWEENNESS", { x: 8.65, y: 2.42, w: 4, h: 0.4, fontSize: 13, bold: true,
      color: COL.muted, charSpacing: 3, margin: 0, isTextBox: true, objectName: "bridges heading" });
    stat(s, 7.9, 3.15, 2.2, pct(D.merge_share_nodes), "of models are merges", "merge share", COL.white, 40);
    stat(s, 10.15, 3.15, 2.4, pct(D.merge_share_betweenness), "of betweenness is held by merges", "betweenness share",
      COL.amber, 40);
    s.addText(`${pct(D.merge_share_top100_bridges, 0)} of the top 100 bridges are merges in long merge chains, led by`,
      { x: 7.9, y: 4.55, w: 4.8, h: 0.6, fontSize: 14, color: COL.muted, margin: 0, valign: "top", isTextBox: true,
        objectName: "bridges note" });
    D.bridges.forEach((b, i) => s.addText(shortName(b), { x: 7.9, y: 5.2 + i * 0.42, w: 4.8, h: 0.36, fontSize: 14,
      color: COL.white, margin: 0, isTextBox: true, objectName: `bridge ${i + 1}` }));
  }

  // =========================================================================
  // 9. Act III: rich get richer
  // =========================================================================
  s = contentSlide("Act III: the kingmakers", "ACT III  ·  THE KINGMAKERS", "The rich get richer",
    "[4:55-5:40] Why do hubs form? I replayed every edge in creation order and measured how likely a model " +
    "with k children is to get the next one. On log axes the points follow a straight line: the exponent is " +
    `${D.beta.toFixed(2)}. That is linear preferential attachment: the rich get richer. But age barely matters: ` +
    `the correlation with age is only ${D.age_rho.toFixed(2)}.`);
  {
    const labels = D.rate_k.map((k) => (k >= 1000 ? (k / 1000).toFixed(k >= 10000 ? 0 : 1) + "k" : String(Math.round(k))));
    const linear = D.rate_k.map((k) => D.rate_r[0] * k);
    s.addChart(pres.charts.LINE, [
      { name: "observed attachment rate", labels, values: D.rate_r },
      { name: "linear preferential attachment", labels, values: linear },
    ], Object.assign(chartBase(), {
      x: M, y: 1.95, w: 8.2, h: 4.75, chartColors: [HEX.amber, HEX.muted], lineSize: 3, lineDataSymbol: "circle",
      lineDataSymbolSize: 8, valAxisLogScaleBase: 10, valAxisLabelFormatCode: "0.0E+0",
      showLegend: true, legendPos: "b", showCatAxisTitle: true, catAxisTitle: "children already held (k)",
      catAxisTitleColor: HEX.muted, catAxisTitleFontSize: 12, showValAxisTitle: true,
      valAxisTitle: "chance of the next child", valAxisTitleColor: HEX.muted, valAxisTitleFontSize: 12,
      catAxisLabelFontSize: 10, objectName: "attachment chart",
    }));
    card(s, 9.2, 2.05, W - M - 9.2, 4.2, "growth card");
    stat(s, 9.5, 2.35, 3.0, `β = ${D.beta.toFixed(2)}`, "attachment grows in proportion to k: preferential attachment",
      "beta", COL.amber, 44);
    stat(s, 9.5, 4.3, 3.0, `ρ = ${D.age_rho.toFixed(2)}`, "age vs children: older is not richer", "age", COL.white, 36);
  }

  // =========================================================================
  // 10. Act IV: the blast radius
  // =========================================================================
  pres.addSection({ title: "Act IV: the blast radius" });
  s = contentSlide("Act IV: the blast radius", "ACT IV  ·  THE BLAST RADIUS", "One flawed base. How far does it spread?",
    "[5:40-6:20] RQ4: if a base model has a flaw, how far does it spread? Each block is a base model; its " +
    `height is its descendants, and amber is what merges add. Merges add ${pct(D.reach_added)} more links, mostly on ` +
    `Llama and Mistral. ${fmt(D.multi_root)} models inherit from two or more bases, up to ${D.max_roots}. This assumes ` +
    "a merge inherits fully from every parent.");
  {
    const iw = 7.3, ih = iw * sky.h / sky.w;
    s.addImage({ path: path.join(ASSETS, "skyline.png"), x: M - 0.2, y: 2.4, w: iw, h: ih,
      altText: "3D bars: descendants of the top 8 base models, merges add a top section on Llama and Mistral bases",
      objectName: "skyline" });
    [["without merges", "5B7290"], ["added by merges", HEX.amber]].forEach(([label, color], i) => {
      s.addShape(pres.shapes.RECTANGLE, { x: M + i * 2.4, y: 2.12, w: 0.22, h: 0.22, fill: { color },
        line: { color, width: 0 }, objectName: `skyline key ${i + 1}` });
      s.addText(label, { x: M + i * 2.4 + 0.32, y: 2.05, w: 2, h: 0.35, fontSize: 12, color: COL.muted, margin: 0,
        isTextBox: true, objectName: `skyline key ${i + 1} label` });
    });
    card(s, 8.55, 2.05, W - M - 8.55, 4.2, "reach card");
    stat(s, 8.9, 2.3, 3.6, "+" + pct(D.reach_added), "more root–descendant links through merges", "reach added",
      COL.amber, 48);
    stat(s, 8.9, 3.75, 3.6, fmt(D.multi_root), "models inherit from two or more bases", "multi root", COL.white, 32);
    stat(s, 8.9, 5.0, 3.6, String(D.max_roots), "bases behind a single model, at most", "max roots", COL.white, 32);
  }

  // =========================================================================
  // 11. Act IV: where to audit
  // =========================================================================
  s = contentSlide("Act IV: the blast radius", "ACT IV  ·  THE BLAST RADIUS", "Audit 100 models, cover half the ecosystem",
    "[6:20-6:55] So where should an auditor look first? Checking the top 100 models by PageRank, and " +
    `everything built from them, covers ${pct(D.coverage_pagerank[2], 0)} of the graph. A hundred random models ` +
    `cover ${pct(D.coverage_random[2])}. That is hub versus random failure, from the large-scale networks lecture.`);
  {
    const labels = D.coverage_k.map((k) => (k === 1 ? "top 1" : `top ${fmt(k)}`));
    s.addChart(pres.charts.LINE, [
      { name: "top models by PageRank", labels, values: D.coverage_pagerank.map((v) => 100 * v) },
      { name: "random models", labels, values: D.coverage_random.map((v) => 100 * v) },
    ], Object.assign(chartBase(), {
      x: M, y: 1.95, w: 8.2, h: 4.75, chartColors: [HEX.amber, "5C616A"], lineSize: 3, lineDataSymbol: "circle",
      lineDataSymbolSize: 9, valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25,
      valAxisLabelFormatCode: "0\"%\"",
      showLegend: true, legendPos: "b", showValAxisTitle: true, valAxisTitle: "share of all models covered",
      valAxisTitleColor: HEX.muted, valAxisTitleFontSize: 12, objectName: "coverage chart",
    }));
    card(s, 9.2, 2.05, W - M - 9.2, 4.2, "coverage card");
    stat(s, 9.5, 2.35, 3.0, pct(D.coverage_pagerank[2], 0), "covered by auditing the top 100 models", "coverage top",
      COL.amber, 54);
    stat(s, 9.5, 4.3, 3.0, pct(D.coverage_random[2]), "covered by 100 random models", "coverage random",
      COL.white, 36);
  }

  // =========================================================================
  // 12. Epilogue: it works
  // =========================================================================
  pres.addSection({ title: "Epilogue" });
  s = contentSlide("Epilogue", "EPILOGUE", "One command reproduces everything",
    "[6:55-7:35] Everything is reproducible with one script, MergeMap.py. Built-in checks run every time: " +
    "the data hash, no cycles, PageRank against my Assignment 3 code, assortativity against igraph. Two full runs " +
    "give identical results. (Only if time allows: python MergeMap.py --quick takes about a minute; otherwise just " +
    "show results/index.html.)");
  {
    const steps = ["download", "edges", "graph", "RQ1", "RQ2", "RQ3", "RQ4", "baselines", "viewer"];
    const sw = (W - 2 * M - 8 * 0.12) / 9;
    steps.forEach((label, i) => {
      const x = M + i * (sw + 0.12);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.15, w: sw, h: 0.9, rectRadius: 0.1,
        fill: { color: i === 8 ? HEX.amber : HEX.panel2 }, line: { color: HEX.line, width: 0.75 }, shadow: softShadow(),
        objectName: `step ${i + 1}` });
      s.addText([{ text: String(i + 1), options: { fontSize: 11, color: i === 8 ? COL.bg : COL.muted, breakLine: true } },
                 { text: label, options: { fontSize: 14, bold: true, color: i === 8 ? COL.bg : COL.white } }],
        { x, y: 2.15, w: sw, h: 0.9, align: "center", valign: "middle", margin: 0, isTextBox: true,
          objectName: `step ${i + 1} text` });
    });
    const checks = [
      ["Snapshot matches the pinned commit", `SHA-256 · ${D.snapshot.commit}`],
      ["Lineage graph has no cycles", "own topological sort"],
      ["PageRank = Assignment 3 matrix inverse", `largest difference ${D.pagerank_check.toExponential(1)}`],
      ["Assortativity = igraph", "same value both ways"],
      ["Two full runs, identical outputs", "fixed order, fixed seeds"],
    ];
    card(s, M, 3.45, 7.3, 3.25, "checks card");
    checks.forEach(([head, note], i) => {
      const y = 3.68 + i * 0.58;
      badge(s, ICON.check, M + 0.3, y, 0.4, HEX.teal, `check ${i + 1}`);
      s.addText([{ text: head + "   ", options: { color: COL.white, bold: true } }, { text: note, options: { color: COL.muted } }],
        { x: M + 0.9, y: y - 0.02, w: 6.2, h: 0.44, fontSize: 14, margin: 0, valign: "middle", isTextBox: true,
          objectName: `check ${i + 1} text` });
    });
    card(s, 8.3, 3.45, W - M - 8.3, 3.25, "demo card", "3A2C12");
    badge(s, ICON.play, 8.6, 3.75, 0.7, HEX.amber, "demo");
    s.addText([{ text: "Live demo", options: { bold: true, color: COL.white, fontSize: 24, fontFace: THEME.headFontFace,
        breakLine: true } }, { text: "python MergeMap.py --quick", options: { color: COL.amber, fontSize: 15,
        fontFace: "Consolas", breakLine: true } }, { text: "about 1 minute, then open results/index.html",
        options: { color: COL.muted, fontSize: 13 } }],
      { x: 8.6, y: 4.65, w: W - M - 8.9, h: 1.8, margin: 0, valign: "top", isTextBox: true, objectName: "demo text" });
  }

  // =========================================================================
  // 13. The ending
  // =========================================================================
  s = contentSlide("Epilogue", "EPILOGUE", "The ending",
    "[7:35-8:05] Three things to remember. Merges are rare, but they fuse the ecosystem. They stay in the " +
    `family, inbreeding ${Math.round(D.inbred["1"] / D.inbred_within_family["1"])} times and copying recipes ` +
    `${Math.round(D.copying.share_copying / D.copying_within_family)} times as often as chance. And growth is ` +
    `rich-get-richer, so auditing 100 models covers ${pct(D.coverage_pagerank[2], 0)} of the ecosystem.`);
  {
    const take = [
      [`${(D.largest_with / D.largest_without).toFixed(1)}×`, "Merges are rare, but they fuse the families",
        `${pct(D.merge_share_of_linked)} of models make the largest group ${(D.largest_with / D.largest_without).toFixed(1)}× bigger`],
      [`${Math.round(D.inbred["1"] / D.inbred_within_family["1"])}× · ${Math.round(D.copying.share_copying / D.copying_within_family)}×`, "They stay in the family, inbreed and copy",
        `close relatives ${(D.inbred["1"] / D.inbred_within_family["1"]).toFixed(1)}× and recipes ${(D.copying.share_copying / D.copying_within_family).toFixed(1)}× more than chance`],
      [pct(D.coverage_pagerank[2], 0), "Rich get richer, so audit the hubs",
        `β = ${D.beta.toFixed(2)}; the top 100 models cover ${pct(D.coverage_pagerank[2], 0)} of all models`],
    ];
    const cw = (W - 2 * M - 2 * 0.35) / 3;
    take.forEach(([big, head, body], i) => {
      const x = M + i * (cw + 0.35);
      card(s, x, 2.05, cw, 4.2, `takeaway ${i + 1}`);
      s.addText(String(i + 1).padStart(2, "0"), { x: x + 0.35, y: 2.3, w: 1, h: 0.4, fontSize: 14, bold: true,
        color: COL.dim, charSpacing: 3, margin: 0, isTextBox: true, objectName: `takeaway ${i + 1} index` });
      s.addText(big, { x: x + 0.35, y: 2.75, w: cw - 0.7, h: 1.05, fontSize: 54, bold: true, color: COL.amber,
        fontFace: THEME.headFontFace, margin: 0, isTextBox: true, objectName: `takeaway ${i + 1} number` });
      s.addText([{ text: head, options: { bold: true, color: COL.white, fontSize: 20, breakLine: true } },
                 { text: body, options: { color: COL.muted, fontSize: 15 } }],
        { x: x + 0.35, y: 4.0, w: cw - 0.7, h: 2.0, margin: 0, valign: "top", isTextBox: true,
          objectName: `takeaway ${i + 1} text` });
    });
  }

  // =========================================================================
  // 14. Limitations
  // =========================================================================
  s = contentSlide("Epilogue", "EPILOGUE", "What this cannot tell us",
    "[8:05-8:40] Some limits. Lineage is self-declared, so every count is a lower bound. A quarter of " +
    "merge parents have no known family. RQ4 assumes full inheritance, and this is one snapshot. Some patterns are " +
    "partly built in, and the attachment result supports preferential attachment without proving it.");
  {
    const limits = [
      [ICON.pen, "Self-declared lineage", `only ${pct(D.declaring_base / D.models, 0)} of models declare a parent, so every count is a lower bound`],
      [ICON.question, "Unknown families", `${pct(D.merge_parents_unknown)} of merge parents match none of the ${D.families} family name patterns`],
      [ICON.link, "Full inheritance assumed", "RQ4 treats a merge as inheriting everything from every parent; the data has no flaw labels"],
      [ICON.camera, "One snapshot", `Hugging Face on ${D.snapshot.date}; the Hub changes every day`],
      [ICON.cubes, "Partly built in", "merges have many ancestors by definition, which inflates their betweenness and clustering"],
      [ICON.seedling, "Fitness not ruled out", "a linear attachment rate is also what built-in differences in model quality produce"],
    ];
    const cw = (W - 2 * M - 2 * 0.3) / 3, ch = 2.05;
    limits.forEach(([ic, head, body], i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = M + col * (cw + 0.3), y = 2.05 + row * (ch + 0.25);
      card(s, x, y, cw, ch, `limit card ${i + 1}`);
      badge(s, ic, x + 0.3, y + 0.3, 0.58, HEX.panel2, `limit ${i + 1}`);
      s.addText(head, { x: x + 1.05, y: y + 0.3, w: cw - 1.3, h: 0.58, fontSize: 17, bold: true, color: COL.white,
        margin: 0, valign: "middle", isTextBox: true, objectName: `limit ${i + 1} head` });
      s.addText(body, { x: x + 0.3, y: y + 1.0, w: cw - 0.6, h: ch - 1.15, fontSize: 14, color: COL.muted,
        margin: 0, valign: "top", isTextBox: true, objectName: `limit ${i + 1} body` });
    });
  }

  // =========================================================================
  // 15. Thank you
  // =========================================================================
  s = pres.addSlide({ masterName: "MM_COVER", sectionTitle: "Epilogue" });
  {
    const iw = 8.2, ih = iw * hero.h / hero.w;
    s.addImage({ path: path.join(ASSETS, "hero_network.png"), x: W - iw + 1.2, y: (H - ih) / 2 + 0.35, w: iw, h: ih,
      altText: "3D cocitation network of the most-cited merge parents", objectName: "closing network" });
    s.addText("THE END", { x: M, y: 1.35, w: 6, h: 0.35, fontSize: 12, bold: true, color: COL.amber, charSpacing: 6,
      margin: 0, isTextBox: true, objectName: "closing eyebrow" });
    s.addText("Thank you", { x: M, y: 1.8, w: 7, h: 1.6, fontSize: 88, color: COL.white, fontFace: THEME.headFontFace,
      margin: 0, isTextBox: true, objectName: "thank you" });
    s.addText("Any questions?", { x: M, y: 3.45, w: 6, h: 0.9, fontSize: 40, color: COL.amber,
      fontFace: THEME.headFontFace, margin: 0, isTextBox: true, objectName: "questions" });
    s.addText([{ text: "MergeMap", options: { bold: true, color: COL.white, breakLine: true } },
               { text: "A network analysis of model merging on Hugging Face", options: { color: COL.muted, breakLine: true } },
               { text: "Md Minhajul Abedin  ·  COMP 6917 Complex Networks", options: { color: COL.muted } }],
      { x: M, y: H - 1.75, w: 6, h: 1.1, fontSize: 14, margin: 0, valign: "bottom", isTextBox: true,
        objectName: "closing credits" });
    s.addNotes("[8:40] Thank you. I'm happy to take questions. " +
      "If asked: unknown families = names that reveal no family (root-level results need no labels); large z-scores = " +
      "the random baselines barely vary, so the size of the gap is the finding; within-family baseline = models of " +
      "different architectures cannot be merged.");
  }

  await pres.writeFile({ fileName: OUT });
  const { applyTheme } = require("./apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("saved " + OUT);
}

main().catch((err) => { console.error(err); process.exit(1); });
