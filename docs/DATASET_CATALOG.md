# Danh mục dữ liệu đã chọn

Ngày kiểm tra và tải: 2026-09-05.

## Bộ dữ liệu cốt lõi

| ID | Tệp/bảng | Quy mô đã kiểm tra | Thời gian | Vai trò | Khóa nối |
|---|---|---:|---|---|---|
| CRIME_LSOA_HIST | `mps_lsoa_level_crime_historical_2019_03_to_2024_07.csv` | 121.222 dòng | Header thực tế: 202008-202407 | Crime chi tiết theo LSOA | `LSOA Code`, tháng |
| CRIME_LSOA_RECENT | `mps_lsoa_level_crime_recent_2024_08_to_2026_07.csv` | 106.304 dòng | 202408-202607 | Nối tiếp bảng historical | `LSOA Code`, tháng |
| CRIME_WARD_HIST | `mps_ward_level_crime_historical_2010_04_to_2024_07.csv` | 20.931 dòng | Header thực tế: 202008-202407 | Drill-down cấp ward | `WardCode`, tháng |
| CRIME_WARD_RECENT | `mps_ward_level_crime_recent_2024_08_to_2026_07.csv` | 18.806 dòng | 202408-202607 | Nối tiếp ward historical | `WardCode`, tháng |
| CRIME_BOROUGH_HIST | `mps_borough_level_crime_historical_2010_04_to_2024_07.csv` | 1.125 dòng | Header thực tế: 202008-202407 | Kiểm tra tổng và dashboard nhanh | `BOCU`, tháng |
| CRIME_BOROUGH_RECENT | `mps_borough_level_crime_recent_2024_08_to_2026_07.csv` | 991 dòng | 202408-202607 | Nối tiếp borough historical | `BOCU`, tháng |
| POPULATION | `census2021-ts001-lsoa.csv` | 35.672 dòng toàn England/Wales; 4.991 dòng khớp crime London | Census 2021 | Mẫu số tính crime rate | `geography code` = `LSOA Code` |
| LSOA_BOUNDARY | 33 shapefile theo borough | 4.994 polygon | LSOA 2021 | Choropleth map và tên borough chuẩn | `lsoa21cd` = `LSOA Code` |
| DWO_ABSTRACTION | Sheet `Sheet1` trong workbook DWO | 126.230 dòng | 2021-08 đến 2026-07 | Thời gian officer bị điều chuyển khỏi nhiệm vụ thường lệ | borough + month |
| DWO_STRENGTH | Sheet `Strengths` trong workbook DWO | 73.567 dòng | 2021-08 đến 2026-07 | Quân số FTE theo team/rank | borough + month |

Nguồn crime: https://data.london.gov.uk/dataset/mps-recorded-crime-geographic-breakdown-exy3m

Nguồn Census TS001: https://www.nomisweb.co.uk/sources/census_2021_bulk

Nguồn boundary: https://data.london.gov.uk/dataset/statistical-gis-boundary-files-for-london-20od9

Nguồn DWO: https://data.london.gov.uk/dataset/mps-dedicated-ward-officer-abstractions-and-strengths-e16kd

## Dữ liệu phụ

| Tệp/bảng | Quy mô | Mục đích phù hợp | Giới hạn |
|---|---:|---|---|
| `lsoatimings.csv` | 4.969 dòng | Bản đồ lịch sử về thời gian đi đến quầy cảnh sát | Dữ liệu năm 2013; chỉ 4.656 mã còn khớp crime hiện tại; 52 giá trị sentinel bằng 600 |
| `police_front_counter_locations_2013.csv` | 137 dòng | Bản đồ điểm quầy cảnh sát lịch sử | Không đại diện mạng lưới hiện tại |
| `police_front_counter_locations_2013.geojson` | 137 đối tượng dự kiến | Vẽ điểm trên bản đồ | Cùng giới hạn thời gian như CSV |

Nguồn front counter: https://data.london.gov.uk/dataset/police-front-counter-access-times-2g1p1

## Kết quả kiểm tra khả năng Join

| Phép nối | Kết quả |
|---|---:|
| Crime LSOA sang Census 2021 | 4.991/4.991 mã, đạt 100% |
| Crime LSOA sang boundary LSOA 2021 | 4.991/4.991 mã, đạt 100% |
| DWO ward code sang crime ward code | Chỉ 366 mã khớp; không dùng làm Join chính |
| DWO borough sang 32 borough crime | 27 tên khớp trực tiếp, 5 tên cần bảng ánh xạ |

Năm tên borough cần chuẩn hóa:

| Tên DWO | Tên chuẩn trong crime/boundary |
|---|---|
| Barking & Dagenham | Barking and Dagenham |
| Hammersmith & Fulham | Hammersmith and Fulham |
| Kensington & Chelsea | Kensington and Chelsea |
| Kingston | Kingston upon Thames |
| Richmond | Richmond upon Thames |

## Lưu ý chất lượng và phương pháp

- Các bảng crime gốc không có missing cell và không có giá trị tháng âm trong lần kiểm tra này.
- Trang nguồn ghi phạm vi historical dài hơn, nhưng header của tệp tải hiện tại bắt đầu từ `202008`. Báo cáo phải dùng phạm vi thực tế trong CSV.
- MPS cảnh báo dữ liệu sau tháng 02/2024 được lấy từ hệ thống CONNECT và một số chi tiết không ánh xạ hoàn toàn với hệ thống cũ. Tạo trường `data_regime` để đánh dấu hai giai đoạn.
- Population Census 2021 là mẫu số cố định. Vì vậy nhãn phù hợp là “crime trên 1.000 cư dân Census 2021”, không gọi đây là ước lượng dân số từng năm.
- `Aviation Policing` không phải borough địa lý. Giữ để đối soát tổng nhưng loại khỏi xếp hạng borough và mô hình theo địa bàn.

