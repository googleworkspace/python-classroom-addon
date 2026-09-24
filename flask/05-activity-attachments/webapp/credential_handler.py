#!/usr/bin/env python3
# Copyright 2022 Google LLC
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
"""Provides the CredentialHandler object to manage OAuth credentials."""

from webapp.models import User
from webapp import app, db
import json
import flask
import os

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from google.auth.transport.requests import Request

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
# These scopes should match the scopes in your GCP project's
# OAuth Consent Screen: https://console.cloud.google.com/apis/credentials/consent
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/classroom.addons.teacher",
    "https://www.googleapis.com/auth/classroom.addons.student",
    "https://www.googleapis.com/auth/classroom.coursework.students",
]

CLASSROOM_API_SERVICE_NAME = "classroom"
CLASSROOM_API_VERSION = "v1"

# An API key in your GCP project's credentials:
# https://console.cloud.google.com/apis/credentials.
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")


class CredentialHandler:
  """Provides the CredentialHandler object to manage OAuth credentials."""

  def __init__(self, client_secrets_file=CLIENT_SECRETS_FILE):
    """Initializes the CredentialHandler object.

    Args:
        client_secrets_file: The path to the client secrets file.
    """
    self._client_secrets_dict = json.load(open(client_secrets_file)).get("web")
    self._credentials = None

  def get_credentials(self):
    """Retrieves or reconstructs valid credentials for the active session.

    Returns:
        google.oauth2.credentials.Credentials or None if not authenticated.
    """
    user_id = flask.session.get("user_id")
    if not user_id:
      return None

    # Retrieve user record using the trusted session user_id.
    stored_user = self.get_credentials_from_storage(user_id)
    if not stored_user or not stored_user.refresh_token:
      return None

    session_creds = flask.session.get("credentials") or {}
    credentials = google.oauth2.credentials.Credentials(
        token=session_creds.get("token"),
        refresh_token=stored_user.refresh_token,
        token_uri=self._client_secrets_dict["token_uri"],
        client_id=self._client_secrets_dict["client_id"],
        client_secret=self._client_secrets_dict["client_secret"],
        scopes=SCOPES,
    )

    if not credentials.valid:
      credentials.refresh(Request())
      flask.session["credentials"] = self.session_credentials_to_dict(credentials)

    self._credentials = credentials

    return self._credentials

  def session_credentials_to_dict(self, credentials):
    """Converts the given credentials to a dictionary.

    Args:
        credentials: A dictionary containing the OAuth credentials to save.
    """
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

  def get_credentials_from_storage(self, id):
    """
    Retrieves credentials from storage and loads them into the session.

    Args:
        id: The user ID, typically passed in the login_hint query parameter.
    Returns:
        The User record from the database for the given ID, or None if
        no record could be found.
    """
    return User.query.get(id)

  def save_credentials_to_storage(self, credentials):
    """
    Updates or adds a User to the database. A new user is added only if both
    credentials and user_info are provided.

    Args:
        credentials: A populated Credentials object.
    """

    # Issue a request for the user's profile details.
    user_info_service = googleapiclient.discovery.build(
        serviceName="oauth2", version="v2", credentials=credentials
    )
    user_info = user_info_service.userinfo().get().execute()
    flask.session["username"] = user_info.get("name")
    flask.session["user_id"] = user_info.get("id")

    # See if we have any stored credentials for this user. If they have used
    # the add-on before, we should have received login_hint in the query
    # parameters.
    existing_user = self.get_credentials_from_storage(user_info.get("id"))

    # If we do have stored credentials, update the database.
    if existing_user:
      if user_info:
        existing_user.id = user_info.get("id")
        existing_user.display_name = user_info.get("name")
        existing_user.email = user_info.get("email")
        existing_user.portrait_url = user_info.get("picture")

      if credentials and credentials.refresh_token is not None:
        existing_user.refresh_token = credentials.refresh_token

    # If not, this must be a new user, so add a new entry to the database.
    else:
      new_user = User(
          id=user_info.get("id"),
          display_name=user_info.get("name"),
          email=user_info.get("email"),
          portrait_url=user_info.get("picture"),
          refresh_token=credentials.refresh_token,
      )

      db.session.add(new_user)

    db.session.commit()

  def get_discovery_service(
      self, service_name, version, service_url=None, credentials=None
  ):
    """Gets the Google Classroom discovery service.

    Returns:
        The Google Classroom discovery service.
    """
    creds = self.get_credentials() if credentials is None else credentials
    return (
        googleapiclient.discovery.build(
            serviceName=service_name,
            version=version,
            credentials=creds,
        )
        if service_url is None
        else googleapiclient.discovery.build(
            serviceName=service_name,
            version=version,
            discoveryServiceUrl=service_url,
            static_discovery=False,
            credentials=creds,
        )
    )

  def get_classroom_service(self):
    # A Google API Key can be created in your GCP project's Credentials
    # settings: https://console.cloud.google.com/apis/credentials.
    # Click "Create Credentials" at top and choose "API key", then provide
    # the key in the service_url below.
    return self.get_discovery_service(
        CLASSROOM_API_SERVICE_NAME,
        CLASSROOM_API_VERSION,
        service_url=f"https://classroom.googleapis.com/$discovery/rest?key={GOOGLE_API_KEY}",
    )

  def clear_credentials_in_session(self):
    """
    Clears the credentials from the session.
    """

    if "credentials" in flask.session:
      del flask.session["credentials"]
    if "username" in flask.session:
      del flask.session["username"]
    if "login_hint" in flask.session:
      del flask.session["login_hint"]
    if "user_id" in flask.session:
      del flask.session["user_id"]
    self._credentials = None


_credential_handler = CredentialHandler()


@app.route("/start-auth-flow/<redirect_destination>")
def start_auth_flow(redirect_destination):
  """
  Starts the OAuth 2.0 authorization flow. It's important that the
  template be rendered to properly manage popups.
  """

  return flask.render_template(
      "authorization.html", redirect_destination=redirect_destination
  )


def build_flow_instance(redirect_uri, state=None):
  """Builds a Google OAuth 2.0 authorization flow instance.

  Args:
      redirect_uri: The URI to redirect to after authorization.

  Returns:
      A Google OAuth 2.0 authorization flow instance.
  """
  return google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE,
      scopes=SCOPES,
      state=state,
      redirect_uri=flask.url_for(redirect_uri, _external=True),
  )


@app.route("/authorize/<redirect_destination>")
def authorize(redirect_destination):
  """
  Initializes the OAuth flow and redirects to Google's authorization page.
  """

  # Create flow instance to manage the OAuth Authorization Grant Flow steps.

  # The URI created here must exactly match one of the authorized redirect
  # URIs for the OAuth 2.0 client, which you configured in the API Console.
  # If this value doesn't match an authorized URI, you will get a
  # "redirect_uri_mismatch" error.
  flow_instance = build_flow_instance(redirect_destination)

  authorization_url, state = flow_instance.authorization_url(
      # Enable offline access so that you can refresh an access token
      # without re-prompting the user for permission. Recommended for web
      # server apps.
      access_type="offline",
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes="true",
      # The user will automatically be selected if we have the login_hint.
      login_hint=flask.session.get("login_hint"),
  )

  # Store the state so the callback can verify the auth server response.
  flask.session["state"] = state

  # Redirect the user to the OAuth authorization URL.
  return flask.redirect(authorization_url)


@app.route("/clear")
def clear_credentials():
  """
  Clears the credentials from the session.
  """

  _credential_handler.clear_credentials_in_session()

  return flask.render_template("signed-out.html")
