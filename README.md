# BokuLangToggle

BokuLangToggle es un plugin para PPSSPP de **Boku no Natsuyasumi Portable** (`UCJS10038`) que permite alternar en tiempo real los diálogos del juego entre el japonés original y la traducción al español v1.0 de TraduSquare/GriffithVIII.

Pulsa **F7** mientras haya un cuadro de diálogo visible para cambiar de idioma. El modo japonés restaura el texto original emparejado, el atlas de fuente japonés y el espaciado fijo; el modo español restaura el texto traducido y el espaciado proporcional. Los menús y las cinemáticas permanecen en español.

## Estado

- Cambio japonés/español en tiempo real para los diálogos de juego compatibles.
- 8.539 registros de diálogo emparejados estructuralmente.
- Retorno automático al español cuando un registro no puede resolverse con seguridad o tiene una paginación incompatible.
- Preparación automatizada del entorno probado: PPSSPP 1.20.4 x64 para Windows.
- Los savestates funcionan si fueron creados con la misma compilación del plugin; después de recompilar conviene crear uno nuevo.

## Requisitos

- Windows 10 u 11
- Git
- PowerShell 5.1 o superior
- Python 3.10 o superior
- Una ISO japonesa limpia de `UCJS10038`
- La traducción española v1.0 de TraduSquare/GriffithVIII, descargada desde su [página oficial](https://tradusquare.es/proyectos/boku-no-natsuyasumi/)
- Acceso a Internet durante la preparación inicial

## Instalación rápida

1. Clona este repositorio.
2. Coloca tu ISO japonesa limpia en `input/jp/Boku_JP.iso`.
3. Descarga el parche español v1.0 desde la página oficial de TraduSquare, aplícalo a una copia de la misma ISO limpia y coloca el resultado en `input/es/Boku_ES.iso`.
4. Ejecuta `install.bat`.
5. Ejecuta `launch.bat`.
6. Durante un diálogo, pulsa **F7** para cambiar de idioma.

`install.bat` descarga las dependencias fijadas por el proyecto, verifica ambas ISOs, extrae los datos necesarios, genera el mapa bilingüe y compila el plugin. No modifica la ISO japonesa original.

Para problemas de instalación y reglas sobre savestates, consulta [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## Cómo funciona

El plugin se ejecuta sobre el EBOOT de la traducción española v1.0 para conservar sus mejoras de renderizado. Las herramientas offline emparejan los diálogos japoneses y españoles por su identidad estructural y generan un blob bilingüe inmutable con los flujos exactos de palabras de 16 bits.

En tiempo de ejecución, el PRX intercepta la ruta de diálogo verificada. En modo español deja intacta la ruta normal de la traducción. En modo japonés sustituye el flujo por su original emparejado, coloca el atlas japonés y restaura el avance fijo original de 16 píxeles. Si un registro es desconocido o incompatible, el plugin vuelve al español.

El puente de **F7** utiliza la interfaz de depuración de PPSSPP para convertir la tecla del host en una entrada del botón Note de PSP que el plugin puede detectar. No hace falta una versión modificada de PPSSPP.

Los detalles técnicos están en [docs/architecture.md](docs/architecture.md), [docs/boku-dialogue-format.md](docs/boku-dialogue-format.md) y [docs/findings.md](docs/findings.md).

## Desarrollo

Las etapas de compilación pueden ejecutarse por separado:

```powershell
./scripts/bootstrap.ps1
./scripts/setup.ps1
./scripts/pipeline.ps1
./scripts/build.ps1
./scripts/deploy.ps1
```

Para ejecutar las pruebas:

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) antes de enviar cambios.

## Distribución y créditos

Debes aportar tu propia ISO japonesa y obtener la traducción española desde su fuente oficial. Este repositorio no distribuye el juego ni el parche de traducción.

El código original de este repositorio se publica bajo la [licencia MIT](LICENSE). La traducción española pertenece a TraduSquare/GriffithVIII y a sus colaboradores acreditados.

> **Nota:** el proyecto fue desarrollado con asistencia extensiva de IA, principalmente OpenAI Codex, bajo dirección, revisión y pruebas humanas.
