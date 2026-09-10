"""Produce an executable teaching notebook from the implemented analysis."""
import nbformat as nbf
import sys
from common import ROOT

nb = nbf.v4.new_notebook()
nb.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
nb.cells = [
    nbf.v4.new_markdown_cell('# London: khám phá dữ liệu tội phạm và nguồn lực cảnh sát\n\nPhạm vi 32 borough MPS. Notebook sử dụng dữ liệu đã xử lý bởi `run_pipeline.py`. Dân số cố định Census 2021; FTE Camden thiếu từ 08/2024. Không điền dữ liệu thiếu thành 0.'),
    nbf.v4.new_code_cell('from pathlib import Path\nimport sys\nROOT = Path.cwd()\nif not (ROOT / "data/processed").exists():\n    ROOT = ROOT.parent\nassert (ROOT / "data/processed").exists(), "Mở notebook từ Do_An hoặc Do_An/notebooks"\nsys.path.insert(0, str(ROOT / "src"))\nimport pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nfrom IPython.display import Image, display\nmonthly = pd.read_parquet(ROOT / "data/processed/monthly.parquet")\nfacts = pd.read_parquet(ROOT / "data/processed/crime_borough.parquet")\nprint("Borough-category-month rows:", len(facts))\nprint("Borough-month rows:", len(monthly))\ndisplay(monthly.head())'),
    nbf.v4.new_markdown_cell('## Chất lượng và dữ liệu thiếu\nKiểm tra phạm vi thời gian, khóa trùng và FTE thiếu. Phân biệt thiếu trước 08/2021 với thiếu Camden sau 08/2024.'),
    nbf.v4.new_code_cell('display(monthly.isna().sum().to_frame("missing"))\nassert not monthly.duplicated(["borough_name", "month"]).any()\nassert monthly.crime_count.sum() == facts.crime_count.sum()\ndisplay(monthly[(monthly.month >= "2021-08-01") & monthly.officer_fte.isna()][["borough_name", "month"]])'),
    nbf.v4.new_markdown_cell('## Sinh sáu hình EDA\nHàm `run_eda` trong src/eda.py vẽ bằng Matplotlib/Seaborn và lưu PNG để đưa vào báo cáo. Mở file code để giải thích từng phép tổng hợp, trục và mẫu số.'),
    nbf.v4.new_code_cell('from eda import run_eda\nrun_eda()\nfor image in sorted((ROOT / "reports/figures").glob("*.png")):\n    print(image.name)\n    display(Image(filename=str(image), width=900))'),
    nbf.v4.new_markdown_cell('## Tự kiểm tra một biểu đồ\nTổng hợp tháng từ bảng borough, tránh cộng lặp dân số hoặc FTE theo phân nhóm.'),
    nbf.v4.new_code_cell('trend = monthly.groupby("month", as_index=False).crime_count.sum()\nfig, ax = plt.subplots(figsize=(11, 4))\nsns.lineplot(trend, x="month", y="crime_count", ax=ax)\nax.set(title="Recorded crime across 32 MPS boroughs", ylabel="Offences")\nplt.show()'),
    nbf.v4.new_markdown_cell('## Dự báo và đánh giá\nTrain 60 tháng, test 12 tháng cuối. Đọc MAE/RMSE/R² của mô hình và baseline. Không thay giả thuyết sau khi xem test để báo cáo điểm đẹp hơn.'),
    nbf.v4.new_code_cell('import json\ndisplay(pd.read_csv(ROOT / "reports/model_metrics.csv").head(10))\nprint(json.dumps(json.loads((ROOT / "reports/model_summary.json").read_text()), indent=2))'),
    nbf.v4.new_markdown_cell('## Câu hỏi thảo luận\n1. Xếp hạng số vụ và tỷ lệ có giống nhau không?\n2. Thiếu FTE Camden tác động thế nào đến so sánh nguồn lực?\n3. Vì sao tổng LSOA không được mặc định bằng tổng borough?\n4. Vì sao hồi quy kém seasonal naive?\n5. Cần thêm dữ liệu gì để nghiên cứu nguyên nhân?'),
]
path = ROOT / 'notebooks' / '02_eda_london_crime.ipynb'
path.parent.mkdir(parents=True, exist_ok=True)
if '--execute' in sys.argv:
    from nbclient import NotebookClient
    NotebookClient(nb, timeout=180, kernel_name='london-project',
                   resources={'metadata': {'path': str(ROOT)}}).execute()
nbf.write(nb, path)
print(path)
