# Generated from a validated allowlisted plan. Run from this project.
from core.cleaning_engine import execute_plan

PLAN = {'dataset': 'employees',
 'steps': [{'operation': 'strip',
            'column': 'employee_id',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in employee_id; 7 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'employee_name',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in employee_name; 5 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'department',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in department; 6 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'normalize_categories',
            'column': 'department',
            'params': {},
            'explanation': 'Canonical casefolded categories; 50 noncanonical cells. No fuzzy '
                           'merging of distinct categories.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'salary',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in salary; 6 formatting '
                           'anomalies detected. Identifier case and leading zeros are retained.',
            'origin': 'local_rule'},
           {'operation': 'convert_numeric',
            'column': 'salary',
            'params': {},
            'explanation': 'Convert currency/number strings to nullable numeric values; 50 '
                           'storage-type anomalies.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'hire_date',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in hire_date; 6 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'convert_dates',
            'column': 'hire_date',
            'params': {'datetime': False},
            'explanation': 'Parse ISO/day-first slash dates; preserve timestamp UTC where '
                           'applicable; invalid values become missing.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'email',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in email; 20 formatting '
                           'anomalies detected. Identifier case and leading zeros are retained.',
            'origin': 'local_rule'},
           {'operation': 'lowercase',
            'column': 'email',
            'params': {},
            'explanation': 'Normalize email case under the demo policy.',
            'origin': 'local_rule'},
           {'operation': 'validate_email',
            'column': 'email',
            'params': {},
            'explanation': 'Mask invalid email formats (2 detected).',
            'origin': 'local_rule'},
           {'operation': 'remove_duplicates',
            'column': None,
            'params': {},
            'explanation': 'Remove identical normalized rows; 2 raw duplicates detected.',
            'origin': 'local_rule'}],
 'missing_policy': 'Preserve unknown business values; explicit fill_missing is opt-in only.',
 'provider': 'local_rules',
 'provider_message': 'No API key required.',
 'reused_steps': 0}

def clean(df, semantics):
    return execute_plan(df, PLAN, semantics)["cleaned"]
