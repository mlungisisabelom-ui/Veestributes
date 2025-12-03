"""
Background Tasks Module
Handles asynchronous tasks using Celery for file processing, distribution, and notifications.
"""

import os
import logging
from celery import Celery
from flask import current_app
from .metadata_processor import metadata_processor
from .models import db, Release, File, Platform
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Initialize Celery
celery = Celery(__name__)

def make_celery(app):
    """Create Celery instance with Flask app context."""
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        timezone='UTC',
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        enable_utc=True,
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

@celery.task(bind=True)
def process_audio_file(self, file_id, file_path):
    """
    Process uploaded audio file asynchronously.

    Args:
        file_id (int): File ID in database
        file_path (str): Path to uploaded file
    """
    try:
        self.update_state(state='PROGRESS', meta={'message': 'Extracting metadata...'})

        # Extract metadata
        metadata = metadata_processor.extract_metadata(file_path)

        # Validate file
        validation = metadata_processor.validate_audio_file(file_path)

        if not validation['is_valid']:
            raise ValueError(f"File validation failed: {validation['errors']}")

        # Update file record in database
        file_record = File.query.get(file_id)
        if file_record:
            file_record.title = metadata.get('title')
            file_record.artist = metadata.get('artist')
            file_record.album = metadata.get('album')
            file_record.duration = metadata.get('duration')
            file_record.bitrate = metadata.get('bitrate')
            file_record.sample_rate = metadata.get('sample_rate')
            file_record.status = 'processed'
            file_record.metadata = metadata

            # Generate waveform data
            waveform = metadata_processor.generate_waveform_data(file_path)
            file_record.waveform_data = waveform

            db.session.commit()

        self.update_state(state='SUCCESS', meta={'message': 'File processed successfully'})

    except Exception as e:
        logger.error(f"File processing failed for {file_path}: {str(e)}")
        self.update_state(state='FAILURE', meta={'message': str(e)})
        raise

@celery.task(bind=True)
def distribute_release(self, release_id):
    """
    Distribute release to various platforms asynchronously.

    Args:
        release_id (int): Release ID in database
    """
    try:
        self.update_state(state='PROGRESS', meta={'message': 'Preparing distribution...'})

        release = Release.query.get(release_id)
        if not release:
            raise ValueError(f"Release {release_id} not found")

        # Get all platforms
        platforms = Platform.query.all()

        distribution_results = {}

        for platform in platforms:
            try:
                self.update_state(state='PROGRESS',
                                meta={'message': f'Distributing to {platform.name}...'})

                # Simulate distribution to platform
                # In a real implementation, this would integrate with platform APIs
                result = distribute_to_platform(release, platform)

                distribution_results[platform.name] = {
                    'status': 'success',
                    'url': result.get('url'),
                    'submission_id': result.get('submission_id')
                }

            except Exception as e:
                logger.error(f"Distribution to {platform.name} failed: {str(e)}")
                distribution_results[platform.name] = {
                    'status': 'failed',
                    'error': str(e)
                }

        # Update release with distribution results
        release.distribution_status = distribution_results
        release.status = 'distributed'
        db.session.commit()

        # Send notification email
        send_distribution_notification.delay(release.user.email, release.title, distribution_results)

        self.update_state(state='SUCCESS', meta={'message': 'Distribution completed'})

    except Exception as e:
        logger.error(f"Release distribution failed for {release_id}: {str(e)}")
        self.update_state(state='FAILURE', meta={'message': str(e)})
        raise

def distribute_to_platform(release, platform):
    """
    Distribute release to a specific platform.

    Args:
        release: Release object
        platform: Platform object

    Returns:
        dict: Distribution result
    """
    # Placeholder implementation
    # In a real application, this would integrate with platform APIs like:
    # - Spotify for Developers API
    # - Apple Music API
    # - DistroKid's distribution network
    # - etc.

    if platform.name.lower() == 'spotify':
        # Simulate Spotify distribution
        return {
            'url': f'https://open.spotify.com/album/{release.id}',
            'submission_id': f'spotify_{release.id}'
        }
    elif platform.name.lower() == 'apple music':
        return {
            'url': f'https://music.apple.com/album/{release.id}',
            'submission_id': f'apple_{release.id}'
        }
    elif platform.name.lower() == 'youtube music':
        return {
            'url': f'https://music.youtube.com/playlist?list={release.id}',
            'submission_id': f'youtube_{release.id}'
        }
    else:
        # Generic distribution
        return {
            'url': f'https://{platform.name.lower().replace(" ", "")}.com/release/{release.id}',
            'submission_id': f'{platform.name.lower()}_{release.id}'
        }

@celery.task(bind=True)
def send_distribution_notification(self, user_email, release_title, results):
    """
    Send email notification about distribution completion.

    Args:
        user_email (str): User's email address
        release_title (str): Release title
        results (dict): Distribution results
    """
    try:
        app = current_app._get_current_object()

        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = user_email
        msg['Subject'] = f'Veestributes - {release_title} Distribution Complete'

        # Create email body
        body = f"""
        <html>
        <body>
            <h2>Your release "{release_title}" has been distributed!</h2>
            <p>Here's the distribution status:</p>
            <ul>
        """

        for platform, result in results.items():
            if result['status'] == 'success':
                body += f'<li><strong>{platform}:</strong> Successfully distributed - <a href="{result["url"]}">View</a></li>'
            else:
                body += f'<li><strong>{platform}:</strong> Failed - {result.get("error", "Unknown error")}</li>'

        body += """
            </ul>
            <p>You can view detailed analytics in your <a href="http://localhost:5000/dashboard">dashboard</a>.</p>
            <p>Thank you for using Veestributes!</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        text = msg.as_string()
        server.sendmail(app.config['MAIL_DEFAULT_SENDER'], user_email, text)
        server.quit()

        logger.info(f"Distribution notification sent to {user_email}")

    except Exception as e:
        logger.error(f"Failed to send notification email to {user_email}: {str(e)}")
        raise

@celery.task(bind=True)
def generate_analytics_report(self, user_id, period='month'):
    """
    Generate analytics report for user.

    Args:
        user_id (int): User ID
        period (str): Report period ('week', 'month', 'year')
    """
    try:
        # Placeholder for analytics generation
        # In a real implementation, this would aggregate streaming data,
        # calculate revenue, generate charts, etc.

        report_data = {
            'total_streams': 0,
            'total_revenue': 0.0,
            'top_tracks': [],
            'platform_breakdown': {},
            'period': period
        }

        # Mock data for demonstration
        report_data['total_streams'] = 125000
        report_data['total_revenue'] = 1250.50
        report_data['top_tracks'] = ['Track 1', 'Track 2', 'Track 3']
        report_data['platform_breakdown'] = {
            'Spotify': 45000,
            'Apple Music': 35000,
            'YouTube Music': 25000,
            'Other': 20000
        }

        # Store report in database or send via email
        # For now, just log it
        logger.info(f"Analytics report generated for user {user_id}: {report_data}")

        self.update_state(state='SUCCESS', meta={'report': report_data})

    except Exception as e:
        logger.error(f"Analytics report generation failed for user {user_id}: {str(e)}")
        self.update_state(state='FAILURE', meta={'message': str(e)})
        raise

@celery.task(bind=True)
def cleanup_temp_files(self):
    """
    Clean up temporary files and old uploads.

    This task runs periodically to free up disk space.
    """
    try:
        # Define cleanup directories and age thresholds
        temp_dir = os.path.join(current_app.root_path, 'temp')
        uploads_dir = current_app.config['UPLOAD_FOLDER']

        # Clean temp files older than 1 hour
        cleanup_old_files(temp_dir, hours=1)

        # Clean unprocessed uploads older than 24 hours
        cleanup_old_files(uploads_dir, hours=24, pattern='*.tmp')

        logger.info("Temporary file cleanup completed")

    except Exception as e:
        logger.error(f"Temp file cleanup failed: {str(e)}")
        raise

def cleanup_old_files(directory, hours=24, pattern=None):
    """
    Remove files older than specified hours.

    Args:
        directory (str): Directory to clean
        hours (int): Age threshold in hours
        pattern (str): File pattern to match (optional)
    """
    import glob
    from datetime import datetime, timedelta

    if not os.path.exists(directory):
        return

    cutoff_time = datetime.now() - timedelta(hours=hours)

    if pattern:
        files = glob.glob(os.path.join(directory, pattern))
    else:
        files = glob.glob(os.path.join(directory, '*'))

    for file_path in files:
        if os.path.isfile(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed old file: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove {file_path}: {str(e)}")

# Periodic task schedule (would be configured in celery beat)
celery.conf.beat_schedule = {
    'cleanup-temp-files': {
        'task': 'tasks.cleanup_temp_files',
        'schedule': 3600.0,  # Every hour
    },
    'generate-monthly-reports': {
        'task': 'tasks.generate_analytics_report',
        'schedule': 2592000.0,  # Every 30 days
        'args': (None, 'month')  # user_id would be passed dynamically
    },
}
