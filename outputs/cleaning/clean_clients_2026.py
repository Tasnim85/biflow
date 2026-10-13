# Generated from a validated allowlisted plan. Run from this project.
from core.cleaning_engine import execute_plan

PLAN = {'dataset': 'clients_2026',
 'steps': [{'operation': 'strip',
            'column': 'location',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in location; 12 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained. Reused from a prior validated recipe with matching semantic '
                           'class.',
            'origin': 'recipe:customers'},
           {'operation': 'normalize_categories',
            'column': 'location',
            'params': {},
            'explanation': 'Canonical casefolded categories; 99 noncanonical cells. No fuzzy '
                           'merging of distinct categories. Reused from a prior validated recipe '
                           'with matching semantic class.',
            'origin': 'recipe:customers'},
           {'operation': 'strip',
            'column': 'email_address',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in email_address; 38 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained. Reused from a prior validated recipe with matching semantic '
                           'class.',
            'origin': 'recipe:customers'},
           {'operation': 'lowercase',
            'column': 'email_address',
            'params': {},
            'explanation': 'Normalize email case under the demo policy. Reused from a prior '
                           'validated recipe with matching semantic class.',
            'origin': 'recipe:customers'},
           {'operation': 'validate_email',
            'column': 'email_address',
            'params': {},
            'explanation': 'Mask invalid email formats (2 detected). Reused from a prior validated '
                           'recipe with matching semantic class.',
            'origin': 'recipe:customers'},
           {'operation': 'strip',
            'column': 'client_identifier',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in client_identifier; 13 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained. Reused from a prior validated recipe with matching semantic '
                           'class.',
            'origin': 'recipe:customers'},
           {'operation': 'strip',
            'column': 'customer_age',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in customer_age; 12 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained. Reused from a prior validated recipe with matching semantic '
                           'class.',
            'origin': 'recipe:customers'},
           {'operation': 'convert_numeric',
            'column': 'customer_age',
            'params': {},
            'explanation': 'Convert currency/number strings to nullable numeric values; 99 '
                           'storage-type anomalies. Reused from a prior validated recipe with '
                           'matching semantic class.',
            'origin': 'recipe:customers'},
           {'operation': 'remove_impossible_values',
            'column': 'customer_age',
            'params': {'min': 0, 'max': 120, 'integer': True},
            'explanation': 'Age must be an integer between 0 and 120.',
            'origin': 'local_rule'},
           {'operation': 'strip',
            'column': 'telephone',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in telephone; 13 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained. Reused from a prior validated recipe with matching semantic '
                           'class.',
            'origin': 'recipe:customers'},
           {'operation': 'normalize_phone',
            'column': 'telephone',
            'params': {},
            'explanation': 'Remove phone presentation separators and convert international 00 '
                           'prefix to +. Reused from a prior validated recipe with matching '
                           'semantic class.',
            'origin': 'recipe:customers'},
           {'operation': 'validate_phone',
            'column': 'telephone',
            'params': {},
            'explanation': 'Require 8–15 digits with optional +; 2 invalid phones detected. No '
                           'country prefix is invented. Reused from a prior validated recipe with '
                           'matching semantic class.',
            'origin': 'recipe:customers'},
           {'operation': 'strip',
            'column': 'signup_date',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in signup_date; 10 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained. Reused from a prior validated recipe with matching semantic '
                           'class.',
            'origin': 'recipe:customers'},
           {'operation': 'convert_dates',
            'column': 'signup_date',
            'params': {'datetime': False},
            'explanation': 'Parse ISO/day-first slash dates; preserve timestamp UTC where '
                           'applicable; invalid values become missing. Reused from a prior '
                           'validated recipe with matching semantic class.',
            'origin': 'recipe:customers'},
           {'operation': 'strip',
            'column': 'full_name',
            'params': {},
            'explanation': 'Normalize surrounding spaces and blank cells in full_name; 12 '
                           'formatting anomalies detected. Identifier case and leading zeros are '
                           'retained. Reused from a prior validated recipe with matching semantic '
                           'class.',
            'origin': 'recipe:customers'},
           {'operation': 'remove_duplicates',
            'column': None,
            'params': {},
            'explanation': 'Remove identical normalized rows; 5 raw duplicates detected.',
            'origin': 'local_rule'}],
 'missing_policy': 'Preserve unknown business values; explicit fill_missing is opt-in only.',
 'provider': 'local_rules',
 'provider_message': 'No API key required.',
 'reused_steps': 14}

def clean(df, semantics):
    return execute_plan(df, PLAN, semantics)["cleaned"]
