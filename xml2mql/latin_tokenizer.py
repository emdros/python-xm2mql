# -*- coding: utf-8 -*-
#
# Basic tokenizer.
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
token_split_chars = " \n\r\t-"

state_between = 0
state_in = 1

def tokenize_string(instring):
    """Takes a string as input, returns a list of (prefix, surface,
    suffix) strings.  Assumes a Western (Latin) character set."""

    tmp_list = []

    state = state_between

    start = 0
    for index in range(0, len(instring)):
        c = instring[index]
        if c in token_split_chars:
            if state == state_between:
                pass
            elif state == state_in:
                tmp_str = instring[start:index]
                start = index
                tmp_list.append(tmp_str)
            else:
                assert False, "Unhandled state: %s\n" % state
        else:
            if state == state_in:
                pass
            elif state == state_between:
                pass
            else:
                assert False, "Unhandled state: %s\n" % state

    if start < len(instring)-1:
        tmp_str = instring[start:]
        tmp_list.append(tmp_str)

    result_list = []

    st_prefix = 0
    st_surface = 1
    st_suffix = 2

    for tmp_str in tmp_list:
        state = st_prefix
        prefix_list = []
        surface_list = []
        suffix_list = []
        for index in range(0, len(tmp_str)):
            c = tmp_str[index]
            if c in token_split_chars:
                if state == st_prefix:
                    prefix_list.append(c)
                elif state == st_surface:
                    state = st_suffix
                    suffix_list.append(c)
                elif state == st_suffix:
                    suffix_list.append(c)
                else:
                    assert False, "Unhandled state: %s\n" % state
            else:
                if state == st_prefix:
                    state = st_surface
                    surface_list.append(c)
                elif state == st_surface:
                    surface_list.append(c)
                elif state == st_suffix:
                    suffix_list.append(c)
                else:
                    assert False, "Unhandled state: %s\n" % state

        prefix = "".join(prefix_list)
        surface = "".join(surface_list)
        suffix = "".join(suffix_list)

        result_list.append((prefix, surface, suffix))

    return result_list
        
    
