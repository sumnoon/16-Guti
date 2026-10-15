# Village Uthan asset handoff

All 39 requested assets have files. The five open technical items from the first-pass handoff (texture seams, panorama wrapping, model engine features, mobile size, in-engine check) have been worked through by the pipeline in `production/`. What is still open is art fidelity, listed at the end.

## Art direction

Approved environment reference: `concepts/uthan_concept_main.png` (option A). The concept boards are inaccurate and decorative only. Never derive gameplay geometry from them. The overhead view hides the playing area under a mat. Both UI images leave plain bare mud for the developer's correct board overlay.

The full brief and later corrections are in `art_bible.txt`. Raster artwork was made with an image generation tool; the exact prompts are in `production/` and beside the concept files. Only the selected option A of the main concept is in this folder; options B and C were not kept.

## Delivered files

- `concepts/`: selected master, player view, overhead view, Dadu front/side sheet.
- `textures/`: eight requested materials plus the supporting `support_stone`, each 1024 × 1024 and seamless, with a matching `*_normal.png` (tangent space, OpenGL / glTF convention, +Y up).
- `panoramas/`: afternoon, sunset and night, 2048 × 1024 equirectangular, wrapping left to right.
- `models/`: 22 GLBs for items 15–36 (LOD0).
  - `models/lod/`: 28 lower-detail GLBs (`_lod1`, `_lod2`) for the 15 props where a reduction is meaningful.
  - `models/collision/`: one collider GLB per asset; the same shapes as primitives are in `production/collision.json`.
- `ui/`: square thumbnail and widescreen loading art.
- `previews/`: renders of the exported GLBs and a contact sheet.
- `viewer.html`: three.js viewer for every model, LOD, collider, animation, panorama and texture tiling (serve the folder over HTTP, e.g. `python -m http.server`).
- `manifest.json` and `index.html`: file inventory and browsable asset index.
- `production/`: generation source, original generated images (`production/source/`), scripts and reports.

## What was done on the open items

**1. Texture seams.** `production/process_images.py` makes each texture tile on both axes: it searches overlap widths to line up repeating weaves and corrugation, joins the edges along a minimum-difference seam, and first spreads any broad colour mismatch across the tile. Broad baked lighting gradients are divided out of the base colour. Results are in `production/image_processing.json`. The wrap error now sits at about the level of ordinary neighbouring pixels in each texture. The highest is the bamboo fence's horizontal wrap: it lands on a strip edge, and 45 interior columns of that texture have larger jumps. Tiling was checked by eye at full resolution and as a 3 × 3 repeat in three.js.

**2. Panorama wrapping.** Left/right edges are colour-matched and joined along a minimum-difference seam: the wrap error fell from 9.9–13.7 to 2.4–4.5, close to the 2.3–3.5 between ordinary neighbouring pixels. The top and bottom pole rows are blended to a single colour, so there is no pinching at zenith or nadir. Each image was resampled from 1774 × 887 to 2048 × 1024 (a 1.15× upscale, so no new detail). All three were viewed as the background and image-based lighting in three.js.

**3. Model engine features** (`production/build_models.py`):
- **Normal maps:** every textured material has a normal map and exported tangents. Each map is scaled to a target average tilt (`NORMAL_TILT` in `production/process_images.py`): the smooth ground mud is kept subtle so the game's carved board stays readable, while rough soil, straw and bark are stronger.
- **Baked AO:** per-vertex sky visibility in `COLOR_0`, which multiplies base colour. The ground is treated as occluding. Game pieces have none.
- **LODs:** generated from the same procedural source with fewer segments and sparser scatter. Scattered straw and leaves get larger as they thin out, so silhouettes hold. For example, the banyan goes 46,218 → 23,454 → 12,474 triangles.
- **Colliders:** boxes and cylinders, authored per asset in glTF space. Tree colliders cover the trunk, not the canopy; the clothesline has its poles only.
- **Rigging and animation:** `prop_chicken` has six joints (hips, neck, head, tail, two legs), rigid-skinned, with `idle`, `peck` and `walk` clips. No other prop needs a skeleton; foliage and cloth sway is better done with a wind shader in the engine.

**4. Mobile size.** Embedded textures are sized to the object: 256 px for game pieces, 512 px up to 1.5 m, 1024 px above that, and halved per LOD. They are stored as JPEG, normal maps at quality 94. Index buffers are 16-bit where possible. LOD0 total fell from 109 MB to 21 MB, even with normal maps added. Engines recompress textures on import (ASTC / ETC2 / BC), so set those import settings per platform. No device profiling has been done.

**5. Engine check.** All 72 GLBs (LOD0, LODs, colliders) pass the Khronos glTF Validator with 0 errors and 0 warnings (`production/gltf_validator_report.json`). Every model and LOD, plus its colliders, also loaded in three.js r160 with no console errors. Shadows, image-based lighting, normal maps, AO and the chicken clips were checked visually there. The game (`../game`, three.js r169) uses these files through `../tools/prepare_assets.py` and was play-tested with them: props, guti, the animated chickens and all three times of day.

## Verified technical properties

All GLBs use metres, glTF Y-up, bottom-centred local origins and embedded textures. Every model is under its triangle budget. Multi-object sets share a local origin: `guti_pebble_variations` has six named nodes and `prop_pots` three, so separate or reposition them after import rather than displaying them overlaid. Their colliders are named `<object>_col_<n>` and share the same origin.

The mat is 1.2 × 0.9 m. The house is 6 × 4 × 3.5 m. The banyan is 15 m wide and 12 m tall. The clothesline poles are about 3 m apart. Detailed dimensions, budgets, LOD and collider counts are in `production/model_validation.json`.

## Still open (art, not pipeline)

- **Model fidelity:** the models are procedural low-poly shapes and do not match the photorealistic concepts. Organic forms, foliage cards, wear, UV packing (planar and cylindrical UVs, no atlas) and per-asset unique texturing need an artist in a modelling tool. The pipeline outputs are a working, engine-ready baseline to replace asset by asset.
- **Textures:** normal maps are derived from image brightness, not real height, so dark stains read as dents. Light baked into the generated photos at small scale (cracks, weave shadows) is still in the base colour; only broad gradients were removed. There are no roughness or metallic maps; materials use constant factors. Large-scale repetition shows on very big surfaces.
- **Panoramas:** these are LDR images, not HDR light probes, and 2048 px is modest for a full-screen sky on tablets.
- **Chicken rig:** rigid weights (no blending at the neck), so extreme poses will crease.

## Rebuilding

Requires Python with numpy and Pillow. Run the commands from this `art/` folder, then run `../tools/prepare_assets.py` to update the game.

```bash
python production/process_images.py
python production/build_models.py
python production/inspect_assets.py
python production/package_assets.py
```

These four steps in order: textures and panoramas from `production/source/`, then GLBs, LODs and colliders, then readback, previews and image checks, then manifest and index. Add `--zip` to the last command to also write an archive in the project root (zips are git-ignored). The validator report was produced with the npm package `gltf-validator` (2.0.0-dev.3.10).
