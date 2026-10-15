# Village Uthan asset handoff

All 39 requested asset names now have files. This is a complete **first-pass asset set**, not a production-approved art pack.

## Art direction

Approved environment reference: `concepts/uthan_concept_main.png` (option A). The original concept boards are inaccurate and decorative only. Never derive gameplay geometry from them. The overhead view conceals the playing area with a mat. Both UI images leave simple bare mud for the developer's correct board overlay.

The full brief and subsequent corrections are in `art_bible.txt`. Raster artwork was made with the built-in image_gen tool. Available exact prompts are in `production/` and beside the concept files. Models were generated locally using `production/build_models.py`.

## Delivered files

- `concepts/`: selected master, all three original alternatives, player view, overhead view, Dadu front/side sheet.
- `textures/`: eight requested material images and one supporting neutral stone material.
- `panoramas/`: matching afternoon, sunset and night images.
- `models/`: 22 binary glTF files for items 15–36.
- `ui/`: square thumbnail and widescreen loading art.
- `previews/`: renders read from the exported GLBs and a model contact sheet.
- `manifest.json` and `index.html`: file inventory and browsable asset index.
- `production/`: generation source, prompts and validation results.

## Verified technical properties

All 22 GLBs were read back successfully. Positions, normals, UVs and indices were checked for valid values. All models are below their triangle budgets, use metres and glTF Y-up coordinates, have bottom-centred local origins, and contain their referenced texture images. Individual props use one mesh node with material primitives. `guti_pebble_variations` has six named mesh nodes; `prop_pots` has three. These sets intentionally share their local origin, so isolate or reposition the individual nodes after import rather than displaying them overlaid.

The mat's total footprint is 1.2 × 0.9 m. The house is 6 × 4 × 3.5 m. The banyan is 15 m wide and 12 m tall, with 46,218 triangles. The clothesline poles are approximately 3 m apart; its total envelope includes the poles' thickness. Detailed dimensions and budgets are in `production/model_validation.json`.

The eight requested material images are 1254 × 1254 PNGs. The panoramas are 1774 × 887 PNGs (2:1). These are the native resolutions returned by image generation; they have not been upscaled. Image dimensions and edge measurements are recorded in `production/image_checks.json`.

## Work still required before production approval

1. **Texture seams:** generated textures were requested as tileable, but opposite-edge comparisons show mismatches, especially in woven patterns and corrugated tin. They are not certified seamless. Their base colour also contains some apparent relief shading. Do not treat these as fully calibrated shadow-free PBR maps.
2. **Panorama wrapping:** the three images preserve a consistent landscape and 2:1 ratio, but horizontal edge mismatches remain. Full-sphere projection and pole continuity have not been validated in an engine. They are panorama candidates, not verified seamless skyboxes or HDR lighting maps.
3. **Model realism:** these are usable procedural low-poly first passes with embedded base-colour textures and material factors. They do not yet match the photorealistic concept fidelity. Organic shapes, foliage, wear, UV packing and material detail need further art polish. They have no rigging, animation, LODs, collision meshes, normal maps or baked AO.
4. **Mobile performance:** full-resolution PNGs are embedded separately in the GLBs. Deduplicate materials and apply the target engine's texture compression and import settings before profiling. Structural triangle-budget checks are not a runtime performance certification.
5. **Preview limits:** software previews are a diagnostic view of actual exported geometry. They omit transparent glass and do not simulate full metallic/specular shading. Inspect final rendering in the target engine.

## Rebuilding

Run `production/build_models.py` using Python with numpy installed, then `production/inspect_assets.py` using numpy and Pillow. The scripts preserve raster source artwork, regenerate the GLBs, render preview images and write reports. `production/package_assets.py` rebuilds the manifest, HTML index and ZIP.
