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
import flask


@app.route("/")
def index():
    """
    Render the index page from the "index.html" template. This is meant to act
    as a facsimile of a company's home page. The Add-on Discovery URL should be
    set to the /classroom-addon route below.
    """

    return flask.render_template(
        "index.html", message="You've reached the index page.")


@app.route("/classroom-addon")
def classroom_addon():
    """
    Renders the addon discovery page from the "addon-discovery.html" template.
    This is meant to be the landing page when opening the web app in the
    Classroom add-on iframe.
    """

    return flask.render_template(
        "addon-discovery.html",
        message="You've reached the addon discovery page.")