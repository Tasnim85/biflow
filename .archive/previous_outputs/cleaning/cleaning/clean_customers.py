# Generated from a validated allowlisted plan. Run from this project.
from core.cleaning_engine import execute_plan

PLAN = {'dataset': 'customers',
 'steps': [{'operation': 'strip',
            'column': 'customer_id',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in customer_id; 27 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'first_name',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in first_name; 25 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'last_name',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in last_name; 25 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'email',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in email; 82 formatting '
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
           {'operation': 'strip',
            'column': 'phone',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in phone; 23 formatting '
                           'anomalies detected. Identifier case and leading zeros are retained.',
            'origin': 'local_rule'},
           {'operation': 'normalize_phone',
            'column': 'phone',
            'params': {},
            'explanation': 'Remove phone presentation separators and convert international 00 '
                           'prefix to +.',
            'origin': 'local_rule'},
           {'operation': 'validate_phone',
            'column': 'phone',
            'params': {},
            'explanation': 'Require 8–15 digits with optional +; 2 invalid phones detected. No '
                           'country prefix is invented.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'city',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in city; 24 formatting '
                           'anomalies detected. Identifier case and leading zeros are retained.',
            'origin': 'local_rule'},
           {'operation': 'normalize_categories',
            'column': 'city',
            'params': {},
            'explanation': 'Canonical casefolded categories; 198 noncanonical cells. No fuzzy '
                           'merging of distinct categories.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'age',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in age; 27 formatting '
                           'anomalies detected. Identifier case and leading zeros are retained.',
            'origin': 'local_rule'},
           {'operation': 'convert_numeric',
            'column': 'age',
            'params': {},
            'explanation': 'Convert currency/number strings to nullable numeric values; 199 '
                           'storage-type anomalies.',
            'origin': 'local_rule'},
           {'operation': 'remove_impossible_values',
            'column': 'age',
            'params': {'min': 0, 'max': 120, 'integer': True},
            'explanation': 'Age must be an integer between 0 and 120.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'registration_date',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in registration_date; 23 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained.',
            'origin': 'local_rule'},
           {'operation': 'convert_dates',
            'column': 'registration_date',
            'params': {'datetime': False},
            'explanation': 'Parse ISO/day-first slash dates; preserve timestamp UTC where '
                           'applicable; invalid values become missing.',
            'origin': 'local_rule'},
           {'operation': 'remove_duplicates',
            'column': None,
            'params': {},
            'explanation': 'Remove identical normalized rows; 10 raw duplicates detected.',
            'origin': 'local_rule'}],
 'missing_policy': 'Preserve unknown business values; explicit fill_missing is opt-in only.',
 'provider': 'local_rules',
 'provider_message': 'No API key required.',
 'reused_steps': 0}

def clean(df, semantics):
    return execute_plan(df, PLAN, semantics)["cleaned"]
