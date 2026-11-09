<!-- SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Readable Roadmap: Validating display names without changing task identity

KC-Brain inspected the actual failed CI run 42603665195 for PR26 head 07f94c528eb06f2069527f9f99f527e751d2e0c5. The build and publication/link checks succeeded at the old source pins, as did 14 renderer,124 rendition and32 legacy roadmap tests. The real-readable-source test failed because check_graph rejected the two already accepted fields display_name and display_name_ru. The source test is retained, not skipped to hide the failure.

This correction accepts precisely those two optional presentation fields. Legacy graphs retain neither. Readable graphs require both on every node, plain-text one-to-three-word labels, uniqueness per language and agreement between the English short card name and graph name. Unknown fields, execution state, dates, malformed names, cycles, missing nodes and dangling or duplicate required links remain errors. Stable ids, priorities, owners, graph edges and planned-only output semantics are unchanged. The compiler adds no task, source admission or execution authority.

Actual local verification: Python3.13.5, existing test_roadmap_names command,39 tests collected,38 passed and one skipped because an actual pinned source checkout was not locally available. The16 new focused methods are included in that existing CI command. No hosted positive result or full-site rebuild is claimed before the new run is observed. The immutable source test still runs in hosted CI against its checked-out publication source and now also compares card and graph names.

Local copies of the three original scripts were reconstructed from connector reads and verified against original Git blob ids before edits: roadmap.py794070253b36809f79c621506571039bd4c84442; roadmap_names.py6ba82856b0689b72f62c376851c5782e9a2aa94c; test_roadmap_names.pye1f7b3e1be736b3ab479889cb8dceab37f913cbf. This is original compatibility code and finite synthetic testing, not independent scientific review. No manifest pin, generated page, deployed site or server index is changed by this patch.
