# TODO: Validate
from datetime import timedelta

TMDB_DOMAIN = "themoviedb.org"

EPISODE_GROUP_FIELD = "tmdb_episode_group_id"

MEDIA_INFO_MAX_AGE = timedelta(days=7)

# How long a title stands for before TMDB is asked what has changed about it.
# Only a title is on a timer: what its seasons and episodes are is settled by
# what that ask comes back with, so one of those is read again when TMDB says it
# moved and is left alone when it says nothing.
CHANGES_INTERVAL = timedelta(days=7)

SHOW_DETAIL_CHANGE_KEYS = frozenset(
    {
        "adult",
        "also_known_as",
        "alternative_titles",
        "biography",
        "birthday",
        "budget",
        "cast",
        "certifications",
        "character_names",
        "created_by",
        "crew",
        "deathday",
        "episode_run_time",
        "freebase_id",
        "freebase_mid",
        "general",
        "genres",
        "homepage",
        "images",
        "imdb_id",
        "languages",
        "name",
        "network",
        "origin_country",
        "original_name",
        "original_title",
        "overview",
        "parts",
        "place_of_birth",
        "plot_keywords",
        "production_companies",
        "production_countries",
        "releases",
        "revenue",
        "season_regular",
        "spoken_languages",
        "status",
        "tagline",
        "title",
        "translations",
        "tvdb_id",
        "tvrage_id",
        "type",
        "videos",
    },
)

SEASON_DETAIL_CHANGE_KEYS = frozenset(
    {
        "air_date",
        "cast",
        "crew",
        "episode",
        "episode_number",
        "general",
        "guest_stars",
        "images",
        "name",
        "overview",
        "production_code",
        "runtime",
        "season",
        "season_number",
        "season_regular",
        "translations",
        "video",
    },
)

EPISODE_TRANSLATIONS_CHANGE_KEYS = frozenset(
    {
        "translations",
    },
)
