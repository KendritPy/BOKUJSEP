# Imágenes locales del juego

Este directorio se incluye sin datos del juego. Debes aportar localmente tus propias imágenes; las ISOs y el material descargado del parche están ignorados por Git.

Estructura esperada:

```text
input/
|-- jp/
|   `-- Boku_JP.iso       # ISO japonesa limpia UCJS10038 aportada por el usuario
`-- es/
    `-- Boku_ES.iso       # ISO parcheada con la traducción española v1.0
```

El proyecto no descarga ni redistribuye el parche español. Obtén la traducción desde su [página oficial de TraduSquare](https://tradusquare.es/proyectos/boku-no-natsuyasumi/), aplícala a una copia de tu ISO japonesa limpia y coloca aquí la ISO resultante.

No cambies los nombres de estos archivos salvo que pases rutas explícitas mediante `-JpIso` y `-EsIso` a `scripts/setup.ps1`.
