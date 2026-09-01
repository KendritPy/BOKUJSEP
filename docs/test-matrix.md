# Test matrix

## Automated tooling

- [x] WebSocket ticket/event interleaving preserves unsolicited broadcasts
- [x] Event waits preserve unrelated queued/socket messages
- [x] Temporary socket timeouts are restored after errors
- [x] Raw memory reads send `replacements=false` and validate length
- [x] PPSSPP 1.20.4 memory-breakpoint stepping payload is recognized
- [x] Newer enriched memory-breakpoint stepping payload is recognized
- [ ] Live PPSSPP 1.20.4 interpreter watch at `0x0892EBA4`
- [ ] Bootstrap verified from a clean Windows checkout

## Baseline

- [ ] Clean JP ISO reaches gameplay
- [ ] Spanish v1.0 ISO reaches gameplay
- [ ] Repeatable early-dialogue save backed up
- [ ] JP/ES canonical screenshots and raw records captured

## Language core

- [ ] Plugin loads only for UCJS10038
- [ ] Starts in JP
- [ ] Starts in ES
- [ ] JP -> ES
- [ ] ES -> JP
- [ ] 20 rapid alternating toggles

## Dialogue

- [ ] New line JP
- [ ] New line ES
- [ ] Current line live switch
- [ ] One/two/three-page lines
- [ ] Pause token and following dummy word
- [ ] Speaker and no-speaker lines
- [ ] Automatic/typewriter text
- [ ] Long Spanish text

## Game state and font

- [ ] Scene/area/day transitions
- [ ] Save/load/restart and same save in both languages
- [ ] Hiragana/katakana/kanji/Japanese punctuation
- [ ] áéíóú/ñ/¿¡

## Other coverage

- [ ] Menus, insects, diary, minigames
- [ ] Movies and Spanish-added subtitles
