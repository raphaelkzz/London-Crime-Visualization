# Pipeline triển khai đồ án

## Phiên bản thực thi ngày 10/09/2026

Lệnh chạy: `python run_pipeline.py`. Các bước đã triển khai thực tế:

1. `src/preprocess.py`: kiểm tra hash, schema, missing, khóa trùng; unpivot; nối Census/boundary; tổng hợp và nối DWO; chỉ số; xuất Parquet/GeoJSON và `reports/data_quality.json`.
2. `src/eda.py`: sáu hình Matplotlib/Seaborn và `reports/INSIGHTS.md`.
3. `src/model.py`: một Linear Regression cho mỗi borough, test 12 tháng, forecast 6 tháng và baseline cùng tháng năm trước.
4. `dashboard/app.py`: dashboard Streamlit + Plotly; khởi động riêng bằng lệnh Streamlit.

Tệp đầu ra chính: `dim_date.parquet`, `dim_lsoa.parquet`, `dim_borough.parquet`, `crime_borough.parquet`, `crime_ward.parquet`, `lsoa_<borough_code>.parquet`, `monthly.parquet`, `security_borough.parquet`, `security_by_rank.parquet`, `forecast.parquet`, `forecast.csv`, `boroughs.geojson`, `lsoa.geojson`.

Điều chỉnh có căn cứ so với thiết kế ban đầu:

- Phân tích chính là 32 borough MPS. LSOA loại trừ Sexual Offences theo chính sách nguồn; tổng LSOA không mặc định bằng borough.
- Dân số borough cộng từ toàn bộ LSOA của borough trong Census/boundary, không chỉ các mã có crime.
- `monthly.parquet` chứa outlier IQR theo borough, rolling 12 tháng, MoM/YoY và hotspot phân vị 75 theo tháng. Outlier được giữ lại.
- Workforce/activity nối đủ khóa 1.920 borough-tháng nhưng FTE chỉ có 1.896 quan sát; thiếu Camden trong 24 tháng được lưu tại `reports/missing_fte_months.csv` và hiển thị độ phủ trên dashboard.
- FTE là ảnh chụp tháng cuối; tuyệt đối không cộng FTE qua nhiều tháng thành số người. Group/subgroup không lọc FTE.
- Forecast là tổng số vụ theo borough đang chọn, có phạm vi lọc riêng được ghi trên trang dự báo. Không dùng lựa chọn nhóm/phân nhóm làm nhãn cho mô hình tổng.
- Chín loại biểu đồ khác nhau: map, line, bar, treemap, donut, heatmap, scatter, box và histogram. Stacked bar không được tính thêm thành loại thứ mười.
- Tỷ lệ kỳ đang chọn không tự annualize. Kỳ khác độ dài cần được so sánh có cân nhắc.

Nội dung bên dưới lưu thiết kế ban đầu để đối chiếu. Khi tên tệp hoặc phạm vi khác nhau, dùng phiên bản thực thi ở trên và đề cương cập nhật.

## Tổng quan

```text
Nguồn chính thức
  -> kiểm tra tệp và schema
  -> làm sạch và chuẩn hóa
  -> unpivot dữ liệu tháng
  -> Join crime + population + boundary + DWO
  -> tạo calculated fields
  -> EDA tĩnh
  -> huấn luyện Linear Regression
  -> xuất bảng tối ưu
  -> Streamlit + Plotly dashboard
  -> kiểm thử, báo cáo và video demo
```

## Bước 1. Thu thập và đóng băng dữ liệu thô

Đầu vào nằm trong `data/raw`. Không sửa trực tiếp các tệp này.

Việc cần làm trong script `src/00_validate_raw.py`:

1. Kiểm tra tệp tồn tại, kích thước và SHA-256 theo `data/SOURCE_MANIFEST.csv`.
2. Ghi lại số dòng, tên cột, kiểu dữ liệu và phạm vi tháng.
3. Kiểm tra khóa địa lý rỗng/trùng và giá trị crime âm.
4. Dừng pipeline nếu thiếu một bảng cốt lõi hoặc tỷ lệ Join LSOA thấp hơn 99%.
5. Lưu kết quả kiểm tra thành `reports/data_quality_raw.json`.

## Bước 2. Làm sạch và chuẩn hóa

Thực hiện trong `src/01_preprocess.py`.

### Crime

1. Đổi tên cột sang snake_case.
2. Đổi `Borough` trong bảng LSOA thành `borough_code` vì giá trị thực tế là mã GSS.
3. Unpivot các cột `YYYYMM` thành `month` và `crime_count`.
4. Chuyển `month` sang ngày đầu tháng, tạo `year`, `quarter`, `month_number`.
5. Nối historical và recent; kiểm tra không chồng tháng và không trùng khóa.
6. Chuẩn hóa `crime_group` và `crime_subgroup` bằng trim, viết hoa/thường nhất quán.
7. Giữ giá trị 0 vì đây là số vụ hợp lệ, không thay bằng missing.
8. Loại `Aviation Policing` khỏi bảng phân tích địa lý nhưng giữ trong bảng đối soát.
9. Tạo `data_regime`: `legacy` đến 2024-02 và `connect` từ 2024-03.

Khóa kỳ vọng sau aggregate:

```text
lsoa_code + month + crime_group
ward_code + month + crime_group
borough_name + month + crime_group
```

### Population và boundary

1. Chỉ giữ 4.991 LSOA xuất hiện trong crime.
2. Đổi `geography code` thành `lsoa_code` và trường total thành `population_2021`.
3. Gộp 33 shapefile thành một GeoDataFrame.
4. Giữ `lsoa21cd`, `lsoa21nm`, `lad22cd`, `lad22nm`, `geometry`.
5. Chuyển CRS sang EPSG:4326 để Plotly hiển thị đúng.
6. Simplify geometry trên bản sao dùng cho dashboard, không thay tệp boundary gốc.

### DWO workforce

1. Đọc cả hai sheet `Sheet1` và `Strengths`.
2. Sửa tên cột `Buisness Group` thành `business_group`.
3. Chuẩn hóa date về tháng.
4. Bỏ hậu tố ` Borough` và áp dụng bảng ánh xạ 5 tên trong `DATASET_CATALOG.md`.
5. Aggregate về `borough_name + month` trước khi Join với crime.
6. Không Join chính theo ward code vì thay đổi biên giới làm tỷ lệ khớp thấp.

### Missing và outlier

- Khóa địa lý hoặc tháng bị thiếu: loại khỏi fact table và ghi vào bảng rejected rows.
- Missing crime count: không tự động đổi thành 0; đối chiếu nguồn trước, nếu không xác minh được thì loại và ghi log.
- Missing population hoặc geometry: dừng pipeline vì làm sai tỷ lệ/map.
- Crime outlier: gắn cờ theo IQR trong từng `borough + crime_group`; giữ lại trừ khi xác nhận là lỗi nhập liệu.
- FTE âm hoặc abstraction minutes âm: coi là lỗi và đưa vào rejected rows.
- Giá trị travel time bằng 600: đổi thành `NaN` vì tài liệu nguồn định nghĩa đây là sentinel lỗi.

## Bước 3. Join và mô hình dữ liệu

Tạo mô hình sao để dashboard chạy nhanh:

| Bảng đầu ra | Grain | Nội dung |
|---|---|---|
| `dim_date.parquet` | 1 dòng/tháng | Năm, quý, tháng, nhãn hiển thị, time index |
| `dim_lsoa.parquet` | 1 dòng/LSOA | Tên LSOA, borough, population 2021 |
| `dim_lsoa.geojson` | 1 feature/LSOA | Geometry đã simplify cho map |
| `fact_crime_lsoa_month.parquet` | LSOA + tháng + group | Crime count và rate |
| `fact_crime_borough_month.parquet` | Borough + tháng + group | Bảng tổng hợp cho biểu đồ nhanh |
| `fact_security_borough_month.parquet` | Borough + tháng | FTE, abstraction minutes và chỉ số nguồn lực |
| `model_forecast.csv` | Borough + tháng | Actual, predicted, forecast và split |

Các Join bắt buộc:

```text
crime.lsoa_code = population.lsoa_code
crime.lsoa_code = boundary.lsoa21cd
crime.borough_name + crime.month = security.borough_name + security.month
```

Sau mỗi Join phải kiểm tra:

1. Số dòng trước/sau.
2. Tỷ lệ khóa khớp.
3. Tổng `crime_count` trước/sau không đổi.
4. Không phát sinh many-to-many ngoài dự kiến.

## Bước 4. Calculated fields

| Trường | Công thức/ý nghĩa |
|---|---|
| `crime_rate_per_1000_month` | `crime_count / population_2021 * 1000` |
| `crime_rolling_12m` | Tổng crime 12 tháng gần nhất theo vùng |
| `crime_rate_per_1000_rolling_12m` | `crime_rolling_12m / population_2021 * 1000` |
| `mom_change_pct` | Thay đổi so với tháng trước |
| `yoy_change_pct` | Thay đổi so với cùng tháng năm trước |
| `crime_share_pct` | Tỷ trọng group/subgroup trong tổng vùng-tháng |
| `is_hotspot` | Rate từ percentile 75 trở lên trong cùng tháng |
| `officer_fte` | Tổng FTE Constable và PCSO theo borough-tháng |
| `officers_per_10000` | `officer_fte / borough_population_2021 * 10000` |
| `abstraction_hours` | `abstraction_minutes / 60` |
| `abstraction_share_pct` | Abstracted minutes / tổng recorded minutes |
| `abstraction_hours_per_fte` | `abstraction_hours / officer_fte` |

Không chia phần trăm khi mẫu số bằng 0. Giữ `NaN` và hiển thị “Không đủ dữ liệu”.

## Bước 5. EDA bằng Matplotlib/Seaborn

Notebook đề xuất: `notebooks/02_eda_london_crime.ipynb`.

Tối thiểu 5 biểu đồ tĩnh:

1. Line chart tổng crime theo tháng, có đánh dấu mốc CONNECT.
2. Horizontal bar top 10 borough theo rolling 12-month rate trên 1.000 dân.
3. Box plot phân phối crime rate theo nhóm tội phạm.
4. Heatmap borough x crime group.
5. Scatter plot officers per 10.000 dân so với crime rate, tô màu theo thời gian hoặc borough.

Mỗi biểu đồ cần có câu hỏi, nhận xét chính, giới hạn diễn giải và ảnh PNG để dùng trong báo cáo.

## Bước 6. Mô hình Linear Regression

Mục tiêu: dự báo tổng crime theo `borough + month` trong 6 tháng tiếp theo.

Feature cơ sở:

- `time_index`
- `month_sin`, `month_cos` để biểu diễn mùa vụ
- one-hot `borough_name`
- có thể thêm one-hot `data_regime`, nhưng phải giải thích đây là thay đổi hệ thống ghi nhận

Không dùng FTE tương lai nếu chưa có giá trị dự báo cho FTE.

Chia dữ liệu theo thời gian:

- Train: 2020-08 đến 2025-07
- Test: 2025-08 đến 2026-07
- Forecast: 2026-08 đến 2027-01

Đánh giá bằng MAE, RMSE và R². So sánh thêm baseline “bằng cùng tháng năm trước”. Nếu Linear Regression kém baseline, vẫn trình bày trung thực và nêu đây là mô hình theo yêu cầu môn học.

## Bước 7. Dashboard Streamlit + Plotly

Filters nhiều cấp:

- Date range
- Borough
- LSOA/ward
- Crime group
- Crime subgroup
- Chế độ Count / Rate

Drill-down:

- London -> Borough -> LSOA
- Crime group -> Crime subgroup

Chín loại biểu đồ đề xuất để có dư địa so với yêu cầu 8 loại:

1. Choropleth map LSOA.
2. Line chart actual + predicted + forecast.
3. Horizontal bar ranking borough.
4. Stacked bar cơ cấu crime group.
5. Treemap group -> subgroup.
6. Heatmap borough x month.
7. Scatter officers per 10.000 vs crime rate.
8. Box plot phân phối crime rate.
9. Donut chart tỷ trọng nhóm crime cho vùng đang chọn.

KPI ở đầu trang: total crime, rolling 12-month rate, YoY change, hotspot count và officer FTE. KPI không tính vào 8 loại biểu đồ.

Cross-filtering: khi chọn borough trên map/bar, lưu selection vào `st.session_state` và cập nhật các biểu đồ còn lại. Tooltip phải hiển thị count, rate, population, MoM/YoY và security metrics phù hợp.

## Bước 8. Kiểm thử và bàn giao

Điều kiện hoàn thành:

1. Pipeline chạy lại từ `data/raw` mà không sửa tay dữ liệu.
2. Báo cáo chất lượng chứng minh Join LSOA đạt 100% với bộ dữ liệu hiện tại.
3. EDA có ít nhất 5 biểu đồ tĩnh.
4. Dashboard có ít nhất 8 loại biểu đồ thật sự khác nhau, map, filter, drill-down, tooltip và cross-filter.
5. Forecast hiển thị actual, predicted và future forecast, kèm metric.
6. Báo cáo tối thiểu 40 trang theo rubric.
7. Video có bản backup và mỗi thành viên trình bày được phần code của mình.
