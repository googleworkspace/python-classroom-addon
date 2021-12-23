from flask import Flask
import config
from flask_sqlalchemy import SQLAlchemy
from os import path

app = Flask(__name__)
app.config.from_object(config.Config)

db = SQLAlchemy(app)

from webapp import routes, models

# Initialize the database file if not created.
if not path.exists(config.DATABASE_FILE_NAME):
    db.create_all()