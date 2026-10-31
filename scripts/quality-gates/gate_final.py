#!/usr/bin/env python3
"""COMPUERTA FINAL: el video terminado no se entrega si falla esto.

Rechaza si:
1. El video final no mide 720×1280 exacto.
2. cropdetect encuentra barras negras en los puntos de muestreo
   (crop con desplazamiento superior y>4 o altura <1200: el patrón real del
   defecto fue crop=720:1180:0:66 en el arranque). Una zona oscura del
   encuadre puede dar p. ej. 720:1246:0:0 sin ser barras: por eso el patrón
   de rechazo es el de barras, y los fotogramas de control (docs/formato.md)
   confirman visualmente.
3. La transcripción total (Groq, whisper-large-v3) no trae TODAS las líneas
   del guion, completas y EN ORDEN (cada línea con similitud ≥ umbral en su
   ventana, avanzando sobre la transcripción).

La presencia del headline en los primeros 5 s se garantiza con
gate_karaoke.py sobre el ASS quemado (evento Headline 0–5 s con el título)
más los fotogramas de control a 1 s y 4,9 s.

Uso:
  python3 gate_final.py --video capitulo-final.mp4 --paquete paquete-capitulo.md
"""
import argparse, json, os, re, subprocess, sys, unicodedata
from difflib import SequenceMatcher


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return [w for w in re.split(r"[^a-z0-9]+", t) if w]


def probe_dims(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()
    w, h = out.split(",")
    return int(w), int(h)


def probe_dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())


def crop_at(path, t):
    r = subprocess.run(
        ["ffmpeg", "-v", "info", "-ss", str(t), "-i", path, "-frames:v", "15",
         "-vf", "cropdetect=limit=24:round=2:reset=0", "-f", "null", "-"],
        capture_output=True, text=True)
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    if not crops:
        return None
    w, h, x, y = (int(v) for v in crops[-1])
    return w, h, x, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--paquete", required=True)
    ap.add_argument("--groq-helper", default=os.environ.get("GROQ_HELPER", "groq_api.py"))
    ap.add_argument("--umbral", type=float, default=0.85)
    a = ap.parse_args()

    problems = []

    if probe_dims(a.video) != (720, 1280):
        problems.append(f"el video final no mide 720×1280: {probe_dims(a.video)}")

    d = probe_dur(a.video)
    samples = sorted({2, 15, 60, 150, 250, max(2, int(d) - 5)})
    for t in samples:
        if t >= d:
            continue
        c = crop_at(a.video, t)
        if c and (c[3] > 4 or c[1] < 1200):
            problems.append(f"posibles BARRAS NEGRAS en t={t}s: crop={c[0]}:{c[1]}:{c[2]}:{c[3]}")

    pkg = open(a.paquete).read()
    expected = {}
    for m in re.finditer(r"^(\d+)\.\s+\*\*[^*]+:\*\*\s+«(.+?)»\s*$", pkg, re.M):
        expected[int(m.group(1))] = m.group(2)

    mp3 = "/tmp/gate-final.mp3"
    out_json = "/tmp/gate-final-groq.json"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.video, "-vn",
                    "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame",
                    "-b:a", "48k", mp3], check=True)
    r = subprocess.run(["python3", a.groq_helper, "transcribe", mp3,
                        "--language", "es", "--out", out_json],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("RECHAZADO: falló la transcripción total:", r.stderr[-300:])
        return 1
    got_words = norm(json.load(open(out_json))["text"])

    pos = 0
    missing = []
    for n in sorted(expected):
        exp = norm(expected[n])
        window = got_words[pos:pos + len(exp) * 3 + 60]
        ratio = SequenceMatcher(None, exp, window[:len(exp) * 2 + 20],
                                autojunk=False).ratio() if window else 0.0
        # avance: buscar el mejor encaje en la ventana y mover el puntero
        best, best_end = 0.0, pos
        sm = SequenceMatcher(None, exp, window, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("equal", "replace") and i2 == len(exp):
                best_end = pos + j2
        ratio = SequenceMatcher(None, exp, got_words[pos:best_end],
                                autojunk=False).ratio() if best_end > pos else ratio
        if ratio < a.umbral:
            missing.append((n, round(ratio, 3)))
        else:
            pos = best_end
    if missing:
        problems.append(f"líneas no encontradas en orden en la transcripción "
                        f"total: {missing}")

    if problems:
        print("RECHAZADO:")
        for p in problems:
            print(" -", p)
        return 1
    print(f"OK: 720×1280, sin barras en {len(samples)} puntos de muestreo, "
          f"y las {len(expected)} líneas del guion completas y en orden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
