"""Distribution shift analysis for the nemos_dream pipeline.

Computes TF-IDF + PCA/t-SNE embeddings across pipeline stages and renders
an interactive HTML showing how each stage's distribution moves relative
to the Korea persona target.

Adapted from nemo_dream/scripts/analyze_distribution_shift.py for the
nemos_dream Pydantic schema (Stage1Output / Stage2Output / Stage3Output).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE

PERSONA_ATTRIBUTES = [
    "sex",
    "age",
    "occupation",
    "education_level",
    "marital_status",
    "family_type",
    "housing_type",
    "military_status",
]

# HuggingFace dataset identifier for the Korea persona target
_HF_TARGET_DATASET = "nvidia/Nemotron-Personas-Korea"

_STAGE_COLORS = {
    "Input": "#98A2B3",
    "Stage1": "#155EEF",
    "Stage2": "#0E7090",
    "Stage3": "#12B76A",
    "Korea Target": "#C11574",
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
        if limit is not None and len(rows) >= limit:
            break
    return rows


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _value_bucket(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "unknown"
    return str(value).strip() or "unknown"


def _age_bucket(age: Any) -> str:
    try:
        a = int(age)
        decade = (a // 10) * 10
        return f"{decade}s"
    except (TypeError, ValueError):
        s = str(age).strip().lower()
        # already bucketed (e.g. "20s", "30s")
        if s.endswith("s") and s[:-1].isdigit():
            return s
        return s or "unknown"


def _normalize_sex(value: Any) -> str:
    s = str(value or "").strip().lower()
    if s in ("male", "man", "m", "남자", "남성"):
        return "male"
    if s in ("female", "woman", "f", "여자", "여성"):
        return "female"
    return "unknown"


def _js_divergence(p: dict[str, int], q: dict[str, int]) -> float:
    keys = sorted(set(p) | set(q))
    if not keys:
        return 0.0
    pa = np.asarray([p.get(k, 0) for k in keys], dtype=float)
    qa = np.asarray([q.get(k, 0) for k in keys], dtype=float)
    if pa.sum() == 0 or qa.sum() == 0:
        return 0.0
    pa /= pa.sum()
    qa /= qa.sum()
    m = 0.5 * (pa + qa)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / np.clip(b[mask], 1e-12, None))))

    return 0.5 * kl(pa, m) + 0.5 * kl(qa, m)


def _mean_pairwise_cosine(emb: np.ndarray) -> float:
    if emb.shape[0] <= 1:
        return 1.0
    norms = np.clip(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12, None)
    norm = emb / norms
    s = norm.sum(axis=0)
    num = float(np.dot(s, s) - emb.shape[0])
    den = float(emb.shape[0] * (emb.shape[0] - 1))
    return num / den if den else 1.0


# ---------------------------------------------------------------------------
# Persona aggregation
# ---------------------------------------------------------------------------


def _aggregate_from_speakers(speakers: list[dict[str, Any]]) -> dict[str, str]:
    def first_known(values: list[str]) -> str:
        known = [v for v in values if v and v not in ("unknown", "")]
        if not known:
            return "unknown"
        return known[0] if len(set(known)) == 1 else "mixed"

    return {
        "sex": _normalize_sex(first_known([str(s.get("gender_hint") or "") for s in speakers])),
        "age": _age_bucket(first_known([str(s.get("age_group_hint") or "") for s in speakers])),
        "occupation": first_known([str(s.get("occupation_hint") or "") for s in speakers]),
        "education_level": "unknown",
        "marital_status": "unknown",
        "family_type": "unknown",
        "housing_type": "unknown",
        "military_status": "unknown",
    }


def _aggregate_from_personas(personas: list[dict[str, Any]]) -> dict[str, str]:
    """Aggregate persona attributes from a list of persona dicts.

    Handles both v3 Persona shape (gender/education/housing keys) and
    v4 RetrievedPersona shape (sex/age/occupation — no demographic details).
    """
    def first_known(values: list[str]) -> str:
        known = [v for v in values if v and v not in ("unknown", "")]
        if not known:
            return "unknown"
        return known[0] if len(set(known)) == 1 else "mixed"

    # v4 retrieved_persona rows: extract nested dict if present
    flat: list[dict[str, Any]] = []
    for p in personas:
        rp = p.get("retrieved_persona")
        flat.append(rp if isinstance(rp, dict) else p)

    # v3 compat: gender→sex, education→education_level, housing→housing_type
    def get_attr(p: dict[str, Any], attr: str) -> str:
        v3_map = {"sex": "gender", "education_level": "education", "housing_type": "housing"}
        val = p.get(attr) or p.get(v3_map.get(attr, ""), "")
        return str(val).strip()

    result: dict[str, str] = {}
    for attr in PERSONA_ATTRIBUTES:
        values = [get_attr(p, attr) for p in flat]
        v = first_known(values)
        if attr == "sex":
            v = _normalize_sex(v)
        elif attr == "age":
            v = _age_bucket(v)
        result[attr] = v
    return result


# ---------------------------------------------------------------------------
# Stage normalizers
# ---------------------------------------------------------------------------


def _normalize_raw(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for idx, row in enumerate(rows):
        turns = row.get("dialogue") or []
        speakers = row.get("speakers") or []
        dialogue_text = "\n".join(f"{s}: {t}" for s, t in zip(speakers, turns, strict=False))
        doc = "\n".join([
            f"narrative {row.get('narrative', '')}",
            f"speaker_count {len(set(map(str, speakers)))}",
            f"turn_count {len(turns)}",
            dialogue_text,
        ])
        out.append({
            "id": str(row.get("id") or f"raw-{row.get('original_index', idx)}"),
            "stage": "Input",
            "doc": doc,
            "details": {a: "unknown" for a in PERSONA_ATTRIBUTES},
        })
    return out


def _stage1_doc(row: dict[str, Any]) -> str:
    speakers = row.get("speakers") or []
    scene = row.get("scene") or {}
    decomposed = row.get("dialogue_decomposed") or {}
    refs = decomposed.get("cultural_refs") or []
    ref_terms = " ".join(f"{r.get('type','')}:{r.get('term','')}" for r in refs)
    topics = " ".join(map(str, scene.get("topics") or []))
    source_text = " ".join(t.get("text", "") for t in (row.get("source_dialogue") or []))
    speaker_blobs = []
    for s in speakers:
        emotion = s.get("dominant_emotion") or {}
        speaker_blobs.append(" ".join([
            str(s.get("name_en", "")),
            str(s.get("role_in_scene", "")),
            str(s.get("gender_hint", "")),
            str(s.get("age_group_hint", "")),
            str(s.get("register", "")),
            str(emotion.get("type", "")),
            str(s.get("occupation_hint", "")),
            " ".join(map(str, s.get("personality_traits") or [])),
            " ".join(map(str, s.get("interests_hints") or [])),
        ]))
    return "\n".join([
        f"narrative {scene.get('narrative_en', '')}",
        f"setting {scene.get('setting', '')}",
        f"relationship {scene.get('relationship_type', '')}",
        f"topics {topics}",
        f"register {decomposed.get('overall_register', '')}",
        f"emotion {(decomposed.get('overall_emotion') or {}).get('type', '')}",
        f"speech_acts {' '.join(map(str, decomposed.get('speech_acts') or []))}",
        f"cultural_refs {ref_terms}",
        f"speakers {' || '.join(speaker_blobs)}",
        f"dialogue {source_text}",
    ])


def _normalize_stage1(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        speakers = row.get("speakers") or []
        scene = row.get("scene") or {}
        decomposed = row.get("dialogue_decomposed") or {}
        refs = decomposed.get("cultural_refs") or []
        persona = _aggregate_from_speakers(speakers)
        out.append({
            "id": str(row.get("id", "")),
            "stage": "Stage1",
            "doc": _stage1_doc(row),
            "details": {
                "setting": scene.get("setting"),
                "relationship_type": scene.get("relationship_type"),
                "register": decomposed.get("overall_register"),
                "cultural_ref_count": len(refs),
                **persona,
            },
        })
    return out


def _normalize_stage2(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        mapped_refs = row.get("mapped_refs") or []
        mapped_blob = " ".join(f"{r.get('term','')} {r.get('ko','')} {r.get('type','')}" for r in mapped_refs)
        ko_text = " ".join(t.get("text", "") for t in (row.get("korean_dialogue") or []))

        # v4: persona[*].retrieved_persona; v3 fallback: speaker_personas
        v4_personas = row.get("persona") or []
        v3_personas = row.get("speaker_personas") or []
        personas = v4_personas if v4_personas else v3_personas

        def _persona_blob(p: dict[str, Any]) -> str:
            rp = p.get("retrieved_persona") or p
            return " ".join([
                str(rp.get("sex", rp.get("gender", ""))),
                str(rp.get("age", "")),
                str(rp.get("occupation", "")),
                str(rp.get("family_type", "")),
            ])

        persona_blob = " ".join(_persona_blob(p) for p in personas)
        doc = "\n".join([
            _stage1_doc(row),
            f"mapped_refs {mapped_blob}",
            f"korean_dialogue {ko_text}",
            f"personas {persona_blob}",
        ])
        persona = _aggregate_from_personas(personas) if personas else _aggregate_from_speakers(row.get("speakers") or [])
        out.append({
            "id": str(row.get("id", "")),
            "stage": "Stage2",
            "doc": doc,
            "details": {
                "mapped_ref_count": len(mapped_refs),
                **persona,
            },
        })
    return out


def _normalize_stage3(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        quality = row.get("quality") or {}
        quality_blob = " ".join(f"{k} {v}" for k, v in quality.items() if isinstance(v, (int, float)))
        doc = "\n".join([
            _stage1_doc(row),
            f"valid {row.get('valid', True)}",
            f"quality {quality_blob}",
        ])
        personas = row.get("speaker_personas") or []
        persona = _aggregate_from_personas(personas) if personas else _aggregate_from_speakers(row.get("speakers") or [])
        out.append({
            "id": str(row.get("id", "")),
            "stage": "Stage3",
            "doc": doc,
            "details": {
                "valid": row.get("valid"),
                "aggregate_quality": quality.get("aggregate"),
                "iter": row.get("iter", 0),
                **persona,
            },
        })
    return out


def _normalize_target(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for idx, row in enumerate(rows):
        details: dict[str, Any] = {}
        for a in PERSONA_ATTRIBUTES:
            v = row.get(a)
            if a == "age":
                details[a] = _age_bucket(v)
            elif a == "sex":
                details[a] = _normalize_sex(v)
            else:
                details[a] = v
        doc = " ".join(f"{a} {details[a]}" for a in PERSONA_ATTRIBUTES)
        out.append({
            "id": str(idx),
            "stage": "Korea Target",
            "doc": doc,
            "details": details,
        })
    return out


def _load_hf_target(limit: int = 5000) -> list[dict[str, Any]]:
    from datasets import load_dataset  # type: ignore[import]

    ds = load_dataset(_HF_TARGET_DATASET, split="train", streaming=True)
    rows: list[dict[str, Any]] = []
    for row in ds:
        rows.append({a: row.get(a) for a in PERSONA_ATTRIBUTES})
        if len(rows) >= limit:
            break
    return rows


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _centroid_metrics(frame: pd.DataFrame, embedding_cols: list[str]) -> dict[str, Any]:
    target = frame[frame["stage"] == "Korea Target"]
    target_center = target[embedding_cols].mean().to_numpy()
    metrics: dict[str, Any] = {}
    for stage in frame["stage"].unique():
        subset = frame[frame["stage"] == stage]
        center = subset[embedding_cols].mean().to_numpy()
        metrics[stage] = {
            "count": int(len(subset)),
            "distance_to_target": float(np.linalg.norm(center - target_center)),
            "centroid": [float(x) for x in center],
        }
    return metrics


def _enrich_metrics(metrics: dict[str, Any], reduced: np.ndarray, frame: pd.DataFrame) -> dict[str, Any]:
    detail_frame = pd.DataFrame(frame["details"].tolist())
    detail_frame["stage"] = frame["stage"].values
    target_detail = detail_frame[detail_frame["stage"] == "Korea Target"]

    for stage in list(frame["stage"].unique()):
        stage_mask = frame["stage"] == stage
        metrics[stage]["within_cosine_similarity"] = float(_mean_pairwise_cosine(reduced[stage_mask.to_numpy()]))
        stage_detail = detail_frame[detail_frame["stage"] == stage]
        per_attr: dict[str, float] = {}
        for attr in PERSONA_ATTRIBUTES:
            tgt = (
                target_detail[attr].map(_value_bucket).value_counts().to_dict()
                if attr in target_detail else {}
            )
            src = (
                stage_detail[attr].map(_value_bucket).value_counts().to_dict()
                if attr in stage_detail else {}
            )
            per_attr[attr] = float(_js_divergence(src, tgt))
        metrics[stage]["js_divergence_to_target"] = float(np.mean(list(per_attr.values()))) if per_attr else 0.0
        metrics[stage]["js_divergence_by_attribute"] = per_attr
    return metrics


# ---------------------------------------------------------------------------
# HTML rendering (canvas-based scatter + centroid path)
# ---------------------------------------------------------------------------


def _build_html(payload: dict[str, Any], output_path: Path) -> None:
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Distribution Shift — nemos_dream</title>
  <style>
    body {{ margin: 0; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans KR",sans-serif;
      color: #1a1a2e; background: linear-gradient(180deg, #f8f9fa 0%, #f1f5f9 100%); min-height:100vh; }}
    main {{ max-width: 1480px; margin: 0 auto; padding: 16px; }}
    .title-row {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 6px; }}
    h1 {{ margin: 0; font-size: 22px; color: #1a1a2e; }}
    .panel {{ background: rgba(255,255,255,.95); border: 1px solid #dde3ed; border-radius: 18px;
      padding: 12px; box-shadow: 0 4px 16px rgba(16,24,40,.07); }}
    .toolbar, .stage-tabs, .attr-tabs {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }}
    button {{ min-height: 30px; border-radius: 999px; border: 1px solid #dde3ed; background: #f1f5f9;
      padding: 0 10px; font-weight: 700; cursor: pointer; color: #475467; font-size: 12px; }}
    button:hover {{ border-color: #76b900; color: #76b900; }}
    button.active {{ color: #fff; border-color: transparent; }}
    .attr-tabs button.active {{ background: #76b900; }}
    #pcaBtn.active, #tsneBtn.active {{ background: #76b900; }}
    .summary {{ margin-bottom: 8px; font-size: 12px; color: #64748b; line-height: 1.6; }}
    .summary strong {{ color: #1a1a2e; }}
    canvas {{ width: 100%; display: block; border: 1px solid #dde3ed; border-radius: 14px;
      background: linear-gradient(180deg, #fff 0%, #f8fbff 100%); }}
    .legend {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
    .legend-item {{ display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: #64748b; }}
    .legend-swatch {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; }}
    .detail {{ margin-top: 8px; min-height: 84px; border: 1px solid #dde3ed; border-radius: 10px;
      padding: 10px; background: #f8fafc; white-space: pre-wrap; font-size: 12px; color: #475467; }}
  </style>
</head>
<body>
<main>
  <section class="panel">
    <div class="title-row">
      <h1>Stage Distribution Shift</h1>
      <div class="toolbar">
        <button id="pcaBtn" class="active">PCA</button>
        <button id="tsneBtn">t-SNE</button>
      </div>
    </div>
    <div class="attr-tabs" id="attrTabs"></div>
    <div class="stage-tabs" id="stageTabs"></div>
    <div class="summary" id="summary"></div>
    <div class="legend" id="legend"></div>
    <canvas id="chart" width="1280" height="680"></canvas>
    <div class="detail" id="detail">Hover a point. Centroid path shows how each stage moves toward the Korea target.</div>
  </section>
</main>
<script>
const payload = {json.dumps(payload, ensure_ascii=False)};
const canvas = document.getElementById("chart");
const ctx = canvas.getContext("2d");
const stageOrder = payload.stageOrder;
const personaAttributes = payload.personaAttributes;
const stageColors = {{
  "Input": "#98A2B3", "Stage1": "#155EEF", "Stage2": "#0E7090",
  "Stage3": "#12B76A", "Korea Target": "#C11574"
}};
const stageBtnColors = stageColors;
const palette = ["#155EEF","#0E7090","#12B76A","#C11574","#F79009","#7A5AF8","#B42318","#344054","#026AA2","#4E5BA6"];
let mode = "pca", mouse = null, hovered = null;
const PINNED = new Set(["Input", "Korea Target"]);
const toggleableStages = stageOrder.filter(n => !PINNED.has(n));
let selectedStages = new Set();
let colorBy = personaAttributes[0] || "gender";

function isVisible(name) {{
  return PINNED.has(name) || selectedStages.has(name);
}}
function setMode(m) {{
  mode = m;
  document.getElementById("pcaBtn").classList.toggle("active", m === "pca");
  document.getElementById("tsneBtn").classList.toggle("active", m === "tsne");
  render();
}}
function toggleStage(name) {{
  if (PINNED.has(name)) return;
  if (selectedStages.has(name)) {{
    selectedStages.clear();
  }} else {{
    selectedStages.clear();
    selectedStages.add(name);
  }}
  renderStageTabs(); renderSummary(); render();
}}
function setColorBy(attr) {{
  colorBy = attr; renderAttrTabs(); renderLegend(activePoints()); render();
}}
function renderAttrTabs() {{
  document.getElementById("attrTabs").innerHTML = personaAttributes.map(a =>
    `<button class="${{a === colorBy ? "active" : ""}}" data-attr="${{a}}">${{a}}</button>`
  ).join("");
  document.querySelectorAll("[data-attr]").forEach(n => {{
    n.addEventListener("click", () => setColorBy(n.getAttribute("data-attr")));
  }});
}}
function renderStageTabs() {{
  document.getElementById("stageTabs").innerHTML = stageOrder.map(name => {{
    const pinned = PINNED.has(name);
    const active = isVisible(name);
    const label = pinned ? `${{name}} 📌` : name;
    return `<button id="stg_${{name.replace(" ","_")}}" class="${{active ? "active" : ""}}" ${{pinned ? 'style="opacity:0.7;cursor:default"' : ""}}>${{label}}</button>`;
  }}).join("");
  stageOrder.forEach(name => {{
    const node = document.getElementById("stg_" + name.replace(" ","_"));
    if (!node) return;
    const active = isVisible(name);
    node.style.background = active ? stageColors[name] : "#f1f5f9";
    node.style.color = active ? "#fff" : "#475467";
    if (!PINNED.has(name)) node.addEventListener("click", () => toggleStage(name));
  }});
}}
function renderSummary() {{
  const m = payload.metrics;
  const parts = stageOrder.filter(n => isVisible(n)).map(n => {{
    const s = m[n];
    if (!s) return "";
    return `<strong>${{n}}</strong> ${{s.count}} pts` +
      (s.distance_to_target != null ? `, dist ${{s.distance_to_target.toFixed(3)}}` : "") +
      (s.within_cosine_similarity != null ? `, cos ${{s.within_cosine_similarity.toFixed(3)}}` : "") +
      (s.js_divergence_to_target != null ? `, JS ${{s.js_divergence_to_target.toFixed(3)}}` : "");
  }});
  document.getElementById("summary").innerHTML = parts.join(" &nbsp;·&nbsp; ");
}}
function valFor(pt, attr) {{
  const v = (pt.details || {{}})[attr];
  return (v === null || v === undefined || v === "") ? "unknown" : v;
}}
function activePoints() {{
  return (payload[mode].points || []).filter(pt => isVisible(pt.stage));
}}
function attrValues(points) {{
  const counts = {{}};
  points.forEach(pt => {{ const v = String(valFor(pt, colorBy)); counts[v] = (counts[v]||0)+1; }});
  return Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([l])=>l);
}}
function colorMapFor(points) {{
  const UNKNOWN_COLOR = "#98A2B3";
  const labels = attrValues(points).filter(l => l !== "unknown");
  const top = labels.slice(0,9), map = {{}};
  top.forEach((l,i) => {{ map[l] = palette[i % palette.length]; }});
  labels.slice(9).forEach(l => {{ map[l] = UNKNOWN_COLOR; }});
  map["unknown"] = UNKNOWN_COLOR;
  return map;
}}
function renderLegend(points) {{
  const items = Object.entries(colorMapFor(points)).slice(0,10).map(([l,c]) =>
    `<span class="legend-item"><span class="legend-swatch" style="background:${{c}}"></span>${{l}}</span>`
  ).join("");
  document.getElementById("legend").innerHTML = items;
}}
// Compute global axis bounds from ALL points once so axes never shift on toggle
const _allPoints = (payload.pca.points || []);
const _allPcaXs = _allPoints.map(p=>p.coords[0]), _allPcaYs = _allPoints.map(p=>p.coords[1]);
const _allTsnePoints = (payload.tsne.points || []);
const _allTsneXs = _allTsnePoints.map(p=>p.coords[0]), _allTsneYs = _allTsnePoints.map(p=>p.coords[1]);
const _globalBounds = {{
  pca:  {{ minX:Math.min(..._allPcaXs),  maxX:Math.max(..._allPcaXs),  minY:Math.min(..._allPcaYs),  maxY:Math.max(..._allPcaYs)  }},
  tsne: {{ minX:Math.min(..._allTsneXs), maxX:Math.max(..._allTsneXs), minY:Math.min(..._allTsneYs), maxY:Math.max(..._allTsneYs) }},
}};
function project() {{
  const b = _globalBounds[mode];
  return {{
    sx: x => 70 + ((x-b.minX)/Math.max(b.maxX-b.minX,1e-6))*(canvas.width-140),
    sy: y => canvas.height-70-((y-b.minY)/Math.max(b.maxY-b.minY,1e-6))*(canvas.height-140),
  }};
}}
function smoothBlob(pts) {{
  if (pts.length < 6) return [];
  const cx = pts.reduce((a,p)=>a+p.x,0)/pts.length, cy = pts.reduce((a,p)=>a+p.y,0)/pts.length;
  const bins=24, radii=Array(bins).fill(0);
  pts.forEach(p => {{
    const angle = (Math.atan2(p.y-cy,p.x-cx)+Math.PI*2)%(Math.PI*2);
    const i = Math.floor(angle/(Math.PI*2)*bins)%bins;
    radii[i] = Math.max(radii[i], Math.hypot(p.x-cx,p.y-cy));
  }});
  const nz = radii.filter(r=>r>0), fallback = nz.length ? nz.reduce((a,r)=>a+r,0)/nz.length : 20;
  const rm = radii.map(r => (r||fallback*0.85)+18);
  const smooth = rm.map((_,i)=>Math.max(rm[i],(rm[(i-1+bins)%bins]+rm[i]*2+rm[(i+1)%bins]+rm[(i+2)%bins])/5));
  return smooth.map((r,i) => {{ const a=i/bins*Math.PI*2; return {{x:cx+Math.cos(a)*r, y:cy+Math.sin(a)*r}}; }});
}}
function drawBackdrops(points, T) {{
  const alpha = {{"Input":0.055,"Stage1":0.06,"Stage2":0.06,"Stage3":0.06,"Korea Target":0.045}};
  stageOrder.forEach(name => {{
    if (!isVisible(name)) return;
    const pts = points.filter(p=>p.stage===name).map(p=>{{return {{x:T.sx(p.coords[0]),y:T.sy(p.coords[1])}}}});
    const blob = smoothBlob(pts);
    if (blob.length < 3) return;
    ctx.beginPath();
    ctx.moveTo(blob[0].x, blob[0].y);
    for (let i=1;i<blob.length;i++) {{
      const prev=blob[i-1],curr=blob[i],mx=(prev.x+curr.x)/2,my=(prev.y+curr.y)/2;
      ctx.quadraticCurveTo(prev.x,prev.y,mx,my);
    }}
    const last=blob[blob.length-1],first=blob[0];
    ctx.quadraticCurveTo(last.x,last.y,(last.x+first.x)/2,(last.y+first.y)/2);
    ctx.quadraticCurveTo(first.x,first.y,first.x,first.y);
    ctx.closePath();
    ctx.fillStyle = stageColors[name];
    ctx.globalAlpha = alpha[name]||0.05;
    ctx.fill();
  }});
  ctx.globalAlpha = 1;
}}
function drawCentroidPath(T) {{
  const centroids = stageOrder.filter(n=>isVisible(n)).map(n => {{
    const c = (payload.metrics[n]||{{}}).centroid2d;
    if (!c) return null;
    return {{name:n, x:T.sx(c[mode][0]), y:T.sy(c[mode][1])}};
  }}).filter(Boolean);
  if (centroids.length < 2) return;
  ctx.strokeStyle="#98A2B3"; ctx.lineWidth=2; ctx.setLineDash([8,6]);
  ctx.beginPath();
  centroids.forEach((c,i)=>i===0?ctx.moveTo(c.x,c.y):ctx.lineTo(c.x,c.y));
  ctx.stroke(); ctx.setLineDash([]);
  centroids.forEach(c => {{
    if (c.name==="Korea Target") return;
    ctx.beginPath(); ctx.fillStyle=stageColors[c.name]; ctx.arc(c.x,c.y,8,0,Math.PI*2); ctx.fill();
  }});
}}
function drawLabels(T) {{
  const centroids = stageOrder.filter(n=>isVisible(n)).map(n => {{
    const c = (payload.metrics[n]||{{}}).centroid2d;
    if (!c) return null;
    return {{name:n, x:T.sx(c[mode][0]), y:T.sy(c[mode][1])}};
  }}).filter(Boolean);
  centroids.forEach(c => {{
    ctx.font="bold 12px sans-serif";
    ctx.lineWidth=3; ctx.strokeStyle="rgba(255,255,255,0.85)";
    ctx.strokeText(c.name, c.x+10, c.y-10);
    ctx.fillStyle=stageColors[c.name];
    ctx.fillText(c.name, c.x+10, c.y-10);
  }});
}}
function render() {{
  const points = activePoints();
  ctx.clearRect(0,0,canvas.width,canvas.height);
  renderLegend(points);
  if (!points.length) return;
  const cm = colorMapFor(points), T = project();
  hovered = null;
  drawBackdrops(points,T);
  drawCentroidPath(T);
  const sorted = [...points].sort((a,b) => {{
    const au = String(valFor(a,colorBy)) === "unknown" ? 0 : 1;
    const bu = String(valFor(b,colorBy)) === "unknown" ? 0 : 1;
    return au - bu;
  }});
  sorted.forEach(pt => {{
    const x=T.sx(pt.coords[0]), y=T.sy(pt.coords[1]);
    const isBackground = pt.stage==="Korea Target" || pt.stage==="Input";
    ctx.beginPath();
    ctx.fillStyle = cm[String(valFor(pt,colorBy))]||"#98A2B3";
    ctx.globalAlpha = isBackground ? 0.45 : 0.84;
    ctx.arc(x,y,isBackground?5:6,0,Math.PI*2); ctx.fill();
    ctx.globalAlpha = isBackground ? 0.25 : 0.12;
    ctx.strokeStyle=stageColors[pt.stage]; ctx.lineWidth=isBackground?1.2:0.8; ctx.stroke();
    ctx.globalAlpha=1;
    if (mouse && Math.hypot(mouse.x-x,mouse.y-y)<10) {{
      hovered = `${{pt.stage}}\\n${{colorBy}}: ${{valFor(pt,colorBy)}}\\n\\n${{JSON.stringify(pt.details,null,2)}}`;
    }}
  }});
  drawLabels(T);
  document.getElementById("detail").textContent = hovered || `Hover a point. Colour = ${{colorBy}}. Darker = pipeline data; lighter = Korea target.`;
}}
document.getElementById("pcaBtn").addEventListener("click", ()=>setMode("pca"));
document.getElementById("tsneBtn").addEventListener("click", ()=>setMode("tsne"));
canvas.addEventListener("mousemove", e => {{
  const r=canvas.getBoundingClientRect();
  mouse={{x:(e.clientX-r.left)*canvas.width/r.width, y:(e.clientY-r.top)*canvas.height/r.height}};
  render();
}});
canvas.addEventListener("mouseleave", ()=>{{ mouse=null; render(); }});
renderAttrTabs(); renderStageTabs(); renderSummary(); renderLegend(activePoints()); render();
</script>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_report(
    stage1_path: Path | None = None,
    stage2_path: Path | None = None,
    stage3_path: Path | None = None,
    raw_path: Path | None = None,
    target_path: Path | None = None,
    output_dir: Path = Path("data/reports"),
    target_limit: int = 5000,
    tsne_limit: int = 2000,
    use_hf_target: bool = True,
) -> Path:
    """Run TF-IDF + PCA/t-SNE on available stage files and write distribution_shift.html.

    At least one stage path must exist. When ``target_path`` is None and
    ``use_hf_target`` is True (default), loads the Korea persona target from
    ``nvidia/Nemotron-Personas-Korea`` on HuggingFace automatically.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    stage_order: list[str] = []

    def _maybe_load(path: Path | None, label: str, normalizer: Any) -> None:
        if path and Path(path).exists():
            stage_order.append(label)
            records.extend(normalizer(_read_jsonl(Path(path))))

    _maybe_load(raw_path, "Input", _normalize_raw)
    _maybe_load(stage1_path, "Stage1", _normalize_stage1)
    _maybe_load(stage2_path, "Stage2", _normalize_stage2)
    _maybe_load(stage3_path, "Stage3", _normalize_stage3)

    if target_path and Path(target_path).exists():
        stage_order.append("Korea Target")
        records.extend(_normalize_target(_read_jsonl(Path(target_path), target_limit)))
    elif use_hf_target:
        print(f"  loading Korea Target from {_HF_TARGET_DATASET} (limit={target_limit})…")
        try:
            target_rows = _load_hf_target(target_limit)
            stage_order.append("Korea Target")
            records.extend(_normalize_target(target_rows))
            print(f"  Korea Target: {len(target_rows)} rows loaded")
        except Exception as exc:
            print(f"  Korea Target skipped: {exc}")

    if not records:
        raise ValueError("No data found — provide at least one stage path.")

    frame = pd.DataFrame(records)
    matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=12000).fit_transform(frame["doc"].tolist())
    svd_dim = min(64, max(8, matrix.shape[0] - 1), max(8, matrix.shape[1] - 1))
    reduced = TruncatedSVD(n_components=svd_dim, random_state=42).fit_transform(matrix)

    pca_coords = PCA(n_components=2, random_state=42).fit_transform(reduced)
    frame["pca_x"], frame["pca_y"] = pca_coords[:, 0], pca_coords[:, 1]

    tsne_frame = frame.head(min(tsne_limit, len(frame))).copy()
    tsne_input = reduced[: len(tsne_frame)]
    n_tsne = len(tsne_frame)
    perplexity = min(30.0, max(2.0, (n_tsne - 1) / 3.0)) if n_tsne >= 5 else max(1.0, n_tsne / 2.0 - 0.5)
    tsne_coords = (
        TSNE(n_components=2, perplexity=perplexity, learning_rate="auto", init="pca", random_state=42, max_iter=1000).fit_transform(tsne_input)
        if n_tsne >= 3 else np.zeros((n_tsne, 2))
    )
    tsne_frame = tsne_frame.copy()
    tsne_frame["tsne_x"], tsne_frame["tsne_y"] = tsne_coords[:, 0], tsne_coords[:, 1]

    reduced_df = pd.DataFrame(reduced, columns=[f"f{i}" for i in range(reduced.shape[1])])
    reduced_df["stage"] = frame["stage"].values

    if "Korea Target" in stage_order:
        base_metrics = _centroid_metrics(reduced_df, [f"f{i}" for i in range(reduced.shape[1])])
        base_metrics = _enrich_metrics(base_metrics, reduced, frame)
    else:
        base_metrics = {
            s: {
                "count": int((frame["stage"] == s).sum()),
                "distance_to_target": None,
                "within_cosine_similarity": float(_mean_pairwise_cosine(reduced[frame["stage"].to_numpy() == s])),
                "js_divergence_to_target": None,
                "js_divergence_by_attribute": {},
            }
            for s in stage_order
        }

    for s in base_metrics:
        sub = frame[frame["stage"] == s]
        tsne_sub = tsne_frame[tsne_frame["stage"] == s]
        base_metrics[s]["centroid2d"] = {
            "pca": [float(sub["pca_x"].mean()), float(sub["pca_y"].mean())] if len(sub) else [0.0, 0.0],
            "tsne": [float(tsne_sub["tsne_x"].mean()), float(tsne_sub["tsne_y"].mean())] if len(tsne_sub) else [0.0, 0.0],
        }

    def _pts(df: pd.DataFrame, xc: str, yc: str) -> list[dict[str, Any]]:
        return [
            {
                "id": row["id"],
                "stage": row["stage"],
                "coords": [round(float(row[xc]), 6), round(float(row[yc]), 6)],
                "details": {k: _to_jsonable(v) for k, v in (row["details"] or {}).items()},
            }
            for _, row in df.iterrows()
        ]

    output_payload = {
        "stageOrder": stage_order,
        "personaAttributes": PERSONA_ATTRIBUTES,
        "metrics": base_metrics,
        "pca": {"points": _pts(frame, "pca_x", "pca_y")},
        "tsne": {"points": _pts(tsne_frame, "tsne_x", "tsne_y")},
    }

    html_path = output_dir / "distribution_shift.html"
    _build_html(output_payload, html_path)
    (output_dir / "distribution_shift_metrics.json").write_text(
        json.dumps(base_metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return html_path
