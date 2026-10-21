# Rev A (initial build): design notes

Date: 2026-10-19, updated 2026-10-21 (Rev A.1) · Phase 4 (CAD) · Governing rules: APEC/IEEE classic micromouse, stricter value where they differ ([rules brief](../research/rules_brief.md))
Tags: **[C: source]** confirmed, **[A]** assumed, **[D]** design choice backed by the reasoning here.
Generated numbers (mass, CG, clearances, checks) live in [`cad_design/build_report.md`](../cad_design/build_report.md). Rerun `cad_design/source/build.py` after any parameter change.

Rev A copies its architecture from the APEC 2026 winners. Nothing is carried over from the earlier SRA-VJTI-style design (ESP32 devkit, ToF sensors, N20 motors, gear-coupled 4 wheels).

## 1. Reference designs studied

| Mouse (event) | Layout | What Rev A takes from it | Flaws its builder or the record reports |
|---|---|---|---|
| **Decimus-5A** (APEC 2026, 1st) [C: S4] | 4WD + fan, 76 x 97 mm, 115 g, Faulhaber 1717 coreless, 35:10 gears, 22 mm wheels, SFH4550/TEFT4300 x4, 2S 240 mAh | Coreless + spur drive, 4 shrouded IR pairs, 2S 240 mAh pack, ~76 mm width | "No crumple zones"; "faster runs require stronger parts" [C: S4] |
| **KOGUMA-CHAN.Mk3** (APEC 2026, 2nd) [C: S4] | 2WD + fan, 120 x 70 mm, 78 g, 24 mm wheels, AS5047P encoders in a bearing-holder unit, carbon frame | 2WD, 24 mm wheels, magnetic encoders on the wheel axle, one rigid frame instead of a PCB chassis | None reported |
| **PIGGY-ONE** (APEC 2026, 3rd) [C: S4] | 4WD + fan, 120 g, STM32F446, LSM6DSR | STM32 + LSM6DSR-class IMU | 66.6 s search run (costs score under the /30 rule) |
| **ZoroBot-A** (APEC 2026) [C: S4] | 8520 coreless, 8T:40T 0.5M gears, 2S 260 mAh | 8520 motor and 0.5M 8T pinion | None stated |
| **Biscuit 2** (APEC 2026) [C: S4] | 8520 coreless x3 (2 drive + fan), ~240 g downforce, AS5047P | Coreless fan motor; downforce ~3x mass is achievable at this size | None stated |
| **Theseus** (APEC 2026, did not run) [C: S4] | 4WD, 7 x 16 mm coreless fan motor | 0716 fan motor size | "Frequent, high-speed crashes" |
| **Decimus (2012 build)** [C: S15, S16] | Printed wheels and mounts | | Mounts "not really rigid enough"; uneven toe-in; hubs too small for bearings; wheels not trued; tyres may shed |
| **Decimus 2** [C: S17] | | | Diagonal sensors too far back: wall edge seen 124 mm into the cell, too late for a 1 g turn |
| **4WD mouse, micromouseonline** [C: S7] | 4WD | | All wheels skid in turns; 0.2 mm drive-train shift reverses drift; nose tipped at 9 m/s² braking |

## 2. Flaw-to-fix table

| # | Flaw seen | Rev A solution | Model | Verified by |
|---|---|---|---|---|
| F1 | 4WD turns skid all wheels unpredictably (S7) | **2WD** with the fan for grip, as on KOGUMA-CHAN | drive train | CG within 1 mm of the axle |
| F2 | Drive-train misalignment: 0.2 mm reverses drift; printed mounts flex (S7, S15) | **One-piece frame.** Both axle bores go through both walls in a single cut, so the wheels are coaxial by construction. Each axle runs in **two MR63 bearings** in a 5 mm wall | `frame`, `bearings_*` | Interference check; Phase 6A spin-down drift test |
| F3 | Hubs too small, tyres shedding, wheels not round (S15, S16) | Wheel turns with a steel axle on bearings (no plastic bore). Hub lips hold the tyre. Tyres are bought rings | `hub_*`, `axle_*`, `tire_*` | Runout check in 6A |
| F4 | Coreless motors are faster and lighter, but need a gear train | **8520 coreless + 8T:36T 0.5M spur (4.5:1)**, motors behind the axle so the centre line stays free for the fan. 36T rather than ZoroBot's 40T keeps the gear tips 2.5 mm off the floor | `motor_*`, `pinion_*`, `spur_*` | Gear floor-clearance check |
| F5 | Motor-shaft encoders read through gear backlash | **AS5047P magnetic encoders on the wheel axles** (KOGUMA-CHAN), with a magnet on each axle end and the chip 1 mm away on a frame rib | `magnet_*`, `encoder_*` | Phase 6A counts-per-rev test |
| F6 | Diagonal sensors too far back (S17) | Diagonal IR mouths 46.5 mm ahead of the axle at ±50°; front pair at the nose | `sensor_block` | `assets/sensor_in_cell.png` |
| F7 | IR crosstalk and calibration drift (brief §5) | Black printed shroud fixes angles and height, with a 1.4 mm septum per pair and 12 mm bores | `sensor_block` | Phase 6C |
| F8 | Beam spill onto the floor or red wall tops | Beam at z = 21.3 mm; every spot stays 9-34 mm up the 50 mm white face | `SENS_Z` | `assets/beam_vs_wall.png` |
| F9 | No crumple zone (S4) | TPU bumper band around the nose, below the beams | `bumper` | Phase 6J |
| F10 | CG far from the axle unloads the drive wheels; forward CG tipped a mouse at 9 m/s² (S7) | Battery behind the fan motor, sensor block ahead. CG +0.8 mm ahead of the axle, 16.2 mm high | layout | Build checks |
| F11 | Fan off-axis loads the skids instead of the wheels | **Fan on the centre line**, 7 mm ahead of the axle. The skirt (suction pan) is the frame floor, and its centroid sits 2.9 mm ahead of the axle | `frame`, `impeller`, `fan_motor` | Build check; `assets/section_fan.png` |
| F12 | Skirt dragging on 0.5 mm floor steps | Skirt 1.3 mm off the floor; worst pitch case still 0.66 mm. PTFE skid domes are moulded into the skirt | `SKIRT_*`, skids | Build check |
| F13 | Extra mounts and placeholders add mass and failure points | **11 part types**, each with a job: frame, plate, sensor block, bumper, battery holder, impeller, hubs, plus bought parts. No separate motor mounts, skid posts, fan brackets or adapter boards: the MCU, IMU and drivers are chips on the PCB | all | Mass 63.3 g ex battery |
| F14 | Oversized chassis hits walls (brief §5) | 96.5 x 74 mm, 47 mm per side in the passage; 60 mm swept radius turning in place | plate | Build check |
| F15 | Diagonal runs pass between post corners only 110.3 mm apart (owner question 2026-10-21) | **Rev A.1:** plate narrowed to 35.5 mm half-width so plate + bumper sit inside the tyres; overall width 77 → 74 mm. Sweep checks on a diagonal straight, 45° in/out and V90 turns with ±5 mm and ±5° error | `PLATE_HALF_W`, `DIAG_*` | Build checks; `assets/diagonal_clearance.png` |
| F16 | Axle end play and the spur rubbing the bearing outer race; magnet gap drifting with the axle (Rev A had a 2 mm float) | **Rev A.1:** inner spacer + e-clip and an outer 0.3 mm shim clamp both inner races, so the axle cannot float and the 1 mm magnet gap is fixed | `axle_hw_*` | Phase 6A end-play and AGC check |
| F17 | A glued wheel can only come off by breaking the encoder magnet joint (fails the Gate 4 swap test) | **Rev A.1:** hub drives through a D-flat and is held by one M2 screw into the axle end; the wheel comes off with a hex key, the encoder side is untouched | `hub_*`, `axle_*`, `hub_screw_*` | Gate 4 swap test |
| F18 | No route for motor and encoder wires: the motor tubes sit 0.2 mm under the PCB | **Rev A.1:** an 8 x 3 mm slot above each encoder board and a 3 x 10 mm slot at the tail for both motor leads; all wires stay inboard of the walls | `ENC_SLOT`, `MOTOR_SLOT` | Visual; assembly step 10 |
| F19 | Frame and axle never checked against crash and drop loads (Phase 4 item) | **Rev A.1:** frontal crash at 2 m/s puts 155 N mean through the bumper, 22x under the shear strength of the 4 frame screws; axle bends 1.1 µm at 10 g | build checks | Phase 6J |

## 3. Assumptions

| ID | Assumption | Effect if wrong | Resolve in |
|---|---|---|---|
| C1 | 8520 coreless drive motors, 8.5 x 20 mm, 5 g, 1 mm shaft ≥ 5.3 mm long [A] | Tube bore, pinion reach | Phase 3; measure on arrival (6A) |
| C2 | 0716 coreless fan motor, 7 x 16 mm, 2.5 g, ~0.6 A at 7.4 V [A] | Collar bore, current budget | Phase 3 |
| C3 | Fan makes 150 gf (1.9x weight) at working PWM [A]; needs ~390 Pa under the pan | Grip with fan | Scale test with the fan on (6A) |
| C4 | 2S 240 mAh pack is 18 x 44 x 11 mm, 15 g [A] | Holder size; CG via `BATT_CX` | Phase 3 |
| C5 | Tyre μ = 1.0 on the maze floor [A] | Grip limits scale with μ | Tilt test (6A) |
| C6 | Shroud limits each IR cone to ±12° [A] | Spot heights | 6C |
| C7 | FDM printer, 0.4 mm nozzle, PETG and TPU [A] | Print notes below | Phase 0 |
| C8 | Gear motor and fan need 3 motor channels: DRV8835 (2) + a low-side MOSFET (fan) [A] | Electronics BOM | Phase 3 |
| C9-C14 | 8520 stall current vs DRV8835 1.5 A, magnet field strength, bearing shield bore, diagonal heading error, IR range, average current | See [build_guide.md §10](build_guide.md#10-things-still-to-verify-assumptions-register-additions) | 6A-6I |

## 4. Manufacturing notes

Moved to [build_guide.md](build_guide.md) §4 (print settings) and §5 (axle preparation).

## 5. Assembly guide

Moved to [build_guide.md](build_guide.md) §6, with the wiring (§7), first power-up (§8) and the order of first tests (§9).

## 6. Gate 4 status

| Item | Status | Evidence |
|---|---|---|
| Interference check passes | **PASS** (CAD) | `build_report.md` |
| Footprint and passage clearance in CAD | **PASS** | 96.5 x 74 mm, 47 mm per side; diagonal corridor 18.2 mm per side (10.0 mm with errors) |
| Footprint on the physical prototype | **FAIL (not built yet)** | Needs a print |
| CG within target | **PASS** (CAD, assumed masses) | +0.6 mm, 16.1 mm high |
| First fit needs only minor trimming | **FAIL (not built yet)** | Print the frame first |
| Serviceability by swapping battery, wheel, sensor | **FAIL (not built yet)** | Designed for it (Rev A.1 removable hub); swap table in build_guide.md §6 needs the physical test |
| Parametric model, STEP/STL, drawings, exploded view, assembly guide | **PASS** | `cad_design/`, `assets/`, [build_guide.md](build_guide.md) |
| Drop and crash loads checked | **PASS** (calculation) | build report, crash and stiffness section |

## 7. Fan: modelled, but the first build runs without it

Update 2026-10-21: the owner decided the first mouse runs fan-free until real results exist. `params.FAN` switches the model; the fan-free variant (`cad_design/no_fan/`) raises the floor plate to 3.0 mm and moves the battery 2 mm forward. Original reasoning for designing the fan in from the start:

### Why the fan is designed in

The Phase 1 brief recommended proving reliability without a fan first. The owner chose to build it in from the start (2026-10-19): APEC/IEEE rules allow fans, and every APEC 2026 top-3 mouse used one. In testing, the speed stages run fan-off first, then repeat with the fan on, so each change is still one variable.

## 8. Rev B candidates

- Carbon or aluminium frame once the printed one is proven (KOGUMA-CHAN moved from PCB to carbon).
- Faulhaber 1717 drive motors if the budget allows (Decimus-5A).
- A 0.8 mm 4-layer PCB to save about 2 g.

## Sources

S4 APEC 2026 Micromouse Contest Report V2 https://apec-conf.org/wp-content/uploads/2026/05/APEC-2026-Micromouse-Contest-Report-V2.pdf ·
S7 https://micromouseonline.com/2013/02/24/four-wheel-micromouse-difficult-to-turn/ ·
S15 https://micromouseonline.com/2012/05/24/printed-wheels-complete-decimus-mechanicals/ ·
S16 https://micromouseonline.com/2014/05/25/travelling-bumpy-road-micromouse/ ·
S17 https://micromouseonline.com/2011/05/29/wall-sensor-alignment-error/ ·
S18 https://micromouseonline.com/2011/01/10/pointing-the-sensors/
