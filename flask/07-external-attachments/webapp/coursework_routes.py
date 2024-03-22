#!/usr/bin/env python3
# Copyright 2024 Google LLC
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
"""Defines CourseWork-related routes for the Flask server."""

from webapp import app
from webapp import credential_handler as ch

import flask
import pprint


@app.route("/create-coursework-assignment")
def create_coursework_assignment():
  """
  Completes the assignment creation flow, then renders
  "coursework-assignment-created.html".

  The logic follows the suggested flow in our guide to creating attachments outside of
  Classroom: https://developers.google.com/classroom/add-ons/developer-guides/third-party-first-journey#workflow
  """
  # Check that the user is signed in.
  credentials = ch._credential_handler.get_credentials()

  if not credentials:
    return ch.start_auth_flow("coursework_assignment_callback")

  # Get the Google Classroom service.
  classroom_service = ch._credential_handler.get_classroom_service()

  request_strings = []
  response_strings = []
  assignment_type = ""

  # The ID of the course to which the assignment will be added.
  # Ordinarily, you'll prompt the user to specify which course to use. For simplicity,
  # we use a hard-coded value in this example.
  course_id = 1234567890  # TODO(developer) Replace with an actual course ID.

  # Check whether the user can create add-on attachments.
  eligibility_response = (
      classroom_service.courses()
      .checkAddOnCreationEligibility(courseId=course_id)
      .execute()
  )
  is_create_attachment_eligible = eligibility_response.get("isCreateAttachmentEligible")

  request_strings.append(f"checkAddOnCreationEligibility courseId:{course_id}")
  response_strings.append(pprint.pformat(eligibility_response))

  # If the user can't create add-on attachments, create a CourseWork assignment with the
  # URL to the selected content as a Link Material.
  if not is_create_attachment_eligible:
    coursework = {
        "title": "My CourseWork Assignment with Link Material",
        "description": "Created using the Classroom CourseWork API.",
        "workType": "ASSIGNMENT",
        "state": "DRAFT",  # Set to 'PUBLISHED' to assign to students.
        "materials": [
            {
                "link": {
                    "url": flask.url_for(
                        "example_coursework_assignment",
                        assignment_type="link-material",
                        _scheme="https",
                        _external=True,
                    )
                }
            }
        ],
    }

    assignment_response = (
        classroom_service.courses()
        .courseWork()
        .create(courseId=course_id, body=coursework)
        .execute()
    )

    request_strings.append(pprint.pformat(coursework))
    response_strings.append(pprint.pformat(assignment_response))
    assignment_type = "link-material"

  else:
    # If the user can create add-on attachments, do the following:
    # Create an assignment.
    coursework = {
        "title": "My CourseWork Assignment with Add-on Attachment",
        "description": "Created using the Classroom CourseWork API.",
        "workType": "ASSIGNMENT",
        "state": "DRAFT",  # Set to 'PUBLISHED' to assign to students.
    }

    assignment_response = (
        classroom_service.courses()
        .courseWork()
        .create(courseId=course_id, body=coursework)
        .execute()
    )

    request_strings.append(pprint.pformat(coursework))
    response_strings.append(pprint.pformat(assignment_response))

    # Create an add-on attachment that links to the selected content and associate it
    # with the new assignment.
    content_url = flask.url_for(
        "example_coursework_assignment",
        assignment_type="add-on-attachment",
        _scheme="https",
        _external=True,
    )
    attachment = {
        "teacherViewUri": {"uri": content_url},
        "studentViewUri": {"uri": content_url},
        "title": f'Test Attachment for Assignment {assignment_response.get("id")}',
    }

    add_on_attachment_response = (
        classroom_service.courses()
        .courseWork()
        .addOnAttachments()
        .create(
            courseId=course_id,
            itemId=assignment_response.get("id"),  # ID of the new assignment.
            body=attachment,
        )
        .execute()
    )

    request_strings.append(pprint.pformat(attachment))
    response_strings.append(pprint.pformat(add_on_attachment_response))

    assignment_type = "add-on attachment"

  # Inform the teacher that the assignment has been created successfully.
  return flask.render_template(
      "coursework-assignment-created.html",
      assignment_type=assignment_type,
      request_strings=request_strings,
      response_strings=response_strings,
  )


@app.route("/modify-coursework-assignment")
def modify_coursework_assignment():
  """
  Alters the title on an existing CourseWork assignment.
  """

  # Check that the user is signed in.
  credentials = ch._credential_handler.get_credentials()

  if not credentials:
    return ch.start_auth_flow("coursework_assignment_callback")

  # Get the Google Classroom service.
  classroom_service = ch._credential_handler.get_classroom_service()

  response_strings = []

  # The ID of the course to which the assignment will be added.
  # Ordinarily, you'll prompt the user to specify which course to use. For simplicity,
  # we use a hard-coded value in this example.
  course_id = 1234567890  # TODO(developer) Replace with an actual course ID.
  coursework_id = 1234567890  # TODO(developer) Replace with an actual assignment ID.

  get_coursework_response = (
      classroom_service.courses()
      .courseWork()
      .get(courseId=course_id, id=coursework_id)
      .execute()
  )

  assignment_title = f"(Modified by API request) {get_coursework_response.get('title')}"

  modify_coursework_response = (
      classroom_service.courses()
      .courseWork()
      .patch(
          courseId=course_id,
          id=coursework_id,
          updateMask="title",
          body={"title": assignment_title},
      )
      .execute()
  )

  response_strings.append(pprint.pformat(get_coursework_response))
  response_strings.append(pprint.pformat(modify_coursework_response))

  return flask.render_template(
      "coursework-modified.html",
      assignment_title=modify_coursework_response.get("title"),
      response_strings=response_strings,
  )


@app.route("/coursework-assignment-callback")
def coursework_assignment_callback():
  flow = ch.build_flow_instance(
      "coursework_assignment_callback", flask.session["state"]
  )

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  credentials = flow.credentials
  flask.session["credentials"] = ch._credential_handler.session_credentials_to_dict(
      credentials
  )

  ch._credential_handler.save_credentials_to_storage(credentials)

  return flask.render_template("close-me.html", redirect_destination="index")


@app.route("/example-coursework-assignment/<assignment_type>")
def example_coursework_assignment(assignment_type):
  """
  Renders the "example-coursework-assignment.html" template. This page is used to
  demonstrate the creation of a CourseWork assignment, and will show the attachment type
  that links to it.
  """
  return flask.render_template(
      "example-coursework-assignment.html", assignment_type=assignment_type
  )
