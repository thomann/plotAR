import base64
import math
import struct

from .common import COLORS, COLORS_LEN

GLTF_ELEMENT_ARRAY_BUFFER = 34963
GLTF_ARRAY_BUFFER = 34962
GLTF_TYPE_UNSIGNED_SHORT = 5123
GLTF_TYPE_FLOAT = 5126


def data2gltf(data, subdiv=16):
    spheres = []
    for i, row in enumerate(data['data']):
        x, y, z = row[:3]
        col = 0
        scale = 0.01
        if 'col' in data:
            col = data['col'][i] % COLORS_LEN
        if 'size' in data:
            scale *= data['size'][i]
        spheres += [{
          "mesh" : col,
          "translation": [x,z,-y],
          "scale": [scale] * 3,
        }]

    indices, vertices, normals = create_sphere(subdiv=subdiv)
    mesh = create_gltf_mesh(indices, vertices, normals, colors=COLORS)
    gltf = {
      "scenes" : [
        {
          "nodes" : list(range(len(spheres)))
        }
      ],
      "nodes" : spheres,
      "asset" : {
        "version" : "2.0"
      }
    }
    gltf.update(mesh)
    return gltf


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
        alpha = math.pi * (2*lat / subdiv - 0.5)
        y = math.cos(alpha)
        radius_lat = math.sin(alpha)
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
    for lat in range(subdiv):
        a = coord2index[lat]
        if len(a) == 1:
            a = a*2*subdiv
        b = coord2index[lat+1]
        if len(b) == 1:
            b = b*2*subdiv
        for lon in range(2*subdiv):
            lon1 = (lon + 1) % (2*subdiv)
            if b[lon] != b[lon1]:
                indices += [ a[lon] , b[lon], b[lon1]]
            if a[lon] != a[lon1]:
                indices += [ b[lon1], a[lon1], a[lon] ]
    # in a sphere of radius 1 the vertices are also their normals
    normals = vertices
    return indices, vertices, normals


def create_gltf_mesh(indices, vertices, normals, colors):
    buffer_format = "H"*len(indices) + "f"*len(vertices) + "f"*len(normals)
    buffer = struct.pack( buffer_format, * indices + vertices + normals )
    buffer_url = "data:application/octet-stream;base64,"+base64.b64encode(buffer).decode("ASCII")
    return {
        "meshes": [
            {
                "primitives": [{
                    "attributes": {
                        "POSITION": 1,
                        "NORMAL": 2,
                    },
                    "indices": 0,
                    "material": col
                }]
            }
            for col in range(len(colors))
        ],

        "buffers": [
            {
                "uri": buffer_url,
                "byteLength": len(buffer)
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": len(indices) * 2,
                "target": GLTF_ELEMENT_ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": struct.calcsize("H"*len(indices)),
                "byteLength": struct.calcsize("f"*len(vertices)),
                "target": GLTF_ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": struct.calcsize("H" * len(indices) + "f"*len(vertices)),
                "byteLength": struct.calcsize("f"*len(normals)),
                "target": GLTF_ARRAY_BUFFER
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": GLTF_TYPE_UNSIGNED_SHORT,
                "count": len(indices),
                "type": "SCALAR",
                "max": [max(indices)],
                "min": [min(indices)]
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": GLTF_TYPE_FLOAT,
                "count": len(vertices)//3,
                "type": "VEC3",
                "max": [1.0, 1.0, 1.0],
                "min": [-1.0, -1.0, -1.0]
            },
            {
                "bufferView": 2,
                "byteOffset": 0,
                "componentType": GLTF_TYPE_FLOAT,
                "count": len(normals)//3,
                "type": "VEC3",
                "max": [1.0, 1.0, 1.0],
                "min": [-1.0, -1.0, -1.0]
            },
        ],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": list(col) + [1.0],
                    "metallicFactor": 0.5,
                    "roughnessFactor": 0.1
                }
            }
            for col in colors
        ],

    }