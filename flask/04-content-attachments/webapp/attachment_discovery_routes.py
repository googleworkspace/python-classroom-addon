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
"""Defines all routes for the Flask server."""

from webapp import app
from webapp import credential_handler as ch

import json
import flask
import requests

import google.oauth2.credentials
import googleapiclient.discovery


@app.route("/")
@app.route("/index")
def index():
    """
    Render the index page from the "index.html" template. This is meant to act
    as a facsimile of a company's home page.
    The Add-on Discovery URL should be set to the /classroom-addon route below.
    """

    return flask.render_template(
        "index.html", message="You've reached the index page.")


@app.route("/classroom-addon")
def classroom_addon():
    """
    Checks if a user is signed in. If so, renders the addon discovery page from
    the "addon-discovery.html" template. This is meant to be the landing page
    when opening the web app in the Classroom add-on iframe.
    Otherwise, renders the "authorization.html" template.

    Several GET query parameters can be passed when loading in the Classroom
    iframe. This example handles three additional parameters:
    - postId: The ID of the assignment the add-on is being loaded in.
    - courseId: The ID of the course the add-on is being loaded in.
    - addOnToken: A unique token provided by Classroom.

    The full list of query parameters is available at
    https://developers.google.com/classroom/eap/add-ons-alpha/technical-details/iframes#attachment_discovery_iframe
    """

    # Retrieve the postId, courseId, and addOnToken query parameters.
    if flask.request.args.get("postId"):
        flask.session["postId"] = flask.request.args.get("postId")
    if flask.request.args.get("courseId"):
        flask.session["courseId"] = flask.request.args.get("courseId")
    if flask.request.args.get("addOnToken"):
        flask.session["addOnToken"] = flask.request.args.get("addOnToken")

    # Retrieve the login_hint and hd query parameters.
    login_hint = flask.request.args.get("login_hint")
    hd = flask.request.args.get("hd")

    # It's possible that we might return to this route later, in which case the
    # parameters will not be passed in. Instead, use the values cached in the session.

    # If neither query parameter is available, use the values in the session.
    if login_hint is None and hd is None:
        login_hint = flask.session.get("login_hint")
        hd = flask.session.get("hd")

    # If there's no login_hint query parameter, then check for hd.
    # Send the user to the sign in page.
    elif hd is not None:
        flask.session["hd"] = hd
        return ch.start_auth_flow("discovery_callback")

    # If the login_hint query parameter is available, we'll store it in the session.
    else:
        flask.session["login_hint"] = login_hint

    # Check if we have any stored credentials for this user.
    credentials = ch._credential_handler.get_credentials(login_hint)

    # Redirect to the authorization page if we received login_hint but don't
    # have any stored credentials for this user. We need the refresh token
    # specifically.
    if credentials is None:
        return ch.start_auth_flow("discovery_callback")

    return flask.render_template(
        "addon-discovery.html",
        message="You've reached the addon discovery page.")


@app.route("/test/<request_type>")
def test_api_request(request_type="username"):
    """
    Tests an API request, rendering the result in the
    "show-api-query-result.html" template.

    Args:
        request_type: The type of API request to test. Currently only "username"
        is supported.
    """

    credentials = ch._credential_handler.get_credentials()
    if credentials is None:
        return ch.start_auth_flow("discovery_callback")

    # Create an API client and make an API request.
    fetched_data = ""

    if request_type == "username":
        user_info_service = googleapiclient.discovery.build(
            serviceName="oauth2", version="v2", credentials=credentials)

        flask.session["username"] = (
            user_info_service.userinfo().get().execute().get("name"))

        fetched_data = flask.session.get("username")

    # Save credentials in case access token was refreshed.
    flask.session[
        "credentials"] = ch._credential_handler.session_credentials_to_dict(
            credentials)
    ch._credential_handler.save_credentials_to_storage(credentials)

    # Render the results of the API call.
    return flask.render_template(
        "show-api-query-result.html",
        data=json.dumps(fetched_data, indent=2),
        data_title=request_type)


@app.route("/discovery-callback")
def discovery_callback():
    """
    Runs upon return from the OAuth 2.0 authorization server. Fetches and stores
    the user's credentials, including the access token, refresh token, and
    allowed scopes.
    """

    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    flow = ch.build_flow_instance("discovery_callback", flask.session["state"])

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    credentials = flow.credentials
    flask.session[
        "credentials"] = ch._credential_handler.session_credentials_to_dict(
            credentials)

    # The flow is complete!
    # Add the credentials to our persistent storage.
    # We'll extract the "id" value from the credentials to use as a key.
    # This is the user's unique Google ID, and will match the login_hint
    # query parameter in the future.

    # If we've reached this point, and there is already a record in our
    # database for this user, they must be obtaining new credentials;
    # update the stored credentials.
    ch._credential_handler.save_credentials_to_storage(credentials)

    return flask.render_template(
        "close-me.html", redirect_destination="classroom_addon")


@app.route("/revoke")
def revoke():
    """
    Revokes the logged in user's credentials.
    """

    if "credentials" not in flask.session:
        return flask.render_template(
            "addon-discovery.html",
            message="You need to authorize before " +
            "attempting to revoke credentials.")

    credentials = google.oauth2.credentials.Credentials(
        **flask.session["credentials"])

    revoke = requests.post(
        "https://oauth2.googleapis.com/revoke",
        params={"token": credentials.token},
        headers={"content-type": "application/x-www-form-urlencoded"})

    ch._credential_handler.clear_credentials_in_session()

    status_code = getattr(revoke, "status_code")
    if status_code == 200:
        return ch.start_auth_flow("discovery_callback")
    else:
        return flask.render_template(
            "addon-discovery.html",
            message="An error occurred during revocation!")
