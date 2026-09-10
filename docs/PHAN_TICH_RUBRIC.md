# Phân tích rubric và tiêu chí nghiệm thu

## Kết luận

Bộ dữ liệu London đã chọn đáp ứng điều kiện đầu vào của rubric. Để đạt điểm tốt, nhóm không nên dừng ở việc vẽ biểu đồ; cần chứng minh được dữ liệu nối đúng, giải thích cách tạo tỷ lệ, đánh giá mô hình trên tập kiểm tra theo thời gian và triển khai tương tác thật trên dashboard.

## Đối chiếu rubric

| Tiêu chí | Cách đáp ứng | Bằng chứng/đầu ra cần nộp |
|---|---|---|
| Tối thiểu 5.000 dòng | Crime LSOA có 227.526 dòng; dữ liệu DWO có tổng 199.797 dòng trong 2 sheet | Bảng thống kê số dòng trước và sau xử lý |
| Tối thiểu 3 bảng | Crime, Census population, LSOA boundary, DWO workforce; front counter là bảng phụ | Sơ đồ mô hình dữ liệu và log Join |
| Nguồn và link cụ thể | London Datastore, MPS và Nomis/ONS | `SOURCE_MANIFEST.csv`, trang nguồn lưu trong `docs/source_pages` |
| Data dictionary | Mô tả trường gốc, trường chuẩn hóa và trường tính toán | `DATA_DICTIONARY.md` |
| Missing value | Kiểm tra khóa, giá trị số và geometry; quy tắc xử lý riêng theo trường | Báo cáo chất lượng dữ liệu trước/sau |
| Outlier | Gắn cờ IQR cho phân tích; không xóa đỉnh crime chỉ vì giá trị lớn | Bảng số điểm bị gắn cờ và lý do giữ/xử lý |
| Chuẩn hóa | Unpivot tháng, chuẩn hóa ngày, tên borough, kiểu dữ liệu và mã địa lý | Script Python tái lập được |
| Join/Merge | LSOA crime + Census + boundary; borough-month crime + DWO | Tỷ lệ khớp khóa và kiểm tra tổng trước/sau Join |
| Calculated fields | Crime rate, rolling 12 tháng, MoM, YoY, officer density, abstraction share | Công thức trong code và data dictionary |
| EDA | Tối thiểu 5 biểu đồ tĩnh Matplotlib/Seaborn | Notebook và ảnh PNG |
| Dashboard | Streamlit + Plotly, ít nhất 8 loại biểu đồ, map, filter, drill-down, tooltip, cross-filter | Ứng dụng chạy trực tiếp và video demo |
| Hồi quy | Linear Regression theo chuỗi thời gian có biến mùa vụ | MAE, RMSE, R² và biểu đồ actual/predicted/forecast |
| Báo cáo | Tối thiểu 40 trang theo cấu trúc rubric | Báo cáo IEEE, tài liệu tham khảo và link video |
| Vấn đáp | Mỗi thành viên hiểu code, Join, công thức tỷ lệ và giới hạn dữ liệu | Chia phần thuyết trình và bộ câu hỏi phản biện |

## Các điểm dễ mất điểm

1. Gọi số vụ là “tỷ lệ tội phạm” mà không chia cho dân số.
2. Xóa các tháng crime tăng mạnh như outlier mà không kiểm tra nguyên nhân.
3. Trộn dữ liệu trước và sau tháng 02/2024 mà không nhắc thay đổi hệ thống CONNECT của MPS.
4. Join DWO với crime bằng mã ward mà không xử lý thay đổi ranh giới. Kiểm tra thực tế chỉ khớp 366 mã ward.
5. Dùng dữ liệu front counter năm 2013 để kết luận về an ninh hiện tại.
6. Chia train/test ngẫu nhiên cho dữ liệu thời gian, gây rò rỉ dữ liệu tương lai.
7. Đếm KPI card hoặc nhiều biến thể bar chart như các “loại biểu đồ khác nhau”.
8. Dashboard có bộ lọc nhưng không có drill-down hoặc liên kết lựa chọn giữa các biểu đồ.

## Phạm vi phân tích được khuyến nghị

Tên đề tài: “Phân tích không gian, xu hướng tội phạm và phân bố nguồn lực cảnh sát tại London giai đoạn 08/2020-07/2026”.

Câu hỏi nghiên cứu:

1. Tội phạm phân bố như thế nào giữa các LSOA và borough khi đã chuẩn hóa theo dân số?
2. Nhóm tội phạm nào đóng góp nhiều nhất và thay đổi theo mùa ra sao?
3. Các hotspot có bền vững theo thời gian hay chỉ xuất hiện ở một số tháng?
4. Nguồn lực Dedicated Ward Officers phân bố ra sao theo borough và thời gian?
5. Mối liên hệ giữa mức crime và nguồn lực cảnh sát là gì? Chỉ diễn giải là tương quan, không kết luận nhân quả.
6. Linear Regression dự báo xu hướng crime 6 tháng tiếp theo tốt đến mức nào?

