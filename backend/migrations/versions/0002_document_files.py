"""Durable database storage for upload bytes on hosts with ephemeral filesystems."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    # Some local instances create tables at startup before migrations run.
    if 'document_files' not in inspect(op.get_bind()).get_table_names():
        op.create_table('document_files',sa.Column('document_id',sa.String(32),sa.ForeignKey('research_documents.id',ondelete='CASCADE'),primary_key=True),sa.Column('content',sa.LargeBinary(),nullable=False))
def downgrade(): op.drop_table('document_files')
