"""Shared fixtures for ETL framework tests."""

import pytest
from typing import Any, Dict, Type

from niagads.etl.types import ETLMode
from niagads.etl.plugins.parameters import BasePluginParams, ResumeCheckpoint
from niagads.etl.plugins.types import ETLLoadResult, ETLLoadStrategy, ETLOperation


class TestPluginParams(BasePluginParams):
    """Test parameter model for mock plugins."""

    pass


# Import after params to avoid circular dependency
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.registry import PluginRegistry, PluginMetadata


class TestPlugin(AbstractBasePlugin):
    """Minimal test plugin for framework testing."""

    def extract(self):
        """Yield test records."""
        for i in range(5):
            yield {"id": f"record_{i}", "data": f"test_data_{i}"}

    def transform(self, data):
        """Pass through transformation."""
        if hasattr(data, "__iter__") and not isinstance(data, dict):
            return [d for d in data if d is not None]
        return data

    async def load(self, session, transformed) -> ETLLoadResult:
        """Mock load operation."""
        count = len(transformed) if isinstance(transformed, list) else 1
        return ETLLoadResult(
            transaction_count=count,
            checkpoint=ResumeCheckpoint(line=count) if count > 0 else None,
        )

    def get_record_id(self, record: Any) -> str:
        """Extract record ID."""
        return record.get("id", str(record))

    @classmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        """Return parameter model."""
        return TestPluginParams


@pytest.fixture
def test_plugin_metadata() -> PluginMetadata:
    """Create test plugin metadata."""
    return PluginMetadata(
        version="1.0.0",
        description="Test plugin for framework testing",
        affected_tables=[],
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        model_parameters=TestPluginParams,
    )


@pytest.fixture
def mock_registry_cleanup():
    """Clean up registry before and after tests."""
    # Store original registry state
    original_registry = PluginRegistry._registry.copy()
    original_meta = PluginRegistry._metadata.copy()

    yield

    # Restore original state
    PluginRegistry._registry = original_registry
    PluginRegistry._metadata = original_meta


@pytest.fixture
def registered_test_plugin(test_plugin_metadata, mock_registry_cleanup):
    """Register and return test plugin instance."""
    PluginRegistry._registry.clear()
    PluginRegistry._metadata.clear()

    # Register the test plugin
    PluginRegistry._registry["TestPlugin"] = TestPlugin
    PluginRegistry._metadata["TestPlugin"] = test_plugin_metadata

    params = {"mode": ETLMode.DRY_RUN.value}
    return TestPlugin(params)


@pytest.fixture
def test_params_dict() -> Dict[str, Any]:
    """Create base test parameters."""
    return {
        "mode": ETLMode.DRY_RUN.value,
        "commit_after": 100,
        "verbose": False,
        "debug": False,
    }


class TestPluginParams(BasePluginParams):
    """Test parameter model for mock plugins."""

    pass


class TestPlugin(AbstractBasePlugin):
    """Minimal test plugin for framework testing."""

    def extract(self):
        """Yield test records."""
        for i in range(5):
            yield {"id": f"record_{i}", "data": f"test_data_{i}"}

    def transform(self, data):
        """Pass through transformation."""
        if hasattr(data, "__iter__") and not isinstance(data, dict):
            return [d for d in data if d is not None]
        return data

    async def load(self, session, transformed) -> ETLLoadResult:
        """Mock load operation."""
        count = len(transformed) if isinstance(transformed, list) else 1
        return ETLLoadResult(
            transaction_count=count,
            checkpoint=ResumeCheckpoint(line=count) if count > 0 else None,
        )

    def get_record_id(self, record: Any) -> str:
        """Extract record ID."""
        return record.get("id", str(record))

    @classmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        """Return parameter model."""
        return TestPluginParams


@pytest.fixture
def test_plugin_metadata() -> PluginMetadata:
    """Create test plugin metadata."""
    return PluginMetadata(
        version="1.0.0",
        description="Test plugin for framework testing",
        affected_tables=[],
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        model_parameters=TestPluginParams,
    )


@pytest.fixture
def mock_registry_cleanup():
    """Clean up registry before and after tests."""
    # Store original registry state
    original_registry = PluginRegistry._registry.copy()
    original_meta = PluginRegistry._metadata.copy()

    yield

    # Restore original state
    PluginRegistry._registry = original_registry
    PluginRegistry._metadata = original_meta


@pytest.fixture
def registered_test_plugin(test_plugin_metadata, mock_registry_cleanup):
    """Register and return test plugin instance."""
    PluginRegistry._registry.clear()
    PluginRegistry._metadata.clear()

    # Register the test plugin
    PluginRegistry._registry["TestPlugin"] = TestPlugin
    PluginRegistry._metadata["TestPlugin"] = test_plugin_metadata

    params = {"mode": ETLMode.DRY_RUN.value}
    return TestPlugin(params)


@pytest.fixture
def test_params_dict() -> Dict[str, Any]:
    """Create base test parameters."""
    return {
        "mode": ETLMode.DRY_RUN.value,
        "commit_after": 100,
        "verbose": False,
        "debug": False,
    }
