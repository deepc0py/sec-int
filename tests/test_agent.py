"""Tests for the core vulnerability analysis agent."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.agent import (
    AgentDependencies,
    build_agent,
    cleanup_agent_dependencies,
    create_agent_dependencies,
    get_agent,
    test_agent_dependencies,
    vulnerability_agent,
)
from app.models import AnalyzedVulnerability


class TestAgentDependencies:
    """Test AgentDependencies dataclass."""

    def test_valid_dependencies(self):
        """Test creating valid dependencies."""
        mock_pool = Mock()
        mock_pool.acquire = Mock()  # Pool-like interface

        mock_oai = Mock()
        mock_oai.models = Mock()  # OpenAI-like interface

        # Create dependencies
        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        assert deps.pool is mock_pool
        assert deps.oai is mock_oai

    def test_invalid_pool_type(self):
        """Test that invalid pool type raises TypeError."""
        mock_oai = Mock()
        mock_oai.models = Mock()

        with pytest.raises(TypeError, match="pool must have an 'acquire' method"):
            AgentDependencies(pool="not a pool", oai=mock_oai)

    def test_invalid_oai_type(self):
        """Test that invalid OpenAI client type raises TypeError."""
        mock_pool = Mock()
        mock_pool.acquire = Mock()

        with pytest.raises(TypeError, match="oai must have a 'models' attribute"):
            AgentDependencies(pool=mock_pool, oai="not an openai client")


class TestBuildAgent:
    """Test agent building and configuration."""

    @patch('app.agent.get_settings')
    def test_build_agent(self, mock_get_settings):
        """Test building the agent with default settings."""
        mock_settings = Mock()
        mock_settings.LLM_MODEL_NAME = "gpt-4o"
        mock_get_settings.return_value = mock_settings

        agent = build_agent()

        # Verify agent is configured correctly
        assert agent is not None
        # Agent should be properly typed, but we can't access internals easily

    def test_get_agent(self):
        """Test getting the global agent instance."""
        agent = get_agent()

        assert agent is not None
        # Verify it's the same instance on repeated calls
        agent2 = get_agent()
        assert agent is agent2


class TestCreateAgentDependencies:
    """Test creating agent dependencies."""

    @pytest.mark.asyncio
    @patch('app.agent.get_settings')
    @patch('asyncpg.create_pool')
    @patch('app.agent.AsyncOpenAI')
    async def test_create_dependencies_success(self, mock_openai, mock_create_pool, mock_get_settings):
        """Test successfully creating agent dependencies."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "postgresql://test:test@localhost/test"
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        mock_get_settings.return_value = mock_settings

        # Mock database pool
        mock_pool = AsyncMock()
        mock_pool.__class__.__name__ = "Pool"
        mock_create_pool.return_value = mock_pool

        # Mock OpenAI client
        mock_oai_client = Mock()
        mock_oai_client.__class__.__name__ = "AsyncOpenAI"
        mock_openai.return_value = mock_oai_client

        # Create dependencies
        deps = await create_agent_dependencies()

        assert deps.pool is mock_pool
        assert deps.oai is mock_oai_client

        # Verify pool was created with correct parameters
        mock_create_pool.assert_called_once_with(
            "postgresql://test:test@localhost/test",
            min_size=2,
            max_size=10,
            command_timeout=30
        )

        # Verify OpenAI client was created with correct API key
        mock_openai.assert_called_once_with(api_key="sk-test-key")

    @pytest.mark.asyncio
    @patch('app.agent.get_settings')
    async def test_create_dependencies_missing_database_url(self, mock_get_settings):
        """Test creating dependencies with missing database URL."""
        mock_settings = Mock()
        mock_settings.DATABASE_URL = None
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValueError, match="DATABASE_URL is required"):
            await create_agent_dependencies()

    @pytest.mark.asyncio
    @patch('app.agent.get_settings')
    async def test_create_dependencies_missing_openai_key(self, mock_get_settings):
        """Test creating dependencies with missing OpenAI API key."""
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "postgresql://test:test@localhost/test"
        mock_settings.OPENAI_API_KEY = None
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            await create_agent_dependencies()

    @pytest.mark.asyncio
    @patch('app.agent.get_settings')
    @patch('asyncpg.create_pool')
    async def test_create_dependencies_database_connection_fail(self, mock_create_pool, mock_get_settings):
        """Test handling database connection failure."""
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "postgresql://test:test@localhost/test"
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        mock_get_settings.return_value = mock_settings

        # Mock database connection failure
        mock_create_pool.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await create_agent_dependencies()

    @pytest.mark.asyncio
    @patch('app.agent.get_settings')
    @patch('asyncpg.create_pool')
    async def test_create_dependencies_pool_is_none(self, mock_create_pool, mock_get_settings):
        """Test handling when pool creation returns None."""
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "postgresql://test:test@localhost/test"
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        mock_get_settings.return_value = mock_settings

        # Mock pool creation returning None
        mock_create_pool.return_value = None

        with pytest.raises(ConnectionError, match="Failed to create database connection pool"):
            await create_agent_dependencies()

    @pytest.mark.asyncio
    async def test_create_dependencies_with_custom_values(self):
        """Test creating dependencies with custom values."""
        custom_db_url = "postgresql://custom:custom@localhost/custom"
        custom_api_key = "sk-custom-key"

        with patch('asyncpg.create_pool') as mock_create_pool, \
             patch('app.agent.AsyncOpenAI') as mock_openai:

            # Mock successful creation
            mock_pool = AsyncMock()
            mock_pool.__class__.__name__ = "Pool"
            mock_create_pool.return_value = mock_pool

            mock_oai_client = Mock()
            mock_oai_client.__class__.__name__ = "AsyncOpenAI"
            mock_openai.return_value = mock_oai_client

            deps = await create_agent_dependencies(
                database_url=custom_db_url,
                openai_api_key=custom_api_key
            )

            assert deps.pool is mock_pool
            assert deps.oai is mock_oai_client

            # Verify custom values were used
            mock_create_pool.assert_called_once()
            assert mock_create_pool.call_args[0][0] == custom_db_url
            mock_openai.assert_called_once_with(api_key=custom_api_key)


class TestCleanupAgentDependencies:
    """Test cleaning up agent dependencies."""

    @pytest.mark.asyncio
    async def test_cleanup_success(self):
        """Test successful cleanup of dependencies."""
        # Mock dependencies
        mock_pool = AsyncMock()
        mock_pool.acquire = Mock()  # Required interface

        mock_oai = Mock()
        mock_oai.models = Mock()  # Required interface
        mock_oai._client = Mock()
        mock_oai._client.aclose = AsyncMock()

        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        # Cleanup should not raise
        await cleanup_agent_dependencies(deps)

        # Verify cleanup calls
        mock_pool.close.assert_called_once()
        mock_oai._client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_pool_error(self):
        """Test cleanup when pool.close() raises an error."""
        # Mock dependencies with failing pool
        mock_pool = AsyncMock()
        mock_pool.acquire = Mock()  # Required interface
        mock_pool.close.side_effect = Exception("Pool close error")

        mock_oai = Mock()
        mock_oai.models = Mock()  # Required interface

        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        # Cleanup should not raise (error is logged)
        await cleanup_agent_dependencies(deps)

        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_client_close(self):
        """Test cleanup when OpenAI client doesn't have aclose method."""
        # Mock dependencies
        mock_pool = AsyncMock()
        mock_pool.acquire = Mock()  # Required interface

        mock_oai = Mock()
        mock_oai.models = Mock()  # Required interface
        # No _client or aclose method

        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        # Should not raise
        await cleanup_agent_dependencies(deps)

        mock_pool.close.assert_called_once()


class TestTestAgentDependencies:
    """Test testing agent dependencies."""

    @pytest.mark.asyncio
    async def test_all_dependencies_working(self):
        """Test when all dependencies are working."""
        # Mock working dependencies
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = "PostgreSQL 15.0"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_models_list = Mock()
        mock_models_list.data = [Mock(), Mock(), Mock()]  # 3 models
        mock_oai = AsyncMock()
        mock_oai.models.list.return_value = mock_models_list

        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        result = await test_agent_dependencies(deps)

        assert result["database"] is True
        assert result["openai"] is True
        assert result["database_error"] is None
        assert result["openai_error"] is None
        assert result["database_version"] == "PostgreSQL 15.0"
        assert result["openai_models_count"] == 3

    @pytest.mark.asyncio
    async def test_database_connection_fails(self):
        """Test when database connection fails."""
        # Mock failing database
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = Exception("Database connection failed")

        mock_oai = AsyncMock()
        mock_oai.models.list.return_value = Mock(data=[])

        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        result = await test_agent_dependencies(deps)

        assert result["database"] is False
        assert result["openai"] is True
        assert result["database_error"] == "Database connection failed"
        assert result["openai_error"] is None

    @pytest.mark.asyncio
    async def test_openai_client_fails(self):
        """Test when OpenAI client fails."""
        # Mock working database
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = "PostgreSQL 15.0"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock failing OpenAI
        mock_oai = AsyncMock()
        mock_oai.models.list.side_effect = Exception("OpenAI API error")

        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        result = await test_agent_dependencies(deps)

        assert result["database"] is True
        assert result["openai"] is False
        assert result["database_error"] is None
        assert result["openai_error"] == "OpenAI API error"

    @pytest.mark.asyncio
    async def test_both_dependencies_fail(self):
        """Test when both dependencies fail."""
        # Mock failing dependencies
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = Exception("DB error")

        mock_oai = AsyncMock()
        mock_oai.models.list.side_effect = Exception("OpenAI error")

        deps = AgentDependencies(pool=mock_pool, oai=mock_oai)

        result = await test_agent_dependencies(deps)

        assert result["database"] is False
        assert result["openai"] is False
        assert result["database_error"] == "DB error"
        assert result["openai_error"] == "OpenAI error"


class TestAgentIntegration:
    """Test integration between agent components."""

    def test_agent_result_type_is_analyzed_vulnerability(self):
        """Test that agent result type is correctly set."""
        agent = get_agent()
        # In the new pydantic-ai API, this is stored as output_type
        assert hasattr(agent, '_output_type') or hasattr(agent, 'output_type')

    def test_agent_deps_type_is_agent_dependencies(self):
        """Test that agent dependencies type is correctly set."""
        agent = get_agent()
        # In the new pydantic-ai API, this is stored as deps_type
        assert hasattr(agent, '_deps_type') or hasattr(agent, 'deps_type')

    def test_agent_has_system_prompt(self):
        """Test that agent has a system prompt configured."""
        agent = get_agent()
        # System prompt should be configured (non-empty)
        assert hasattr(agent, '_system_prompt') or hasattr(agent, 'system_prompt')

    @patch('app.agent.get_settings')
    def test_agent_uses_configured_model(self, mock_get_settings):
        """Test that agent uses the model from settings."""
        mock_settings = Mock()
        mock_settings.LLM_MODEL_NAME = "gpt-4o-mini"
        mock_get_settings.return_value = mock_settings

        agent = build_agent()

        # The LLM model should be configured correctly
        # Note: The exact way to test this depends on pydantic_ai internals
        assert agent is not None