# encoding: utf-8

import re
from flask import *
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wah.sqlite'
db = SQLAlchemy(app)
app.secret_key = 'FIXME: Change Me'

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

try:
    cards = Card.query.first()
    decks = Deck.query.first()
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
    if request.method == 'POST':
        error = None
        # FIXME: stub
        if request.form['username'] == 'donald.trump':
            error = 'Invalid account'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_main_index'))
    # if method is not POST
    return render_template('login.html')


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
    """Tries to add a new deck to the database."""
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
    """List all decks."""
    return render_template('show_decks.html', all_decks=Deck.query.all())
