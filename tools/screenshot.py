"""Headless screenshots of the running game (for quick visual checks).

Start a server first (game/start-game.bat or `python -m http.server 8080` inside game/), then:
  python screenshot.py out.png "wait 2000;; __game.newGame('ai');; wait 300;; __game.setView('seat');; wait 2500"
Steps are separated by ';;'. 'wait N' sleeps, 'shot file.png' saves a frame, anything else is evaluated as JavaScript.
window.__game exposes newGame, tap(pointIndex), setView('seat'|'top'), loadPosition([[x,z,player],...]), world, pieces, R (rules).
Env vars: URL (default http://localhost:8080/index.html), W, H (viewport size).
Software rendering is slow, so animations and CSS fades take far longer than on a real GPU.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

URL = os.environ.get('URL', 'http://localhost:8080/index.html')
W, H = int(os.environ.get('W', '1280')), int(os.environ.get('H', '760'))

async def main(out, script):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': W, 'height': H})
        logs = []
        pg.on('console', lambda m: logs.append(f'{m.type}: {m.text}'))
        pg.on('pageerror', lambda e: logs.append(f'PAGEERROR: {e}'))
        await pg.goto(URL)
        await pg.wait_for_function('window.__game', timeout=180000)
        for step in filter(None, (s.strip() for s in script.split(';;'))):
            if step.startswith('wait '): await pg.wait_for_timeout(int(step[5:]))
            elif step.startswith('shot '): await pg.screenshot(path=step[5:])
            else:
                r = await pg.evaluate(step)
                if r is not None: print('eval:', r)
        await pg.screenshot(path=out)
        print('\n'.join(logs[-30:]))
        await b.close()

if __name__ == '__main__':
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'wait 2000'))
