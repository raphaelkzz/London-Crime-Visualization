from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'data' / 'processed'
REPORTS = ROOT / 'reports'
BOROUGH_ALIASES = {
    'Barking & Dagenham': 'Barking and Dagenham',
    'Hammersmith & Fulham': 'Hammersmith and Fulham',
    'Kensington & Chelsea': 'Kensington and Chelsea',
    'Kingston': 'Kingston upon Thames',
    'Richmond': 'Richmond upon Thames',
}


def borough_names(values):
    return values.astype('string').str.strip().str.replace(
        r' Borough$', '', regex=True
    ).replace(BOROUGH_ALIASES)


def ratio(numerator, denominator, scale=1):
    return numerator.div(denominator.where(denominator > 0)).mul(scale)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def temporal_fields(frame):
    result = frame.copy()
    result['year'] = result.month.dt.year
    result['month_number'] = result.month.dt.month
    result['quarter'] = result.month.dt.to_period('Q').astype(str)
    result['data_regime'] = np.where(result.month < pd.Timestamp('2024-03-01'), 'legacy', 'connect')
    return result
