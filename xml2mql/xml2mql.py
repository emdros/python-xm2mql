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

import tokenize

def usage():
    sys.stderr.write("""
Usage:
     python3 xml2mql.py command [options] jsonfilename.json [filename.xml...]

COMMANDS
     json     Generate an example JSON script, put it into jsonfilename.json
     mql      Generate MQL based on jsonfilename.json

""")


def getBasename(pathname):
    filename = pathname.split("/")[-1]
    if "." in filename:
        basename = ".".join(filename.split(".")[:-1])
    else:
        basename = filename
    return basename


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
        assert False, "FIXME: Implement"
        pass
    

########################################
##
## MQL string mangling
##
########################################
special_re = re.compile(r"[\n\t\"\\]")

special_dict = {
    '\n' : '\\n',
    '\t' : '\\t',
    '"' : '\\"',
    '\\' : '\\\\',
}

upper_bit_re = re.compile(b'[\x80-\xff]')

def special_sub(mo):
    c = mo.group(0)
    assert len(c) == 1
    return special_dict[c]

def upper_bit_sub(mo):
    c = mo.group(0)
    assert len(c) == 1
    return "\\x%02x" % ord(c)

def mangleMQLString(ustr):
    result = special_re.sub(special_sub, ustr.encode('utf-8'))
    result = upper_bit_re.sub(upper_bit_sub, result)
    return result

    

def mangle_XML_entities(s):
    r = s.replace("&", "&amp;")
    r = r.replace("<", "&lt;")
    r = r.replace(">", "&gt;")
    r = r.replace("\"", "&quot;")
    return r



class Token:
    def __init__(self, monad, prefix, surface, suffix, xmlindex, id_d):
        self.monad = monad
        self.wholesurface = prefix + surface + suffix
        self.prefix = prefix
        self.surface = surface
        self.suffix = suffix
        self.xmlindex = xmlindex
        self.id_d = id_d

    def dumpMQL(self, f):
        surface_lowcase = self.surface.lower();
        surface_stripped_lowcase = surface_re.findall(surface_lowcase)[0][1]

        f.write("CREATE OBJECT FROM MONADS={%d}\n" % self.monad)
        if self.id_d != 0:
            f.write("WITH ID_D=%d\n" % self.id_d)
        f.write(("[surface_stripped_lowcase:=\"%s\";\n" % (mangleMQLString(surface_stripped_lowcase))).encode('utf-8'))
        f.write(("wholesurface:=\"%s\";xmlindex:=%d;\n]\n" % (mangleMQLString(self.wholesurface), self.xmlindex)).encode('utf-8'))


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

    def dumpMQL(self, fout):
        fout.write("CREATE OBJECT FROM MONADS={%d-%d}" % (self.fm, self.lm))
        if self.id_d != 0:
            fout.write("WITH ID_D=%d" % self.id_d)
        fout.write("[")
        for (key,value) in self.nonStringFeatures.items():
            print >>fout, "  %s:=%s;" % (key, value)
        for (key,value) in self.stringFeatures.items():
            print >>fout, ("  %s:=\"%s\";" % (key, mangleMQLString(value))).encode('utf-8')
        fout.write("]\n")

class BaseHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.elemstack = []
        self.charstack = []
        self.nixing_stack = []

        self.nixed_elements = set()
        self.ignored_elements = set()
        self.handled_elements = set()

    def getCurElement(self):
        if len(self.elemstack) == 0:
            return ""
        else:
            return self.elemstack[-1]
        
    def characters(self, data):
        self.charstack.append(data)

    def handleChars(self, chars_before, tag, bIsEndTag):
        pass

    def startDocument(self):
        pass

    def endDocument(self):
        pass

    def startElement(self, tag, attributes):
        self.elemstack.append(tag)

        chars = "".join(self.charstack)
        del self.charstack
        self.charstack = []

        self.handleChars(chars, tag, False)

        self.doActionsBeforeHandleElementStart(tag, attributes)
        
        if tag in self.nixed_elements:
            self.nixing_stack.append(tag)
        elif len(self.nixing_stack) != 0:
            pass
        elif tag in self.handled_elements:
            self.handleElementStart(tag, attributes)
        elif tag in self.ignored_elements:
            pass
        elif self.handleUnknownElementStart(tag, attributes):
            pass
        else:
            raise Exception(("Error: Unknown start-tag '<" + tag + ">'").encode('utf-8'))

        self.doActionsAfterHandleElementStart(tag, attributes)

    def handleElementStart(self, tag, attributes):
        pass

    def handleUnknownElementStart(self, tag, attributes):
        """Must return True if element was handled, False otherwise."""
        return False

    def doActionsBeforeHandleElementStart(self, tag, attributes):
        pass
    
    def doActionsAfterHandleElementStart(self, tag, attributes):
        pass
        

    def endElement(self, tag):
        chars = "".join(self.charstack)
        del self.charstack
        self.charstack = []

        self.handleChars(chars, tag, True)

        self.doActionsBeforeHandleElementEnd(tag)

        if len(self.nixing_stack) != 0 and self.nixing_stack[-1] == tag:
            self.nixing_stack.pop()
        elif len(self.nixing_stack) != 0:
            pass
        elif tag in self.handled_elements:
            self.handleElementEnd(tag)
        elif tag in self.ignored_elements:
            pass
        elif self.handleUnknownElementEnd(tag):
            pass
        else:
            raise Exception(("Error: Unknown end-tag " + tag).encode('utf-8'))

        self.doActionsAfterHandleElementEnd(tag)

        self.elemstack.pop()


    def handleElementEnd(self, tag):
        pass

    def handleUnknownElementEnd(self, tag):
        """Must return True if element was handled, False otherwise."""
        return False

    def doActionsBeforeHandleElementEnd(self, tag):
        pass
    
    def doActionsAfterHandleElementEnd(self, tag):
        pass
        
    def doCommand(self, fout):
        pass

        
        

class JSONGeneratorHandler(BaseHandler):
    def __init__(self, default_token_name):
        BaseHandler.__init__(self)
        
        self.bElementHasPCHAR = False

        self.default_token_name = default_token_name

        self.element2ObjectTypeName = {}
        self.objectTypeName2Element = {
            self.default_token_name : "" # Don't use the default token
                                         # name for elements names...
        }

        self.init_default_script()

    def init_default_script(self):
        self.script = {}
        self.script["global_parameters"] = {
            "docIndexFeatureName" : "xmlindex",
            "docIndexIncrementBeforeObjectType" : {
                self.default_token_name : 1,
            },
            "tokenObjectTypeNameList" : [
                self.default_token_name
            ]
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
        real_result = "".join(result).lower()

        return real_result

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

class MQLGeneratorHandler(BaseHandler):
    def __init__(self, json_file, first_monad, first_id_d):
        BaseHandler.__init__(self)

        self.objstacks = {} # objectTypename -> [object-list]
        self.objects = {} # objectTypeName -> [object-list]
        
        self.script = json.load(json_file)

        # objectTypeName -> ObjectTypeDescription
        self.schema = {}

        self.curdocindex = 1
        self.curmonad = first_monad
        self.curid_d = first_id_d

        self.docIndexFeatureName = ""

        self.tokens = {}

        self.initialize()

        self.makeSchema()

    def initialize(self):
        for tokenObjectTypeName in self.script["global_parameters"]["tokenObjectTypeNameList"]:
            self.tokens.setdefault(tokenObjectTypeName, [])

        self.docIndexFeatureName = self.script["global_parameters"]["docIndexFeatureName"]

    def makeSchema(self):
        for tokenObjectTypeName in self.scripts["global_parameters"]:
            objectTypeDescription = ObjectTypeDescription(tokenObjectTypeName)

            for (featureName, featureType) in [
                    ("pre", "STRING FROM SET"),
                    ("surface", "STRING WITH INDEX"),
                    ("post", "STRING FROM SET"),
                    ("surface_lowcase", "STRING WITH INDEX")]:
                objectTypeDescription.addFeature(featureName, featureType)

            objectTypeDescription.addFeature(self.docIndexFeatureName, "INTEGER")
            self.schema[tokenObjectTypeName] = objectTypeDescription
            

        for element_name in self.script["handled_elements"]:
            objectTypeName = self.script["handled_elements"][element_name]["objectTypeName"]
            objectTypeDescription = ObjectTypeDescription(objectTypeName)

            if "attributes" in self.script["handled_elements"][element_name]:
                for key in self.script["handled_elements"][element_name]["attributes"]:
                    featureName = self.script["handled_elements"][element_name]["attributes"][key].getdefault(featureName, "")
                    featureType = self.script["handled_elements"][element_name]["attributes"][key].getdefault(featureType, "")

                    if featureName and featureType:
                        objectTypeDescription.addFeature(featureName, featureType)

            # Add docIndex feature
            objectTypeDescription.addFeature(self.docIndexFeatureName, "INTEGER")

            self.schema[objectTypeName] = objectTypeDescription

    def handleChars(self, chars_before, tag, bIsEndTag):
        if not bIsEndTag:
            bDoIt = False
        elif tag not in self.script["handled_elements"]:
            bDoIt = False
        elif self.script["handled_elements"][tag].getdefault("tokenObjectTypeName", None) != None:
            bDoIt = True
        else:
            bDoIt = False
            
        if bDoIt:
            token_list = tokenize.tokenize(chars_before)

            tokenObjectTypeName = self.script["handled_elements"][tag]["tokenObjectTypeName"]

            for (prefix, surface, suffix) in token_list:
                self.createToken(tokenObjectTypeName, prefix, surface, suffix)

    def createToken(self, tokenObjectTypeName, prefix, surface, suffix):
        docindex_increment = min(1, self.script["global_parameters"]["docIndexCrementBeforeObjectType"].getdefault(tokenObjectTypeName, 1))
        self.curdocindex += docindex_increment
        
        t = Token(self.curmonad, prefix, surface, suffix, self.curdocindex, self.curid_d)

        self.curmonad += 1
        self.curid_d += 1
        self.curdocindex += 1

        self.tokens[tokenObjectTypeName].append(t)

    def createObject(self, objectTypeName):
        obj = SRObject(objectTypeName, self.curmonad)
        obj.setNonStringFeature(self.docIndexFeatureName, self.curdocindex)
        self.curdocindex += 1

        self.objstacks.setdefault(objectTypeName, []).append(obj)

        return obj

    def endObject(self, objectTypeName):
        obj = self.objstacks[objectTypeName].pop()
        assert obj.objectTypeName == objectTypeName
        
        obj.setLastMonad(self.curmonad - 1)
        
        self.objects.setdefault(objectTypeName, []).append(obj)
        
        return obj

    def doCommand(self, fout):
        # FIXME: Dump MQL
        pass

if len(sys.argv) < 4:
    usage()
    sys.exit(1)
else:
    command = sys.argv[1]

    if command in ["json", "mql"]:
        pass
    else:
        usage()
        sys.exit(1)
        
    json_filename = sys.argv[2]
    xml_filenames = sys.argv[3:]

    first_monad = 1
    first_id_d = 1
    default_token_name = "token"

    if command == "mql":
        handler = MQLGeneratorHandler(json_filename, first_monad, first_id_d)
    elif command == "json":
        handler = JSONGeneratorHandler(default_token_name)
    else:
        usage()
        sys.exit(1)

    for filename in xml_filenames:
        fin = open(filename, "rb")
        sys.stderr.write("Now reading: %s ...\n" % filename)
        xml.sax.parse(fin, handler)
        fin.close()

    if command == "mql":
        handler.doCommand(sys.stdout)
    elif command == "json":
        sys.stderr.write("Now writing: %s ...\n" % json_filename)

        fout = open(json_filename, "wb")
        handler.doCommand(fout)
        fout.close() 

        sys.stderr.write("... Done!\n\n")
    else:
        assert False, "Unhandled command: %s\n" % command

