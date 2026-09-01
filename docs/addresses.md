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
| `0x0892EBA4` (2 bytes) | Stable within each sampled textbox; `0x0063` on A and `0x01C0` on B | Strong renderer/layout trace seed | Catch its writer in interpreter mode and trace backward |
| `0x0892EBDC-0x0892EC33` | Rapidly changing repeated small 16-bit pairs | Renderer/time state | Do not use as dialogue identity |
| `0x0892EC00-0x0892EC33` | Writer backtrace reaches `sceKernelGetSystemTimeLow`; fired before user advance | Rejected identity | Historical evidence only |
| `0x0881Cxxx` cluster | Appeared only when debugger replacements were exposed | False candidate | Never reproduce with `replacements=true` |

Every report must record the game edition/hash, PPSSPP version, CPU core,
module map, raw bytes, and surrounding disassembly. Move an address into the
accepted table only after both a static signature and repeatable runtime role
are established.
