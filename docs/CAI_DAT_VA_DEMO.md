# Cài đặt và demo

## Chạy trên máy hiện tại

Mở PowerShell tại `E:\truc_quan_hoa_du_lieu\Do_An`.

```powershell
.\.venv\Scripts\python.exe run_pipeline.py
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501
```

Nếu chỉ cần xem ứng dụng, chạy lệnh Streamlit vì dữ liệu đã xử lý có sẵn. Nếu cổng 8501 bận, đổi sang 8502.

## Máy mới

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_pipeline.py
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

Giữ thư mục `data/raw` và `data/SOURCE_MANIFEST.csv`. Không chỉnh dữ liệu gốc để vượt kiểm tra hash; nếu đổi snapshot, kiểm tra và cập nhật manifest có ghi nguồn/ngày tải.

Pipeline ghi kết quả vào `data/processed/`, hình và audit vào `reports/`. Mọi đường dẫn dựa trên vị trí script nên có thể chạy từ thư mục khác. Các script dừng khi phát hiện lỗi dữ liệu có thể làm sai kết quả.

## Kịch bản demo 7–10 phút

1. Mở đề tài, giới thiệu 32 borough và dân số Census 2021 (1 phút).
2. Xem 12 tháng cuối; so sánh thứ hạng số vụ và tỷ lệ (1 phút).
3. Chọn borough trên bản đồ/bar, quan sát sidebar và biểu đồ xu hướng cập nhật (1 phút).
4. Xem treemap, chọn nhóm/phân nhóm và heatmap (1 phút).
5. Xem LSOA trong borough, nói rõ phạm vi không có Sexual Offences (1 phút).
6. Xem DWO FTE và scatter; giải thích tương quan không phải nhân quả (1 phút).
7. Xem dự báo, bảng MAE/RMSE/R² và so với baseline; trình bày trung thực kết quả kém hơn (1 phút).
8. Kết thúc bằng audit Join và insight đã kiểm chứng; tải CSV minh họa (1 phút).

## Video và báo cáo

Chưa quay video hoặc tạo báo cáo 40 trang trong lượt triển khai này. Nhóm bổ sung tên/MSSV, mẫu IEEE của giảng viên, phân công chính thức và đường dẫn video sau khi quay. Không ghi link demo giả vào báo cáo.

## Giới hạn phiên bản hiện tại

- Dự báo tổng tội phạm theo borough có metric kiểm tra; chưa có khoảng dự báo.
- Một số nhóm phân loại chỉ tồn tại trong một giai đoạn. Không suy ra bản ghi vắng mặt là 0.
- Dân số là mốc cố định 2021; nguồn lực chỉ gồm DWO.
- Nguồn thiếu FTE Camden từ 08/2024 đến 07/2026. Tổng quân số tháng có thiếu chỉ là phần quan sát được.
- Ảnh chụp và kiểm thử ứng dụng nằm trong `reports/verification/`.
