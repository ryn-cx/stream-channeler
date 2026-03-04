# TODO: Validate
from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.exc import NoResultFound
from sqlmodel import Session

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeInput
from app.plugins.models import File, Plugin
from app.plugins.schemas import FileInput, PluginInput
from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from app.sources.schemas import SourceInput
from app.utils import tz_datetime
from tests.plugins.utils import create_random_plugin
from tests.seasons.utils import create_random_season
from tests.shows.utils import create_random_show
from tests.sources.utils import create_random_source
from tests.utils.media import create_random_heirarchy
from tests.utils.utils import build_random_model

real_models = Plugin | File | Source | Show | Season | Episode
input_models = (
    PluginInput | FileInput | SourceInput | ShowInput | SeasonInput | EpisodeInput
)


media_test_params = (
    (PluginInput, None),
    (SourceInput, create_random_plugin),
    (ShowInput, create_random_source),
    (SeasonInput, create_random_show),
    (EpisodeInput, create_random_season),
)

input_creator_type = type[
    PluginInput | SourceInput | ShowInput | SeasonInput | EpisodeInput
]
parent_creator_type = Callable[[Session], Source | Plugin | Show | Season] | None


def upsert_wrapper(
    model_input: input_models,
    parent: Plugin | Source | Show | Season | Session,
    protected_keys: set[str] | None = None,
) -> real_models:
    """Wrapper around upsert to force type safety.

    This exists purely to make tests type safe.
    """
    match model_input:
        case PluginInput():
            assert isinstance(parent, Session)
            model_input.user_id = None
            existing_plugin = Plugin.get(parent, model_input.key)
            return model_input.upsert(
                parent,
                existing_plugin,
                protected_keys=protected_keys,
            )
        case SourceInput():
            assert isinstance(parent, Plugin)
            existing_plugins = {source.key: source for source in parent.sources}
            existing_plugin = existing_plugins.get(model_input.key)
            return model_input.upsert(
                parent,
                existing_plugin,
                protected_keys=protected_keys,
            )
        case ShowInput():
            assert isinstance(parent, Source)
            existing_shows = {show.key: show for show in parent.shows}
            existing_show = existing_shows.get(model_input.key)
            return model_input.upsert(
                parent,
                existing_show,
                protected_keys=protected_keys,
            )
        case SeasonInput():
            assert isinstance(parent, Show)
            existing_seasons = {season.key: season for season in parent.seasons}
            existing_season = existing_seasons.get(model_input.key)
            return model_input.upsert(
                parent,
                existing_season,
                protected_keys=protected_keys,
            )
        case EpisodeInput():
            assert isinstance(parent, Season)
            existing_episodes = {episode.key: episode for episode in parent.episodes}
            existing_episode = existing_episodes.get(model_input.key)
            return model_input.upsert(
                parent,
                existing_episode,
                protected_keys=protected_keys,
            )
        case _:
            msg = f"Unsupported type: {type(model_input)}"
            raise ValueError(msg)


class TestUpsert:
    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_insert(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test inserting a new entry."""
        parent = parent_creator(db) if parent_creator else db
        model_input = build_random_model(input_creator)
        model = upsert_wrapper(model_input, parent)
        assert model.key == model_input.key
        assert model.data_timestamp == model_input.data_timestamp

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_update_value_to_value(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test updating a value to a different value."""
        parent = parent_creator(db) if parent_creator else db
        model_input = build_random_model(input_creator)
        model_input.extra = "Extra"
        model = upsert_wrapper(model_input, parent)

        model_input.extra = "Extra2"
        model = upsert_wrapper(model_input, parent)

        assert model.key == model_input.key
        assert model.data_timestamp == model_input.data_timestamp
        assert model.extra == "Extra2"

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_update_none_to_value(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test updating a value from None to a different value."""
        parent = parent_creator(db) if parent_creator else db
        model_input = build_random_model(input_creator)
        model = upsert_wrapper(model_input, parent)

        model_input.extra = "Extra"
        model = upsert_wrapper(model_input, parent)

        assert model.key == model_input.key
        assert model.data_timestamp == model_input.data_timestamp
        assert model.extra == "Extra"

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_update_value_to_none(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test updating a value from a value to None."""
        parent = parent_creator(db) if parent_creator else db
        model_input = build_random_model(input_creator)
        model_input.extra = "Extra"
        model = upsert_wrapper(model_input, parent)

        model_input = build_random_model(input_creator, extra=None)
        model_input.key = model.key
        model = upsert_wrapper(model_input, parent)

        assert model.key == model_input.key
        assert model.data_timestamp == model_input.data_timestamp
        assert model.extra is None

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_update_protected_keys(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test that protected keys are not updated."""
        parent = parent_creator(db) if parent_creator else db
        model_input = build_random_model(input_creator)
        model_input.extra = "Extra"
        model = upsert_wrapper(model_input, parent)

        model_input.extra = "Extra2"
        model = upsert_wrapper(model_input, parent, protected_keys={"extra"})

        assert model.key == model_input.key
        assert model.data_timestamp == model_input.data_timestamp
        assert model.extra == "Extra"

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_upsert_sets_modified_at(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test that modified_at is automatically updated when model fields change."""
        parent = parent_creator(db) if parent_creator else db
        model_input = build_random_model(input_creator)
        db_entry = upsert_wrapper(model_input, parent)
        timestamp = tz_datetime.now()
        model_input.name = "updated_name"
        db_entry = upsert_wrapper(model_input, parent)
        assert db_entry.modified_at > timestamp


class TestGet:
    def get_args(
        self,
        db: Session,
        entry: real_models,
        bad_id: str | None = None,
    ) -> tuple[Any, ...]:
        """Get the arguments for the get and get_one methods in a type safe way."""
        match entry:
            case Plugin():
                return (db, bad_id or entry.key)
            case File() | Source():
                return (db, entry.plugin, bad_id or entry.key)
            case Show():
                return (db, entry.source, bad_id or entry.key)
            case Season():
                return (db, entry.show, bad_id or entry.key)
            case Episode():
                return (db, entry.season, bad_id or entry.key)
            case _:
                msg = f"Unsupported type: {type(entry)}"
                raise ValueError(msg)

    def get_bad_id(
        self,
        entry_type: type[real_models],
        db_entry_2: real_models,
    ) -> str:
        """Get a bad ID value for the given entry type."""
        # Since Plugins do not have a parent they need to manually be assigned a bad ID
        # value that is guaranteed to not match any existing entry.
        if entry_type == Plugin:
            return "BAD_ID"

        # For all other entries, the id from the second entry will be used with the
        # parent from the first entry. This way the tests confirms that each parent
        # has its own set of entries that do not conflict with each other.
        return db_entry_2.key

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_get(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test getting a single entry."""
        parent = parent_creator(db) if parent_creator else db

        db_entry_1 = upsert_wrapper(build_random_model(input_creator), parent)
        db_entry_2 = upsert_wrapper(build_random_model(input_creator), parent)

        assert db_entry_1 == db_entry_1.get_one(*self.get_args(db, db_entry_1))
        assert db_entry_2 == db_entry_2.get_one(*self.get_args(db, db_entry_2))

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_get_wrong_parent(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test getting a single entry with wrong parent returns None."""
        parent_1 = parent_creator(db) if parent_creator else db
        parent_2 = parent_creator(db) if parent_creator else db

        db_entry_1 = upsert_wrapper(build_random_model(input_creator), parent_1)
        db_entry_2 = upsert_wrapper(build_random_model(input_creator), parent_2)

        bad_id = self.get_bad_id(type(db_entry_1), db_entry_2)

        args = self.get_args(db, db_entry_1, bad_id)
        assert db_entry_1.get(*args) is None

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_get_one(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test getting a single entry."""
        parent = parent_creator(db) if parent_creator else db

        db_entry_1 = upsert_wrapper(build_random_model(input_creator), parent)
        db_entry_2 = upsert_wrapper(build_random_model(input_creator), parent)

        assert db_entry_1 == db_entry_1.get_one(*self.get_args(db, db_entry_1))
        assert db_entry_2 == db_entry_2.get_one(*self.get_args(db, db_entry_2))

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_get_one_wrong_parent(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test getting a single entry with wrong parent raises an exception."""
        parent_1 = parent_creator(db) if parent_creator else db
        parent_2 = parent_creator(db) if parent_creator else db

        db_entry_1 = upsert_wrapper(build_random_model(input_creator), parent_1)
        db_entry_2 = upsert_wrapper(build_random_model(input_creator), parent_2)

        bad_id = self.get_bad_id(type(db_entry_1), db_entry_2)

        with pytest.raises(NoResultFound):
            db_entry_1.get_one(*self.get_args(db, db_entry_1, bad_id))


class TestDelete:
    def check_deleted_at_entry(self, item: real_models, *, is_deleted: bool) -> None:
        """Check if a single value is deleted or not deleted."""
        if is_deleted:
            assert item.deleted_at is not None
        else:
            assert item.deleted_at is None

    def check_recursive_entries(
        self,
        plugins: list[Plugin],
        depth: int,
        *,
        is_deleted: bool,
    ) -> None:
        """Check that all entries in the hierarchy are deleted or not deleted."""
        assertion_counter = 0
        assert len(plugins) == depth
        for plugin in plugins:
            self.check_deleted_at_entry(plugin, is_deleted=is_deleted)
            assert len(plugin.sources) == depth
            assert len(plugin.files) == depth
            assertion_counter += 3

            # Files should not be modified by soft_delete and soft_undelete so it should
            # always be False.
            for file in plugin.files:
                self.check_deleted_at_entry(file, is_deleted=False)
                assertion_counter += 1

            for source in plugin.sources:
                self.check_deleted_at_entry(source, is_deleted=is_deleted)
                assert len(source.shows) == depth
                assertion_counter += 2

                for show in source.shows:
                    self.check_deleted_at_entry(show, is_deleted=is_deleted)
                    assert len(show.seasons) == depth
                    assertion_counter += 2

                    for season in show.seasons:
                        self.check_deleted_at_entry(season, is_deleted=is_deleted)
                        assert len(season.episodes) == depth
                        assertion_counter += 2

                        for episode in season.episodes:
                            self.check_deleted_at_entry(episode, is_deleted=is_deleted)
                            assertion_counter += 1

        assert assertion_counter == 495  # noqa: PLR2004

    def create_four_entries(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> tuple[real_models, real_models, real_models, real_models, datetime]:
        """Create four entries, two deleted and two not deleted."""
        timestamp = tz_datetime.now()
        parent = parent_creator(db) if parent_creator else db

        entry1 = upsert_wrapper(
            build_random_model(input_creator, deleted_at=None),
            parent,
        )
        entry2 = upsert_wrapper(
            build_random_model(input_creator, deleted_at=None),
            parent,
        )

        entry3_input = build_random_model(input_creator)
        entry3_input.deleted_at = timestamp
        entry3 = upsert_wrapper(entry3_input, parent)

        entry4_input = build_random_model(input_creator)
        entry4_input.deleted_at = timestamp
        entry4 = upsert_wrapper(entry4_input, parent)

        return entry1, entry2, entry3, entry4, timestamp

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_delete(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test deleting a single entry."""
        e1, e2, e3, e4, ts = self.create_four_entries(db, input_creator, parent_creator)
        e1.soft_delete()

        assert e1.deleted_at
        assert e1.deleted_at > ts
        assert e2.deleted_at is None
        assert e3.deleted_at == ts
        assert e4.deleted_at == ts

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_delete_idempotent(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test deleting a single entry that is idempotent."""
        e1, e2, e3, e4, ts = self.create_four_entries(db, input_creator, parent_creator)
        e3.soft_delete()

        assert e1.deleted_at is None
        assert e2.deleted_at is None
        assert e3.deleted_at == ts
        assert e4.deleted_at == ts

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_undelete(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test undeleting a single entry."""
        e1, e2, e3, e4, ts = self.create_four_entries(db, input_creator, parent_creator)
        e4.soft_undelete()

        assert e1.deleted_at is None
        assert e2.deleted_at is None
        assert e3.deleted_at == ts
        assert e4.deleted_at is None

    @pytest.mark.parametrize(("input_creator", "parent_creator"), media_test_params)
    def test_undelete_idempotent(
        self,
        db: Session,
        input_creator: input_creator_type,
        parent_creator: parent_creator_type,
    ) -> None:
        """Test undeleting a single entry is idempotent."""
        e1, e2, e3, e4, ts = self.create_four_entries(db, input_creator, parent_creator)
        e1.soft_undelete()

        assert e1.deleted_at is None
        assert e2.deleted_at is None
        assert e3.deleted_at == ts
        assert e4.deleted_at == ts

    def test_recursive_undelete(self, db: Session) -> None:
        """Test recursive undeletion of a full hierarchy."""
        depth = 3
        plugins = create_random_heirarchy(db, default_count=depth)

        for plugin in plugins:
            plugin.soft_undelete()

        self.check_recursive_entries(plugins, depth, is_deleted=False)

    def test_recursive_delete(self, db: Session) -> None:
        """Test recursive deletion of a full hierarchy."""
        depth = 3
        plugins = create_random_heirarchy(db, default_count=depth)
        for plugin in plugins:
            plugin.soft_delete()

        self.check_recursive_entries(plugins, depth, is_deleted=True)
