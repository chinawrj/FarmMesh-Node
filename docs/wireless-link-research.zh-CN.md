# 无线链路研究

**研究草案 · 2026-09-22 · 尚未选定无线技术路线**

[English](wireless-link-research.md) | 简体中文 | [项目概览](../README.zh-CN.md)

本文记录针对 RP2350B + 三颗 ESP32-C5 架构所核查的公开接口及实现证据。ESP-NOW 仍是待研究的候选，并非已选定的 Mesh 传输方案。当前不推进 AP+STA 配合 proxy ARP 的路线。项目的太阳能部署、客户端接入和传感器容量目标仍以 README 为准；本次研究不新增实测性能结论或固件实现。

## 证据与版本范围

| 证据 | 范围 | 解读边界 |
| --- | --- | --- |
| 官方 API 文档与头文件 | ESP-IDF `v5.5`；本次核查访问的 C5 `stable` 文档及 Espressif FAQ | 已文档化接口，不是 FarmMesh 实测结果；`stable` 与 `latest` 内容可能变化 |
| 当前头文件快照 | ESP-IDF `master`，提交 `422c4f5925d9a2408d5ddcc5bb1a95cc46da1e3d` | 仅为源码声明；不是项目已选定或测试过的发布版本 |
| C5 二进制检查 | ESP-IDF `v5.5` gitlink 引用的 `esp32-wifi-lib` 提交 `8a1b7bbc00e895d040c5c9a6fb9d1db2bbfc7958` | 仅针对该静态库的符号与重定位证据 |
| MTU 计算与后续自适应 | 推导约束及可能的后续软件工作 | 本项目均尚未实现或验证 |

[v5.5 C5 ESP-NOW 页面](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32c5/api-reference/network/esp_now.html)提示，部分内容尚未针对 C5 更新。帧格式结论已与[官方 FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html)和 [v5.5 ESP-NOW 头文件](https://github.com/espressif/esp-idf/blob/v5.5/components/esp_wifi/include/esp_now.h)交叉核对。实施前仍需冻结实际 SDK 版本并确认目标芯片的具体行为。

## 能力与约束概览

| 项目 | 核查结果 | 证据 / 状态 |
| --- | --- | --- |
| WDS / 四地址透明桥接 | 在已核查的 ESP-IDF 文档/API 中，未确认 C5 有可直接启用的公开模式 | 公开支持尚未确认；不能据此断言芯片不可能实现 |
| ESP-NOW 传输 | 使用厂商特定的 802.11 Action 帧；无需 IP/UDP 封装 | 官方已文档化；仅为候选 |
| ESP-NOW 应用载荷 | v1：最多 250 B；v2：最多 1470 B | 官方已文档化；接收端需支持所发送的版本与载荷长度 |
| 公开 raw 发送接口 | `esp_wifi_80211_tx()` 接受 24–1500 B 的原始缓冲区，包含 802.11 MAC 头 | API 长度限制，不是应用载荷或 IP MTU |
| 速率配置 | `esp_now_set_peer_rate_config()` 提供按 peer 配置 PHY/速率的接口 | 公开接口；配置的 PHY 速率不等于有效吞吐 |
| 自动速率自适应 | 本次核查未确认 ESP-NOW 有可直接启用的公开开关或现成官方工具 | 自定义自适应策略属于后续软件工作 |
| 发射功率 | `esp_wifi_set_max_tx_power()` 设置每颗 C5 的 Wi-Fi 功率上限 | 设备级上限，不是按 peer/按包独立设置功率 |
| C5 的 ESP-NOW / 公开 raw 路径持续吞吐 | 本次尚未确定其最大有效吞吐 | 本项目无基准测试；没有证据表明该路线已达到 50 Mbps 接入目标 |
| AP+STA + proxy ARP | 曾短暂考虑；当前不推进 | 项目路线偏好，并非认定技术上不可行 |

## 透明桥接与公开 raw 发送接口

[C5 Wi-Fi 驱动指南](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32c5/api-guides/wifi.html)及已核查的公开头文件，尚不能确认存在受支持、可直接启用的 WDS/四地址透明桥接模式。普通 AP+STA 运行方式不会自动通过透明二层桥接保留下游客户端的 MAC 地址。仅有原始帧注入能力，也不等于具备完整的四地址加密桥接实现。

[v5.5 raw 发送 API 约定](https://github.com/espressif/esp-idf/blob/v5.5/components/esp_wifi/include/esp_wifi.h#L1178-L1203)规定缓冲区长度为 24–1500 B。该缓冲区包含 802.11 MAC 头，并非 1500 B 的应用载荷或 IP MTU。[C5 帧发送文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c5/api-guides/wifi-driver/wifi-vendor-features.html#wi-fi-80211-packet-send)列出 beacon、probe request/response、Action 和非 QoS data 帧，并说明这条公开 raw 路径不支持加密帧及 QoS 帧。这些限制不代表驱动内部所有发送路径的能力。

AP+STA 配合 proxy ARP 不属于当前推进的路线。为完整记录，IPv4 proxy ARP 仍需配合实际 IP 转发和回程路由；仅回复 ARP 并不能形成透明二层转发。DHCP、广播处理及 IPv6 还需分别处理。[RFC 1027](https://datatracker.ietf.org/doc/html/rfc1027)仅作为背景资料，并非已采用的 FarmMesh 设计。

## ESP-NOW 帧格式与特定版本实现证据

ESP-NOW 通过厂商特定的 802.11 Action 帧承载应用数据，无需 IP 或 UDP。v2 格式在一个 Action 帧内串联多个厂商特定信息元素，承载最多 1470 B；这不等同于分片为多个独立的 v1 包。v1 最多支持 250 B。混合版本的接收存在条件限制，因此需核对两端版本和载荷接收能力。参见[官方 ESP-NOW FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html)。

ESP-NOW v2 的 1470 B 应用载荷上限与公开 raw 接口的 1500 B 缓冲区上限，计量的是不同层级。直接比较两者不能得出可用应用载荷或吞吐的比较结果。

对 [ESP-IDF v5.5 Wi-Fi 库 gitlink](https://github.com/espressif/esp-idf/tree/v5.5/components/esp_wifi)所选定的 [C5 `libespnow.a` 静态库](https://github.com/espressif/esp32-wifi-lib/blob/8a1b7bbc00e895d040c5c9a6fb9d1db2bbfc7958/esp32c5/libespnow.a)进行静态检查，发现以下直接调用链：

```text
esp_now_send -> mt_send -> ieee80211_send_action_vendor_spec
```

| 目标文件 / 节 | 重定位偏移 | 调用目标 |
| --- | --- | --- |
| `espnow.o` / `.text.esp_now_send` | `0xe8`、`0x15e` | `mt_send` |
| `manatick.o` / `.text.mt_send` | `0xf8` | `ieee80211_send_action_vendor_spec` |

被检查静态库的大小为 63,178 B，Git blob SHA 为 `1bf0d49f4b910475577058a291c50ac83cb86392`。其符号表没有对 `esp_wifi_80211_tx` 的引用，因此观察到的这一段调用路径不经过该公开 API。这些内部符号不是稳定接口；该观察也不排除驱动更深层或其他版本共用代码的可能性。这不是运行时测试或吞吐测试。

使用上述确切版本的静态库及 ESP RISC-V 工具链，可通过以下命令复核相关证据：

```sh
git hash-object libespnow.a
riscv32-esp-elf-objdump -r -j .text.esp_now_send -j .text.mt_send libespnow.a
riscv32-esp-elf-nm -A libespnow.a | rg 'esp_now_send|mt_send|ieee80211_send_action_vendor_spec|esp_wifi_80211_tx'
```

## MTU、TCP MSS 与 UDP 边界

若自定义链路将一个 IP 包放入一个 ESP-NOW v2 载荷，且不进行链路分片/重组，则其最大 IP MTU 为 **M = 1470 − H 字节**。其中 **H** 是 IP 包之外的全部自定义封装开销，包括任何保留的 Ethernet 头或标签。实际选用的 MTU 可以更小，路径上其他环节也可能施加更小的限制。这是长度预算，并非已选定的封装方案或吞吐预测。

| 项目 | 基于有效 MTU M 的预算 | 前提 |
| --- | --- | --- |
| IPv4 TCP MSS | M − 40 | 固定 20 B IPv4 头和 20 B TCP 头 |
| IPv6 TCP MSS | M − 60 | 固定 40 B IPv6 头和 20 B TCP 头 |
| IPv4 UDP 应用载荷 | M − 28 | 无 IPv4 options；UDP 头为 8 B |
| IPv6 UDP 应用载荷 | M − 48 | 无 IPv6 扩展头；UDP 头为 8 B |

TCP 通告的 MSS 按固定头部计算；发送方仍需进一步减少实际 TCP 数据长度，为 options 或扩展头留出空间。[RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html)说明了这一区别。UDP 没有 MSS：限制 TCP MSS 不能解决过大的 UDP 数据报，而仅修改中间节点的 MTU，也不能保证终端自动减小其 UDP 报文。仍需处理报文长度及路径 MTU。[RFC 8085 第 3.2 节](https://www.rfc-editor.org/rfc/rfc8085.html#section-3.2)

自定义链路分片/重组层可以保留较大的上层 MTU，但目前尚未选定或实现此类方案。未来若设计 IPv6 链路，还必须满足 1280 B 的最小链路 MTU 要求，并在必要时于 IPv6 之下提供适配。[RFC 8200 第 5 节](https://www.rfc-editor.org/rfc/rfc8200.html#section-5)

## 速率、功率与可能的后续自适应

已核查的 [`esp_now_set_peer_rate_config()` 声明](https://github.com/espressif/esp-idf/blob/422c4f5925d9a2408d5ddcc5bb1a95cc46da1e3d/components/esp_wifi/include/esp_now.h)接受按 peer 设置的速率配置，其 [`wifi_tx_rate_config_t` 定义](https://github.com/espressif/esp-idf/blob/422c4f5925d9a2408d5ddcc5bb1a95cc46da1e3d/components/esp_wifi/include/esp_wifi_types_generic.h)包含 `phymode`、`rate`、`ersu` 和 `dcm`。仍需确认目标芯片、对端和 SDK 的支持情况；设置 PHY 速率不保证应用载荷吞吐。芯片标称 PHY 速率和普通 Wi-Fi TCP 基准测试，都不能证明 ESP-NOW 或公开 raw 路径的持续性能。

[Wi-Fi 功率 API](https://github.com/espressif/esp-idf/blob/v5.5/components/esp_wifi/include/esp_wifi.h)设置每颗 C5 的最大发射功率上限，并非按 peer 或按包设置。三颗 C5 可以各自设置上限。参数单位为 0.25 dBm，并不意味着硬件具有连续可用的 0.25 dB 档位，也不意味着每帧都以该功率发射。本次核查不根据通用头文件推断 C5 在各频段的精确最大功率。

在已核查的官方文档、FAQ 和公开头文件中，尚未确认存在可直接启用的 ESP-NOW 自动速率自适应开关或现成官方工具。按 peer 的设置接口提供控制能力，并不等于自动选择算法。这也不能证明所有内部自适应逻辑均不存在。若项目后续需要自定义自适应，一种可能的软件策略是跟踪每个 peer 的发送成功率与耗时、探测更高速率并在失败后降速，同时以 RSSI 作为辅助信息。这属于尚未实现、尚未验证的后续工作，并非已选算法或当前能力。

## 硬件方案延续与待决事项

内部接口候选保持不变：三条独立的 PARLIO ↔ PIO 链路，TX/RX 各使用独立的 4 位数据总线，两个方向的时钟均由对应 C5 提供。每个方向使用 4 DATA + CLK + VALID，即每条链路 12 根信号、三条共 36 根，对照 RP2350B 的 48 个 Bank0 GPIO。这只是资源估算，并非固件或时序验证。共享半双工数据总线需要明确的输出使能、三态及换向控制。参见[内部接口草案](../README.zh-CN.md#候选内部接口)。

无线技术路线、SDK 基线、封装/分片选择、所需速率控制行为及实际有效吞吐仍待确定。本记录用于支持硬件讨论，不启动固件实现，也不改变已有产品目标。
