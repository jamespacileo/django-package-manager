import re
import requests
import os
import json
import urlparse
import unicodedata

def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)

class ReadTheDocsBootstrap(object):

    def __init__(self, proxy=None):
        self.proxy = proxy

    def check_if_docs_exist(self, package_name):
        package_name = slugify(package_name)

        url = "http://readthedocs.org/api/v1/project/%s/?format=json"
        r = requests.get( url %package_name, proxies = {
            'http': self.proxy
        })
        if not r.content:
            return False
        jdata = json.loads(r.content)
        if jdata.has_key('error_message'):
            print jdata['error_message']
            return False
        if jdata.get('absolute_url'):
            print urlparse.urljoin("http://readthedocs.org", jdata.get('absolute_url'))
            return urlparse.urljoin("http://readthedocs.org", jdata.get('absolute_url'))
        print jdata
        return False