# Guía de usuario

## Instalación

1. Instala Git y Python 3.10 o superior.
2. Clona el repositorio.
3. Coloca una ISO japonesa limpia de `UCJS10038` en `input/jp/Boku_JP.iso`.
4. Descarga la traducción española v1.0 desde la [página oficial de TraduSquare](https://tradusquare.es/proyectos/boku-no-natsuyasumi/), aplícala a una copia de la ISO japonesa limpia y coloca el resultado en `input/es/Boku_ES.iso`.
5. Ejecuta `install.bat`.
6. Ejecuta `launch.bat`.

`install.bat` descarga las dependencias fijadas por el proyecto, verifica ambas ISOs, extrae los datos necesarios y compila el plugin. No modifica la ISO japonesa original.

## Uso

- Pulsa **F7** mientras haya un diálogo de juego visible para alternar entre japonés y español.
- Los menús y las cinemáticas permanecen en español.
- Los diálogos no resueltos o incompatibles se mantienen en español o vuelven automáticamente a él.
- El primer cambio puede tardar un poco más porque algunos recursos se cargan de forma diferida.

## Savestates

Los savestates de PPSSPP incluyen la memoria del plugin. Utiliza un savestate únicamente con la misma compilación de `BokuLangToggle.prx` con la que fue creado. Después de recompilar el plugin, inicia el juego normalmente y crea un savestate nuevo. Para progreso a largo plazo, es preferible utilizar los guardados internos del juego.

## Comandos de desarrollo

| Comando | Función |
| --- | --- |
| `install.bat` | Preparación y compilación inicial completas |
| `./scripts/build.ps1` | Recompilar después de cambios en el código |
| `./scripts/deploy.ps1` | Copiar la compilación actual a PPSSPP portable |
| `launch.bat` | Desplegar, iniciar PPSSPP y activar el puente de F7 |

## Solución de problemas

### La ISO es rechazada

Utiliza la versión japonesa limpia `UCJS10038`. El instalador espera el MD5 `B4D363D59CB87E25AB76AFC5384CCA31`. Para la versión española, utiliza el resultado de aplicar la traducción oficial v1.0 a esa misma imagen limpia.

### F7 no hace nada

Cierra PPSSPP por completo y vuelve a iniciarlo mediante `launch.bat`. El launcher despliega el plugin, configura la interfaz de depuración de PPSSPP utilizada por el proyecto e inicia el puente de la tecla F7.

### Un savestate se comporta de forma extraña

Probablemente fue creado con otra compilación del plugin. Reinicia el juego, carga una partida guardada dentro del juego y crea un nuevo savestate de PPSSPP.

### Logs

El log del plugin se escribe en:

```text
external/ppsspp-bin/portable/memstick/PSP/PLUGINS/BokuLangToggle/
```

Para reportar un problema, incluye la versión de PPSSPP, el hash de la compilación del plugin, los pasos para reproducirlo, el fragmento relevante del log, el idioma activo y una captura de pantalla.
