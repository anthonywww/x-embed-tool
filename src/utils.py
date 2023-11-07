#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import base64
import logging

logger = logging.getLogger(__name__)

def b64e(s):
    return base64.b64encode(bytes(s, 'utf-8')).decode('utf-8')

def b64d(s):
    return str(base64.b64decode(s), 'utf-8')
