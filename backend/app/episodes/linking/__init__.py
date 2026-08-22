# TODO: Validate
"""Matching a show's episodes to the canonical episodes that stand for them.

`linker` is the entry point; the rest are the pieces it reads an episode through:

- `rules` - the keys an episode is looked up by, and the index that drops ties
- `split_names` - an episode whose title holds several episodes' titles
- `tmdb_facts` - the translated names and alternate numbering TMDB carries
"""

from app.episodes.linking.linker import EpisodeLinker

__all__ = ["EpisodeLinker"]
