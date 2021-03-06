# encoding: utf-8

import re

import json

from flask import *
from flask_sqlalchemy import SQLAlchemy

import logging
from logging.handlers import RotatingFileHandler


# CHANGE HERE
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin'
ADMIN_MAIL = 'admin@example.org'


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wah.sqlite'
db = SQLAlchemy(app)
app.secret_key = 'FIXME: Change Me'
app.debug = True

# logging
handler = RotatingFileHandler('wah.log', maxBytes=10000000, backupCount=1)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)


# ~~ database ~~

# Deck / Card associations
deck_card_associations = db.Table('deck_card_associations',
    db.Column('card_id', db.Integer, db.ForeignKey('card.id')),
    db.Column('deck_id', db.Integer, db.ForeignKey('deck.id'))
)

class Card(db.Model):
    """Model for a card."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(512), unique=True)
    kind = db.Column(db.Integer)

    def __init__(self, text):
        """Create the Card object."""
        # substitute any number of underscores with 4
        text = re.sub('__+', '____', text)

        if "____" in text:
            self.kind = 1
        else:
            self.kind = 0
        self.text = text

    def __repr__(self):
        return '"%r"' % self.text

class Deck(db.Model):
    """Model for a collection of Cards."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(512), unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cards = db.relationship('Card', secondary=deck_card_associations,
        backref=db.backref('decks', lazy='dynamic'))

    def __init__(self, name):
        """Create the Deck object."""
        self.name = name

    def __repr__(self):
        return '"%r"' % self.name

    def add_card(self, card):
        try:
            self.cards.add(card)
        except Exception as e:
            app.logger.error("error adding card %s to deck %s, %s", card.name, self.name, e)
            raise e


class User(db.Model):
    """Model for a user."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True)
    email = db.Column(db.String(512), unique=True)
    password = db.Column(db.String(64))
    owned_games = db.relationship('Game',
        backref=db.backref('owner'),
        lazy='dynamic')
    owned_decks = db.relationship('Deck',
        backref=db.backref('owner'),
        lazy='dynamic')

    def __init__(self, username, email, password):
        """Create the User object."""
        self.username = username
        self.email = email
        self.password = self.__crypt(password.encode('utf-8'))

    def __repr__(self):
        return '"%r"' % self.username

    def valid_pass(self, password):
        return self.__crypt(password.encode('utf-8')) == self.password

    def __crypt(self, text):
        from hashlib import sha256
        hash = sha256()
        hash.update(text)
        return hash.hexdigest()


class Game(db.Model):
    """Model for a game."""
    # FIXME: this is horrible and really needs transactions to be safe to use
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.PickleType())
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, status, owner):
        """Create the Game object."""
        try:
            app.logger.debug("Game.__init__")
            app.logger.debug("status: %s", status)
            app.logger.debug("owner ID: %s", owner.id)
            self._status = status
            self.status = self._status
            self.owner_id = owner.id
        except Exception as e:
            app.logger.error("error while initializing a game, %s", e)
            raise e

    def __repr__(self):
        return '"Game ID: %r"' % self.id

    def valid_pass(self, password):
        return self.__crypt(password.encode('utf-8')) == self._status['password']

    def save_status(self):
        self.status = self._status

    def __crypt(self, text):
        from hashlib import sha256
        hash = sha256()
        hash.update(text)
        return hash.hexdigest()


# ~~ main ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# FIXME: quick 'n' dirty hack to create all the required tables on first run
try:
    card = Card.query.first()
    deck = Deck.query.first()
    user = User.query.first()
    game = Game.query.first()
    owned_games = user.owned_games.all()
    print('Database ready.')
except Exception as e:
    # create all tables
    db.create_all()
    # create a default admin user
    admin = User(ADMIN_USER, ADMIN_MAIL, ADMIN_PASS)
    db.session.add(admin)
    db.session.commit()
    print('Initialized the database.')


# /    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/')
def show_main_index():
    """Shows the main index for the website."""
    return render_template('main_index.html',
        card_number = db.session.query(Card).count(),
        user = User.query.get(session['uid']))


# /login    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in the website."""
    error = None
    if request.method == 'POST':
        user = request.form['username']
        pasw = request.form['password']
        try:
            # FIXME: should be able to use username OR email to log in
            #u = User.query.filter_by((User.username == user | User.email == user)).first()
            u = User.query.filter_by(username=user).first()
            if u.valid_pass(pasw):
                app.logger.info('valid password')
                session['logged_in'] = True
                session['uid'] = u.id
                flash('Logged in successfully')
                return redirect(url_for('show_main_index'))
            else:
                app.logger.error('invalid password')
                error = 'Invalid account'
        except Exception as e:
            app.logger.info('exception while logging', e)
            error = 'Invalid account'
    # if method is not POST
    return render_template('login.html', error=error)


# /logout    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/logout')
def logout():
    """Logs the user out of the website."""
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_main_index'))


# /card/add    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/card/add', methods=['GET', 'POST'])
def add_card():
    """Add a new card to the database."""
    if request.method == 'POST':
        error = None
        try:
            c = Card(request.form['card-text'])
            db.session.add(c)
            db.session.commit()
            flash('Card added!')
            return redirect(url_for('show_cards'))
        except Exception as e:
            flash('Error adding the card!')
            error = str(e)
            return render_template('show_cards.html', error=error)
    # if method is not POST
    return render_template('show_cards.html')


# /card/list    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/card/list')
def show_cards():
    """List all cards."""
    return render_template('show_cards.html', all_cards=Card.query.all())


# /deck/add    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/deck/add', methods=['GET', 'POST'])
def add_deck():
    """Adds a new deck to the database."""
    if request.method == 'POST':
        error = None
        try:
            d = Deck(request.form['deck-name'])
            db.session.add(d)
            db.session.commit()
            flash('deck added!')
            return redirect(url_for('show_decks'))
        except Exception as e:
            flash('Error adding the deck!')
            error = str(e)
            return render_template('show_decks.html', error=error)
    # if method is not POST
    return render_template('show_decks.html')


# /deck/list    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/deck/list')
def show_decks():
    """Lists all decks."""
    return render_template('show_decks.html', all_decks=Deck.query.all())


# /deck/X/add/Y    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/deck/<int:deck_id>/add/<int:card_id>')
def add_card_to_deck(deck_id, card_id):
    """Adds a Card to a Deck."""
    error = None
    try:
        card = Card.query.get(card_id)
        deck = Deck.query.get(deck_id)
        if card is not None:
            deck.cards.append(card)
            db.session.commit()
            flash('Added card ' + card.text)
    except Exception as e:
        app.logger.error("Error adding card id %d to deck id %d: %s", card_id, deck_id, e)
        error = "Error adding card id %d to deck id %d: %s" % (card_id, deck_id, e)
    return redirect(url_for('show_deck', deck_id = deck_id))


# /deck/X/    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/deck/<int:deck_id>/')
@app.route('/deck/<int:deck_id>/show')
def show_deck(deck_id):
    """Shows the contents of a specific Deck."""
    error = None
    try:
        deck = Deck.query.get(deck_id)
    except Exception as e:
        app.logger.error("Error retrieving deck_id %d: %s", deck_id, e)
        error = "Error retrieving deck_id %d: %s" % (deck_id, e)
    return render_template('show_deck.html', error = error, deck = deck)


# /user/add    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    """Tries to add a new user to the database."""
    # FIXME: this is a security risk, anyone can add users
    error = None
    if request.method == 'POST':
        try:
            u = User(request.form['username'], request.form['email'], request.form['password'])
            db.session.add(u)
            db.session.commit()
            flash('user added!')
            return redirect(url_for('show_users'))
        except Exception as e:
            flash('Error adding the user!')
            error = str(e)
            return render_template('show_users.html', error=error)
    # if method is not POST
    return render_template('show_users.html', error=error, user_number=db.session.query(User).count())


# /user/show    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/user/show')
def show_users():
    """Shows how many users we have (stub)."""
    return render_template('show_users.html', user_number=db.session.query(User).count())


# /game/add    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/game/add', methods=['GET', 'POST'])
def add_game():
    """Add a new game entry to the database."""
    error = None
    try:
        u = User.query.get(session['uid'])
        if u is None:
            error = 'Invalid session'
    except Exception as e:
        flash('Error retrieving user data')
        error = str(e)
        return render_template('show_games.html', error=error, games = [])
    if request.method == 'POST':
        try:
            g = Game({}, u)
            db.session.add(g)
            db.session.commit()
            flash('game created!')
            return redirect(url_for('play_game', game_id = g.id))
        except Exception as e:
            flash('Error creating the game!')
            app.logger.error("error while creating a game: %s", e)
            error = str(e)
            return render_template('show_games.html', error=error, games = u.owned_games.all())
    # if method is not POST
    return render_template('show_games.html', error=error, games = u.owned_games.all())


# /game/X/play    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/game/<int:game_id>/play')
def play_game(game_id):
    """Shows the page to play the game with id game_id."""
    error = None
    return 'Game %d' % game_id


# /game/list    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/game/list')
def show_games():
    """Shows all games belonging to a user."""
    error = None
    try:
        u = User.query.get(session['uid'])
        if u is None:
            error = 'Invalid session'
    except Exception as e:
        flash('Error retrieving user data')
        error = str(e)
        return render_template('show_games.html', error=error, games = [])
    try:
        games = u.owned_games.all()
    except Exception as e:
        flash('Error retrieving games for the user!')
        error = str(e)
        return render_template('show_games.html', error=error, games = [])
    # if method is not POST
    return render_template('show_games.html', error=error, games = u.owned_games)
