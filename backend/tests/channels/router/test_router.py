# TODO: Validate
from app.channels.models import Channel
from tests.channels.router import ChannelTestMixin
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import BaseGetTests
from tests.utils.base_list import BaseListFromParentTests
from tests.utils.base_update import BaseUpdateTests


class TestCreateChannel(ChannelTestMixin, BaseCreateTests[Channel]):
    pass


class TestGetChannel(ChannelTestMixin, BaseGetTests[Channel]):
    pass


class TestListChannels(ChannelTestMixin, BaseListFromParentTests[Channel]):
    pass


class TestUpdateChannel(ChannelTestMixin, BaseUpdateTests[Channel]):
    pass


class TestDeleteChannel(ChannelTestMixin, BaseDeleteTests[Channel]):
    pass
