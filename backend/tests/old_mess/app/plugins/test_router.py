# TODO: Validate
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginCreate,
    PluginOutput,
    PluginUpdate,
)
from tests.old_mess.app.plugins.utils import create_random_plugin
from tests.old_mess.app.utils.base import BaseTests
from tests.old_mess.app.utils.base_create import UserOwnedCreateMixin
from tests.old_mess.app.utils.base_delete import BaseDeleteTests
from tests.old_mess.app.utils.base_get import UserOwnedGetMixin
from tests.old_mess.app.utils.base_update import BaseUpdateTests


# TODO: Validate
class PluginTestMixin(BaseTests[Plugin]):
    database_model = Plugin
    create_schema = PluginCreate
    output_schema = PluginOutput
    update_schema = PluginUpdate
    create_record_function = staticmethod(create_random_plugin)


# TODO: Validate
class TestCreatePlugin(PluginTestMixin, UserOwnedCreateMixin[Plugin]):
    pass


# TODO: Validate
class TestUpdatePlugin(PluginTestMixin, BaseUpdateTests[Plugin]):
    pass


# TODO: Validate
class TestGetPlugin(PluginTestMixin, UserOwnedGetMixin[Plugin]):
    pass


# TODO: Validate
class TestDeletePlugin(PluginTestMixin, BaseDeleteTests[Plugin]):
    pass
