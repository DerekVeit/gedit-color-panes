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
Version 1.0     Initial release
Version 1.0.1   Added coloring of Embedded Terminal and Chracter Map table.
Version 1.5.0   Added response to color scheme change.
                Added response to pane additions.
                Eliminated redundant color updates.
                Eliminated most redundant widget searching.

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
        self.logger.setLevel(logging.WARNING)
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
    
    Public methods:
    deactivate -- ColorPanesPlugin calls this when Gedit calls deactivate for
                  this window.
    update_ui -- ColorPanesPlugin calls this when Gedit calls update_ui for
                 this window.  Also, ColorPanesWindowHelper.__init__ calls
                 this.  It generally corresponds to a document tab being added,
                 changed (e.g. saved), selected, or removed.
    
    The plugin will update the colors in these cases:
        The first time it finds the active document.
        Each time the color scheme is changed.
        Each time a tab is added to one of the panes.
    
    It does not (yet) handle a case of a view being added to an existing tab.
    
    """
    
    def __init__(self, plugin, window):
        """Establish the circumstances of this Color Panes instance."""
        
        self._window = window
        """The window this ColorPanesWindowHelper runs on."""
        self._plugin = plugin
        """The ColorPanesPlugin that spawned this ColorPanesWindowHelper."""
        
        self._plugin.log()
        self._plugin.log('Started for %s' % self._window)
        
        # The active document will signal if the color scheme is changed.
        self._signal_doc = None
        """The gedit.Document currently connected to the signal callback."""
        self._doc_signal_handler = None
        """The handler connecting _signal_doc to the callback."""
        
        # The side and bottom panes are gtk.Notebook instances.
        # They will signal if a new tabbed view ("page") is added.
        self._handlers_per_notebook = {}
        """Signal handlers for each gtk.Notebook in the Gedit window."""
        self._notebooks = self._get_notebooks(self._window)
        self._connect_notebooks()
        
        self.update_ui(window)
        """
        The plugin gets the color scheme through the document instance, so if
        the plugin is activated without any document open, it will not be able
        to update the colors until a document is opened.  When a document is
        opened, update_ui will be called.  The first time update_ui finds a
        document, it calls _update_pane_colors.
        """
    
    def deactivate(self):
        """End this instance of Color Panes."""
        self._plugin.log()
        self._plugin.log('Stopping for %s' % self._window)
        self._disconnect_notebooks()
        self._disconnect_doc()
    
    def update_ui(self, window):
        """Respond to change of document."""
        self._plugin.log()
        doc = window.get_active_document()
        if doc and not self._signal_doc:
            self._update_pane_colors(doc)
        if doc != self._signal_doc:
            self._update_doc_handler(doc)
    
    def _update_pane_colors(self, doc):
        """Apply the color scheme to other view widgets in the Gedit window."""
        self._plugin.log()
        style = self._get_style(doc)
        fg_color, bg_color = self._get_colors(style)
        state = gtk.STATE_NORMAL
        for notebook in self._notebooks:
            #self._plugin.log('notebook: %r' % notebook)
            for widget in self._get_widgets_to_color(notebook):
                #self._plugin.log('widget: %r' % widget)
                widget.modify_text(state, fg_color)
                widget.modify_base(state, bg_color)
                if have_terminal and isinstance(widget, vte.Terminal):
                    widget.set_colors(fg_color, bg_color, [])
    
    def _get_style(self, doc):
        """Return the GtkStyle specifying Gedit's color scheme for text."""
        style_scheme = doc.get_style_scheme()
        style = style_scheme.get_style('text')
        return style
    
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
    
    def _get_widgets_to_color(self, widget, depth=0):
        """
        Recursively find:
            all child widgets of GtkScrolledWindow objects
            the Embedded Terminal view
            the Character Map table
        """
        if depth == 0:
            self._plugin.log()
        depth += 1
        
        widgets_to_color = set()
        
        if (isinstance(widget, gtk.TextView) or
                isinstance(widget, gtk.TreeView) or
                isinstance(widget, gtk.Entry)):
            widgets_to_color.add(widget)
        if isinstance(widget, gtk.Container):
            
            if (isinstance(widget, gtk.ScrolledWindow) or
                    have_terminal and isinstance(widget, terminal.GeditTerminal) or
                    'GucharmapTable' in type(widget).__name__):
                first_child = widget.get_children()[0]
                if first_child not in widgets_to_color:
                    widgets_to_color.add(first_child)
            
            children = widget.get_children()
            for child in children:
                widgets_to_color |= self._get_widgets_to_color(child, depth)
        
        return widgets_to_color
    
    # Respond to change of the color scheme.
    
    def _update_doc_handler(self, doc):
        """Connect to gedit.Document signal for style scheme change."""
        self._plugin.log()
        self._disconnect_doc()
        if doc:
            self._signal_doc = doc
            self._doc_signal_handler = doc.connect(
                'notify::style-scheme', self.on_notify_style_scheme)
            self._plugin.log('Connected to %r' % doc)
    
    def _disconnect_doc(self):
        """Disconnect signal handler from the gedit.Document."""
        self._plugin.log()
        if self._signal_doc and self._doc_signal_handler:
            self._signal_doc.disconnect(self._doc_signal_handler)
            self._plugin.log('Disconnected from %r' % self._signal_doc)
            self._doc_signal_handler = None
    
    def on_notify_style_scheme(self, source_buffer, gparam):
        """Propogate the color scheme because it has changed."""
        self._plugin.log()
        doc = source_buffer
        self._update_pane_colors(doc)
    
    # Respond to addition of paned views (gtk.Notebookk pages).
    
    def _connect_notebooks(self):
        """Connect to the 'add' signal of each gtk.Notebook widget."""
        self._plugin.log()
        self._plugin.log('notebooks: \n%s\n' % '\n'.join([repr(x) for x in self._notebooks]))
        for notebook in self._notebooks:
            self._handlers_per_notebook[notebook] = notebook.connect(
                'page-added', self.on_page_added)
    
    def _disconnect_notebooks(self):
        """Disconnect signal handlers from gtk.Notebook widgets."""
        self._plugin.log()
        for notebook in self._handlers_per_notebook:
            notebook.disconnect(self._handlers_per_notebook[notebook])
    
    def _get_notebooks(self, widget, depth=0):
        """Return a list of all gtk.Notebook widgets in the Gedit window."""
        if depth == 0:
            self._plugin.log()
        depth += 1
        
        notebooks = []
        if isinstance(widget, gtk.Container):
            if (isinstance(widget, gtk.Notebook) and
                'GeditNotebook' not in type(widget).__name__):
                notebooks.append(widget)
            children = widget.get_children()
            for child in children:
                notebooks += self._get_notebooks(child, depth)
        return notebooks
    
    def on_page_added(self, notebook, child, page_num):
        """Propogate the color scheme because a view was added to a pane."""
        self._plugin.log()
        doc = self._window.get_active_document()
        if doc:
            self._update_pane_colors(doc)
    

