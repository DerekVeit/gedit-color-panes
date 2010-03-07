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
2010-03-07  Version 2.0.0
    Added immediate response to desktop theme changes.
    Removed dependency on the document by using GConf instead.
    Further simplified widget selection.
    Moved terminal widget search to a separate function.
    Improved method of getting colors for Embedded Terminal.
    Added restoration of colors and terminal font when plugin is deactivated.
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

LOGGING_LEVEL = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')[2]

import logging
import os
import sys

import gedit
import gconf
import gtk
import gtksourceview2

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
        """Set up logging and the dictionary of instances."""
        
        gedit.Plugin.__init__(self)
        
        self.logger = None
        """Logger for debugging."""
        
        self.gconf_client = None
        """GConfClient for responding to changes in Gedit preferences."""
        self._gconf_cnxn = None
        """GConf connection ID for the preferences change notification."""
        
        self._instances = {}
        """Each Gedit window will get a ColorPanesWindowHelper instance."""
        
        self.terminal_colors = {}
        """Original Embedded Terminal colors before changing."""
        self.terminal_font = {}
        """Original Embedded Terminal font before changing."""
        
        self._start_logging()
        self.log()
    
    def activate(self, window):
        """Start a ColorPanesWindowHelper instance for this Gedit window."""
        self.log()
        if not self._instances:
            self.log('Color Panes activating.')
            self._connect_gconf()
        self._instances[window] = ColorPanesWindowHelper(self, window)
        self._instances[window].activate()
    
    def deactivate(self, window):
        """End the ColorPanesWindowHelper instance for this Gedit window."""
        self.log()
        self._instances[window].deactivate()
        del self._instances[window]
        if not self._instances:
            self._disconnect_gconf()
            self.terminal_colors = {}
            self.terminal_font = {}
            self.log('Color Panes deactivated.')
    
    def update_ui(self, window):
        """(Gedit calls update_ui for each window.)"""
        self.log()
    
    def is_configurable(self):
        """Identify for Gedit that Color Panes is not configurable."""
        self.log()
        return False
    
    # Respond to a change of the Gedit preferences.
    
    def _connect_gconf(self):
        """Have GConf call if the Gedit preferences change."""
        self.log()
        if not self.gconf_client:
            self.gconf_client = gconf.client_get_default()
            gconf_dir = '/apps/gedit-2/preferences'
            self.gconf_client.add_dir(gconf_dir, gconf.CLIENT_PRELOAD_NONE)
            gconf_key = gconf_dir + '/editor'
            self._gconf_cnxn = self.gconf_client.notify_add(
                gconf_key,
                lambda client, cnxn_id, entry, user_data:
                    self.on_gedit_prefs_changed())
            self.log('Connected to GConf, connection ID: %r' %
                self._gconf_cnxn)
    
    def _disconnect_gconf(self):
        """Stop having GConf call if the Gedit preferences change."""
        self.log()
        if self.gconf_client and self._gconf_cnxn:
            self.gconf_client.notify_remove(self._gconf_cnxn)
            self.log('Disconnected from GConf, connection ID: %r' %
                self._gconf_cnxn)
        self._gconf_cnxn = None
        self.gconf_client = None
    
    def on_gedit_prefs_changed(self):
        """Respond to a change in Gedit's editor preferences."""
        self.log()
        for window in self._instances:
            self._instances[window].update_pane_colors()
    
    # Log
    
    def _start_logging(self):
        """Set up logging (to stdout) for the plugin."""
        self.logger = logging.getLogger('color_panes')
        log_handler = logging.StreamHandler(sys.stdout)
        log_format = "%(levelname)s - %(message)s"
        #log_format = "%(asctime)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(log_format)
        log_handler.setFormatter(formatter)
        self.logger.addHandler(log_handler)
        logging_level = getattr(logging, LOGGING_LEVEL)
        self.logger.setLevel(logging_level)
        self.log('Color Panes logging started. '.ljust(72, '-'))
    
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
                 this window.
    
    The plugin will update the colors in these cases:
        When the plugin is initialized for the window.
        When Gedit's editor preferences are changed.
        When the desktop theme is changed.
        When a tab is added to one of the panes (on_page_added).
    
    It does not handle the event of a view being added to an existing tab.
    
    """
    
    def __init__(self, plugin, window):
        """Establish the circumstances of this Color Panes instance."""
        
        self._window = window
        """The window this ColorPanesWindowHelper runs on."""
        self._plugin = plugin
        """The ColorPanesPlugin that spawned this ColorPanesWindowHelper."""
        
        self._plugin.log()
        
        # The side and bottom panes are gtk.Notebook instances.
        # They will signal if a new tabbed view ("page") is added.
        self._handlers_per_notebook = {}
        """Signal handlers for each gtk.Notebook in the Gedit window."""
        self._notebooks = None
        """The container widgets corresponding to the side and bottom panes."""
        
        self._window_style_handler = None
        """Signal handler for when the desktop theme changes."""
    
    def activate(self):
        """Start this instance of Color Panes."""
        self._plugin.log()
        self._plugin.log('Color Panes activating for %s' % self._window)
        self._connect_window()
        self._notebooks = self._get_notebooks(self._window)
        self._connect_notebooks()
        self.update_pane_colors()
    
    def deactivate(self):
        """End this instance of Color Panes."""
        self._plugin.log()
        self._restore_pane_colors()
        self._disconnect_notebooks()
        self._notebooks = None
        self._disconnect_window()
        self._plugin.log('Color Panes deactivated for %s\n' % self._window)
    
    # Color widgets.
    
    def update_pane_colors(self):
        """Apply the color scheme to appropriate widgets in the Gedit panes."""
        self._plugin.log()
        widgets_to_color = set()
        terminals = set()
        for notebook in self._notebooks:
            widgets_to_color |= self._get_widgets_to_color(notebook)
            terminals |= self._get_terminals(notebook)
        state = gtk.STATE_NORMAL
        text_color, base_color = self._get_gedit_scheme_colors()
        self._plugin.log('Matching widget text colors to editor.')
        for widget in widgets_to_color:
            #self._plugin.log('Recoloring widget:\n %r' % widget)
            widget.modify_text(state, text_color)
            widget.modify_base(state, base_color)
        for terminal in terminals:
            self._plugin.log('Recoloring terminal:\n %r' % terminal)
            if TERMINAL_MATCH_COLORS:
                if terminal not in self._plugin.terminal_colors:
                    self._store_terminal_colors(terminal)
                # If the colors are None, the other widgets will default to
                # system colors.  For the terminal widget, we need to get those
                # default colors from the widget and apply them explicitly.
                term_fg = text_color or terminal.get_style().text[state]
                term_bg = base_color or terminal.get_style().base[state]
                self._plugin.log('Matching terminal fg color to editor: %s' %
                                        term_fg.to_string())
                terminal.set_color_foreground(term_fg)
                self._plugin.log('Matching terminal bg color to editor: %s' %
                                        term_bg.to_string())
                terminal.set_color_background(term_bg)
            if TERMINAL_MATCH_FONT:
                if terminal not in self._plugin.terminal_font:
                    self._store_terminal_font(terminal)
                gedit_font = self._get_gedit_font()
                self._plugin.log('Matching terminal font to editor: %s' %
                                    gedit_font)
                terminal.set_font_from_string(gedit_font)
    
    def _restore_pane_colors(self):
        """Apply the color scheme to appropriate widgets in the Gedit panes."""
        self._plugin.log()
        widgets_to_color = set()
        terminals = set()
        for notebook in self._notebooks:
            widgets_to_color |= self._get_widgets_to_color(notebook)
            terminals |= self._get_terminals(notebook)
        state = gtk.STATE_NORMAL
        self._plugin.log('Restoring widget text colors to defaults.')
        for widget in widgets_to_color:
            widget.modify_text(state, None)
            widget.modify_base(state, None)
        for terminal in terminals:
            if TERMINAL_MATCH_COLORS:
                if terminal in self._plugin.terminal_colors:
                    term_fg, term_bg = self._plugin.terminal_colors[terminal]
                    if term_fg:
                        self._plugin.log('Restoring terminal fg color: %s' %
                                            term_fg.to_string())
                        terminal.set_color_foreground(term_fg)
                    if term_bg:
                        self._plugin.log('Restoring terminal bg color: %s' %
                                            term_bg.to_string())
                        terminal.set_color_background(term_bg)
            if TERMINAL_MATCH_FONT:
                if terminal in self._plugin.terminal_font:
                    font_string = self._plugin.terminal_font[terminal]
                    if font_string:
                        self._plugin.log('Restoring terminal font: %s' %
                                            font_string)
                        terminal.set_font_from_string(font_string)
    
    # Collect widgets
    
    def _get_notebooks(self, widget, original=True):
        """Return a list of all gtk.Notebook widgets in the Gedit window."""
        if original:
            self._plugin.log()
        notebooks = set()
        if hasattr(widget, 'get_children'):
            if (isinstance(widget, gtk.Notebook) and
                'GeditNotebook' not in type(widget).__name__):
                notebooks.add(widget)
            children = widget.get_children()
            for child in children:
                notebooks |= self._get_notebooks(child, False)
        return notebooks
    
    def _get_widgets_to_color(self, widget, original=True):
        """Return a set of widgets likely to need re-coloring."""
        if original:
            self._plugin.log()
        widgets_to_color = set()
        if hasattr(widget, 'modify_text') and hasattr(widget, 'modify_base'):
            widgets_to_color.add(widget)
        if hasattr(widget, 'get_children'):
            for child in widget.get_children():
                widgets_to_color |= self._get_widgets_to_color(child, False)
        return widgets_to_color
    
    def _get_terminals(self, widget, original=True):
        """Return a set of terminals."""
        if original:
            self._plugin.log()
        terminals = set()
        if (hasattr(widget, 'set_color_foreground') and
                hasattr(widget, 'set_color_background')):
            terminals.add(widget)
        if hasattr(widget, 'get_children'):
            for child in widget.get_children():
                terminals |= self._get_terminals(child, False)
        return terminals
    
    # Respond to change of the system/desktop Gnome theme.
    
    def _connect_window(self):
        """Connect to the Gedit window's signal for desktop theme change."""
        self._plugin.log()
        self._window_style_handler = self._window.connect(
                'style-set',
                lambda widget, previous_style: self.on_style_set())
        self._plugin.log('Connected to %r' % self._window)
    
    def _disconnect_window(self):
        """Disconnect signal handler from the Gedit window."""
        self._plugin.log()
        if self._window_style_handler:
            self._window.disconnect(self._window_style_handler)
            self._plugin.log('Disconnected from %r' % self._window)
    
    def on_style_set(self):
        """Propogate the color scheme because system colors changed."""
        self._plugin.log()
        self.update_pane_colors()
        return False
    
    # Respond to addition of paned views (gtk.Notebook pages).
    
    def _connect_notebooks(self):
        """Connect to the 'add' signal of each gtk.Notebook widget."""
        self._plugin.log()
        self._plugin.log('notebooks: \n%s\n' %
            '\n'.join([repr(x) for x in self._notebooks]))
        for notebook in self._notebooks:
            self._handlers_per_notebook[notebook] = notebook.connect(
                'page-added',
                lambda notebook, child, page_num: self.on_page_added())
            self._plugin.log('Connected to %r' % notebook)
    
    def _disconnect_notebooks(self):
        """Disconnect signal handlers from gtk.Notebook widgets."""
        self._plugin.log()
        for notebook in self._handlers_per_notebook:
            notebook.disconnect(self._handlers_per_notebook[notebook])
            self._plugin.log('Disconnected from %r' % notebook)
        self._handlers_per_notebook = {}
    
    def on_page_added(self):
        """Propogate the color scheme because a view was added to a pane."""
        self._plugin.log()
        self.update_pane_colors()
    
    # Get the colors and font to apply.
    
    def _get_gedit_scheme_colors(self):
        """Return foreground and background colors of Gedit's color scheme."""
        self._plugin.log()
        text_color, base_color = None, None
        scheme_name = self._plugin.gconf_client.get_string(
            '/apps/gedit-2/preferences/editor/colors/scheme') or 'classic'
        self._plugin.log('Gedit color scheme: %s' % scheme_name)
        scheme_manager = self._get_gedit_style_scheme_manager()
        style_scheme = scheme_manager.get_scheme(scheme_name)
        if style_scheme:
            style = style_scheme.get_style('text')
            if style:
                text_color, base_color = self._get_style_colors(style)
        if text_color and base_color:
            self._plugin.log('Gedit text color: %s' % text_color.to_string())
            self._plugin.log('Gedit base color: %s' % base_color.to_string())
        else:
            gtk_theme = self._plugin.gconf_client.get_string(
                '/desktop/gnome/interface/gtk_theme')
            self._plugin.log('GTK theme: %s' % gtk_theme)
            state = gtk.STATE_NORMAL
            gtk_theme_text_color = self._window.get_style().text[state]
            gtk_theme_base_color = self._window.get_style().text[state]
            self._plugin.log('GTK theme text color: %s' %
                gtk_theme_text_color.to_string())
            self._plugin.log('GTK theme base color: %s' %
                gtk_theme_base_color.to_string())
        return text_color, base_color
    
    def _get_gedit_style_scheme_manager(self):
        """Return a gtksourceview2.StyleSchemeManager imitating Gedit's."""
        self._plugin.log()
        scheme_manager = gtksourceview2.style_scheme_manager_get_default()
        gedit_styles_path = os.path.expanduser('~/.gnome2/gedit/styles')
        scheme_manager.append_search_path(gedit_styles_path)
        return scheme_manager
    
    def _get_style_colors(self, style):
        """Return GDK colors for the gtksourceview2.Style."""
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
        gedit_uses_system_font = self._plugin.gconf_client.get_bool(
            '/apps/gedit-2/preferences/editor/font/use_default_font')
        if gedit_uses_system_font:
            gedit_font = self._plugin.gconf_client.get_string(
                '/desktop/gnome/interface/monospace_font_name')
            self._plugin.log('System font: %s' % gedit_font)
        else:
            gedit_font = self._plugin.gconf_client.get_string(
                '/apps/gedit-2/preferences/editor/font/editor_font')
            self._plugin.log('Gedit font: %s' % gedit_font)
        return gedit_font
    
    # Record original terminal colors and font for restoring on deactivation.
    
    def _store_terminal_colors(self, terminal):
        """Record the original terminal colors before changing them."""
        self._plugin.log()
        term_fg, term_bg = self._get_term_colors_from_term(terminal)
        if (not term_fg or not term_bg or
                term_fg.to_string() == term_bg.to_string()):
            term_fg, term_bg = self._get_term_colors_from_gconf()
        self._plugin.log('Storing terminal fg color: %s' % term_fg.to_string())
        self._plugin.log('Storing terminal bg color: %s' % term_bg.to_string())
        self._plugin.terminal_colors[terminal] = term_fg, term_bg
    
    def _get_term_colors_from_term(self, terminal):
        """Get the text colors from the terminal widget."""
        self._plugin.log()
        attributes_per_char = terminal.get_text(
            (lambda terminal, column, row, data: True), True)[1]
        if not attributes_per_char:
            return None, None
        first_char_attributes = attributes_per_char[1]
        if not first_char_attributes:
            return None, None
        term_fg = first_char_attributes['fore']
        term_bg = first_char_attributes['back']
        return term_fg, term_bg
    
    def _get_term_colors_from_gconf(self):
        """Get the text colors from the Gnome Terminal profile in GConf."""
        self._plugin.log()
        profile = self._plugin.gconf_client.get_string(
            '/apps/gnome-terminal/global/default_profile')
        # The Embedded Terminal plugin has 'Default' hard coded.
        profile = 'Default'
        term_fg_desc = self._plugin.gconf_client.get_string(
            '/apps/gnome-terminal/profiles/%s/foreground_color' % profile)
        term_fg = gtk.gdk.color_parse(term_fg_desc)
        term_bg_desc = self._plugin.gconf_client.get_string(
            '/apps/gnome-terminal/profiles/%s/background_color' % profile)
        term_bg = gtk.gdk.color_parse(term_bg_desc)
        return term_fg, term_bg
    
    def _store_terminal_font(self, terminal):
        """Record the original terminal font before changing it."""
        self._plugin.log()
        self._plugin.terminal_font[terminal] = None
        pango_font = terminal.get_font()
        if pango_font:
            font_string = pango_font.to_string()
            self._plugin.terminal_font[terminal] = font_string
            self._plugin.log('Storing terminal font: %s' % font_string)
    
