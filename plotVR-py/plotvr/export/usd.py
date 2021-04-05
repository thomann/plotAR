import logging

import jinja2
import numpy as np

from .common import COLORS, COLORS_LEN, text2png, create_surface

logger = logging.getLogger(__name__)

def data2usd_ascii(data):
    spheres = ""
    texts = ""
    surface = ""
    assets = {}
    colors = [ ','.join([str(i) for i in _]) for _ in COLORS ]
    for i, row in enumerate(data.get('data',[])):
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
    if 'surface' in data:
        indices, normals, vertices = create_surface(data['surface'])
        def serialize(x):
            x = np.array(x)
            print(x.shape)
            inlet = ",".join(f"{tuple(row)}" for row in x)
            return f"[{inlet}]"
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
        {% if texts %}def Scope "Texts"
        {
            {{texts}}
        }{%endif%}
        {% if surface %}def Scope "surface"
        {
            {{surface}}
        }{%endif%}
        {% if spheres %}def Xform "Nodes" {
            {{spheres}}
        }{%endif%}
        def Scope "Materials"
        {
            """ + materials + """
        }
    }
    """
    usda = jinja2.Template(usda).render(**locals())
    return usda, assets


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