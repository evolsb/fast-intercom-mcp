"""Basic MCP server startup tests."""

from unittest.mock import Mock

import pytest

from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.mcp_server import FastIntercomMCPServer


class TestMCPServer:
    """Test basic MCP server functionality."""

    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager."""
        mock_db = Mock(spec=DatabaseManager)
        mock_db.db_path = ":memory:"
        mock_db.get_sync_status.return_value = {
            "database_size_mb": 1.5,
            "total_conversations": 0,
            "total_messages": 0,
            "last_sync": None,
            "database_path": ":memory:",
            "recent_syncs": [],
        }
        mock_db.search_conversations.return_value = []
        mock_db.get_data_freshness_for_timeframe.return_value = 0
        mock_db.record_request_pattern = Mock()
        return mock_db

    @pytest.fixture
    def server(self, mock_database_manager):
        """Create a FastIntercomMCPServer instance for testing."""
        # Simplified architecture - no sync service or intercom client needed for basic tests
        return FastIntercomMCPServer(
            database_manager=mock_database_manager,
            sync_service=None,
            intercom_client=None,
        )

    def test_server_can_be_created(self, server):
        """Test that the MCP server can be created without errors."""
        assert server is not None
        assert hasattr(server, "server")
        assert hasattr(server, "db")
        # In simplified architecture, sync_service and intercom_client are optional
        assert hasattr(server, "sync_service")
        assert hasattr(server, "intercom_client")

    def test_server_mcp_registration(self, server):
        """Test that MCP request handlers are properly registered."""
        from mcp.types import CallToolRequest, ListToolsRequest

        # Check that key MCP request types are registered
        registered_types = list(server.server.request_handlers.keys())
        assert ListToolsRequest in registered_types
        assert CallToolRequest in registered_types

        # Verify handlers are callable
        list_tools_handler = server.server.request_handlers[ListToolsRequest]
        call_tool_handler = server.server.request_handlers[CallToolRequest]
        assert callable(list_tools_handler)
        assert callable(call_tool_handler)

    def test_server_initialization_options(self, server):
        """Test that server can create initialization options."""
        options = server.server.create_initialization_options()
        assert options is not None
        assert hasattr(options, "server_name")
        assert hasattr(options, "server_version")
        assert hasattr(options, "capabilities")

        # Verify the values
        assert options.server_name == "fastintercom"
        assert options.server_version is not None
        assert options.capabilities is not None
