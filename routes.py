import csv
import io
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import app, db, login_manager
from models import User, APIKey, Article
from llm_service import generate_article

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    articles = Article.query.order_by(Article.created_at.desc()).all()
    return render_template('dashboard.html', articles=articles)

@app.route('/settings')
@login_required
def settings():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    api_keys = APIKey.query.all()
    return render_template('settings.html', api_keys=api_keys)

@app.route('/api/keys', methods=['POST'])
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

@app.route('/upload', methods=['POST'])
@login_required
def upload_titles():
    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('dashboard'))

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"))
        csv_reader = csv.reader(stream)
        next(csv_reader, None)  # Skip header row
        
        for row in csv_reader:
            if row:  # Check if row is not empty
                article = Article(title=row[0])
                db.session.add(article)
        
        db.session.commit()
        flash('Titles uploaded successfully')
    except Exception as e:
        flash(f'Error processing file: {str(e)}')
    
    return redirect(url_for('dashboard'))

@app.route('/generate/<int:article_id>', methods=['POST'])
@login_required
def generate(article_id):
    article = Article.query.get_or_404(article_id)
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

@app.route('/status/<int:article_id>')
@login_required
def article_status(article_id):
    article = Article.query.get_or_404(article_id)
    return jsonify({
        'status': article.status,
        'error': article.error if article.error else None
    })

# Initialize admin user if not exists
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')  # Change this in production
        db.session.add(admin)
        db.session.commit()
