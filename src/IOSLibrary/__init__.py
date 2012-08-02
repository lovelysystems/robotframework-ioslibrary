import requests
import logging
import subprocess
import json
import os
import robot
import time
from robot.variables import GLOBAL_VARIABLES
from robot.api import logger

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
execfile(os.path.join(THIS_DIR, 'version.py'))

__version__ = VERSION

ORIENTATIONS = {
    "down":0,
    "right":90,
    "left":270,
    "up":180
}

ORIENTATIONS_REV = {
    0:"down",
    90:"right",
    180:"up",
    270:"left"
}

DEFAULT_SIMULATOR = "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Applications/iPhone Simulator.app/Contents/MacOS/iPhone Simulator"

class IOSLibrary(object):

    ROBOT_LIBRARY_VERSION = VERSION
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, device_endpoint='localhost:37265'):
        self._url = 'http://%s/' % device_endpoint
        self._screenshot_index = 0
        self._current_orientation = 0
        self._emulator = DEFAULT_SIMULATOR
        assert os.path.exists(self._emulator), "Couldn't find simulator at %s" % self._emulator
        self._device = "iPhone"

    def set_device(self, device):
        ''' 
        Set the simulated device

        `device` {iPhone | iPad | iPhone (Retina) | iPad (Retina)}
        '''
        self._device = device

    def start_emulator(self,app):
        '''
        Starts the simulator with a specific app
        '''
        assert os.path.exists(app), "Couldn't find app binary at %s" % app
        self._app = app

        cmd = [self._emulator,'-SimulateDevice',self._device, '-SimulateApplication',app]
        self._emulator_proc = subprocess.Popen(cmd)
        
    def stop_emulator(self):
        '''
        Stops a previously started emulator
        '''
        cmd = "`echo 'application \"iPhone Simulator\" quit' | osascript`"
        subprocess.Popen(cmd,shell=True)

    def is_device_available(self):
        assert requests.get(self._url).status_code == 405, "Device is not available"

    def _post(self, endp, request):
        logging.info("Request to device %s: %s", self._url+endp, request)

        res = requests.post(self._url+endp, data=request, headers={
          'Content-Type': 'application/x-www-form-urlencoded'
        })

        logging.info("Response from device %s: %s", self._url+endp, res.text)
        return res

    def _get(self,endp):
        res = requests.get(self._url+endp)
        assert res.status_code == 200, (
                "Device sent http status code %d" % res.status_code)
        return res

    def _map(self, query, method_name, args=None):
        if args is None:
            args = []
        data = json.dumps({
            "query":query,
            "operation":{
                "arguments":args,
                "method_name":method_name
            }
        })
        res = self._post("map",data)
        res = json.loads(res.text)
        if res['outcome'] != 'SUCCESS':
            self._screen_and_raise('map %s failed because: %s \n %s' % (query, res['reason'], res['details']))
        return res['results']

    def _screenshot(self, filename=None):
        res = self._get('screenshot')
        path, link = self._get_screenshot_paths(filename)
        with open(path,'w') as f:
            f.write(res.content)
        logger.info('</td></tr><tr><td colspan="3"><a href="%s">'
                   '<img src="%s"></a>' % (link, link), True, False)

    def _screen_and_raise(self, err):
        logger.warn(err)
        self._screenshot()
        raise Exception

    def _load_playback_data(self, recording, options=None):
        if options is None:
            options = {}
        ios = options.get("OS", "ios5")
        device = options.get("DEVICE","iphone")
        if not recording.endswith(".base64"):
            recording = "%s_%s_%s.base64" % (recording, ios, device)
        p = os.path.join(os.path.join(os.path.dirname(__file__),'resources'),recording)
        if os.path.exists(p):
            with open(p,'r') as f:
                return f.read()
        else:
            self._screen_and_raise('Playback not found: %s' % p)

    def _playback(self, recording, options=None):
        data = self._load_playback_data(recording)
        post_data = {
            "events": data
        }
        if options:
            post_data.update(options)
        res = json.loads(self._post('play',json.dumps(post_data)).text)
        if res['outcome'] != 'SUCCESS':
            self._screen_and_raise('playback failed because: %s \n %s' % (res['reason'],res['details']))
        return res['results']
        
    def _rotate_to(self, orientation, direction="left"):
        orientation = self._reduce_degrees(orientation)
        self._current_orientation = orientation
        if direction == "right":
           orientation +=90
        elif direction == "left":
           orientation +=270
        orientation = self._reduce_degrees(orientation)
        orientation = ORIENTATIONS_REV[orientation]
        playback = "rotate_%s_home_%s" % (direction,orientation)
        self._playback(playback)

    def _reduce_degrees(self, degrees):
        while degrees >=360:
            degrees -=360
        while degrees < 0:
            degrees +=360
        return degrees

    def _element_exists(self, query):
        if not self.query(query):
            return False
        return True

    def query(self, query):
        '''
        Query a UIElement
        Syntax: https://github.com/calabash/calabash-ios/wiki/05-Query-syntax
        '''
        return self._map(query,"query")

    def query_all(self, query):
        return self._map(query,"query_all")

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
        if not filename:
            self._screenshot_index += 1
            filename = 'ios-screenshot-%d.png' % self._screenshot_index
        else:
            filename = filename.replace('/', os.sep)
        logdir = self._get_log_dir()
        path = os.path.join(logdir, filename)
        link = robot.utils.get_link_path(path, logdir)
        return path, link

    # END: STOLEN FROM SELENIUM2LIBRARY

    # DEFINITIONS

    def touch(self, query):
        '''
        Touch element specified by query

        `query` query to specify the element
        '''
        self._playback("touch",{"query":query})

    def touch_position(self, x=0, y=0):
        '''
        Touch position
        
        `x` `y` position to touch
        '''
        self._playback("touch",
                    {"offset":{
                        "x":x,
                        "y":y
                        }
                    })

    def capture_screenshot(self,filename=None):
        '''
        Captures a screenshot of the current screen and embeds it in the test report

        `filename` Location where the screenshot will be saved.
        '''
        self._screenshot(filename)

    def toggle_switch(self, name=None):
        '''
        toggle switch

        `name` (optional) Switch to toggle
        '''
        if not name:
            self.touch("switch")
        else:
            self.touch("switch marked:'%s'" % name)

    def touch_text(self, placeholder=None):
        '''
        Touch a Textfield

        `placeholder` (optional) of textField to touch
        '''
        if not placeholder:
            self.touch("textField")
        else:
            self.touch("textField placeholder:'%s'" % placeholder)

    def go_back(self):
        '''
        Touch the first Navigationitem in a Navigation Bar
        '''
        self.touch("navigationItemButtonView first")

    def rotate(self, direction):
        '''
        Rotate simulator { left | right }
        '''
        if direction == "right":
            self._current_orientation -= 90
        elif direction == "left":
            self._current_orientation += 90
        else:
            self._screen_and_raise("not a valid direction %s" % direction)
        self._rotate_to(self._current_orientation, direction)

    def set_device_orientation_to(self, orientation, direction="left"):
        '''
        Set orientation of simulator to { up | down | left | right}
        '''
        degrees = ORIENTATIONS[orientation]
        self._rotate_to(degrees, direction)

    def scroll(self, direction, query = "scrollView index:0"):
        '''
        Scroll { up | down | left | right}
        '''
        views_touched = self._map(query, "scroll", [direction])
        if not views_touched:
            self._screen_and_raise("could not find a view to scroll: %s" % query)

    def pinch(self, direction, query = None):
        '''
        pinch {in | out}

        `direction` in or out
        `query` (optional) to specify an element to pinch on
        '''
        options = {}
        if query:
           options = {"query":query} 
        self._pinch(direction, options)

    def swipe(self, direction):
        '''
        { up | down | left | right}
        '''
        degrees = ORIENTATIONS[direction]
        direction = (360 - self._current_orientation) + degrees
        direction = self._reduce_degrees(direction)
        direction = ORIENTATIONS_REV[direction]
        self._playback("swipe_%s" % direction)

    def screen_should_contain(self, expected):
        '''
        Asserts that the current screen contains a given text or view

        `expected` { String | View } that should be on the current screen
        '''
        res = (self._element_exists("view marked:'%s'" % expected) or
               self._element_exists("view text:'%s'" % expected))
        if not res:
            self._screen_and_raise("No element found with mark or text %s" % expected)

    # END: DEFINITIONS
