import base64
import math
import struct
import json
from pathlib import Path

import numpy as np

from .common import text2png, create_surface, line_segments, create_line, flip_yz
from . import common

GLTF_ELEMENT_ARRAY_BUFFER = 34963
GLTF_ARRAY_BUFFER = 34962
GLTF_TYPE_UNSIGNED_SHORT = 5123
GLTF_TYPE_UNSIGNED_INT = 5125
GLTF_TYPE_FLOAT = 5126
GLTF_WRAP_MIRRORED_REPEAT = 33648
GLTF_MINFILTER_LINEAR_MIPMAP_LINEAR = 9987
GLTF_MAGFILTER_LINEAR = 9729

# For more documentation look e.g. at:
# https://github.com/KhronosGroup/glTF/blob/master/specification/2.0/figures/gltfOverview-2.0.0b.png
class GLTF(object):
    def __init__(self):
        self.d = {
            "asset": {"version" : "2.0"},
            "scene": 0,
        }
        for i in ['scenes', 'nodes', 'meshes', 'buffers', 'bufferViews', 'accessors', 'materials', 'textures', 'samplers', 'images', ]:
            self.d[i] = []
        self._buffer_dict = {}
        self._buffer = b''
        self.add('buffers', self._buffer_dict)
    def add(self, path, x):
        lst = self.d.get(path)
        id = len(lst)
        lst.append(x)
        return id

    def add_buffer_data(self, arrays, target, type, remove_view_target=False, use_main_buffer=True):
        # GLTF spec says little-endian
        buffer_format = "<"
        acc_id = []
        buffer_dict = {}
        if use_main_buffer:
            byte_offset = len(self._buffer)
            b_id = 0
        else:
            byte_offset = 0
            b_id = self.add('buffers', buffer_dict)
        for x, tg, tp in zip(arrays, target, type):
            if tg == GLTF_ELEMENT_ARRAY_BUFFER:
                if max(x) < 2**16:
                    bin_format = GLTF_TYPE_UNSIGNED_SHORT
                    arr_format = "H"
                else:
                    bin_format = GLTF_TYPE_UNSIGNED_INT
                    arr_format = "I"
            else:
                bin_format = GLTF_TYPE_FLOAT
                arr_format = "f"
            arr_format = f"{len(x)}{arr_format}"
            buffer_format += arr_format
            n = struct.calcsize(arr_format)
            view_id = self.add('bufferViews', {
                    "buffer": b_id,
                    "byteOffset": byte_offset,
                    "byteLength": n,
                    "target": tg
                })
            if remove_view_target:
                del self.d['bufferViews'][view_id]['target']
            byte_offset += n
            if tp == 'SCALAR':
                dim = 1
                component_type = bin_format
            else:
                dim = int(tp[-1])
                component_type = GLTF_TYPE_FLOAT
            arr = np.array(x).reshape((-1,dim))
            acc_id.append(self.add("accessors", {
                "bufferView": view_id,
                "byteOffset": 0,
                "componentType": component_type,
                "count": len(x) // dim,
                "type": tp,
                "max": arr.max(0).tolist(),
                "min": arr.min(0).tolist(),
            }))
        buffer = struct.pack(buffer_format, *sum(arrays, []))
        if use_main_buffer:
            self._buffer += buffer
            self._buffer_dict["byteLength"] = len(self._buffer)
        else:
            buffer_url = "data:application/octet-stream;base64," + base64.b64encode(buffer).decode("ASCII")
            buffer_dict["uri"] = buffer_url
            buffer_dict["byteLength"] = len(buffer)

        return acc_id
    
    def format_gltf(self):
        buffer_url = "data:application/octet-stream;base64," + base64.b64encode(self._buffer).decode("ASCII")
        self._buffer_dict["uri"] = buffer_url
        return self.d
    def format_glb(self):
        if "uri" in self._buffer_dict:
            del self._buffer_dict["uri"]
        for img in self.d.get("images",[]):
            img_data = base64.b64decode(img['uri'][len("data:image/png;base64,"):].encode("ASCII"))
            view_id = self.add('bufferViews', {
                "buffer": 0,
                "byteOffset": len(self._buffer),
                "byteLength": len(img_data),
            })
            self._buffer += img_data
            self._buffer_dict["byteLength"] = len(self._buffer)
            del img['uri']
            img["bufferView"] = view_id
            img["mimeType"] = "image/png"

        json_string = json.dumps(self.d).encode("ASCII")
        # pad to 4 bytes alignment according to specification
        json_string += b"\x20" * (-len(json_string)%4)
        self._buffer += b"\x00" * (-len(self._buffer)%4)
        # 0x4E4F534A = b'JSON'
        # 0x004E4942 = b'BIN\x00'
        chunks = \
            struct.pack('II', len(json_string), 0x4E4F534A) + json_string + \
            struct.pack('II', len(self._buffer), 0x004E4942) + self._buffer
        # 0x46546C67 = b'glTF'
        header = struct.pack('III', 0x46546C67, 2, len(chunks) + 12)
        return header + chunks
    
    def load_font(self, f, board_acc_id):
        font = common.BitmapFont(f)
        fc = font.common

        img_uri = "data:image/png;base64," + base64.b64encode(font.png()).decode("ASCII")
        src_id = self.add("images", {
            "uri": img_uri
        })
        texture_id = self.add("textures", {
            "sampler": self.add('samplers', {
                "magFilter": GLTF_MAGFILTER_LINEAR,
                "minFilter": GLTF_MINFILTER_LINEAR_MIPMAP_LINEAR,
                "wrapS": GLTF_WRAP_MIRRORED_REPEAT,
                "wrapT": GLTF_WRAP_MIRRORED_REPEAT
            }),
            "source": src_id
        })
        self.d.update({
            "extensionsUsed": [
                "KHR_texture_transform"
            ],
            "extensionsRequired": [
                "KHR_texture_transform"
            ],
        })
        glyph_mesh_id = {}
        def get_glyph_mesh_id(ch):
            if ch in glyph_mesh_id:
                return glyph_mesh_id[ch]
            glyph = font.chars.get(ch)
            mat_id = self.add('materials', {
                "name": f"Material for char '{ch}'",
                "alphaMode": "MASK",
                "alphaCutoff": 0.5,
                "doubleSided": True,
                "pbrMetallicRoughness" : {
                    "baseColorTexture" : {
                            "index" : texture_id,
                            "extensions": {
                            "KHR_texture_transform": {
                                "offset": [glyph['x'] / fc['scaleW'], glyph['y'] / fc['scaleH']],
                                # "rotation": 0,
                                "scale": [glyph['width'] / fc['scaleW'], glyph['height'] / fc['scaleW']]
                            }
                        }
                    },
                    "baseColorFactor": [1.0,1.0,1.0, 1.0],
                    "metallicFactor" : 0.0,
                    "roughnessFactor" : 0.0,
                }
            })
            glyph_mesh_id[ch] = self.add('meshes', {
                "name": f"Mesh for char '{ch}'",
                "primitives": [{
                    "attributes": {
                        "POSITION": board_acc_id[1],
                        "NORMAL": board_acc_id[2],
                        "TEXCOORD_0": board_acc_id[3],
                    },
                    "indices": board_acc_id[0],
                    "material": mat_id
                }]
            })
            return glyph_mesh_id[ch]
        def drawText(text, valign=0.25, halign='left'):
            layout = font.layoutText(text)
            x_offset = 0.0
            if halign == 'center':
                text_width = layout[-1]['left']+layout[-1]['width']
                x_offset = - text_width / 2
            glyphs = []
            for glyph in layout:
                ch = chr(glyph['id'])
                glyphs.append(self.add('nodes', {
                "name" : f"glyph_{ch}",
                "mesh" : get_glyph_mesh_id(ch),
                "translation": [
                    (x_offset+glyph['left'] + glyph['xoffset']) / font.common['lineHeight'] ,#/ fc['scaleW'],
                    (font.common['base'] * (1-valign) - glyph['yoffset'] - glyph['height']) / font.common['lineHeight'] ,#/ fc['scaleH'],
                    0.0],
                "scale": [
                    glyph['width'] / font.common['lineHeight'],
                    glyph['height'] / font.common['lineHeight'],
                    1.0
                ],
                }))
            return glyphs
            return self.add('nodes', {
                "name" : f"text_{text}",
                "children" : glyphs,
                # "translation": [glyph['xoffset'] / fc['scaleW'], glyph['yoffset'] / fc['scaleH'], 0.0],
                # "scale": scale,
                })
        return drawText

def data2gltf(data, subdiv=16):

    COLORS = data['color_palette'] if "color_palette" in data else common.COLORS
    COLORS_LEN = len(COLORS)
    meters_per_unit = float(data.get('meters_per_unit', 0.1))
    add_glow = bool(data.get('add_glow', False))

    gltf = GLTF()
    indices, vertices, normals = create_sphere(subdiv=subdiv)
    sphere_acc_id = gltf.add_buffer_data(
        [indices, vertices, normals],
        [GLTF_ELEMENT_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER],
        "SCALAR VEC3 VEC3".split(),
    )
    arrow_radius = 0.01
    indices, vertices, normals = create_rotation(
        [(0,arrow_radius),(1-2*arrow_radius,arrow_radius),(1-2*arrow_radius,2*arrow_radius)], subdiv=subdiv)
    arrow_acc_id = gltf.add_buffer_data(
        [indices, vertices, normals],
        [GLTF_ELEMENT_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER],
        "SCALAR VEC3 VEC3".split(),
    )
    grey_mat_id = gltf.add("materials", {
        "name" : f"grey",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.5,0.5,0.5,1.0],
            "metallicFactor": 0.1,
            "roughnessFactor": 0.4,
        },
        "doubleSided": True,
    })
    arrow_mesh_id = gltf.add("meshes", {
                "name" : f"arrow",
                "primitives": [{
                    "attributes": {
                        "POSITION": arrow_acc_id[1],
                        "NORMAL": arrow_acc_id[2],
                    },
                    "indices": arrow_acc_id[0],
                    "material": grey_mat_id
                }]
            })

    indices, vertices, normals, st = create_board()
    board_acc_id = gltf.add_buffer_data(
        [indices, vertices, normals, st],
        [GLTF_ELEMENT_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER],
        "SCALAR VEC3 VEC3 VEC2".split(),
    )
    # sampler_id = gltf.add('samplers', {
    #         "magFilter": GLTF_MAGFILTER_LINEAR,
    #         "minFilter": GLTF_MINFILTER_LINEAR_MIPMAP_LINEAR,
    #         "wrapS": GLTF_WRAP_MIRRORED_REPEAT,
    #         "wrapT": GLTF_WRAP_MIRRORED_REPEAT
    #     })

    material_quality = dict(opacity=1, roughness=0.1, metallic=0.5)
    if "material_quality" in data:
        for _ in ['opacity', 'roughness', 'metallic']:
            if _ in data['material_quality']:
                material_quality[_] = data['material_quality'][_]
    
    col_mat_ids = [ gltf.add("materials", {
                "name": f"Material for color {col}",
                "pbrMetallicRoughness": {
                    "baseColorFactor": list(col) + [1.0],
                    "metallicFactor": material_quality['metallic'],
                    "roughnessFactor": material_quality['roughness'],
                },
                # let's add some wow factor by default:
                "emissiveFactor": [_*0.3 for _ in col]
            })
            for col in COLORS
        ]
    if material_quality.get('opacity',1)<1:
        # gltf.d["extensionsUsed"] = ["KHR_materials_transmission"]
        ## following prohibits import in blender 2.93
        # gltf.d["extensionsRequired"] = ["KHR_materials_transmission"]

        for _ in gltf.d['materials']:
            # _["extensions"] = {
            #     "KHR_materials_transmission" : {
            #         "transmissionFactor" : 1-material_quality['opacity']
            #     }
            # }
            _['alphaMode'] = "BLEND"
            _["pbrMetallicRoughness"]["baseColorFactor"][3] = material_quality['opacity']

    col_mesh_id = [ gltf.add("meshes", {
            "name": f"Mesh for material {mat_id}",
            "primitives": [{
                "attributes": {
                    "POSITION": sphere_acc_id[1],
                    "NORMAL": sphere_acc_id[2],
                },
                "indices": sphere_acc_id[0],
                "material": mat_id
            }]
        })
        for mat_id in col_mat_ids
    ]
    if add_glow:
        halo_transparency = 0.3
        glow_col_mat_ids = [ gltf.add("materials", {
                    "name": f"Material for glow for col {col}",
                    "pbrMetallicRoughness": {
                        "baseColorFactor": list(col) + [halo_transparency],
                        "metallicFactor": 0.5,
                        "roughnessFactor": 0.1
                    },
                    # "emissiveFactor": list(col) + [1.0],
                })
                for col in COLORS
            ]
        glow_col_mesh_id = [ gltf.add("meshes", {
                    "name": f"Mesh for glow for mat_id {mat_id}",
                    "primitives": [{
                        "attributes": {
                            "POSITION": sphere_acc_id[1],
                            "NORMAL": sphere_acc_id[2],
                        },
                        "indices": sphere_acc_id[0],
                        "material": mat_id
                    }]
                })
                for mat_id in glow_col_mat_ids
            ]

    data_node = dict(children=[], name="Data")
    data_node_id = gltf.add('nodes', data_node)
    if 'col_labels' in data:
        legend_node = dict(children=[], name="Legend", translation=[1,0,-1])
        legend_node_id = gltf.add('nodes', legend_node)
    else:
        legend_node_id = None
    if 'axis_names' in data:
        axes_node = dict(children=[], name="Axes")
        axes_node_id = gltf.add('nodes', axes_node)
    else:
        axes_node_id = None
    drawText = gltf.load_font(Path(__file__).parent / 'font/DejaVu-sdf.fnt', board_acc_id)
    animation = False
    if 'animation' in data:
        animation = data['animation']
        end_time_code = len(animation.get('time_labels')) - 1
        start_time_code = 0
        time_codes_per_second = animation.get('time_codes_per_second', 24)
        animation_input = np.arange(end_time_code+1) / time_codes_per_second
        animation_inputs = [ [_/time_codes_per_second for _ in t] for t in animation.get('time_values',[])]
        max_animation_input = max(max(_) for _ in animation_inputs)
        animation_outputs = [
            flip_yz(np.array(_)).reshape((-1, )).tolist()
            for _ in animation.get('data',[])
        ]
        animation_input_acc_id, *animation_output_acc_ids = gltf.add_buffer_data(
            [animation_input.tolist()] + animation_outputs,
            [GLTF_ARRAY_BUFFER] + [GLTF_ARRAY_BUFFER] * len(animation_outputs),
            ["SCALAR"] + ["VEC3"] * len(animation_outputs),
            remove_view_target=True,
        )
        animation_inputs_acc_ids = gltf.add_buffer_data(
            animation_inputs,
            [GLTF_ARRAY_BUFFER] * len(animation_inputs),
            ["SCALAR"] * len(animation_inputs),
            remove_view_target=True,
        )
        animation_channels = []
        animation_samplers = []
        gltf.d["animations"] = [ dict(channels=animation_channels, samplers=animation_samplers) ]

    for i, row in enumerate(data.get('data', []) if data.get('type') != 'l' else []):
        x, y, z = row[:3]
        col = 0
        scale = 0.01
        if 'col' in data:
            col = data['col'][i] % COLORS_LEN
        if 'size' in data:
            scale *= data['size'][i]
        scale = [scale] * 3
        mesh_id = col_mesh_id[col]
        current_node = {
            "name": f"Data Point {i}",
            "mesh": mesh_id,
            "translation": [x, z, -y],
            "scale": scale,
        }
        current_node_id = gltf.add('nodes', current_node)
        if 'label' in data:
            text = data['label'][i]
            char_node_ids = drawText(text)

            current_node['children'] = [gltf.add('nodes', {
                "name" : f"text_{text}",
                "children": char_node_ids,
                "translation": [1.5,0,0],
                "scale": [ _*100 for _ in scale],
            }), ]
        data_node['children'].append(current_node_id)
        if add_glow:
            _ = gltf.add('nodes', {"name": f"Data Point {i} glow" ,
                "mesh": glow_col_mesh_id[col], "translation": [x, z, -y],
                "scale": [ _*1.3 for _ in scale],
            })
            data_node['children'].append(_)

        if animation:
            if len(animation_inputs_acc_ids):
                animation_input_acc_id = animation_inputs_acc_ids[i]
            animation_samplers.append(dict(
                input=animation_input_acc_id,
                interpolation="LINEAR",
                output=animation_output_acc_ids[i],
            ))
            animation_channels.append(dict(
                target=dict(node=current_node_id, path='translation'),
                sampler=len(animation_samplers)-1,
            ))
            time_values = animation['time_values'][i]
            a,b = min(time_values), max(time_values)
            if a > 0 or b < max_animation_input:
                t=[]
                scales = []
                if a>0:
                    t += [0,a/time_codes_per_second]
                    scales += [ 0,0,0 ] + scale
                else:
                    t += [0]
                    scales += scale
                if b < max_animation_input:
                    t += [b/time_codes_per_second]
                    scales += [ 0,0,0 ]
                sum([
                    scale if a >0 else [0,0,0],
                    scale,
                    scale if b==max_animation_input else [0,0,0],
                ], [])
                animation_scale_input, animation_scale_output = gltf.add_buffer_data(
                    [t] + [scales],
                    [GLTF_ARRAY_BUFFER,GLTF_ARRAY_BUFFER],
                    ["SCALAR"] + ["VEC3"],
                    remove_view_target=True,
                )
                animation_samplers.append(dict(
                    input=animation_scale_input,
                    interpolation="STEP",
                    output=animation_scale_output,
                ))
                animation_channels.append(dict(
                    target=dict(node=current_node_id, path='scale'),
                    sampler=len(animation_samplers)-1,
                ))

    if 'surface' in data:
        surface = data['surface']
        indices, normals, vertices, uv = create_surface(surface)
        surface_acc_id = gltf.add_buffer_data(
            [ _.flatten().tolist() for _ in [indices, vertices, normals, uv] ],
            [GLTF_ELEMENT_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER],
            "SCALAR VEC3 VEC3 VEC2".split(),
        )
        surface_mat_id = grey_mat_id
        if 'surfacecolor' in surface:
            import PIL, io
            img = PIL.Image.fromarray(np.uint8(surface['surfacecolor']))
            buffer = io.BytesIO()
            img.save(buffer, format='png', compress_level=0)
            img_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ASCII")
            src_id = gltf.add("images", {
                "uri": img_uri
            })
            sampler_id = gltf.add('samplers', {
                "magFilter": GLTF_MAGFILTER_LINEAR,
                "minFilter": GLTF_MINFILTER_LINEAR_MIPMAP_LINEAR,
                "wrapS": GLTF_WRAP_MIRRORED_REPEAT,
                "wrapT": GLTF_WRAP_MIRRORED_REPEAT
            })
            texture_id = gltf.add("textures", {
                "sampler": sampler_id,
                "source": src_id
            })
            surface_mat_id = gltf.add('materials', {
                    "name": f"Material {texture_id} for surface color",
                    "pbrMetallicRoughness": {
                        "baseColorTexture": {"index": texture_id},
                        "metallicFactor": 0.1,
                        "roughnessFactor": 0.8,
                        "emissiveFactor": [0.3,0.3,0.3],
                    },
                    "alphaMode": "BLEND",
                    "doubleSided": True,
                })
        mesh_id = gltf.add('meshes',
            {
                "name": f"Mesh for surface",
                "primitives": [{
                    "attributes": {
                        "POSITION": surface_acc_id[1],
                        "NORMAL": surface_acc_id[2],
                        "TEXCOORD_0": surface_acc_id[3],
                    },
                    "indices": surface_acc_id[0],
                    "material": surface_mat_id
                }]
            })
        data_node['children'].append(gltf.add('nodes', {
          "mesh" : mesh_id,
          # "translation": [x,z,-y],
          # "scale": scale,
        }))

    if 'lines' in data and 'data' in data:
        for i, line in enumerate(data['lines']):
            data_list = data.get('data', [])
            line_width = line.get('width', 1) / 500
            indices, vertices, normals = create_line(data_list, line, radius=line_width)
            line_acc_id = gltf.add_buffer_data(
                [indices, vertices, normals],
                [GLTF_ELEMENT_ARRAY_BUFFER, GLTF_ARRAY_BUFFER, GLTF_ARRAY_BUFFER],
                "SCALAR VEC3 VEC3".split(),
            )
            mat_id = col_mat_ids[ line.get('col', 0) % COLORS_LEN ]
            # n = len(data_list)
            mesh_id = gltf.add('meshes',
                {
                    "primitives": [{
                        "attributes": {
                            "POSITION": line_acc_id[1],
                            "NORMAL": line_acc_id[2],
                        },
                        "indices": line_acc_id[0],
                        "material": mat_id
                    }]
                })
            # for t,q,s in line_segments(data_list, line, n, flip_vector=True):
            #     data_node['children'].append(gltf.add('nodes', {
            #         "mesh": mesh_id,
            #         "translation": t,
            #         "scale": [1,s,1],
            #         "rotation": q,
            #     }))
            data_node['children'].append(gltf.add('nodes', {
                "mesh": mesh_id,
            }))

    for i, text in enumerate(data.get('col_labels',[])):
        col = i % COLORS_LEN
        scale = [0.01] * 3
        x, y, z = 0,0,1-i*scale[1]*10
        char_node_ids = drawText(text)
        legend_node['children'].append(gltf.add('nodes', {
          "name" : f"text_{text}",
        #   "mesh" : mesh_id,
          "children": char_node_ids,
          "translation": [x,z,-y],
          "scale": [0.08] * 3,
        }))
        # the sphere
        legend_node['children'].append(gltf.add('nodes', {
          "name" : f"sphere_{text}",
          "mesh" : col_mesh_id[col],
          "translation": [x-0.04,z+scale[1]/2,-y],
          "scale": [0.02] * 3,
        }))
    for i, text in enumerate(data.get('axis_names',[])):
        scale = [0.01] * 3
        translation = [0,0,0]
        translation[(2*i) % 3] = -1 if i==1 else 1
        rotation = [0,0,0,0]
        if i<2:
            rotation[0] = math.sqrt(2)/2 * (1-2*i)
            rotation[1 if i==0 else 3] = math.sqrt(2)/2
        else:
            rotation[1] = -1
        # h, w, img = text2png(text, color=COLORS[0])
        # img_uri = "data:image/png;base64," + base64.b64encode(img).decode("ASCII")
        # src_id = gltf.add("images", {
        #     "uri": img_uri
        # })
        # texture_id = gltf.add("textures", {
        #     "sampler": sampler_id,
        #     "source": src_id
        # })
        # mat_id = gltf.add('materials', {
        #         "pbrMetallicRoughness": {
        #             "baseColorTexture": {"index": texture_id},
        #             "metallicFactor": 0.5,
        #             "roughnessFactor": 0.1,
        #         },
        #         "alphaMode": "BLEND",
        #         "doubleSided": True,
        #     })
        # mesh_id = gltf.add('meshes',
        #     {
        #         "primitives": [{
        #             "attributes": {
        #                 "POSITION": board_acc_id[1],
        #                 "NORMAL": board_acc_id[2],
        #                 "TEXCOORD_0": board_acc_id[3],
        #             },
        #             "indices": board_acc_id[0],
        #             "material": mat_id
        #         }]
        #     })
        # scale = [scale[0] * h, scale[1] * w, scale[2] ]
        char_node_ids = drawText(text)
        axes_node['children'].append(gltf.add('nodes', {
          "name" : f"text_{text}",
          "children": char_node_ids,
        #   "mesh" : mesh_id,
          "translation": translation,
          "scale": [0.08] * 3,
        }))
        axes_node['children'].append(gltf.add('nodes', {
          "name" : f"arrow_{text}",
          "mesh" : arrow_mesh_id,
          # "translation": [i,0,0],
          "rotation": rotation,
          # "scale": scale,
        }))
    if animation:
        axes_node['children'].append(gltf.add('nodes', {
          "name" : f"AnimationIndicatorArrow",
          "mesh" : arrow_mesh_id,
          "translation": [-1,-1,1],
          "rotation": [math.sqrt(2)/2, math.sqrt(2)/2, 0, 0 ],
          "scale": [0.3,2,0.3],
        }))
        current_node_id = gltf.add('nodes', {
            "name": f"AnimationIndicatorPoint",
            "mesh": col_mesh_id[0],
            "translation": [-1,-1,1],
            "scale": [0.02] * 3,
        })
        axes_node['children'].append(current_node_id)
        animation_input_acc_id, animation_output_acc_id = gltf.add_buffer_data(
            [ [0,max_animation_input], np.array([ [-1,-1,1],[1,-1,1] ]).reshape((-1, )).tolist() ],
            [GLTF_ARRAY_BUFFER] *3 ,
            ["SCALAR"] + ["VEC3"] * 2,
            remove_view_target=True,
        )
        animation_samplers.append(dict(
            input=animation_input_acc_id,
            interpolation="LINEAR",
            output=animation_output_acc_id,
        ))
        animation_channels.append(dict(
            target=dict(node=current_node_id, path='translation'),
            sampler=len(animation_samplers)-1,
        ))
        if 'time_labels' in animation:
            for i,(t,label) in enumerate(animation['time_labels']):
                x = (1-t) * -1 + t * 1
                char_node_ids = drawText(label, halign='center')
                axes_node['children'].append(gltf.add('nodes', {
                    "name" : f"text_{text}",
                    "children": char_node_ids,
                    #   "mesh" : mesh_id,
                    "translation": [x,-1.01,1.03],
                    "scale": [0.05] * 3,
                }))
                axes_node['children'].append(gltf.add('nodes', {
                    "name": f"Animation Indicator Tick {i}",
                    "mesh": col_mesh_id[0],
                    "translation": [x,-1,1],
                    "scale": [0.01]*3,
                }))
    root_children = [data_node_id]
    if legend_node_id is not None:
        root_children.append(legend_node_id)
    if axes_node_id is not None:
        root_children.append(axes_node_id)
    root_node_id = gltf.add('nodes', {
        "name": f"Root_{data.get('metadata',{}).get('name','')}",
        "children": root_children,
        "scale": [meters_per_unit]*3,
    })
    gltf.add("scenes", {
          "nodes" : [ root_node_id, ]
        })
    for k in [ k for k,v in gltf.d.items() if isinstance(v, list) and len(v) == 0 ]:
        del gltf.d[k]
    return gltf


def create_board(subdiv=8):
    vertices = [ 0,0,0, 1,0,0, 1,1,0, 0,1,0 ]
    indices = [ 0,1,2 , 0,2,3 ]
    normals = [ 0,0,1 ] * (len(vertices) // 3)
    st = [ 0,1, 1,1, 1,0, 0,0 ]
    return indices, vertices, normals, st

def create_sphere(subdiv=8):
    """
    Divide into subdiv latitudinal stripes of 2*subdiv trapeces, and each into 2 triangles.
    :param subdiv:
    :return:
    """
    vertices = [] #[0.0,0.0,0.0] * ((subdiv-1)*(subdiv * 2)+2)
    # normals = [0.0] * len(vertices)
    indices = [] # [0,0,0] * ( subdiv * 2*subdiv * 2 )
    coord2index = []
    # calculate vertices and normals:
    i = 0
    vertices += [0,-1,0] # south pole
    coord2index.append([i])
    i += 1
    for lat in range(1,subdiv):
        alpha = math.pi * (lat / (subdiv)-0.5)
        y = math.sin(alpha)
        radius_lat = math.cos(alpha)
        coords = []
        for lon in range(2*subdiv):
            beta = math.pi * lon / subdiv
            x = math.sin(beta) * radius_lat
            z = math.cos(beta) * radius_lat
            vertices += [x,y,z]
            coords.append(i)
            i+=1
        coord2index.append(coords)
    vertices += [0,1,0] # north pole
    coord2index.append([i])
    # create triangles
    for lat in range(0,subdiv):
        a = coord2index[lat]
        if len(a) == 1:
            a = a*2*subdiv
        b = coord2index[lat+1]
        if len(b) == 1:
            b = b*2*subdiv
        for lon in range(2*subdiv):
            lon1 = (lon + 1) % (2*subdiv)
            if b[lon] != b[lon1]:
                indices += [ a[lon], b[lon1], b[lon]]
            if a[lon] != a[lon1]:
                indices += [ b[lon1], a[lon], a[lon1] ]
    # in a sphere of radius 1 the vertices are also their normals
    normals = vertices
    return indices, vertices, normals

def create_rotation(profile, z_from_to=[0,1], subdiv=8):
    """
    Divide into subdiv latitudinal stripes of 2*subdiv trapeces, and each into 2 triangles.
    :param subdiv:
    :return:
    """
    vertices = [] #[0.0,0.0,0.0] * ((subdiv-1)*(subdiv * 2)+2)
    normals = []
    # normals = [0.0] * len(vertices)
    indices = [] # [0,0,0] * ( subdiv * 2*subdiv * 2 )
    coord2index = []
    # calculate vertices and normals:
    i = 0
    vertices += [0,z_from_to[0],0] # south pole
    normals += [0.0,-1.0,0.0]
    coord2index.append([i])
    i += 1
    for lat,(y,radius_lat)  in enumerate(profile):
        coords = []
        for lon in range(2*subdiv):
            beta = math.pi * lon / subdiv
            x = math.sin(beta) * radius_lat
            z = math.cos(beta) * radius_lat
            vertices += [x,y,z]
            normals += [x / math.sqrt(x**2+z**2), 0.0, z / math.sqrt(x**2+z**2)]
            coords.append(i)
            i+=1
        coord2index.append(coords)
    vertices += [0,z_from_to[1],0] # north pole
    normals += [0.0,1.0,0.0]
    coord2index.append([i])
    # create triangles
    for lat in range(len(profile)+1):
        a = coord2index[lat]
        if len(a) == 1:
            a = a*2*subdiv
        b = coord2index[lat+1]
        if len(b) == 1:
            b = b*2*subdiv
        for lon in range(2*subdiv):
            lon1 = (lon + 1) % (2*subdiv)
            if b[lon] != b[lon1]:
                indices += [ b[lon], a[lon], b[lon1]]
            if a[lon] != a[lon1]:
                indices += [ a[lon1], b[lon1], a[lon] ]
    return indices, vertices, normals
