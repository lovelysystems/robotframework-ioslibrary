import requests
import logging
import json
import os
import robot
from robot.variables import GLOBAL_VARIABLES
from robot.api import logger

class IOSLibrary(object):

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, device_endpoint='localhost:37265'):
        self._url = 'http://%s/' % device_endpoint
        self._screenshot_index = 0

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
            "query":json.loads(query),
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

    def _screen_and_raise(self, err):
        logging.error(err)
        self.capture_screenshot()
        raise Exception

    def _playback(self, request):
        return self.post('play',request)

    def _readfile(self, path):
        with open(path,'r') as f:
            return f.read()
 
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

    def query(self, query):
        return self._map(query,"query")

    def query_all(self, query):
        return self._map(query,"query_all")

    def touch(self, query):
        p = os.path.abspath("resources")
        p = os.path.join(p,"touch_ios5_iphone.base64")
        p = self._readfile(p).replace("\n",'')
        self._play({
            "query":json.loads(query),
            "events":p
        })

    def check_element_does_exist(self,query):
        assert self.search_ui_elements(query)["results"]

    def check_element_does_not_exist(self,query):
        assert not self.search_ui_elements(query)["results"]

    def capture_screenshot(self, filename=None):
        res = self.get('screenshot')
        path, link = self._get_screenshot_paths(filename)
        with open(path,'w') as f:
            f.write(res.content)
        logger.info('</td></tr><tr><td colspan="3"><a href="%s">'
                   '<img src="%s"></a>' % (link, link), True, False)
    # DEFINITIONS
