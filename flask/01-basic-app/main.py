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

Loads the webapp module and starts the server."""

from webapp import app
import os

if __name__ == "__main__":
    # You have several options for running the web server.

    ### OPTION 1: Unsecured localhost
    # When running locally on unsecured HTTP, use this line to disable
    # OAuthlib's HTTPs verification.

    # Important: When running in production *do not* leave this option enabled.
    # os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Run the application on a local server, defaults to http://localhost:5000.
    # Note: the OAuth flow requires a TLD, *not* an IP address; "localhost" is
    # acceptable, but http://127.0.0.1 is not.
    # app.run(debug=True)

    ### OPTION 2: Secure localhost
    # Run the application over HTTPs with a locally stored certificate and key.
    # Defaults to https://localhost:5000.
    app.run(
        host="localhost",
        ssl_context=("localhost.pem", "localhost-key.pem"),
        debug=True)

    ### OPTION 3: Production- or cloud-ready server
    # Start a Gunicorn server, which is appropriate for use in production or a
    # cloud deployment.
    # server_port = os.environ.get("PORT", "8080")
    # app.run(debug=True, port=server_port, host="0.0.0.0")