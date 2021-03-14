#!/usr/bin/env python
##ImmunityHeader v1 
################################################################################
## File       :  Struct.py
## Description:  Generic binary structure class
##            :  
## Created_On :  Mon Nov 29 15:15:18 2010
## Created_By :  Chris
## Modified_On:  Fri Oct 20 00:49:12 EDT 2017
## Modified_By:  Ronald
##
## (c) Copyright 2010-2017, Immunity, Inc. all rights reserved.
################################################################################

import copy
import struct
import traceback
from serialize import *
from error import *

class Struct(Serializable):
    def __init__(self, data=None, **kwargs):
        if not hasattr(self, 'st'):
            raise AbstractAttributeError(type(self), 'st')

        self.value = {}
        self.type  = {}

        for member in self.st:
            mkey, mtype, mdefault, mdeserialize = self._unpack_member(member)

            if not isinstance(mtype, (str, type)):
                msg = "unsupported type field for member '{0}': expected 'type', got '{1}'"
                raise TypeError(msg.format(mkey, type(mdefault).__name__))

            if callable(mdefault):
                self.value[mkey] = mdefault()
            # XXX: decorator + descriptor binding hack. FML.
            elif hasattr(mdefault, '__func__') and callable(mdefault.__func__):
                self.value[mkey] = mtype(mdefault.__func__())
            else:
                self.value[mkey] = mdefault

            self.type[mkey] = mtype

        if data is not None:
            self.unpack(data)

        # Override the defaults based on kwargs.
        for key, value in kwargs.iteritems():
            self.value[key] = value

    def _unpack_member(self, member):
        return (list(member) + [None])[:4]

    def __getitem__(self, key):
        if key not in self.value:
            msg = "'{0}' is not a structure member'"
            raise KeyError(msg.format(key))

        return self.value[key]

    def __setitem__(self, key, value):
        if key not in self.value:
            msg = "'{0}' is not a structure member'"
            raise KeyError(msg.format(key))

        if not isinstance(self.type[key], str) and not isinstance(value, self.type[key]):
            msg = "unsupported type for member '{0}': expected '{1}', got '{2}'"
            raise TypeError(msg.format(key, self.type[key].__name__, type(value).__name__))
        self.value[key] = value

    def offsetof(self, key, context=None):
        return self.calcsize(context, key)

    def calcsize(self, context=None, key=None):
        if context is None:
            context = SerializationContext()
        else:
            # We don't want to change the context provided when simply
            # determining the size of the object.
            context = copy.deepcopy(context)

        # The size of the object is unrelated to the offset. We record
        # the start offset so we can subtract it later.
        start = context.offset
        for member in self.st:
            mkey, mtype, mdefault, mdeserialize = self._unpack_member(member)
            if key is not None and key == mkey:
                break

            if isinstance(mtype, str):
                context.offset += struct.calcsize(mtype)
            else:
                value = self[mkey]
                if isinstance(value, str):
                    context.offset += len(value)
                else:
                    context.offset += self[mkey].size(context)

        return context.offset - start

    def size(self, context=None):
        return self.calcsize(context)

    def serialize(self, context=None):
        if context is None:
            context = SerializationContext()

        data = ''
        for member in self.st:
            mkey, mtype, mdefault, mdeserialize = self._unpack_member(member)

            if isinstance(mtype, str):
                chunk = struct.pack(mtype, self.value[mkey])
                context.offset += len(chunk)
            else:
                value = self.value[mkey]
                if not isinstance(value, mtype):
                    msg = "'{}.{}' has type '{}' instead of '{}'"
                    msg = msg.format(self.__class__.__name__, mkey,
                                     mtype.__name__, type(value).__name__)
                    raise SerializationError(msg)

                if isinstance(value, str):
                    chunk = value
                    context.offset += len(chunk)
                else:
                    chunk = value.serialize(context)

            data += chunk

        return data

    @classmethod
    def deserialize(cls, data, context=None):
        if not hasattr(cls, 'st'):
            raise AbstractAttributeError(cls, 'st')

        if context is None:
            context = SerializationContext()

        #print "Struct.deserialize(off=%d)" % context.offset, data.encode('hex')[:50]

        obj = cls()
        start = end = 0
        for member in obj.st:
            mkey, mtype, mdefault, mdeserialize = (list(member) + [None])[:4]

            #print "---- ROUND: %s [off=%d]" % (mkey, context.offset)

            if isinstance(mtype, str):
                #print "%s.unpack(off=%d)" % (mtype, context.offset)
                try:
                    size = struct.calcsize(mtype)
                    end += size
                    obj.value[mkey] = struct.unpack(mtype, data[start:end])[0]
                    context.offset += size
                except:
                    tb = traceback.format_exc()
                    raise DeserializationError(tb)
            else:
                obj_context     = copy.deepcopy(context)

                # Set self/key/type/value in the deserialization context.
                context.self    = obj
                context.key     = mkey
                context.type    = mtype
                context.default = mdefault

                # Construct the arguments to pass to 'deserialize'.
                args = ()
                if mdeserialize is not None:
                    args = mdeserialize(context)

                #print mkey, mtype, data[start:].encode('hex')[:40], args, context
                # Call the deserialization function.
                obj.value[mkey] = mtype.deserialize(data[start:], *args, context=context)
                # Ensure these don't persist to earlier catch bugs.
                del context.self, context.key, context.type, context.default

                size            = obj.value[mkey].size(obj_context)
                end            += size
                context.offset += size

            start = end

        return obj

    def pack(self):
        data = ''
        for field in self.st:
            if field[1] != '0s':
                data += struct.pack(field[1], self.value[field[0]])

        return data

    def unpack(self, data):
        pos = 0
        for i in (range(0, len(self.st))):
            npos = pos + struct.calcsize(self.st[i][1])
            self.value[self.st[i][0]] = struct.unpack(self.st[i][1], data[pos:npos])[0]
            pos = npos

    def debugprint(self):
        print(str(self))

    def __str__(self):
        members = ((m[0], self.value[m[0]]) for m in self.st)
        return "\n".join("{} = {}".format(k, v) for k, v in members)

    def __repr__(self):
        return '{}(**{})'.format(type(self).__name__, pformat(self.value))
