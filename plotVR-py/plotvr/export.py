
from .server import logger
import struct, base64, math

COLORS = [(1, 0, 0), (0, 0, 1), (0, 1, 0)]
COLORS_LEN = len(COLORS)

GLTF_ELEMENT_ARRAY_BUFFER = 34963
GLTF_ARRAY_BUFFER = 34962
GLTF_TYPE_UNSIGNED_SHORT = 5123
GLTF_TYPE_FLOAT = 5126

# with mac developer account: https://developer.apple.com/augmented-reality/tools/


def data2obj(data):
    result = ['# OBJ file for dataset']
    def add(x):
        result.append(x)
    numVert = 1
    colors = [ " ".join(_) for _ in COLORS ]
    for i,row in enumerate(data['data']):
        x, y, z = row[:3]
        col = COLORS[0]
        if 'col' in data and i <= len( data['col']):
            col = colors[ data['col'][i] % COLORS_LEN ]
        add(f'o Point {i}')
        for a in [1,-1]:
            for b in [1,-1]:
                for c in [1,-1]:
                    r = 0.05
                    v = " ".join(map(str, [x+a*r,y+b*r,z+c*r]))
                    add(f'v {v} {col}')
        f = [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [0, 2, 4, 6],
            [1, 3, 5, 7],
            [0, 1, 4, 5],
            [2, 3, 6, 7],
        ]
        for a,b,c,d in f:
            add(f"f {a+numVert} {b+numVert} {c+numVert} {a+numVert}")
            add(f"f {a+numVert} {c+numVert} {b+numVert} {a+numVert}")
            add(f"f {d + numVert} {b + numVert} {c + numVert} {d + numVert}")
            add(f"f {d + numVert} {c + numVert} {b + numVert} {d + numVert}")
        numVert += 8
    return "\n".join(result)

def data2usd_ascii(data):
    spheres = ""
    colors = [ ','.join([str(i) for i in _]) for _ in COLORS ]
    for i, row in enumerate(data['data']):
        x, y, z = row[:3]
        col = 0
        if 'col' in data:
            col = data['col'][i] % COLORS_LEN
        # color = colors[col]
        spheres += f"""
        def Sphere "Point{i}" {{
            double3 xformOp:translate = ({x},{y},{z})
            uniform token[] xformOpOrder = ["xformOp:translate"]
            rel material:binding = </Spheres/Materials/material_{col}>

            double radius = 0.02
        }}
        """
            # color3f[] primvars:displayColor = [({color})]
    materials = ""
    for i,col in enumerate(COLORS):
        materials += f"""
        def Material "material_{i}"
        {{
            token outputs:surface.connect = </Spheres/Materials/material_{i}/surfaceShader.outputs:surface>

            def Shader "surfaceShader"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({", ".join(str(_) for _ in col)})
                color3f inputs:emissiveColor = (0, 0, 0)
                float inputs:metallic = 0.5
                normal3f inputs:normal = (1, 1, 1)
                float inputs:occlusion = 0
                float inputs:opacity = 1
                float inputs:roughness = 0.1
                token outputs:surface
            }}
        }}
"""
    usda = """#usda 1.0
    (
        defaultPrim = "Spheres"
        upAxis = "Y"
        metersPerUnit = 1
    )
    def Xform "Spheres" {
        def Xform "Nodes" {
            """ + spheres + """
        }
        def Scope "Materials"
        {
            """ + materials + """
        }
    }
    """
    return usda

def data2gltf(data, subdiv=16):
    spheres = []
    for i, row in enumerate(data['data']):
        x, y, z = row[:3]
        col = 0
        scale = 0.01
        if 'col' in data:
            col = data['col'][i] % COLORS_LEN
        if 'scale' in data:
            scale *= data['scale'][i]
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

def data2usdz(data, use_tools=True, save_usda=False):
    usda = data2usd_ascii(data)
    if save_usda:
        with open('data_tmp.usda', 'w') as f:
            f.writelines(usda)
    if use_tools:
        result = run_usdconvert_python_package(usda, inSuffix='.usda')
        # n = len(usdc)
        # n_align = math.ceil(n / 64) * 64
        # logger.info(f"Padding usdc to 64 bytes align {n} --> {n_align}")
        # usdc = usdc + b'\0' * (n_align-n)
        # from io import BytesIO
        # import zipfile
        # f = BytesIO()
        # zf = zipfile.ZipFile(f, "w", compression=zipfile.ZIP_STORED)
        # zf.writestr('data.usdc', usdc)
        # zf.close()
        # result = f.getvalue()
    else:
        from io import BytesIO
        import zipfile
        f = BytesIO()
        zf = zipfile.ZipFile(f, "w", compression=zipfile.ZIP_STORED)
        zf.writestr('data.usda', usda)
        zf.close()
        with open("test.usdz", "wb") as tmp:
            tmp.write(f.read())
        result = f.getvalue()
    return result


def run_usdconvert_python_package(content, inSuffix='.usda', tmpSuffix='.usdc', outSuffix='.usdz'):
    from pxr import Usd
    from pxr import Sdf
    import tempfile, os
    a = tempfile.mktemp(inSuffix)
    b = tempfile.mktemp(tmpSuffix)
    c = tempfile.mktemp(outSuffix)
    print(a, b, c)
    with open(a, 'w') as inp:
        inp.write(content)
    stage = Sdf.Layer.FindOrOpen(a)
    stage.Export(b)
    with Usd.ZipFileWriter.CreateNew(c) as zfw:
        addedFile = zfw.AddFile(b, 'data.usdc')
        logger.info(f"addedFile {b} as data.usdc")
    with open(c, 'rb') as out:
        result = out.read()
    return result

def run_usdconvert_python_cli(content, inSuffix='.usda', outSuffix='.usdz'):
    # with mac developer account: https://developer.apple.com/augmented-reality/tools/
    # https://developer.nvidia.com/usd-20.05-binary-linux-python-3.6
    import tempfile, os
    a = tempfile.mktemp(inSuffix)
    b = tempfile.mktemp(outSuffix)
    print(a, b)
    with open(a, 'w') as inp:
        inp.write(content)
    USDZ_DIR = '/Applications/usdpython/'
    cmd = f'PYTHONPATH={USDZ_DIR}/USD/lib/python {USDZ_DIR}/usdzconvert/usdzconvert {a} {b}'
    logger.info("running " + cmd)
    os.system(cmd)
    with open(b, 'rb') as out:
        result = out.read()
    return result

def runXcrun(content, in_suffix='.obj', out_suffix='.usdz'):
    import tempfile, os
    a = tempfile.mktemp(in_suffix)
    b = tempfile.mktemp(out_suffix)
    print(a, b)
    with open(a, 'w') as inp:
        inp.write(content)
    cmd = f'xcrun usdz_converter {a} {b}'
    logger.info("running " + cmd)
    os.system(cmd)
    with open(b, 'rb') as out:
        result = out.read()
    return result

def obj2usdz(data):
    obj = data2obj(data)
    usdz = run_usdconvert(obj, in_suffix='obj')
    return usdz

if __name__ == '__main__':
    print("Welcome")
    input = 'iris.json'
    output = 'data_tmp.usdz'
    # output = 'iris.gltf'
    import json
    with open(input) as f:
        payload = json.load(f)
    result = data2usdz(payload, save_usda=True)
    with open(output, 'wb') as f:
        f.write(result)
        # json.dump(result, f, indent=True)
    with open('data_tmp.gltf', 'w') as f:
        result = data2gltf(payload)
        json.dump(result, f, indent=4)
    print("Byebye.")
