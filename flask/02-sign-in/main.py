# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import flask
import requests
import json

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

app = flask.Flask(__name__)

# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See https://flask.palletsprojects.com/quickstart/#sessions.
app.secret_key = "REPLACE ME - this value is here as a placeholder."

# Configure the flask cookie settings per the iframe security recommendations:
# https://developers.google.com/classroom/eap/add-ons-alpha/iframes#iframe_security_guidelines
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
)

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
# These scopes should match the scopes in your GCP project's
# OAuth Consent Screen: https://console.cloud.google.com/apis/credentials/consent
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email"
]


@app.route("/")
def index():
    """
    Render the index page from the "index.html" template. This is meant to act
    as a facsimile of a company's home page.
    The Add-on Discovery URL should be set to the /classroom-addon route below.
    """

    return flask.render_template("index.html",
                                 message="You've reached the index page.")


@app.route("/classroom-addon")
def classroom_addon():
    """
    Checks if a user is signed in. If so, renders the addon discovery page from
    the "addon-discovery.html" template. This is meant to be the landing page
    when opening the web app in the Classroom add-on iframe.
    Otherwise, renders the "authorization.html" template.
    """

    if "credentials" not in flask.session:
        return flask.render_template("authorization.html")

    return flask.render_template(
        "addon-discovery.html",
        message="You've reached the addon discovery page.")


@app.route("/test/<request_type>")
def test_api_request(request_type="username"):
    """
    Tests an API request, rendering the result in the "show-api-query-result.html" template.

    Args:
        request_type: The type of API request to test. Currently only "username" is supported.
    """

    if "credentials" not in flask.session:
        return flask.render_template("authorization.html")

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **flask.session["credentials"])

    # Create an API client and make an API request.
    fetched_data = ""

    if request_type == "username":
        if not flask.session.get("username"):
            user_info_service = googleapiclient.discovery.build(
                serviceName="oauth2", version="v2", credentials=credentials)

            flask.session["username"] = (
                user_info_service.userinfo().get().execute().get("name"))

        fetched_data = flask.session.get("username")

    # Save credentials back to session in case access token was refreshed.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    flask.session["credentials"] = credentials_to_dict(credentials)

    # Render the results of the API call.
    return flask.render_template(
        "show-api-query-result.html",
        data=json.dumps(fetched_data, indent=2),  #flask.jsonify(courses),
        data_title=request_type)


@app.route("/authorize")
def authorize():
    """
    Initializes the OAuth flow and redirects to Google's authorization page.
    """

    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a "redirect_uri_mismatch"
    # error.
    flow.redirect_uri = flask.url_for("callback", _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type="offline",
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes="true")

    # Store the state so the callback can verify the auth server response.
    flask.session["state"] = state

    # Redirect the user to the OAuth authorization URL.
    return flask.redirect(authorization_url)


@app.route("/callback")
def callback():
    """
    Runs upon return from the OAuth 2.0 authorization server. Fetches and stores
    the user's credentials, including the access token, refresh token, and allowed scopes.
    """

    # Specify the state when creating the flow in the callback so that it can be
    # verified in the authorization server response.
    state = flask.session["state"]

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for("callback", _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    flask.session["credentials"] = credentials_to_dict(credentials)

    # The flow is complete! We'll use the credentials to fetch the username.
    user_info_service = googleapiclient.discovery.build(
        serviceName="oauth2", version="v2", credentials=credentials)

    flask.session["username"] = (
        user_info_service.userinfo().get().execute().get("name"))

    return flask.render_template("close-me.html")


@app.route("/revoke")
def revoke():
    """
    Revokes the logged in user's credentials.
    """

    if "credentials" not in flask.session:
        return flask.render_template("addon-discovery.html",
                                     message="You need to authorize before " +
                                     "attempting to revoke credentials.")

    credentials = google.oauth2.credentials.Credentials(
        **flask.session["credentials"])

    revoke = requests.post(
        "https://oauth2.googleapis.com/revoke",
        params={"token": credentials.token},
        headers={"content-type": "application/x-www-form-urlencoded"})

    clear_credentials_in_session()

    status_code = getattr(revoke, "status_code")
    if status_code == 200:
        return flask.render_template("authorization.html")
    else:
        return flask.render_template(
            "index.html", message="An error occurred during revocation!")


@app.route("/clear")
def clear_credentials():
    """
    Clears the credentials from the session.
    """

    clear_credentials_in_session()

    return flask.render_template("signed-out.html")


def clear_credentials_in_session():
    """
    Clears the credentials from the session.
    """

    if "credentials" in flask.session:
        del flask.session["credentials"]
        del flask.session["username"]

    flask.session.clear()


def credentials_to_dict(credentials):
    """
    Returns a dictionary from a credentials object.
    """

    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }


if __name__ == "__main__":
    # Allow the OAuth flow to adjust scopes.
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

    # You have several options for running the web server.

    ### OPTION 1: Unsecured localhost
    # When running locally on unsecured HTTP, use this line to disable
    # OAuthlib's HTTPs verification.
    # Important: When running in production *do not* leave this option enabled.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Run the application on a local server, defaults to http://localhost:5000.
    # Note: the OAuth flow requires a TLD, *not* an IP address; "localhost" is
    #   acceptable, but http://127.0.0.1 is not.
    app.run(debug=True)

    ### OPTION 2: Secure localhost
    # Run the application over HTTPs with a locally stored certificate and key.
    # Defaults to https://localhost:5000.
    # app.run(host="localhost",
    #         ssl_context=("localhost.pem", "localhost-key.pem"),
    #         debug=True)

    ### OPTION 3: Production- or cloud-ready server
    # Start a Gunicorn server, which is appropriate for use in
    # production or a cloud deployment.
    # server_port = os.environ.get("PORT", "8080")
    # app.run(debug=True, port=server_port, host="0.0.0.0")
