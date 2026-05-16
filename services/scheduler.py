from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from models.database import db, Post, LinkedInAccount
from services.linkedin_api import LinkedInAPI
from config import Config
import logging

# Configure logging — also write to scheduler.log for easy debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_file_handler = logging.FileHandler('scheduler.log', encoding='utf-8')
_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(_file_handler)

def publish_scheduled_posts(app):
    try:
        with app.app_context():
            now = datetime.utcnow()
            logger.info(f"[scheduler tick] UTC now = {now.strftime('%Y-%m-%d %H:%M:%S')}")

            # ----------------------------------------------------------------
            # FIX 1: Row-level lock (SELECT FOR UPDATE) so that if Flask's
            # debug reloader spawns two scheduler processes, only ONE of them
            # claims each post. The second process sees status != 'Scheduled'
            # and skips it — preventing duplicate LinkedIn posts (422 errors).
            # ----------------------------------------------------------------
            posts_to_publish = Post.query.filter(
                Post.status == 'Scheduled',
                Post.scheduled_time <= now
            ).with_for_update(skip_locked=True).all()

            if not posts_to_publish:
                logger.info("[scheduler] No posts due yet.")
                return

            logger.info(f"[scheduler] Found {len(posts_to_publish)} posts to publish.")

            # Immediately claim all due posts by setting status → 'Publishing'
            # so no other scheduler instance picks them up even after the lock releases.
            for post in posts_to_publish:
                post.status = 'Publishing'
            db.session.commit()

            linkedin_api = LinkedInAPI(
                Config.LINKEDIN_CLIENT_ID,
                Config.LINKEDIN_CLIENT_SECRET,
                Config.LINKEDIN_REDIRECT_URI
            )

            for post in posts_to_publish:
                account = db.session.get(LinkedInAccount, post.linkedin_account_id)
                if not account or not account.linkedin_token:
                    post.status = 'Failed'
                    post.error_message = "LinkedIn account not found or token missing."
                    db.session.commit()
                    logger.warning(f"[scheduler] Post {post.id} skipped — no account/token.")
                    continue

                try:
                    # ----------------------------------------------------------------
                    # FIX 2: Posts with no content kept retrying every minute forever.
                    # Mark them Failed immediately so they stop appearing as due.
                    # ----------------------------------------------------------------
                    if not post.generated_text or not post.generated_text.strip():
                        post.status = 'Failed'
                        post.error_message = "Post has no content. Please edit the post and add content before scheduling."
                        db.session.commit()
                        logger.warning(f"[scheduler] Post {post.id} failed — no generated_text.")
                        continue

                    logger.info(f"[scheduler] Publishing post {post.id} (scheduled={post.scheduled_time}) for account {account.name}")
                    post_id = linkedin_api.create_post(
                        access_token=account.linkedin_token,
                        author_urn=account.linkedin_id,
                        text=post.generated_text,
                        image_url=post.generated_image_url
                    )
                    post.status = 'Published'
                    post.linkedin_post_id = post_id
                    post.error_message = None
                    logger.info(f"[scheduler] Successfully published post {post.id}")
                except Exception as e:
                    logger.error(f"[scheduler] Failed to publish post {post.id}: {str(e)}")
                    post.status = 'Failed'
                    post.error_message = str(e)

                db.session.commit()
    except Exception as fatal:
        # Log the error but DO NOT re-raise — APScheduler must keep running
        logger.error(f"[scheduler] Unexpected error in publish_scheduled_posts: {fatal}")

def init_scheduler(app):
    scheduler = BackgroundScheduler()
    # Check for scheduled posts every minute
    scheduler.add_job(
        func=publish_scheduled_posts,
        trigger="interval",
        minutes=1,
        args=[app]
    )
    scheduler.start()
    logger.info("Background Scheduler started.")
    return scheduler
