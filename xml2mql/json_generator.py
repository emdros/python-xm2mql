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
import json

from .base_handler import BaseHandler
from . import emdros_util

class JSONGeneratorHandler(BaseHandler):
    def __init__(self, default_document_name, default_token_name):
        BaseHandler.__init__(self)
        
        self.bElementHasPCHAR = False

        self.default_document_name = default_document_name
        self.default_token_name = default_token_name

        self.element2ObjectTypeName = {}
        self.objectTypeName2Element = {
            # Don't use the default token
            # name for elements names...
            self.default_token_name : "",
            
            # Don't use the default document name for elements...            
            self.default_document_name : "", 
        }

        self.init_default_script()

    def init_default_script(self):
        self.script = {}
        self.script["global_parameters"] = {
            "docIndexFeatureName" : "xmlindex",
            "docIndexIncrementBeforeObjectType" : {
                self.default_token_name : 1,
            },
            "documentObjectTypeName" : self.default_document_name,
            "tokenObjectTypeNameList" : [
                self.default_token_name
            ],
        }
        self.script["handled_elements"] = {}
        self.script["ignored_elements"] = []
        self.script["nixed_elements"] = []

    def createOrUpdateElement(self, tag, attributes):
        if tag in self.script["handled_elements"]:
            self.updateElement(tag, attributes, False)
        else:
            self.createElement(tag, attributes)

    def updateElement(self, tag, attributes, bHasTokens):
        if len(attributes) > 0:
            self.script["handled_elements"][tag].setdefault("attributes", {})
            for key in attributes.keys():
                self.script["handled_elements"][tag]["attributes"][key] = {
                    "featureName" : self.makeIdentifier(key),
                    "featureType" : "STRING"
                }

        if bHasTokens:
            self.script["handled_elements"][tag]["tokenObjectTypeName"] = self.default_token_name

    def createElement(self, tag, attributes):
        self.script["handled_elements"][tag] = {
            "objectTypeName" : self.makeObjectTypeName(tag),
            "tokenObjectTypeName" : None,
            "minimumMonadLength" : 1,
        }
        if len(attributes) > 0:
            self.script["handled_elements"][tag]["attributes"] = {}
            for key in attributes.keys():
                self.script["handled_elements"][tag]["attributes"][key] = {
                    "featureName" : self.makeIdentifier(key),
                    "featureType" : "STRING"
                }

    def makeObjectTypeName(self, element_name):
        if element_name in self.element2ObjectTypeName:
            return self.element2ObjectTypeName[element_name]
        else:
            suggestion = self.makeIdentifier(element_name)
            while suggestion in self.objectTypeName2Element and \
                  self.objectTypeName2Element[suggestion] != element_name:
                suggestion += "_"

            while suggestion == self.default_document_name:
                suggestion += "_"

            while suggestion in self.script["global_parameters"]["tokenObjectTypeNameList"]:
                suggestion += "_"
                
            self.objectTypeName2Element[suggestion] = element_name
            self.element2ObjectTypeName[element_name] = suggestion

            return suggestion

    def makeIdentifier(self, instring):
        result = []

        for c in instring:
            c_ord = ord(c)

            if c_ord >= ord('a') and c_ord <= ord('z'):
                c_out = c
            elif c_ord >= ord('A') and c_ord <= ord('Z'):
                c_out = c
            elif c_ord >= ord('0') and c_ord <= ord('9'):
                c_out = c
            else:
                c_out = '_'

            result.append(c_out)

        if len(result) == 0:
            # instring was empty. Append a single "_".
            result.append("_")
        else:
            # Is the first character a digit?
            if ord(result[0]) >= ord('0') and ord(result[0]) <= ord('9'):
                # Yes, so prepend a _
                result = ['_'] + result

        # Identifiers are case-insensitive, so lower-case the string
        # for uniformity.
        suggestion = "".join(result).lower()

        if suggestion in emdros_util.emdros_reserved_word_set:
            suggestion += "_"

        return suggestion

    def updateTokenObjectTypeName(self, element_name):
        if element_name in self.script["handled_elements"]:
            self.script["handled_elements"][element_name]["tokenObjectTypeName"] = self.default_token_name

    def handleChars(self, chars_before, tag, bIsEndTag):
        stripped_chars = chars_before.strip()
        if len(stripped_chars) > 0:
            if bIsEndTag:
                element_name = tag
                self.updateTokenObjectTypeName(element_name)
            else:
                if len(self.elemstack) >= 2:
                    element_name = self.elemstack[-2]
                    self.updateTokenObjectTypeName(element_name)
                else:
                    pass # Ignore characters before first element.


    def handleUnknownElementStart(self, tag, attributes):
        """Must return True if element was handled, False otherwise."""
        self.createOrUpdateElement(tag, attributes)
        
        return True

    def handleUnknownElementEnd(self, tag):
        if tag in self.script["handled_elements"]:
            return True
        else:
            assert False, "End-tag </%s> not handled at start." % tag

    def doCommand(self, fout):
        fout.write(json.dumps(self.script).encode('utf-8'))
