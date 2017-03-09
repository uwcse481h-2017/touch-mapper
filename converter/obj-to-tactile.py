from __future__ import print_function
import sys
import argparse
import os
import pprint
import bpy
import mathutils
import bmesh
import json
import math
import random
import time

ROAD_HEIGHT_CAR_MM = 0.82 # 3 x 0.25-0.3mm layers
ROAD_HEIGHT_PEDESTRIAN_MM = 2.2 #1.5
BUILDING_HEIGHT_MM = 0.75 # 2.9
BASE_HEIGHT_MM = 1.75 # 0.6 Jess's--1.75?
BASE_OVERLAP_MM = 0.01
WATER_AREA_DEPTH_MM = 1.5
WATER_WAVE_DISTANCE_MM = 10.3
WATERWAY_DEPTH_MM = 0.55 # 2 x 0.25-0.3mm layers
BORDER_WIDTH_MM = 1.2 # 3 shells
BORDER_HEIGHT_MM = (ROAD_HEIGHT_PEDESTRIAN_MM + BUILDING_HEIGHT_MM) / 2
BORDER_HORIZONTAL_OVERLAP_MM = 0.05
MARKER_HEIGHT_MM = BUILDING_HEIGHT_MM + 2
MARKER_RADIUS_MM = MARKER_HEIGHT_MM * 0.5

def warning(*objs):
    print("WARNING: ", *objs, file=sys.stderr)

def do_cmdline():
    parser = argparse.ArgumentParser(description='''Read an OSM map as a .obj file, modify it to a tactile map, and export as .stl''')
    parser.add_argument('--min-x', metavar='FLOAT', type=float, help='minimum X bound')
    parser.add_argument('--min-y', metavar='FLOAT', type=float, help='minimum Y bound')
    parser.add_argument('--max-x', metavar='FLOAT', type=float, help='maximum X bound')
    parser.add_argument('--max-y', metavar='FLOAT', type=float, help='maximum Y bound')
    parser.add_argument('--no-stl-export', action='store_true', help='do not export to .stl file')
    parser.add_argument('--scale', metavar='N', type=int, help="scale to export STL in, 4000 would mean one Blender unit (meter) = 0.25mm (STL file unit is normally mm)")
    parser.add_argument('--marker1', metavar='MARKER', help="first marker's position relative to top left corner")
    parser.add_argument('--diameter', metavar='METERS', type=int, help="larger of map area x and y diameter in meters")
    parser.add_argument('--no-borders', action='store_true', help="don't draw borders around the edges")
    parser.add_argument('obj_paths', metavar='PATHS', nargs='+', help='.obj files to use as input')
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    return args

def print_verts(ob):
    for v in ob.data.vertices:
        print(ob.name, ob.matrix_world * mathutils.Vector(v.co))

def get_minimum_coordinate(ob):
    bbox_corners = [ob.matrix_world * mathutils.Vector(corner) for corner in ob.bound_box]
    min_x = 1000000
    min_y = 1000000
    min_z = 1000000
    for corner in bbox_corners:
        min_x = min(min_x, corner[0])
        min_y = min(min_y, corner[1])
        min_z = min(min_z, corner[2])
    return (min_x, min_y, min_z)

def move_everything(move_by):
    vector = mathutils.Vector(move_by)
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH':
            ob.location += vector

def _export_stl(stl_path, scale):
    print("creating {stl}...".format(stl=stl_path))
    bpy.ops.export_mesh.stl(filepath=stl_path, check_existing=False, \
                            axis_forward='Y', axis_up='Z', global_scale=(1000 / scale))

def export_stl(base_path, scale):
    bpy.ops.object.select_all(action='SELECT')
    _export_stl(base_path + '.stl', scale)

def export_stl_separate(base_path, scale):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        ob.select = ob.name.endswith('Roads') or ob.name.endswith('RoadAreas') or ob.name.endswith('Rails')
    _export_stl(base_path + '-ways.stl', scale)
    bpy.ops.object.select_all(action='INVERT')
    _export_stl(base_path + '-rest.stl', scale)

def export_blend_file(base_path):
    blend_path = base_path + '.blend'
    bpy.ops.object.select_all(action='SELECT') # it's handy to have everything selected initially
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False, compress=True)
    
def create_cube(min_x, min_y, max_x, max_y, min_z, max_z):
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent()
    bpy.ops.object.mode_set(mode = 'OBJECT')
    cube.location = [ (min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2 ]
    cube.scale = [ (max_x - min_x) / 2, (max_y - min_y) / 2, (max_z - min_z) / 2 ]
    bpy.context.scene.update() # flush changes to location and scale
    return cube

def add_borders(min_x, min_y, max_x, max_y, width, bottom, height, corner_height):
    borders = []
    # north edge
    borders.append(create_cube(min_x, max_y, max_x, max_y - width, bottom, height))
    join_objects(borders, 'Borders')

def create_bounds(min_x, min_y, max_x, max_y, scale, no_borders):
    mm_to_units = scale / 1000
    if not no_borders:
        add_borders(min_x, min_y, max_x, max_y, BORDER_WIDTH_MM * mm_to_units, \
                    0, BORDER_HEIGHT_MM * mm_to_units, (BUILDING_HEIGHT_MM + 1) * mm_to_units)
    base_height = BASE_HEIGHT_MM * mm_to_units
    overlap = BASE_OVERLAP_MM * mm_to_units # move cube this much up so that it overlaps enough with objects they merge into one object
    base_cube = create_cube(min_x, min_y, max_x, max_y, -base_height + overlap, overlap)
    base_cube.name = 'Base'
    return base_cube

def add_marker1(args, scale):
    min_x, min_y, max_x, max_y = (args.min_x, args.min_y, args.max_x, args.max_y)
    if args.marker1 == 'center':
        marker_x, marker_y = (0.5, 0.5)
    else:
        coords = json.loads(args.marker1)
        marker_x = float(coords['x'])
        marker_y = float(coords['y'])
        
    mm_to_units = scale / 1000
    radius = MARKER_RADIUS_MM * mm_to_units
    height = (MARKER_HEIGHT_MM * mm_to_units) + 1.5
    # If the cone has sharp top, three.js won't render it remotely properly, and it'll 3D print poorly too
    bpy.ops.mesh.primitive_cone_add(vertices = 16, radius1 = radius, radius2 = radius / 8, depth = height, \
        location = [ min_x + (max_x - min_x) * marker_x, min_y + (max_y - min_y) * marker_y, height / 2 ])
    bpy.context.active_object.name = 'SelectedAddress'
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.translate(value=(0, 0, -1.5))
    bpy.ops.object.mode_set(mode='OBJECT')

def remove_everything():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

# Import given file as .obj and return it
def import_obj_file(obj_path):
    t = time.clock()
    bpy.ops.import_scene.obj(filepath=obj_path, axis_forward='-Z', axis_up='Y')
    print("importing STL took " + (str(time.clock() - t)))

# Extrude floor to a flat-roofed building
def extrude_building(ob, height):
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={ "value": (0.0, 0.0, height) })    
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent()
    bpy.ops.object.mode_set(mode = 'OBJECT') 

def clip_object_to_map(ob, min_co, max_co):
    try:
        #print("Clipping {}".format(ob.name))
        bpy.context.scene.objects.active = ob
        bpy.ops.object.mode_set(mode = 'EDIT')

        # Clip from all sides
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.bisect(plane_co=min_co, plane_no=(-1, 0, 0), clear_outer=True, use_fill=True)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.bisect(plane_co=min_co, plane_no=(0, -1, 0), clear_outer=True, use_fill=True)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.bisect(plane_co=max_co, plane_no=(1, 0, 0), clear_outer=True, use_fill=True)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.bisect(plane_co=max_co, plane_no=(0, 1, 0), clear_outer=True, use_fill=True)

        bpy.ops.object.mode_set(mode = 'OBJECT')
        return True
    except Exception as e:
        warning("Failed to clip {}: {}".format(ob.name, str(e)))
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        ob.select = True
        bpy.context.scene.objects.active = ob
        try:
            bpy.ops.object.delete()
        except Exception as e:
            print("Failed to remove {}: {}".format(ob.name, str(e)))
        return False

def join_selected(name):
    combined = bpy.context.selected_objects[0]
    bpy.context.scene.objects.active = combined
    combined.name = name
    bpy.ops.object.join()
    return combined

def join_objects(objects, name):
    if len(objects) == 0:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.select = True
    return join_selected(name)

def join_and_clip(objects, min_co, max_co, name):
    if len(objects) == 0:
        return None
    combined = join_objects(objects, name)
    clip_object_to_map(combined, min_co, max_co)
    return combined

def raise_ob(objs, height):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.objects.active = objs
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={ "value": (0.0, 0.0, height) })
    bpy.ops.object.mode_set(mode = 'OBJECT')

def water_remesh_and_extrude(object, extrude_height):
    # Extrude just enough that remeshing works
    bpy.context.scene.objects.active = object
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={ "value": (0.0, 0.0, extrude_height) })
    bpy.ops.mesh.normals_make_consistent()
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # Remesh
    max_dimension = max(object.dimensions[0], object.dimensions[2])
    depth = min(max(math.log2(max_dimension) - 1, 2), 8) # Max vertex distance == 2m => max dimension 128 == remesh depth 6 (or so)
    modifier = object.modifiers.new('Modifier', 'REMESH')
    modifier.octree_depth = math.ceil(depth)
    modifier.use_remove_disconnected = False
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier.name)

def water_wave_pattern(object, depth, scale):
    extrude_height = 1.0
    water_remesh_and_extrude(object, extrude_height)

    # Start creating wave pattern
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bm = bmesh.from_edit_mesh(object.data)
    bm.verts.ensure_lookup_table()

    # Record x,z positions of edge verts (verts of non-horizontal edges)
    edge_verts = {}
    for edge in bm.edges:
        verts = edge.verts
        if abs(verts[0].co.y - verts[1].co.y) > extrude_height / 2:
            edge_verts[str(verts[0].co.x) + ',' + str(verts[0].co.z)] = True

    # Set top verts' y positions. Bottom verts are at 0.
    density = math.pi * 2 / WATER_WAVE_DISTANCE_MM / (scale/1000) 
    for v in bm.verts:
        if v.co.y > extrude_height / 2:
            min_height = -10000
            if str(v.co.x) + ',' + str(v.co.z) in edge_verts:
                min_height = depth / 4
            v.co.y = max(min_height, (math.sin(v.co.x * density) + math.sin(v.co.z * density)) * depth / 4 + depth / 2)
        else:
            v.co.y = 0
    bmesh.update_edit_mesh(object.data, tessface=False, destructive=False)

    bpy.ops.object.mode_set(mode = 'OBJECT')

def is_pedestrian(road_name):
    return road_name.endswith('::pedestrian')

## Disable stdout buffering
#class Unbuffered(object):
#   def __init__(self, stream):
#       self.stream = stream
#   def write(self, data):
#       self.stream.write(data)
#       self.stream.flush()
#   def __getattr__(self, attr):
#       return getattr(self.stream, attr)
#
#sys.stdout = Unbuffered(sys.stdout)


# Join edges that seem to form two ends of the same logical road or railway
def join_matching_edges(ob, min_x, min_y, max_x, max_y):
    lt = 0.2  # length difference + -
    dt = 0.15  # max distance 
    at = 0.5  # max sin(angle)  (30°)
    
    bpy.context.scene.objects.active = ob
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    from math import sin
    bm = bmesh.from_edit_mesh( bpy.context.object.data )
    bm.edges.ensure_lookup_table()
    
    center   = lambda e : ( e.verts[0].co + e.verts[1].co ) / 2
    length   = lambda e : ( e.verts[0].co - e.verts[1].co ).length
    dist     = lambda v1, v2: (  v2 -  v1 ).length
    sinAngle = lambda e1, e2: abs(sin((e1.verts[1].co - e1.verts[0].co).angle(e2.verts[1].co - e2.verts[0].co)))

    def point_between_edge_neighbor_verts(e):
        # Return middle of the verts adjacent to the edge
        verts = []
        for v in e.verts:
            for linked_e in v.link_edges:
                verts.extend((vv for vv in linked_e.verts if vv != e.verts[0] and vv != e.verts[1]))
        if len(verts) != 2:
            #print("edge has non-2 adjacent verts: " + str(len(verts)))
            return None
        return ((verts[0].co[0] + verts[1].co[0]) / 2, \
                (verts[0].co[1] + verts[1].co[1]) / 2, \
                (verts[0].co[2] + verts[1].co[2]) / 2)
    
    class CEdge:
        def __init__(self, e, into_edge):
            self.e = e
            self.center = center(e)
            self.length = length(e)
            self.into_edge = into_edge
            self.welded = False
    
    # Lengthen an edge that is supposedly at the end of a road, in an attempt to make roads'
    # widths consistent, instead of being the more narrow the greater the angle of their end edge.
    radians_90degrees = math.pi / 2
    def lengthen_edges(ce1, ce2):
        for ce in (ce1, ce2):
            verts = ce.e.verts
            edge_v = mathutils.Vector(verts[0].co) - mathutils.Vector(verts[1].co)
            angle = ce.into_edge.angle(edge_v)
            if abs(angle - radians_90degrees) > radians_90degrees / 9:
                multiplier = 1 / math.sin(angle)
                print("angle: %f, mult: %f" % (angle * (90 / radians_90degrees), multiplier))
                if multiplier > 3:
                    print("abnormally high multiplier, not lengthening")
                else:
                    verts[0].co = ce.center + (verts[0].co - ce.center) * multiplier
                    verts[1].co = ce.center + (verts[1].co - ce.center) * multiplier
    
    def filter_edges(edges):
        out = []
        for e in edges:
            if len(e.link_faces) != 1:
                continue
            # Because roads are clipped at the edges, funny coincidences can happen, so ignore those edges
            c = center(e)
            if abs(c[0] - min_x) < 0.1 or abs(c[0] - max_x) < 0.1 or abs(c[2] - min_y) < 0.1 or abs(c[2] - max_y) < 0.1:
                continue
            point_between_edges = point_between_edge_neighbor_verts(e)
            if not point_between_edges:
                continue
            vector_into_edge_face = center(e) - mathutils.Vector(point_between_edges)
            if vector_into_edge_face.length == 0:
                continue
            out.append(CEdge(e, vector_into_edge_face / vector_into_edge_face.length))
        return out
    candidate_edges = filter_edges(bm.edges)

    # Index edges into search tree
    edge_index_to_ce = {} # enable finding CEdge by edge
    kd = mathutils.kdtree.KDTree(len(candidate_edges))
    for i, ce in enumerate(candidate_edges):
        kd.insert(ce.center, i)
        edge_index_to_ce[ce.e.index] = ce
    kd.balance()

    def mark_all_t_junction_edges_welded(cedge):
        face_edges = cedge.e.link_faces[0].edges
        if len(face_edges) == 6:
            # Faces with 6 edges are probably T junctions. If we allow multiple roads
            # to connect to them, we often get a road that intersects itself (because X junctions are disabled in OSM2World)
            for fe in face_edges:
                fe_ce = edge_index_to_ce.get(fe.index, None)
                if fe_ce:
                    fe_ce.welded = True

    to_weld = {}
    for i, ce in enumerate(candidate_edges[:-1]):
        if ce.welded:
            continue
        ce.welded = True
        lmin = ce.length - lt
        lmax = ce.length + lt
        matches = []
        for (_co, oe_index, _dist) in kd.find_range(ce.center, dt):
            oe = candidate_edges[oe_index]
            if not oe.welded and lmin < oe.length < lmax and sinAngle(ce.e, oe.e) < at:
                turn_angle = ce.into_edge.angle(-oe.into_edge)
                if turn_angle > math.pi * 0.6: # pi * 0.5 is 90%
                    #print("not merging edges (%s, %s) pointing to opposite directions, angle is %f" % (ce.e, oe.e, turn_angle))
                    continue
                matches.append(oe)
                oe.welded = True
        
        if len(matches) == 1:
            # Join nothing where >2 ways meet, else all roads in the scene may become joined and intersect itself
            ev1, ev2 = ce.e.verts[:]
            oev1, oev2 = matches[0].e.verts[:]
            if dist(ev1.co, oev1.co) < dist(ev1.co, oev2.co) :
                if ev1 != oev1: to_weld[ev1] = oev1
                if ev2 != oev2: to_weld[ev2] = oev2
            else :
                if ev1 != oev2: to_weld[ev1] = oev2
                if ev2 != oev1: to_weld[ev2] = oev1
                # TODO: move welded verts to locations between the originals?
            lengthen_edges(ce, matches[0])
            mark_all_t_junction_edges_welded(ce)
            mark_all_t_junction_edges_welded(matches[0])
            
    print("%s: melding %d out of %d edges" % (ob.name, len(to_weld) / 2, len(bm.edges)))
    bmesh.ops.weld_verts(bm, targetmap = to_weld)
    bmesh.update_edit_mesh(bpy.context.object.data ,True)
    bpy.ops.object.mode_set(mode = 'OBJECT')

# Decimating gets rid of useless and harmful lane edges, as well as changing
# tris to n-gons (important to find edge's "direction")
def decimate(ob):
    # Decimating gets rid of useless lanes
    bpy.context.scene.objects.active = ob
    modifier = ob.modifiers.new('Modifier', 'DECIMATE')
    modifier.decimate_type = 'DISSOLVE'
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier.name)

# Fatten slightly to cause overlap and avoid faces too close to each other
def fatten(ob):
    bpy.context.scene.objects.active = ob
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.transform.shrink_fatten(value=-0.05) # less than this and programs start to "remove double vertices"
    bpy.ops.object.mode_set(mode = 'OBJECT')

def do_ways(ways, height, min_x, min_y, max_x, max_y):
    if ways == None:
        return
    t = time.clock()
    decimate(ways)
    join_matching_edges(ways, min_x, min_y, max_x, max_y)
    raise_ob(ways, height)
    fatten(ways)
    print("processing %s took %.2f" % (ways.name, time.clock() - t))

def do_road_areas(roads, height):
    if roads == None:
        return
    t = time.clock()
    decimate(roads)
    raise_ob(roads, height)
    fatten(roads)
    #print("processing %s took %.2f" % (roads.name, time.clock() - t))

def do_building(building, mm_to_units):
    if building == None:
        return
    extrude_building(building, BUILDING_HEIGHT_MM * mm_to_units)
    # move the buliding down 1.5 units
    bpy.context.scene.objects.active = building
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.translate(value=(0, 0, -1.5))
    bpy.ops.object.mode_set(mode='OBJECT')

def process_objects(min_x, min_y, max_x, max_y, scale, no_borders):
    t = time.clock()
    mm_to_units = scale / 1000
    if not no_borders:
        space = (BORDER_WIDTH_MM - BORDER_HORIZONTAL_OVERLAP_MM) * mm_to_units 
        min_x = min_x
        min_y = min_y
        max_x = max_x
        max_y = max_y - space # to make room for the north edge
    min_co = (min_x, min_y, 0)
    max_co = (max_x, max_y, 0)

    # First find out everything that we can join together into combined objects and do join,
    # because CPU usage is dominated by each Blender operation iterating through every object in the scene.
    roads_car = []
    roads_ped = []
    road_areas_car = []
    road_areas_ped = []
    buildings = []
    rails = []
    clippable_waterways = []
    clippable_water_areas = []
    joinable_waterways = []
    inner_water_areas = []
    deleteables = []
    points_of_interest = []
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        if ob.name == 'map':
            # Happens when there is nothing on the map
            continue

        if ob.name.startswith('BuildingEntrance'):
            deleteables.append(ob)
        elif ob.name.startswith('Building'):
            buildings.append(ob)
        elif ob.name.startswith('Road'):
            if is_pedestrian(ob.name):
                if ob.name.startswith('RoadArea'):
                    road_areas_ped.append(ob)
                else:
                    roads_ped.append(ob)
            else:
                if ob.name.startswith('RoadArea'):
                    road_areas_car.append(ob)
                else:
                    roads_car.append(ob)
        elif ob.name.startswith('Rail'):
            rails.append(ob)
        elif ob.name.startswith('Point'):
            points_of_interest.append(ob)
        else:
            n_total = len(ob.data.vertices)
            n_outside = 0
            for vert in ob.data.vertices:
                vx, vy, vz = ((ob.matrix_world * vert.co))
                if vx < min_x or vx > max_x or vy < min_y or vy > max_y:
                    n_outside = n_outside + 1

            if n_outside == 0:
                if ob.name.startswith('Waterway') or ob.name.startswith('River'):
                    joinable_waterways.append(ob)
                elif ob.name.startswith('Water') or ob.name.startswith('AreaFountain'):
                    inner_water_areas.append(ob)
                else:
                    print("UNHANDLED INNER OBJECT TYPE: " + ob.name)
            elif n_outside == n_total:
                deleteables.append(ob)
            else:
                if ob.name.startswith('Waterway') or ob.name.startswith('River'):
                    clippable_waterways.append(ob)
                elif ob.name.startswith('Water') or ob.name.startswith('AreaFountain'):
                    clippable_water_areas.append(ob)
                else:
                    print("UNHANDLED CLIPPABLE OBJECT TYPE: " + ob.name)
    print("initial steps took %.2f" % (time.clock() - t))

    # Delete
    t = time.clock()
    if len(deleteables) > 0:
        bpy.ops.object.select_all(action='DESELECT')
        for ob in deleteables:
            ob.select = True
        bpy.ops.object.delete()
        #print("deleting %d objects took %.2f" % (len(deleteables), time.clock() - t))

    # Pre-join stuff for performance
    joined_roads_car = join_and_clip(roads_car, min_co, max_co, 'CarRoads')
    joined_roads_ped = join_and_clip(roads_ped, min_co, max_co, 'PedestrianRoads')
    joined_road_areas_car = join_and_clip(road_areas_car, min_co, max_co, 'CarRoadAreas')
    joined_road_areas_ped = join_and_clip(road_areas_ped, min_co, max_co, 'PedestrianRoadAreas')
    clipped_rails = join_and_clip(rails, min_co, max_co, 'Rails')
    joined_pois = join_objects(points_of_interest, 'PointsOfInterest')

    # Waters
    t = time.clock()
    if len(joinable_waterways) > 0:
        joined_waterways = join_objects(joinable_waterways, 'JoinedWaterways')
        raise_ob(joined_waterways, WATERWAY_DEPTH_MM * mm_to_units)
    if len(clippable_waterways) > 0:
        clipped_waterways = join_and_clip(clippable_waterways, min_co, max_co, 'ClippedWaterways')
        raise_ob(clipped_waterways, WATERWAY_DEPTH_MM * mm_to_units)
    if len(clippable_water_areas) > 0:
        for water in clippable_water_areas:
            clip_object_to_map(water, min_co, max_co)
            water_wave_pattern(water, WATER_AREA_DEPTH_MM * mm_to_units, scale)
        join_objects(clippable_water_areas, 'ClippedWaterAreas')
    if len(inner_water_areas):
        for water in inner_water_areas:
            water_wave_pattern(water, WATER_AREA_DEPTH_MM * mm_to_units, scale)
        join_objects(inner_water_areas, 'InnerWaterAreas')
    print("processing waters took %.2f" % (time.clock() - t))

    # Rails
    if clipped_rails != None:
        do_ways(clipped_rails, ROAD_HEIGHT_CAR_MM * mm_to_units * 0.99, min_x, min_y, max_x, max_y) # 0.99 to avoid faces in the same coordinates with roads

    # Roads
    do_road_areas(joined_road_areas_car, ROAD_HEIGHT_CAR_MM * mm_to_units)
    do_road_areas(joined_road_areas_ped, ROAD_HEIGHT_PEDESTRIAN_MM * mm_to_units)
    do_ways(joined_roads_car, ROAD_HEIGHT_CAR_MM * mm_to_units, min_x, min_y, max_x, max_y)
    do_ways(joined_roads_ped, ROAD_HEIGHT_PEDESTRIAN_MM * mm_to_units, min_x, min_y, max_x, max_y)

    # lower the paths so they don't float above the inset buildings
    if joined_road_areas_ped:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.objects.active = joined_road_areas_ped
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.transform.translate(value=(0, 0, -1.5))
        bpy.ops.object.mode_set(mode='OBJECT')
    if joined_roads_ped:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.objects.active = joined_roads_ped
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.transform.translate(value=(0, 0, -1.5))
        bpy.ops.object.mode_set(mode='OBJECT')

    # Points of Interest
    # lower them so they don't float above the inset buildings
    if joined_pois:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.objects.active = joined_pois
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.transform.translate(value=(0, 0, -1.5))
        bpy.ops.object.mode_set(mode='OBJECT')

    # Buildings
    # first shrink them individually
    if len(buildings) > 0:
        for building in buildings:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.scene.objects.active = building
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.transform.resize(value=(0.75, 0.75, 1)) # shrinks on x and y axis by 0.75
            bpy.ops.object.mode_set(mode='OBJECT')
    # then join, clip, and process them as one unit
    if len(buildings) > 0:
        joined_buildings = join_and_clip(buildings, min_co, max_co, 'Buildings')
        print('META-START:{"building_count":%d}:META-END\n' % (len(buildings)))
    if joined_buildings:
        t = time.clock()
        do_building(joined_buildings, mm_to_units)
        print("processing %d buildings took %.2f" % (len(buildings), time.clock() - t))


def make_tactile_map(args):
    t = time.clock()
    min_x, min_y, max_x, max_y = (args.min_x, args.min_y, args.max_x, args.max_y)
    
    process_objects(min_x, min_y, max_x, max_y, args.scale, args.no_borders)
    print("process_objects() took " + (str(time.clock() - t)))

    # Create the support cube and borders
    base_cube = create_bounds(min_x, min_y, max_x, max_y, args.scale, args.no_borders)

    # Dig out the buildings by boolean differencing the base with them
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.scene.objects.active = bpy.data.objects['Base']
    bpy.ops.object.modifier_add(type='BOOLEAN')
    bpy.context.object.modifiers["Boolean"].operation = 'DIFFERENCE'
    bpy.context.object.modifiers["Boolean"].object = bpy.data.objects['Buildings']
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='Boolean')

    # Delete the buildings so we can see them inset rather than protruding
    bpy.data.objects['Base'].select = False
    bpy.data.objects['Buildings'].select = True
    bpy.ops.object.delete()

    # Add marker(s)
    if args.marker1 != None:
        add_marker1(args, args.scale)
        
    return base_cube

def main():
    args = do_cmdline()
    remove_everything()
    for obj_path in args.obj_paths:
        import_obj_file(obj_path)
        base_cube = make_tactile_map(args)
        move_everything([-c for c in get_minimum_coordinate(base_cube)])
        if not args.no_stl_export:
            base_path = os.path.splitext(obj_path)[0]
            export_stl(base_path, args.scale)
            export_stl_separate(base_path, args.scale)
            export_blend_file(base_path)
    bpy.ops.object.select_all(action='SELECT') # it's handy to have everything selected when getting into UI

if __name__ == "__main__":
    main()
