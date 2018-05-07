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

class RenderJSONGeneratorHandler:
    def __init__(self, json_file):
        self.script = json.loads(b"".join(json_file.readlines()).decode('utf-8'))

        self.make_default_render()

        self.make_render()

    def make_default_render(self):
        self.render = {
            "fetchinfo" : {
                "base" : {
                    "object_types": {
                    },
                    "prepend_XML_declaration" : True,
                }
            },
            "renderinfo" : {
                "base" : {
                    "elements" : {
                    }
                }
            }
        }

    def make_render(self):
        self.docindex = self.script["global_parameters"]["docIndexFeatureName"]

        for elementName in sorted(self.script["handled_elements"]):
            self.handleElement(elementName)

        for tokenObjectTypeName in self.script["global_parameters"]["tokenObjectTypeNameList"]:
            get_list = [
                "pre",
                "surface",
                "post"
            ]
            obj = {
                "docindexfeature" : self.docindex,
                "start" : "{{ feature 0 }}{{ feature 1 }}{{ feature 2 }}",
                "get" : get_list
            }

            self.render["fetchinfo"]["base"]["object_types"][tokenObjectTypeName] = obj


    def handleElement(self, elementName):
        assert elementName in self.script["handled_elements"]

        objectTypeName = self.script["handled_elements"][elementName]["objectTypeName"]
        featureList = []

        if "attributes" in self.script["handled_elements"][elementName]:
            for key in self.script["handled_elements"][elementName]["attributes"]:
                featureName = self.script["handled_elements"][elementName]["attributes"][key]["featureName"]
                featureList.append((featureName, key))

        self.handleObjectType(elementName, objectTypeName, featureList)

        start_list = []
        start_list.append("<")
        start_list.append(elementName)

        for (featureName, attributeName) in featureList:
            start_list.append(" %s=\"{{ attribute '%s' }}\"" % (attributeName, attributeName))

        start_list.append(">")
        
        start_str = "".join(start_list)

        end_str = "</%s>" % elementName
        
        element_obj = {
            "docindexfeature" : self.docindex,
            "start" : start_str,
            "end" : end_str
            }

        self.render["renderinfo"]["base"]["elements"][elementName] = element_obj


    def handleObjectType(self, elementName, objectTypeName, featureList):
        start_list = []
        start_list.append("<")
        start_list.append(elementName)
        index = 0
        get_list = []
        for (featureName, attributeName) in featureList:
            start_list.append(" %s=\"{{ feature %d }}\"" % (attributeName, index))
            get_list.append(featureName)
            index += 1
            
        start_list.append(">")

        end_str = "</" + elementName + ">",
       
        obj = {
            "end" : end_str,
            "start" : "".join(start_list)
        }

        if len(get_list) > 0:
            obj["get"] = get_list
        
        self.render["fetchinfo"]["base"]["object_types"][objectTypeName] = obj
 
    def doCommand(self, fout):
        fout.write(json.dumps(self.render).encode('utf-8'))
