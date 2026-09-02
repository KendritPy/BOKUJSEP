# Runtime addresses

No address is accepted without both a static signature and runtime evidence.

| Name | Address | Edition | Evidence | Confidence |
|---|---:|---|---|---:|
| Pending active dialogue reader | — | ES v1.0 | Awaiting canonical line memory search/read breakpoint | 0 |
| Pending textbox state | — | ES v1.0 | Awaiting visible-text redraw experiment | 0 |
| Pending font atlas/table pointers | — | JP/ES | Awaiting extracted asset and initialization comparison | 0 |

## Trace seeds and rejected identities

These addresses may be used to find code, but none is an accepted content
identity or hook:

| Address/range | Observed role | Status | Next use |
|---:|---|---|---|
| `0x0892EBA4` (2 bytes) | Stable within sampled textboxes and changed across lines | Rejected renderer geometry | Writer `0x088A0E4C` is `sh v1,0x174(v0)` in `z_un_088a0ccc`; transformed coordinate, not text identity |
| `0x08843070` / call at `0x08843074` | Spanish signature `move a0,s3; jal 0x08919BF0` | Best whole-stream candidate | Log-only execution probe captures `s3`, then dumps raw 16-bit words to `0x8000` |
| `0x08919BF0` | Spanish injected executable region | Raw-stream walker/count helper | Reads halfwords, handles `0x8000`; validate against two known dialogue lines before accepting hook boundary |
| `0x0892EBDC-0x0892EC33` | Rapidly changing repeated small 16-bit pairs | Renderer/time state | Do not use as dialogue identity |
| `0x0892EC00-0x0892EC33` | Writer backtrace reaches `sceKernelGetSystemTimeLow`; fired before user advance | Rejected identity | Historical evidence only |
| `0x0881Cxxx` cluster | Appeared only when debugger replacements were exposed | False candidate | Never reproduce with `replacements=true` |

Every report must record the game edition/hash, PPSSPP version, CPU core,
module map, raw bytes, and surrounding disassembly. Move an address into the
accepted table only after both a static signature and repeatable runtime role
are established.
