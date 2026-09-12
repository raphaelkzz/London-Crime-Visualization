"""Verify reference shapes and real pointer-triggered drop lines in the browser."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

DEST = Path(__file__).resolve().parents[1] / 'reports' / 'verification'
DEST.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://localhost:8501', wait_until='networkidle')
    page.get_by_role('button', name='Tải bảng đang lọc', include_hidden=True).wait_for(state='attached', timeout=60000)
    page.locator('[data-testid="stStatusWidget"]').wait_for(state='hidden', timeout=60000)

    def hover_point(plot, name):
        plot.scroll_into_view_if_needed()
        point = plot.locator('.scatterlayer .points .point').nth(5)
        point.hover(force=True)
        page.wait_for_function('document.querySelectorAll("line.spikeline").length >= 2')
        assert plot.locator('line.spikeline').count() >= 2
        plot.screenshot(path=str(DEST / f'{name}_drop_lines.png'))

    trend = page.locator('.js-plotly-plot').filter(has_text='Xu hướng')
    assert trend.locator('.shapelayer path').count() == 1
    hover_point(trend, 'trend')
    page.get_by_role('tab', name='Nguồn lực cảnh sát', exact=True).click()
    scatter = page.locator('.js-plotly-plot').filter(has_text='Nguồn lực và tỷ lệ tội phạm')
    hover_point(scatter, 'scatter')
    page.get_by_role('tab', name='Tổng quan', exact=True).click()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_function('document.querySelector("[data-testid=stSidebar]").getBoundingClientRect().right <= 1')
    trend.scroll_into_view_if_needed()
    page.screenshot(path=str(DEST / 'mobile_reference_line.png'))
    assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    assert not page.locator('[data-testid="stException"]').count()
    assert not errors, errors
    (DEST / 'reference_line_checks.json').write_text(json.dumps({
        'trend_reference_line': True, 'trend_pointer_drop_lines': True,
        'scatter_pointer_drop_lines': True, 'mobile_no_overflow': True,
        'page_errors': errors,
    }, indent=2), encoding='utf-8')
    print('Reference line, pointer drop lines and mobile checks passed.')
    browser.close()
