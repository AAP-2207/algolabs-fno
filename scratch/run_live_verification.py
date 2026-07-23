import os
import sys
import time
import json
import urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
os.makedirs('screenshots', exist_ok=True)

LIVE_FRONTEND = 'https://algolabs-fno.vercel.app'
LIVE_BACKEND = 'https://algolabs-fno.onrender.com'

results = {
    'commit': '1b960c6ba9858bb425d04dea5a8d40448c54a8de',
    'live_frontend': LIVE_FRONTEND,
    'live_backend': LIVE_BACKEND,
    'pages': {},
    'backend_responses': {},
    'console_logs': {}
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # ---------------------------------------------------------
    # ROUTE 1: /chain
    # ---------------------------------------------------------
    print("Testing Live Route: /chain...")
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    logs_chain = []
    page.on('console', lambda m: logs_chain.append(f"[{m.type.upper()}] {m.text}"))
    page.on('pageerror', lambda e: logs_chain.append(f"[UNHANDLED ERROR] {str(e)}"))
    
    page.goto(f'{LIVE_FRONTEND}/chain', wait_until='networkidle')
    time.sleep(2)
    page.screenshot(path='screenshots/chain-initial.png', full_page=True)
    text_chain_initial = page.inner_text('body')
    
    time.sleep(10)
    page.screenshot(path='screenshots/chain-after-10s.png', full_page=True)
    text_chain_10s = page.inner_text('body')
    
    results['pages']['chain'] = {
        'initial_text': text_chain_initial,
        'after_10s_text': text_chain_10s,
    }
    results['console_logs']['chain'] = logs_chain
    context.close()

    # ---------------------------------------------------------
    # ROUTE 2: /greeks
    # ---------------------------------------------------------
    print("Testing Live Route: /greeks...")
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    logs_greeks = []
    page.on('console', lambda m: logs_greeks.append(f"[{m.type.upper()}] {m.text}"))
    page.on('pageerror', lambda e: logs_greeks.append(f"[UNHANDLED ERROR] {str(e)}"))
    
    page.goto(f'{LIVE_FRONTEND}/greeks', wait_until='networkidle')
    time.sleep(2)
    page.screenshot(path='screenshots/greeks-initial.png', full_page=True)
    text_greeks_initial = page.inner_text('body')
    
    time.sleep(10)
    page.screenshot(path='screenshots/greeks-after-10s.png', full_page=True)
    text_greeks_10s = page.inner_text('body')
    
    results['pages']['greeks'] = {
        'initial_text': text_greeks_initial,
        'after_10s_text': text_greeks_10s,
    }
    results['console_logs']['greeks'] = logs_greeks
    context.close()

    # ---------------------------------------------------------
    # ROUTE 3: /pnl
    # ---------------------------------------------------------
    print("Testing Live Route: /pnl...")
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    logs_pnl = []
    page.on('console', lambda m: logs_pnl.append(f"[{m.type.upper()}] {m.text}"))
    page.on('pageerror', lambda e: logs_pnl.append(f"[UNHANDLED ERROR] {str(e)}"))
    
    page.goto(f'{LIVE_FRONTEND}/pnl', wait_until='networkidle')
    time.sleep(2)
    page.screenshot(path='screenshots/pnl-initial.png', full_page=True)
    text_pnl_initial = page.inner_text('body')
    
    time.sleep(10)
    page.screenshot(path='screenshots/pnl-after-10s.png', full_page=True)
    text_pnl_10s = page.inner_text('body')
    
    # Fill in test case: Strike 24000 CE, Buy, Qty 50, Entry 120, Spot Prev 24300, Spot Now 24350, Days Elapsed 1, Entry IV 15%, Current IV 15.5%
    # Selectors in PnlPage.tsx:
    # Inputs have labels or placeholder / value defaults. Let's find inputs or trigger calculation
    btn_decompose = page.query_selector('button[type="submit"]') or page.query_selector('button:has-text("Run Taylor Decomposer")') or page.query_selector('button:has-text("Decompose")')
    if btn_decompose:
        btn_decompose.click()
        time.sleep(2)
    page.screenshot(path='screenshots/pnl-result.png', full_page=True)
    text_pnl_result = page.inner_text('body')
    
    results['pages']['pnl'] = {
        'initial_text': text_pnl_initial,
        'after_10s_text': text_pnl_10s,
        'result_text': text_pnl_result,
    }
    results['console_logs']['pnl'] = logs_pnl
    context.close()

    # ---------------------------------------------------------
    # ROUTE 4: /dos
    # ---------------------------------------------------------
    print("Testing Live Route: /dos...")
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    logs_dos = []
    page.on('console', lambda m: logs_dos.append(f"[{m.type.upper()}] {m.text}"))
    page.on('pageerror', lambda e: logs_dos.append(f"[UNHANDLED ERROR] {str(e)}"))
    
    page.goto(f'{LIVE_FRONTEND}/dos', wait_until='networkidle')
    time.sleep(2)
    page.screenshot(path='screenshots/dos-initial.png', full_page=True)
    text_dos_initial = page.inner_text('body')
    
    time.sleep(10)
    page.screenshot(path='screenshots/dos-after-10s.png', full_page=True)
    text_dos_10s = page.inner_text('body')
    
    btn_bt = page.query_selector('#run-backtest-btn')
    text_dos_bt = ""
    if btn_bt:
        print("Clicking Run Backtest on live site...")
        btn_bt.click()
        try:
            page.wait_for_selector('text=Trade Log', timeout=30000)
            time.sleep(2)
            page.screenshot(path='screenshots/dos-backtest-result.png', full_page=True)
            text_dos_bt = page.inner_text('body')
        except Exception as err:
            print("Backtest wait timeout on live site:", err)
            page.screenshot(path='screenshots/dos-backtest-result.png', full_page=True)
            text_dos_bt = page.inner_text('body')
            
    results['pages']['dos'] = {
        'initial_text': text_dos_initial,
        'after_10s_text': text_dos_10s,
        'backtest_text': text_dos_bt
    }
    results['console_logs']['dos'] = logs_dos
    context.close()
    browser.close()

# ---------------------------------------------------------
# STEP 3: BACKEND DIRECT CHECKS (LIVE URLs)
# ---------------------------------------------------------
print("Fetching Live Backend Endpoints...")
endpoints = {
    'health': f'{LIVE_BACKEND}/health',
    'option_chain': f'{LIVE_BACKEND}/api/option-chain?symbol=NIFTY',
    'greeks': f'{LIVE_BACKEND}/api/greeks?symbol=NIFTY',
    'dos_signal': f'{LIVE_BACKEND}/api/dos/signal'
}

for key, url in endpoints.items():
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            results['backend_responses'][key] = json.loads(body)
    except Exception as e:
        results['backend_responses'][key] = {'error': str(e)}

with open('scratch/live_verification_raw.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("LIVE VERIFICATION COMPLETE! RAW JSON WRITTEN TO scratch/live_verification_raw.json")
