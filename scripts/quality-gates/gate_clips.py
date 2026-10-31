#!/usr/bin/env python3
"""COMPUERTA: todo clip aceptado debe medir 720×1280 EXACTO.

El generador a veces entrega 1152×768 horizontal pese al prompt 9:16
(pasó en producción con 15 líneas de un capítulo). Esa salida se descarta
AQUÍ, antes de verificar audio y antes de que entre al armado: un clip
horizontal que llega al armado termina en barras negras o recortes forzados.

Uso:
  python3 gate_clips.py clip1.mp4 clip2.mp4 [...]
  python3 gate_clips.py --dir ./clips

Sale con código 1 y lista los rechazados si alguno no mide 720×1280.
"""
import argparse, glob, os, subprocess, sys


def dims(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()
    try:
        w, h = out.split(",")
        return int(w), int(h)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("archivos", nargs="*")
    a = ap.parse_args()
    files = list(a.archivos)
    if a.dir:
        files += sorted(glob.glob(os.path.join(a.dir, "*.mp4")))
    if not files:
        print("RECHAZADO: no se pasaron clips")
        return 1
    bad = []
    for f in files:
        d = dims(f)
        if d != (720, 1280):
            bad.append((f, d))
    if bad:
        print(f"RECHAZADO: {len(bad)} de {len(files)} clips NO miden 720×1280:")
        for f, d in bad:
            print(f"  {f}: {d}")
        return 1
    print(f"OK: {len(files)} clips, todos 720×1280 exacto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
