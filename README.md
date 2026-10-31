# relatos-que-atrapan-pipeline

Pipeline completo de producción de las sagas verticales dramatizadas de **«Relatos que atrapan»**, tal como se usa en producción real (sagas «El hilo de Rosa» y «El carrito de doña Graciela»). Este repositorio es la fuente de verdad del método: si una escena o un capítulo contradice lo aquí escrito, se corrige la escena, no el método.

## El método en breve

- **Sagas de 4 capítulos.** Cada capítulo dura ~5–7 minutos.
- **48 líneas por capítulo, un clip por línea, un solo hablante por clip.** Los demás personajes aparecen en silencio, con los labios cerrados.
- **Cámara fija en cada clip** (`LOCKED STATIC CAMERA, NO zoom, NO push-in, NO pull-out`).
- **Estilo visual:** ultra realista, fotorrealista cinematográfico, como una película real. Nada de ilustración pintada.
- **Hook con una persona hablando en pantalla** — nunca objetos sin caras — y bajo el [estándar de hook brutal](docs/hook-brutal.md): los primeros 5 segundos enganchan con violencia emocional.
- **Verificación obligatoria por transcripción:** ningún clip se acepta sin transcribirlo y confirmar que dice la línea completa y exacta del guion; ningún capítulo se entrega sin transcribir el video final completo y revisar las 48 líneas en orden.
- **Compuertas de calidad automáticas** (`scripts/quality-gates/`): el capítulo no se marca terminado hasta que todas pasan.

## Flujo de producción de un capítulo

1. **Biblia y paquete aprobados antes de generar un solo clip** (plantillas en `templates/`): biblia de la saga (reparto fijo con descriptores de voz exactos, objetos ancla, locaciones, reglas de narración) y paquete del capítulo (título, descripción, prompt de portada y guion completo, línea por línea, con hablante y texto exacto entre «»).
2. **Generación por tandas** (máx. 6 clips por tanda): prompt vertical 9:16 con la frase explícita de sincronía labial (`Precise lip sync: his/her lips move exactly with every word he/she says`), descriptor de voz exacto del personaje y la línea exacta del guion entre «».
3. **Verificación de cada clip** (`scripts/verificar_linea.py`): transcripción con Whisper local y arbitraje con Groq (whisper-large-v3). Si una línea falla de verdad, se regenera con dirección distinta; si se atasca, ruta de respaldo: visual muda que oculta la boca + audio TTS verificado exacto. Nunca se entrega una línea sin verificar.
4. **Tiempos por palabra** (`scripts/timings.py`) de los 48 clips aceptados.
5. **Armado** (`scripts/armado.py`): segmentos recortados a la voz real (margen ~0,1 s), normalizados a 720×1280 / 30 fps / 48 kHz, unión con fundidos xfade/acrossfade de 0,3 s, y quemado del ASS (karaoke + headline + «CAPÍTULO N DE 4» + marca).
6. **Compuertas finales** (`scripts/quality-gates/`): dimensiones exactas de cada clip, karaoke con colores en línea en cada palabra, headline presente 0–5 s, sin barras negras (cropdetect), transcripción total con las 48 líneas en orden. Si una compuerta rechaza, no hay entrega.

## Estructura

```
README.md                  ← este archivo: el método
docs/formato.md            ← especificación técnica exacta del formato vigente
docs/hook-brutal.md        ← estándar de los primeros 5 segundos
scripts/timings.py         ← tiempos por palabra de los clips aceptados
scripts/armado.py          ← segmentos, karaoke ASS, unión y quemado
scripts/verificar_linea.py ← verificación por transcripción clip a clip
scripts/quality-gates/     ← compuertas que rechazan antes de entregar
templates/                 ← biblia, paquete, estado de producción, prompt de portada
.env.example               ← variables requeridas (SIN valores: las claves viven en la bóveda)
```

## Reglas que no se negocian

- Nada se da por verificado sin la transcripción real leída.
- Si una línea no se puede generar dialogada tras intentos con direcciones distintas, se marca pendiente con la desviación exacta y se sigue con el resto; la saga no se frena por un clip.
- Toda desviación aceptada (partícula tragada, respaldo, recorte mínimo de guion) queda **anotada** en el estado de producción y en el paquete. Nada se oculta.
- Las claves de Fish Audio y Groq **nunca** van en este repositorio: se ingresan por la bóveda segura. Aquí solo está `.env.example`.
- Los videos finales y los clips son pesados y **no** se versionan (ver `.gitignore`).
