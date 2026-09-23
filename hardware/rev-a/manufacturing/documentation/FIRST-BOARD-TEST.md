# FarmMesh Node A1 — 首板分阶段验收 / First-board staged acceptance

**状态 / Status: TEST PLAN — NOT EXECUTED / 验收计划，尚未执行。**

日期 / Date: 2026-09-23。本文不包含实测结果，也不保证 2.2 A、3 A、USB 或无线吞吐已经达到。记录板号、制造包版本/哈希、BOM 替代料、RP2350 silicon revision、固件与工具版本、仪器/探头、环境温度、输入线长、负载设置及波形文件。每阶段通过后再进入下一阶段；失败时保留证据并断电排查，不靠提高限流掩盖异常。

This is an unexecuted test plan, not a performance certificate. Record board/release identifiers, substitutions, silicon revision, firmware/tool versions, instruments, ambient temperature, input wiring, load settings and waveform files. Resolve failures before advancing. Use the final schematic, [manufacturing specification](FABRICATION.md) and [power review](reports/a1-power-review.md) together with this plan.

## 1. 上电前 / Before power

- 用显微镜检查 QFN/USB/0402 桥连、虚焊、移位；核对所有 IC pin 1、D1/Q1、聚合物电容正极和 L101 定向标记。L101 pad1=CORE_1V1、pad2=LX。核对 ENIG 表面无污染/露铜异常、板厚、USB 机械孔与外侧地焊盘、四个 φ3.2 mm NPTH。隐藏 EP 的装配质量需合适的检查方法；外观看不见不等于焊接合格。
- Microscope-inspect bridges, opens and alignment; check IC pin 1, diode/MOSFET orientation, capacitor polarity and the marked inductor. Check ENIG condition and mechanical fit; inspect hidden exposed-pad joints appropriately.
- 完全断开电池、USB、SWD、UART 与电子负载电源。检查 BAT_PLUS→GND、TP1→GND、TP2→GND、TP101→GND，以及 3V3↔CORE 是否存在持续硬短路。等待电容充电读数稳定、交换表笔观察半导体路径，记录欧姆/二极管档结果；没有适用于所有节点的统一“低于某欧姆即短路”阈值。不要用高压绝缘测试仪测芯片。
- Disconnect every power/data source. Record rail-to-ground and 3V3-to-core resistance/diode readings after charging transients settle. Semiconductor paths make a universal resistance threshold inappropriate; investigate persistent near-zero resistance.
- J1 pin1=BAT_PLUS、pin2=GND，使用合适受保护的常规 1S、4.20 V 最高锂电源。首测使用台式电源。释放任何可能运行发射固件的 C5 之前先接好相应天线。本板没有充电器，USB VBUS 只用于检测/ESD；**USB、SWD 和 UART 的 3V3 参考脚都不是供电入口**。
- J1 is the sole normal power input. USB does not power the board or charge a cell. Debug 3V3 pins are references only. Keep all adapters disconnected during initial rail tests. Attach the antenna before releasing any C5 that may run transmitting firmware.

## 2. 限流上电 / Current-limited bring-up

以下电流均为**台式电源的输入限流**，不是 3V3 输出负载。数值是逐级诊断建议，不是已测空载电流规格。初始设 3.8 V（首测范围 3.6–4.2 V），短粗线接 J1，电源关闭时接线。

These are **input current limits**, not output-current ratings. They are diagnostic starting settings. Start at 3.8 V within the 3.6–4.2 V initial range, using short adequately sized leads connected with the supply disabled.

| 阶段 / Stage | 建议输入限流 / Suggested limit | 操作及通过条件 / Action and gate |
| --- | ---: | --- |
| 转换器关闭 / Converter off | 20 mA | J2 装 OFF 帽；上电检查 TP1 接近输入、3V3 不应被外部供电、无异常发热或持续限流。暂态充电后记录关机电流 / fit J2, check input rail, no back-power or heating; record settled off current |
| 电源及复位 / Rails, reset held | 100 mA；必要时经排查升至 300 mA / then 300 mA after inspection | 断电后将三 C5 EN 拉低并让 RP_RUN 保持低；移除 J2 再上电。检查 3V3、core 和启动波形。充电期间限流不立即等于短路；持续打嗝则先查波形和焊接 / hold resets, remove J2 and inspect rails/startup before increasing limit |
| RP 单独运行 / RP only | 300 mA | 仅释放 RP_RUN，其余 C5 保持复位；读取 SWD/ROM，记录输入电流和温度 / release RP only, verify SWD/ROM |
| 单个 C5 / One C5 | 先 1.0 A，确认后最多 1.5 A / 1.0 A then up to 1.5 A | 每次只释放一个模组，先 UART ROM/无 RF 固件，再受控 RF；确认电流变化与活动一致 / enable one module at a time, ROM/no-RF first |
| 系统及负载 / System and load | 依据实测功耗逐步升至 3.5 A；低压 3 A 输出脉冲试验可需 4.5 A / up to 3.5 A, or 4.5 A for validated low-input pulses | 只在前级通过后进行；不能超过线束、连接器、电源和保护路径能力 / only after previous stages pass and test path supports the current |

临时复位夹具只接指定 EN/RUN 与 GND，避免误碰 3V3；RP 可用 J101 pin5 或 SW102，C5 可用对应 UART pin4 或 RESET。记录夹具接法。RUN 拉低不是 RP buck 断电，core 仍应检查。出现输出过压、持续限流、冒烟/异味或温度快速上升即断电；不要长时间让芯片在反复 brownout 中运行。

Connect reset fixtures only to the identified reset nets and ground, and document them. RP RUN reset does not disable its switching regulator. Stop for unexpected overvoltage, persistent current limiting or rapid heating. Do not use repeated brownout as normal operation.

## 3. 测点和启动预期 / Test points and expected nominal behavior

| 测量 / Measurement | 位置 / Access | 名义预期及限制 / Nominal expectation and limit |
| --- | --- | --- |
| 输入 / Protected input | TP1 对 TP3 / TP1 to TP3 | 接近 J1 输入减去 F1/Q1/线损；记录启动和加载压降 / near input minus protection/wiring loss |
| 主轨 / Main rail | TP2 对 TP3；再测 C201/C301/C401 正端与就近地 / then each module local supply | `0.795×(1+316/100)=3.3072 V` nominal；每个 C5 端包括瞬态维持 3.0–3.6 V；最终稳定目标应比此工作极限留余量 / retain margin inside the operating range |
| RP core | TP101 对 TP102 / TP101 to TP102 | 默认约 1.1 V；记录纹波/启动，不擅自提高 core 或超频 / approximately 1.1 V default; no initial overclocking |
| RP reset | TP103 或 J101 pin5 / TP103 or J101 pin5 | 释放时接近 3V3，按 SW102 应变低并触发复位 / high when released, low on reset |
| PGOOD | TP104 | 稳压后由 R6 拉至 3V3；输出欠压应变低；不能代替高速示波器抓取短毛刺 / high when regulated; not a substitute for ripple captures |
| 转换器 RUN / Converter RUN | J2 pin1，参考 J2 pin2 GND / J2 pin1 to pin2 | J2 开路约 `VIN/2.74`，含小滞回电流修正；短接 J2 接近 0 V，停止转换 / divider level when open, low with OFF shunt |
| UVLO | 同时记录 TP1、J2 pin1、TP2、TP104 / capture together | 输入上升启动约 3.30 V、下降停止约 3.01 V；受器件/阻值公差及输入压降影响 / nominal only |
| USB reference / OE | U104 pin5、U103 pin9 / use fine probes | 有 3V3 时 REF≈1.242 V；无 VBUS 时 OE≈3V3、断连；有效 VBUS 时 OE 低 / reference and disconnected/enabled states |

电源输出、RUN 阈值和 PGOOD 依据 [LTC3119 电气表及应用说明](https://www.analog.com/media/en/technical-documentation/data-sheets/3119fb.pdf)；core/reset/ROM 依据 [RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf)。C5 供电范围依据 [模组 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf)。所有名义值均待实测，电池 ADC 本版没有安装，不能用软件读取代替这些测量。

Nominal targets follow the cited device documents and actual resistor values. There is no battery ADC circuit in this revision; software cannot replace the input-voltage measurements.

## 4. RP2350 SWD、Flash 和 USB ROM / RP debug and ROM

J101 针序 / pinout: **1=3V3 reference, 2=SWDIO, 3=GND, 4=SWCLK, 5=RUN**。使用支持 RP2350 的探针/软件，先低速 SWD 连接、读芯片和复位状态，再运行 RAM 小程序、测试外部 W25Q128JVSIQ（标称 16 MB）读写。记录工具与二进制哈希。初始不编程 OTP/security bits；读取 silicon revision，优先验证 A3/A4，但不能因偏好批次忽略 A2 的输入泄漏约束。

Use an RP2350-capable probe at a conservative SWD clock. Identify silicon, test a RAM program, then validate the external flash. Do not program irreversible OTP/security settings during bring-up. Keep the three C5 devices reset for these initial tests.

USB BOOTSEL：板由 J1 独立供电；保持 SW101 BOOTSEL，按下/释放 SW102 RESET，复位采样后释放 BOOTSEL。连接带数据线芯的 USB 线，确认 ROM USB/UF2/PICOBOOT 可枚举并完成已知测试镜像传输/校验。重复拔插和复位；本步检验晶振、PHY、mux、ESD 与主机路径，不代表 USB 电气认证。RP 固件必须禁用 GPIO37 内部上下拉。

With J1 power present, hold BOOTSEL while pulsing RESET, then release BOOTSEL after reset sampling. Verify ROM enumeration and a known test-image transfer/checksum. Repeat cable and reset cycles. Disable internal pulls on GPIO37 in application firmware.

## 5. USB 断连和电源顺序 / USB disconnect and power sequencing

使用可观测 VBUS 的 USB breakout，不向计算机端口反送外部电源。先无主机做受控 VBUS 扫描，再接真实主机测功能。记录 USB_VBUS、USB_DISCONNECT/OE、板端和连接器端 D+/D−、3V3。连接器端电平应在明确的主机端负载下判断，浮空探头读数不能证明隔离。

Use a breakout without back-feeding a host. Characterize VBUS switching without a host first, then test real enumeration. Capture VBUS, OE, both sides of the data path and 3V3; judge connector-side levels with a defined host-side termination.

| 电源组合 / Power case | 必须验证 / Required observation |
| --- | --- |
| J1 有电，VBUS=0 / Battery on, VBUS absent | OE 高；包括 ROM BOOTSEL 在内，连接器端不得被 RP 上拉造成假连接，也不得抬高 VBUS / disconnect even while ROM drives its internal pull-up |
| J1 有电，VBUS 正常 / Both present | 门限名义约 4.186 V 后允许连接，正常枚举 / qualify VBUS then enumerate |
| J1 无电，VBUS 正常 / Board off, VBUS present | 3V3/core 不应经 USB 被有效反供；测实际泄漏，不声称数学零 / no meaningful back-power; measure leakage |
| 任一电源先上/先下 / Every power order | 快/慢坡、掉电、重复插拔及阈值附近均无持续误连接/反灌 / no sustained false attach or back-power |

对无 VBUS 的 ROM 模式，**硬件必须断开**，不能依赖 GPIO37 应用固件。TLV3011B 的 POR/fail-safe 与 TS3USB30E 的 Ioff 支持该方案；U103 VCC 推荐工作下限为 3.0 V，0–3.0 V 的欠压过程还需实测，不能把 VCC=0 的 Ioff 指标当整个慢降过程的保证。门限容差估计和器件出处见 [DFM 审阅](reports/a1-dfm-bom-review.md) 与 [电源审阅](reports/a1-power-review.md)。

Hardware must disconnect the connector when VBUS is absent, including ROM operation. Measure brownout behavior as well as fully powered/off states; an Ioff specification at zero supply does not qualify every intermediate voltage.

## 6. 三个 C5 UART 下载 / Three C5 UART programming ports

| 模组 / Module | UART | RESET | BOOT |
| --- | --- | --- | --- |
| A / U201 | J201 | SW201 | SW202 |
| B / U301 | J301 | SW301 | SW302 |
| C / U401 | J401 | SW401 | SW402 |

三个 UART 针序相同 / common pinout: **1=GND, 2=C5 TX → adapter RX, 3=C5 RX ← adapter TX, 4=EN, 5=BOOT/GPIO28, 6=3V3 reference**。适配器只用 3.3 V 逻辑，共地；手动下载通常只接 pin1/2/3，pin6 默认不接。普通 USB-UART 的 3V3/VCC 常是电源输出，不可当 VTref 接入；不接 5 V/供电脚，不假设 DTR/RTS 已具有自动下载电路。

Use 3.3 V UART logic and a common ground. Cross TX/RX as shown. Manual download normally uses pins 1/2/3 only; leave pin6 open unless the instrument has a genuine voltage-reference input. A USB-UART 3V3/VCC output is not VTref. Do not connect adapter power or assume automatic-reset circuitry exists.

逐个模组操作：先维持 RP 接口高阻/复位，其他 C5 复位。按住 BOOT，将 RESET 拉低至少 10 ms 后释放，继续保持 BOOT 约 100 ms 再释放；确认 GPIO27 高。先用支持 ESP32-C5 的 esptool 读取芯片与 flash ID，再烧录明确为 N8R8 配置的最小 UART/无 RF 测试固件并校验；记录 flash/PSRAM 检测结果。正常运行时释放 BOOT 后再次 RESET。[Espressif C5 boot-mode documentation](https://docs.espressif.com/projects/esptool/en/latest/esp32c5/advanced-topics/boot-mode-selection.html)。

Test one module at a time with RP pins high impedance and the others reset. Hold BOOT, pulse RESET low for at least 10 ms, then retain BOOT for about 100 ms after reset release. Verify GPIO27 high. Read identification before flashing a known N8R8 test image; test both flash and PSRAM. Release BOOT and reset for normal execution. These manual timing suggestions are intentionally slow, not throughput requirements.

C5 原生 USB 引脚用于并行总线；本板 C5 不通过 J102 下载。开机 USB D+ 默认行为可能出现在数据引脚上：RP 在 C5 配置完成并有效断言 VALID 之前不得解释这些电平为业务数据。

The C5 native USB pins serve the parallel interface. J102 programs the RP, not the radios. Ignore startup transitions until the interface is configured and VALID is asserted.

## 7. 电流、低压、温升与环路 / Current, undervoltage, thermal and loop tests

先禁用 RF，以已知电子负载检验电源，再加入真实芯片活动。电子负载**吸收**电流，不能把外部电源接到 3V3。TP 只是探测焊盘；大电流负载使用确认能承载电流的电源/地焊接引线或夹具，不让测试点、细探针或单个普通 via 承担 3 A。

Use a sinking electronic load before adding real RF traffic. Do not drive 3V3 from an external source. Attach high-current fixtures to suitable supply/ground copper; tiny test pads and probe leads are measurement access, not a 3 A connector.

1. 从轻载开始，按 **0.2 → 0.6 → 1.2 → 1.8 → 2.2 A 总 3V3 负载**分级。总数包括芯片自身电流，不能在已耗 2.2 A 的板上再加 2.2 A 电子负载。每级记录输入功率、各支路电压、效率与温度。
2. 在 4.2、3.8、3.3 V 以及**实测 UVLO 以上**的低压点重复；低压测试先在 3.8 V 启动后降压。慢扫通过 UVLO 验证关断/恢复滞回、输入线压降和电池/BMS模拟串阻。不宣称 2.8 V 满载工作。
3. **2.2 A 连续是设计验收目标**：保持至热稳定，建议至少 15–30 min，且连续 5 min 温变小于约 1°C；记录环境、风速/外壳、U1/L1/Q1/F1/J1 和三个模组温度。没有经验证的封装热模型时不把表面温度直接等同结温。初测可用 80°C 外壳/器件表面作保守中止点，它不是器件额定值；提高温度/环境范围须另评估。
4. **3 A 是总输出脉冲目标**：先 2.2↔3.0 A、100 µs、约 1% 占空比，波形正常后扩展至 1 ms/10 ms、最高 10% 占空比的明确定义场景；记录实际上升/下降时间和重复率。之后按真实无线包络调整。不能由短脉冲通过推断 3 A 连续额定。
5. 做轻载↔中载、0.6↔1.8 A、1.8↔2.2 A 与上述 3 A 步进；同时观察转换器端及最远模组端。短地弹簧或同轴/差分探头测纹波，记录带宽限制（例如 20 MHz）、另留全带宽异常检查。记录最小/最大电压、振铃衰减、恢复时间；任何持续振荡、反复复位、模块端越出 3.0–3.6 V 均须停测排查。
6. 输出网络包括 220 µF + 3×100 µF 聚合物，以及已查得偏压衰减的陶瓷；保留补偿/负载模型。负载步进正常不能直接宣称相位裕度合格，需要时做正式环路增益测量。Buck/boost 交界、Burst 轻载和低输入都是必测点。

Step through **total** 3V3 loads of 0.2, 0.6, 1.2, 1.8 and 2.2 A, including the board's own current. Repeat at the stated inputs and sweep actual UVLO after starting above its threshold. Characterize 2.2 A until thermal equilibrium; document environmental conditions and surface temperatures without claiming junction temperature. Begin 3 A pulses at 100 µs/1% duty and extend only after clean waveforms, recording duration, duty and slew rate. Measure regulator and remote-module rails using short-ground probes. Stop for sustained oscillation, repeated reset or supply excursions outside the module range. Load-step testing is not a direct phase-margin measurement.

假设效率 80% 时 `Iin=3.3×Iout/(VIN×0.8)`：3.0 V 输入、2.2 A 输出约 3.03 A 输入；3 A 输出约 4.13 A。这是限流/线束规划估计，不是测得效率；不要把输出限流与输入限流混用。

At an assumed 80% efficiency, 3.0 V input requires about 3.03 A for 2.2 A output and 4.13 A for a 3 A pulse. Replace this planning estimate with measured efficiency and current.

## 8. RF、并行链路及结果记录 / RF, parallel links and records

发射前给三个模组分别接好选定 **2.4/5 GHz、50 Ω 天线及 MHF I 同轴**，核对插头完全扣合、线缆应力和天线位置。先单模组、再双模组、最后三模组并发；分别记录 2.4/5 GHz 的信道、带宽、发射功率、距离、环境、丢包/重试/吞吐和电源波形。天线安装、互扰与认证适用范围须独立评价；没有这些条件的“速率数字”不可比较。

Connect the selected dual-band 50 Ω antennas before transmitting. Test one, two, then three radios, documenting RF settings, antenna placement, environment, retries/loss, throughput and rail waveforms. This test does not establish regulatory certification.

本仓库当前硬件不等于已有业务固件。PIO/PARLIO 先以低时钟、单链路、已知计数/CRC 图样测试，再逐级升频；两方向时钟均由该 C5 输出，RP 只驱动 RX_D[3:0]/RX_VALID。接收事务预先排队，验证 VALID 空闲低、复位高阻、启动毛刺屏蔽、丢帧恢复、DMA/FIFO 饥饿，以及每条线在**接收端**的 setup/hold 和阈值。PIO 分组为 BASE0/0/16；WAIT pin 窗口、同步器延迟和每样本指令数由实际程序验证。

There is no validated application firmware yet. Begin with low-clock single-link counter/CRC traffic, then increase rate. Each C5 supplies both clocks; RP drives only its RX data/VALID outputs. Pre-arm receive transactions and verify startup/reset behavior, underrun/overflow handling and timing at each receiver. Verify PIO window/WAIT mapping and actual instruction/synchronizer timing in the implemented programs.

### A1 冻结走线的重点波形 / Priority waveform captures for the frozen A1 routing

本项是 **NOT RUN**。依据 [最终 RF/digital 审阅](reports/a1-rf-digital-review.md)，A1 已接受以下源端绕行和九处回流距离偏差用于受控原型；这不放行额定 50 Mbps 时序。使用低电容探头、短接地弹簧或合适差分探头，记录探头负载；细间距脚采用可靠的探测夹具，避免短接相邻脚。先单链路低时钟，逐级升频，并记录驱动设置。降低时钟频率不等于降低边沿速度，仍须观察过冲、欠冲和振铃。

These are unexecuted acceptance gates for the approved prototype deviations, not a speed qualification. Use low-capacitance probes and short ground connections, document loading/driver settings, and capture source and receiver waveforms before each clock-rate increase. A lower repetition rate does not itself remove fast-edge ringing.

| 重点信号 / Signal | 具体测量位置 / Probe points | 必须记录 / Required evidence |
| --- | --- | --- |
| A_RX_D0：源端 17.185 mm、4 vias | U101.3（RP 源端）；R216.2（电阻源端侧）、R216.1（负载侧）；U201.8（C5 接收端） | 与 A_RX_CLK 同时捕获，比较电阻两侧和接收端过冲、振铃、稳定时间及 setup/hold；此为最高优先级 / highest-priority source-tail and receiver-timing capture |
| A_RX_VALID：12.302 mm、2 vias | U101.9；R221.2 / R221.1；U201.23 | 启动、空闲、稳态和丢帧恢复时的电平、阈值、边沿及 VALID 采样窗口；不得有假断言 / no false or late VALID assertion |
| C_RX_D1：11.778 mm、0 vias；源端直距10.338 mm | U101.39；R417.2 / R417.1；U401.10 | 与 C_RX_CLK 对照的接收端数据眼/阈值及 setup/hold；不要仅凭发送端波形判定 / receiver-side margin, not only source appearance |
| B_TX_CLK：一处换层孔离最近 plated GND 2.318 mm | U301.17；R314.1（源端侧）/R314.2；U101.16（RP 接收端） | 源/收时钟振铃、阈值重复穿越、占空比、相关数据/VALID 的相位与裕量 / clock integrity and related-data timing |
| B_RX_VALID：一处回流邻孔距离3.195 mm | U101.23；R321.2 / R321.1；U301.23 | 接收端 VALID 的稳态及复位恢复时序 / steady-state and reset-recovery VALID timing |

九个超过 **2 mm 项目启发阈值**的网是 A_RX_D0、A_RX_D3、B_RX_D0、B_RX_D1、B_RX_D3、B_RX_VALID、B_TX_CLK、C_RX_D2、C_TX_D2；准确过孔坐标和 2.154–3.425 mm 距离见审阅表。2 mm 不是器件厂商硬限。除了上表重点，完整覆盖这些数据线的接收端时序；多无线并发和低输入电压下复测。下一版优先缩短 RP 到源端电阻的绕行，并在全局布线前保留换层接地空间。

The nine exceptions are accepted only for this controlled prototype. Include every listed receiver in the timing sweep and repeat under concurrent radio activity and low-input conditions. The next layout should shorten RP-to-series tails and reserve return-via access before routing other nets.

每级并行链路时钟测试须同时运行 QSPI/Flash 读写校验或已知数据 CRC/XIP 压力，并由单 C5 扩展至三 C5 并发；记录存储器错误、复位、USB 枚举/传输失败、FIFO/DMA 错误与电源波形。QSPI 区有普通 A 链路走线，晶振负载电容附近有 B.Cu 普通信号经过，故只做独立 Flash 或独立链路测试不足以关闭耦合风险。反复冷启动、热复位、USB ROM 和满活动切换也须通过。不要用高电容普通探头直接加载晶体脚后把异常归因于板子；采用合适的低负载方法或经验证的时钟输出诊断。

At each rate, stress flash/QSPI readback or known-data CRC/XIP while progressing from one to three active radios. Log memory errors, resets, USB failures, DMA/FIFO events and rail waveforms. Repeat cold/warm starts and activity transitions. Unrelated routes exist in the broader flash/crystal area, so isolated subsystem tests are insufficient. Avoid loading the crystal with an unsuitable probe.

若出现接收端阈值重复穿越、采样窗口不足、CRC/Flash 错误或活动相关复位，保留波形并停止升频，先修正路由/终端/驱动/采样策略；不得用提高目标速率或忽略异常关闭验收。功能及有效吞吐只有在这些门槛通过后才能记录为实测。

Stop increasing rate if ringing creates repeated threshold crossings, timing margin is insufficient, data/memory errors occur, or resets correlate with activity. Preserve evidence and correct routing, termination, drive or sampling before claiming measured performance.

每方向四位每时钟的 `4×fCLK` 只是原始位率；有效吞吐还受 VALID 占空比、帧头、CRC、DMA、调度与无线协议开销影响。任何频率、链路或三无线总吞吐数字在测试完成前均为目标。

`4×fCLK` is raw bitrate per direction, not payload throughput. Account for framing, VALID duty, CRC, DMA, scheduling and radio overhead. Frequency and aggregate-throughput figures remain targets until measured.

结果表留空，由测试人员填写 / Complete after testing:

| 阶段 / Stage | 板号、条件和证据 / Board, conditions and evidence | PASS / FAIL / NOT RUN | 负责人、日期 / Owner, date |
| --- | --- | --- | --- |
| 静态/装配 / Static and assembly | | NOT RUN | |
| 启动/电压/UVLO / Power and UVLO | | NOT RUN | |
| RP SWD/Flash/ROM USB | | NOT RUN | |
| USB 电源顺序/断连 / Power order and disconnect | | NOT RUN | |
| C5 A/B/C UART/存储器 / UART and memory | | NOT RUN | |
| 2.2 A 连续/3 A 脉冲/环路 / Load and loop | | NOT RUN | |
| 单/多无线与 PIO/PARLIO / RF and parallel links | | NOT RUN | |
