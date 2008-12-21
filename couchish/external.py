#! /usr/bin/env python

import sys
import simplejson

#
# Example External ... us these settings in your ini file.
#
# [httpd_db_handlers]
# _test = {couch_httpd_external, handle_external_req, <<"my_external_key">>}
# [external]
# my_external_key = /home/tim/git/couchish/couchich/external.py
#

_logfile = file('/tmp/external.log', 'a')


def log(msg):
    _logfile.write('%s\n'%(msg,))
    _logfile.flush()

def requests():
    # `for line in sys.stdin` won't work here
    line = sys.stdin.readline()
    while line:
        data = simplejson.loads(line)
        log('data: %s'%data)
        yield data
        line = sys.stdin.readline()

def respond(code=200, data={}, headers={}):
    sys.stdout.write("%s\n" % simplejson.dumps({"code": code, "json": data, "headers": headers}))
    sys.stdout.flush()

def main():
    for req in requests():
        respond(data={"qs": req["query"]})

if __name__ == "__main__":
    main()

