# FarmMesh Node A1 硬件设计说明

日期：2026-09-23。A1 投样放行状态以 [RELEASE.md](RELEASE.md) 为准；尚无实物或性能验证。

The A1 eight-sheet KiCad 10 design and 100 × 100 mm four-layer PCB contain one RP2350B, three official ESP32-C5-WROOM-1U-N8R8 modules, a protected 1S Li-ion input and a 3.3 V buck-boost supply. ERC and static connectivity/pad checks do not establish power, RF or interface performance. The prototype release status is recorded in RELEASE.md. Charging/solar power and application firmware remain future work.

## 打开与文件

使用 KiCad **10.0.5 或兼容的 KiCad 10** 打开 [FarmMesh-Node.kicad_pro](FarmMesh-Node.kicad_pro)，再进入原理图编辑器。需安装 KiCad 标准符号及封装库；项目表使用 `KICAD10_SYMBOL_DIR` / `KICAD10_FOOTPRINT_DIR`，项目自建库通过 `${KIPRJMOD}` 引用。无需插件即可编辑。

| 文件 | 用途 |
| --- | --- |
| [八页 PDF](review/FarmMesh-Node-A1.pdf) | 索引、电源、RP2350B、三页 C5、USB、测试及机械 |
| [BOM.csv](BOM.csv) | 153 个已定料装配元件与 11 个 PCB 特征；下单用 manufacturing/assembly/BOM-assembly.csv |
| [gpio-pinmap.csv](gpio-pinmap.csv) | 全部 36 条链路信号，C5 GPIO/模组焊盘与 RP GPIO/封装焊盘 |
| [ERC](reports/erc.json) | KiCad 原始检查结果 |
| [网表及焊盘核对](reports/connectivity-and-footprints.json) | 实际导出网表与已加载封装的结构检查 |
| [电源审阅](reports/power-review.md)、[RP 审阅](reports/rp2350-review.md)、[C5 审阅](reports/c5-review.md) | 独立检查、官方依据及待验证边界 |

索引页的子图框使用全局网络标签连接，框本身没有层次端口。`TX` / `RX` 始终从 C5 视角命名。五个 PWR_FLAG 只是 ERC 驱动声明，不是物料；164 个板上对象之外另有这五个标记。

## 硬件决策

### 电池与 3.3 V 电源

- J1 接常规 **1S、标称 3.7 V、满充 4.20 V** 的锂离子电池包，pin1 正极、pin2 负极。必须使用带过充/过放/过流保护的电池包，连接器、导线与保护板需支持至少 5 A 峰值。不能接 2S、LiFePO4 或高压锂电池。
- F1 为 5 A Littelfuse 0451005.MRL；Q1 DMP2008UFG-7 实现反接保护，D 面向电池、S 面向负载。KiCad PowerDI3333-8 把物理 D 脚 5–8 及底部铜区合并为 pad5，符号因此也只用 D pad5。保险丝和本板 UVLO 不代替电芯保护。
- LTC3119IFE#PBF 使用官方 TA06 3.3 V / 500 kHz 电路为起点。4.7 µH XAL7070-472MEC，反馈 316 kΩ / 100 kΩ，输出标称 3.307 V。78.7 kΩ + 820 pF 补偿是起始值，附加模组电容后的环路稳定性尚未测量。
- MPPC 接 VCC 关闭该功能，本稿不是 MPPT；PWM/SYNC 接地允许 Burst。VCC 是内部辅助电源，不得直接短接到 3V3；D1 阳极 3V3、阴极 VCC。PGOOD 仅给 RP 检测，不直接拉三颗 C5 的 EN。
- RUN 174 kΩ / 100 kΩ：标称启动约 3.30 V、停止约 3.01 V，受器差和负载压降影响。电压低于启动点的电池可能不能冷启动。J2 短接将 RUN 拉低用于关机；仅触发 UVLO 不能等同于数据表的完整关断电流。
- C7 6SVPE220M 为 Panasonic C6 外形，使用 `CP_Elec_6.3x5.9`。C6 输入选 10SVPC120M（120 µF / 10 V）；各 C5 选 6SVPC100M（100 µF / 6.3 V），封装分别为 6.3 × 5.9 mm 和 5 × 5.9 mm。输出共有 520 µF 聚合物电容，分布电容对启动和环路的影响仍须实测。22 µF MLCC 的官方 25°C 直流偏压典型数据和重放记录见 parts-selection.json，不将典型值当全温最小保证。

| 预算项目 | 当前设计输入 |
| --- | --- |
| 三颗 C5 | 每颗供电能力至少 0.6 A，共 1.8 A；不是宣称连续耗电 0.6 A |
| RP、Flash、外围和余量 | 0.4 A 暂定预算 |
| 3V3 总预算 | 2.2 A；3 A 作为瞬态验证目标，不能当成全输入/温度范围连续额定值 |
| 电池端估计 | 在输入 3.0 V、假设效率 80% 时，2.2 A 输出约需 3.03 A；3 A 输出约需 4.13 A |

效率 80% 是预算假设，尚未测得；此计算未保证低温电池、保险丝、线缆及 Q1 压降后的性能。LTC3119 的开关/电感电流限制不是输出电流保证。电源和电池容量不能据此直接换算太阳能板尺寸或续航。

本版**没有充电器、太阳能输入、电池电量监测或 USB 供电路径**。电池 ADC 原方案已移除，避免 3V3 关闭时仍将电池分压施加到非 FT 的 ADC 脚；后续需要带关断隔离的采样电路。

### RP2350B 最小系统

RP2350B 的 QFN80 + EP81、外置 16 MB W25Q128JVSIQ、12 MHz ABM8-272-T3、USB、SWD、BOOTSEL 与 RESET 均已连接。IOVDD / USB_OTP_VDD / QSPI_IOVDD 等接 3.3 V，DVDD 接核心 1.1 V。

核心使用 **RP 内部 buck**，不是 LDO：VREG_LX 经 3.3 µH 到 CORE_1V1，再接 VREG_FB / DVDD。L101 使用官方 R4-S1 的带方向 Abracon 封装，**pad2=LX，pad1=1V1**；换电感时不能只比较电感量。VREG_AVDD 经 33 Ω、4.7 µF 滤波；核心输出及远端 pad32 各有 4.7 µF，并给各电源脚单独 100 nF。

GPIO0–35 分配三组接口，GPIO36 为 PGOOD，GPIO37（FT pad46）检测 USB VBUS，GPIO38–47 保留。A3/A4 硅片优先；为兼顾 A2 E9 漏电问题，VALID 接收端下拉用 4.7 kΩ，USB 检测下臂用 7.5 kΩ，均小于官方 8.2 kΩ 规避阈值。仍需在选定硅片上实测。

### 三个 ESP32-C5 模组

U201/U301/U401 均选官方 **ESP32-C5-WROOM-1U-N8R8**：8 MB Flash、8 MB PSRAM、外置天线接口。每颗需独立的 2.4/5 GHz 天线及适配 ANT1 的线缆，已选配套 MPN 见 parts-selection.json 的 accessories；默认不用模组 ANT2 pad31。此 1U 型号没有 PCB 天线，不应机械套用 PCB 天线版的 15 mm 天线区规则；仍须规划连接器空间、天线摆放及三射频之间隔离。

每模组 22 µF + 100 nF 近 pad2，100 µF 聚合物电容提供本地储能。EN 采用 10 kΩ / 1 µF，GPIO27 和 GPIO28 各 10 kΩ 上拉；BOOT 将 GPIO28 拉低，RESET 拉低 EN。按住 BOOT、脉冲 RESET 进入 UART 下载。

J201/J301/J401：1 GND，2 C5 TX，3 C5 RX，4 EN，5 BOOT，6 3V3 参考。使用 3.3 V 逻辑的 UART 适配器；pin6 是参考输出，不是另一电源入口。RP SWD J101：1 3V3 参考，2 SWDIO，3 GND，4 SWCLK，5 RUN。

### 候选 PARLIO ↔ PIO

| C5 侧信号 | C5 GPIO（模组 pad） | RP A / B / C GPIO | 驱动端 |
| --- | --- | --- | --- |
| TX_D0..3 | 0(6), 1(7), 13(13), 14(14) | 0–3 / 12–15 / 24–27 | C5 |
| TX_CLK | 4(17) | 4 / 16 / 28 | C5 |
| TX_VALID | 5(16) | 5 / 17 / 29 | C5 |
| RX_D0..3 | 6(8), 8(10), 9(11), 10(12) | 6–9 / 18–21 / 30–33 | RP |
| RX_CLK | 23(21) | 10 / 22 / 34 | **C5** |
| RX_VALID | 24(23) | 11 / 23 / 35 | RP |

所有接口避开启动绑带脚和内部 Flash/PSRAM 脚；C5 GPIO13/14 的 USB 功能被让给数据线，因此三颗 C5 通过 UART 下载。GPIO13/14 启动时可能出现 USB 状态变化，RP 必须保持输入，直到 C5 配置完成且 VALID 生效。

每条信号有初始 22 Ω 串联电阻，布板时放在**驱动端**，不能因它画在 C5 页就一律放在 C5 旁。TX_VALID 的 4.7 kΩ 下拉在 RP 端，RX_VALID 的下拉在 C5 端；任一芯片复位后均需重建收发状态、清理 FIFO / 事务。

PIO0 GPIOBASE=0 负责 A；PIO1 GPIOBASE=0 负责 B；PIO2 GPIOBASE=16 负责 C。C 路 GPIO28/34 在相应窗口中的 WAIT GPIO 索引为 12/18，不能把 34 直接塞入 5 位立即数。每路双向各一个状态机、DMA 共约六路仅是资源估算。PARLIO RX 要预先挂好接收事务，RX clock 输出不代表接收已准备好。实际 PIO 程序、指令预算、采样边沿、首拍时序、DMA 重装、持续全双工以及 50 Mbps 均未验证。

### USB 边界

J102 USB4105-GF-A 只用于 RP 数据；VBUS 不给板供电，也不充电，使用时仍需电池。CC1/CC2 各 5.1 kΩ，D± 经 USBLC6-2SC6、TS3USB30EDGSR 数据开关及靠 RP 的 27 Ω 串联电阻。USBLC6 的 I/O 是 1↔6 与 3↔4 直通对，VBUS 有 100 nF。

VBUS 通过 5.1 kΩ / 7.5 kΩ 接 GPIO37。按 1% 电阻及 4.4–5.5 V VBUS，检测电压约 2.598–3.300 V，低于 FT 脚 IOVDD=0 时的 3.63 V 上限；程序检测前应关闭 GPIO37 内部上下拉。A1 增加 TLV3011BIDBVR（必须 B 版本）与 237 kΩ / 100 kΩ 比较网络，在 VBUS 低于标称约 4.19 V 时将开关 /OE 拉高；10 kΩ 默认上拉使 USB 物理断开，不依赖应用程序或 ROM 读取 GPIO37。容差、失电、欠压及电源先后顺序仍须按首板指南测量；Ioff 规格不代表任意欠压条件。

## 布局与校验

A1 使用 100 × 100 mm、四层 1.6 mm 板；F.Cu / In1.GND / In2.GND / B.Cu。JLC04161H-3313 叠层、USB 90 Ω 主干几何和制造公差见 [FABRICATION.md](FABRICATION.md)。两内层保留为参考地，RP buck 的 LX 下方仅在相邻 In1.Cu 局部避空。三路 C5 电源主干为 1.5 mm，RP 支路为 1.0 mm；局部电源回路、QSPI、晶振和 USB 先行布线，再完成普通信号。

153 个装配元件均有明确 MPN，7 个裸铜测试点及 4 个安装孔为 PCB 特征。三颗 C5、RP 和 LTC 的接地过孔均置于实际 EP 锡膏窗口之外，采用普通 tenting；这不等同于树脂填孔或保证封孔。M3 螺钉头部区域禁布外层铜。

最终 ERC、DRC、未连接、原理图一致性以及逐焊盘几何校验以 reports 中绑定最终文件 SHA 的报告为准。三份 A1 独立审阅分别覆盖电源、RF/数字接口和定料/制造；原 A0 审阅记录仅保留为历史。

[首板验收指南](FIRST-BOARD-TEST.md) 给出分阶段限流上电、3V3/1V1、UVLO、UART/SWD/USB、环路/负载/温升及射频测试。2.2 A 总输出和 3 A 脉冲是验证目标，50 Mbps 板内链路、用户吞吐与无线共存尚未测得。投样文件通过静态检查不能代替这些实测。

## 重生成与来源

原理图可直接在 KiCad 编辑。`scripts/build_design.py` 是本稿生成源，**重新运行会覆盖全部原理图与项目自建符号库**；先保存手工改图，或将变更回写生成器。依赖 Python 3 和 `sexpdata`，通过环境变量 `KICAD_SHARE` 指向 KiCad `SharedSupport`；未设置时脚本使用本次 macOS 安装位置。验证器需要 KiCad 自带 `pcbnew` Python。

```sh
python3 scripts/build_design.py
for sheet in *.kicad_sch; do kicad-cli sch upgrade "$sheet"; done
kicad-cli sch export netlist --format kicadxml -o reports/netlist.xml FarmMesh-Node.kicad_sch
kicad-cli sch erc --format json --severity-all -o reports/erc.json FarmMesh-Node.kicad_sch
kicad-cli sch export pdf -o review/FarmMesh-Node-A1.pdf FarmMesh-Node.kicad_sch
# 用能 import pcbnew 的 Python 运行：
python3 scripts/verify_design.py
```

关键引用见三份审阅记录：[Espressif C5 模组 v1.3](https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf)、[RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf)、[RP 硬件设计指南](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008280-DS-2-hardware-design-with-rp2350.pdf)、[LTC3119 Rev B](https://www.analog.com/media/en/technical-documentation/data-sheets/3119fb.pdf)。链接内容可能更新，选型重新冻结时需复核版本。

L101 footprint 的几何和方向标记提取自 Raspberry Pi 官方 RP2350B Minimal R4-S1，去掉了原工程专属元数据和不可独立解析的内嵌 3D 引用；保留其 [MIT 许可](third-party/raspberry-pi-reference-LICENSE.txt)。[参考设计下载](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-010329-CA-1-RP2350B%20Minimal%20KiCAD.zip)。其余标准符号/封装依赖 KiCad 库，自建 C5 焊盘按官方尺寸绘制。本文件不为整个项目额外指定许可证。

`build_pcb.py` 只重建放置与关键走线底稿，**不会重现最终普通信号布线，不能覆盖发布板后直接下单**。最终原生 PCB 是完整布线的权威源；`verify_pcb.py` 为只读核查。`export_manufacturing.py` 与封包脚本在冻结源上生成并核验制造输出。
