"""BI Semantic & KPI Agent (simplified).

Responsibility: own the KPI catalog. It finds KPI definitions on disk,
checks that they are complete, and hands them to the rest of the pipeline.
"""

from pathlib import Path

import yaml

# The kpis/ folder sits next to the agents/ folder
KPI_DIR = Path(__file__).parent.parent / "kpis"

REQUIRED_FIELDS = [
    "name",
    "version",
    "status",
    "description",
    "formula",
    "source_table",
    "source_columns",
    "aggregation_grain",
    "grain_key",
    "filters",
    "owner",
]


def _version_key(version):
    """Turn "2.10" into (2, 10) so versions sort correctly."""
    return tuple(int(part) for part in str(version).split("."))


def _load_all_definitions():
    """Read every YAML file in kpis/ and check that it is complete."""
    definitions = []
    for path in sorted(KPI_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as file:
            definition = yaml.safe_load(file)

        missing = [field for field in REQUIRED_FIELDS if field not in definition]
        if missing:
            raise ValueError(f"{path.name} is missing required fields: {missing}")

        definition["version"] = str(definition["version"])
        definition["source_file"] = path.name
        definitions.append(definition)
    return definitions


def list_versions(kpi_name):
    """Return the available versions of a KPI, oldest first."""
    versions = [
        d["version"]
        for d in _load_all_definitions()
        if d["name"].lower() == kpi_name.lower()
    ]
    return sorted(versions, key=_version_key)


def load_definition(kpi_name, version):
    """Return the definition (a dict) of one KPI version."""
    for definition in _load_all_definitions():
        if (
            definition["name"].lower() == kpi_name.lower()
            and definition["version"] == str(version)
        ):
            return definition
    available = list_versions(kpi_name)
    raise ValueError(
        f"KPI '{kpi_name}' version '{version}' not found. Available versions: {available}"
    )


def get_latest_approved(kpi_name):
    """Return the highest version whose status is 'approved'."""
    approved = [
        d
        for d in _load_all_definitions()
        if d["name"].lower() == kpi_name.lower() and d["status"] == "approved"
    ]
    if not approved:
        raise ValueError(f"No approved version found for KPI '{kpi_name}'.")
    return max(approved, key=lambda d: _version_key(d["version"]))