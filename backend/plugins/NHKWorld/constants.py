# TODO: Validate
# https://www3.nhk.or.jp/nhkworld/en/shows/100years-midosuji/
# The lookahead requires a non-numeric character so this matches title slugs but
# not numeric episode URLs like https://www3.nhk.or.jp/nhkworld/en/shows/5001461/
TITLE_URL_REGEX = (
    r"\/nhkworld\/en\/shows\/(?P<title_key>(?=[a-z0-9_-]*[a-z_-])[a-z0-9_-]+)"
    r"\/?(?:$|[?#])"
)
