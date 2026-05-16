# routes/auth.py
import secrets
from flask import Blueprint, jsonify, request, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from models.database import db, User, LinkedInAccount
from services.linkedin_api import LinkedInAPI
from config import Config

auth_bp = Blueprint("auth", __name__)

def _get_linkedin_api():
    """Lazy-instantiate LinkedInAPI so missing credentials don't crash startup."""
    return LinkedInAPI(
        Config.LINKEDIN_CLIENT_ID,
        Config.LINKEDIN_CLIENT_SECRET,
        Config.LINKEDIN_REDIRECT_URI,
    )


@auth_bp.route("/linkedin", methods=["GET"])
def initiate_oauth():
    if not Config.LINKEDIN_CLIENT_ID or not Config.LINKEDIN_CLIENT_SECRET:
        return jsonify({"error": "LinkedIn OAuth credentials not configured."}), 503
    
    # Host mismatch detection
    current_host = request.host
    redirect_uri = Config.LINKEDIN_REDIRECT_URI
    if current_host not in redirect_uri and not (current_host.startswith('127.0.0.1') and 'localhost' in redirect_uri):
        # This is a common cause of "Invalid state parameter"
        print(f"DEBUG: Host mismatch detected! Browser is on {current_host}, but Redirect URI is {redirect_uri}")

    state = secrets.token_urlsafe(16)
    session.permanent = True
    session["linkedin_oauth_state"] = state
    
    linkedin_api = _get_linkedin_api()
    return jsonify({"auth_url": linkedin_api.get_authorization_url(state=state)})


@auth_bp.route("/callback", methods=["GET"])
def oauth_callback():
    code  = request.args.get("code")
    state = request.args.get("state")
    stored_state = session.get("linkedin_oauth_state")

    if not code:
        return jsonify({"error": "Authorization code not provided"}), 400
    
    if state != stored_state:
        # Detailed error for debugging
        error_details = {
            "error": "Invalid state parameter",
            "received": state,
            "stored": stored_state,
            "session_empty": stored_state is None,
            "advice": "Ensure you are using the same host (e.g. localhost vs 127.0.0.1) that you used to start the login."
        }
        print(f"DEBUG: State mismatch: {error_details}")
        return jsonify(error_details), 400

    linkedin_api = _get_linkedin_api()
    try:
        token_data   = linkedin_api.get_access_token(code)
        access_token = token_data.get("access_token")
        profile      = linkedin_api.get_profile(access_token)

        linkedin_id = profile.get("sub")
        if linkedin_id and not linkedin_id.startswith('urn:li:'):
            linkedin_id = f"urn:li:person:{linkedin_id}"
            
        email       = profile.get("email")
        name        = profile.get("name")
        picture     = profile.get("picture")

        # BUG FIX: use db.session.get() — Query.get() is removed in SQLAlchemy 2.x
        account = LinkedInAccount.query.filter_by(linkedin_id=linkedin_id).first()

        if current_user.is_authenticated:
            user = current_user
            if not account:
                account = LinkedInAccount(user_id=user.id, linkedin_id=linkedin_id, account_type='PERSON')
                db.session.add(account)
            elif account.user_id != user.id:
                account.user_id = user.id
        else:
            if account:
                user = db.session.get(User, account.user_id)   # ✅ fixed
            else:
                user = User.query.filter_by(email=email).first()
                if not user:
                    user = User(email=email)
                    db.session.add(user)
                    db.session.flush()   # get user.id without a full commit
                account = LinkedInAccount(user_id=user.id, linkedin_id=linkedin_id, account_type='PERSON')
                db.session.add(account)

        account.linkedin_token       = access_token
        account.name                 = name
        account.profile_picture_url  = picture
        db.session.commit()

        login_user(user, remember=True)
        session["active_account_id"] = account.id
        session.pop("linkedin_oauth_state", None)

        return redirect("/dashboard")

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@auth_bp.route("/accounts", methods=["GET"])
@login_required
def get_accounts():
    accounts  = LinkedInAccount.query.filter_by(user_id=current_user.id).all()
    active_id = session.get("active_account_id")

    if not active_id and accounts:
        active_id = accounts[0].id
        session["active_account_id"] = active_id

    return jsonify(
        {
            "accounts": [
                {
                    "id":                  a.id,
                    "name":                a.name,
                    "profile_picture_url": a.profile_picture_url,
                    "linkedin_id":         a.linkedin_id,
                    "account_type":        a.account_type,
                }
                for a in accounts
            ],
            "active_account_id": active_id,
        }
    )

@auth_bp.route("/organizations", methods=["GET"])
@login_required
def get_organizations():
    active_id = session.get('active_account_id')
    if not active_id:
        return jsonify({'error': 'No personal account connected'}), 400

    account = db.session.get(LinkedInAccount, active_id)
    if not account or not account.linkedin_token:
        return jsonify({'error': 'Active account has no token'}), 400

    try:
        linkedin_api = _get_linkedin_api()
        orgs = linkedin_api.get_organizations(account.linkedin_token)
        return jsonify(orgs)
    except Exception as e:
        err_str = str(e)
        # 403 means the LinkedIn app lacks r_organization_admin scope.
        # Return a structured response so the frontend can show the manual
        # connection UI instead of a red error toast.
        if '403' in err_str:
            return jsonify({'organizations_unavailable': True, 'reason': 'permission'}), 200
        return jsonify({'error': err_str}), 500

@auth_bp.route("/organizations/link", methods=["POST"])
@login_required
def link_organization():
    data = request.get_json()
    org_id = data.get('id') # Full URN
    name = data.get('name')
    
    if not org_id:
        return jsonify({'error': 'Organization ID required'}), 400
        
    # Check if already linked
    account = LinkedInAccount.query.filter_by(linkedin_id=org_id, user_id=current_user.id).first()
    
    # We need the token from the personal account to post to the org
    personal_account = LinkedInAccount.query.filter(
        LinkedInAccount.user_id == current_user.id,
        LinkedInAccount.linkedin_id.like('urn:li:person:%')
    ).first()
    
    if not personal_account:
        return jsonify({'error': 'Please connect your personal account first'}), 400

    if not account:
        account = LinkedInAccount(
            user_id=current_user.id,
            linkedin_id=org_id,
            name=name,
            account_type='ORGANIZATION',
            linkedin_token=personal_account.linkedin_token # Share token
        )
        db.session.add(account)
    else:
        account.name = name
        account.linkedin_token = personal_account.linkedin_token
        
    db.session.commit()
    session['active_account_id'] = account.id
    
    return jsonify({'status': 'success', 'account_id': account.id})


@auth_bp.route("/switch/<int:account_id>", methods=["POST"])
@login_required
def switch_account(account_id):
    account = LinkedInAccount.query.filter_by(
        id=account_id, user_id=current_user.id
    ).first()
    if not account:
        return jsonify({"error": "Account not found"}), 404
    session["active_account_id"] = account.id
    return jsonify({"status": "success", "active_account_id": account.id})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.pop("active_account_id", None)
    return jsonify({"status": "logged out"})


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    active_id = session.get("active_account_id")
    account   = None

    if active_id:
        account = db.session.get(LinkedInAccount, active_id)   # ✅ fixed

    if not account:
        account = LinkedInAccount.query.filter_by(user_id=current_user.id).first()
        if account:
            session["active_account_id"] = account.id

    return jsonify(
        {
            "id":    current_user.id,
            "email": current_user.email,
            "active_account": (
                {
                    "id":                  account.id,
                    "name":                account.name,
                    "profile_picture_url": account.profile_picture_url,
                    "linkedin_id":         account.linkedin_id,
                    "account_type":        account.account_type,
                }
                if account
                else None
            ),
        }
    )