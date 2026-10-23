"""Parameters shared by the scripts (edit here, no command-line arguments)."""

QUOTE_DATE = None  # e.g. "2026-10-15"; None uses the latest date in the file
SNAPSHOT_DATES = ("2024-01-02", "2025-01-02")  # plus the quote date, for the snapshot figure
RISK_BOOK = [  # (kind, maturity) of the bonds whose risk is reported
    ("LTN", "2029-01-01"),
    ("LTN", "2032-01-01"),
    ("NTN-F", "2029-01-01"),
    ("NTN-F", "2033-01-01"),
    ("NTN-F", "2037-01-01"),
]
