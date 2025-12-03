from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    releases = db.relationship('Release', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Release(db.Model):
    __tablename__ = 'releases'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Basic information
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    album = db.Column(db.String(200))
    genre = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.String(500))  # Comma-separated tags

    # Release details
    release_date = db.Column(db.Date)
    platforms = db.Column(db.String(500))  # Comma-separated platform names
    status = db.Column(db.String(20), default='draft')  # draft, processing, distributed, failed

    # Analytics
    streams = db.Column(db.Integer, default=0)
    earnings = db.Column(db.Numeric(10, 2), default=0.00)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    distributed_at = db.Column(db.DateTime)

    # Relationships
    files = db.relationship('File', backref='release', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Release {self.title} by {self.artist}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre,
            'description': self.description,
            'tags': self.tags,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'platforms': self.platforms,
            'status': self.status,
            'streams': self.streams,
            'earnings': float(self.earnings),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'distributed_at': self.distributed_at.isoformat() if self.distributed_at else None
        }

class File(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    release_id = db.Column(db.Integer, db.ForeignKey('releases.id'), nullable=False, index=True)

    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    file_type = db.Column(db.String(20), nullable=False)  # audio, artwork, etc.
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100))

    # File paths
    file_path = db.Column(db.String(500), nullable=False)  # Full path to file
    url_path = db.Column(db.String(500))  # URL path for serving

    # Metadata
    duration = db.Column(db.Integer)  # For audio files, in seconds
    bitrate = db.Column(db.Integer)  # For audio files
    sample_rate = db.Column(db.Integer)  # For audio files
    channels = db.Column(db.Integer)  # For audio files (mono/stereo)

    # Artwork metadata
    width = db.Column(db.Integer)  # For image files
    height = db.Column(db.Integer)  # For image files

    # Processing status
    processing_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    processing_error = db.Column(db.Text)

    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<File {self.filename} ({self.file_type})>'

    def to_dict(self):
        return {
            'id': self.id,
            'release_id': self.release_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'file_path': self.file_path,
            'url_path': self.url_path,
            'duration': self.duration,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'width': self.width,
            'height': self.height,
            'processing_status': self.processing_status,
            'processing_error': self.processing_error,
            'uploaded_at': self.uploaded_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

class Platform(db.Model):
    __tablename__ = 'platforms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    api_endpoint = db.Column(db.String(500))
    api_key = db.Column(db.String(500))  # Encrypted in production
    is_active = db.Column(db.Boolean, default=True)

    # Distribution settings
    max_file_size = db.Column(db.Integer)  # In bytes
    supported_formats = db.Column(db.String(500))  # Comma-separated
    distribution_fee = db.Column(db.Numeric(8, 2), default=0.00)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Platform {self.name}>'

class DistributionLog(db.Model):
    __tablename__ = 'distribution_logs'

    id = db.Column(db.Integer, primary_key=True)
    release_id = db.Column(db.Integer, db.ForeignKey('releases.id'), nullable=False, index=True)
    platform_id = db.Column(db.Integer, db.ForeignKey('platforms.id'), nullable=False)

    # Distribution details
    status = db.Column(db.String(20), default='pending')  # pending, processing, distributed, failed
    platform_release_id = db.Column(db.String(100))  # ID from the platform
    platform_url = db.Column(db.String(500))  # URL to the distributed content

    # Error handling
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    distributed_at = db.Column(db.DateTime)

    # Relationships
    release = db.relationship('Release', backref='distribution_logs')
    platform = db.relationship('Platform', backref='distribution_logs')

    def __repr__(self):
        return f'<DistributionLog {self.release_id} -> {self.platform.name}: {self.status}>'

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    release_id = db.Column(db.Integer, db.ForeignKey('releases.id'), index=True)

    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    payment_method = db.Column(db.String(50))  # stripe, paypal, etc.
    transaction_id = db.Column(db.String(100), unique=True)

    # Status
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded

    # Description
    description = db.Column(db.String(255))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', backref='payments')
    release = db.relationship('Release', backref='payments')

    def __repr__(self):
        return f'<Payment {self.transaction_id}: {self.amount} {self.currency}>'

class RoyaltyPayment(db.Model):
    __tablename__ = 'royalty_payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    release_id = db.Column(db.Integer, db.ForeignKey('releases.id'), nullable=False, index=True)

    # Royalty details
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    streams = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')

    # Platform breakdown (JSON stored as text)
    platform_breakdown = db.Column(db.Text)  # JSON string with platform-specific data

    # Status
    status = db.Column(db.String(20), default='pending')  # pending, paid, failed

    # Payment reference
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', backref='royalty_payments')
    release = db.relationship('Release', backref='royalty_payments')
    payment = db.relationship('Payment', backref='royalty_payments')

    def __repr__(self):
        return f'<RoyaltyPayment {self.user.name}: {self.amount} for {self.period_start} - {self.period_end}>'

# Indexes for performance
db.Index('idx_release_user_status', Release.user_id, Release.status)
db.Index('idx_file_release_type', File.release_id, File.file_type)
db.Index('idx_distribution_log_release_platform', DistributionLog.release_id, DistributionLog.platform_id)
db.Index('idx_payment_user_status', Payment.user_id, Payment.status)
db.Index('idx_royalty_user_period', RoyaltyPayment.user_id, RoyaltyPayment.period_start, RoyaltyPayment.period_end)
