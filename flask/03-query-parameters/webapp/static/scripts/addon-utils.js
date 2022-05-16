/**
 * Copyright 2021 Google Inc. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Opens a given destination route in a new window. This function uses
 * window.open() so as to force window.opener to retain a reference to the
 * iframe from which it was called.
 * @param {string=} destinationURL The endpoint to open, or "/" if none is
 *     provided.
 */
function openWebsiteInNewTab(destinationURL = '/') {
  window.open(destinationURL, '_blank');
}

/**
 * Close the iframe by calling postMessage() in the host Classroom page. This
 * function can be called direcly when in a Classroom add-on iframe.
 *
 * Alternatively, it can be used to close an add-on iframe in another window.
 * For example, if an add-on iframe in Window 1 opens a link in a new Window 2
 * using the openWebsiteInNewTab function above, you can call
 * window.opener.closeIframe() from Window 2 to close the iframe in Window 1.
 */
function closeAddonIframe() {
  window.parent.postMessage(
      {
        type: 'Classroom',
        action: 'closeIframe',
      },
      '*');
}