#!/usr/bin/env python3
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Initialize the webapp module.

Starts the flask server, loads the config, and initializes the database."""

import flask
import config
from flask_sqlalchemy import SQLAlchemy
from os import path

app = flask.Flask(__name__)
app.config.from_object(config.Config)

db = SQLAlchemy(app)

from webapp import attachment_routes, attachment_discovery_routes, models
from webapp import credential_handler as ch

with app.app_context():
  # Initialize the database file if not created.
  if not path.exists(config.DATABASE_FILE_NAME):
    db.create_all()
