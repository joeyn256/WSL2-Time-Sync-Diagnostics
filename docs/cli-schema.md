# CLI and schema reference

This is the maintained v0.6.0 reference for the read-only guest acquisition, offline interval analysis, kernel-state observation, and method-aware comparison introduced through [issue #2](https://github.com/joeyn256/WSL2-Time-Sync-Diagnostics/issues/2). Runtime dependencies remain standard-library-only. Package-release numbers and schema/method version numbers are independent: `schema_version: 2` and `fixed_window_interval_v2` remain the public data/method identifiers while the package is still pre-1.0.

## Commands and defaults

Every command emits JSON to stdout unless `--output PATH` is supplied; with that flag it writes JSON and prints the path. A completed observation, including an anomaly or unavailable state, exits 0. Invalid options/input or a file I/O error exits 2; classifications must be read from the JSON.

| Command | Options and defaults |
|---|---|
| `diagnose` | Existing environment inventory plus an additive `adjtimex` snapshot; `--output`. |
| `probe` | `--duration 30`, `--cadence 1`, `--output`; seconds. |
| `analyze INPUT` | `--window 10` seconds, `--rate-band-ppm 100`, `--event-threshold-ns 500000000`, `--output`. |
| `settle-check` | `--duration 30`, `--cadence 1`, `--expected-tick 10000`, `--max-abs-freq-ppm 100`, `--required-consecutive 3`, `--output`. |
| `compare LEFT RIGHT` | Compare analysis JSON files; `--output`. |
| `python-check` | Existing `--requirements` and `--output` behavior. |

These bands are example settings. Choose settings appropriate to the question and retain them with the result. Analysis window length must be finite and at least one nanosecond; the rate band must be finite and nonnegative, and the event band is a nonnegative integer number of nanoseconds. Requests requiring more than 100,000 analysis windows are rejected.

```bash
wsl-time-sync diagnose --output diagnose.json
wsl-time-sync probe --duration 60 --cadence 1 --output probe.json
wsl-time-sync analyze probe.json --window 10 --rate-band-ppm 100 --output analysis.json
wsl-time-sync settle-check --duration 30 --cadence 1 --output kernel-observation.json
wsl-time-sync compare analysis-before.json analysis-after.json --output comparison.json
```

## Probe schema 2

Top-level fields include:

- `schema_version: 2`, `mode: "read_only"`;
- `acquisition: "raw_bracket_v1"`;
- `reference: "CLOCK_MONOTONIC_RAW"`;
- `clock_pair: "CLOCK_MONOTONIC/CLOCK_MONOTONIC_RAW"`;
- `duration_requested_s`, `cadence_requested_s`, `started_wall_ns`;
- `elapsed_observation_ns`, `observation_clock: "perf_counter_ns"`, `observations_planned`, `collection_complete`, and `collection_errors`;
- `schedule`, `continuity_label`, `samples`, and explanatory `notes`.

Each sample contains `index`, `raw_before_ns`, `realtime_ns`, `monotonic_ns`, `boottime_ns`, `raw_after_ns`, `bracket_width_ns`, `target_raw_ns`, `schedule_lateness_ns`, `observation_elapsed_ns`, and `errors`. Timestamp values are integer nanoseconds when available. Unavailable reads are `null`, with field-specific messages in `errors`. Bracket width is `raw_after_ns - raw_before_ns`; a reversed bracket is retained with an error.

Acquisition follows RAW-before → REALTIME → MONOTONIC → optional BOOTTIME → RAW-after. There is no substituted RAW reference and no Windows QPC channel. Schema 2 replaces the old sample's single `monotonic_raw_ns` and `perf_counter_ns` fields. Existing v0.1 files remain valid analyzer inputs.

The `schedule` uses `method: "raw_origin_v1"` and `clock: "CLOCK_MONOTONIC_RAW"`. Its `origin_raw_ns` is the first sample's valid RAW-before timestamp. For sample index `i`, `target_raw_ns = origin_raw_ns + min(i * cadence_ns, duration_ns)`. The terminal target therefore covers the requested duration in the same RAW reference used by analysis, including when cadence exceeds duration. Each sample preserves its actual lateness (`raw_before_ns - target_raw_ns`) and elapsed observation time.

The guard uses `guard_clock: "perf_counter_ns"`, with `guard_budget_ns = duration_ns + max(1_000_000_000, duration_ns // 10)` measured from before the initial acquisition, and `max_wait_iterations_per_target: 64`. These limits bound waits without replacing RAW with the guard clock. Unavailable or regressing RAW, an exhausted guard or wait limit, or an acquisition that reaches the next cadence target before finishing leaves `collection_complete: false` and explicit `collection_errors`. Missed targets are not filled by compressed catch-up reads. Scheduler or clock-read delays can overrun the guard; actual elapsed time is retained, and completion verification rejects an over-budget capture.

Duration is positive and at most 86,400 seconds; cadence is positive, and at most 100,000 observations may be planned. Both durations and cadences must represent at least one nanosecond. An exceptionally short or failed capture can contain fewer than two samples; `analyze` rejects that input explicitly rather than reporting a successful observation.

## Analysis schema 2

Both legacy v0.1 and current schema-v2 probe inputs produce `schema_version: 2` reports, with `source_schema_version` retained. The top-level `method` records acquisition, reference, clock pair, `analysis: "fixed_window_interval_v2"`, and uncertainty method. `settings` records the three analysis options and the requested capture duration/cadence when supplied. `coverage` records sample validity and complete, partial, and invalid windows, observed RAW duration, requested RAW-duration coverage/fraction, explicit capture completion, verified completion/count consistency (`collection_completion_verified`, `observations_planned`, `observations_expected_from_schedule`), and guard-clock elapsed time when available.

`full_run` and each `windows` entry include:

- `monotonic_vs_raw_ppm`: descriptive point estimate retained for legacy consumers;
- `raw_duration_ns`, `raw_duration_interval_ns`, and `rate_interval_ppm`;
- `classification`, `complete`, and `issues`.

Window entries also preserve nominal start/end timestamps, selected sample positions/indices, sample count, endpoint displacement, and partial/boundary-coverage flags. Fixed windows retain early adverse results even when the full-run estimate improves. Rate enclosures use actual endpoint spans; see [methodology](methodology.md) for arithmetic and boundary selection. A closing sample's overshoot does not generate a duplicate zero-span partial tail. A genuine partial tail with a distinct later endpoint remains indeterminate.

Schema-2 completion verification requires the requested duration/cadence, RAW-origin schedule and guard context, an empty `collection_errors` list, consistent planned/actual counts, sequential zero-based indexes, and consistent per-sample targets, lateness, and elapsed times. Samples must reach their targets without missing the next target, and observed RAW-before duration must cover the requested duration. A `collection_complete: true` claim never overrides `requested_raw_duration_shortfall` or contradictory/missing context. Earlier schema-2 captures remain readable, but missing the corrected schedule context prevents verified completion and aggregate `WITHIN`.

For `full_run`, `span_complete` describes valid observed span geometry and `acquisition_complete` records verified requested-acquisition completion; `complete` requires both. Its rate `classification` still describes the observed span, so a locally established `OUTSIDE` result remains visible on an incomplete capture. Read aggregate classification and coverage to assess the requested observation as a whole.

The rate band is inclusive: a wholly enclosed interval is `WITHIN`, an interval wholly beyond either boundary is `OUTSIDE`, and an overlap or unavailable enclosure is `INDETERMINATE`. The report never uses its point estimate to classify an interval. Rate-boundary decisions use exact rational arithmetic with decimal settings; serialized bounds round outward, so their displayed precision does not override the classification.

`realtime_events` records adjacent-sample signed REALTIME-minus-RAW change enclosures, directions, classifications, issues, and backward-read indicators. The event setting defines an inclusive symmetric change band; an event is `OUTSIDE` only when its entire enclosure exceeds that band. `realtime_backward_events` and `large_realtime_minus_raw_changes` remain available. The raw backward-read count remains visible even when sample order is invalid; only a valid ordered pair can make that diagnostic an aggregate anomaly.

Each valid complete fixed window also reports `realtime_offset_change_interval_ns`, `realtime_offset_classification`, and `realtime_offset_direction`: cumulative REALTIME-minus-RAW change between its bracketed endpoints, using the same configured event band. Positive, negative, and boundary-straddling enclosures retain their direction and uncertainty. Invalid or partial windows leave this evidence unavailable/indeterminate. `outside_realtime_offset_windows` counts the outside-band cumulative windows. `full_run.realtime_offset_change_interval_ns` and `realtime_offset_direction` describe the cumulative change over the observed full span without thresholding an arbitrarily long run as one event.

The aggregate classification preserves an observed outside-band rate window, adjacent event, fixed-window cumulative change, or a backward REALTIME read in a valid ordered pair. A within result requires complete, bounded, within-band evidence for rates and both REALTIME checks; otherwise it is indeterminate. Legacy unbracketed inputs retain descriptive endpoint estimates, but cannot establish a bounded `WITHIN` result. Missing, duplicate, malformed, or nonincreasing samples remain explicit validity/coverage issues.

## Kernel observation

`diagnose` retains schema 1 and adds `adjtimex`. The reader calls libc only after validating Linux x86-64 LP64 little-endian platform/type sizes, alignments, complete field offsets, and structure sizes (`timex` 208 bytes, `timeval` 16 bytes). The layout and field interpretation follow the [Linux UAPI header](https://github.com/torvalds/linux/blob/master/include/uapi/linux/timex.h) and [adjtimex manual](https://man7.org/linux/man-pages/man2/adjtimex.2.html). Other environments return `available: false` and `unavailable_reason: "unsupported_abi"`.

A snapshot includes `mode: "read_only"`, `modes: 0`, `abi`, `available`, `raw`, `freq_ppm`, `return_state`, and interpretation notes. Successful snapshots add `units`. `raw` preserves scalar timex fields, including `tick`, `freq`, `status`, `maxerror`, `esterror`, and nested `time`. Interface/read errors return structured unavailability; they do not become zero-valued state.

`freq_ppm = freq / 65536`. `tick`, `maxerror`, `esterror`, and `precision` use microseconds. `offset`, `jitter`, and `time.tv_usec` are interpreted using `STA_NANO`; the historical field name `tv_usec` is retained even when its unit is nanoseconds. A successful `TIME_ERROR` return is recorded as a kernel time state, distinct from a failed syscall.

## Finite settling observation

`settle-check` produces schema 2 with `method: "adjtimex_modes0_finite_observation"`. It repeatedly observes kernel state; it does not run bracketed rate analysis.

The default named policy is `historical_example_tick10000_freq100ppm`. Its condition is `tick == 10000` and `abs(freq / 65536) < 100`; the frequency boundary is **strict**. Changing those values selects `configured_tick_frequency_band`. The report carries all policy settings and each reading's classification.

- `ANOMALY_OBSERVED`: at least one usable reading violates the configured tick/frequency policy; later nominal or missing readings do not erase it.
- `WITHIN_CONFIGURED_BAND`: all scheduled readings were collected and usable, all met the policy, and the required consecutive count was reached.
- `INDETERMINATE`: missing/malformed data, an incomplete scheduled series, or too few consecutive readings, without an observed policy anomaly.

Capture duration is positive and at most 86,400 seconds; at most 100,000 readings may be planned. Cadence is positive, with durations/cadences of at least one nanosecond. The required consecutive count is at least two. The report preserves requested duration/cadence, elapsed time, planned/collected counts, completeness, and each read's before/after elapsed timestamps. A delayed read can overrun the scheduled deadline; there is no retry-until-success loop.

These outcomes concern sampled tick/frequency fields only. Other fields, including kernel error/status state, are preserved for interpretation but are not part of this example predicate. Neither one snapshot nor repeated policy matches proves a pending slew is absent or certifies a benchmark.

## Comparison schema 2

`compare` emits `comparability` as `COMPARABLE`, `DIFFERENT_METHOD`, or `INSUFFICIENT_CONTEXT`, with `differences`, `missing_context`, and both source contexts. It checks schema, known acquisition/reference/clock-pair and analysis/uncertainty vocabulary, settings, and coverage before emitting a numerical difference. Both `fixed_window_interval_v1` and `fixed_window_interval_v2` are recognized, but comparing different analysis methods produces `DIFFERENT_METHOD`. Matching invented method strings cannot establish comparability.

Each report must supply a finite full-run point estimate and finite positive `raw_duration_ns`; bounded RAW-bracket reports also require a finite ordered `rate_interval_ppm` and a finite ordered positive `raw_duration_interval_ns`. Optional enclosures on legacy reports must also be valid when present. Non-finite or unrepresentable differences are insufficient evidence for comparison. Missing or invalid required evidence produces `INSUFFICIENT_CONTEXT` unless recorded method/settings/coverage differences already require `DIFFERENT_METHOD`. When requested duration/cadence are present, different values are method differences and one-sided availability is insufficient context; both absent remain acceptable for legacy/synthetic contexts. Exact observed durations need not match, because normal scheduling jitter can differ.

`continuity_label` is optional caller-supplied acquisition context; the probe emits `null`. Different supplied labels produce `DIFFERENT_METHOD`, and a label on only one side produces `INSUFFICIENT_CONTEXT`. It is not a boot identifier, and equality does not establish guest or host boot continuity.

`difference_ppm` is right minus left and remains a descriptive point estimate. For comparable bracketed reports, `difference_interval_ppm` encloses that difference using both intervals. On method mismatch or insufficient context, both difference fields remain `null`. Original sample counts and point estimates remain visible for inspection. `left_classification` and `right_classification` retain the aggregate results, while `left_anomaly_counts` and `right_anomaly_counts` expose outside rate windows, cumulative REALTIME windows, adjacent events, and backward reads; unavailable counts are `null`. A numerically comparable report can still be `OUTSIDE`; comparability does not erase its observed anomalies.

An old v0.1 analysis report has no full method/coverage context and is insufficient for direct method-aware comparison. Re-analyzing its original probe file supplies the explicit legacy method; it still does not manufacture acquisition uncertainty bounds. Comparable methods do not establish matched host conditions or a distro ranking.

## Synthetic scope and provenance

Regression inputs are parameterized constructions, including nominal guest-relative behavior, early slew followed by normal-looking windows, periodic sawtooth changes, positive/negative steps, backward REALTIME, missing/duplicate samples, threshold straddles, common-mode guest behavior, and nominal/non-nominal kernel examples. Scheduled synthetic fixtures carry internally consistent acquisition metadata, and scheduler tests drive actual acquisition with controlled clock origins, rates, delays, and failures. Their historical shape names are explanatory labels. No raw private evidence bytes or historical controllers are included.

Small mathematical and acquisition ideas were informed by the historical reuse audit: RAW brackets, elapsed-time enclosures, fixed boundaries, and uncertainty-preserving classifications. Kernel layout handling follows the public Linux interface. The implementation excludes host transport, service changes, elevation, firewall logic, and administrative/session machinery.
