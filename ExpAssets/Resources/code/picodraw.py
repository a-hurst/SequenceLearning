from math import sqrt

import numpy
from PIL import Image
from aggdraw import Draw, Brush, Pen

from klibs.KLUtilities import rotate_points, translate_points, canvas_size_from_points


def _offset_from_points(points, size):
    x_points = []
    y_points = []
    for i in range(0, len(points), 2):
        x_points.append(points[i])
        y_points.append(points[i+1])
    x = (max(x_points) + min(x_points)) / 2
    y = (max(y_points) + min(y_points)) / 2
    return [size[0] / 2 - x, size[1] / 2 - y]


def _prepare_points(pts, angle=0, x_adj=0, y_adj=0):
    pts_agg = []
    for x, y in pts:
        pts_agg += [(x - x_adj), (y - y_adj)]
    return rotate_points(pts_agg, (0, 0), angle, flat=True)


def _render_polygon(pts, color, offset=None):
    # Get size and offset
    size = canvas_size_from_points(pts, flat=True)
    if not offset:
        offset = _offset_from_points(pts, size)
    # Initialize surface and colour
    canvas = Image.new("RGBA", size, tuple(list(color[:3]) + [0]))
    surf = Draw(canvas)
    fill = Brush(tuple(color[:3]), color[3] if len(color) > 3 else 255)
    # Actually draw shape to canvas
    pts = translate_points(pts, delta=offset, flat=True)
    surf.polygon(pts, None, fill)
    surf.flush()
    return canvas


def _get_arrow_pts(height, width, thickness, angle=0, alt=False):
    half_h = height // 2
    t = thickness
    t2 = int(thickness * sqrt(2))
    # Get basic chevron
    pts = [(0, 0), (half_h, half_h)]
    if alt:
        pts += [(half_h + t2, half_h)]
    else:
        pts += [(half_h + (t2 // 2), half_h - (t2 // 2))]
    # Get connection coords between head and body
    pts += [(t2 + (t // 2), t // 2), (width, t // 2), (width, 0)]
    # Mirror on other side
    for x, y in pts[::-1][1:-1]:
        pts += [(x, -y)]
    # Center and convert to flat format for aggdraw
    return _prepare_points(pts, angle, x_adj=(width // 2))


def draw_arrow(height, width, thickness, color, angle=0):
    pts = _get_arrow_pts(height, width, thickness, angle)
    canvas = _render_polygon(pts, color)
    return numpy.asarray(canvas)


def draw_rect(width, height, color, angle=0):
    # Prepare points for drawing
    hw, hh = (width / 2, height / 2)
    pts = [(-hw, -hh), (-hw, hh), (hw, hh), (hw, -hh)]
    pts = _prepare_points(pts, angle)
    # Draw and render square
    canvas = _render_polygon(pts, color)
    return numpy.asarray(canvas)


def draw_square(size, color, angle=0):
    # Prepare points for drawing
    hs = size / 2
    pts = [(-hs, -hs), (-hs, hs), (hs, hs), (hs, -hs)]
    pts = _prepare_points(pts, angle)
    # Draw and render square
    canvas = _render_polygon(pts, color)
    return numpy.asarray(canvas)


def draw_triangle(size, color, angle=0):
    # Prepare points for drawing
    hs = size / 2
    pts = []
    for i in range(0, 3):
        p = [0, hs]
        pts += rotate_points(p, (0, 0), i*(360.0/3) + 60, flat=True)
    pts = rotate_points(pts, (0, 0), angle, flat=True)
    # Draw and render square
    canvas = _render_polygon(pts, color)
    return numpy.asarray(canvas)


def draw_star(size, color, shape=0.5):
    # Prepare points for drawing
    hs = size / 2
    pts = []
    for i in range(0, 10):
        p = [0, hs] if i % 2 == 1 else [0, hs * shape]
        pts += rotate_points(p, (0, 0), i*(360.0/10), flat=True)
    # Draw and render star
    canvas = _render_polygon(pts, color, offset=(hs, hs))
    return numpy.asarray(canvas)


def draw_asterisk(size, thickness, color, spokes=6):
    ht = thickness / 2.0 # half of the asterisk's thickness
    hs = size / 2.0 # half of the asterisk's size
    pts = []
    for i in range(0, spokes):
        spoke = [-ht, -ht, -ht, -hs, ht, -hs, ht, -ht]
        pts += rotate_points(spoke, (0, 0), i*(360.0/spokes), flat=True)
    # Draw and render asterisk
    canvas = _render_polygon(pts, color, offset=(hs, hs))
    return numpy.asarray(canvas)


def draw_circle(size, color):
    # Initialize surface and colour
    canvas_size = (size + 2, size + 2)
    canvas = Image.new("RGBA", canvas_size, tuple(list(color[:3]) + [0]))
    #canvas = Image.new("RGBA", canvas_size, (0, 255, 0, 255))
    surf = Draw(canvas)
    fill = Brush(tuple(color[:3]), color[3] if len(color) > 3 else 255)
    # Actually draw shape to canvas
    surf.ellipse([1, 1, size + 1, size + 1], None, fill)
    surf.flush()
    return numpy.asarray(canvas)


def draw_squircle(size, color, radius=0.6):
    # Initialize surface and colour
    r = radius * size / 2
    canvas_size = (size + 2, size + 2)
    canvas = Image.new("RGBA", canvas_size, tuple(list(color[:3]) + [0]))
    #canvas = Image.new("RGBA", canvas_size, (0, 255, 0, 255))
    surf = Draw(canvas)
    fill = Brush(tuple(color[:3]), color[3] if len(color) > 3 else 255)
    # Actually draw shape to canvas
    surf.rounded_rectangle([1, 1, size + 1, size + 1], r, None, fill)
    surf.flush()
    return numpy.asarray(canvas)
