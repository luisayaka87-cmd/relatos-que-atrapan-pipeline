#!/usr/bin/env python3
"""Armado de un capítulo: segmentos, karaoke ASS con headline, unión xfade y quemado.

Generalización del script usado en producción (Caps. 1 y 2 de Graciela).

Uso:
  python3 armado.py --work ./capitulo-N --config capitulo.json --timings timings.json --fuentes ./fonts

capitulo.json:
  {"guion": {"1": "texto exacto...", ..., "48": "..."},
   "headline_lineas": ["¡TÍTULO EN", "MAYÚSCULAS!"],
   "capitulo": 2, "total_capitulos": 4, "marca": "VERA MONTALVO"}

timings.json lo produce scripts/timings.py (manifest + tiempos por palabra).

Produce en --work: segmentos/, segmentos.json, karaoke.ass,
<capitulo>-unido.mp4 y <capitulo>-final.mp4 (720×1280).

Lecciones incorporadas (ver docs/formato.md):
- TODOS los colores van EN LÍNEA en cada evento y en cada palabra: la libass
  de producción ignora los colores de los Style y lo que no lleva color en
  línea sale NEGRO (incluida la primera palabra de cada evento de karaoke).
- Headline 0–5 s: ningún evento de karaoke termina antes de 5 s; el que cruza
  5 s se recorta para empezar en 5,0.
"""
import argparse, json, os, re, subprocess, sys, unicodedata
from difflib import SequenceMatcher

FADE = 0.3
VF = ("scale=720:1280:force_original_aspect_ratio=decrease,"
      "pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p,setsar=1")
AF = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FALLO:", " ".join(cmd[:6]), r.stderr[-500:], flush=True)
        sys.exit(1)


def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", s)


def ass_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--timings", required=True)
    ap.add_argument("--fuentes", required=True, help="directorio de fuentes (fontsdir de libass)")
    a = ap.parse_args()

    work = a.work
    seg_dir = os.path.join(work, "segmentos")
    os.makedirs(seg_dir, exist_ok=True)
    cfg = json.load(open(a.config))
    guion = {int(k): v for k, v in cfg["guion"].items()}
    n_lines = max(guion)
    data = json.load(open(a.timings))
    man, tim = data["manifest"], data["timings"]

    # ── Segmentos recortados a la voz real ──────────────────────────────
    seginfo = {}
    for n in range(1, n_lines + 1):
        words = tim[str(n)]["words"]
        first, last = words[0]["s"], words[-1]["e"]
        seg = os.path.join(seg_dir, f"seg-{n:02d}.mp4")
        info = man[str(n)]
        if info["respaldo"]:
            adur = dur(info["audio"])
            a0 = max(0.0, first - 0.1)
            a1 = min(adur, last + 0.1)
            sdur = a1 - a0
            run(["ffmpeg", "-y", "-v", "error", "-ss", "0.3", "-i", info["visual"],
                 "-i", info["audio"],
                 "-filter_complex",
                 f"[0:v]{VF},tpad=stop_mode=clone:stop_duration={sdur + 1:.2f},"
                 f"trim=duration={sdur:.3f},setpts=PTS-STARTPTS[v];"
                 f"[1:a]atrim=start={a0:.3f}:end={a1:.3f},asetpts=PTS-STARTPTS,{AF}[a]",
                 "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "18", "-c:a", "aac", "-b:a", "160k", seg])
            cut = a0
        else:
            src = info["clip"]
            d = dur(src)
            c0 = max(0.0, first - 0.1)
            c1 = min(d, last + 0.1)
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{c0:.3f}", "-to", f"{c1:.3f}",
                 "-i", src, "-vf", VF, "-af", AF, "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "18", "-c:a", "aac",
                 "-b:a", "160k", seg])
            cut = c0
        sd = dur(seg)
        seginfo[n] = {"seg": seg, "dur": sd, "cut": cut,
                      "words": [(w["w"], w["s"] - cut, w["e"] - cut) for w in words]}
        print(f"seg {n}: {sd:.2f}s (corte {cut:.2f})", flush=True)

    json.dump({str(k): {"seg": v["seg"], "dur": v["dur"], "cut": v["cut"],
                        "words": v["words"]} for k, v in seginfo.items()},
              open(os.path.join(work, "segmentos.json"), "w"),
              ensure_ascii=False, indent=1)

    offsets, acc = {}, 0.0
    for n in range(1, n_lines + 1):
        offsets[n] = acc
        acc += seginfo[n]["dur"] - FADE
    total = acc + FADE
    print(f"duración total estimada: {total:.2f}s", flush=True)

    # ── Alineación guion <-> tiempos por palabra ────────────────────────
    def align(n):
        sw = re.findall(r"[^\s]+", guion[n])
        sn = [norm(w)[0] if norm(w) else "" for w in sw]
        aw = seginfo[n]["words"]
        an = [norm(w)[0] if norm(w) else "" for w, _, _ in aw]
        sm = SequenceMatcher(None, sn, an, autojunk=False)
        times = [None] * len(sw)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    times[i1 + k] = (aw[j1 + k][1], aw[j1 + k][2])
            elif tag == "replace":
                cnt_s, cnt_a = i2 - i1, j2 - j1
                for k in range(cnt_s):
                    if cnt_a:
                        j = j1 + min(k, cnt_a - 1)
                        times[i1 + k] = (aw[j][1], aw[j][2])
        known = [i for i, t in enumerate(times) if t]
        for i in range(len(times)):
            if times[i] is None:
                prev = max([k for k in known if k < i], default=None)
                nxt = min([k for k in known if k > i], default=None)
                if prev is not None and nxt is not None:
                    span = times[nxt][0] - times[prev][1]
                    frac = (i - prev) / (nxt - prev)
                    t0 = times[prev][1] + span * frac
                    times[i] = (t0, t0 + 0.25)
                elif prev is not None:
                    times[i] = (times[prev][1], times[prev][1] + 0.25)
                elif nxt is not None:
                    times[i] = (max(0.0, times[nxt][0] - 0.25), times[nxt][0])
                else:
                    times[i] = (0.0, 0.25)
        return sw, times

    # ── Eventos de karaoke (colores EN LÍNEA en cada palabra) ───────────
    ev, nev = [], 0
    for n in range(1, n_lines + 1):
        sw, times = align(n)
        base = offsets[n]
        chunks = [list(range(i, min(i + 3, len(sw)))) for i in range(0, len(sw), 3)]
        for ci, chunk in enumerate(chunks):
            for pos, wi in enumerate(chunk):
                start = base + times[wi][0]
                if pos + 1 < len(chunk):
                    end = base + times[chunk[pos + 1]][0]
                elif ci + 1 < len(chunks):
                    end = base + times[chunks[ci + 1][0]][0]
                else:
                    end = base + times[wi][1] + 0.15
                parts = []
                for wj in chunk:
                    txt = sw[wj].upper()
                    if wj == wi:
                        parts.append("{\\fs70\\c&H00D7FF&}" + txt + "{\\fs53\\c&HFFFFFF&}")
                    else:
                        parts.append("{\\fs53\\c&HFFFFFF&}" + txt)
                ev.append((start, end, "Karaoke", " ".join(parts)))
                nev += 1
    # Headline 0–5 s: sin karaoke que termine antes de 5 s; el que cruce, recorta a 5,0
    ev = [(max(s, 5.0), e, st, tx) for s, e, st, tx in ev if e > 5.0]
    ev.sort()

    headline = "\\N".join(cfg["headline_lineas"])
    capitulo_txt = f"CAPÍTULO {cfg['capitulo']} DE {cfg['total_capitulos']}"
    lines = [
        "[Script Info]", "Title: karaoke", "ScriptType: v4.00+",
        "PlayResX: 720", "PlayResY: 1280", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColor, SecondaryColor, OutlineColor, BackColor, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Karaoke,Montserrat ExtraBold,53,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,20,20,380,1",
        "Style: Capitulo,Montserrat ExtraBold,45,&H0000D7FF,&H0000D7FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,0,8,20,20,54,1",
        "Style: Marca,Gelasio,31,&H80FFFFFF,&H80FFFFFF,&H00000000,&H00000000,0,-1,0,0,100,100,0,0,1,0,0,2,20,20,26,1",
        "Style: Headline,Montserrat ExtraBold,56,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,20,20,380,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 3,{ass_time(0)},{ass_time(5.0)},Headline,,0,0,0,,{{\\c&H00FFFF&}}{headline}",
        f"Dialogue: 1,{ass_time(0)},{ass_time(4.0)},Capitulo,,0,0,0,,{{\\c&H00D7FF&}}{capitulo_txt}",
        f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Marca,,0,0,0,,{{\\c&HFFFFFF&\\alpha&H80&}}{cfg['marca']}",
    ]
    for s, e, st, tx in ev:
        lines.append(f"Dialogue: 2,{ass_time(s)},{ass_time(e)},{st},,0,0,0,,{tx}")
    ass_path = os.path.join(work, "karaoke.ass")
    open(ass_path, "w").write("\n".join(lines))
    print(f"ASS: {len(ev)} eventos de karaoke (de {nev} antes del recorte headline)",
          flush=True)

    # ── Unión xfade/acrossfade ──────────────────────────────────────────
    inputs = []
    for n in range(1, n_lines + 1):
        inputs += ["-i", seginfo[n]["seg"]]
    fc = []
    vprev, aprev, cum = "0:v", "0:a", seginfo[1]["dur"]
    for n in range(2, n_lines + 1):
        off = cum - FADE
        vl, al = f"vx{n}", f"ax{n}"
        fc.append(f"[{vprev}][{n-1}:v]xfade=transition=fade:duration={FADE}:offset={off:.3f}[{vl}]")
        fc.append(f"[{aprev}][{n-1}:a]acrossfade=d={FADE}[{al}]")
        cum += seginfo[n]["dur"] - FADE
        vprev, aprev = vl, al
    joined = os.path.join(work, "capitulo-unido.mp4")
    run(["ffmpeg", "-y", "-v", "error"] + inputs +
        ["-filter_complex", ";".join(fc), "-map", f"[{vprev}]", "-map", f"[{aprev}]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac",
         "-b:a", "160k", joined])
    print(f"unido: {dur(joined):.2f}s", flush=True)

    # ── Quemado del ASS ─────────────────────────────────────────────────
    final = os.path.join(work, "capitulo-final.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-i", joined,
         "-vf", f"ass={ass_path}:fontsdir={a.fuentes}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "copy", final])
    print(f"FINAL: {final} {dur(final):.2f}s", flush=True)


if __name__ == "__main__":
    main()
