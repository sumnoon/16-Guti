# Asset prompts

How the Village Uthan art was made, and the prompts to reuse for the next environments.
The exact prompts used for each Uthan image are saved next to the files in `art/concepts/` and `art/production/`,
and the full art direction is in `art/art_bible.txt`.

## How to use

1. Open a new ChatGPT chat and paste the master prompt for the environment.
2. Pick one of the concept options. It becomes the master reference.
3. Type **next** for each following asset, or **redo** with notes.
4. If the style drifts, re-upload the master concept image and say "match this reference".
5. Save files into `art/` with the given names, then run `tools/prepare_assets.py`.

Rules that matter:
- **Never copy the Sholo Guti board from generated images.** Image models draw it wrong. The game draws the real board in code.
- Textures: ask for "top-down, flat, even lighting, no shadows, seamless". Seams still appear; `prepare_assets.py` fixes the ground textures.
- Panoramas: "360-degree equirectangular, 2:1, eye level, seamless left and right edges".
- Models: real-world metres, origin at bottom centre, triangle budget, `.glb`.

## Master prompt: Village Uthan (used)

```
You are the lead artist for a 3D mobile board game called Sholo Guti (the traditional Bangladeshi 16-piece game). We are creating ALL assets for the first environment, "Village Uthan." Everything must look like it belongs to ONE consistent world.

=== ART BIBLE (apply to every asset) ===
Setting: a rural Bangladeshi village courtyard (uthan) in late afternoon. A Sholo Guti board is scratched into smooth packed mud in the center. A huge old banyan tree with hanging aerial roots shades one side. Behind: a mud-walled house with a corrugated tin roof and small veranda, a bamboo fence, a haystack, a clay stove with thin smoke, chickens, a clothesline with a gamcha. Beyond the fence: green rice paddies and coconut palms.
Style: photorealistic, grounded, nostalgic and peaceful. No fantasy, no cartoon, no text or logos.
Lighting (for concept and UI art only): warm late-afternoon sun from the left, soft long shadows, golden haze.
Color palette: mud ochre #B98A5E, clay terracotta #A9542F, straw gold #D9B25F, bamboo pale #CDB27A, leaf green #4F7A3A, tin grey #8C8F8A, shadow brown #4A3426, sky warm #F2D3A2.
Materials: hand-made, worn, dusty, slightly uneven. Nothing looks new or factory-perfect.
Scale: real-world sizes in meters.

=== TECHNICAL RULES ===
Textures: seamless tileable, square, top-down or flat front view, EVEN lighting, NO shadows, NO perspective, highest resolution you can give.
Panoramas: 360-degree equirectangular, 2:1 aspect ratio, eye level, empty foreground at the bottom, seamless left and right edges.
3D models: .glb format (if not possible, .obj or .3mf). Real-world scale in meters, origin at bottom center, textures embedded, single object, no background, no ground plane, game-ready low poly within the triangle budget given.
File names: use the names given below.

=== WORKFLOW ===
- Create ONE asset per reply, in the order listed.
- Start with item 1 and give me 3 concept options. After I choose one, treat it as the master reference for everything that follows.
- After each asset, write one line saying what the next asset is, then wait for me to type "next".
- If I type "redo", fix the current asset based on my notes.
- Never change the art bible unless I ask.

=== ASSET LIST ===
CONCEPT ART
1. uthan_concept_main – wide cinematic view of the full courtyard with the board in the foreground (3 options).
2. uthan_concept_player – low view from a player sitting on a jute mat beside the board, pebble pieces on it, background softly blurred.
3. uthan_concept_topdown – overhead layout of the courtyard showing where every element sits.

TEXTURES
4. uthan_tex_ground_mud – smooth swept packed mud, hairline cracks, tiny pebbles, faint straw.
5. uthan_tex_ground_rough – rougher soil for the courtyard edges, dry leaves, sparse grass.
6. uthan_tex_wall_mud – hand-plastered mud wall with smear marks and small cracks.
7. uthan_tex_roof_tin – weathered corrugated tin with rust patches.
8. uthan_tex_fence_bamboo – woven split-bamboo panel (bera).
9. uthan_tex_mat_jute – woven jute floor mat (pati).
10. uthan_tex_bark_banyan – grey-brown banyan bark with deep grooves and moss.
11. uthan_tex_straw – densely packed dried rice straw.

PANORAMAS
12. uthan_pano_afternoon – rice paddies, palms, distant tin-roof houses, a pond, warm afternoon sky.
13. uthan_pano_sunset – same scene, orange-pink sunset, silhouetted palms, haze.
14. uthan_pano_night – same scene, moonlit blue sky, stars, distant lantern lights, fireflies.

GAME PIECES (guti)
15. guti_pebble_dark – smooth river pebble, 2.5 cm wide, 1.2 cm tall, flat enough to sit stably, dark slate grey. Under 3,000 triangles.
16. guti_pebble_light – same, light cream stone.
17. guti_pebble_variations – 3 extra shape variations of each color, in one file as separate objects.
18. guti_clay_shard – rounded terracotta pot shard, 2.5 cm wide, 0.8 cm thick. Under 3,000 triangles.
19. guti_tamarind_seed – glossy dark brown tamarind seed scaled to 2.5 cm. Under 2,000 triangles.

3D PROPS
20. prop_kolshi – clay water pot, 35 cm tall. Under 8,000 triangles.
21. prop_chula – U-shaped clay stove, 50 cm wide, 25 cm tall, soot inside. Under 6,000.
22. prop_piri – low wooden stool, 40 x 25 cm, 10 cm tall. Under 3,000.
23. prop_pati – jute mat lying flat, 120 x 90 cm, curled corners. Under 2,000.
24. prop_lantern – rusty red hurricane kerosene lantern, 30 cm. Under 5,000.
25. prop_haystack – straw dome around a bamboo pole, 2.5 m tall. Under 8,000.
26. prop_fence – bamboo fence segment, 2 m long, 1.5 m tall, repeatable end to end. Under 4,000.
27. prop_house – mud house with tin roof, veranda, door, shuttered window, 6 x 4 x 3.5 m. Under 20,000.
28. prop_chouki – wooden bed-platform, 1.8 x 1.2 m, 45 cm tall. Under 5,000.
29. prop_clothesline – rope between two bamboo poles 3 m apart, gamcha and lungi hanging. Under 4,000.
30. prop_kula – flat round winnowing tray, 50 cm. Under 4,000.
31. prop_dala – round bamboo basket, 45 cm wide. Under 4,000.
32. prop_pots – aluminium handi, brass lota, clay rice pot, separate objects in one file. Under 5,000.
33. prop_jharu – coconut-midrib broom, 70 cm. Under 2,000.
34. prop_chicken – brown-black deshi chicken, standing, 35 cm. Under 6,000.
35. prop_banana_tree – 3 m tall, some torn and dry leaves. Under 10,000.
36. prop_banyan_tree – large old banyan, twisted trunk, hanging aerial roots, 12 m tall, 15 m wide. Under 50,000.

CHARACTER AND UI
37. char_dadu_concept – elderly village grandfather, white beard, round glasses, white panjabi, checked lungi, gamcha on shoulder, front and side view, plain background.
38. ui_uthan_thumbnail – square level-select image, no text.
39. ui_uthan_loading – 16:9 image of a child and grandfather playing Sholo Guti under the banyan tree at golden hour, space at top for a title, no text.

Begin with item 1 now.
```

Correction added after item 2, keep it for every environment:

```
Note for all remaining assets: the Sholo Guti board in the concept images is inaccurate and is only decorative. Do not copy its layout. In any image where the board is clearly visible, show it from far away or partly covered, or keep it out of frame. For the thumbnail and loading images, leave the board area simple, because the developer will composite the correct board on top.
```

## Next environments: what to swap into the master prompt

Replace the Setting, Lighting, palette and asset list. Keep the technical rules and workflow.

| Environment | Concept | Ground texture | Panorama | Props |
|---|---|---|---|---|
| Monsoon Ghat | Old brick steps down to a wide river in monsoon rain, wet surfaces, wooden boats, dark clouds, blue-grey light | Wet weathered red brick with moss in the gaps | Wide river, far bank with trees, heavy clouds | Nouka boat, banana-leaf umbrella, brass pot, rope coil, mooring post |
| Sylhet Tea Garden | Wooden platform on a hilltop tea estate, early morning, rows of tea bushes, mist in the valleys | Weathered planks with dew | Rolling tea hills, mist layers, pale sky | Tea-picker's basket, tin cup and kettle, bench, shade tree |
| Sundarbans | Forest-watch deck at dusk, mangrove roots in muddy water, fireflies | Dark wet timber deck with rope binding | Dense mangroves, tidal channels, dusk sky | Kerosene lamp, golpata shelter, small boat, distant deer |
| Mughal Courtyard | Lalbagh-inspired courtyard, white marble floor with inlay, red sandstone arches, fountain, midday sun | Polished white marble with grey veins | Red sandstone walls, domes, garden, blue sky | Brass hookah, silk cushions, stone planter, ornate lamp |
| Cox's Bazar Sunset | Long beach at sunset, wet sand reflecting the sky, gentle waves, fishing boats | Fine damp golden sand with tiny shells | Bay of Bengal horizon, setting sun, colourful boats | Beach umbrella, coconuts, fishing net, small boat, shells |
| Old Dhaka Rooftop | Rooftop at night during Shakrain, kites, string lights, water tanks, dense old buildings | Rough cement roof with paint stains | Old Dhaka skyline at night, lit windows, mosque domes, kites | Kites and natai spool, plastic chairs, water tank, potted plants, string lights |
