# Formato de diálogo de Boku Portable

Este documento describe las estructuras serializadas de las que depende BokuLangToggle. La implementación conserva las palabras binarias originales del juego y las identidades estructurales; las cadenas decodificadas se utilizan únicamente para inspección.

## Ruta de los contenedores

```text
PSP_GAME/USRDIR/
  cdimg.idx + cdimg0.img
    -> map/gz/*.bin
      -> M_*.bin.gz / .gzx
        -> pack sin nombre
          -> miembro 1
            -> archivo de diálogo
              -> bloque
                -> elemento de texto/segmento
```

La identidad estable de un diálogo se basa en esta estructura, no en una dirección de RAM en tiempo de ejecución:

```text
(script, miembro del pack con nombre, id de diálogo/bloque, elemento de texto, segmento)
```

## CDIMG y packs

`cdimg.idx` comienza con `DFI\0`. Los offsets de archivo se almacenan en sectores de `0x800` bytes. Los packs con nombre contienen un contador seguido de entradas de `0x0C` bytes `(offset, size, name_offset)`; los packs sin nombre utilizan entradas de `0x08` bytes `(offset, size)`. Los miembros `.gz` son flujos gzip normales; `.gzx` añade un prefijo de 32 bits con el tamaño descomprimido antes de los datos gzip.

Las entradas de tamaño cero y las posiciones originales de las tablas deben conservarse al reconstruir los archivos.

## Bloques de diálogo

Un archivo de diálogo comienza con un contador de bloques de 32 bits, seguido de entradas que contienen un ID de 16 bits, la longitud del bloque en 16 bits y un offset de bloque de 32 bits.

Cada bloque comienza con un contador de elementos y una tabla de offsets. En los parsers públicos utilizados como base para este proyecto, las entradas a partir del índice 3 alternan entre claves/nombres ASCII y flujos de texto de 16 bits:

```text
3 clave, 4 texto, 5 clave, 6 texto, ...
```

El generador bilingüe conserva el flujo binario exacto junto a cada representación decodificada, de modo que los códigos de control y terminadores nunca se reconstruyen a partir del texto.

## Palabras de texto

Las palabras son valores `u16` little-endian. Los controles utilizados por el pipeline actual incluyen:

| Palabra | Significado / regla |
| ---: | --- |
| `0x8000` | terminador normal de texto; conservar exactamente |
| `0xFFFF` | terminador alternativo; conservar exactamente |
| `0x8001` | salto de línea |
| `0x8002` | control de página/pausa; consume el argumento siguiente |
| `0x0000` | separación de segmento, guard de página o límite dependiente del contexto; no descartarlo a ciegas |

La secuencia multipágina verificada es:

```text
0x8002, argumento, 0x0000, primera palabra de la página siguiente, ...
```

Eliminar ese cero puede hacer desaparecer el primer carácter visible de la página siguiente. Por ello, los límites de página se interpretan mediante el elemento contenedor y la secuencia de controles, no tratando cada cero como un terminador de cadena C.

## Atlas de fuentes

Los códigos de caracteres indexan tiles de glifos de 16x16 dentro de hojas PIM2 de 512x512 y 4 bpp:

```text
atlas_index = code // 1024
tile_index  = code % 1024
tile_x      = (tile_index % 32) * 16
tile_y      = (tile_index // 32) * 16
```

Los píxeles PIM2 utilizan el swizzling de PSP. Durante la compilación local se extraen los atlas JP y ES de sus respectivas imágenes del juego; el plugin intercambia el atlas adecuado en runtime en lugar de asumir que la tabla de códigos de una edición sirve para la otra.

## Reglas de mapeo en runtime

El generador offline empareja los registros JP y ES por identidad estructural y guarda sus flujos binarios exactos en un blob inmutable. También conserva el contexto necesario para rechazar firmas ES ambiguas y diferencias incompatibles en el número de páginas.

En runtime, el hook de diálogo verificado resuelve el registro ES actual. El modo japonés sustituye el ordinal de página correspondiente en JP, restaura el atlas japonés y utiliza el avance fijo original de 16 píxeles. Si el registro no puede resolverse, es ambiguo o tiene una paginación incompatible, el plugin permanece en español o vuelve a él.

Estas reglas prefieren deliberadamente perder un cambio puntual de idioma antes que mostrar texto corrupto, sustituir el registro equivocado o mezclar estados de renderizado incompatibles.
