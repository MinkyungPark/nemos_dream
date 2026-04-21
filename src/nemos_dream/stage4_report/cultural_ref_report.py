"""Cultural reference bag-of-words report.

Three side-by-side word bags:
  1. Source English text  — top words in the raw dialogue
  2. Cultural terms (EN)  — mapped_refs[*].term  (extracted EN cultural refs)
  3. Korean mapping (KO)  — mapped_refs[*].ko    (culturally adapted equivalents)

Hover a word in any bag to highlight its counterpart(s) across bags.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

_STOPWORDS = {
    "i","you","he","she","it","we","they","a","an","the","and","or","but",
    "in","on","at","to","for","of","is","was","are","were","be","been",
    "have","has","had","do","did","not","that","this","with","my","your",
    "his","her","its","our","their","me","him","us","them","so","just",
    "like","get","got","what","how","about","up","out","if","no","yes",
    "yeah","oh","hi","hey","im","dont","cant","re","ve","ll","s","t","m",
    "know","really","think","well","feel","going","want","need","see",
    "here","there","when","then","than","even","still","would","could",
    "should","will","also","some","more","one","two","three","can","much",
    "something","anything","everything","nothing","people","time","way",
    "day","back","good","little","much","now","come","go","make","take",
    "look","right","mean","thing","things","been","being","having",
}

_TYPE_COLORS = {
    "brand":       "#155EEF",
    "service":     "#0E7090",
    "food":        "#12B76A",
    "holiday":     "#C11574",
    "event":       "#F79009",
    "pop_culture": "#7A5AF8",
    "place":       "#B42318",
    "slang":       "#026AA2",
    "person":      "#4E5BA6",
    "meme":        "#6941C6",
    "other":       "#667085",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def build_report(
    stage_path: Path,
    output_dir: Path = Path("data/reports"),
    label: str = "Stage1",
    top_source_words: int = 60,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_jsonl(Path(stage_path))

    # Bag 1 — source text words
    raw_words: list[str] = []
    for row in rows:
        for turn in (row.get("source_dialogue") or []):
            text = turn.get("text", "") if isinstance(turn, dict) else str(turn)
            for w in re.findall(r"[a-zA-Z']+", text.lower()):
                w = w.strip("'")
                if len(w) > 2 and w not in _STOPWORDS:
                    raw_words.append(w)
    source_counter = Counter(raw_words)
    bag1 = [
        {"word": w, "count": c, "type": "source", "color": "#94A3B8"}
        for w, c in source_counter.most_common(top_source_words)
    ]

    # Bag 2 + 3 — mapped refs
    term_type: dict[str, str] = {}
    term_ko: dict[str, str] = {}
    term_counter: Counter[str] = Counter()
    ko_counter: Counter[str] = Counter()
    ko_terms: dict[str, list[str]] = {}

    for row in rows:
        for r in (row.get("mapped_refs") or []):
            term = (r.get("term") or "").strip().lower()
            ko = (r.get("ko") or "").strip()
            rtype = r.get("type") or "other"
            if term:
                term_counter[term] += 1
                term_type[term] = rtype
                term_ko[term] = ko
            if ko:
                ko_counter[ko] += 1
                ko_terms.setdefault(ko, [])
                if term and term not in ko_terms[ko]:
                    ko_terms[ko].append(term)

    bag2 = [
        {
            "word": term,
            "count": cnt,
            "type": term_type[term],
            "color": _TYPE_COLORS.get(term_type[term], "#667085"),
            "ko": term_ko.get(term, ""),
        }
        for term, cnt in term_counter.most_common()
    ]

    bag3 = [
        {
            "word": ko,
            "count": cnt,
            "type": ko_terms.get(ko, []) and term_type.get(ko_terms[ko][0], "other") or "other",
            "color": _TYPE_COLORS.get(
                term_type.get((ko_terms.get(ko) or [""])[0], "other"), "#667085"
            ),
            "terms": ko_terms.get(ko, []),
        }
        for ko, cnt in ko_counter.most_common()
    ]
    # fix type on bag3
    for item in bag3:
        t = term_type.get((item["terms"] or [""])[0], "other")
        item["type"] = t
        item["color"] = _TYPE_COLORS.get(t, "#667085")

    payload = {
        "label": label,
        "bag1": bag1,
        "bag2": bag2,
        "bag3": bag3,
        "typeColors": _TYPE_COLORS,
        "stats": {
            "source_unique": len(source_counter),
            "source_total": sum(source_counter.values()),
            "term_unique": len(term_counter),
            "ko_unique": len(ko_counter),
            "covered_rows": sum(1 for row in rows if row.get("mapped_refs")),
            "total_rows": len(rows),
        },
    }

    out = output_dir / "cultural_ref_report.html"
    out.write_text(_build_html(payload), encoding="utf-8")
    return out


def _build_html(p: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>Cultural Ref Report — {p['label']}</title>
  <style>
    body {{
      margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans KR",sans-serif;
      color:#172033; background:linear-gradient(180deg,#f7f8fc 0%,#edf2f7 100%);
      min-height:100vh;
    }}
    main {{ max-width:1300px; margin:0 auto; padding:24px 20px; }}
    h1 {{ font-size:20px; font-weight:600; margin-bottom:4px; }}
    .subtitle {{ font-size:13px; color:#667085; margin-bottom:20px; }}
    /* stat strip */
    .stats {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:20px; }}
    .stat {{ background:rgba(255,255,255,.9); border:1px solid #d8dee9; border-radius:10px;
             padding:10px 16px; }}
    .stat .v {{ font-size:20px; font-weight:700; color:#172033; }}
    .stat .k {{ font-size:11px; color:#667085; margin-top:1px; }}
    /* three bags */
    .bags {{ display:grid; grid-template-columns:1fr auto 1fr auto 1fr; gap:0; align-items:start; }}
    @media(max-width:800px){{ .bags{{grid-template-columns:1fr; gap:16px;}} .arrow{{display:none;}} }}
    .bag {{ background:rgba(255,255,255,.93); border:1px solid #d8dee9; border-radius:16px;
            padding:18px 16px; box-shadow:0 4px 12px rgba(16,24,40,.06); }}
    .bag-header {{ margin-bottom:14px; }}
    .bag-title {{ font-size:13px; font-weight:700; color:#172033; margin-bottom:2px; }}
    .bag-desc {{ font-size:11px; color:#667085; }}
    .bag-count {{ display:inline-block; background:#f1f5f9; color:#475467;
                  border-radius:999px; padding:1px 8px; font-size:11px; font-weight:600; margin-left:6px; }}
    .words {{ display:flex; flex-wrap:wrap; gap:7px; }}
    .chip {{
      display:inline-flex; align-items:center;
      border-radius:999px; padding:4px 11px; cursor:default;
      border:1.5px solid transparent;
      transition:filter .12s, transform .12s, box-shadow .12s;
      white-space:nowrap; font-weight:600; user-select:none;
    }}
    .chip:hover {{ filter:brightness(1.12); transform:scale(1.05); box-shadow:0 2px 8px rgba(0,0,0,.12); }}
    .chip.dim {{ opacity:.22; }}
    .chip.highlighted {{ transform:scale(1.08); box-shadow:0 0 0 2.5px #172033; opacity:1 !important; }}
    /* arrow */
    .arrow {{ display:flex; align-items:center; justify-content:center;
              padding:0 8px; padding-top:56px; color:#94A3B8; font-size:22px; }}
    /* legend */
    .legend {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; }}
    .legend-item {{ display:inline-flex; align-items:center; gap:5px; font-size:11px; color:#475467; }}
    .legend-dot {{ width:9px; height:9px; border-radius:50%; flex-shrink:0; }}
    /* tooltip */
    .tooltip {{ position:fixed; background:#1e2433; color:#e6e8ee; border-radius:8px;
                padding:8px 12px; font-size:12px; pointer-events:none; display:none;
                z-index:100; line-height:1.6; max-width:220px; }}
  </style>
</head>
<body>
<main>
  <h1>Cultural Reference Bags — {p['label']}</h1>
  <div class="subtitle">원문 단어 → 추출된 영어 문화참조어 → 한국어 변환</div>

  <div class="stats" id="stats"></div>

  <div class="bags">
    <div class="bag" id="bag1">
      <div class="bag-header">
        <div class="bag-title">원문 영어 단어 <span class="bag-count" id="c1"></span></div>
        <div class="bag-desc">source_dialogue 상위 단어</div>
      </div>
      <div class="words" id="words1"></div>
    </div>
    <div class="arrow">→</div>
    <div class="bag" id="bag2">
      <div class="bag-header">
        <div class="bag-title">영어 문화참조어 <span class="bag-count" id="c2"></span></div>
        <div class="bag-desc">mapped_refs · term</div>
      </div>
      <div class="words" id="words2"></div>
    </div>
    <div class="arrow">→</div>
    <div class="bag" id="bag3">
      <div class="bag-header">
        <div class="bag-title">한국어 문화 변환 <span class="bag-count" id="c3"></span></div>
        <div class="bag-desc">mapped_refs · ko</div>
      </div>
      <div class="words" id="words3"></div>
    </div>
  </div>

  <div class="legend" id="legend"></div>
</main>
<div class="tooltip" id="tooltip"></div>

<script>
const p = {json.dumps(p, ensure_ascii=False)};
const tooltip = document.getElementById("tooltip");

// ── Stats ────────────────────────────────────────────────────────────────
const s = p.stats;
[
  [s.source_total, "원문 총 단어"],
  [s.source_unique, "원문 고유 단어"],
  [s.term_unique,   "추출된 문화참조어"],
  [s.ko_unique,     "한국어 변환어"],
  [`${{s.covered_rows}}/${{s.total_rows}}`, "참조어 있는 row"],
].forEach(([v,k]) => {{
  document.getElementById("stats").innerHTML +=
    `<div class="stat"><div class="v">${{v}}</div><div class="k">${{k}}</div></div>`;
}});

// ── Chip renderer ────────────────────────────────────────────────────────
function hexToRgb(hex) {{
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return [r,g,b];
}}
function chipStyle(color, count, maxCount) {{
  const scale = 0.7 + (count / maxCount) * 0.8;
  const fs = Math.round(11 * scale);
  const [r,g,b] = hexToRgb(color);
  const alpha = 0.1 + (count / maxCount) * 0.12;
  return `font-size:${{fs}}px;background:rgba(${{r}},${{g}},${{b}},${{alpha}});color:${{color}};border-color:rgba(${{r}},${{g}},${{b}},0.35);`;
}}

function renderBag(elId, countId, words, bagId, getKey) {{
  const el = document.getElementById(elId);
  const maxCount = Math.max(...words.map(w=>w.count), 1);
  document.getElementById(countId).textContent = words.length;
  el.innerHTML = words.map((w,i) =>
    `<span class="chip" data-bag="${{bagId}}" data-key="${{getKey(w)}}" data-idx="${{i}}"
      style="${{chipStyle(w.color, w.count, maxCount)}}"
      data-tip="${{w.word}}${{w.ko ? ' → '+w.ko : ''}}${{w.terms && w.terms.length ? ' ← '+w.terms.join(', ') : ''}} · ${{w.type||'source'}} · ×${{w.count}}"
    >${{w.word}}</span>`
  ).join("");
}}

const b1max = Math.max(...p.bag1.map(w=>w.count),1);
const b2max = Math.max(...p.bag2.map(w=>w.count),1);
const b3max = Math.max(...p.bag3.map(w=>w.count),1);

renderBag("words1","c1", p.bag1, 1, w => w.word);
renderBag("words2","c2", p.bag2, 2, w => w.word);
renderBag("words3","c3", p.bag3, 3, w => w.word);

// ── Hover cross-highlight ─────────────────────────────────────────────────
// Build lookup: term→ko, ko→[terms], source word → matching term
const termToKo = {{}};
const koToTerms = {{}};
p.bag2.forEach(w => {{ termToKo[w.word] = w.ko; }});
p.bag3.forEach(w => {{ koToTerms[w.word] = w.terms || []; }});

function allChips() {{ return document.querySelectorAll(".chip"); }}

function highlight(bag, key) {{
  // compute which words should be lit
  const lit1 = new Set(), lit2 = new Set(), lit3 = new Set();
  if (bag === 2) {{
    lit2.add(key);
    const ko = termToKo[key]; if (ko) lit3.add(ko);
    // highlight source words that contain this term
    p.bag1.forEach(w => {{ if (w.word === key || w.word.includes(key)) lit1.add(w.word); }});
  }} else if (bag === 3) {{
    lit3.add(key);
    const terms = koToTerms[key] || [];
    terms.forEach(t => {{ lit2.add(t); p.bag1.forEach(w=>{{ if(w.word===t||w.word.includes(t)) lit1.add(w.word); }}); }});
  }} else {{
    lit1.add(key);
    // find any term that matches this source word
    p.bag2.forEach(w => {{ if (w.word === key || key.includes(w.word) || w.word.includes(key)) {{
      lit2.add(w.word); const ko=termToKo[w.word]; if(ko) lit3.add(ko);
    }} }});
  }}
  const hasHighlight = lit1.size||lit2.size||lit3.size;
  allChips().forEach(chip => {{
    const b = parseInt(chip.dataset.bag), k = chip.dataset.key;
    const inLit = (b===1&&lit1.has(k))||(b===2&&lit2.has(k))||(b===3&&lit3.has(k));
    chip.classList.toggle("highlighted", inLit);
    chip.classList.toggle("dim", hasHighlight && !inLit);
  }});
}}

function clearHighlight() {{
  allChips().forEach(c => {{ c.classList.remove("highlighted","dim"); }});
}}

document.querySelectorAll(".chip").forEach(chip => {{
  chip.addEventListener("mouseenter", e => {{
    const bag = parseInt(e.target.dataset.bag), key = e.target.dataset.key;
    highlight(bag, key);
    tooltip.style.display = "block";
    tooltip.textContent = e.target.dataset.tip;
  }});
  chip.addEventListener("mousemove", e => {{
    tooltip.style.left = (e.clientX+14)+"px";
    tooltip.style.top  = (e.clientY-8)+"px";
  }});
  chip.addEventListener("mouseleave", () => {{
    clearHighlight();
    tooltip.style.display = "none";
  }});
}});

// ── Legend ────────────────────────────────────────────────────────────────
const usedTypes = [...new Set(p.bag2.map(w=>w.type).concat(p.bag3.map(w=>w.type)))];
document.getElementById("legend").innerHTML = usedTypes.map(t =>
  `<span class="legend-item"><span class="legend-dot" style="background:${{p.typeColors[t]||'#667085'}}"></span>${{t}}</span>`
).join("");
</script>
</body>
</html>"""
