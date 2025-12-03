"""
Music Metadata Processing Module
Handles extraction and processing of audio file metadata using mutagen.
"""

import os
import logging
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.wavpack import WavPack
from mutagen.oggvorbis import OggVorbis
from mutagen.aac import AAC
from PIL import Image
import io

logger = logging.getLogger(__name__)

class MetadataProcessor:
    """Processes audio file metadata and extracts relevant information."""

    SUPPORTED_FORMATS = {
        '.mp3': MP3,
        '.flac': FLAC,
        '.wv': WavPack,
        '.ogg': OggVorbis,
        '.aac': AAC,
        '.m4a': AAC
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_metadata(self, file_path):
        """
        Extract metadata from audio file.

        Args:
            file_path (str): Path to the audio file

        Returns:
            dict: Extracted metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported audio format: {file_ext}")

        try:
            # Load audio file
            audio = self.SUPPORTED_FORMATS[file_ext](file_path)

            metadata = {
                'duration': int(audio.info.length),
                'bitrate': getattr(audio.info, 'bitrate', None),
                'sample_rate': audio.info.sample_rate,
                'channels': audio.info.channels,
                'title': None,
                'artist': None,
                'album': None,
                'genre': None,
                'year': None,
                'track_number': None,
                'album_artist': None,
                'composer': None,
                'lyrics': None,
                'artwork': None
            }

            # Extract tags based on format
            if hasattr(audio, 'tags') and audio.tags:
                tags = audio.tags

                # Handle different tag formats
                if hasattr(tags, 'getall'):  # ID3 tags
                    metadata.update(self._extract_id3_tags(tags))
                elif hasattr(tags, 'items'):  # Vorbis comments
                    metadata.update(self._extract_vorbis_tags(tags))
                else:
                    # Generic tag extraction
                    for key, value in tags.items():
                        if isinstance(value, list) and len(value) > 0:
                            value = value[0]
                        metadata[key.lower()] = str(value)

            # Extract embedded artwork
            metadata['artwork'] = self._extract_artwork(audio)

            return metadata

        except Exception as e:
            self.logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
            raise

    def _extract_id3_tags(self, tags):
        """Extract ID3v2 tags."""
        metadata = {}

        # Common ID3 mappings
        tag_mappings = {
            'TIT2': 'title',
            'TPE1': 'artist',
            'TALB': 'album',
            'TCON': 'genre',
            'TYER': 'year',
            'TDRC': 'year',  # ID3v2.4
            'TRCK': 'track_number',
            'TPE2': 'album_artist',
            'TCOM': 'composer',
            'USLT': 'lyrics'
        }

        for tag_id, field in tag_mappings.items():
            if tag_id in tags:
                value = tags[tag_id]
                if hasattr(value, 'text'):
                    metadata[field] = str(value.text[0]) if value.text else None
                else:
                    metadata[field] = str(value)

        return metadata

    def _extract_vorbis_tags(self, tags):
        """Extract Vorbis comment tags."""
        metadata = {}

        # Common Vorbis mappings
        tag_mappings = {
            'title': 'title',
            'artist': 'artist',
            'album': 'album',
            'genre': 'genre',
            'date': 'year',
            'year': 'year',
            'tracknumber': 'track_number',
            'albumartist': 'album_artist',
            'composer': 'composer',
            'lyrics': 'lyrics'
        }

        for vorbis_key, field in tag_mappings.items():
            if vorbis_key in tags:
                value = tags[vorbis_key]
                if isinstance(value, list):
                    metadata[field] = value[0] if value else None
                else:
                    metadata[field] = str(value)

        return metadata

    def _extract_artwork(self, audio):
        """Extract embedded artwork from audio file."""
        try:
            # Check for embedded artwork
            if hasattr(audio, 'tags') and audio.tags:
                # ID3v2 APIC frames
                if 'APIC:' in str(audio.tags):
                    for key in audio.tags.keys():
                        if key.startswith('APIC'):
                            apic = audio.tags[key]
                            return {
                                'data': apic.data,
                                'mime_type': apic.mime,
                                'description': apic.desc
                            }

                # FLAC pictures
                if hasattr(audio, 'pictures') and audio.pictures:
                    picture = audio.pictures[0]
                    return {
                        'data': picture.data,
                        'mime_type': picture.mime,
                        'description': picture.desc
                    }

            return None

        except Exception as e:
            self.logger.warning(f"Could not extract artwork: {str(e)}")
            return None

    def validate_audio_file(self, file_path):
        """
        Validate audio file and return basic information.

        Args:
            file_path (str): Path to audio file

        Returns:
            dict: Validation results
        """
        try:
            metadata = self.extract_metadata(file_path)

            # Basic validation rules
            validation = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }

            # Check duration (must be at least 30 seconds)
            if metadata['duration'] < 30:
                validation['errors'].append('Audio file must be at least 30 seconds long')

            # Check sample rate (should be at least 44.1kHz)
            if metadata['sample_rate'] < 44100:
                validation['warnings'].append('Sample rate is below 44.1kHz')

            # Check bitrate for compressed formats
            if metadata['bitrate'] and metadata['bitrate'] < 128000:
                validation['warnings'].append('Bitrate is below 128kbps')

            # Check file size (rough estimate: 30 seconds at 128kbps = ~480KB)
            file_size = os.path.getsize(file_path)
            if file_size < 480000:  # 480KB
                validation['warnings'].append('File size seems unusually small')

            if validation['errors']:
                validation['is_valid'] = False

            return validation

        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'Could not validate audio file: {str(e)}'],
                'warnings': []
            }

    def process_artwork(self, artwork_data, max_size=(1400, 1400)):
        """
        Process and validate artwork image.

        Args:
            artwork_data (bytes): Raw image data
            max_size (tuple): Maximum dimensions (width, height)

        Returns:
            dict: Processed artwork information
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(artwork_data))

            # Check dimensions
            width, height = image.size

            if width < 1400 or height < 1400:
                raise ValueError('Artwork must be at least 1400x1400 pixels')

            if width > max_size[0] or height > max_size[1]:
                # Resize image
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Convert to RGB if necessary
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')

            # Save processed image
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            processed_data = output.getvalue()

            return {
                'data': processed_data,
                'width': image.width,
                'height': image.height,
                'format': 'JPEG',
                'size': len(processed_data)
            }

        except Exception as e:
            raise ValueError(f'Could not process artwork: {str(e)}')

    def generate_waveform_data(self, file_path, samples=100):
        """
        Generate waveform visualization data from audio file.

        Args:
            file_path (str): Path to audio file
            samples (int): Number of samples to generate

        Returns:
            list: Waveform amplitude data
        """
        try:
            # This is a simplified implementation
            # In a real application, you'd use libraries like pydub or scipy
            # to extract actual audio samples

            # For now, return mock data
            import random
            waveform = []
            for i in range(samples):
                # Generate pseudo-random waveform based on file characteristics
                base_amplitude = 0.5
                variation = random.uniform(-0.3, 0.3)
                waveform.append(max(0, min(1, base_amplitude + variation)))

            return waveform

        except Exception as e:
            self.logger.error(f"Could not generate waveform for {file_path}: {str(e)}")
            return []

    def extract_lyrics(self, file_path):
        """
        Extract lyrics from audio file metadata.

        Args:
            file_path (str): Path to audio file

        Returns:
            str: Extracted lyrics or None
        """
        try:
            audio = MutagenFile(file_path)

            if hasattr(audio, 'tags') and audio.tags:
                # Check for lyrics in various formats
                lyrics_fields = ['USLT', 'lyrics', 'LYRICS', 'text']

                for field in lyrics_fields:
                    if field in audio.tags:
                        lyrics_data = audio.tags[field]
                        if hasattr(lyrics_data, 'text'):
                            return str(lyrics_data.text)
                        elif isinstance(lyrics_data, list):
                            return str(lyrics_data[0])
                        else:
                            return str(lyrics_data)

            return None

        except Exception as e:
            self.logger.warning(f"Could not extract lyrics from {file_path}: {str(e)}")
            return None

# Global processor instance
metadata_processor = MetadataProcessor()
