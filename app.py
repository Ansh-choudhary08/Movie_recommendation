from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import requests
from dotenv import load_dotenv
import os
from datetime import datetime
import logging
import sys
from pathlib import Path
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from models import db, User, WatchlistItem
from werkzeug.exceptions import HTTPException
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Required environment variables
REQUIRED_ENV_VARS = {
    'TMDB_API_KEY': os.getenv('TMDB_API_KEY'),
    'TMDB_ACCESS_TOKEN': os.getenv('TMDB_ACCESS_TOKEN')
}

# Validate environment variables
missing_vars = [var for var, value in REQUIRED_ENV_VARS.items() if not value]
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)
    print(error_msg)
    print("Please create a .env file with the required variables.")
    sys.exit(1)

# TMDB API configuration
TMDB_API_KEY = REQUIRED_ENV_VARS['TMDB_API_KEY']
TMDB_ACCESS_TOKEN = REQUIRED_ENV_VARS['TMDB_ACCESS_TOKEN']
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Get the absolute path to the instance directory
instance_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance'))

# Configure Flask app
app = Flask(__name__, instance_path=instance_path)

# Configure SQLAlchemy with absolute path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "movie_finder.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'error'

@login_manager.user_loader
def load_user(user_id: str) -> User:
    return User.query.get(int(user_id))

def fetch_tmdb_data(endpoint, params=None):
    """Fetch data from TMDB API with error handling"""
    try:
        url = f"{TMDB_BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
            "accept": "application/json"
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"TMDB API error: {e}")
        return None

@app.route("/")
def hello_world():
    try:
        # Fetch trending movies
        trending = fetch_tmdb_data('trending/movie/week')
        trending_movies = trending.get('results', []) if trending else []

        # Fetch movies by genre
        action_movies = fetch_tmdb_data('discover/movie', {
            'with_genres': 28,  # Action
            'sort_by': 'popularity.desc'
        }).get('results', [])[:6]

        adventure_movies = fetch_tmdb_data('discover/movie', {
            'with_genres': 12,  # Adventure
            'sort_by': 'popularity.desc'
        }).get('results', [])[:6]

        romance_movies = fetch_tmdb_data('discover/movie', {
            'with_genres': 10749,  # Romance
            'sort_by': 'popularity.desc'
        }).get('results', [])[:6]

        comedy_movies = fetch_tmdb_data('discover/movie', {
            'with_genres': 35,  # Comedy
            'sort_by': 'popularity.desc'
        }).get('results', [])[:6]

        # Format all movie data
        for movies in [trending_movies, action_movies, adventure_movies, romance_movies, comedy_movies]:
            for movie in movies:
                movie['release_date'] = movie.get('release_date', 'N/A')
                movie['vote_average'] = movie.get('vote_average', 0)
                if not movie.get('poster_path'):
                    movie['poster_path'] = None

        return render_template('index.html', 
                             movies=trending_movies[:6],
                             action_movies=action_movies,
                             adventure_movies=adventure_movies,
                             romance_movies=romance_movies,
                             comedy_movies=comedy_movies)

    except Exception as e:
        logger.error(f"Error loading homepage: {e}")
        return render_template('500.html'), 500

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            # Validate input
            if not all([username, email, password, confirm_password]):
                flash('All fields are required', 'error')
                return redirect(url_for('register'))

            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('register'))

            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return redirect(url_for('register'))

            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return redirect(url_for('register'))

            # Create new user
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('An error occurred during registration', 'error')
            return redirect(url_for('register'))

    return render_template('registration.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            user = User.query.filter_by(username=username).first()

            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('hello_world'))
            else:
                flash('Invalid username or password', 'error')
                return redirect(url_for('login'))

        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('An error occurred during login', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('hello_world'))

@app.route("/search")
def search_movies():
    query = request.args.get('query', '')
    if not query:
        return render_template('search_results.html', movies=[], query='')
    
    try:
        search_results = fetch_tmdb_data('search/movie', {'query': query})
        movies = search_results.get('results', []) if search_results else []
        
        for movie in movies:
            movie['release_date'] = movie.get('release_date', 'N/A')
            movie['vote_average'] = movie.get('vote_average', 0)
            if not movie.get('poster_path'):
                movie['poster_path'] = None
        
        return render_template('search_results.html', movies=movies, query=query)
    except Exception as e:
        logger.error(f"Search error: {e}")
        return render_template('search_results.html', movies=[], query=query)

@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):
    try:
        movie = fetch_tmdb_data(f'movie/{movie_id}')
        if not movie:
            return render_template('404.html'), 404
            
        return render_template('movie_details.html', movie=movie)
    except Exception as e:
        logger.error(f"Error fetching movie details: {e}")
        return render_template('500.html'), 500
    
@app.route("/watchlist")
@login_required
def watchlist():
    try:
        # Get watchlist items for current user
        watchlist_items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
        movies = []
        
        for item in watchlist_items:
            movie = fetch_tmdb_data(f'movie/{item.movie_id}')
            if movie:
                movie['release_date'] = movie.get('release_date', 'N/A')
                movie['vote_average'] = movie.get('vote_average', 0)
                movie['added_date'] = item.added_at.strftime('%Y-%m-%d')
                if not movie.get('poster_path'):
                    movie['poster_path'] = None
                movies.append(movie)
        
        return render_template('watchlist.html', movies=movies)
    except Exception as e:
        logger.error(f"Error in watchlist route: {e}")
        return render_template('watchlist.html', movies=[])

@app.route("/api/watchlist/add", methods=['POST'])
@login_required
def add_to_watchlist():
    try:
        data = request.get_json()
        movie_id = data.get('movie_id')
        
        if not movie_id:
            return jsonify({'error': 'Movie ID is required'}), 400
            
        # Check if movie already in watchlist
        existing = WatchlistItem.query.filter_by(
            user_id=current_user.id,
            movie_id=movie_id
        ).first()
        
        if existing:
            return jsonify({'error': 'Movie already in watchlist'}), 400
            
        # Add movie to watchlist
        watchlist_item = WatchlistItem(movie_id=movie_id, user_id=current_user.id)
        db.session.add(watchlist_item)
        db.session.commit()
        
        return jsonify({'message': 'Movie added to watchlist'}), 200
        
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        return jsonify({'error': 'Failed to add movie to watchlist'}), 500

@app.route("/api/watchlist/remove/<int:movie_id>", methods=['DELETE'])
@login_required
def remove_from_watchlist(movie_id):
    try:
        # Find and delete the watchlist item
        watchlist_item = WatchlistItem.query.filter_by(
            user_id=current_user.id,
            movie_id=movie_id
        ).first()
        
        if watchlist_item:
            db.session.delete(watchlist_item)
            db.session.commit()
            return jsonify({'message': 'Movie removed from watchlist'}), 200
        else:
            return jsonify({'error': 'Movie not found in watchlist'}), 404
            
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        return jsonify({'error': 'Failed to remove movie from watchlist'}), 500

@app.route("/trending/<time_window>")
def trending_movies(time_window):
    try:
        # Validate time window
        if time_window not in ['day', 'week']:
            time_window = 'week'
        
        # Fetch trending movies
        trending = fetch_tmdb_data(f'trending/movie/{time_window}')
        movies = trending.get('results', []) if trending else []
        
        # Add formatted data
        for movie in movies:
            movie['release_date'] = movie.get('release_date', 'N/A')
            movie['vote_average'] = movie.get('vote_average', 0)
            if not movie.get('poster_path'):
                movie['poster_path'] = None
        
        logger.debug(f"Found {len(movies)} trending movies for {time_window}")
        return render_template('trending.html', 
                             movies=movies, 
                             time_window=time_window)
                             
    except Exception as e:
        logger.error(f"Error fetching trending movies: {e}")
        return render_template('trending.html', movies=[], time_window=time_window)

@app.route("/actor/<int:actor_id>")
def actor_movies(actor_id):
    try:
        # Fetch actor details
        actor = fetch_tmdb_data(f'person/{actor_id}')
        if not actor:
            return render_template('404.html'), 404
            
        # Fetch actor's movies
        movies = fetch_tmdb_data(f'person/{actor_id}/movie_credits')
        if movies:
            # Sort by popularity and get cast appearances
            cast_movies = sorted(
                movies.get('cast', []),
                key=lambda x: x.get('popularity', 0),
                reverse=True
            )
            
            # Format movie data
            for movie in cast_movies:
                movie['release_date'] = movie.get('release_date', 'N/A')
                movie['vote_average'] = movie.get('vote_average', 0)
                if not movie.get('poster_path'):
                    movie['poster_path'] = None
            
            return render_template('actor.html', 
                                 actor=actor,
                                 movies=cast_movies[:24])  # Limit to top 24 movies
                                 
    except Exception as e:
        logger.error(f"Error fetching actor movies: {e}")
        return render_template('500.html'), 500

@app.route("/genre/<int:genre_id>")
def genre_movies(genre_id):
    try:
        # Get genre name from our predefined list
        genres = {
            28: 'Action', 12: 'Adventure', 16: 'Animation',
            35: 'Comedy', 80: 'Crime', 18: 'Drama',
            14: 'Fantasy', 27: 'Horror', 9648: 'Mystery',
            10749: 'Romance', 878: 'Science Fiction', 53: 'Thriller'
        }
        
        genre_name = genres.get(genre_id, 'Unknown')
        
        # Fetch movies by genre
        movies_data = fetch_tmdb_data('discover/movie', {
            'with_genres': genre_id,
            'sort_by': 'popularity.desc'
        })
        
        if not movies_data:
            return render_template('404.html'), 404
            
        movies = movies_data.get('results', [])
        
        # Format movie data
        for movie in movies:
            movie['release_date'] = movie.get('release_date', 'N/A')
            movie['vote_average'] = movie.get('vote_average', 0)
            if not movie.get('poster_path'):
                movie['poster_path'] = None
        
        return render_template('genre.html', 
                             genre_name=genre_name,
                             movies=movies)
                             
    except Exception as e:
        logger.error(f"Error fetching genre movies: {e}")
        return render_template('500.html'), 500

# Add these error handlers after your routes
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()  # Roll back the session in case of database errors
    logger.error(f"500 error: {error}\n{traceback.format_exc()}")
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Get detailed error information
    exc_info = sys.exc_info()
    error_details = {
        'type': exc_info[0].__name__,
        'message': str(exc_info[1]),
        'traceback': traceback.format_exc()
    }
    
    # Log the detailed error
    logger.error(f"Unhandled exception:\nType: {error_details['type']}\nMessage: {error_details['message']}\nTraceback:\n{error_details['traceback']}")
    
    # Pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    # Roll back database changes
    if db.session.is_active:
        db.session.rollback()
    
    # In debug mode, show error details
    if app.debug:
        return f"""
        <pre>
        Error Type: {error_details['type']}
        Error Message: {error_details['message']}
        Traceback:
        {error_details['traceback']}
        </pre>
        """, 500
    
    # In production, show generic error page
    return render_template("500.html"), 500

# Update the init_db function to be more robust
def init_db():
    try:
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}\n{traceback.format_exc()}")
        sys.exit(1)

# Update the main block to include better error handling
if __name__ == "__main__":
    try:
        init_db()
        app.run(debug=True)
    except Exception as e:
        logger.error(f"Application failed to start: {e}\n{traceback.format_exc()}")
        sys.exit(1)