"""fase 4 bloque a - schema multi-tenant

Revision ID: 59662106973d
Revises: 5d2485cf875e
Create Date: 2026-04-16 20:39:52.924225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '59662106973d'
down_revision: Union[str, Sequence[str], None] = '5d2485cf875e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Data in conversations/messages is intentionally discarded (Fase 4 design).
    # These DELETEs must come before any ADD COLUMN NOT NULL on those tables.
    op.execute("DELETE FROM messages")
    op.execute("DELETE FROM conversations")

    # --- New tables -----------------------------------------------------------
    op.create_table('tenants',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('plan', sa.Enum('free', 'pro', 'business', name='tenant_plan'), server_default='free', nullable=False),
    sa.Column('status', sa.Enum('trial', 'active', 'suspended', 'cancelled', name='tenant_status'), server_default='trial', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('contacts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('phone_number', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('zoho_contact_id', sa.String(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_contacts_tenant_id_tenants', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'phone_number', name='uq_contacts_tenant_phone')
    )
    op.create_index('ix_contacts_tenant_id', 'contacts', ['tenant_id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('zoho_user_id', sa.String(), nullable=True),
    sa.Column('role', sa.Enum('admin', 'supervisor', 'agent', name='user_role'), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_users_tenant_id_tenants', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email')
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'], unique=False)
    op.create_index('uq_users_tenant_zoho_user', 'users', ['tenant_id', 'zoho_user_id'], unique=True, postgresql_where=sa.text('zoho_user_id IS NOT NULL'))
    op.create_table('channels',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('phone_number_id', sa.String(), nullable=False),
    sa.Column('business_account_id', sa.String(), nullable=False),
    sa.Column('display_phone_number', sa.String(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=True),
    sa.Column('token', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_channels_created_by_users', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_channels_tenant_id_tenants', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('phone_number_id', name='uq_channels_phone_number_id')
    )
    op.create_index('ix_channels_tenant_id', 'channels', ['tenant_id'], unique=False)
    op.create_table('zoho_connections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('org_id', sa.String(), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=False),
    sa.Column('refresh_token', sa.Text(), nullable=False),
    sa.Column('region', sa.String(), nullable=False),
    sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_zoho_connections_created_by_users', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_zoho_connections_tenant_id_tenants', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('org_id', name='uq_zoho_connections_org_id'),
    sa.UniqueConstraint('tenant_id', name='uq_zoho_connections_tenant_id')
    )

    # --- Modify conversations -------------------------------------------------
    op.add_column('conversations', sa.Column('tenant_id', sa.UUID(), nullable=False))
    op.add_column('conversations', sa.Column('channel_id', sa.UUID(), nullable=False))
    op.add_column('conversations', sa.Column('contact_id', sa.UUID(), nullable=False))
    op.add_column('conversations', sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True))

    # Create conversation_status enum type before altering the column type.
    sa.Enum('open', 'closed', name='conversation_status').create(op.get_bind(), checkfirst=True)
    op.alter_column('conversations', 'status',
               existing_type=sa.VARCHAR(),
               type_=sa.Enum('open', 'closed', name='conversation_status'),
               nullable=False,
               postgresql_using='status::conversation_status')
    op.alter_column('conversations', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               nullable=False,
               server_default=sa.text('now()'))
    op.alter_column('conversations', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               nullable=False,
               server_default=sa.text('now()'))
    # Use literal constraint name — no naming convention is active in this project.
    op.drop_constraint('conversations_contact_number_key', 'conversations', type_='unique')
    op.create_index('ix_conversations_contact_id', 'conversations', ['contact_id'], unique=False)
    op.create_index('ix_conversations_tenant_id', 'conversations', ['tenant_id'], unique=False)
    # DESC on last_message_at for efficient "most recent conversation" queries.
    op.create_index('ix_conversations_tenant_last_msg', 'conversations',
                    ['tenant_id', sa.text('last_message_at DESC')], unique=False)
    op.create_unique_constraint('uq_conversations_channel_contact', 'conversations', ['channel_id', 'contact_id'])
    op.create_foreign_key('fk_conversations_channel_id_channels', 'conversations', 'channels', ['channel_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_conversations_contact_id_contacts', 'conversations', 'contacts', ['contact_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_conversations_tenant_id_tenants', 'conversations', 'tenants', ['tenant_id'], ['id'], ondelete='RESTRICT')
    op.drop_column('conversations', 'zoho_contact_id')
    op.drop_column('conversations', 'contact_number')
    op.drop_column('conversations', 'contact_name')

    # --- Modify messages ------------------------------------------------------
    op.add_column('messages', sa.Column('tenant_id', sa.UUID(), nullable=False))
    op.alter_column('messages', 'timestamp',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('messages', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               nullable=False,
               server_default=sa.text('now()'))
    op.create_index('ix_messages_tenant_id', 'messages', ['tenant_id'], unique=False)
    # Drop the old anonymous FK on conversation_id, replace with named one.
    op.drop_constraint('messages_conversation_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('fk_messages_tenant_id_tenants', 'messages', 'tenants', ['tenant_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_messages_conversation_id_conversations', 'messages', 'conversations', ['conversation_id'], ['id'], ondelete='RESTRICT')


def downgrade() -> None:
    """Downgrade schema."""
    # --- Restore messages -----------------------------------------------------
    op.drop_constraint('fk_messages_conversation_id_conversations', 'messages', type_='foreignkey')
    op.drop_constraint('fk_messages_tenant_id_tenants', 'messages', type_='foreignkey')
    # Restore original anonymous FK (PostgreSQL auto-names it messages_conversation_id_fkey).
    op.create_foreign_key('messages_conversation_id_fkey', 'messages', 'conversations', ['conversation_id'], ['id'])
    op.drop_index('ix_messages_tenant_id', table_name='messages')
    op.alter_column('messages', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               nullable=True,
               server_default=None)
    op.alter_column('messages', 'timestamp',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.drop_column('messages', 'tenant_id')

    # --- Restore conversations ------------------------------------------------
    op.add_column('conversations', sa.Column('contact_name', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('conversations', sa.Column('contact_number', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('conversations', sa.Column('zoho_contact_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint('fk_conversations_tenant_id_tenants', 'conversations', type_='foreignkey')
    op.drop_constraint('fk_conversations_contact_id_contacts', 'conversations', type_='foreignkey')
    op.drop_constraint('fk_conversations_channel_id_channels', 'conversations', type_='foreignkey')
    op.drop_constraint('uq_conversations_channel_contact', 'conversations', type_='unique')
    op.drop_index('ix_conversations_tenant_last_msg', table_name='conversations')
    op.drop_index('ix_conversations_tenant_id', table_name='conversations')
    op.drop_index('ix_conversations_contact_id', table_name='conversations')
    op.create_unique_constraint('conversations_contact_number_key', 'conversations', ['contact_number'], postgresql_nulls_not_distinct=False)
    op.alter_column('conversations', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               nullable=True,
               server_default=None)
    op.alter_column('conversations', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               nullable=True,
               server_default=None)
    op.alter_column('conversations', 'status',
               existing_type=sa.Enum('open', 'closed', name='conversation_status'),
               type_=sa.VARCHAR(),
               nullable=True,
               postgresql_using='status::varchar')
    op.drop_column('conversations', 'last_message_at')
    op.drop_column('conversations', 'contact_id')
    op.drop_column('conversations', 'channel_id')
    op.drop_column('conversations', 'tenant_id')

    # --- Drop new tables (reverse dependency order) --------------------------
    op.drop_table('zoho_connections')
    op.drop_index('ix_channels_tenant_id', table_name='channels')
    op.drop_table('channels')
    op.drop_index('uq_users_tenant_zoho_user', table_name='users', postgresql_where=sa.text('zoho_user_id IS NOT NULL'))
    op.drop_index('ix_users_tenant_id', table_name='users')
    op.drop_table('users')
    op.drop_index('ix_contacts_tenant_id', table_name='contacts')
    op.drop_table('contacts')
    op.drop_table('tenants')

    # --- Drop PostgreSQL enum types (not dropped automatically with tables) --
    sa.Enum(name='conversation_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='tenant_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='tenant_plan').drop(op.get_bind(), checkfirst=True)
