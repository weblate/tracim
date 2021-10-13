"""add user_calls table

Revision ID: 4a9a9c4890de
Revises: 94893551ad7c
Create Date: 2021-09-21 11:09:24.013727

"""
# revision identifiers, used by Alembic.
from alembic import op
import sqlalchemy as sa

revision = "4a9a9c4890de"
down_revision = "94893551ad7c"


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user_calls",
        sa.Column("call_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caller_id", sa.Integer(), nullable=False),
        sa.Column("callee_id", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "IN_PROGRESS",
                "ACCEPTED",
                "REJECTED",
                "DECLINED",
                "POSTPONED",
                "CANCELLED",
                "UNANSWERED",
                name="usercallstate",
            ),
            server_default="IN_PROGRESS",
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.ForeignKeyConstraint(
            ["callee_id"], ["users.user_id"], name=op.f("fk_user_calls_callee_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["caller_id"], ["users.user_id"], name=op.f("fk_user_calls_caller_id_users")
        ),
        sa.PrimaryKeyConstraint("call_id", name=op.f("pk_user_calls")),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("user_calls")
    sa.Enum(name="usercallstate").drop(op.get_bind(), checkfirst=False)

    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP SEQUENCE IF EXISTS user_calls_call_id_seq;")

    # ### end Alembic commands ###
