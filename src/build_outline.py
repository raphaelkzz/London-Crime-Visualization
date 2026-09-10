"""Render the Vietnamese project outline as a standalone, printable HTML file."""
from pathlib import Path
import mistune

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'docs' / 'DE_CUONG_DO_AN.md'
markdown = mistune.create_markdown(escape=True, plugins=['table'])
body = markdown(source.read_text(encoding='utf-8'))
html = '''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Đề cương đồ án · London</title><style>
body{font:16px/1.7 Georgia,"Times New Roman",serif;color:#222;background:#fff;margin:0}
main{max-width:960px;margin:48px auto;padding:0 24px 60px}
h1,h2,h3{font-family:Arial,sans-serif;line-height:1.3;letter-spacing:0}
h1{font-size:28px;border-bottom:2px solid #007c83;padding-bottom:16px}
h2{font-size:21px;margin-top:36px}h3{font-size:17px;margin-top:24px}
table{border-collapse:collapse;width:100%;font:14px/1.5 Arial,sans-serif;display:block;overflow-x:auto}
th,td{border-bottom:1px solid #ddd;padding:10px;text-align:left;vertical-align:top}
th{background:#edf3f3}a{color:#007078;overflow-wrap:anywhere}
pre{background:#f4f5f5;padding:16px;overflow:auto}code{font-size:13px}
@media print{main{margin:0;max-width:none;padding:0}body{font-size:11pt}h2{break-after:avoid}tr{break-inside:avoid}a{color:inherit}pre{white-space:pre-wrap}}
</style></head><body><main>''' + body + '</main></body></html>'
target = source.with_suffix('.html')
target.write_text(html, encoding='utf-8')
print(target)
