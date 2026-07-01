"""
Tests for CSV import of the real data files.

Reproduces and guards against:
  - Company Contacts.csv being cp1252-encoded (0xa0) crashing utf-8 read
  - Company CSV using a 'Company' column instead of 'Company Name'
  - schools_waitlist_hydrated CSV using 'name'/'eircode'/etc columns
    instead of the legacy 'Official Name' + positional layout
"""
import os
import tempfile

# Point the database at a throwaway file BEFORE importing modules that read it.
_TMP_DB = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_TMP_DB.close()
os.environ['DATABASE_PATH'] = _TMP_DB.name

import database
database.DATABASE_PATH = _TMP_DB.name
database.init_db()

import main
# Avoid network geocoding during the test.
main.convert_eircode_to_address = lambda eircode: ''

COMPANY_CSV = os.path.join('data', 'Company_Contacts.csv')
SCHOOL_CSV = os.path.join('data', 'schools_waitlist_hydrated.csv')


def _row_count(table):
    conn = database.get_db_connection()
    n = conn.cursor().execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    conn.close()
    return n


def test_company_import():
    imported = main.import_companies_from_excel(COMPANY_CSV)
    assert imported > 0, "expected company rows to import"
    # Row count may be <= imported because duplicate (eircode, company_name)
    # rows are upserted rather than inserted.
    assert 0 < _row_count('companies') <= imported
    # Spot check a known row survived the cp1252 decode.
    conn = database.get_db_connection()
    row = conn.cursor().execute(
        "SELECT company_name FROM companies WHERE company_name = 'MSD'").fetchone()
    conn.close()
    assert row is not None, "expected 'MSD' company to be imported"
    print(f"company rows imported: {imported}")


def test_school_import():
    imported = main.import_schools_from_excel(SCHOOL_CSV)
    assert imported > 0, "expected school rows to import"
    # Duplicate roll_numbers are upserted, so rows <= imported.
    assert 0 < _row_count('schools') <= imported
    conn = database.get_db_connection()
    row = conn.cursor().execute(
        "SELECT roll_number, county, school_type FROM schools "
        "WHERE school_name = 'Borris College'").fetchone()
    conn.close()
    assert row is not None, "expected 'Borris College' to be imported"
    assert row['roll_number'] == '70400L'
    assert row['county'] == 'Carlow'
    print(f"school rows imported: {imported}")


if __name__ == '__main__':
    ok = True
    for fn in (test_company_import, test_school_import):
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:
            ok = False
            print(f"FAIL {fn.__name__}: {e}")
    os.unlink(_TMP_DB.name)
    raise SystemExit(0 if ok else 1)
