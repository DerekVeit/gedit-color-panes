# -*- coding: utf8 -*-
#  Color Panes plugin for Gedit
#
#  Copyright (C) 2010 Derek Veit
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module provides the plugin object that Gedit interacts with.

Classes:
ColorPanesPlugin -- object is loaded once by an instance of Gedit
ColorPanesWindowHelper -- object is constructed for each Gedit window

"""

import logging
import logging.handlers
import os
import sys

import gedit
import gtk
try:
    import terminal
    import vte
except ImportError:
    have_terminal = False
else:
    have_terminal = True

class ColorPanesPlugin(gedit.Plugin):
    
    """
    An object of this class is loaded once by a Gedit instance.
    
    It creates a ColorPanesWindowHelper object for each Gedit main window.
    
    Public methods:
    activate -- Gedit calls this to start the plugin.
    deactivate -- Gedit calls this to stop the plugin.
    update_ui -- Gedit calls this at certain times when the ui changes.
    is_configurable -- Gedit calls this to check if the plugin is configurable.
    
    """
    
    def __init__(self):
        """Establish the settings shared by all Color Panes instances."""
        
        gedit.Plugin.__init__(self)
        
        self.logger = logging.getLogger('color_panes')
        handler = logging.StreamHandler(sys.stdout)
        log_format = "%(levelname)s - %(message)s"
        #log_format = "%(asctime)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        self.log('Color Panes logging started. '.ljust(72, '-'))
        self.log()
        
        self._instances = {}
        """Each Gedit window will get a ColorPanesWindowHelper instance."""
    
    def activate(self, window):
        """Start a ColorPanesWindowHelper instance for this Gedit window."""
        self.log()
        self._instances[window] = ColorPanesWindowHelper(self, window)
    
    def deactivate(self, window):
        """End the ColorPanesWindowHelper instance for this Gedit window."""
        self.log()
        self._instances[window].deactivate()
        del self._instances[window]
    
    def update_ui(self, window):
        """Forward Gedit's update_ui command for this window."""
        self.log()
        self._instances[window].update_ui(window)
    
    def is_configurable(self):
        """Identify for Gedit that Color Panes is not configurable."""
        self.log()
        return False
    
    def log(self, message=None, level='info'):
        """Log the message or log the calling function."""
        if message:
            logger = {'debug': self.logger.debug,
                      'info': self.logger.info,
                      'warning': self.logger.warning,
                      'error': self.logger.error,
                      'critical': self.logger.critical}[level]
            logger(message)
        else:
            self.logger.debug(self._whoami())
    
    def _whoami(self):
        """Identify the calling function for logging."""
        filename = os.path.basename(sys._getframe(2).f_code.co_filename)
        line = sys._getframe(2).f_lineno
        class_name = sys._getframe(2).f_locals['self'].__class__.__name__
        function_name = sys._getframe(2).f_code.co_name
        return '%s Line %s %s.%s' % (filename, line, class_name, function_name)

class ColorPanesWindowHelper(object):
    
    """
    ColorPanesPlugin creates a ColorPanesWindowHelper object for each Gedit
    window.
    
    This could be fine-tuned with event handlers to respond immediately to
    changes in the color scheme or to the addition of new panes rather than
    waiting for the next call to update_ui.
    
    Public methods:
    deactivate -- ColorPanesPlugin calls this when Gedit calls deactivate for
                  this window.
    update_ui -- ColorPanesPlugin calls this when Gedit calls update_ui for
                 this window.  It activates the menu for the Gedit window and
                 connects the mouse event handler to the current View.
                 Also, ColorPanesWindowHelper.__init__ calls this.
    
    """
    
    def __init__(self, plugin, window):
        """Establish the circumstances of this Color Panes instance."""
        
        self._window = window
        """The window this ColorPanesWindowHelper runs on."""
        self._plugin = plugin
        """The ColorPanesPlugin that spawned this ColorPanesWindowHelper."""
        
        self._plugin.log()
        self._plugin.log('Started for %s' % self._window)
        
        self.update_ui(self._window)
        
    
    def deactivate(self):
        """End this instance of Color Panes."""
        self._plugin.log()
        self._plugin.log('Stopping for %s' % self._window)
    
    def update_ui(self, window):
        """Set the colors."""
        self._plugin.log()
        doc = self._window.get_active_document()
        current_view = self._window.get_active_view()
        if doc and current_view and current_view.get_editable():
            style_scheme = doc.get_style_scheme()
            style = style_scheme.get_style('text')
            fg_color, bg_color = self._get_colors(style)
            state = gtk.STATE_NORMAL
            scrolled_windows = self._list_scrolledwindows(self._window)
            for scrolled_window in scrolled_windows:
                self._plugin.log('Parent: %r' % scrolled_window)
                for view in scrolled_window.get_children():
                    self._plugin.log('Child: %r' % view)
                    view.modify_text(state, fg_color)
                    view.modify_base(state, bg_color)
                    if have_terminal and isinstance(view, vte.Terminal):
                        view.set_colors(fg_color, bg_color, [])
    
    def _get_colors(self, style):
        """Return GDK colors for style, default to black on white."""
        self._plugin.log()
        if style and style.get_property('foreground-set'):
            fg_color_desc = style.get_property('foreground')
        else:
            fg_color_desc = 'black'
        fg_color = gtk.gdk.color_parse(fg_color_desc)
        
        if style and style.get_property('background-set'):
            bg_color_desc = style.get_property('background')
        else:
            bg_color_desc = 'white'
        bg_color = gtk.gdk.color_parse(bg_color_desc)
        return fg_color, bg_color
    
    def _list_scrolledwindows(self, widget):
        """
        Recursively find all GtkScrolledWindow objects.
        
        This is just a lazy way of guessing all of the appropriate view-like
        widgets to re-color.  This could probably be improved, though it mostly
        seems to work well.
        
        Also includes the parent widget of the Embedded Terminal view and the
        Character Map table.
        """
        scrolled_windows = []
        if isinstance(widget, gtk.ScrolledWindow):
            scrolled_windows.append(widget)
        if have_terminal and isinstance(widget, terminal.GeditTerminal):
            scrolled_windows.append(widget)
        if 'GucharmapTable' in type(widget).__name__:
            scrolled_windows.append(widget)
        if isinstance(widget, gtk.Container):
            children = widget.get_children()
            for child in children:
                scrolled_windows += self._list_scrolledwindows(child)
        return scrolled_windows
    

