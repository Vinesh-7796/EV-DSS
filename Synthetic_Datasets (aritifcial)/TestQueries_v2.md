# EV DDSS Test Queries v2 — 75 Evaluation Questions

Multi-hop Reasoning | Cross-Document Retrieval | Entity Resolution | Diagnostic Logic

---

## Query 1
**Question:** Motor does not rotate and error code P0A94 is displayed.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 10.1, 11.1
- EngineeringDatabase_v2.xlsx — ErrorCodes P0A94, Connectors C21/C42, Fuses F18, Relays K2, CAN 0x181

**Expected Excel Rows:**
- ErrorCodes: P0A94
- Connectors: C21, C42
- Fuses: F18
- Relays: K2
- CAN Messages: 0x181
- DiagnosticMeasurements: F18, C21, K2

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — Battery Pack -> F18 -> K2 -> C21 -> MCU

**Expected Entities:**
- P0A94
- C21
- F18
- K2
- MotorRPM
- 0x181

**Reasoning Chain:** Check BatteryVoltage (0x182) -> F18 continuity -> K2 operation -> HV at C21 -> MotorRPM on 0x181 -> resolver at C42 -> MCU fault log

**Expected Summary:** 1) BatteryVoltage on 0x182: 320-390V. 2) F18 < 0.5 Ohm. 3) K2 click, coil ~25 Ohm. 4) C21 pins 1-2: 355V. 5) 0x181 MotorRPM. 6) C42 pins 1-4 resolver: 20-40 Ohm. 7) MCU fault log via 0x201.

---
## Query 2
**Question:** Coolant over-temperature warning. P1C21 stored. CoolantTemp = 95C on scan tool.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 10.2, 11.2, 5.1, 5.2
- EngineeringDatabase_v2.xlsx — ErrorCodes P1C21, Fuses F21, Relays K5, CAN Signals CoolantTemp

**Expected Excel Rows:**
- ErrorCodes: P1C21
- Fuses: F21
- Relays: K5
- CAN Signals: CoolantTemp
- DiagnosticMeasurements: F21, K5, Pump

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — F21 -> K5 -> Cooling Pump -> Temp Sensor

**Expected Entities:**
- P1C21
- F21
- K5
- CoolantTemp
- 0x182
- Cooling Pump

**Reasoning Chain:** Read CoolantTemp (0x182) -> Coolant level -> F21 -> K5 coil -> Activate pump via 0x201 -> Pump resistance -> NTC at C42 pin 11

**Expected Summary:** CoolantTemp 95C > 85C. Check coolant level. F21 < 0.5 Ohm. K5 coil ~85 Ohm. Activate pump via 0x201 byte 3=0x01. Pump motor: 0.8-1.2 Ohm. NTC at C42 pin 11: ~10k Ohm @ 25C.

---
## Query 3
**Question:** P2B07 displayed. No CAN communication with Motor Controller.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 10.3, 11.3, 7.1, 8
- EngineeringDatabase_v2.xlsx — ErrorCodes P2B07, Connectors C42, CAN Messages, DiagnosticMeasurements

**Expected Excel Rows:**
- ErrorCodes: P2B07
- Connectors: C42
- CAN Messages: 0x181/0x182/0x201
- DiagnosticMeasurements: C42 Pin5, C42 Pin7-8

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — C42 -> CAN Bus -> VCU

**Expected Entities:**
- P2B07
- C42
- 0x181
- 0x182
- 0x201
- CAN-H (pin7)
- CAN-L (pin8)

**Reasoning Chain:** 12V at C42 pin5 -> CAN term C42 pins7-8 (60 Ohm) -> CAN DC levels -> Monitor traffic -> Inspect C42

**Expected Summary:** C42 pin5: 11.5-13.5V. C42 pins7-8: 60 Ohm. 120 Ohm = missing term. <50 Ohm = short. CAN-H ~2.5V, CAN-L ~2.5V. Expect 0x181/0x182/0x201 @10Hz.

---
## Query 4
**Question:** P3F10 active. Cooling system degraded. CoolantTemp = 92C.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 10.4, 11.4, 5.2, 9
- EngineeringDatabase_v2.xlsx — ErrorCodes P3F10, Fuses F21, Relays K5, CoolantTemp

**Expected Excel Rows:**
- ErrorCodes: P3F10
- Fuses: F21
- Relays: K5
- CAN Signals: CoolantTemp
- DiagnosticMeasurements: F21, K5, Pump

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — F21 -> K5 -> Cooling Pump

**Expected Entities:**
- P3F10
- F21
- K5
- CoolantTemp
- 0x182
- 0x201

**Reasoning Chain:** CoolantTemp 92C > 85C. F21 continuity. K5 actuation via 0x201. Coolant level & glycol%. Radiator fan.

**Expected Summary:** Verify F21 (< 0.5 Ohm). Actuate K5 via 0x201 byte3=0x01. Listen for pump. Coolant level MIN-MAX. Glycol 48-52%. Radiator fan at 85C.

---
## Query 5
**Question:** Fuse F18 suspected blown. Diagnosis and replacement?

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 9 (Table 9.1), 11.1
- EngineeringDatabase_v2.xlsx — Fuses: F18, DiagnosticMeasurements

**Expected Excel Rows:**
- Fuses: F18
- DiagnosticMeasurements: F18

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — F18 location

**Expected Entities:**
- F18
- 250A
- gR
- Battery Pack Junction Box

**Reasoning Chain:** F18 is 250A gR in Battery Pack J-Box. Continuity < 0.5 Ohm. If open, inspect MCU for short. Replace: EV-F18-250A.

**Expected Summary:** F18 (250A gR) in Battery Pack Junction Box. Continuity < 0.5 Ohm. If blown: check MCU for short before replacement. Part: EV-F18-250A.

---
## Query 6
**Question:** Cooling pump does not activate. F21 intact.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 5.2, 9, 11.2
- EngineeringDatabase_v2.xlsx — Relays: K5, DiagnosticMeasurements

**Expected Excel Rows:**
- Fuses: F21
- Relays: K5
- DiagnosticMeasurements: K5 Coil, Pump Motor

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — K5 -> Cooling Pump

**Expected Entities:**
- F21
- K5
- Cooling Pump
- 0x201
- C42

**Reasoning Chain:** F21 OK. K5 coil ~85 Ohm. Activate via 0x201 byte3=0x01. Pump motor 0.8-1.2 Ohm. 12V at C42 pin5.

**Expected Summary:** F21 < 0.5 Ohm OK. K5 coil ~85 Ohm. Actuate via 0x201 byte3=0x01, byte4=0x01. Pump motor: 0.8-1.2 Ohm. 12V at C42 pin5 (W201).

---
## Query 7
**Question:** BatteryVoltage reads 0V on diagnostic tool.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 7 (Table 7.2), 11.5
- EngineeringDatabase_v2.xlsx — CAN Signals: BatteryVoltage

**Expected Excel Rows:**
- CAN Signals: BatteryVoltage
- CAN Messages: 0x182
- Connectors: C21

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — Battery -> CAN Bus -> VCU

**Expected Entities:**
- BatteryVoltage
- 0x182
- C21
- C42

**Reasoning Chain:** BatteryVoltage on 0x182 bytes 2-3, bit16, len16, scale 0.1V/bit. BMS offline? Compare direct at C21 (320-390V).

**Expected Summary:** 0x182 bytes 2-3: BatteryVoltage, scale 0.1V/bit. If 0V: BMS offline. Check CAN. Direct HV at C21 pins 1-2: expected 320-390V.

---
## Query 8
**Question:** MotorRPM erratic at steady speed.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 7 (Table 7.2), 3.2
- EngineeringDatabase_v2.xlsx — CAN Signals: MotorRPM, Connectors: C42

**Expected Excel Rows:**
- CAN Signals: MotorRPM
- CAN Messages: 0x181
- Connectors: C42, C35

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — MotorRPM label near Traction Motor

**Expected Entities:**
- MotorRPM
- 0x181
- C42
- C35

**Reasoning Chain:** MotorRPM on 0x181 bits 0-15, scale 0.125. Check resolver C42 pins 1-4 (20-40 Ohm). SIN/COS ratio 0.9-1.1. C35 torque 8Nm.

**Expected Summary:** 0x181 MotorRPM erratic: resolver fault or electrical noise. C42 pins 1-4: 20-40 Ohm. SIN/COS ratio 0.9-1.1. C35 bolts: 8Nm.

---
## Query 9
**Question:** Where is F21 located? Specifications?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 9 (Table 9.1)
- EngineeringDatabase_v2.xlsx — Fuses: F21

**Expected Excel Rows:**
- Fuses: F21

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — F21 label

**Expected Entities:**
- F21
- 50A
- Medium-blow
- Cabin Fuse Panel Slot 21

**Reasoning Chain:** F21: 50A medium-blow LV blade fuse in Cabin Fuse Panel Slot 21. Protects Cooling Pump. Part: EV-F21-50A.

**Expected Summary:** F21 = 50A medium-blow LV fuse, Cabin Fuse Panel Slot 21. Circuit: Cooling Pump. Spare: EV-F21-50A.

---
## Query 10
**Question:** Complete pinout of connector C42.

**Expected Documents:**
- ServiceManual_v2.pdf — Section 8 (Table 8.4)
- EngineeringDatabase_v2.xlsx — ConnectorPinout: C42

**Expected Excel Rows:**
- ConnectorPinout: C42 (all 12 pins)

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png — C42 detail

**Expected Entities:**
- C42
- Resolver
- CAN-H
- CAN-L
- 12V
- NTC
- CoolantTemp

**Reasoning Chain:** C42 is 12-pin LV on MCU side. Pins 1-4: resolver (Grn/Blu). Pin5: 12V (Red). Pin6: GND (Blk). Pins7-8: CAN-H/Yel, CAN-L/YelBlk. Pins9-10: NTC1/2 (Wht). Pins11-12: CoolantTemp In/Out (Violet).

**Expected Summary:** Pin1-2: Resolver SIN+/- (Grn/GrnWht, 20-40 Ohm). Pin3-4: COS+/- (Blu/BluWht). Pin5: +12V (Red). Pin6: GND (Blk). Pin7: CAN-H (Yel). Pin8: CAN-L (Yel/Blk). Pin9: NTC1. Pin10: NTC2. Pin11: CoolantTemp In. Pin12: CoolantTemp Out.

---
## Query 11
**Question:** What does relay K2 control? Specifications and location.

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 9 (Table 9.2), 2
- EngineeringDatabase_v2.xlsx — Relays: K2

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- K2
- Main Positive
- 450V/400A
- Battery Pack J-Box
- ~25 Ohm

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** K2 is Main Positive Contactor (HV), SPST NO 450V/400A, in Battery Pack J-Box. Closes after pre-charge. Coil ~25 Ohm.

---
## Query 12
**Question:** What is CAN ID 0x201 used for? Contents and transmission?

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 7 (Table 7.1), 4
- EngineeringDatabase_v2.xlsx — CAN Messages: 0x201, ECUList: VCU,MCU,BMS

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- 0x201
- VCU Command
- TorqueDemand
- PumpCmd
- DiagService

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** 0x201 from VCU to MCU/BMS/TMM at 10Hz. DLC 8. TorqueDemand bytes0-1 (0.1Nm/bit). PumpCmd byte3. FanCmd byte4. DiagService byte7.

---
## Query 13
**Question:** How to perform motor winding resistance test?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 3.1
- EngineeringDatabase_v2.xlsx — Connectors: C35, TorqueSpecifications: C35

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- C35
- 0.025 Ohm
- 5 MOhm
- 8 Nm

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** Disconnect C35. 4-wire DMM: U-V, V-W, W-U = 0.025 Ohm ±10%. Megohmmeter 500V: min 5 MOhm. Imbalance >5% = replace. Torque C35 to 8 Nm.

---
## Query 14
**Question:** Safe HV de-energization procedure? Required PPE?

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 2 Warning, 4 Warning, Appendix C

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- C21
- CAT III
- Class 00
- 5 min

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** De-energize. Wait 5 min (DC link discharge via 47kOhm). Measure C21 pins1-2 < 5V. CAT III 1000V DMM. Class 00 gloves (tested <6mo).

---
## Query 15
**Question:** How to replace coolant and bleed system?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 12.2
- EngineeringDatabase_v2.xlsx — MaintenanceSchedule

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- Coolant
- G12 EVO
- 0x201
- 48-52%

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** Drain, fill G12 EVO 50/50. Run pump via 0x201 byte3=0x01 for 5 min. Bleed air. Verify glycol 48-52% via refractometer.

---
## Query 16
**Question:** MotorCurrent signal encoding details?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 7 (Table 7.2)
- EngineeringDatabase_v2.xlsx — CAN Signals: MotorCurrent

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- MotorCurrent
- 0x182
- 0.1 A/bit
- -400 A offset

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** MotorCurrent on 0x182 bytes0-1, start bit0, len16, scale 0.1 A/bit, offset -400A, range -400 to +400A. Intel order.

---
## Query 17
**Question:** Connector C21 inspection? Torque? Wire details?

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 8 (Table 8.2), 12.1, Appendix B
- EngineeringDatabase_v2.xlsx — ConnectorPinout: C21

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- C21
- 12 Nm
- W101
- W102
- 50 mm^2

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** C21: 2-pin HV input (orange). Pin1: HV+ W101 (Org, 50mm^2). Pin2: HV- W102 (Org/Blk, 50mm^2). Check overheating. Torque: 12 Nm (M8).

---
## Query 18
**Question:** Traction motor specifications?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 3 (Table 3.1)
- EngineeringDatabase_v2.xlsx — SensorSpecifications: Resolver

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- PMSM-IPM
- 120kW
- 280Nm
- 12,000rpm
- 0.025 Ohm

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** PMSM-IPM, 120kW/60kW cont, 280Nm, 12,000rpm, 4 pole pairs, Rs=0.025 Ohm, Ld=0.12mH, Lq=0.28mH, liquid-cooled, 52kg, Class H.

---
## Query 19
**Question:** MCU power supply verification steps?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 4.1
- EngineeringDatabase_v2.xlsx — DiagnosticMeasurements: C21, C42

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- F18
- K2
- C21
- 355V
- C42
- 12V

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** F18 < 0.5 Ohm. Close K2 (click, ~25 Ohm). C21 pins1-2: 320-390V. C42 pin5: 11.5-13.5V. CAN at C42 pins7-8: 60 Ohm. Traffic 0x181/0x182.

---
## Query 20
**Question:** Normal CoolantTemp range and thresholds?

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 5, 7 (Table 7.2)
- EngineeringDatabase_v2.xlsx — CAN Signals: CoolantTemp

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- CoolantTemp
- 0x182
- 50-85C
- 90C warn
- 105C shutdown

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** Normal 50-85C. Warning >90C (derating). Shutdown >105C. On 0x182 byte4, scale 1, offset -40C. NTC at C42 pin11 ~10kOhm @25C.

---
## Query 21
**Question:** Compare F18 and F21: ratings, type, circuit, location.

**Expected Documents:**
- ServiceManual_v2.pdf — Section 9 (Table 9.1)
- EngineeringDatabase_v2.xlsx — Fuses: F18, F21

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- F18
- 250A
- gR
- Battery J-Box
- F21
- 50A
- medium-blow
- Cabin Slot 21

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** F18: 250A gR, HV Main (MCU), Battery Pack J-Box. F21: 50A medium-blow LV, Cooling Pump, Cabin Fuse Panel Slot 21.

---
## Query 22
**Question:** Compare K2 and K5: function, type, location, coil R, rating.

**Expected Documents:**
- ServiceManual_v2.pdf — Section 9 (Table 9.2)
- EngineeringDatabase_v2.xlsx — Relays: K2, K5

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- K2
- Main Positive
- 450V/400A
- ~25 Ohm
- K5
- Cooling Pump
- 12V/30A
- ~85 Ohm

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** K2: Main Positive HV, SPST NO 450V/400A, Battery J-Box, ~25 Ohm. K5: Cooling Pump LV, SPST NO 12V/30A, Cabin Slot 22, ~85 Ohm.

---
## Query 23
**Question:** All DTCs and severities?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 10
- EngineeringDatabase_v2.xlsx — ErrorCodes: all

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- P0A94 HIGH
- P1C21 MED
- P2B07 HIGH
- P3F10 MED
- P0A00 MED
- P1A01 HIGH

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** P0A94 (HIGH) MCU HV Fault. P1C21 (MED) Motor Overtemp. P2B07 (HIGH) CAN Lost. P3F10 (MED) Cooling. P0A00 (MED) BatteryVoltage. P1A01 (HIGH) Resolver Loss.

---
## Query 24
**Question:** CAN details for MotorRPM and BatteryVoltage?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 7 (Table 7.2)
- EngineeringDatabase_v2.xlsx — CAN Signals

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- MotorRPM
- 0.125
- 0x181
- BatteryVoltage
- 0.1
- 0x182

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** MotorRPM: 0x181 bytes0-1, bit0, len16, 0.125 rpm/bit, range 0-12,000. BatteryVoltage: 0x182 bytes2-3, bit16, len16, 0.1V/bit, range 0-500V.

---
## Query 25
**Question:** Recommended HV diagnostic tools?

**Expected Documents:**
- ServiceManual_v2.pdf — Appendix C
- EngineeringDatabase_v2.xlsx — -

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- CAT III DMM
- Megohmmeter
- CANalyzer
- HV Gloves
- Refractometer

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** CAT III DMM (1000V), Megohmmeter (500V), CANalyzer/CANnect, Oscilloscope (100MHz), HV Gloves Class 00, Refractometer, Torque Wrench (5-50Nm).

---
## Query 26
**Question:** K2 does not close. Diagnostic steps?

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 11.1, 9
- EngineeringDatabase_v2.xlsx — Relays: K2, DiagnosticMeasurements

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- K2
- ~25 Ohm
- 12V
- Battery J-Box

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** Check 12V supply to K2 coil. Measure coil resistance (~25 Ohm). Listen for click. If no click: replace K2. Check pre-charge sequence (K5).

---
## Query 27
**Question:** CAN bus wiring test. How to verify termination?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 7.1
- EngineeringDatabase_v2.xlsx — DiagnosticMeasurements: C42 Pin7-8

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- C42
- 60 Ohm
- 120 Ohm
- CAN-H
- CAN-L

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** Measure C42 pins7-8 (power OFF): expected 60 Ohm (two 120 Ohm in parallel). 120 Ohm = missing terminator. <50 Ohm = short.

---
## Query 28
**Question:** BatteryVoltage on 0x182 reads 300V when direct at C21 is 355V. Diagnosis?

**Expected Documents:**
- ServiceManual_v2.pdf — Sections 11.5, 7
- EngineeringDatabase_v2.xlsx — CAN Signals: BatteryVoltage

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- BatteryVoltage
- 0x182
- C21
- 355V
- BMS

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** CAN 0x182 BatteryVoltage 300V vs direct C21 355V = 55V error > 5V. BMS calibration drift. Check CAN signal corruption. Verify BMS.

---
## Query 29
**Question:** How to test resolver on traction motor?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 3.2
- EngineeringDatabase_v2.xlsx — SensorSpecifications: Resolver, ConnectorPinout: C42

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- C42
- 20-40 Ohm
- SIN/COS
- resolver

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** Disconnect C42. Measure pins1-2 (SIN): 20-40 Ohm. Pins3-4 (COS): 20-40 Ohm. Verify SIN/COS amplitude ratio 0.9-1.1 when rotor rotated.

---
## Query 30
**Question:** MCU fault log read procedure?

**Expected Documents:**
- ServiceManual_v2.pdf — Section 4 Note, 11.1
- EngineeringDatabase_v2.xlsx — CAN Messages: 0x201

**Expected Excel Rows:**
- Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:**
- 0x201
- 0x03
- 0x22
- MCU
- fault log

**Reasoning Chain:** Cross-reference Service Manual section with Engineering Database.

**Expected Summary:** Use CAN diagnostic service: 0x201 byte7=0x03, subfunction 0x22. MCU stores last 10 fault events with timestamps.

---
## Query 31
**Question:** What is the cooling system total capacity and pump flow rate?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 32
**Question:** Where is the coolant temperature sensor located and what type is it?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 33
**Question:** What does the BMS monitor and at what accuracy?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 34
**Question:** Which connector carries the 12V supply to the MCU and what is the wire color?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 35
**Question:** What is the pre-charge sequence for the HV contactors?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 36
**Question:** What are the CAN signal details for MotorCurrent on 0x182?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 37
**Question:** Compare the pinout of C21 and C35 connectors.

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 38
**Question:** What is the part number for F18 and where to order it?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 39
**Question:** What maintenance is required at 40,000 km?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 40
**Question:** What is the insulation test minimum acceptable value at 355V?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 41
**Question:** Which ECUs receive CAN ID 0x201?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 42
**Question:** What is the MCU switching frequency range?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 43
**Question:** How to verify coolant glycol concentration?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 44
**Question:** What torque for C35 phase connector bolts?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 45
**Question:** Which wire carries the CAN-H signal and what color?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 46
**Question:** What does error P1A01 indicate and how to troubleshoot?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 47
**Question:** What is the total weight of the battery pack?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 48
**Question:** Which fuse protects the cooling pump circuit?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 49
**Question:** How to check resolver integrity without oscilloscope?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 50
**Question:** What is the CAN bus nominal data rate?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 51
**Question:** Which relay controls the cooling pump?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 52
**Question:** What is the radiator fan activation temperature?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 53
**Question:** Where is the VCU located in the vehicle?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 54
**Question:** What is the purpose of the TMM module?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 55
**Question:** How to read MCU fault codes via CAN?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 56
**Question:** What is the HVIL loop maximum resistance?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 57
**Question:** What is the C42 connector wire color for NTC1?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 58
**Question:** How to verify K5 relay coil is good?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 59
**Question:** What is the maximum peak discharge current of the battery?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 60
**Question:** What is the coolant type specification?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 61
**Question:** Which CAN ID carries CoolantTemp and at what scale?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 62
**Question:** What is the pinout for C35 phase U?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 63
**Question:** How to safely discharge DC link capacitors?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 64
**Question:** What are the MCU IGBT module ratings?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 65
**Question:** Compare the function of VCU and MCU on the CAN bus.

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 66
**Question:** What does error P0A00 mean and how to diagnose?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 67
**Question:** Where is the cabin fuse panel located?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 68
**Question:** What is the battery usable SOC window?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 69
**Question:** How often should HV gloves be retested?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 70
**Question:** What is the cooling pump nominal flow rate?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 71
**Question:** Which connector pins carry resolver signals?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 72
**Question:** What is the insulation class of the traction motor?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 73
**Question:** How to verify 12V supply at the MCU?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 74
**Question:** What is the MCU DC link capacitance?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
## Query 75
**Question:** What tools are needed for HV isolation testing?

**Expected Documents:**
- ServiceManual_v2.pdf
- EngineeringDatabase_v2.xlsx

**Expected Excel Rows:** Related rows in EngineeringDatabase_v2.xlsx

**Expected Schematic:** HV_Power_Distribution_Schematic_v2.png

**Expected Entities:** Varied identifiers from the dataset

**Reasoning Chain:** Multi-hop retrieval across PDF sections, Excel sheets, and schematic labels.

**Expected Summary:** Answer found by cross-referencing Service Manual sections with Engineering Database entries and schematic labels.

---
