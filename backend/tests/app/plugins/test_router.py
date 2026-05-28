# TODO: Validate
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginCreate,
    PluginOutput,
    PluginUpdate,
)
from tests.app.plugins.utils import create_random_plugin
from tests.app.utils.base import BaseTests
from tests.app.utils.base_create import UserOwnedCreateMixin
from tests.app.utils.base_delete import BaseDeleteTests
from tests.app.utils.base_get import UserOwnedGetMixin
from tests.app.utils.base_update import BaseUpdateTests


class PluginTestMixin(BaseTests[Plugin]):
    database_model = Plugin
    create_schema = PluginCreate
    output_schema = PluginOutput
    update_schema = PluginUpdate
    create_record_function = staticmethod(create_random_plugin)


class TestCreatePlugin(PluginTestMixin, UserOwnedCreateMixin[Plugin]):
    pass


class TestUpdatePlugin(PluginTestMixin, BaseUpdateTests[Plugin]):
    pass


class TestGetPlugin(PluginTestMixin, UserOwnedGetMixin[Plugin]):
    pass


class TestDeletePlugin(PluginTestMixin, BaseDeleteTests[Plugin]):
    pass
