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
Version history:
2010-03-01  Version 1.6.0
    Changed to default to system colors instead of black-on-white.
    Added applying editor font to Embedded Terminal.
    Simplified widget selection.
2010-02-25  Version 1.5.0
    Added response to color scheme change.
    Added response to pane additions.
    Eliminated redundant color updates.
    Eliminated most redundant widget searching.
2010-02-21  Version 1.0.1
    Added coloring of Embedded Terminal and Chracter Map table.
2010-02-20  Version 1.0
    Initial release

Classes:
ColorPanesPlugin -- object is loaded once by an instance of Gedit
ColorPanesWindowHelper -- object is constructed for each Gedit window

"""

TERMINAL_MATCH_COLORS = True
TERMINAL_MATCH_FONT = True

import logging
import logging.handlers
import os
import sys

import gedit
import gconf
import gtk
try:
    import vte
except ImportError:
    HAVE_VTE = False
else:
    HAVE_VTE = True

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
            self.logger.debug(whoami())
    
def whoami():
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
        """The container widgets corresponding to the side and bottom panes."""
        self._connect_notebooks()
        
        self._terminal = None
        """The widget of the Embedded Terminal view if it is found."""
        
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
    
    def _get_notebooks(self, widget, original=True):
        """Return a list of all gtk.Notebook widgets in the Gedit window."""
        if original:
            self._plugin.log()
        notebooks = []
        if isinstance(widget, gtk.Container):
            if (isinstance(widget, gtk.Notebook) and
                'GeditNotebook' not in type(widget).__name__):
                notebooks.append(widget)
            children = widget.get_children()
            for child in children:
                notebooks += self._get_notebooks(child, False)
        return notebooks
    
    def _update_pane_colors(self, doc):
        """Apply the color scheme to appropriate widgets in the Gedit panes."""
        self._plugin.log()
        self._terminal = None
        widgets_to_color = set()
        for notebook in self._notebooks:
            widgets_to_color |= self._get_widgets_to_color(notebook)
        state = gtk.STATE_NORMAL
        style = self._get_style(doc)
        text_color, base_color = self._get_colors(style)
        for widget in widgets_to_color:
            self._plugin.log('Recoloring widget:\n %r' % widget)
            widget.modify_text(state, text_color)
            widget.modify_base(state, base_color)
        if self._terminal:
            if TERMINAL_MATCH_COLORS:
                term_fg = text_color or self._get_gtk_system_color('text_color')
                term_bg = base_color or self._get_gtk_system_color('base_color')
                self._terminal.set_color_foreground(term_fg)
                self._terminal.set_color_background(term_bg)
            if TERMINAL_MATCH_FONT:
                gedit_font = self._get_gedit_font()
                self._terminal.set_font_from_string(gedit_font)
    
    def _get_widgets_to_color(self, widget, original=True):
        """
        Return a set of widgets likely to need re-coloring.
        Identify the Embedded Terminal widget to be recolored.
        """
        if original:
            self._plugin.log()
        widgets_to_color = set()
        if (('View' in type(widget).__name__ and
                not isinstance(widget, gtk.CellView)) or
                isinstance(widget, gtk.Entry) or
                isinstance(widget, gtk.DrawingArea)):
            widgets_to_color.add(widget)
        elif isinstance(widget, gtk.Container):
            children = widget.get_children()
            for child in children:
                widgets_to_color |= self._get_widgets_to_color(child, False)
        elif HAVE_VTE and isinstance(widget, vte.Terminal):
            self._terminal = widget
            #widgets_to_color.add(widget)
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
        self._plugin.log('notebooks: \n%s\n' %
            '\n'.join([repr(x) for x in self._notebooks]))
        for notebook in self._notebooks:
            self._handlers_per_notebook[notebook] = notebook.connect(
                'page-added', self.on_page_added)
            self._plugin.log('Connected to %r' % notebook)
    
    def _disconnect_notebooks(self):
        """Disconnect signal handlers from gtk.Notebook widgets."""
        self._plugin.log()
        for notebook in self._handlers_per_notebook:
            notebook.disconnect(self._handlers_per_notebook[notebook])
            self._plugin.log('Disconnected from %r' % notebook)
    
    def on_page_added(self, notebook, child, page_num):
        """Propogate the color scheme because a view was added to a pane."""
        self._plugin.log()
        doc = self._window.get_active_document()
        if doc:
            self._update_pane_colors(doc)
    
    # Miscellaneous
    
    def _get_gtk_system_color(self, color_name):
        """Return the GDK color for the given system color name."""
        self._plugin.log()
        gtk_settings = gtk.settings_get_default()
        gtk_color_scheme = gtk_settings.get_property('gtk-color-scheme')
        gtk_color_list = gtk_color_scheme.strip().split('\n')
        gtk_color_pairs = [line.split(': ') for line in gtk_color_list]
        gtk_colors = {}
        for name, desc in gtk_color_pairs:
            gtk_colors[name] = desc
        color_desc = gtk_colors[color_name]
        gdk_color = gtk.gdk.color_parse(color_desc)
        return gdk_color
    
    def _get_style(self, doc):
        """Return the GtkStyle specifying Gedit's color scheme for text."""
        self._plugin.log()
        style_scheme = doc.get_style_scheme()
        style = style_scheme.get_style('text')
        return style
    
    def _get_colors(self, style):
        """Return GDK colors for the style."""
        self._plugin.log()
        text_color = None
        if style and style.get_property('foreground-set'):
            text_color_desc = style.get_property('foreground')
            if text_color_desc:
                text_color = gtk.gdk.color_parse(text_color_desc)
        base_color = None
        if style and style.get_property('background-set'):
            base_color_desc = style.get_property('background')
            if base_color_desc:
                base_color = gtk.gdk.color_parse(base_color_desc)
        return text_color, base_color
    
    def _get_gedit_font(self):
        """Return the font string for the font used in Gedit's editor."""
        self._plugin.log()
        gconf_client = gconf.client_get_default()
        gedit_uses_system_font = gconf_client.get_bool(
            '/apps/gedit-2/preferences/editor/font/use_default_font')
        if gedit_uses_system_font:
            gedit_font = gconf_client.get_string(
                '/desktop/gnome/interface/monospace_font_name')
        else:
            gedit_font = gconf_client.get_string(
                '/apps/gedit-2/preferences/editor/font/editor_font')
        return gedit_font
    

