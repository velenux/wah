# encoding: utf-8

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wah.sqlite'
db = SQLAlchemy(app)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(512), unique=True)

    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return '"%r"' % self.text


# create the database if it doesn't exist
try:
    cards = Card.query.first()
except Exception as e:
    db.create_all()


@app.route('/')
def show_index():
    return 'Currently holding %d cards' % db.session.query(Card).count()

@app.route('/card/add')
def add_card():
    c = Card('sopra la panca la capra canta')
    db.session.add(c)
    db.session.commit()
    return 'Added.'
