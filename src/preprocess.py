"""Bước 1 của pipeline: kiểm tra dữ liệu thô và tạo các bảng phân tích.

Luồng xử lý:

    1. validate_sources       kiểm tra SHA-256 của mọi tệp trong SOURCE_MANIFEST.csv
    2. load_geography         ranh giới LSOA + dân số Census 2021 → dim_lsoa, dim_borough, GeoJSON
    3. reshape_crime          6 CSV tội phạm wide → long, kiểm tra join LSOA, lưu theo borough
    4. build_borough_facts    phạm vi 32 borough MPS, join dân số, rate_per_1000
    5. build_monthly          bảng borough × tháng + calculated fields + cờ outlier/hotspot
    6. build_security         FTE và abstraction của ward officer
    7. join_monthly_security  join tội phạm ⨝ nhân lực, kiểm tra khoảng thời gian chung
    8. build_access_2013      thời gian tới quầy tiếp dân 2013 (giữ riêng, không trộn)

Nguyên tắc:
"""
import hashlib
import re

import geopandas as gpd
import numpy as np
import pandas as pd

from common import ROOT, RAW, OUT, REPORTS, borough_names, ratio, save_json, temporal_fields

# Tham số
MONTH_COLUMN = re.compile(r'20\d{4}')          # cột tháng dạng YYYYMM
EXCLUDED_BOROUGH = 'City of London'            # có lực lượng cảnh sát riêng, ngoài phạm vi MPS
BRITISH_NATIONAL_GRID = 27700                  # CRS tính bằng mét, dùng để đơn giản hoá hình
WGS84 = 4326                                   # CRS cho bản đồ web
BOROUGH_SIMPLIFY_M = 30
LSOA_SIMPLIFY_M = 20
ROLLING_MONTHS = 12
OUTLIER_IQR_K = 1.5
HOTSPOT_QUANTILE = .75
TRAVEL_PLACEHOLDER = 600                       # phút; giá trị giữ chỗ trong dữ liệu 2013

CRIME_RENAME = {
    'Group': 'crime_group', 'SubGroup': 'crime_subgroup', 'BOCU': 'borough_name',
    'LSOA Code': 'lsoa_code', 'LSOA Name': 'lsoa_name_raw', 'Borough': 'borough_code',
    'WardCode': 'ward_code', 'WardName': 'ward_name', 'LookUp_BoroughName': 'borough_name',
}
BOUNDARY_RENAME = {
    'lsoa21cd': 'lsoa_code', 'lsoa21nm': 'lsoa_name', 'lad22cd': 'borough_code', 'lad22nm': 'borough_name',
}
CENSUS_RENAME = {
    'geography code': 'lsoa_code', 'Residence type: Total; measures: Value': 'population_2021',
}
SECURITY_BOOK = RAW / 'security' / 'MPS_Dedicated_Ward_Officer_Abstractions_and_Strengths.xlsx'
TRAVEL_FILE = RAW / 'security' / 'lsoa_police_front_counter_travel_times_2013' / 'lsoatimings.csv'
TRAVEL_COLUMNS = ['pre12', 'pre24', 'post12', 'post24']


def log(message):
    print(message, flush=True)


# Hàm kiểm tra dùng chung
def sha256(path):
    """SHA-256 của một tệp, đọc theo khối để không giữ cả tệp trong bộ nhớ."""
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def unpivot(frame, identifiers):
    """Chuyển bảng wide (mỗi tháng một cột) sang long, kiểm tra chặt số vụ và khoá.
    Dừng nếu: không có cột tháng; ô thiếu, không phải số, âm hoặc không nguyên; khoá thiếu hoặc trùng.
    """
    months = [c for c in frame if MONTH_COLUMN.fullmatch(c)]
    if not months:
        raise ValueError('No monthly columns found')
    values = frame[months].apply(pd.to_numeric, errors='coerce')
    if values.isna().any().any() or (values < 0).any().any():
        raise ValueError('Missing, non-numeric or negative crime count; inspect source')
    if not np.equal(values, np.floor(values)).all().all():
        raise ValueError('Crime counts must be integers')

    frame = frame.copy()
    frame[months] = values
    for column in identifiers:
        frame[column] = frame[column].astype('string').str.strip()
    if frame[identifiers].isna().any().any():
        raise ValueError('Missing crime key')
    if frame.duplicated(identifiers).any():
        raise ValueError('Duplicate raw crime key; resolve before aggregation')

    long = frame.melt(id_vars=identifiers, value_vars=months, var_name='month', value_name='crime_count')
    long['month'] = pd.to_datetime(long.month, format='%Y%m')
    long['crime_count'] = long.crime_count.astype('int32')
    assert long.crime_count.sum() == values.to_numpy().sum()
    return long


def iqr_outlier(series):
    """True nếu giá trị nằm ngoài [Q1 − k·IQR, Q3 + k·IQR] của chính chuỗi đó."""
    q1, q3 = series.quantile(.25), series.quantile(.75)
    spread = OUTLIER_IQR_K * (q3 - q1)
    return (series < q1 - spread) | (series > q3 + spread)


# 1. Nguồn
def validate_sources():
    """So SHA-256 từng tệp với manifest; lệch là dừng."""
    manifest = pd.read_csv(ROOT / 'data' / 'SOURCE_MANIFEST.csv')
    entries = []
    for row in manifest.itertuples():
        path = ROOT / row.relative_path
        digest = sha256(path)
        if digest.upper() != row.sha256.upper():
            raise ValueError(f'Source hash mismatch: {path.name}')
        entries.append({'dataset': row.dataset_id, 'bytes': path.stat().st_size, 'sha256': digest})
    return entries


# 2. Địa lý + dân số
def load_geography(quality):
    """Đọc 33 shapefile LSOA, join Census 2021; lưu dim_lsoa, dim_borough và hai GeoJSON."""
    log('Reading census and 33 boundary files...')
    shapefiles = sorted((RAW / 'boundaries' / 'LB_LSOA2021_shp' / 'LB_shp').glob('*.shp'))
    parts = [gpd.read_file(p) for p in shapefiles]
    if not parts or any(p.crs != parts[0].crs for p in parts):
        raise ValueError('Missing or inconsistent boundary CRS')
    geo = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
    geo = geo.rename(columns=BOUNDARY_RENAME)[['lsoa_code', 'lsoa_name', 'borough_code', 'borough_name', 'geometry']]
    if geo.lsoa_code.duplicated().any() or geo.geometry.is_empty.any() or geo.geometry.isna().any():
        raise ValueError('Invalid boundary keys or empty geometry')
    quality['invalid_geometries_before'] = int((~geo.is_valid).sum())
    geo.geometry = geo.geometry.make_valid()

    census_file = RAW / 'population' / 'census2021-ts001' / 'census2021-ts001-lsoa.csv'
    census = pd.read_csv(census_file).rename(columns=CENSUS_RENAME)[['lsoa_code', 'population_2021']]
    dim = geo.drop(columns='geometry').merge(census, on='lsoa_code', how='left', validate='one_to_one')
    if dim.population_2021.isna().any() or (dim.population_2021 <= 0).any():
        raise ValueError('Missing/nonpositive population')
    dim.to_parquet(OUT / 'dim_lsoa.parquet', index=False)

    borough = dim.groupby(['borough_code', 'borough_name'], as_index=False).population_2021.sum()
    borough = borough[borough.borough_name != EXCLUDED_BOROUGH].copy()
    borough.to_parquet(OUT / 'dim_borough.parquet', index=False)

    geo = geo.to_crs(BRITISH_NATIONAL_GRID)
    borough_geo = geo.dissolve(by='borough_name', as_index=False)[['borough_name', 'geometry']]
    borough_geo.geometry = borough_geo.simplify(BOROUGH_SIMPLIFY_M, preserve_topology=True)
    borough_geo.to_crs(WGS84).to_file(OUT / 'boroughs.geojson', driver='GeoJSON')
    geo.geometry = geo.simplify(LSOA_SIMPLIFY_M, preserve_topology=True)
    geo.to_crs(WGS84).to_file(OUT / 'lsoa.geojson', driver='GeoJSON')
    return dim, borough


# 3. Tội phạm wide → long
def save_lsoa_by_borough(lsoa_parts):
    """Ghép hai đoạn LSOA theo từng borough, kiểm tra chồng lấn, lưu lsoa_<mã>.parquet."""
    for code, parts in lsoa_parts.items():
        long = pd.concat(parts, ignore_index=True)
        if long.duplicated(['lsoa_code', 'crime_group', 'crime_subgroup', 'month']).any():
            raise ValueError('Overlapping LSOA snapshots')
        for column in ['lsoa_code', 'borough_code', 'crime_group', 'crime_subgroup']:
            long[column] = long[column].astype('category')
        long.to_parquet(OUT / f'lsoa_{code}.parquet', index=False)


def reshape_crime(dim, quality):
    """Đọc 6 CSV (borough / ward / LSOA × lịch sử / gần đây), chuyển long và trả về các đoạn."""
    log('Reshaping crime snapshots and checking joins...')
    borough_parts, ward_parts, lsoa_parts, all_dates = [], [], {}, set()
    lsoa_codes_recent = 0
    for level in ['borough', 'ward', 'lsoa']:
        for path in sorted((RAW / 'crime').glob(f'mps_{level}_*.csv')):
            wide = pd.read_csv(path).rename(columns=CRIME_RENAME)
            ids = [c for c in wide if not MONTH_COLUMN.fullmatch(c)]
            entry = {'file': path.name, 'rows': len(wide), 'missing_cells': int(wide.isna().sum().sum())}
            quality['raw_crime'].append(entry)

            if level == 'lsoa':
                matched = wide.lsoa_code.isin(dim.lsoa_code)
                if not matched.all():
                    raise ValueError('Crime LSOA missing from census/boundary')
                entry['matched_rows'] = int(matched.sum())
                if 'recent' in path.name:
                    lsoa_codes_recent += wide.lsoa_code.nunique()
                for code, block in wide.groupby('borough_code'):
                    long = unpivot(block, ids).drop(columns='lsoa_name_raw')
                    lsoa_parts.setdefault(code, []).append(long)
            else:
                long = temporal_fields(unpivot(wide, ids))
                all_dates.update(long.month.unique())
                (borough_parts if level == 'borough' else ward_parts).append(long)

    save_lsoa_by_borough(lsoa_parts)
    return borough_parts, ward_parts, all_dates, lsoa_codes_recent


def save_dim_date(all_dates):
    """Bảng tháng phải liên tục"""
    dates = pd.DataFrame({'month': sorted(all_dates)})
    assert len(dates) == len(pd.date_range(dates.month.min(), dates.month.max(), freq='MS'))
    temporal_fields(dates).to_parquet(OUT / 'dim_date.parquet', index=False)
    return dates


# 4. Phạm vi 32 borough + dân số
def build_borough_facts(borough_parts, ward_parts, borough):
    """Tách phần ngoài 32 borough (lưu riêng), join dân số, tính rate_per_1000."""
    facts = pd.concat(borough_parts, ignore_index=True)
    in_scope = facts.borough_name.isin(borough.borough_name)
    excluded = facts[~in_scope]
    excluded.to_parquet(OUT / 'excluded_non_mps_boroughs.parquet', index=False)

    facts = facts[in_scope].copy()
    if facts.duplicated(['borough_name', 'month', 'crime_group', 'crime_subgroup']).any():
        raise ValueError('Overlapping borough snapshots')
    total = int(facts.crime_count.sum())
    facts = facts.merge(borough, on='borough_name', how='left', validate='many_to_one')
    assert int(facts.crime_count.sum()) == total
    facts['rate_per_1000'] = ratio(facts.crime_count, facts.population_2021, 1000)
    facts.to_parquet(OUT / 'crime_borough.parquet', index=False)

    pd.concat(ward_parts, ignore_index=True).to_parquet(OUT / 'crime_ward.parquet', index=False)
    return facts, excluded, total


# 5. Bảng tháng + calculated fields
def build_monthly(facts, borough, quality):
    """Gộp borough × tháng và thêm rolling 12 tháng, MoM, YoY, cờ outlier và hotspot."""
    monthly = facts.groupby(['borough_name', 'month'], as_index=False).crime_count.sum()
    monthly = (monthly.merge(borough, on='borough_name', validate='many_to_one')
               .sort_values(['borough_name', 'month']))
    monthly['rate_per_1000'] = ratio(monthly.crime_count, monthly.population_2021, 1000)

    counts = monthly.groupby('borough_name').crime_count
    previous_month, previous_year = counts.shift(1), counts.shift(ROLLING_MONTHS)
    monthly['rolling_12_count'] = counts.transform(
        lambda s: s.rolling(ROLLING_MONTHS, min_periods=ROLLING_MONTHS).sum())
    monthly['rolling_12_rate'] = ratio(monthly.rolling_12_count, monthly.population_2021, 1000)
    monthly['mom_pct'] = ratio(monthly.crime_count - previous_month, previous_month, 100)
    monthly['yoy_pct'] = ratio(monthly.crime_count - previous_year, previous_year, 100)
    monthly['outlier_iqr'] = counts.transform(iqr_outlier)
    hotspot_cut = monthly.groupby('month').rate_per_1000.transform(lambda s: s.quantile(HOTSPOT_QUANTILE))
    monthly['is_hotspot'] = monthly.rate_per_1000 >= hotspot_cut
    quality['outlier_months_retained'] = int(monthly.outlier_iqr.sum())
    return monthly


# 6. Nhân lực ward officer
def to_month_start(values):
    return pd.to_datetime(values, errors='coerce').dt.to_period('M').dt.to_timestamp()


def reject_invalid(name, table, measure, borough, quality):
    """Ghi các dòng thiếu / âm / borough lạ ra reports/rejected_<name>.csv; có dòng nào là dừng."""
    invalid = table[['borough_name', 'month', measure]].isna().any(axis=1) | (table[measure] < 0)
    invalid |= ~table.borough_name.isin(borough.borough_name)
    table[invalid].to_csv(REPORTS / f'rejected_{name}.csv', index=False)
    quality['security'][f'invalid_{name}'] = int(invalid.sum())
    if invalid.any():
        raise ValueError(f'Invalid {name}: inspect reports/rejected_{name}.csv')


def build_security(borough, quality):
    """FTE theo ngạch và phút abstraction theo borough × tháng; lưu security_*.parquet."""
    log('Aggregating officer FTE and abstraction activity...')
    strengths = pd.read_excel(SECURITY_BOOK, sheet_name='Strengths')
    activity = pd.read_excel(SECURITY_BOOK, sheet_name='Sheet1')
    quality['security'] = {'strength_rows': len(strengths), 'activity_rows': len(activity)}

    strengths['borough_name'] = borough_names(strengths.Department)
    strengths['month'] = to_month_start(strengths.Date)
    strengths['FTE'] = pd.to_numeric(strengths.FTE, errors='coerce')
    activity['borough_name'] = borough_names(activity.Borough)
    activity['month'] = to_month_start(activity['Month of Abstraction'])
    activity['minutes'] = pd.to_numeric(activity['Abstraction Minutes'], errors='coerce')
    reject_invalid('strengths', strengths, 'FTE', borough, quality)
    reject_invalid('activity', activity, 'minutes', borough, quality)

    # Bảng Strengths có thể lặp bản ghi tổng hợp có chủ đích → chỉ báo cáo, không khử trùng FTE.
    quality['security']['exact_duplicate_strength_rows'] = int(strengths.duplicated().sum())
    strengths['rank'] = strengths.Rank.astype(str).str.strip()
    by_rank = strengths.pivot_table(index=['borough_name', 'month'], columns='rank', values='FTE',
                                    aggfunc='sum', fill_value=0).reset_index()
    by_rank.columns.name = None
    by_rank.to_parquet(OUT / 'security_by_rank.parquet', index=False)

    fte = (strengths.groupby(['borough_name', 'month'], as_index=False).FTE.sum()
           .rename(columns={'FTE': 'officer_fte'}))
    statuses = activity['Abstracted From Duty'].astype(str).str.strip().str.lower()
    if not statuses.isin(['yes', 'no']).all():
        raise ValueError('Unexpected abstraction flag')
    activity['abstracted_minutes'] = activity.minutes.where(statuses.eq('yes'), 0)
    minutes = activity.groupby(['borough_name', 'month'], as_index=False)[['minutes', 'abstracted_minutes']].sum()

    security = fte.merge(minutes, on=['borough_name', 'month'], how='outer', validate='one_to_one')
    security = security.merge(borough, on='borough_name', validate='many_to_one')
    security['officers_per_10000'] = ratio(security.officer_fte, security.population_2021, 10000)
    security['abstraction_hours'] = security.abstracted_minutes / 60
    security['abstraction_share_pct'] = ratio(security.abstracted_minutes, security.minutes, 100)
    security['abstraction_hours_per_fte'] = ratio(security.abstraction_hours, security.officer_fte)
    security.to_parquet(OUT / 'security_borough.parquet', index=False)
    return security


# 7. Tội phạm nhân lực
def join_monthly_security(monthly, security, total):
    """Join trái theo (borough, tháng); trong khoảng thời gian chung mọi tháng phải khớp nhân lực."""
    joined = monthly.merge(security.drop(columns=['borough_code', 'population_2021']),
                           on=['borough_name', 'month'], how='left', validate='one_to_one', indicator=True)
    assert int(joined.crime_count.sum()) == total

    in_window = joined[joined.month >= security.month.min()]
    missing_fte = in_window[in_window.officer_fte.isna()]
    missing_fte[['borough_name', 'month']].to_csv(REPORTS / 'missing_fte_months.csv', index=False)
    if (in_window._merge != 'both').any():
        raise ValueError('Missing security joins in the common time interval')
    joined.drop(columns='_merge').to_parquet(OUT / 'monthly.parquet', index=False)
    return {
        'security_eligible_months': len(in_window),
        'security_matched_months': int((in_window._merge == 'both').sum()),
        'fte_observed_months': int(in_window.officer_fte.notna().sum()),
        'fte_missing_months': len(missing_fte),
    }


# 8. Tiếp cận đồn 2013
def build_access_2013(quality):
    """Thay giá trị giữ chỗ 600 phút bằng NaN; lưu riêng, không trộn với dữ liệu hiện tại."""
    travel = pd.read_csv(TRAVEL_FILE).loc[:, ['lsoa', *TRAVEL_COLUMNS]]
    quality['travel_600_replaced'] = int((travel[TRAVEL_COLUMNS] == TRAVEL_PLACEHOLDER).sum().sum())
    travel[TRAVEL_COLUMNS] = travel[TRAVEL_COLUMNS].replace(TRAVEL_PLACEHOLDER, np.nan)
    travel.to_parquet(OUT / 'historical_access_2013.parquet', index=False)


# Điều phối
def preprocess():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    quality = {'sources': validate_sources(), 'raw_crime': [], 'join_checks': {}}

    dim, borough = load_geography(quality)
    borough_parts, ward_parts, all_dates, lsoa_codes_recent = reshape_crime(dim, quality)
    dates = save_dim_date(all_dates)
    facts, excluded, total = build_borough_facts(borough_parts, ward_parts, borough)
    monthly = build_monthly(facts, borough, quality)
    security = build_security(borough, quality)
    window_checks = join_monthly_security(monthly, security, total)
    build_access_2013(quality)

    quality['join_checks'] = {
        'census_boundary_lsoa': len(dim),
        'mps_boroughs': len(borough),
        'crime_lsoa_codes': lsoa_codes_recent,
        'security_eligible_months': window_checks['security_eligible_months'],
        'security_matched_months': window_checks['security_matched_months'],
        'crime_total_preserved': total,
        'excluded_crime_total': int(excluded.crime_count.sum()),
        'fte_observed_months': window_checks['fte_observed_months'],
        'fte_missing_months': window_checks['fte_missing_months'],
    }
    quality['period'] = {'start': str(dates.month.min().date()), 'end': str(dates.month.max().date()),
                         'months': len(dates)}
    # Giữ đúng thứ tự khoá của báo cáo chất lượng.
    order = ['sources', 'raw_crime', 'join_checks', 'invalid_geometries_before', 'outlier_months_retained',
             'security', 'travel_600_replaced', 'period']
    save_json(REPORTS / 'data_quality.json', {key: quality[key] for key in order})
    log(f'Completed preprocessing: {len(facts):,} borough-category-month rows; {total:,} recorded offences.')


if __name__ == '__main__':
    preprocess()
