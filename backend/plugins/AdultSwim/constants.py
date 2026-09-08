# TODO: Validate
FREE = "Adult Swim Free"
SUBSCRIPTION = "Adult Swim Subscription"

EPISODE_URL_REGEX = r"\/videos\/(?P<episode_path>[a-z0-9-]+\/[a-z0-9-]+)(?:[\/?#]|$)"
TITLE_URL_REGEX = (
    r"\/(?!videos(?:$|[?#]|\/(?:$|[?#])))"
    r"(?:videos\/)?(?P<title_key>[a-z0-9-]+)\/?(?:$|[?#])"
)

CHANNEL_DESCRIPTION_FILES = {
    SUBSCRIPTION: "subscription_channel_description.md",
    FREE: "free_channel_description.md",
}
