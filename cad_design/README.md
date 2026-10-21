# CAD design (parametric, CadQuery)

The whole mouse is generated from one parameter file. Change a number, rebuild, and every part, check, export and drawing updates together.

| Path | What |
|---|---|
| `source/params.py` | Every dimension, tagged confirmed `[C]`, assumed `[A]` or design choice `[D]`. Edit here |
| `source/micromouse.py` | Part geometry |
| `source/build.py` | Runs the 22 design checks, exports STEP/STL/DXF, renders views into `../assets/`, writes `build_report.md` |
| `source/render.py` | Headless renderer for the images |
| `step/micromouse_revA_assembly.step` | **Full assembly: open this in Fusion 360** |
| `step/*.step` | One STEP per part; `plate_outline.dxf` for the KiCad board outline |
| `stl/` | Printable parts: frame, hubs, impeller, sensor block, battery holder, bumper (plate STL is for fit checks) |
| `build_report.md` | Generated: check results, mass and CG table, fan, grip, IR geometry, diagonal clearance, crash loads, clearances |

## Open in Fusion 360

File > Open > Open from my computer > `step/micromouse_revA_assembly.step`. It loads as one assembly of named, coloured components. Fusion does not run the Python source: edit the bodies in Fusion directly, or change `params.py`, rebuild and re-import.

## Rebuild

```bash
python3 -m pip install cadquery matplotlib shapely
cd cad_design/source && python3 build.py   # exit code 0 only when every check passes
```

## Parts

| Part | Source | Qty |
|---|---|---|
| frame (skirt, bearing walls, motor tubes, encoder ribs, fan housing, skid domes) | printed PETG | 1 |
| plate | 1.0 mm FR4 PCB | 1 |
| sensor_block | printed black PETG | 1 |
| bumper | printed TPU 95A | 1 |
| battery_holder | printed PETG | 1 |
| impeller | printed PETG / resin | 1 |
| hub | printed PETG | 2 |
| 8520 coreless motor, 8T 0.5M pinion, 36T 0.5M spur | bought | 2 each |
| 3 mm stainless axle (D-flat, M2 tapped end), MR63ZZ bearing | bought, machined | 2, 4 |
| spacer + 0.3 mm shim + e-clip (axle_hw), M2 x 4 hub screw + washer | bought | 2 sets, 2 |
| 4 x 2 mm diametric magnet, AS5047P board | bought | 2 each |
| 0716 coreless fan motor | bought | 1 |
| SFH4550 emitter, TEFT4300 receiver | bought | 4 each |
| 2S 240 mAh LiPo | bought | 1 |
| silicone/PU tyre | bought | 2 |
| M2 heat-set insert, M2 screws | bought | 4, 8 |
