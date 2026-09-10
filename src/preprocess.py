"""Validate raw snapshots and produce analysis tables without changing sources."""
import hashlib
import re

import geopandas as gpd
import numpy as np
import pandas as pd

from common import ROOT, RAW, OUT, REPORTS, borough_names, ratio, save_json, temporal_fields


def unpivot(frame, identifiers):
    months = [c for c in frame if re.fullmatch(r'20\d{4}', c)]
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


def validate_sources():
    manifest = pd.read_csv(ROOT / 'data' / 'SOURCE_MANIFEST.csv')
    entries = []
    for row in manifest.itertuples():
        path = ROOT / row.relative_path
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(path.read_bytes()).hexdigest()
        if digest.upper() != row.sha256.upper():
            raise ValueError(f'Source hash mismatch: {path.name}')
        entries.append({'dataset': row.dataset_id, 'bytes': path.stat().st_size, 'sha256': digest})
    return entries


def preprocess():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    quality = {'sources': validate_sources(), 'raw_crime': [], 'join_checks': {}}
    print('Reading census and 33 boundary files...', flush=True)
    geos = [gpd.read_file(p) for p in sorted((RAW / 'boundaries' / 'LB_LSOA2021_shp' / 'LB_shp').glob('*.shp'))]
    if not geos or any(g.crs != geos[0].crs for g in geos):
        raise ValueError('Missing or inconsistent boundary CRS')
    geo = gpd.GeoDataFrame(pd.concat(geos, ignore_index=True), crs=geos[0].crs).rename(columns={
        'lsoa21cd': 'lsoa_code', 'lsoa21nm': 'lsoa_name', 'lad22cd': 'borough_code', 'lad22nm': 'borough_name'
    })[['lsoa_code', 'lsoa_name', 'borough_code', 'borough_name', 'geometry']]
    if geo.lsoa_code.duplicated().any() or geo.geometry.is_empty.any() or geo.geometry.isna().any():
        raise ValueError('Invalid boundary keys or empty geometry')
    quality['invalid_geometries_before'] = int((~geo.is_valid).sum())
    geo.geometry = geo.geometry.make_valid()
    census = pd.read_csv(RAW / 'population' / 'census2021-ts001' / 'census2021-ts001-lsoa.csv').rename(columns={
        'geography code': 'lsoa_code', 'Residence type: Total; measures: Value': 'population_2021'
    })[['lsoa_code', 'population_2021']]
    dim = geo.drop(columns='geometry').merge(census, on='lsoa_code', how='left', validate='one_to_one')
    if dim.population_2021.isna().any() or (dim.population_2021 <= 0).any():
        raise ValueError('Missing/nonpositive population')
    dim.to_parquet(OUT / 'dim_lsoa.parquet', index=False)
    borough = dim.groupby(['borough_code', 'borough_name'], as_index=False).population_2021.sum()
    # City of London has a separate police force: restrict the main analysis to 32 MPS boroughs.
    borough = borough[borough.borough_name != 'City of London'].copy()
    borough.to_parquet(OUT / 'dim_borough.parquet', index=False)
    geo = geo.to_crs(27700)
    borough_geo = geo.dissolve(by='borough_name', as_index=False)[['borough_name', 'geometry']]
    borough_geo.geometry = borough_geo.simplify(30, preserve_topology=True)
    borough_geo.to_crs(4326).to_file(OUT / 'boroughs.geojson', driver='GeoJSON')
    geo.geometry = geo.simplify(20, preserve_topology=True)
    geo.to_crs(4326).to_file(OUT / 'lsoa.geojson', driver='GeoJSON')

    print('Reshaping crime snapshots and checking joins...', flush=True)
    fact_parts, ward_parts, all_dates = [], [], set()
    lsoa_parts = {}
    for level in ['borough', 'ward', 'lsoa']:
        for path in sorted((RAW / 'crime').glob(f'mps_{level}_*.csv')):
            wide = pd.read_csv(path)
            rename = {'Group': 'crime_group', 'SubGroup': 'crime_subgroup', 'BOCU': 'borough_name',
                      'LSOA Code': 'lsoa_code', 'LSOA Name': 'lsoa_name_raw', 'Borough': 'borough_code',
                      'WardCode': 'ward_code', 'WardName': 'ward_name', 'LookUp_BoroughName': 'borough_name'}
            wide = wide.rename(columns=rename)
            ids = [c for c in wide if not re.fullmatch(r'20\d{4}', c)]
            entry = {'file': path.name, 'rows': len(wide), 'missing_cells': int(wide.isna().sum().sum())}
            quality['raw_crime'].append(entry)
            if level == 'lsoa':
                matched = wide.lsoa_code.isin(dim.lsoa_code)
                if not matched.all():
                    raise ValueError('Crime LSOA missing from census/boundary')
                for code, block in wide.groupby('borough_code'):
                    long = unpivot(block, ids).drop(columns='lsoa_name_raw')
                    lsoa_parts.setdefault(code, []).append(long)
                entry['matched_rows'] = int(matched.sum())
            else:
                long = temporal_fields(unpivot(wide, ids))
                all_dates.update(long.month.unique())
                (fact_parts if level == 'borough' else ward_parts).append(long)
    for code, parts in lsoa_parts.items():
        long = pd.concat(parts, ignore_index=True)
        if long.duplicated(['lsoa_code', 'crime_group', 'crime_subgroup', 'month']).any():
            raise ValueError('Overlapping LSOA snapshots')
        for c in ['lsoa_code', 'borough_code', 'crime_group', 'crime_subgroup']:
            long[c] = long[c].astype('category')
        long.to_parquet(OUT / f'lsoa_{code}.parquet', index=False)
    del lsoa_parts
    facts = pd.concat(fact_parts, ignore_index=True)
    excluded = facts[~facts.borough_name.isin(borough.borough_name)]
    excluded.to_parquet(OUT / 'excluded_non_mps_boroughs.parquet', index=False)
    facts = facts[facts.borough_name.isin(borough.borough_name)].copy()
    if facts.duplicated(['borough_name', 'month', 'crime_group', 'crime_subgroup']).any():
        raise ValueError('Overlapping borough snapshots')
    count_before = int(facts.crime_count.sum())
    facts = facts.merge(borough, on='borough_name', how='left', validate='many_to_one')
    assert int(facts.crime_count.sum()) == count_before
    facts['rate_per_1000'] = ratio(facts.crime_count, facts.population_2021, 1000)
    facts.to_parquet(OUT / 'crime_borough.parquet', index=False)
    wards = pd.concat(ward_parts, ignore_index=True)
    wards.to_parquet(OUT / 'crime_ward.parquet', index=False)
    dates = pd.DataFrame({'month': sorted(all_dates)})
    assert len(dates) == len(pd.date_range(dates.month.min(), dates.month.max(), freq='MS'))
    temporal_fields(dates).to_parquet(OUT / 'dim_date.parquet', index=False)
    monthly = facts.groupby(['borough_name', 'month'], as_index=False).crime_count.sum()
    monthly = monthly.merge(borough, on='borough_name', validate='many_to_one').sort_values(['borough_name', 'month'])
    monthly['rate_per_1000'] = ratio(monthly.crime_count, monthly.population_2021, 1000)
    grouped = monthly.groupby('borough_name').crime_count
    monthly['rolling_12_count'] = grouped.transform(lambda s: s.rolling(12, min_periods=12).sum())
    monthly['rolling_12_rate'] = ratio(monthly.rolling_12_count, monthly.population_2021, 1000)
    monthly['mom_pct'] = ratio(monthly.crime_count - grouped.shift(1), grouped.shift(1), 100)
    monthly['yoy_pct'] = ratio(monthly.crime_count - grouped.shift(12), grouped.shift(12), 100)
    q1 = grouped.transform(lambda s: s.quantile(.25))
    q3 = grouped.transform(lambda s: s.quantile(.75))
    monthly['outlier_iqr'] = (monthly.crime_count < q1 - 1.5 * (q3-q1)) | (monthly.crime_count > q3 + 1.5 * (q3-q1))
    monthly['is_hotspot'] = monthly.rate_per_1000 >= monthly.groupby('month').rate_per_1000.transform(lambda s: s.quantile(.75))
    quality['outlier_months_retained'] = int(monthly.outlier_iqr.sum())

    print('Aggregating officer FTE and abstraction activity...', flush=True)
    book = RAW / 'security' / 'MPS_Dedicated_Ward_Officer_Abstractions_and_Strengths.xlsx'
    strengths = pd.read_excel(book, sheet_name='Strengths')
    activity = pd.read_excel(book, sheet_name='Sheet1')
    quality['security'] = {'strength_rows': len(strengths), 'activity_rows': len(activity)}
    strengths['borough_name'] = borough_names(strengths.Department)
    strengths['month'] = pd.to_datetime(strengths.Date, errors='coerce').dt.to_period('M').dt.to_timestamp()
    strengths['FTE'] = pd.to_numeric(strengths.FTE, errors='coerce')
    activity['borough_name'] = borough_names(activity.Borough)
    activity['month'] = pd.to_datetime(activity['Month of Abstraction'], errors='coerce').dt.to_period('M').dt.to_timestamp()
    activity['minutes'] = pd.to_numeric(activity['Abstraction Minutes'], errors='coerce')
    for name, table, measure in [('strengths', strengths, 'FTE'), ('activity', activity, 'minutes')]:
        invalid = table[['borough_name', 'month', measure]].isna().any(axis=1) | (table[measure] < 0)
        invalid |= ~table.borough_name.isin(borough.borough_name)
        table[invalid].to_csv(REPORTS / f'rejected_{name}.csv', index=False)
        quality['security'][f'invalid_{name}'] = int(invalid.sum())
        if invalid.any():
            raise ValueError(f'Invalid {name}: inspect reports/rejected_{name}.csv')
    # The published Strengths table may contain repeated aggregate records; never silently deduplicate FTE.
    quality['security']['exact_duplicate_strength_rows'] = int(strengths.duplicated().sum())
    strengths['rank'] = strengths.Rank.astype(str).str.strip()
    rank = strengths.pivot_table(index=['borough_name', 'month'], columns='rank', values='FTE', aggfunc='sum', fill_value=0).reset_index()
    rank.columns.name = None
    rank.to_parquet(OUT / 'security_by_rank.parquet', index=False)
    fte = strengths.groupby(['borough_name', 'month'], as_index=False).FTE.sum().rename(columns={'FTE': 'officer_fte'})
    statuses = activity['Abstracted From Duty'].astype(str).str.strip().str.lower()
    if not statuses.isin(['yes', 'no']).all():
        raise ValueError('Unexpected abstraction flag')
    activity['abstracted_minutes'] = activity.minutes.where(statuses.eq('yes'), 0)
    activity_sum = activity.groupby(['borough_name', 'month'], as_index=False)[['minutes', 'abstracted_minutes']].sum()
    security = fte.merge(activity_sum, on=['borough_name', 'month'], how='outer', validate='one_to_one')
    security = security.merge(borough, on='borough_name', validate='many_to_one')
    security['officers_per_10000'] = ratio(security.officer_fte, security.population_2021, 10000)
    security['abstraction_hours'] = security.abstracted_minutes / 60
    security['abstraction_share_pct'] = ratio(security.abstracted_minutes, security.minutes, 100)
    security['abstraction_hours_per_fte'] = ratio(security.abstraction_hours, security.officer_fte)
    security.to_parquet(OUT / 'security_borough.parquet', index=False)
    joined = monthly.merge(security.drop(columns=['borough_code', 'population_2021']), on=['borough_name', 'month'], how='left', validate='one_to_one', indicator=True)
    assert int(joined.crime_count.sum()) == count_before
    eligible = joined.month >= security.month.min()
    quality['join_checks'] = {'census_boundary_lsoa': len(dim), 'mps_boroughs': len(borough),
        'crime_lsoa_codes': sum(pd.read_csv(p, usecols=['LSOA Code'])['LSOA Code'].nunique() for p in (RAW / 'crime').glob('*lsoa*recent*')),
        'security_eligible_months': int(eligible.sum()), 'security_matched_months': int((joined.loc[eligible, '_merge'] == 'both').sum()),
        'crime_total_preserved': count_before, 'excluded_crime_total': int(excluded.crime_count.sum())}
    quality['join_checks']['fte_observed_months'] = int(joined.loc[eligible, 'officer_fte'].notna().sum())
    quality['join_checks']['fte_missing_months'] = int(joined.loc[eligible, 'officer_fte'].isna().sum())
    joined.loc[eligible & joined.officer_fte.isna(), ['borough_name', 'month']].to_csv(REPORTS / 'missing_fte_months.csv', index=False)
    if (joined.loc[eligible, '_merge'] != 'both').any():
        raise ValueError('Missing security joins in the common time interval')
    joined.drop(columns='_merge').to_parquet(OUT / 'monthly.parquet', index=False)
    # Keep historical access data separate from present-day crime and workforce.
    travel_path = RAW / 'security' / 'lsoa_police_front_counter_travel_times_2013' / 'lsoatimings.csv'
    travel = pd.read_csv(travel_path).loc[:, ['lsoa', 'pre12', 'pre24', 'post12', 'post24']]
    quality['travel_600_replaced'] = int((travel.iloc[:, 1:] == 600).sum().sum())
    travel.iloc[:, 1:] = travel.iloc[:, 1:].replace(600, np.nan)
    travel.to_parquet(OUT / 'historical_access_2013.parquet', index=False)
    quality['period'] = {'start': str(dates.month.min().date()), 'end': str(dates.month.max().date()), 'months': len(dates)}
    save_json(REPORTS / 'data_quality.json', quality)
    print(f'Completed preprocessing: {len(facts):,} borough-category-month rows; {count_before:,} recorded offences.', flush=True)


if __name__ == '__main__':
    preprocess()
