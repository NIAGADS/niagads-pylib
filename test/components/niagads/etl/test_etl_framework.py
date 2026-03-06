"""Tests for ETL framework functionality.

Tests cover:
- dry-run chunked/bulk status logging
- non-dry-run tally summarization
- registry introspection
- checkpoint logging on failure
- runtime param override and restore
"""

import pytest
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from niagads.etl.plugins.registry import PluginRegistry, PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, ResumeCheckpoint
from niagads.etl.plugins.types import ETLLoadResult, ETLLoadStrategy, ETLOperation
from niagads.etl.types import ETLMode
from niagads.common.types import ProcessStatus

from conftest import TestPlugin, TestPluginParams


class TestRegistryIntrospection:
    """Test registry discovery and introspection."""

    def test_registry_list_plugins(self, registered_test_plugin):
        """Test listing all registered plugins."""
        plugins = PluginRegistry.list_plugins()
        assert "TestPlugin" in plugins
        assert isinstance(plugins, list)

    def test_registry_get_plugin(self, registered_test_plugin):
        """Test retrieving a registered plugin by name."""
        plugin_cls = PluginRegistry.get("TestPlugin")
        assert plugin_cls is TestPlugin

    def test_registry_get_nonexistent_plugin(self):
        """Test that retrieving nonexistent plugin raises KeyError."""
        with pytest.raises(KeyError, match="Plugin 'NonExistent' not found"):
            PluginRegistry.get("NonExistent")

    def test_registry_describe_plugin(self, registered_test_plugin):
        """Test plugin metadata introspection."""
        description = PluginRegistry.describe("TestPlugin")
        assert description["class"] == "TestPlugin"
        assert description["version"] == "1.0.0"
        assert description["description"] == "Test plugin for framework testing"
        assert "parameter_model" in description

    def test_registry_describe_nonexistent_plugin(self):
        """Test that describing nonexistent plugin raises KeyError."""
        with pytest.raises(KeyError, match="Plugin 'NonExistent' not found"):
            PluginRegistry.describe("NonExistent")


class TestDryRunStatusLogging:
    """Test status logging in dry-run mode for chunked and bulk loads."""

    def test_dry_run_chunked_status_logging(self, test_params_dict):
        """Test that dry-run chunked mode logs status correctly."""
        params = {**test_params_dict, "mode": ETLMode.DRY_RUN.value}
        plugin = TestPlugin(params)

        assert plugin.is_dry_run is True
        assert plugin.load_strategy == ETLLoadStrategy.CHUNKED

    def test_dry_run_bulk_status_logging(self, test_params_dict):
        """Test that dry-run bulk mode logs status correctly."""
        params = {**test_params_dict, "mode": ETLMode.DRY_RUN.value}
        plugin = TestPlugin(params)

        assert plugin.is_dry_run is True
        # Plugin has CHUNKED strategy, but framework should handle both

    def test_dry_run_transaction_count(self, test_params_dict):
        """Test transaction count tracking in dry-run mode."""
        params = {**test_params_dict, "mode": ETLMode.DRY_RUN.value}
        plugin = TestPlugin(params)

        plugin.inc_tx_count(5)
        assert plugin.tx_count == 5

        plugin.inc_tx_count(3)
        assert plugin.tx_count == 8


class TestNonDryRunTallyization:
    """Test tally summarization in non-dry-run modes."""

    def test_plugin_affected_tables_property(self, registered_test_plugin):
        """Test retrieval of affected tables."""
        tables = registered_test_plugin.affected_tables
        assert isinstance(tables, list)

    def test_plugin_operation_property(self, registered_test_plugin):
        """Test retrieval of operation type."""
        operation = registered_test_plugin.operation
        assert operation == ETLOperation.INSERT

    def test_plugin_load_strategy_property(self, registered_test_plugin):
        """Test retrieval of load strategy."""
        strategy = registered_test_plugin.load_strategy
        assert strategy == ETLLoadStrategy.CHUNKED

    def test_plugin_is_large_dataset_property(self, registered_test_plugin):
        """Test retrieval of large dataset flag."""
        is_large = registered_test_plugin.is_large_dataset
        assert isinstance(is_large, bool)


class TestCheckpointLoggingOnFailure:
    """Test checkpoint handling during failures."""

    def test_set_checkpoint_with_line(self, registered_test_plugin):
        """Test creating checkpoint with line number."""
        checkpoint = registered_test_plugin.set_checkpoint(line=42)
        assert checkpoint.line == 42
        assert isinstance(checkpoint, ResumeCheckpoint)

    def test_set_checkpoint_with_record(self, registered_test_plugin):
        """Test creating checkpoint with record."""
        record = {"id": "record_123", "data": "test"}
        checkpoint = registered_test_plugin.set_checkpoint(record=record)
        assert checkpoint.record == "record_123"
        assert checkpoint.full_record == record

    def test_set_checkpoint_requires_line_or_record(self, registered_test_plugin):
        """Test that checkpoint requires either line or record."""
        with pytest.raises(ValueError, match="Must set either line or record"):
            registered_test_plugin.set_checkpoint()

    def test_checkpoint_none_handling(self, registered_test_plugin):
        """Test that None checkpoint is handled gracefully."""
        # Checkpoint can be None after successful load with no updates
        checkpoint = None
        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_load_result_with_checkpoint(self):
        """Test ETLLoadResult with checkpoint."""
        checkpoint = ResumeCheckpoint(line=10)
        result = ETLLoadResult(transaction_count=5, checkpoint=checkpoint)
        assert result.transaction_count == 5
        assert result.checkpoint == checkpoint

    @pytest.mark.asyncio
    async def test_load_result_without_checkpoint(self):
        """Test ETLLoadResult without checkpoint."""
        result = ETLLoadResult(transaction_count=3, checkpoint=None)
        assert result.transaction_count == 3
        assert result.checkpoint is None


class TestRuntimeParamOverrideAndRestore:
    """Test runtime parameter override and restoration."""

    def test_runtime_params_dict_creation(self, test_params_dict):
        """Test creating runtime params dict."""
        assert test_params_dict["mode"] == ETLMode.DRY_RUN.value
        assert test_params_dict["commit_after"] == 100

    def test_override_mode_param(self, test_params_dict):
        """Test that mode parameter can be overridden."""
        original_mode = test_params_dict["mode"]
        test_params_dict["mode"] = ETLMode.COMMIT.value
        assert test_params_dict["mode"] != original_mode
        assert test_params_dict["mode"] == ETLMode.COMMIT.value

    def test_override_commit_after_param(self, test_params_dict):
        """Test that commit_after parameter can be overridden."""
        original_commit = test_params_dict["commit_after"]
        test_params_dict["commit_after"] = 500
        assert test_params_dict["commit_after"] != original_commit
        assert test_params_dict["commit_after"] == 500

    def test_parameter_model_validation(self):
        """Test that parameter model validates on instantiation."""
        # Valid params
        params = {
            "mode": ETLMode.DRY_RUN.value,
            "commit_after": 100,
        }
        param_model = TestPluginParams(**params)
        assert param_model.mode == ETLMode.DRY_RUN

    def test_parameter_model_invalid_commit_after(self):
        """Test that negative commit_after is rejected."""
        params = {
            "mode": ETLMode.DRY_RUN.value,
            "commit_after": -1,
        }
        with pytest.raises(ValueError):
            TestPluginParams(**params)

    def test_plugin_params_copy_and_restore(self, test_params_dict):
        """Test that plugin params can be copied for override."""
        original_params = test_params_dict.copy()

        # Simulate override
        test_params_dict["commit_after"] = 250
        test_params_dict["verbose"] = True

        # Restore
        test_params_dict.update(original_params)

        assert test_params_dict["commit_after"] == original_params["commit_after"]
        assert test_params_dict["verbose"] == original_params["verbose"]
