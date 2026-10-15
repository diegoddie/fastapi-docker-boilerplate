"""The commons package constants."""

# Why: spreadsheets run cells starting with these characters as formulas, so
# exported values are prefixed with a quote (OWASP "CSV injection").
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
# Why: a CSV export reads this many rows at a time from the database.
CSV_BATCH_SIZE = 1000
