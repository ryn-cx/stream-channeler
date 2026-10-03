# TODO: Validate
# https://www.disneyplus.com/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
# https://www.disneyplus.com/en-gb/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
# The optional locale segment, e.g. /en-gb or /de.
ENTITY_URL_REGEX = (
    r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?\/browse\/entity-"
    r"(?P<title_key>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(?:\/|$)"
)
