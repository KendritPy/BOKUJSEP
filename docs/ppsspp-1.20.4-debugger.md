# PPSSPP 1.20.4 debugger compatibility

This document describes the Windows x64 1.20.4 binary used by BOKUJSEP. It is
based on the annotated `v1.20.4` tag, whose peeled commit is
`fa50bb1976065c4f8b1b47af227d367fe9771555` (2026-05-16).

The previously recorded snapshot
`56bba5f6f5e4ce5786f8528e73f2ece391fe34ea` is dated 2026-08-31. It is useful
for comparison, but it is not the source of the shipped 1.20.4 debugger.

## Corrections that affect BOKUJSEP

1. **There is no `cpu.breakpoint.hit` event in 1.20.4.** A CPU or memory
   breakpoint produces the ordinary unsolicited `cpu.stepping` broadcast.
   For a memcheck it includes:

   ```json
   {
     "event": "cpu.stepping",
     "pc": 142680000,
     "ticks": 123456,
     "reason": "memory.breakpoint",
     "relatedAddress": 143846308
   }
   ```

   `relatedAddress` is the configured memcheck start. The event has no access
   address, access size, source, or nested `hit` object. The later comparison
   commit enriches this same `cpu.stepping` event with `hit`; it still does not
   send a separate `cpu.breakpoint.hit` event.

2. **The desktop interpreter flag is `-i`.** `--cpu=interpreter` is not parsed
   by 1.20.4. `UI/NativeApp.cpp` maps `-i` to `CPUCore::INTERPRETER` (numeric
   config value 0) and disables saving that temporary choice.

3. **The broadcast configuration event is `broadcast.config.set`.** The old
   client sent nonexistent `client.config.set`. Stepping broadcasts are allowed
   by default, and the unified client now explicitly sends:

   ```json
   {"event":"broadcast.config.set","disallowed":{"stepping":false}}
   ```

4. **`change` is a modifier, not a write mode.** A write-on-change watch must
   specify both `write=true` and `change=true`. `change=true, write=false`
   creates a condition mask that is never selected by a write access.

## Protocol matrix

| Event | 1.20.4 behavior | BOKUJSEP rule | Source |
|---|---|---|---|
| `version` | Request/response; returns `PPSSPP_GIT_VERSION` | Send first and record returned version | `Core/Debugger/WebSocket/GameSubscriber.cpp` |
| `broadcast.config.set` | Controls `logger`, `game`, `stepping`, and `input` broadcasts per client | Keep `stepping` allowed | `ClientConfigSubscriber.cpp`, `WebSocket.cpp` |
| `client.config.set` | Unknown event | Never send | No handler in 1.20.4 |
| `game.status` | Returns game object and UI pause-menu state | Validate `UCJS10038`; do not use `paused` as CPU-step state | `GameSubscriber.cpp` |
| `cpu.status` | Returns `stepping`, UI-derived `paused`, `pc`, and `ticks` | `stepping` is the CPU-stop field; `paused` is not | `CPUCoreSubscriber.cpp` |
| `cpu.stepping` request | No direct response; calls `Core_Break()` | Send without ticket or wait for the broadcast separately | `CPUCoreSubscriber.cpp` |
| `cpu.stepping` broadcast | Reports stop PC, ticks, optional reason and related address | Match `reason` and `relatedAddress`; preserve interleaved events | `SteppingBroadcaster.cpp`, `Core/Core.cpp` |
| `cpu.resume` request | No direct response; fails if CPU is not stepping | Send without ticket; optionally wait for resume broadcast/status | `CPUCoreSubscriber.cpp` |
| `cpu.getAllRegs` | Returns categories, names, integer and float values | Capture only after a verified stop | `CPUCoreSubscriber.cpp` |
| `hle.func.list` | Lists active function symbols; CPU need only be active | Use to reject code ranges before arming | `HLESubscriber.cpp` |
| `hle.module.list` | Lists loaded modules and their ranges | Record module layout in every probe | `HLESubscriber.cpp` |
| `hle.backtrace` | Requires CPU stepping | Call immediately after verified hit | `HLESubscriber.cpp` |
| `memory.read` | Base64 bytes; `replacements` defaults to true | Always pass `replacements=false` for raw guest evidence | `MemorySubscriber.cpp` |
| `memory.search` | Not implemented | Use the client's chunked local fallback | No handler in 1.20.4 |
| `memory.disasm` | Returns analyzed lines and branch guides | Use at verified writer PC; `encoding` may reflect active JIT/replacements | `DisasmSubscriber.cpp` |
| `memory.breakpoint.*` | Add/update/remove/list memchecks | See exact semantics below | `BreakpointSubscriber.cpp` |
| `input.buttons.press` | Presses now and responds after release; accepts `note` | Ticketed request is safe; fire-and-forget is suitable for hotkey | `InputSubscriber.cpp` |
| `gpu.buffer.screenshot` | Returns PNG data URI by default | Pause first, capture, and resume in `finally` | `GPUBufferSubscriber.cpp` |

Paths in the table are under `Core/Debugger/WebSocket/` unless otherwise
qualified.

## Memory-breakpoint semantics

### Range and identity

The WebSocket API accepts `(address, size)` and converts it to an internal
half-open range `[address, address + size)`. An access matches when its interval
overlaps that range. `size=0` is a special exact-start form, not an unbounded
range.

Add replaces a memcheck with the same exact start and end. Update and remove
also identify a memcheck by that same exact pair, so removal must repeat the
original `address` and `size`.

Relevant source: `BreakpointSubscriber.cpp` parameter parsing and
`Core/Debugger/Breakpoints.cpp::GetMemCheckLocked()`.

### Flags and counters

The condition bits are:

```text
READ            0x01
WRITE           0x02
WRITE_ONCHANGE  0x04
```

`WRITE_ONCHANGE` does not imply `WRITE`. For BOKUJSEP writer probes the valid
combination is `read=false, write=true, change=true`.

`enabled` controls pausing and `log` controls PPSSPP logging. On add, both
default to true. `hits` increments only after the access type and optional
expression condition pass. `memory.breakpoint.list` exposes the counter, so a
probe should snapshot it both when armed and at the stop.

### Interpreter timing

The interpreter checks a memory instruction in
`Core/MIPS/MIPSTables.cpp::RunUntilWithChecks()` before calling its interpreter
implementation. If the memcheck pauses, it exits without executing the guest
instruction. Consequences:

- the broadcast/status PC is the writer instruction;
- registers are pre-instruction values;
- watched RAM is still the pre-store value at the stop;
- resuming uses PPSSPP's skip-first mechanism so the instruction can execute.

In 1.20.4 the interpreter calls `ExecMemCheck()`, which does not run
`OpWouldChangeMemory()`. Therefore `write+change` behaves as any matching write
in interpreter mode. This is noisier but is still the reliable choice for
identifying the writer.

### JIT timing and write-change

The native JIT inserts a memcheck call before the guest memory operation,
flushes relevant register-cache state, and exits the block when the memcheck
pauses. Its `ExecOpMemCheck()` path calls `OpWouldChangeMemory()` for
`write+change` and compares supported store values with current RAM. Unsupported
or uncertain store forms may conservatively count as a change.

JIT memchecks are implemented in 1.20.4, but the project has already observed
unhelpful `0xDEADBEEF` register values after JIT stops. Use interpreter mode for
writer attribution and JIT only when its change filtering has a clear measured
benefit.

### Broadcast timing

`SteppingBroadcaster` polls state and automatically emits `cpu.stepping` when
the stepping counter changes. The WebSocket loop polls at roughly 1 ms for a
short high-activity interval after a request, otherwise once per rendered
frame. Requests and broadcasts share the same connection and can interleave in
either order. A correct client must queue every nonmatching ticket/broadcast.

## Unified client guarantees

`tools/ppsspp_debug.py` is now the only WebSocket transport. It guarantees:

- unrelated broadcasts survive a ticketed `request()`;
- `wait_event()` searches queued messages before receiving;
- unmatched messages remain queued;
- temporary socket timeouts are restored on success and failure;
- raw reads default to `replacements=false` and validate decoded length;
- stepping broadcasts are explicitly enabled with the correct 1.20.4 event.

`tests/test_ppsspp_debug.py` and
`tests/test_dialogue_watch_event_probe.py` cover event/ticket interleaving,
queue preservation, timeout restoration, raw-memory reads, the exact 1.20.4
memcheck payload, and the newer enriched payload.

## Next runtime probe

The corrected sequence remains:

```text
launch-debug.bat       -> passes -i
probe-watch-glyph.bat  -> watches 0x0892EBA4, size 2
```

The probe must show the installed `write=true, change=true` memcheck. A valid
1.20.4 hit is a `cpu.stepping` event with:

```text
reason         memory.breakpoint
relatedAddress 0x0892EBA4
```

At that point capture PC, GPRs, backtrace, disassembly, module list and the
memcheck hit counter before resuming. Do not expect a nested `hit` object from
the 1.20.4 binary.
