"""Triangle intersection checks used by local geometry review."""
import numpy as np
eps=1e-6

def cross2(a, b):
    return float(a[0] * b[1] - a[1] * b[0])

def projected_clip(A, B, drop):
    A = np.delete(A, drop, axis=1)
    B = np.delete(B, drop, axis=1)
    orientation = np.sign(cross2(B[1] - B[0], B[2] - B[0]))
    if orientation == 0:
        return None
    poly = list(A)
    for i in range(3):
        aa = B[i]
        edge = B[(i + 1) % 3] - aa
        new = []
        if not poly:
            break
        for (p, q) in zip(poly, poly[1:] + poly[:1]):
            dp = orientation * cross2(edge, p - aa)
            dq = orientation * cross2(edge, q - aa)
            if dp >= 0:
                new.append(p)
            if (dp >= 0) != (dq >= 0):
                new.append(p + (q - p) * dp / (dp - dq))
        poly = new
    return np.asarray(poly)

def polygon_area(poly):
    if poly is None or len(poly) < 3:
        return 0.0
    p = poly - poly.mean(0)
    return 0.5 * abs(sum((cross2(a, b) for (a, b) in zip(p, np.roll(p, -1, axis=0)))))

def cut(T, d):
    points = [T[i] for i in range(3) if abs(d[i]) < 1e-12]
    for (i, j) in ((0, 1), (1, 2), (2, 0)):
        if d[i] * d[j] < 0:
            points.append(T[i] + (T[j] - T[i]) * d[i] / (d[i] - d[j]))
    return np.asarray(points)

def intersection(A, B):
    na = np.cross(A[1] - A[0], A[2] - A[0])
    nb = np.cross(B[1] - B[0], B[2] - B[0])
    la = np.linalg.norm(na)
    lb = np.linalg.norm(nb)
    if min(la, lb) < 1e-12:
        return None
    na /= la
    nb /= lb
    da = (A - B[0]) @ nb
    db = (B - A[0]) @ na
    if da.min() > eps or da.max() < -eps or db.min() > eps or (db.max() < -eps):
        return None
    axis = int(np.argmax(abs(na) + abs(nb)))
    overlap = projected_clip(A, B, axis)
    if overlap is not None and len(overlap) == 0:
        return None
    line = np.cross(na, nb)
    line_length = np.linalg.norm(line)
    separation = max(abs(da).max(), abs(db).max())
    if line_length < 1e-05 and separation <= eps:
        area = polygon_area(overlap)
        if area <= eps * eps:
            return None
        kind = 'coplanar_overlap' if line_length < 1e-08 and separation < 1e-09 else 'near_coplanar_contact'
        return {'kind': kind, 'projected_overlap_area_mm2': area, 'maximum_plane_distance_mm': float(separation)}
    if line_length < 1e-12:
        return None
    aa = cut(A, da)
    bb = cut(B, db)
    if len(aa) == 0 or len(bb) == 0:
        return None
    line /= line_length
    ta = aa @ line
    tb = bb @ line
    size = min(ta.max(), tb.max()) - max(ta.min(), tb.min())
    if size <= eps:
        return None
    strict = da.min() < -eps and da.max() > eps and (db.min() < -eps) and (db.max() > eps)
    return {'kind': 'transverse_crossing' if strict else 'edge_or_near_plane_contact', 'intersection_length_mm': float(size)}
