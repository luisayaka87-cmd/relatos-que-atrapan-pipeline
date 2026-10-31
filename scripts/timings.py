#!/usr/bin/env python3
"""Tiempos por palabra de las fuentes aceptadas de un capítulo + manifiesto.

Generalización del script usado en producción (Cap. 2 de Graciela).

Uso:
  python3 timings.py --clips-dir ./clips --manifiesto manifiesto.json --out timings.json

manifiesto.json mapea número de línea -> entrada:
  {"1":  {"clip": "linea-01.mp4"},
   "31": {"respaldo": true, "audio": "linea-31-audio.mp3",
          "visual": "linea-31-visual.mp4", "groq": "linea-31-groq.json"}}

Para clips normales, si existe <clip>-groq.json junto al clip se reutiliza;
si no, se transcribe con Groq (whisper-large-v3). El ayudante de Groq se
resuelve con --groq-helper o la variable de entorno GROQ_HELPER.
La transcripción de cada clip YA debió pasar la verificación contra el guion
(scripts/verificar_linea.py): aquí solo se extraen los tiempos por palabra.
"""
import argparse, json, os, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips-dir", required=True)
    ap.add_argument("--manifiesto", required=True)
    ap.add_argument("--out", default="timings.json")
    ap.add_argument("--groq-helper", default=os.environ.get("GROQ_HELPER", "groq_api.py"))
    a = ap.parse_args()

    manifest_in = json.load(open(a.manifiesto))
    out = {"manifest": {}, "timings": {}}
    for n in sorted(manifest_in, key=lambda x: int(x)):
        info = manifest_in[n]
        if info.get("respaldo"):
            audio = os.path.join(a.clips_dir, info["audio"])
            visual = os.path.join(a.clips_dir, info["visual"])
            out["manifest"][n] = {"audio": audio, "visual": visual, "respaldo": True}
            gj = os.path.join(a.clips_dir, info["groq"])
            d = json.load(open(gj))
        else:
            src = os.path.join(a.clips_dir, info["clip"])
            out["manifest"][n] = {"clip": src, "respaldo": False}
            gj = src[:-4] + "-groq.json"
            if not os.path.exists(gj):
                r = subprocess.run(["python3", a.groq_helper, "transcribe", src,
                                    "--language", "es", "--out", gj],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    print(f"L{n}: GROQ FAIL {r.stderr[-200:]}", flush=True)
                    sys.exit(1)
            d = json.load(open(gj))
        ws = d.get("words") or []
        out["timings"][n] = {"text": d["text"], "words": [
            {"w": w["word"], "s": round(w["start"], 3), "e": round(w["end"], 3)}
            for w in ws]}
        if ws:
            print(f"L{n}: {len(ws)} palabras, voz {ws[0]['start']:.2f}..{ws[-1]['end']:.2f}",
                  flush=True)
        else:
            print(f"L{n}: SIN PALABRAS", flush=True)
            sys.exit(1)
    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"LISTO -> {a.out}")


if __name__ == "__main__":
    main()
