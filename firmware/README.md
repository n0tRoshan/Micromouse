# Firmware (Phase 5, not started)

Target: STM32F4 on the main PCB. This file records the plan the hardware was designed around, so each sensor and motor channel in the CAD has a place in the code.

## State machine

`BOOT/CALIBRATE → WAIT_START → EXPLORE → COMPUTE_PATH → SPEED_RUN → IDLE`, plus `FAULT`: a safe stop on sensor failure, brownout or watchdog trip.

## Modules

| Module | Hardware it drives or reads |
|---|---|
| IR driver: pulsed emitters, on/off differencing for ambient rejection, per-sensor lookup table | 4 x SFH4550 / TEFT4300 |
| Wall detection with hysteresis | IR driver |
| Odometry | 2 x AS5047P on the wheel axles |
| Heading hold (gyro Z) and wall-centering PID | IMU, IR |
| Motion profiles: trapezoidal over multi-cell straights, separate turn parameters | 2 x 8520 via DRV8835 |
| Fan control: PWM set-point, soft start, off in FAULT | 0716 via low-side MOSFET |
| Maze solver: flood fill, then incremental re-flood, then time-weighted cost, then diagonals | |
| Run logger: per-cell, timestamped, over UART | |

The solver is simulated off-robot on many mazes before it runs on the mouse.

## Constraints from the CAD (Rev A.1)

| Item | Value | Source |
|---|---|---|
| Encoder | AS5047P ABI into TIM2 / TIM5 encoder mode, 4096 counts per wheel rev = 0.0184 mm per count; SPI2 for AGC and magnet diagnostics at boot | [build guide §1, §7](../documentation/build_guide.md) |
| Drive duty cap | `D_max = 1.5 A x R_measured / V_batt` until Phase 3 confirms the driver | build guide §1 |
| Fan duty cap | average fan voltage at or below the 0716's rating; fan off in FAULT and between runs | build guide §1 |
| Diagonals | V90 turn radius ≤ 75 mm; heading error on a diagonal > 5° is a fault condition | [build report](../cad_design/build_report.md), diagonal section |
