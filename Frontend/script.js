// Advanced JavaScript for Veestributes Frontend

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Initialize Application
function initializeApp() {
    setupNavigation();
    setupAnimations();
    setupFormValidation();
    setupAPIIntegration();
    setupDarkMode();
}

// Navigation Setup
function setupNavigation() {
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            hamburger.classList.toggle('active');
        });
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Animation Setup
function setupAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.feature-card, .pricing-card').forEach(card => {
        observer.observe(card);
    });
}

// Form Validation Setup
function setupFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
        form.addEventListener('input', handleInputValidation);
    });
}

function handleFormSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    if (validateForm(form)) {
        submitForm(formData, form);
    }
}

function handleInputValidation(e) {
    const input = e.target;
    const errorElement = input.parentElement.querySelector('.error-message');

    if (input.hasAttribute('required') && !input.value.trim()) {
        showError(input, 'This field is required');
    } else if (input.type === 'email' && !isValidEmail(input.value)) {
        showError(input, 'Please enter a valid email address');
    } else if (input.type === 'password' && input.value.length < 8) {
        showError(input, 'Password must be at least 8 characters long');
    } else {
        hideError(input);
    }
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showError(field, 'This field is required');
            isValid = false;
        }
    });

    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (!isValidEmail(field.value)) {
            showError(field, 'Please enter a valid email address');
            isValid = false;
        }
    });

    return isValid;
}

function showError(input, message) {
    let errorElement = input.parentElement.querySelector('.error-message');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        input.parentElement.appendChild(errorElement);
    }
    errorElement.textContent = message;
    input.classList.add('error');
}

function hideError(input) {
    const errorElement = input.parentElement.querySelector('.error-message');
    if (errorElement) {
        errorElement.remove();
    }
    input.classList.remove('error');
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// API Integration Setup
function setupAPIIntegration() {
    // Placeholder for API calls
    window.VeestributesAPI = {
        login: (credentials) => apiCall('/api/auth/login', 'POST', credentials),
        signup: (userData) => apiCall('/api/auth/signup', 'POST', userData),
        uploadTrack: (formData) => apiCall('/api/upload', 'POST', formData),
        getReleases: () => apiCall('/api/releases', 'GET'),
        getAnalytics: () => apiCall('/api/analytics', 'GET')
    };
}

async function apiCall(endpoint, method, data = null) {
    const config = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    // Add authentication token if available
    const token = localStorage.getItem('authToken');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }

    if (data && method !== 'GET') {
        if (data instanceof FormData) {
            // For file uploads, don't set Content-Type (let browser set it with boundary)
            delete config.headers['Content-Type'];
            config.body = data;
        } else {
            config.body = JSON.stringify(data);
        }
    }

    try {
        const response = await fetch(`http://localhost:5000${endpoint}`, config);

        // Handle different response types
        const contentType = response.headers.get('content-type');
        let result;

        if (contentType && contentType.includes('application/json')) {
            result = await response.json();
        } else {
            result = await response.text();
        }

        if (!response.ok) {
            throw new Error(result.message || result.error || 'API call failed');
        }

        return result;
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// Dark Mode Setup
function setupDarkMode() {
    const toggleButton = document.createElement('button');
    toggleButton.className = 'dark-mode-toggle';
    toggleButton.innerHTML = '🌙';
    toggleButton.title = 'Toggle Dark Mode';
    document.body.appendChild(toggleButton);

    toggleButton.addEventListener('click', toggleDarkMode);

    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        toggleButton.innerHTML = '☀️';
    }
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');

    const toggleButton = document.querySelector('.dark-mode-toggle');
    toggleButton.innerHTML = isDark ? '☀️' : '🌙';
}

// Notification System
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// File Upload Handling (for upload page)
function setupFileUpload() {
    const fileInput = document.getElementById('track-file');
    const progressBar = document.getElementById('upload-progress');
    const progressText = document.getElementById('progress-text');

    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            if (validateAudioFile(file)) {
                displayFileInfo(file);
            } else {
                showNotification('Please select a valid audio file (MP3, WAV, FLAC)', 'error');
                fileInput.value = '';
            }
        }
    }

    function validateAudioFile(file) {
        const allowedTypes = ['audio/mpeg', 'audio/wav', 'audio/flac'];
        return allowedTypes.includes(file.type) || file.name.match(/\.(mp3|wav|flac)$/i);
    }

    function displayFileInfo(file) {
        const fileInfo = document.getElementById('file-info');
        if (fileInfo) {
            fileInfo.innerHTML = `
                <p><strong>File:</strong> ${file.name}</p>
                <p><strong>Size:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <p><strong>Type:</strong> ${file.type || 'Unknown'}</p>
            `;
        }
    }
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Export for use in other scripts
window.VeestributesUtils = {
    debounce,
    throttle,
    showNotification,
    setupFileUpload
};
