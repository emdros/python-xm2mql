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
import xml.sax

from xml2mql import xml2mql

def usage():
    sys.stderr.write("""
Usage:
     python3 xml2mql.py command [options] jsonfilename.json [filename.xml...]

COMMANDS
     json     Generate an example JSON script, put it into jsonfilename.json
     mql      Generate MQL based on jsonfilename.json

""")

def generateJSON(json_filename_or_file, xml_filesname_list, default_token_name = "token"):
    handler = xml2mql.JSONGeneratorHandler(default_token_name)

    for filename in xml_filenames:
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

def generateMQL(json_filename, xml_filenames_list, first_monad, first_id_d, default_token_name = "token"):
    if json_filename == None or json_filename == "":
        json_file = os.tmpfile()

        # Generate JSON first...
        generateJSON(json_file, xml_filesname_list, default_token_name)

        # Rewind file
        json_file.seek(0)
    else:
        json_file = open(json_filename, "rb")
        print(repr(json_file))

    handler = xml2mql.MQLGeneratorHandler(json_file, first_monad, first_id_d)

    for filename in xml_filenames:
        fin = open(filename, "rb")
        sys.stderr.write("Now reading: %s ...\n" % filename)
        xml.sax.parse(fin, handler)
        fin.close()


    # Dump MQL on stdout
    handler.doCommand(sys.stdout)
        


    json_file.close()

    

if __name__ == '__main__':
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
            generateMQL(json_filename, xml_filenames, first_monad, first_id_d, default_token_name)
        elif command == "json":
            generateJSON(json_filename, xml_filenames, default_token_name)
        else:
            usage()
            sys.exit(1)
