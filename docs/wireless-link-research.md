# Wireless link research

**Draft research notes · 2026-09-22 · no wireless route selected**

English | [简体中文](wireless-link-research.zh-CN.md) | [Project overview](../README.md)

These notes record the public interfaces and implementation evidence reviewed for the RP2350B + three ESP32-C5 architecture. ESP-NOW remains a candidate for investigation, not the selected Mesh transport. AP+STA with proxy ARP is not being pursued at present. The project's solar deployment, client-access and sensor-capacity goals remain as stated in the README; this research adds no measured performance claims or firmware implementation.

## Evidence and version scope

| Evidence | Scope | Interpretation |
| --- | --- | --- |
| Official API documentation and headers | ESP-IDF `v5.5`; C5 `stable` documentation and Espressif FAQ accessed for this review | Documented interfaces, not FarmMesh measurements; `stable` and `latest` can change |
| Current header snapshot | ESP-IDF `master` at `422c4f5925d9a2408d5ddcc5bb1a95cc46da1e3d` | Source declarations only; not a selected or tested release |
| C5 binary inspection | `esp32-wifi-lib` commit `8a1b7bbc00e895d040c5c9a6fb9d1db2bbfc7958`, referenced by the ESP-IDF `v5.5` gitlink | Static symbol/relocation evidence for this archive only |
| MTU calculations and future adaptation | Derived constraints and possible future software work | Neither implemented nor validated on this project |

The [v5.5 C5 ESP-NOW page](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32c5/api-reference/network/esp_now.html) warns that some content has not yet been updated for C5. Packet-format statements are cross-checked with the [official FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html) and [v5.5 ESP-NOW header](https://github.com/espressif/esp-idf/blob/v5.5/components/esp_wifi/include/esp_now.h). Freeze the actual SDK and verify target-specific behavior before implementation.

## Capability and constraint summary

| Topic | Finding | Evidence / status |
| --- | --- | --- |
| WDS / four-address transparent bridging | No directly enabled public C5 mode confirmed in the reviewed ESP-IDF documentation/API | Public support unconfirmed; not proof of silicon impossibility |
| ESP-NOW transport | Vendor-specific 802.11 Action frames; no IP/UDP envelope required | Officially documented; candidate only |
| ESP-NOW application payload | v1: up to 250 B; v2: up to 1470 B | Officially documented; receiver must support the transmitted version and payload size |
| Public raw transmission | `esp_wifi_80211_tx()` accepts a 24–1500 B raw buffer, including the 802.11 MAC header | API limit, not application payload or IP MTU |
| Rate configuration | `esp_now_set_peer_rate_config()` exposes per-peer PHY/rate configuration | Public interface; configured PHY rate is not effective throughput |
| Automatic rate adaptation | No ready-to-enable public ESP-NOW switch or official ready-made tool confirmed in this review | A custom adaptation policy would be future software work |
| Transmit power | `esp_wifi_set_max_tx_power()` sets a Wi-Fi power ceiling on each C5 | Device-wide limit, not independent per-peer/per-packet power |
| Sustained ESP-NOW / public raw throughput on C5 | Maximum effective throughput has not been established here | No project benchmark; no evidence of this route meeting the 50 Mbps access goal |
| AP+STA + proxy ARP | Considered briefly; currently not pursued | Project preference, not a finding of technical impossibility |

## Transparent bridging and public raw transmission

The [C5 Wi-Fi driver guide](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32c5/api-guides/wifi.html) and reviewed public headers do not establish a supported, directly enabled WDS/four-address transparent bridge. Ordinary AP+STA operation does not automatically preserve downstream clients' MAC addresses through a transparent Layer 2 bridge. Raw frame injection alone does not provide a complete four-address encrypted bridging implementation.

The [v5.5 raw-send API contract](https://github.com/espressif/esp-idf/blob/v5.5/components/esp_wifi/include/esp_wifi.h#L1178-L1203) specifies a buffer length of 24–1500 B. That buffer includes the 802.11 MAC header; it is not a 1500 B application payload or IP MTU. The [C5 packet-send documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c5/api-guides/wifi-driver/wifi-vendor-features.html#wi-fi-80211-packet-send) lists beacon, probe request/response, Action and non-QoS data frames, and excludes encrypted and QoS frames on this public raw path. These limits do not describe every internal driver transmission path.

AP+STA with proxy ARP remains outside the current route. For completeness, IPv4 proxy ARP would still need actual IP forwarding and return-path routing; ARP replies alone do not create transparent Layer 2 forwarding. DHCP, broadcast handling and IPv6 would require separate treatment. [RFC 1027](https://datatracker.ietf.org/doc/html/rfc1027) is background, not an adopted FarmMesh design.

## ESP-NOW framing and versioned implementation evidence

ESP-NOW carries application data in vendor-specific 802.11 Action frames without requiring IP or UDP. Its v2 format chains multiple vendor-specific information elements within an Action frame to carry up to 1470 B; this is not fragmentation into independent v1 packets. v1 supports up to 250 B. Mixed-version reception is conditional, so both endpoints' version and payload-receive capabilities must be checked. See the [official ESP-NOW FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html).

The 1470 B ESP-NOW v2 application limit and 1500 B public raw-buffer limit measure different layers. Comparing them directly does not compare usable application payloads or throughput.

Static inspection of the [C5 `libespnow.a` archive](https://github.com/espressif/esp32-wifi-lib/blob/8a1b7bbc00e895d040c5c9a6fb9d1db2bbfc7958/esp32c5/libespnow.a), selected by the [ESP-IDF v5.5 Wi-Fi library gitlink](https://github.com/espressif/esp-idf/tree/v5.5/components/esp_wifi), found this direct call chain:

```text
esp_now_send -> mt_send -> ieee80211_send_action_vendor_spec
```

| Object / section | Relocation offset | Call target |
| --- | --- | --- |
| `espnow.o` / `.text.esp_now_send` | `0xe8`, `0x15e` | `mt_send` |
| `manatick.o` / `.text.mt_send` | `0xf8` | `ieee80211_send_action_vendor_spec` |

The inspected archive is 63,178 B, Git blob SHA `1bf0d49f4b910475577058a291c50ac83cb86392`. Its symbol table has no reference to `esp_wifi_80211_tx`. Thus the observed call segment does not go through that public API. These internal symbols are not stable interfaces, and this observation does not rule out shared code deeper in the driver or in other versions. It is not a runtime or throughput test.

With this exact archive and an ESP RISC-V toolchain, the relevant inspection can be repeated with:

```sh
git hash-object libespnow.a
riscv32-esp-elf-objdump -r -j .text.esp_now_send -j .text.mt_send libespnow.a
riscv32-esp-elf-nm -A libespnow.a | rg 'esp_now_send|mt_send|ieee80211_send_action_vendor_spec|esp_wifi_80211_tx'
```

## MTU, TCP MSS and UDP boundaries

If a custom link puts one IP packet in one ESP-NOW v2 payload without link fragmentation/reassembly, its maximum IP MTU is **M = 1470 − H bytes**. Here **H** is all custom encapsulation outside the IP packet, including any retained Ethernet header or tags. A chosen operating MTU can be smaller, and the rest of the path may impose a smaller limit. This is a size budget, not a selected encapsulation or throughput prediction.

| Quantity | Budget from effective MTU M | Assumptions |
| --- | --- | --- |
| IPv4 TCP MSS | M − 40 | Fixed 20 B IPv4 and 20 B TCP headers |
| IPv6 TCP MSS | M − 60 | Fixed 40 B IPv6 and 20 B TCP headers |
| IPv4 UDP application payload | M − 28 | No IPv4 options; 8 B UDP header |
| IPv6 UDP application payload | M − 48 | No IPv6 extension headers; 8 B UDP header |

TCP's advertised MSS calculation uses fixed headers; the sender must further reduce actual TCP data to accommodate options or extension headers. [RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html) explains this distinction. UDP has no MSS: clamping TCP MSS does not solve oversized UDP datagrams, and changing an intermediate node's MTU alone does not ensure that a terminal reduces its UDP messages. Packet sizing/path-MTU handling still matters. [RFC 8085, section 3.2](https://www.rfc-editor.org/rfc/rfc8085.html#section-3.2)

A custom link fragmentation/reassembly layer could preserve a larger upper-layer MTU, but no such scheme is selected or implemented. Any eventual IPv6 link design must also respect the 1280 B minimum link MTU and provide adaptation below IPv6 if necessary. [RFC 8200, section 5](https://www.rfc-editor.org/rfc/rfc8200.html#section-5)

## Rate, power and possible future adaptation

The reviewed [`esp_now_set_peer_rate_config()` declaration](https://github.com/espressif/esp-idf/blob/422c4f5925d9a2408d5ddcc5bb1a95cc46da1e3d/components/esp_wifi/include/esp_now.h) accepts per-peer rate settings. Its [`wifi_tx_rate_config_t` definition](https://github.com/espressif/esp-idf/blob/422c4f5925d9a2408d5ddcc5bb1a95cc46da1e3d/components/esp_wifi/include/esp_wifi_types_generic.h) contains `phymode`, `rate`, `ersu` and `dcm`. Target, peer and SDK support must be checked; configuring a PHY rate is not a guarantee of payload throughput. Neither advertised chip PHY rates nor ordinary Wi-Fi TCP benchmarks establish sustained ESP-NOW or public raw-path performance.

The [Wi-Fi power API](https://github.com/espressif/esp-idf/blob/v5.5/components/esp_wifi/include/esp_wifi.h) sets a maximum transmit-power ceiling per C5, not per peer or per packet. Each of the three C5 chips can have its own ceiling. Its 0.25 dBm argument unit does not imply continuously available 0.25 dB hardware steps, nor that every transmitted frame uses that power. This review does not infer exact C5 maxima across bands from a generic header.

In the reviewed official documentation, FAQ and public headers, no ready-to-enable ESP-NOW automatic rate-adaptation switch or ready-made official tool was confirmed. The per-peer setter supplies control, not an automatic selection algorithm. This does not prove that all internal adaptation logic is absent. If the project later needs custom adaptation, a possible software policy would track per-peer success and transmission time, probe higher rates and reduce rates after failures, using RSSI as supporting information. This is unimplemented, unvalidated future work, not a chosen algorithm or a current capability.

## Hardware continuity and remaining decisions

The internal interface candidate remains unchanged: three independent PARLIO ↔ PIO links, separate 4-bit TX/RX buses, and both clocks supplied by each corresponding C5. Each direction uses 4 DATA + CLK + VALID: 12 signals per link, 36 total against RP2350B's 48 Bank0 GPIOs. That is a resource estimate, not firmware or timing validation. Sharing a half-duplex data bus would require explicit output-enable, tri-state and direction-change control. See the [internal-interface draft](../README.md#candidate-internal-interface).

Wireless route selection, the SDK baseline, encapsulation/fragmentation choices, required rate-control behavior and actual effective throughput remain open. This record supports hardware discussion; it does not start firmware implementation or alter the existing product targets.
