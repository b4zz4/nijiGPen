import bpy
from ..utils import *

def save_stroke_selection(gp_obj):
    """
    Record the selection state of a Grease Pencil object to a map
    """
    select_map = {}
    for layer in gp_obj.data.layers:
        select_map[layer] = {}
        for frame in layer.frames:
            select_map[layer][frame] = {}
            for stroke in frame.strokes:
                select_map[layer][frame][stroke] = stroke.select_index
    return select_map

def load_stroke_selection(gp_obj, select_map):
    """
    Apply selection to strokes according to a map saved by save_stroke_selection()
    """
    for layer in gp_obj.data.layers:
        for frame in layer.frames:
            for stroke in frame.strokes:
                if stroke in select_map[layer][frame]:
                    stroke.select = (select_map[layer][frame][stroke] > 0)
                else:
                    stroke.select = False

def get_input_frames(gp_obj, multiframe=False, return_range=False):
    """
    Get either active frames or all selected frames depending on the edit mode
    """
    frames_to_process = []
    time_ranges = []
    if multiframe:
        # Process every selected frame
        for i,layer in enumerate(gp_obj.data.layers):
            if not is_layer_locked(layer):
                for j,frame in enumerate(layer.frames):
                    if frame.select:
                        frames_to_process.append(frame)
                        # Get start and end frame numbers
                        if j != len(layer.frames)-1:
                            time_ranges.append( (frame.frame_number, layer.frames[j+1].frame_number))
                        else:
                            time_ranges.append( (frame.frame_number, bpy.context.scene.frame_end))
    else:
        # Process only the active frame of each layer
        for i,layer in enumerate(gp_obj.data.layers):
            if layer.active_frame and not is_layer_locked(layer):
                frames_to_process.append(layer.active_frame)
    if return_range:
        return frames_to_process, time_ranges
    else:
        return frames_to_process
                
def get_input_strokes(gp_obj, frame: bpy.types.GPencilFrame, select_all = False):
    """
    Check each stroke in a frame if it belongs to the input
    """
    res = []
    if hasattr(frame, 'strokes'):
        for stroke in frame.strokes:
            if not is_stroke_locked(stroke, gp_obj) and (select_all or stroke.select):
                res.append(stroke)
    return res

def refresh_strokes(gp_obj, frame_numbers):
    """
    When generating new strokes via scripting, sometimes the strokes do not have correct bound boxes and are not displayed correctly.
    This function performs a zero-value translation to all strokes to force refreshing the data
    """
    current_mode = bpy.context.mode
    current_frame = bpy.context.scene.frame_current
    select_map = save_stroke_selection(gp_obj)

    bpy.ops.object.mode_set(mode='EDIT_GPENCIL')
    for f in frame_numbers:
        bpy.context.scene.frame_current = f
        bpy.ops.gpencil.select_all(action='SELECT')
        bpy.ops.transform.translate()
    
    load_stroke_selection(gp_obj, select_map)
    bpy.ops.object.mode_set(mode=current_mode)
    bpy.context.scene.frame_current = current_frame

def copy_stroke_attributes(dst: bpy.types.GPencilStroke, srcs,
                           copy_hardness = False,
                           copy_linewidth = False,
                           copy_cap = False,
                           copy_cyclic = False,
                           copy_uv = False,
                           copy_material = False,
                           copy_color = False):
    """
    Set the attributes of a stroke by copying from other stroke(s)
    """
    # Single values
    src = srcs[0]
    if copy_cap:
        dst.start_cap_mode = src.start_cap_mode
        dst.end_cap_mode = src.end_cap_mode
    if copy_cyclic:
        dst.use_cyclic = src.use_cyclic
    if copy_material:
        dst.material_index = src.material_index
        
    # Average values
    color_fill = [.0,.0,.0,.0]
    uv_translation = [.0,.0]
    uv_scale, uv_rotation = .0, .0
    linewidth = 0
    hardness = 0.0
    for src in srcs:
        if copy_hardness:
            hardness += src.hardness
        if copy_linewidth:
            linewidth += src.line_width
        if copy_uv:
            uv_scale += src.uv_scale
            uv_rotation += src.uv_rotation
            uv_translation[0] += src.uv_translation[0]
            uv_translation[1] += src.uv_translation[1]
        if copy_color:
            for i in range(4):
                color_fill[i] += src.vertex_color_fill[i]
    n = len(srcs)
    if copy_hardness:
        dst.hardness = hardness / n
    if copy_linewidth:
        dst.line_width = int(linewidth // n)
    if copy_uv:
        dst.uv_rotation, dst.uv_scale = uv_rotation / n, uv_scale / n
        dst.uv_translation[0],  dst.uv_translation[1] = uv_translation[0] / n, uv_translation[1] / n
    if copy_color:
        for i in range(4):
            dst.vertex_color_fill[i] = color_fill[i] / n
    