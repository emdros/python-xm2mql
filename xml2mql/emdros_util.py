# -*- coding: utf-8 -*-
#
# XML to Emdros MQL data importer.
#
#
# Copyright (C) 2018  Sandborg-Petersen Holding ApS, Denmark
#
# Made available under the MIT License.
#
# See the file LICENSE in the root of the sources for the full license
# text.
#
#
import sys
import os
import re
import json
import xml.sax

emdros_reserved_word_set = set([
    "create",
    "object",
    "type",
    "list",
    "index",
    "sum",
    "avg",
    ])

class ObjectTypeDescription:
    def __init__(self, objectTypeName, objectRangeType):
        self.objectTypeName = objectTypeName
        if objectRangeType: # != None && != ""
            self.objectRangeType = objectRangeType
        else:
            self.objectRangeType = "WITH SINGLE RANGE OBJECTS"

        self.features = {} # featureName -> featureType

    def addFeature(self, featureName, featureType):
        assert featureName and featureType

        self.features[featureName] = featureType

    def dumpMQL(self, fout):
        result = []

        result.append("CREATE OBJECT TYPE")
        result.append(self.objectRangeType)
        result.append("[%s" % self.objectTypeName)
        for featureName in sorted(self.features):
            featureType = self.features[featureName];
            result.append("  %s : %s;" % (featureName, featureType))
        result.append("]")
        result.append("GO")


        result.append("")
        result.append("")

        fout.write("\n".join(result))
    

########################################
##
## MQL string mangling
##
########################################
special_re = re.compile(r"[\r\n\t\"\\]")

special_dict = {
    '\r' : '\\r',
    '\n' : '\\n',
    '\t' : '\\t',
    '"' : '\\"',
    '\\' : '\\\\',
}


def special_sub(mo):
    c = mo.group(0)
    assert len(c) == 1
    return special_dict[c]


def mangleMQLString(ustr):
    result = special_re.sub(special_sub, ustr)
    return result

    
class SRObject:
    def __init__(self, objectTypeName, starting_monad):
        self.objectTypeName = objectTypeName
        self.fm = starting_monad
        self.lm = starting_monad
        self.stringFeatures = {}
        self.nonStringFeatures = {}
        self.id_d = 0

    def setID_D(self, id_d):
        self.id_d = id_d

    def setStringFeature(self, name, value):
        self.stringFeatures[name] = value

    def setNonStringFeature(self, name, value):
        self.nonStringFeatures[name] = value

    def getStringFeature(self, name):
        return self.stringFeatures[name]

    def setLastMonad(self, ending_monad):
        if ending_monad < self.fm:
            self.lm = self.fm
        else:
            self.lm = ending_monad

    def getMonadLength(self):
        return self.lm - self.fm + 1

    
    def dumpMQL(self, fout):
        result = []
        if self.fm == self.lm:
            result.append("CREATE OBJECT FROM MONADS={%d}" % self.fm)
        else:
            result.append("CREATE OBJECT FROM MONADS={%d-%d}" % (self.fm, self.lm))
        if self.id_d != 0:
            result.append("WITH ID_D=%d" % self.id_d)
        result.append("[")
        for (key,value) in self.nonStringFeatures.items():
            result.append("  %s:=%s;" % (key, value))
        for (key,value) in self.stringFeatures.items():
            result.append("  %s:=\"%s\";" % (key, mangleMQLString(value)))
        result.append("]")
        result.append("")

        str_result = "\n".join(result)
        fout.write(str_result)
        
