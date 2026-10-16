# Old Dhaka Rooftop Night — asset handoff

The 43 requested asset names have files: 20 PNGs and 23 GLBs. The approved master is option C, saved as `concepts/rooftop_concept_main.png`. The original user brief is preserved in `rooftop_art_bible.txt`.

Open `rooftop_index.html` to browse the files. For the interactive GLB viewer, serve the project root with `python -m http.server 8766 --bind 127.0.0.1`, then open `http://127.0.0.1:8766/art/rooftop_index.html`. The viewer uses the game's existing local Three.js library and does not require a CDN. Asset creation does not install this environment into the game.

## Delivered

- `concepts/`: main reference, seated player view, overhead layout, rooftop rival front/side sheet. The top-down concept is an elevated layout illustration rather than an engineering orthographic plan.
- `textures/rooftop_*`: nine requested textures. Six material surfaces are 1254 × 1254 and wrap in both directions. Facades are 1254 × 1254 and wrap horizontally only. The kite atlas is 1280 × 1280 with 16 designs on white. `rooftop_tex_facade_emissive.png` is an additional aligned emission mask.
- `panoramas/rooftop_*`: dusk and night LDR backgrounds, 2048 × 1024, horizontal wrapping and constant-colour pole rows. These are generated environment approximations, not surveyed spherical photographs or HDR lighting captures. Perspective and close foreground distortion remain possible when viewed on a sphere.
- `effects/`: three 2048 × 2048 sheets with exact 512 × 512 cells, black gutters and near-black noise removed. `rooftop_fx_playback.json` specifies frame order, origin, additive blending and suggested 12 fps. Fireworks have one four-frame clip per colour; fire breath and sparks have 16-frame clips. Generated frame shapes can still flicker; these are not fluid-simulation exports.
- `models/`: 23 static GLBs, all below their individual triangle budgets. Flower pots and kite flyers each contain three named objects, laid out side by side. All other GLBs contain one mesh object with material primitives. No rigs, background or ground planes.
- `ui/`: square thumbnail and exact 1664 × 936 (16:9) loading image. Loading art leaves bare cement for the real board.
- `previews/rooftop_model_contact_sheet.jpg`: geometry previews; the software preview does not reproduce glass transmission. Use the interactive viewer for the marble.
- `rooftop_manifest.json`: ordered 43-item inventory, dimensions, triangle budgets, file sizes and SHA-256 hashes.

## Validation and processing

All 23 GLBs were read back after export: finite geometry, valid indices, embedded texture references, expected object counts, metre scale and bottom-centred local mesh origins. Multi-object nodes have display translations; each individual mesh retains its own local bottom centre. Triangle counts range from 12 to 9,882. Exact per-object dimensions and counts are in `production/rooftop_model_validation.json`.

All 23 also loaded through the game's local Three.js GLTFLoader in the inspection viewer without a model-loading error. This is an asset-load check, not Android device profiling or a complete level play-test. No Khronos Validator run was performed for this new pack.

Generated images were made with the built-in image generation tool. The user then explicitly authorized scripted technical finishing. Original generated files are preserved under `production/rooftop_source/` for processed assets. Scripts quilt material seams, match boundary pixels, flatten broad material illumination, correct panorama wrapping/poles and repack sprite cells. Final opposite edge pixels match exactly along the specified repeat axes. Equal boundary pixels do not eliminate recognizable pattern repetition or all interior quilting transitions.

The final night facade is a lighting-only pixel transformation of the final day facade, so architecture and sampling coordinates match exactly. Three windows are lit and others remain dark. The original separately generated night variant is retained in the source folder. Both panoramas use the same wrap cut and remapping; the generated night source can still contain small lighting-related details that differ from dusk.

The source square images were 1254 × 1254 and panorama sources 1774 × 887. Larger effect sheets and panoramas are resampled for exact layout; upscaling adds no new source detail. GLB embedded textures are resized to 256–1024 pixels for asset size. Original materials use neutral normal maps where the shared exporter requires a normal slot. Supplemental materials use synthetic micro-normal and roughness maps; none are measured scans. The marble uses `KHR_materials_transmission` and `KHR_materials_ior`; bulbs use emissive materials.

## Art fidelity still needing work

Latest direction: human faces remain simple and stylized. No photographic face texture is embedded in the models or included in this package. A rejected face study is preserved outside the delivery in the workspace only. The latest surface pass adds dedicated weathered plastic, iron, wood, clay, paper and food materials, embedded roughness/metallic maps and subtle synthetic micro-normal maps. These maps are authored approximations, not measured scans. The chair has a rounded moulded seat, flared legs, curved back and arms. Updated counts are 1,164 triangles for the chair, 9,882 for the kite-flyer group and 2,890 for the fire breather; all remain below budget. Earlier counts below describe the preceding revision.

The second model pass adds shaped torsos, facial features, articulated static fingers, sandals, collars, cotton garments and a checked lungi. Marigolds have compound leaves and petal rings; tulsi has broad leaves and flower spikes. Moa has exposed puffed-rice kernels and naru has coconut flakes. The revised kite-flyer set uses 9,282/12,000 triangles, the fire breather 2,690/6,000, flower pots 4,974/6,000 and food plate 2,784/3,000. Static previews now convert linear material colours correctly for display. The prior delivery remains available separately as `Old_Dhaka_Rooftop_Night_v1.zip` in the workspace.

The raster concepts establish the requested photorealistic world. The 3D assets are procedural low-poly approximations and do **not** reach that photorealistic standard, particularly the characters, foliage and food. They are usable for placement and prototype rendering, but need sculpting, garment/anatomy refinement, improved UVs and authored surface detail for final close-up art. Buildings use simple modular geometry and facade images; their flat side walls and repeating facade bands will be visible at close range. A production art pass is still required; file and technical completion should not be read as photorealistic art approval.

The chalk boards in concept images are decorative only. Render gameplay lines with the developer's board geometry.

## Rebuild

Use Python with numpy and Pillow. Run from the repository root:

```text
python art/production/process_rooftop.py
python art/production/prepare_rooftop_cloth.py
python art/production/prepare_rooftop_surfaces.py
python art/production/build_rooftop.py
python art/production/inspect_rooftop.py
python art/production/package_rooftop.py
python art/production/finalize_rooftop.py
```

These scripts target rooftop files only. Shared mesh/export and inspection helpers are `build_models.py`, `process_images.py` and `inspect_assets.py`; the second model pass is implemented in `rooftop_refinements.py`. Existing wood/clay supporting textures and the new cotton/lungi textures are included. Image prompts are in `production/rooftop_image_prompts.json`, `production/support_rooftop_cotton_prompt.txt` and the main/player prompt files beside the concept images. Re-running image generation itself requires the built-in image tool; the rebuild scripts process the preserved source files.


