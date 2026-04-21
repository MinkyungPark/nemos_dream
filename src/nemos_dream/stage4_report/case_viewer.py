"""Stage-by-stage case progression viewer for the nemos_dream pipeline.

Reads stage1, stage2, stage3 JSONL files, joins records by ID, and renders
a static HTML file that lets you page through each use-case and see what
changed at every stage (source → Korean rewrite → quality verdict).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data loading & joining
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def join_stages(
    stage1_path: Path | None = None,
    stage2_path: Path | None = None,
    stage3_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Join stage JSONL files by ``id`` and return merged records.

    Each returned record has the form::

        {"id": "...", "stage1": {...}|None, "stage2": {...}|None, "stage3": {...}|None}

    The record list is ordered by first appearance across the provided files.
    """
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def _ingest(path: Path | None, key: str) -> None:
        if not (path and Path(path).exists()):
            return
        for row in _read_jsonl(Path(path)):
            rid = str(row.get("id") or "")
            if rid not in by_id:
                by_id[rid] = {"id": rid, "stage1": None, "stage2": None, "stage3": None}
                order.append(rid)
            by_id[rid][key] = row

    _ingest(stage1_path, "stage1")
    _ingest(stage2_path, "stage2")
    _ingest(stage3_path, "stage3")

    return [by_id[rid] for rid in order]


# ---------------------------------------------------------------------------
# HTML rendering helpers (inline JS template)
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<title>Pipeline Case Viewer — nemos_dream</title>
<style>
  :root {
    --bg:#f8f9fa; --panel:rgba(255,255,255,0.95); --panel2:#f1f5f9; --panel3:#e8edf5;
    --text:#1a1a2e; --muted:#64748b; --accent:#76b900; --accent2:#0ea5e9;
    --good:#76b900; --warn:#f59e0b; --bad:#ef4444;
    --chip:#e8edf5; --border:#dde3ed;
  }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans KR",sans-serif;
         background:linear-gradient(180deg,#f8f9fa 0%,#f1f5f9 100%); color:var(--text); line-height:1.5; min-height:100vh; }
  header { position:sticky; top:0; z-index:20; background:rgba(255,255,255,0.97); border-bottom:1px solid var(--border);
           padding:10px 18px; display:flex; align-items:center; gap:10px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
  header h1 { font-size:14px; margin:0; color:var(--muted); font-weight:500; }
  .spacer { flex:1; }
  .id-badge { background:rgba(118,185,0,.1); color:var(--accent); padding:3px 8px; border-radius:4px;
              font-family:ui-monospace,monospace; font-size:12px; border:1px solid rgba(118,185,0,.25); }
  .stage-badge { padding:2px 8px; border-radius:10px; font-size:11px; font-weight:700; }
  .stage-badge.s1 { background:rgba(118,185,0,.12); color:#4a7a00; }
  .stage-badge.s2 { background:rgba(14,165,233,.12); color:#0369a1; }
  .stage-badge.s3 { background:rgba(139,92,246,.12); color:#6d28d9; }
  button, input[type=number] { background:var(--panel2); color:var(--text); border:1px solid var(--border);
    border-radius:6px; padding:5px 12px; cursor:pointer; font-size:13px; }
  button:hover { border-color:var(--accent); color:var(--accent); }
  button:disabled { opacity:.4; cursor:not-allowed; }
  input[type=number] { width:72px; text-align:center; }
  .counter { color:var(--muted); font-variant-numeric:tabular-nums; }
  kbd { background:var(--panel2); border:1px solid var(--border); border-bottom-width:2px;
        border-radius:4px; padding:1px 6px; font-size:11px; }
  .tab-bar { display:flex; gap:4px; padding:8px 18px; background:rgba(255,255,255,0.97); border-bottom:1px solid var(--border); }
  .tab-bar button { border-radius:6px; padding:4px 14px; font-size:12px; font-weight:600; }
  .tab-bar button.active { background:var(--accent); color:#fff; border-color:transparent; }
  main { max-width:1400px; margin:0 auto; padding:16px; display:grid; gap:12px; }
  .dialogue-row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  @media(max-width:800px) { .dialogue-row { grid-template-columns:1fr; } }
  .card { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:14px 16px;
          box-shadow:0 2px 8px rgba(0,0,0,.04); }
  .card h2 { font-size:11px; margin:0 0 10px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }
  .dialogue { display:flex; flex-direction:column; gap:6px; }
  .bubble { max-width:88%; padding:7px 11px; border-radius:12px; background:var(--panel2); }
  .bubble.right { align-self:flex-end; background:rgba(118,185,0,.1); border:1px solid rgba(118,185,0,.2); }
  .bubble .spk { font-size:10px; color:var(--muted); margin-bottom:2px; font-weight:600; }
  .bubble .txt { font-size:13.5px; white-space:pre-wrap; }
  .kv { display:grid; grid-template-columns:max-content 1fr; column-gap:10px; row-gap:4px; font-size:12.5px; }
  .kv .k { color:var(--muted); }
  .chips { display:flex; flex-wrap:wrap; gap:3px; }
  .chip { background:var(--chip); color:var(--text); font-size:11px; padding:2px 7px; border-radius:10px; }
  .chip.a { background:rgba(118,185,0,.12); color:#4a7a00; }
  .chip.w { background:rgba(245,158,11,.12); color:#b45309; }
  .chip.g { background:rgba(118,185,0,.12); color:#4a7a00; }
  .chip.b { background:rgba(239,68,68,.12); color:#b91c1c; }
  .bar-row { display:flex; align-items:center; gap:8px; font-size:12.5px; }
  .bar-track { flex:1; height:6px; background:var(--chip); border-radius:3px; max-width:120px; }
  .bar-fill { height:100%; border-radius:3px; }
  .speaker-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:8px; }
  .spk-card { background:var(--panel2); border-radius:8px; padding:10px 12px; border:1px solid var(--border); }
  .spk-card .name { font-weight:600; font-size:13px; color:var(--accent); margin-bottom:6px; }
  table.refs { width:100%; border-collapse:collapse; font-size:12.5px; }
  table.refs th, table.refs td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--border); }
  table.refs th { color:var(--muted); font-weight:500; font-size:11px; text-transform:uppercase; }
  table.refs .ko { color:var(--accent2); font-weight:500; }
  .quality-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:8px; }
  .score-card { background:var(--panel2); border-radius:8px; padding:10px 12px; border:1px solid var(--border); }
  .score-card .label { font-size:11px; color:var(--muted); margin-bottom:4px; }
  .valid-banner { padding:10px 14px; border-radius:8px; font-weight:700; font-size:14px; margin-bottom:10px; }
  .valid-banner.ok { background:rgba(118,185,0,.12); color:#4a7a00; border:1px solid rgba(118,185,0,.3); }
  .valid-banner.reject { background:rgba(239,68,68,.1); color:#b91c1c; border:1px solid rgba(239,68,68,.25); }
  .empty { color:var(--muted); font-style:italic; font-size:12px; }
  details.raw summary { cursor:pointer; color:var(--muted); font-size:11px; }
  details.raw pre { background:#f8fafc; color:#334155; border:1px solid var(--border); padding:10px; border-radius:6px;
                    overflow:auto; font-size:11.5px; max-height:320px; margin-top:6px; }
  .section { display:none; }
  .section.active { display:block; }
</style>
</head>
<body>
<header>
  <h1>nemos_dream · Pipeline Case Viewer</h1>
  <span class="id-badge" id="rec-id">—</span>
  <div class="spacer"></div>
  <button id="prev">◀</button>
  <input id="jump" type="number" min="1"/>
  <span class="counter">/ <span id="total">0</span></span>
  <button id="next">▶</button>
  <span class="counter" style="margin-left:6px;">(<kbd>←</kbd><kbd>→</kbd>)</span>
</header>
<div class="tab-bar">
  <button class="active" data-tab="scene">Scene &amp; Decomp</button>
  <button data-tab="speakers">Speakers</button>
  <button data-tab="refs">Cultural Refs</button>
  <button data-tab="quality">Quality</button>
</div>
<main id="app">
  <div style="padding:40px;color:var(--muted);">Loading…</div>
</main>

<script>
try {
const RECORDS = __DATA__;
const app = document.getElementById("app");
const total = document.getElementById("total");
const jumpInput = document.getElementById("jump");
total.textContent = RECORDS.length;
jumpInput.max = RECORDS.length;
let cur = 0;
let activeTab = "scene";

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function chip(t, cls="") { return `<span class="chip ${cls}">${esc(t)}</span>`; }
function chips(arr, cls="") {
  if (!arr || !arr.length) return `<span class="empty">—</span>`;
  return `<div class="chips">${arr.map(x=>chip(String(x),cls)).join("")}</div>`;
}
function kv(pairs) {
  if (!pairs.length) return "";
  return `<div class="kv">${pairs.map(([k,v])=>`<div class="k">${esc(k)}</div><div class="v">${v}</div>`).join("")}</div>`;
}
function emotionView(e) {
  if (!e) return `<span class="empty">—</span>`;
  const pct = Math.max(0, Math.min(5, Number(e.intensity ?? 0))) * 20;
  return `${chip(e.type||"—","a")} <span class="bar-row" style="display:inline-flex">
    <span class="bar-track"><span class="bar-fill" style="width:${pct}%;background:var(--accent)"></span></span>
    <span style="font-size:11px;color:var(--muted)">${esc(e.intensity)}/5</span></span>`;
}
function scoreBar(val, max=5) {
  if (val == null) return `<span class="empty">—</span>`;
  const pct = (Number(val)/max)*100;
  const color = pct>=80?"var(--good)":pct>=50?"var(--warn)":"var(--bad)";
  return `<div class="bar-row">
    <span class="bar-track"><span class="bar-fill" style="width:${pct}%;background:${color}"></span></span>
    <span style="font-size:12px">${esc(val)}</span>
  </div>`;
}

function renderDialogue(turns, title, cls="") {
  if (!turns || !turns.length) return `<div class="card"><h2>${esc(title)}</h2><span class="empty">—</span></div>`;
  const speakers = [...new Set(turns.map(t=>t.speaker))];
  const bubbles = turns.map(t => {
    const side = speakers.indexOf(t.speaker) % 2 === 1 ? "right" : "";
    return `<div class="bubble ${side}">
      <div class="spk">${esc(t.speaker)} · #${esc(t.index)}</div>
      <div class="txt">${esc(t.text)}</div>
    </div>`;
  }).join("");
  return `<div class="card ${cls}"><h2>${esc(title)}</h2><div class="dialogue">${bubbles}</div></div>`;
}

// ----- SCENE & DECOMP TAB -----
function renderSceneTab(r) {
  const s1 = r.stage1 || {};
  const scene = s1.scene || {};
  const d = s1.dialogue_decomposed || {};
  return `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
      <div class="card">
        <h2>Scene</h2>
        ${scene.narrative_en ? `<div style="font-size:13px;color:var(--text);background:var(--panel2);padding:8px 10px;border-radius:6px;margin-bottom:8px">${esc(scene.narrative_en)}</div>` : ""}
        ${kv([
          ["setting", chip(scene.setting||"—","a")],
          ["relationship", chip(scene.relationship_type||"—")],
          ["topics", chips(scene.topics,"a")],
        ])}
      </div>
      <div class="card">
        <h2>Dialogue Decomposition</h2>
        ${kv([
          ["register", chip(d.overall_register||"—","a")],
          ["emotion", emotionView(d.overall_emotion)],
          ["speech acts", chips(d.speech_acts)],
          ["cultural refs found", String((d.cultural_refs||[]).length)],
        ])}
      </div>
    </div>
    ${r.stage2 ? `<div class="card">
      <h2>Translation Meta</h2>
      ${kv([
        ["target platform", chip(((r.stage2.translation_meta||{}).target_platform)||(r.stage2.translation_meta||{}).platform||"—","a")],
        ["target community", esc((r.stage2.translation_meta||{}).target_community||"—")],
        ["pass", chip((r.stage2.translation_meta||{}).pass||"—","g")],
      ])}
    </div>` : ""}
  `;
}

// ----- SPEAKERS TAB -----
function renderSpeakersTab(r) {
  const s1 = r.stage1 || {};
  const s2 = r.stage2 || {};
  const speakers = s1.speakers || [];
  const personas = s2.speaker_personas || [];
  const styles = s2.speaker_styles || [];
  const personaMap = Object.fromEntries(personas.map(p=>[p.speaker_ref,p]));
  const styleMap = Object.fromEntries(styles.map(st=>[st.speaker_ref,st]));

  if (!speakers.length) return `<div class="card"><span class="empty">No speaker data.</span></div>`;
  const cards = speakers.map(sp => {
    const p = personaMap[sp.name_en] || {};
    const st = styleMap[sp.name_en] || {};
    const koPersona = personas.length ? `
      ${p.gender ? `<div style="margin-top:6px;font-size:11px;color:var(--muted);font-weight:600">KOREAN PERSONA</div>` : ""}
      ${kv([
        p.gender ? ["gender", esc(p.gender)] : null,
        p.age ? ["age", esc(p.age)] : null,
        p.occupation ? ["occupation", esc(p.occupation)] : null,
        p.education ? ["education", esc(p.education)] : null,
        p.marital_status ? ["marital", esc(p.marital_status)] : null,
        p.family_type ? ["family", esc(p.family_type)] : null,
        p.housing ? ["housing", esc(p.housing)] : null,
        p.military_status ? ["military", esc(p.military_status)] : null,
        st.speech_style_notes ? ["style notes", `<span style="font-size:12px;color:var(--muted)">${esc(st.speech_style_notes)}</span>`] : null,
      ].filter(Boolean))}` : "";
    return `<div class="spk-card">
      <div class="name">${esc(sp.name_en)}</div>
      ${kv([
        ["role", chip(sp.role_in_scene||"—")],
        ["gender", esc(sp.gender_hint||"—")],
        ["age", chip(sp.age_group_hint||"—","a")],
        ["register", chip(sp.register||"—","a")],
        ["emotion", emotionView(sp.dominant_emotion)],
        sp.occupation_hint ? ["occupation", esc(sp.occupation_hint)] : null,
        sp.personality_traits?.length ? ["traits", chips(sp.personality_traits)] : null,
        sp.interests_hints?.length ? ["interests", chips(sp.interests_hints)] : null,
        sp.speech_style_notes ? ["style (en)", `<span style="font-size:12px;color:var(--muted)">${esc(sp.speech_style_notes)}</span>`] : null,
      ].filter(Boolean))}
      ${koPersona}
    </div>`;
  }).join("");
  return `<div class="speaker-grid">${cards}</div>`;
}

// ----- CULTURAL REFS TAB -----
function renderRefsTab(r) {
  const s1 = r.stage1 || {};
  const s2 = r.stage2 || {};
  const cultural = (s1.dialogue_decomposed || {}).cultural_refs || [];
  const mapped = s2.mapped_refs || s1.mapped_refs || [];

  const found = cultural.length ? `
    <div class="card" style="margin-bottom:12px">
      <h2>Cultural Refs Found (Stage 1)</h2>
      ${cultural.map(r=>`${chip(r.term||"","w")} <span style="font-size:11px;color:var(--muted)">${esc(r.type||"")}</span>`).join(" ")}
    </div>` : "";

  const mappedHtml = mapped.length ? `
    <div class="card">
      <h2>Mapped Refs EN → KO (Stage 2)</h2>
      <table class="refs">
        <thead><tr><th>English</th><th>Korean</th><th>Type</th><th>Source</th><th>Notes</th></tr></thead>
        <tbody>${mapped.map(ref=>`
          <tr>
            <td>${esc(ref.term)}</td>
            <td class="ko">${esc(ref.ko||"—")}</td>
            <td>${chip(ref.type||"—")}</td>
            <td>${chip(ref.source||"—", ref.retrieved?"g":"b")}</td>
            <td style="font-size:11px;color:var(--muted)">${esc(ref.notes||"")}${
              (ref.validation||[]).length ? `<br><span style="color:var(--bad)">⚠ ${esc(JSON.stringify(ref.validation))}</span>` : ""
            }</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>` : `<div class="card"><span class="empty">No mapped refs.</span></div>`;

  return found + mappedHtml;
}

// ----- QUALITY TAB -----
function renderQualityTab(r) {
  const s3 = r.stage3;
  if (!s3) return `<div class="card"><span class="empty">Stage 3 data not available.</span></div>`;

  const q = s3.quality || {};
  const valid = s3.valid !== false;
  const banner = `<div class="valid-banner ${valid?"ok":"reject"}">${valid?"✓ Accepted":"✗ Rejected"} — iter ${s3.iter||0}</div>`;

  const judgeScores = [
    ["property_preservation", q.property_preservation],
    ["naturalness", q.naturalness],
    ["cultural_appropriateness", q.cultural_appropriateness],
    ["register_consistency", q.register_consistency],
    ["persona_style_consistency", q.persona_style_consistency],
  ].filter(([,v])=>v!=null);

  const floatScores = [
    ["intra_kr_coherence", q.intra_kr_coherence, 1.0],
    ["aggregate", q.aggregate, 5.0],
  ].filter(([,v])=>v!=null);

  const guardrails = [
    ["safety_pass", q.safety_pass],
    ["pii_pass", q.pii_pass],
  ].filter(([,v])=>v!=null);

  const scoresHtml = `
    <div class="quality-grid" style="margin-bottom:12px">
      ${judgeScores.map(([label, val]) => `
        <div class="score-card">
          <div class="label">${esc(label)}</div>
          ${scoreBar(val, 5)}
        </div>`).join("")}
      ${floatScores.map(([label, val, max]) => `
        <div class="score-card">
          <div class="label">${esc(label)}</div>
          ${scoreBar(val != null ? Math.round(val*10)/10 : null, max)}
        </div>`).join("")}
      ${guardrails.map(([label, val]) => `
        <div class="score-card">
          <div class="label">${esc(label)}</div>
          <span class="chip ${val?"g":"b"}">${val?"PASS":"FAIL"}</span>
        </div>`).join("")}
    </div>`;

  const rewardHtml = q.reward ? `
    <div class="card" style="margin-bottom:12px">
      <h2>Reward Scores</h2>
      <div class="quality-grid">
        ${Object.entries(q.reward).map(([k,v]) => `
          <div class="score-card">
            <div class="label">${esc(k)}</div>
            ${scoreBar(v != null ? Math.round(Number(v)*100)/100 : null, 1.0)}
          </div>`).join("")}
      </div>
    </div>` : "";

  const reasoningHtml = q.judge_reasoning && Object.keys(q.judge_reasoning).length ? `
    <div class="card" style="margin-bottom:12px">
      <h2>Judge Reasoning</h2>
      <div class="kv">${Object.entries(q.judge_reasoning).map(([k,v])=>
        `<div class="k" style="font-size:12px">${esc(k)}</div><div style="font-size:12.5px;color:var(--muted)">${esc(v)}</div>`
      ).join("")}</div>
    </div>` : "";

  const rejectHtml = (s3.reject_reasons||[]).length ? `
    <div class="card" style="margin-bottom:12px">
      <h2>Reject Reasons</h2>
      ${(s3.reject_reasons||[]).map(rr=>`
        <div style="margin-bottom:6px">
          ${chip(rr.stage||"—","b")} ${rr.rule?chip(rr.rule,"w"):""}
          <span style="font-size:12.5px;color:var(--muted);margin-left:6px">${esc(rr.detail||"")}</span>
        </div>`).join("")}
    </div>` : "";

  return banner + `<div class="card" style="margin-bottom:12px"><h2>Judge Scores</h2>${scoresHtml}</div>` + rewardHtml + reasoningHtml + rejectHtml;
}

// ----- MAIN RENDER -----
function render(i) {
  const r = RECORDS[i];
  if (!r) return;
  document.getElementById("rec-id").textContent = r.id || `#${i}`;
  jumpInput.value = i + 1;

  const s1 = r.stage1 || {};
  const s2 = r.stage2 || {};
  const s3 = r.stage3 || null;

  const stageIndicator = [
    s1.id ? `<span class="stage-badge s1">Stage 1</span>` : "",
    s2.id ? `<span class="stage-badge s2">Stage 2</span>` : "",
    s3 ? `<span class="stage-badge s3">Stage 3</span>` : "",
  ].filter(Boolean).join(" ");

  const sourceDlg = renderDialogue(s1.source_dialogue, "Source Dialogue (EN)");
  const koDlg = s2.korean_dialogue?.length
    ? renderDialogue(s2.korean_dialogue, "Korean Dialogue (KO)")
    : `<div class="card"><h2>Korean Dialogue (KO)</h2><span class="empty">Stage 2 not available.</span></div>`;

  const tabContent = {
    scene: renderSceneTab(r),
    speakers: renderSpeakersTab(r),
    refs: renderRefsTab(r),
    quality: renderQualityTab(r),
  };

  app.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">${stageIndicator}</div>
    <div class="dialogue-row">${sourceDlg}${koDlg}</div>
    <div id="tab-scene" class="section${activeTab==="scene"?" active":""}">${tabContent.scene}</div>
    <div id="tab-speakers" class="section${activeTab==="speakers"?" active":""}">${tabContent.speakers}</div>
    <div id="tab-refs" class="section${activeTab==="refs"?" active":""}">${tabContent.refs}</div>
    <div id="tab-quality" class="section${activeTab==="quality"?" active":""}">${tabContent.quality}</div>
    <details class="raw card">
      <summary>raw JSON</summary>
      <pre>${esc(JSON.stringify(r, null, 2))}</pre>
    </details>
  `;

  document.getElementById("prev").disabled = i <= 0;
  document.getElementById("next").disabled = i >= RECORDS.length - 1;
}

function go(delta) {
  cur = Math.max(0, Math.min(RECORDS.length - 1, cur + delta));
  render(cur);
}

// Tab switching (event delegation)
document.querySelector(".tab-bar").addEventListener("click", e => {
  const btn = e.target.closest("[data-tab]");
  if (!btn) return;
  activeTab = btn.getAttribute("data-tab");
  document.querySelectorAll(".tab-bar button").forEach(b => b.classList.toggle("active", b === btn));
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  const sec = document.getElementById("tab-" + activeTab);
  if (sec) sec.classList.add("active");
});

document.getElementById("prev").onclick = () => go(-1);
document.getElementById("next").onclick = () => go(1);
jumpInput.oninput = e => {
  const v = parseInt(e.target.value, 10);
  if (!isNaN(v) && v >= 1 && v <= RECORDS.length) { cur = v - 1; render(cur); }
};
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  if (e.key === "ArrowLeft") go(-1);
  else if (e.key === "ArrowRight") go(1);
});

render(cur);
} catch (err) {
  document.getElementById("app").innerHTML =
    `<div style="padding:30px;color:var(--bad);white-space:pre-wrap;font-family:monospace">JS error: ${err && err.stack ? err.stack : err}</div>`;
  console.error(err);
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_html(
    stage1_path: Path | None = None,
    stage2_path: Path | None = None,
    stage3_path: Path | None = None,
    output_path: Path = Path("data/reports/case_viewer.html"),
) -> Path:
    """Join stage files by ID and write a static case-viewer HTML.

    Returns the output path.
    """
    records = join_stages(stage1_path, stage2_path, stage3_path)
    if not records:
        raise ValueError("No records found — provide at least one stage path.")

    data_js = json.dumps(records, ensure_ascii=False)
    page = _HTML_TEMPLATE.replace("__DATA__", data_js)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    return output_path
