import requests
import json

DJANGO_PACKAGES_API_URL = "http://djangopackages.com/api/v1/"

class DjangoPackagesBootstrap(object):

    def __init__(self, caching=False, proxy=None):
        self.caching = caching
        if proxy:
            self.proxy = {
                'http': proxy,
            }
        else:
            self.proxy = {}

    def grid_list(self):
        url = "http://djangopackages.com/api/v1/grid/?limit=0"
        r = requests.get(url, proxies=self.proxy)
        jdata = json.loads(r.content)
        return jdata['objects']

    def grid(self, name):
        url = "http://djangopackages.com/api/v1/package/%s/" %name
        r = requests.get(url, proxies=self.proxy)
        jdata = json.loads(r.content)
        return jdata

    def app_list(self, category=None):
        if not category:
            url = "http://djangopackages.com/api/v1/package/?limit=0"
        else:
            url = "http://djangopackages.com/api/v1/package/?grid=%s&limit=0" %category
        r = requests.get(url, proxies=self.proxy)
        jdata = json.loads(r.content)
        return jdata['objects']

    def app(self, name):
        url = "http://djangopackages.com/api/v1/package/%s/" %name
        r = requests.get(url, proxies=self.proxy)
        jdata = json.loads(r.content)
        return jdata

