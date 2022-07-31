import bpy
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "nijiGPen",
    "author" : "https://github.com/chsh2/nijiGPen",
    "description" : "Tools modifying Grease Pencil strokes in the 2D (XZ) plane",
    "blender" : (3, 00, 0),
    "version" : (0, 1, 0),
    "location" : "View3D > Sidebar > NijiGP, in Draw and Edit mode of Grease Pencil objects",
    "warning" : "This addon is still in an early stage of development",
    "category" : "Object"
}

from . import auto_load

auto_load.init()

def draw_shortcuts(self, context):
    if not context.preferences.addons[__package__].preferences.extra_buttons:
        return
    if context.mode == 'PAINT_GPENCIL' or context.mode == 'SCULPT_GPENCIL':
        self.layout.operator("ed.undo", text='', icon='TRIA_LEFT')
        self.layout.operator("ed.redo", text='', icon='TRIA_RIGHT')


def register():
    auto_load.register()
    bpy.types.Scene.nijigp_fast_polygon_point_match = bpy.props.BoolProperty(
                        default=False, 
                        description="Faster polygon operations, which however may lead to imprecise point properties"
                        )
    bpy.types.Scene.nijigp_fast_error_tolerance = bpy.props.FloatProperty(
                        default=0.05, min=0, unit='LENGTH',
                        description="Maximum error that can be tolerated for point properties of strokes generated in the fast mode"
                        )
    bpy.types.Scene.nijigp_draw_bool_material_constraint = bpy.props.BoolProperty(
                        default=False, 
                        description="Boolean operations in Draw mode only apply to strokes with the same material"
                        )
    bpy.types.Scene.nijigp_draw_bool_fill_constraint = bpy.props.BoolProperty(
                        default=True, 
                        description="Boolean operations in Draw mode only apply to strokes showing fills"
                        )
    bpy.types.PROPERTIES_PT_navigation_bar.prepend(draw_shortcuts)

def unregister():
    auto_load.unregister()
    bpy.types.PROPERTIES_PT_navigation_bar.remove(draw_shortcuts)
