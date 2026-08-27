# TODO: Validate
# The website serves every on-demand page under a locale segment.
LOCALE = "en"

MILLISECONDS_PER_SECOND = 1000

ITEM_ID_REGEX = r"[0-9a-f]{24}"
# Optional locale segment, e.g. /en, /us or /en-gb.
LOCALE_REGEX = r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?"
# Optional suffix the website adds to the canonical URL of a title.
DETAILS_REGEX = r"(?:\/details)?"
