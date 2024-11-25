from pathlib import Path


PEP_INDEX_URL = 'https://peps.python.org/'
MAIN_DOC_URL = 'https://docs.python.org/3/'
BASE_DIR = Path(__file__).parent

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
