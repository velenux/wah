# encoding: utf-8

import re

import json

from flask import *
from flask_sqlalchemy import SQLAlchemy

import logging
from logging.handlers import RotatingFileHandler

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
    cards = db.relationship('Card', secondary=deck_card_associations,
        backref=db.backref('decks', lazy='dynamic'))

    def __init__(self, name):
        """Create the Deck object."""
        self.name = name

    def __repr__(self):
        return '"%r"' % self.name

class User(db.Model):
    """Model for a user."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True)
    email = db.Column(db.String(512), unique=True)
    password = db.Column(db.String(64))

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

class Match(db.Model):
    """Model for a match."""
    # FIXME: this is horrible and really needs transactions to be safe to use
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Text(), unique=True)

    def __init__(self, status):
        """Create the Match object."""
        self._status = status
        self.status = json.dumps(self._status)

    def __repr__(self):
        return '"Game ID: %r"' % self.id

    def valid_pass(self, password):
        return self.__crypt(password.encode('utf-8')) == self._status['password']

    def save_status(self):
        self.status = json.dumps(self._status)

    def __crypt(self, text):
        from hashlib import sha256
        hash = sha256()
        hash.update(text)
        return hash.hexdigest()


# ~~ main ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# FIXME: quick 'n' dirty hack to create all the required tables on first run
try:
    cards = Card.query.first()
    decks = Deck.query.first()
    users = User.query.first()
    matches = Match.query.first()
    print('Database ready.')
except Exception as e:
    db.create_all()
    print('Initialized the database.')


@app.route('/')
def show_main_index():
    """Shows the main index for the website."""
    return render_template('main_index.html', card_number = db.session.query(Card).count())


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in the website."""
    error = None
    if request.method == 'POST':
        user = request.form['username']
        pasw = request.form['password']
        try:
            #u = User.query.filter_by((User.username == user | User.email == user)).first()
            u = User.query.filter_by(username=user).first()
            if u.valid_pass(pasw):
                app.logger.info('valid password')
                session['logged_in'] = True
                flash('You were logged in')
                return redirect(url_for('show_main_index'))
            else:
                app.logger.error('invalid password')
                error = 'Invalid account'
        except Exception as e:
            app.logger.info('exception while logging', e)
            error = 'Invalid account'
    # if method is not POST
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out of the website."""
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_main_index'))


@app.route('/card/add', methods=['GET', 'POST'])
def add_card():
    """Tries to add a new card to the database."""
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


@app.route('/card/list')
def show_cards():
    """List all cards."""
    return render_template('show_cards.html', all_cards=Card.query.all())


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


@app.route('/deck/list')
def show_decks():
    """Lists all decks."""
    return render_template('show_decks.html', all_decks=Deck.query.all())


# FIXME: this is a security risk, anyone can add users
@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    """Tries to add a new user to the database."""
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


@app.route('/user/show')
def show_users():
    """Shows how many users we have (stub)."""
    return render_template('show_users.html', user_number=db.session.query(User).count())
