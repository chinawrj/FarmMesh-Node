#!/usr/bin/env python3
"""Generate the editable FarmMesh Node A1 schematic; release status is in RELEASE.md."""
from schematic_builder import *

root=Sheet(PROJECT,'FarmMesh Node - schematic review index',1)
power=Sheet('01-power','1S battery input and 3.3V buck-boost',2)
rp=Sheet('02-rp2350','RP2350B aggregation, memory and debug',3)
radios=[Sheet('03-radio-a','C5-A module and independent link A',4),Sheet('04-radio-b','C5-B module and independent link B',5),Sheet('05-radio-c','C5-C module and independent link C',6)]

# Official module pad map: datasheet v1.3, pp14-15, recommended pattern p55.
c5data=json.loads((BASE/'c5-pinmap.json').read_text())
ordered=[6,7,13,14,17,16,8,10,11,12,21,23]
other=[2,3,24,25,18,15,4,5,9,26,27,19,20,22,31,1,28,29,30,32]
cpins=[]
for p in c5data['pins']:
    n=int(p['pad'])
    if n in ordered: x,y,angle=25.4,27.94-5.08*ordered.index(n),180
    else:x,y,angle=-25.4,24.13-2.54*other.index(n),0
    cpins.append((n,p['name'],p['electrical_type'],x,round(y,4),angle))
c5sym=custom_ic('ESP32-C5-WROOM-1U-N8R8',cpins,'FarmMesh:ESP32-C5-WROOM-1U','https://www.espressif.com/sites/default/files/documentation/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf',40.64,66.04)

# LTC3119 FE pinout from datasheet Rev B pp2,12,34. Repeated power pads shown.
lnames={1:'NC',2:'NC',3:'BST2',4:'PGND',5:'SW2',6:'PVOUT',7:'PVOUT',8:'SW2',9:'PGND',10:'PGOOD',11:'SVCC',12:'FB',13:'VC',14:'SGND',15:'MPPC',16:'VCC',17:'RT',18:'RUN',19:'VIN',20:'PGND',21:'SW1',22:'PVIN',23:'PVIN',24:'SW1',25:'PGND',26:'BST1',27:'NC',28:'PWM_SYNC',29:'EP_PGND'}
left=[22,23,19,26,21,24,18,28,17,15,16,11,1,2,27]
right=[3,5,8,6,7,10,12,13,14,4,9,20,25,29]
lpins=[]
for n,pname in lnames.items():
    side=left if n in left else right
    x=-25.4 if n in left else 25.4;angle=0 if n in left else 180
    y=35.56-5.08*side.index(n)
    kind='no_connect' if pname=='NC' else 'power_in' if pname in ['PVIN','VIN','SVCC','PGND','SGND','EP_PGND'] else 'power_out' if n in [6,16] else 'open_collector' if n==10 else 'passive' if pname in ['SW1','SW2','BST1','BST2','PVOUT'] else 'input'
    lpins.append((n,pname,kind,x,round(y,4),angle))
ltc=custom_ic('LTC3119IFE',lpins,'Package_SO:TSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.05x7.56mm','https://www.analog.com/media/en/technical-documentation/data-sheets/3119fb.pdf',40.64,81.28)
mpins=[(n,'S','passive',15.24,7.62-2.54*(n-1),180) for n in [1,2,3]]+[(4,'G','input',-15.24,-7.62,0)]+[(5,'D_5-8_EP','passive',-15.24,7.62,0)]
mos=custom_ic('DMP2008UFG',mpins,'Package_SON:Diodes_PowerDI3333-8','https://www.diodes.com/datasheet/download/DMP2008UFG.pdf',20.32,22.86)

root.text('FarmMesh Node / Revision A1 - PROTOTYPE',25.4,22.86,3,True)
root.text('1 x RP2350B + 3 x ESP32-C5-WROOM-1U-N8R8\n1S protected Li-ion input; 3.3V regulated rail\nNative KiCad 10 schematic + four-layer prototype PCB',25.4,35.56,1.8)
root.subsheet(power,25.4,66.04,110,25.4)
root.subsheet(rp,25.4,116.84,110,25.4)
for s,y in zip(radios,[66.04,116.84,167.64]):root.subsheet(s,228.6,y,135,25.4)
root.text('INTERFACE CONVENTION',25.4,165.1,1.8,True)
root.text('TX / RX are named from the C5 perspective.\nBoth TX_CLK and RX_CLK originate at that C5.\nRP drives only RX_D[0..3] and RX_VALID.\nGlobal net labels make the electrical sheet connections.\nNo wireless protocol is selected by this schematic.',25.4,175.26,1.5)
root.text('REVIEW BOUNDARIES',25.4,215.9,1.8,True)
root.text('Battery: conventional 4.20V-max Li-ion, NOT LiFePO4 or HV Li-ion.\nNormal loaded operation about 3.0-4.2V; cold start about 3.3V.\nExternal protected pack required. No on-board charger or PV input.\nPCB release status: see RELEASE.md and final review reports.\nRF isolation, converter stability and throughput require first-board validation.',25.4,226.06,1.4)

# POWER SHEET --------------------------------------------------------------
power.text('BATTERY INPUT / REVERSE POLARITY',22.86,22.86,1.7,True)
power.component('Connector_Generic:Conn_01x02','J1','1S Li-ion pack',40.64,43.18,{'1':'BAT_PLUS','2':'GND'},footprint='Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical',mpn='B2P-VH(LF)(SN)')
power.component('Device:Fuse','F1','5A fuse',83.82,40.64,{'1':'BAT_PLUS','2':'BAT_FUSED'},rotation=90,footprint='Fuse:Fuse_Littelfuse-NANO2-451_453',mpn='0451005.MRL')
power.component(mos,'Q1','DMP2008UFG-7',139.7,45.72,{'1':'VBAT_PROTECTED','2':'VBAT_PROTECTED','3':'VBAT_PROTECTED','4':'REV_GATE','5':'BAT_FUSED'},mpn='DMP2008UFG-7')
resistor(power,'R1','100k',83.82,63.5,'REV_GATE','GND')
power.text('Q1 drain faces battery, source faces converter.\nBody diode initially conducts toward load.\nProtected pack / connector must support >=5A peak.\nFuse is not a substitute for cell protection.',22.86,78.74,1.25)

power.text('3.3V BUCK-BOOST / LTC3119 TA06 BASIS',22.86,111.76,1.7,True)
pn={str(n):'GND' for n in [4,9,14,20,25,29]}
pn.update({'3':'BST2','5':'SW2','6':'+3V3','7':'+3V3','8':'SW2','10':'PWR_GOOD','11':'REG_VCC','12':'REG_FB','13':'REG_VC','15':'REG_VCC','16':'REG_VCC','17':'REG_RT','18':'REG_RUN','19':'VBAT_PROTECTED','21':'SW1','22':'VBAT_PROTECTED','23':'VBAT_PROTECTED','24':'SW1','26':'BST1','28':'GND'})
power.component(ltc,'U1','LTC3119IFE#PBF',139.7,180.34,pn,mpn='LTC3119IFE#PBF')
power.component('Device:L','L1','4.7uH',139.7,101.6,{'1':'SW1','2':'SW2'},rotation=90,footprint='Inductor_SMD:L_Coilcraft_XAL7070-XXX',mpn='XAL7070-472MEC')
capacitor(power,'C1','100n / 16V',106.68,101.6,'BST1','SW1')
capacitor(power,'C2','100n / 16V',175.26,101.6,'BST2','SW2')
for n,x,value in [(3,203.2,'22u / 10V X7R'),(4,236.22,'22u / 10V X7R'),(5,269.24,'100n / 10V')]:
    capacitor(power,'C'+str(n),value,x,45.72,'VBAT_PROTECTED',footprint='Capacitor_SMD:C_0805_2012Metric' if n<5 else CFP)
capacitor(power,'C6','100u / 10V bulk',307.34,45.72,'VBAT_PROTECTED',footprint='Capacitor_SMD:CP_Elec_6.3x5.8')
capacitor(power,'C7','220u / 6.3V polymer',203.2,91.44,'+3V3',footprint='Capacitor_SMD:CP_Elec_6.3x5.9',mpn='6SVPE220M')
capacitor(power,'C8','22u / 10V X7R',248.92,91.44,'+3V3',footprint='Capacitor_SMD:C_0805_2012Metric')
capacitor(power,'C9','100n / 10V',289.56,91.44,'+3V3')
power.text('OUTPUT: 2.2A rail budget; 3A transient validation target.\n3 x C5 supply capability >=0.6A each + RP and margin.\nNot a guaranteed continuous 3A rating at every input/temperature.',203.2,111.76,1.2)
resistor(power,'R2','316k 1%',218.44,144.78,'+3V3','REG_FB')
resistor(power,'R3','100k 1%',279.4,144.78,'REG_FB','GND')
resistor(power,'R4','78.7k 1%',218.44,167.64,'REG_VC','COMP_RC')
capacitor(power,'C10','820p C0G',281.94,167.64,'COMP_RC',label_stub=0)
resistor(power,'R5','162k 1%',218.44,193.04,'REG_RT','GND')
capacitor(power,'C11','4.7u / 10V',281.94,198.12,'REG_VCC',footprint='Capacitor_SMD:C_0805_2012Metric',label_stub=0)
power.component('Device:D_Schottky','D1','PMEG2010EA',335.28,193.04,{'1':'REG_VCC','2':'+3V3'},footprint='Diode_SMD:D_SOD-323',mpn='PMEG2010EA,115')
resistor(power,'R6','100k',335.28,144.78,'+3V3','PWR_GOOD')
power.text('500kHz; VOUT = 0.795 x (1 + 316k/100k) = 3.307V nominal.\nMPPC tied to VCC (disabled). PWM/SYNC = GND (Burst allowed).\nSGND and PGND meet at exposed-pad ground; honor TA06 layout.\nD1: anode=3V3, cathode=VCC; do not short VCC to 3V3.',203.2,210.82,1.2)

power.text('BATTERY UVLO / USER OFF',22.86,238.76,1.5,True)
resistor(power,'R7','174k 1%',48.26,254,'VBAT_PROTECTED','REG_RUN')
resistor(power,'R8','100k 1%',116.84,254,'REG_RUN','GND')
capacitor(power,'C12','470p C0G',170.18,254,'REG_RUN')
power.component('Connector_Generic:Conn_01x02','J2','OFF jumper',226.06,254,{'1':'REG_RUN','2':'GND'},footprint='Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical')
power.text('RUN nominal: on 3.30V / off 3.01V; tolerances/load sag apply.\nNo external charger/PV input is provided.',259.08,243.84,1.2)
for i,net in enumerate(['GND','VBAT_PROTECTED']):power.component('power:PWR_FLAG',f'#FLG0{i+1}',net,35.56+i*30.48,205.74,{'1':net})

# RP2350B SHEET ------------------------------------------------------------
rp.text('RP2350B / QFN80 + EP81',22.86,22.86,1.8,True)
rpn={p['name']:'+3V3' for p in pins_of(library_symbol('MCU_RaspberryPi:RP2350B')) if p['name'] in ['IOVDD','ADC_AVDD','QSPI_IOVDD','USB_OTP_VDD','VREG_VIN']}
rpn.update({'DVDD':'CORE_1V1','VREG_AVDD':'VREG_A','VREG_LX':'VREG_LX','VREG_FB':'CORE_1V1','VREG_PGND':'GND','GND':'GND','RUN':'RP_RUN','XIN':'XIN','XOUT':'XOUT','SWCLK':'SWCLK','SWDIO':'SWDIO','USB_DM':'RP_USB_DM','USB_DP':'RP_USB_DP','~{QSPI_SS}':'QSPI_CS','QSPI_SCLK':'QSPI_CLK','QSPI_SD0':'QSPI_IO0','QSPI_SD1':'QSPI_IO1','QSPI_SD2':'QSPI_IO2','QSPI_SD3':'QSPI_IO3','GPIO36':'PWR_GOOD','GPIO37':'USB_VBUS_SENSE'})
signals=['TX_D0','TX_D1','TX_D2','TX_D3','TX_CLK','TX_VALID','RX_D0','RX_D1','RX_D2','RX_D3','RX_CLK','RX_VALID']
for i,letter in enumerate('ABC'):
    for j,sig in enumerate(signals):rpn['GPIO'+str(i*12+j)]=letter+'_'+sig
rp.component('MCU_RaspberryPi:RP2350B','U101','RP2350B',190.5,119.38,rpn,mpn='RP2350B',fields=(224.79,50.8,224.79,53.34))
rp.text('PIO0 BASE0: GPIO0..11 = A\nPIO1 BASE0: GPIO12..23 = B\nPIO2 BASE16: GPIO24..35 = C\n36 = PGOOD; 37 = USB sense (FT pad)\n38..47 reserved (NC); battery ADC deferred.\nPIO timing/programs NOT validated.',238.76,134.62,1.2)
rp.text('CORE BUCK - follow official R4-S1 placement and L orientation',22.86,35.56,1.25,True)
resistor(rp,'R101','33R',50.8,50.8,'+3V3','VREG_A')
capacitor(rp,'C101','4.7u X5R 20%',91.44,50.8,'VREG_A')
capacitor(rp,'C102','4.7u X5R 20%',124.46,50.8,'+3V3')
rp.component('Device:L','L101','3.3uH - oriented',50.8,76.2,{'1':'CORE_1V1','2':'VREG_LX'},rotation=90,footprint='FarmMesh:AOTA-B201610S3R3-101-T',mpn='AOTA-B201610S3R3-101-T')
capacitor(rp,'C103','4.7u X5R 20%',99.06,76.2,'CORE_1V1')
rp.component('power:PWR_FLAG','#FLG101','CORE_1V1',132.08,76.2,{'1':'CORE_1V1'})
rp.component('power:PWR_FLAG','#FLG102','VREG_A',132.08,55.88,{'1':'VREG_A'})
rp.text('L101 pad2=LX; pad1=1V1.\nDo not substitute orientation blindly.',22.86,88.9,1.1)
rp.component('Memory_Flash:W25Q128JVS','U102','W25Q128JVSIQ',78.74,121.92,{'1':'QSPI_CS','2':'QSPI_IO1','3':'QSPI_IO2','4':'GND','5':'QSPI_IO0','6':'QSPI_CLK','7':'QSPI_IO3','8':'+3V3'},mpn='W25Q128JVSIQ',fields=(96.52,99.06,96.52,101.6))
capacitor(rp,'C104','100n',121.92,119.38,'+3V3')
resistor(rp,'R102','10k',48.26,152.4,'+3V3','QSPI_CS')
resistor(rp,'R103','1k',111.76,152.4,'QSPI_CS','BOOT_BUTTON')
rp.component('Switch:SW_Push','SW101','BOOTSEL',66.04,175.26,{'1':'BOOT_BUTTON','2':'GND'},footprint='Button_Switch_SMD:SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG')
rp.component('Switch:SW_Push','SW102','RESET',121.92,175.26,{'1':'RP_RUN','2':'RP_RST_R'},footprint='Button_Switch_SMD:SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG')
resistor(rp,'R104','1k',116.84,195.58,'RP_RST_R','GND')
rp.component('Device:Crystal_GND24','Y101','12MHz ABM8-272-T3',48.26,205.74,{'1':'XIN','3':'XTAL_OUT','2':'GND','4':'GND'},footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',mpn='ABM8-272-T3')
resistor(rp,'R105','1k',111.76,220.98,'XOUT','XTAL_OUT')
capacitor(rp,'C105','15p C0G',30.48,228.6,'XIN')
capacitor(rp,'C106','15p C0G',68.58,228.6,'XTAL_OUT')
rp.text('LOCAL DECOUPLING - one 100n at each listed supply pad',157.48,193.04,1.4,True)
decoupling=[5,15,24,29,41,50,60,76,59,68,69,10,32,51]
for i,pad in enumerate(decoupling):
    x=162.56+(i%7)*33.02;y=215.9+(i//7)*25.4
    net='CORE_1V1' if pad in [10,32,51] else '+3V3'
    capacitor(rp,'C'+str(110+i),'100n pin'+str(pad),x,y,net,label_stub=0)
capacitor(rp,'C124','4.7u at pad32',111.76,256.54,'CORE_1V1')
rp.text('SWD DEBUG',266.7,25.4,1.4,True)
rp.component('Connector_Generic:Conn_01x05','J101','SWD / 3V3 ref only',294.64,48.26,{'1':'+3V3','2':'SWDIO','3':'GND','4':'SWCLK','5':'RP_RUN'},footprint='Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical')

# A small dedicated USB sub-sheet keeps the dense RP decoupling page readable.
usb=Sheet('06-usb','RP USB boot / self-powered USB-C',7)
root.subsheet(usb,228.6,218.44,135,25.4)
usb.text('RP USB-C / BATTERY POWER REQUIRED',25.4,25.4,2,True)
usb.text('USB VBUS does not power the board or charge the battery.\nHardware disconnects USB data below approximately 4.19V VBUS, including ROM BOOTSEL.\nC5 USB pads are allocated to PARLIO; each C5 uses its UART header.',25.4,38.1,1.4)
usb_nets={'A1':'GND','A12':'GND','B1':'GND','B12':'GND','SH':'GND','A4':'USB_VBUS','A9':'USB_VBUS','B4':'USB_VBUS','B9':'USB_VBUS','A5':'USB_CC1','B5':'USB_CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM'}
usb.component('Connector:USB_C_Receptacle_USB2.0_16P','J102','USB4105-GF-A',58.42,101.6,usb_nets,footprint='Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal',mpn='USB4105-GF-A')
resistor(usb,'R108','5.1k 1%',121.92,81.28,'USB_CC1','GND')
resistor(usb,'R109','5.1k 1%',121.92,111.76,'USB_CC2','GND')
usb.component('Power_Protection:USBLC6-2SC6','D101','USBLC6-2SC6',180.34,99.06,{'1':'USB_DP','6':'USB_DP_ESD','3':'USB_DM','4':'USB_DM_ESD','2':'GND','5':'USB_VBUS'},mpn='USBLC6-2SC6',fields=(167.64,68.58,167.64,71.12))

# TS3USB30E DGS/VSSOP pinout: TI Rev G p3, truth table p12.
# DGS and RSW pin maps differ. OE=1 disconnects; S=0/OE=0 selects D1.
# Stock TSSOP-10_3x3 footprint fits the DGS 3x3mm body/0.5mm pitch, no EP.
usw=custom_ic('TS3USB30E_DGS',[
    (4,'D+','passive',-22.86,15.24,0),(6,'D-','passive',-22.86,5.08,0),
    (9,'~{OE}','input',-22.86,-5.08,0),(1,'S','input',-22.86,-15.24,0),
    (5,'GND','power_in',-22.86,-25.4,0),(2,'D1+','passive',22.86,15.24,180),
    (8,'D1-','passive',22.86,5.08,180),(3,'D2+','passive',22.86,-5.08,180),
    (7,'D2-','passive',22.86,-15.24,180),(10,'VCC','power_in',22.86,-25.4,180)],
    'Package_SO:TSSOP-10_3x3mm_P0.5mm','https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf',35.56,60.96)
usb.component(usw,'U103','TS3USB30EDGSR',266.7,99.06,{'1':'GND','2':'USB_DP_SW','4':'USB_DP_ESD','5':'GND','6':'USB_DM_ESD','8':'USB_DM_SW','9':'USB_DISCONNECT','10':'+3V3'},mpn='TS3USB30EDGSR')
resistor(usb,'R110','27R at RP',355.6,83.82,'USB_DP_SW','RP_USB_DP')
resistor(usb,'R111','27R at RP',355.6,106.68,'USB_DM_SW','RP_USB_DM')
capacitor(usb,'C128','100n / 16V at U103',355.6,137.16,'+3V3')
capacitor(usb,'C127','100n / 16V at D101',180.34,137.16,'USB_VBUS')

# TLV3011B DBV pinout: TI Rev C p3. B suffix is mandatory: fail-safe inputs
# tolerate live VBUS with board off; open-drain POR defaults high impedance.
vbuscmp=custom_ic('TLV3011B_DBV',[
    (3,'IN+','input',-20.32,7.62,0),(4,'IN-','input',-20.32,-2.54,0),
    (2,'V-','power_in',-20.32,-12.7,0),(1,'OUT','open_collector',20.32,7.62,180),
    (5,'REF','output',20.32,-2.54,180),(6,'V+','power_in',20.32,-12.7,180)],
    'Package_TO_SOT_SMD:SOT-23-6','https://www.ti.com/lit/ds/symlink/tlv3011.pdf',30.48,35.56)
usb.text('VBUS HARDWARE QUALIFICATION - NO FIRMWARE DEPENDENCY',25.4,160.02,1.4,True)
resistor(usb,'R114','237k 0.1%',86.36,185.42,'USB_VBUS','USB_VBUS_CMP')
resistor(usb,'R115','100k 0.1%',86.36,210.82,'USB_VBUS_CMP','GND')
usb.component(vbuscmp,'U104','TLV3011BIDBVR',228.6,200.66,{'1':'USB_DISCONNECT','2':'GND','3':'USB_REF','4':'USB_VBUS_CMP','5':'USB_REF','6':'+3V3'},mpn='TLV3011BIDBVR',fields=(223.52,177.8,223.52,180.34))
resistor(usb,'R116','10k OE pull-up',337.82,180.34,'+3V3','USB_DISCONNECT')
capacitor(usb,'C129','100n / 16V at U104',337.82,213.36,'+3V3')
capacitor(usb,'C130','1n C0G REF',152.4,213.36,'USB_REF')

# Independent firmware VBUS sense remains on FT GPIO37; no ADC/battery sense.
resistor(usb,'R112','5.1k 1%',86.36,251.46,'USB_VBUS','USB_VBUS_SENSE')
resistor(usb,'R113','7.5k 1%',210.82,251.46,'USB_VBUS_SENSE','GND')
capacitor(usb,'C126','10n',269.24,248.92,'USB_VBUS_SENSE')
usb.component('power:PWR_FLAG','#FLG103','USB_VBUS',370.84,223.52,{'1':'USB_VBUS'})
usb.text('GPIO37: FT input; 5.1k/7.5k divider; disable internal pulls. U104 B variant required.\nU103 OE defaults high (disconnected). VBUS trip tolerances/power ordering need sample validation.\n90 ohm USB pair: J102 -> D101 -> U103 -> 27R near RP. Keep ESD on connector side.',25.4,271.78,1.15)

# Global cross-sheet nets also include RP USB and VBUS sensing.
# See GLOBAL_EXTRA in builder; this is an explicit interface, not a PCB route.

# THREE RADIO SHEETS -------------------------------------------------------
for i,(s,letter) in enumerate(zip(radios,'ABC')):
    base=200+i*100
    s.text(f'ESP32-C5 MODULE {letter} / UART PROGRAMMING / INDEPENDENT 12-SIGNAL LINK',22.86,22.86,1.7,True)
    s.text('C5 TX and RX clocks both originate here. RP never drives either clock.\nUART0 download retained; C5 native USB disabled to release GPIO13/14.\nAll interface GPIOs avoid boot straps and internal Flash/PSRAM.',22.86,33.02,1.3)
    mn={'1':'GND','2':'+3V3','3':letter+'_EN','15':letter+'_BOOT','18':letter+'_STRAP27','24':letter+'_UART_RX','25':letter+'_UART_TX','28':'GND','29':'GND','30':'GND','32':'GND'}
    for pad,sig in zip(ordered,signals):mn[str(pad)]=letter+'_'+sig+'_C5'
    s.component(c5sym,f'U{base+1}','ESP32-C5-WROOM-1U-N8R8',101.6,116.84,mn,mpn='ESP32-C5-WROOM-1U-N8R8')
    s.text('22R initial series damping; validate edges on hardware.',165.1,66.04,1.3,True)
    for j,sig in enumerate(signals):
        yy=78.74+j*10.16
        resistor(s,f'R{base+10+j}','22R',203.2,yy,letter+'_'+sig+'_C5',letter+'_'+sig)
        src='C5 source' if sig.startswith('TX') or sig=='RX_CLK' else 'RP source'
        s.text(src,266.7,yy-2.54,1.1)
    for k,x,value in [(1,175.26,'22u / 10V X7R'),(2,220.98,'100n / 10V'),(3,266.7,'100u / 6.3V bulk')]:
        capacitor(s,f'C{base+k}',value,x,50.8,'+3V3',footprint='Capacitor_SMD:C_0805_2012Metric' if k==1 else 'Capacitor_SMD:CP_Elec_6.3x5.8' if k==3 else CFP)
    s.text('Place 22u + 100n at pad2, short ground return.\n100u polymer reservoir; measure full rail stability.\nANT1 needs an external 2.4/5 GHz antenna and cable.\nPad31 ANT2 remains unused on the default module.',304.8,48.26,1.1)
    resistor(s,f'R{base+1}','10k',45.72,172.72,'+3V3',letter+'_EN')
    capacitor(s,f'C{base+4}','1u / 10V',106.68,172.72,letter+'_EN')
    s.component('Switch:SW_Push',f'SW{base+1}','RESET',53.34,200.66,{'1':letter+'_EN','2':'GND'},footprint='Button_Switch_SMD:SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG')
    resistor(s,f'R{base+2}','10k',132.08,203.2,'+3V3',letter+'_BOOT')
    s.component('Switch:SW_Push',f'SW{base+2}','BOOT',53.34,226.06,{'1':letter+'_BOOT','2':'GND'},footprint='Button_Switch_SMD:SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG')
    resistor(s,f'R{base+3}','10k',132.08,228.6,'+3V3',letter+'_STRAP27')
    s.component('Connector_Generic:Conn_01x06',f'J{base+1}','UART / 3V3 reference only',220.98,238.76,{'1':'GND','2':letter+'_UART_TX','3':letter+'_UART_RX','4':letter+'_EN','5':letter+'_BOOT','6':'+3V3'},footprint='Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical')
    resistor(s,f'R{base+4}','4.7k VALID idle low',332.74,157.48,letter+'_TX_VALID','GND')
    resistor(s,f'R{base+5}','4.7k VALID idle low',332.74,187.96,letter+'_RX_VALID_C5','GND')
    s.text('Place each VALID pull-down at its receiver.',299.72,210.82,1.1)
    s.text('DOWNLOAD: hold BOOT (GPIO28 low), pulse RESET; GPIO27 stays high.\n3.3V logic UART only; header pin6 is a voltage reference, not a power input.\nUSB D+ startup transitions may appear on TX data: RP stays input and ignores\ndata until C5 configures PARLIO and asserts VALID. Pre-arm all RX transactions.\nSeries resistors belong at the listed source, regardless of schematic page.',22.86,251.46,1.15)

mechanical=Sheet('07-test-mechanical','Test access and mechanical features',8)
root.subsheet(mechanical,144.78,66.04,73.66,25.4)
mechanical.text('TEST ACCESS / FABRICATED PCB FEATURES',25.4,25.4,2,True)
mechanical.text('Exposed copper test pads and unplated mounting holes are part of the PCB.\nNo assembly component is fitted to these references. Test ground first.\nAll voltages are relative to GND. Use current-limited battery supply on first power-up.',25.4,38.1,1.5)
for i,(ref,net) in enumerate([('TP1','VBAT_PROTECTED'),('TP2','+3V3'),('TP3','GND'),('TP101','CORE_1V1'),('TP102','GND'),('TP103','RP_RUN'),('TP104','PWR_GOOD')]):
    mechanical.component('Connector:TestPoint',ref,net,40.64+(i%4)*81.28,91.44+(i//4)*50.8,{'1':net},footprint='TestPoint:TestPoint_Pad_D1.5mm',mpn='PCB-FEATURE')
for i in range(4):
    mechanical.component('Mechanical:MountingHole',f'H{i+1}','M3 / 3.2mm NPTH',40.64+i*81.28,205.74,footprint='MountingHole:MountingHole_3.2mm_M3',mpn='PCB-FEATURE')
for s in [root,power,rp,*radios,usb,mechanical]:s.save()
save_library()
pro=BASE/(PROJECT+'.kicad_pro')
if not pro.exists():pro.write_text(json.dumps({'meta':{'filename':PROJECT+'.kicad_pro','version':1}},indent=2)+'\n')
print(f'Generated {len(MANIFEST)} component instances across 8 sheets')
