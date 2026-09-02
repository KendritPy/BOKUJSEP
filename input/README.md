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
    `-- Boku_ES.iso       # user-supplied Spanish v1.0 patched image
```

The project does not download or redistribute the Spanish patch. Obtain it
from its official project, apply it independently to your own clean dump, and
then provide the resulting ISO here. Do not rename these files unless you pass
explicit `-JpIso` and `-EsIso` paths to `scripts/setup.ps1`.
