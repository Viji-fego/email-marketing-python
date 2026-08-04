"""SQLAlchemy event listener for webhook debugging."""

import logging
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect as sqlalchemy_inspect

logger = logging.getLogger(__name__)


def setup_sqlalchemy_listeners():
    """Attach listeners to trace SQLAlchemy operations."""

    @event.listens_for(Session, "before_flush")
    def receive_before_flush(session, flush_context, instances):
        """Log object state before flush."""
        logger.info("=" * 100)
        logger.info("🔍 BEFORE_FLUSH EVENT - Checking session state")
        logger.info("=" * 100)

        # Log all objects in session
        logger.info("📊 Session Statistics:")
        logger.info(f"   new (to be inserted): {len(session.new)}")
        logger.info(f"   dirty (to be updated): {len(session.dirty)}")
        logger.info(f"   deleted (to be deleted): {len(session.deleted)}")
        logger.info(f"   identity_map (tracked objects): {len(session.identity_map)}")

        # Log all CampaignContact objects
        for identity_key, obj in list(session.identity_map.items()):
            if obj.__class__.__name__ == "CampaignContact":
                insp = sqlalchemy_inspect(obj)
                logger.info("━" * 100)
                logger.info(f"🎯 CampaignContact Object Found:")
                logger.info(f"   Object ID (Python): {id(obj)}")
                logger.info(f"   DB ID: {obj.id}")
                logger.info(f"   SQLAlchemy State PERSISTENT: {bool(insp.persistent)}")
                logger.info(f"   Modified Attributes: {insp.modified}")
                logger.info(f"━ Current Field Values:")
                logger.info(f"      status: {obj.status}")
                logger.info(f"      opened_at: {obj.opened_at}")
                logger.info(f"      clicked_at: {obj.clicked_at}")
                logger.info(f"      last_event: {obj.last_event}")
                logger.info(f"      provider_message_id: {obj.provider_message_id}")
                logger.info("━" * 100)

        # Log all EmailEvent objects
        for identity_key, obj in list(session.identity_map.items()):
            if obj.__class__.__name__ == "EmailEvent":
                insp = sqlalchemy_inspect(obj)
                logger.info(f"✉️ EmailEvent Object:")
                logger.info(f"   DB ID: {obj.id}")
                logger.info(f"   SQLAlchemy State NEW: {bool(insp.pending)}")
                logger.info(f"   event_type: {obj.event_type}")
                logger.info(f"   provider_message_id: {obj.provider_message_id}")

    @event.listens_for(Session, "after_flush")
    def receive_after_flush(session, flush_context):
        """Log after flush."""
        logger.info("=" * 100)
        logger.info("✅ AFTER_FLUSH EVENT - SQL statements executed to database")
        logger.info("=" * 100)

    @event.listens_for(Session, "after_commit")
    def receive_after_commit(session):
        """Log after commit."""
        logger.info("=" * 100)
        logger.info("✅ AFTER_COMMIT EVENT - Transaction successfully committed")
        logger.info("=" * 100)

    @event.listens_for(Session, "after_rollback")
    def receive_after_rollback(session):
        """Log rollback."""
        logger.info("=" * 100)
        logger.info("❌ AFTER_ROLLBACK EVENT - Transaction rolled back")
        logger.info("=" * 100)


def enable_sql_echo(engine):
    """Enable detailed SQL logging."""
    import logging

    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(logging.INFO)

    # Check if handler already exists
    if not sqlalchemy_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        sqlalchemy_logger.addHandler(handler)
