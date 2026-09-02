# Arquitectura

BokuLangToggle es un PRX de espacio de usuario compatible con PPSSPP para `UCJS10038`. Se ejecuta sobre el EBOOT de la traducción española v1.0 para conservar sus modificaciones de renderizado y sustituye el diálogo por el japonés original únicamente cuando se solicita.

## Datos generados offline

El pipeline extrae ambas ediciones, identifica los diálogos estructuralmente, empareja registros JP/ES compatibles y genera un blob bilingüe determinista. Los registros conservan los flujos exactos de palabras de 16 bits y sus códigos de control en lugar de reconstruirlos a partir del texto decodificado.

La identidad estructural se basa en la jerarquía interna del juego (script/miembro/diálogo/bloque/elemento de texto/segmento), no en direcciones volátiles de RAM. El blob también conserva el contexto necesario para rechazar flujos traducidos ambiguos y pares con paginación incompatible.

## Ruta de runtime

En modo español se utiliza normalmente el ejecutable traducido. Al solicitar por primera vez un cambio de idioma, el PRX carga de forma diferida los datos bilingües y el atlas japonés, verifica la firma esperada del ejecutable e instala el hook de diálogo.

En modo japonés:

1. resuelve el flujo español actual contra el mapa bilingüe;
2. lo sustituye por el flujo japonés original emparejado;
3. coloca el atlas de fuente japonés original;
4. sustituye el avance proporcional de la traducción por el avance fijo original de 16 píxeles.

Al volver al español se restauran el flujo traducido, su atlas y el espaciado proporcional.

Las revisiones desconocidas, registros no resueltos, coincidencias ambiguas o paginaciones incompatibles vuelven al español. El plugin evita deliberadamente renderizar texto español con el atlas japonés.

## Puente de entrada

PPSSPP no expone directamente al juego la tecla F7 elegida en el host. `tools/ppsspp_debug.py` utiliza la interfaz de depuración de PPSSPP para traducir esa tecla al bit del botón Note de PSP. El PRX detecta ese flanco y alterna el idioma. Así se mantiene la compatibilidad con la versión estándar de PPSSPP probada por el proyecto, sin requerir un fork del emulador.

## Estructura del proyecto

- `plugin/` — código fuente y configuración del PRX ejecutado en PSP.
- `tools/` — extracción, comparación, generación del blob bilingüe, auditoría de fuentes y puente con el depurador de PPSSPP.
- `scripts/` — descarga de dependencias, preparación local, compilación, despliegue y automatización del launcher.
- `tests/` — pruebas deterministas de las herramientas soportadas.

Consulta [boku-dialogue-format.md](boku-dialogue-format.md) para el formato serializado de los diálogos y [findings.md](findings.md) para los resultados de ingeniería inversa verificados que condicionan la implementación.
