# Generated from a validated allowlisted plan. Run from this project.
from core.cleaning_engine import execute_plan

PLAN = {'dataset': 'transactions',
 'steps': [{'operation': 'strip',
            'column': 'transaction_id',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in transaction_id; 12 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'client_id',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in client_id; 12 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'transaction_date',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in transaction_date; 12 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'convert_dates',
            'column': 'transaction_date',
            'params': {'datetime': False},
            'explanation': 'Parse ISO/day-first slash dates; preserve timestamp UTC where '
                           'applicable; invalid values become missing.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'amount',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in amount; 12 formatting '
                           'anomalies detected. Identifier case and leading zeros are retained.',
            'origin': 'local_rule'},
           {'operation': 'convert_numeric',
            'column': 'amount',
            'params': {},
            'explanation': 'Convert currency/number strings to nullable numeric values; 98 '
                           'storage-type anomalies.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'payment_method',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in payment_method; 11 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'normalize_categories',
            'column': 'payment_method',
            'params': {},
            'explanation': 'Canonical casefolded categories; 100 noncanonical cells. No fuzzy '
                           'merging of distinct categories.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'product_id',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in product_id; 13 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'remove_duplicates',
            'column': None,
            'params': {},
            'explanation': 'Remove identical normalized rows; 5 raw duplicates detected.',
            'origin': 'local_rule'}],
 'missing_policy': 'Preserve unknown business values; explicit fill_missing is opt-in only.',
 'provider': 'local_rules',
 'provider_message': 'No API key required.',
 'reused_steps': 0}

def clean(df, semantics):
    return execute_plan(df, PLAN, semantics)["cleaned"]
