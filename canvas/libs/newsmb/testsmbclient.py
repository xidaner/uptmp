#!/usr/bin/env python
##ImmunityHeader v1
###############################################################################
## File       :  testsmbclient.py
## Description:
##            :
## Created_On :  Thu Oct 21 14:00:04 2010
## Created_By :  Chris
## Modified_On:  Thu Apr 12 11:52:43 CEST 2018
## Modified_By:  X.
##
## (c) Copyright 2010, Immunity, Inc. all rights reserved.
###############################################################################

import sys
import os
import time
from socket import socket

if '.' not in sys.path:
    sys.path.append('.')

import libs.newsmb.libsmb as libsmb


sockaddr = ('127.0.0.1', 445)
s = socket()
s.connect(sockaddr)
u = u'kostya'
p = u'basrules'
smb = libsmb.SMBClient(s, u, p)
smb.is_unicode = True
#smb.max_smbfrag = 1
smb.negotiate()
smb.session_setup()
smb.tree_connect(u'LALA')

os.system('mkdir /tmp/lala; mkdir /tmp/sfiles')

# READING
print '=========== READ  ===='
for name in ('ls', 'cat', 'df'):
    os.system('cp ' + '/bin/' + name +' /tmp/lala/')
    f = file('/tmp/sfiles/' + name, 'wb')
    try:
        smb.get(u'\\' + name, f)
    except Exception as e:
        print "Download failed: %s" % str(e)
    f.close()
    os.system('md5sum ' + '/tmp/sfiles/' + name)
    os.system('md5sum ' + '/tmp/lala/' + name)


## WRITING
print '=========== WRITE ===='
os.system('rm -rf /tmp/lala/*; rm -rf /tmp/sfiles/*')
for name in ('ls', 'cat', 'df'):
    os.system('cp ' + '/bin/' + name +' /tmp/sfiles/')
    f = file('/tmp/sfiles/' + name, 'rb')
    smb.put(f, u'\\' + name)
    f.close()
    os.system('md5sum ' + '/tmp/sfiles/' + name)
    os.system('md5sum ' + '/tmp/lala/' + name)

files = smb.dir(u'\\*')
for f in files:
    print f['FileName']
