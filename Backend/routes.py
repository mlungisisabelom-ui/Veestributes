"""
API Routes for Veestributes
This file contains all the API endpoints for the music distribution platform.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Release, File, Platform, DistributionLog, Payment, RoyaltyPayment
from datetime import datetime, timedelta
import os
import uuid
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

# Decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# User Management Routes
@api_bp.route('/users/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user profile"""
    return jsonify(current_user.to_dict())

@api_bp.route('/users/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        user = User.query.get(current_user.id)

        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            # Check if email is already taken
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({'error': 'Email already in use'}), 400
            user.email = data['email']

        db.session.commit()
        return jsonify({'success': True, 'user': user.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500

# Release Management Routes
@api_bp.route('/releases', methods=['GET'])
@login_required
def get_user_releases():
    """Get all releases for current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')

        query = Release.query.filter_by(user_id=current_user.id)

        if status_filter:
            query = query.filter_by(status=status_filter)

        releases = query.order_by(Release.created_at.desc()).paginate(page=page, per_page=per_page)

        return jsonify({
            'releases': [release.to_dict() for release in releases.items],
            'total': releases.total,
            'pages': releases.pages,
            'current_page': releases.page
        })

    except Exception as e:
        logger.error(f"Error fetching releases: {str(e)}")
        return jsonify({'error': 'Failed to fetch releases'}), 500

@api_bp.route('/releases/<int:release_id>', methods=['GET'])
@login_required
def get_release_details(release_id):
    """Get detailed information about a specific release"""
    release = Release.query.filter_by(id=release_id, user_id=current_user.id).first()
    if not release:
        return jsonify({'error': 'Release not found'}), 404

    return jsonify(release.to_dict())

@api_bp.route('/releases/<int:release_id>', methods=['PUT'])
@login_required
def update_release(release_id):
    """Update release information"""
    release = Release.query.filter_by(id=release_id, user_id=current_user.id).first()
    if not release:
        return jsonify({'error': 'Release not found'}), 404

    try:
        data = request.get_json()

        # Update allowed fields
        allowed_fields = ['title', 'artist', 'album', 'genre', 'description', 'tags', 'release_date']
        for field in allowed_fields:
            if field in data:
                if field == 'release_date':
                    setattr(release, field, datetime.fromisoformat(data[field]).date())
                else:
                    setattr(release, field, data[field])

        db.session.commit()
        return jsonify({'success': True, 'release': release.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Release update error: {str(e)}")
        return jsonify({'error': 'Failed to update release'}), 500

@api_bp.route('/releases/<int:release_id>', methods=['DELETE'])
@login_required
def delete_release(release_id):
    """Delete a release"""
    release = Release.query.filter_by(id=release_id, user_id=current_user.id).first()
    if not release:
        return jsonify({'error': 'Release not found'}), 404

    try:
        # Delete associated files from filesystem
        for file in release.files:
            if os.path.exists(file.file_path):
                os.remove(file.file_path)

        db.session.delete(release)
        db.session.commit()

        logger.info(f"Release {release_id} deleted by user {current_user.email}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Release deletion error: {str(e)}")
        return jsonify({'error': 'Failed to delete release'}), 500

# File Management Routes
@api_bp.route('/releases/<int:release_id>/files', methods=['GET'])
@login_required
def get_release_files(release_id):
    """Get all files for a release"""
    release = Release.query.filter_by(id=release_id, user_id=current_user.id).first()
    if not release:
        return jsonify({'error': 'Release not found'}), 404

    return jsonify([file.to_dict() for file in release.files])

@api_bp.route('/files/<int:file_id>/download', methods=['GET'])
@login_required
def download_file(file_id):
    """Download a file"""
    file = File.query.join(Release).filter(
        File.id == file_id,
        Release.user_id == current_user.id
    ).first()

    if not file:
        return jsonify({'error': 'File not found'}), 404

    if not os.path.exists(file.file_path):
        return jsonify({'error': 'File not found on server'}), 404

    from flask import send_file
    return send_file(file.file_path, as_attachment=True, download_name=file.original_filename or file.filename)

# Upload Routes
@api_bp.route('/upload/audio', methods=['POST'])
@login_required
def upload_audio():
    """Upload audio file for a release"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    release_id = request.form.get('release_id', type=int)

    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    allowed_extensions = {'mp3', 'wav', 'flac', 'aac', 'ogg'}
    if not file.filename.lower().endswith(tuple('.' + ext for ext in allowed_extensions)):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        # Generate unique filename
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'audio', filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save file
        file.save(file_path)

        # Create file record
        file_record = File(
            release_id=release_id,
            filename=filename,
            original_filename=file.filename,
            file_type='audio',
            file_size=os.path.getsize(file_path),
            file_path=file_path,
            mime_type=file.mimetype,
            processing_status='completed'  # Mark as completed for now
        )

        if release_id:
            db.session.add(file_record)
            db.session.commit()

        return jsonify({
            'success': True,
            'file': file_record.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Audio upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

@api_bp.route('/upload/artwork', methods=['POST'])
@login_required
def upload_artwork():
    """Upload artwork for a release"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    release_id = request.form.get('release_id', type=int)

    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
    if not file.filename.lower().endswith(tuple('.' + ext for ext in allowed_extensions)):
        return jsonify({'error': 'Invalid file type. Use JPG, PNG, or GIF'}), 400

    # Validate file size (10MB max)
    if file.content_length and file.content_length > 10 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum size is 10MB'}), 400

    try:
        # Generate unique filename
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'artwork', filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save file
        file.save(file_path)

        # Create file record
        file_record = File(
            release_id=release_id,
            filename=filename,
            original_filename=file.filename,
            file_type='artwork',
            file_size=os.path.getsize(file_path),
            file_path=file_path,
            mime_type=file.mimetype,
            processing_status='completed'
        )

        if release_id:
            db.session.add(file_record)
            db.session.commit()

        return jsonify({
            'success': True,
            'file': file_record.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Artwork upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

# Analytics Routes
@api_bp.route('/analytics/overview', methods=['GET'])
@login_required
def get_analytics_overview():
    """Get analytics overview for current user"""
    try:
        # Get date range
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)

        releases = Release.query.filter_by(user_id=current_user.id).all()

        # Calculate metrics
        total_releases = len(releases)
        total_streams = sum(r.streams for r in releases)
        total_earnings = sum(float(r.earnings) for r in releases)

        # Recent releases
        recent_releases = Release.query.filter_by(user_id=current_user.id)\
            .filter(Release.created_at >= start_date)\
            .order_by(Release.created_at.desc())\
            .limit(5)\
            .all()

        # Top performing releases
        top_releases = sorted(releases, key=lambda r: r.streams, reverse=True)[:5]

        return jsonify({
            'total_releases': total_releases,
            'total_streams': total_streams,
            'total_earnings': total_earnings,
            'recent_releases': [r.to_dict() for r in recent_releases],
            'top_releases': [r.to_dict() for r in top_releases]
        })

    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500

@api_bp.route('/analytics/streams', methods=['GET'])
@login_required
def get_streams_analytics():
    """Get streams analytics data"""
    try:
        days = request.args.get('days', 30, type=int)
        release_id = request.args.get('release_id', type=int)

        # This would typically query actual streaming data
        # For now, return mock data
        labels = []
        data = []

        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days-i-1)
            labels.append(date.strftime('%Y-%m-%d'))
            # Mock data - in real app, this would come from analytics service
            data.append(max(0, int(1000 + (i * 50) + (i % 7) * 200)))

        return jsonify({
            'labels': labels,
            'data': data
        })

    except Exception as e:
        logger.error(f"Streams analytics error: {str(e)}")
        return jsonify({'error': 'Failed to fetch streams data'}), 500

# Distribution Routes
@api_bp.route('/releases/<int:release_id>/distribute', methods=['POST'])
@login_required
def distribute_release(release_id):
    """Trigger distribution for a release"""
    release = Release.query.filter_by(id=release_id, user_id=current_user.id).first()
    if not release:
        return jsonify({'error': 'Release not found'}), 404

    if release.status != 'draft':
        return jsonify({'error': 'Release is not ready for distribution'}), 400

    try:
        # Update release status
        release.status = 'processing'
        db.session.commit()

        # TODO: Trigger actual distribution process
        # This would typically queue a background job

        logger.info(f"Distribution triggered for release {release_id}")
        return jsonify({
            'success': True,
            'message': 'Distribution process started'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Distribution trigger error: {str(e)}")
        return jsonify({'error': 'Failed to start distribution'}), 500

@api_bp.route('/releases/<int:release_id>/distribution-status', methods=['GET'])
@login_required
def get_distribution_status(release_id):
    """Get distribution status for a release"""
    release = Release.query.filter_by(id=release_id, user_id=current_user.id).first()
    if not release:
        return jsonify({'error': 'Release not found'}), 404

    logs = DistributionLog.query.filter_by(release_id=release_id)\
        .order_by(DistributionLog.created_at.desc())\
        .all()

    return jsonify({
        'release_status': release.status,
        'distribution_logs': [log.to_dict() for log in logs]
    })

# Payment Routes
@api_bp.route('/payments/history', methods=['GET'])
@login_required
def get_payment_history():
    """Get payment history for current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        payments = Payment.query.filter_by(user_id=current_user.id)\
            .order_by(Payment.created_at.desc())\
            .paginate(page=page, per_page=per_page)

        return jsonify({
            'payments': [payment.to_dict() for payment in payments.items],
            'total': payments.total,
            'pages': payments.pages,
            'current_page': payments.page
        })

    except Exception as e:
        logger.error(f"Payment history error: {str(e)}")
        return jsonify({'error': 'Failed to fetch payment history'}), 500

@api_bp.route('/royalties', methods=['GET'])
@login_required
def get_royalties():
    """Get royalty information for current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        royalties = RoyaltyPayment.query.filter_by(user_id=current_user.id)\
            .order_by(RoyaltyPayment.period_end.desc())\
            .paginate(page=page, per_page=per_page)

        return jsonify({
            'royalties': [royalty.to_dict() for royalty in royalties.items],
            'total': royalties.total,
            'pages': royalties.pages,
            'current_page': royalties.page
        })

    except Exception as e:
        logger.error(f"Royalties error: {str(e)}")
        return jsonify({'error': 'Failed to fetch royalties'}), 500

# Admin Routes
@api_bp.route('/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Get admin statistics"""
    try:
        total_users = User.query.count()
        total_releases = Release.query.count()
        total_streams = db.session.query(db.func.sum(Release.streams)).scalar() or 0
        total_earnings = db.session.query(db.func.sum(Release.earnings)).scalar() or 0

        # Recent activity
        recent_releases = Release.query.order_by(Release.created_at.desc()).limit(10).all()
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

        return jsonify({
            'total_users': total_users,
            'total_releases': total_releases,
            'total_streams': total_streams,
            'total_earnings': float(total_earnings),
            'recent_releases': [r.to_dict() for r in recent_releases],
            'recent_users': [u.to_dict() for u in recent_users]
        })

    except Exception as e:
        logger.error(f"Admin stats error: {str(e)}")
        return jsonify({'error': 'Failed to fetch admin stats'}), 500

@api_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user (admin only)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        data = request.get_json()

        if 'is_admin' in data:
            user.is_admin = data['is_admin']

        db.session.commit()
        return jsonify({'success': True, 'user': user.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"User update error: {str(e)}")
        return jsonify({'error': 'Failed to update user'}), 500

# Search Routes
@api_bp.route('/search/releases', methods=['GET'])
@login_required
def search_releases():
    """Search user's releases"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'releases': []})

    try:
        releases = Release.query.filter_by(user_id=current_user.id)\
            .filter(
                db.or_(
                    Release.title.ilike(f'%{query}%'),
                    Release.artist.ilike(f'%{query}%'),
                    Release.album.ilike(f'%{query}%')
                )
            )\
            .order_by(Release.created_at.desc())\
            .limit(20)\
            .all()

        return jsonify({
            'releases': [r.to_dict() for r in releases]
        })

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

# Health Check
@api_bp.route('/health', methods=['GET'])
def health():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })
