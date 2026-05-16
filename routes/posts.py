from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from models.database import db, Post, LinkedInAccount
from services.ai_generator import AIGenerator
from services.linkedin_api import LinkedInAPI
from config import Config
from datetime import datetime, timezone


def _to_utc_naive(dt_str: str) -> datetime:
    """Convert an ISO 8601 string (with or without timezone offset) to a UTC-naive datetime.
    
    The browser sends the local time the user picked, e.g. '2026-05-08T16:36:00+05:30'.
    We convert it to UTC (11:06:00) before storing so the scheduler's utcnow() comparison works.
    """
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is not None:
        # Has timezone info — convert to UTC and strip the tzinfo
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

posts_bp = Blueprint('posts', __name__)

def _get_ai():
    """Lazy-init AIGenerator so a missing GROQ_API_KEY never crashes startup."""
    return AIGenerator(Config.GROQ_API_KEY)

def _get_linkedin_api():
    """Lazy-init LinkedInAPI so missing credentials never crash startup."""
    return LinkedInAPI(
        Config.LINKEDIN_CLIENT_ID,
        Config.LINKEDIN_CLIENT_SECRET,
        Config.LINKEDIN_REDIRECT_URI,
    )

@posts_bp.route('/generate', methods=['POST'])
@login_required
def generate_content():
    data = request.get_json()
    topic = data.get('topic')
    tone = data.get('tone', 'Professional')
    length = data.get('length', 'Medium')
    image_style = data.get('imageStyle', 'Professional')

    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    ai_gen = _get_ai()
    text = ai_gen.generate_text(topic, tone, length)
    image_url = ai_gen.generate_image_url(topic, image_style)

    return jsonify({
        'text': text,
        'image_url': image_url
    })

@posts_bp.route('', methods=['POST'])
@login_required
def create_post():
    data = request.get_json()
    active_account_id = session.get('active_account_id')
    
    # If no active account in session, pick the first one available for the user
    if not active_account_id:
        account = LinkedInAccount.query.filter_by(user_id=current_user.id).first()
        if account:
            active_account_id = account.id
        else:
            return jsonify({'error': 'No LinkedIn account connected. Please connect one in Settings.'}), 400


    new_post = Post(
        user_id=current_user.id,
        linkedin_account_id=active_account_id,
        topic=data.get('topic'),
        generated_text=data.get('generated_text'),
        generated_image_url=data.get('generated_image_url'),
        status=data.get('status', 'Draft'), # Draft, Scheduled
        tone=data.get('tone'),
        length=data.get('length'),
        image_style=data.get('image_style')
    )

    if data.get('scheduled_time'):
        try:
            new_post.scheduled_time = _to_utc_naive(data['scheduled_time'])  # Store as UTC
            new_post.status = 'Scheduled'
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid date format'}), 400

    db.session.add(new_post)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'post_id': new_post.id
    })

@posts_bp.route('/<int:id>', methods=['PUT'])
@login_required
def update_post(id):
    post = Post.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    
    if 'topic' in data: post.topic = data['topic']
    if 'generated_text' in data: post.generated_text = data['generated_text']
    if 'status' in data: post.status = data['status']
    if 'scheduled_time' in data:
        try:
            if data['scheduled_time']:
                post.scheduled_time = _to_utc_naive(data['scheduled_time'])  # Store as UTC
                # Auto-promote: if a draft gets a scheduled time, flip it to Scheduled
                if post.status in ('Draft', 'Failed'):
                    post.status = 'Scheduled'
            else:
                post.scheduled_time = None
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid date format'}), 400
            
    db.session.commit()
    return jsonify({'status': 'success'})

@posts_bp.route('/<int:id>', methods=['DELETE'])
@login_required
def delete_post(id):
    post = Post.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(post)
    db.session.commit()
    return jsonify({'status': 'success'})


@posts_bp.route('/<int:id>', methods=['GET'])
@login_required
def get_post(id):
    """Fetch a single post by ID — used by the calendar preview modal."""
    post = Post.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return jsonify({
        'id': post.id,
        'topic': post.topic,
        'text': post.generated_text,
        'image_url': post.generated_image_url,
        'status': post.status,
        'scheduled_time': (post.scheduled_time.isoformat() + 'Z') if post.scheduled_time else None,
        'created_at': post.created_at.isoformat()
    })


@posts_bp.route('', methods=['GET'])
@login_required
def get_posts():
    active_account_id = session.get('active_account_id')
    status = request.args.get('status')
    
    query = Post.query.filter_by(user_id=current_user.id)
    if active_account_id:
        query = query.filter_by(linkedin_account_id=active_account_id)
    if status:
        query = query.filter_by(status=status)
        
    posts = query.order_by(Post.created_at.desc()).all()
    
    return jsonify([{
        'id': p.id,
        'topic': p.topic,
        'text': p.generated_text,
        'image_url': p.generated_image_url,
        'status': p.status,
        'scheduled_time': (p.scheduled_time.isoformat() + 'Z') if p.scheduled_time else None,
        'created_at': p.created_at.isoformat()
    } for p in posts])

@posts_bp.route('/<int:id>/publish', methods=['POST'])
@login_required
def publish_post(id):
    post = Post.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    account = db.session.get(LinkedInAccount, post.linkedin_account_id)

    if not account or not account.linkedin_token:
        return jsonify({'error': 'LinkedIn account not connected'}), 400

    # Guard: never publish a blank post
    if not post.generated_text or not post.generated_text.strip():
        return jsonify({'error': 'Post has no content. Please generate content before publishing.'}), 400

    try:
        linkedin_api = _get_linkedin_api()
        post_id = linkedin_api.create_post(
            access_token=account.linkedin_token,
            author_urn=account.linkedin_id,
            text=post.generated_text,
            image_url=post.generated_image_url
        )
        post.status = 'Published'
        post.linkedin_post_id = post_id
        db.session.commit()
        return jsonify({'status': 'success', 'linkedin_post_id': post_id})
    except Exception as e:
        post.status = 'Failed'
        post.error_message = str(e)
        db.session.commit()
        return jsonify({'error': str(e)}), 500
