import requests
import logging
import subprocess
import json
import os
import robot
import time
from robot.variables import GLOBAL_VARIABLES
from robot.api import logger
from urlparse import urljoin

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
execfile(os.path.join(THIS_DIR, 'version.py'))

__version__ = VERSION

ORIENTATIONS = {
    "down": 0,
    "right": 90,
    "left": 270,
    "up": 180
}

ORIENTATIONS_REV = {
    0: "down",
    90: "right",
    180: "up",
    270: "left"
}

DEFAULT_SIMULATOR = ("/Applications/Xcode.app/Contents/Applications/" +
                     "iPhone Simulator.app/Contents/MacOS/iPhone Simulator")


class IOSLibraryException(Exception):
    pass


class IOSLibrary(object):

    ROBOT_LIBRARY_VERSION = VERSION
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, device_endpoint='localhost:37265'):
        """
        Initialize the IOSLibrary.

        `device_endpoint` endpoint of the test server (the instrumented app).
        Optional if you are running tests on the local machine against the
        simulator.
        """
        if device_endpoint:
            self.set_device_url('http://%s/' % device_endpoint)
        self._screenshot_index = 0
        self._current_orientation = 0
        self._waxsim = self._find_waxsim()
        if os.path.exists(DEFAULT_SIMULATOR):
            self.set_simulator(DEFAULT_SIMULATOR)
        self._device = "iPhone"

    def set_device_url(self, url):
        """
        Set the device url where the application is started.

        `url` the base url to use for all requests
        """
        self._url = url

    def _find_waxsim(self):
        path = os.environ['PATH']
        for d in path.split(os.pathsep):
            if os.path.exists(d):
                files = os.listdir(d)
                if 'waxsim' in files:
                    return os.path.join(d, 'waxsim')
        return None

    def set_simulator(self, simulator_path=DEFAULT_SIMULATOR):
        """
        Set the path where the iOS Simulator is found.

        If the iOS Simulator is at the default location, you don't need to call
        this. However, if you are using beta release of XCode, you can choose
        which simulator to use.

        `simulator_path` fully qualified path to the iOS Simulator executable.
        """
        self._simulator = simulator_path

    def set_device(self, device_name):
        """
        Set the simulated device

        `device` The device to simulate. Valid values are: "iPhone", "iPad", "iPhone (Retina)" and "iPad (Retina)"
        """
        self._device = device_name


    def _get_app_and_binary(self, app_path):
        filename, ext = os.path.splitext(app_path)
        binary = None
        if ext == '.app':
            binary = os.path.join(app_path,filename)
        elif ext == '':
            app_path = os.path.dirname(app_path)
            binary = filename
        return app_path, binary

    def _check_simulator(self):
        assert (os.path.exists(self._simulator) or (self._waxsim and os.path.exists(self._waxsim))), (
                "neither simulator at %s nor waxsim could be found" % self._simulator)


    def start_simulator(self, app_path, sdk='5.1'):
        """
        Starts the App found at `app_path` in the iOS Simulator.

        `app_path` Path to the binary of the App to start.
        """
        self._check_simulator()
        app_path = os.path.expanduser(app_path)
        assert os.path.exists(app_path), "Couldn't find app bundle or binary at %s" % app_path

        cmd = []
        app_path, binary = self._get_app_and_binary(app_path)
        if not self._waxsim:

            assert binary, "Could not parse app binary name"
            assert os.path.exists(binary), "Could not find app binary at %s" % app_path
            logging.warning("Waxsim not found, execute app without installing it in simulator")
            cmd = [self._simulator,
                  '-SimulateDevice',
                  self._device,
                  '-SimulateApplication',
                  binary]
        else:
            cmd = [self._waxsim,
                   '-s',
                   sdk,
                   '-f',
                   self._device.lower(),
                   app_path]
        with open("waxsim.log", "w") as logfile:
            self._simulator_proc = subprocess.Popen(cmd, stderr=logfile)

    def reset_simulator(self):
        """
        Reset the simulator. Warning the simulator should run
        """
        p = os.path.join(
                        os.path.join(os.path.dirname(__file__), 'resources'),
                        "reset.applescript")
        cmd = ["osascript",p]
        subprocess.Popen(cmd)

    def stop_simulator(self):
        """
        Stops a previously started iOS Simulator.
        """
        cmd = "`echo 'application \"iPhone Simulator\" quit' | osascript`"
        stop_proc = subprocess.Popen(cmd, shell=True)
        stop_proc.wait()
        self._simulator_proc.wait()

    def is_device_available(self):
        """
        Succeeds if the test server is available for receiving commands.

        This is best used with the `Wait Until Keyword Succeeds` keyword from
        the BuiltIn library like this:

        Example:
        | Wait Until Keyword Succeeds | 1 minute | 10 seconds | Is device available |
        """
        logging.getLogger().setLevel(logging.ERROR)
        status_code = 0
        try:
            resp = self._get('version')
            status_code = resp.status_code
        except:
            raise
        finally:
            logging.getLogger().setLevel(logging.WARNING)
        assert status_code == 200, "Device is not available"

    def _post(self, endp, request):
        url = urljoin(self._url, endp)
        res = requests.post(url, data=request, headers={
          'Content-Type': 'application/json;charset=utf-8'
        })

        return res

    def _get(self, endp):
        res = requests.get(urljoin(self._url, endp))
        assert res.status_code == 200, (
                "Device sent http status code %d" % res.status_code)
        return res

    def _map(self, query, method_name, args=None):
        if args is None:
            args = []
        data = json.dumps({
            "query": query,
            "operation": {
                "arguments": args,
                "method_name": method_name
            }
        })
        res = self._post("map", data)
        logging.debug("<< %r %r", res.status_code, res.text)
        res = json.loads(res.text)
        if res['outcome'] != 'SUCCESS':
            raise IOSLibraryException('map %s failed because: %s \n %s' %
                                      (query, res['reason'], res['details']))
        return res['results']

    def _screenshot(self, filename=None):
        res = self._get('screenshot')
        path, link = self._get_screenshot_paths(filename)
        with open(path, 'w') as f:
            f.write(res.content)
        logger.info('</td></tr><tr><td colspan="3"><a href="%s">'
                   '<img src="%s"></a>' % (link, link), True, False)

    def _load_playback_data(self, recording, options=None):
        if options is None:
            options = {}
        ios = options.get("OS", "ios5")
        device = options.get("DEVICE", "iphone")
        if not recording.endswith(".base64"):
            recording = "%s_%s_%s.base64" % (recording, ios, device)
        p = os.path.join(
                        os.path.join(os.path.dirname(__file__), 'resources'),
                        recording)
        if os.path.exists(p):
            with open(p, 'r') as f:
                return f.read()
        else:
            raise IOSLibraryException('Playback not found: %s' % p)

    def _playback(self, recording, options=None):
        data = self._load_playback_data(recording)
        post_data = {
            "events": data
        }
        if options:
            post_data.update(options)
        res = self._post('play', json.dumps(post_data))
        jres = json.loads(res.text)
        if res.status_code != 200 or jres['outcome']!='SUCCESS':
            raise IOSLibraryException('playback failed because: %s \n %s' %
                                       (jres['reason'], jres['details']))
        return res

    def _rotate_to(self, orientation, direction="left"):
        orientation = self._reduce_degrees(orientation)
        self._current_orientation = orientation
        if direction == "right":
            orientation += 90
        elif direction == "left":
            orientation += 270
        orientation = self._reduce_degrees(orientation)
        orientation = ORIENTATIONS_REV[orientation]
        playback = "rotate_%s_home_%s" % (direction, orientation)
        self._playback(playback)
        time.sleep(1)

    def _reduce_degrees(self, degrees):
        while degrees >= 360:
            degrees -= 360
        while degrees < 0:
            degrees += 360
        return degrees

    def _element_exists(self, query):
        if not self.query(query):
            return False
        return True

    def _get_webview_html(self, index):
        res = self.query("webView css:'body'")
        index = int(index)
        if not res or not res[index]:
            raise IOSLibraryException("No WebView with index %i found" % index)
        return res[index]["html"]

    def query(self, query):
        """
        Search for a UIElement matching `query`

        `query` query selector. The available syntax is documented here https://github.com/calabash/calabash-ios/wiki/05-Query-syntax
        """
        return self._map(query, "query")

    def query_all(self, query):
        """
        Search for all UIElements matching `query`

        `query` query selector. The available syntax is documented here https://github.com/calabash/calabash-ios/wiki/05-Query-syntax
        """
        return self._map(query, "query_all")

    def _pinch(self, in_out, options={}):
        f = "pinch_in"
        if in_out == "out":
            f = "pinch_out"
        self._playback(f, options)

    # BEGIN: STOLEN FROM SELENIUM2LIBRARY

    def _get_log_dir(self):
        logfile = GLOBAL_VARIABLES['${LOG FILE}']
        if logfile != 'NONE':
            return os.path.dirname(logfile)
        return GLOBAL_VARIABLES['${OUTPUTDIR}']

    def _get_screenshot_paths(self, filename):
        logdir = self._get_log_dir()
        if not filename:
            self._screenshot_index += 1
            filename = 'ios-screenshot-%d.png' % self._screenshot_index
            filename = os.path.join('screenshots', filename)
            screen_dir = os.path.join(logdir, 'screenshots')
            if not os.path.exists(screen_dir):
                os.mkdir(screen_dir)
        else:
            filename = filename.replace('/', os.sep)
        path = os.path.join(logdir, filename)
        link = robot.utils.get_link_path(path, logdir)
        return path, link

    # END: STOLEN FROM SELENIUM2LIBRARY

    # DEFINITIONS

    def touch(self, query):
        """
        Touch element specified by query

        `query` selector of the element to touch. The available syntax is documented here https://github.com/calabash/calabash-ios/wiki/05-Query-syntax
        """
        return self._playback("touch", {"query": query})

    def touch_position(self, x=0, y=0):
        """
        Simulate a touch at the specified position

        `x` X-Coordinate of the position to touch

        `y` Y-Coordinate of the position to touch
        """
        self._playback("touch",
                    {"offset": {
                        "x": x,
                        "y": y
                        }
                    })

    def capture_screenshot(self, filename=None):
        """
        Captures a screenshot of the current screen and embeds it
        in the test report

        `filename` Location where the screenshot will be saved. If omitted a unique filename will be chosen.
        """
        self._screenshot(filename)

    def toggle_switch(self, name=None):
        """
        Toggle a switch

        `name` Name of the switch to toggle.
        """
        if not name:
            self.touch("switch")
        else:
            self.touch("switch marked:'%s'" % name)

    def touch_text(self, placeholder=None):
        """
        Touch a Textfield

        `placeholder` of textField to touch
        """
        if not placeholder:
            self.touch("textField")
        else:
            self.touch("textField placeholder:'%s'" % placeholder)

    def set_text(self, value, query="textField"):
        """
        Set the value of a textField

        `value` the new value of the textField

        `query` query selector to find the textField that will be set to the new value
        """
        text_fields_modified = self._map(query, "setText", [value])

        if not text_fields_modified:
            raise IOSLibraryException("could not find text field %s" % query)

    def go_back(self):
        """
        Touch the first Navigationitem in a Navigation Bar
        """
        self.touch("navigationItemButtonView first")

    def rotate(self, direction):
        """
        Rotate the simulator

        `direction` The direction to rotate the simulator in. Valid values are "left" and "right".
        """

        if direction == "right":
            self._current_orientation -= 90
        elif direction == "left":
            self._current_orientation += 90
        else:
            raise IOSLibraryException("not a valid direction %s" % direction)
        self._rotate_to(self._current_orientation, direction)

    def set_device_orientation_to(self, orientation, direction="left"):
        """
        Set orientation of the simulator

        `orientation` The final orientation the simulator should have afterwards. Valid values are "up", "down", "left", "right".

        `direction` The direction to rotate the simulator in until it reached the final orientation. Valid values are "left" and "right".
        """
        degrees = ORIENTATIONS[orientation]
        self._rotate_to(degrees, direction)

    def scroll(self, direction, query="scrollView index:0"):
        """
        Scroll the view.

        `direction` direction to scroll in. Valid values are "up", "down", "left", "right"

        `query` selector of the view to scroll in. Defaults to the first scrollView.
        """
        views_touched = self._map(query, "scroll", [direction])
        if not views_touched:
            raise IOSLibraryException("could not find view to scroll: %s" %
                                      query)

    def pinch(self, direction, query=None):
        """
        Pinch in or out.

        `direction` to pinch. Valid values are "in" and "out".

        `query` selector of the element to pinch on
        """
        options = {}
        if query:
            options = {"query": query}
        self._pinch(direction, options)

    def swipe(self, direction):
        """
        Swipe.

        `direction` The direction to swipe in. Valid values are "up", "down", "left", "right"
        """
        degrees = ORIENTATIONS[direction]
        direction = (360 - self._current_orientation) + degrees
        direction = self._reduce_degrees(direction)
        direction = ORIENTATIONS_REV[direction]
        self._playback("swipe_%s" % direction)

    def screen_should_contain_text(self, expected):
        """
        Asserts that the current screen contains a given text

        `expected` The text that should be on the screen
        """
        if not self._element_exists("view {text == '%s'}" %
                                    expected.replace("'", r"\'")):
            raise IOSLibraryException("No text %s found" % expected)

    def screen_should_contain(self, expected):
        """
        Asserts that the current screen contains a given element
        specified by name or query

        `expected` String or View that should be on the current screen
        """
        res = (self._element_exists("view marked:'%s'" % expected) or
               self._element_exists(expected))
        if not res:
            raise IOSLibraryException("No element found with mark or text %s" %
                                      expected)

    def webview_should_contain(self, expected, index=0):
        """
        Asserts that the current webview contains a given text

        `expected` text that should be in the webview

        `index` index of the webView
        """
        if not expected in self._get_webview_html(index):
            raise IOSLibraryException("%s not found in webView" % expected)

    def webview_should_not_be_empty(self, index=0):
        """
        Asserts that the current webview is not empty

        `index` index of the webView
        """
        if not self._get_webview_html(index):
            raise IOSLibraryException("Webview is empty")

    # END: DEFINITIONS
