# Shaastra Micro Mouse Maze: rules and constraints brief

Researched 2026-10-19. Tags: **[CONFIRMED: source]** = stated by a cited source for that event; **[REF-STD: source]** = stated by a standard micromouse rulebook (APEC / UK), not by Shaastra; **[ASSUMED]** = no source found.

## Headline findings

1. **No official Shaastra Micro Mouse rulebook is publicly reachable.** shaastra.org, cac.shaastra.org and the Unstop fest listing render only via JavaScript or behind cookies, and searches returned no rulebook PDF. Every Shaastra-specific rule below is therefore unconfirmed.
2. **The event's existence is confirmed only for 2019 and 2020.** A team repo says "We participated in the Micro Mouse Maze competition in 2019 and 2020", goal "reach the center in the shortest possible time" ([VIEKASH2001/Shaastra-IITM-Micro-Mouse-Maze](https://github.com/VIEKASH2001/Shaastra-IITM-Micro-Mouse-Maze)). IIT Madras's Shaastra 2026 press release lists Robo GP, rover challenges and robot wars but **not micromouse** ([IITM press release](https://www.iitm.ac.in/happenings/press-releases-and-coverages/iit-madras-annual-technical-festival-shaastra-2026-be-held)). Risk: the event may not run in 2027, or may run under different rules. **Action: contact Shaastra events team to confirm the event is on and get the rulebook.**
3. **Event date is not announced.** Shaastra 2024 and 2025 ran 3–7 Jan, 2026 ran 2–6 Jan [CONFIRMED: [IITM 2025 release](https://www.iitm.ac.in/happenings/press-releases-and-coverages/iit-madras-annual-tech-festival-shastra-be-held-3-7-jan), [IITM 2026 release](https://www.iitm.ac.in/happenings/press-releases-and-coverages/iit-madras-annual-technical-festival-shaastra-2026-be-held), [Wikipedia](https://en.wikipedia.org/wiki/Shaastra)]. Shaastra 2027 is therefore likely about **2–7 Jan 2027 [ASSUMED]**, which puts the two-week design freeze around **19 Dec 2026 [ASSUMED]**, about 9 weeks from today.

## Constraint table

| Item | Project value | Status | Best source found |
|---|---|---|---|
| Maze grid | 16 x 16 | [REF-STD] | APEC I.1, UK rules |
| Cell size | 18 cm | [REF-STD] | APEC I.1 |
| Wall height / thickness | 5 cm / 1.2 cm | [REF-STD] | APEC I.1 |
| Passage width | 16.8 cm | [REF-STD] | APEC I.1 |
| Colours | white sides, red tops, black non-gloss floor; walls IR-reflective, floor IR-absorbing | [REF-STD] | APEC I.2 |
| Dimensional tolerance | ±5% or 2 cm (lesser); floor steps ≤0.5 mm, gaps ≤1 mm | [REF-STD] | APEC I.5 |
| Robot footprint | 25 x 25 cm incl. any shape change, no height limit | [REF-STD] | APEC II.2, UK rules |
| Wall contact | must not jump, climb, scratch or damage walls | [REF-STD] | APEC II.4 |
| Start cell and orientation | a corner; walls on 3 sides, open side "north" | [REF-STD]; Shaastra [ASSUMED] | APEC I.3 |
| Goal size | central 2x2 (4 cells); Shaastra says "the center" | [REF-STD]; Shaastra partly [CONFIRMED: team repo] | APEC I.3 |
| Access window | **7 min** (current APEC; older APEC/IEEE R2 say 10 min) | [CONFIRMED: APEC current page] | https://apec-conf.org/attendees/special-events-social-activities/micromouse/ |
| Number of runs | **up to 5** (older APEC said 10) | [CONFIRMED: APEC current page] | APEC current page |
| Scoring | APEC: run time + maze time/30, −3 s if untouched; UK similar (+1/30 search time) | [REF-STD]; Shaastra [ASSUMED] | APEC III.1, UK rules |
| Is exploration timed | yes, via the maze-time handicap in APEC/UK | [REF-STD]; Shaastra [ASSUMED] | APEC III.1/III.4 |
| Timing method | IR beam at start-cell boundary and goal entrance, ~1 cm above floor; or manual | [REF-STD] | APEC III.4/III.5 |
| Touch / restart penalty | current APEC: 2 s touch penalty; IEEE R2: one-time 30 s for returning to start; older APEC/UK: lose bonus or 3 s + 10%; restart only for malfunction; part swaps require erasing maze memory | [REF-STD] | APEC III.3/III.9/III.10, UK rules |
| Between runs | must sit in start cell ≥1 s | [REF-STD] | APEC III.13 |
| Fan / suction | not prohibited by APEC or UK text (only combustion banned) | [REF-STD] silent; Shaastra [ASSUMED] | APEC II.1 |
| Battery limits | none beyond "self-contained, non-combustion" | [REF-STD]; Shaastra [ASSUMED] | APEC II.1 |
| Lifting point | UK requires a hook/loop for lifting from centre | [REF-STD] | UK rules |
| Event date | likely 2–7 Jan 2027 | [ASSUMED] from past editions | IITM releases |

## Design-changing unknowns to ask Shaastra
1. Is Micro Mouse Maze running at Shaastra 2027, and on which dates?
2. Maze spec: classic 18 cm 16x16, or a smaller/half-size or different-material maze? (Indian fests sometimes use plywood or flex mazes; this changes IR calibration and tire grip.)
3. Scoring formula: is exploration time penalised, and how many runs fit the window?
4. Touch and restart penalties, and whether reprogramming between runs is allowed.
5. Fan/suction allowed? (Earlier design in Micromouse-main used a suction fan.)
6. Start orientation and goal size.
7. Any battery chemistry or voltage limit.

## Techfest (IIT Bombay) for comparison
- Techfest has run an International Micromouse Competition (e.g. 3–5 Jan 2020, INR 175,000 prize pool) with rules in a separate "Problem Statement" document that was not retrievable [CONFIRMED event existed: [Micromouse Online](https://micromouseonline.com/2019/08/25/micromouse-in-mumbai/)]. Techfest 2026 is reported for 16–18 Dec 2026 by a third-party blog only [ASSUMED: [iitianvibes](https://iitianvibes.com/blog/techfest-2026-iit-bombay-30th-edition-complete-guide/)]; if it runs a micromouse event, it is a useful rehearsal two weeks before Shaastra, but it falls inside the freeze window.
- Techfest rule specifics (maze size, timing, fans): **not found [ASSUMED same as classic]**.

## Decision: governing rulebook
**Owner decision (2026-10-19): every model in this project is designed, tested and run to the APEC/IEEE classic rulebook.** The [REF-STD] values above are the project's design rules and are treated as [CONFIRMED: APEC rulebook]. If Shaastra publishes different rules, the differences get flagged to the owner rather than adopted silently. Keep the robot well under the 16.8 cm passage (about 10 cm wide), keep any fan optional and removable, and plan for exploration time costing score (maze time/30). Where APEC and IEEE differ, the stricter value governs (7 min, 5 runs), matching the Phase 1 brief and the `design-rulebook` memory entry.

## Sources
- APEC Micromouse Contest Rules: https://www.thierry-lequeu.fr/data/APEC/APEC_MicroMouse_Contest_Rules.html
- UK / Micromouse Online rules: https://micromouseonline.com/micromouse-book/rules/
- Shaastra team repo (2019/2020): https://github.com/VIEKASH2001/Shaastra-IITM-Micro-Mouse-Maze
- IITM Shaastra 2026 press release: https://www.iitm.ac.in/happenings/press-releases-and-coverages/iit-madras-annual-technical-festival-shaastra-2026-be-held
- IITM Shaastra 2025 press release: https://www.iitm.ac.in/happenings/press-releases-and-coverages/iit-madras-annual-tech-festival-shastra-be-held-3-7-jan
- Wikipedia, Shaastra: https://en.wikipedia.org/wiki/Shaastra
- Techfest micromouse 2020: https://micromouseonline.com/2019/08/25/micromouse-in-mumbai/
