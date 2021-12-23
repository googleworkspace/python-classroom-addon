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
"""Data models for the Flask server.

Uses the flask-sqlalchemy database object defined in the webapp module."""

from webapp import db

# Database model to represent a user.
class User(db.Model):
    # The user's identifying information:
    id = db.Column(db.String(120), primary_key=True)
    display_name = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True)
    portrait_url = db.Column(db.Text())

    # The user's refresh token, which will be used to obtain an access token.
    # Note that refresh tokens will become invalid if:
    # - The refresh token has not been used for six months.
    # - The user revokes your app's access permissions.
    # - The user changes passwords.
    # - The user belongs to a Google Cloud Platform organization
    #   that has session control policies in effect.
    refresh_token = db.Column(db.Text())

    def __repr__(self):
        return f"<User {self.display_name}, ID {self.id}>"