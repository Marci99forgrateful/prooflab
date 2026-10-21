# Phase 6 measured results

1440 genuine searches on 48 frozen new statements in twelve families. Every verified success includes a fresh complete-proof Lean check and transitive axiom audit. All failures and unsolved statements are retained.

The learned hybrid changes verified success by **-2.083 percentage points** relative to the strongest Phase 4 expanded/P3 reference; paired theorem 95% interval **[-14.583, +10.417]**. This does not establish a positive success difference on this sample.
The learned-minus-deterministic contrast is **-10.417 pp**, interval **[-20.833, +0.000]**. Symbolic/candidate gains are not attributed automatically to learning.

| Policy | Verified runs | Theorem success % [95% interval] | Mean attempts/calls | Mean expansions | Wall s | Lean s | Retrieval s | Inference s | Resource limits | Execution errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| phase4 | 46/96 | 47.92 [+33.333, +62.500] | 165.60 | 20.75 | 5.328 | 1.675 | 0.000 | 0.061 | 22 | 0 |
| typed5 | 18/96 | 18.75 [+8.333, +31.250] | 536.33 | 45.69 | 7.510 | 4.143 | 1.683 | 0.266 | 78 | 0 |
| learned5 | 18/96 | 18.75 [+8.333, +31.250] | 537.15 | 45.65 | 7.471 | 4.077 | 1.663 | 0.319 | 78 | 0 |
| naive | 36/96 | 37.50 [+25.000, +52.083] | 398.85 | 30.10 | 7.696 | 4.057 | 1.320 | 0.189 | 60 | 0 |
| deterministic | 54/96 | 56.25 [+41.667, +70.833] | 238.75 | 33.56 | 6.884 | 3.046 | 1.289 | 0.090 | 34 | 0 |
| learned | 44/96 | 45.83 [+31.250, +60.417] | 198.35 | 29.88 | 6.325 | 2.608 | 0.914 | 0.125 | 32 | 0 |
| linear | 46/96 | 47.92 [+33.333, +62.500] | 256.83 | 41.81 | 7.260 | 3.455 | 1.184 | 0.177 | 50 | 0 |
| staged | 60/96 | 62.50 [+47.917, +75.000] | 205.33 | 30.25 | 6.483 | 2.418 | 0.849 | 0.080 | 28 | 0 |
| automation | 46/96 | 47.92 [+33.333, +62.500] | 1.00 external calls | opaque | 3.848 | 0.245 | 0.000 | 0.001 | 2 | 0 |
| grind | 52/96 | 54.17 [+39.583, +68.750] | 1.00 external calls | opaque | 3.634 | 0.025 | 0.000 | 0.001 | 0 | 0 |
| fixed | 27/48 | 56.25 [+41.667, +70.833] | 238.75 | 33.56 | 6.892 | 3.033 | 1.274 | 0.096 | 17 | 0 |
| no_synthesis | 21/48 | 43.75 [+29.167, +58.333] | 238.25 | 33.50 | 6.808 | 3.141 | 1.330 | 0.093 | 17 | 0 |
| applicability | 22/48 | 45.83 [+31.250, +60.417] | 198.35 | 29.88 | 6.263 | 2.609 | 0.909 | 0.127 | 16 | 0 |
| phase4_canonical | 23/48 | 47.92 [+33.333, +62.500] | 165.96 | 20.75 | 5.419 | 1.775 | 0.000 | 0.066 | 11 | 0 |
| phase4_small | 22/48 | 45.83 [+31.250, +60.417] | 91.44 | 12.35 | 4.352 | 0.943 | 0.000 | 0.035 | 12 | 0 |
| deterministic_small | 24/48 | 50.00 [+35.417, +64.583] | 121.92 | 17.40 | 5.357 | 1.624 | 0.628 | 0.047 | 20 | 0 |
| learned_small | 19/48 | 39.58 [+25.000, +54.167] | 104.81 | 16.02 | 4.798 | 1.395 | 0.486 | 0.066 | 19 | 0 |
| staged_small | 28/48 | 58.33 [+43.750, +72.917] | 111.29 | 16.60 | 5.301 | 1.411 | 0.457 | 0.045 | 16 | 0 |
| learned_seed1 | 20/48 | 41.67 [+27.083, +56.250] | 198.62 | 29.27 | 5.995 | 2.411 | 0.600 | 0.110 | 17 | 0 |
| learned_seed2 | 21/48 | 43.75 [+29.167, +58.333] | 212.23 | 31.25 | 6.483 | 2.868 | 1.081 | 0.126 | 19 | 0 |

Primary arms share 18 seconds, 600 attempts, eighty expansions, depth twelve, 24 candidates and two seconds per tactic/query. Smaller arms share 10 seconds, 240 attempts and forty expansions. Aesop/grind use one two-second external call; their work is not one elementary inference. Retrieval, Python inference and independent-audit wall count inside the shared outer budget. All-run effort mixes successes/failures and does not measure proof efficiency alone. Selected relevance is linear in both learned and fully linear controls; their controllers differ (boosted versus ridge). The applicability relevance ablation holds the selected controller fixed.

## Paired comparisons

| Left minus right | Success difference pp [theorem 95%] | Equal-family point pp [family interval] | Common-verified theorems | Common-success attempts difference [95%] |
|---|---:|---:|---:|---:|
| learned minus phase4 | -2.083 [-14.583, +10.417] | -2.083 [-18.750, +12.500] | 18 | +37.611 [+2.333, +91.611] |
| deterministic minus phase4 | +8.333 [-6.250, +22.917] | +8.333 [-12.500, +29.167] | 18 | +10.500 [+2.111, +24.444] |
| learned minus deterministic | -10.417 [-20.833, +0.000] | -10.417 [-20.833, +0.000] | 21 | +13.333 [-35.095, +67.286] |
| typed5 minus phase4 | -29.167 [-45.833, -12.500] | -29.167 [-50.000, -10.417] | 5 | +173.000 [+41.200, +304.800] |
| learned5 minus typed5 | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | 9 | +4.333 [+0.000, +9.222] |
| naive minus phase4 | -10.417 [-29.167, +8.333] | -10.417 [-37.500, +16.667] | 10 | +21.500 [+8.800, +36.300] |
| deterministic minus naive | +18.750 [+6.250, +31.250] | +18.750 [+4.167, +35.417] | 17 | -24.588 [-34.882, -14.824] |
| deterministic minus fixed | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | 27 | +0.000 [+0.000, +0.000] |
| deterministic minus no_synthesis | +12.500 [+4.167, +22.917] | +12.500 [+0.000, +25.000] | 21 | +0.286 [+0.048, +0.571] |
| learned minus linear | -2.083 [-12.500, +8.333] | -2.083 [-16.667, +14.583] | 19 | +13.368 [-42.158, +74.737] |
| learned minus applicability | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | 22 | +0.000 [+0.000, +0.000] |
| staged minus deterministic | +6.250 [+0.000, +14.583] | +6.250 [+0.000, +12.500] | 27 | -12.852 [-34.519, -0.556] |
| phase4_canonical minus phase4 | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | 23 | +0.739 [+0.217, +1.391] |
| automation minus phase4 | +0.000 [-18.750, +18.750] | +0.000 [-29.167, +29.167] | 13 | -62.538 [-108.615, -22.769] |
| grind minus phase4 | +6.250 [-8.333, +20.833] | +6.250 [-16.667, +29.167] | 18 | -82.500 [-121.722, -46.889] |
| learned_small minus phase4_small | -6.250 [-18.750, +6.250] | -6.250 [-25.000, +10.417] | 15 | +3.667 [+1.333, +7.000] |
| deterministic_small minus phase4_small | +4.167 [-10.417, +18.750] | +4.167 [-16.667, +25.000] | 16 | +4.312 [+1.750, +7.625] |
| staged_small minus phase4_small | +12.500 [+0.000, +27.083] | +12.500 [-6.250, +29.167] | 19 | +12.474 [+2.211, +25.789] |
| learned_seed1 minus learned | -4.167 [-10.417, +0.000] | -4.167 [-10.417, +0.000] | 20 | -29.950 [-77.800, +2.350] |
| learned_seed1 minus phase4 | -6.250 [-16.667, +4.167] | -6.250 [-22.917, +6.250] | 18 | +4.333 [+1.333, +8.056] |
| learned_seed2 minus learned | -2.083 [-6.250, +0.000] | -2.083 [-6.250, +0.000] | 21 | -3.000 [-7.762, +0.143] |
| learned_seed2 minus phase4 | -4.167 [-16.667, +8.333] | -4.167 [-20.833, +10.417] | 17 | +36.647 [+2.882, +85.235] |

10,000 paired bootstrap draws, seed 2718, on theorem averages across repeats. The family sensitivity is a different equal-family estimand; it is not another interval around the theorem-weighted point. Common-success comparisons condition on a potentially different subset for each contrast. Repetitions are execution-variability checks, not independent new theorems. Secondary contrasts are descriptive.

## Mathematical families

| Family | Expanded P3 | Typed 5 | Learned 5 | Deterministic | Learned | Staged | Aesop | grind |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| callable_composition | 2/8 | 4/8 | 4/8 | 6/8 | 4/8 | 6/8 | 8/8 | 2/8 |
| conjugation_commutator_words | 6/8 | 2/8 | 2/8 | 4/8 | 4/8 | 6/8 | 2/8 | 0/8 |
| dependent_function_graphs | 4/8 | 4/8 | 4/8 | 8/8 | 6/8 | 8/8 | 8/8 | 6/8 |
| image_preimage_composition | 4/8 | 2/8 | 2/8 | 4/8 | 2/8 | 4/8 | 4/8 | 8/8 |
| inverse_contextual_chain | 2/8 | 2/8 | 2/8 | 2/8 | 2/8 | 2/8 | 0/8 | 4/8 |
| lattice_mixed_intervals | 2/8 | 0/8 | 0/8 | 0/8 | 2/8 | 0/8 | 0/8 | 0/8 |
| noncommutative_context_systems | 2/8 | 2/8 | 2/8 | 4/8 | 4/8 | 6/8 | 0/8 | 0/8 |
| polynomial_constraint_systems | 8/8 | 2/8 | 2/8 | 8/8 | 8/8 | 8/8 | 0/8 | 8/8 |
| quantified_case_witness | 0/8 | 0/8 | 0/8 | 4/8 | 2/8 | 4/8 | 4/8 | 8/8 |
| relation_diamond_context | 8/8 | 0/8 | 0/8 | 8/8 | 8/8 | 8/8 | 6/8 | 8/8 |
| set_nested_partition | 6/8 | 0/8 | 0/8 | 0/8 | 0/8 | 2/8 | 6/8 | 6/8 |
| ternary_witness_pipeline | 2/8 | 0/8 | 0/8 | 6/8 | 2/8 | 6/8 | 8/8 | 2/8 |

## Applicability, selection and actual progress

| Policy | Potential / selected occurrences | Entered / displaced | Compatible accepted / rejected | Symbolic / hybrid / typed decisions |
|---|---:|---:|---:|---:|
| phase4 | 0 / 16250 | 0 / 0 | 0 / 0 | 0 / 0 / 0 |
| typed5 | 52280 / 52264 | 37668 / 0 | 37912 / 0 | 0 / 0 / 0 |
| learned5 | 52294 / 52278 | 37650 / 0 | 37946 / 0 | 0 / 0 / 0 |
| naive | 39418 / 39282 | 25246 / 0 | 25288 / 0 | 0 / 2890 / 0 |
| deterministic | 36730 / 23252 | 5118 / 0 | 5996 / 0 | 1376 / 1846 / 0 |
| learned | 31816 / 19362 | 3110 / 2 | 3618 / 0 | 1142 / 1724 / 2 |
| linear | 46750 / 24964 | 4404 / 0 | 4772 / 0 | 970 / 3044 / 0 |
| staged | 30830 / 20010 | 3462 / 0 | 3704 / 0 | 1426 / 1478 / 0 |
| automation | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 / 0 |
| grind | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 / 0 |
| fixed | 18365 / 11626 | 2559 / 0 | 2998 / 0 | 688 / 923 / 0 |
| no_synthesis | 18332 / 11593 | 2538 / 0 | 2977 / 0 | 685 / 923 / 0 |
| applicability | 15908 / 9681 | 1555 / 1 | 1809 / 0 | 571 / 862 / 1 |
| phase4_canonical | 0 / 8125 | 0 / 0 | 0 / 0 | 0 / 0 / 0 |
| phase4_small | 0 / 4570 | 0 / 0 | 0 / 0 | 0 / 0 / 0 |
| deterministic_small | 9314 / 6060 | 1262 / 0 | 1459 / 0 | 392 / 443 / 0 |
| learned_small | 8402 / 5178 | 851 / 1 | 966 / 0 | 323 / 445 / 1 |
| staged_small | 8251 / 5513 | 837 / 0 | 969 / 0 | 427 / 370 / 0 |
| learned_seed1 | 14288 / 9694 | 1210 / 1 | 1358 / 0 | 762 / 642 / 1 |
| learned_seed2 | 16384 / 10345 | 1664 / 1 | 2044 / 0 | 675 / 824 / 1 |

Native resource rejections are retained separately as `tactic_resource_failures` and probe errors as `retrieval_probe_errors` in summary observations; an exhausted tactic is not evidence of mathematical incompatibility. Potential occurrences here count the scored candidate pool, not every declaration probe; complete returned native rows, including incompatible proposals, remain in each raw query. Symbolic decisions have no invented typed availability. Compatibility is a proposal annotation, actual acceptance is a native event, and useful availability is witnessed only by complete audited paths at identical prefixes. `summary.json/availability` links those partial recall witnesses. `run-diagnostics.json.gz` retains every observed goal reduction, new metavariable count, actual status and verified-path flag; valid unproductive steps remain unknown as mathematical conclusions.

## Learning evidence

The development and final-test boundaries are distinct. There are 160 development tasks, 144 contributing tasks, 212 source states and 1964 pair preferences. Labels: `{'accepted_censored': 295, 'accepted_unknown': 1742, 'rejected_application': 579, 'tool_error_unknown': 3, 'verified_continuation': 538, 'verified_path': 12}`. Preference kinds: `{'verified_lower_continuation_cost': 484, 'verified_over_rejected': 1480}`.

Relevance validation winner: `{'configuration': {'l2': 0.01}, 'kind': 'linear', 'validation_loss': 0.4609121574200186}`. Selected selector: `{'nonlinear': True, 'validation_mse': 1.202459976567885}` from 347 verified matched fixed-mode costs. Censored/unknown costs were excluded rather than labelled mathematically wrong. The selector has success-conditioned missingness and root/continuation-policy distribution limitations. The fully linear control uses the same linear relevance and a ridge controller. The applicability control changes relevance while holding the selected controller fixed.

## Resource measurement scope

The full-call wall column includes provider/model/index setup and engine metadata work; engine elapsed_s separately measures search, native initialization, retrieval, inference, verification and cleanup. Archive I/O/interpreter startup are outside the solver call. Fixed artifact setup precedes the engine deadline. All comparable arms use the same engine budget and execute every tactic/query/branch within it. Inference timing includes P2/P3/P4 comparison annotations and explanations as well as new controller/relevance work, so it is not isolated new-model overhead.

Failed native queries are metered too. Missing interrupted native probe/heartbeat counts remain unknown; returned native counters are allocation observations, not primitive-inference totals. Session CPU/RSS exclude independent-audit process resources; total CPU is not claimed.

## Per-theorem primary outcomes

Each entry is verified repetitions / total. Exact attempts, expansions, wall, terminations, proofs and filenames are in `summary.json/per_theorem`; every single run is in `results.csv`.

| Theorem | Expanded | Typed 5 | Learned 5 | Deterministic | Learned | Staged | Aesop | grind |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| p6_test_callable_composition_01 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_callable_composition_02 | 0/2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 |
| p6_test_callable_composition_03 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 |
| p6_test_callable_composition_04 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| p6_test_conjugation_commutator_words_01 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 |
| p6_test_conjugation_commutator_words_02 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 0/2 |
| p6_test_conjugation_commutator_words_03 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_conjugation_commutator_words_04 | 2/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 | 0/2 |
| p6_test_dependent_function_graphs_01 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_dependent_function_graphs_02 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 | 2/2 |
| p6_test_dependent_function_graphs_03 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 |
| p6_test_dependent_function_graphs_04 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_image_preimage_composition_01 | 2/2 | 0/2 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 | 2/2 |
| p6_test_image_preimage_composition_02 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_image_preimage_composition_03 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 |
| p6_test_image_preimage_composition_04 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 |
| p6_test_inverse_contextual_chain_01 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 |
| p6_test_inverse_contextual_chain_02 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_inverse_contextual_chain_03 | 0/2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_inverse_contextual_chain_04 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 |
| p6_test_lattice_mixed_intervals_01 | 2/2 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 | 0/2 | 0/2 |
| p6_test_lattice_mixed_intervals_02 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_lattice_mixed_intervals_03 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_lattice_mixed_intervals_04 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_noncommutative_context_systems_01 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_noncommutative_context_systems_02 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 0/2 |
| p6_test_noncommutative_context_systems_03 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 0/2 |
| p6_test_noncommutative_context_systems_04 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 | 0/2 |
| p6_test_polynomial_constraint_systems_01 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 |
| p6_test_polynomial_constraint_systems_02 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 |
| p6_test_polynomial_constraint_systems_03 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 |
| p6_test_polynomial_constraint_systems_04 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 |
| p6_test_quantified_case_witness_01 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 | 2/2 |
| p6_test_quantified_case_witness_02 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 |
| p6_test_quantified_case_witness_03 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_quantified_case_witness_04 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 |
| p6_test_relation_diamond_context_01 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 |
| p6_test_relation_diamond_context_02 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_relation_diamond_context_03 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_relation_diamond_context_04 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| p6_test_set_nested_partition_01 | 2/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 |
| p6_test_set_nested_partition_02 | 2/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 |
| p6_test_set_nested_partition_03 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| p6_test_set_nested_partition_04 | 2/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 |
| p6_test_ternary_witness_pipeline_01 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| p6_test_ternary_witness_pipeline_02 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| p6_test_ternary_witness_pipeline_03 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 |
| p6_test_ternary_witness_pipeline_04 | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

## Resource and storage limitations

The lossless trace archive stores 4,414,981,360 original JSON bytes in 213,099,647 gzip bytes, with per-file raw/compressed SHA-256 hashes. Static replay reuses compressed archives; it does not commit another unpacked copy.

Linux live-session CPU and sum of process high-water RSS bounds are practical partial measurements; they exclude independent-audit CPU/RSS and are not simultaneous physical-memory peaks. End-to-end wall includes audit. Planning/inference/native interaction are overlapping measured categories and must not be summed as disjoint wall components. Shared-host timings, finite budgets and timeout variation limit interpretation. No pretrained model, hosted inference, paid AI API or GPU is used. Previous frozen data and measurements remain unchanged.
