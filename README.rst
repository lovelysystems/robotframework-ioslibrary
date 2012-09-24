=========================
robotframework-ioslibrary
=========================

**robotframework-ioslibrary** is a `Robot Framework
<http://code.google.com/p/robotframework/>`_ test library for all your iOS
automation needs.

It uses `Calabash iOS Server
<https://github.com/calabash/calabash-ios-server>`_ to communicate with your
instrumented iOS application similar to how `Selenium WebDriver
<http://seleniumhq.org/projects/webdriver/>`_ talks to your web browser.

Installation
++++++++++++

To install, just fetch the latest version from PyPI:.

    pip install --upgrade robotframework-ioslibrary

Prepare your iOS app
++++++++++++++++++++

To prepare your iOS app look at <https://github.com/calabash/calabash-ios#installation>

Install Waxsim
++++++++++++++

To get full simulator support, e.g.: for testing in app purchases
you have to install waxsim.

Download the source from::

https://github.com/jonathanpenn/WaxSim/tarball/93d4dd1d137609eb2dd7dd97161d8b7d7b8267e9

change into the directory and build it with::

xcodebuild

Then add the binary to your path

Simulator Reset
+++++++++++++++

To use `Reset Simultor` enable:

    System preferences -> Accesability -> Enable access for Assisted devices

Usage
+++++

API documentation can be found at
`http://lovelysystems.github.com/robotframework-ioslibrary/IOSLibrary.html
<http://lovelysystems.github.com/robotframework-ioslibrary/IOSLibrary.html>`_,
here is an example on how to use it:

============  ================
  Setting          Value
============  ================
Library          IOSLibrary
============  ================

\

============  =================================  ===================================  ==========     ========================
 Test Case    Action                             Argument                              Argument      Argument
============  =================================  ===================================  ==========     ========================
Example
\             [Documentation]                    Starts the iOS Simulator and swipes
\             Set Device URL                     localhost:37265
\             Start Simulator
\             Wait Until Keyword Succeeds        1 minute                             5 seconds      Is Device Available
\             Swipe                              right
\             Rotate                             left
\             Screen Should Contain              Hello World
============  =================================  ===================================  ==========     ========================

License
+++++++

robotframework is a port of the ruby-based `calabash-ios` and therefore
licensed under the  `Eclipse Public License (EPL) v1.0
<http://www.eclipse.org/legal/epl-v10.html>`_

Development by `Lovely Systems GmbH <http://www.lovelysystems.com/>`_,
sponsored by `Axel Springer AG <http://www.axelspringer.de/>`_.

