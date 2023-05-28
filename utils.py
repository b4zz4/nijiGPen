import math
import bpy
from mathutils import *

SCALE_CONSTANT = 8192
LINE_WIDTH_FACTOR = 2000.0

def linear_to_srgb(color):
    """
    Convert a Linear RGB value to an sRGB one. Can be replaced by from_scene_linear_to_srgb() if Blender version >= 3.2
    """
    s_color = 0
    if color < 0.0031308:
        s_color = 12.92 * color
    else:
        s_color = 1.055 * math.pow(color, 1/2.4) - 0.055
    return s_color

def srgb_to_linear(color):
    '''
    Can be replaced by from_srgb_to_scene_linear() if Blender version >= 3.2
    '''
    if color<0:
        return 0
    elif color<0.04045:
        return color/12.92
    else:
        return ((color+0.055)/1.055)**2.4

def hex_to_rgb(h, to_linear = False) -> Color:
    r = (h & 0xff0000) >> 16 
    g = (h & 0x00ff00) >> 8
    b = (h & 0x0000ff)
    if to_linear:
        return Color((srgb_to_linear(r/255.0), srgb_to_linear(g/255.0), srgb_to_linear(b/255.0)))
    else:
        return Color((r/255.0, g/255.0, b/255.0))
    
def rgb_to_hex_code(color:Color) -> str:
    r,g,b = int(color[0]*255), int(color[1]*255), int(color[2]*255)
    hex_code = f"#{r:02x}{g:02x}{b:02x}"
    return hex_code

def smoothstep(x):
    if x<0:
        return 0
    if x>1:
        return 1
    return 3*(x**2) - 2*(x**3)

def get_concyclic_info(x0,y0,x1,y1,x2,y2):
     """
     Given three 2D points, calcualte their concyclic center and reciprocal radius
     """
     # Coefficients of the formula
     a = 2*(x1-x0)
     b = 2*(y1-y0)
     c = x1**2 - x0**2 + y1**2 - y0**2
     d = 2*(x2-x0)
     e = 2*(y2-y0)
     f = x2**2 - x0**2 + y2**2 - y0**2
     det = a*e - b*d
     
     # Case of colinear points
     if math.isclose( det, 0 ):
         return 0, None
     
     # Solution of the formula
     xc = (c*e-f*b)/det
     yc = (a*f-c*d)/det
     center = Vector(( xc, yc ))
     radius = math.sqrt((x0-xc)**2 + (y0-yc)**2)
     
     return 1.0/radius, center

def vec3_to_vec2(co) -> Vector:
    """Convert 3D coordinates into 2D"""
    scene = bpy.context.scene
    if scene.nijigp_working_plane == 'X-Z':
        return Vector([co.x, -co.z])
    if scene.nijigp_working_plane == 'Y-Z':
        return Vector([co.y, -co.z])
    if scene.nijigp_working_plane == 'X-Y':
        return Vector([co.x, -co.y])

def vec2_to_vec3(co, depth = 0.0, scale_factor = 1.0) -> Vector:
    """Convert 2D coordinates into 3D"""
    scene = bpy.context.scene
    if scene.nijigp_working_plane == 'X-Z':
        return Vector([co[0] / scale_factor, -depth, -co[1] / scale_factor])
    if scene.nijigp_working_plane == 'Y-Z':
        return Vector([depth, co[0] / scale_factor, -co[1] / scale_factor])
    if scene.nijigp_working_plane == 'X-Y':
        return Vector([co[0] / scale_factor, -co[1] / scale_factor, depth])

def set_vec2(point, co, scale_factor = 1.0):
    """Set 2D coordinates to a GP point"""
    scene = bpy.context.scene
    if scene.nijigp_working_plane == 'X-Z':    
        point.co.x = co[0] / scale_factor
        point.co.z = -co[1] / scale_factor
    if scene.nijigp_working_plane == 'Y-Z':    
        point.co.y = co[0] / scale_factor
        point.co.z = -co[1] / scale_factor
    if scene.nijigp_working_plane == 'X-Y':    
        point.co.x = co[0] / scale_factor
        point.co.y = -co[1] / scale_factor

def vec3_to_depth(co):
    """Get depth value from 3D coordinates"""
    scene = bpy.context.scene
    if scene.nijigp_working_plane == 'X-Z':    
        return -co.y
    if scene.nijigp_working_plane == 'Y-Z':    
        return co.x
    if scene.nijigp_working_plane == 'X-Y':    
        return co.z

def set_depth(point, depth):
    """Set depth to a GP point"""
    scene = bpy.context.scene
    if hasattr(point, 'co'):
        target = point.co
    else:
        target = point
    if scene.nijigp_working_plane == 'X-Z':    
        target.y = -depth
    if scene.nijigp_working_plane == 'Y-Z':    
        target.x = depth
    if scene.nijigp_working_plane == 'X-Y':    
        target.z = depth

def get_depth_direction() -> Vector:
    """Return a vector pointing to the positive side of the depth dimension"""
    scene = bpy.context.scene
    if scene.nijigp_working_plane == 'X-Z':    
        return Vector((0,-1,0))
    if scene.nijigp_working_plane == 'Y-Z':    
        return Vector((1,0,0))
    if scene.nijigp_working_plane == 'X-Y':    
        return Vector((0,0,1))

def get_2d_squared_distance(co1, scale_factor1, co2, scale_factor2):
    """Euclidean distance that takes the scale factors into consideration"""
    delta = [co1[0]/scale_factor1 - co2[0]/scale_factor2, co1[1]/scale_factor1 - co2[1]/scale_factor2]
    return delta[0]*delta[0] + delta[1]*delta[1]

def get_stroke_length(stroke: bpy.types.GPencilStroke = None, co_list = None):
    """Calculate the total length of a stroke"""
    res = 0
    if stroke:
        for i,point in enumerate(stroke.points):
            point0 = stroke.points[i-1]
            if i==0 and not stroke.use_cyclic:
                continue
            res += (point.co - point0.co).length
    if co_list:
        for i,co in enumerate(co_list):
            co0 = co_list[i-1]
            if i>0:
                res += math.sqrt(get_2d_squared_distance(co,1,co0,1))
    return max(res,1e-9)

def is_poly_in_poly(poly1, poly2):
    """False if either at least one point is outside, or all points are on the boundary"""
    import pyclipper
    inner_count = 0
    for co in poly1:
        res = pyclipper.PointInPolygon(co, poly2)
        if res == 0:
            return False
        if res == 1:
            inner_count += 1
    return inner_count > 0

def get_an_inside_co(poly):
    """Return a coordinate that is inside an integer polygon as part of the triangle input"""
    import pyclipper
    delta = 64
    while delta > 1:
        for co in poly:
            for co_ in [(co[0]-delta, co[1]-delta), (co[0]-delta, co[1]+delta), 
                        (co[0]+delta, co[1]-delta), (co[0]+delta, co[1]+delta)]:
                if pyclipper.PointInPolygon(co_, poly):
                    return co_
        delta /= 2
    return None

def overlapping_bounding_box(s1, s2):
    scene = bpy.context.scene
    if scene.nijigp_working_plane == 'X-Z':
        if s1.bound_box_max[0] < s2.bound_box_min[0] or s1.bound_box_max[2] < s2.bound_box_min[2]:
            return False
        if s2.bound_box_max[0] < s1.bound_box_min[0] or s2.bound_box_max[2] < s1.bound_box_min[2]:
            return False
    if scene.nijigp_working_plane == 'Y-Z':
        if s1.bound_box_max[1] < s2.bound_box_min[1] or s1.bound_box_max[2] < s2.bound_box_min[2]:
            return False
        if s2.bound_box_max[1] < s1.bound_box_min[1] or s2.bound_box_max[2] < s1.bound_box_min[2]:
            return False
    if scene.nijigp_working_plane == 'X-Y':
        if s1.bound_box_max[0] < s2.bound_box_min[0] or s1.bound_box_max[1] < s2.bound_box_min[1]:
            return False
        if s2.bound_box_max[0] < s1.bound_box_min[0] or s2.bound_box_max[1] < s1.bound_box_min[1]:
            return False
    return True    

def overlapping_strokes(s1, s2):
    """
    Check if two strokes overlap with each other. Ignore the cases involving holes
    """
    
    # First, check if bounding boxes overlap
    if not overlapping_bounding_box(s1, s2):
        return False
    
    # Then check every pair of edge
    N1 = len(s1.points)
    N2 = len(s2.points)
    for i in range(N1):
        for j in range(N2):
            p1 = vec3_to_vec2(s1.points[i].co)
            p2 = vec3_to_vec2(s1.points[(i+1)%N1].co)
            p3 = vec3_to_vec2(s2.points[j].co)
            p4 = vec3_to_vec2(s2.points[(j+1)%N2].co)
            if geometry.intersect_line_line_2d(p1,p2,p3,p4):
                return True

    return False

def is_stroke_line(stroke, gp_obj):
    """
    Check if a stroke does not have fill material
    """
    mat_idx = stroke.material_index
    material = gp_obj.material_slots[mat_idx].material
    return not material.grease_pencil.show_fill

def is_stroke_locked(stroke, gp_obj):
    """
    Check if a stroke has the material that is being locked or invisible
    """
    mat_idx = stroke.material_index
    material = gp_obj.material_slots[mat_idx].material
    return material.grease_pencil.lock or material.grease_pencil.hide

def is_stroke_hole(stroke, gp_obj):
    """
    Check if a stroke has a material with fill holdout
    """
    mat_idx = stroke.material_index
    material = gp_obj.material_slots[mat_idx].material
    return material.grease_pencil.use_fill_holdout

def is_layer_locked(layer: bpy.types.GPencilLayer):
    """
    Check if a layer should be edited
    """
    return layer.lock or layer.hide

def stroke_to_poly(stroke_list, scale = False, correct_orientation = False, scale_factor=None):
    """
    Convert Blender strokes to a list of 2D coordinates compatible with Clipper.
    Scaling can be applied instead of Clipper's built-in method
    """
    poly_list = []
    w_bound = [math.inf, -math.inf]
    h_bound = [math.inf, -math.inf]

    for stroke in stroke_list:
        co_list = []
        for point in stroke.points:
            co_list.append(vec3_to_vec2(point.co))
            w_bound[0] = min(w_bound[0], co_list[-1][0])
            w_bound[1] = max(w_bound[1], co_list[-1][0])
            h_bound[0] = min(h_bound[0], co_list[-1][1])
            h_bound[1] = max(h_bound[1], co_list[-1][1])
        poly_list.append(co_list)

    if scale and not scale_factor:
        poly_W = w_bound[1] - w_bound[0]
        poly_H = h_bound[1] - h_bound[0]
        
        if math.isclose(poly_W, 0) and math.isclose(poly_H, 0):
            scale_factor = 1
        elif math.isclose(poly_W, 0):
            scale_factor = SCALE_CONSTANT / min(poly_H, SCALE_CONSTANT)
        elif math.isclose(poly_H, 0):
            scale_factor = SCALE_CONSTANT / min(poly_W, SCALE_CONSTANT)
        else:
            scale_factor = SCALE_CONSTANT / min(poly_W, poly_H, SCALE_CONSTANT)

    if scale_factor:
        for co_list in poly_list:
            for co in co_list:
                co[0] *= scale_factor
                co[1] *= scale_factor

    # Since Grease Pencil does not care whether the sequence of points is clockwise,
    # Clipper may regard some strokes as negative polygons, which needs a fix 
    if correct_orientation:
        import pyclipper
        for co_list in poly_list:
            if not pyclipper.Orientation(co_list):
                co_list.reverse()

    return poly_list, scale_factor

