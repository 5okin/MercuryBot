import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from dotenv import load_dotenv
from utils import environment
from utils.database import Database

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

logger = environment.logging.getLogger("web.app")

# Store reference to Discord client (will be set by main.py)
discord_client = None


def set_discord_client(client):
    """Set the Discord client reference"""
    global discord_client
    discord_client = client


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))

        # Check if user is the admin
        if str(session['admin_user_id']) != str(environment.DISCORD_ADMIN_ACC):
            return jsonify({'error': 'Unauthorized'}), 403

        return f(*args, **kwargs)
    return decorated_function


# MARK: Routes
@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in"""
    if 'admin_user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login')
def login():
    """Login page"""
    return render_template('login.html')


@app.route('/api/auth/simple', methods=['POST'])
def simple_auth():
    """Simple authentication with admin ID"""
    data = request.json
    admin_id = data.get('admin_id')

    if str(admin_id) == str(environment.DISCORD_ADMIN_ACC):
        session['admin_user_id'] = admin_id
        return jsonify({'success': True, 'redirect': url_for('dashboard')})

    return jsonify({'success': False, 'error': 'Invalid admin ID'}), 401


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@admin_required
def dashboard():
    """Main dashboard"""
    # Get current configuration
    config = {
        'emojis': {
            'epic': os.getenv('DISCORD_EPIC_EMOJI', ''),
            'steam': os.getenv('DISCORD_STEAM_EMOJI', ''),
            'gog': os.getenv('DISCORD_GOG_EMOJI', ''),
            'psplus': os.getenv('DISCORD_PSPLUS_EMOJI', ''),
            'primegaming': os.getenv('DISCORD_PRIMEGAMING_EMOJI', ''),
        },
        'bot_info': {
            'guilds': len(discord_client.guilds) if discord_client else 0,
            'stores': len(discord_client.modules) if discord_client else 0,
        }
    }

    stores = []
    if discord_client and discord_client.modules:
        for store in discord_client.modules:
            stores.append({
                'name': store.name,
                'service_name': store.service_name,
                'id': store.id,
                'has_data': bool(store.data),
                'data_count': len(store.data) if store.data else 0
            })

    return render_template('dashboard.html', config=config, stores=stores)


@app.route('/templates')
@admin_required
def templates_page():
    """Message templates editor"""
    # Load current templates from messages.py
    templates = {}
    try:
        import clients.discord.messages as messages
        for store_name in ['epic', 'steam', 'gog', 'psplus', 'primegaming']:
            if hasattr(messages, store_name):
                templates[store_name] = f"Template for {store_name}"
    except Exception as e:
        logger.error(f"Failed to load templates: {e}")

    return render_template('templates.html', templates=templates)


@app.route('/test-notification')
@admin_required
def test_notification_page():
    """Test notification page"""
    servers = []
    if discord_client:
        for guild in discord_client.guilds:
            server_data = Database.get_discord_server(guild.id)
            servers.append({
                'id': guild.id,
                'name': guild.name,
                'channel_id': server_data.get('channel') if server_data else None,
                'has_channel': bool(server_data and server_data.get('channel'))
            })

    stores = []
    if discord_client and discord_client.modules:
        for store in discord_client.modules:
            stores.append({
                'name': store.name,
                'service_name': store.service_name,
                'has_data': bool(store.data)
            })

    return render_template('test_notification.html', servers=servers, stores=stores)


# MARK: API Endpoints
@app.route('/api/config/emojis', methods=['GET', 'POST'])
@admin_required
def config_emojis():
    """Get or update emoji configuration"""
    if request.method == 'GET':
        return jsonify({
            'epic': os.getenv('DISCORD_EPIC_EMOJI', ''),
            'steam': os.getenv('DISCORD_STEAM_EMOJI', ''),
            'gog': os.getenv('DISCORD_GOG_EMOJI', ''),
            'psplus': os.getenv('DISCORD_PSPLUS_EMOJI', ''),
            'primegaming': os.getenv('DISCORD_PRIMEGAMING_EMOJI', ''),
        })

    if request.method == 'POST':
        data = request.json
        # Update .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

        # Read current .env
        env_vars = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value

        # Update emoji values
        if 'epic' in data:
            env_vars['DISCORD_EPIC_EMOJI'] = data['epic']
        if 'steam' in data:
            env_vars['DISCORD_STEAM_EMOJI'] = data['steam']
        if 'gog' in data:
            env_vars['DISCORD_GOG_EMOJI'] = data['gog']
        if 'psplus' in data:
            env_vars['DISCORD_PSPLUS_EMOJI'] = data['psplus']
        if 'primegaming' in data:
            env_vars['DISCORD_PRIMEGAMING_EMOJI'] = data['primegaming']

        # Write back to .env
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f'{key}={value}\n')

        return jsonify({'success': True, 'message': 'Emojis updated. Restart bot to apply changes.'})


@app.route('/api/test-notification', methods=['POST'])
@admin_required
def send_test_notification():
    """Send a test notification to a specific server"""
    if not discord_client:
        return jsonify({'success': False, 'error': 'Discord client not available'}), 500

    data = request.json
    server_id = int(data.get('server_id'))
    store_name = data.get('store_name')

    # Find the store
    store = None
    for s in discord_client.modules:
        if s.name == store_name:
            store = s
            break

    if not store:
        return jsonify({'success': False, 'error': 'Store not found'}), 404

    if not store.data:
        return jsonify({'success': False, 'error': 'Store has no data to send'}), 400

    # Get server info
    server_data = Database.get_discord_server(server_id)
    if not server_data or not server_data.get('channel'):
        return jsonify({'success': False, 'error': 'Server has no channel configured'}), 400

    # Send test notification
    async def send_test():
        from io import BytesIO
        import discord

        try:
            image_bytes = store.image
            image_type = store.image_type

            buffer = BytesIO(image_bytes.getvalue())
            file = discord.File(fp=buffer, filename=f'img.{image_type.lower()}')

            await discord_client.store_messages(
                store.name,
                server_id,
                server_data.get('channel'),
                server_data.get('role'),
                file
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send test notification: {e}")
            return False

    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(send_test())
    loop.close()

    if success:
        return jsonify({'success': True, 'message': 'Test notification sent!'})
    else:
        return jsonify({'success': False, 'error': 'Failed to send notification'}), 500


@app.route('/api/stats')
@admin_required
def get_stats():
    """Get bot statistics"""
    stats = {
        'guilds': len(discord_client.guilds) if discord_client else 0,
        'stores': len(discord_client.modules) if discord_client else 0,
        'total_deals': 0
    }

    if discord_client and discord_client.modules:
        for store in discord_client.modules:
            if store.data:
                stats['total_deals'] += len(store.data)

    return jsonify(stats)


def run_server(client, host='0.0.0.0', port=5000):
    """Run the Flask server"""
    set_discord_client(client)
    logger.info(f"Starting web interface on {host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)
