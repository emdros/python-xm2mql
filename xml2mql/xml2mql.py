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

from . import json_generator
from . import mql_generator
from . import renderjson_generator

def getBasename(pathname):
    basename = os.path.split(pathname)[-1]
    return basename

def mangle_XML_entities(s):
    r = s.replace("&", "&amp;")
    r = r.replace("<", "&lt;")
    r = r.replace(">", "&gt;")
    r = r.replace("\"", "&quot;")
    return r

def generateJSON(json_filename_or_file, xml_filename_list, default_document_name = "document", default_token_name = "token"):
    handler = json_generator.JSONGeneratorHandler(default_document_name, default_token_name)

    for filename in xml_filename_list:
        fin = open(filename, "rb")
        sys.stderr.write("Now reading: %s ...\n" % filename)
        xml.sax.parse(fin, handler)
        fin.close()

    if type(json_filename_or_file) == type(""):
        sys.stderr.write("Now writing: %s ...\n" % json_filename_or_file)

        fout = open(json_filename_or_file, "wb")
        handler.doCommand(fout)
        fout.close()
    else:
        sys.stderr.write("Now writing: JSON ...\n")

        handler.doCommand(json_filename_or_file)
        
    sys.stderr.write("... Done!\n\n")

    
def generateRenderJSON(json_filename_or_file, render_json_filename):
    if type(json_filename_or_file) == type(""):
        sys.stderr.write("Now reading: JSON file %s ...\n" % json_filename_or_file)
        fin = open(json_filename_or_file, "rb")
        handler = renderjson_generator.RenderJSONGeneratorHandler(fin)
        fin.close()
    else:
        sys.stderr.write("Now reading: JSON ...\n")
        handler = renderjson_generator.RenderJSONGeneratorHandler(json_filename_or_file)

    sys.stderr.write("Now writing: %s...\n" % render_json_filename)
    handler.doCommand(open(render_json_filename, "wb"))
    sys.stderr.write("... Done!\n")

    
def generateMQL(json_filename, xml_filenames_list, first_monad, first_id_d, defualt_document_name = "document", default_token_name = "token"):
    if json_filename == None or json_filename == "":
        json_file = tempfile.NamedTemporaryFile()

        # Generate JSON first...
        generateJSON(json_file, xml_filenames_list, default_document_name, default_token_name)

        # Rewind file
        json_file.seek(0)
    else:
        json_file = open(json_filename, "rb")

    handler = mql_generator.MQLGeneratorHandler(json_file, sys.stdout, first_monad, first_id_d)

    json_file.close()
    
    for filename in xml_filenames_list:
        fin = open(filename, "rb")
        sys.stderr.write("Now reading: %s ...\n" % filename)
        handler.setBasename(getBasename(filename))
        xml.sax.parse(fin, handler)
        fin.close()
