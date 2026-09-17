from __future__ import annotations

import hashlib
import json
import math
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_elbow_v10_spec as build
from sw_client import _get


OUT = Path(__file__).resolve().parent / 'output'


def attach():
    sw = build.TargetClient()
    sw.connect(False, False)
    pid = build.verify_visible_instance(sw)
    doc = sw._active_doc()
    if Path(_get(doc, 'GetPathName')).resolve() != build.OUT_SLDPRT.resolve():
        raise RuntimeError('Target document mismatch')
    sw.target_title = _get(doc, 'GetTitle')
    return sw, doc, pid


def measure(doc):
    bodies = doc.GetBodies2(0, False)
    if len(bodies) != 1:
        raise RuntimeError('Expected one solid body')
    faces = list(_get(bodies[0], 'GetFaces'))
    rows = []
    for index, face in enumerate(faces):
        surf = _get(face, 'GetSurface')
        row = {'index': index, 'box_mm': [v * 1000 for v in _get(face, 'GetBox')]}
        for kind, method in [('Cylinder', 'CylinderParams'), ('Plane', 'PlaneParams'), ('Torus', 'TorusParams')]:
            if _get(surf, 'Is' + kind):
                row.update(kind=kind, parameters_si=list(_get(surf, method)))
                break
        rows.append(row)
    return faces, rows


def capture(sw, doc, name, state):
    doc.ClearSelection2(True)
    doc.ViewZoomtofit2()
    doc.GraphicsRedraw2()
    time.sleep(0.4)
    path = OUT / ('verified_' + name + '.bmp')
    result = sw.capture_screenshot(str(path))
    return {'path': str(path), 'state': state, 'capture': result,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dimensional_checks(rows, spec):
    checks = []
    tolerance = spec['verification']['linear_tolerance']

    def check(name, actual, expected):
        passed = actual is not None and abs(actual-expected) <= tolerance
        checks.append({'item': name, 'actual': actual, 'expected': expected,
                       'status': 'PASS' if passed else 'FAIL'})

    def cylinders(axis, radius):
        return [r['parameters_si'] for r in rows if r.get('kind') == 'Cylinder'
                and abs(abs(build.dot(r['parameters_si'][3:6], axis))-1) < 1e-7
                and abs(r['parameters_si'][6]*1000-radius) < tolerance]

    def diameter(name, axis, expected):
        found = cylinders(axis, expected/2)
        check(name, found[0][6]*2000 if found else None, expected)
        return found

    vertical, front = (0, 1, 0), (0, 0, 1)
    upper, branch = (-2**-.5, 2**-.5, 0), (3**.5/2, .5, 0)
    main, top, side, boss, base = (spec[k] for k in ['main_tube','top_flange','side_branch','front_boss','base'])
    for label, axis in [('lower', vertical), ('upper', upper)]:
        diameter('main_'+label+'_outer', axis, main['outer_diameter'])
        diameter('main_'+label+'_inner', axis, main['inner_diameter'])
    torus = [r['parameters_si'] for r in rows if r.get('kind') == 'Torus' and abs(r['parameters_si'][7]-.02)<1e-7]
    check('bend_path_radius', torus[0][6]*1000 if torus else None, main['path']['arc_radius'])
    check('bend_center_height', torus[0][1]*1000 if torus else None, main['path']['arc_center'][1])
    holes = diameter('base_hole_diameter', vertical, base['mounting_holes']['diameter'])
    centers = sorted(set((round(p[0]*1000,5),round(p[2]*1000,5)) for p in holes))
    check('base_hole_count',len(centers),base['mounting_holes']['count'])
    for axis_index,key in [(0,'pitch_x'),(1,'pitch_z')]:
        vals=[p[axis_index] for p in centers]
        check('base_'+key,max(vals)-min(vals) if vals else None,base['mounting_holes'][key])
    diameter('base_corner_diameter',vertical,2*base['corner_radius'])
    bottom=[r for r in rows if r.get('kind')=='Plane' and abs(r['parameters_si'][1])>.999 and abs(r['parameters_si'][4])<1e-7]
    if len(bottom)==1:
        box=bottom[0]['box_mm']
        check('base_width',box[3]-box[0],base['width'])
        check('base_depth',box[5]-box[2],base['depth'])
    else:
        check('base_bottom_face',None,1)
    for label,axis,expected in [('B_body',upper,top['body_diameter']),('B_ear',upper,2*top['lug_radius']),('B_transition',upper,2*top['transition_radius']),('side_outer',branch,side['outer_diameter']),('side_bore',branch,side['inner_diameter']),('C_middle',branch,2*side['flange']['center_radius']),('C_ear',branch,2*side['flange']['ear_radius']),('front_outer',front,boss['outer_diameter']),('front_bore',front,boss['bore_diameter'])]:
        diameter(label,axis,expected)
    bore=cylinders(front,boss['bore_diameter']/2)
    check('front_axis_height',bore[0][1]*1000 if bore else None,boss['center_height'])
    bholes=diameter('B_hole_diameter',upper,top['hole_diameter'])
    check('B_hole_count',len(bholes),top['hole_count'])
    choles=cylinders(branch,2.5)
    check('C_tap_drill_count',len(choles),side['flange']['hole_count'])
    check('C_hole_pitch',abs(choles[0][2]-choles[1][2])*1000 if len(choles)==2 else None,side['flange']['hole_pitch'])
    # 实际平面沿法向的距离，不使用生成器记录的端点作为测量值。
    def plane_offsets(axis,origin):
        return sorted(set(round(build.dot(tuple(p[i+3]-origin[i] for i in range(3)),axis)*1000,6)
                          for r in rows if r.get('kind')=='Plane'
                          for p in [r['parameters_si']] if abs(abs(build.dot(p[:3],axis))-1)<1e-7))
    sy=side['axis_center_height']/1000
    cp=plane_offsets(branch,(side['axis_origin_x']/1000,sy,0))
    for name,expected in [('C_back_datum_distance',side['visible_pipe_length']),('C_front_datum_distance',side['visible_pipe_length']+side['flange']['thickness'])]:
        check(name,min(cp,key=lambda v:abs(v-expected)) if cp else None,expected)
    bp=plane_offsets(upper,(0,0,0))
    check('B_thickness',max(bp)-min(bp) if len(bp)==2 else None,top['thickness'])
    fp=plane_offsets(front,(0,0,0))
    check('front_face_to_main_axis',min(fp,key=lambda v:abs(v-boss['outer_face_to_main_axis'])) if fp else None,boss['outer_face_to_main_axis'])
    yp=plane_offsets(vertical,(0,0,0))
    check('base_thickness',min(yp,key=lambda v:abs(v-base['thickness'])) if yp else None,base['thickness'])
    return checks


def main():
    sw, doc, pid = attach()
    faces, rows = measure(doc)
    result = {'pid': pid, 'document': _get(doc, 'GetPathName'), 'body_count': 1,
              'spec_sha256': hashlib.sha256(build.SPEC_PATH.read_bytes()).hexdigest(),
              'faces': rows, 'views': {}, 'drawing_match': 'UNVERIFIED'}
    spec=json.loads(build.SPEC_PATH.read_text(encoding='utf-8'))
    result['dimensions']=dimensional_checks(rows,spec)
    result['geometry']=sw.check_geometry()
    sw.remove_section_view()
    # 用实际端面法向定向，不以等轴测外观代替端视验收。
    for name, normal, point in [('B', (-2**-0.5, 2**-0.5, 0), (-.032573593, .087071068, 0)),
                                ('C', (3**0.5/2, .5, 0), (.0268467875, .0655, 0))]:
        choices = []
        for row in rows:
            if row.get('kind') != 'Plane':
                continue
            p = row['parameters_si']
            if abs(abs(build.dot(p[:3], normal))-1) < 1e-7 and abs(build.dot(tuple(p[i+3]-point[i] for i in range(3)), normal)) < 1e-6:
                choices.append(row['index'])
        if len(choices) != 1:
            raise RuntimeError(f'{name}: expected one end face, found {choices}')
        doc.ClearSelection2(True)
        faces[choices[0]].Select4(False, _get(doc.SelectionManager, 'CreateSelectData'))
        activated = doc.Extension.RunCommand(169, '')
        time.sleep(.4)
        matrix = list(_get(_get(doc.ActiveView, 'Orientation3'), 'ArrayData'))
        result['views'][name] = capture(sw, doc, name, {'face_index': choices[0], 'normal_to_result': activated, 'matrix': matrix})
    for name, plane, offset, view in [('front_section', 'Front Plane', 0, 'front'),
                                       ('AA', 'Top Plane', 20, 'top'),
                                       ('front_boss_section', 'Right Plane', 0, 'right')]:
        sw.remove_section_view()
        section = sw.create_section_view(plane, offset)
        state = sw.set_view_orientation(view)
        result['views'][name] = capture(sw, doc, name, {'section': section, 'orientation': state})
    sw.remove_section_view()
    result['views']['iso'] = capture(sw, doc, 'iso', sw.set_view_orientation('isometric'))
    result['distinct_view_hashes']=len({v['sha256'] for v in result['views'].values()})==len(result['views'])
    (OUT / 'independent_geometry_audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'face_count': len(rows), 'views': list(result['views']), 'pid': pid,
                      'checks':len(result['dimensions']), 'failed':[r for r in result['dimensions'] if r['status']!='PASS']}))


if __name__ == '__main__':
    main()
