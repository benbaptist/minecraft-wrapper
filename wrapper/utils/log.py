# -*- coding: utf-8 -*-

import os
import logging
from logging.config import dictConfig

import termcolors

from core.config import Config

DEFAULT_CONFIG = dict({
    'version': 1,              
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(plugin)s/%(levelname)s]: %(message)s'
        },
        'file': {
            'format': '[%(asctime)s] [%(plugin)s/%(levelname)s]: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'trace': {
            'format': '[%(asctime)s] [%(plugin)s/%(levelname)s] [THREAD:%(threadName)s]: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'standard'
        },
        'wrapper_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'NOTSET',
            'formatter': 'file',
            'filename': '../../logs/wrapper/wrapper.log',
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        },
        'error_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'file',
            'filename': '../../logs/wrapper/wrapper.errors.log',
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        },
        'trace_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'TRACE',
            'formatter': 'trace',
            'filename': '../../logs/wrapper/wrapper.trace.log',
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        }
    },
    'root': {
        'level': 'NOTSET',
        'handlers': ['console', 'wrapper_file_handler', 'error_file_handler', 'trace_file_handler']
    }
})

# https://docs.python.org/2/howto/logging.html#optimization

class Log:

    def __init__(self, plugin='Wrapper.py'):
        self.setCustomLevels()
        self.loadConfig()

        self.plugin = plugin
        self.logger = logging.getLogger()

    """
        Confirmation that things are working as expected.
    """
    def info(self, message, *args, **kwargs):
        logging.info(message, *args, **dict(kwargs, extra={'plugin':self.plugin}))

    """
        Detailed information, typically of interest only when diagnosing problems.
    """
    def debug(self, message, *args, **kwargs):
        if Config.debug:
            debug_style = termcolors.make_style(fg='cyan')
            logging.debug(debug_style(message), *args, **dict(kwargs, extra={'plugin':self.plugin}))

    def trace(self, message, *args, **kwargs):
        if Config.trace:
            trace_style  = termcolors.make_style(fg='magenta')
            logging.trace(trace_style(message), *args, **dict(kwargs, extra={'plugin':self.plugin}))

    """
        An indication that something unexpected happened, or indicative of some problem in the near future (e.g. 'disk space low'). 
        The software is still working as expected.
    """
    def warn(self, message, *args, **kwargs):
        warn_style = termcolors.make_style(fg='yellow', opts=('bold',))
        logging.warn(warn_style(message), *args, **dict(kwargs, extra={'plugin':self.plugin}))

    """
        Due to a more serious problem, the software has not been able to perform some function.
    """
    def error(self, message, *args, **kwargs):
        error_style = termcolors.make_style(fg='red', opts=('bold',))
        logging.error(error_style(message), *args, **dict(kwargs, extra={'plugin':self.plugin}))

    """ 
        Creates a log message similar to Logger.error(). 
        The difference is that Logger.exception() dumps a stack trace along with it.
        Call this method only from an exception handler.
    """
    def exception(self, message, *args, **kwargs):
        except_style = termcolors.make_style(fg='red', opts=('bold',))
        logging.exception(except_style(message), *args, **dict(kwargs, extra={'plugin':self.plugin}))

    """
        A serious error, indicating that the program itself may be unable to continue running.
    """
    def critical(self, message, *args, **kwargs):
        crit_style = termcolors.make_style(fg='black', bg='red', opts=('bold',))
        logging.critical(crit_style(message), *args, **dict(kwargs, extra={'plugin':self.plugin}))

    def setCustomLevels(self):
        # Create a TRACE level
        # We should probably not do this, but for wrappers use case this is non-impacting.
        # See: https://docs.python.org/2/howto/logging.html#custom-levels
        logging.TRACE = 51
        logging.addLevelName(logging.TRACE, 'TRACE')
        logging.Logger.trace = lambda inst, msg, *args, **kwargs: inst.log(logging.TRACE, msg, *args, **kwargs)

    def loadConfig(self, file="logging.json"):
        dictConfig(DEFAULT_CONFIG)

log = Log()
log.info('hey %s', "h")