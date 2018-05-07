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
import xml.sax

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
