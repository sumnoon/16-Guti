# Game plan

The design plan this project follows. The status column shows what the current build has.

## Core game

| Topic | Decision | Status |
|---|---|---|
| Board | 37 points: 5×5 grid with Alquerque diagonals, plus a 6-point triangle at each end whose tip touches the middle of the grid edge | Done (`game/js/rules.js`) |
| Setup | 16 guti each: own triangle plus the two nearest grid rows. Middle row empty | Done |
| Move | One step along a line to an adjacent empty point | Done |
| Capture | Jump an adjacent enemy guti to the empty point straight behind it, along a line | Done |
| Chains | After a capture the same guti may keep jumping | Done |
| Win | Capture all enemy guti, or leave the opponent with no legal move | Done |
| House rules | Captures optional or forced (setting). Draw after 60 moves without a capture | Done |
| Architecture | Rules are pure code with no graphics, shared by the UI, the AI and the tests | Done |

## Platform

The current build is a **Three.js browser game**, which is the fastest way to prototype and share.
The plan for the shipped game is **Unity (URP), Android first**, with quality tiers. The rules engine (`rules.js`)
and AI (`ai.js`) are small and easy to port to C#. The optimized models in `game/assets/models-glb/` import into Unity or Godot.

## Environments (one at a time, each to full quality)

1. **Village Uthan.** Mud courtyard, banyan tree, tin-roof house, chickens, chula smoke. **Built.**
2. Monsoon Ghat. Brick river steps in rain, boats, thunder on big captures.
3. Sylhet Tea Garden. Misty hills, fog lifting as the match goes on.
4. Sundarbans. Mangrove deck at dusk, fireflies, distant deer.
5. Mughal Courtyard. Marble inlaid board, fountain, Lalbagh-style arches.
6. Cox's Bazar Sunset. Board drawn in sand, waves, golden hour.
7. **Old Dhaka Rooftop.** Shakrain kites, string lights, skyline, fire-breathers, fireworks, sky lanterns. **Built second** (dusk and night; opponent Rana). Models are procedural first passes, see `art/rooftop_README.md`.

## Responsive world

| Idea | Status |
|---|---|
| Time of day: afternoon, sunset, night with smooth transitions | Done (player-controlled) |
| Captures cause reactions: chickens scatter, leaves fall | Done |
| Long chain captures get a slow-motion camera push-in | Done |
| Tension when a player is down to a few guti | Partial (wind rises) |
| Time of day advancing during long matches | To do |
| Weather (rain for the Ghat) | To do |
| Quality tiers by device, with override | Done (High / Battery saver) |

## Pieces

River pebbles (3 shapes per colour), clay shard vs tamarind seed, and glass marbles vs bottle caps (rooftop) are in. Planned: carved wood, terracotta,
brass, cowries, marble and onyx. Ideally scan real pebbles and seeds with a phone (Polycam, RealityScan).

## Making it enjoyable

| Feature | Status |
|---|---|
| Vs AI, three strengths (Dadu) | Done |
| Local two-player with view rotation | Done |
| Move highlights and capture arcs, undo | Done |
| Tutorial with Dadu teaching in the courtyard | To do |
| Daily puzzles ("win in 3 captures") | To do |
| Campaign across the 7 environments | To do |
| Online play | To do |
| Bangla UI and voice lines | To do (title is Bangla already) |
| Replays highlighting the best chain | To do |

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1 Prototype | Rules engine, 3D board, local play | Done |
| 2 AI and UX | Minimax AI, highlights, undo | Done (tutorial still to do) |
| 3 First environment | Village Uthan, 2 piece sets, sound | First pass done. Models need art polish |
| 4 Responsiveness | Time cycle, capture reactions, quality tiers | Mostly done |
| 5 Content | More environments and piece sets | In progress (Old Dhaka Rooftop, marbles & caps done) |
| 6 Online and polish | Matchmaking, campaign, optimization | Later |
| 7 Launch | Android first, then iOS, PC and web | Later |

Build one environment to full quality before starting the next. It becomes the quality benchmark and the trailer.
