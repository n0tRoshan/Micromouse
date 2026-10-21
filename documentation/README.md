# Documentation

| Document | What it covers |
|---|---|
| [build_guide.md](build_guide.md) | **How to build Rev A.1**: performance numbers, diagonal fit, BOM, print settings, assembly, wiring, first power-up, first tests |
| [design_notes.md](design_notes.md) | Reference winners studied, the flaw each feature fixes, assumptions, print settings, assembly guide, Gate 4 status |
| [../cad_design/build_report.md](../cad_design/build_report.md) | Generated check results, mass/CG table, fan and grip numbers, IR geometry |
| [../research/phase1_research_brief.md](../research/phase1_research_brief.md) | Phase 1: top designs, IR vs ToF, MCU, 2WD vs 4WD, top student-build failures |
| [../research/rules_brief.md](../research/rules_brief.md) | Rules we design to (APEC/IEEE) and what is still unknown about Shaastra |

## What a micromouse has to do

A micromouse is a small autonomous robot that finds its way from a corner of a 16 x 16 maze of 18 cm cells to the 2 x 2 goal in the centre. It first explores (search runs), then races the best path it found (speed runs). Under APEC rules the score is the best run time plus total maze time / 30, inside a 7-minute window with up to 5 runs. Search time therefore counts, and a crashed run scores nothing.

## Rules we design to

APEC/IEEE classic rules, taking the stricter value where they differ. The full table and sources are in [rules_brief.md](../research/rules_brief.md).

| Item | Value |
|---|---|
| Maze | 16 x 16 cells of 18 cm; walls 5 cm high, 1.2 cm thick; passage 16.8 cm; white walls, red tops, black floor |
| Floor | steps ≤ 0.5 mm, gaps ≤ 1 mm |
| Robot | within 25 x 25 cm, no height limit, self-contained, must not damage walls |
| Window | 7 min, up to 5 runs |
| Score | run time + maze time / 30, best run counts |
| Fan | allowed |

## Architecture (Rev A)

| Subsystem | Choice | Why (source) |
|---|---|---|
| Drive | 2WD, 8520 coreless motors, 8T:36T 0.5M spur, 24 mm wheels on bearings | Top-3 APEC 2026 mice use coreless + gears; 2WD avoids 4WD turn skid |
| Grip | Suction fan on the centre line, 0716 coreless, 20 mm centrifugal impeller, skirt pan | All APEC 2026 top 3 run fans |
| Wall sensing | 4 pulsed IR pairs (SFH4550 / TEFT4300) in a shroud, ±0° and ±50° | All top 3 use IR; ToF is too slow above ~0.5 m/s |
| Odometry | AS5047P magnetic encoders on the wheel axles | KOGUMA-CHAN; reads the wheel, not the motor, so gear backlash drops out |
| Heading | LSM6DSR-class IMU at the turn centre | PIGGY-ONE, KOGUMA-CHAN |
| MCU | STM32F4 (F405/F446) | All top 3 |
| Power | 2S 240 mAh LiPo | Decimus-5A |
| Chassis | One printed frame + 1.0 mm PCB on top | KOGUMA-CHAN's rigid frame; one part keeps both axles coaxial |
