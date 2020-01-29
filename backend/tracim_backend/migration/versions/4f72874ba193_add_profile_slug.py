"""add profile_slug

Revision ID: 4f72874ba193
Revises: 3de3e7f2b049
Create Date: 2020-01-24 16:30:16.365418

"""
from datetime import datetime
import enum

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Sequence
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq__%(table_name)s__%(column_0_name)s",  # Unique constrains
    # for ck contraint.
    # "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)
DeclarativeBase = declarative_base(metadata=metadata)


# revision identifiers, used by Alembic.
revision = "4f72874ba193"
down_revision = "3de3e7f2b049"


class TemporaryProfileEnum(enum.Enum):
    """This model is the "max" group associated to a given user."""

    NOBODY = (0, "nobody")
    USER = (1, "users")
    TRUSTED_USER = (2, "trusted-users")
    ADMIN = (3, "administrators")

    def __init__(self, profile_id: int, slug: str):
        self.id = profile_id
        self.slug = slug

    @classmethod
    def get_all_valid_slugs(cls, include_nobody: bool = False):
        if include_nobody:
            return [item.slug for item in list(cls)]
        return [item.slug for item in list(cls) if item.id > 0]

    @classmethod
    def get_profile_from_id(cls, id: int):
        profiles = [item for item in list(cls) if item.id == id]
        if len(profiles) != 1:
            raise Exception()
        return profiles[0]

    @classmethod
    def get_profile_from_slug(cls, slug: str):
        profiles = [item for item in list(cls) if item.slug == slug]
        if len(profiles) != 1:
            raise Exception()
        return profiles[0]


class TemporaryUsers(DeclarativeBase):
    """ temporary sqlalchemy object to help migration"""

    __tablename__ = "users"
    user_id = Column(Integer, Sequence("seq__users__user_id"), autoincrement=True, primary_key=True)
    profile = Column(
        Enum(TemporaryProfileEnum), nullable=True, server_default=TemporaryProfileEnum.NOBODY.name
    )


user_group_table = Table(
    "user_group",
    metadata,
    Column("user_id", Integer, ForeignKey("users.user_id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.group_id"), primary_key=True),
)


class TemporaryGroups(DeclarativeBase):
    __tablename__ = "groups"

    group_id = Column(
        Integer, Sequence("seq__groups__group_id"), autoincrement=True, primary_key=True
    )
    group_name = Column(Unicode(16), unique=True, nullable=False)
    display_name = Column(Unicode(255))
    created = Column(DateTime, default=datetime.utcnow)
    users = relationship("TemporaryUsers", secondary=user_group_table, backref="groups")


def upgrade():
    enum = sa.Enum("NOBODY", "USER", "TRUSTED_USER", "ADMIN", name="profiles")
    enum.create(op.get_bind(), checkfirst=False)
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("profile", enum, server_default="NOBODY", nullable=False))
    # ### end Alembic commands ###
    connection = op.get_bind()
    session = Session(bind=connection)
    # INFO - G.M - 2019-09-20 - get one tracim admin as fallback
    users = session.query(TemporaryUsers)
    for user in users:
        profile_id = 0
        if len(user.groups) > 0:
            profile_id = max(group.group_id for group in user.groups)
        profile = TemporaryProfileEnum.get_profile_from_id(profile_id)
        user.profile = profile
    session.commit()

    op.drop_table("groups")
    op.drop_table("user_group")


def downgrade():
    op.create_table(
        "groups",
        sa.Column("group_id", sa.INTEGER(), nullable=False),
        sa.Column("group_name", sa.VARCHAR(length=16), nullable=False),
        sa.Column("display_name", sa.VARCHAR(length=255), nullable=True),
        sa.Column("created", sa.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint("group_id", name="pk_groups"),
        sa.UniqueConstraint("group_name", name="uq__groups__group_name"),
    )
    op.create_table(
        "user_group",
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("group_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.group_id"],
            name="fk_user_group_group_id_groups",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_user_group_user_id_users",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "group_id", name="pk_user_group"),
    )

    connection = op.get_bind()
    session = Session(bind=connection)

    g1 = TemporaryGroups()
    g1.group_id = 1
    g1.group_name = "users"
    g1.display_name = "Users"
    session.add(g1)

    g2 = TemporaryGroups()
    g2.group_id = 2
    g2.group_name = "trusted-users"
    g2.display_name = "Trusted Users"
    session.add(g2)

    g3 = TemporaryGroups()
    g3.group_id = 3
    g3.group_name = "administrators"
    g3.display_name = "Administrators"
    session.add(g3)

    users = session.query(TemporaryUsers)
    group_profile_id_convert = {1: g1, 2: g2, 3: g3}
    for user in users:
        user.groups = [group_profile_id_convert[user.profile.id]]
    session.commit()

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("profile")
    sa.Enum(name="profiles").drop(op.get_bind(), checkfirst=False)
    # ### end Alembic commands ###
