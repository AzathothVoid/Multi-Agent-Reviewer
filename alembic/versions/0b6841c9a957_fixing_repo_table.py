"""fixing repo table

Revision ID: 0b6841c9a957
Revises: 821bb98c7936
Create Date: 2026-01-01 19:06:10.271569

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b6841c9a957"
down_revision: Union[str, Sequence[str], None] = "821bb98c7936"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
