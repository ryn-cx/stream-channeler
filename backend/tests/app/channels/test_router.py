# TODO: Validate


from app.channels.models import Channel
from tests.app.channels.base import ChannelTestMixin
from tests.app.utils.base_create import UserOwnedCreateMixin
from tests.app.utils.base_delete import BaseDeleteTests
from tests.app.utils.base_get import UserOwnedGetMixin
from tests.app.utils.base_update import BaseUpdateTests


# TODO: Validate
class TestCreateChannel(ChannelTestMixin, UserOwnedCreateMixin[Channel]):
    pass


# TODO: Validate
class TestGetChannel(ChannelTestMixin, UserOwnedGetMixin[Channel]):
    pass


# TODO: Validate
class TestUpdateChannel(ChannelTestMixin, BaseUpdateTests[Channel]):
    pass


# TODO: Validate
class TestDeleteChannel(ChannelTestMixin, BaseDeleteTests[Channel]):
    pass
