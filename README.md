# Đồ án trực quan hóa tội phạm và phân bố an ninh London

## Lưu ý khi clone từ GitHub

Kho Git lưu mã nguồn, tài liệu, notebook và kết quả kiểm chứng; không lưu `.venv`, dữ liệu thô hoặc dữ liệu đã xử lý. Các dữ liệu này vẫn được giữ nguyên trên máy thực hiện đồ án. Clone kho chưa đủ để chạy dashboard ngay: cần khôi phục `data/raw` theo cấu trúc và nguồn trong [danh mục dataset](docs/DATASET_CATALOG.md), đối chiếu [manifest](data/SOURCE_MANIFEST.csv), cài thư viện theo [hướng dẫn](docs/CAI_DAT_VA_DEMO.md), rồi chạy `python run_pipeline.py` để tạo lại `data/processed`. Notebook đã lưu kết quả có thể đọc mà không chạy lại.

## Phiên bản đã triển khai ngày 10/09/2026

Đã chạy tiền xử lý, EDA và mô hình trên dữ liệu thực: 5.214.794 vụ thuộc 32 borough, 72 tháng. Dashboard có chín loại biểu đồ, lọc theo thời gian/địa bàn/nhóm, chọn borough trên map/bar và drill-down đến LSOA.

- [Đề cương đồ án](docs/DE_CUONG_DO_AN.md): mục tiêu, phương pháp, câu hỏi nghiên cứu, kế hoạch báo cáo và vấn đáp.
- [Cài đặt và demo](docs/CAI_DAT_VA_DEMO.md).
- [Notebook EDA](notebooks/02_eda_london_crime.ipynb).
- [Insight từ dữ liệu thực](reports/INSIGHTS.md).
- [Kết quả đánh giá mô hình](reports/model_summary.json).

Chạy từ thư mục `Do_An`:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501
```

Pipeline hiện thực nằm trong `src/preprocess.py`, `src/eda.py`, `src/model.py`, được điều phối bằng `run_pipeline.py`. Dữ liệu xử lý lưu trong `data/processed`; LSOA chia tệp theo borough để giảm lượng dữ liệu phải đọc khi tương tác.

Hai kết quả cần trình bày rõ: nguồn thiếu 24 tháng FTE Camden (08/2024–07/2026), nên KPI tổng FTE chỉ là phần đã biết; Linear Regression có MAE 255,64 vụ/borough-tháng trên test, cao hơn seasonal naive 157,36. Không điền quân số thiếu bằng 0 hoặc che kết quả mô hình kém baseline.

Tài liệu pipeline bên dưới ban đầu là thiết kế đề xuất; phần “Phiên bản thực thi” trong `docs/PIPELINE.md` ghi tên tệp và quyết định triển khai thực tế.

Thư mục này chứa dữ liệu thô đã tải, bằng chứng nguồn và pipeline đề xuất cho đồ án. Phạm vi được chọn là London vì các nguồn chính thức tải được ổn định, có dữ liệu không gian và có thể kết nối crime, population, boundary và police workforce.

## Bắt đầu từ đâu

1. Đọc [PHAN_TICH_RUBRIC.md](docs/PHAN_TICH_RUBRIC.md) để biết các điều kiện phải đạt.
2. Đọc [DATASET_CATALOG.md](docs/DATASET_CATALOG.md) để hiểu bộ dữ liệu đã chọn và các giới hạn.
3. Đọc [PIPELINE.md](docs/PIPELINE.md) để triển khai từng bước.
4. Tra cứu [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) khi viết code và báo cáo.
5. Kiểm tra [SOURCE_MANIFEST.csv](data/SOURCE_MANIFEST.csv) để lấy link nguồn và mã SHA-256 của tệp tải về.

## Cấu trúc thư mục

```text
Do_An/
├── data/
│   ├── raw/          Dữ liệu gốc, không chỉnh sửa
│   ├── processed/    Dữ liệu sau làm sạch và kết nối
│   └── SOURCE_MANIFEST.csv
├── src/              Script Python của pipeline
├── notebooks/        Notebook EDA
├── dashboard/        Ứng dụng Streamlit + Plotly
├── reports/          Báo cáo IEEE và hình xuất
└── docs/             Rubric, pipeline, data dictionary, bằng chứng nguồn
```

## Kết luận chọn dữ liệu

- Bộ dữ liệu hợp lệ theo rubric: nhiều hơn 5.000 dòng và có ít nhất 3 bảng độc lập để Join/Merge.
- Crime LSOA có 227.526 dòng thô, bao phủ 08/2020 đến 07/2026.
- Census 2021 khớp 4.991/4.991 mã LSOA xuất hiện trong dữ liệu crime.
- Boundary khớp đủ 4.991 mã crime và hỗ trợ choropleth map.
- Dữ liệu cảnh sát có 126.230 dòng hoạt động và 73.567 dòng quân số, từ 08/2021 đến 07/2026.
- Dữ liệu quầy cảnh sát năm 2013 chỉ là nguồn phụ để minh họa khả năng tiếp cận lịch sử, không dùng để suy luận hiện trạng hoặc làm biến dự báo chính.

## Công cụ đề xuất

Python cho tiền xử lý, EDA và mô hình; Streamlit + Plotly cho dashboard. Cấu hình này thống nhất một ngôn ngữ từ đầu đến cuối và phù hợp yêu cầu bản đồ, bộ lọc, drill-down và biểu đồ dự báo.
