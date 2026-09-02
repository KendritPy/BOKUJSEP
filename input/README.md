# Local game images

This directory is intentionally committed without game data. Supply your own
legally obtained images locally; ISO files and downloaded patch material are
ignored by Git.

Expected layout:

```text
input/
|-- jp/
|   `-- Boku_JP.iso       # user-supplied clean UCJS10038 image
`-- es/
    `-- Boku_ES.iso       # generated locally by scripts/setup.ps1
```

Do not rename these files unless you also pass the corresponding explicit
path to the PowerShell scripts.
