"""Update schema align with design docs

Revision ID: 0efbe8935fab
Revises: 706bffd3db3b
Create Date: 2026-03-09 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0efbe8935fab"
down_revision: Union[str, Sequence[str], None] = "706bffd3db3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: thêm clerk_id ──────────────────────────────────────────────────
    op.add_column("users", sa.Column("clerk_id", sa.String(), nullable=True))
    # Backfill: dùng id hiện tại làm clerk_id tạm
    op.execute("UPDATE users SET clerk_id = id WHERE clerk_id IS NULL")
    op.alter_column("users", "clerk_id", nullable=False)
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)

    # ── projects: thêm is_deleted, updated_at ────────────────────────────────
    op.add_column("projects", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("projects", sa.Column("updated_at", sa.DateTime(timezone=True),
                                        server_default=sa.text("now()"), nullable=True))
    op.create_index("ix_projects_is_deleted", "projects", ["is_deleted"])

    # ── chats: drop cột role/content (cũ), thêm title/is_deleted/updated_at ──
    # Drop quan hệ cũ (chats.role, chats.content không cần nữa)
    op.drop_column("chats", "role")
    op.drop_column("chats", "content")
    op.add_column("chats", sa.Column("title", sa.String(), nullable=False, server_default="Cuộc trò chuyện mới"))
    op.add_column("chats", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("chats", sa.Column("updated_at", sa.DateTime(timezone=True),
                                     server_default=sa.text("now()"), nullable=True))
    op.create_index("ix_chats_is_deleted", "chats", ["is_deleted"])

    # ── chat_messages: bảng mới ───────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("chat_id", sa.String(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"])
    op.create_index("ix_chat_messages_chat_id", "chat_messages", ["chat_id"])

    # ── chapters: bảng mới ───────────────────────────────────────────────────
    op.create_table(
        "chapters",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_chapters_id", "chapters", ["id"])
    op.create_index("ix_chapters_project_id", "chapters", ["project_id"])

    # ── lorebooks: đổi tên cột + thêm fields ─────────────────────────────────
    op.add_column("lorebooks", sa.Column("keyword", sa.String(), nullable=True))
    op.add_column("lorebooks", sa.Column("category", sa.String(), nullable=False, server_default="Rule"))
    op.add_column("lorebooks", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("lorebooks", sa.Column("fts_vector", postgresql.TSVECTOR(), nullable=True))
    op.add_column("lorebooks", sa.Column("updated_at", sa.DateTime(timezone=True),
                                          server_default=sa.text("now()"), nullable=True))

    # Copy data từ cột cũ sang cột mới
    op.execute("UPDATE lorebooks SET keyword = term, description = definition, fts_vector = search_vector")
    op.alter_column("lorebooks", "keyword", nullable=False)
    op.alter_column("lorebooks", "description", nullable=False)

    # Drop cột cũ
    op.drop_index("ix_lorebooks_term", table_name="lorebooks")
    op.drop_column("lorebooks", "term")
    op.drop_column("lorebooks", "definition")
    op.drop_column("lorebooks", "metadata_json")
    op.drop_column("lorebooks", "search_vector")

    op.create_index("ix_lorebooks_keyword", "lorebooks", ["keyword"])
    op.create_index("ix_lorebooks_fts", "lorebooks", ["fts_vector"], postgresql_using="gin")

    # ── Postgres trigger: tự động cập nhật fts_vector khi insert/update lorebook
    op.execute("""
        CREATE OR REPLACE FUNCTION lorebooks_fts_update() RETURNS trigger AS $$
        BEGIN
            NEW.fts_vector := to_tsvector('simple', coalesce(NEW.keyword, '') || ' ' || coalesce(NEW.description, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trig_lorebooks_fts ON lorebooks")
    op.execute("""
        CREATE TRIGGER trig_lorebooks_fts
        BEFORE INSERT OR UPDATE ON lorebooks
        FOR EACH ROW EXECUTE FUNCTION lorebooks_fts_update()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trig_lorebooks_fts ON lorebooks")
    op.execute("DROP FUNCTION IF EXISTS lorebooks_fts_update()")

    op.drop_table("chapters")
    op.drop_table("chat_messages")

    op.drop_index("ix_lorebooks_fts", table_name="lorebooks")
    op.drop_index("ix_lorebooks_keyword", table_name="lorebooks")
    op.add_column("lorebooks", sa.Column("term", sa.String(), nullable=False, server_default=""))
    op.add_column("lorebooks", sa.Column("definition", sa.String(), nullable=False, server_default=""))
    op.add_column("lorebooks", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.add_column("lorebooks", sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True))
    op.execute("UPDATE lorebooks SET term = keyword, definition = description, search_vector = fts_vector")
    op.drop_column("lorebooks", "keyword")
    op.drop_column("lorebooks", "category")
    op.drop_column("lorebooks", "description")
    op.drop_column("lorebooks", "fts_vector")
    op.drop_column("lorebooks", "updated_at")
    op.create_index("ix_lorebooks_term", "lorebooks", ["term"])

    op.drop_index("ix_chats_is_deleted", table_name="chats")
    op.drop_column("chats", "title")
    op.drop_column("chats", "is_deleted")
    op.drop_column("chats", "updated_at")
    op.add_column("chats", sa.Column("role", sa.String(), nullable=False, server_default="user"))
    op.add_column("chats", sa.Column("content", sa.String(), nullable=False, server_default=""))

    op.drop_index("ix_projects_is_deleted", table_name="projects")
    op.drop_column("projects", "is_deleted")
    op.drop_column("projects", "updated_at")

    op.drop_index("ix_users_clerk_id", table_name="users")
    op.drop_column("users", "clerk_id")
