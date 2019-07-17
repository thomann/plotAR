
from .server import logger

COLORS = [
    '1 0 0', # RED
    '0 1 0', # GREEN
    '0 0 1', # BLUE
]

def makeObj(data):
    result = ['# OBJ file for dataset']
    def add(x):
        result.append(x)
    numVert = 1
    for i,row in enumerate(data['data']):
        x, y, z = row[:3]
        col = COLORS[0]
        if 'col' in data and i <= len( data['col']):
            col = COLORS[ data['col'][i] % len(COLORS) ]
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

def dev_makeUsd(data):
    spheres = ""
    for i, row in enumerate(data):
        x, y, z = row[:3]
        color = "1, 0, 0"
        if 'color' in data:
            color = ["1,0,0", "0,1,0", "0,0,1"][data['color'][i] % 3]
        spheres += f"""
        def Sphere "Point{i}" {{
            uniform token[] xformOpOrder = ["xformOp:translate"]
            float3 xformOp:translate = ({x},{y},{z})
            double radius = 0.02
            color3f[] primvars:displayColor = [({color})]
        }}
        """
    usda = """#usda 1.0

    (
        upAxis = "Y"
    )

    def Xform "Spheres" {
        """ + spheres + """
    }
    """
    if False:
        from io import BytesIO
        import zipfile
        zipname = "clients_counter.zip"
        f = BytesIO()
        zf = zipfile.ZipFile(f, "w")
        zf.writestr('data.usda', usda)
        zf.close()
        result = f.getvalue()
    if True:
        result = runXcrun(usda, inSuffix='.usda')
    return result


def runXcrun(content, inSuffix='.obj', outSuffix='.usdz'):
    import tempfile, os
    a = tempfile.mktemp(inSuffix)
    b = tempfile.mktemp(outSuffix)
    print(a, b)
    with open(a, 'w') as inp:
        inp.write(content)
    cmd = f'xcrun usdz_converter {a} {b}'
    logger.info("running " + cmd)
    os.system(cmd)
    with open(b, 'rb') as out:
        result = out.read()
    return result

def makeUsdz(data):
    obj = makeObj(data)
    usdz = runXcrun(obj)
    return usdz

if __name__ == '__main__':
    print("Welcome")
    input = '../../tmp/ecoinvest.json'
    output = '../../tmp/ecoinvest.obj'
    import json
    with open(input) as f:
        payload = json.load(f)
    obj = makeObj(payload)
    print(obj)
    with open(output, 'w') as f:
        f.write(obj)
    print("Byebye.")
