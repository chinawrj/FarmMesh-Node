# Rev A — ESP32-C5 module review

**Review date: 2026-09-23 · schematic and footprint review · no hardware measurements**

Scope: [`design-manifest.json`](../design-manifest.json), [`c5-pinmap.json`](../c5-pinmap.json) and [`ESP32-C5-WROOM-1U.kicad_mod`](../FarmMesh.pretty/ESP32-C5-WROOM-1U.kicad_mod). This review covers the three radio modules and their connections to RP2350B. It does not replace the project ERC report, power-converter review or PCB review.

## Result

No unresolved C5 pin-mapping or module-footprint error was found in the inspected design. The previously identified missing VALID idle bias has been corrected and verified below. This is a review of the design data, not confirmation that the interfaces operate on hardware.

This record covers the final reviewed connection set, including the six 4.7 kΩ VALID pull-downs. Later changes require checking the affected connections again.

## Interface and support-circuit checks

- Exactly three `ESP32-C5-WROOM-1U-N8R8` modules are present: U201, U301 and U401. Each uses the reviewed 32-pad footprint.
- All 36 interface signals pass through their own 22 Ω series resistor to the intended RP2350B GPIO0–35, with no cross-connection between modules. Signal names use the C5 perspective. C5 supplies **both** TX_CLK and RX_CLK; RP drives only RX_D0–D3 and RX_VALID.
- The 12 interface GPIOs match the pinmap: TX data GPIO0/1/13/14, TX clock GPIO4, TX VALID GPIO5; RX data GPIO6/8/9/10, RX clock GPIO23, RX VALID GPIO24. No boot strap or internal flash/PSRAM pin is used for PARLIO.
- C5 USB GPIO13/14 are assigned to the C5-to-RP data direction. They are not connected to a USB connector. UART0 remains on module pad24/GPIO12 (RX) and pad25/GPIO11 (TX). Each UART header has GND, TX, RX, EN, BOOT and a 3.3 V reference; that reference is labelled as **not a power input**.
- Each module has its EN pull-up/RC and RESET button, GPIO28 pull-up/BOOT button, and GPIO27 pull-up. GPIO26 is unused. The documented download sequence holds GPIO28 low with GPIO27 high while resetting.
- Every module 3V3 pad is on `+3V3`; ground pads 1/28/29/30/32 are on GND. Local 22 µF, 100 nF and 100 µF capacitors are present for each module. Pad19, NC pads20/22 and the default-disabled ANT2 pad31 are unconnected.

The physical pad mapping, reset/download conditions and reference supply/EN circuits were checked against the [official module datasheet v1.3](https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf), tables 3-2 and 4-3, and figure 9-2 (PDF pages 14–15, 18 and 50 in the inspected 62-page document).

## Corrected finding: VALID idle bias

The initial design did not explicitly hold either direction's VALID signal inactive when its driving pin was released. In particular, GPIO5/MTDO does not have a default pull-up or pull-down in the [C5 SoC datasheet, table 2-1](https://documentation.espressif.com/esp32-c5_datasheet_en.html). Relying on software alone would leave reset and reconfiguration behavior dependent on initialization order and configured internal pulls.

The following six **4.7 kΩ pull-downs to GND** are now present on the receiving side of the corresponding series resistor:

| Radio | C5 → RP VALID, RP receiver | RP → C5 VALID, C5 receiver |
| --- | --- | --- |
| A | R204: `A_TX_VALID` | R205: `A_RX_VALID_C5` |
| B | R304: `B_TX_VALID` | R305: `B_RX_VALID_C5` |
| C | R404: `C_TX_VALID` | R405: `C_RX_VALID_C5` |

The initial 47 kΩ choice was reduced to 4.7 kΩ to accommodate RP2350 A2 silicon: [RP2350 erratum E9](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf) documents Bank 0 input leakage and an external pull-down workaround of 8.2 kΩ or less (printed pages 1366–1368; fixed in A3). This requirement applies to the RP receiver side; the C5 receiver side uses the same 4.7 kΩ value for consistency. At a nominal 3.3 V high level, each pull-down draws approximately 0.70 mA.

All six values and net endpoints were checked directly in the final manifest. This closes the hardware-bias finding; it does not implement reset recovery or transaction resynchronization.

## Footprint checks

The footprint has 32 unique pad numbers and 40 copper lands: 31 peripheral lands plus nine lands sharing EPAD number29. Pad numbering matches the module pin table. Checks against the official module datasheet figure 11-2 (PDF page55) confirmed the 18 × 21.2 mm body, 1.27 mm side pitch, 17.5 mm side-pad center spacing, 1.5 × 0.9 mm side lands, 0.9 × 1.5 mm top lands and 3 × 3 EPAD array of 1.3 mm squares with 0.4 mm gaps. All pads fit inside the footprint courtyard.

ANT1 is the module-mounted external-antenna connector; it is not another host-board solder pad. The footprint identifies ANT1 and the need for an external 2.4/5 GHz antenna. ANT2 remains disabled for the selected standard module. A PCB-antenna keepout has not been incorrectly applied beneath this external-connector module; cable clearance and actual antenna placement remain PCB/enclosure work. See module datasheet figures 10-2/10-3 and the [official module-layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c5/pcb-layout-design.html#general-principles-of-pcb-layout-for-modules-positioning-a-module-on-a-base-board).

## Boundaries and required validation

1. **Driver and timing:** No PIO/PARLIO driver has been implemented or tested. The reviewed [ESP-IDF v5.5 C5 capability definitions](https://github.com/espressif/esp-idf/blob/v5.5/components/soc/esp32c5/include/soc/soc_caps.h) support independent TX/RX units and RX-clock output. The [RX driver](https://github.com/espressif/esp-idf/blob/v5.5/components/esp_driver_parlio/src/parlio_rx.c) maps VALID through the GPIO matrix; `valid_sig_line_id = 4` denotes an internal RX lane for the 4-bit bus, not physical GPIO4. RX buffers/transactions must be prepared before accepting VALID. First-beat setup, sampling edges, frame end and restart behavior remain to be designed and measured.
2. **Reset and USB multiplexing:** RP must keep C5 TX-data and both clock nets as inputs. C5 firmware must reconfigure GPIO13/14 from USB before starting PARLIO; the [official hardware guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c5/schematic-checklist.html#usb) notes USB D+ startup transitions. Test power-up, each C5's independent reset, RP reset and UART download while the other devices remain powered. Receivers must discard startup data and recover partial transactions.
3. **Signal integrity:** The 22 Ω values are initial damping choices. Place each series resistor at its actual driver, including the C5 source for RX_CLK. Validate interconnect delay, ringing and setup/hold margins after PCB routing. No 50 Mbps interface or client-access performance has been demonstrated by this review.
4. **Power:** The [official supply guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c5/schematic-checklist.html#power-supply) calls for 3.3 V with at least 600 mA supply capability per C5. This is not a measured continuous load. Board-level regulation, simultaneous radio transients, capacitor DC-bias derating and local placement still require validation; the source is a regulated rail, not a direct 3.7 V cell connection.
5. **External antennas:** Three external antennas and their cable/enclosure arrangement remain to be selected and validated. The connector footprint alone does not establish coverage, antenna isolation, coexistence or throughput. No RF measurements or finished PCB layout are included in this review.
