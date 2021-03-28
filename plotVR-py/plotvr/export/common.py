
COLORS = [(1, 0, 0), (0, 0, 1), (0, 1, 0)]
COLORS_LEN = len(COLORS)


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


def obj2usdz(data):
    from .usd import run_usdconvert_python_cli
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