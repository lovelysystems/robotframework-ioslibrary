import requests
import logging
import json

class IOSLibrary(object):

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, device_endpoint='localhost:37265'):
        self._url = 'http://%s/map' % device_endpoint

    def _http(self, request):
        logging.info("Request to device %s: %s", self._url, request)

        httprequest = requests.post(self._url, data=json.dumps(request), headers={
          'Content-Type': 'application/x-www-form-urlencoded'
        })

        logging.info("Response from device %s: %s", self._url, httprequest.text)

        assert httprequest.status_code == 200, (
                "Device sent http status code %d" % httprequest.status_code)

        return json.loads(httprequest.text)

    def search_ui_elements(self, query):
        self._http({
          "query": json.loads(query),
          "operation": {
            "arguments": [],
            "method_name":"query"
          },
        })

