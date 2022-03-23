import cv2

from PIL import Image
from PIL import ImageDraw


def draw_polygon(im, vertices, vertex_colors=None, edge_colors=None,
                 alter_input_image=False, draw_edges=True, draw_vertices=True):
    """Draws a polygon bounding box."""
    _default_vertex_color = (255, 0, 0)
    _default_edge_color = (255, 0, 0)
    im2 = im if alter_input_image else im.copy()
    if vertices is not None:
        N = len(vertices)
        vertices = [tuple(v) for v in vertices]
        if vertex_colors is None:
            vertex_colors = [_default_vertex_color] * N
        if edge_colors is None:
            edge_colors = [_default_edge_color] * N

        for i in range(N):
            startpt = (int(vertices[(i - 1) % N][0]), int(vertices[(i - 1) % N][1]))

            if draw_vertices:
                cv2.circle(im2, startpt, 3, vertex_colors[(i - 1) % N], -3, cv2.LINE_AA)

        for i in range(N):
            startpt = (int(vertices[(i - 1) % N][0]), int(vertices[(i - 1) % N][1]))
            if draw_edges:
                endpt = (int(vertices[i][0]), int(vertices[i][1]))
                cv2.line(im2, startpt, endpt, edge_colors[(i - 1) % N], 2, cv2.LINE_AA)
    
    return im2


def draw_objects(draw, objs):
    """Draws the bounding box and label for each object."""
    for bbox in objs:
        draw.rectangle([(bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax)],
                   outline='red')