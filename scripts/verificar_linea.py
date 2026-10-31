#!/usr/bin/env python3
"""Verificación por transcripción de clips sueltos contra el guion del paquete.

Generalización del script usado en producción (Cap. 2 de Graciela).

Uso:
  python3 verificar_linea.py --paquete paquete-capitulo.md --clips-dir ./clips \
      linea-05.mp4 linea-06.mp4

Lee las líneas esperadas del paquete (formato: `N. **HABLANTE:** «texto»`),
transcribe cada clip con Groq (whisper-large-v3) y reporta la similitud
normalizada (sin acentos ni puntuación) de cada línea contra el guion.

Regla del método: una línea solo se acepta COMPLETA y exacta. Las diferencias
de ASR conocidas (cifras en dígitos, «nomás» partido, homófonos, seseo) NO son
fallos y se juzgan leyendo la transcripción, no solo el número: si Whisper
local y Groq coinciden en un error, el clip está mal de verdad.
"""
import argparse, json, os, pathlib, re, subprocess, sys, unicodedata
from difflib import SequenceMatcher


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return [w for w in re.split(r"[^a-z0-9]+", t) if w]


def transcribe(mp4, groq_helper):
    mp3 = mp4.with_suffix(".mp3")
    out = mp4.with_name(mp4.stem + "-groq.json")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-vn",
                    "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame",
                    "-b:a", "48k", str(mp3)], check=True)
    subprocess.run(["python3", groq_helper, "transcribe", str(mp3),
                    "--language", "es", "--out", str(out)],
                   check=True, capture_output=True, timeout=300)
    return json.loads(out.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paquete", required=True)
    ap.add_argument("--clips-dir", required=True)
    ap.add_argument("--groq-helper", default=os.environ.get("GROQ_HELPER", "groq_api.py"))
    ap.add_argument("--salida", default="verificacion.json")
    ap.add_argument("archivos", nargs="+")
    a = ap.parse_args()

    pkg = pathlib.Path(a.paquete).read_text()
    expected = {}
    for m in re.finditer(r"^(\d+)\.\s+\*\*[^*]+:\*\*\s+«(.+?)»\s*$", pkg, re.M):
        expected[int(m.group(1))] = m.group(2)

    clips = pathlib.Path(a.clips_dir)
    results = {}
    for f in a.archivos:
        p = clips / f
        n = int(re.search(r"(\d+)", f).group(1))
        data = transcribe(p, a.groq_helper)
        r = SequenceMatcher(None, norm(expected[n]), norm(data["text"])).ratio()
        results[f"L{n:02d}"] = {"archivo": f, "similitud": round(r, 3),
                                "duracion": data.get("duration"),
                                "transcripcion": data["text"].strip()}
        print(f"L{n:02d} sim={r:.3f} :: {data['text'].strip()[:110]}")
    out = pathlib.Path(a.salida)
    prev = json.loads(out.read_text()) if out.exists() else {}
    prev.update(results)
    out.write_text(json.dumps(prev, ensure_ascii=False, indent=2))
    print("guardado en", out)


if __name__ == "__main__":
    main()
