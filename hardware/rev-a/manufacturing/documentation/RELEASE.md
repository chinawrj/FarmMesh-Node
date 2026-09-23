# FarmMesh Node A1 prototype release

**Status: GO FOR CONTROLLED A1 PROTOTYPE FABRICATION / 可受控工程原型投样。**

Release date: **2026-09-23**. KiCad **10.0.5**. The 100 × 100 mm, four-layer A1 board is fully routed and filled. This engineering release is bound to the following native PCB SHA-256:

```text
94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9
```

布线、铺铜、静态电气/制造检查、三项独立 AI 辅助工程会审及最终图纸目视核验已完成，未留有未处置的静态投样阻断。此状态只适用于所列哈希及一致的制造包；任何源文件、BOM 或几何修改都须重新核验和导出。

## Completed release gates / 已完成门槛

| Gate | Final evidence |
| --- | --- |
| Electrical rules | ERC **0** violations; `reports/erc.json` (package: `audit/erc.json`) |
| PCB rules and connectivity | DRC **0** violations, **0** unconnected items, **0** schematic-parity findings; `reports/drc.json` (package: `audit/drc.json`) |
| Independent geometry/connectivity checks | All **11** checks pass against the frozen PCB/netlist/library hashes; `reports/pcb-verification.json` (package: `audit/pcb-verification.json`) |
| Selected parts | **153** fitted components, including **147 SMD + 6 through-hole**; **11** bare-board test/mounting features excluded from assembly |
| Manufacturing outputs | **11 Gerber layers**, separate Excellon files containing **427 PTH holes/slots + 6 NPTH holes**, assembly BOM, accessory BOM, all/SMD placements and five review PDFs |
| Power review | [PASS on final native and actual Gerber/drill output](reports/a1-power-review.md) |
| RF/digital review | [GO for controlled engineering prototypes, with documented routing dispositions](reports/a1-rf-digital-review.md) |
| BOM/DFM review | [PASS on final native, actual fabrication data and source-hash closure](reports/a1-dfm-bom-review.md) |
| Visual review | Eight schematic pages, eleven layer pages, assembly drawing, two drill maps and actual Gerber/drill renderings inspected; `reports/a1-visual-review.md` (package: `review/evidence/reports/a1-visual-review.md`) |

The sealed archive is `FarmMesh-Node-A1-manufacturing.zip`, with external checksum `FarmMesh-Node-A1-manufacturing.zip.sha256`. Inside it, `manifest.json` records frozen-source and payload hashes; `SHA256SUMS` also hashes that manifest. `scripts/finalize_release.py --check-only` verifies the complete file set, individual bytes, ZIP CRC and external ZIP SHA-256. The archive hash is kept outside this document to avoid a circular hash dependency.

## Accepted prototype dispositions / 已接受的原型处置

- A_RX_D0 and A_RX_VALID have source-to-resistor detours; C_RX_D1 exceeds the review's placement attention threshold. Nine signal transitions have a nearest GND return farther than the 2 mm review heuristic. These are accepted for controlled bring-up with the specific waveform, clock-ramp and concurrent QSPI/radio tests in [FIRST-BOARD-TEST.md](FIRST-BOARD-TEST.md). They do not establish 50 Mbps timing.
- The ordinary double-sided via tenting process has three small positive hole-to-mask/paste margins of approximately 0.025, 0.028 and 0.040 mm. They have no nominal overlap but require targeted CAM and first-piece inspection. This release does not require or promise VIPPO, ink plugging or completely sealed holes. See [FABRICATION.md](FABRICATION.md) and the DFM review.
- Fabrication must preserve the specified JLC04161H-3313 construction, 1.6 mm thickness, ENIG, separate PTH/NPTH and USB 90 Ω differential ±10% requirement. Factory confirmation of actual stack-up, impedance, stencil and ordinary tenting is part of manufacturing execution. Unreviewed automatic CAM geometry changes are not covered by this release.

## Prototype boundary / 原型边界

Prototype-ready manufacturing means the design package is internally consistent and reviewed for first-board fabrication. It does not mean a physical board has been built or measured. Converter stability, thermal headroom, voltage droop, USB enumeration, PARLIO/PIO timing, RF isolation and sustained throughput require first-board testing. There is no on-board charger, PV input, USB power mode or battery ADC. No purchasing or manufacturing order is performed by this task.

可投样仅表示文件与设计审核完成；它不等于实物已验证。电源稳定性、温升、动态压降、USB、并行接口时序、射频隔离和持续吞吐量仍以首板实测为准。不包含充电、光伏输入、USB供电或电池ADC；本任务不采购、不下单。
