import logging

import jinja2
import numpy as np

from plotar.export.common import line_segments

from .common import COLORS, COLORS_LEN, text2png, create_surface

logger = logging.getLogger(__name__)

def serialize(x, flip_yz=False):
    x = np.array(x)
    if flip_yz:
        x = x[:,(0,2,1)]
        x[:,2] *= -1
    print(x.shape)
    inlet = ",".join(f"{tuple(row)}" for row in x)
    return f"[{inlet}]"

def data2usd_ascii(data):
    spheres = ""
    texts = ""
    surface = ""
    lines = ""
    axes = ""
    legend = ""
    assets = {}
    meters_per_unit = float(data.get('meters_per_unit', 0.1))
    colors = [ ','.join([str(i) for i in _]) for _ in COLORS ]
    for i, row in enumerate(data.get('data',[])):
        x, z, y = row[:3]
        z = -z
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
            # file = f"text_{i}.png"
            # assets[file] = img
            text_template = """
            def Preliminary_Text "text_{{i}}"
            {
                string content = "{{text|e}}"
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
                i=i, x=x, y=y, z=z, #file=file, w=w, h=h,
                text=data['label'][i], col=col,
            )
            # color3f[] primvars:displayColor = [({color})]
    if 'surface' in data:
        indices, normals, vertices = create_surface(data['surface'])
        vars = dict(
            vertexCounts = [3] * (indices.shape[0] // 3),
            extent = serialize([vertices.min(axis=0), vertices.max(axis=0)]),
            indices = indices.flatten().tolist(),
            vertices = serialize(vertices),
            normals = serialize(normals.flatten().reshape((-1,3))),
        )
        template = """
        def Mesh "Mesh"
        {
            int[] faceVertexCounts = {{vertexCounts}}
            int[] faceVertexIndices = {{indices}}
            normal3f[] normals = {{normals}} (
                interpolation = "vertex"
            )
            point3f[] points = {{vertices}}
            {#
            float3[] extent = {{extent}}
            texCoord2f[] primvars:st = [(0, 0), (0, 1), (1, 0), (1, 1), (0, 0), (0, 1), (1, 0), (1, 1), (0, 0), (0, 1), (1, 0), (1, 1), (0, 0), (0, 1), (1, 0), (1, 1), (0, 0), (0, 1), (1, 0), (1, 1), (0, 0), (0, 1), (1, 0), (1, 1)] (
                interpolation = "faceVarying"
            )
            int[] primvars:st:indices = [0, 3, 1, 0, 2, 3, 4, 7, 5, 4, 6, 7, 8, 11, 9, 8, 10, 11, 12, 15, 13, 12, 14, 15, 16, 19, 17, 16, 18, 19, 20, 23, 21, 20, 22, 23]
            #}
            uniform token subdivisionScheme = "none"
            uniform bool doubleSided = 1
    
            double3 xformOp:translate = (0,0.2,0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
            rel material:binding = </Spheres/Materials/material_{{col}}>
        }
        """
        surface = jinja2.Template(template).render(
            **vars, col=0,
        )
    if 'data' in data and 'lines' in data:
        for i, line in enumerate(data['lines']):
            data_list = data.get('data', [])
            n = len(data_list)
            segments = line_segments(data_list, line, n)
            # points = [ data_list[_][:3] for _ in line.get('points',[]) if _ < n ]
            vars = dict(
                i=i,
                # n_points=len(points),
                segments=segments,
                col=line.get('col',0) % COLORS_LEN,
                width=line.get('width',1)/100,
                # points = serialize(points, flip_yz=True),
            )
            template = """
            def Scope "Line_{{i}}"{
                {% for t,q,s in segments %}
                def Capsule "Line_{{i}}_{{loop.index}}" {
                    rel material:binding = </Spheres/Materials/material_{{col}}>
                    double radius = {{width}}
                    double height = {{s*2}}
                    uniform token axis = "X"
                    double3 xformOp:translate = {{t}}
                    quatf xformOp:orient = {{q}}
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
                }
                {% endfor %}
                {# # BasisCurves is in the USD standard but seems not supporte by Apple 
                def BasisCurves "Curve_{{i}}" (){
                    uniform token type = "linear"
                    int[] curveVertexCounts = [{{n_points}}]
                    point3f[] points = {{points}}
                    float[] widths = [{{width}}] (interpolation = "constant") 
                    color3f[] primvars:displayColor = [(1, 0, 0)]
                }
                    rel material:binding = </Spheres/Materials/material_{{col}}>
                    color3f[] primvars:displayColor = [(1, 0, 0)]
                def BasisCurves "VaryingWidth" (){
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    float3 xformOp:translate = (6, 0, 0)
        
                    uniform token type = "linear"
                    int[] curveVertexCounts = [7]
                    point3f[] points = [(0, 0, 0), (1, 1, 0), (1, 2, 0), (0, 3, 0), (-1, 4, 0), (-1, 5, 0), (0, 6, 0)]
                    float[] widths = [0, .5, .5, .8, .5, .5, 0] (interpolation = "varying")
                    color3f[] primvars:displayColor = [(0, 0, 1)]
                }
                #}
            }
            """
            lines += jinja2.Template(template).render(
                **vars,
            )

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

    for i, text in enumerate(data.get('col_labels',[])):
        col = i % COLORS_LEN
        x, y, z = 1,1-i/10,-1
        template = """
            def Xform "Legend_{{i}}" {
                def Preliminary_Text "Legend_Text_{{i}}"
                {
                    string content = "{{text|e}}"
                    string[] font = [ "Helvetica", "Arial" ]
                    token wrapMode = "singleLine"
                    token horizontalAlignment = "left"
                    token verticalAlignment = "baseline"
                    float depth = 0.01
        
                    double3 xformOp:translate = (0.03,-.03,0)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </Spheres/Materials/material_{{col}}>
                }
                
                def Sphere "Legend_Point{{i}}" {
                    double3 xformOp:translate = (0,0,0)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </Spheres/Materials/material_{{col}}>
        
                    double radius = 0.02
                }
    
                double3 xformOp:translate = ({{x}},{{y}},{{z}})
                uniform token[] xformOpOrder = ["xformOp:translate"]
                rel material:binding = </Spheres/Materials/material_{{col}}>
            }
        """
        legend += jinja2.Template(template).render(
            i=i, x=x, y=y, z=z,
            text=text, col=col,
        )

    for i, text in enumerate(data.get('axis_names',[])):
        scale = [0.01] * 3
        translation = [0,0,0]
        translation[(2*i) % 3] = (-1 if i==1 else 1) * 1.02
        rotation = [0,0,0,0]
        if i<2:
            rotation[0] = np.sqrt(2)/2 * (1-2*i)
            rotation[1 if i==0 else 3] = np.sqrt(2)/2
        else:
            rotation[1] = -1
        # axes_node['children'].append(gltf.add('nodes', {
        #   "mesh" : mesh_id,
        #   "translation": translation,
        #   "scale": scale,
        # }))
        # axes_node['children'].append(gltf.add('nodes', {
        #   "mesh" : arrow_mesh_id,
        #   # "translation": [i,0,0],
        #   "rotation": rotation,
        #   # "scale": scale,
        # }))
        if i==0:
            transform = "(-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (1, 0, 0, 1)"
        elif i==1:
            transform = "(-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, -1, 1)"
        else:
            transform = "(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 1, 0, 1)"
        radius = 0.01
        template = """
            def Xform "Axis_{{i}}" {
                def Preliminary_Text "Axis_Text_{{i}}"
                {
                    string content = "{{text|e}}"
                    string[] font = [ "Helvetica", "Arial" ]
                    token wrapMode = "singleLine"
                    token horizontalAlignment = "left"
                    token verticalAlignment = "baseline"
                    float depth = 0.01

                    double3 xformOp:translate = ({{translation}})
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </Spheres/Materials/material_{{col}}>
                }

                def Cylinder "Axis_Cyl_{{i}}" {
                    rel material:binding = </Spheres/Materials/material_{{col}}>
                    double radius = {{radius}}
                    double height = {{2-2*radius}}
                    uniform token axis = "{{axis}}"
                }
                def Cone "Axis_Cone_{{i}}" {
                    rel material:binding = </Spheres/Materials/material_{{col}}>
                    double radius = {{2*radius}}
                    double height = {{2*radius}}
                    uniform token axis = "{{axis}}"
                    matrix4d xformOp:transform = ( {{transform}} )
                    uniform token[] xformOpOrder = ["xformOp:transform"]
                }
            }
        """
        axes += jinja2.Template(template).render(
            i=i, axis="XZY"[i], radius=radius, transform=transform,
            translation=str(translation)[1:-1],
            rotation=str(rotation)[1:-1],
            text=text, col=i,
        )
    usda = """#usda 1.0
    (
        doc = "PlotAR v0.3.0"
        defaultPrim = "Spheres"
        upAxis = "Y"
        metersPerUnit = {{meters_per_unit}}
    )
    def Xform "Spheres" {
        {% if texts %}def Scope "Texts"
        {
            {{texts}}
        }{%endif%}
        {% if surface %}def Scope "surface"
        {
            {{surface}}
        }{%endif%}
        {% if spheres %}def Scope "Nodes" {
            {{spheres}}
        }{%endif%}
        {% if lines %}def Scope "Lines" {
            {{lines}}
        }{%endif%}
        {% if legend %}def Scope "Legend" {
            {{legend}}
        }{%endif%}
        {% if axes %}def Scope "Axes" {
            {{axes}}
        }{%endif%}
        def Scope "Materials"
        {
            """ + materials + """
        }
    }
    """
    usda = jinja2.Template(usda).render(**locals())
    return usda, assets


def data2usdz(data, use_tools=True, save_usda=False, check=False):
    usda, assets = data2usd_ascii(data)
    if save_usda:
        with open('data_tmp.usda', 'w') as f:
            f.writelines(usda)
    if use_tools:
        result = run_usdconvert_python_package(usda, assets, inSuffix='.usda', check_output=check)
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
    import tempfile
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