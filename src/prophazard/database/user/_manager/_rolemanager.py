from typing_extensions import override

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..._base._basemanager import _BaseManager
from .._orm import Role, Permission


class RoleManager(_BaseManager[Role]):

    @property
    @override
    def _table_class(self) -> type[Role]:
        """
        Property holding the respective class type for the database object

        :return Type[User]: Returns the User class
        """
        return Role

    @_BaseManager._optional_session
    async def role_by_name(self, session: AsyncSession, name: str) -> Role | None:
        """
        Get a role by name.

        :param AsyncSession session: _description_
        :param str name: Role name
        :return Role | None: The retrieved role object.
        """
        statement = select(Role).where(Role.name == name)
        return await session.scalar(statement)

    @_BaseManager._optional_session
    async def verify_persistant_role(
        self, session: AsyncSession, name: str, permissions: set[Permission]
    ) -> None:
        """
        Verify permissions are setup for a role.

        :param AsyncSession session: _description_
        :param str name: Name of role to check
        :param set[Permission] permissions: Set of permissions to apply
        """
        if await self.role_by_name(session, name) is None:
            role = Role(name=name, permissions=permissions, persistent=True)
            await self.add(session, role)
            await session.flush()