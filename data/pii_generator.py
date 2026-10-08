"""Separate PII demo copy; original seven-column schema stays untouched."""
from data.dirty_generator import generate_dirty_dataset

DEMO_NAMES = ["Amina Exemple", "Karim Fictif", "Lina Demo", "Sami Test"]


def generate_pii_dataset():
    data = generate_dirty_dataset().copy(deep=True)
    size = len(data)
    data["full_name"] = [DEMO_NAMES[i % 4] for i in range(size)]
    data["email"] = [f"client{i % 40:03d}@example.com" for i in range(size)]
    # Reserved North American fictional phone range; deliberately limited demo scope.
    data["phone"] = [f"+1-202-555-{100 + i % 100:04d}" for i in range(size)]
    data["national_id"] = [f"DEMO-ID-{i % 40:06d}" for i in range(size)]
    data["notes"] = [f"Contact : {data.iloc[i]['full_name']}, {data.iloc[i]['email']} ; téléphone {data.iloc[i]['phone']}." for i in range(size)]
    return data
