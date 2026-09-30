#!/usr/bin/env python3
"""Aristotle teach hub: data-driven lesson hub + server-side answer sync (tailnet-only).

Routes:
  GET  /                              home: pick a track
  GET  /t/<slug>                      track page: lesson path with done-status
  GET  /<slug>/lessons/<file>.html    serve a lesson WITH injected autosave (old + new lessons)
  GET  /<slug>/<sub>/<file>           serve other track files (reference/, assets/)
  GET  /api/tracks                    JSON: tracks + lessons + status (stable API for a future pretty UI)
  GET  /api/answers/<slug>/<lesson>   JSON: saved answers for a lesson
  POST /api/answers/<slug>/<lesson>   save answers (server-side sync; written to <track>/.answers/)

Pages are rendered server-side from the same data /api/tracks exposes, so the
frontend can be restyled without touching the data layer.

Bind it to your tailnet address only (HUB_HOST), never a public interface:
there is no auth, the tailnet ACL is the access control.
"""
import ipaddress
import json
import os
import socket
import sys
import re
import html
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

BASE = (Path.home() / "brain" / "teach").resolve()
HOST = os.environ.get("HUB_HOST", "localhost")
PORT = int(os.environ.get("HUB_PORT", "8688"))
MAX_BODY = 256 * 1024
SLUG_RE = re.compile(r"^[a-z0-9-]+$")
# One path segment. No leading dot: blocks "..", ".status.json", ".answers", .claude/.
FILE_RE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$")

# ---------- data helpers ----------

def _safe_track(slug: str):
    if not slug or not SLUG_RE.match(slug):
        return None
    d = (BASE / slug)
    if d.is_dir() and (d / "MISSION.md").exists():
        return d
    return None

def _nice(slug: str) -> str:
    return slug.replace("-", " ").title()

def _lesson_num(name: str) -> int:
    m = re.match(r"(\d+)", name)
    return int(m.group(1)) if m else 0

def _lesson_title(f: Path) -> str:
    try:
        t = re.search(r"<title>(.*?)</title>", f.read_text(errors="ignore"), re.S | re.I)
        if t:
            return html.unescape(re.sub(r"\s+", " ", t.group(1)).strip())
    except Exception:
        pass
    return f.stem

def _mission_why(d: Path) -> str:
    try:
        txt = (d / "MISSION.md").read_text(errors="ignore")
        m = re.search(r"##\s*Why\s*\n(.+?)(\n##|\Z)", txt, re.S | re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:260]
    except Exception:
        pass
    return ""

def _answers_path(slug: str, lesson: str) -> Path:
    return BASE / slug / ".answers" / (lesson + ".json")

def _read_answers(slug: str, lesson: str) -> dict:
    p = _answers_path(slug, lesson)
    try:
        d = json.loads(p.read_text()) if p.exists() else {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def _has_answers(slug: str, lesson: str) -> bool:
    return bool(_read_answers(slug, lesson))

def _track_list():
    out = []
    if not BASE.exists():
        return out
    for d in sorted(BASE.iterdir()):
        if not d.is_dir() or not (d / "MISSION.md").exists():
            continue
        lessons = []
        ldir = d / "lessons"
        if ldir.exists():
            for f in sorted(ldir.glob("*.html"), key=lambda x: _lesson_num(x.name)):
                lessons.append({
                    "n": _lesson_num(f.name),
                    "file": f.name,
                    "title": _lesson_title(f),
                    "done": _has_answers(d.name, f.name),
                    "url": f"/{d.name}/lessons/{f.name}",
                })
        out.append({
            "slug": d.name,
            "name": _nice(d.name),
            "why": _mission_why(d),
            "lessons": lessons,
            "count": len(lessons),
        })
    return out

# ---------- the autosave script injected into every served lesson ----------

AUTOSAVE = """
<script>
(function(){
  // Clipboard fallback: navigator.clipboard is blocked on plain-HTTP (non-secure) origins
  // like a bare tailnet IP, so the lessons' "Copy results" button would silently fail.
  (function(){
    function fb(text){return new Promise(function(res,rej){try{
      var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');
      ta.style.cssText='position:fixed;top:0;left:0;opacity:0';document.body.appendChild(ta);
      ta.focus();ta.select();try{ta.setSelectionRange(0,text.length);}catch(e){}
      var ok=document.execCommand('copy');document.body.removeChild(ta);
      ok?res():rej(new Error('copy failed'));}catch(e){rej(e);}});}
    if(!(navigator.clipboard&&navigator.clipboard.writeText&&window.isSecureContext)){
      try{Object.defineProperty(navigator,'clipboard',{value:{writeText:fb},configurable:true});}
      catch(e){try{navigator.clipboard={writeText:fb};}catch(e2){}}
    }
  })();
  var p=location.pathname.split('/').filter(Boolean);
  if(p.length<3) return;
  var slug=p[0], lesson=p[p.length-1];
  var api='/api/answers/'+encodeURIComponent(slug)+'/'+encodeURIComponent(lesson);
  var restoring=false, picked=[];
  function tas(){return [].slice.call(document.querySelectorAll('textarea'));}
  function ins(){return [].slice.call(document.querySelectorAll('input'));}
  function choices(){return [].slice.call(document.querySelectorAll('button.choice,.judge button,.choices button,.quiz button,.q button'))
      .filter(function(b){return !/reveal|copy|reset|next|prev|show|submit|skip|print/i.test(b.className||'');});}
  function collect(){
    return {
      textareas: tas().map(function(t){return t.value;}),
      inputs: ins().map(function(i){return {checked:i.checked,value:i.value};}),
      picked: picked.slice(),
      saved_at: new Date().toISOString()
    };
  }
  function restore(d){
    if(!d) return; restoring=true;
    if(d.textareas) tas().forEach(function(t,i){ if(d.textareas[i]!=null) t.value=d.textareas[i]; });
    if(d.inputs) ins().forEach(function(inp,i){ var s=d.inputs[i]; if(!s) return;
      if(inp.type==='checkbox'||inp.type==='radio'){ inp.checked=!!s.checked; if(s.checked){try{inp.dispatchEvent(new Event('change',{bubbles:true}));}catch(e){}} }
      else if(s.value!=null){ inp.value=s.value; } });
    if(d.picked){ picked=d.picked.slice(); var L=choices();
      d.picked.forEach(function(i){ var b=L[i]; if(b){ try{b.click();}catch(e){} } }); }
    setTimeout(function(){restoring=false;},300);
  }
  var timer=null;
  function save(){ if(restoring) return; clearTimeout(timer); timer=setTimeout(function(){
    try{ fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(collect())}); }catch(e){}
  },600); }
  function ready(fn){ if(document.readyState!=='loading') fn(); else document.addEventListener('DOMContentLoaded',fn); }
  ready(function(){
    document.addEventListener('input', save, true);
    document.addEventListener('change', save, true);
    document.addEventListener('click', function(e){
      var b=e.target && e.target.closest && e.target.closest('button');
      if(b && !restoring){ var L=choices(); var i=L.indexOf(b); if(i>=0 && picked.indexOf(i)<0) picked.push(i); }
      if(!restoring) setTimeout(save,60);
    }, true);
    var bar=document.createElement('div');
    bar.style.cssText='position:fixed;top:0;left:0;right:0;padding:6px 12px;font:13px system-ui,sans-serif;background:#1a1a1a;color:#fff;z-index:99999;opacity:.92';
    bar.innerHTML='<a href="/t/'+slug+'" style="color:#8fd0ff;text-decoration:none">← '+slug+' path</a> · <span style="color:#9f9">answers auto-save</span>';
    document.body.appendChild(bar); document.body.style.paddingTop='34px';
    try{ fetch(api).then(function(r){return r.ok?r.json():null;}).then(restore).catch(function(){}); }catch(e){}
  });
})();
</script>
"""

# ---------- page templates (Lyceum editorial design) ----------

HEAD_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
              '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')

PAGE_CSS = """
:root{
  --paper:#e7e0d1;
  --paper-2:#ece6d9;
  --card:#f5f1e7;
  --card-hi:#faf7ee;
  --ink:#1b1714;
  --ink-2:#5f584c;
  --ink-3:#938b7c;
  --line:rgba(27,23,20,.16);
  --line-soft:rgba(27,23,20,.09);
  --accent:#a23a28;
  --accent-deep:#86301f;
  --accent-soft:rgba(162,58,40,.10);
  --ease:cubic-bezier(.22,.61,.36,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
body{
  background:var(--paper);
  color:var(--ink);
  font-family:"Manrope",system-ui,sans-serif;
  min-height:100vh;
  overflow-x:hidden;
}
/* subtle paper grain */
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  opacity:.05;mix-blend-mode:multiply;
}
::selection{background:var(--accent);color:var(--card-hi)}

.mono{font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.2em;font-size:11px;font-weight:500;color:var(--ink-2)}
.serif{font-family:"Cormorant Garamond",serif}

.wrap{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:0 clamp(22px,5vw,72px)}

/* ---------- top bar ---------- */
.topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:clamp(20px,3.4vw,34px) 0;
}
.brand{display:flex;align-items:center;gap:11px;cursor:pointer;background:none;border:0;color:inherit;text-decoration:none}
.brand .lam{
  font-family:"Cormorant Garamond",serif;font-size:23px;font-weight:600;line-height:1;
  width:30px;height:30px;display:grid;place-items:center;border:1px solid var(--ink);border-radius:50%;
  transition:transform .5s var(--ease);
}
.brand:hover .lam{transform:rotate(-8deg)}
.brand .name{font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.28em;font-size:12px;font-weight:500}
.topbar .right{display:flex;gap:clamp(14px,2vw,26px)}
.topbar .right span{opacity:.62}

.back{
  display:inline-flex;align-items:center;gap:10px;background:none;border:0;cursor:pointer;color:var(--ink-2);text-decoration:none;
  font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.2em;font-size:11px;font-weight:500;
  transition:color .3s var(--ease),gap .3s var(--ease);
}
.back:hover{color:var(--ink);gap:14px}
.back .arr{transition:transform .35s var(--ease)}
.back:hover .arr{transform:translateX(-3px)}

/* ---------- screens ---------- */
.screen{display:block;animation:fade .6s var(--ease)}
@keyframes fade{from{transform:translateY(16px);opacity:.4}to{transform:none;opacity:1}}

/* ---------- HOME hero ---------- */
.hero{padding:clamp(34px,7vw,86px) 0 clamp(26px,4vw,46px)}
.hero .kicker{display:flex;align-items:center;gap:14px;margin-bottom:clamp(22px,3vw,34px)}
.hero .kicker .ln{height:1px;width:clamp(34px,7vw,80px);background:var(--accent)}
.hero h1{
  font-family:"Cormorant Garamond",serif;font-weight:500;
  font-size:clamp(58px,12.5vw,148px);line-height:.9;letter-spacing:-.02em;
  margin-bottom:clamp(20px,3vw,30px);
}
.hero h1 em{font-style:italic;color:var(--accent);font-weight:500}
.hero .lede{
  max-width:46ch;font-size:clamp(16px,2.1vw,20px);line-height:1.55;color:var(--ink-2);font-weight:400;
}

/* ---------- section label ---------- */
.seclabel{display:flex;align-items:baseline;justify-content:space-between;gap:20px;
  padding-top:clamp(30px,4vw,48px);border-top:1px solid var(--line);}

/* ---------- track rows (HOME) ---------- */
.tracks{margin-top:8px}
.track{
  width:100%;text-align:left;background:none;border:0;cursor:pointer;color:inherit;text-decoration:none;
  display:grid;grid-template-columns:1fr;gap:clamp(18px,3vw,40px);
  padding:clamp(34px,5vw,58px) 0;border-bottom:1px solid var(--line);
  position:relative;transition:padding-left .5s var(--ease);
}
.track::after{content:"";position:absolute;left:-100vw;right:-100vw;top:0;bottom:0;z-index:-1;
  background:var(--card);opacity:0;transition:opacity .45s var(--ease)}
.track:hover{padding-left:clamp(14px,2.4vw,30px)}
.track:hover::after{opacity:.55}
.track .idx{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--accent);letter-spacing:.1em}
.track .head{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap}
.track h2{font-family:"Cormorant Garamond",serif;font-weight:500;font-size:clamp(38px,7.4vw,82px);
  line-height:.96;letter-spacing:-.015em;transition:color .4s var(--ease)}
.track:hover h2{color:var(--accent-deep)}
.track .why{font-size:clamp(15px,2vw,18.5px);line-height:1.5;color:var(--ink-2);max-width:42ch;margin-top:14px}
.track .cont{display:inline-flex;align-items:center;gap:9px;margin-top:20px;
  font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.16em;font-size:11px;color:var(--ink);
  opacity:0;transform:translateY(4px);transition:opacity .4s var(--ease),transform .4s var(--ease)}
.track:hover .cont{opacity:1;transform:none}
.track .cont .arr{transition:transform .4s var(--ease)}
.track:hover .cont .arr{transform:translateX(5px)}

.meta{display:flex;flex-direction:column;gap:14px;align-items:flex-start}
.meta .count{display:flex;align-items:baseline;gap:8px}
.meta .count .big{font-family:"Cormorant Garamond",serif;font-size:clamp(40px,6vw,62px);line-height:.8;font-weight:500}
.meta .count .sl{font-family:"IBM Plex Mono",monospace;font-size:15px;color:var(--ink-3)}
.meta .clabel{font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.16em;font-size:10.5px;color:var(--ink-2)}

/* segmented progress */
.ticks{display:flex;gap:6px;align-items:flex-end;height:24px}
.ticks .t{width:5px;height:14px;background:var(--line);border-radius:1px;transition:height .45s var(--ease),background .45s var(--ease)}
.ticks .t.done{background:var(--ink);height:18px}
.ticks .t.now{background:var(--accent);height:24px;animation:breathe 2.6s var(--ease) infinite}
@keyframes breathe{0%,100%{opacity:1}50%{opacity:.55}}

@media(min-width:760px){
  .track{grid-template-columns:1fr auto;align-items:center}
  .meta{align-items:flex-end;text-align:right}
  .track .why{margin-top:16px}
}

/* ---------- TRACK screen ---------- */
.thead{padding:clamp(26px,5vw,60px) 0 clamp(26px,4vw,44px)}
.thead .idx{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--accent);letter-spacing:.12em;margin-bottom:18px}
.thead h1{font-family:"Cormorant Garamond",serif;font-weight:500;font-size:clamp(46px,10vw,118px);
  line-height:.92;letter-spacing:-.02em;margin-bottom:22px}
.thead .why{line-height:1.5;color:var(--ink-2);max-width:40ch;font-style:italic;font-family:"Cormorant Garamond",serif;font-size:clamp(20px,2.6vw,27px)}
.tprogress{display:flex;align-items:center;gap:clamp(18px,3vw,30px);flex-wrap:wrap;margin-top:clamp(26px,4vw,40px);
  padding-top:clamp(22px,3vw,30px);border-top:1px solid var(--line)}
.tprogress .frac{display:flex;align-items:baseline;gap:6px}
.tprogress .frac .big{font-family:"Cormorant Garamond",serif;font-size:clamp(36px,5vw,52px);line-height:.8;font-weight:500}
.tprogress .frac .sl{font-family:"IBM Plex Mono",monospace;font-size:15px;color:var(--ink-3)}
.tprogress .note{font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:var(--ink-2)}
.tprogress .note b{color:var(--accent);font-weight:500}

/* lesson path */
.path{position:relative;padding:clamp(20px,3vw,30px) 0 80px}
.lesson{
  width:100%;text-align:left;background:none;border:0;cursor:pointer;color:inherit;text-decoration:none;
  display:grid;grid-template-columns:54px 1fr auto;align-items:center;gap:clamp(14px,3vw,30px);
  padding:clamp(22px,3.2vw,30px) clamp(14px,2.4vw,26px) clamp(22px,3.2vw,30px) 0;
  position:relative;border-radius:3px;transition:background .4s var(--ease),transform .4s var(--ease);
}
.lesson::before{content:"";position:absolute;left:26px;top:50%;bottom:-50%;width:1px;background:var(--line);z-index:0}
.lesson:last-child::before{display:none}
.lesson.done::before{background:var(--ink-2);opacity:.45}
/* node */
.node{grid-column:1;justify-self:center;width:14px;height:14px;border-radius:50%;border:1.5px solid var(--line);
  background:var(--paper);position:relative;z-index:2;display:grid;place-items:center;transition:all .4s var(--ease)}
.lesson.done .node{background:var(--ink);border-color:var(--ink)}
.lesson.done .node svg{width:8px;height:8px;stroke:var(--card-hi);stroke-width:2.4;fill:none}
.lesson.now .node{border-color:var(--accent);background:var(--accent);box-shadow:0 0 0 5px var(--accent-soft);animation:pulse 2.8s var(--ease) infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 5px var(--accent-soft)}50%{box-shadow:0 0 0 9px rgba(162,58,40,.04)}}
.lbody{grid-column:2;min-width:0}
.lbody .ln{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.18em;color:var(--ink-3);margin-bottom:6px;text-transform:uppercase}
.lbody h3{font-family:"Cormorant Garamond",serif;font-weight:500;font-size:clamp(25px,4.4vw,42px);line-height:1.02;
  letter-spacing:-.01em;transition:color .35s var(--ease)}
.lesson.done .lbody h3{color:var(--ink-2)}
.lesson.up .lbody h3{color:var(--ink-3)}
.lesson.now .lbody h3{color:var(--accent-deep)}
.lstate{grid-column:3;display:flex;align-items:center;gap:14px;justify-self:end}
.lstate .tag{font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.16em;font-size:10px;color:var(--ink-3)}
.lesson.now .lstate .tag{display:none}
.go{display:inline-flex;align-items:center;gap:9px;font-family:"IBM Plex Mono",monospace;text-transform:uppercase;
  letter-spacing:.14em;font-size:11px;color:var(--card-hi);background:var(--accent);padding:11px 17px;border-radius:2px;
  white-space:nowrap;transition:background .35s var(--ease),gap .35s var(--ease)}
.go .arr{transition:transform .35s var(--ease)}
.lesson .openarr{opacity:0;transform:translateX(-4px);color:var(--ink-3);transition:opacity .35s var(--ease),transform .35s var(--ease)}
.lesson:not(.now):hover{background:var(--card)}
.lesson:not(.now):hover .lbody h3{color:var(--ink)}
.lesson:not(.now):hover .openarr{opacity:1;transform:none}
.lesson.now:hover .go{background:var(--accent-deep);gap:13px}
.lesson.now:hover .go .arr{transform:translateX(4px)}
/* current lesson elevated card */
.lesson.now{background:var(--card-hi);box-shadow:0 1px 0 var(--line-soft),0 26px 50px -34px rgba(27,23,20,.5);
  padding-left:clamp(14px,2.4vw,26px);margin:8px 0}
.lesson.now::after{content:"";position:absolute;left:0;top:14px;bottom:14px;width:2px;background:var(--accent);border-radius:2px}

@media(max-width:560px){
  .lstate .tag{display:none}
  .lesson{grid-template-columns:40px 1fr auto;gap:14px}
  .lesson::before{left:19px}
  .node{width:12px;height:12px}
  .lesson.now::after{display:none}
  .go{padding:10px 13px}
}

/* footer */
.foot{display:flex;justify-content:space-between;flex-wrap:wrap;gap:14px;
  padding:clamp(30px,4vw,46px) 0;border-top:1px solid var(--line)}
.foot span{opacity:.6}
"""

def _pad2(n) -> str:
    try:
        return f"{int(n):02d}"
    except Exception:
        return str(n)

def _home_html():
    tracks = _track_list()
    if tracks:
        rows = ""
        for i, t in enumerate(tracks):
            total = t["count"]
            done = sum(1 for l in t["lessons"] if l["done"])
            nxt = next((l for l in t["lessons"] if not l["done"]), None)
            ticks = ""
            for l in t["lessons"]:
                cls = "t done" if l["done"] else ("t now" if (nxt is not None and l is nxt) else "t")
                ticks += f'<span class="{cls}"></span>'
            if total == 0:
                clabel = "No lessons yet"
            elif nxt is not None:
                clabel = f"Lesson {nxt['n']} next"
            else:
                clabel = "Track complete"
            rows += (
                f'<a class="track" href="/t/{html.escape(t["slug"])}">'
                f'<div class="main">'
                f'<div class="head"><span class="idx">{_pad2(i + 1)}</span><h2>{html.escape(t["name"])}</h2></div>'
                + (f'<p class="why">{html.escape(t["why"])}</p>' if t["why"] else "")
                + '<span class="cont mono">Continue track <span class="arr">&rarr;</span></span>'
                '</div>'
                '<div class="meta">'
                f'<div class="count"><span class="big">{_pad2(done)}</span><span class="sl">/ {_pad2(total)}</span></div>'
                f'<div class="ticks">{ticks}</div>'
                f'<span class="clabel">{html.escape(clabel)}</span>'
                '</div></a>'
            )
    else:
        rows = '<p class="why" style="padding:48px 0">No tracks yet. Create one with Aristotle in Telegram.</p>'
    return f"""<!doctype html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Lyceum: Choose your track</title>{HEAD_FONTS}<style>{PAGE_CSS}</style></head>
<body><div class="wrap">
<header class="topbar">
<a class="brand" href="/" aria-label="The Lyceum home"><span class="lam">&Lambda;</span><span class="name">The&nbsp;Lyceum</span></a>
<div class="right mono"><span>&Lambda;&Upsilon;&Kappa;&Epsilon;&Iota;&Omicron;&Nu;</span></div>
</header>
<main class="screen">
<section class="hero">
<div class="kicker"><span class="ln"></span><span class="mono">A personal tutor, guided by Aristotle</span></div>
<h1>Choose<br>your <em>track.</em></h1>
<p class="lede">Your paths of study. Pick up exactly where you left off, or begin somewhere new. Aristotle keeps your place.</p>
</section>
<div class="seclabel"><span class="mono">The Tracks</span><span class="mono">{_pad2(len(tracks))} Active</span></div>
<section class="tracks">{rows}</section>
<footer class="foot">
<span class="mono">The Lyceum &middot; &Lambda;&Upsilon;&Kappa;&Epsilon;&Iota;&Omicron;&Nu;</span>
<span class="mono">Tutor in residence: Aristotle</span>
</footer>
</main></div></body></html>"""

def _track_html(slug: str):
    tracks = _track_list()
    t = next((x for x in tracks if x["slug"] == slug), None)
    if not t:
        return None
    i = next((k for k, x in enumerate(tracks) if x["slug"] == slug), 0)
    idx = _pad2(i + 1)
    total = t["count"]
    done = sum(1 for l in t["lessons"] if l["done"])
    nxt = next((l for l in t["lessons"] if not l["done"]), None)
    if t["lessons"]:
        path = ""
        for l in t["lessons"]:
            if l["done"]:
                state = "done"
            elif nxt is not None and l is nxt:
                state = "now"
            else:
                state = "up"
            node = ('<span class="node"><svg viewBox="0 0 10 10"><polyline points="1.5,5.4 4,7.8 8.5,2.6"/></svg></span>'
                    if state == "done" else '<span class="node"></span>')
            if state == "now":
                right = '<div class="lstate"><span class="go">Continue <span class="arr">&rarr;</span></span></div>'
            elif state == "done":
                right = '<div class="lstate"><span class="tag">Complete</span><span class="openarr">&rarr;</span></div>'
            else:
                right = '<div class="lstate"><span class="tag">Upcoming</span><span class="openarr">&rarr;</span></div>'
            path += (
                f'<a class="lesson {state}" href="{html.escape(l["url"])}">'
                + node
                + f'<div class="lbody"><div class="ln">Lesson {_pad2(l["n"])}</div><h3>{html.escape(l["title"])}</h3></div>'
                + right + '</a>'
            )
    else:
        path = '<p class="why">No lessons yet. Ask Aristotle for the first one in this track’s topic.</p>'
    if total == 0:
        note = "No lessons yet"
    elif nxt is not None:
        note = f"Lesson <b>{nxt['n']}</b> awaits &middot; {total - done} remaining"
    else:
        note = "Complete &middot; every lesson mastered"
    why_html = f'<p class="why">&ldquo;{html.escape(t["why"])}&rdquo;</p>' if t["why"] else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(t["name"])} · The Lyceum</title>{HEAD_FONTS}<style>{PAGE_CSS}</style></head>
<body><div class="wrap">
<header class="topbar">
<a class="brand" href="/" aria-label="The Lyceum home"><span class="lam">&Lambda;</span><span class="name">The&nbsp;Lyceum</span></a>
<div class="right mono"><span>{idx} / {_pad2(len(tracks))}</span></div>
</header>
<main class="screen">
<div class="topbar" style="padding-top:0">
<a class="back" href="/"><span class="arr">&larr;</span> All tracks</a>
<span class="mono">{html.escape(t["name"])}</span>
</div>
<section class="thead">
<div class="idx">Track {idx}</div>
<h1>{html.escape(t["name"])}</h1>
{why_html}
<div class="tprogress">
<div class="frac"><span class="big">{_pad2(done)}</span><span class="sl">/ {_pad2(total)}</span></div>
<span class="note">{note}</span>
</div>
</section>
<section class="path">{path}</section>
<footer class="foot">
<span class="mono">Lesson complete &rarr; the next unlocks</span>
<span class="mono">Guided by Aristotle</span>
</footer>
</main></div></body></html>"""

# ---------- HTTP handler ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "TeachHub/1.0"

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def _serve_file(self, track_dir: Path, rel: str, inject: bool):
        target = (track_dir / rel).resolve()
        if not target.is_relative_to(track_dir.resolve()) or not target.is_file():
            return self._send(404, "Not found", "text/plain")
        if inject and target.suffix.lower() == ".html":
            txt = target.read_text(errors="ignore")
            low = txt.lower()
            idx = low.rfind("</body>")
            txt = (txt[:idx] + AUTOSAVE + txt[idx:]) if idx != -1 else (txt + AUTOSAVE)
            return self._send(200, txt, "text/html; charset=utf-8")
        ctype = "text/html; charset=utf-8" if target.suffix.lower() == ".html" else "application/octet-stream"
        if target.suffix.lower() == ".css":
            ctype = "text/css"
        elif target.suffix.lower() == ".js":
            ctype = "application/javascript"
        self._send(200, target.read_bytes(), ctype)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        seg = [s for s in path.split("/") if s]

        if not seg:
            return self._send(200, _home_html())
        if seg[0] == "t" and len(seg) == 2:
            page = _track_html(seg[1])
            return self._send(200, page) if page else self._send(404, "No such track", "text/plain")
        if seg[0] == "api":
            if seg[1:] == ["tracks"]:
                return self._json(200, {"tracks": _track_list()})
            if len(seg) == 4 and seg[1] == "answers":
                if not _safe_track(seg[2]) or not FILE_RE.match(seg[3]):
                    return self._json(404, {"error": "not found"})
                return self._json(200, _read_answers(seg[2], seg[3]))
            return self._json(404, {"error": "unknown api"})
        # track file: /<slug>/<...>
        td = _safe_track(seg[0])
        if td and len(seg) >= 2:
            rel = "/".join(seg[1:])
            if not all(FILE_RE.match(s) for s in seg[1:]):
                return self._send(404, "Not found", "text/plain")
            inject = (len(seg) >= 3 and seg[1] == "lessons")
            return self._serve_file(td, rel, inject)
        return self._send(404, "Not found", "text/plain")

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        seg = [s for s in path.split("/") if s]
        if len(seg) == 4 and seg[0] == "api" and seg[1] == "answers":
            slug, lesson = seg[2], seg[3]
            td = _safe_track(slug)
            if not td or not FILE_RE.match(lesson) or not (td / "lessons" / lesson).is_file():
                return self._json(404, {"error": "not found"})
            try:
                n = int(self.headers.get("Content-Length", 0))
                if n <= 0 or n > MAX_BODY:
                    return self._json(413, {"error": "bad size"})
                data = json.loads(self.rfile.read(n).decode("utf-8"))
            except Exception:
                return self._json(400, {"error": "bad json"})
            p = _answers_path(slug, lesson)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2))
            return self._json(200, {"ok": True})
        return self._json(404, {"error": "unknown"})

    def log_message(self, *a):
        pass  # quiet

# ---------- startup guard: never listen on a public interface by accident ----------

_CGNAT = ipaddress.IPv4Network((0x64400000, 10))              # Tailscale IPv4 range (100.64/10)
_TS_V6 = ipaddress.IPv6Network((0xFD7A115CA1E0 << 80, 48))    # Tailscale IPv6 ULA (fd7a:115c:a1e0::/48)


def _check_host(host: str):
    """Resolve HUB_HOST and refuse anything but loopback or a tailnet address, unless
    HUB_ALLOW_PUBLIC=1. The hub has no auth: the tailnet ACL is the access control."""
    try:
        infos = socket.getaddrinfo(host, PORT, type=socket.SOCK_STREAM)
    except OSError as e:
        sys.exit(f"teach_hub: cannot resolve HUB_HOST={host!r}: {e}")
    fam, addr = infos[0][0], infos[0][4][0]
    if os.environ.get("HUB_ALLOW_PUBLIC") == "1":
        return fam
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip.is_unspecified:
            sys.exit(f"teach_hub: refusing HUB_HOST={host!r}: it listens on every interface. "
                     "Set HUB_HOST to your tailnet IP (or HUB_ALLOW_PUBLIC=1 to override).")
        ok = ip.is_loopback or (ip.version == 4 and ip in _CGNAT) or (ip.version == 6 and ip in _TS_V6)
        if not ok:
            sys.exit(f"teach_hub: refusing HUB_HOST={host!r} ({ip}): not loopback or a tailnet "
                     "address, and the hub has no auth. Use your tailnet IP "
                     "(or HUB_ALLOW_PUBLIC=1 to override).")
    return fam


if __name__ == "__main__":
    family = _check_host(HOST)
    ThreadingHTTPServer.address_family = family
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
