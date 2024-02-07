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
"""Defines routes that handle attachments for the Flask server."""

from webapp import app
from webapp.models import Attachment, Submission
from webapp import db
from webapp import credential_handler as ch

from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField, StringField
from wtforms.validators import DataRequired

import os
import flask
import pprint

# This example demonstrates grade passback at two different moments.
# Set this value to True to pass back grades when the teacher opens the Student
# Work Review iframe.
# Set this value to False to pass back grades when the student submits the
# activity.
SET_GRADE_WITH_LOGGED_IN_USER_CREDENTIALS = False


def image_list_form_builder(image_filenames):
  """Builds a form composed of checkboxes and captions.

  This has to be done dynamically since FieldList doesn't support checkboxes:
  https://wtforms.readthedocs.io/en/2.3.x/fields/#wtforms.fields.FieldList

  Args:
      image_filenames: A list of image filenames.
  Returns:
      A FlaskForm object with a series of checkboxes and the attribute names
      assigned to them.
  """

  class ImageListForm(FlaskForm):
    pass

  name_pairs = []

  # For this example, images have the format "landmark-name.type".
  image_captions = [
      x.split(".")[0].replace("-", " ").title() for x in image_filenames
  ]

  # Add a checkbox for each image to the form, named by the image filename.
  for i in range(len(image_filenames)):
    setattr(
        ImageListForm,
        f"selected_{i}",
        BooleanField(label=image_captions[i], name=image_filenames[i]),
    )
    name_pairs.append(f"selected_{i}")

  # Add a submit button to the form.
  setattr(ImageListForm, "submit", SubmitField("Submit"))
  return ImageListForm(), name_pairs


def construct_filename_caption_dictionary_list(form):
  """
  Construct a dictionary that maps filenames to captions.

  There will be one dictionary entry per checked item in the form.

  Args:
      form: A completed, validated form.
  Returns:
      A dictionary that maps image filenames to captions.
  """

  selected_images = [
      key
      for key, value in form.data.items()
      if value is True and key != "submit"
  ]

  filename_caption_pairs = {
      form[image_id].name: form[image_id].label.text
      for image_id in selected_images
  }

  return filename_caption_pairs


def activity_form_builder():
  """
  Builds a form for the activity with a String input field and submit button.
  """

  class ActivityForm(FlaskForm):
    student_response = StringField("Your response", [DataRequired()])
    submit = SubmitField("Submit")

  return ActivityForm()


@app.route("/attachment-options", methods=["GET", "POST"])
def attachment_options():
  """
  Render the attachment options page from the "attachment-options.html"
  template.

  This page displays a grid of images that the user can select using
  checkboxes.
  """

  # A list of the filenames in the static/images directory.
  image_filenames = os.listdir(os.path.join(app.static_folder, "images"))

  # Create a form from the list of images. Store the list of attribute names
  # in the form.
  form, var_names = image_list_form_builder(image_filenames)

  # If the form was submitted, validate the input and create the attachments.
  if form.validate_on_submit():
    filename_caption_pairs = construct_filename_caption_dictionary_list(form)

    if len(filename_caption_pairs) > 0:
      return create_attachments(filename_caption_pairs)
    else:
      return flask.render_template(
          "create-attachment.html",
          message="You didn't select any images.",
          form=form,
          var_names=var_names,
      )

  return flask.render_template(
      "attachment-options.html",
      message=(
          "You've reached the attachment options page. "
          "Select one or more images and click 'Create Attachment'."
      ),
      form=form,
      var_names=var_names,
  )


def create_attachments(filename_caption_pairs):
  """
  Create attachments and show an acknowledgement page.

  Args:
      filename_caption_pairs: A dictionary that maps image filenames to
          captions.
  """
  # Get the Google Classroom service.
  classroom_service = ch._credential_handler.get_classroom_service()

  response_strings = []
  request_strings = []

  # Create a new attachment for each image that was selected.
  attachment_count = 0
  for key, value in filename_caption_pairs.items():
    attachment_count += 1
    attachment = {
        # Specifies the route for a teacher user.
        "teacherViewUri": {
            "uri": flask.url_for(
                "load_activity_attachment", _scheme="https", _external=True
            ),
        },
        # Specifies the route for a student user.
        "studentViewUri": {
            "uri": flask.url_for(
                "load_activity_attachment", _scheme="https", _external=True
            )
        },
        # Specifies the route for a teacher user when the attachment is
        # loaded in the Classroom grading view.
        "studentWorkReviewUri": {
            "uri": flask.url_for(
                "view_submission", _scheme="https", _external=True
            )
        },
        # Sets the maximum points that a student can earn for this activity.
        # This is the denominator in a fractional representation of a grade.
        "maxPoints": 50,
        # The title of the attachment.
        "title": f"Attachment {attachment_count}",
    }

    request_strings.append(pprint.pformat(attachment))

    # Issue a request to create the attachment on an assignment.
    resp = (
        classroom_service.courses()
        .courseWork()
        .addOnAttachments()
        .create(
            courseId=flask.session["courseId"],
            itemId=flask.session["itemId"],
            addOnToken=flask.session["addOnToken"],
            body=attachment,
        )
        .execute()
    )

    response_strings.append(pprint.pformat(resp))

    # Store the value by id.
    new_attachment = Attachment(
        # The new attachment's unique ID, returned in the CREATE response.
        attachment_id=resp.get("id"),
        image_filename=key,
        image_caption=value,
        max_points=int(resp.get("maxPoints")),
        teacher_id=flask.session["login_hint"],
    )
    db.session.add(new_attachment)
    db.session.commit()

  return flask.render_template(
      "create-attachment.html",
      message=(
          "You've reached the create attachment page.\n\n"
          f"I created {attachment_count} attachments."
      ),
      requests=request_strings,
      responses=response_strings,
  )


def add_iframe_query_parameters_to_session(args):
  """
  Extract the identifiers passed to the iframe as query parameters.

  Args:
      args: The dictionary of query parameters passed to the iframe.
  """

  if args.get("itemId"):
    flask.session["itemId"] = args.get("itemId")
  if args.get("itemType"):
    flask.session["itemType"] = args.get("itemType")
  if args.get("courseId"):
    flask.session["courseId"] = args.get("courseId")
  if args.get("addOnToken"):
    flask.session["addOnToken"] = args.get("addOnToken")
  if args.get("attachmentId"):
    flask.session["attachmentId"] = args.get("attachmentId")
  if args.get("submissionId"):
    flask.session["submissionId"] = args.get("submissionId")
  if args.get("login_hint"):
    flask.session["login_hint"] = args.get("login_hint")


@app.route("/load-activity-attachment", methods=["GET", "POST"])
def load_activity_attachment():
  """
  Render an activity attachment from the "show-activity-attachment.html"
  template.
  """

  # Save the query parameters passed to the iframe in the session.
  add_iframe_query_parameters_to_session(flask.request.args)

  # Redirect to the authorization page if we received login_hint but don't
  # have any stored credentials for this user.
  credentials = ch.check_login_query_parameters(flask.request.args)
  if credentials is None:
    return ch.start_auth_flow("attachment_callback")

  # Look up the attachment in the database.
  attachment = Attachment.query.get(flask.session["attachmentId"])

  # Create an instance of the Classroom service.
  classroom_service = ch._credential_handler.get_classroom_service()

  addon_context_response = (
      classroom_service.courses()
      .courseWork()
      .getAddOnContext(
          courseId=flask.session["courseId"], itemId=flask.session["itemId"]
      )
      .execute()
  )

  response_strings = [pprint.pformat(addon_context_response)]
  request_strings = []

  # Determine which view we are in by testing the returned context type.
  user_context = (
      "student" if addon_context_response.get("studentContext") else "teacher"
  )

  message_str = f"I see that you are a {user_context}! "

  # If the user is a teacher, we can fetch information about the attachment.
  if user_context == "teacher":
    attachment_response = (
        classroom_service.courses()
        .courseWork()
        .addOnAttachments()
        .get(
            courseId=flask.session["courseId"],
            itemId=flask.session["itemId"],
            attachmentId=flask.session["attachmentId"],
        )
        .execute()
    )

    response_strings.append(pprint.pformat(attachment_response))

    message_str += (
        f"I've loaded the attachment with ID {attachment.attachment_id}."
    )

  # If the user is a student, get their submission status for this attachment.
  # Note that the submissionId was returned in the addOnContext response.
  else:
    flask.session["submissionId"] = addon_context_response.get(
        "studentContext"
    ).get("submissionId")

    submission_response = (
        classroom_service.courses()
        .courseWork()
        .addOnAttachments()
        .studentSubmissions()
        .get(
            courseId=flask.session["courseId"],
            itemId=flask.session["itemId"],
            attachmentId=flask.session["attachmentId"],
            submissionId=flask.session["submissionId"],
        )
        .execute()
    )

    response_strings.append(pprint.pformat(submission_response))

    if submission_response.get("postSubmissionState") == "TURNED_IN":
      message_str += "You have already turned in this activity."
    else:
      message_str += "Please complete the activity below."

  # Build the activity form.
  form = activity_form_builder()

  if form.validate_on_submit():
    # Check if the student has already submitted a response.
    # If so, update the response stored in the database.
    student_submission = Submission.query.get(
        (flask.session["submissionId"], flask.session["attachmentId"])
    )

    if student_submission is not None:
      student_submission.student_response = form.student_response.data
    else:
      # Store the student's response by the submission ID.
      new_submission = Submission(
          submission_id=flask.session["submissionId"],
          attachment_id=flask.session["attachmentId"],
          student_response=form.student_response.data,
      )
      db.session.add(new_submission)

    db.session.commit()

    if not SET_GRADE_WITH_LOGGED_IN_USER_CREDENTIALS:
      # Pass back a grade when the student completes the activity.
      # Note that this is one of two moments in which you can pass back a
      # grade; while this moment requires more implementation work, it
      # does provide the most "correct" feeling experience to end users.
      # See details in our walkthrough guide page:
      # https://developers.google.com/classroom/add-ons/walkthroughs/grade-passback
      grade = 0

      # See if the student response matches the stored name.
      if form.student_response.data.lower() == attachment.image_caption.lower():
        grade = attachment.max_points

      # Only a teacher can set the attachment's grade; since the currently
      # logged in user is a student, we'll need to retrieve the teacher's
      # credentials.

      # Create an instance of the Classroom service using the refresh
      # token for the teacher that created the attachment.
      teacher_classroom_service = (
          ch._credential_handler.get_classroom_service_for_user(
              attachment.teacher_id
          )
      )

      # Build an AddOnAttachmentStudentSubmission instance.
      add_on_attachment_student_submission = {
          # Specifies the student's score for this attachment.
          "pointsEarned": grade,
      }

      request_strings.append(
          pprint.pformat(add_on_attachment_student_submission)
      )

      # Issue a PATCH request as the teacher to set the grade numerator
      # for this attachment.
      patch_grade_response = (
          teacher_classroom_service.courses()
          .courseWork()
          .addOnAttachments()
          .studentSubmissions()
          .patch(
              courseId=flask.session["courseId"],
              itemId=flask.session["itemId"],
              attachmentId=flask.session["attachmentId"],
              submissionId=flask.session["submissionId"],
              # updateMask is a list of fields being modified.
              updateMask="pointsEarned",
              body=add_on_attachment_student_submission,
          )
          .execute()
      )

      response_strings.append(pprint.pformat(patch_grade_response))

    return flask.render_template(
        "acknowledge-submission.html",
        message="Your response has been recorded. You can close the "
        "iframe now.",
        instructions="Please Turn In your assignment if you have "
        "completed all tasks.",
    )

  # Show the activity. Disable the submission button if the user is a teacher.
  return flask.render_template(
      "show-activity-attachment.html",
      message=message_str,
      image_filename=attachment.image_filename,
      image_caption=attachment.image_caption,
      user_context=user_context,
      form=form,
      requests=request_strings,
      responses=response_strings,
  )


@app.route("/attachment-callback")
def attachment_callback():
  """
  Runs upon return from the OAuth 2.0 authorization server. Fetches and stores
  the user's credentials, including the access token, refresh token, and
  allowed scopes.
  """

  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
  flow = ch.build_flow_instance("attachment_callback", flask.session["state"])

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  credentials = flow.credentials
  flask.session["credentials"] = ch.credentials_to_dict(credentials)

  # Add or update the user's record in the database.
  ch._credential_handler.save_credentials_to_storage(credentials)

  return flask.render_template(
      "close-me.html", redirect_destination="load_activity_attachment"
  )


@app.route("/view-submission")
def view_submission():
  """
  Render a student submission using the show-student-submission.html template.
  """

  # Save the query parameters passed to the iframe in the session.
  add_iframe_query_parameters_to_session(flask.request.args)

  # For the sake of brevity in this example, we'll skip the conditional logic
  # to see if we need to authorize the user as we have done in previous steps.
  # We can assume that the user that reaches this route is a teacher that has
  # already authorized and created an attachment using the add-on.

  # In production, we recommend fully validating the user's authorization at
  # this stage as well.

  # Look up the student's submission in our database.
  student_submission = Submission.query.get(
      (flask.session["submissionId"], flask.session["attachmentId"])
  )

  # Look up the attachment in the database.
  attachment = Attachment.query.get(student_submission.attachment_id)

  # Show a message if the student has not yet submitted a response.
  if student_submission is None:
    return flask.render_template(
        "acknowledge-submission.html",
        message="This student has not yet submitted a response.",
        student_response="N/A",
        correct_answer=attachment.image_caption,
    )

  response_strings = []
  request_strings = []

  if SET_GRADE_WITH_LOGGED_IN_USER_CREDENTIALS:
    # Pass back a grade when opened in the Student Work Review iframe.
    # Note that this is one of two moments in which you can pass back a
    # grade; while this moment is easier to implement, it does have user
    # experience considerations. See details in our walkthrough guide page:
    # https://developers.google.com/classroom/add-ons/walkthroughs/grade-passback
    grade = 0

    # See if the student response matches the stored name.
    if (
        student_submission.student_response.lower()
        == attachment.image_caption.lower()
    ):
      grade = attachment.max_points

    # Create an instance of the Classroom service.
    classroom_service = ch._credential_handler.get_classroom_service()

    # Build an AddOnAttachmentStudentSubmission instance.
    add_on_attachment_student_submission = {
        # Specifies the student's score for this attachment.
        "pointsEarned": grade,
    }

    request_strings.append(pprint.pformat(add_on_attachment_student_submission))

    # Issue a PATCH request to set the grade numerator for this attachment.
    patch_grade_response = (
        classroom_service.courses()
        .courseWork()
        .addOnAttachments()
        .studentSubmissions()
        .patch(
            courseId=flask.session["courseId"],
            itemId=flask.session["itemId"],
            attachmentId=flask.session["attachmentId"],
            submissionId=flask.session["submissionId"],
            # updateMask is a list of fields being modified.
            updateMask="pointsEarned",
            body=add_on_attachment_student_submission,
        )
        .execute()
    )

    response_strings.append(pprint.pformat(patch_grade_response))

  # Render the student's response alongside the correct answer.
  return flask.render_template(
      "show-student-submission.html",
      message=f"Loaded submission {student_submission.submission_id} for "
      f"attachment {attachment.attachment_id}.",
      student_response=student_submission.student_response,
      correct_answer=attachment.image_caption,
      requests=request_strings,
      responses=response_strings,
  )
