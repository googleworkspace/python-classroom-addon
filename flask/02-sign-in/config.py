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
"""The Flask server configuration."""

import os


class Config(object):
  # Note: A secret key is included in the sample so that it works.
  # If you use this code in your application, replace this with a truly secret
  # key. See https://flask.palletsprojects.com/quickstart/#sessions.
  SECRET_KEY = (
      os.environ.get("SECRET_KEY")
      or "REPLACE ME - this value is here as a placeholder."
  )

  # Configure the flask cookie settings per the iframe security recommendations:
  # https://developers.google.com/classroom/add-ons/developer-guides/iframes#iframe_security_guidelines
  SESSION_COOKIE_SECURE = True
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SAMESITE = "None"
