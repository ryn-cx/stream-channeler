# TODO: Validate
# Which of a title's images stands for it, most wanted first.
IMAGE_PREFERENCE = ("covershot", "packshot", "titleshot", "heroshot")

MOVIE_ENTITY_TYPE = "Movie"
"""What Prime Video calls a title that is a film rather than a series."""

# Prime itself is offered through the same payload as a channel, but a title
# included with Prime belongs to Prime Video rather than to a separate source.
PRIME_BENEFIT_ID = "Prime"

# A plain ASIN is 10 characters, but a link written by Prime Video itself uses a
# longer id of its own.
TITLE_KEY_REGEX = r"[A-Z0-9]{10,}"

# Names the source that holds the titles that have to be bought or rented.
PURCHASE_SOURCE_SUFFIX = "Purchase"
