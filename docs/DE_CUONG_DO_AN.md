# ĐỀ CƯƠNG ĐỒ ÁN CUỐI KỲ

## 1. Thông tin đề tài

**Tên đề tài:** Nghiên cứu và trực quan hóa tỷ lệ tội phạm, phân bố nguồn lực cảnh sát tại London giai đoạn 08/2020–07/2026.

**Học phần:** Trực quan hóa dữ liệu.

**Nhóm thực hiện, mã số sinh viên, giảng viên hướng dẫn:** Nhóm bổ sung thông tin trước khi nộp.

**Công cụ:** Python, Pandas, GeoPandas, Matplotlib, Seaborn, scikit-learn, Streamlit và Plotly.

**Trạng thái đề cương:** Được xây dựng trên dữ liệu đã tải và kết quả chạy pipeline, không chỉ dự kiến lựa chọn dữ liệu. Tài liệu này là đề cương triển khai, chưa phải báo cáo hoàn chỉnh 40 trang.

## 2. Lý do chọn đề tài

Tội phạm có sự khác biệt theo địa bàn, thời gian và loại hành vi. Số vụ cao tại một khu vực đông dân không đồng nghĩa tỷ lệ trên dân số cao; đồng thời, vị trí và quy mô nguồn lực cảnh sát cần được xem xét trong bối cảnh đặc điểm từng khu vực. Trực quan hóa dữ liệu theo không gian và thời gian giúp người đọc nhận diện các khác biệt này và đặt câu hỏi phân tích có căn cứ.

London có nguồn dữ liệu mở về tội phạm do Metropolitan Police Service (MPS) công bố, dữ liệu dân số Census 2021, ranh giới LSOA và dữ liệu Dedicated Ward Officers (DWO). Các nguồn có khóa địa lý và khoảng thời gian đủ để thực hiện phép nối nhiều bảng, phân tích mô tả, xây dựng dashboard và thử nghiệm hồi quy theo yêu cầu môn học [1]–[4].

## 3. Mục tiêu

### 3.1. Mục tiêu tổng quát

Xây dựng một quy trình tái lập từ dữ liệu thô đến dashboard tương tác, phục vụ phân tích phân bố tội phạm, tỷ lệ theo dân số và nguồn lực cảnh sát địa bàn tại London; đánh giá khả năng dự báo số vụ theo tháng bằng hồi quy tuyến tính.

### 3.2. Mục tiêu cụ thể

1. Thu thập, mô tả và kiểm tra ít nhất ba bảng dữ liệu có thể kết nối, bảo đảm tối thiểu 5.000 dòng thô.
2. Chuẩn hóa mã địa lý, thời gian và biến định lượng; kiểm tra missing, trùng khóa, giá trị bất hợp lệ và outlier.
3. Kết nối dữ liệu crime, Census, boundary và DWO mà không làm tăng tổng số vụ do Join sai.
4. Tính số vụ/1.000 cư dân, tăng trưởng theo tháng/cùng kỳ, tổng 12 tháng và FTE DWO/10.000 cư dân.
5. Xây dựng ít nhất năm biểu đồ tĩnh để khám phá dữ liệu trước khi thiết kế dashboard.
6. Triển khai ít nhất tám loại biểu đồ khác nhau, bản đồ, lọc nhiều cấp, drill-down, tooltip và cross-filtering.
7. Huấn luyện Linear Regression, đánh giá trên giai đoạn tương lai chưa tham gia huấn luyện và so sánh baseline.
8. Rút ra insight có căn cứ, giải thích giới hạn dữ liệu và chuẩn bị báo cáo, demo, nội dung vấn đáp.

## 4. Câu hỏi nghiên cứu

- RQ1: Số vụ và tỷ lệ tội phạm theo dân số khác nhau như thế nào giữa 32 borough?
- RQ2: Tội phạm thay đổi theo tháng, mùa và nhóm hành vi như thế nào?
- RQ3: Trong một borough, các LSOA nào có số vụ hoặc tỷ lệ cao trong kỳ quan sát?
- RQ4: Quân số DWO và tỷ lệ thời gian điều chuyển khác nhau thế nào giữa các borough?
- RQ5: Tỷ lệ tội phạm có tương quan với DWO FTE/10.000 cư dân hay không? Những yếu tố nào hạn chế diễn giải mối liên hệ này?
- RQ6: Hồi quy tuyến tính có dự báo số vụ theo tháng tốt hơn baseline lấy cùng tháng năm trước không?

## 5. Đối tượng và phạm vi

**Đối tượng:** Số vụ tội phạm được MPS ghi nhận, dân số thường trú, địa giới LSOA và quân số/hoạt động DWO.

**Không gian:** Phần phân tích chính bao gồm 32 borough thuộc MPS. City of London có lực lượng cảnh sát riêng nên không nằm trong so sánh chính. Aviation Policing và Unknown được lưu để đối soát, không đưa vào xếp hạng borough.

**Thời gian crime:** 08/2020–07/2026, theo header thực tế của CSV. Không sử dụng năm bắt đầu trong tên historical để suy ra phạm vi dữ liệu.

**Thời gian nguồn lực:** 08/2021–07/2026. Các tháng crime trước giai đoạn này không có FTE; giữ missing, không điền 0.

**Dân số:** Census 2021, mẫu số cố định. Chỉ số phải được gọi là số vụ trên 1.000 cư dân Census 2021, không coi là dân số cập nhật theo năm.

**Mức chi tiết:** Borough → LSOA; nhóm → phân nhóm. Ward và LSOA là hai hệ phân vùng khác nhau, không mặc định LSOA nằm hoàn toàn trong một ward.

**Giới hạn nội dung:** Dữ liệu front counter 2013 chỉ được lưu như nguồn lịch sử, không dùng để mô tả an ninh hiện tại. Đồ án không đo nguy cơ cá nhân, thời gian phản ứng khẩn cấp hoặc quan hệ nhân quả giữa cảnh sát và tội phạm.

## 6. Dữ liệu và nguồn

| Nguồn/bảng | Quy mô đã kiểm tra | Vai trò |
|---|---:|---|
| MPS crime LSOA: historical + recent | 121.222 + 106.304 dòng thô | Bản đồ và phân tích khu vực nhỏ |
| MPS crime borough: historical + recent | 1.125 + 991 dòng thô | Tổng số vụ và dự báo theo borough |
| MPS crime ward: historical + recent | 20.931 + 18.806 dòng thô | Nguồn phụ cho phân tích địa giới ward |
| ONS TS001 LSOA | 35.672 dòng toàn England/Wales | Dân số, nối bằng mã LSOA |
| GLA LSOA boundaries | 4.994 polygon tại London | Bản đồ và ánh xạ borough |
| DWO Strengths | 73.567 dòng | FTE theo tháng/đội/cấp bậc |
| DWO activity | 126.230 dòng | Thời gian hoạt động và điều chuyển |

Các file historical/recent là hai phần của cùng một bảng nghiệp vụ; CSV và GeoJSON chứa cùng một nguồn không được tính là hai bảng độc lập để đối phó rubric.

Nguồn và hash được lưu ở `data/SOURCE_MANIFEST.csv`. Bộ dữ liệu có nhiều hơn ba bảng nghiệp vụ độc lập: crime, population, geography, workforce và activity.

## 7. Mô hình dữ liệu và phép nối

### 7.1. Khóa và mức quan sát

| Bảng | Mức quan sát/khóa |
|---|---|
| Crime borough | borough + tháng + nhóm + phân nhóm |
| Crime LSOA | LSOA + tháng + nhóm + phân nhóm |
| Dân số | LSOA, tham chiếu năm 2021 |
| Boundary | LSOA, có mã và tên borough |
| FTE đã tổng hợp | borough + tháng |
| Activity đã tổng hợp | borough + tháng |

### 7.2. Phép nối chính

1. `LSOA Code` của crime nối `lsoa21cd` của boundary và `geography code` của Census.
2. Tổng hợp dân số theo borough từ toàn bộ LSOA thuộc borough trong boundary, không chỉ các LSOA có crime.
3. Chuẩn hóa tên borough DWO bằng bảng ánh xạ minh bạch, rồi tổng hợp từng nguồn về borough-tháng.
4. Nối bảng crime borough-tháng với FTE/activity theo khóa một-một.

Mã ward trong DWO không đủ tương thích với crime ward để dùng làm Join chính. Không phân bổ FTE borough xuống LSOA bằng một tỷ lệ tùy ý.

Kiểm thử đầy đủ phát hiện thiếu FTE Camden trong 24 tháng 08/2024–07/2026. Bảng hoạt động vẫn có những tháng này nên tỷ lệ Join khóa không phản ánh độ đầy đủ của từng biến. Giai đoạn giao nhau có 1.920 bản ghi hoạt động nhưng chỉ 1.896 bản ghi FTE. Giữ missing, công bố độ phủ theo tháng và chỉ hiển thị tổng FTE đã biết.

### 7.3. Kiểm soát chất lượng Join

Kiểm tra tính duy nhất của bảng bên phải, ghi tỷ lệ khớp và đối chiếu số dòng/tổng số vụ trước-sau. Kết quả chạy hiện tại: 4.991 mã LSOA crime đều có Census và polygon; nguồn lực khớp 1.920/1.920 borough-tháng trong giai đoạn giao nhau. Tổng 5.214.794 vụ tại 32 borough được bảo toàn sau Join.

## 8. Phương pháp và pipeline

```text
Raw snapshots + manifest
    → kiểm tra hash và schema
    → làm sạch và chuyển wide → long
    → Join và đối soát
    → chỉ số tính toán + Parquet/GeoJSON
    → EDA tĩnh + hồi quy kiểm tra theo thời gian
    → dashboard tương tác
    → insight, báo cáo, demo và vấn đáp
```

### 8.1. Tiền xử lý

- Chuẩn hóa ngày về đầu tháng và giữ mã GSS dạng chuỗi.
- Kiểm tra các cột số vụ có thể chuyển thành số nguyên không âm.
- Kiểm tra khóa thiếu, trùng và khoảng tháng chồng lấn trước khi ghép historical/recent.
- Với lỗi khóa hoặc số vụ bất hợp lệ, dừng xử lý và yêu cầu kiểm tra nguồn; không tự suy diễn giá trị.
- Với dữ liệu DWO bất hợp lệ, xuất rejected rows và dừng để tránh báo cáo thiếu quân số.
- Gắn cờ outlier theo IQR trong từng borough; giữ lại các điểm bất thường có thể là hiện tượng thực tế.
- Kiểm tra CRS, geometry và chuyển EPSG:4326 để hiển thị; simplify trên bản sao phục vụ dashboard.
- Thay 52 giá trị sentinel 600 của dữ liệu access 2013 bằng missing theo readme nguồn.

### 8.2. Công thức

| Chỉ số | Công thức | Diễn giải |
|---|---|---|
| Rate theo kỳ | tổng số vụ kỳ / dân số 2021 × 1.000 | Không tự quy đổi thành tỷ lệ năm nếu kỳ không đủ năm |
| Rolling 12-month rate | tổng 12 tháng liên tiếp / dân số 2021 × 1.000 | 11 tháng đầu không đủ dữ liệu: missing |
| MoM | (tháng hiện tại / tháng trước − 1) × 100 | Mẫu số 0: missing |
| YoY | (tháng hiện tại / cùng tháng năm trước − 1) × 100 | So sánh cùng kỳ |
| DWO FTE/10.000 | tổng FTE borough-tháng / dân số 2021 × 10.000 | DWO, không phải tổng cảnh sát London |
| Abstraction share | phút điều chuyển / tổng phút ghi nhận × 100 | Cộng phút trước, tính tỷ lệ sau |
| Abstraction hours/FTE | phút điều chuyển / 60 / FTE | Không coi là số giờ tuần tra bị mất đã được kiểm chứng |

Khi lọc nhiều borough, chỉ cộng dân số một lần cho mỗi borough. FTE trên KPI là ảnh chụp tháng cuối kỳ, không cộng quân số nhiều tháng thành số người.

### 8.3. EDA

Sáu hình tĩnh đã tạo bằng Matplotlib/Seaborn:

1. Line: xu hướng tổng số vụ và mốc CONNECT.
2. Bar: top 10 borough theo rolling 12-month rate.
3. Box plot: phân phối tỷ lệ theo nhóm tội phạm.
4. Heatmap: borough × nhóm tội phạm trong 12 tháng cuối.
5. Scatter: DWO FTE/10.000 dân và tỷ lệ crime ở tháng cuối.
6. Histogram: phân phối tỷ lệ các borough-tháng.

Mỗi hình trong báo cáo phải kèm câu hỏi, lý do chọn biểu đồ, phát hiện và giới hạn diễn giải. Nhận xét ban đầu nằm ở `reports/INSIGHTS.md`.

### 8.4. Mô hình dự báo

Mỗi borough có một Linear Regression dự báo tổng số vụ theo tháng. Biến đầu vào: chỉ số thời gian, sin/cos tháng và cờ giai đoạn CONNECT. Không sử dụng FTE tương lai chưa quan sát được.

Train: 08/2020–07/2025. Test: 08/2025–07/2026. Sau đánh giá, fit lại trên 72 tháng để dự báo 08/2026–01/2027. Không chia ngẫu nhiên và không chọn đặc trưng dựa trên kết quả test.

Đánh giá bằng MAE, RMSE, R²; baseline là cùng tháng năm trước. Dự báo âm được chặn tại 0 nhất quán trong đánh giá và hiển thị. Chưa xây dựng khoảng dự báo nên không vẽ dải tin cậy giả.

Kết quả chạy ban đầu trên từng borough-tháng của test: Linear Regression có MAE khoảng 255,64 vụ; baseline khoảng 157,36 vụ. Hồi quy hiện kém baseline. Nhóm cần trình bày kết quả thực này, thảo luận mô hình đơn giản, thay đổi hệ thống ghi nhận, mùa vụ và đặc điểm riêng từng địa bàn. Đạt rubric về thuật toán không đồng nghĩa mô hình sẵn sàng dùng cho quyết định thực tế.

## 9. Thiết kế dashboard

Dashboard dùng Streamlit + Plotly, chia sáu trang bằng tab: Tổng quan; Cơ cấu và phân phối; Nguồn lực cảnh sát; Chi tiết LSOA; Dự báo; Nguồn và chất lượng.

| Loại biểu đồ | Mục đích | Tương tác |
|---|---|---|
| Choropleth | Phân bố theo borough/LSOA | Hover; lựa chọn borough liên kết các trang |
| Line | Xu hướng tháng và dự báo | Hover; lọc phạm vi địa lý |
| Bar | So sánh thứ hạng borough | Chọn borough cập nhật bộ lọc |
| Treemap | Nhóm → phân nhóm | Drill-down phân cấp Plotly |
| Donut | Tỷ trọng các nhóm | Hover, legend |
| Heatmap | Borough × tháng | Màu thể hiện count/rate |
| Scatter | Nguồn lực và tỷ lệ tội phạm | Hover, kích thước theo dân số |
| Box plot | Phân phối và điểm cực trị | Hover |
| Histogram | Phân bố tần suất | Hover |

Có chín loại riêng biệt, không tính KPI và stacked bar như loại bổ sung. Bộ lọc chính: khoảng tháng, borough, nhóm, phân nhóm, chế độ count/rate. LSOA có lựa chọn riêng trong borough. Bản đồ/ranking toàn thành phố vẫn giữ bối cảnh để chọn địa bàn khác.

Phạm vi dự báo được ghi rõ: tổng tội phạm, theo borough đang chọn; không áp dụng lọc nhóm/phân nhóm và khoảng tháng mô tả vào mô hình đã huấn luyện. FTE không bị lọc theo loại tội phạm.

## 10. Insight và kể chuyện bằng dữ liệu

Kịch bản trình bày: bắt đầu bằng quy mô thành phố → so sánh count và rate → chọn borough nổi bật → xem nhóm tội phạm đóng góp → drill-down LSOA → đối chiếu nguồn lực DWO → đánh giá dự báo và giới hạn.

Chỉ phát biểu insight có con số và biểu đồ hỗ trợ. Phân tích nguyên nhân ở dạng giả thuyết cần kiểm chứng nếu dữ liệu hiện có chưa chứng minh được. Không kết luận “tăng cảnh sát làm tăng tội phạm” chỉ từ scatter dương.

## 11. Kiểm thử và tiêu chí nghiệm thu

- Hash nguồn khớp; đủ số dòng và ít nhất ba bảng nghiệp vụ độc lập.
- Không có khóa trùng gây many-to-many; tổng crime bảo toàn sau Join.
- Dân số dương và khớp địa bàn; thời gian thiếu DWO không bị thay 0.
- Chuỗi thời gian liên tục; rolling 12 tháng yêu cầu đủ 12 quan sát.
- Có ít nhất năm hình tĩnh và tám loại biểu đồ dashboard, trong đó có bản đồ.
- Kiểm tra bộ lọc, trạng thái rỗng, drill-down, cross-filter và tải CSV.
- Forecast có ranh giới train/test/future và bảng metric so baseline.
- Ứng dụng chạy trên máy demo; có hướng dẫn và video backup.

## 12. Cấu trúc báo cáo cuối kỳ dự kiến

| Chương | Nội dung | Số trang dự kiến |
|---|---|---:|
| 1 | Giới thiệu, bài toán và dữ liệu | 6 |
| 2 | Tiền xử lý, Join, calculated fields và EDA | 10 |
| 3 | Thiết kế dashboard, tương tác và lý do chọn biểu đồ | 9 |
| 4 | Insight và storytelling | 5 |
| 5 | Hồi quy, đánh giá và trực quan dự báo | 6 |
| 6 | Cài đặt, sử dụng và kịch bản demo | 4 |
| 7 | Kết luận, hạn chế và hướng phát triển | 2 |

Tổng dự kiến 42 trang nội dung, cộng tài liệu tham khảo và phụ lục. Dùng đánh số trích dẫn IEEE [1], [2]… và mẫu trình bày do giảng viên cung cấp; không tự coi đề cương Markdown này là báo cáo IEEE hoàn chỉnh.

## 13. Kế hoạch và phân công

| Giai đoạn | Công việc | Vai trò đề xuất | Đầu ra |
|---|---|---|---|
| Tuần 1 | Chốt phạm vi, kiểm tra nguồn và dictionary | Phụ trách dữ liệu | Catalog, audit |
| Tuần 2 | Làm sạch, Join, calculated fields, kiểm thử | Phụ trách pipeline | Code + Parquet |
| Tuần 3 | EDA và câu hỏi storytelling | Phụ trách phân tích | Notebook + hình |
| Tuần 4 | Dashboard, cross-filter và UI | Phụ trách ứng dụng | App chạy được |
| Tuần 5 | Hồi quy, metric, báo cáo | Phụ trách mô hình | Forecast + chương 5 |
| Tuần 6 | Hoàn thiện báo cáo, quay demo, luyện vấn đáp | Cả nhóm | Báo cáo + video backup |

Vai trò có thể kiêm nhiệm theo số thành viên thực tế; lịch tính tương đối vì chưa có hạn nộp. Các bước dữ liệu/EDA/mô hình hiện đã có bản chạy đầu tiên, nhóm dùng lịch để kiểm tra và hoàn thiện.

## 14. Sản phẩm bàn giao

1. Dữ liệu thô và manifest nguồn.
2. Script tái lập và bảng dữ liệu đã xử lý.
3. Notebook EDA và sáu ảnh biểu đồ.
4. Dashboard Streamlit + Plotly có hướng dẫn chạy.
5. Forecast, metric và insight có bằng chứng.
6. Đề cương này; báo cáo cuối kỳ tối thiểu 40 trang sẽ được nhóm phát triển tiếp.
7. Video demo và bản backup do nhóm quay sau khi thống nhất nội dung thuyết trình.

## 15. Câu hỏi chuẩn bị vấn đáp

1. Vì sao không dùng số vụ thay cho tỷ lệ? Vì sao dân số không được cộng lặp sau Join?
2. Vì sao tên file lịch sử khác phạm vi tháng thực tế?
3. Vì sao chọn borough-tháng để nối nguồn lực, không dùng ward code?
4. Vì sao FTE không phải headcount và không phải tổng số cảnh sát thành phố?
5. Vì sao tổng LSOA có thể khác tổng borough?
6. Missing và 0 khác nhau thế nào? Vì sao giữ outlier?
7. Vì sao train/test phải theo thời gian? Baseline có vai trò gì?
8. Vì sao R² có thể âm? Làm gì khi mô hình kém baseline?
9. Cross-filter khác lọc độc lập thế nào? Drill-down nào đã được triển khai?
10. Dữ liệu này hỗ trợ kết luận nào và chưa hỗ trợ kết luận nhân quả nào?

## Tài liệu tham khảo

[1] Metropolitan Police Service, “MPS Recorded Crime: Geographic Breakdown,” London Datastore. https://data.london.gov.uk/dataset/mps-recorded-crime-geographic-breakdown-exy3m. Truy cập: 10/09/2026.

[2] Office for National Statistics, “Census 2021 Bulk Data Download, TS001,” Nomis. https://www.nomisweb.co.uk/sources/census_2021_bulk. Tệp đã tải: 05/09/2026.

[3] Greater London Authority, “Statistical GIS Boundary Files for London.” https://data.london.gov.uk/dataset/statistical-gis-boundary-files-for-london-20od9. Tệp đã tải: 04/09/2026.

[4] Metropolitan Police Service, “MPS Dedicated Ward Officer Abstractions and Strengths.” https://data.london.gov.uk/dataset/mps-dedicated-ward-officer-abstractions-and-strengths-e16kd. Tệp đã tải: 05/09/2026.

[5] London Assembly, “Police Front Counter Access Times.” https://data.london.gov.uk/dataset/police-front-counter-access-times-2g1p1. Dữ liệu lịch sử năm 2013, lưu tham khảo.
