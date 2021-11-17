# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import flask
import os

app = flask.Flask(__name__)

# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See https://flask.palletsprojects.com/quickstart/#sessions.
app.secret_key = "REPLACE ME - this value is here as a placeholder."


@app.route("/")
def index():
    return flask.render_template("index.html", message="Welcome!")


@app.route("/authorize")
def authorize():
    # Set the username to test the navigation bar.
    flask.session["username"] = "Test Username"

    return flask.render_template("index.html",
                                 message="Test username stored in session.")


@app.route("/clear")
def clear_credentials():
    flask.session.clear()

    return flask.render_template("index.html", message="Session cleared.")


if __name__ == "__main__":
    # You have several options for running the web server.

    ### OPTION 1: Unsecured localhost
    # When running locally on unsecured HTTP, use this line to disable
    # OAuthlib's HTTPs verification.
    # Important: When running in production *do not* leave this option enabled.
    # os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Run the application on a local server, defaults to http://localhost:5000.
    # Note: the OAuth flow requires a TLD, *not* an IP address; "localhost" is
    #   acceptable, but http://127.0.0.1 is not.
    # app.run(debug=True)

    ### OPTION 2: Secure localhost
    # Run the application over HTTPs with a locally stored certificate and key.
    # Defaults to https://localhost:5000.
    app.run(host="localhost",
            ssl_context=("localhost.pem", "localhost-key.pem"),
            debug=True)

    ### OPTION 3: Production- or cloud-ready server
    # Start a Gunicorn server, which is appropriate for use in
    # production or a cloud deployment.
    # server_port = os.environ.get("PORT", "8080")
    # app.run(debug=True, port=server_port, host="0.0.0.0")