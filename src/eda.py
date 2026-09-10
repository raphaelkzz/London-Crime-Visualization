"""Static figures and descriptive findings derived from processed observations."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from common import OUT, REPORTS, ratio


def run_eda():
    figures = REPORTS / 'figures'
    figures.mkdir(parents=True, exist_ok=True)
    monthly = pd.read_parquet(OUT / 'monthly.parquet')
    facts = pd.read_parquet(OUT / 'crime_borough.parquet')
    population = pd.read_parquet(OUT / 'dim_borough.parquet')
    sns.set_theme(style='whitegrid', palette=['#007C83', '#B83E58', '#DAA520', '#437BBA', '#606C38'])

    def save(name):
        plt.tight_layout()
        plt.savefig(figures / name, dpi=160, bbox_inches='tight')
        plt.close()

    city = monthly.groupby('month', as_index=False).crime_count.sum()
    fig, ax = plt.subplots(figsize=(11, 4))
    sns.lineplot(data=city, x='month', y='crime_count', ax=ax)
    ax.axvline(pd.Timestamp('2024-03-01'), ls='--', c='#B83E58', label='CONNECT recording change')
    ax.set(title='Monthly recorded crime | 32 MPS boroughs', ylabel='Recorded offences', xlabel='Month')
    ax.legend()
    save('01_monthly_trend.png')

    latest = monthly[monthly.month == monthly.month.max()].sort_values('rolling_12_rate', ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=latest.head(10), x='rolling_12_rate', y='borough_name', color='#007C83', ax=ax)
    ax.set(title='Highest rolling 12-month rates', xlabel='Offences per 1,000 Census 2021 residents', ylabel='Borough')
    save('02_borough_ranking.png')

    groups = facts.groupby(['borough_name', 'month', 'crime_group'], as_index=False).crime_count.sum().merge(population[['borough_name', 'population_2021']], on='borough_name', validate='many_to_one')
    groups['rate'] = ratio(groups.crime_count, groups.population_2021, 1000)
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.boxplot(data=groups, x='rate', y='crime_group', color='#80B5B7', ax=ax, fliersize=1)
    ax.set(title='Distribution of borough-month rates by crime group', xlabel='Offences per 1,000 Census 2021 residents', ylabel='')
    save('03_group_boxplot.png')

    last12 = groups[groups.month > groups.month.max() - pd.DateOffset(months=12)]
    heat = last12.pivot_table(index='borough_name', columns='crime_group', values='rate', aggfunc='sum')
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(heat, cmap='YlOrRd', ax=ax, cbar_kws={'label': '12-month offences per 1,000 residents'})
    ax.set(title='Borough and crime group | latest 12 months', xlabel='', ylabel='')
    save('04_borough_group_heatmap.png')

    available = monthly[monthly.month == monthly.month.max()].dropna(subset=['officers_per_10000', 'rate_per_1000'])
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(data=available, x='officers_per_10000', y='rate_per_1000', size='population_2021', sizes=(30, 300), legend=False, ax=ax)
    ax.set(title='DWO FTE and recorded crime | latest month', xlabel='DWO FTE per 10,000 residents', ylabel='Monthly offences per 1,000 residents')
    save('05_workforce_scatter.png')

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(monthly.rate_per_1000, bins=40, ax=ax, color='#B83E58')
    ax.set(title='Distribution of borough-month rates', xlabel='Monthly offences per 1,000 residents')
    save('06_rate_histogram.png')

    top = latest.iloc[0]
    last = city.iloc[-1]
    previous = city.iloc[-13]
    correlation = available[['officers_per_10000', 'rate_per_1000']].corr().iloc[0, 1]
    notes = f'''# Kết quả EDA từ dữ liệu thực

Phạm vi: 32 borough thuộc MPS, {city.month.min():%m/%Y}-{city.month.max():%m/%Y}. Tổng số vụ ghi nhận: {int(city.crime_count.sum()):,}.

1. Trong 12 tháng kết thúc {last.month:%m/%Y}, {top.borough_name} có tỷ lệ cao nhất: {top.rolling_12_rate:.2f} vụ/1.000 cư dân Census 2021. Mẫu số là cư dân thường trú, chưa phản ánh khách du lịch và người đi làm.
2. Tháng {last.month:%m/%Y} ghi nhận {int(last.crime_count):,} vụ, thay đổi {(last.crime_count/previous.crime_count-1)*100:.2f}% so với cùng tháng năm trước. Đây là thống kê mô tả; chưa chứng minh nguyên nhân tăng/giảm.
3. Tương quan Pearson giữa FTE DWO/10.000 dân và số vụ/1.000 dân trong tháng cuối: {correlation:.3f}, trên {len(available)} borough. Phân bổ cảnh sát có thể phản ứng với mức crime; không suy ra tác động nhân quả.
4. Có {int(monthly.outlier_iqr.sum())} borough-month được gắn cờ IQR và giữ lại. Các đỉnh thực tế vẫn cần xuất hiện trong phân tích.
5. Hình 01 đánh dấu mốc 03/2024. Thay đổi hệ thống ghi nhận và khác biệt phân loại có thể ảnh hưởng so sánh trước/sau mốc này.

Các hình 01-06 trong `figures/` là kết quả Matplotlib/Seaborn từ toàn bộ dữ liệu đã xử lý. Cần diễn giải sâu thêm theo câu hỏi nghiên cứu trước khi đưa vào báo cáo cuối kỳ.
'''
    (REPORTS / 'INSIGHTS.md').write_text(notes, encoding='utf-8')
    print(f'Saved six EDA figures and findings to {REPORTS}', flush=True)


if __name__ == '__main__':
    run_eda()
