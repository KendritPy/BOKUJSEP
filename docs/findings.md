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

## Runtime investigation (2026-08-31)

- Exact visible Spanish dialogue was not found in PSP RAM as literal UTF-8, Latin-1, UTF-16, or as a simple unknown fixed-width 8-bit/16-bit equality-pattern stream.
- A first two-sample RAM differential misleadingly concentrated line-transition changes around `0x0892EBDC-0x0892EC33`.
- A change watchpoint on `0x0892EC00-0x0892EC33` fired only ~0.00033 s after arming, before the user advanced dialogue.
- The hit PC was `0x0882AC2C`; the backtrace includes a call to `sceKernelGetSystemTimeLow`, and the watched region consists largely of repeated small 16-bit pairs. This is consistent with time-driven render/geometry state, not a current-dialogue identity structure.
- Therefore `0x0892EC00` is a **rejected dialogue candidate**. Do not use it as a text hook target without new evidence.
- The first differential probe used only one same-line noise interval and was vulnerable to periodic-state aliasing. `dialogue_stable_diff_probe.py` now samples each textbox repeatedly at irregular intervals before classifying line-specific changes.
- A later multi-sample differential ranked `0x0881C600` highly, but the selected word `0x0881C62C` currently contains bytes `F0 FF BD 27`, i.e. little-endian MIPS `0x27BDFFF0` / `addiu sp,sp,-0x10`, a normal function prologue. A real memory-breakpoint broadcast then timed out after the textbox was advanced. Treat this region as **executable code, not dialogue state**, unless future module/function mapping proves otherwise.
- Differential candidates must now be classified against PPSSPP's `hle.func.list` / module map before any watchpoint is armed. `classify_diff_candidates.py` performs this gate on the existing stable-diff report.
- The original watch scripts also incorrectly inferred a breakpoint hit from `cpu.status.stepping`. PPSSPP exposes the actual reason through the unsolicited `cpu.breakpoint.hit` broadcast; `dialogue_watch_event_probe.py` now waits for that real event and ignores unrelated stepping states.
- JIT memcheck register snapshots contained many `0xDEADBEEF` values. Future memory-breakpoint work should use PPSSPP interpreter mode (`launch-debug.bat`) for reliable registers/memchecks.

## Pending measured results

Input hashes, detected IDs, per-file diffs, font coverage, decrypted EBOOT
hashes, and verified runtime text/parser addresses will be appended by the pipeline/debugging tools as evidence is collected.
