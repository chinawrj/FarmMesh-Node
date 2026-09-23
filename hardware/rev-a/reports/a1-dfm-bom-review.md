# A1 BOM 与 DFM 独立审阅

日期：2026-09-23。**最终 BOM / DFM 静态审阅：PASS，可受控工程原型投样。** 范围包括确切选料、官方器件资料、JLCPCB 工艺基线、最终原生板和实际导出的 Gerber、钻孔、BOM、坐标及源文件哈希闭包。结论绑定 PCB SHA256 `94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9`；后续原生源或制造几何变化须重新核验。本报告不把静态审阅或 ERC/DRC 通过等同于电源、USB、无线性能或装配良率实测。

## 已落实的选料

`parts-selection.json` 覆盖 **153 个装配器件**（原 145 个加 USB 隔离电路 8 个）以及 **11 个裸板制造特征**；每个位号都有 MPN、厂商、封装、来源和说明。5 个电源标志不属于实物。TP1/2/3/101/102/103/104 和 H1–H4 使用 `PCB_FEATURE_NOT_PURCHASED`、`purchasable=false`，不是待定采购件。所有指定封装都在本地 KiCad 库或 FarmMesh.pretty 中存在。

RP2350 buck 的 C101/102/103、R101，晶振 C105/106，以及 100 nF 的 C104/C110–C123 采用 [Raspberry Pi RP2350B R4-S1 官方参考 BOM](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-010329-CA-1-RP2350B%20Minimal%20KiCAD.zip) 的具体 0402 料号。R102/103/105、两只 USB 27 Ω 和 RP2350 源端的 15 只 22 Ω 也改为 0402；各 C5 源端 7 只串阻仍为 0603。这是布线尺寸变化，不改变电阻值。

新增 U103=`TS3USB30EDGSR`、U104=`TLV3011BIDBVR`，以及 C128/129/130、R114/115/116 已定料；两只阈值分压电阻为 Yageo RT 0.1%、25 ppm/°C。U104 的 **B** 版本不可换为老 TLV3011。普通 0603 100 nF/10 nF 改用有当前官方单件规格页的 KEMET `C0603C104K5RACTU` / `C0603C103K5RACTU`；RP 官方 0402 电容保持 Murata 原选型。[TI comparator datasheet](https://www.ti.com/lit/ds/symlink/tlv3011.pdf)、[Yageo 100 kΩ 单件规格](https://www.yageogroup.com/component-documentation/download/specsheet/RT0603BRD07100KL)、[KEMET 100 nF](https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU)。

## 电容选型与有效容量边界

| 位号 | 确切选型 | 关键额定值与封装 | 结论 |
| --- | --- | --- | --- |
| C6 | Panasonic 10SVPC120M | 120 µF ±20%，10 V，聚合物；27 mΩ；2.32 Arms；φ6.3 × 5.9 mm | 原 100 µF 改为 120 µF，值及 footprint 必须同步 |
| C7 | Panasonic 6SVPE220M | 220 µF ±20%，6.3 V，聚合物；10 mΩ；3.90 Arms；φ6.3 × 5.9 mm | 保留；注意不能套用其他 SVP/SVPC 系列 ESR |
| C203/303/403 | Panasonic 6SVPC100M | 100 µF ±20%，6.3 V，聚合物；30 mΩ；1.97 Arms；φ5.0 × 5.9 mm | 原泛用 φ6.3 footprint 改为 CP_Elec_5x5.9 |
| C3/4/8/201/301/401 | Murata GRM21BZ71A226ME15L | 22 µF ±20%，10 V，X7R(MURATA) Z7，0805 | 官方典型：3.3 V 时 14.29 µF、4.2 V 时 11.79 µF；条件和边界见下 |
| C11 | Murata GRM21BR71A475KA73L | 4.7 µF ±10%，10 V，X7R，0805 | LTC3119 VCC 陶瓷旁路；须短回路 |
| C101/102/103 | Murata GRM155R60J475ME47D | 4.7 µF ±20%，6.3 V，X5R，0402 | 精确复用 RP 官方 buck 选型和局部布局 |
| C124 | Murata GRM188R60J475KE19D | 4.7 µF ±10%，6.3 V，X5R，0603 | CORE 额外局部储能，不替代 C103 |
| C204/304/404 | Murata GRM188R71C105KA12D | 1 µF ±10%，16 V，X7R，0603 | EN 延时名义 10 ms，启动波形仍须测量 |
| C10/C12/C130 | KEMET C0603C821/471/102J5GACTU | 分别 820 pF/470 pF/1 nF，±5%，50 V，C0G，0603 | 补偿及参考旁路使用稳定介质 |

聚合物 ESR 表中数值为厂家 100 kHz 指标，纹波电流为 100 kHz、105°C 额定条件，不能直接视为任意频率、任何 PCB 散热条件下的能力。来源：[10SVPC120M](https://industrial.panasonic.com/ww/products/pt/os-con/models/10SVPC120M)、[6SVPE220M](https://industrial.panasonic.com/ww/products/pt/os-con/models/6SVPE220M)、[6SVPC100M](https://industrial.panasonic.com/ww/products/pt/os-con/models/6SVPC100M)。初始名义容量仅计 −20% 公差时，C6 为 96 µF，C7 为 176 µF，每只无线储能为 80 µF；这些数字不是全温、寿命后的系统有效电容保证。

已取得 [Murata 官方 SimSurfing](https://ds.murata.com/simsurfing/mlcc.html?lcid=en-us) 对精确电气料号 `GRM21BZ71A226ME15`（末尾 L 为包装代码）的典型曲线。条件为 **25°C、0.5 Vrms、120 Hz**，偏压施加 60 s；频率和施加时间依据 [厂家测量条件 pp.7–8](https://ds.murata.com/simsurfing_data/pdf/en-us/mlcc/sim_mlcc_measuringcond_e.pdf) 及该料号官方数据行 `Condition=120Hz / 0.5Vrms`。

| DC bias | 典型 C / µF | 数据处理 |
| ---: | ---: | --- |
| 0 V | 21.481700 | 原始数据点 |
| 3.3 V | 14.288852 | 原始 0.05 V 网格点，无插值 |
| 4.2 V | 11.788160 | 原始 0.05 V 网格点，无插值 |
| 5.0 V | 9.963983 | 原始数据点 |

完整官方 HTTP 请求、原始响应、SHA256 和摘要位于 JSON 的 `capacitor_validation.GRM21BZ71A226ME15L`。可以直接复核：

```sh
python3 - <<'PYCODE'
import json, urllib.parse, urllib.request
p = json.load(open('hardware/rev-a/parts-selection.json'))['capacitor_validation']['GRM21BZ71A226ME15L']
u = p['request_endpoint'] + '?' + urllib.parse.urlencode(p['request_params'])
r = json.load(urllib.request.urlopen(u))
c = r['JsonCharaData'][0]['charadata'][0]
assert not c['error'] and c['tc'] == '25' and c['ac'] == '0.5'
for x, y in c['data']:
    if any(abs(x[0]-v) < 1e-9 for v in (3.3, 4.2)):
        print(x[0], 'V:', y[0], c['y_subunit'] + c['y_unit'])
PYCODE
```

**这些是典型曲线值，不是全温、负公差和老化后的保证最小值。** 官方 API `GetAcChoices4Cdcb` 只返回 0.5 Vrms；10 mVrms 请求明确报条件不支持。请求 −20°C / 85°C 时，`WorkInfo` 会回显请求温度，但实际 `charadata.tc` 仍为 25，不能将它当成三温验证。[22 µF 规格书](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM21BZ71A226ME15-01A.pdf) 中 Z7 的“50% 额定电压下温度变化 ±15%”也不是“5 V 偏压后保留 85% 标称电容”。

建议保留该确切 22 µF/10 V/0805 料号：现在有可追溯曲线，无须仅为获得数据而换料或改封装。C3/C4 两只在 4.2 V 下的典型合计约 23.576 µF；3.3 V 各支路的陶瓷按约 14.29 µF 典型值纳入电源评估。小纹波工作条件、初始公差、全温、寿命和动态负载仍须在模型/首件验证中留余量，不能由这张曲线直接宣布已满足全部供电边界。

[LTC3119 数据手册 pp.12、18–20、22–25](https://www.analog.com/media/en/technical-documentation/data-sheets/3119fb.pdf) 要求低阻抗输入旁路，并给出 4.7 µF VCC 旁路及输出电容/补偿指导。所选聚合物总输出标称储能为 520 µF，分布电阻、电感及上述实际 ESR 都应纳入环路。选料可用于限流供电的工程样板；满负载、冷启动和无线突发负载的电压包络不能先行宣称通过。详见同目录 `a1-power-review.md`。

## USB 新增器件封装、脚位及失电复核

**U103 的 stock footprint 可用于 TS3USB30EDGSR，但不是 TI 示例坐标的逐字复制。** [TI DGS0010A 图 4221984/A，pp.1–3](https://www.ti.com/lit/pdf/mpds035) 规定无 EP 的 10-pin VSSOP、3.0 × 3.0 mm body、0.5 mm pitch、4.75–5.05 mm 总焊尾跨度。KiCad `Package_SO:TSSOP-10_3x3mm_P0.5mm` 自身 tags 明确包含 `Texas_DGS0010A` 和 `Texas_VSSOP-10`；名称 TSSOP 不表示这里选成另一种脚距。

| DGS land 几何 | TI example | 当前 KiCad stock |
| --- | ---: | ---: |
| pad 长 × 宽 | 1.45 × 0.30 mm | 1.45 × 0.30 mm |
| 同排 pitch | 0.50 mm | 0.50 mm |
| 两排中心距 | 4.40 mm | 4.30 mm |
| 单侧 pad 外缘 | 2.925 mm | 2.875 mm |
| 最大 lead-tip 半跨度 | 2.525 mm | 同一实际器件 |

KiCad 每排向内移 0.05 mm，外缘仍较最大 lead tip 多 0.35 mm，pin 1 与逆时针编号正确；这是一种几何兼容的替代 land pattern，不能声称 TI 已批准其钢网或焊接工艺。保留当前封装，首件看焊趾/焊跟润湿和桥连。

按 [TS3USB30E Rev. G，pp.3–5、12](https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf) 再核对当前 manifest：1=S→GND，2=D1+→USB_DP_SW，3=D2+→NC，4=D+→USB_DP_ESD，5=GND，6=D−→USB_DM_ESD，7=D2−→NC，8=D1−→USB_DM_SW，9=OE→USB_DISCONNECT，10=VCC→3V3。S=0/OE=0 选 D1，OE=1 断开。使用 DGS pin map，不能误套 RSW/UQFN pin map。VCC=0、VO=0–4.3 V 等规定条件下 Ioff 最大 ±2 µA；推荐工作 VCC=3.0–4.3 V。失电漏电规格不是数学零，也不保证 0–3.0 V 欠压区间的完整行为。

U104=`TLV3011BIDBVR` 的 DBV 是 SOT-23-6、0.95 mm pitch，无 EP；当前 stock `SOT-23-6` 编号正确。TI DBV0006A 的示例焊盘为 1.10×0.60 mm、两排距 2.60 mm，KiCad 为 1.325×0.60 mm、两排距 2.275 mm；stock 外缘 ±1.80 mm，覆盖该器件最大总焊尾跨度 3.00 mm（±1.50），属于兼容的通用 land，亦非 TI 逐点复制。[TLV3011 Rev. C，pp.37–39](https://www.ti.com/lit/ds/symlink/tlv3011.pdf)。

实际脚位再核：1=OUT→USB_DISCONNECT，2=V−→GND，3=IN+→USB_REF，4=IN−→USB_VBUS_CMP，5=REF→USB_REF，6=V+→3V3。该 **B** 版本输入在 V+=0 或上下电时对 0–5.5 V 保持 fail-safe 高阻；本分压在 VBUS=5.5 V 时名义仅 1.632 V。POR 时 TLV3011B 开漏输出为 Hi-Z，R116 在 3V3 存在时把 OE 拉高；完全断电时不能说 R116 仍输出高电平，隔离依靠开关 Ioff。非 B 的 TLV3011 及推挽 TLV3012B 均不接受替代。保持 C130=1 nF，未超过参考输出 10 nF 条件。[TI sections 9.4.1、9.4.3–9.4.5](https://www.ti.com/lit/ds/symlink/tlv3011.pdf)。

静态脚位/几何没有新增阻断项；慢电源坡、VBUS 门限、欠压、ROM BOOTSEL 和线缆拔除仍须按 `FIRST-BOARD-TEST.md` 验证。本次未修改 PCB 或原理图，未执行硬件测量。

## USB4105 本地派生封装

原 KiCad 10 库 `USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal` 的外侧 GND 焊盘至定位 NPTH 约 0.1944 mm。JLC 官方 NPTH 至走线要求 0.2 mm；不能靠降低 DRC 规则忽略。

新 `FarmMesh:USB_C_GCT_USB4105_A1` **仅修改 A1/A12/B1/B12 四个同位地焊盘**：原 0.60 × 1.15 mm、Y=−3.68，改为 0.60 × 1.11 mm、Y=−3.70。只切去靠孔侧 0.04 mm，远孔端不变；所有 NPTH/PTH 的孔径、坐标、槽孔及其余焊盘均经文本比较确认原样保留。按圆角几何算得最近铜距约 **0.233308 mm**，最终以主板 DRC 复核为准。

[GCT USB4105 官方 B4 图（2023-12-18），p.1](https://gct.co/files/drawings/usb4105.pdf) 的推荐焊盘长度为 1.15 mm、PCB 图公差 ±0.05 mm；1.11 mm 位于该区间内。横向仍为 0.60 mm，覆盖图示 0.45 mm GND 焊尾。焊尾覆盖关系和连接器机械孔位保持，仍需首件焊接检查。铜、阻焊和钢网采用同一个缩短后的圆角图形，开口面积较 stock 约减少 3.58%；重复 A/B 编号的同位图形应在 Gerber 中合并为同一开口。

来源和修改 SHA256 存于 JSON 的 `dfm.usb_connector_footprint`，随附 `FarmMesh.pretty/LICENSE-KiCad.txt`。派生数据保留 KiCad 社区归属及 [CC-BY-SA-4.0 + KiCad exception](https://gitlab.com/kicad/libraries/kicad-footprints/-/blob/master/LICENSE.md)。这不是 GCT 对自定义钢网或装配工艺的批准。

## 四层 1.6 mm 制造基线与 USB 阻抗

选用 **JLC04161H-3313**，外层 1 oz、内层 0.5 oz；由上至下名义铜/介质厚度为 `0.035 / 0.0994 / 0.0152 / 1.265 / 0.0152 / 0.0994 / 0.035 mm`。L2 作连续地参考，3313 的计算 Dk=4.1；核心 Dk 在静态表与当前计算接口有差异（4.6/4.42），此处外层 USB 模型只使用邻近 3313。来源：[JLC 层叠](https://jlcpcb.com/impedance)、[官方计算器](https://jlcpcb.com/pcb-impedance-calculator)。订单须指定该层叠，不接受任意“4 层 1.6 mm”等效替换。

常规信号采用 0.15/0.15 mm，RP2350 局部采用 0.10 mm 线距；过孔 0.45/0.20 mm。NPTH 至铜至少 0.20 mm，机械通孔焊盘和内层孔距另按规则检查；选择 1 oz 外铜、绿色阻焊和 ENIG。上述基线留有常规制造余量，仍需 CAM 检查细间距阻焊、通孔环宽、钢网和板边。来源：[JLCPCB 当前能力表](https://jlcpcb.com/capabilities/Capab)。不因连接器库数据存在而自动豁免孔铜间距。

USB 采用 **0.158 mm 线宽、0.200 mm 线间隙**。官方公开计算接口于审阅日期返回 **89.9522758704 Ω differential**，有效状态 `dResultValid=1`。JSON 中保存完整请求和响应，模型为 `DiffEdgeCoupledCoatedMicrostrip1B`，`dCalculateMode=3`，L1 对 L2 coated microstrip。

| 计算参数 | 数值 |
| --- | --- |
| H1 / Er1 | 0.0994 mm / 4.1 |
| W1（底宽） / W2（顶宽） | 0.158 / 0.1453 mm，即 W2=W1−0.5 mil |
| S1 | 0.200 mm |
| T1 | 1.6 mil，计算器成品导体模型 |
| C1/C2/C3 / CEr | 1.0/0.6/1.0 mil，3.8 |

模型不含近旁同层地铜；相邻其他顶层铜至少退让 0.5 mm。保持 L2 连续地，避免分割、跨电源岛或信号参考层空洞。芯片/ESD/mux 焊盘局部展宽和连接器引脚不由这一均匀传输线值代表。下单应要求 **90 Ω differential ±10%** 受控阻抗及厂家确认；该值是模型结果，不是已制造板的测试结果。

重算路径：打开 JLC 计算器，选该层叠及 L1/L2，选 coated differential microstrip，填上表；其接口 POST `https://jlcpcb.com/api/jlcTools/impedance/calc`，结果通过同一 UUID 的 `wss://tools.jlc.com/jlcTools/webSocket/<uuid>` 返回。JSON 保存了完整参数而非只留下截图。`dCalculateMode=1` 给的是奇模约 44.976 Ω，不能误报为差分值。

## 外购附件和采购边界

完整附件 MPN/数量/来源位于 JSON `accessories`。每板三条 Taoglas **FXP830.07.0100C**，每条包含 100 mm 同轴及 MHF I/U.FL 插头，不另买 MHF4 尾线；与 [C5 模组规定的第一代外接天线接口](https://documentation.espressif.com/esp32-c5-wroom-1_wroom-1u_datasheet_en.html) 对应。该 [Taoglas 天线](https://www.taoglas.com/product/freedom-fxp830-2-44-9-6-0ghz-flex-pcb-antenna-ipex-mhfi-2/) 用于样板 RF 试验，安装环境、三天线隔离和增益差异仍须评价；没有宣称复用模组原有认证的天线测试结果。

USB 线为 StarTech **USB2AC1M**；电池插头采用 JST **VHR-2N + 2×SVH-21T-P1.1**，18 AWG 短线按项目极性制作；J2 配 Samtec **SNT-100-BK-G**。SWD/UART 线束板端采用 Harwin **M20-1060500 / M20-1060600 + M20-1180042**，与 0.64 mm 方针匹配。它们是定料的线束元件，不是声称现成通用线缆能直接匹配本板针序；按实际原理图逐针制作，3V3 仅作参考，禁止调试器电源反供。[JST VH](https://www.jst-mfg.com/product/pdf/eng/eVH.pdf)、[Harwin 5-pin](https://www.harwin.com/products/M20-1060500)、[Harwin 6-pin](https://www.harwin.com/products/M20-1060600)、[StarTech](https://www.startech.com/en-at/cables/usb2ac1m)。

关键 IC 均有精确订货型号和官方/分销商目录证据；JSON `procurement_check` 保留来源。RP2350B、C5-N8R8、LTC3119IFE、W25Q128JVSIQ、TS3USB30EDGSR 与 TLV3011BIDBVR 检索到产品/库存指示；**没有预订库存或承诺交期**。Abracon 定向电感为 Active，官方直销仓不可用，但审阅时 [DigiKey 精确型号](https://www.digikey.com.au/en/products/detail/abracon-llc/AOTA-B201610S3R3-101-T/25621527) 有库存指示；装配前须落实原型号，不能用普通无标记 3.3 µH 电感替换。TI 两器件的匿名直销页显示不可用，不等于分销渠道不存在现货。[Abracon 定向电感](https://abracon.com/parametric/inductors/AOTA-B201610S3R3-101-T)、[USB mux 分销记录](https://www.digikey.com/en/products/detail/texas-instruments/TS3USB30EDGSR/2193086)、[B 版比较器分销记录](https://www.mouser.com/ProductDetail/Texas-Instruments/TLV3011BIDBVR?qs=3Rah4i%252BhyCEbcRLZ4CMXdw%3D%3D)。

## 最终原生设计核验

只读核验对象为 `FarmMesh-Node.kicad_pcb`，SHA256：

```text
94b96a96ef75f9561a9c2552ea9e2db2f6d1eb0fe6a99cec8e6313b0ac1b4ab9
```

加载前后原文件哈希不变。实际 164 个 footprint 与 manifest、工程 BOM 及 `parts-selection.json` 一致：153 个实装件、147 个 SMD、6 个通孔件、11 个非采购裸板特征。逐位号检查值、MPN、厂商、footprint 和装配排除属性；无缺失 MPN 或 TBD。C6=120 µF、C203/303/403 的 φ5.0 mm 罐体封装、RP 全部已指定 0402 元件及 J102 派生封装均已落实。27 种库封装、640 个 pad region 的实际板内几何核验通过；没有仅改封装名而保留旧 pad 几何的问题。USB 派生库文件 SHA256 为 `6b5a19aa0bc9462f0afe56b61d3cd2b0560e5659198d3ff32dcae09e6b7866ef`，与选料记录一致。

最终 `audit/erc.json` 为 0 个违规；`audit/drc.json` 为 **0 违规 / 0 未连接 / 0 schematic-parity**。`audit/pcb-verification.json` 的 11 项自动检查全部通过，且输入 PCB、manifest、XML netlist 和 footprint 库哈希与当前来源一致。这里引用的是最终导出树中的实际证据，不是中间候选板的结果。

### 过孔盖油与钢网

最终板有 **396 个过孔**：193 个显式双面 TENTED，203 个继承板级双面盖油；KiCad 10.0.5 的实际 `IsTented(F_Cu/B_Cu)` 对全部过孔均为真。最大过孔钻径为 0.30 mm。所有过孔均无自身 F/B.Mask 或 F/B.Paste 开口；板级/footprint 的额外 mask/paste 图形以及轨线开窗也已检查。

对实际 Gerber 开口进行另一轮独立几何解析后，全部过孔孔边与 F/B.Mask、F/B.Paste 开口均无相切或相交，采用 1 µm 保守几何容差。早期候选中 J2 地过孔 `(98.00, 26.54)` 与 J2 pad 2 的 1.70 mm 阻焊开口相切；最终孔已移至 **`(98.25, 26.54)`**，实际 PTH 文件旧孔位置不存在，双面孔边净距均为 **0.25 mm**。C5 和 R7 的两处原有 paste/drill 交叠也已经修正，最终文件没有重新带入。

下列是仍然较小、但为正值的实际工艺余量；它们不是尚未关闭的 paste/孔交叠：

| 过孔位置，KiCad 板坐标 mm | 最近开口 | 孔边至开口净距 |
| --- | --- | ---: |
| (70.40, 28.70) | C9 F.Mask / F.Paste | 0.0250 mm |
| (87.30, 30.30) | C5 F.Mask / F.Paste | 约 0.0281 mm |
| (93.50, 40.00) | J1 F.Mask / B.Mask | 0.0400 mm |

它们按本板已选的普通 tenting 基线接受，用于受控样板；不宣称在任何阻焊对位公差下均完全封闭。CAM 和首件须重点检查这些位置是否露铜、露孔或发生吸锡，必要的工艺调整不得擅自扩大钢网或阻焊开口侵入孔口。依据 [JLCPCB via finishes](https://jlcpcb.com/blog/five-via-finishes) 及 [via covering guidance](https://jlcpcb.com/help/article/pcb-via-covering)，**普通 tenting 与 solder-mask ink plugging 不同**：0.35 mm 相邻开口距离条件不能直接外推为普通 tenting 的统一最小间距；普通盖油也不是树脂填孔、铜帽/VIPPO 或密封孔保证。本版未要求这些填孔工艺。

三个 C5 模组各有 9 个 1.30×1.30 mm EP 钢网开口，实际 F.Paste 已逐模组核对，孔完全在 EP/paste 区域之外；RP 和 LTC3119 也不存在 EP 钢网区域内的孔。外围接地过孔的散热效果、阻焊成膜及焊膏转移仍需首件验证，不能沿用参考板的已测热阻。

## 实际制造输出核验

核验最终 `manufacturing/manifest.json` 所记导出批次 `2026-09-23T07:56:01.530010+00:00`，并重新检查文件集合和 SHA256 闭包。所有 `frozen_source_sha256` 项与工作区原生源及包内 `native/` 快照一致；已复制自动审阅证据的哈希一致。没有混入旧 A0 制造文件，也没有把 11 个测试点/安装孔特征变成采购或贴装件。

| 输出 | 实际检查结果 |
| --- | --- |
| Gerber | 11 层全部由 gerbonara 1.6.3 成功解析；4 铜层顺序 F.Cu / In1.Cu / In2.Cu / B.Cu，另含双面 mask、paste、silk 和 Edge.Cuts |
| 层叠和表面 | gbrjob 明确 4 层、1.6 mm、ENIG、受控阻抗；铜/介质厚度依次 0.035 / 0.0994 / 0.0152 / 1.265 / 0.0152 / 0.0994 / 0.035 mm，与 JLC04161H-3313 基线一致 |
| 板框 | 实际 Edge.Cuts 四条线中心组成 100.00×100.00 mm 闭合矩形；gbrjob 的 100.05×100.05 mm 是含 0.05 mm 画线宽度的包围盒，不是另一个成品板尺寸 |
| PTH | 共 427 个孔/槽：155×Ø0.20、8×Ø0.25、233×Ø0.30、25×Ø1.00、2×Ø1.70，另有 4 个 0.60 mm 宽 USB 壳脚槽 |
| NPTH | 共 6 个：2×Ø0.65 USB 定位孔、4×Ø3.20 M3 安装孔；与 PTH 分钻 |
| 钻孔坐标 | 全部孔中心、孔径、槽中心/宽度/长度逐项对应原生板；最大圆心差约 0.707 µm，来自 Excellon 0.001 mm 坐标量化；NPTH 中心完全相符 |
| 钢网/阻焊 | 实际 F.Paste 597 个 flash 对象、B.Paste 空；F.Mask 615、B.Mask 37 个 flash 对象。它们不是唯一几何开口数量：USB 同位 A/B pad 会产生重合 flash |
| USB 修订焊盘 | 实际 F.Paste/F.Mask 的 A1/A12/B1/B12 仍为 0.60×1.11 mm，同位图形重合，不生成额外或错位开口；所有定位孔和壳脚槽保留 |
| 装配 BOM | 74 个分组行，展开后恰为 153 个不同位号；数量、值、MPN、厂商和封装逐位号与选料/原生板一致 |
| 坐标文件 | all=153、SMD=147；全部 X/Y、旋转角（模 360°）、值、封装逐条对应原生 footprint，容差 1.1 µm / 1.1 µdeg；全部 top，USB 混合 SMD/PTH 插座 J102 保留 |
| 附件 BOM | 8 行与 `parts-selection.json.accessories` 的数量、MPN、厂商、用途、说明和来源逐字段一致 |

坐标采用 Gerber/钻孔共同的绝对原点 `(0,0)`，X 向右、Y 向上；本板位于 KiCad 原点下方，因此装配 CSV 的负 Y 正确。表中位置是 footprint 原点，不保证等于器件本体重心；装配厂仍须按 `placement-schema.json` 核对导入坐标系、极性和旋转库。该工程 CSV 没有被误标为已匹配 LCSC 物料库的一键贴片文件。

Gerbonara 对两个 Excellon 文件发出 `G90 header statement found after end of header` 警告；该 KiCad 文件仍明确使用 G90 绝对坐标和 METRIC 十进制单位。没有隐藏警告，也没有仅凭解析成功忽略它：上述 427+6 个孔/槽与原生坐标的逐项比对独立确认了解析原点、单位及数值没有偏移。

可从项目根目录只读重验当前包内闭包和冻结源：

```sh
python3 - <<'PYCODE'
from pathlib import Path
import sys
sys.path.insert(0, str(Path('hardware/rev-a/scripts').resolve()))
import export_manufacturing as e
m = e.verify_closure(e.OUT)
e.require_same_sources(m['frozen_source_sha256'])
e.verify_prior_reports()
print(m['board_sha256'], m['assembly_count'], m['smd_count'])
PYCODE
```

独立几何核验使用 KiCad `pcbnew` 只读提取孔/footprint 位置，gerbonara 解析实际文件，Shapely 合并各 Gerber aperture 的正极性图元并计算孔边距离；圆弧多边形化误差纳入 1 µm 保守容差。最终 ZIP 的文件集合、每项 SHA、CRC 及外部 ZIP SHA 由 `finalize_release.py` 封包后再以 `--check-only` 检查；本报告不把尚未运行的封包步骤冒称完成。文档状态统一由 `RELEASE.md` 记录，最终封包会同步本报告和制造要求文本。

## 受控投样结论与实物边界

**在上述精确 PCB 和制造输出范围内，BOM / 封装 / DFM 审阅通过，没有尚未关闭的静态制造阻断，可进入受控工程原型制造与装配。** 该结论不需要追加未约定的人工批准流程，也不代表已经下单、已经制造或通过量产工艺认证。成品依已指定层叠、普通盖油、独立 PTH/NPTH、ENIG 和受控阻抗要求生产；工厂 CAM 对层叠、阻抗、窄余量盖油与钢网的实际工艺确认仍是制造执行的一部分。

装配前核对连接器/电池极性、极性罐体、IC pin 1、L101 定向电感及天线 MHF I/U.FL 配套。首件按 `FIRST-BOARD-TEST.md` 分阶段限流上电，并检查盖油窄余量、EP 焊接、USB 连接器润湿及桥连。环路稳定性、持续 2.2 A 温升、已定义脉宽的 3 A 瞬态、冷启动/UVLO、ROM BOOTSEL/无 VBUS 断连、USB 枚举和三无线并发仍未实测；PIO/PARLIO 时序与吞吐仍是无固件验证的目标。电池 ADC 本版已延期。没有将这些性能边界写成已完成的试验结果。
