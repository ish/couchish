#!/usr/bin/env python

import sys, time

import logging as log
log.basicConfig(level=log.INFO, filename='/tmp/couch-updater.log')


def notifications():
    while True:
        line = sys.stdin.readline()
        log.info('read %s'%line)
        if not line:
            raise StopIteration()
        yield line


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

