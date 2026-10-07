"""Bước 2 của pipeline: 6 biểu đồ EDA tĩnh (Matplotlib / Seaborn) và ghi chú insight.

Đọc dữ liệu đã xử lý trong data/processed, lưu PNG vào reports/figures:

    01_monthly_trend.png         Line chart          xu hướng tổng số vụ + trung bình trượt 12 tháng
    02_borough_ranking.png       Horizontal bar chart  tỷ lệ 12 tháng của 32 borough + mốc trung bình
    03_group_boxplot.png         Boxplot (thang log)   phân phối tỷ lệ theo nhóm tội phạm
    04_borough_group_heatmap.png Heatmap              chỉ số so với trung bình 32 borough
    05_workforce_scatter.png     Scatter plot         FTE ward officer và tỷ lệ tội phạm
    06_rate_histogram.png        Histogram + KDE      phân phối tỷ lệ borough × tháng

"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter

from common import OUT, REPORTS, ratio

# --- Giao diện chung -----------------------------------------------------------------------
BLUE, ORANGE, INK, MUTED, GRID, NEUTRAL = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3de', '#ececea'
CONNECT_START = pd.Timestamp('2024-03-01')
MINOR_GROUP_SHARE = .001          # nhóm < 0,1% tổng số vụ (NFIB Fraud, Fraud and Forgery) bị loại khỏi hình 03–04
HEATMAP_RANGE = (0.2, 3)          # chặn màu heatmap; giá trị ngoài khoảng dùng màu đậm nhất
FIGURES = REPORTS / 'figures'

plt.rcParams.update({
    'figure.dpi': 110, 'savefig.dpi': 160, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': MUTED,
    'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED, 'text.color': INK,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': .8, 'axes.axisbelow': True,
    'axes.titleweight': 'bold', 'axes.titlesize': 12, 'axes.titlelocation': 'left', 'font.size': 10,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / name, bbox_inches='tight')
    plt.close(fig)


def thousands(value, _):
    return f'{value / 1000:,.0f}k'


# Chuẩn bị dữ liệu
def load():
    monthly = pd.read_parquet(OUT / 'monthly.parquet')
    facts = pd.read_parquet(OUT / 'crime_borough.parquet')
    population = pd.read_parquet(OUT / 'dim_borough.parquet')
    return monthly, facts, population


def group_rates(facts, population):
    """Tỷ lệ / 1.000 dân theo (borough, tháng, nhóm tội phạm)."""
    groups = (facts.groupby(['borough_name', 'month', 'crime_group'], as_index=False).crime_count.sum()
              .merge(population[['borough_name', 'population_2021']], on='borough_name', validate='many_to_one'))
    groups['rate'] = ratio(groups.crime_count, groups.population_2021, 1000)
    return groups


def minor_groups(facts):
    """Nhóm gần như không có số liệu ở MPS → chỉ số tương đối chỉ là nhiễu."""
    totals = facts.groupby('crime_group').crime_count.sum()
    return totals[totals < MINOR_GROUP_SHARE * totals.sum()].index.tolist()


# 01 Line chart
def plot_trend(monthly):
    city = monthly.groupby('month', as_index=False).crime_count.sum()
    city['ma12'] = city.crime_count.rolling(12).mean()

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(city.month, city.crime_count, color=BLUE, lw=2, label='Tổng số vụ mỗi tháng')
    ax.plot(city.month, city.ma12, color=ORANGE, lw=2, ls='--', label='Trung bình trượt 12 tháng')
    ax.axvline(CONNECT_START, color=MUTED, lw=1, ls=':')
    ax.text(CONNECT_START, 0.03, '  đổi hệ thống ghi nhận\n  CONNECT (03/2024)', transform=ax.get_xaxis_transform(),
            color=MUTED, fontsize=9, va='bottom')
    ax.set_ylim(0)
    ax.yaxis.set_major_formatter(FuncFormatter(thousands))
    ax.set(title='Line chart: Số vụ tội phạm ghi nhận mỗi tháng (32 borough MPS)', xlabel='', ylabel='Số vụ')
    ax.legend(frameon=False, loc='upper left', ncols=2)
    save(fig, '01_monthly_trend.png')
    return city


# 02 Horizontal bar chart
def plot_ranking(monthly):
    latest = monthly[monthly.month == monthly.month.max()].sort_values('rolling_12_rate')
    mean_rate = latest.rolling_12_rate.mean()

    fig, ax = plt.subplots(figsize=(8, 9))
    ax.barh(latest.borough_name, latest.rolling_12_rate, color=BLUE, height=.7)
    ax.axvline(mean_rate, color=ORANGE, lw=2, ls='--')
    ax.text(mean_rate + 4, 2, f'TB {len(latest)} borough: {mean_rate:,.0f}', color=ORANGE, va='center',
            fontsize=9, fontweight='bold')
    ax.set(title='Horizontal bar chart: Tỷ lệ tội phạm / 1.000 dân\n(12 tháng gần nhất)',
           xlabel='Vụ / 1.000 dân Census 2021', ylabel='')
    ax.grid(axis='y', visible=False)
    save(fig, '02_borough_ranking.png')
    return latest.sort_values('rolling_12_rate', ascending=False)


# 03 Boxplot
def plot_group_boxplot(groups, minor):
    data = groups[(groups.rate > 0) & ~groups.crime_group.isin(minor)]   # log không nhận giá trị 0
    order = data.groupby('crime_group').rate.median().sort_values(ascending=False).index

    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.boxplot(data=data, y='crime_group', x='rate', order=order, color=BLUE, fliersize=1.5, linewidth=1,
                flierprops={'markerfacecolor': MUTED, 'markeredgecolor': MUTED}, ax=ax)
    ax.set_xscale('log')
    ax.set_yticks(range(len(order)), [g.title() for g in order])
    ax.set(title='Boxplot: Phân phối tỷ lệ theo nhóm tội phạm (thang log)',
           xlabel='Vụ / 1.000 dân / tháng', ylabel='')
    ax.grid(axis='y', visible=False)
    save(fig, '03_group_boxplot.png')


# 04 Heatmap
def plot_heatmap(groups, minor):
    """Chỉ số = tỷ lệ 12 tháng của borough ÷ trung bình 32 borough cùng nhóm (1 = bằng trung bình)."""
    last12 = groups[groups.month > groups.month.max() - pd.DateOffset(months=12)]
    rate = (last12[~last12.crime_group.isin(minor)]
            .pivot_table(index='borough_name', columns='crime_group', values='rate', aggfunc='sum'))
    index = rate / rate.mean()
    index = index.loc[rate.sum(axis=1).sort_values(ascending=False).index,
                      rate.mean().sort_values(ascending=False).index]

    cmap = mcolors.LinearSegmentedColormap.from_list('diverging', [BLUE, NEUTRAL, ORANGE])
    norm = mcolors.TwoSlopeNorm(vcenter=1, vmin=HEATMAP_RANGE[0], vmax=HEATMAP_RANGE[1])
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(index, cmap=cmap, norm=norm, linewidths=.5, linecolor='white', ax=ax,
                cbar_kws={'label': 'Chỉ số so với trung bình 32 borough (1 = trung bình, chặn ở 3)', 'shrink': .6})
    # Ghi số thật lên các ô vượt ngưỡng màu để không mất thông tin.
    for i, borough in enumerate(index.index):
        for j, group in enumerate(index.columns):
            value = index.loc[borough, group]
            if value > HEATMAP_RANGE[1]:
                ax.text(j + .5, i + .5, f'{value:.1f}×', ha='center', va='center', color='white',
                        fontsize=8, fontweight='bold')
    ax.set_xticklabels([g.title() for g in index.columns], rotation=40, ha='right')
    ax.set(title='Heatmap: Borough nào nổi bật ở nhóm tội phạm nào? (12 tháng gần nhất)', xlabel='', ylabel='')
    ax.grid(False)
    save(fig, '04_borough_group_heatmap.png')
    return index


# 05 Scatter plot
def plot_workforce(monthly):
    """Mỗi điểm là một borough: FTE TB 12 tháng và tỷ lệ 12 tháng; borough thiếu FTE bị bỏ, không điền 0."""
    last12 = monthly[monthly.month > monthly.month.max() - pd.DateOffset(months=12)]
    data = (last12.groupby('borough_name', as_index=False)
            .agg(officers_per_10000=('officers_per_10000', 'mean'), rolling_12_rate=('rolling_12_rate', 'last')))
    dropped = data[data.officers_per_10000.isna()].borough_name.tolist()
    data = data.dropna()
    slope, intercept = np.polyfit(data.officers_per_10000, data.rolling_12_rate, 1)
    r = data.officers_per_10000.corr(data.rolling_12_rate)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.scatter(data.officers_per_10000, data.rolling_12_rate, s=55, color=BLUE, edgecolor='white',
               linewidth=1.2, zorder=3)
    xs = np.linspace(data.officers_per_10000.min(), data.officers_per_10000.max(), 50)
    ax.plot(xs, slope * xs + intercept, color=ORANGE, lw=2, ls='--', label=f'Đường hồi quy tuyến tính, r = {r:.2f}')
    labelled = pd.concat([data.nlargest(3, 'rolling_12_rate'), data.nlargest(2, 'officers_per_10000'),
                          data.nsmallest(1, 'officers_per_10000')]).drop_duplicates()
    for row in labelled.itertuples():
        ax.annotate(row.borough_name, (row.officers_per_10000, row.rolling_12_rate), xytext=(6, 4),
                    textcoords='offset points', fontsize=8, color=MUTED)
    ax.set(title='Scatter plot: FTE ward officer và tỷ lệ tội phạm theo borough',
           xlabel='FTE / 10.000 dân, TB 12 tháng', ylabel='Vụ / 1.000 dân, 12 tháng')
    ax.legend(frameon=False)
    save(fig, '05_workforce_scatter.png')
    return r, len(data), dropped


# 06 Histogram + KDE
def plot_histogram(monthly):
    values = monthly.rate_per_1000.dropna()
    median = values.median()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    sns.histplot(values, bins=40, kde=True, color=BLUE, edgecolor='white', line_kws={'color': ORANGE, 'lw': 2}, ax=ax)
    ax.axvline(median, color=MUTED, ls='--', lw=1.2)
    ax.text(median, 1.005, f' trung vị {median:.1f}', color=MUTED, transform=ax.get_xaxis_transform(), fontsize=9)
    ax.set(title='Histogram + KDE: Phân phối tỷ lệ tội phạm / 1.000 dân mỗi tháng',
           xlabel='Vụ / 1.000 dân / tháng', ylabel='Số quan sát borough × tháng')
    save(fig, '06_rate_histogram.png')
    return values


def run_eda():
    FIGURES.mkdir(parents=True, exist_ok=True)
    monthly, facts, population = load()
    groups = group_rates(facts, population)
    minor = minor_groups(facts)

    city = plot_trend(monthly)
    ranking = plot_ranking(monthly)
    plot_group_boxplot(groups, minor)
    plot_heatmap(groups, minor)
    r, n_scatter, dropped = plot_workforce(monthly)
    plot_histogram(monthly)
    print(f'Saved six EDA figures to {FIGURES}', flush=True)


if __name__ == '__main__':
    run_eda()
