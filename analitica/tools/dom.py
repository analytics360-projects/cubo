import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(locale="es-MX")
    pg.goto("http://localhost:8088/login/"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
    print(pg.evaluate("""() => { const out=[]; const walk=(el,d)=>{ if(d>14) return; const c=(el.className&&el.className.baseVal===undefined?el.className:'').toString().slice(0,90);
      out.push('  '.repeat(d)+el.tagName.toLowerCase()+(el.id?'#'+el.id:'')+(c?' .'+c.split(' ').join('.'):'')+(el.children.length==0&&el.textContent.trim()?' «'+el.textContent.trim().slice(0,50)+'»':''));
      for(const ch of el.children) walk(ch,d+1)}; walk(document.querySelector('#app')||document.body,0); return out.join('\\n')}"""))
    b.close()
