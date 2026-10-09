"""Bước 3 của pipeline: dự báo số vụ theo borough bằng Linear Regression.

Mỗi borough một mô hình riêng, đánh giá theo đúng thứ tự thời gian:

    train : mọi tháng trừ 12 tháng cuối
    test  : 12 tháng cuối → so với baseline seasonal naive (giá trị cùng tháng năm trước)
    refit : huấn luyện lại trên toàn bộ chuỗi rồi dự báo 6 tháng tới

Feature chỉ suy ra từ lịch nên dự báo tương lai không cần dữ liệu chưa biết:

    time_index          số tháng kể từ tháng đầu chuỗi → xu hướng tuyến tính
    month_sin, month_cos  vị trí tháng trên vòng tròn 12 tháng → mùa vụ; tháng 12 và tháng 1 nằm cạnh nhau,
                          điều mà một biến month_number 1..12 không thể hiện được
    connect             1 từ 03/2024 → dịch mức khi đổi hệ thống ghi nhận

Dự báo âm được chặn về 0, áp dụng nhất quán cho cả test lẫn forecast.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from common import OUT, REPORTS, save_json

# Tham số
SERIES_START = pd.Timestamp('2020-08-01')   # time_index = 0 tại tháng này
CONNECT_START = pd.Timestamp('2024-03-01')
TEST_MONTHS = 12
HORIZON = 6
MIN_HISTORY = 36
FEATURES = ['time_index', 'month_sin', 'month_cos', 'connect']


def features(months):
    """Ma trận feature lịch cho một dãy tháng (đầu tháng)."""
    month = pd.DatetimeIndex(months)
    angle = 2 * np.pi * month.month / 12
    return pd.DataFrame({
        'time_index': (month.year - SERIES_START.year) * 12 + month.month - SERIES_START.month,
        'month_sin': np.sin(angle),
        'month_cos': np.cos(angle),
        'connect': (month >= CONNECT_START).astype(int),
    })


def scores(actual, predicted):
    return {'MAE': float(mean_absolute_error(actual, predicted)),
            'RMSE': float(np.sqrt(mean_squared_error(actual, predicted))),
            'R2': float(r2_score(actual, predicted))}


def check_series(rows):
    """Chuỗi phải đủ dài, không trùng tháng và không hụt tháng."""
    expected = pd.date_range(rows.month.min(), rows.month.max(), freq='MS')
    assert len(rows) >= MIN_HISTORY and rows.month.nunique() == len(rows)
    assert list(rows.month) == list(expected)


def evaluate_borough(name, rows):
    """Train/test theo thời gian; trả về bảng kết quả theo tháng và chỉ số của hai mô hình."""
    x, y = features(rows.month), rows.crime_count.to_numpy()
    split = len(rows) - TEST_MONTHS
    model = LinearRegression().fit(x.iloc[:split], y[:split])
    predicted = np.maximum(0, model.predict(x.iloc[split:]))
    baseline = y[split - 12:-12]                                   # seasonal naive: cùng tháng năm trước

    is_test = np.arange(len(rows)) >= split
    history = pd.DataFrame({'borough_name': name, 'month': rows.month, 'actual': rows.crime_count,
                            'predicted': np.nan, 'baseline': np.nan,
                            'split': np.where(is_test, 'test', 'train')})
    history.loc[is_test, 'predicted'] = predicted
    history.loc[is_test, 'baseline'] = baseline

    metrics = [{'borough_name': name, 'model': label, **scores(y[split:], pred)}
               for label, pred in [('Linear Regression', predicted), ('Seasonal naive', baseline)]]
    return history, metrics


def forecast_borough(name, rows):
    """Huấn luyện lại trên toàn bộ chuỗi (sau khi đã đánh giá) và dự báo HORIZON tháng tới."""
    x, y = features(rows.month), rows.crime_count.to_numpy()
    model = LinearRegression().fit(x, y)
    future = pd.date_range(rows.month.max() + pd.offsets.MonthBegin(), periods=HORIZON, freq='MS')
    forecast = pd.DataFrame({'borough_name': name, 'month': future, 'actual': np.nan,
                             'predicted': np.maximum(0, model.predict(features(future))),
                             'baseline': np.nan, 'split': 'forecast'})
    coefficients = {'borough_name': name, 'intercept': model.intercept_, **dict(zip(FEATURES, model.coef_))}
    return forecast, coefficients


def print_summary(report):
    print(f"Test {report['test_start']} → {report['test_end']} | dự báo {report['forecast_months']} tháng", flush=True)
    print(f"{'Cấp':<16}{'Mô hình':<20}{'MAE':>10}{'RMSE':>10}{'R2':>8}", flush=True)
    for level in ['borough_month', 'city_month']:
        for label, key in [('Linear Regression', 'linear'), ('Seasonal naive', 'baseline')]:
            s = report[f'{key}_{level}']
            print(f"{level:<16}{label:<20}{s['MAE']:>10.2f}{s['RMSE']:>10.2f}{s['R2']:>8.3f}", flush=True)


def train():
    monthly = pd.read_parquet(OUT / 'monthly.parquet')
    output, metrics, coefficients = [], [], []
    for name, rows in monthly.groupby('borough_name'):
        rows = rows.sort_values('month').reset_index(drop=True)
        check_series(rows)
        history, borough_metrics = evaluate_borough(name, rows)
        future, borough_coefficients = forecast_borough(name, rows)
        output += [history, future]
        metrics += borough_metrics
        coefficients.append(borough_coefficients)

    forecast = pd.concat(output, ignore_index=True)
    forecast.to_parquet(OUT / 'forecast.parquet', index=False)
    forecast.to_csv(OUT / 'forecast.csv', index=False)
    pd.DataFrame(metrics).to_csv(REPORTS / 'model_metrics.csv', index=False)
    pd.DataFrame(coefficients).to_csv(REPORTS / 'model_coefficients.csv', index=False)

    test = forecast[forecast.split == 'test']
    city = test.groupby('month')[['actual', 'predicted', 'baseline']].sum()
    report = {
        'unit': 'recorded offences per borough-month',
        'test_start': str(test.month.min().date()), 'test_end': str(test.month.max().date()),
        'forecast_months': HORIZON,
        'linear_borough_month': scores(test.actual, test.predicted),
        'baseline_borough_month': scores(test.actual, test.baseline),
        'linear_city_month': scores(city.actual, city.predicted),
        'baseline_city_month': scores(city.actual, city.baseline),
        'note': 'Negative predictions clipped to zero consistently in evaluation and forecast. No causal interpretation.',
    }
    save_json(REPORTS / 'model_summary.json', report)
    print_summary(report)


if __name__ == '__main__':
    train()
