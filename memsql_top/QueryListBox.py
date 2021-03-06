#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 by MemSQL. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import urwid

from urwid.command_map import ACTIVATE


class QueryRow(urwid.AttrMap):
    def __init__(self, column_meta, **kwargs):
        columns = []
        self.column_meta = column_meta
        self.values = {}
        self.text = {}
        self.attr = {}
        for name, meta in self.column_meta.columns.items():
            t = urwid.Text(meta.humanize(kwargs[name]), wrap="clip")
            color = meta.colorize(kwargs[name])
            a = urwid.AttrMap(t, 'body_%d' % color)
            self.text[name] = t
            self.attr[name] = a
            self.values[name] = kwargs[name]

            if meta.fixed_width:
                columns.append((meta.display_width(), a))
            else:
                columns.append(("weight", meta.display_weight(), a))

        content = urwid.Columns(columns, dividechars=1)
        super(QueryRow, self).__init__(content, "body", {
            "body_0": "body_focus_0",
            "body_1": "body_focus_1",
            "body_2": "body_focus_2",
            "body_3": "body_focus_3",
            "body_4": "body_focus_4",
            None: "body_focus",
        })

    def selectable(self):
        return True

    def keypress(self, size, key):
        # We don't handle any keypresses.
        return key

    def update(self, **kwargs):
        for name, meta in self.column_meta.columns.items():
            self.text[name].set_text(meta.humanize(kwargs[name]))
            color = meta.colorize(kwargs[name])
            self.attr[name].set_attr_map({None: 'body_%d' % color})
            self.values[name] = kwargs[name]


class QueryListBox(urwid.ListBox):
    signals = ['sort_column_changed', 'query_selected']

    def __init__(self, column_meta):
        self.qrlist = urwid.SimpleFocusListWalker([])
        self.widgets = {}
        self.column_meta = column_meta
        self.sort_column = column_meta.default_sort_key
        self.sort_keys_map = {c.sort_key: name
                              for name, c in column_meta.columns.items()}
        super(QueryListBox, self).__init__(self.qrlist)

    def sort_columns(self):
        self.qrlist.sort(key=lambda qr: qr.values[self.sort_column],
                         reverse=True)

    def sort_keys(self):
        return self.sort_keys_map.keys()

    def keypress(self, size, key):
        if self._command_map[key] == ACTIVATE:
            self._emit("query_selected",
                self.focus.values[self.column_meta.focus_column])
            return None
        else:
            return super(QueryListBox, self).keypress(size, key)

    def render(self, size, focus):
        if "top" not in self.ends_visible(size, focus):
            _, maxr = size
            assert maxr is not None and maxr > 0
            self.set_focus(maxr - 1)
            self.set_focus_valign("bottom")
        return super(QueryListBox, self).render(size, focus)

    def update_sort_column(self, key):
        self.sort_column = self.sort_keys_map[key]
        self.sort_columns()
        self.qrlist.set_focus(0)
        self._emit('sort_column_changed', self.sort_column)

    def update_entries(self, diff_plancache):
        # Remove entries that become obsolete
        remove = [k for k in self.widgets if k not in diff_plancache]
        for qr in remove:
            self.qrlist.remove(self.widgets[qr])
            del self.widgets[qr]

        was_empty = len(self.qrlist) == 0
        for key, ent in diff_plancache.items():
            if key not in self.widgets:
                self.widgets[key] = QueryRow(self.column_meta, **ent)
                self.qrlist.append(self.widgets[key])
            else:
                self.widgets[key].update(**ent)

        self.sort_columns()
        if was_empty:
            self.qrlist.set_focus(0)
