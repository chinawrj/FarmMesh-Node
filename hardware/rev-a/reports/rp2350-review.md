# RP2350B / USB 独立电气审阅

审阅日期：2026-09-23。范围为 `scripts/build_design.py`、`design-manifest.json`、RP2350B 官方符号及本地 AOTA 电感封装。结论限于原理图连接、器件选择依据和封装引脚对应；没有进行实物上电、USB 枚举、ESD、时序或 PCB 电源完整性验证。本文件不是投板放行记录。

## 已处理的真实问题

初稿将电池分压和 USB VBUS 分压接到 GPIO40/41 的标准 ADC 引脚。RP 掉电时，这些外部电压会高于标准 IO 的 `IOVDD + 0.5V` 绝对最大值；串联大电阻不能单独证明符合电压规格。本版已移除电池采样 R106/R107/C125，GPIO40/41 留空；USB 检测移至 GPIO37（QFN80 pad 46，FT 类型）。电池 ADC 延至下一版，届时需重新设计并验证关断隔离采样。[RP2350 datasheet，Table 1427、1433](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=1337)

### USB VBUS 检测的最终值

`USB_VBUS → R112 5.1kΩ ±1% → USB_VBUS_SENSE → R113 7.5kΩ ±1% → GND`，C126 为 10nF，检测点接 GPIO37。

按本版 VBUS 4.4–5.5V 的设计范围，`Vsense = VBUS × R113 / (R112 + R113)`：

| 检查项 | 计算结果 |
| --- | --- |
| 4.4V、上臂 +1%、下臂 −1% | 2.5978V |
| 5.5V、上臂 −1%、下臂 +1% | 3.3003V |
| 标称 Thevenin 电阻 / RC 时间常数 | 3.036kΩ / 30.36µs |
| 5.5V 标称分压电流 | 0.437mA |
| 下臂最大电阻 | 7.575kΩ |

Table 1436 在 IOVDD=3.3V 时给 FT 的 VIH 最小值为 **2.0V**；不应将 2.31V 写成该表规定值。按表中的 1µA 输入漏电估算，电压偏差约 3.1mV，仍有裕量。Table 1433 给 FT 在 IOVDD=0V 时的电压上限为 **3.63V**，上述掉电输入电压低于该值；这不是直接输入 5V 在掉电时也安全的依据。[RP2350 datasheet，§14.9.1、§14.9.4](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=1340)

固件必须先将 GPIO37 配置为输入并**关闭内部上拉和下拉**，再判断 VBUS；不得将其设为输出。需要考虑 C126 稳定时间及连接/断开去抖，具体时序尚未验证。VBUS 检测是存在性判断，不是精确的电压监测。

RP2350 A2 的 E9 会在输入经过不确定区时产生额外源电流，导致高阻下拉读低失败。最终 7.5kΩ 下臂（含容差）满足官方外部下拉 ≤8.2kΩ 的规避条件；六个 VALID 接收端下拉也已改为 4.7kΩ。仍建议优先采购 A3/A4；这项硬件规避不代表全部硅片勘误均已审阅。[RP2350 datasheet，RP2350-E9，pp.1366–1368](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=1367)

## 最小系统连接核对

| 项目 | 本版实现及核对结果 |
| --- | --- |
| MCU 符号 | 使用 `MCU_RaspberryPi:RP2350B`；81 个引脚（80 个外引脚及 EP81）与官方 QFN80 参考一致，EP 接 GND。 |
| 电源域 | IOVDD、QSPI_IOVDD、ADC_AVDD、USB_OTP_VDD、VREG_VIN 接 3.3V；三个 DVDD 接 CORE_1V1。VREG_PGND 接 GND，VREG_FB 接 CORE_1V1。 |
| 内置 buck | R101 33Ω 与 C101 4.7µF 滤波 VREG_AVDD；C102 为输入旁路，L101 3.3µH，C103 为输出电容；C124 为远端 DVDD 补充 4.7µF。拓扑符合参考。 |
| 去耦 | 电源引脚有对应 100nF；本版还将 USB_OTP_VDD 和 QSPI_IOVDD 分别去耦。位置、回流与选定电容的有效容量尚待 PCB/BOM 核验。 |
| Flash | W25Q128JVSIQ，16MB，`W25Q128JVS` 符号与 5.3×5.3mm SOIC-8 封装；pin 1/2/3/4/5/6/7/8 对应 CS/IO1/IO2/GND/IO0/CLK/IO3/3V3。C104 100nF。 |
| BOOTSEL | QSPI CS 上拉 10kΩ，按钮经 1kΩ 接地。与官方参考方式一致。 |
| 晶振 | ABM8-272-T3 12MHz，XOUT 串 1kΩ，两侧各 15pF C0G，外壳 pads 2/4 接地。实际负载电容包含走线寄生，需短线布局。 |
| RUN / SWD | RUN 使用内部上拉，按钮经 1kΩ 拉低；J101 提供 3V3 参考、SWDIO、GND、SWCLK、RUN。该 5 针顺序为项目自定义接口，调试线须按原理图配接。 |

依据：[Hardware design with RP2350，§2–5](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008280-DS-2-hardware-design-with-rp2350.pdf)，[官方 RP2350B Minimal R4-S1 KiCad 设计](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-010329-CA-1-RP2350B%20Minimal%20KiCAD.zip)。Flash、晶振、BOOTSEL 和 RUN 均按该参考核对；这不等于固件启动配置已测试。

### AOTA 本地封装方向

`FarmMesh.pretty/AOTA-B201610S3R3-101-T.kicad_mod` 与官方 R4-S1 PCB 的 L1 逐项比较：

| 几何项 | 两者相同的局部坐标 / 尺寸（mm） |
| --- | --- |
| pad 1 | 中心 (−0.7, 0)，尺寸 0.7×1.7 |
| pad 2 | 中心 (+0.7, 0)，尺寸 0.7×1.7 |
| 丝印方向点 | 中心 (−1.4, +0.7)，半径 0.15 |
| Fab 方向点 | 中心 (−0.7, +0.55)，半径 0.10 |

焊盘层均为 F.Cu/F.Mask/F.Paste；除板级 net/UUID 属性外，相关焊盘几何一致。官方 L1 和本版 L101 均为 **pad 1 → 1V1，pad 2 → VREG_LX**，没有反向。电感无电气正负极，但此指定器件的绕组方向会影响紧凑 buck 布局；必须保留方向点，并继续遵循官方输出电容相对位置与回流布局。仅复制封装方向不足以证明整个 buck 稳定。[官方参考 KiCad](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-010329-CA-1-RP2350B%20Minimal%20KiCAD.zip)，[硬件指南 §2.1](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008280-DS-2-hardware-design-with-rp2350.pdf#page=6)

## USB 接口核对与边界

D101 `USBLC6-2SC6` 的 1↔6 为同一 I/O1 通路，3↔4 为同一 I/O2 通路；本版分别连接 D+ 与 D−，pin 2 接 GND，pin 5 接 USB_VBUS，方向和通道没有交叉错误。C127 100nF/16V 应放在 D101 的 VBUS 与 GND 附近，参考 ST Figure 17；这颗电容不应被当作板上任意位置的公共旁路。[ST USBLC6-2 datasheet Rev 7，功能图及 Figure 17](https://www.st.com/resource/en/datasheet/usblc6-2.pdf)

R110/R111 为 RP 侧 27Ω 串联电阻；A6/B6 同接 D+、A7/B7 同接 D−；CC1、CC2 各自使用 5.1kΩ 下拉，SBU 留空。USB4105-GF-A 对应 KiCad 的 `USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal`，库内适用型号标注明确包含该 MPN；信号 pad 名与 16 接点连接器一致。此轮核对了型号、接点与安装类型，未完成制造图机械公差逐项复核，应在 PCB 放行前核验板边、定位孔及壳体焊脚。[GCT USB4105 官方页面](https://gct.co/connector/usb4105)

本板必须由电池供电，USB VBUS 只用于检测和 ESD 保护，不能单独给系统供电或给电池充电。应用固件需要随 VBUS 控制 USB attach；**不能据此推定 ROM BOOTSEL 也会读取自定义 GPIO37**。带电 BOOTSEL、拔线、主机掉电时的数据线状态及 USBLC6 向 VBUS 的钳位电流仍需验证。当前没有硬件数据线隔离，因此不能宣称已经完成自供电 USB 合规验证。

后续 PCB 必须核验 buck 回路、选定 4.7µF 电容的 ESR/ESL/有效容量、晶振寄生、USB 90Ω 差分与 ESD 回流路径；当前原理图与封装审阅不能覆盖这些布局结果。电池 ADC 本版无采样功能，USB/PIO/PARLIO 的实测结果也尚不存在。
