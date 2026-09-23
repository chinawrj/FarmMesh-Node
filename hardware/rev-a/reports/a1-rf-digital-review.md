# A1 RF / digital review — final routed prototype

Review date: **2026-09-23**. Independent AI-assisted engineering review of the actual routed, filled A1 PCB, manifest/netlist, library pads and official device/reference-board documents. Reviewed PCB SHA-256:

`94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9`

This final snapshot includes the J2 GND via move from (98.00,26.54) to (98.25,26.54) mm to separate its drill from the adjacent connector's mask opening. Signal routing and the reviewed inner-plane return topology are unchanged. Fresh DRC and all 11 automatic checks pass for the hash above.

**Disposition: GO for controlled A1 engineering prototypes.** No unresolved RF/digital layout blocker is identified for this snapshot. The source-route and return-via deviations below are explicitly accepted for prototype investigation. This is not approval of 50 Mbps timing, RF throughput, production yield or regulatory compliance. Firmware, SI measurements, reset behavior, RF coexistence and thermal performance remain unvalidated. Manufacturing/assembly acceptance is also governed by [FABRICATION.md](../FABRICATION.md), [the DFM review](a1-dfm-bom-review.md) and [the power review](a1-power-review.md).

This report supersedes the earlier pre-layout recommendations: **In1.Cu and In2.Cu are both GND; the C5 EP gap vias were removed; the complete routed PCB is now reviewed.** The former In2 power/signal proposal and internal EP gap-via proposal are historical, not manufacturing instructions.

## Evidence and automatic checks

`pcb-verification.json` (package: `audit/pcb-verification.json`) records the exact PCB/manifest/XML/library hashes and passes all 11 automated checks. The verifier does not alter or refill its input board. `drc.json` (package: `audit/drc.json`) reports 0 violations, 0 unconnected items and 0 schematic-parity findings; `erc.json` (package: `audit/erc.json`) reports 0 violations. These are design-tool results, not assembled-board tests.

| Check on final copper | Result and interpretation |
| --- | --- |
| Inventory, electrical assignments and library geometry | 164 front-side footprints; 640 pad regions across 27 library types. Local position, angle, size, shape, drill, layers and pad overrides match the assigned libraries, including PowerDI3333 custom-pad geometry. All 566 unique numbered pads / 609 numbered physical lands match the XML and manifest topology; 44 no-connect nodes remain isolated. |
| Paste / exposed pads | All **396 via drills** checked against **597 F/B paste apertures**: no collision. The RP, LTC3119 and three C5 EP bounding envelopes also contain no holes. Component PTH/NPTH drills are excluded from the global via-in-paste check. |
| Ground reference layers | No tracks/arcs on In1.Cu or In2.Cu. Each saved GND fill has one connected polygon; areas are 9664.725 and 9672.906 mm², respectively (97.8175% / 97.9003% of their 9880.36 mm² outline). Local clearance holes and the intentional LX cutout remain. Polygon connectivity alone does not prove every return-path neck or RF behavior. |
| RP LX exception | Full F.Cu LX copper, including U101 pad 63 and its neck, projects **0 mm²** onto actual In1 copper. This uses Boolean geometry of zones, tracks, vias and pads, not only keepout bounds. |
| USB straight coupled trunk | F.Cu x=50.000 / 50.358 mm, common y=25.950–40.048 mm: **W=0.158 mm, edge gap=0.200 mm, common length=14.098 mm**. Its complete rectangular projection has no missing GND below it on either inner layer. Connector, ESD, switch, crossover and resistor escapes are not claimed to have that same impedance. |
| Link source resistors | All 36 × 22 Ω resistors are on their intended driver side. All C5-driven source tails have 0 signal vias; C5 clock/control tails are approximately 2.03–2.12 mm of copper. The longer RP-driven tails are listed below. |

## RP core, flash and crystal

The core buck uses the RP internal regulator, the selected direction-marked Abracon inductor and 0402 R101/C101–C103. The local input, output, LX and high-current ground copper is adapted from the official **RP2350B Minimal R4 / schematic S1** reference. The source front-layer central 1V1 distribution was changed to a small B.Cu distribution region so the target EP retains solid top GND; this is an adaptation, not a claim of an identical reference PCB.

The high-current ground has adjacent 0.60/0.25 mm vias at (54.1,43.25) and (54.1,43.85). CFILT/C101 has its own short ground return. The RP EP connects to top GND and eight perimeter vias outside its paste/EP envelope; the reference's nine internal plated pads are not treated as a mandatory via count. The final In1 LX cutout includes the neck through y=45.65 mm. Its predecessor stopped at y=43.2 and left 0.427187 mm² of GND under LX; that finding is closed in the reviewed board.

These choices follow [RP2350 datasheet §6.3.8, printed pp.454–455 / Fig.24](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=456): compact switching loops, adjacent high-current ground vias, a separate filtered-supply return and clearance immediately below LX on multilayer boards. The [RP hardware guide, pp.5–8](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008280-DS-2-hardware-design-with-rp2350.pdf) explains the component/orientation sensitivity. Actual regulator transient/thermal behavior is still a first-board gate.

**QSPI:** all six nets use F.Cu and zero vias. There are no optional bottom-flash branches, and CS is connected across the absent reference 0 Ω selection position. Total copper lengths are IO0 7.158, CLK 8.920, IO3 10.432, IO2 13.186 and IO1 17.338 mm. CS totals 30.295 mm including its pull-up/BOOTSEL branches, so that figure is not a single end-to-end flight length. The broader flash/escape corridor contains unrelated A-link routing, including a short passage under U102's body; it does not cross the QSPI copper electrically. This is accepted for the prototype with concurrent flash/link stress tests, not as crosstalk qualification.

**Crystal:** XIN, XOUT and XTAL_OUT remain F.Cu-only, with no signal vias (total copper 11.324 / 2.928 / 5.449 mm). Actual ordinary-routing inspection found no unrelated signal crossing beneath the Y101 resonator body. C_TX_D2 passes the upper/right edge of the broader local crystal-ground area and B_RX_VALID_C5 its upper/left edge. C_TX_D0/1/2 run partly on B.Cu near the load-capacitor/escape area; the two internal GND planes separate them from the top crystal circuit. This is a prototype compromise, not an assertion of an entirely empty crystal region. Verify startup/restart and USB operation while all links and radios are active. In a subsequent revision, reserve this wider quiet region before global autorouting.

The [official RP2350B Minimal KiCad reference](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-010329-CA-1-RP2350B%20Minimal%20KiCAD.zip) and [hardware guide pp.10–15](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008280-DS-2-hardware-design-with-rp2350.pdf) are the source for the flash, crystal and USB layout intent. Reusing geometry does not replace timing, oscillator or USB measurements.

## Accepted source-route deviations and measurement gates

Lengths below are total track lengths on the source-to-resistor net; vias are counted separately. Straight placement distance alone hid the A-link routing detours.

| Signal | Source → series source pad → receiver | Source copper / signal vias | Disposition |
| --- | --- | ---: | --- |
| A_RX_D0 | U101.3 → R216.2; R216.1 → U201.8 | **17.185 mm / 4**; direct pad distance 5.044 mm | Accepted for A1 bring-up. Highest-priority source/receiver ringing and setup/hold capture; reroute this source tail first in the next PCB revision. |
| A_RX_VALID | U101.9 → R221.2; R221.1 → U201.23 | **12.302 mm / 2**; direct 5.671 mm | Capture both resistor sides and the receiving C5 VALID input; reject false/late VALID transitions. |
| C_RX_D1 | U101.39 → R417.2; R417.1 → U401.10 | **11.778 mm / 0**; direct **10.338 mm** | Exceeds this review's 10 mm RP placement attention threshold. Validate timing against C_RX_CLK; move the termination closer to the RP in the next revision. |

These are not presently open fabrication blockers. They remain functional acceptance gates. Start with one link and a low clock, then increase rate only after receiver timing and waveforms pass; reduced clock frequency does not itself slow edges or eliminate ringing. Record driver settings, probe loading, source and receiver levels, overshoot/undershoot, settling and setup/hold. Repeat with all links/radios active while stressing QSPI/XIP and checking CRC/readback. Do not infer a validated 50 Mbps operating point from DRC or raw `4×fCLK` arithmetic. Concrete probe points are in [FIRST-BOARD-TEST.md](../FIRST-BOARD-TEST.md).

## Return transitions: nine accepted heuristic exceptions

The final board contains 396 vias. The stitching audit `ground-stitching.json` (package: `review/evidence/reports/ground-stitching.json`) checks 141 signal through-vias; 132 have a GND plated via/pad within 2 mm centre distance. Two fabrication-compatible 0.45/0.20 mm GND vias were added for SWDIO and B_TX_VALID after the 0.60/0.30 mm search. All new holes remain outside pads, paste and EP envelopes and passed final DRC. The remaining nine positions could not fit another candidate without violating the conservative geometry constraints:

| Signal | Signal-via position, mm | Nearest plated GND centre distance, mm | A1 disposition |
| --- | --- | ---: | --- |
| A_RX_D0 | (46.0030,43.5463) | 3.424662 | Accepted; highest-priority source-tail/data waveform and A-link timing test. |
| A_RX_D3 | (43.1146,48.5897) | 2.629674 | Accepted; include in A-link receiver timing captures. |
| B_RX_D0 | (45.8286,52.7901) | 2.673413 | Accepted; include in B-link data/clock margin sweep. |
| B_RX_D1 | (45.5199,54.3042) | 2.827745 | Accepted; include in B-link data/clock margin sweep. |
| B_RX_D3 | (45.4390,55.5881) | 2.154122 | Accepted; include in B-link data/clock margin sweep. |
| B_RX_VALID | (47.8951,56.5079) | 3.195144 | Accepted; capture C5 VALID threshold and timing during startup and steady traffic. |
| B_TX_CLK | (45.8325,52.1474) | 2.317672 | Accepted; priority clock-edge capture at RP U101.16 against the source at U301.17/R314. |
| C_RX_D2 | (54.5296,54.9281) | 2.541838 | Accepted; include in C-link receiver timing captures. |
| C_TX_D2 | (48.6210,55.9071) | 2.583730 | Accepted; include in C-link and crystal/concurrent-traffic stress. |

**2 mm is this project's review heuristic, not a manufacturer-mandated limit.** The two inner GND planes remain connected, and the nearest physical return connection is 2.154–3.425 mm away for these exceptions. This supports accepting a controlled prototype; it does not establish transition impedance or timing margin. For the next layout, reserve ground-transition space and fix RP source-to-series routes before autorouting the remaining nets. First-board failures require correcting routing/termination/drive settings before increasing the claimed operating rate.

## C5 module land pattern and RF assembly

U201/U301/U401 remain ESP32-C5-WROOM-1U-N8R8 at (20,20)/90°, (20,80)/180° and (80,80)/270°. UART, EN and BOOT support is retained; GPIO13/14 are parallel-interface pins, so native C5 USB is intentionally unavailable. Both link clocks are C5 outputs. All six receiver VALID pull-downs remain 4.7 kΩ; verify actual reset/high-impedance/startup behavior in firmware and on hardware.

The [C5 module datasheet v1.3, Fig.11-2 / inspected PDF p.55](https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf) supports 32 pad numbers / 40 copper lands, including nine 1.3 × 1.3 mm EP29 lands with 0.4 mm gaps. Each module has 15.21 mm² paste over a 4.7 × 4.7 mm envelope (68.9%). The **complete envelope is hole-free**. Local solid top GND joins these lands to eight perimeter EP vias and peripheral ground-pad accesses. The four former internal gap vias are absent. Ordinary double-sided tenting is used; no filled/capped via process or reliable ink-plugging capability is assumed. Tenting, solder-mask webs, voiding and thermal performance remain manufacturing/assembly verification items.

ANT1 is the on-module connector. Approximate board centres are A (11.78,14.00), B (14.00,88.22), C (88.22,86.00) mm. ANT2/pad31 has no host RF trace. The [module datasheet Figs.10-2/10-3, inspected PDF pp.51–52](https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf) gives module/connector dimensions and the compatible U.FL / MHF I / AMC families. This external-connector variant does not require the PCB-antenna 15 mm carrier void, but the plug/coax/enclosure assembly must be checked physically.

The provisional 8 × 8 mm connector-access square, 3 mm cable corridor and 7 mm unobstructed height are planning allowances, not vendor-certified minimums. Verify the selected dual-band 50 Ω antenna, exact mating plug, coax bend radius, strain relief and final enclosure. Keep cables clear of switching inductors and exposed headers; measure isolation/coexistence with one, two and three radios active. Follow the module's handling/reflow requirements (inspected PDF p.56). The [Espressif C5 PCB guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c5/pcb-layout-design.html) informs return/decoupling practice; its bare-chip via-count rules are not misrepresented as a mandatory WROOM carrier count.

The review approves the stated **prototype** snapshot with the documented deviations and test gates. It supplies no fabricated-board result and no certification of link speed, three-radio performance, antenna placement or production readiness.
