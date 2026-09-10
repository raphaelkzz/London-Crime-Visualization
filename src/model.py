"""Time-ordered evaluation and six-month forecasts, one OLS model per borough."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from common import OUT, REPORTS, save_json


def features(months):
    month = pd.DatetimeIndex(months)
    t = (month.year - 2020) * 12 + month.month - 8
    return pd.DataFrame({'time_index': t,
        'month_sin': np.sin(2 * np.pi * month.month / 12),
        'month_cos': np.cos(2 * np.pi * month.month / 12),
        'connect': (month >= pd.Timestamp('2024-03-01')).astype(int)})


def scores(actual, predicted):
    return {'MAE': float(mean_absolute_error(actual, predicted)),
            'RMSE': float(np.sqrt(mean_squared_error(actual, predicted))),
            'R2': float(r2_score(actual, predicted))}


def train():
    monthly = pd.read_parquet(OUT / 'monthly.parquet')
    output, metrics, coefficients = [], [], []
    for name, rows in monthly.groupby('borough_name'):
        rows = rows.sort_values('month').reset_index(drop=True)
        assert len(rows) >= 36 and rows.month.nunique() == len(rows)
        assert list(rows.month) == list(pd.date_range(rows.month.min(), rows.month.max(), freq='MS'))
        x, y = features(rows.month), rows.crime_count.to_numpy()
        split = len(rows) - 12
        reg = LinearRegression().fit(x.iloc[:split], y[:split])
        held_out = np.maximum(0, reg.predict(x.iloc[split:]))
        baseline = y[split - 12:-12]
        for label, pred in [('Linear Regression', held_out), ('Seasonal naive', baseline)]:
            metrics.append({'borough_name': name, 'model': label, **scores(y[split:], pred)})
        for i, row in rows.iterrows():
            output.append({'borough_name': name, 'month': row.month, 'actual': row.crime_count,
                'predicted': held_out[i - split] if i >= split else np.nan,
                'baseline': baseline[i - split] if i >= split else np.nan,
                'split': 'test' if i >= split else 'train'})
        # Refit only after held-out evaluation; future predictors are calendar-derived.
        final = LinearRegression().fit(x, y)
        future = pd.date_range(rows.month.max() + pd.offsets.MonthBegin(), periods=6, freq='MS')
        predictions = np.maximum(0, final.predict(features(future)))
        for month, pred in zip(future, predictions):
            output.append({'borough_name': name, 'month': month, 'actual': np.nan,
                           'predicted': pred, 'baseline': np.nan, 'split': 'forecast'})
        coefficients.append({'borough_name': name, 'intercept': final.intercept_,
                             **dict(zip(x.columns, final.coef_))})
    forecast = pd.DataFrame(output)
    forecast.to_parquet(OUT / 'forecast.parquet', index=False)
    forecast.to_csv(OUT / 'forecast.csv', index=False)
    pd.DataFrame(metrics).to_csv(REPORTS / 'model_metrics.csv', index=False)
    pd.DataFrame(coefficients).to_csv(REPORTS / 'model_coefficients.csv', index=False)
    test = forecast[forecast.split == 'test']
    city = test.groupby('month')[['actual', 'predicted', 'baseline']].sum()
    report = {'unit': 'recorded offences per borough-month', 'test_start': str(test.month.min().date()),
        'test_end': str(test.month.max().date()), 'forecast_months': 6,
        'linear_borough_month': scores(test.actual, test.predicted),
        'baseline_borough_month': scores(test.actual, test.baseline),
        'linear_city_month': scores(city.actual, city.predicted),
        'baseline_city_month': scores(city.actual, city.baseline),
        'note': 'Negative predictions clipped to zero consistently in evaluation and forecast. No causal interpretation.'}
    save_json(REPORTS / 'model_summary.json', report)
    print(report, flush=True)


if __name__ == '__main__':
    train()
