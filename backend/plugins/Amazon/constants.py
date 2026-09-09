# TODO: Validate
# Which of a title's images stands for it, most wanted first.
IMAGE_PREFERENCE = ("covershot", "packshot", "titleshot", "heroshot")

# Prime itself is offered through the same payload as a channel, but a title
# included with Prime belongs to Prime Video rather than to a separate source.
PRIME_BENEFIT_ID = "Prime"

# A plain ASIN is 10 characters, but a link written by Prime Video itself uses a
# longer id of its own.
TITLE_KEY_REGEX = r"[A-Z0-9]{10,}"

# Names the source that holds the titles that have to be bought or rented.
PURCHASE_SOURCE_SUFFIX = "Purchase"

# https://watch.amazon.com/detail?gti=amzn1.dv.gti.92ad2133-d35e-1cb1-5d8e-f7b122a68228
# The id Amazon writes into a share link, which names the title in a
# different id space to the one its own pages are keyed by.
SHARE_URL_REGEX = (
    r"\/detail\?gti=(?P<watch_amazon_title_key>amzn1\.dv\.gti\.[0-9a-f-]+)"
)
# https://www.primevideo.com/detail/0GTKUFQSFLP1YVFDMW9IR56I90
# The region a link was written in is the region of whoever wrote it, and the
# title is the same title whichever region asked for it.
PRIME_VIDEO_URL_REGEX = (
    rf"(?:\/region\/[a-z]{{2}})?\/detail\/(?P<prime_video_title_key>{TITLE_KEY_REGEX})"
)
# https://www.amazon.com/gp/video/detail/B0D9MYVLNM
# The title slug Amazon puts in front of /dp/ is decorative, only the id
# after it matters.
AMAZON_URL_REGEX = (
    r"(?:\/[^\/]+)?\/(?:dp|gp\/video\/detail)\/"
    rf"(?P<amazon_title_key>{TITLE_KEY_REGEX})"
)
