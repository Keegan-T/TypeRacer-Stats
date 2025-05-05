import math
import random

import matplotlib.path as mpath
from PIL import Image, ImageDraw
from matplotlib.path import Path

YELLOW = (255, 204, 77)
BROWN = (102, 69, 0)
ORANGE = (245, 144, 12)


##### SHAPE GENERATORS #####

def generate_blob(center, radius):
    spikiness = random.uniform(0, 1)
    point_count = random.randint(6, 18)
    cx, cy = center
    angle_step = 2 * math.pi / point_count

    points = []

    for i in range(point_count):
        angle = i * angle_step
        r = radius * (1 + random.uniform(-spikiness, spikiness))
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))

    points.append(points[0])

    return points


def generate_eyes(face_polygon, inside=True):
    eye_radius = random.randint(20, 50)
    eyes = []
    for _ in range(2):
        center = random_point_in_polygon(face_polygon, inside)
        if center is None:
            continue

        eye_blob = generate_eye(center, eye_radius)
        eyes.append(eye_blob)

    return eyes


def generate_eye(center, radius):
    spikiness = random.uniform(0, 0.5)
    point_count = random.randint(4, 8)
    cx, cy = center
    angle_step = 2 * math.pi / point_count

    points = []

    for i in range(point_count):
        angle = i * angle_step
        r = radius * (1 + random.uniform(-spikiness, spikiness))
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))

    points.append(points[0])

    return points


def generate_eyebrow(eye_bbox):
    x0, y0, x1, y1 = eye_bbox
    eye_width = x1 - x0
    eye_height = y1 - y0
    cx = (x0 + x1) / 2

    width = eye_width * random.uniform(1.0, 2.2)
    height = eye_height * random.uniform(0.2, 0.5)

    vertical_offset = eye_height * random.uniform(0, 1)
    top = y0 - vertical_offset

    arc_amount = random.uniform(-0.3, 0.3) * height

    left = cx - width / 2
    right = cx + width / 2
    points = [
        (left, top),
        (right, top),
        (right, top + height + arc_amount),
        (left, top + height - arc_amount),
    ]

    rotation = random.uniform(-math.pi / 6, math.pi / 6)
    rotated = [rotate_point(x, y, cx, top + height / 2, rotation) for x, y in points]

    return rotated


def generate_unibrow(bbox1, bbox2):
    x0 = min(bbox1[0], bbox2[0])
    y0 = min(bbox1[1], bbox2[1])
    x1 = max(bbox1[2], bbox2[2])
    y1 = min(bbox1[1], bbox2[1])

    cx = (x0 + x1) / 2
    width = (x1 - x0) * random.uniform(1.0, 1.3)
    height = (bbox1[3] - bbox1[1]) * random.uniform(0.3, 0.6)
    top = y1 - random.uniform(5, 15)

    arc_amount = random.uniform(-0.4, 0.4) * height

    left = cx - width / 2
    right = cx + width / 2
    points = [
        (left, top),
        (right, top),
        (right, top + height + arc_amount),
        (left, top + height - arc_amount),
    ]

    rotation = random.uniform(-math.pi / 20, math.pi / 20)
    rotated = [rotate_point(x, y, cx, top + height / 2, rotation) for x, y in points]
    return rotated


def generate_mouth(eye_shapes):
    lowest_y = max(max(y for _, y in eye) for eye in eye_shapes)

    all_eye_x = [x for eye in eye_shapes for x, _ in eye]
    min_x, max_x = min(all_eye_x), max(all_eye_x)
    cx = (min_x + max_x) / 2

    cy = lowest_y + random.uniform(15, 35)

    if cy > 512:
        cy = 512 - random.randint(50, 200)

    width = random.uniform(40, 160)
    height = random.uniform(10, 20)
    angle = random.uniform(-math.pi / 15, math.pi / 15)

    points = [
        (cx - width / 2, cy - height / 2),
        (cx + width / 2, cy - height / 2),
        (cx + width / 2, cy + height / 2),
        (cx - width / 2, cy + height / 2),
    ]
    rotated = [rotate_point(px, py, cx, cy, angle) for px, py in points]
    return rotated


def generate_open_mouth(eye_shapes, mood):
    lowest_y = max(max(y for _, y in eye) for eye in eye_shapes)
    all_eye_x = [x for eye in eye_shapes for x, _ in eye]
    min_x, max_x = min(all_eye_x), max(all_eye_x)
    cx = (min_x + max_x) / 2
    cy = lowest_y + random.uniform(15, 35)

    if cy > 512:
        cy = 512 - random.randint(50, 200)

    width = random.uniform(40, 200)
    height = random.uniform(20, 100)
    angle = random.uniform(-math.pi / 15, math.pi / 15)

    x1, y1 = cx - width / 2, cy
    x2, y2 = cx + width / 2, cy

    ctrl_y_offset = 0
    if mood == "frown":
        ctrl_y_offset = -height
    elif mood == "smile":
        ctrl_y_offset = height

    cx_ctrl, cy_ctrl = cx, cy + ctrl_y_offset

    points = [
        bezier_quadratic(t, (x1, y1), (cx_ctrl, cy_ctrl), (x2, y2))
        for t in [i / 20 for i in range(21)]
    ]

    rotated = [rotate_point(px, py, cx, cy, angle) for px, py in points]
    return rotated


def generate_closed_mouth(eye_shapes, mood):
    lowest_y = max(max(y for _, y in eye) for eye in eye_shapes)
    all_eye_x = [x for eye in eye_shapes for x, _ in eye]
    min_x, max_x = min(all_eye_x), max(all_eye_x)
    cx = (min_x + max_x) / 2
    cy = lowest_y + random.uniform(15, 35)

    rx = random.uniform(15, 100)
    ry = random.uniform(15, 100)
    start_angle = 180
    end_angle = 0
    smile_offset = 2
    if mood == "frown":
        end_angle = 360
        smile_offset = -smile_offset
        cy += ry
    rotation = random.uniform(-30, 30)

    outer = generate_mouth_polygon(cx, cy + smile_offset, rx, ry, start_angle, end_angle, rotation=rotation)

    margin = random.uniform(10, 20)
    inner = generate_mouth_polygon(cx, cy, rx - margin, ry - margin, start_angle, end_angle, rotation=rotation)

    return outer, inner


def generate_mouth_polygon(cx, cy, rx, ry, start_angle, end_angle, steps=300, rotation=0):
    points = []
    for i in range(steps + 1):
        theta = math.radians(start_angle + (end_angle - start_angle) * i / steps)
        x = rx * math.cos(theta)
        y = ry * math.sin(theta)

        rot = math.radians(rotation)
        x_rot = x * math.cos(rot) - y * math.sin(rot)
        y_rot = x * math.sin(rot) + y * math.cos(rot)

        points.append((cx + x_rot, cy + y_rot))
    return points


def generate_hand():
    cx, cy = 256, 256

    thumb_width = 20
    thumb_height = 100

    finger_width = random.uniform(175, 225)
    long_chance = random.randint(0, 50)
    if long_chance == 25:
        finger_width = random.uniform(300, 400)
    finger_height = 20

    palm_width = 100
    palm_height = 60

    thumb_left = cx - thumb_width // 2
    thumb_right = cx + thumb_width // 2
    thumb_top = cy - thumb_height

    thumb = [
        (thumb_left, cy + 30),
        (thumb_right, cy + 30),
        (thumb_right, thumb_top + 30),
        (thumb_left, thumb_top + 30),
    ]

    finger_top = cy - finger_height // 2
    finger_bottom = cy + finger_height // 2
    finger_left = cx
    finger_right = cx + finger_width

    finger = [
        (finger_left, finger_bottom),
        (finger_right - 30, finger_bottom),
        (finger_right - 30, finger_top),
        (finger_left, finger_top),
    ]

    palm_left = thumb_left
    palm_right = palm_left + palm_width
    palm_top = cy + (palm_height // 2) - palm_height // 2
    palm_bottom = cy + (palm_height // 2) + palm_height // 2

    palm = [
        (palm_left, palm_bottom),
        (palm_right, palm_bottom),
        (palm_right, palm_top),
        (palm_left, palm_top),
    ]

    return thumb, finger, palm


##### LOCATION HELPERS #####

def polygons_overlap(poly1, poly2):
    path1 = mpath.Path(poly1)
    path2 = mpath.Path(poly2)

    for point in poly1:
        if path2.contains_point(point):
            return True
    for point in poly2:
        if path1.contains_point(point):
            return True
    return False


def closest_polygon_points(poly1, poly2):
    min_dist = float('inf')
    closest_pair = (None, None)

    for p1 in poly1:
        for p2 in poly2:
            dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            if dist < min_dist:
                min_dist = dist
                closest_pair = (p1, p2)

    (x1, y1), (x2, y2) = closest_pair
    midpoint = ((x1 + x2) / 2, (y1 + y2) / 2)

    return closest_pair[0], closest_pair[1], midpoint


def random_point_in_polygon(polygon, inside=True):
    path = Path(polygon)
    min_x = min(p[0] for p in polygon)
    max_x = max(p[0] for p in polygon)
    min_y = min(p[1] for p in polygon)
    max_y = max(p[1] for p in polygon)

    for _ in range(100):
        x = random.uniform(min_x, max_x)
        y = random.uniform(min_y, max_y)
        if (inside and path.contains_point((x, y))) or (not inside and not path.contains_point((x, y))):
            return (x, y)

    return None


def bounding_box(points):
    xs, ys = zip(*points)
    return (min(xs), min(ys), max(xs), max(ys))


def should_use_unibrow(bbox1, bbox2, max_diff=75):
    top_diff = abs(bbox1[1] - bbox2[1])

    return top_diff < max_diff


def point_in_polygon(x, y, polygon):
    inside = False
    px, py = polygon[-1]

    for cx, cy in polygon:
        if ((cy > y) != (py > y)) and (x < (px - cx) * (y - cy) / (py - cy + 1e-10) + cx):
            inside = not inside
        px, py = cx, cy

    return inside


def is_polygon_inside_blob(polygon, blob):
    return all(point_in_polygon(x, y, blob) for x, y in polygon)


def offset_points(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]


def bounding_boxes_collide(box1, box2):
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2

    return not (
            x1_max < x2_min or
            x1_min > x2_max or
            y1_max < y2_min or
            y1_min > y2_max
    )


##### SHAPE MODIFIERS #####

def chaikin_smooth(points, iterations=2):
    for _ in range(iterations):
        new_points = []
        for i in range(len(points)):
            p0 = points[i]
            p1 = points[(i + 1) % len(points)]
            Q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            R = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_points.extend([Q, R])
        points = new_points
    return points


def rotate_point(x, y, cx, cy, angle_rad):
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    dx = x - cx
    dy = y - cy
    return (
        cx + dx * cos_a - dy * sin_a,
        cy + dx * sin_a + dy * cos_a
    )


def bezier_quadratic(t, p0, p1, p2):
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
    return (x, y)


def transform_points(points, angle_deg=0, current_origin=(0, 0), new_origin=(0, 0), zoom=1.0):
    angle_rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

    cx, cy = current_origin
    nx, ny = new_origin
    dx, dy = nx - cx, ny - cy

    transformed = []
    for x, y in points:
        sx, sy = x + dx, y + dy
        tx, ty = sx - nx, sy - ny
        tx *= zoom
        ty *= zoom
        rx = tx * cos_a - ty * sin_a
        ry = tx * sin_a + ty * cos_a
        transformed.append((rx + nx, ry + ny))
    return transformed


def extend_canvas_if_needed(img, bbox):
    min_x, min_y, max_x, max_y = bbox
    old_w, old_h = img.size

    extra_left = max(0, -int(min_x))
    extra_top = max(0, -int(min_y))
    extra_right = max(0, int(max_x - old_w))
    extra_bottom = max(0, int(max_y - old_h))

    if extra_left or extra_top or extra_right or extra_bottom:
        new_w = old_w + extra_left + extra_right
        new_h = old_h + extra_top + extra_bottom

        new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        new_img.paste(img, (extra_left, extra_top))

        offset = (extra_left, extra_top)
        return new_img, offset
    else:
        return img, (0, 0)


def generate_thonk(file_name, seed):
    random.seed(seed)

    size = (512, 512)
    img = Image.new("RGBA", size, (0, 0, 0, 0))

    center = (size[0] // 2, size[1] // 2)
    radius = 180

    features = []
    extra_features = []

    # FACE
    face = generate_blob(center, radius)
    face = chaikin_smooth(face, 5)
    features.append((face, YELLOW))
    mouth_blob = None

    # EYES
    inside = True
    if random.randint(1, 20) == 20:
        inside = False

    eye1, eye2 = generate_eyes(face, inside)
    while bounding_boxes_collide(bounding_box(eye1), bounding_box(eye2)):
        eye1, eye2 = generate_eyes(face, inside)
    eyes = [eye1, eye2]

    if not inside:
        mx = sum(x for x, _ in eye1) / len(eye1)
        my = sum(y for _, y in eye1) / len(eye1)

        eye_blob1 = generate_blob((mx, my), 90)
        eye_blob1 = chaikin_smooth(eye_blob1, iterations=5)
        extra_features.append((eye_blob1, YELLOW))

        mx = sum(x for x, _ in eye2) / len(eye2)
        my = sum(y for _, y in eye2) / len(eye2)

        eye_blob2 = generate_blob((mx, my), 90)
        eye_blob2 = chaikin_smooth(eye_blob2, iterations=5)
        extra_features.append((eye_blob2, YELLOW))

    # MOUTH
    mood = random.choice(["neutral", "smile", "frown", "open smile", "open frown"])
    inner = None
    if mood == "neutral":
        mouth = generate_mouth(eyes)
    elif mood in ["open smile", "open frown"]:
        mouth = generate_open_mouth(eyes, mood.split(" ")[1])
    else:
        mouth, inner = generate_closed_mouth(eyes, mood)

    if not is_polygon_inside_blob(mouth, face):
        mx = sum(x for x, _ in mouth) / len(mouth)
        my = sum(y for _, y in mouth) / len(mouth)

        mouth_blob = generate_blob((mx, my), 90)
        mouth_blob = chaikin_smooth(mouth_blob, iterations=5)
        extra_features.append((mouth_blob, YELLOW))
    features.append((mouth, BROWN))
    if inner:
        features.append((inner, YELLOW))

    for eye in eyes:
        eye = chaikin_smooth(eye, iterations=5)
        features.append((eye, BROWN))

    # EYEBROWS
    bbox1 = bounding_box(eyes[0])
    bbox2 = bounding_box(eyes[1])
    if should_use_unibrow(bbox1, bbox2):
        max_left_1 = min(x for x, _ in eye1)
        max_left_2 = min(x for x, _ in eye2)
        if max_left_1 > max_left_2:
            eye1, eye2 = eye2, eye1
        max_eye_1 = min(y for _, y in eye1)
        max_eye_2 = min(y for _, y in eye2)
        if max_eye_1 < max_eye_2:
            higher_eye = "left"
        else:
            higher_eye = "right"
        brow = generate_unibrow(bbox1, bbox2)

        low_y_brow = (0, 0)
        high_y_brow = (float("inf"), float("inf"))
        for x, y in brow:
            if y > low_y_brow[1]:
                low_y_brow = (x, y)
            if y < high_y_brow[1]:
                high_y_brow = (x, y)
        if low_y_brow[0] < high_y_brow[0]:
            higher_brow = "right"
        else:
            higher_brow = "left"

        if higher_eye != higher_brow:
            x_values = [x for x, y in brow]
            center_x = (min(x_values) + max(x_values)) / 2
            brow = [(2 * center_x - x, y) for x, y in brow]

        features.append((brow, BROWN))

    else:
        eyebrow = generate_eyebrow(bbox1)
        eyebrow2 = generate_eyebrow(bbox2)
        features.append((eyebrow, BROWN))
        features.append((eyebrow2, BROWN))

    # HAND
    lowest = face
    if mouth_blob:
        lowest = mouth_blob

    low_point = (0, 0)
    for point in lowest:
        if point[1] > low_point[1]:
            low_point = point

    thumb, finger, palm = generate_hand()
    thumb = chaikin_smooth(thumb, iterations=2)
    finger = chaikin_smooth(finger, iterations=2)
    palm_top_og = [(palm[0][0], palm[0][1] - 30), (palm[1][0], palm[1][1] - 30), palm[2], palm[3]]
    palm = chaikin_smooth(palm, iterations=3)

    base_point = (256, 256)
    angle = random.uniform(-30, 30)
    zoom = random.uniform(0.4, 1)

    thumb = transform_points(thumb, angle_deg=angle, current_origin=base_point, new_origin=low_point, zoom=zoom)
    finger = transform_points(finger, angle_deg=angle, current_origin=base_point, new_origin=low_point, zoom=zoom)
    palm = transform_points(palm, angle_deg=angle, current_origin=base_point, new_origin=low_point, zoom=zoom)
    palm_top = transform_points(palm_top_og, angle_deg=angle, current_origin=base_point, new_origin=low_point, zoom=zoom)

    palm_box = bounding_box(palm_top)
    palm_width = palm_box[2] - palm_box[0]
    palm_height = palm_box[3] - palm_box[1]

    new_point = (low_point[0] - palm_width / 2, low_point[1] - palm_height / 2)

    thumb = transform_points(thumb, current_origin=low_point, new_origin=new_point)
    finger = transform_points(finger, current_origin=low_point, new_origin=new_point)
    palm = transform_points(palm, current_origin=low_point, new_origin=new_point)
    palm_top = transform_points(palm_top, current_origin=low_point, new_origin=new_point)

    features.append((finger, ORANGE))
    features.append((thumb, ORANGE))
    features.append((palm_top, ORANGE))
    features.append((palm, ORANGE))

    for feature in extra_features:
        points = feature[0]
        overlap = polygons_overlap(face, points)
        if not overlap:
            p1, p2, mid = closest_polygon_points(face, points)
            bridge = generate_blob(mid, 90)
            bridge = chaikin_smooth(bridge, iterations=5)
            features.insert(0, (bridge, YELLOW))
        features.insert(0, (points, feature[1]))

    final_points = []
    for feature in features:
        for point in feature[0]:
            final_points.append((point))

    final_bbox = bounding_box(final_points)

    img, offset = extend_canvas_if_needed(img, final_bbox)
    draw = ImageDraw.Draw(img)

    for feature in features:
        points = feature[0]
        if offset != (0, 0):
            dx, dy = offset
            points = offset_points(feature[0], dx, dy)
        draw.polygon(points, fill=feature[1])

    img = img.resize((256, 256), resample=Image.LANCZOS)
    img.save(file_name)
