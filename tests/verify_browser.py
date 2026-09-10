"""Browser smoke test and screenshots of the actual Streamlit application."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

DEST = Path(__file__).resolve().parents[1] / 'reports' / 'verification'
DEST.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://localhost:8501', wait_until='networkidle')
    page.get_by_text('Số vụ trong kỳ', exact=True).wait_for(timeout=60000)
    page.get_by_role('button', name='Tải bảng đang lọc', include_hidden=True).wait_for(state='attached', timeout=60000)
    page.locator('[data-testid="stStatusWidget"]').wait_for(state='hidden', timeout=60000)
    page.locator('.choroplethlayer path').first.wait_for(timeout=45000)
    page.screenshot(path=str(DEST / 'desktop_overview.png'), full_page=True)
    geo_count = page.locator('.choroplethlayer path').count()
    assert geo_count >= 32, f'Blank/incomplete map: {geo_count} paths'
    # A click on a ranking bar must update the shared borough widget and reveal LSOA detail.
    page.locator('.barlayer .point path').first.click(force=True)
    page.wait_for_function("(() => {const e=document.querySelector('[data-testid=stSidebar] [data-testid=stSelectbox]'); return e && !e.innerText.includes('Tất cả');})()", timeout=30000)
    page.get_by_text('LSOA', exact=True).first.wait_for(state='attached', timeout=30000)
    page.locator('[data-testid="stStatusWidget"]').wait_for(state='hidden', timeout=60000)
    page.get_by_role('tab', name='Chi tiết LSOA').click()
    page.get_by_role('tab', name='Chi tiết LSOA').wait_for(timeout=30000)
    page.get_by_text('LSOA', exact=True).filter(visible=True).wait_for(timeout=30000)
    page.locator('[data-testid="stPlotlyChart"]').filter(visible=True).first.wait_for(timeout=30000)
    page.screenshot(path=str(DEST / 'desktop_drilldown.png'), full_page=True)
    page.get_by_role('tab', name='Dự báo', exact=True).click()
    page.get_by_text('Dự báo 6 tháng', exact=True).first.wait_for(timeout=30000)
    page.screenshot(path=str(DEST / 'desktop_forecast.png'), full_page=True)
    page.get_by_role('tab', name='Cơ cấu và phân phối').click()
    page.screenshot(path=str(DEST / 'desktop_distributions.png'), full_page=True)
    page.get_by_role('tab', name='Tổng quan', exact=True).click()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_function("document.querySelector('[data-testid=stSidebar]').getBoundingClientRect().right <= 1", timeout=10000)
    page.screenshot(path=str(DEST / 'mobile_overview.png'), full_page=True)
    page.locator('[data-testid="stPlotlyChart"]').filter(visible=True).first.scroll_into_view_if_needed()
    page.screenshot(path=str(DEST / 'mobile_map.png'), full_page=True)
    overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    assert not page.locator('[data-testid="stException"]').count()
    assert not errors, errors
    (DEST / 'browser_checks.json').write_text(json.dumps({'map_paths': geo_count,
        'bar_click_drilldown': True, 'page_errors': errors, 'mobile_document_overflow': overflow}, indent=2), encoding='utf-8')
    print({'map_paths': geo_count, 'errors': errors, 'overflow': overflow})
    browser.close()
