import math

import numpy as np

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


def text2png(text, truetype=None, fontsize=10, color=(1, 0, 1), dpi_factor=10,
             font=[ "HelveticaNeue123", "HelveticaNeue", "Helvetica", "DejaVuSans", "Arial", ]):
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    f = None
    # we also need to search lower case on Windows
    for fontname in font + [f.lower() for f in font]:
        try:
            f = ImageFont.truetype(fontname, fontsize * dpi_factor)
            # print(f"found font {f.font.family}")
            break
        except:
            pass
    if f is None:
        f = ImageFont.load_default()
        dpi_factor = 1
    w, h = f.getsize(text)

    img = Image.new("RGBA", (w, h), (0,0,0,0))
    # get a drawing context
    d = ImageDraw.Draw(img)
    # draw text, half opacity
    d.text((0, 0), text, font=f, fill=tuple(c*255 for c in color) + (255,) )

    buffer = BytesIO()
    img.save(buffer, format='png', compress_level=0)
    return w / dpi_factor, h / dpi_factor, buffer.getvalue()


def create_surface(surface):
    n, m = [int(_) for _ in surface['shape']]
    # print('surface:', n, m)
    arr = np.array(surface['data'])
    assert len(surface['data']) == n
    xvec = surface.get('x') or np.arange(-1, 1, 2 / m).tolist()
    yvec = surface.get('y') or np.arange(-1, 1, 2 / n).tolist()
    # TODO convert the following for loops into numpy
    vertices = np.array([
        [x, z / 20.0, y]
        for y, row in zip(yvec, surface['data'])
        for x, z in zip(xvec, row)
    ])
    indices = np.array([
        [j, j + m + 1, j + 1, j, j + m, j + m + 1]
        for j in range((n - 1) * m) if (j + 1) % m
    ]).flatten()#.tolist()
    # print('surface:', indices.max(), vertices.shape)
    # TODO handle edges better than roll-over
    dx = (np.roll(arr, 1, axis=0) - np.roll(arr, -1, axis=0)) / (np.roll(xvec, 1) - np.roll(xvec, -1))[np.newaxis, :]
    dy = (np.roll(arr, 1, axis=1) - np.roll(arr, -1, axis=1)) / (np.roll(yvec, 1) - np.roll(yvec, -1))[:, np.newaxis]
    dz = np.zeros((n, m)) + 2
    dlen = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    # print(dlen.shape, dlen.max())
    normals = np.stack((dx / dlen, dz / dlen, dy / dlen), axis=-1)
    # print(normals.shape)
    return indices, normals, vertices


def line_segments(data_list, line, n, flip_vector=False):
    mids, quats, scales, a = [], [], [], None
    front_vector = (0,1,0) if flip_vector else (1, 0, 0)
    front_vector = np.array(front_vector)

    def flip_yz(x):
        x = np.array(x)
        x = x[..., (0, 2, 1)]
        x[..., 2] *= -1
        return x

    for b in [flip_yz(data_list[_][:3]) for _ in line.get('points', []) if _ < n]:
        if a is not None:
            # calculate quat for cylinder from a to b
            d = (b - a) / 2
            dlen = np.linalg.norm(d)
            if dlen == 0:
                # b==a so we do not add anything at that point
                continue
            mids.append(tuple((a + b) / 2))
            scales.append(dlen)
            if all(np.abs(d) == np.abs(d*front_vector)):
                # we do not need to rotate anything
                quats.append((1, 0, 0, 0))
            else:
                theta_2 = math.acos(np.dot(front_vector, d / dlen)) / 2
                rot_axis = np.cross(front_vector, d / dlen)
                if flip_vector:
                    rot_axis = rot_axis[[2,1,0]]
                    rot_axis[2] *= -1
                rot_axis = rot_axis / np.linalg.norm(rot_axis) * np.sin(theta_2)
                quats.append((np.cos(theta_2),) + tuple(rot_axis))
        a = b
    return zip(mids, quats, scales)