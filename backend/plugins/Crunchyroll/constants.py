# TODO: Validate
from datetime import timedelta

DETAIL_MAX_AGE = timedelta(days=7)

# Music is its own `Source` so a channel can take an artist without the video
# catalogue coming with it, and so the two can be scheduled apart. Each source is
# keyed by the name it is shown under, and the plugin owned channel every artist
# is queued into is named after the music source it collects.
VIDEO_SOURCE = "Crunchyroll"
MUSIC_SOURCE = "Crunchyroll Music"
