"""Irish government school registry (data/gov_data) used as a reference lookup
to enrich school records by name. This is reference-only data: it is never
inserted into the `schools` table on its own, only used to fill in accurate
fields (address, Eircode, coordinates, DEIS, contacts, enrolment) for schools
that already exist or are being added/imported elsewhere.
"""
import logging
import os
import re
import threading
import unicodedata

import pandas as pd

logger = logging.getLogger('elephant')

_GOV_DATA_DIR = os.path.join('data', 'gov_data')

# Only the newest, fullest-schema file per school category is used - see
# the plan doc for why the other files in data/gov_data are excluded
# (older years, or - in the case of primary-schools-20232024.csv - a
# mislabeled duplicate of the special-schools historical data).
_SOURCES = [
    (os.path.join(_GOV_DATA_DIR, 'Data_on_Individual_Schools_Mainstream_2024_25.csv'), 'primary'),
    (os.path.join(_GOV_DATA_DIR, 'Data_on_Individual_Schools_Mainstream_2024_25_special_schools.csv'), 'special'),
    (os.path.join(_GOV_DATA_DIR, 'Data_on_Individual_Schools_post_primary.csv'), 'post_primary'),
]

_registry_lock = threading.Lock()
_registry = None


def _normalize_name(name):
    """Uppercase, accent-fold and strip punctuation/whitespace so names that
    differ only in casing/accents/trailing punctuation compare equal. This is
    normalization, not fuzzy matching - words themselves must still match."""
    if not name:
        return ''
    folded = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode('ascii')
    folded = folded.upper().strip()
    folded = re.sub(r'\s+', ' ', folded)
    folded = folded.strip('.,;:\'"- ')
    return folded


def _round_down_hundred(n):
    return (int(n) // 100) * 100


def _title_case(name):
    """str.title() wrongly capitalizes the letter after an apostrophe
    (e.g. "st. mary's".title() -> "St. Mary'S") - fix that up."""
    if not name:
        return name
    titled = str(name).title()
    return re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), titled)


def _clean(value):
    """Normalize a raw pandas cell to either a stripped string or None."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == 'nan':
        return None
    return text


def _parse_enrolment(raw):
    text = _clean(raw)
    if not text:
        return None
    text = text.replace(',', '')
    try:
        return _round_down_hundred(int(float(text)))
    except (ValueError, TypeError):
        return None


def _join_address(*parts):
    lines = [p for p in (_clean(part) for part in parts) if p]
    return ', '.join(lines) if lines else None


def _build_record(roll_number, school_name, address, county, eircode, latitude, longitude,
                   deis, school_type, school_level, enrolment_raw, email, phone, contact_name):
    lat = _clean(latitude)
    lon = _clean(longitude)
    try:
        lat_val = float(lat) if lat else None
        lon_val = float(lon) if lon else None
    except (ValueError, TypeError):
        lat_val = lon_val = None
    return {
        'roll_number': _clean(roll_number),
        'school_name': _title_case(_clean(school_name)),
        'address': address,
        'county': _clean(county),
        'eircode': _clean(eircode),
        'latitude': lat_val,
        'longitude': lon_val,
        'deis': _clean(deis),
        'school_type': _clean(school_type),
        'school_level': school_level,
        'enrolment': _parse_enrolment(enrolment_raw),
        'email': _clean(email),
        'phone': _clean(phone),
        'contact_name': _clean(contact_name),
    }


def _load_primary(path):
    df = pd.read_csv(path, header=1, dtype=str)
    records = []
    for _, row in df.iterrows():
        name = _clean(row.get('Official Name'))
        if not name:
            continue
        address = _join_address(row.get('Address (Line 1)'), row.get('Address (Line 2)'),
                                 row.get('Address (Line 3)'), row.get('Address (Line 4)'))
        records.append(_build_record(
            roll_number=row.get('Roll Number'), school_name=name, address=address,
            county=row.get('County Description'), eircode=row.get('Eircode'),
            latitude=row.get('School Latitude'), longitude=row.get('School Longitude'),
            deis=row.get('DEIS (Y/N)'), school_type=row.get('School Type'),
            school_level='Primary', enrolment_raw=row.get('Enrolment per Return'),
            email=row.get('Email'), phone=row.get('Phone No.'), contact_name=row.get('Principal Name'),
        ))
    return records


def _load_special(path):
    df = pd.read_csv(path, header=1, dtype=str)
    records = []
    for _, row in df.iterrows():
        name = _clean(row.get('Official Name'))
        if not name:
            continue
        address = _join_address(row.get('Address (Line 1)'), row.get('Address (Line 2)'),
                                 row.get('Address (Line 3)'), row.get('Address (Line 4)'))
        records.append(_build_record(
            roll_number=row.get('Roll Number'), school_name=name, address=address,
            county=row.get('County Description'), eircode=row.get('Eircode'),
            latitude=row.get('School Latitude'), longitude=row.get('School Longitude'),
            deis=row.get('DEIS (Y/N)'), school_type=None,
            school_level='Special', enrolment_raw=row.get('Enrolment per Return'),
            email=row.get('Email'), phone=row.get('Phone No.'), contact_name=row.get('Principal Name'),
        ))
    return records


def _load_post_primary(path):
    df = pd.read_csv(path, header=1, dtype=str)
    records = []
    for _, row in df.iterrows():
        name = _clean(row.get('Official School Name'))
        if not name:
            continue
        address = _join_address(row.get('Address 1'), row.get('Address 2'),
                                 row.get('Address 3'), row.get('Address 4'))
        records.append(_build_record(
            roll_number=row.get('Roll Number'), school_name=name, address=address,
            county=row.get('County'), eircode=row.get('Eircode'),
            latitude=row.get('School Latitude'), longitude=row.get('School Longitude'),
            deis=row.get('DEIS (Y/N)'), school_type=row.get('Post Primary School Type'),
            school_level='Secondary', enrolment_raw=row.get('Total 2025-2026'),
            email=row.get('Email'), phone=row.get('Phone'), contact_name=row.get('Principal Name'),
        ))
    return records


_LOADERS = {
    'primary': _load_primary,
    'special': _load_special,
    'post_primary': _load_post_primary,
}


def _load_registry():
    """Many Irish primary schools share the same official name across
    different towns (e.g. several dozen "Scoil Mhuire"s) - about 13% of the
    ~3950 registry entries collide with at least one other school on
    normalized name. Silently matching one of them by name would risk
    overwriting a school's data with a same-named but unrelated school's
    address/coordinates/DEIS from a different town. So an ambiguous name is
    treated as no match at all (name key removed) rather than guessing -
    matching by roll_number, which is always unique, is unaffected."""
    global _registry
    with _registry_lock:
        if _registry is not None:
            return _registry
        by_name = {}
        ambiguous = set()
        by_roll = {}
        for path, category in _SOURCES:
            for record in _LOADERS[category](path):
                key = _normalize_name(record['school_name'])
                if key:
                    if key in by_name:
                        ambiguous.add(key)
                    else:
                        by_name[key] = record
                if record['roll_number']:
                    by_roll[record['roll_number']] = record
        for key in ambiguous:
            del by_name[key]
        if ambiguous:
            logger.warning(
                f"gov_schools: {len(ambiguous)} school names are shared by more than one "
                f"school in the registry - these will only match by roll_number, not by name"
            )
        logger.info(
            f"gov_schools: loaded {len(by_roll)} schools from government registry "
            f"({len(by_name)} with an unambiguous name)"
        )
        _registry = {'by_name': by_name, 'by_roll': by_roll}
        return _registry


def find_gov_match(name, roll_number=None):
    """Look up a school in the government registry by roll number (if given
    and present) or by normalized name. Returns the matched record dict, or
    None if no match was found."""
    registry = _load_registry()
    if roll_number:
        record = registry['by_roll'].get(str(roll_number).strip())
        if record:
            return record
    if not name:
        return None
    return registry['by_name'].get(_normalize_name(name))
