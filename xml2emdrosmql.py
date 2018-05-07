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
import tempfile
import xml.sax

from xml2mql import xml2mql

def usage():
    sys.stderr.write("""
Usage:
     python3 xml2mql.py command [options] jsonfilename.json [filename.xml...]

COMMANDS
     json        Generate an example JSON script, put it into jsonfilename.json
     mql         Generate MQL based on jsonfilename.json
     renderjson  Generate RenderObjects JSON based on jsonfilename.json

""")



    

if __name__ == '__main__':
    if len(sys.argv) < 4:
        usage()
        sys.exit(1)
    else:
        command = sys.argv[1]
        
        if command in ["json", "mql", "renderjson"]:
            pass
        else:
            usage()
            sys.exit(1)
        
        json_filename = sys.argv[2]
        xml_filenames = sys.argv[3:]

        first_monad = 1
        first_id_d = 1
        default_token_name = "token"
        default_document_name = "document"

        if command == "mql":
            xml2mql.generateMQL(json_filename, xml_filenames, first_monad, first_id_d, default_document_name, default_token_name)
        elif command == "json":
            xml2mql.generateJSON(json_filename, xml_filenames, default_document_name, default_token_name)
        elif command == "renderjson":
            xml2mql.generateRenderJSON(json_filename, xml_filenames[0])
        else:
            usage()
            sys.exit(1)
