# TODO: Validate
UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# A series is keyed by a long number, a movie and an episode by a UUID. A few
# series, mostly the ones under /sports and /news, are keyed by a UUID too.
TITLE_KEY_REGEX = rf"(?:{UUID_REGEX}|\d+)"
# The section and name segments in front of the id are decorative, and a movie
# has an extra genre segment between them, e.g.
# https://www.peacocktv.com/watch/asset/movies/romance/renegade/06145283-20dc-3916-a072-e0c00daaa8e6
SLUG_REGEX = r"(?:\/[^\/?#]+){2,3}"

# https://www.peacocktv.com/watch/asset/tv/the-office/4902514835143843112/seasons/1/episodes/pilot-episode-1/58fabbf4-9291-3575-bcdc-bd25eee192c8
EPISODE_URL_REGEX = (
    rf"\/watch\/asset{SLUG_REGEX}\/(?P<title_key>{TITLE_KEY_REGEX})"
    rf"\/seasons\/\d+\/episodes\/[^\/?#]+\/(?P<episode_key>{UUID_REGEX})"
    r"\/?(?:$|[?#])"
)
# https://www.peacocktv.com/watch/asset/tv/the-office/4902514835143843112
# https://www.peacocktv.com/watch/asset/movies/shrek/b6303073-41bf-3644-8e71-0e8278c33678
TITLE_URL_REGEX = (
    rf"\/watch\/asset{SLUG_REGEX}\/(?P<title_key>{TITLE_KEY_REGEX})\/?(?:$|[?#])"
)
