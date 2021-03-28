import jinja2

from .server import logger
import struct, base64, math
import click
import json
from pathlib import Path

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
    texts = ""
    assets = {}
    colors = [ ','.join([str(i) for i in _]) for _ in COLORS ]
    for i, row in enumerate(data['data']):
        x, y, z = row[:3]
        col = 0
        if 'col' in data:
            col = data['col'][i] % COLORS_LEN
        # color = colors[col]
        size = data['size'][i] if 'size' in data else 1.0
        if 'label' not in data:
            spheres += f"""
            def Sphere "Point{i}" {{
                double3 xformOp:translate = ({x},{y},{z})
                uniform token[] xformOpOrder = ["xformOp:translate"]
                rel material:binding = </Spheres/Materials/material_{col}>
    
                double radius = {0.02*size}
            }}
            """
        else:
            w,h, img = text2png(data['label'][i])
            w /= 100
            h /= 100
            file = f"text_{i}.png"
            # assets[file] = img
            text_template = """
            def Preliminary_Text "text_{{i}}"
            {
                string content = "{{text}}"
                string[] font = [ "Helvetica", "Arial" ]
                token wrapMode = "singleLine"
                token horizontalAlignment = "left"
                token verticalAlignment = "baseline"
                float depth = 0.01
                
                double3 xformOp:translate = ({{x}},{{y}},{{z}})
                uniform token[] xformOpOrder = ["xformOp:translate"]
                rel material:binding = </Spheres/Materials/material_{{col}}>
            }
            """
            ## the following
            _template_image = """
            def Mesh "text_{{i}}"
            {
                // float3[] extent = [(-430, -145, 0), (430, 145, 0)]
                int[] faceVertexCounts = [4]
                int[] faceVertexIndices = [0, 1, 2, 3]
                rel material:binding = </Spheres/Texts/text_{{i}}/boardMat>
                point3f[] points = [ ({{x}}, {{y}}, {{z}}), ({{x+w}}, {{y}}, {{z}}), ({{x+w}}, {{y+h}}, {{z}}), ({{x}}, {{y+h}}, {{z}}) ]
                texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
                    interpolation = "varying"
                )
        
                def Material "boardMat"
                {
                    token inputs:frame:stPrimvarName = "st"
                    token outputs:surface.connect = </Spheres/Texts/text_{{i}}/boardMat/PBRShader.outputs:surface>
        
                    def Shader "PBRShader"
                    {
                        uniform token info:id = "UsdPreviewSurface"
                        color3f inputs:diffuseColor.connect = </Spheres/Texts/text_{{i}}/boardMat/diffuseTexture.outputs:rgb>
                        float inputs:metallic = 0
                        float inputs:roughness = 0.4
                        token outputs:surface
                    }
        
                    def Shader "stReader"
                    {
                        uniform token info:id = "UsdPrimvarReader_float2"
                        token inputs:varname.connect = </Spheres/Texts/text_{{i}}/boardMat.inputs:frame:stPrimvarName>
                        float2 outputs:result
                    }
        
                    def Shader "diffuseTexture"
                    {
                        uniform token info:id = "UsdUVTexture"
                        asset inputs:file = @{{file}}@
                        float2 inputs:st.connect = </Spheres/Texts/text_{{i}}/boardMat/stReader.outputs:result>
                        float3 outputs:rgb
                    }
                }
            }
            """
            texts += jinja2.Template(text_template).render(
                i=i, x=x, y=y, z=z, w=w, h=h, file=file,
                text=data['label'][i], col=col,
            )
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
        def Scope "Texts"
        {
            """ + texts + """
        }
        def Xform "Nodes" {
            """ + spheres + """
        }
        def Scope "Materials"
        {
            """ + materials + """
        }
    }
    """
    return usda, assets

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

def data2usdz(data, use_tools=True, save_usda=False):
    usda, assets = data2usd_ascii(data)
    if save_usda:
        with open('data_tmp.usda', 'w') as f:
            f.writelines(usda)
    if use_tools:
        result = run_usdconvert_python_package(usda, assets, inSuffix='.usda')
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


def run_usdconvert_python_package(content, assets={}, inSuffix='.usda', tmpSuffix='.usdc', outSuffix='.usdz', check_output=False):
    from pxr import Usd
    from pxr import Sdf
    from pxr import Ar
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
        ## Actually this seems not to work as expected
        ## right now:
        for key, val in assets.items():
            d = tempfile.mktemp()
            with open(d, 'w') as f:
                f.write(content)
            zfw.AddFile(d, key)

    # r = Ar.GetResolver()
    # resolvedAsset = r.Resolve(args.arkitAsset)
    # if args.checkCompliance:
    #     success = _CheckCompliance(resolvedAsset, arkit=True) and success
    #
    # context = r.CreateDefaultContextForAsset(resolvedAsset)
    # with Ar.ResolverContextBinder(context):
    #     # Create the package only if the compliance check was passed.
    #     success = success and UsdUtils.CreateNewARKitUsdzPackage(
    #         Sdf.AssetPath(args.arkitAsset), usdzFile)

    if check_output:
        usd_check(c)
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

def usd_check(inputFile, arkit=True, verbose=True):
    from pxr import UsdUtils
    checker = UsdUtils.ComplianceChecker(arkit=arkit, verbose=verbose,
                                         # skipARKitRootLayerCheck=False, rootPackageOnly=args.rootPackageOnly,
                                         # skipVariants=args.skipVariants
                                         )

    checker.CheckCompliance(inputFile)

    errors = checker.GetErrors()
    failedChecks = checker.GetFailedChecks()

    if len(errors) > 0 or len(failedChecks) > 0:
        for msg in errors + failedChecks:
            print(msg)

def obj2usdz(data):
    obj = data2obj(data)
    usdz = run_usdconvert_python_cli(obj, in_suffix='obj')
    return usdz

def text2png(text, truetype=None, fontsize=100):
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    f = ImageFont.load_default()
    w, h = f.getsize(text)

    img = Image.new("RGBA", (w, h), (0,0,0,0))
    # get a drawing context
    d = ImageDraw.Draw(img)
    # draw text, half opacity
    d.text((0, 0), text, font=f, fill=(255, 0, 255, 128))

    buffer = BytesIO()
    img.save(buffer, format='png')
    return w, h, buffer.getvalue()

if False:
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

@click.command()
@click.argument('data', type=click.Path(exists=True))
@click.argument('out', default='', type=click.Path())
@click.option('-f', '--format', default=None, help="format: gltf usdz usda obj. Default is to take extension of out or else gltf")
def export(data, out=None, format=None):
    """Convert the DATA.json to OUT.format."""
    data_path = Path(data)
    with open(data, 'r') as f:
        input = json.load(f)
    if format is None:
        assert out is not None
        # data_path.suffix might be '' !
        format = Path(out).suffix.lstrip('.')
    elif out is None or out == '':
        format = format or 'usdz'
        out = data_path.with_suffix("."+format)
    mode = 'wb' if format.startswith("usd") else 'w'
    with open(out, mode) as outfile:
        if format == 'gltf':
            result = data2gltf(input)
            json.dump(result, outfile)
        elif format == 'obj':
            result = data2obj(input)
            outfile.write(result)
        elif format == 'usda':
            usda, assets = data2usd_ascii(input)
            outfile.write(usda.encode("utf-8"))
            for key, val in assets.items():
                with open(key, 'wb') as f:
                    f.write(val)
        else:
            result = data2usdz(input, save_usda=False)
            outfile.write(result)

if __name__ == '__main__':
    export()