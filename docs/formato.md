# Especificación de formato vigente — «Relatos que atrapan»

Especificación exacta y verificada en producción (saga «El hilo de Rosa» y «El carrito de doña Graciela»). Cualquier desviación debe anotarse y justificarse; el formato no se improvisa por capítulo.

## Video

- **Vertical 9:16, 720×1280 exactos**, 30 fps, audio 48 kHz estéreo.
- Un clip por línea, una línea completa por clip, un solo hablante por clip.
- Cámara fija: `LOCKED STATIC CAMERA, NO zoom, NO push-in, NO pull-out` en cada prompt.
- Estilo: `ultra realistic photorealistic cinematic, like a real film`.
- Sincronía labial explícita en cada prompt de diálogo: `Precise lip sync: his/her lips move exactly with every word he/she says`.
- Sin subtítulos quemados ni texto legible dentro del clip generado (`No burned-in subtitles, no text overlays, no readable text anywhere`): los textos se queman después, en el armado.
- **Compuerta:** un clip solo se acepta si el archivo mide **720×1280 exacto**. El generador a veces entrega 1152×768 horizontal pese al prompt 9:16: esa salida se descarta antes de verificar el audio.

## Apertura (ver también docs/hook-brutal.md)

- El capítulo abre con **una persona hablando en pantalla** (nunca un objeto sin cara).
- Los primeros 5 segundos siguen el estándar de hook brutal: la primera línea es la más fuerte del capítulo.

## Subtítulos karaoke (ASS quemado)

- Fuente **Montserrat ExtraBold**, tamaño **53** (a 720×1280), todo en mayúsculas, centrado abajo, **MarginV 380**.
- Máximo **3 palabras por línea** de karaoke.
- La palabra que se está diciendo va en **dorado `&H0000D7FF`** y más grande (**70**); las demás en blanco.
- Contorno negro 4.
- El texto mostrado es el **del guion** (no el de la transcripción), alineado a los tiempos por palabra medidos.

## Textos fijos

- **«CAPÍTULO N DE 4»**: Montserrat ExtraBold **45**, dorado, contorno 5, arriba centrado, de **0 a 4 s**.
- **Marca de agua «VERA MONTALVO»**: cursiva **31** (Gelasio-Italic, gemela métrica de Georgia), blanca semitransparente, centrada abajo, **durante todo el video**.
- **HEADLINE del título del capítulo**: todo en mayúsculas, **amarillo puro `&H00FFFF`**, Montserrat ExtraBold **56**, a la altura de los subtítulos (MarginV 380), durante los **primeros 5 segundos exactos**, y **sin karaoke en ese tramo** (el karaoke entra a los 5,0 s; el evento que cruce ese punto se recorta para empezar en 5,0).

## ⚠️ LECCIÓN CRÍTICA — colores SIEMPRE en línea (libass)

La libass de la máquina de producción **ignora los colores definidos en los Style del ASS**: todo texto cuyo color va solo en el estilo sale **NEGRO** al quemar.

Por tanto, **TODOS los colores van en línea dentro del texto de cada evento, palabra por palabra**:

- Palabras ya dichas: `{\\c&HFFFFFF&}` (blanco).
- Palabra activa: `{\\fs70\\c&H00D7FF&}` (dorada y más grande), cerrando con `{\\fs53\\c&HFFFFFF&}`.
- Palabras siguientes: `{\\c&HFFFFFF&}` (blanco).
- Headline: `{\\c&H00FFFF&}`. «CAPÍTULO N DE 4»: `{\\c&H00D7FF&}`. Marca: `{\\c&HFFFFFF&\\alpha&H80&}`.

El error típico (detectado y corregido en producción): los eventos de karaoke llevaban color solo en la palabra activa y las siguientes, y las palabras **ya dichas** quedaban sin color en línea → salían negras. La compuerta `gate_karaoke.py` rechaza cualquier evento donde una palabra aparezca sin su color en línea.

## Armado

- Tiempos por palabra medidos sobre cada clip aceptado.
- Cada segmento se recorta a su **rango de voz real** con margen ~0,1 s.
- Segmentos con audio externo (respaldos): visual desde 0,3 s, extendida por congelamiento (`tpad stop_mode=clone`) hasta la duración exacta del audio.
- Unión con **xfade 0,3 s** (video) y **acrossfade 0,3 s** (audio), con offsets acumulados.
- Fotogramas de control del video final se extraen con `-ss` **después** del `-i` (búsqueda exacta). Con `-ss` antes del `-i`, la libass puede mostrar eventos de t≈0 y el fotograma miente.

## Verificación (obligatoria, sin excepciones)

- **Cada clip:** transcripción (Whisper local; arbitraje Groq con whisper-large-v3) y confirmación de línea completa y exacta contra el guion.
- **Video final:** transcripción completa (Groq) y revisión de las **48 líneas en orden** por ventanas (offsets desde `segmentos.json`); se tolera el sangrado de los fundidos de 0,3 s entre ventanas y las desviaciones ya anotadas por clip.
- **Formato final:** cropdetect sin barras negras; headline presente a 1 s y 4,9 s; karaoke de vuelta a 5,5 s; fotogramas de mitad y cierre.
- Artefactos de ASR que **no** son fallos: cifras escritas («30 años», «$1,317» como dígitos), «nomás» partido, homófonos, nombres leídos fonéticamente («Yakima»→«Yáquima»), seseo («Zinapécuaro» oído como «Sinapecuaro» es pronunciación correcta).
