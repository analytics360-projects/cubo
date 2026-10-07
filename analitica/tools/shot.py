"""Capturas de la UI: python shot.py <ruta> <archivo.png> [dark] [anchoxalto]"""
import os, sys
from playwright.sync_api import sync_playwright

path, out = sys.argv[1], sys.argv[2]
dark = len(sys.argv) > 3 and sys.argv[3] == "dark"
w, h = (int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else "1440x900").split("x"))
base = os.environ.get("BASE", "https://nginx" + os.environ.get("SUPERSET_APP_ROOT", "").rstrip("/"))
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": w, "height": h}, color_scheme="dark" if dark else "light",
                        locale="es-MX", device_scale_factor=1, ignore_https_errors=True)
    pg = ctx.new_page()
    if path != "/login/":
        pg.goto(base + "/login/")
        pg.fill("input[name=username], #username", os.environ["ADMIN_USERNAME"])
        pg.fill("input[name=password], #password", os.environ["ADMIN_PASSWORD"])
        pg.keyboard.press("Enter")
        pg.wait_for_load_state("networkidle")
    pg.goto(base + path)
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(int(os.environ.get("WAIT_MS", "2500")))
    pg.screenshot(path=out, full_page=os.environ.get("FULL") == "1")
    b.close()
