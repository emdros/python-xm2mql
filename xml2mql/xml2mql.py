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

from . import latin_tokenizer

def usage():
    sys.stderr.write("""
Usage:
     python3 xml2mql.py command [options] jsonfilename.json [filename.xml...]

COMMANDS
     json     Generate an example JSON script, put it into jsonfilename.json
     mql      Generate MQL based on jsonfilename.json

""")

emdros_reserved_word_set = set([
    "create",
    "object",
    "type",
    "list",
    "index",
    "sum",
    "avg",
    ])
    

def getBasename(pathname):
    basename = os.path.split(pathname)[-1]
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

        result = []
        result.append("CREATE OBJECT FROM MONADS={%d}" % self.monad)

        if self.id_d != 0:
            result.append("WITH ID_D=%d" % self.id_d)

        result.append("[")
        for (featureName, featureValue) in [
                ("pre", self.prefix),
                ("surface", self.surface),
                ("post", self.suffix),
                ("surface_lowcase", surface_lowcase),
               ]:
            result.append("%s:=\"%s\";" % (featureName, mangleMQLString(featureValue)))
        result.append("xmlindex:=%d;" % self.xmlindex)
        result.append("]")
        result.append("")

        str_result = "\n".join(result)
        f.write(str_result)


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

        if suggestion in emdros_reserved_word_set:
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

class MQLGeneratorHandler(BaseHandler):
    def __init__(self, json_file, mql_file, first_monad, first_id_d):
        BaseHandler.__init__(self)

        self.bSchemaHasBeenDumped = False
        self.basename = None

        self.objstacks = {} # objectTypename -> [object-list]
        self.objects = {} # objectTypeName -> [object-list]
        
        self.script = json.loads(b"".join(json_file.readlines()).decode('utf-8'))
        self.mql_file = mql_file

        # objectTypeName -> ObjectTypeDescription
        self.schema = {}

        self.curdocindex = 1
        self.curmonad = first_monad
        self.curid_d = first_id_d

        self.docIndexFeatureName = ""

        self.initialize()

        self.makeSchema()

    def initialize(self):
        for tokenObjectTypeName in self.script["global_parameters"]["tokenObjectTypeNameList"]:
            self.objects.setdefault(tokenObjectTypeName, [])

        self.docIndexFeatureName = self.script["global_parameters"]["docIndexFeatureName"]

        self.documentObjectTypeName = self.script["global_parameters"].get("documentObjectTypeName", "document")

        for element_name in self.script["handled_elements"]:
            self.handled_elements.add(element_name)
            
        for element_name in self.script["ignored_elements"]:
            self.ignored_elements.add(element_name)
            
        for element_name in self.script["nixed_elements"]:
            self.nixed_elements.add(element_name)
            

    def makeSchema(self):
        for tokenObjectTypeName in self.script["global_parameters"]["tokenObjectTypeNameList"]:
            objectTypeDescription = ObjectTypeDescription(tokenObjectTypeName, "WITH SINGLE MONAD OBJECTS")

            for (featureName, featureType) in [
                    ("pre", "STRING FROM SET"),
                    ("surface", "STRING WITH INDEX"),
                    ("post", "STRING FROM SET"),
                    ("surface_lowcase", "STRING WITH INDEX")]:
                objectTypeDescription.addFeature(featureName, featureType)

            objectTypeDescription.addFeature(self.docIndexFeatureName, "INTEGER")
            self.schema[tokenObjectTypeName] = objectTypeDescription

        objectTypeDescription = ObjectTypeDescription(self.documentObjectTypeName, "WITH SINGLE RANGE OBJECTS")
        objectTypeDescription.addFeature("basename", "STRING")
        objectTypeDescription.addFeature(self.docIndexFeatureName, "INTEGER")
        self.schema[self.documentObjectTypeName] = objectTypeDescription

        for element_name in self.script["handled_elements"]:
            objectTypeName = self.script["handled_elements"][element_name]["objectTypeName"]
            objectRangeType = self.script["handled_elements"][element_name].get("objectRangeType", "WITH SINGLE RANGE OBJECTS")
            objectTypeDescription = ObjectTypeDescription(objectTypeName, objectRangeType)

            if "attributes" in self.script["handled_elements"][element_name]:
                for key in self.script["handled_elements"][element_name]["attributes"]:
                    featureName = self.script["handled_elements"][element_name]["attributes"][key].get("featureName", "")
                    featureType = self.script["handled_elements"][element_name]["attributes"][key].get("featureType", "")

                    if featureName and featureType:
                        objectTypeDescription.addFeature(featureName, featureType)

            # Add docIndex feature
            objectTypeDescription.addFeature(self.docIndexFeatureName, "INTEGER")

            self.schema[objectTypeName] = objectTypeDescription

    def setBasename(self, basename):
        self.basename = basename
            
    def handleChars(self, chars_before, tag, bIsEndTag):
        if not bIsEndTag:
            bDoIt = False
        elif tag not in self.script["handled_elements"]:
            bDoIt = False
        elif self.script["handled_elements"][tag].get("tokenObjectTypeName", None) != None:
            bDoIt = True
        else:
            bDoIt = False
            
        if bDoIt:
            token_list = latin_tokenizer.tokenize_string(chars_before)

            tokenObjectTypeName = self.script["handled_elements"][tag]["tokenObjectTypeName"]

            for (prefix, surface, suffix) in token_list:
                self.createToken(tokenObjectTypeName, prefix, surface, suffix)

    def createToken(self, tokenObjectTypeName, prefix, surface, suffix):
        docindex_increment = min(1, self.script["global_parameters"]["docIndexIncrementBeforeObjectType"].get(tokenObjectTypeName, 1))
        self.curdocindex += docindex_increment

        surface_lowcase = surface.lower()

        t = self.createObject(tokenObjectTypeName)
        t.setStringFeature("pre", prefix)
        t.setStringFeature("surface", surface)
        t.setStringFeature("post", suffix)
        t.setStringFeature("surface_lowcase", surface_lowcase)

        t.setID_D(self.curid_d)
        self.curid_d += 1

        self.curmonad += 1

    def createObject(self, objectTypeName):
        obj = SRObject(objectTypeName, self.curmonad)
        obj.setID_D(self.curid_d)
        self.curid_d += 1
        
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

    def getFeatureType(self, tag, attribute):
        assert tag in self.script["handled_elements"], "Logic error: Tag <%s> not in handled elements." % tag
        assert "attributes" in self.script["handled_elements"][tag], "Logic error: Element %s does not have 'attributes' sub-key, yet getFeatureType() was called." % tag
        return self.script["handled_elements"][tag]["attributes"][attribute].get("featureType", "STRING")

    def featureTypeIsSTRING(self, featureType):
        if "string" in featureType.lower():
            return True
        else:
            return False

    def startDocument(self):
        obj = self.createObject(self.documentObjectTypeName)
        if self.basename != None:
            obj.setStringFeature("basename", self.basename)

    def endDocument(self):
        self.endObject(self.documentObjectTypeName)
        self.basename = None

        if not self.bSchemaHasBeenDumped:
            self.mql_file.write("""//
// Dumped with xml2emdrosmql.py.
//

""")
            self.dumpMQLSchema(self.mql_file)
            self.bSchemaHasBeenDumped = True

        self.dumpMQLObjects(self.mql_file)
            
        
    def handleElementStart(self, tag, attributes):
        if tag not in self.script["handled_elements"]:
            return False
        else:
            objectTypeName = self.script["handled_elements"][tag]["objectTypeName"]
            obj = self.createObject(objectTypeName)

            if "attributes" in self.script["handled_elements"][tag]:
                for key in self.script["handled_elements"][tag]["attributes"]:
                    if key in attributes:
                        value = attributes[key]

                        featureName = self.script["handled_elements"][tag]["attributes"][key]["featureName"]
                        featureType = self.getFeatureType(tag, key)
                        if self.featureTypeIsSTRING(featureType):
                            obj.setStringFeature(featureName, value)
                        else:
                            obj.setNonStringFeature(featureName, value)

            return True

    def handleElementEnd(self, tag):
        if tag not in self.script["handled_elements"]:
            return False
        else:
            objectTypeName = self.script["handled_elements"][tag]["objectTypeName"]
            obj = self.endObject(objectTypeName)

            minimumMonadLength = self.script["handled_elements"][tag].get("minimumMonadLength", 1)
            
            while obj.getMonadLength() < minimumMonadLength:
                obj.setLastMonad(self.curmonad)
                self.curmonad += 1

            return True

    
    def dumpMQLSchema(self, fout):
        for objectTypeName in sorted(self.schema):
            objectTypeDescription = self.schema[objectTypeName]
            objectTypeDescription.dumpMQL(fout)
    
    def dumpMQLObjects(self, fout):
        for objectTypeName in sorted(self.objects):
            self.dumpMQLObjectType(fout, objectTypeName, self.objects[objectTypeName])

        del self.objects
        self.objects = {}



    def dumpMQLObjectType(self, fout, objectTypeName, object_list):
        if len(object_list) == 0:
            return
        
        max_in_statement = 50000

        fout.write("CREATE OBJECTS WITH OBJECT TYPE [%s]\n" % objectTypeName)

        count = 0
        for obj in object_list:
            count += 1
            if count == max_in_statement:
                fout.write("GO\n")
                fout.write("CREATE OBJECTS WITH OBJECT TYPE [%s]\n" % objectTypeName)
                count = 0
            obj.dumpMQL(fout)


        fout.write("GO\n")

        
