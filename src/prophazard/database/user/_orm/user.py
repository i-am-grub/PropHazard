"""
ORM classes for User data
"""

import logging
import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    HashingError,
    VerificationError,
    InvalidHashError,
)

from ..._base import _UserBase
from .role import Role


logger = logging.Logger(__name__)

_ph = PasswordHasher()

user_role_association = Table(
    "user_role_mapping",
    _UserBase.metadata,
    Column("user", ForeignKey("user.id"), primary_key=True),
    Column("role", ForeignKey("role.id"), primary_key=True),
)


class User(_UserBase):
    """
    User for the application
    """

    # pylint: disable=W0212

    __tablename__ = "user"

    auth_id: Mapped[UUID] = mapped_column(default=uuid4)
    """The UUID associated with the user"""
    username: Mapped[str] = mapped_column(unique=True)
    """Username of user"""
    first_name: Mapped[str | None] = mapped_column()
    """First name of user"""
    last_name: Mapped[str | None] = mapped_column()
    """Last name of user"""
    _password_hash: Mapped[str | None] = mapped_column()
    """Hash of the user's password"""
    _roles: Mapped[set[Role]] = relationship(secondary=user_role_association)
    """The role of the user"""
    last_login: Mapped[datetime | None] = mapped_column()
    """Time of last authenication"""
    reset_required: Mapped[bool] = mapped_column()
    """A flag signaling the user's password should be reset"""

    def __init__(
        self,
        username: str,
        *,
        roles: set[Role] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        persistent: bool = False,
    ):
        """
        Class initialization

        :param username: The username to set for the user
        :param roles: The roles to designate to
        the user, defaults to None
        :param first_name: The first name of the user
        , defaults to None
        :param last_name: The last name of the user,
        defaults to None
        :param persistent: When set to `True` prevents the object
        from being deleted from the database, defaults to False
        """
        # pylint: disable=R0913

        self.username = username
        self._roles = set() if roles is None else roles

        self.first_name = first_name if first_name is not None else None
        self.last_name = last_name if last_name is not None else None
        self.persistent = persistent
        self.reset_required = True

    @property
    async def permissions(self) -> set[str]:
        """
        Gets the permissions for the user. Can only be used when a
        session to the database has not been closed

        :return: The set of permissions
        """
        permissions: set[str] = set()

        roles: set[Role] = await self.awaitable_attrs._roles
        for role in roles:
            permissions = permissions | await role.get_permissions()

        return permissions

    @staticmethod
    def _generate_hash(password: str) -> str | None:
        """
        Generates a hash of the provided password. Thread
        safely.

        :param password: The password to hash.
        :return: The hashed password
        """
        try:
            result = _ph.hash(password)
        except HashingError:
            logger.error("Failed to hash password")
            result = None

        return result

    async def generate_hash(self, password: str) -> str:
        """
        Generates a hash of the provided password without blocking.

        :param password: The password to hash.
        :return: The hashed password
        """
        result = await asyncio.to_thread(self._generate_hash, password)

        if result is None:
            raise HashingError()

        return result

    @staticmethod
    def _verify_password(password_hash: str, password: str, username: str) -> bool:
        """
        Checks a hash of the provided password against a provided hash.

        The function is setup to be ran thread safe

        :param password: The password to hash.
        :return: Whether the comparsion of the hash was sucessful or not.
        """
        try:
            result = _ph.verify(password_hash, password)
        except VerifyMismatchError:
            logger.warning("Failed password attempt for %s", username)
            return False
        except VerificationError:
            logger.error("Failed verification error for %s", username)
            return False
        except InvalidHashError:
            logger.warning("Invalid hash error for %s", username)
            return False

        return result

    async def verify_password(self, password: str) -> bool:
        """
        Checks a hash of the provided password against the hash in the database.

        :param password: The password to hash.
        :return: Whether the comparsion of the hash was sucessful or not.
        """

        if self._password_hash is None:
            return False

        result = await asyncio.to_thread(
            self._verify_password, self._password_hash, password, self.username
        )

        return result

    async def check_password_rehash(self) -> bool:
        """
        Checks if the user's password needs to be rehashed due to a
        configuration change.

        :return: The status of the check
        """
        if self._password_hash is None:
            return True

        result = await asyncio.to_thread(_ph.check_needs_rehash, self._password_hash)
        return result
