"""
asdf
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from ..._base import _UserBase
from ._usermanager import UserManager
from ._rolemanager import RoleManager
from ._permissionmanager import PermissionManager


class UserDatabaseManager:

    def __init__(self, *, filename: str = ":memory:"):
        """
        Class initialization

        :param str filename: Filename for the database, defaults to ":memory:"
        """

        self.engine = create_async_engine(f"sqlite+aiosqlite:///{filename}", echo=False)
        default_session_maker = self.new_session_maker()

        self.users = UserManager(default_session_maker)
        self.roles = RoleManager(default_session_maker)
        self.permissions = PermissionManager(default_session_maker)

    async def setup(self) -> None:
        """
        Setup the database connection. Used at server startup.
        """

        async with self.engine.begin() as conn:
            await conn.run_sync(_UserBase.metadata.create_all)

    async def verify_persistant_objects(
        self, defualt_username: str, default_password: str
    ):
        """
        Verify that the default object are in the database.

        :param str defualt_username: Default username to use for the admin user
        :param str default_password: Default password to use for the admin user
        """
        await self.permissions.verify_persistant()
        permissions = await self.permissions.get_all(None)
        await self.roles.verify_persistant_role(None, "SYSTEM_ADMIN", set(permissions))

        roles = set()
        if (role := await self.roles.role_by_name(None, "SYSTEM_ADMIN")) is not None:
            roles.add(role)

        await self.users.verify_persistant_user(
            None, defualt_username, default_password, roles
        )

    async def shutdown(self) -> None:
        """
        Shutdown the database connection.
        """

        await self.engine.dispose()

    def new_session_maker(self, *args, **kwargs) -> async_sessionmaker[AsyncSession]:
        """A wrapper for async_sessionmaker with `autoflush`, `autocommit`, and
        `expire_on_commit` set to `False`

        :param expire_on_commit: _description_, defaults to False
        :type expire_on_commit: bool, optional
        :return: _description_
        :rtype: async_sessionmaker
        """
        kwargs["autoflush"] = False
        kwargs["autocommit"] = False
        kwargs["expire_on_commit"] = False

        return async_sessionmaker(self.engine, *args, **kwargs)
