# A1 independent power review

Date: 2026-09-23. **Final static prototype power review: PASS.** This review is bound to the actual frozen `hardware/rev-a/FarmMesh-Node.kicad_pcb`, SHA-256 **`94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9`**. Its bytes were checked before and after the read-only review. No identified power-related issue remains open that blocks prototype fabrication. This conclusion supersedes the earlier placement-only and temporary-board snapshots; it does not establish measured electrical stability, thermal performance or a production operating envelope. No simulation or hardware measurements have been performed.

## Final disposition and hardware validation

1. **USB hardware isolation is present and its static connectivity is closed; sample testing remains open.** In A0, battery-powered RP2350 can present its USB pull-up while D101's upper steering diode connects that data line to dead USB_VBUS. GPIO37 sensing only helps application firmware; it does not control ROM BOOTSEL. A rail-independent ESD replacement removes the D101 rail path but does not disconnect the RP PHY from an unpowered host. A1's U103/U104 pad-to-net assignments match the VBUS-qualified isolation circuit below, with ESD on the connector side. The actual 3V3/GND chains are connected, and the frozen board has zero unconnected items and zero schematic-parity issues. Physical USB power-sequence tests remain first-board work. See [ST USBLC6-2 circuit, p. 1](https://www.st.com/resource/en/datasheet/usblc6-2.pdf).
2. **Power capacitor MPN/footprint selections are now present; operating-envelope validation remains open.** A1 uses the exact Murata 22 µF MPN, 10SVPC120M input bulk, 6SVPC100M radio reservoirs and 6SVPE220M output bulk. Manufacturer bias data were retrieved for the 22 µF part, as detailed in the later integrated review. Do not equate its label with its capacitance in circuit or treat the retrieved typical curve as a guaranteed minimum.
3. **Final power copper and paste corrections are closed at the SHA above.** The converter loops, peripheral exposed-pad cooling, continuous inner GND, wide supply branches and both corrected via positions were rechecked on the frozen board. All four supply paths match the recorded geometry; the full-board actual pad-shape/drill test finds no paste/drill intersection. An ERC/DRC pass cannot establish current capacity, stability or junction temperature.

No wrong power pin, reversed PMOS, reversed bootstrap connection, feedback polarity error or charger connection remains identified in the reviewed A1 power implementation.

## USB correction implemented in the A1 generator

The USB block in `build_design.py` was edited under the implementation owner's explicit delegation. Its regenerated U103/U104 PCB pad numbers and named nets were subsequently checked on the routed candidate and agree with the connections below. This closes the earlier generator-only uncertainty; it does not replace final package verification or USB measurements.

U103 is **TS3USB30EDGSR**, DGS/VSSOP-10, powered from board 3V3, with C128 100 nF bypass. The selected stock `Package_SO:TSSOP-10_3x3mm_P0.5mm` has the required 3 × 3 mm body, 0.5 mm pitch and no exposed pad; its 1.45 × 0.30 mm pads at ±2.15 mm are compatible with the DGS lead envelope. The DGS pin mapping is:

| Pin | A1 connection |
| --- | --- |
| 1 S | GND; select port 1 |
| 2 D1+ / 8 D1− | RP side, through the existing 27 Ω resistors near RP2350 |
| 3 D2+ / 7 D2− | NC |
| 4 D+ / 6 D− | Connector-side ESD paths |
| 5 GND / 10 VCC | GND / 3V3 |
| 9 OE, active low | 10 kΩ pull-up to 3V3; comparator output below |

OE high disconnects both lines; S low and OE low select D1. The data sheet specifies power-off leakage with VCC = 0. Its recommended operating table requires VCC ≥ 3.0 V, despite the front-page 2.7 V wording; use the stricter table. Source: [TI TS3USB30E, Rev. G, pp. 3–5 and table 7-1](https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf).

U104 is **TLV3011BIDBVR**, `Package_TO_SOT_SMD:SOT-23-6`, as a VBUS comparator: pin 6 to 3V3 with C129 100 nF bypass; pin 2 to GND; pin 5 REF to pin 3 IN+ with C130 1 nF REF-to-GND; pin 4 IN− to R114/R115, a 237 kΩ / 100 kΩ VBUS divider, both 0.1%; pin 1 open-drain OUT to switch OE, with R116 10 kΩ pull-up. The GPIO37 divider remains independent. VBUS above approximately `1.242 × (1 + 237/100) = 4.186 V` pulls OE low; absent VBUS leaves OE pulled high. The **B** suffix is required for fail-safe inputs and the high-impedance power-on-reset state. The non-B device is not an approved substitution. Source: [TI TLV3011B, pin table, section 6.9 and sections 9.4.4–9.4.5](https://www.ti.com/lit/ds/symlink/tlv3011.pdf).

A conservative engineering estimate combining reference spread, temperature drift, offset, full hysteresis and resistor tolerance gives roughly 4.02–4.36 V trip limits; this is not a characterized board limit. Avoid a large divider capacitor that delays disconnect. Check slow VBUS ramps, cable removal, battery removal, rail brownout, normal enumeration and ROM BOOTSEL. The switch adds series resistance/capacitance, so retain waveform/USB functional validation. This circuit does not establish USB compliance by itself.

## Converter implementation requirements

The [LTC3119 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/3119fb.pdf) provides the FE layout in Figure 11, pp. 25–26, the TA06 starting circuit on p. 28, and compensation guidance on pp. 22–25. It requires short/wide high-current paths, close bypass capacitors, an uninterrupted ground plane, exposed-pad vias, and Kelvin small-signal returns. TA06 is a reference circuit, not a guarantee for the FarmMesh board.

The following are engineering placement/route requirements for this design:

- Place C3/C4 directly beside PVIN pins 22/23 and PGND20; place C8/C9 beside PVOUT6/7 and PGND9. Give each local capacitor a direct short ground connection. C6/C7 bulk capacitors must not displace these local ceramics. Route the battery and load trunks from the capacitor regions, avoiding a shared narrow neck in the bypass loops.
- Place L1 adjacent to SW1 pins 21/24 and SW2 pins 5/8. Keep SW copper compact but wide; do not route FB, RT, RUN, crystal, USB or radio signals beneath/through those switching-node regions. C1 joins BST1/26 to SW1 and C2 joins BST2/3 to SW2 with very short loops.
- Place C11 at VCC16 and keep D1 nearby. Group R2/R3 at FB12, R4/C10 at VC13 and R5 at RT17. Route their quiet ground back to SGND14/exposed-pad ground without sharing the input/output capacitor current path. Sense 3V3 separately from the local output-capacitor positive copper: A1 uses C9 at the C7 output-distribution region. A common GND net name alone does not create this geometry.
- Use an uninterrupted inner GND reference across the whole converter and preserve it beneath the bypass loops. Connect the entire exposed pad to ground copper with multiple thermal vias. Choose via drill, paste openings and tenting/plugging with the fabricator's assembly rules; avoid unfilled large holes that drain the solder joint. Extend heat-spreading copper beyond the IC and keep it connected through multiple vias.
- Route J1–F1–Q1–input capacitors and the common output trunk as pours/wide tracks sized for the low-battery current. Do not funnel these through one signal-width track, one ordinary via, or thin thermal spokes. If changing layers, use multiple vias and account for their aggregate resistance. Branch the three module supplies from the output distribution region and place each reservoir/ceramic pair at its module supply pins.
- Keep test access to VBAT_PROTECTED, 3V3, GND and PGOOD; provide a short-ground probing location at both the converter and farthest module. Leave R4/C10 accessible for compensation tuning. Do not add a large test stub to SW or FB.

The PMOS orientation is correct: fused battery to Q1 drain, converter to source, 100 kΩ gate pull-down. It protects reverse battery polarity, not reverse current from an externally driven 3V3 rail. Its low-voltage RDS(on) supports this application, subject to heating and copper. See [DMP2008UFG](https://www.diodes.com/datasheet/download/DMP2008UFG.pdf).

## Current, thermal and compensation assessment

The three C5 modules require supply capability of at least 0.6 A each, totaling 1.8 A before RP2350 and other circuitry. The **2.2 A output figure is a design budget**, not a measured load or guaranteed converter rating. The additional 0.4 A remains an allocation to confirm with the actual RP workload. The **3 A figure is a transient test target**, requiring a defined pulse duration/duty cycle. Source: [ESP32-C5-WROOM-1/1U data sheet, table 6-2](https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf).

Calculated using an explicitly assumed 80% efficiency and 3.3 V output:

| Operating point | Output power | Input current at 3.0 V | Total converter-stage loss |
| --- | ---: | ---: | ---: |
| 2.2 A budget | 7.26 W | 3.03 A | 1.82 W |
| 3.0 A transient target | 9.90 W | 4.13 A | 2.48 W |

`Iin = Vout × Iout / (Vin × efficiency)`; loss is `Pout × (1/efficiency − 1)`. These are estimates, not efficiency measurements. Loss is distributed between IC, inductor, MOSFET and other resistances; do not put all of it into an IC junction calculation. The selected cell/BMS, connector, fuse, wiring and copper must support the input current including cold-cell and contact resistance. Normal full-load operation stops near the UVLO threshold; 2.8 V is not a promised full-load condition.

L1's [XAL7070-472MEC data](https://www.coilcraft.com/getmedia/1ba55433-bcc8-4838-9b21-382f497e12e0/xal7070.pdf) gives 4.7 µH ±20%, about 14.3 mΩ maximum DCR and 15.2 A typical saturation current at 25°C, defined by 30% inductance loss. That is not a guaranteed hot saturation threshold. The converter's inductor-current limit must not be read as an output-current rating. With the 80% estimate, Q1 conduction loss at the 4.13 A input pulse is approximately 0.17 W using its 25°C 9.8 mΩ maximum figure; hot resistance is higher.

The existing 78.7 kΩ / 820 pF network has a calculated compensation zero near 2.47 kHz. Its output load includes C7's 220 µF, three 100 µF reservoirs and ceramics; nominal bulk alone totals 520 µF. This differs from TA06 and includes trace resistance/inductance. A1 selects C6 = Panasonic 10SVPC120M (120 µF input) and C203/C303/C403 = 6SVPC100M (100 µF each, 30 mΩ specified ESR). These polymer selections must be included in the model; lower ESR is not by itself evidence of stable operation. For illustration, the simplified boost RHP-zero equation gives about 41.9 kHz at 3.0 V / 2.2 A and 30.7 kHz at 3.0 V / 3 A with 4.7 µH. These calculations identify validation cases; they do not prove phase margin. Retain the TA06 compensation as the prototype starting point, model the selected capacitor network, and confirm with load-step tests before asserting the operating envelope.

C7 is correctly polarized and dimensioned. [Panasonic 6SVPE220M](https://industrial.panasonic.com/sa/products/pt/os-con/models/6SVPE220M) uses the 6.3 mm diameter, 5.9 mm case; [case dimensions](https://industrial.panasonic.com/cdbs/www-data/pdf/AAB8000/AAB8000C179.pdf) and [recommended lands](https://industrial.panasonic.com/cdbs/www-data/pdf/AAB8000/AAB8000COL10.pdf) support the chosen footprint. Its 220 µF is nominal with tolerance, not minimum capacitance.

## Required sample measurements and release boundary

- Sweep converter input from 4.2 V down to just above actual UVLO, then through shutdown/restart. Include startup with the full capacitor bank and realistic protected-cell/cable resistance. UVLO stopping switching is not zero battery drain; use the specified external protected pack and measure standby/off current.
- At 2.2 A and simultaneous radio operation, measure converter and all three module supply pins, ripple/overshoot, efficiency and component temperature after thermal equilibrium. Test the defined 3 A pulse separately. Stay within each module's 3.0–3.6 V supply range, including transients. Do not use thermal shutdown as the normal junction-temperature limit.
- Check light-load/Burst behavior, repeated load steps and buck/boost transition near 3.3 V. Investigate sustained ringing or supply dips before radio/RF testing. A voltage probe with a long ground lead is insufficient evidence for switching ripple.
- Verify reversed battery, pack protection behavior and fuse coordination with a current-limited test setup. No board charger, raw PV input, battery ADC or USB-powered board operation is introduced by this review.
- The USB hardware change is statically closed against the final PCB/netlist. Test every power-order combination on the sample, including ROM BOOTSEL; that functional validation remains unperformed.

## Power placement implementation and local audit

Under the implementation owner's later delegation, this reviewer added `scripts/power_placement.py`. It loads no project board and saves none: `placements()` supplies the component coordinates, and `route(board, footprints, nets)` draws the converter cell after the caller loads the real footprints and assigns nets. The script rejects moved component coordinates rather than drawing stale routes. L1 is rotated 180 degrees so SW1 and SW2 face their matching U1 sides. C3/C4/C8 bridge the lower switch branch through the gap between their pads, following the FE reference arrangement. High-current trunks use 1.0–1.5 mm copper, with narrower local pin escapes and 0.6 mm sections beneath those ceramic bodies.

An isolated four-layer test board was built in `/tmp` using the actual final power footprints and net assignments, including C6 = 10SVPC120M. With continuous inner GND planes and the project's 0.15 mm clearance / 0.45 mm via / 0.20 mm drill constraints, its KiCad DRC reported **zero copper/clearance/courtyard/hole conflicts and zero unconnected power items**. Remaining scratch-board findings were 20 default-reference/value silkscreen overlaps; the full-board build manages these labels. This local result does not replace full-board DRC or final copper inspection.

The script returns the B.Cu 3V3 distribution anchor `(68.0, 28.7)` and three 0.6 mm / 0.3 mm output-bulk vias. The feedback sense is routed separately from C9's positive pad at this output-distribution region. The builder must preserve both continuous inner ground planes and join the system supply branches at the specified distribution copper.

For ordinary prototype assembly, **no thermal drill remains inside U1's exposed-pad solder-mask/paste area**. Nine 0.6 mm / 0.3 mm GND vias lie beyond the exposed pad, at x = 79/80/81 mm and y = 22.1/31.9/32.7 mm. Three 0.8 mm copper strips at each end join these vias to the exposed-pad copper. This avoids relying on filled/capped via-in-pad assembly; it increases thermal-path resistance compared with the data-sheet board using vias beneath the exposed pad. Therefore data-sheet thermal resistance cannot be assigned to A1, and 2.2 A operation remains subject to actual temperature measurement. Ordinary tented capacitor-adjacent vias are separate from their pads; the 0.35 mm spacing advice for reliable solder-mask **filling** was not treated as a universal tenting rule.

## Integrated power-distribution review

Actual routed-candidate inspection: 2026-09-23. The loaded power footprint positions match `power_placement.placements()`. Every segment of all four paths in `reports/power-distribution.json` exists on B.Cu and 3V3: A/B/C are 1.5 mm, and the RP feed is 1.0 mm. The earlier C7/R104 and TP2/R6 courtyard conflicts are closed: R104 is at `(63,13)` and TP2 at `(66,26)`, and the candidate DRC reports no courtyard violations. The actual LTC3119 board uses the nine **peripheral** EP vias described above; the superseded in-pad EP arrangement is absent. These findings replace the initial integration snapshot.

Using nominal 35 µm outer copper and copper resistivity at 20°C, the branch estimates are internally consistent:

| Branch | Actual route length | Width | Estimated copper resistance | Calculated drop at 0.6 A |
| --- | ---: | ---: | ---: | ---: |
| A | 65.409 mm | 1.5 mm | 21.43 mΩ | 12.86 mV |
| B | 80.982 mm | 1.5 mm | 26.53 mΩ | 15.92 mV |
| C | 50.229 mm | 1.5 mm | 16.46 mΩ | 9.88 mV |

The RP feed is 13.853 mm long and 1.0 mm wide, approximately 6.81 mΩ by the same model. Its 0.4 A allocation would give about 2.72 mV of copper drop; this is an allocation calculation, not a measured RP current.

These are conductor estimates, excluding vias, pads, the common feed, ground return, copper-thickness tolerance and temperature rise. At 0.6 A the longest branch dissipates about 9.6 mW. The common 1.0 mm-wide, 6.7 mm-long copper segment before the star point is approximately 3.29 mΩ under the same assumptions, or 7.24 mV at 2.2 A. Those values support the prototype layout choice; they are not measured current or temperature ratings. The 0.6 A number is a module supply-capability requirement, not a cap on each module's instantaneous draw.

The specified stackup places In2 GND about 0.0994 mm from B.Cu. On the frozen board, both In1 and In2 contain one connected filled GND outline; all 1,540 routed tracks are on F.Cu/B.Cu, so signal traces have not divided the inner reference planes. Sampling each actual branch centerline at intervals no larger than 0.25 mm gives 298/341/280/65 sample positions for A/B/C/RP. GND is present beneath the trunks; the only misses are local positive-supply-via antipads at module/RP entry. The RP LX keepout is confined to its intended In1 region, away from the LTC3119 cell. Thus the inspected board provides nearby plane returns without a long reference-plane split beneath these supply paths. Further routing/zone changes require repeating this check. Local reservoirs and their ground vias handle high-frequency pulse current; a long 3V3 trace alone is not the decoupling network.

### Copper corrections and final frozen-board closure

The Specctra session import had omitted all fixed seed tracks/vias. `merge_seed_routing.py` restores their 825 unique geometries with destination-board net mapping; the source seed contained 827 objects including two duplicate geometries. Before the two deliberate paste fixes below, every unique seed copper geometry was present in this candidate. The high-current battery paths, PVIN/PVOUT bypass connections, bootstrap loops, FB/VC/RT routes and power footprints consequently retained the independently reviewed local arrangement. The nine EP ground vias are actually present at x = 79/80/81 mm and y = 22.1/31.9/32.7 mm, with 0.6 mm copper/0.3 mm drills and the 0.8 mm copper bridges. Their external placement avoids EP solder drain, but the thermal penalty relative to an in-pad reference board still requires measurement.

`finish_power_access.py` closes nine disconnected GND chains and three low-current 3V3 tails with 12 added tracks and nine ordinary tented 0.6/0.3 mm vias. It checks connection to a filled inner GND zone rather than assuming that an existing track reaches ground. The added vias are outside all pad/paste windows. USB control/switch supply and the debug/reference branches join existing distribution copper through 0.3 mm B.Cu tails; those tails do not carry the three-radio load. Repeated invocation adds no further copper.

An actual paste-shape/drill intersection check found two defects that ordinary electrical DRC did not report: the original C5.2 GND via at `(88.0,30.6)` and R7.2 REG_RUN via at `(88.3,35.5)` each intruded about 0.025 mm into its adjacent paste opening. `fix_power_paste_clearance.patch(board)` moves them to `(88.0,30.85)` and `(88.3,35.75)`. The REG_RUN B.Cu diagonals retain their former meeting point, with one 0.25 mm stub to the new via, preserving clearance to C11's GND via. The same coordinates/stub are now in `power_placement.py` to prevent regeneration of the defect. The patched temporary candidate has **zero actual drill/paste intersections**. A C5.1 bounding-box overlap with another via was checked against its rounded pad shape and is not a physical intersection.

The intermediate temporary board had three remaining connections outside the power-tail work. Those are now closed on the frozen main PCB. The final read-only review confirmed:

| Static check | Result at the frozen PCB SHA-256 |
| --- | --- |
| Final DRC / unconnected / schematic parity | 0 / 0 / 0 in `reports/drc.json` |
| ERC | 0 sheet violations in `reports/erc.json` |
| Actual board via count | 396, including the final ground-access fallback vias |
| Converter component positions and rotations | Match `power_placement.placements()` |
| Reviewed local converter copper | Preserved after final unrelated reroutes |
| A/B/C/RP distribution paths | Every recorded segment, net and width present |
| LTC3119 exposed-pad ground vias | All nine peripheral vias and copper bridges present |
| C5 and R7 paste corrections | New via positions present; old positions absent |
| J2 ground-via mask clearance | Via at (98.25, 26.54); 0.25 mm nominal hole-edge to pad-mask-opening gap |
| Full-board actual paste-shape/drill collision check | 0 intersections |
| In1/In2 GND continuity and branch return sampling | Rechecked and unchanged, as described above |

**No unclosed power-related prototype-fabrication blocker was identified for PCB SHA-256 `94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9`.** This is static power-review sign-off for making and testing the prototype. It does not authorize substitutions or apply to later copper changes. Electrical stability, sustained 2.2 A temperature, the defined 3 A transient test and USB power-order behavior remain first-board measurements; the stated current figures are design/test targets, not demonstrated ratings.

### Actual manufacturing-layer review

The final exported manufacturing files were independently inspected through `review/gerber/F_Cu.png`, `B_Cu.png`, `In1_Cu.png`, `In2_Cu.png` and `paste-drill-overlay.png`, rendered directly from Gerber/Excellon bytes with gerbonara 1.6.3. Local converter enlargements were also inspected. This review uses the manufacturing layers themselves, not only KiCad's native display. All 11 Gerber and two Excellon input hashes, plus the inspected image hashes, match `review/gerber/render-manifest.json`, SHA-256 **`321257ff7851ca2e0f5fdc9abaaaf83bd13e512c23543d28fce0b9004fea47b3`**. The export manifest binds these outputs to the final PCB SHA above.

Parsed Gerber coordinates/apertures confirm every A/B/C 1.5 mm and RP 1.0 mm supply segment. U1's exported GND heatsink pad is 3.05 × 7.56 mm, with all six 0.8 mm copper bridges and nine 0.3 mm peripheral drill hits present. The two corrected C5/R7 holes occur at their new positions only. The final DFM improvement moves the J2 GND via from `(98.0,26.54)` to `(98.25,26.54)`; the actual F.Mask circle is 1.7 mm diameter at `(97.0,26.54)` and Excellon drill diameter is 0.3 mm, giving **0.25 mm nominal hole-edge-to-mask-opening clearance**. The original tangent hole is absent.

Both inner Gerbers have one continuous main filled region. Visual inspection and polygon point checks confirm ground around the LTC3119 cell; the RP LX body and neck are cleared on In1 while In2 retains ground there. No missing supply copper, severed EP bridge, unexpected ground-plane split, or power-related export discrepancy was identified. **Final manufacturing-layer power review: PASS for prototype fabrication**, with the unmeasured operating limits and first-board tests below unchanged.

### Capacitor model and first-board tests

The official [Murata SimSurfing](https://ds.murata.com/simsurfing/mlcc.html?lcid=en-us) response for GRM21BZ71A226ME15 is preserved in `parts-selection.json` under `capacitor_validation.GRM21BZ71A226ME15L`, including request parameters, the full 201-point response and SHA-256 `662e4209ee2470dc889907910592f94f6a3ba756e7fa337bd67166ccd6e7feca`. The curve gives 14.288852 µF at 3.3 V and 11.788160 µF at 4.2 V per part. Its conditions are 25°C, 0.5 Vrms, 120 Hz, consistent with [Murata's measurement conditions, pp. 7–8](https://ds.murata.com/simsurfing_data/pdf/en-us/mlcc/sim_mlcc_measuringcond_e.pdf).

Accordingly, a nominal model at 4.2 V uses about **23.5763 µF for C3+C4**, plus the 120 µF input polymer, rather than 44 µF of input ceramic. On the output, the 220 µF central polymer and three 100 µF polymers total **520 µF nominal**; C8 and the three radio 22 µF ceramics add about **57.1554 µF** under the retrieved 3.3 V curve. This gives approximately 577.2 µF before the other decouplers and device-internal capacitance. It is a distributed network with branch resistance/inductance and distinct ESRs, not a single ideal capacitor at U1. C7's specified ESR is 10 mΩ; the radio polymers are 30 mΩ each and the input polymer is 27 mΩ.

No verified full-temperature or low-ripple bias curve was obtained. Do not convert these typical points into guaranteed capacitance minima or derive them from the X7R label. Model component tolerances and distributed impedance, then measure startup/inrush, no-load-to-load and reverse load steps, three-radio simultaneous bursts, 3.3 V buck/boost transition, UVLO recovery and output overshoot. Record voltage at U1 and at every module; measure ripple with short-ground probing. Sweep input and relevant ambient temperatures and allow thermal equilibrium at 2.2 A. Define the 3 A pulse width/duty cycle before testing it. **Electrical stability, sustained-load temperature and actual radio-load performance remain unmeasured; this is prototype review evidence, not a production operating guarantee.**
