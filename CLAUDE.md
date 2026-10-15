# Notes for development

Technical context for anyone (or any AI assistant) continuing this project.

## Running and checking
- Serve `game/` over HTTP (`game/start-game.bat`, or `python -m http.server 8080` inside `game/`). `file://` will not load the models.
- three.js r169 is vendored in `game/vendor/three/` (core + only the addons used: GLTFLoader, OrbitControls, SkeletonUtils, BufferGeometryUtils) and mapped in the `page.html` import map. Fonts are in `game/vendor/fonts/`. Nothing loads from the internet, which the Android app and offline play rely on. A new addon import needs its file (and its own imports) copied in.
- Installable web app: `game/manifest.webmanifest`, icons from `tools/make_icons.py`, and `game/sw.js` (stale-while-revalidate cache). `main.js` registers the service worker only on https, not on localhost and not inside the Android app. Bump `CACHE` in `sw.js` if cached files ever need a hard reset.
- Android: Capacitor 8.5.2 wraps the game (`docs/ANDROID.md`). `npm run android:sync` = `tools/build_web.py` (game/ -> www/, runtime files only) + `cap sync`. Native code is only `MainActivity.java`: `setDecorFitsSystemWindows(false)` (without it Android 14 and older leave a dark band at the cutout), hidden system bars, keep screen on. `www/` and `android/app/src/main/assets/public/` are generated.
- Phone performance: Battery saver renders at pixel ratio 1 (measured 48 vs 35 fps at 1.5 on a Mali-G76); shadows made no measurable difference there. The fence ring is drawn as one `InstancedMesh` per side (`instanced()` in `world.js`). To profile on a phone: install the debug APK, `adb forward tcp:9333 localabstract:webview_devtools_remote_<pid>` and drive the page over the DevTools protocol (or `chrome://inspect`). Count `requestAnimationFrame` calls in the page; `dumpsys gfxinfo` under-reports WebView frames. Measure after warm-up, since the first seconds after launch are slower.
- `page.html` is the page body only. `index.html` is generated from it by `game/build_index.py`. Edit `page.html`.
- The same `page.html` + `js/` + `assets/` is published as a Claude artifact. Artifacts only serve common web types, which is why models ship as `assets/models/*.json` (base64 GLB) and are decoded in `loadModel()` in `main.js`.
- Debug hook: `window.__game` exposes `newGame(mode)`, `tap(pointIndex)`, `setView('seat'|'top')`, `loadPosition([[x, z, player], ...], turn)`, `world`, `pieces`, `R` (rules), `camera`, `controls`.
- `tools/screenshot.py` drives the game headlessly. Software rendering is slow, so animations and CSS fades take much longer than on a GPU.

## Coordinates and board
- Units are metres. y is up. The board centre is the world origin.
- Player 1 (human vs AI, cream / clay guti) sits at +z, facing -z. Player 2 (Dadu, slate / tamarind) sits at -z.
- Board points use grid coordinates x ∈ [-2, 2], z ∈ [-4, 4]. `POINTS[i] = {x, z}`. `pointAt(x, z)` gives the index.
  - Grid rows z ∈ [-2, 2], all x. Triangle rows: z = ±3 → x ∈ {-1, 0, 1}; z = ±4 → x ∈ {-2, 0, 2}.
  - Diagonals pass through points where x + z is even and continue into the triangles' sides.
- World position = grid × `SPACING` (0.085 m). Guti models are 2.5 cm and drawn at 1.6× scale.
- `LINES` are ordered point sequences. Adjacent = consecutive on a line. A jump = three consecutive points on one line.

## Rules engine (`js/rules.js`)
- State: `{ board: Int8Array(37), turn, chain, quiet, ply, options }`. `chain >= 0` means that piece is mid-capture-chain and must (or may) keep jumping.
- `legalActions(s)` returns `{from, to, over?}` or `{end: true}` (end an optional chain). `applyAction(s, a)` is pure and returns a new state.
- `outcome(s)` returns `{winner: 0 | 1 | 2, reason}` or null. `generateTurns(s)` expands whole turns (chains included) for the AI.
- Options: `forcedCapture` (default false), `drawPlies` (60 quiet plies = draw).

## AI (`js/ai.js`)
- Negamax with alpha-beta over whole turns, iterative deepening with a time budget, capture quiescence, Zobrist-keyed transposition table.
- Levels: easy (depth 1 + noise + occasional blunder), medium (depth 3, 0.7 s), hard (up to depth 9, 1.6 s).
- Evaluation: material ×100, centre control, mobility, pieces that can be captured right now.

## Environment (`js/world.js`)
- Sky: a sphere with a shader that cross-fades two equirectangular panoramas. `uYaw` rotates the panorama so its sun matches `SUN_DIR` (sun left-front of player 1).
- Ground: one 80 m plane. `onBeforeCompile` adds macro variation, a rough-soil blend away from the centre and under the banyan, an alpha fade at 22–36 m into the panorama, and the board grooves. The grooves come from a canvas height map (`makeBoardHeight`) applied to colour and normals.
- Time of day presets are in `TIMES` (sun colour, intensity, elevation, hemisphere light, fog, exposure, lantern, dust, fireflies).
- Prop placement is in `placeProps()`. The house is at x ≈ 8.6, the banyan at (-7.8, -5.8), the fence ring at x ∈ [-14, 13], z ∈ [-11.5, 9].
- Shadows: one directional light, ±10 m frustum, 4096 px (High) or 2048 px (Battery saver), plus soft contact shadows under the guti.

## Asset pipeline
- Two stages. Never edit `game/assets/` by hand.
  1. `art/` is source art plus its own pipeline (run from `art/`, see `art/README.md`): `production/process_images.py` (seamless textures + calibrated normal maps, wrapped panoramas, from `production/source/`), `production/build_models.py` (GLBs with normal maps, tangents, baked AO in `COLOR_0`, LODs in `models/lod/`, colliders in `models/collision/`), `production/inspect_assets.py`, `production/package_assets.py`.
  2. `tools/prepare_assets.py`: `art/` -> `game/assets/`.
- `build_models.py` with no arguments regenerates every file in `art/models/`. After a model has been replaced by hand, pass asset names to rebuild only the others.
- Models: textures resized to 512 px (1024 px for banyan, house, haystack), normal maps half that, WebP q82, deduplicated, then quantized (KHR_mesh_quantization). Output goes to `game/assets/models-glb/` and is wrapped into `game/assets/models/*.json`.
- Quantized nodes carry their dequantization scale/offset as the node transform. Never overwrite the transform of a cloned model node: wrap it in a `THREE.Group` and place the group (`put()` in `world.js`, `makeMesh()` in `pieces.js`).
- `guti_pebble_variations` holds six named nodes (`dark_variation_1..3`, `cream_variation_1..3`) and `prop_pots` holds three (`aluminium_handi`, `brass_lota`, `clay_rice_pot`), all sharing one origin. They are picked by node name.
- `prop_chicken` is skinned (joints hips, neck, head, tail, leg_L, leg_R; clips `idle`, `walk`, `peck`). Clone it with `SkeletonUtils.clone`, never `clone(true)`. `main.js` copies `gltf.animations` onto the scene; `makeChickens()` gives each bird an `AnimationMixer`.
- Normal maps are scaled to a target mean tilt (`NORMAL_TILT` in `process_images.py`). The ground mud is deliberately subtle (0.09) so the carved board grooves stay readable.
- `tools/package.json` pins every `@gltf-transform/*` package to the same version. A mismatched `functions` package pulls in a second `core` and every CLI command fails with "Cannot read properties of null (reading 'getRoot')".

## Testing in a browser
- A hidden or background tab pauses `requestAnimationFrame`, which stops the game loop (camera moves and taps appear to do nothing). For headless checks, replace `window.requestAnimationFrame` with a `setTimeout` shim before the game boots.
- ES modules and assets are cached hard. After changing `js/` or `assets/`, hard refresh (Ctrl+Shift+R), or a stale `world.js` may run against new models.

## Known issues / ideas
- The banyan's aerial roots cast long stripe shadows. A better tree model or a shadow-proxy mesh would fix it. `art/models/lod/` has lighter banyan LODs (23k / 12k triangles) if the Battery saver setting needs them; the game does not use LODs or colliders yet.
- The menu-background camera orbit sometimes passes through the hanging roots.
- No tutorial, Bangla UI, online play or second environment yet. See `docs/GAME_PLAN.md`.
