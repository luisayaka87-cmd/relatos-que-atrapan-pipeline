#!/usr/bin/env python3
"""COMPUERTA: el ASS de karaoke debe cumplir el formato antes de quemar.

Rechaza si:
1. Falta el evento Headline de 0,0 a 5,0 s, o su texto no contiene el título.
2. Algún evento Karaoke empieza antes de 5,0 s (invadiría el tramo del
   headline, donde no va karaoke).
3. Alguna palabra de algún evento Karaoke aparece SIN color en línea justo
   antes de ella. La libass de producción ignora los colores de los Style:
   la palabra sin \\c en línea sale NEGRA al quemar. Este fue un defecto real
   detectado en producción: las palabras ya dichas salían negras porque solo
   la activa y las siguientes llevaban color.

Uso:
  python3 gate_karaoke.py --ass karaoke.ass --titulo "¡LA MULTA QUE NADIE PODÍA CREER!"
"""
import argparse, re, sys, unicodedata


def ass_seconds(ts):
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def words_without_inline_color(text):
    """En ASS el color en línea persiste desde que aparece un \\c& hasta el
    fin del evento: las únicas palabras que salen NEGRAS con la libass que
    ignora los Style son las que aparecen ANTES del primer \\c& del evento
    (el defecto real de producción: la primera palabra de cientos de eventos
    no llevaba color en línea)."""
    tokens = re.split(r"(\{[^}]*\})", text)
    bad = []
    seen_color = False
    for tok in tokens:
        if tok.startswith("{"):
            if "\\c&" in tok:
                seen_color = True
            continue
        for w in tok.split():
            if w and not seen_color:
                bad.append(w)
    return bad


def words_of(text):
    t = re.sub(r"\{[^}]*\}", "", text).replace("\\N", " ")
    t = unicodedata.normalize("NFD", t.upper())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[A-Z]+", t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ass", required=True)
    ap.add_argument("--titulo", required=True, help="título del capítulo, en mayúsculas")
    a = ap.parse_args()

    events = []
    for line in open(a.ass):
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            events.append((ass_seconds(parts[1]), ass_seconds(parts[2]),
                           parts[3], parts[9].strip()))

    problems = []

    head = [e for e in events if e[2] == "Headline"]
    titulo_words = words_of(a.titulo)
    if not head:
        problems.append("falta el evento Headline")
    else:
        s, e, _, tx = head[0]
        if not (s == 0.0 and abs(e - 5.0) < 0.01):
            problems.append(f"Headline fuera de ventana 0–5 s ({s}–{e})")
        # las palabras del título deben aparecer, en orden, en el headline
        hw = words_of(tx)
        it = iter(range(len(hw)))
        pos = 0
        ok = True
        for w in titulo_words:
            found = False
            while pos < len(hw):
                if hw[pos] == w:
                    found = True
                    pos += 1
                    break
                pos += 1
            if not found:
                ok = False
                break
        if not ok:
            problems.append("el texto del Headline no contiene el título del capítulo")

    karaoke = [e for e in events if e[2] == "Karaoke"]
    if not karaoke:
        problems.append("no hay eventos Karaoke")
    for s, e, _, tx in karaoke:
        if s < 5.0:
            problems.append(f"evento Karaoke empieza antes de 5,0 s ({s})")
            break
    black = []
    for s, e, _, tx in karaoke:
        black += words_without_inline_color(tx)
    if black:
        problems.append(f"{len(black)} palabras sin color en línea (salen NEGRAS), "
                        f"ej.: {black[:5]}")

    if problems:
        print("RECHAZADO:")
        for p in problems:
            print(" -", p)
        return 1
    print(f"OK: headline 0–5 s con el título, {len(karaoke)} eventos de karaoke "
          "desde 5,0 s y todas las palabras con color en línea")
    return 0


if __name__ == "__main__":
    sys.exit(main())
