## Description ##
This plugin will make the side and bottom panels match the current color scheme as selected in Gedit's preferences.  The main advantage is for color schemes with a colored background, such as Oblivion.

## Update ##
**Version 2.2.0, 2010-10-13**<br>
<ul><li>Fixed <a href='https://code.google.com/p/gedit-color-panes/issues/detail?id=3'>Issue 3</a>, cursor color is now updated in panels, e.g. in Python Console.</li></ul>

<img src='http://gedit-color-panes.googlecode.com/files/Color_Panes-2.1.0-gedit-screenshot.png' />
Screenshot of Gedit using Color Panes plugin with <a href='http://github.com/mig/gedit-themes/blob/master/cobalt.xml'>Cobalt</a> <a href='http://live.gnome.org/GtkSourceView/StyleSchemes'>Gtksourceview theme</a> and <a href='http://customize.org/gtk/themes/66374'>BlackBird</a> <a href='http://customize.org/gtk/themes/'>GNOME theme</a>.  The font is a <a href='https://bugs.launchpad.net/ubuntu/+bug/200671'>modified Fixedsys Excelsior (FSEX301-L2.ttf)</a>.<br>
<br>
<h2>Installation</h2>
<ol><li>Download <a href='http://gedit-color-panes.googlecode.com/files/Color_Panes-2.2.0.tar.gz'>Color_Panes-2.2.0.tar.gz</a>.<br>
</li><li>Extract the files into your <code>~/.gnome2/gedit/plugins</code> directory:<br>
<ul><li><img src='http://gedit-color-panes.googlecode.com/files/Color_Panes-1.0-files-screenshot.png' />
</li></ul></li><li>Restart Gedit<br>
</li><li>Activate the plugin in Gedit Edit > Preferences > Plugins.</li></ol>

<h2>Previous version history</h2>
<b>Version 2.1.1, 2010-05-10</b><br>
<ul><li>Fixed <a href='https://code.google.com/p/gedit-color-panes/issues/detail?id=2'>Issue 2</a>, which occurred with Gedit 2.30.2 on Ubuntu Lucid.<br>
<b>Version 2.1.0, 2010-03-26</b><br>
</li><li>Added recoloring of prelight (hover) state.<br>
<ul><li>Fixes a rare case where checkboxes showed their original color while the mouse pointer was over them.<br>
</li></ul></li><li>Added matching of the Python Console plugin font and its tagged colors.<br>
<ul><li>To disable this, just set <code>PYTERM_MATCH_FONT = False</code> in color_panes.py.<br>
<b>Version 2.0.1, 2010-03-07</b>
</li></ul></li><li>Minor updates to docstrings, names, etc.  No functional change.<br>
<b>Version 2.0.0, 2010-03-07</b>
</li><li>Added immediate response to desktop theme changes.<br>
</li><li>Removed dependency on the document by using GConf instead.<br>
</li><li>Further simplified widget selection.<br>
</li><li>Moved terminal widget search to a separate function.<br>
</li><li>Improved method of getting colors for Embedded Terminal.<br>
</li><li>Added restoration of colors and terminal font when plugin is deactivated.<br>
<b>Version 1.6.0, 2010-03-01</b>
</li><li>Changed to default to system colors instead of black-on-white.<br>
<ul><li>This is important if you use a desktop theme with normal text coloring other than black-on-white, e.g. <a href='http://customize.org/gtk/themes/66374'>BlackBird</a>, along with a Gedit color scheme that doesn't redefine the normal text colors, e.g. Classic or Tango.<br>
</li></ul></li><li>Added applying the editor font to the Embedded Terminal.<br>
<ul><li>To disable this, just set <code>TERMINAL_MATCH_FONT = False</code> in color_panes.py.<br>
<b>Version 1.5.0, 2010-02-25</b>
</li></ul></li><li>Improved how and when the plugin does its work, so it is much more efficient.<br>
</li><li>Updates the color scheme of the panes as soon as you switch color schemes.<br>
</li><li>Re-colors new plugin views as soon as they are added.<br>
<b>Version 1.0.1, 2010-02-21</b>
</li><li>Added coloring of Embedded Terminal and Character Map table.<br>
<b>Version 1.0, 2010-02-20</b>
</li><li>Initial release.</li></ul>

<h2>Origin</h2>
Question from Petr Mach on gedit-list:<br>
<a href='http://mail.gnome.org/archives/gedit-list/2010-February/msg00016.html'>http://mail.gnome.org/archives/gedit-list/2010-February/msg00016.html</a>