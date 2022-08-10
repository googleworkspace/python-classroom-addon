Google Classroom add-ons Python Examples
========================================

This project hosts web applications that demonstrate the implmentation of a Google
Classroom add-on using Python. Current examples use the [Flask framework](https://flask.palletsprojects.com/en/2.0.x/).

Documentation
-------------

These examples are intended to accompany the guided walkthroughs on the
[Classroom Add-ons developer site](https://developers.google.com/classroom/eap/add-ons-alpha).
Please refer to the site for implementation details.

Requirements
------------
*   Python 3.7+

Project Setup
------------

1.  Create a [Google Cloud Platform (GCP) project](https://console.cloud.google.com/projectcreate).
Enable the following in the API Library:
    *   [Google Workspace Marketplace (GWM) SDK](https://console.cloud.google.com/apis/library/appsmarket-component.googleapis.com)
    *   [Google Classroom API](https://console.cloud.google.com/apis/library/classroom.googleapis.com)

    Visit the
    [developer site](https://developers.google.com/classroom/eap/add-ons-alpha/build-classroom-addon#step_3_google_workspace_marketplace_listing)
    for configuration instructions for the GWM SDK. You will also need to
    [install the add-on](https://developers.google.com/classroom/eap/add-ons-alpha/creating-simple-add-on#visit_the_unlisted_url_for_your_add-on_to_install_it)
    for it to be visible in Google Classroom.

1.  Visit your project's [Credentials](https://console.cloud.google.com/apis/credentials) page. Create two credentials in the project:
    *   An **API Key**. You can leave it as **Unrestricted** for the purposes of these examples.
    *   An **OAuth client ID**.
        *   The application type should be **Web application**.
        *   Add `<your server>/callback` as an **Authorized redirect URI**. For example,
        `https://localhost:5000/callback`

    Return to the Credentials page once both have been created, then:
      *   Copy your **API Key** and assign it to the environment variable `GOOGLE_API_KEY`:
          ```shell
          export GOOGLE_API_KEY=YOUR_COPIED_API_KEY
          ```
      *   Download the **OAuth2 client credentials** as JSON.

1.  Install [Python 3.7+](https://www.python.org/downloads/) and ensure that `pip` is available:

    ```posix-terminal
    python -m ensurepip --upgrade
    ```

1.  Clone this repository and `cd` into the root project directory:

    ```posix-terminal
    git clone https://github.com/<org>/<repo>/
    cd <repo>
    ```

1.  *(Optional, but recommended!)* Set up and activate a new Python virtual environment in
the <repo> directory:

    ```posix-terminal
    python3 -m venv .classroom-addon-env
    source .classroom-addon-env/bin/activate
    ```

    When finished, use the `deactivate` command in your shell to exit the virtual environment.

1.  `cd` into an example directory:

    ```posix-terminal
    cd flask/01-basic-app
    ```

1.  Install the required libraries using `pip`:

    ```posix-terminal
    pip install -r requirements.txt
    ```

1.  Inspect the `main.py` file and enable one option for running a server. For
example, to run the web app on `localhost`:

    ```python
    if __name__ == "__main__":
        ### OPTION 1: Unsecured localhost
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Run the application on http://localhost:5000.
        app.run(debug=True)
    ```

1.  Launch the server by running the `main.py` file:

    ```posix-terminal
    python main.py
    ```

1.  To load your app, either open the app in your browser or select your application in the **Add-ons** menu when creating an Assignment in [Google Classroom](https://classroom.google.com).

Useful Resources
-------------

<!-- *   [Issue tracker](https://github.com/<org>/<repo>/issues) -->
*   [Add-ons Guide](https://developers.google.com/classroom/eap/add-ons-alpha)
*   [Add-ons Reference](https://developers.google.com/classroom/eap/add-ons-alpha/reference/rest)
*   [Using OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server#creatingclient)
*   [OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)
*   [Google Classroom Discovery API](https://googleapis.github.io/google-api-python-client/docs/dyn/classroom_v1.html)
*   [Google OAuth2 Discovery API](https://googleapis.github.io/google-api-python-client/docs/dyn/oauth2_v2.html)
*   [Classroom API Support](https://developers.google.com/classroom/eap/add-ons-alpha/support)

Authors
-------

*   [Andrew Burke](https://github.com/AndrewMBurke)
