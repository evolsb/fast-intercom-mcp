"""Basic MCP protocol functionality tests."""

from unittest.mock import Mock

import pytest

from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.mcp_server import FastIntercomMCPServer


class TestBasicFunctionality:
    """Test basic MCP protocol functionality."""

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

    def test_database_integration(self, server):
        """Test that database integration works."""
        # Test database is accessible
        assert server.db is not None
        assert hasattr(server.db, "get_sync_status")

        # Test mock database returns expected data
        status = server.db.get_sync_status()
        assert isinstance(status, dict)
        assert "total_conversations" in status
        assert "total_messages" in status
        assert "database_path" in status

    def test_server_has_mcp_components(self, server):
        """Test that server has required MCP components."""
        # Check that MCP server is initialized
        assert server.server is not None

        # Check that it has the core MCP attributes
        assert hasattr(server.server, "name")
        assert hasattr(server.server, "version")
        assert hasattr(server.server, "request_handlers")
        assert hasattr(server.server, "notification_handlers")

        # Verify MCP request handlers are registered
        assert len(server.server.request_handlers) > 0
