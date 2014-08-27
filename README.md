# gimp-ora-plus

`gimp-ora-plus` exports a GIMP xcf file as an OpenRaster file. GIMP already has OpenRaster export built-in, but this plugin will also export your paths, which the built-in functionality does do. Additionally, this plugin will let you associate arbitrary attributes to your layers and paths.

## Install

To install, put gimp_ora_plus.py in your [plugins directory](http://en.wikibooks.org/wiki/GIMP/Installing_Plugins#Copying_the_plugin_to_the_GIMP_plugin_directory).

## Usage

To export, open up GIMP and select `File -> Export as OpenRaster Plus` from the menu.

To specify custom metadata on a layer or path, you'll need to add to add a url querystring-like string to your layer or path's name. For example, if you name your layer:

```
rock?type=obstacle&weight=50
```

The resulting xml metadata will look like:

```
<layer name="rock" type="obstacle" weight="50" />
```

Which you can then use in whatever other program you're importing this data into.

Specifying an attribute twice like this:

```
wall?material=wood&material=metal
```

will create a comma-separated array like this:

```
<layer name="wall" material="wood,metal"  />
```

Paths are exported as CSVs, following the [path-csv format](http://gimp-path-tools.sourceforge.net/tools.shtml#path-csv).
