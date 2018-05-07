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

from . import latin_tokenizer
from . import emdros_util
from .base_handler import BaseHandler

def getBasename(pathname):
    basename = os.path.split(pathname)[-1]
    return basename

def mangle_XML_entities(s):
    r = s.replace("&", "&amp;")
    r = r.replace("<", "&lt;")
    r = r.replace(">", "&gt;")
    r = r.replace("\"", "&quot;")
    return r

        


class MQLGeneratorHandler(BaseHandler):
    def __init__(self, json_file, mql_file, first_monad, first_id_d):
        BaseHandler.__init__(self)

        self.bSchemaHasBeenDumped = False
        self.basename = None

        self.objstacks = {} # objectTypename -> [object-list]
        self.objects = {} # objectTypeName -> [object-list]
        
        self.script = json.loads(b"".join(json_file.readlines()).decode('utf-8'))
        self.mql_file = mql_file

        # objectTypeName -> emdros_util.ObjectTypeDescription
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
            objectTypeDescription = emdros_util.ObjectTypeDescription(tokenObjectTypeName, "WITH SINGLE MONAD OBJECTS")

            for (featureName, featureType) in [
                    ("pre", "STRING FROM SET"),
                    ("surface", "STRING WITH INDEX"),
                    ("post", "STRING FROM SET"),
                    ("surface_lowcase", "STRING WITH INDEX")]:
                objectTypeDescription.addFeature(featureName, featureType)

            objectTypeDescription.addFeature(self.docIndexFeatureName, "INTEGER")
            self.schema[tokenObjectTypeName] = objectTypeDescription

        objectTypeDescription = emdros_util.ObjectTypeDescription(self.documentObjectTypeName, "WITH SINGLE RANGE OBJECTS")
        objectTypeDescription.addFeature("basename", "STRING")
        objectTypeDescription.addFeature(self.docIndexFeatureName, "INTEGER")
        self.schema[self.documentObjectTypeName] = objectTypeDescription

        for element_name in self.script["handled_elements"]:
            objectTypeName = self.script["handled_elements"][element_name]["objectTypeName"]
            objectRangeType = self.script["handled_elements"][element_name].get("objectRangeType", "WITH SINGLE RANGE OBJECTS")
            objectTypeDescription = emdros_util.ObjectTypeDescription(objectTypeName, objectRangeType)

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
        obj = emdros_util.SRObject(objectTypeName, self.curmonad)
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

        
