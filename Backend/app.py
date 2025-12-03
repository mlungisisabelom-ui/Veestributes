from flask import Flask, request, jsonify, session, render_template, send_from_directory, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timedelta
import logging
from functools import wraps
import secrets

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///veestributes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'artwork'), exist_ok=True)

# Initialize extensions
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models after db initialization
from models import User, Release, File

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return send_from_directory('../Frontend', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('../Frontend', filename)

# API Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email')).first()

        if user and bcrypt.check_password_hash(user.password_hash, data.get('password')):
            login_user(user)
            logger.info(f"User {user.email} logged in successfully")
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'is_admin': user.is_admin
                }
            })

        return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()

        # Check if user already exists
        existing_user = User.query.filter_by(email=data.get('email')).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400

        # Create new user
        hashed_password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
        user = User(
            email=data.get('email'),
            name=f"{data.get('firstname')} {data.get('lastname')}",
            password_hash=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        logger.info(f"New user {user.email} registered successfully")

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_admin': user.is_admin
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True})

@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'is_admin': current_user.is_admin,
        'created_at': current_user.created_at.isoformat()
    })

@app.route('/api/releases', methods=['GET'])
@login_required
def get_releases():
    try:
        releases = Release.query.filter_by(user_id=current_user.id).order_by(Release.created_at.desc()).all()
        return jsonify([{
            'id': release.id,
            'title': release.title,
            'artist': release.artist,
            'album': release.album,
            'genre': release.genre,
            'status': release.status,
            'streams': release.streams,
            'earnings': float(release.earnings),
            'created_at': release.created_at.isoformat(),
            'release_date': release.release_date.isoformat() if release.release_date else None
        } for release in releases])

    except Exception as e:
        logger.error(f"Error fetching releases: {str(e)}")
        return jsonify({'error': 'Failed to fetch releases'}), 500

@app.route('/api/releases/<int:release_id>', methods=['GET'])
@login_required
def get_release(release_id):
    release = Release.query.filter_by(id=release_id, user_id=current_user.id).first()
    if not release:
        return jsonify({'error': 'Release not found'}), 404

    return jsonify({
        'id': release.id,
        'title': release.title,
        'artist': release.artist,
        'album': release.album,
        'genre': release.genre,
        'description': release.description,
        'tags': release.tags,
        'status': release.status,
        'streams': release.streams,
        'earnings': float(release.earnings),
        'platforms': release.platforms,
        'created_at': release.created_at.isoformat(),
        'release_date': release.release_date.isoformat() if release.release_date else None,
        'files': [{
            'id': file.id,
            'filename': file.filename,
            'file_type': file.file_type,
            'file_size': file.file_size,
            'uploaded_at': file.uploaded_at.isoformat()
        } for file in release.files]
    })

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_release():
    try:
        # Get form data
        title = request.form.get('title')
        artist = request.form.get('artist')
        album = request.form.get('album')
        genre = request.form.get('genre')
        release_date = request.form.get('release_date')
        description = request.form.get('description')
        tags = request.form.get('tags')
        platforms = request.form.getlist('platforms')

        # Validate required fields
        if not all([title, artist, genre, release_date]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Handle file uploads
        audio_file = request.files.get('audio_file')
        artwork_file = request.files.get('artwork')

        if not audio_file:
            return jsonify({'error': 'Audio file is required'}), 400

        # Save audio file
        audio_filename = secure_filename(f"{uuid.uuid4()}_{audio_file.filename}")
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', audio_filename)
        audio_file.save(audio_path)

        # Save artwork file if provided
        artwork_filename = None
        if artwork_file:
            artwork_filename = secure_filename(f"{uuid.uuid4()}_{artwork_file.filename}")
            artwork_path = os.path.join(app.config['UPLOAD_FOLDER'], 'artwork', artwork_filename)
            artwork_file.save(artwork_path)

        # Create release record
        release = Release(
            user_id=current_user.id,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            description=description,
            tags=tags,
            platforms=','.join(platforms),
            release_date=datetime.fromisoformat(release_date),
            status='processing'
        )

        db.session.add(release)
        db.session.flush()  # Get release ID

        # Create file records
        audio_file_record = File(
            release_id=release.id,
            filename=audio_filename,
            file_type='audio',
            file_size=os.path.getsize(audio_path),
            file_path=audio_path
        )
        db.session.add(audio_file_record)

        if artwork_filename:
            artwork_file_record = File(
                release_id=release.id,
                filename=artwork_filename,
                file_type='artwork',
                file_size=os.path.getsize(artwork_path),
                file_path=artwork_path
            )
            db.session.add(artwork_file_record)

        db.session.commit()

        # TODO: Trigger background processing for distribution
        logger.info(f"Release {release.id} uploaded successfully by user {current_user.email}")

        return jsonify({
            'success': True,
            'release_id': release.id,
            'message': 'Release uploaded successfully. Processing will begin shortly.'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/analytics', methods=['GET'])
@login_required
def get_analytics():
    try:
        releases = Release.query.filter_by(user_id=current_user.id).all()

        total_releases = len(releases)
        total_streams = sum(release.streams for release in releases)
        total_earnings = sum(release.earnings for release in releases)

        # Mock monthly growth calculation
        monthly_growth = 12.5  # Placeholder

        # Mock chart data
        chart_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        chart_data = [1200, 1900, 3000, 5000, 2000, 3000]

        return jsonify({
            'totalReleases': total_releases,
            'totalStreams': total_streams,
            'totalEarnings': float(total_earnings),
            'monthlyGrowth': monthly_growth,
            'chartLabels': chart_labels,
            'chartData': chart_data,
            'recentActivity': [
                {'icon': '🎵', 'description': 'New release uploaded', 'time': '2 hours ago'},
                {'icon': '▶️', 'description': 'Track reached 1000 streams', 'time': '1 day ago'},
                {'icon': '💰', 'description': 'Royalties paid', 'time': '3 days ago'}
            ]
        })

    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500

# Admin routes
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat()
    } for user in users])

@app.route('/api/admin/releases', methods=['GET'])
@admin_required
def get_all_releases():
    releases = Release.query.order_by(Release.created_at.desc()).limit(100).all()
    return jsonify([{
        'id': release.id,
        'title': release.title,
        'artist': release.artist,
        'user_email': release.user.email,
        'status': release.status,
        'streams': release.streams,
        'created_at': release.created_at.isoformat()
    } for release in releases])

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large'}), 413

# Health check
@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")

    app.run(debug=True, host='0.0.0.0', port=5000)
