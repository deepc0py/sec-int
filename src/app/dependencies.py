"""Simple dependency injection for FastAPI endpoints."""

from typing import Annotated

import asyncpg
from fastapi import Depends
from openai import AsyncOpenAI

from app.agent import AgentDependencies
from app.config import Settings, get_settings


class AppDependencies:
    """Container for application-wide dependencies."""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self.oai: AsyncOpenAI | None = None
        self._initialized = False

    async def initialize(self, settings: Settings):
        """Initialize dependencies."""
        if self._initialized:
            return

        self.pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
        self.oai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._initialized = True

    async def cleanup(self):
        """Clean up resources."""
        if self.pool:
            await self.pool.close()
        self._initialized = False

    def get_agent_deps(self) -> AgentDependencies:
        """Get agent dependencies."""
        if not self._initialized:
            raise RuntimeError("Dependencies not initialized")
        return AgentDependencies(pool=self.pool, oai=self.oai)


# Global instance (single instance per app)
_app_deps = AppDependencies()


async def get_app_dependencies() -> AppDependencies:
    """Get the global app dependencies instance."""
    return _app_deps


async def get_agent_dependencies() -> AgentDependencies:
    """FastAPI dependency to inject agent dependencies."""
    app_deps = await get_app_dependencies()
    return app_deps.get_agent_deps()


# Type alias for cleaner function signatures
AgentDeps = Annotated[AgentDependencies, Depends(get_agent_dependencies)]
SettingsDep = Annotated[Settings, Depends(get_settings)]