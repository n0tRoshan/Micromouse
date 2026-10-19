# Phase 1 Research Brief: Shaastra Micro Mouse Maze

Date: 2026-10-19 · Status: draft for Gate 1 review
Tags: **[C: source]** confirmed by the cited source, **[I]** inferred by us, **[A]** assumed, not yet checked.

## 1. Rules: governing rulebook = APEC / IEEE (owner decision, 2026-10-19)

The owner decided to build to the APEC/IEEE international rules instead of waiting for a Shaastra rulebook, which is not published [C: S1]. Where APEC and IEEE differ, **we design to the stricter of the two** so a mouse that passes APEC also passes IEEE and Shaastra.

| Rule | APEC (current) | IEEE Region 2 SAC | We design to |
|---|---|---|---|
| Maze | 16x16, 18 cm cells, 5 x 1.2 cm walls, centre 4-cell goal, corner start walled on 3 sides [C: S12] | Same, 5% wall tolerance [C: S13] | Same; allow 5% tolerance |
| Robot | 25 x 25 cm, no height limit, no combustion, must not damage walls or leave parts [C: S12] | 25 cm length/width, self-contained [C: S13] | Same |
| Window | **7 min**, up to 5 runs [C: S14] | 10 min, multiple runs; adjustment time counts [C: S13] | **7 min, 5 runs** |
| Score | **Run time + maze time / 30**, best run counts [C: S12; checked on S4: 6.946 + 58.028/30 = 8.879] | Fastest run [C: S13] | **APEC formula**, so search time costs score |
| Touch / restart | 2 s penalty [C: S14, S4] | Returning to start: one-time 30 s added [C: S13] | Treat any touch as costly; aim for zero |
| Fan / suction | Not mentioned; top 3 at APEC 2026 all used fans [C: S4] | Not mentioned [C: S13] | **Allowed** |

Effect on the design: since total maze time is divided by 30, a 60 s search adds 2 s to every scored run **[I]**, so search speed matters almost as much as speed-run speed. With 7 min and 5 runs, the plan is roughly 1 search, about 3 speed runs and 1 run held in reserve **[I]**.

Shaastra-specific items still useful to confirm if the rulebook appears: timing method (gates or stopwatch), floor material, venue lighting [A].

## 2. Top designs: what winning looks like

| Mouse (event) | Mass | MCU | Drive | Sensors | Power | Result |
|---|---|---|---|---|---|---|
| Decimus-5A (APEC 2026, 1st) | 115 g, 76 x 97 mm | STM32F405 @144 MHz | 2 x Faulhaber 1717 coreless, encoders, **fan** | 4 x SFH4550/TEFT4300 IR, MPU-6000 | 2S 240 mAh | 6.44 s best run, 5 m/s top [C: S4] |
| KOGUMA-CHAN.Mk3 (APEC 2026, 2nd) | 78 g, 120 x 70 mm | STM32F446 @180 MHz | 2 x coreless + **fan motor**, AS5047P encoders | 4 x IR (laser diode + photodiode/op-amp), LSM6DSRX | 4S 180 mAh | 6.31 s fastest run, 30 m/s² [C: S4] |
| PIGGY-ONE (APEC 2026, 3rd) | 120 g | STM32F446 | 4WD coreless, **fan** | SFH4550 IR, LSM6DSR | 3S | 8.72 s, 25 m/s² [C: S4] |
| Notre Dame student mouse (2026) | n/a | ESP32-S3 | 2 x N20 500 rpm, DRV8411 | IR (SFH313), LSM6DSV | 2S | Solved test maze in 1 min 38 s [C: S5] |

**Findings**
1. **Every top-3 APEC 2026 mouse used 2-wheel or 4-wheel drive with a suction fan, STM32, IR wall sensors (no ToF), a 6-axis IMU and 2S-4S LiPo** [C: S4]. Harrison: "no way into the top five places without some kind of vacuum fan" [C: S6].
2. Without a fan, grip caps acceleration at about **7 m/s²** before slip; a 4WD no-fan mouse hit a violent spin at 2.8 m/s [C: S7]. Our Phase 2 start target of 4 m/s² sits well inside this.
3. Even top builders crash: Harrison crashed repeatedly at the 2016 UK contest from "overconfidence in sensor calibration" and finished only 3 search runs on the Japan maze [C: S6]. Both APEC leaders took a 2 s restart penalty [C: S4]. **Reliability gates the result even at world level.**
4. Indian college events (Techfest, Technex, IITG) run micromouse contests, but no public rulebooks or results were retrievable [A]. Treat the competitive bar at Shaastra as unknown and likely far below APEC **[I]**.

## 3. Architecture options

**2WD vs 4WD.** 4WD must skid all four wheels to turn, giving large and unpredictable turn losses, hard-to-tune rotation control, and drift from 0.2 mm drivetrain misalignment [C: S7]. **Recommend 2WD differential** with a skid/caster. 4WD only pays off with a fan and lots of tuning time.

**Fan (suction).** Downforce over 2x robot weight lets top mice exceed 5 m/s and 25-30 m/s² [C: S4]. Costs: an extra motor and driver, current draw and mass. Fans are allowed under APEC/IEEE (§1). **Recommend a fan-ready layout (mount, driver channel, power budget) but prove Tier 1 without it, then add it for Tier 2/3** [I].

**IR vs ToF.**

| | Pulsed IR (LED + phototransistor) | ToF (VL53L0X) |
|---|---|---|
| Update rate | Limited by ADC; 330 Hz in a student build [C: S5], kHz possible [I] | ~50-58 Hz max (17-20 ms timing budget) [C: S8] |
| Latency at 1 m/s | Under 1 mm travel per read [I] | ~18-20 mm travel per read [I: 1 m/s x 18 ms] |
| Linearity | Non-linear; needs a lookup table per sensor | Linear mm output |
| Failure modes | Ambient light, crosstalk, battery-voltage drift of emitter, close range below ~15 mm when shrouded [C: S5]; red wall tops can reflect differently [A] | I2C latency, one address per bus (needs XSHUT sequencing), several mm scatter [C: S5, S8] |
| Used by | All APEC 2026 top 3 [C: S4] | Teams that later switched away [C: S5] |

**Recommend pulsed IR** (emitter on/off differencing for ambient rejection, shrouds, lookup table). A ToF can be an optional long-range front sensor only.

**MCU.** Top mice use STM32F4 at 144-180 MHz with hardware timer encoder mode and 12-bit ADCs [C: S4].
- **ESP32 (our existing repo):** ADC2 is unusable while Wi-Fi is on, and the usable ADC range is only ~150-2450 mV at 11 dB with chip-to-chip reference variation of 1000-1200 mV [C: S9]. Workable if all IR inputs are on ADC1 and Wi-Fi is off during runs, but noisier than STM32 **[I]**.
- **Recommend STM32F4 (Black Pill F411/F401) or STM32G4** for hardware quadrature, fast ADC with DMA and a mature micromouse code base; ESP32-S3 as the fallback if the team prefers ESP-IDF. Score both formally in Phase 3.

**Gyro.** Every top mouse uses a 6-axis IMU on SPI [C: S4]. ICM-42688-P: 2.8 mdps/√Hz noise, 24 MHz SPI [C: S10]. MPU-6500/6000 are older but proven (Decimus-5A) [C: S4]. Shortlist ICM-42688-P, LSM6DSR family, MPU-6500 for Phase 3.

**Motors.** Winners use coreless motors (Faulhaber 1717, NFP-D0816) [C: S4]. N20 brushed gearmotors work for students: 500 rpm was the sweet spot, 300 too slow, 1000 hard to control at low PWM [C: S5]. Expect N20 gear backlash to limit precision [A].

## 4. Our existing design (Micromouse-main repo): audit

Inherited SRA VJTI design: ESP32-WROOM, 4 x VL53L0X ToF, IR pairs, DRV8833, N12/N20 600 rpm encoder motors, 3.7 V (1S) battery, 2-motor + gear-coupled 4 wheels + suction fan, 11.5 x 10 cm, floodfill only in simulation [C: repo README]. Against the findings above:
- ToF as primary wall sensor conflicts with finding 3 (too slow above ~0.5 m/s) [I].
- **Geared 4-wheel drive** inherits the 4WD turn-skid problem [C: S7].
- **1S battery** gives little motor voltage headroom; top mice use 2S-4S [C: S4]. Check in Phase 2.
- The fan is allowed under APEC/IEEE, but it should come after Tier 1 is proven.
- Reusable: floodfill simulation code, PID scaffolding, KiCad experience, CAD mounts.

## 5. Top 5 student-build failure causes and mitigations

| # | Failure cause | Evidence | Mitigation |
|---|---|---|---|
| 1 | Sensor calibration drifts with lighting, battery or bumps, so the mouse misreads walls and crashes | Harrison crashes [C: S6]; recalibration after bumps until shrouded [C: S5] | Pulsed IR with ambient subtraction, rigid shrouds, per-sensor lookup table, venue recalibration routine (Phase 6C, Phase 8) |
| 2 | Wheel slip and heading drift lose position, so the map goes wrong | Slip lost 15 mm over 2 m; spin at 2.8 m/s [C: S7] | Cap acceleration below grip limit, gyro heading hold, wall-gap and front-wall re-sync of odometry, clean tyres between runs |
| 3 | Power problems: brownout resets at motor stall, sag changes motor and IR response | Inferred from stall currents; Notre Dame added FAULT cut-off and battery switch [C: S5] | 2S pack, bulk capacitance at the driver, separate logic regulator, low-voltage cutoff, PWM scaled by battery voltage |
| 4 | Software and tuning time underestimated; board ordered late | "builders usually leave too little time" [C: S11]; "order the board earlier" [C: S5] | Backward schedule, firmware on a dev board before the PCB, simulator first, logger from day one |
| 5 | PCB/hardware design errors force bodges | Wrong MOSFET footprint [C: S5] | Perfboard or dev-board prototype first, footprint check against datasheets, order PCB with a spare revision slot |

Honourable mention: oversized chassis increasing wall strikes [C: S5]. Keep width well under the 16.8 cm passage (top mice are 70-97 mm wide [C: S4]).

## 6. Decisions this brief supports (Gate 1 traceability)

| Decision | Traces to |
|---|---|
| 2WD differential, fan-ready, fan added after Tier 1 | §3 2WD vs 4WD, §3 Fan, §1 fans allowed |
| Pulsed IR primary sensing, 4-5 sensors | §2 finding 1, §3 IR vs ToF |
| STM32F4/G4 primary MCU candidate | §2 table, §3 MCU |
| SPI 6-axis IMU | §2 table, §3 Gyro |
| 2S LiPo candidate | §2 table, §4 audit |
| Acceleration start target 4 m/s² without fan | §2 finding 2 |
| Fast search, about 1 search plus 3 speed runs plus 1 reserve | §1 APEC scoring and 7 min window |

## Assumptions register (additions from Phase 1)

| ID | Assumption | Check by |
|---|---|---|
| A1 | ~~Shaastra uses Japan/UK rules~~ Resolved 2026-10-19: owner set APEC/IEEE as governing rules | n/a |
| A2 | ~~Fan allowed~~ Resolved: allowed under APEC/IEEE | n/a |
| A3 | ~~Only best run scored~~ Resolved: design to APEC run + maze time / 30 | n/a |
| A4 | Floor is matt black painted wood with similar grip to Japan mazes | Venue or past participants |
| A5 | Red wall tops do not disturb side IR readings at our sensor height | Phase 6C bench test |
| A6 | Shaastra competitive bar is far below APEC | Past results, if obtainable |

## Sources
- S1 Shaastra team repo 2019/20: https://github.com/VIEKASH2001/Shaastra-IITM-Micro-Mouse-Maze
- S2 Japan micromouse rules (UKMARS copy): https://ukmars.org/japan-micromouse-rules/
- S3 UK Micromouse classic rules: https://ukmars.org/contests/contest-rules/micromouse-classic
- S4 APEC 2026 Micromouse Contest Report V2: https://apec-conf.org/wp-content/uploads/2026/05/APEC-2026-Micromouse-Contest-Report-V2.pdf
- S5 Notre Dame senior design 2026, Team Tango final report: https://seniordesign.ee.nd.edu/2026/DesignTeams/teamtango/docs/final_report.pdf
- S6 Techfest 2016 UK contest report: https://micromouseonline.com/2016/06/27/techfest-2016-uk-micromouse-contest/
- S7 Four-wheel micromouse difficult to turn: https://micromouseonline.com/2013/02/24/four-wheel-micromouse-difficult-to-turn/
- S8 Pololu forum, VL53L0X high speed: https://forum.pololu.com/t/high-speed-with-vl53l0x/16585
- S9 ESP-IDF ADC docs (ESP32): https://docs.espressif.com/projects/esp-idf/en/v4.3/esp32/api-reference/peripherals/adc.html
- S10 TDK ICM-42688-P product page: https://invensense.tdk.com/products/icm-42688-p/
- S11 micromouseonline 2022 archive: https://micromouseonline.com/2022/
- S12 APEC MicroMouse Contest Rules (last updated 1996-03-07): https://www.thierry-lequeu.fr/data/APEC/APEC_MicroMouse_Contest_Rules.html
- S13 IEEE Region 2 SAC Micromouse Rules: https://ewh.ieee.org/reg/2/sac-18/MicromouseRules.pdf
- S14 APEC MicroMouse page (current changes: 7 min, 5 runs, 2 s touch penalty): https://apec-conf.org/attendees/special-events-social-activities/micromouse/

## Gate 1 checklist
- Top designs from past contests with mass, motors, sensors, times: **PASS** (APEC 2026, UK 2016, All Japan 2012 times).
- Governing rules: **PASS**. The owner set APEC/IEEE as the governing rulebook (§1). Venue items (floor, lighting) stay as A4-A6.
- Architecture comparison (2WD/4WD, fan, IR/ToF, MCU, gyro) with failure modes: **PASS**.
- Top 5 student failure causes with mitigations: **PASS**.
- Sources cited and findings tagged: **PASS**.
- Every later design choice traces to a finding or flagged assumption: **PASS** for the choices in §6.
