"""The users test factories."""

from app.auth.security import password_hasher
from app.users.enums import Group
from app.users.models import User
from tests.factories.base import BaseFactory

TEST_PASSWORD = "correct-horse-battery-staple"
# Why: argon2 is slow on purpose, so the hash is computed once for all users.
TEST_PASSWORD_HASH = password_hasher.hash(TEST_PASSWORD)


class UserFactory(BaseFactory[User]):
    """A user factory."""

    __model__ = User

    password_hash = TEST_PASSWORD_HASH
    datetime_disabled = None

    @classmethod
    def email(cls) -> str:
        """Return a fake email."""
        return str(cls.__faker__.unique.email())

    @classmethod
    def first_name(cls) -> str:
        """Return a fake first name."""
        return str(cls.__faker__.first_name())

    @classmethod
    def last_name(cls) -> str:
        """Return a fake last name."""
        return str(cls.__faker__.last_name())

    @classmethod
    def groups(cls) -> list[str]:
        """Return the default groups."""
        return [Group.MEMBER]
