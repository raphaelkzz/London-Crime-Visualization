# Data dictionary

## Tên trường trong phiên bản thực thi

| Bảng/tệp | Trường | Định nghĩa thực tế |
|---|---|---|
| `crime_borough.parquet` | `crime_count` | Số vụ theo borough-tháng-nhóm-phân nhóm |
| `crime_borough.parquet`, `monthly.parquet` | `rate_per_1000` | Số vụ tháng / dân số Census 2021 × 1.000 |
| `monthly.parquet` | `rolling_12_count`, `rolling_12_rate` | Tổng/tỷ lệ 12 tháng đầy đủ; 11 tháng đầu missing |
| `monthly.parquet` | `mom_pct`, `yoy_pct` | Phần trăm thay đổi tháng trước/cùng kỳ; mẫu số 0 → missing |
| `monthly.parquet` | `outlier_iqr` | Cờ ngoài Q1−1,5 IQR hoặc Q3+1,5 IQR theo borough; giữ quan sát |
| `monthly.parquet` | `is_hotspot` | Tỷ lệ >= phân vị 75 của borough trong cùng tháng, chỉ là nhãn tương đối |
| `security_borough.parquet` | `officer_fte` | FTE DWO gồm Constable và PCSO tại tháng đó; không phải tất cả cảnh sát |
| `security_borough.parquet` | `minutes`, `abstracted_minutes` | Tổng phút ghi nhận/tổng phút có Abstracted From Duty = Yes |
| `security_borough.parquet` | `officers_per_10000` | FTE DWO / dân số Census 2021 × 10.000 |
| `security_borough.parquet` | `abstraction_share_pct` | abstracted_minutes / minutes × 100 |
| `security_borough.parquet` | `abstraction_hours`, `abstraction_hours_per_fte` | Phút điều chuyển / 60 và giờ / FTE |
| `forecast.parquet` | `actual`, `predicted`, `baseline`, `split` | Quan sát; dự đoán test/forecast; cùng tháng năm trước; train/test/forecast |

FTE Camden thiếu 08/2024–07/2026 được giữ missing. Các bảng dân số là bảng dimension; không cộng lặp dân số theo các dòng crime. Các mục dưới đây mô tả schema nguồn và tên chuẩn hóa đề xuất ban đầu; bảng trên ghi tên cột thực tế để viết code.

## Crime geographic breakdown

| Trường gốc | Tên chuẩn hóa | Kiểu | Ý nghĩa |
|---|---|---|---|
| `LSOA Code` | `lsoa_code` | string | Mã GSS của LSOA |
| `LSOA Name` | `lsoa_name` | string | Tên LSOA |
| `Borough` trong bảng LSOA | `borough_code` | string | Mã GSS borough, dù tên cột gốc là Borough |
| `WardCode` | `ward_code` | string | Mã GSS ward |
| `WardName` | `ward_name` | string | Tên ward |
| `LookUp_BoroughName` | `borough_name` | string | Tên borough tra cứu từ ward |
| `BOCU` | `borough_name_raw` | string | Tên borough hoặc đơn vị như Aviation Policing |
| `Group` | `crime_group` | category | Nhóm tội phạm cấp cao |
| `SubGroup` | `crime_subgroup` | category | Nhóm tội phạm chi tiết |
| Cột `YYYYMM` | `month`, `crime_count` | date, integer | Tháng và số vụ sau unpivot |

## Census 2021 TS001

| Trường gốc | Tên chuẩn hóa | Kiểu | Ý nghĩa |
|---|---|---|---|
| `date` | `census_year` | integer | Năm Census, bằng 2021 |
| `geography` | `lsoa_name_census` | string | Tên LSOA trong Census |
| `geography code` | `lsoa_code` | string | Khóa nối với crime và boundary |
| `Residence type: Total; measures: Value` | `population_2021` | integer | Tổng cư dân thường trú |
| `Residence type: Lives in a household; measures: Value` | `household_population_2021` | integer | Cư dân sống trong hộ gia đình |
| `Residence type: Lives in a communal establishment; measures: Value` | `communal_population_2021` | integer | Cư dân sống trong cơ sở cộng đồng |

## LSOA boundary 2021

| Trường gốc | Tên chuẩn hóa | Kiểu | Ý nghĩa |
|---|---|---|---|
| `lsoa21cd` | `lsoa_code` | string | Mã LSOA 2021 |
| `lsoa21nm` | `lsoa_name_boundary` | string | Tên LSOA 2021 |
| `msoa21cd` | `msoa_code` | string | Mã MSOA 2021 |
| `msoa21nm` | `msoa_name` | string | Tên MSOA 2021 |
| `lad22cd` | `borough_code` | string | Mã local authority/borough |
| `lad22nm` | `borough_name` | string | Tên borough chuẩn |
| `geometry` | `geometry` | geometry | Polygon hoặc MultiPolygon |

## Dedicated Ward Officer data

### Sheet `Sheet1`

| Trường gốc | Tên chuẩn hóa | Kiểu | Ý nghĩa |
|---|---|---|---|
| `Month of Abstraction` | `month` | date | Tháng ghi nhận hoạt động |
| `BCU` | `bcu` | string | Basic Command Unit |
| `Borough` | `borough_name_raw` | string | Tên borough có hậu tố Borough |
| `Team` | `team_name` | string | Tên đội/ward team |
| `Abstracted From Duty` | `abstracted_from_duty` | boolean/category | Có bị điều chuyển khỏi nhiệm vụ thường lệ hay không |
| `Abstracted Type` | `abstraction_type` | category | Loại hoạt động điều chuyển |
| `Abstraction Minutes` | `abstraction_minutes` | number | Tổng phút hoạt động |
| `Ward_Code` | `ward_code_raw` | string | Mã ward do MPS cung cấp; không dùng làm khóa Join chính |

### Sheet `Strengths`

| Trường gốc | Tên chuẩn hóa | Kiểu | Ý nghĩa |
|---|---|---|---|
| `Date` | `month` | date | Ngày cuối tháng |
| `Buisness Group` | `business_group` | string | Nhóm nghiệp vụ; cột gốc viết sai chính tả |
| `OCU` | `bcu` | string | Đơn vị chỉ huy |
| `Department` | `borough_name_raw` | string | Borough/department |
| `Team` | `team_name` | string | Đội công tác |
| `Rank` | `rank` | category | Constable hoặc PCSO và các cấp có trong nguồn |
| `FTE` | `officer_fte` | number | Quân số quy đổi toàn thời gian |

## Front counter access 2013, dữ liệu phụ

| Trường gốc | Tên chuẩn hóa | Kiểu | Ý nghĩa |
|---|---|---|---|
| `lsoa` | `lsoa_code_2011` | string | Mã LSOA theo phiên bản cũ |
| `pre12` | `travel_min_pre_midday` | number | Phút đến quầy gần nhất lúc 12h trước thay đổi |
| `pre24` | `travel_min_pre_4am` | number | Phút đến quầy gần nhất lúc 4h trước thay đổi |
| `post12` | `travel_min_post_midday` | number | Phút đến quầy gần nhất lúc 12h sau thay đổi |
| `post24` | `travel_min_post_4am` | number | Phút đến quầy gần nhất lúc 4h sau thay đổi |

Giá trị 600 ở bốn trường thời gian là sentinel lỗi theo readme nguồn và phải đổi thành missing.

## Trường tính toán

| Trường | Kiểu | Công thức/định nghĩa |
|---|---|---|
| `year` | integer | Năm từ `month` |
| `quarter` | string | Quý từ `month` |
| `data_regime` | category | `legacy` đến 2024-02, `connect` từ 2024-03 |
| `crime_rate_per_1000_month` | number | Crime tháng / population 2021 x 1.000 |
| `crime_rate_per_1000_rolling_12m` | number | Tổng crime 12 tháng / population 2021 x 1.000 |
| `mom_change_pct` | number | `(current / previous_month - 1) x 100` |
| `yoy_change_pct` | number | `(current / same_month_last_year - 1) x 100` |
| `crime_share_pct` | number | Crime group / tổng crime cùng vùng-tháng x 100 |
| `is_hotspot` | boolean | Rate >= percentile 75 trong cùng tháng |
| `officers_per_10000` | number | FTE / borough population 2021 x 10.000 |
| `abstraction_hours` | number | Abstraction minutes / 60 |
| `abstraction_share_pct` | number | Abstracted minutes / tổng recorded minutes x 100 |
| `abstraction_hours_per_fte` | number | Abstraction hours / FTE |
| `predicted_crime` | number | Kết quả Linear Regression trên tập test |
| `forecast_crime` | number | Dự báo 6 tháng sau kỳ dữ liệu cuối |
