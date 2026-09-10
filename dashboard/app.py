from pathlib import Path
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'processed'
ALL = 'Tất cả'
COLORS = ['#007C83', '#B83E58', '#DAA520', '#437BBA', '#606C38', '#9365A0', '#DC7150']
st.set_page_config(page_title='London | Tội phạm và an ninh', layout='wide')
st.markdown('''<style>
.block-container {max-width:1500px;padding-top:1.5rem;}
h1 {font-size:2rem !important;letter-spacing:0 !important;}
h2 {font-size:1.35rem !important;letter-spacing:0 !important;}
[data-testid="stMetricValue"] {font-size:1.65rem;}
</style>''', unsafe_allow_html=True)


@st.cache_data
def load(name):
    return pd.read_parquet(DATA / f'{name}.parquet')


@st.cache_data
def geography(level, borough=None):
    geo = json.loads((DATA / f'{level}.geojson').read_text(encoding='utf-8'))
    if borough:
        geo['features'] = [f for f in geo['features'] if f['properties']['borough_name'] == borough]
    return geo


def select_borough(key):
    event = st.session_state.get(key, {})
    points = event.get('selection', {}).get('points', [])
    if points:
        st.session_state['borough'] = points[0]['customdata'][0]
        st.session_state['lsoa_choice'] = ALL


def reset():
    st.session_state['borough'] = ALL
    st.session_state['group'] = ALL
    st.session_state['subgroup'] = ALL
    st.session_state['lsoa_choice'] = ALL
    st.session_state['chart_epoch'] = st.session_state.get('chart_epoch', 0) + 1


def chart(fig, key, callback=None):
    fig.update_layout(font={'family': 'Arial', 'size': 12}, margin=dict(l=12, r=12, t=40, b=12),
                      paper_bgcolor='white', plot_bgcolor='white', colorway=COLORS,
                      legend=dict(orientation='h', y=-.2), height=410)
    if callback:
        fig.update_layout(clickmode='event+select')
        st.plotly_chart(fig, width='stretch', key=key, on_select=callback, selection_mode='points')
    else:
        st.plotly_chart(fig, width='stretch', key=key)


if not (DATA / 'monthly.parquet').exists():
    st.error('Chưa có dữ liệu đã xử lý. Chạy run_pipeline.py theo README của dự án.')
    st.stop()

facts, dim, monthly = load('crime_borough'), load('dim_borough'), load('monthly')
months = sorted(facts.month.dt.strftime('%Y-%m').unique())
with st.sidebar:
    st.title('London')
    start, end = st.select_slider('Khoảng tháng', options=months, value=(months[-12], months[-1]))
    borough = st.selectbox('Borough', [ALL] + sorted(dim.borough_name), key='borough')
    group = st.selectbox('Nhóm tội phạm', [ALL] + sorted(facts.crime_group.unique()), key='group')
    group_rows = facts if group == ALL else facts[facts.crime_group == group]
    sub_options = [ALL] + sorted(group_rows.crime_subgroup.unique())
    if st.session_state.get('subgroup', ALL) not in sub_options:
        st.session_state['subgroup'] = ALL
    subgroup = st.selectbox('Phân nhóm', sub_options, key='subgroup')
    measure = st.radio('Chỉ số', ['Số vụ', 'Vụ / 1.000 dân'])
    st.button('Đặt lại lựa chọn', icon=':material/restart_alt:', on_click=reset)
    st.caption('Nguồn: MPS · ONS Census 2021 · GLA')

st.title('Tội phạm và nguồn lực cảnh sát London')
st.caption(f'{start} đến {end} · 32 borough thuộc MPS · Dữ liệu ghi nhận, chưa phản ánh toàn bộ tội phạm xảy ra')
date_mask = facts.month.between(pd.Timestamp(start), pd.Timestamp(end))
filtered = facts[date_mask].copy()
if group != ALL:
    filtered = filtered[filtered.crime_group == group]
if subgroup != ALL:
    filtered = filtered[filtered.crime_subgroup == subgroup]
context = filtered.copy()
if borough != ALL:
    filtered = filtered[filtered.borough_name == borough]
scope_dim = dim if borough == ALL else dim[dim.borough_name == borough]
population = int(scope_dim.population_2021.sum())
metric = 'crime_count' if measure == 'Số vụ' else 'rate_per_1000'
monthly_scope = monthly[monthly.month.between(pd.Timestamp(start), pd.Timestamp(end))]
if borough != ALL:
    monthly_scope = monthly_scope[monthly_scope.borough_name == borough]
security_snapshot = monthly_scope[monthly_scope.month == pd.Timestamp(end)]
if filtered.empty:
    st.info('Không có bản ghi phù hợp với bộ lọc hiện tại. Dữ liệu không có bản ghi không được tự coi là 0.')
    st.stop()

total = int(filtered.crime_count.sum())
metric_cols = st.columns(4)
metric_cols[0].metric('Số vụ trong kỳ', f'{total:,}')
metric_cols[1].metric('Vụ / 1.000 dân trong kỳ', f'{total/population*1000:,.2f}')
metric_cols[2].metric('Dân số Census 2021', f'{population:,}')
fte = security_snapshot.officer_fte.sum(min_count=1)
fte_coverage = int(security_snapshot.officer_fte.notna().sum())
metric_cols[3].metric(f'DWO FTE đã biết · {end}', 'Chưa có' if pd.isna(fte) else f'{fte:,.1f}')
if fte_coverage < len(scope_dim):
    st.warning(f'FTE chỉ có số liệu cho {fte_coverage}/{len(scope_dim)} borough trong tháng {end}. Tổng FTE hiển thị là phần đã biết; nguồn thiếu Camden từ 08/2024, không quy thành 0.')
st.caption('Tỷ lệ dùng dân số cố định năm 2021; kỳ dài hơn tích lũy nhiều vụ hơn. DWO FTE là quân số đội địa bàn, không phải toàn bộ cảnh sát. Mốc ghi nhận CONNECT: 03/2024.')

overview, composition, security_tab, local, forecast_tab, evidence = st.tabs([
    'Tổng quan', 'Cơ cấu và phân phối', 'Nguồn lực cảnh sát', 'Chi tiết LSOA', 'Dự báo', 'Nguồn và chất lượng'])
with overview:
    ranking = context.groupby('borough_name', as_index=False).crime_count.sum().merge(dim, on='borough_name', validate='one_to_one')
    ranking['rate_per_1000'] = ranking.crime_count / ranking.population_2021 * 1000
    epoch = st.session_state.get('chart_epoch', 0)
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader('Phân bố theo borough')
        fig = px.choropleth(ranking, geojson=geography('boroughs'), locations='borough_name',
            featureidkey='properties.borough_name', color=metric, color_continuous_scale='YlOrRd',
            hover_name='borough_name', custom_data=['borough_name'],
            labels={'crime_count': 'Số vụ', 'rate_per_1000': 'Vụ / 1.000 dân', 'population_2021': 'Dân số 2021'},
            hover_data={'crime_count': ':,', 'rate_per_1000': ':.2f', 'population_2021': ':,'})
        fig.update_geos(fitbounds='locations', visible=False)
        key = f'borough_map_{epoch}'
        chart(fig, key, lambda: select_borough(key))
    with right:
        st.subheader('Xếp hạng borough')
        rank_key = f'borough_rank_{epoch}'
        fig = px.bar(ranking.nlargest(15, metric).sort_values(metric), x=metric, y='borough_name',
                     custom_data=['borough_name'], color_discrete_sequence=COLORS,
                     labels={metric: measure, 'borough_name': ''})
        chart(fig, rank_key, lambda: select_borough(rank_key))
    st.caption(f'Bản đồ và xếp hạng: toàn bộ 32 borough trong bộ lọc thời gian/loại tội phạm. Phạm vi chi tiết đang chọn: {borough}.')
    trend = filtered.groupby('month', as_index=False).crime_count.sum()
    trend['rate_per_1000'] = trend.crime_count / population * 1000
    chart(px.line(trend, x='month', y=metric, markers=True, title=f'Xu hướng · {borough}',
                  labels={'month': 'Tháng', metric: measure}), 'trend')

with composition:
    left, right = st.columns(2)
    with left:
        tree = filtered.groupby(['crime_group', 'crime_subgroup'], as_index=False).crime_count.sum()
        tree = tree[tree.crime_count > 0]
        if not tree.empty:
            chart(px.treemap(tree, path=['crime_group', 'crime_subgroup'], values='crime_count',
                             color='crime_group', color_discrete_sequence=COLORS, title='Nhóm và phân nhóm'), 'treemap')
    with right:
        shares = filtered.groupby('crime_group', as_index=False).crime_count.sum()
        chart(px.pie(shares, names='crime_group', values='crime_count', hole=.55,
                     color_discrete_sequence=COLORS, title='Tỷ trọng tội phạm'), 'donut')
    rows = filtered.groupby(['borough_name', 'month'], as_index=False).crime_count.sum().merge(
        dim[['borough_name', 'population_2021']], on='borough_name', validate='many_to_one')
    rows['rate_per_1000'] = rows.crime_count / rows.population_2021 * 1000
    heat = rows.pivot(index='borough_name', columns='month', values=metric)
    heat.columns = heat.columns.strftime('%Y-%m')
    chart(px.imshow(heat, aspect='auto', color_continuous_scale='YlOrRd',
                    title='Borough theo tháng', labels={'color': measure}), 'heatmap')
    left, right = st.columns(2)
    with left:
        chart(px.box(rows, y='rate_per_1000', points='outliers', title='Phân phối tỷ lệ theo borough-tháng',
                     labels={'rate_per_1000': 'Vụ / 1.000 dân / tháng'}), 'box')
    with right:
        chart(px.histogram(rows, x='rate_per_1000', nbins=30, title='Tần suất tỷ lệ theo borough-tháng',
                           labels={'rate_per_1000': 'Vụ / 1.000 dân / tháng'}), 'histogram')

with security_tab:
    st.subheader('Nguồn lực đội cảnh sát địa bàn')
    st.caption('FTE là ảnh chụp tháng cuối kỳ, cộng Constable và PCSO một lần theo địa bàn. Hoạt động điều chuyển và FTE có dữ liệu từ 08/2021. Bộ lọc crime chỉ tác động trục số vụ, không lọc quân số.')
    st.caption(f'Độ phủ FTE tháng {end}: {fte_coverage}/{len(scope_dim)} borough. Scatter chỉ bao gồm địa bàn có FTE quan sát được.')
    scatter_counts = filtered[filtered.month == pd.Timestamp(end)].groupby('borough_name', as_index=False).crime_count.sum()
    snapshot = security_snapshot.drop(columns=['crime_count', 'rate_per_1000']).merge(scatter_counts, on='borough_name', validate='one_to_one')
    snapshot['rate_per_1000'] = snapshot.crime_count / snapshot.population_2021 * 1000
    snapshot = snapshot.dropna(subset=['officers_per_10000'])
    if snapshot.empty:
        st.info('Không có dữ liệu nguồn lực cho tháng cuối kỳ đang chọn.')
    else:
        chart(px.scatter(snapshot, x='officers_per_10000', y='rate_per_1000', size='population_2021',
            hover_name='borough_name', color='abstraction_share_pct', color_continuous_scale='Tealrose',
            title=f'Nguồn lực và tỷ lệ tội phạm · {end}',
            labels={'officers_per_10000': 'DWO FTE / 10.000 dân', 'rate_per_1000': 'Vụ / 1.000 dân / tháng',
                    'abstraction_share_pct': '% phút điều chuyển'}), 'scatter')
        st.caption('Mối liên hệ trên biểu đồ là tương quan. Nguồn lực có thể được phân bổ để đáp ứng tình hình tội phạm.')
        rank = load('security_by_rank')
        rank = rank[(rank.month == pd.Timestamp(end)) & rank.borough_name.isin(scope_dim.borough_name)]
        rank_long = rank.melt(id_vars=['borough_name', 'month'], var_name='rank', value_name='FTE')
        chart(px.bar(rank_long, x='borough_name', y='FTE', color='rank', barmode='stack',
                     color_discrete_sequence=COLORS, title='Quân số theo cấp bậc'), 'rank_fte')
        st.dataframe(snapshot[['borough_name', 'officer_fte', 'officers_per_10000', 'abstraction_hours', 'abstraction_share_pct']], hide_index=True)

with local:
    if borough == ALL:
        st.info('Chọn một borough để xem LSOA thuộc địa bàn đó.')
    else:
        st.subheader(f'LSOA · {borough}')
        st.caption('MPS không công bố Sexual Offences tại LSOA. Phạm vi ghi nhận và phân loại có thể khác bảng borough; không dùng tổng LSOA để thay tổng borough.')
        code = scope_dim.borough_code.iloc[0]
        lsoa = load(f'lsoa_{code}')
        lsoa = lsoa[lsoa.month.between(pd.Timestamp(start), pd.Timestamp(end))]
        if group != ALL:
            lsoa = lsoa[lsoa.crime_group == group]
        if subgroup != ALL:
            lsoa = lsoa[lsoa.crime_subgroup == subgroup]
        local_dim = load('dim_lsoa')
        local_dim = local_dim[local_dim.borough_name == borough]
        area_counts = lsoa.groupby('lsoa_code', observed=True, as_index=False).crime_count.sum()
        area_counts['lsoa_code'] = area_counts.lsoa_code.astype(str)
        areas = local_dim.merge(area_counts, on='lsoa_code', how='left', validate='one_to_one')
        areas['rate_per_1000'] = areas.crime_count / areas.population_2021 * 1000
        options = [ALL] + sorted(areas.lsoa_code)
        if st.session_state.get('lsoa_choice', ALL) not in options:
            st.session_state['lsoa_choice'] = ALL
        names = dict(zip(areas.lsoa_code, areas.lsoa_name))
        chosen = st.selectbox('LSOA', options, key='lsoa_choice', format_func=lambda x: names.get(x, x))
        if areas.crime_count.notna().any():
            plot_areas = areas if chosen == ALL else areas[areas.lsoa_code == chosen]
            fig = px.choropleth(plot_areas, geojson=geography('lsoa', borough), locations='lsoa_code',
                featureidkey='properties.lsoa_code', color=metric, color_continuous_scale='YlOrRd',
                labels={'crime_count': 'Số vụ', 'rate_per_1000': 'Vụ / 1.000 dân', 'population_2021': 'Dân số 2021'},
                hover_name='lsoa_name', hover_data={'population_2021': ':,', 'crime_count': ':,', 'rate_per_1000': ':.2f'})
            fig.update_geos(fitbounds='locations', visible=False)
            chart(fig, 'lsoa_map')
            history = lsoa if chosen == ALL else lsoa[lsoa.lsoa_code == chosen]
            local_trend = history.groupby('month', as_index=False).crime_count.sum()
            chart(px.line(local_trend, x='month', y='crime_count', title='Số vụ ghi nhận tại LSOA đang chọn'), 'lsoa_trend')
            st.dataframe(plot_areas[['lsoa_code', 'lsoa_name', 'crime_count', 'population_2021', 'rate_per_1000']], hide_index=True)
        else:
            st.info('Không có dữ liệu LSOA cho nhóm/phân nhóm và thời gian này; không coi là không có tội phạm.')

with forecast_tab:
    st.subheader(f'Dự báo tổng số vụ · {borough}')
    st.caption('Mô hình tổng tội phạm theo borough, không áp dụng bộ lọc nhóm/phân nhóm và thời gian của các trang mô tả. Train: 08/2020–07/2025; test: 08/2025–07/2026; dự báo: 08/2026–01/2027. Đường dự báo không phải quan sát thực.')
    forecast = load('forecast')
    forecast = forecast[forecast.borough_name.isin(scope_dim.borough_name)]
    totals = forecast.groupby(['month', 'split'], as_index=False)[['actual', 'predicted', 'baseline']].sum(min_count=1)
    fig = go.Figure()
    fig.add_scatter(x=totals.month, y=totals.actual, name='Thực tế', line={'color': COLORS[0]})
    test = totals[totals.split == 'test']
    future = totals[totals.split == 'forecast']
    fig.add_scatter(x=test.month, y=test.predicted, name='Dự đoán tập test', line={'color': COLORS[1], 'dash': 'dash'})
    fig.add_scatter(x=test.month, y=test.baseline, name='Cùng tháng năm trước', line={'color': '#777', 'dash': 'dot'})
    fig.add_scatter(x=future.month, y=future.predicted, name='Dự báo 6 tháng', line={'color': COLORS[2], 'dash': 'dash'})
    fig.update_layout(yaxis_title='Số vụ', xaxis_title='Tháng')
    chart(fig, 'forecast')
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    evaluation = pd.DataFrame([{'Mô hình': label, 'MAE': mean_absolute_error(test.actual, test[col]),
        'RMSE': np.sqrt(mean_squared_error(test.actual, test[col])), 'R²': r2_score(test.actual, test[col])}
        for label, col in [('Linear Regression', 'predicted'), ('Cùng tháng năm trước', 'baseline')]])
    st.dataframe(evaluation, hide_index=True)
    if evaluation.MAE.iloc[0] > evaluation.MAE.iloc[1]:
        st.info('Trong phạm vi đang chọn, Linear Regression có MAE cao hơn mô hình cùng tháng năm trước. Cần ghi nhận hạn chế này khi sử dụng dự báo.')
    st.caption('Các biến dự báo: chỉ số thời gian, sin/cos tháng và cờ CONNECT. Mỗi borough có mô hình riêng; mô hình được huấn luyện lại trên toàn bộ dữ liệu sau khi đánh giá. Giá trị âm được chặn tại 0. Chưa ước lượng khoảng dự báo.')
    st.download_button('Tải kết quả dự báo', forecast.to_csv(index=False).encode('utf-8-sig'), 'forecast.csv', 'text/csv', icon=':material/download:')

with evidence:
    st.subheader('Nguồn dữ liệu và phạm vi')
    st.markdown('''- [MPS Recorded Crime](https://data.london.gov.uk/dataset/mps-recorded-crime-geographic-breakdown-exy3m)
- [ONS Census 2021 TS001](https://www.nomisweb.co.uk/sources/census_2021_bulk)
- [GLA Statistical Boundaries](https://data.london.gov.uk/dataset/statistical-gis-boundary-files-for-london-20od9)
- [MPS Dedicated Ward Officers](https://data.london.gov.uk/dataset/mps-dedicated-ward-officer-abstractions-and-strengths-e16kd)''')
    st.caption('Loại Aviation Policing, Unknown và City of London khỏi so sánh 32 borough. Dữ liệu quầy cảnh sát 2013 không tham gia dashboard hiện trạng. Bản đồ chứa dữ liệu National Statistics và Ordnance Survey, Crown copyright/database right; điều kiện sử dụng theo trang nguồn GLA.')
    quality = json.loads((ROOT / 'reports' / 'data_quality.json').read_text(encoding='utf-8'))
    st.json({'period': quality['period'], 'joins': quality['join_checks'], 'outliers_retained': quality['outlier_months_retained']})
    st.download_button('Tải bảng đang lọc', filtered.to_csv(index=False).encode('utf-8-sig'), 'london_filtered.csv', 'text/csv', icon=':material/download:')
