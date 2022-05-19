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
from webapp.models import Attachment
from webapp import db
from webapp import credential_handler as ch

from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField

import os
import flask
import pprint


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
        setattr(ImageListForm, f"selected_{i}",
                BooleanField(label=image_captions[i], name=image_filenames[i]))
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
        key for key, value in form.data.items()
        if value is True and key != "submit"
    ]

    filename_caption_pairs = {
        form[image_id].name: form[image_id].label.text
        for image_id in selected_images
    }

    return filename_caption_pairs


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

        filename_caption_pairs = construct_filename_caption_dictionary_list(
            form)

        if len(filename_caption_pairs) > 0:
            return create_attachments(filename_caption_pairs)
        else:
            return flask.render_template(
                "create-attachment.html",
                message="You didn't select any images.",
                form=form,
                var_names=var_names)

    return flask.render_template(
        "attachment-options.html",
        message=("You've reached the attachment options page. "
                 "Select one or more images and click 'Create Attachment'."),
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
                "uri":
                    flask.url_for(
                        "load_attachment", _scheme='https', _external=True),
            },
            # Specifies the route for a student user.
            "studentViewUri": {
                "uri":
                    flask.url_for(
                        "load_attachment", _scheme='https', _external=True)
            },
            # The title of the attachment.
            "title": f"Attachment {attachment_count}",
        }

        request_strings.append(pprint.pformat(attachment))

        # Issue a request to create the attachment.
        resp = classroom_service.courses().posts().addOnAttachments().create(
            courseId=flask.session["courseId"],
            postId=flask.session["postId"],
            addOnToken=flask.session["addOnToken"],
            body=attachment).execute()

        response_strings.append(pprint.pformat(resp))

        # Store the value by id.
        new_attachment = Attachment(
            # The new attachment's unique ID, returned in the CREATE response.
            attachment_id=resp.get("id"),
            image_filename=key,
            image_caption=value)
        db.session.add(new_attachment)
        db.session.commit()

    return flask.render_template(
        "create-attachment.html",
        message=("You've reached the create attachment page.\n\n"
                 f"I created {attachment_count} attachments."),
        requests=request_strings,
        responses=response_strings)


@app.route("/load-attachment")
def load_attachment():
    """
    Load the attachment for the user's role."""

    if flask.request.args.get("postId"):
        flask.session["postId"] = flask.request.args.get("postId")
    if flask.request.args.get("courseId"):
        flask.session["courseId"] = flask.request.args.get("courseId")
    if flask.request.args.get("attachmentId"):
        flask.session["attachmentId"] = flask.request.args.get("attachmentId")

    # Retrieve the login_hint and hd query parameters.
    hd = flask.request.args.get("hd")

    # Check if hd is provided. If so, send the user to the sign in page.
    if hd is not None:
        flask.session["hd"] = hd
        return ch.start_auth_flow("attachment_callback")

    # If the login_hint query parameter is available, store it in the session.
    else:
        flask.session["login_hint"] = flask.request.args.get("login_hint")

    # Redirect to the authorization page if we received login_hint but don't
    # have any stored credentials for this user. We need the refresh token
    # specifically.
    credentials = ch._credential_handler.get_credentials(
        flask.session["login_hint"])
    if credentials is None:
        return ch.start_auth_flow("attachment_callback")

    # Create an instance of the Classroom service.
    classroom_service = ch._credential_handler.get_classroom_service()

    addon_context_response = classroom_service.courses().posts(
    ).getAddOnContext(
        courseId=flask.session["courseId"],
        postId=flask.session["postId"]).execute()

    response_strings = [pprint.pformat(addon_context_response)]

    # Determine which view we are in by testing the returned context type.
    user_context = "student" if addon_context_response.get(
        "studentContext") else "teacher"

    if user_context == "teacher":
        attachment_response = classroom_service.courses().posts(
        ).addOnAttachments().get(
            courseId=flask.session["courseId"],
            postId=flask.session["postId"],
            attachmentId=flask.session["attachmentId"]).execute()

        response_strings.append(pprint.pformat(attachment_response))

    # Look up the attachment in the database.
    attachment = Attachment.query.get(flask.session["attachmentId"])

    message_str = f"I see that you are a {user_context}! "
    message_str += (
        f"I've loaded the attachment with ID {attachment.attachment_id}. "
        if user_context == "teacher" else
        "Please enjoy this image of a famous landmark!")

    return flask.render_template(
        "show-content-attachment.html",
        message=message_str,
        image_filename=attachment.image_filename,
        image_caption=attachment.image_caption,
        responses=response_strings)


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
    flask.session[
        "credentials"] = ch._credential_handler.session_credentials_to_dict(
            credentials)

    # Add or update the user's record in the database.
    ch._credential_handler.save_credentials_to_storage(credentials)

    return flask.render_template(
        "close-me.html", redirect_destination="load_attachment")
