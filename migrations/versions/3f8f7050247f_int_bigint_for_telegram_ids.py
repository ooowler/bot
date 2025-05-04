"""Int → BigInt for telegram IDs

Revision ID: 3f8f7050247f
Revises: cfe818f60a44
Create Date: 2025‑05‑05 00:10:10.925597
"""

from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f8f7050247f"
down_revision: Union[str, None] = "cfe818f60a44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ───────────────────────────────────────── upgrade ─────────────────────────────
def upgrade() -> None:
    # accounts.owner_tid  INT → BIGINT
    op.alter_column(
        "accounts",
        "owner_tid",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )

    # users.telegram_id  VARCHAR → BIGINT   (нужно явное USING)
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.VARCHAR(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="telegram_id::bigint",
    )

    # user_friends.user_id  INT → BIGINT
    op.alter_column(
        "user_friends",
        "user_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    # user_friends.friend_id  INT → BIGINT
    op.alter_column(
        "user_friends",
        "friend_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


# ───────────────────────────────────────── downgrade ───────────────────────────
def downgrade() -> None:
    # откат user_friends.friend_id
    op.alter_column(
        "user_friends",
        "friend_id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
    # откат user_friends.user_id
    op.alter_column(
        "user_friends",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )

    # откат users.telegram_id  BIGINT → VARCHAR
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(),
        existing_nullable=False,
        postgresql_using="telegram_id::varchar",
    )

    # откат accounts.owner_tid  BIGINT → INT
    op.alter_column(
        "accounts",
        "owner_tid",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
