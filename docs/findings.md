# Findings

## Baseline (2026-08-31)

- Target: `Boku no Natsuyasumi Portable: Mushi Mushi Hakase to Teppen-yama no Himitsu!!`.
- Expected product ID: `UCJS10038` (PARAM.SFO commonly formats this as `UCJS-10038`).
- Official Spanish translation release: v1.0, dated 2025-08-01.
- Spanish patch archive SHA-256: `F38EDCE9CFEAD315574460F9F0356AFF1B6EE03FD22AD023D09CA11B24F735F7`.
- Spanish xdelta SHA-256: `B6F4145FD880406CC56D9F3C929A56E642F0218EEBC03E9ECE84C3C9228074C3`.
- Known clean Japanese ISO MD5 from the Korean tool project: `B4D363D59CB87E25AB76AFC5384CCA31`.
- PPSSPP portable baseline: 1.20.4 Windows x64.
- PPSSPP ZIP SHA-256: `FBC9CD2F5131B159A92424E5C458C35CE43BA603CDDED64DFC98E4BD4F17FF93`.
- PPSSPP source snapshot: `56bba5f6f5e4ce5786f8528e73f2ece391fe34ea`.
- Spanish repository snapshot: `86820b58d881c9d947b87f6a913297bc9aec8163`.
- Korean tooling snapshot: recorded by `scripts/bootstrap.ps1` on each checkout.
- Pleonex tooling snapshot: `c88677d5709338fe1adf0fe61bb9dd43404e55ac`.

## Local inventory

- No clean Japanese ISO, Spanish-patched ISO, prior PPSSPP installation, or save was found in the usual Desktop/Documents/Downloads/configuration locations.
- The official Spanish v1.0 patch and PPSSPP portable baseline were downloaded into ignored local directories.
- PSPModBase's Windows PSPSDK submodule is present, so PRX compilation requires no user-installed PSP toolchain.
- PPSSPP 1.20.4 persists remote-debugger activation through `[General]` keys in `ppsspp.ini`; the newer upstream `--debugger` command-line flag is not present in that release binary. Development scripts configure the release-supported INI path and back it up.

## Spanish patch scope

The official project documents 100% dialogue, graphics, insect names,
cinematics, minigames, save-data presentation, widened menus, and VWF. Its
EBOOT changes add horizontal dialogue and several subtitle systems. Therefore
the Spanish EBOOT is the initial runtime base; Japanese mode must restore
original Japanese content without discarding those useful renderer changes.

## Pending measured results

Input hashes, detected IDs, per-file diffs, font coverage, decrypted EBOOT
hashes, and runtime addresses will be appended by the pipeline/debugging tools
after `input/jp/Boku_JP.iso` is available.
