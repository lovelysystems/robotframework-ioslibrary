import requests
import logging
import json
import os
import robot
import time
from robot.variables import GLOBAL_VARIABLES
from robot.api import logger

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

class IOSLibrary(object):

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, device_endpoint='localhost:37265'):
        self._url = 'http://%s/' % device_endpoint
        self._screenshot_index = 0
        self._current_orientation = 0

    def post(self, endp, request):
        logging.info("Request to device %s: %s", self._url+endp, request)

        res = requests.post(self._url+endp, data=request, headers={
          'Content-Type': 'application/x-www-form-urlencoded'
        })

        logging.info("Response from device %s: %s", self._url+endp, res.text)
        return res

    def get(self,endp):
        res = requests.get(self._url+endp)
        assert res.status_code == 200, (
                "Device sent http status code %d" % res.status_code)
        return res

    def _map(self, query, method_name, args=[]):
        data = json.dumps({
            "query":query,
            "operation":{
                "arguments":args,
                "method_name":method_name
            }
        })
        res = self.post("map",data)
        res = json.loads(res.text)
        if res['outcome'] != 'SUCCESS':
            self._screen_and_raise('map %s failed because: %s \n %s' % (query, res['reason'], res['details']))
        return res['results']

    def _screenshot(self, filename=None):
        res = self.get('screenshot')
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
        ios = options["OS"] if options.has_key("OS") else "ios5"
        device = options["DEVICE"] if options.has_key("DEVICE") else "iphone"
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
                if options.has_key('query'):
                    post_data['query']=options['query']
                if options.has_key('offset'):
                    post_data['offset']=options['offset']
                if options.has_key('reverse'):
                    post_data['reverse']=options['reverse']
                if options.has_key('prototype'):
                    post_data['prototype']=options['prototype']
        res = json.loads(self.post('play',json.dumps(post_data)).text)
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

    def query(self, query):
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
        self._playback("touch",{"query":query})

    def touch_position(self, x=0, y=0):
        self._playback("touch",
                    {"offset":{
                        "x":x,
                        "y":y
                        }
                    })

    def check_element_does_exist(self,query):
        assert self.search_ui_elements(query)["results"]

    def check_element_does_not_exist(self,query):
        assert not self.search_ui_elements(query)["results"]

    def capture_screenshot(self,filename=None):
        self._screenshot(filename)

    def toggle_switch(self, name=None):
        if not name:
            self.touch("switch")
        else:
            self.touch("switch marked:'%s'" % name)

    def touch_text(self, name=None):
        if not name:
            self.touch("textField")
        else:
            self.touch("textField placeholder:'%s'" % name)

    def go_back(self):
        self.touch("navigationItemButtonView first")

    def enter_background(self, time=10):
        self.post('background',json.dumps({'duration':time}))         

    def rotate(self, direction):
        if direction == "right":
            self._current_orientation -= 90
        elif direction == "left":
            self._current_orientation += 90
        else:
            self._screen_and_raise("not a valid direction %s" % direction)
        self._rotate_to(self._current_orientation, direction)

    def set_device_orientation_to(self, orientation, direction="left"):
        degrees = ORIENTATIONS[orientation]
        self._rotate_to(degrees, direction)

    def scroll(self, direction, query = "scrollView index:0"):
        views_touched = self._map(query, "scroll", [direction])
        if not views_touched:
            self._screen_and_raise("could not find a view to scroll: %s" % query)
    def pinch(self, direction, query = None):
        options = {}
        if query:
           options = {"query":query} 
        self._pinch(direction, options)

    def swipe(self, direction):
        degrees = ORIENTATIONS[direction]
        direction = (360 - self._current_orientation) + degrees
        direction = self._reduce_degrees(direction)
        direction = ORIENTATIONS_REV[direction]
        self._playback("swipe_%s" % direction)

    # END: DEFINITIONS
