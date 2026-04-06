# TODO: Validate
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
)
from tests.plugins.utils import create_random_plugin
from tests.utils.base import BaseTests
from tests.utils.base_create import UserOwnedCreateMixin
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import UserOwnedGetMixin
from tests.utils.base_update import BaseUpdateTests


class PluginTestMixin(BaseTests[Plugin]):
    database_model = Plugin
    input_schema = PluginPostInput
    output_model = PluginOutput
    patch_model = PluginPatchInput
    create_record_function = staticmethod(create_random_plugin)


class TestCreatePlugin(PluginTestMixin, UserOwnedCreateMixin[Plugin]):
    pass


class TestUpdatePlugin(PluginTestMixin, BaseUpdateTests[Plugin]):
    pass


class TestGetPlugin(PluginTestMixin, UserOwnedGetMixin[Plugin]):
    pass


class TestDeletePlugin(PluginTestMixin, BaseDeleteTests[Plugin]):
    pass
