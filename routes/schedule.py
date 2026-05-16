from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from models.database import db, Post, Schedule
from datetime import datetime
from services.ai_generator import AIGenerator
from config import Config

def _get_ai():
    """Lazy-init AIGenerator — prevents startup crash when GROQ_API_KEY is missing."""
    return AIGenerator(Config.GROQ_API_KEY)

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route('', methods=['GET', 'POST'])
@login_required
def handle_schedule():
    active_account_id = session.get('active_account_id')
    if request.method == 'GET':
        schedules = Schedule.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': s.id,
            'day_of_week': s.day_of_week,
            'time': s.time.strftime('%H:%M'),
            'is_active': s.is_active
        } for s in schedules])
    
    if request.method == 'POST':
        data = request.get_json()
        new_schedule = Schedule(
            user_id=current_user.id,
            day_of_week=data.get('day_of_week'),
            time=datetime.strptime(data.get('time'), '%H:%M').time(),
            is_active=data.get('is_active', True)
        )
        db.session.add(new_schedule)
        db.session.commit()
        return jsonify({'status': 'success', 'id': new_schedule.id})

@schedule_bp.route('/calendar', methods=['GET'])
@login_required
def get_calendar():
    active_account_id = session.get('active_account_id')
    # Fetch all posts (Scheduled, Published, etc.) for the calendar
    posts = Post.query.filter_by(user_id=current_user.id)
    if active_account_id:
        posts = posts.filter_by(linkedin_account_id=active_account_id)
    
    posts = posts.all()
    
    calendar_events = []
    for p in posts:
        if p.scheduled_time and p.topic and p.topic.strip() and p.topic.lower() != "untitled post":
            calendar_events.append({
                'id': p.id,
                'title': p.topic,
                'start': p.scheduled_time.isoformat() + 'Z',
                'status': p.status,
                'color': '#0a66c2' if p.status == 'Published' else '#F59E0B',
                'extendedProps': {
                    'text': p.generated_text,
                    'image_url': p.generated_image_url or '',
                    'status': p.status
                }
            })

            
    return jsonify(calendar_events)

@schedule_bp.route('/ideas', methods=['GET', 'POST'])
@login_required
def handle_ideas():
    from models.database import Idea
    if request.method == 'GET':
        ideas = Idea.query.filter_by(user_id=current_user.id).order_by(Idea.created_at.desc()).all()
        return jsonify([{
            'id': i.id,
            'content': i.content,
            'created_at': i.created_at.isoformat()
        } for i in ideas])
    
    data = request.get_json()
    new_idea = Idea(
        user_id=current_user.id,
        content=data.get('content')
    )
    db.session.add(new_idea)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_idea.id})

@schedule_bp.route('/ideas/<int:id>', methods=['DELETE'])
@login_required
def delete_idea(id):
    from models.database import Idea
    idea = Idea.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(idea)
    db.session.commit()
    return jsonify({'status': 'success'})

@schedule_bp.route('/ai/suggestions', methods=['GET'])
@login_required
def ai_suggestions():
    # Mock AI suggestions based on LinkedIn algorithm peak times
    # Tuesday-Thursday, 8-10 AM, 12-1 PM, 5-6 PM
    import datetime
    suggestions = []
    today = datetime.date.today()
    for i in range(1, 14): # Suggest for next 2 weeks
        day = today + datetime.timedelta(days=i)
        if day.weekday() in [1, 2, 3]: # Tue, Wed, Thu
            # Morning slot
            suggestions.append({
                'id': f'suggest-{i}-1',
                'title': '✨ Suggestion: Industry Insight',
                'start': datetime.datetime.combine(day, datetime.time(9, 0)).isoformat(),
                'type': 'suggestion',
                'reason': 'LinkedIn peak engagement time'
            })
            # Midday slot
            suggestions.append({
                'id': f'suggest-{i}-2',
                'title': '✨ Suggestion: Personal Story',
                'start': datetime.datetime.combine(day, datetime.time(12, 30)).isoformat(),
                'type': 'suggestion',
                'reason': 'Midday break activity'
            })
    return jsonify(suggestions)

@schedule_bp.route('/ai/fill-month', methods=['POST'])
@login_required
def fill_month():
    """Generate 5 AI-written draft posts via Groq, spaced 2 days apart."""
    import datetime
    from models.database import Post
    today = datetime.date.today()
    new_posts = []

    topics = [
        "AI Trends in LinkedIn",
        "Personal Branding Strategy",
        "Content Automation Tips",
        "Future of Work with AI",
        "Networking Masterclass"
    ]

    for i in range(5):
        topic = topics[i % len(topics)]
        ai_gen = _get_ai()
        # Use Groq to generate real post content
        generated_text = ai_gen.generate_text(topic, tone="Professional", length="Medium")
        day = today + datetime.timedelta(days=i * 2)
        post = Post(
            user_id=current_user.id,
            topic=topic,
            generated_text=generated_text,
            generated_image_url=ai_gen.generate_image_url(topic, "Professional"),
            status='Draft',
            scheduled_time=datetime.datetime.combine(day, datetime.time(9, 0))
        )
        db.session.add(post)
        new_posts.append(post)

    db.session.commit()
    return jsonify({'status': 'success', 'count': len(new_posts)})


@schedule_bp.route('/ai/balance', methods=['POST'])
@login_required
def balance_schedule():
    # Mock: Reschedule all drafts to be at least 2 days apart
    from models.database import Post
    import datetime
    drafts = Post.query.filter_by(user_id=current_user.id, status='Draft').order_by(Post.scheduled_time).all()
    if not drafts: return jsonify({'status': 'success', 'moved': 0})
    
    # Guard: skip posts with no scheduled_time to avoid TypeError
    drafts = [d for d in drafts if d.scheduled_time is not None]
    if not drafts: return jsonify({'status': 'success', 'moved': 0})
    
    current_time = drafts[0].scheduled_time
    moved = 0
    for post in drafts[1:]:
        if (post.scheduled_time - current_time).days < 2:
            post.scheduled_time = current_time + datetime.timedelta(days=2)
            moved += 1
        current_time = post.scheduled_time
    db.session.commit()
    return jsonify({'status': 'success', 'moved': moved})

@schedule_bp.route('/ai/theme-week', methods=['POST'])
@login_required
def theme_week():
    """Generate a 5-post themed week series via Groq."""
    data = request.get_json(silent=True) or {}
    topic = data.get('topic', 'Artificial Intelligence')
    import datetime
    from models.database import Post
    today = datetime.date.today()
    # Find next Monday
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = today + datetime.timedelta(days=days_ahead)

    tones = ["Inspirational", "Educational", "Professional", "Conversational", "Storytelling"]
    new_posts = []
    for i in range(5):
        day_topic = f"{topic} Series: Day {i + 1}"
        tone = tones[i % len(tones)]
        ai_gen = _get_ai()
        # Use Groq to generate a unique post for each day
        generated_text = ai_gen.generate_text(day_topic, tone=tone, length="Medium")
        day = next_monday + datetime.timedelta(days=i)
        post = Post(
            user_id=current_user.id,
            topic=day_topic,
            generated_text=generated_text,
            generated_image_url=ai_gen.generate_image_url(day_topic, "Professional"),
            status='Draft',
            scheduled_time=datetime.datetime.combine(day, datetime.time(10, 0))
        )
        db.session.add(post)
        new_posts.append(post)

    db.session.commit()
    return jsonify({'status': 'success', 'count': len(new_posts)})


@schedule_bp.route('/parse-nlp', methods=['POST'])
@login_required
def parse_nlp():
    data = request.get_json()
    text = data.get('text')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    ai_gen = _get_ai()
    parsed = ai_gen.parse_nlp(text)
    if not parsed:
        return jsonify({'error': 'Could not parse text'}), 400
        
    return jsonify(parsed)


