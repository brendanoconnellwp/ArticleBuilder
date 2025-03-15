import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import User, APIKey, Article
from app import db, login_manager
from llm_service import generate_article

# Create blueprint
main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('register.html')

            # Check password strength
            if len(password) < 8:
                flash('Password must be at least 8 characters long', 'error')
                return render_template('register.html')

            # Check if username exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('register.html')

            # Create new user
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash('Registration successful!', 'success')
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration', 'error')
            return render_template('register.html')

    return render_template('register.html')

@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user:
            # Here you would typically send an email with reset link
            # For demo, we'll just reset to a default password
            user.set_password('temporary')
            db.session.commit()
            flash('Password has been reset to: temporary', 'success')
            return redirect(url_for('main.login'))
        flash('Username not found', 'error')
    return render_template('forgot_password.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/')
@login_required
def dashboard():
    articles = Article.query.filter_by(user_id=current_user.id).order_by(Article.created_at.desc()).all()
    return render_template('dashboard.html', articles=articles)

@main.route('/settings')
@login_required
def settings():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('main.dashboard'))
    api_keys = APIKey.query.all()
    return render_template('settings.html', api_keys=api_keys)

@main.route('/add_title', methods=['POST'])
@login_required
def add_title():
    titles = request.form.get('titles', '').strip().split('\n')
    titles = [title.strip() for title in titles if title.strip()]

    if not titles:
        flash('No titles provided')
        return redirect(url_for('main.dashboard'))

    for title in titles:
        article = Article(title=title, user_id=current_user.id)
        db.session.add(article)

    db.session.commit()
    flash(f'Added {len(titles)} title(s) successfully')
    return redirect(url_for('main.dashboard'))

@main.route('/api/keys', methods=['POST'])
@login_required
def update_api_key():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    service = request.form.get('service')
    key = request.form.get('key')

    if not service or not key:
        return jsonify({'error': 'Missing required fields'}), 400

    api_key = APIKey.query.filter_by(service=service).first()
    if api_key:
        api_key.key = key
        api_key.updated_at = datetime.utcnow()
    else:
        api_key = APIKey(service=service, key=key)
        db.session.add(api_key)

    db.session.commit()
    return jsonify({'message': 'API key updated successfully'})

@main.route('/upload_titles', methods=['POST'])
@login_required
def upload_titles():
    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('main.dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('main.dashboard'))

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"))
        csv_reader = csv.reader(stream)
        next(csv_reader, None)  # Skip header row

        for row in csv_reader:
            if row:  # Check if row is not empty
                article = Article(title=row[0], user_id=current_user.id)
                db.session.add(article)

        db.session.commit()
        flash('Titles uploaded successfully')
    except Exception as e:
        flash(f'Error processing file: {str(e)}')

    return redirect(url_for('main.dashboard'))

@main.route('/generate/<int:article_id>', methods=['POST'])
@login_required
def generate(article_id):
    article = Article.query.get_or_404(article_id)
    if article.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if article.status == 'processing':
        return jsonify({'error': 'Article is already being processed'}), 400

    try:
        article.status = 'processing'
        db.session.commit()

        content = generate_article(article.title)

        article.content = content
        article.status = 'completed'
        article.completed_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'status': 'success',
            'content': content
        })
    except Exception as e:
        article.status = 'failed'
        article.error = str(e)
        db.session.commit()
        return jsonify({'error': str(e)}), 500

@main.route('/status/<int:article_id>')
@login_required
def article_status(article_id):
    article = Article.query.get_or_404(article_id)
    if article.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'status': article.status,
        'error': article.error if article.error else None
    })