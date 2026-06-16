# -*- coding: utf-8 -*-
"""
DWG -> Revit : Traçage automatique de murs
Approche : fusion des segments colinéaires + déduplication des faces
"""
from pyrevit import forms, revit, script
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from collections import defaultdict, OrderedDict
import math

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
logger = script.get_logger()


def safe_type_name(elem):
    try:
        return Element.Name.GetValue(elem)
    except Exception:
        return str(elem.Id)

def get_cad_transform(cad_link):
    if hasattr(cad_link, "GetTotalTransform"):
        try: return cad_link.GetTotalTransform()
        except Exception: pass
    if isinstance(cad_link.Location, LocationPoint):
        lp = cad_link.Location.Point
        rot = cad_link.Location.Rotation
        t = Transform.CreateTranslation(lp)
        if abs(rot) > 1e-9:
            t = t.Multiply(Transform.CreateRotationAtPoint(XYZ.BasisZ, rot, XYZ.Zero))
        return t
    return Transform.Identity

def get_all_curves(geo_elem, transform=None):
    if transform is None:
        transform = Transform.Identity
    curves = []
    for obj in geo_elem:
        if isinstance(obj, GeometryInstance):
            try:
                curves.extend(get_all_curves(obj.GetInstanceGeometry(), Transform.Identity))
            except Exception:
                pass
        elif isinstance(obj, PolyLine):
            try:
                pts = obj.GetCoordinates()
                gs_id = obj.GraphicsStyleId
                min_len = doc.Application.ShortCurveTolerance * 2.0
                for k in range(len(pts) - 1):
                    p1, p2 = pts[k], pts[k+1]
                    if p1.DistanceTo(p2) < min_len:
                        continue
                    try:
                        curves.append((Line.CreateBound(p1, p2), transform, gs_id))
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("PolyLine ignoree : {}".format(e))
        elif isinstance(obj, Curve):
            curves.append((obj, transform, None))
        elif isinstance(obj, Solid):
            for edge in obj.Edges:
                try:
                    c = edge.AsCurve()
                    if c: curves.append((c, transform, None))
                except Exception:
                    pass
    return curves

def collect_segments_by_layer(all_curves, link_transform):
    segments_by_layer = defaultdict(list)
    for curve, local_trans, gs_id_override in all_curves:
        gs = doc.GetElement(gs_id_override if gs_id_override else curve.GraphicsStyleId)
        if gs is None or gs.GraphicsStyleCategory is None:
            continue
        layer_name = gs.GraphicsStyleCategory.Name.strip()
        try:
            if not curve.IsBound:
                continue
            t = link_transform.Multiply(local_trans)
            p1 = t.OfPoint(curve.GetEndPoint(0))
            p2 = t.OfPoint(curve.GetEndPoint(1))
            if p1.DistanceTo(p2) < 0.01:
                continue
            segments_by_layer[layer_name].append((p1, p2))
        except Exception:
            pass
    return segments_by_layer

def get_active_level():
    view = doc.ActiveView
    if hasattr(view, "GenLevel") and view.GenLevel is not None:
        return view.GenLevel
    levels = FilteredElementCollector(doc).OfClass(Level).ToElements()
    if levels:
        return sorted(levels, key=lambda l: l.Elevation)[0]
    raise Exception("Aucun niveau trouve.")

# ---------------------------------------------------------------------------
# Normalisation de l'angle [0, pi[
# ---------------------------------------------------------------------------
def seg_angle(p1, p2):
    return math.atan2(p2.Y - p1.Y, p2.X - p1.X) % math.pi

def proj(pt, origin, direction):
    return (pt - origin).DotProduct(direction)

def perp_dist(pt, origin, direction):
    v = pt - origin
    return (v - direction.Multiply(v.DotProduct(direction))).GetLength()

# ---------------------------------------------------------------------------
# Fusion des segments colinéaires
# ---------------------------------------------------------------------------
def merge_collinear(segments, angle_tol=0.05, perp_tol=0.15):
    """
    Fusionne tous les segments colinéaires en un seul segment continu.
    angle_tol  : ~3 degrés (assoupli pour murs légèrement hors équerre)
    perp_tol   : ~45mm - distance max pour être sur la même droite (assoupli)
    """
    if not segments:
        return []

    # Grouper par angle
    angle_groups = []
    for p1, p2 in segments:
        angle = seg_angle(p1, p2)
        placed = False
        for ag in angle_groups:
            da = abs(ag[0] - angle)
            if da < angle_tol or abs(da - math.pi) < angle_tol:
                ag[1].append((p1, p2))
                placed = True
                break
        if not placed:
            angle_groups.append([angle, [(p1, p2)]])

    merged = []
    for angle, segs in angle_groups:
        direction = XYZ(math.cos(angle), math.sin(angle), 0.0)

        # Grouper par ligne (colinéarité)
        line_groups = []
        for p1, p2 in segs:
            placed = False
            for lg in line_groups:
                ref = lg[0][0]
                if (perp_dist(p1, ref, direction) < perp_tol and
                        perp_dist(p2, ref, direction) < perp_tol):
                    lg.append((p1, p2))
                    placed = True
                    break
            if not placed:
                line_groups.append([(p1, p2)])

        # Fusionner chaque ligne
        for lg in line_groups:
            origin = lg[0][0]
            params = []
            for p1, p2 in lg:
                params.append(proj(p1, origin, direction))
                params.append(proj(p2, origin, direction))
            t_min = min(params)
            t_max = max(params)
            if t_max - t_min < 0.01:
                continue
            start = origin + direction.Multiply(t_min)
            end   = origin + direction.Multiply(t_max)
            merged.append((start, end))

    return merged

# ---------------------------------------------------------------------------
# Déduplication des faces parallèles proches (doublon de mur)
# ---------------------------------------------------------------------------
def deduplicate_walls(segments, max_face_dist_ft=1.15, min_face_dist_ft=0.01):
    """
    Détecte les paires de segments parallèles proches (deux faces d'un mur)
    et les remplace par leur ligne centrale.
    max_face_dist_ft : épaisseur max du mur (~350mm = 1.15 pi)
    """
    used   = [False] * len(segments)
    result = []

    for i in range(len(segments)):
        if used[i]:
            continue
        p1, p2  = segments[i]
        angle1  = seg_angle(p1, p2)
        dir1    = XYZ(math.cos(angle1), math.sin(angle1), 0.0)
        len_i   = p1.DistanceTo(p2)
        best_j, best_dist = None, max_face_dist_ft

        for j in range(i+1, len(segments)):
            if used[j]:
                continue
            q1, q2 = segments[j]
            angle2 = seg_angle(q1, q2)
            da = abs(angle1 - angle2)
            if da > 0.05 and abs(da - math.pi) > 0.05:
                continue

            # Distance perpendiculaire
            dist = (perp_dist(q1, p1, dir1) + perp_dist(q2, p1, dir1)) / 2.0
            if dist < min_face_dist_ft or dist > max_face_dist_ft:
                continue

            # Chevauchement
            tq1 = proj(q1, p1, dir1)
            tq2 = proj(q2, p1, dir1)
            if tq1 > tq2: tq1, tq2 = tq2, tq1
            ovlp = max(0.0, min(len_i, tq2) - max(0.0, tq1))
            if ovlp < 0.1:
                continue

            if dist < best_dist:
                best_dist, best_j = dist, j

        if best_j is not None:
            q1, q2 = segments[best_j]
            # Ligne centrale = union des deux segments
            all_t = [proj(p1, p1, dir1), proj(p2, p1, dir1),
                     proj(q1, p1, dir1), proj(q2, p1, dir1)]
            t_min = min(all_t)
            t_max = max(all_t)
            # Offset perpendiculaire vers q
            v    = q1 - p1
            perp = v - dir1.Multiply(v.DotProduct(dir1))
            off  = perp.Multiply(0.5)
            result.append((
                p1 + dir1.Multiply(t_min) + off,
                p1 + dir1.Multiply(t_max) + off
            ))
            used[i] = used[best_j] = True
        else:
            result.append((p1, p2))
            used[i] = True

    return result

# ---------------------------------------------------------------------------
# Création des murs
# ---------------------------------------------------------------------------
def create_walls(doc, segments, wall_type, level,
                 height_m=3.0, max_len_m=30.0, min_len_mm=400.0):
    height     = UnitUtils.ConvertToInternalUnits(height_m,   UnitTypeId.Meters)
    max_len_ft = UnitUtils.ConvertToInternalUnits(max_len_m,  UnitTypeId.Meters)
    min_len_ft = UnitUtils.ConvertToInternalUnits(min_len_mm, UnitTypeId.Millimeters)
    lev_z      = level.Elevation

    # Filtrer par longueur
    filtered = [(p1,p2) for p1,p2 in segments
                if min_len_ft <= p1.DistanceTo(p2) <= max_len_ft]
    logger.debug("{} segs -> {} apres filtre longueur (min={:.0f}mm)".format(
        len(segments), len(filtered), min_len_mm))

    # Fusionner les colinéaires
    merged = merge_collinear(filtered)
    logger.debug("{} apres fusion colineaire".format(len(merged)))

    # Dédupliquer les faces
    deduped = deduplicate_walls(merged)
    logger.debug("{} apres deduplication".format(len(deduped)))

    # Alerte diagnostic
    forms.alert(
        "Calque traité :\n"
        "Segments bruts   : {}\n"
        "Après filtre len : {}\n"
        "Après fusion     : {}\n"
        "Après dédup      : {}".format(
            len(segments), len(filtered), len(merged), len(deduped))
    )

    count = 0
    for p1, p2 in deduped:
        try:
            c1 = XYZ(p1.X, p1.Y, lev_z)
            c2 = XYZ(p2.X, p2.Y, lev_z)
            if c1.DistanceTo(c2) < 0.01:
                continue
            w = Wall.Create(doc, Line.CreateBound(c1, c2),
                            wall_type.Id, level.Id, height, 0.0, False, False)
            if w:
                try:
                    WallUtils.DisallowWallJoinAtEnd(w, 0)
                    WallUtils.DisallowWallJoinAtEnd(w, 1)
                except Exception:
                    pass
                count += 1
        except Exception as e:
            logger.warning("Mur ignore : {}".format(e))
    return count

# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------
def run_script():
    try:
        ref      = uidoc.Selection.PickObject(ObjectType.Element,
                                              "Selectionnez le lien CAD (DWG)")
        cad_link = doc.GetElement(ref.ElementId)
    except Exception:
        return

    link_transform = get_cad_transform(cad_link)

    try:
        all_layers = sorted([
            sub.Name.strip()
            for sub in cad_link.Category.SubCategories
            if sub.Name and sub.Name.strip()
        ])
    except Exception as e:
        forms.alert("Impossible de lire les calques.\n{}".format(e))
        return

    if not all_layers:
        forms.alert("Aucun calque trouve.")
        return

    mapping = OrderedDict([
        ("1 - Murs Exterieurs", {"layers": [], "type_obj": None}),
        ("2 - Murs Interieurs", {"layers": [], "type_obj": None}),
    ])

    for cat_name, data in mapping.items():
        chosen_layers = forms.SelectFromList.show(
            all_layers, title="Calques CAD -> {}".format(cat_name), multiselect=True)
        data["layers"] = chosen_layers or []
        if not data["layers"]:
            continue
        wall_types   = FilteredElementCollector(doc).OfClass(WallType).ToElements()
        name_to_type = {safe_type_name(t): t for t in wall_types}
        chosen_name  = forms.SelectFromList.show(
            sorted(name_to_type.keys()),
            title="Type de mur -> {}".format(cat_name), multiselect=False)
        data["type_obj"] = name_to_type.get(chosen_name)

    opt = Options()
    opt.DetailLevel = ViewDetailLevel.Fine
    opt.IncludeNonVisibleObjects = True
    try:
        all_curves = get_all_curves(cad_link.get_Geometry(opt), Transform.Identity)
    except Exception as e:
        forms.alert("Erreur geometrie : {}".format(e))
        return

    if not all_curves:
        forms.alert("Aucune courbe trouvee.")
        return

    segments_by_layer = collect_segments_by_layer(all_curves, link_transform)

    diag = ["Segments bruts par calque :"]
    for name in sorted(segments_by_layer.keys()):
        diag.append("  {} : {}".format(name, len(segments_by_layer[name])))
    forms.alert("\n".join(diag))

    try:
        level = get_active_level()
    except Exception as e:
        forms.alert(str(e))
        return

    walls_count = 0
    with revit.Transaction("DWG -> Murs Revit"):
        for cat_name, data in mapping.items():
            if not data["type_obj"] or not data["layers"]:
                continue
            for layer in data["layers"]:
                segs = segments_by_layer.get(layer, [])
                n    = create_walls(doc, segs, data["type_obj"], level)
                walls_count += n
                logger.debug("{} | {} -> {} murs".format(cat_name, layer, n))

    forms.alert("Termine !\nMurs crees : {}".format(walls_count))

if __name__ == "__main__":
    run_script()