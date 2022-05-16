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
"""Entry point for the Flask server.

Loads the webapp module and starts the server. Choose an appropriate launch
method below before running this program.

WARNING: NOT FOR PRODUCTION
----------------------------
This is a sample application for development purposes. You should follow
best practices when securing your production application and in particular
how you securely store and use OAuth tokens.

Note that storing tokens in the session is for demonstration purposes. Be sure
to store your tokens securely in your production application.

Review these resources for additional security considerations:
+ Google Identity developer website: https://developers.google.com/identity
+ OAuth 2.0 Security Best Current Practice:
  https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics
+ OAuth 2.0 Threat Model and Security Considerations:
  https://datatracker.ietf.org/doc/html/rfc6819"""

from webapp import app
import os

if __name__ == "__main__":
    # You have several options for running the web server.

    ### OPTION 1: Unsecured localhost
    # When running locally on unsecured HTTP, use this line to disable
    # OAuthlib's HTTPs verification.

    # Important: When running in production *do not* leave this option enabled.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Run the application on a local server, defaults to http://localhost:5000.
    # Note: the OAuth flow requires a TLD, *not* an IP address; "localhost" is
    # acceptable, but http://127.0.0.1 is not.
    app.run(debug=True)

    ### OPTION 2: Secure localhost
    # Run the application over HTTPs with a locally stored certificate and key.
    # Defaults to https://localhost:5000.
    # app.run(
    #     host="localhost",
    #     ssl_context=("localhost.pem", "localhost-key.pem"),
    #     debug=True)

    ### OPTION 3: Production- or cloud-ready server
    # Start a Gunicorn server, which is appropriate for use in production or a
    # cloud deployment.
    # server_port = os.environ.get("PORT", "8080")
    # app.run(debug=True, port=server_port, host="0.0.0.0")
