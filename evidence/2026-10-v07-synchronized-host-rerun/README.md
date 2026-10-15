# v0.7 synchronized-host rerun — public evidence index

This directory records the **public boundary** of the v0.7 synchronized-host effort.

No synchronized-host Ubuntu scientific run was launched on the investigated host. The Windows host failed the frozen synchronization/admission prerequisite, so infrastructure attempts are not presented as guest scientific measurements.

## Terminal state

```text
FINAL_W32TIME_CORRECTION_FAILED — RESTORATION_PROVEN
```

Scientific accounting at closure:

```text
launches = 0 / 8
unknown = 0
replacements = 0 / 2
Seq 2 = absent
formal host-admission observation = UNUSED
```

## Final plain-resync attempt

The last bounded attempt:

- captured `MaxAllowedPhaseOffset` as DWORD 1;
- temporarily set only that value to DWORD 0;
- applied one temporary `w32tm /config /update`;
- dispatched exactly one plain `w32tm /resync`;
- received explicit `no time data was available` output despite process exit 0;
- observed a contemporaneous ~-0.121 s clock step and Windows Time events indicating valid time data/synchronization activity;
- treated those events as corroborating state, not as permission to override the explicit failure;
- restored the original DWORD 1;
- independently verified restoration;
- did not run the triage screen;
- did not invoke formal host admission;
- did not open Seq 2 or launch Ubuntu scientifically.

## Private-evidence digests retained by the project owner

| Evidence | SHA-256 |
|---|---|
| Executor return report | `1057bf28fcac9a8c90662aea454900e3bb15bc85750ed0daaaa37f673bc74728` |
| Final disposition | `5c326d84115775a5072ef4bbedc9412766dcad1560d3c7436b5f977712861838` |
| Recovery | `4d236a9ba2bdba425c2ef6f325fd7c850bfc5d33bec02fa105c291c09da4c20d` |
| Restoration verifier | `c2a858c8fc9460eb5df32e89c9612b4713a55c0c518f09453cc63d620f75b1e9` |
| Event/final-state addendum | `a121586acdfaf81d38bd5fe30af18eaadc9a6802257e28046adc1ec6140b7e8d` |

The underlying private evidence is intentionally not mirrored here because it contains host-specific operational paths and execution-control material.

See [the v0.7 closure report](../../docs/v0.7-synchronized-host-rerun.md) for interpretation and limitations.
