# Hallazgos verificados

Este archivo resume los resultados de ingeniería inversa que condicionan materialmente la implementación actual. Se omiten deliberadamente los callejones sin salida históricos y los registros de pruebas puntuales.

## Base de referencia

- Juego: `Boku no Natsuyasumi Portable: Mushi Mushi Hakase to Teppen-yama no Himitsu!!`
- Product ID: `UCJS10038`
- Traducción española: TraduSquare/GriffithVIII v1.0 (2025-08-01)
- Emulador probado: PPSSPP 1.20.4 Windows x64
- MD5 esperado de la ISO japonesa limpia: `B4D363D59CB87E25AB76AFC5384CCA31`

El parche español conserva el `BOOT.BIN` japonés original y sustituye `EBOOT.BIN`. El ejecutable español se utiliza como base de runtime porque contiene los cambios de diálogo horizontal, subtítulos, disposición de menús y fuente proporcional introducidos por la traducción.

## Datos de diálogo

Las herramientas públicas existentes para Boku y la extracción directa JP/ES coinciden en la estructura anidada CDIMG/pack/diálogo del juego. El texto se serializa como palabras little-endian de 16 bits con controles que incluyen `0x8000`, `0xFFFF`, `0x8001` y `0x8002` junto con su argumento y el guard de página.

El pipeline actual empareja estructuralmente 8.539 registros de diálogo JP/ES y conserva sus flujos binarios exactos en un blob bilingüe determinista. La resolución en runtime no utiliza direcciones volátiles del renderer como identidad del diálogo.

Consulta [boku-dialogue-format.md](boku-dialogue-format.md) para el contrato del formato.

## Comportamiento del ejecutable y runtime

La comparación estática mostró que el ejecutable español añade una región ejecutable inyectada y modifica la ruta original de texto/renderizado. Candidatos tempranos de estado del renderer, como `0x0892EBA4`, fueron descartados experimentalmente como identidades de diálogo: representaban geometría o estado de layout.

La implementación funcional engancha en su lugar la ruta verificada de diálogo completo. El plugin comprueba la firma del ejecutable español esperado antes de instalar el hook y se desactiva de forma segura en revisiones desconocidas.

El modo japonés necesita dos cambios de renderizado además de sustituir el flujo de diálogo:

- restaurar el atlas de fuente japonés original;
- sustituir la carga de ancho proporcional española por el avance fijo original de 16 píxeles.

Restaurar cambios más amplios del text-walker japonés fue probado y descartado porque corrompía el layout. El cambio estrecho del estado de ancho es suficiente para la ruta soportada.

## Ambigüedad y paginación

Un mismo flujo traducido puede corresponder a más de un registro japonés original. Por ello, el blob bilingüe conserva información estructural y de contexto y marca firmas ambiguas en lugar de adivinarlas.

Los registros JP y ES también pueden diferir en número de páginas. El resolver de runtime mapea explícitamente ordinales de página compatibles; los registros incompatibles permanecen o vuelven al español.

Estas reglas son intencionalmente conservadoras: es preferible perder un cambio puntual a japonés antes que mostrar texto incorrecto o mezclar estados de renderizado incompatibles.

## Integración con PPSSPP

La interfaz de depuración de PPSSPP se utiliza únicamente como puente de entrada: una pulsación de F7 en el host se traduce al bit del botón Note de PSP, que el PRX detecta dentro del estado de entrada del juego. Por ello el mod funciona con la versión estándar de PPSSPP probada y no necesita un fork del emulador.

Los savestates incluyen memoria del plugin. Deben utilizarse con la misma compilación del plugin con la que fueron creados; después de recompilar, inicia el juego normalmente y crea un savestate nuevo.
