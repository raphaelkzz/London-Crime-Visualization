"""Dashboard Streamlit: tội phạm và nguồn lực cảnh sát tại 32 borough MPS.

Chạy:  python -m streamlit run dashboard/app.py

Bố cục: sidebar (bộ lọc) → dòng bộ lọc đang áp dụng → 4 KPI → 6 tab.
Cross-filtering: click bản đồ, cột xếp hạng hoặc điểm scatter → chọn borough;
click cột nhóm tội phạm (tab Cơ cấu) → chọn nhóm. Mọi biểu đồ khác cập nhật theo.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Cấu hình
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'processed'
ALL = 'Tất cả'
OTHER = 'Khác'
CONNECT_START = pd.Timestamp('2024-03-01')

BLUE, ORANGE, MUTED, NEUTRAL = '#2a78d6', '#eb6834', '#52514e', '#ececea'
# Palette phân loại cố định (8 màu); màu gắn với nhóm tội phạm, không đổi theo bộ lọc.
CATEGORICAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
OTHER_COLOR = '#a8a7a2'
SEQUENTIAL = 'Blues'
DIVERGING = [[0, BLUE], [.5, NEUTRAL], [1, ORANGE]]
CARTESIAN = {'bar', 'scatter', 'box', 'histogram', 'heatmap'}   # trace có trục x/y
SPIKE_STYLE = dict(showspikes=True, spikemode='toaxis', spikesnap='data',
                   spikecolor='#5F6368', spikethickness=1, spikedash='dot')
LABELS = {'crime_count': 'Số vụ', 'rate_per_1000': 'Vụ / 1.000 dân', 'population_2021': 'Dân số 2021',
          'borough_name': 'Borough', 'crime_group': 'Nhóm tội phạm', 'month': 'Tháng'}

st.set_page_config(page_title='London | Tội phạm và an ninh', layout='wide')
st.markdown('''<style>
.block-container {max-width:1500px;padding-top:1.5rem;}
h1 {font-size:2rem !important;letter-spacing:0 !important;}
h2, h3 {font-size:1.25rem !important;letter-spacing:0 !important;}
[data-testid="stMetricValue"] {font-size:1.65rem;}
</style>''', unsafe_allow_html=True)


# Dữ liệu
@st.cache_data
def load(name):
    return pd.read_parquet(DATA / f'{name}.parquet')


@st.cache_data
def geography(level, borough=None):
    geo = json.loads((DATA / f'{level}.geojson').read_text(encoding='utf-8'))
    if borough:
        geo['features'] = [f for f in geo['features'] if f['properties']['borough_name'] == borough]
    return geo


@st.cache_data
def group_colors(facts):
    """7 nhóm lớn nhất (toàn bộ dữ liệu) có màu riêng; các nhóm còn lại gộp thành 'Khác'."""
    order = facts.groupby('crime_group').crime_count.sum().sort_values(ascending=False).index.tolist()
    colors = {group: CATEGORICAL[i] for i, group in enumerate(order[:7])}
    colors.update({group: OTHER_COLOR for group in order[7:]})
    colors[OTHER] = OTHER_COLOR
    return colors


@st.cache_data
def minor_groups(facts):
    """Nhóm < 0,1% tổng số vụ (NFIB Fraud, Fraud and Forgery): bỏ khỏi boxplot vì gần như không có số liệu."""
    totals = facts.groupby('crime_group').crime_count.sum()
    return totals[totals < .001 * totals.sum()].index.tolist()


def with_rate(frame, dim):
    """Join dân số Census 2021 và tính vụ / 1.000 dân."""
    frame = frame.merge(dim[['borough_name', 'population_2021']], on='borough_name', validate='many_to_one')
    frame['rate_per_1000'] = frame.crime_count / frame.population_2021 * 1000
    return frame


# Tương tác
def selected_value(key):
    points = st.session_state.get(key, {}).get('selection', {}).get('points', [])
    values = [p['customdata'][0] for p in points if p.get('customdata')]   # bỏ qua đường hồi quy / viền chọn
    return values[0] if values else None


# Lưu ý: callback truyền `lambda key=key: ...` để gắn đúng key của từng biểu đồ. Viết `lambda: ...(key)` thì Python
# đọc biến `key` lúc click (late binding) → bản đồ đọc nhầm sự kiện của cột xếp hạng và mất click.
def select_borough(key):
    value = selected_value(key)
    if value:
        st.session_state['borough'] = value
        st.session_state['lsoa_choice'] = ALL


def select_group(key):
    value = selected_value(key)
    if value:
        st.session_state['group'] = value
        st.session_state['subgroup'] = ALL


def clear(key):
    st.session_state[key] = ALL
    if key == 'group':
        st.session_state['subgroup'] = ALL


def reset():
    for key in ['borough', 'group', 'subgroup', 'lsoa_choice']:
        st.session_state[key] = ALL
    st.session_state['chart_epoch'] = st.session_state.get('chart_epoch', 0) + 1


def chart(fig, key, callback=None, spikes=False, height=410):
    """Áp style chung; spikes = đường dóng tới hai trục; callback = click để lọc chéo."""
    fig.update_layout(font={'family': 'Arial', 'size': 12}, margin=dict(l=12, r=12, t=48, b=12),
                      paper_bgcolor='white', plot_bgcolor='white', colorway=CATEGORICAL,
                      legend=dict(orientation='h', y=-.2), height=height,
                      hoverlabel=dict(bgcolor='white'))
    # Chỉ chỉnh font tiêu đề khi biểu đồ có tiêu đề; đặt font cho tiêu đề rỗng làm Plotly hiện chữ "undefined".
    if fig.layout.title.text:
        fig.update_layout(title_font=dict(size=15))
    # Chỉ style trục cho biểu đồ có trục x/y; thêm xaxis vào bản đồ / pie / treemap có thể chặn click.
    if all(trace.type in CARTESIAN for trace in fig.data):
        fig.update_xaxes(gridcolor='#e4e3de', zeroline=False)
        fig.update_yaxes(gridcolor='#e4e3de', zeroline=False)
    if spikes:
        fig.update_layout(hovermode='closest', hoverdistance=30, spikedistance=-1)
        fig.update_xaxes(**SPIKE_STYLE)
        fig.update_yaxes(**SPIKE_STYLE)
    if callback:
        fig.update_layout(clickmode='event+select')
        st.plotly_chart(fig, width='stretch', key=key, on_select=callback, selection_mode='points')
    else:
        st.plotly_chart(fig, width='stretch', key=key)


# Sidebar + phạm vi lọc
def sidebar(facts, dim, months):
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
        st.caption('Click bản đồ, cột xếp hạng hoặc điểm scatter để chọn borough; '
                   'click cột nhóm tội phạm (tab Cơ cấu) để chọn nhóm.')
        st.caption('Nguồn: MPS · ONS Census 2021 · GLA')
    return dict(start=pd.Timestamp(start), end=pd.Timestamp(end), start_label=start, end_label=end,
                borough=borough, group=group, subgroup=subgroup, measure=measure,
                metric='crime_count' if measure == 'Số vụ' else 'rate_per_1000')


def scope(facts, dim, monthly, f):
    """Tạo các bảng con theo bộ lọc. `context` = mọi borough (cho bản đồ/xếp hạng)."""
    in_period = facts[facts.month.between(f['start'], f['end'])]
    by_group = in_period if f['group'] == ALL else in_period[in_period.crime_group == f['group']]
    context = by_group if f['subgroup'] == ALL else by_group[by_group.crime_subgroup == f['subgroup']]
    filtered = context if f['borough'] == ALL else context[context.borough_name == f['borough']]
    by_borough = in_period if f['borough'] == ALL else in_period[in_period.borough_name == f['borough']]
    scope_dim = dim if f['borough'] == ALL else dim[dim.borough_name == f['borough']]
    monthly_scope = monthly[monthly.month.between(f['start'], f['end'])]
    if f['borough'] != ALL:
        monthly_scope = monthly_scope[monthly_scope.borough_name == f['borough']]
    return dict(context=context, filtered=filtered, monthly_all=monthly[monthly.month.between(f['start'], f['end'])], by_borough=by_borough, scope_dim=scope_dim,
                population=int(scope_dim.population_2021.sum()), monthly_scope=monthly_scope,
                snapshot=monthly_scope[monthly_scope.month == f['end']])


def active_filters(f):
    """Dòng 'Đang lọc' với nút xoá từng điều kiện."""
    active = [(key, f[key]) for key in ['borough', 'group', 'subgroup'] if f[key] != ALL]
    labels = {'borough': 'Borough', 'group': 'Nhóm', 'subgroup': 'Phân nhóm'}
    row = st.container(horizontal=True, vertical_alignment='center')
    row.markdown(f'**Đang lọc:** {f["start_label"]} → {f["end_label"]}'
                 + ('' if active else ' · toàn bộ 32 borough, mọi nhóm'), width='content')
    for key, value in active:
        row.button(f'{labels[key]}: {value.title() if key != "borough" else value}  ✕',
                   key=f'clear_{key}', on_click=clear, args=(key,), width='content')


def previous_year_total(facts, f):
    """Tổng số vụ cùng kỳ năm trước theo đúng bộ lọc; None nếu chưa có dữ liệu."""
    start, end = f['start'] - pd.DateOffset(years=1), f['end'] - pd.DateOffset(years=1)
    if start < facts.month.min():
        return None
    rows = facts[facts.month.between(start, end)]
    for key, column in [('borough', 'borough_name'), ('group', 'crime_group'), ('subgroup', 'crime_subgroup')]:
        if f[key] != ALL:
            rows = rows[rows[column] == f[key]]
    return int(rows.crime_count.sum())


def kpis(facts, f, s):
    total = int(s['filtered'].crime_count.sum())
    previous = previous_year_total(facts, f)
    delta = None if not previous else f'{(total / previous - 1) * 100:+.1f}% so với cùng kỳ năm trước'
    columns = st.columns(4)
    columns[0].metric('Số vụ trong kỳ', f'{total:,}', delta=delta, delta_color='inverse')
    columns[1].metric('Vụ / 1.000 dân trong kỳ', f'{total / s["population"] * 1000:,.2f}')
    columns[2].metric('Dân số Census 2021', f'{s["population"]:,}')
    fte = s['snapshot'].officer_fte.sum(min_count=1)
    coverage = int(s['snapshot'].officer_fte.notna().sum())
    columns[3].metric(f'DWO FTE đã biết · {f["end_label"]}', 'Chưa có' if pd.isna(fte) else f'{fte:,.1f}')
    if coverage < len(s['scope_dim']):
        st.warning(f'FTE chỉ có số liệu cho {coverage}/{len(s["scope_dim"])} borough trong tháng {f["end_label"]}. '
                   'Tổng FTE hiển thị là phần đã biết; nguồn thiếu Camden từ 08/2024, không quy thành 0.')
    st.caption('Tỷ lệ dùng dân số cố định năm 2021; kỳ dài hơn tích lũy nhiều vụ hơn. DWO FTE là quân số đội địa bàn, '
               'không phải toàn bộ cảnh sát. Mốc ghi nhận CONNECT: 03/2024.')
    return coverage


# Tab 1: Tổng quan
def add_connect_marker(fig, months):
    """Đánh dấu mốc CONNECT nếu nằm trong khoảng đang xem (thêm sau đường trung bình)."""
    if months.min() <= CONNECT_START <= months.max():
        fig.add_shape(type='line', x0=CONNECT_START, x1=CONNECT_START, y0=0, y1=1, yref='paper',
                      line=dict(color=MUTED, width=1, dash='dot'))
        fig.add_annotation(x=CONNECT_START, y=1, yref='paper', text='CONNECT 03/2024', showarrow=False,
                           xanchor='left', yanchor='top', font=dict(color=MUTED, size=11))


def render_overview(dim, f, s, epoch):
    ranking = with_rate(s['context'].groupby('borough_name', as_index=False).crime_count.sum(), dim)
    metric, measure = f['metric'], f['measure']
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader('Bản đồ phân bố theo borough')
        fig = px.choropleth(ranking, geojson=geography('boroughs'), locations='borough_name',
                            featureidkey='properties.borough_name', color=metric,
                            color_continuous_scale=SEQUENTIAL, hover_name='borough_name',
                            custom_data=['borough_name'], labels=LABELS,
                            hover_data={'crime_count': ':,', 'rate_per_1000': ':.2f', 'population_2021': ':,',
                                        'borough_name': False})
        fig.update_geos(fitbounds='locations', visible=False)
        key = f'borough_map_{epoch}'
        chart(fig, key, lambda key=key: select_borough(key))
    with right:
        st.subheader('Horizontal bar chart: xếp hạng borough')
        top = ranking.nlargest(15, metric).sort_values(metric)
        top['highlight'] = np.where(top.borough_name == f['borough'], ORANGE, BLUE)
        fig = px.bar(top, x=metric, y='borough_name', custom_data=['borough_name'],
                     labels={metric: measure, 'borough_name': ''})
        fig.update_traces(marker_color=top.highlight)
        average = ranking[metric].mean()
        fig.add_vline(x=average, line_dash='dash', line_color=ORANGE,
                      annotation_text=f'TB {len(ranking)} borough: {average:,.2f}', annotation_position='top right',
                      annotation_y=1.0, annotation_yanchor='bottom', annotation_font_color=ORANGE)
        key = f'borough_rank_{epoch}'
        chart(fig, key, lambda key=key: select_borough(key))
    st.caption(f'Bản đồ và xếp hạng: toàn bộ borough trong bộ lọc thời gian / loại tội phạm (cột cam = borough đang chọn). '
               f'Phạm vi chi tiết đang chọn: {f["borough"]}.')

    trend = s['filtered'].groupby('month', as_index=False).crime_count.sum()
    trend['rate_per_1000'] = trend.crime_count / s['population'] * 1000
    fig = px.line(trend, x='month', y=metric, markers=True, title=f'Xu hướng · {f["borough"]} · Line chart',
                  labels={'month': 'Tháng', metric: measure})
    fig.update_traces(line_color=BLUE, marker_color=BLUE)
    average = trend[metric].mean()
    fig.add_hline(y=average, line_dash='dash', line_color=ORANGE,
                  annotation_text=f'TB tháng trong kỳ: {average:,.2f}', annotation_position='top right')
    add_connect_marker(fig, trend.month)
    chart(fig, 'trend', spikes=True)


# Tab 2: Cơ cấu và phân phối
def render_composition(dim, f, s, colors, epoch):
    filtered, metric, measure = s['filtered'], f['metric'], f['measure']
    left, right = st.columns(2)
    with left:
        # Cột nhóm tội phạm bỏ qua bộ lọc nhóm để luôn thấy đủ các nhóm và click chọn được.
        groups = (s['by_borough'].groupby('crime_group', as_index=False).crime_count.sum()
                  .query('crime_count > 0').sort_values('crime_count'))
        groups['color'] = np.where(groups.crime_group == f['group'], ORANGE, BLUE)
        fig = px.bar(groups, x='crime_count', y='crime_group', custom_data=['crime_group'],
                     title='Bar chart: số vụ theo nhóm (click để lọc)', labels=LABELS)
        fig.update_traces(marker_color=groups.color)
        fig.update_yaxes(title='')
        key = f'group_bar_{epoch}'
        chart(fig, key, lambda key=key: select_group(key))
    with right:
        shares = filtered.groupby('crime_group', as_index=False).crime_count.sum()
        shares['label'] = np.where(shares.crime_group.map(colors) == OTHER_COLOR, OTHER, shares.crime_group)
        shares = shares.groupby('label', as_index=False).crime_count.sum().query('crime_count > 0')
        chart(px.pie(shares, names='label', values='crime_count', hole=.55, color='label',
                     color_discrete_map=colors, title='Donut chart: tỷ trọng tội phạm'), 'donut')

    tree = filtered.groupby(['crime_group', 'crime_subgroup'], as_index=False).crime_count.sum()
    tree = tree[tree.crime_count > 0]
    if not tree.empty:
        chart(px.treemap(tree, path=['crime_group', 'crime_subgroup'], values='crime_count', color='crime_group',
                         color_discrete_map=colors, title='Treemap: nhóm và phân nhóm')
              .update_traces(textfont_color='white', root_color='white'), 'treemap')

    rows = with_rate(filtered.groupby(['borough_name', 'month'], as_index=False).crime_count.sum(), dim)
    relative = st.toggle('Heatmap theo chỉ số so với trung bình các borough cùng tháng (1 = trung bình)',
                         value=True, key='heat_relative')
    heat = rows.pivot(index='borough_name', columns='month', values=metric)
    heat.columns = heat.columns.strftime('%Y-%m')
    heat = heat.loc[heat.mean(axis=1).sort_values(ascending=False).index]
    if relative and len(heat) > 1:
        heat = heat / heat.mean()
        fig = px.imshow(heat, aspect='auto', color_continuous_scale=DIVERGING,
                        range_color=(0, 2), labels={'color': 'Chỉ số', 'x': 'Tháng', 'y': ''},
                        title='Heatmap: borough theo tháng · chỉ số so với trung bình (màu chặn ở 2)')
    else:
        fig = px.imshow(heat, aspect='auto', color_continuous_scale=SEQUENTIAL,
                        labels={'color': measure, 'x': 'Tháng', 'y': ''}, title=f'Heatmap: borough theo tháng · {measure}')
    chart(fig, 'heatmap', height=max(410, 22 * len(heat) + 120))

    group_rates = with_rate(filtered.groupby(['borough_name', 'month', 'crime_group'], as_index=False)
                            .crime_count.sum(), dim)
    group_rates = group_rates[(group_rates.rate_per_1000 > 0)                   # thang log không nhận 0
                              & ~group_rates.crime_group.isin(minor_groups(load('crime_borough')))]
    order = group_rates.groupby('crime_group').rate_per_1000.median().sort_values(ascending=False).index.tolist()
    left, right = st.columns(2)
    with left:
        fig = px.box(group_rates, x='rate_per_1000', y='crime_group', points='outliers', log_x=True,
                     category_orders={'crime_group': order}, title='Boxplot: tỷ lệ borough-tháng theo nhóm (thang log)',
                     labels={'rate_per_1000': 'Vụ / 1.000 dân / tháng', 'crime_group': ''})
        fig.update_traces(marker_color=BLUE, line_color=BLUE)
        chart(fig, 'box')
    with right:
        fig = px.histogram(rows, x='rate_per_1000', nbins=30, title='Histogram: tần suất tỷ lệ borough-tháng',
                           labels={'rate_per_1000': 'Vụ / 1.000 dân / tháng'})
        fig.update_traces(marker_color=BLUE, marker_line_color='white', marker_line_width=1)
        median = rows.rate_per_1000.median()
        fig.add_vline(x=median, line_dash='dash', line_color=ORANGE, annotation_text=f'Trung vị {median:.2f}')
        fig.update_yaxes(title='Số borough-tháng')
        chart(fig, 'histogram')


# Tab 3: Nguồn lực cảnh sát
def render_security(f, s, coverage, epoch):
    st.subheader('Nguồn lực đội cảnh sát địa bàn')
    st.caption('Scatter dùng trung bình FTE của cả kỳ đang lọc và tỷ lệ tội phạm cả kỳ. Hoạt động điều chuyển và FTE '
               'có dữ liệu từ 08/2021. Bộ lọc nhóm tội phạm chỉ tác động trục tỷ lệ, không lọc quân số.')
    period = s['monthly_all']
    security = (period.groupby('borough_name', as_index=False)
                .agg(officers_per_10000=('officers_per_10000', 'mean'), officer_fte=('officer_fte', 'mean'),
                     abstraction_share_pct=('abstraction_share_pct', 'mean'),
                     abstraction_hours=('abstraction_hours', 'sum'), population_2021=('population_2021', 'first')))
    counts = s['context'].groupby('borough_name', as_index=False).crime_count.sum()
    data = security.merge(counts, on='borough_name', validate='one_to_one')
    data['rate_per_1000'] = data.crime_count / data.population_2021 * 1000
    missing = data[data.officers_per_10000.isna()].borough_name.tolist()
    data = data.dropna(subset=['officers_per_10000'])
    st.caption(f'Độ phủ FTE tháng {f["end_label"]}: {coverage}/{len(s["scope_dim"])} borough. '
               'Scatter luôn hiện mọi borough; borough đang chọn có viền cam.'
               + (f' Không có FTE trong kỳ (bỏ khỏi scatter, không điền 0): {", ".join(missing)}.' if missing else ''))
    if data.empty:
        st.info('Không có dữ liệu nguồn lực cho kỳ đang chọn.')
        return

    fig = px.scatter(data, x='officers_per_10000', y='rate_per_1000', size='population_2021', hover_name='borough_name',
                     custom_data=['borough_name'], color='abstraction_share_pct', color_continuous_scale=SEQUENTIAL,
                     title=f'Scatter plot: nguồn lực và tỷ lệ tội phạm · {f["start_label"]} → {f["end_label"]}',
                     labels={'officers_per_10000': 'DWO FTE / 10.000 dân (TB kỳ)', 'rate_per_1000': 'Vụ / 1.000 dân (cả kỳ)',
                             'abstraction_share_pct': '% phút điều chuyển', 'population_2021': 'Dân số 2021'})
    if len(data) >= 3:
        slope, intercept = np.polyfit(data.officers_per_10000, data.rate_per_1000, 1)
        r = data.officers_per_10000.corr(data.rate_per_1000)
        xs = np.linspace(data.officers_per_10000.min(), data.officers_per_10000.max(), 50)
        fig.add_scatter(x=xs, y=slope * xs + intercept, mode='lines', name=f'Hồi quy tuyến tính, r = {r:.2f}',
                        line=dict(color=ORANGE, dash='dash'), hoverinfo='skip')
        extremes = pd.concat([data.nlargest(2, 'rate_per_1000'), data.nsmallest(1, 'officers_per_10000'),
                              data.nlargest(1, 'officers_per_10000')]).drop_duplicates('borough_name')
        for row in extremes.itertuples():
            fig.add_annotation(x=row.officers_per_10000, y=row.rate_per_1000, text=row.borough_name, showarrow=False,
                               xanchor='left', xshift=10, font=dict(size=11, color=MUTED))
    chosen = data[data.borough_name == f['borough']]
    if not chosen.empty:
        fig.add_scatter(x=chosen.officers_per_10000, y=chosen.rate_per_1000, mode='markers', name=f['borough'],
                        marker=dict(size=26, color='rgba(0,0,0,0)', line=dict(color=ORANGE, width=3)),
                        hoverinfo='skip')
    key = f'scatter_{epoch}'
    chart(fig, key, lambda key=key: select_borough(key), spikes=True)
    st.caption('Mối liên hệ trên biểu đồ là tương quan. Nguồn lực có thể được phân bổ để đáp ứng tình hình tội phạm.')

    rank = load('security_by_rank')
    rank = rank[(rank.month == f['end']) & rank.borough_name.isin(s['scope_dim'].borough_name)]
    order = rank.assign(total=rank.drop(columns=['borough_name', 'month']).sum(axis=1)).sort_values(
        'total', ascending=False).borough_name.tolist()
    rank_long = rank.melt(id_vars=['borough_name', 'month'], var_name='rank', value_name='FTE')
    chart(px.bar(rank_long, x='borough_name', y='FTE', color='rank', barmode='stack',
                 category_orders={'borough_name': order}, color_discrete_sequence=CATEGORICAL,
                 title=f'Stacked bar chart: quân số theo cấp bậc · {f["end_label"]}',
                 labels={'borough_name': '', 'rank': 'Cấp bậc'}), 'rank_fte')
    st.dataframe(data[['borough_name', 'officer_fte', 'officers_per_10000', 'abstraction_hours', 'abstraction_share_pct']]
                 .sort_values('officers_per_10000', ascending=False), hide_index=True,
                 column_config={'borough_name': 'Borough', 'officer_fte': st.column_config.NumberColumn('FTE TB', format='%.1f'),
                                'officers_per_10000': st.column_config.NumberColumn('FTE / 10.000 dân', format='%.2f'),
                                'abstraction_hours': st.column_config.NumberColumn('Giờ điều chuyển', format='%,.0f'),
                                'abstraction_share_pct': st.column_config.NumberColumn('% điều chuyển', format='%.1f')})


# Tab 4: Chi tiết LSOA
def render_lsoa(f, s):
    if f['borough'] == ALL:
        st.info('Chọn một borough (sidebar, bản đồ hoặc cột xếp hạng) để xem LSOA thuộc địa bàn đó.')
        return
    st.subheader(f'LSOA · {f["borough"]}')
    st.caption('MPS không công bố Sexual Offences tại LSOA. Phạm vi ghi nhận và phân loại có thể khác bảng borough; '
               'không dùng tổng LSOA để thay tổng borough.')
    lsoa = load(f'lsoa_{s["scope_dim"].borough_code.iloc[0]}')
    lsoa = lsoa[lsoa.month.between(f['start'], f['end'])]
    if f['group'] != ALL:
        lsoa = lsoa[lsoa.crime_group == f['group']]
    if f['subgroup'] != ALL:
        lsoa = lsoa[lsoa.crime_subgroup == f['subgroup']]
    local_dim = load('dim_lsoa')
    local_dim = local_dim[local_dim.borough_name == f['borough']]
    counts = lsoa.groupby('lsoa_code', observed=True, as_index=False).crime_count.sum()
    counts['lsoa_code'] = counts.lsoa_code.astype(str)
    areas = local_dim.merge(counts, on='lsoa_code', how='left', validate='one_to_one')
    areas['rate_per_1000'] = areas.crime_count / areas.population_2021 * 1000

    options = [ALL] + sorted(areas.lsoa_code)
    if st.session_state.get('lsoa_choice', ALL) not in options:
        st.session_state['lsoa_choice'] = ALL
    names = dict(zip(areas.lsoa_code, areas.lsoa_name))
    chosen = st.selectbox('LSOA', options, key='lsoa_choice', format_func=lambda x: names.get(x, x))
    if not areas.crime_count.notna().any():
        st.info('Không có dữ liệu LSOA cho nhóm/phân nhóm và thời gian này; không coi là không có tội phạm.')
        return

    plot_areas = areas if chosen == ALL else areas[areas.lsoa_code == chosen]
    fig = px.choropleth(plot_areas, geojson=geography('lsoa', f['borough']), locations='lsoa_code',
                        featureidkey='properties.lsoa_code', color=f['metric'], color_continuous_scale=SEQUENTIAL,
                        labels=LABELS, hover_name='lsoa_name', title='Choropleth map: LSOA',
                        hover_data={'population_2021': ':,', 'crime_count': ':,', 'rate_per_1000': ':.2f', 'lsoa_code': False})
    fig.update_geos(fitbounds='locations', visible=False)
    chart(fig, 'lsoa_map')

    history = lsoa if chosen == ALL else lsoa[lsoa.lsoa_code == chosen]
    local_trend = history.groupby('month', as_index=False).crime_count.sum()
    fig = px.line(local_trend, x='month', y='crime_count', markers=True, title='Line chart: số vụ tại LSOA đang chọn',
                  labels={'month': 'Tháng', 'crime_count': 'Số vụ'})
    fig.update_traces(line_color=BLUE, marker_color=BLUE)
    average = local_trend.crime_count.mean()
    fig.add_hline(y=average, line_dash='dash', line_color=ORANGE, annotation_text=f'TB tháng trong kỳ: {average:,.2f}',
                  annotation_position='top right')
    chart(fig, 'lsoa_trend', spikes=True)
    st.dataframe(plot_areas[['lsoa_code', 'lsoa_name', 'crime_count', 'population_2021', 'rate_per_1000']]
                 .sort_values('rate_per_1000', ascending=False), hide_index=True,
                 column_config={'lsoa_code': 'Mã LSOA', 'lsoa_name': 'Tên LSOA', 'crime_count': 'Số vụ',
                                'population_2021': 'Dân số 2021',
                                'rate_per_1000': st.column_config.NumberColumn('Vụ / 1.000 dân', format='%.2f')})


# Tab 5: Dự báo
def span(frame):
    return f'{frame.month.min():%m/%Y}–{frame.month.max():%m/%Y}'


def render_forecast(f, s):
    st.subheader(f'Dự báo tổng số vụ · {f["borough"]}')
    forecast = load('forecast')
    forecast = forecast[forecast.borough_name.isin(s['scope_dim'].borough_name)]
    train, test, future = (forecast[forecast.split == name] for name in ['train', 'test', 'forecast'])
    st.caption(f'Mô hình tổng tội phạm theo borough, không áp dụng bộ lọc nhóm/phân nhóm và thời gian của các tab mô tả. '
               f'Train: {span(train)}; test: {span(test)}; dự báo: {span(future)}. Đường dự báo không phải quan sát thực.')
    totals = forecast.groupby(['month', 'split'], as_index=False)[['actual', 'predicted', 'baseline']].sum(min_count=1)
    test_totals, future_totals = totals[totals.split == 'test'], totals[totals.split == 'forecast']

    fig = go.Figure()
    fig.add_vrect(x0=test_totals.month.min(), x1=test_totals.month.max(), fillcolor=BLUE, opacity=.06, line_width=0,
                  annotation_text='Test', annotation_position='top left')
    fig.add_vrect(x0=future_totals.month.min(), x1=future_totals.month.max(), fillcolor=ORANGE, opacity=.08, line_width=0,
                  annotation_text='Dự báo', annotation_position='top left')
    fig.add_scatter(x=totals.month, y=totals.actual, name='Thực tế', line=dict(color=BLUE, width=2))
    fig.add_scatter(x=test_totals.month, y=test_totals.predicted, name='Linear Regression (test)',
                    line=dict(color=ORANGE, dash='dash'))
    fig.add_scatter(x=test_totals.month, y=test_totals.baseline, name='Cùng tháng năm trước', line=dict(color=MUTED, dash='dot'))
    fig.add_scatter(x=future_totals.month, y=future_totals.predicted, name='Dự báo 6 tháng',
                    line=dict(color=ORANGE, width=3), mode='lines+markers')
    fig.update_layout(title='Line chart: thực tế, kiểm tra và dự báo', yaxis_title='Số vụ', xaxis_title='Tháng')
    chart(fig, 'forecast', spikes=True)

    evaluation = pd.DataFrame([{'Mô hình': label, 'MAE': mean_absolute_error(test_totals.actual, test_totals[col]),
                                'RMSE': np.sqrt(mean_squared_error(test_totals.actual, test_totals[col])),
                                'R²': r2_score(test_totals.actual, test_totals[col])}
                               for label, col in [('Linear Regression', 'predicted'), ('Cùng tháng năm trước', 'baseline')]])
    st.dataframe(evaluation, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format='%.2f') for c in ['MAE', 'RMSE', 'R²']})
    if evaluation.MAE.iloc[0] > evaluation.MAE.iloc[1]:
        st.info('Trong phạm vi đang chọn, Linear Regression có MAE cao hơn mô hình cùng tháng năm trước.')
    st.caption('Các biến dự báo: chỉ số thời gian, sin/cos tháng và cờ CONNECT. Mỗi borough có mô hình riêng; mô hình được '
               'huấn luyện lại trên toàn bộ dữ liệu sau khi đánh giá. Giá trị âm được chặn tại 0. Chưa ước lượng khoảng dự báo.')
    st.download_button('Tải kết quả dự báo', forecast.to_csv(index=False).encode('utf-8-sig'), 'forecast.csv', 'text/csv',
                       icon=':material/download:')


# Tab 6: Nguồn và chất lượng
def render_evidence(s):
    st.subheader('Nguồn dữ liệu và phạm vi')
    st.markdown('''- [MPS Recorded Crime](https://data.london.gov.uk/dataset/mps-recorded-crime-geographic-breakdown-exy3m)
- [ONS Census 2021 TS001](https://www.nomisweb.co.uk/sources/census_2021_bulk)
- [GLA Statistical Boundaries](https://data.london.gov.uk/dataset/statistical-gis-boundary-files-for-london-20od9)
- [MPS Dedicated Ward Officers](https://data.london.gov.uk/dataset/mps-dedicated-ward-officer-abstractions-and-strengths-e16kd)''')
    st.caption('Loại Aviation Policing, Unknown và City of London khỏi so sánh 32 borough. Dữ liệu quầy cảnh sát 2013 không '
               'tham gia dashboard hiện trạng. Bản đồ chứa dữ liệu National Statistics và Ordnance Survey, Crown copyright/'
               'database right; điều kiện sử dụng theo trang nguồn GLA.')
    quality = json.loads((ROOT / 'reports' / 'data_quality.json').read_text(encoding='utf-8'))
    joins, period = quality['join_checks'], quality['period']
    st.markdown('**Kiểm tra chất lượng** (từ `reports/data_quality.json`)')
    columns = st.columns(4)
    columns[0].metric('Kỳ dữ liệu', f'{period["months"]} tháng', help=f'{period["start"]} → {period["end"]}')
    columns[1].metric('Số vụ bảo toàn', f'{joins["crime_total_preserved"]:,}')
    columns[2].metric('Số vụ ngoài 32 borough', f'{joins["excluded_crime_total"]:,}')
    columns[3].metric('Outlier giữ lại', f'{quality["outlier_months_retained"]}')
    checks = pd.DataFrame([
        ('LSOA khớp Census + ranh giới', joins['census_boundary_lsoa']),
        ('Borough MPS', joins['mps_boroughs']),
        ('Mã LSOA có số liệu tội phạm', joins['crime_lsoa_codes']),
        ('Borough-tháng cần khớp nhân lực', joins['security_eligible_months']),
        ('Borough-tháng khớp nhân lực', joins['security_matched_months']),
        ('Borough-tháng có FTE', joins['fte_observed_months']),
        ('Borough-tháng thiếu FTE (để trống)', joins['fte_missing_months']),
    ], columns=['Kiểm tra', 'Giá trị'])
    st.dataframe(checks, hide_index=True)
    st.download_button('Tải bảng đang lọc', s['filtered'].to_csv(index=False).encode('utf-8-sig'), 'london_filtered.csv',
                       'text/csv', icon=':material/download:')


# Trang
def main():
    if not (DATA / 'monthly.parquet').exists():
        st.error('Chưa có dữ liệu đã xử lý. Chạy run_pipeline.py theo README của dự án.')
        st.stop()

    facts, dim, monthly = load('crime_borough'), load('dim_borough'), load('monthly')
    colors = group_colors(facts)
    months = sorted(facts.month.dt.strftime('%Y-%m').unique())
    f = sidebar(facts, dim, months)

    st.title('Tội phạm và nguồn lực cảnh sát London')
    st.caption(f'{f["start_label"]} đến {f["end_label"]} · 32 borough thuộc MPS · '
               'Dữ liệu ghi nhận, chưa phản ánh toàn bộ tội phạm xảy ra')
    active_filters(f)
    s = scope(facts, dim, monthly, f)
    if s['filtered'].empty:
        st.info('Không có bản ghi phù hợp với bộ lọc hiện tại. Dữ liệu không có bản ghi không được tự coi là 0.')
        st.stop()
    coverage = kpis(facts, f, s)
    epoch = st.session_state.get('chart_epoch', 0)

    tabs = st.tabs(['Tổng quan', 'Cơ cấu và phân phối', 'Nguồn lực cảnh sát', 'Chi tiết LSOA', 'Dự báo',
                    'Nguồn và chất lượng'])
    with tabs[0]:
        render_overview(dim, f, s, epoch)
    with tabs[1]:
        render_composition(dim, f, s, colors, epoch)
    with tabs[2]:
        render_security(f, s, coverage, epoch)
    with tabs[3]:
        render_lsoa(f, s)
    with tabs[4]:
        render_forecast(f, s)
    with tabs[5]:
        render_evidence(s)


main()
