"""The commons package constants."""

# Why: spreadsheets run cells starting with these characters as formulas, so
# exported values are prefixed with a quote (OWASP "CSV injection").
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
