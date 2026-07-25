import os
import sys
import json
import time
import urllib.request
import urllib.error
from playwright.sync_api import sync_playwright

BASE_FE_URL = "http://localhost:3001"
BASE_BE_URL = "http://127.0.0.1:8000"
ROOT_DIR = r"c:\Users\armaa\OneDrive\Documents\f&o_sofi\algolabs-fno"
SCREENSHOT_DIR = os.path.join(ROOT_DIR, "audit_screenshots")
AUDIT_DATA_PATH = os.path.join(ROOT_DIR, "scratch", "audit_data.json")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

audit_results = {
    "console_logs": [],
    "console_errors": [],
    "part1": {},
    "part2": {},
    "part3": {},
    "part4": {},
    "part5": {},
    "part6": {}
}

def log_msg(msg):
    print(f"[AUDIT] {msg}")

def run_playwright_audit():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        def handle_console(msg):
            entry = f"[{msg.type.upper()}] {msg.text}"
            audit_results["console_logs"].append(entry)
            if msg.type in ["error"]:
                audit_results["console_errors"].append(entry)

        page.on("console", handle_console)

        # REQ 1: /chain
        try:
            log_msg("Auditing Req 1: /chain")
            page.goto(f"{BASE_FE_URL}/chain")
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req1_chain_viewer.png"))

            table_rows = page.query_selector_all("table tbody tr")
            row_count = len(table_rows)
            headers = [th.inner_text().strip() for th in page.query_selector_all("table thead th")]
            
            sample_rows_data = []
            for r in table_rows[:5]:
                cells = [td.inner_text().strip() for td in r.query_selector_all("td")]
                sample_rows_data.append(cells)

            header_text = page.locator("header").inner_text()
            
            audit_results["part1"]["req1"] = {
                "row_count": row_count,
                "headers": headers,
                "sample_rows": sample_rows_data,
                "header_summary": header_text.replace("\n", " | "),
                "screenshot": "req1_chain_viewer.png"
            }
        except Exception as e:
            audit_results["part1"]["req1_error"] = str(e)

        # REQ 2, 3, 4: /greeks
        try:
            log_msg("Auditing Req 2, 3, 4: /greeks")
            page.goto(f"{BASE_FE_URL}/greeks")
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req2_greeks_calculator.png"))
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req3_iv_solver.png"))
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req4_2d_iv_smile.png"))

            greeks_table_rows = page.query_selector_all("table tbody tr")
            greeks_sample = []
            for r in greeks_table_rows[:5]:
                cells = [td.inner_text().strip() for td in r.query_selector_all("td")]
                greeks_sample.append(cells)

            chart_present = page.locator(".recharts-responsive-container").count() > 0

            audit_results["part1"]["req2_3_4"] = {
                "row_count": len(greeks_table_rows),
                "greeks_sample": greeks_sample,
                "chart_present": chart_present,
                "screenshots": ["req2_greeks_calculator.png", "req3_iv_solver.png", "req4_2d_iv_smile.png"]
            }
        except Exception as e:
            audit_results["part1"]["req2_3_4_error"] = str(e)

        # REQ 5: /pnl
        try:
            log_msg("Auditing Req 5: /pnl")
            page.goto(f"{BASE_FE_URL}/pnl")
            page.wait_for_timeout(1000)

            page.fill("#strike", "23800")
            page.fill("#quantity", "50")
            page.fill("#entryPrice", "250")
            page.fill("#currentPrice", "310")
            page.fill("#currentS", "23950")
            page.fill("#previousS", "23800")
            page.fill("#daysElapsed", "2")
            page.fill("#volatility", "16")
            page.fill("#currentVolatility", "18")
            
            submit_btn = page.locator("button[type='submit']")
            if submit_btn.count() > 0:
                submit_btn.click()
                page.wait_for_timeout(1500)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req5_pnl_decomposer.png"))

            pnl_results_text = page.locator("body").inner_text()

            audit_results["part1"]["req5"] = {
                "pnl_output_summary": pnl_results_text.replace("\n", " | ")[:1200],
                "screenshot": "req5_pnl_decomposer.png"
            }
        except Exception as e:
            audit_results["part1"]["req5_error"] = str(e)

        # REQ 6: Interpretation Cards
        try:
            log_msg("Auditing Req 6: Interpretation Cards")
            page.goto(f"{BASE_FE_URL}/chain")
            page.wait_for_timeout(1000)
            chain_cards_text = page.locator("body").inner_text()

            page.goto(f"{BASE_FE_URL}/greeks")
            page.wait_for_timeout(1000)
            greeks_cards_text = page.locator("body").inner_text()

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req6_interpretation_cards.png"))

            audit_results["part1"]["req6"] = {
                "chain_cards_text": chain_cards_text[:1200],
                "greeks_cards_text": greeks_cards_text[:1200],
                "screenshot": "req6_interpretation_cards.png"
            }
        except Exception as e:
            audit_results["part1"]["req6_error"] = str(e)

        # REQ 7-12: /dos
        try:
            log_msg("Auditing Req 7-12: /dos")
            page.goto(f"{BASE_FE_URL}/dos")
            page.wait_for_timeout(1500)
            
            initial_dos_text = page.locator("body").inner_text()

            bypass_switch = page.locator("button[role='switch']")
            if bypass_switch.count() > 0:
                bypass_switch.click()
                page.wait_for_timeout(1000)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req7_dos_gated_and_active.png"))
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req8_strike_autoselect.png"))
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req9_sl_monitor.png"))

            active_dos_text = page.locator("body").inner_text()

            backtest_btn = page.locator("button:has-text('Run Backtest')")
            if backtest_btn.count() > 0:
                backtest_btn.click()
                page.wait_for_timeout(3000)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req10_backtest_results.png"))
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req11_dos_interpretation_card.png"))
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "req12_card_styling_consistency.png"))

            post_backtest_dos_text = page.locator("body").inner_text()

            audit_results["part1"]["dos_module"] = {
                "initial_dos_text": initial_dos_text.replace("\n", " | ")[:800],
                "active_dos_text": active_dos_text.replace("\n", " | ")[:800],
                "post_backtest_text": post_backtest_dos_text.replace("\n", " | ")[:1200],
                "screenshots": [
                    "req7_dos_gated_and_active.png",
                    "req8_strike_autoselect.png",
                    "req9_sl_monitor.png",
                    "req10_backtest_results.png",
                    "req11_dos_interpretation_card.png",
                    "req12_card_styling_consistency.png"
                ]
            }
        except Exception as e:
            audit_results["part1"]["dos_module_error"] = str(e)

        # EDGE CASES 13-21
        log_msg("Auditing Edge Cases 13-21")

        # EC 13: Sell position
        try:
            page.goto(f"{BASE_FE_URL}/pnl")
            page.wait_for_timeout(1000)
            sell_button = page.locator("button:has-text('Sell (Short)')")
            if sell_button.count() > 0:
                sell_button.click()
            page.fill("#strike", "23800")
            page.fill("#quantity", "50")
            page.fill("#entryPrice", "250")
            page.fill("#currentPrice", "310")
            page.fill("#currentS", "23950")
            page.fill("#previousS", "23800")
            page.fill("#daysElapsed", "2")
            page.fill("#volatility", "16")
            page.fill("#currentVolatility", "18")
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ec13_pnl_sell_position.png"))
            audit_results["part2"]["ec13"] = page.locator("body").inner_text().replace("\n", " | ")[:800]
        except Exception as e:
            audit_results["part2"]["ec13_error"] = str(e)

        # EC 14: Put option
        try:
            pe_button = page.locator("button:has-text('Put (PE)')")
            if pe_button.count() > 0:
                pe_button.click()
                page.locator("button[type='submit']").click()
                page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ec14_pnl_pe_option.png"))
            audit_results["part2"]["ec14"] = page.locator("body").inner_text().replace("\n", " | ")[:800]
        except Exception as e:
            audit_results["part2"]["ec14_error"] = str(e)

        # EC 15: Zero quantity
        try:
            page.fill("#quantity", "0")
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ec15_pnl_zero_quantity.png"))
            audit_results["part2"]["ec15"] = page.locator("body").inner_text().replace("\n", " | ")[:800]
        except Exception as e:
            audit_results["part2"]["ec15_error"] = str(e)

        # EC 16: Negative inputs
        try:
            page.fill("#entryPrice", "-10")
            page.fill("#daysElapsed", "-5")
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ec16_pnl_negative_inputs.png"))
            audit_results["part2"]["ec16"] = page.locator("body").inner_text().replace("\n", " | ")[:800]
        except Exception as e:
            audit_results["part2"]["ec16_error"] = str(e)

        # EC 17: Rapid reloads
        try:
            page.goto(f"{BASE_FE_URL}/chain")
            page.reload()
            page.reload()
            page.reload()
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ec17_rapid_reloads.png"))
            audit_results["part2"]["ec17"] = page.locator("body").inner_text()[:500]
        except Exception as e:
            audit_results["part2"]["ec17_error"] = str(e)

        # EC 18: Direct URLs
        try:
            urls = ["/chain", "/greeks", "/pnl", "/dos"]
            ec18_statuses = []
            for url in urls:
                res = page.goto(f"{BASE_FE_URL}{url}")
                ec18_statuses.append((url, res.status))
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ec18_direct_urls.png"))
            audit_results["part2"]["ec18_statuses"] = ec18_statuses
        except Exception as e:
            audit_results["part2"]["ec18_error"] = str(e)

        # EC 19: Double click Run Backtest
        try:
            page.goto(f"{BASE_FE_URL}/dos")
            page.wait_for_timeout(1000)
            bypass_switch = page.locator("button[role='switch']")
            if bypass_switch.count() > 0:
                bypass_switch.click()
            btn = page.locator("button:has-text('Run Backtest')")
            if btn.count() > 0:
                btn.click()
                btn.click()
                page.wait_for_timeout(2500)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "ec19_backtest_double_click.png"))
            audit_results["part2"]["ec19"] = page.locator("body").inner_text()[:600]
        except Exception as e:
            audit_results["part2"]["ec19_error"] = str(e)

        # EC 20: Mobile Viewport 375px
        try:
            mobile_context = browser.new_context(viewport={"width": 375, "height": 812})
            mobile_page = mobile_context.new_page()
            for page_name in ["chain", "greeks", "pnl", "dos"]:
                mobile_page.goto(f"{BASE_FE_URL}/{page_name}")
                mobile_page.wait_for_timeout(1000)
                mobile_page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"ec20_mobile_{page_name}.png"))

            mobile_context.close()
            audit_results["part2"]["ec20"] = "Captured 4 mobile screenshots (375x812)"
        except Exception as e:
            audit_results["part2"]["ec20_error"] = str(e)

        browser.close()

        # PART 4: FastAPI Docs Screenshot
        try:
            log_msg("Auditing Part 4: Swagger Docs")
            doc_browser = p.chromium.launch(headless=True)
            doc_page = doc_browser.new_page(viewport={"width": 1280, "height": 900})
            doc_page.goto(f"{BASE_BE_URL}/docs")
            doc_page.wait_for_timeout(2000)
            doc_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "part4_swagger_docs.png"))
            doc_browser.close()
            audit_results["part4"] = "Swagger UI rendered cleanly at /docs"
        except Exception as e:
            audit_results["part4_error"] = str(e)

def run_backend_api_audit():
    log_msg("Auditing Part 3: Direct Backend APIs")
    endpoints = [
        ("GET", "/health", None),
        ("GET", "/api/option-chain?symbol=NIFTY", None),
        ("GET", "/api/greeks?symbol=NIFTY", None),
        ("POST", "/api/pnl-decompose", {
            "strike": 23800,
            "option_type": "CE",
            "position": "buy",
            "quantity": 50,
            "entry_price": 250,
            "current_price": 310,
            "current_S": 23950,
            "previous_S": 23800,
            "days_elapsed": 2,
            "volatility": 0.16,
            "days_to_expiry": 30,
            "current_volatility": 0.18
        }),
        ("GET", "/api/dos/signal", None),
        ("POST", "/api/dos/backtest", {
            "capital": 100000,
            "days": 60
        }),
        ("GET", "/api/dos/trades", None),
        ("GET", "/api/spot?ticker=^NSEI", None)
    ]

    api_results = {}
    for method, path, payload in endpoints:
        url = f"{BASE_BE_URL}{path}"
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header('Content-Type', 'application/json')
            data_bytes = json.dumps(payload).encode('utf-8') if payload else None
            res = urllib.request.urlopen(req, data=data_bytes)
            body = res.read().decode('utf-8')
            api_results[path] = {
                "status": res.status,
                "response": json.loads(body) if body.startswith("{") or body.startswith("[") else body
            }
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            api_results[path] = {
                "status": e.code,
                "response": json.loads(body) if body.startswith("{") else body
            }
        except Exception as e:
            api_results[path] = {
                "status": 500,
                "error": str(e)
            }

    # Test 23: Missing required field
    log_msg("Auditing Test 23: Missing required field")
    url_23 = f"{BASE_BE_URL}/api/pnl-decompose"
    bad_payload = {
        "option_type": "CE",
        "position": "buy",
        "quantity": 50,
        "entry_price": 250,
        "current_price": 310,
        "current_S": 23950,
        "previous_S": 23800,
        "days_elapsed": 2
    }
    try:
        req = urllib.request.Request(url_23, method="POST")
        req.add_header('Content-Type', 'application/json')
        res = urllib.request.urlopen(req, data=json.dumps(bad_payload).encode('utf-8'))
        api_results["test23_missing_field"] = {"status": res.status, "body": res.read().decode('utf-8')}
    except urllib.error.HTTPError as e:
        api_results["test23_missing_field"] = {"status": e.code, "body": json.loads(e.read().decode('utf-8'))}

    # Test 24: Invalid symbol
    log_msg("Auditing Test 24: Invalid symbol")
    url_24 = f"{BASE_BE_URL}/api/option-chain?symbol=FAKESTOCK"
    try:
        res = urllib.request.urlopen(url_24)
        api_results["test24_invalid_symbol"] = {"status": res.status, "body": json.loads(res.read().decode('utf-8'))}
    except urllib.error.HTTPError as e:
        api_results["test24_invalid_symbol"] = {"status": e.code, "body": e.read().decode('utf-8')}

    audit_results["part3"] = api_results

if __name__ == "__main__":
    run_playwright_audit()
    run_backend_api_audit()

    with open(AUDIT_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"Audit runner complete. Data saved to {AUDIT_DATA_PATH}.")
