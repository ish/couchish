#!/usr/bin/env python

import sys, time

import logging as log
log.basicConfig(level=log.INFO, filename='/tmp/couch-updater.log')


def notifications():
    simplejson_imported = False
    while True:
        line = sys.stdin.readline()
        log.info('read %s'%line)
        if not line:
            raise StopIteration()
        if not simplejson_imported:
            try:
                import simplejson
                simplejson_imported = True
            except ImportError:
                yield 'Bad Import'
        try:
            yield simplejson.loads(line)
        except Exception, e:
            yield 'Failed to Parse line : "%s"'%line


def main(args):
    for notification in notifications():
        log.info("notification: %r" % (notification,))


if __name__ == '__main__':
    try:
        args = sys.argv[1:]
        log.info("Started with args: %r"%(args,))
        main(args)
        log.info("Shutdown normally")
    except KeyboardInterrupt:
        log.info("Shutdown with Ctrl+C")
    except Exception, e:
        log.info("Shutdown by exception: %r"%(e,))

