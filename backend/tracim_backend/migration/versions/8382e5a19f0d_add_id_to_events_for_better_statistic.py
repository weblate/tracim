"""add id to events for better statistic

Revision ID: 8382e5a19f0d
Revises: 94893551ad7c
Create Date: 2021-09-08 11:57:57.919572

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "8382e5a19f0d"
down_revision = "7cb0ddd4ed08"

events = sa.Table(
    "events",
    sa.MetaData(),
    sa.Column("author_id", sa.Integer()),
    sa.Column("content_id", sa.Integer()),
    sa.Column("parent_id", sa.Integer()),
    sa.Column("fields", sa.JSON()),
)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("author_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("content_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
    # ### end Alembic commands ###
    connection = op.get_bind()
    connection.execute(
        events.update()
        .where(
            sa.func.cast(events.c.fields["content"]["content_id"], sa.String) != sa.text("'null'"),
        )
        .values(content_id=events.c.fields["content"]["content_id"].as_integer())
    )
    connection.execute(
        events.update()
        .where(sa.func.cast(events.c.fields["author"]["user_id"], sa.String) != sa.text("'null'"),)
        .values(author_id=events.c.fields["author"]["user_id"].as_integer())
    )
    connection.execute(
        events.update()
        .where(
            sa.func.cast(events.c.fields["content"]["parent_id"], sa.String) != sa.text("'null'"),
        )
        .values(parent_id=events.c.fields["content"]["parent_id"].as_integer())
    )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_column("parent_id")
        batch_op.drop_column("content_id")
        batch_op.drop_column("author_id")
    # ### end Alembic commands ###
