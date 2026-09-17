from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_elbow_v10_live as audit
from sw_client import _get
import pythoncom
from win32com.client import VARIANT


def finish_threads(sw):
    doc = sw._active_doc()
    null = VARIANT(pythoncom.VT_DISPATCH, None)
    features = []
    feat = _get(doc, 'FirstFeature')
    while feat:
        if _get(feat, 'GetTypeName2') == 'SweepCut':
            data = _get(feat, 'GetDefinition')
            if abs(_get(data, 'CircularProfileDiameter') - .006) < 1e-8:
                features.append(feat)
        feat = _get(feat, 'GetNextFeature')
    if len(features) != 2:
        raise RuntimeError('Expected exactly two unchanged M6 pilot features; no blind rerun')
    log = {'threads': [], 'representation': '5 mm drilled hole plus M6x1 cosmetic thread'}
    for feat in features:
        name = _get(feat, 'Name')
        data = _get(feat, 'GetDefinition')
        if not data.AccessSelections(doc, null):
            raise RuntimeError('AccessSelections failed: ' + name)
        data.CircularProfileDiameter = .005
        if not feat.ModifyDefinition(data, doc, null):
            raise RuntimeError('ModifyDefinition failed: ' + name)
        sw.rebuild_model()
        log['threads'].append({'hole_feature': name, 'drill_diameter_mm': 5})
    # 仅选 C 外端面的两个底孔圆边，不选择中心通道或主管孔。
    axis = (3**.5/2, .5, 0)
    edges = []
    for face in _get(doc.GetBodies2(0, False)[0], 'GetFaces'):
        surf = _get(face, 'GetSurface')
        if not _get(surf, 'IsCylinder'):
            continue
        p = _get(surf, 'CylinderParams')
        if abs(p[6]-.0025) > 1e-8 or abs(abs(p[2])-.016) > 1e-7:
            continue
        for edge in _get(face, 'GetEdges'):
            curve = _get(edge, 'GetCurve')
            if not _get(curve, 'IsCircle'):
                continue
            circle = _get(curve, 'CircleParams')
            distance = circle[0]*axis[0] + (circle[1]-.05)*axis[1]
            if abs(distance-.031) < 1e-7:
                edges.append(edge)
    if len(edges) != 2:
        raise RuntimeError('Expected two C outer hole edges')
    for index, edge in enumerate(edges):
        doc.ClearSelection2(True)
        if not edge.Select4(False, _get(doc.SelectionManager, 'CreateSelectData')):
            raise RuntimeError('Thread edge selection failed')
        thread = doc.FeatureManager.InsertCosmeticThread3(8, 'Tapped Hole', 'M6x1.0', .006, 2, .006, 'M6x1 THRU')
        if thread is None:
            raise RuntimeError('Cosmetic thread creation failed')
        definition = _get(thread, 'GetDefinition')
        log['threads'][index]['cosmetic_feature'] = _get(thread, 'Name')
        log['threads'][index]['diameter_m'] = _get(definition, 'Diameter')
        log['threads'][index]['callout'] = _get(definition, 'ThreadCallout')
    doc.ClearSelection2(True)
    return log


def main():
    sw, doc, pid = audit.attach()
    log = finish_threads(sw)
    log['pid'] = pid
    log['rebuild'] = sw.rebuild_model()
    log['geometry'] = sw.check_geometry()
    log['saved'] = sw.save_document()
    (audit.OUT / 'finishing_changes.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(log, ensure_ascii=True))


if __name__ == '__main__':
    main()
