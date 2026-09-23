# FarmMesh Node A1 package

Release authority/status: `documentation/RELEASE.md`. Sealing hashes does not approve fabrication.

- `gerber/`: 11 copper/mask/legend/paste/outline layers, with Gerber job file when emitted.
- `drill/`: separate PTH/NPTH Excellon files, drill report and two PDF drill maps.
- `assembly/BOM-assembly.csv`: 153 fitted components only. `placements-all.csv` has the same 153 references; `placements-smd.csv` contains 147 SMD components, including the hybrid USB connector. Read `placement-schema.json` before machine import.
- `assembly/BOM-accessories.csv`: eight separately selected antenna, cable and mating-harness part types with per-board quantities; these are not PCB placement rows.
- `review/`: PDFs generated from the frozen sources; explicit review evidence may be added during final sealing.
- `native/`: editable KiCad project, all eight schematics, local symbols/footprints/licenses, selected parts, engineering BOM, scripts and verification inputs. The engineering `native/BOM.csv` also lists 11 bare-board features; do not use it as the fitted assembly BOM.
- `audit/`: fresh ERC/DRC, prior independent verification bound to native hashes, and exact export commands.
- `documentation/`: manufacturing/first-board instructions and final review/status documents, mirrored into the native workspace for reproducibility.
- `manifest.json`: every payload SHA256 plus frozen source hashes. `SHA256SUMS` additionally hashes the manifest. The final ZIP checksum is external, avoiding self-referential hashes.

Reproduce with KiCad 10.0.5 (or re-review tool changes), the same library geometry and Python. In `native/`, regenerate `reports/netlist.xml`, run `scripts/verify_design.py` and `scripts/verify_pcb.py` using KiCad Python, then run `python3 scripts/export_manufacturing.py`. Review the new outputs, document authorized status separately, then run `python3 scripts/finalize_release.py` and `python3 scripts/finalize_release.py --check-only`. A changed native/BOM/parts/script hash requires a new export. CAD-generated timestamps can change a fresh export; sealing an unchanged payload produces a deterministic ZIP.
