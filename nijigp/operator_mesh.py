import bpy
import os
import math
import bmesh
from .utils import *

class MeshGenerationByOffsetting(bpy.types.Operator):
    """Replacing the selected strokes with new ones whose polygons are offset"""
    bl_idname = "nijigp.mesh_generation_offset"
    bl_label = "Convert to Meshes by Offsetting"
    bl_category = 'View'
    bl_options = {'REGISTER', 'UNDO'}

    # Define properties
    offset_amount: bpy.props.FloatProperty(
            name='Offset',
            default=0.1, soft_min=0, unit='LENGTH',
            description='Offset length'
    )
    resolution: bpy.props.IntProperty(
            name='Resolution',
            default=4, min=2, max=256,
            description='Number of offsets calculated'
    )
    corner_shape: bpy.props.EnumProperty(
            name='Corner Shape',
            items=[('JT_ROUND', 'Round', ''),
                    ('JT_SQUARE', 'Square', ''),
                    ('JT_MITER', 'Miter', '')],
            default='JT_ROUND',
            description='Shape of corners generated by offsetting'
    )
    slope_style: bpy.props.EnumProperty(
            name='Corner Shape',
            items=[('LINEAR', 'Linear', ''),
                    ('SPHERE', 'Sphere', ''),
                    ('STEP', 'Step', '')],
            default='SPHERE',
            description='Slope shape of the generated mesh'
    )
    keep_original: bpy.props.BoolProperty(
            name='Keep Original',
            default=True,
            description='Do not delete the original stroke'
    )
    smooth_level: bpy.props.IntProperty(
            name='Smooth Level',
            default=0, min=0, max=16,
            description='Add a Smooth modifier if not zero'
    )
    remesh: bpy.props.BoolProperty(
            name='Smooth Level',
            default=False,
            description='Add a Remesh modifier'
    )
    shade_smooth: bpy.props.BoolProperty(
            name='Shade Smooth',
            default=False,
            description='Enable face smooth shading and auto smooth normals'
    )


    def draw(self, context):
        layout = self.layout
        layout.label(text = "Geometry Options:")
        box1 = layout.box()
        box1.prop(self, "offset_amount", text = "Offset Amount")
        box1.prop(self, "resolution", text = "Resolution")
        box1.label(text = "Corner Shape")
        box1.prop(self, "corner_shape", text = "")
        box1.label(text = "Slope Style")
        box1.prop(self, "slope_style", text = "")
        box1.prop(self, "keep_original", text = "Keep Original")

        layout.label(text = "Post-Processing Options:")
        box2 = layout.box()
        box2.prop(self, "smooth_level", text = "Smooth Modifier")
        box2.prop(self, "remesh", text = "Remesh Modifier")
        box2.prop(self, "shade_smooth", text = "Shade Smooth")

    def execute(self, context):

        # Import and configure Clipper
        try:
            import pyclipper
        except ImportError:
            self.report({"ERROR"}, "Please install dependencies in the Preferences panel.")
        clipper = pyclipper.PyclipperOffset()
        clipper.MiterLimit = math.inf
        jt = pyclipper.JT_ROUND
        if self.corner_shape == "JT_SQUARE":
            jt = pyclipper.JT_SQUARE
        elif self.corner_shape == "JT_MITER":
            jt = pyclipper.JT_MITER
        et = pyclipper.ET_CLOSEDPOLYGON

        # Convert selected strokes to 2D polygon point lists
        current_gp_obj = context.object
        stroke_info = []
        stroke_list = []
        mesh_names = []
        for i,layer in enumerate(current_gp_obj.data.layers):
            if not layer.lock:
                for j,stroke in enumerate(layer.active_frame.strokes):
                    if stroke.select:
                        stroke_info.append([stroke, i, j])
                        stroke_list.append(stroke)
                        mesh_names.append('Offset_' + layer.info + '_' + str(j))
        poly_list, scale_factor = stroke_to_poly(stroke_list, scale = True)

        def process_single_stroke(i, co_list):
            '''
            Function that processes each stroke separately
            '''
            # Calculate offsets
            clipper.Clear()
            clipper.AddPath(co_list, jt, et)
            contours = []
            vert_idx_list = []
            vert_counter = 0
            offset_interval = self.offset_amount / self.resolution * scale_factor
            for j in range(self.resolution):
                new_contour = clipper.Execute( -offset_interval * j)
                # STEP style requires duplicating each contour
                for _ in range(1 + int(self.slope_style=='STEP')):
                    contours.append( new_contour )
                    new_idx_list = []
                    for poly in new_contour:
                        num_vert = len(poly)
                        new_idx_list.append( (vert_counter, vert_counter + num_vert) )
                        vert_counter += num_vert
                    vert_idx_list.append(new_idx_list)

            # Mesh generation
            new_mesh = bpy.data.meshes.new(mesh_names[i])
            bm = bmesh.new()
            edges_by_level = []
            verts_by_level = []
            
            for j,contour in enumerate(contours):
                edges_by_level.append([])
                verts_by_level.append([])
                edge_extruded = []

                # One contour may contain more than one closed loops
                for k,poly in enumerate(contour):
                    height = abs(j * offset_interval/scale_factor)
                    if self.slope_style == 'SPHERE':
                        sphere_rad = abs(self.offset_amount)
                        height = math.sqrt(sphere_rad ** 2 - (sphere_rad - height) ** 2)
                    elif self.slope_style == 'STEP':
                        height = abs( (j+1)//2 * offset_interval/scale_factor)

                        
                    for co in poly:
                        verts_by_level[-1].append(
                            bm.verts.new([co[0]/scale_factor, -height, -co[1]/scale_factor])
                            )
                    bm.verts.ensure_lookup_table()

                    # Connect same-level vertices
                    for v_idx in range(vert_idx_list[j][k][0],vert_idx_list[j][k][1] - 1):
                        edges_by_level[-1].append( bm.edges.new([bm.verts[v_idx],bm.verts[v_idx + 1]]) )
                    edges_by_level[-1].append( 
                            bm.edges.new([ bm.verts[vert_idx_list[j][k][0]], bm.verts[vert_idx_list[j][k][1] - 1] ]) 
                            )

                # STEP style only: connect extruding edges
                if self.slope_style=='STEP' and j%2 > 0:
                    for v_idx,_ in enumerate(verts_by_level[-1]):
                        edge_extruded.append(
                                bm.edges.new([verts_by_level[-1][v_idx], verts_by_level[-2][v_idx]])
                            )

                bm.edges.ensure_lookup_table()
                if j>0:
                    if self.slope_style=='STEP' and j%2==1:
                        bmesh.ops.edgenet_fill(bm, edges= edges_by_level[-1]+edges_by_level[-2]+edge_extruded)
                    else:
                        bmesh.ops.triangle_fill(bm, use_beauty=True, edges= edges_by_level[-1]+edges_by_level[-2])
            bmesh.ops.triangle_fill(bm, use_beauty=True, edges= edges_by_level[-1])
            bm.faces.ensure_lookup_table()
            
            # Cleanup
            to_remove = []
            for face in bm.faces:
                if len(face.verts) > 4:
                    to_remove.append(face)
            for face in to_remove:
                bm.faces.remove(face)


            if self.shade_smooth:
                for f in bm.faces:
                    f.smooth = True

            bm.to_mesh(new_mesh)
            bm.free()

            # Object generation
            new_object = bpy.data.objects.new(mesh_names[i], new_mesh)
            bpy.context.collection.objects.link(new_object)
            new_object.parent = current_gp_obj

            # Post-processing: Add modifiers
            new_object.modifiers.new(name="nijigp_Mirror", type='MIRROR')
            new_object.modifiers["nijigp_Mirror"].use_axis[0] = False
            new_object.modifiers["nijigp_Mirror"].use_axis[1] = True
            if self.smooth_level > 0:
                new_object.modifiers.new(name="nijigp_Smooth", type='SMOOTH')
                new_object.modifiers["nijigp_Smooth"].iterations = self.smooth_level
            if self.remesh:
                new_object.modifiers.new(name="nijigp_Remesh", type='REMESH')
                new_object.modifiers["nijigp_Remesh"].voxel_size = max(0.02, abs(self.offset_amount / self.resolution))
                new_object.modifiers["nijigp_Remesh"].use_smooth_shade = self.shade_smooth
            new_object.data.use_auto_smooth = self.shade_smooth

        for i,co_list in enumerate(poly_list):
            process_single_stroke(i, co_list)

        # Delete old strokes
        if not self.keep_original:
            for info in stroke_info:
                layer_index = info[1]
                current_gp_obj.data.layers[layer_index].active_frame.strokes.remove(info[0])

        return {'FINISHED'}

