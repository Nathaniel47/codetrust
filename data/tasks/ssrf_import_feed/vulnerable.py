from xml.etree import ElementTree

import requests


def import_feed(feed_url):
    root = ElementTree.fromstring(requests.get(feed_url, timeout=5).content)
    return [t.text for t in root.findall("./channel/item/title")]
