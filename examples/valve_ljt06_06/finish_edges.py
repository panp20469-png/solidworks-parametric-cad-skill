"""限定本图纸的法兰背面铸造过渡及加工端面外缘，避免全局选边。"""
import math
from sw_client import _get

def circle(edge):
    c=_get(edge,'GetCurve')
    if not _get(c,'IsCircle'):return None
    p=list(_get(c,'CircleParams'))
    return [x*1000 for x in p[:3]],p[6]*1000

def apply(sw,p,mode):
    doc=sw._active_doc();doc.ClearSelection2(True)
    x=-p['port_axis_offset'];z=p['port_height'];inner=p['port_half_length']-p['port_flange_thickness']
    chosen=[]
    for edge in _get(doc.GetBodies2(0,False)[0],'GetEdges'):
        cp=circle(edge);take=False
        if mode!='machined_perimeters' and cp:
            c,r=cp
            middle=abs(c[0]-x)<1e-6 and abs(c[2]-z)<1e-6
            if mode=='c-root':take=middle and abs(c[1]-inner)<1e-6 and abs(r-p['c_neck_diameter']/2)<1e-6
            if mode=='d-root':take=middle and abs(c[1]+inner)<1e-6 and abs(r-p['d_neck_diameter']/2)<1e-6
            if mode=='d-back':take=middle and abs(c[1]+inner)<1e-6 and abs(r-p['d_flange_diameter']/2)<1e-6
            if mode=='c-back':take=abs(abs(c[0]-x)-p['c_hole_pitch']/2)<1e-6 and abs(c[2]-z)<1e-6 and abs(c[1]-inner)<1e-6 and abs(r-p['ear_radius'])<1e-6
        elif mode=='machined_perimeters':
            pts=[]
            for key in ('GetStartVertex','GetEndVertex'):
                v=_get(edge,key)
                if v is not None:pts.append([q*1000 for q in _get(v,'GetPoint')])
            if cp:
                c,r=cp
                base=abs(abs(c[0])-(p['base_width']/2-p['base_corner_radius']))<1e-6 and abs(abs(c[1])-(p['base_width']/2-p['base_corner_radius']))<1e-6 and abs(r-p['base_corner_radius'])<1e-6 and any(abs(c[2]-v)<1e-6 for v in (0,p['base_thickness']))
                top=abs(c[2]-p['total_height'])<1e-6 and abs(r-p['body_diameter']/2)<1e-6
                excluded=[p['port_bore_diameter']/2+p['chamfer'],(p['ear_thread_major']-5*math.sqrt(3)*p['ear_thread_pitch']/8)/2+p['chamfer']]
                port=abs(abs(c[1])-p['port_half_length'])<1e-6 and all(abs(r-a)>1e-6 for a in excluded)
                take=base or top or port
            elif len(pts)==2:
                base=any(all(abs(q[2]-v)<1e-6 for q in pts) for v in (0,p['base_thickness'])) and any(all(abs(abs(q[a])-p['base_width']/2)<1e-6 for q in pts) for a in (0,1))
                port=any(all(abs(q[1]-v)<1e-6 for q in pts) for v in (-p['port_half_length'],p['port_half_length']))
                take=base or port
        if take:
            assert edge.Select4(True,_get(doc.SelectionManager,'CreateSelectData'))
            chosen.append(cp)
    expected={'c-root':1,'d-root':1,'d-back':4,'c-back':2}
    if mode in expected:assert len(chosen)==expected[mode],(mode,len(chosen))
    else:assert len(chosen)>=25,(mode,len(chosen))
    before=sw.get_mass_properties()['volume_mm3']
    result=sw.chamfer(p['chamfer'],45) if mode=='machined_perimeters' else sw.fillet(p['casting_fillet_radius'],mode in ('c-back','d-back'))
    faces=_get(doc.FeatureByName(result['feature']),'GetFaces') or []
    after=sw.get_mass_properties()['volume_mm3']
    assert faces and abs(after-before)>1e-6
    if mode=='machined_perimeters':assert after<before
    assert not sw.check_geometry()['errors']
    doc.ClearSelection2(True)
    return {**result,'selected_edges':len(chosen),'generated_faces':len(faces),'volume_before_mm3':before,'volume_after_mm3':after}
