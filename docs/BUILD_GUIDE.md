# Build guide: continuing Sholo Guti with Claude Code

This guide takes the project from where it is now (a playable 3D Village Uthan in the browser) to a full game.
Every step comes with a prompt you can paste into Claude Code. Claude Code reads `CLAUDE.md` in the project root
automatically at the start of each session, so it already knows the coordinates, rules engine, shaders and asset pipeline.

---

## Part 1: Set up the PC

Install these once:

| Tool | Why | Get it |
|---|---|---|
| Git for Windows | Version control. It also lets Claude Code use Bash on Windows | https://git-scm.com/downloads/win |
| Python 3.10+ | Local web server and the asset pipeline. Tick "Add python.exe to PATH" | https://www.python.org/downloads/ |
| Node.js 18+ (LTS) | Model optimisation in `tools/` | https://nodejs.org/ |
| VS Code (optional) | Editing and diffs. Claude Code has a VS Code extension | https://code.visualstudio.com/ |
| Claude Code | The AI coding agent | See below |

**Install Claude Code** (Windows PowerShell):

```powershell
irm https://claude.ai/install.ps1 | iex
```

Open a new terminal and check it with `claude --version`. Alternatively, use the Claude desktop app's **Code** tab, which includes Claude Code.
Official docs: https://code.claude.com/docs/en/overview

---

## Part 2: Get the project

### If the project is already on GitHub

```powershell
git clone https://github.com/sumnoon/16-Guti.git
cd 16-Guti
claude
```

### If you only have the `16-Guti` folder (first time)

The download `16-Guti-project.zip` contains everything except the full-resolution source art, which is already on your PC.

1. Unzip it, for example to `Desktop\ST\16 Guti\16-Guti`.
2. Copy **everything inside** `Desktop\ST\16 Guti\assets` into `16-Guti\art`, so you get `art\models`, `art\textures`, `art\concepts` and so on.
3. Open a terminal in `16-Guti`, start Claude Code with `claude`, then paste:

```
This folder is my Sholo Guti game project. Initialise a git repository on branch main,
commit everything with a clear message, add https://github.com/sumnoon/16-Guti.git as origin
and push. If the remote already has commits (like a starter README), merge them in
with --allow-unrelated-histories and keep my README.md. Check that no file is over 100 MB first.
```

Git will ask you to sign in to GitHub the first time (a browser window opens).

---

## Part 3: The daily loop

1. Start the game server in one terminal: `game\start-game.bat`, then keep http://localhost:8080 open.
2. Start Claude Code in a second terminal in the project root: `claude`.
3. Ask for **one** change at a time. Refresh the browser (Ctrl+Shift+R) to see it.
4. When it works, ask Claude Code to commit: `commit this with a clear message and push`.

Habits that keep the project healthy:

- For bigger features, ask for a plan first: start with "Plan this before writing code: …", or use plan mode (Shift+Tab in Claude Code).
- Ask Claude Code to run `node tools/test_rules.mjs 1` after any change to `rules.js` or `ai.js`.
- If something looks wrong, take a screenshot and drag it into the Claude Code terminal, or describe exactly what you see.
- Keep `CLAUDE.md` up to date. After a big change, say: `update CLAUDE.md with anything a future session needs to know`.
- Never hand-edit `game/assets/`. Change `art/`, then run the pipeline (Part 5).

---

## Part 4: Milestones, in order

Each milestone is a few sessions of work. Paste the prompt, review what Claude Code proposes, then play-test.

### M1. Put it online (GitHub Pages)

```
Set up GitHub Pages so the game in the game/ folder is playable at a public URL.
Use a GitHub Actions workflow that deploys game/ as the site root. Explain any settings
I need to change on github.com.
```

Then test the URL on your phone.

### M2. Polish Village Uthan

Work through these one at a time:

```
The banyan's hanging aerial roots cast long stripe shadows across the courtyard.
Make the roots not cast shadows while the trunk and canopy still do. If the model is one mesh,
split it by material or by height, or add a simple invisible shadow-proxy mesh. Show me before and after.
```

```
Make the chickens feel alive: head-bob while walking, occasional pecking with the head only,
short hops, a soft cluck sound now and then, and running from a captured piece's landing point.
```

```
Let the time of day advance slowly during a match (afternoon to sunset over about 15 minutes,
then night), with a setting to turn it off. Keep the manual time button.
```

```
Add a subtle depth-of-field effect in seat view (background softly blurred, board sharp),
only on the High graphics setting, and make sure it stays above 50 fps on a mid-range laptop.
```

**Replacing a model** (for example a better banyan from Sketchfab, Poly Haven or an image-to-3D tool):
put the new `.glb` in `art/models/` with the same name, in metres, origin at bottom centre, then:

```
I replaced art/models/prop_banyan_tree.glb. Run the asset pipeline, check the new model's
size and orientation in the scene, and fix its placement in world.js if needed.
```

### M3. Tutorial with Dadu

```
Build an interactive tutorial taught by Dadu in the courtyard. Use window.__game.loadPosition
to set up small positions. Lessons: 1) moving one step along a line, 2) capturing by jumping,
3) chain captures, 4) how the triangles connect to the grid, 5) winning by blockade.
Dadu speaks through a speech bubble with his portrait (assets/ui/dadu.jpg). Each lesson waits for
the correct move and gently corrects a wrong one. Add a "Learn with Dadu" button to the menu,
and offer it automatically on the first visit.
```

### M4. Bangla interface

```
Add a language switch (English / বাংলা) to the menu. Move every UI string into a strings file
with both languages, use Bangla numerals in Bangla mode, and remember the choice in localStorage.
Use the Hind Siliguri font for Bangla text. List any strings you were unsure how to translate.
```

Have a native speaker check the translations.

### M5. Game feel and replay value

```
Add a match summary on the win screen: total turns, longest chain, captures by each side,
and a "watch the best chain again" replay that re-animates that turn with the cinematic camera.
```

```
Add daily puzzles: a set of positions where the player must win or capture N guti in M moves.
Store puzzles as JSON in game/puzzles/. Pick today's puzzle from the date. Add 10 starter puzzles,
and verify each one has a solution using the rules engine.
```

```
Add sound design: a soft ambient music loop with a dotara or flute feel that changes for
afternoon, sunset and night, plus a tension layer when either player has 4 or fewer guti.
Keep it generated with WebAudio or use small royalty-free files, and list their licences.
```

### M6. Second environment: Monsoon Ghat

First make art with ChatGPT using the Monsoon Ghat row in `docs/ASSET_PROMPTS.md`. Save it into
`art/ghat/` with the same naming pattern (for example `ghat_tex_ground_brick.png`, `ghat_pano_day.png`, `prop_nouka.glb`).

Then:

```
Refactor the environment code so each environment is its own module (environments/uthan.js,
environments/ghat.js) sharing the board, sky, lighting and particle helpers from world.js.
Add an environment picker to the menu with the level thumbnails. Don't change how Uthan looks.
```

```
Build the Monsoon Ghat environment from the art in art/ghat/: brick steps leading down to the
river, the board carved into a wet brick landing, boats drifting on animated water, rain
particles with splashes on the bricks, puddle reflections, and thunder with a lightning flash
on chain captures. Extend tools/prepare_assets.py to process art/ghat/.
```

Repeat the same two steps for each remaining environment: Tea Garden, Sundarbans, Mughal Courtyard, Cox's Bazar, Old Dhaka Rooftop.

### M7. Campaign

```
Add a campaign: travel across the environments, beating a local champion in each (different
names, portraits and AI styles, such as aggressive, defensive or trap-setting). Unlock the next
environment and a new guti set after each win. Save progress in localStorage.
```

### M8. Online play

This needs a server. Ask for a plan first:

```
Plan online multiplayer for this game. Compare a small Node.js WebSocket server
(hosted on Render or Fly.io), Firebase Realtime Database, and peer-to-peer WebRTC with a
signalling server. I want friends to play with an invite link first and random matchmaking later.
The server must validate moves with rules.js. Recommend one and list the steps.
```

### M9. Phone app

The fastest route to Android is to wrap the web game:

```
Make the game installable as a Progressive Web App (manifest, icons from assets/ui, offline
caching of all assets with a service worker). Then set up Capacitor to build an Android app
from game/, and write the exact steps to produce a signed APK/AAB for the Play Store.
```

For the highest-quality mobile version later, port to **Unity (URP)**:

```
Plan a Unity URP port. Translate rules.js and ai.js to C# with matching unit tests, import the
models from game/assets/models-glb with glTFast, and recreate the board-carving ground shader in
Shader Graph. List the work in order.
```

---

## Part 5: Making and adding art

1. Generate with ChatGPT using `docs/ASSET_PROMPTS.md`. Follow its rule: **never trust the board drawn in AI images.**
2. Save files into `art/` (or `art/<environment>/`) with the standard names.
3. Run the pipeline once per PC:
   ```powershell
   cd tools
   npm install
   pip install -r requirements.txt
   ```
   and after every art change:
   ```powershell
   python prepare_assets.py
   ```
   If you changed raw generated images, first rebuild them in `art/` (`python production/process_images.py`, run inside `art/`).
   `art/production/build_models.py` regenerates **every** procedural model in `art/models/`. If you replaced a model by hand,
   rebuild only the others by name (for example `python production/build_models.py prop_house prop_fence`) so yours is not overwritten.
4. Ask Claude Code to place and check new props in the scene.

Where to find better 3D models: Poly Haven (free, CC0), Fab / Quixel Megascans, Sketchfab (check the licence), and image-to-3D tools such as Meshy, Tripo, Hunyuan3D and Rodin (clean up in Blender).
For the most authentic guti, scan real pebbles, tamarind seeds or cowries with Polycam or RealityScan.

**Licences:** if you plan to sell the game, keep a list of every asset's source and licence in `art/LICENSES.md`.

---

## Part 6: Check before every commit

- [ ] Game loads with no errors in the browser console (F12).
- [ ] A full move, a capture and a chain capture work.
- [ ] Undo works, and the win screen appears (use `__game.loadPosition` in the console to reach it fast).
- [ ] Afternoon, sunset and night all look right.
- [ ] Phone layout works (Chrome DevTools device mode, or a real phone over GitHub Pages).
- [ ] `node tools/test_rules.mjs 1` passes if rules or AI changed.

You can hand this list to Claude Code: `run the pre-commit checklist in docs/BUILD_GUIDE.md`.
It can use `tools/screenshot.py` for the visual checks.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Black screen, or "Some game files did not load" | Use the server (`start-game.bat`), not a double-clicked `index.html`. Check the internet connection (three.js loads from a CDN) |
| `python` not found | Reinstall Python with "Add to PATH" ticked, or use `py` instead of `python` |
| `claude` not found after installing | Open a new terminal. If that doesn't help, see https://code.claude.com/docs/en/troubleshoot-install |
| Changes don't show | Hard refresh with Ctrl+Shift+R. After editing `page.html`, run `python game/build_index.py` |
| Game is slow on a phone | Menu → More settings → Graphics → Battery saver |
| Push rejected (file too large) | Files over 100 MB can't go to GitHub. Keep big source files out, or use Git LFS |
