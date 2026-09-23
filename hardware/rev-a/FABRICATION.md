# FarmMesh Node A1 — 制造与装配要求 / Fabrication and assembly requirements

**状态 / Status: GO FOR CONTROLLED A1 PROTOTYPE FABRICATION / 可受控工程原型投样。**

日期 / Date: 2026-09-23。完整布线及铺铜、最终 ERC/DRC、独立电气/DFM 会审和实际制造文件一致性已通过；统一放行依据为 [RELEASE.md](RELEASE.md)。本文件绑定原生 PCB SHA256 `94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9`，适用于受控工程样板。实物电气性能及量产工艺尚未验证。

The frozen board and actual manufacturing outputs have passed the release gates recorded in RELEASE.md. Fabricate and assemble the exact released snapshot under the requirements below. Physical performance and production process qualification remain open; execute the first-board plan after assembly.

## PCB 配置 / PCB construction

| 项目 / Item | 要求 / Requirement |
| --- | --- |
| 层数及材料 / Layers and material | 4-layer FR-4，JLCPCB **JLC04161H-3313** |
| 板厚 / Finished thickness | 1.6 mm nominal；按下单层叠和制造公差 / per confirmed fabrication stack-up |
| 外形 / Outline | 当前设计 100 × 100 mm，连续闭合 Edge.Cuts；最终以发布 Gerber 为准 / current design 100 × 100 mm; released outline governs |
| 铜厚 / Copper | Outer 1 oz，inner 0.5 oz；不可无复核改 2 oz / no unreviewed change to 2 oz |
| 表面 / Finish | ENIG |
| 阻焊 / Solder mask | 双面绿色 / green, both sides |
| 丝印 / Legend | 元件位号、pin 1、电容正极、电池极性清晰；不压焊盘 / legible references, pin 1 and polarity marks, clear of solderable pads |
| 安装孔 / Mounting holes | H1–H4：φ3.2 mm NPTH，中心为 (5,5)、(95,5)、(5,95)、(95,95) mm；以当前 PCB 左上角为原点 / from current PCB top-left |
| 测试点 / Test pads | TP1/2/3/101/102/103/104 为裸铜焊盘，无贴装件 / exposed PCB pads, no purchased components |

层序 / Layer order: **F.Cu → In1.Cu → In2.Cu → B.Cu**。In1.Cu 和 In2.Cu 均为 GND；In1.Cu 为顶层主要参考，RP2350 buck LX 下方按设计保留局部铜禁区。保持完整发布层序；CAM 不得自行删改地平面和电源铜。

In1.Cu is the principal ground reference, with the intentional local RP2350 buck LX copper keepout. Preserve the released layer order and copper clearances. Do not modify plane connectivity during CAM processing without engineering review.

[JLC 层叠 / Stack-up](https://jlcpcb.com/impedance)：外铜/介质/内铜/core/内铜/介质/外铜名义为 `0.035 / 0.0994 / 0.0152 / 1.265 / 0.0152 / 0.0994 / 0.035 mm`。厂商必须确认该层叠，不能只按“四层 1.6 mm”换任意芯板 / Confirm this exact construction rather than substituting any four-layer 1.6 mm stack.

## 几何及钻孔 / Geometry and drilling

- 常规信号线宽/间距 0.15/0.15 mm；RP2350 QFN 逃线局部 0.10 mm 线宽/间距。大电流电源铜按发布 PCB 保留，不统一缩为信号线宽。
- Normal signals use 0.15/0.15 mm trace/space; local RP2350 fanout uses 0.10 mm rules. Preserve the released power-copper widths.
- 常规通孔 via 0.45 mm 焊盘 / 0.20 mm 钻孔；另有较大接地、散热和电源 via。PTH 与 NPTH 必须分开钻孔输出，USB 插座槽孔不得改圆孔。
- Standard through vias use 0.45 mm land / 0.20 mm drill, with larger ground, thermal and power vias where specified. Keep plated and non-plated drills separate; preserve USB shell slots.
- NPTH 至铜至少 0.20 mm；检查内部铜至孔、元件 PTH 环宽和板边间距，不能用全局降低 DRC 限值掩盖违规。
- Maintain at least 0.20 mm NPTH-to-copper clearance and verify inner-layer hole clearances, component-hole annular rings and board-edge clearance.

这些是本项目基线，制造方以 [JLC 工艺能力表](https://jlcpcb.com/capabilities/Capab) 和最终 CAM 复核确认。存在任何与本规格不一致的自动修改，应先返回工程确认 / Report any required CAM changes before fabrication.

## USB 受控阻抗和插座焊盘 / USB impedance and connector lands

USB D+/D− 主线按顶层对 In1.Cu 参考的差分微带设计：**0.158 mm 宽、0.200 mm 线间隙、90 Ω differential ±10%**。同层其他铜通常至少退让 0.5 mm，局部器件焊盘例外由工程审阅。所列宽距只适用于指定层叠；未经复核不允许换层叠或改变阻抗线宽。

The USB pair uses top-layer coated microstrip referenced to In1.Cu: **0.158 mm width, 0.200 mm edge gap, 90 Ω differential ±10%**. Keep other top copper generally 0.5 mm away. These dimensions are specific to the selected stack-up. Confirm controlled impedance with the fabricator; the nominal calculator result is 89.9523 Ω, not a measurement of a manufactured board.

J102 使用 **FarmMesh:USB_C_GCT_USB4105_A1**，不是未修订 stock footprint。仅 A1/A12/B1/B12 的同位 GND 焊盘靠定位孔边缩短 0.04 mm：0.60 × 1.11 mm、局部 Y=−3.70 mm；孔径、孔位、槽孔及其他焊盘不变。阻焊/钢网开口随该铜形状；重叠 A/B 编号不得重复叠加锡膏厚度。计算孔铜净距约 0.2333 mm，最终 Gerber 须复查。

J102 uses the local revised land pattern. Only the four coincident outer ground pads are shortened on the locating-hole side. Preserve all drill geometry and remaining lands. Coincident A/B pad definitions represent one physical aperture, not two paste deposits. The nominal revised length is within the 1.15 ±0.05 mm recommended-land dimension in the [GCT B4 drawing](https://gct.co/files/drawings/usb4105.pdf); inspect the first assembled connector for wetting and alignment.

## Via、裸露焊盘与钢网 / Vias, exposed pads and stencil

普通信号/接地 via 默认双面 tenting，不开钢网。**Tenting 不是树脂塞孔加电镀盖帽（VIPPO），也不是保证完全填满孔。** 本样板目标为普通非 VIPPO 工艺；不得在裸露焊盘钢网开口内自动添加未填充开孔。

Ordinary signal/ground vias are tented on both sides and absent from paste. Tenting is not VIPPO and does not guarantee a filled hole. This prototype targets a conventional non-VIPPO process; do not add open unfilled holes inside exposed-pad paste apertures.

C5 模组 EP29 保留 3 × 3 个 1.3 × 1.3 mm 钢网窗口，间隙 0.4 mm，包络 4.7 × 4.7 mm；窗口面积总计 15.21 mm²，约为包络 68.9%。顶层实心 GND 铜连接九块 EP 铜焊盘；**EP 包络内部无孔**，使用八个外围接地 via 和模组边缘 GND 焊盘附近的 via 接入内层。不得恢复已取消的四个内部间隙 via，不得合并钢网窗口。

The C5 EP29 retains nine 1.3 mm square paste windows within a 4.7 mm square envelope, approximately 68.9% aperture coverage. Solid top-layer ground copper joins the nine EP lands. **No holes are permitted inside the EP envelope**; eight perimeter ground vias and additional vias near the module edge ground pads connect to the internal planes. Do not restore the removed four interior gap vias or merge the paste windows.

[JLC 普通 tenting 与塞孔说明](https://jlcpcb.com/blog/five-via-finishes) 的 0.35 mm 开口距离限制属于**油墨塞孔**，不是普通 tenting 的统一规则；普通 tenting 建议孔径不超过 0.4 mm。最终 Gerber 必须检查 via 在双面 mask 上没有开窗，孔不在钢网开口内，并保留足够 mask web。RP2350 外围孔到 EP 铜边约 0.25 mm 的名义距离本身不触犯该塞孔条件，因为本板不要求塞孔；仍须根据实际 mask expansion 检查。普通 tenting 可能存在局部透光或不完全密封，不可宣称达到填孔效果。[JLC Via Covering](https://jlcpcb.com/help/article/pcb-via-covering)。

JLC's 0.35 mm exclusion from adjacent openings applies to **solder-mask ink plugging**, not a universal tenting clearance. Ordinary tenting is recommended for holes no larger than 0.4 mm. Inspect the final mask and paste data: no via mask openings, no holes in paste apertures, and adequate mask web. The RP2350 perimeter hole-to-EP copper clearance of approximately 0.25 mm is not automatically disqualified by an ink-plugging rule; review its actual mask expansion. Ordinary tenting does not promise fully sealed holes.

最终实际 Gerber/钻孔中 396 个 via 的最大孔径为 0.30 mm，全部有效双面 tenting；没有孔与钢网或阻焊开口的名义相交。以下位置余量较小，**CAM 及首件重点检查**：KiCad 坐标 (70.40,28.70) 的 C9 邻孔净距 0.0250 mm，(87.30,30.30) 的 C5 邻孔约 0.0281 mm，(93.50,40.00) 的 J1 邻孔 0.0400 mm。避免对位偏差造成露孔或吸锡；工艺无法满足时返回工程处理，不自行扩大开窗。J2 地孔现为 (98.25,26.54)，孔边到其相邻双面 mask 开口 0.25 mm，旧相切位置已移除。详见 [最终 DFM 审阅](reports/a1-dfm-bom-review.md)。

All 396 vias are effectively tented on both sides with drills no larger than 0.30 mm. The three small positive margins above are accepted for prototype CAM/first-piece inspection, not a guarantee of sealed holes under all process tolerances. Verify mask registration and solder wicking at these locations before accepting assembled samples.

U101、U1 和三个模组的 EP 必须焊接到 GND，不能作为“可不焊”处理。RP2350 EP 外围散热孔不应被钢网开窗覆盖。钢网厚度以装配方兼顾 0402、0.4 mm QFN 和模组窗口的工艺审查为准；0.10 mm 可作为试制讨论起点，不是已验证参数。

Solder the exposed pads of U101, U1 and all three modules to ground. Keep the RP2350 perimeter thermal vias outside paste openings. The assembler must select stencil thickness and paste process for 0402 parts, 0.4 mm QFN and the module windows; 0.10 mm is an engineering starting point, not a qualified process.

建议整板受控回流焊并检查隐藏 EP 焊点；返修 C5 时使用底部预热、适配风嘴和热电偶，按 [Espressif 模组回流/处理规定](https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf) 设定实际温度曲线。不要仅凭热风枪设定温度判断焊点峰温，也不要在同轴插头连接时强行移动模组。

Prefer controlled whole-board reflow and inspection of hidden EP joints. For module rework, use bottom preheat, a suitable nozzle and thermocouple monitoring against the module manufacturer's processing profile. Hot-air station setpoint alone is not solder-joint temperature. Disconnect coax cables before rework.

## BOM、方向和附件 / BOM, orientation and accessories

装配依据最终发布 BOM 与 `parts-selection.json`，共 153 个实装件；11 个 TP/H 裸板特征不采购、不贴装。不得静默用“同容量/同封装”替代关键电容、定向电感或 USB B 版比较器。C6 实际为 **120 µF/10 V**；C203/303/403 为 **φ5 × 5.9 mm**。C7 的厂家极性标记须与 PCB 正极匹配。

Use the released BOM and parts-selection mapping: 153 fitted components; 11 bare-board TP/H features are not purchased or placed. Substitutions require engineering review. C6 is 120 µF/10 V, and the three radio bulk capacitors use 5 mm diameter cans. Verify all polymer-capacitor polarity marks.

L101=`AOTA-B201610S3R3-101-T` 的厂家定位标记须对应本地 footprint pad1 / CORE_1V1，pad2 / LX；它是定向电感，不能按普通对称 3.3 µH 件任意旋转。核查 RP2350、Flash、LTC3119、USB mux/comparator、各 C5 的 pin 1。[Abracon 图纸](https://abracon.com/datasheets/AOTA-B201610S3R3-101-T.pdf)。

Place the marked inductor in its specified orientation: pad 1 to CORE_1V1, pad 2 to LX. Verify pin 1 orientation for every IC and module.

| 附件 / Accessory | 数量 / Qty | 料号 / MPN | 接线与使用 / Wiring and use |
| --- | ---: | --- | --- |
| 双频天线含同轴 / Dual-band antenna with coax | 3 | Taoglas FXP830.07.0100C | 100 mm cable, MHF I/U.FL；每模组一条 / one per module; not MHF4 |
| USB 数据线 / USB data cable | 1 | StarTech USB2AC1M | USB-A ↔ USB-C；不为电池充电 / no battery charging path |
| 电池插头壳 / Battery housing | 1 | JST VHR-2N | J1 pin1 BAT_PLUS，pin2 GND |
| 电池端子 / Battery contacts | 2 | JST SVH-21T-P1.1 | 建议 18 AWG 短线，极性逐线检查 / short 18 AWG leads; verify polarity |
| OFF 短路帽 / OFF shunt | 1 | Samtec SNT-100-BK-G | 装到 J2 则 OFF / fitted on J2 disables converter |
| SWD 线壳 / SWD housing | 1 | Harwin M20-1060500 | 按板上针序制作 / custom pin mapping |
| UART 线壳 / UART housings | 3 | Harwin M20-1060600 | 按板上针序制作 / custom pin mapping |
| 调试线端子 / Debug contacts | 23 | Harwin M20-1180042 | 5+3×6 positions；3V3 为参考，不外部供电 / 3V3 reference only |

天线保持远离板铜、电池和金属外壳，留同轴弯曲余量与插拔空间。该天线组合用于样板验证，三无线互扰和装入外壳后的效率需实测。电池需为合适的受保护 1S 锂电源；本板无充电器，首件先使用限流台式电源验证。USB 或调试口不得用来反向给 3V3 母线供电。

Keep antenna radiators clear of board copper, battery and enclosure metal, with cable strain relief and mating access. Validate three-radio coexistence and enclosure effects on the samples. The board requires a suitable protected 1S source and contains no charger. Use a current-limited bench supply for first power-up; never back-power 3V3 through a debugger or USB connection.

## 发布前交付核对 / Pre-release deliverable review

最终包包含一致版本的四层铜、双面阻焊/丝印/钢网、板框、PTH/NPTH 钻孔、BOM、坐标及装配图，均由冻结源统一导出并记录 SHA256。导入装配系统时核对极性、单位、原点、顶/底视图和重复同位焊盘。位号以 F.Fab 装配图及坐标为完整依据；密集 0402 区域未把所有位号强行挤入丝印。

The release package contains matching copper, mask, legend, outline, separate plated/non-plated drills, stencil, BOM, placement and assembly views, exported from the frozen source with SHA256 records. Verify units, origins, polarity and coincident pads when importing it. Use the complete F.Fab assembly drawing and placement references in dense areas where all 0402 references cannot fit on silkscreen.
