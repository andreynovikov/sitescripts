# coding: utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

import re, sys, os
from urlparse import urlparse
import eventlet
from eventlet.green import urllib2
from sitescripts.utils import get_config, get_template, setupStderr
import sitescripts.subscriptions.subscriptionParser as subscriptionParser

def checkURL(url):
  try:
    result = urllib2.urlopen(url, timeout=60).read(1)
    return (url, True)
  except urllib2.HTTPError, e:
    return (url, e.code)
  except:
    return (url, False)

def checkSite(site):
  try:
    result = urllib2.urlopen('http://downforeveryoneorjustme.com/' + site, timeout=60).read()
    if re.search(r'\blooks down\b', result):
      return (site, False)
    else:
      return (site, True)
  except:
    return (site, True)

def checkSubscriptions():
  subscriptions = subscriptionParser.readSubscriptions().values()
  subscriptions.sort(key=lambda s: s.name.lower())

  urls = {}
  sites = {}
  for subscription in subscriptions:
    for key in ('homepage', 'forum', 'blog', 'faq', 'contact', 'changelog', 'policy'):
      url = getattr(subscription, key)
      if url != None:
        urls[url] = True
    for (title, url, complete) in subscription.variants:
      urls[url] = True

  pool = eventlet.GreenPool()
  for (url, result) in pool.imap(checkURL, urls.iterkeys()):
    urls[url] = result
    if result == False:
      sites[urlparse(url).netloc] = True
  for (site, result) in pool.imap(checkSite, sites.iterkeys()):
    sites[site] = result

  result = []
  for subscription in subscriptions:
    s = {'name': subscription.name, 'links': []}
    result.append(s)
    for key in ('homepage', 'forum', 'blog', 'faq', 'contact', 'changelog', 'policy'):
      url = getattr(subscription, key)
      if url != None:
        site = urlparse(url).netloc
        s['links'].append({
          'url': url,
          'title': key[0].upper() + key[1:],
          'result': urls[url],
          'siteResult': site in sites and sites[site],
        })
    for (title, url, complete) in subscription.variants:
      site = urlparse(url).netloc
      s['links'].append({
        'url': url,
        'title': title,
        'result': urls[url],
        'siteResult': site in sites and sites[site],
      })
  return result

if __name__ == '__main__':
  setupStderr()

  subscriptions = checkSubscriptions()
  outputFile = get_config().get('subscriptions', 'statusPage')
  template = get_template(get_config().get('subscriptions', 'statusTemplate'))
  template.stream({'subscriptions': subscriptions}).dump(outputFile, encoding='utf-8')
