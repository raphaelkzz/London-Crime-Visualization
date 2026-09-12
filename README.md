# London Crime Visualization

Đồ án nghiên cứu và trực quan hóa tội phạm cùng phân bố nguồn lực cảnh sát tại London, sử dụng Python, Streamlit và Plotly.

## Phạm vi và chức năng

- Phân tích 5.214.794 vụ được ghi nhận tại 32 borough, từ 08/2020 đến 07/2026.
- Kết nối dữ liệu tội phạm, dân số Census 2021, ranh giới địa lý và nguồn lực cảnh sát.
- Dashboard gồm 9 loại biểu đồ, bộ lọc thời gian/địa bàn/loại tội phạm và drill-down đến LSOA.
- Reference line thể hiện trung bình tháng theo bộ lọc trên biểu đồ xu hướng và trung bình cộng các borough có dữ liệu trên xếp hạng (32 khi đầy đủ, không chỉ top 15). Nhãn ghi số borough tham gia; tỷ lệ được lấy trung bình cộng, không phải tỷ lệ dân số có trọng số toàn London. Đây là mốc mô tả, không phải ngưỡng an toàn. Drop line dóng điểm dữ liệu tới hai trục khi rê chuột trên xu hướng, scatter, LSOA và dự báo.
- Pipeline làm sạch dữ liệu, tạo 6 biểu đồ EDA và dự báo 6 tháng bằng Linear Regression, so sánh với seasonal naive.

## Cài đặt và chạy

Yêu cầu Python 3.10 trở lên. Chạy tại thư mục gốc của kho:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_pipeline.py
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501
```

Mở http://localhost:8501 sau khi khởi động Streamlit.

**Cần chuẩn bị dữ liệu trước khi chạy pipeline.** Kho không chứa `data/raw`, `data/processed` hoặc `.venv`. Khôi phục các tệp gốc và thư mục giải nén vào `data/raw` theo đường dẫn trong `src/preprocess.py`; [manifest nguồn](data/SOURCE_MANIFEST.csv) cung cấp URL và SHA-256 để đối chiếu. Dữ liệu vẫn được giữ nguyên trên máy thực hiện đồ án. Clone kho không tự tải dữ liệu; pipeline tạo lại `data/processed` từ dữ liệu gốc đã có.

## Cấu trúc

```text
dashboard/       Dashboard Streamlit
src/             Tiền xử lý, EDA, mô hình và tiện ích
data/            Manifest nguồn; dữ liệu local không đưa vào Git
notebooks/       Notebook EDA có kết quả đã chạy
reports/         Biểu đồ, chỉ số mô hình và bằng chứng kiểm thử
docs/            Rubric, bản HTML đề cương và bằng chứng nguồn
tests/           Kiểm thử pipeline, ứng dụng và trình duyệt
run_pipeline.py  Chạy pipeline từ đầu đến cuối
```

Các tài liệu Markdown phân tích đã được chuyển ra ngoài kho, vào thư mục `Tai_Lieu_Do_An` cạnh thư mục dự án trên máy local. README này là tài liệu Markdown duy nhất được duy trì trong kho. EDA lưu ghi chú mới vào `Tai_Lieu_Do_An/reports`; tiện ích tạo HTML đề cương cần tài liệu local tại `Tai_Lieu_Do_An/docs/DE_CUONG_DO_AN.md`.

## Kết quả và kiểm thử

- [Notebook EDA](notebooks/02_eda_london_crime.ipynb)
- [Kết quả mô hình](reports/model_summary.json)
- [Kiểm tra chất lượng dữ liệu](reports/data_quality.json)
- [Kiểm chứng giao diện](reports/verification/browser_checks.json)

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline.py tests/test_app.py -q
```

Các kiểm thử dữ liệu và ứng dụng cần có dữ liệu đã xử lý. Lần kiểm chứng gần nhất: 8 kiểm thử đạt; bản đồ đủ 32 borough, chọn biểu đồ cập nhật bộ lọc và giao diện mobile không tràn ngang. Đường dóng đã được kiểm tra bằng thao tác rê chuột thật trên trình duyệt; bằng chứng trong `reports/verification/reference_line_checks.json`. Có thể chạy lại bằng `python tests/verify_reference_lines.py` khi dashboard đang chạy (cần Playwright và Microsoft Edge).

## Giới hạn cần lưu ý

- Số vụ ghi nhận không phản ánh đầy đủ tội phạm thực tế. Tỷ lệ dùng dân số thường trú Census 2021 làm mẫu số cố định.
- Dữ liệu LSOA không công bố Sexual Offences; không đối chiếu tổng LSOA với tổng borough như hai phạm vi tương đương.
- Camden thiếu 24 tháng FTE từ 08/2024 đến 07/2026. KPI nhân lực chỉ cộng phần đã biết, không thay số thiếu bằng 0.
- Linear Regression có MAE 255,64 vụ/borough-tháng, kém seasonal naive (157,36) trên tập kiểm tra. Dự báo mang tính tham khảo; tương quan nhân lực và tội phạm không chứng minh quan hệ nhân quả.
