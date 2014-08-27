#!/usr/bin/env python
'''
Exports layers and paths to OpenRaster compatible file with
extra metadata usefule for importing into LOVE games.
'''

import csv
import errno
import os.path
import shutil
import xml.etree.cElementTree as et
from zipfile import ZipFile

import gimpfu
from gimp import pdb

def ora_love(img, active_layer, compression, dir_name, should_merge, should_zip):
    ''' Plugin entry point
    '''

    # Create the root now
    root = et.Element('image')
    root.set('w', unicode(img.width))
    root.set('h', unicode(img.height))
    stack = et.SubElement(root, 'stack')

    # Create the image directory
    name = os.path.splitext(os.path.basename(img.filename))[0]
    base_dir = os.path.join(dir_name, name)
    if os.access(base_dir, os.F_OK):
        shutil.rmtree(base_dir, ignore_errors=False)
    mkdirs(os.path.join(base_dir, 'data'))

    # Save the layer images and metadata
    for layer in img.layers:
        to_save = process_layer(img, layer, stack, ['data'], base_dir, should_merge)
        save_layers(img, to_save, compression, base_dir)

    # Write the thumbnail
    save_thumb(img, base_dir)

    if len(img.vectors) > 0:
        # Create the path directory
        paths_path = os.path.join(base_dir, 'paths')
        mkdirs(paths_path)

        # Save the paths and metadata
        paths_node = et.SubElement(root, 'paths')
        for path in img.vectors:
            to_save = process_path(path, paths_node, ['paths'])
            save_paths(to_save, base_dir)

    # Write the mimetype file
    with open(os.path.join(base_dir, 'mimetype'), 'w') as output_file:
        output_file.write('image/openraster')

    # Write the metadata file
    with open(os.path.join(base_dir, 'stack.xml'), 'w') as output_file:
        et.ElementTree(root).write(output_file)

    # Zip it, if requested
    if should_zip:
        with ZipFile(os.path.join(dir_name, '%s.ora' % name), 'w') as f:
            old_cwd = os.getcwd()
            os.chdir(base_dir)
            try:
                for root, dirs, files in os.walk('.'):
                    for filename in files:
                        full_path = os.path.join(root, filename)
                        f.write(full_path, full_path[2:])
            finally:
                os.chdir(old_cwd)


def process_layer(img, layer, stack, dir_stack, base_dir, should_merge):
    processed = []

    # If this layer is a layer has sublayers, recurse into them
    if not should_merge and hasattr(layer, 'layers'):
        new_dir_stack = dir_stack + [layer.name]
        try:
            os.makedirs(os.path.join(base_dir, *new_dir_stack))
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        for sublayer in layer.layers:
            processed.extend(process_layer(img, sublayer, stack, new_dir_stack, base_dir, should_merge))
    else:
        layer_name = layer.name
        x, y = layer.offsets
        filename = '/'.join(dir_stack + ['%s.png' % layer_name])

        layer_node = et.SubElement(stack, 'layer')
        layer_node.set('name', layer_name)
        layer_node.set('src', filename)
        layer_node.set('x', unicode(x))
        layer_node.set('y', unicode(y))

        # Hardcoded vals. FIXME one day
        layer_node.set('composite-op', 'svg:src-over')
        layer_node.set('opacity', '1.0')
        layer_node.set('visibility', 'visible')

        processed.append((filename, layer))

    return processed

def save_layers(img, layers, compression, base_dir):
    for rel_path, layer in layers:
        rel_path = rel_path.replace('/', os.sep)
        tmp_img = pdb.gimp_image_new(img.width, img.height, img.base_type)
        tmp_layer = pdb.gimp_layer_new_from_drawable(layer, tmp_img)
        tmp_layer.name = layer.name
        tmp_img.add_layer(tmp_layer, 0)
        tmp_img.resize_to_layers()

        full_path = os.path.join(base_dir, rel_path)
        filename = os.path.basename(rel_path)

        pdb.file_png_save(
            tmp_img,
            tmp_img.layers[0],
            full_path,
            filename,
            0, # interlace
            compression, # compression
            1, # bkgd
            1, # gama
            1, # offs
            1, # phys
            1 # time
        )

def process_path(path, paths_node, base_dir):
    data = [[None] * 8]
    strokes_count = 0

    for stroke in path.strokes:
        strokes_count = strokes_count+1
        stroke_points, is_closed = stroke.points

        # copy triplets
        for triplet in range(0, len(stroke_points), 6):
            row = [path.name, strokes_count]
            row.extend(stroke_points[triplet:triplet + 6])
            data.append(row)
        # for closed stroke, close with first triplet
        if is_closed:
            row = [path.name, strokes_count]
            row.extend(stroke_points[:6])
            data.append(row)

    filename = '/'.join(base_dir + ['%s.csv' % path.name])

    path_node = et.SubElement(paths_node, 'path')
    path_node.set('name', path.name)
    path_node.set('src', filename)

    return [(filename, data)]

def save_paths(paths, base_dir):
    for rel_path, path_data in paths:
        rel_path = rel_path.replace('/', os.sep)
        with open(os.path.join(base_dir, rel_path), 'w') as f:
            writer = csv.writer(f)
            writer.writerows(path_data)

def save_thumb(img, base_dir):
    tmp_img = pdb.gimp_image_new(img.width, img.height, img.base_type)
    for i, layer in enumerate(img.layers):
        tmp_layer = pdb.gimp_layer_new_from_drawable(layer, tmp_img)
        tmp_img.add_layer(tmp_layer, i)
    flattened = tmp_img.flatten()

    max_dim = 255
    if img.width > max_dim or img.height > max_dim:
        if img.width > img.height:
            width = max_dim
            height = width * img.height / img.width
        elif img.width < img.height:
            height = max_dim
            width = height * img.width / img.height
        else:
            width = height = max_dim
        pdb.gimp_image_scale(tmp_img, width, height)

    thumb_path = os.path.join(base_dir, 'Thumbnails')
    mkdirs(thumb_path)
    thumb_filename = 'thumbnail.png'
    pdb.file_png_save_defaults(tmp_img, flattened, os.path.join(thumb_path, thumb_filename), thumb_filename)

def mkdirs(dir_name):
    try:
        os.makedirs(dir_name)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

gimpfu.register(
    # name
    "ora-love",
    # blurb
    "OpenRaster-love exporter",
    # help
    "Exports layers and paths to OpenRaster file with extra metadata useful for importing into LOVE games",
    # author
    "Carlo Cabanilla",
    # copyright
    "Carlo Cabanilla",
    # date
    "2014",
    # menupath
    "<Image>/File/Export/Export as ora-love",
    # imagetypes
    "*",
    # params
    [
        (gimpfu.PF_ADJUSTMENT, "compression", "PNG Compression level:", 0, (0, 9, 1)),
        (gimpfu.PF_DIRNAME, "dir", "Directory", os.getcwd()),
        (gimpfu.PF_BOOL, "should_merge", "Merge layer groups?", True),
        (gimpfu.PF_BOOL, "should_zip", "Zip to .ora?", False),
    ],
    # results
    [],
    # function
    ora_love
)

gimpfu.main()
