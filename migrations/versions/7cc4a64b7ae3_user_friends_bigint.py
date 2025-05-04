"""user_friends bigint

Revision ID: 7cc4a64b7ae3
Revises: 3f8f7050247f
Create Date: 2025-05-05 00:33:52.858399

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7cc4a64b7ae3"
down_revision: Union[str, None] = "3f8f7050247f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "user_friends",
        "user_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "user_friends",
        "friend_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        nullable=False,
    )


def downgrade():
    op.alter_column(
        "user_friends",
        "friend_id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "user_friends",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        nullable=False,
    )
