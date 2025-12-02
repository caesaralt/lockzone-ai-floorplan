"""
CRM Google Integration Routes Blueprint

Handles Google Calendar and Gmail integration:
- /api/crm/google/config - Configuration management
- /api/crm/google/auth-url - OAuth URL generation
- /api/crm/google/callback - OAuth callback
- /api/crm/google/disconnect - Disconnect account
- /api/crm/google/calendar/* - Calendar operations
- /api/crm/google/gmail/* - Gmail operations
"""

import os
import json
import logging
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

# Create blueprint
crm_google_bp = Blueprint('crm_google_bp', __name__)


def load_json_file(filepath, default=None):
    """Load JSON file with default fallback"""
    if default is None:
        default = {}
    try:
        if filepath and os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
    return default


def save_json_file(filepath, data):
    """Save data to JSON file"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False


def get_google_config_file():
    """Get the Google config file path"""
    return os.path.join(current_app.config.get('CRM_DATA_FOLDER', 'crm_data'), 'google_config.json')


def refresh_google_token():
    """Refresh Google access token if expired"""
    config_file = get_google_config_file()
    config = load_json_file(config_file, {})

    if not config.get('refresh_token'):
        return None

    # Check if token is expired
    if config.get('token_expiry') and datetime.now().timestamp() < config['token_expiry'] - 60:
        return config.get('access_token')

    # Refresh the token
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'refresh_token': config['refresh_token'],
        'grant_type': 'refresh_token'
    }

    response = requests.post(token_url, data=token_data)

    if response.status_code == 200:
        tokens = response.json()
        config['access_token'] = tokens.get('access_token')
        config['token_expiry'] = (datetime.now().timestamp() + tokens.get('expires_in', 3600))
        save_json_file(config_file, config)
        return config['access_token']

    return None


# ============================================================================
# GOOGLE CONFIG
# ============================================================================

@crm_google_bp.route('/api/crm/google/config', methods=['GET', 'POST'])
def handle_google_config():
    """Manage Google API configuration"""
    try:
        config_file = get_google_config_file()
        
        if request.method == 'GET':
            config = load_json_file(config_file, {
                'client_id': '',
                'client_secret': '',
                'redirect_uri': '',
                'access_token': '',
                'refresh_token': '',
                'token_expiry': '',
                'calendar_enabled': False,
                'gmail_enabled': False,
                'connected': False
            })
            # Don't expose tokens in GET
            safe_config = {
                'client_id': config.get('client_id', ''),
                'redirect_uri': config.get('redirect_uri', ''),
                'calendar_enabled': config.get('calendar_enabled', False),
                'gmail_enabled': config.get('gmail_enabled', False),
                'connected': bool(config.get('access_token'))
            }
            return jsonify({'success': True, 'config': safe_config})

        # POST - Save configuration
        data = request.get_json()
        config = load_json_file(config_file, {})

        config['client_id'] = data.get('client_id', config.get('client_id', ''))
        config['client_secret'] = data.get('client_secret', config.get('client_secret', ''))
        config['redirect_uri'] = data.get('redirect_uri', config.get('redirect_uri', ''))
        config['calendar_enabled'] = data.get('calendar_enabled', config.get('calendar_enabled', False))
        config['gmail_enabled'] = data.get('gmail_enabled', config.get('gmail_enabled', False))

        save_json_file(config_file, config)

        return jsonify({
            'success': True,
            'message': 'Google configuration saved'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_google_bp.route('/api/crm/google/auth-url', methods=['GET'])
def get_google_auth_url():
    """Generate Google OAuth2 authorization URL"""
    try:
        config_file = get_google_config_file()
        config = load_json_file(config_file, {})

        if not config.get('client_id'):
            return jsonify({'success': False, 'error': 'Google client ID not configured'}), 400

        scopes = []
        if config.get('calendar_enabled'):
            scopes.append('https://www.googleapis.com/auth/calendar')
        if config.get('gmail_enabled'):
            scopes.extend([
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly'
            ])

        if not scopes:
            return jsonify({'success': False, 'error': 'No Google services enabled'}), 400

        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={config['client_id']}&"
            f"redirect_uri={config.get('redirect_uri', '')}&"
            f"response_type=code&"
            f"scope={' '.join(scopes)}&"
            f"access_type=offline&"
            f"prompt=consent"
        )

        return jsonify({
            'success': True,
            'auth_url': auth_url
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_google_bp.route('/api/crm/google/callback', methods=['POST'])
def google_oauth_callback():
    """Handle Google OAuth2 callback and exchange code for tokens"""
    try:
        config_file = get_google_config_file()
        data = request.get_json()
        code = data.get('code')

        if not code:
            return jsonify({'success': False, 'error': 'Authorization code required'}), 400

        config = load_json_file(config_file, {})

        # Exchange code for tokens
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': config['redirect_uri']
        }

        response = requests.post(token_url, data=token_data)

        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Token exchange failed: {response.text}'
            }), 400

        tokens = response.json()

        config['access_token'] = tokens.get('access_token')
        config['refresh_token'] = tokens.get('refresh_token', config.get('refresh_token'))
        config['token_expiry'] = (datetime.now().timestamp() + tokens.get('expires_in', 3600))
        config['connected'] = True

        save_json_file(config_file, config)

        return jsonify({
            'success': True,
            'message': 'Google account connected successfully'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_google_bp.route('/api/crm/google/disconnect', methods=['POST'])
def disconnect_google():
    """Disconnect Google account"""
    try:
        config_file = get_google_config_file()
        config = load_json_file(config_file, {})
        config['access_token'] = ''
        config['refresh_token'] = ''
        config['token_expiry'] = ''
        config['connected'] = False
        save_json_file(config_file, config)

        return jsonify({
            'success': True,
            'message': 'Google account disconnected'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# GOOGLE CALENDAR
# ============================================================================

@crm_google_bp.route('/api/crm/google/calendar/events', methods=['GET', 'POST'])
def handle_google_calendar_events():
    """List or create Google Calendar events"""
    try:
        access_token = refresh_google_token()
        if not access_token:
            return jsonify({'success': False, 'error': 'Google account not connected'}), 401

        headers = {'Authorization': f'Bearer {access_token}'}

        if request.method == 'GET':
            # Get calendar events
            calendar_id = request.args.get('calendar_id', 'primary')
            time_min = request.args.get('time_min', datetime.now().isoformat() + 'Z')
            max_results = request.args.get('max_results', 50)

            url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events'
            params = {
                'timeMin': time_min,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                return jsonify({'success': False, 'error': 'Failed to fetch events'}), 400

            events = response.json().get('items', [])
            return jsonify({'success': True, 'events': events})

        else:  # POST - Create event
            data = request.get_json()
            calendar_id = data.get('calendar_id', 'primary')

            event = {
                'summary': data.get('title', ''),
                'description': data.get('description', ''),
                'start': {
                    'dateTime': data.get('start'),
                    'timeZone': data.get('timezone', 'UTC')
                },
                'end': {
                    'dateTime': data.get('end'),
                    'timeZone': data.get('timezone', 'UTC')
                }
            }

            if data.get('attendees'):
                event['attendees'] = [{'email': email} for email in data['attendees']]

            url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events'
            response = requests.post(url, headers={**headers, 'Content-Type': 'application/json'}, json=event)

            if response.status_code not in [200, 201]:
                return jsonify({'success': False, 'error': 'Failed to create event'}), 400

            return jsonify({'success': True, 'event': response.json()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_google_bp.route('/api/crm/google/calendar/events/<event_id>', methods=['PUT', 'DELETE'])
def handle_google_calendar_event(event_id):
    """Update or delete a Google Calendar event"""
    try:
        access_token = refresh_google_token()
        if not access_token:
            return jsonify({'success': False, 'error': 'Google account not connected'}), 401

        headers = {'Authorization': f'Bearer {access_token}'}
        calendar_id = request.args.get('calendar_id', 'primary')

        if request.method == 'PUT':
            data = request.get_json()

            event = {
                'summary': data.get('title', ''),
                'description': data.get('description', ''),
                'start': {
                    'dateTime': data.get('start'),
                    'timeZone': data.get('timezone', 'UTC')
                },
                'end': {
                    'dateTime': data.get('end'),
                    'timeZone': data.get('timezone', 'UTC')
                }
            }

            url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}'
            response = requests.put(url, headers={**headers, 'Content-Type': 'application/json'}, json=event)

            if response.status_code != 200:
                return jsonify({'success': False, 'error': 'Failed to update event'}), 400

            return jsonify({'success': True, 'event': response.json()})

        else:  # DELETE
            url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}'
            response = requests.delete(url, headers=headers)

            if response.status_code not in [200, 204]:
                return jsonify({'success': False, 'error': 'Failed to delete event'}), 400

            return jsonify({'success': True, 'message': 'Event deleted'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_google_bp.route('/api/crm/google/calendar/list', methods=['GET'])
def get_google_calendars():
    """Get list of user's Google calendars"""
    try:
        access_token = refresh_google_token()
        if not access_token:
            return jsonify({'success': False, 'error': 'Google account not connected'}), 401

        headers = {'Authorization': f'Bearer {access_token}'}
        url = 'https://www.googleapis.com/calendar/v3/users/me/calendarList'

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Failed to fetch calendars'}), 400

        calendars = response.json().get('items', [])
        return jsonify({'success': True, 'calendars': calendars})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# GOOGLE GMAIL
# ============================================================================

@crm_google_bp.route('/api/crm/google/gmail/send', methods=['POST'])
def send_gmail():
    """Send an email via Gmail API"""
    try:
        access_token = refresh_google_token()
        if not access_token:
            return jsonify({'success': False, 'error': 'Google account not connected'}), 401

        data = request.get_json()
        to = data.get('to')
        subject = data.get('subject', '')
        body = data.get('body', '')

        if not to:
            return jsonify({'success': False, 'error': 'Recipient email required'}), 400

        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        url = 'https://www.googleapis.com/gmail/v1/users/me/messages/send'
        response = requests.post(url, headers=headers, json={'raw': raw})

        if response.status_code not in [200, 201]:
            return jsonify({'success': False, 'error': 'Failed to send email'}), 400

        return jsonify({'success': True, 'message': 'Email sent successfully'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_google_bp.route('/api/crm/google/gmail/messages', methods=['GET'])
def get_gmail_messages():
    """Get Gmail messages"""
    try:
        access_token = refresh_google_token()
        if not access_token:
            return jsonify({'success': False, 'error': 'Google account not connected'}), 401

        headers = {'Authorization': f'Bearer {access_token}'}
        max_results = request.args.get('max_results', 20)
        query = request.args.get('q', '')

        url = 'https://www.googleapis.com/gmail/v1/users/me/messages'
        params = {'maxResults': max_results}
        if query:
            params['q'] = query

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Failed to fetch messages'}), 400

        messages = response.json().get('messages', [])
        return jsonify({'success': True, 'messages': messages})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_google_bp.route('/api/crm/google/gmail/message/<message_id>', methods=['GET'])
def get_gmail_message(message_id):
    """Get a specific Gmail message"""
    try:
        access_token = refresh_google_token()
        if not access_token:
            return jsonify({'success': False, 'error': 'Google account not connected'}), 401

        headers = {'Authorization': f'Bearer {access_token}'}
        url = f'https://www.googleapis.com/gmail/v1/users/me/messages/{message_id}'

        response = requests.get(url, headers=headers, params={'format': 'full'})

        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Failed to fetch message'}), 400

        return jsonify({'success': True, 'message': response.json()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

