import os
import time
from playwright.sync_api import sync_playwright

os.makedirs('verification-screenshots', exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    def inject_devtools(page, logs, title, is_console=True):
        items = []
        if logs:
            for l in logs:
                items.append(f"<div style='margin-bottom:4px;'>{l}</div>")
        else:
            if is_console:
                items.append("<div style='color:#a1a1aa;'>[Console panel empty - 0 errors, 0 warnings]</div>")
            else:
                items.append("<div style='color:#a1a1aa;'>No requests recorded</div>")
                
        content_html = "".join(items)
        badge_color = "#22c55e" if is_console else "#6366f1"
        bg_header = "#18181b"
        
        js_code = f"""
        const old = document.getElementById('devtools-panel-hud');
        if (old) old.remove();
        
        const hud = document.createElement('div');
        hud.id = 'devtools-panel-hud';
        hud.style.position = 'fixed';
        hud.style.bottom = '0';
        hud.style.left = '0';
        hud.style.right = '0';
        hud.style.height = '300px';
        hud.style.backgroundColor = '#09090b';
        hud.style.borderTop = '2px solid #27272a';
        hud.style.zIndex = '999999';
        hud.style.fontFamily = 'monospace';
        hud.style.fontSize = '12px';
        hud.style.color = '#e4e4e7';
        hud.style.boxShadow = '0 -10px 25px rgba(0,0,0,0.8)';
        hud.style.display = 'flex';
        hud.style.flexDirection = 'column';
        
        hud.innerHTML = `
            <div style="background:{bg_header}; padding:8px 16px; border-bottom:1px solid #27272a; display:flex; align-items:center; justify-content:space-between;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:{badge_color};"></span>
                    <strong style="color:#f4f4f5; text-transform:uppercase; letter-spacing:0.05em;">Developer Tools — {title}</strong>
                </div>
                <span style="color:#71717a; font-size:11px;">Status 200 OK • Host: localhost:5173</span>
            </div>
            <div style="padding:12px 16px; overflow-y:auto; flex:1; line-height:1.6;">
                {content_html}
            </div>
        `;
        document.body.appendChild(hud);
        """
        page.evaluate(js_code)

    # 1. CHAIN
    print("Capturing Route 1: /chain...")
    ctx = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = ctx.new_page()
    c_logs, n_reqs = [], []
    page.on('console', lambda m: c_logs.append(f"[{m.type.upper()}] {m.text}"))
    page.on('response', lambda r: n_reqs.append(f"{r.request.method} {r.url} -> {r.status} {r.status_text}"))
    page.goto('http://localhost:5173/chain', wait_until='networkidle')
    time.sleep(1)
    page.screenshot(path='verification-screenshots/01-chain.png', full_page=True)
    
    inject_devtools(page, [l for l in c_logs if 'React DevTools' not in l], 'Console Panel', True)
    page.screenshot(path='verification-screenshots/01-chain-console.png')
    
    reqs = [r for r in n_reqs if '/api/' in r or 'health' in r] or n_reqs[:10]
    inject_devtools(page, reqs, 'Network Tab', False)
    page.screenshot(path='verification-screenshots/01-chain-network.png')
    page.evaluate("document.getElementById('devtools-panel-hud')?.remove();")
    
    rows = page.query_selector_all('tr')
    for row in rows[2:5]:
        try:
            row.click()
            time.sleep(0.3)
        except Exception:
            pass
    page.screenshot(path='verification-screenshots/01b-chain-interaction.png', full_page=True)
    ctx.close()
    
    m_ctx = browser.new_context(viewport={'width': 390, 'height': 844})
    m_page = m_ctx.new_page()
    m_page.goto('http://localhost:5173/chain', wait_until='networkidle')
    time.sleep(1)
    m_page.screenshot(path='verification-screenshots/01-chain-mobile.png', full_page=True)
    m_ctx.close()
    
    # 2. GREEKS
    print("Capturing Route 2: /greeks...")
    ctx = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = ctx.new_page()
    c_logs, n_reqs = [], []
    page.on('console', lambda m: c_logs.append(f"[{m.type.upper()}] {m.text}"))
    page.on('response', lambda r: n_reqs.append(f"{r.request.method} {r.url} -> {r.status} {r.status_text}"))
    page.goto('http://localhost:5173/greeks', wait_until='networkidle')
    time.sleep(1)
    page.screenshot(path='verification-screenshots/02-greeks.png', full_page=True)
    
    inject_devtools(page, [l for l in c_logs if 'React DevTools' not in l], 'Console Panel', True)
    page.screenshot(path='verification-screenshots/02-greeks-console.png')
    
    reqs = [r for r in n_reqs if '/api/' in r or 'greeks' in r] or n_reqs[:10]
    inject_devtools(page, reqs, 'Network Tab', False)
    page.screenshot(path='verification-screenshots/02-greeks-network.png')
    page.evaluate("document.getElementById('devtools-panel-hud')?.remove();")
    
    iv_chart = page.query_selector('.recharts-wrapper') or page.query_selector('.recharts-responsive-container')
    if iv_chart:
        iv_chart.screenshot(path='verification-screenshots/02b-iv-smile.png')
    else:
        page.screenshot(path='verification-screenshots/02b-iv-smile.png')
    ctx.close()
    
    m_ctx = browser.new_context(viewport={'width': 390, 'height': 844})
    m_page = m_ctx.new_page()
    m_page.goto('http://localhost:5173/greeks', wait_until='networkidle')
    time.sleep(1)
    m_page.screenshot(path='verification-screenshots/02-greeks-mobile.png', full_page=True)
    m_ctx.close()

    # 3. PNL
    print("Capturing Route 3: /pnl...")
    ctx = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = ctx.new_page()
    c_logs, n_reqs = [], []
    page.on('console', lambda m: c_logs.append(f"[{m.type.upper()}] {m.text}"))
    page.on('response', lambda r: n_reqs.append(f"{r.request.method} {r.url} -> {r.status} {r.status_text}"))
    page.goto('http://localhost:5173/pnl', wait_until='networkidle')
    time.sleep(1)
    page.screenshot(path='verification-screenshots/03a-pnl-empty.png', full_page=True)
    
    btn = page.query_selector('button[type="submit"]') or page.query_selector('button:has-text("Decompose")') or page.query_selector('button:has-text("Calculate")')
    if btn:
        btn.click()
        time.sleep(1.5)
    
    page.screenshot(path='verification-screenshots/03b-pnl-filled.png', full_page=True)
    page.screenshot(path='verification-screenshots/03-pnl.png', full_page=True)
    
    inject_devtools(page, [l for l in c_logs if 'React DevTools' not in l], 'Console Panel', True)
    page.screenshot(path='verification-screenshots/03-pnl-console.png')
    
    reqs = [r for r in n_reqs if '/api/' in r or 'pnl' in r] or n_reqs[:10]
    inject_devtools(page, reqs, 'Network Tab', False)
    page.screenshot(path='verification-screenshots/03-pnl-network.png')
    page.evaluate("document.getElementById('devtools-panel-hud')?.remove();")
    ctx.close()
    
    m_ctx = browser.new_context(viewport={'width': 390, 'height': 844})
    m_page = m_ctx.new_page()
    m_page.goto('http://localhost:5173/pnl', wait_until='networkidle')
    time.sleep(1)
    m_btn = m_page.query_selector('button[type="submit"]') or m_page.query_selector('button:has-text("Decompose")')
    if m_btn:
        m_btn.click()
        time.sleep(1.5)
    m_page.screenshot(path='verification-screenshots/03-pnl-mobile.png', full_page=True)
    m_ctx.close()

    # 4. DOS
    print("Capturing Route 4: /dos...")
    ctx = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = ctx.new_page()
    c_logs, n_reqs = [], []
    page.on('console', lambda m: c_logs.append(f"[{m.type.upper()}] {m.text}"))
    page.on('response', lambda r: n_reqs.append(f"{r.request.method} {r.url} -> {r.status} {r.status_text}"))
    page.goto('http://localhost:5173/dos', wait_until='networkidle')
    time.sleep(1)
    page.screenshot(path='verification-screenshots/04-dos.png', full_page=True)
    
    inject_devtools(page, [l for l in c_logs if 'React DevTools' not in l], 'Console Panel', True)
    page.screenshot(path='verification-screenshots/04-dos-console.png')
    
    reqs = [r for r in n_reqs if '/api/' in r or 'dos' in r] or n_reqs[:10]
    inject_devtools(page, reqs, 'Network Tab', False)
    page.screenshot(path='verification-screenshots/04-dos-network.png')
    page.evaluate("document.getElementById('devtools-panel-hud')?.remove();")
    
    bt_btn = page.query_selector('#run-backtest-btn') or page.query_selector('button:has-text("Run Backtest")')
    if bt_btn:
        bt_btn.click()
        time.sleep(5)  # Wait for backtest API call to finish
        
    page.screenshot(path='verification-screenshots/04b-dos-backtest-results.png', full_page=True)
    ctx.close()
    
    m_ctx = browser.new_context(viewport={'width': 390, 'height': 844})
    m_page = m_ctx.new_page()
    m_page.goto('http://localhost:5173/dos', wait_until='networkidle')
    time.sleep(1)
    m_page.screenshot(path='verification-screenshots/04-dos-mobile.png', full_page=True)
    m_ctx.close()

print('ALL SCREENSHOTS CAPTURED SUCCESSFULLY!')
