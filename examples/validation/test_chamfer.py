import ast, math, unittest
from pathlib import Path
from types import SimpleNamespace
P=Path(__file__).resolve().parents[1]/'elbow/external_sources/Solidworks-MCP-Server/sw_client.py'
tree=ast.parse(P.read_text('utf-8'))
method=next(n for cls in tree.body if isinstance(cls,ast.ClassDef) and cls.name=='SolidWorksClient' for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='chamfer')
ns={'math':math,'Dict':dict,'_m':lambda v:v/1000,'_r':math.radians,'_get':lambda obj,key:getattr(obj,key)()}
exec(compile(ast.Module(body=[method],type_ignores=[]),str(P),'exec'),ns)
class Tests(unittest.TestCase):
    def client(self,result):
        calls=[]
        def insert(*args): calls.append(args); return result
        obj=SimpleNamespace(_active_doc=lambda:SimpleNamespace(FeatureManager=SimpleNamespace(InsertFeatureChamfer=insert)))
        return obj,calls
    def test_nondefault_angle(self):
        obj,calls=self.client(SimpleNamespace(Name='C',GetFaces=lambda:[object()]))
        out=ns['chamfer'](obj,2,30)
        self.assertEqual(calls,[(0,1,.002,math.pi/6,0.,0.,0.,0.)]); self.assertEqual(out['angle_deg'],30)
    def test_invalid_inputs(self):
        for distance,angle in [(0,45),(-1,45),(float('nan'),45),(float('inf'),45),(1,0),(1,90),(1,float('nan'))]:
            with self.subTest(distance=distance,angle=angle):
                obj,calls=self.client(None)
                with self.assertRaises(ValueError): ns['chamfer'](obj,distance,angle)
                self.assertEqual(calls,[])
    def test_failure_has_no_fallback(self):
        obj,calls=self.client(None)
        with self.assertRaises(RuntimeError): ns['chamfer'](obj,1,30)
        self.assertEqual(len(calls),1)
    def test_empty_feature_rejected(self):
        obj,calls=self.client(SimpleNamespace(Name='C',GetFaces=lambda:[]))
        with self.assertRaises(RuntimeError): ns['chamfer'](obj,1)
unittest.main()
