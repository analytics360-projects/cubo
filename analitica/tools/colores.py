"""Vuelca serie -> color de cada gráfica ECharts de un tablero. Uso: python colores.py /superset/dashboard/<slug>/"""
import os, sys, json
from playwright.sync_api import sync_playwright
JS = """() => [...document.querySelectorAll('[_echarts_instance_]')].map(el => {
  const card = el.closest('.dashboard-component-chart-holder');
  const title = card ? (card.querySelector('.header-title, [data-test=editable-title]')?.innerText || '') : '';
  let f = el[Object.keys(el).find(k => k.startsWith('__reactFiber'))], opt = null;
  for (let i = 0; f && i < 40 && !opt; i++, f = f.return) {
    const p = f.memoizedProps || {}; opt = p.echartOptions || p.option || null;
  }
  const series = opt ? (Array.isArray(opt.series) ? opt.series : [opt.series]).map(s => ({
      name: s.name, id: s.id, stack: s.stack, color: s.itemStyle && s.itemStyle.color, n: (s.data||[]).length,
      data: s.type === 'pie' ? (s.data||[]).map(d => [d.name, d.itemStyle && d.itemStyle.color]) : undefined })) : null;
  return {title, series};
})"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(ignore_https_errors=True, viewport={"width": 1600, "height": 2400}).new_page()
    pg.goto("https://nginx/login/"); pg.fill("#username", os.environ["ADMIN_USERNAME"]); pg.fill("#password", os.environ["ADMIN_PASSWORD"])
    pg.keyboard.press("Enter"); pg.wait_for_load_state("networkidle")
    pg.goto("https://nginx" + sys.argv[1]); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(12000)
    for c in pg.evaluate(JS):
        print(json.dumps(c, ensure_ascii=False))
    if len(sys.argv) > 2:
        pg.set_viewport_size({"width": 1400, "height": 2400}); pg.wait_for_timeout(4000)
        print("-- tras redibujar")
        for c in pg.evaluate(JS):
            print(json.dumps(c, ensure_ascii=False))
    b.close()
