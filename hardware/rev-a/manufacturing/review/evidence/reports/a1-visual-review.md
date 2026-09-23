# A1 final visual and artifact review

Date: **2026-09-23**. **PASS for controlled A1 prototype fabrication.** This record covers the frozen native PCB and the final export batch, after the last J2 GND via correction. It is an AI-assisted drawing review supported by independent numeric comparison, not a claim of manufactured-board inspection.

PCB SHA-256: `94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9`.

## Inspected drawings and actual fabrication layers

- **Eight schematic pages:** hierarchy, power, RP2350, radios A/B/C, USB and test/mechanical. Reviewed full pages and dense circuit crops. USB C126/title-block interference and U104 field/body interference were corrected before the frozen export. A1 revision, page borders, pin/net labels and component fields remain legible; no clipping or new overlap was identified in the final drawings.
- **Eleven native-layer PDF pages:** F.Cu, In1.Cu, In2.Cu, B.Cu, F.Mask, B.Mask, F.Silkscreen, B.Silkscreen, F.Paste, B.Paste and Edge.Cuts. The two internal GND planes, intentional LX void, supply branches, signal routing, module ground, EP apertures and mechanical outline agree with the reviewed PCB. The layer PDF uses 1:1 placement on A4 landscape; surrounding white space is intentional.
- **Assembly top PDF:** black-on-white F.Fab, F.CrtYd and outline at 2:1. Reference text, pin-1 chamfers, capacitor polarity and connector outlines were inspected. Pad-number overlays and black drill marks that obscured references were removed from this drawing. Use the placement CSV for machine coordinates; this drawing is not a placement-coordinate conversion.
- **Separate PTH and NPTH map PDFs:** map legends, tool diameters, hole symbols, USB shell slots and four mounting holes inspected. PTH map records 155×0.20, 8×0.25, 233×0.30, 25×1.00, 2×1.70 mm circular holes plus four 0.60 mm slots (427 objects). NPTH map records two 0.65 mm USB locating holes and four 3.20 mm mounting holes (6 objects). Map/table layout is unclipped and readable.
- **Actual fabrication data:** all 11 Gerbers and both Excellon files parsed and rendered independently using gerbonara 1.6.3 / PyMuPDF 1.28.2. Individual layers, a whole-board paste/drill overlay and power/USB/EP crops were inspected. B.Paste and B.Silkscreen Gerbers are intentionally empty because all components and legend are on top; native-layer PDFs may still show hole marks. Edge.Cuts centre lines form 100.00×100.00 mm; the 100.05 mm plotted stroke bounding box is not a change of board size.

The power reviewer independently checked final copper, EP bridges, peripheral holes and both GND planes in actual Gerbers. The BOM/DFM reviewer compared every drill/slot and all placement rows against native geometry and checked actual aperture-to-hole distances. Their signed reports bind the same PCB SHA. The J2 corrected hole has 0.25 mm clearance from its adjacent mask opening; no old hole remains. The small positive C9/C5/J1 mask/paste margins remain documented process inspection points, not unreported nominal collisions.

## Byte-level binding

`a1-visual-review.json` records the five PDF hashes and their **22 pages**. The following PDF files are relative to the manufacturing directory:

| PDF | Pages | SHA-256 |
| --- | ---: | --- |
| `assembly/assembly-top.pdf` | 1 | `c04a042f8e78a04d16a9fdb229817e2fee73d63460d02b508e442c02c7551f56` |
| `drill/FarmMesh-Node-NPTH-drl_map.pdf` | 1 | `84eeb3dbee1d99c60d84002b8f43f89835599fa3b3fe27506ed15eb28a09816a` |
| `drill/FarmMesh-Node-PTH-drl_map.pdf` | 1 | `eeb676f8588073c070e1b07bb4f59805782da8d83d67bdb93ceb01ecc86a312c` |
| `review/FarmMesh-Node-A1-layers.pdf` | 11 | `bd471e7db77bc61a662f03485c131455b3cad9d35ada366ee70ad5fe4c25d258` |
| `review/FarmMesh-Node-A1.pdf` | 8 | `bcd6535ca11eea474bb898c9616155a8a5e4b6c48af0084b56e28cb095b480f8` |

`review/gerber/render-manifest.json` SHA-256: `321257ff7851ca2e0f5fdc9abaaaf83bd13e512c23543d28fce0b9004fea47b3`. Every listed input Gerber/drill hash and every generated PNG/SVG hash was rechecked against the final files. The manifest's renderer-only status means images require inspection; this signed review records that inspection without changing the renderer's original output. The package includes the render manifest and rendered evidence under `review/evidence/`.

## Rule-check scope

The zero ERC/DRC counts apply to the recorded project rule severities. The exported JSON retains the disabled categories: ERC `single_global_label`, `four_way_junction`, `simulation_model_issue`, `footprint_filter`; DRC `missing_courtyard`, `track_not_centered_on_via`, `tuning_profile_track_geometries`, `footprint_filters_mismatch`, `footprint_type_mismatch`. There are no per-item DRC exclusions. Electrical connectivity, copper/holes/clearances, courtyard overlap and silkscreen checks remain active; pad geometry, selected package identity and assembly type are additionally covered by the independent verifier and DFM review. A zero count is not a claim that disabled advisory categories were run.

## Disposition and limits

No unresolved visual/artifact mismatch blocks this controlled prototype. Final sealing must preserve the frozen native sources, refresh the final release/review documents, and pass `finalize_release.py --check-only` before distribution. The authoritative status is RELEASE.md; archive hashes remain external to avoid self-reference. Converter loop/thermal behavior, USB power sequencing, signal timing, RF operation and assembly yield remain first-board work. No purchase or manufacturing order was placed.
