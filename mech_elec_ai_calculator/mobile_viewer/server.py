"""
移动端轻量化模型 + 查看端口 (模块4)
========================================

核心功能:
  • 3D 轻量化生成器 (Simple JSON / glTF)
  • ProjectRepository 项目仓库（内存）
  • FastAPI REST API
  • 移动端 HTML 查看器 (PWA-ready)

API Endpoints:
  GET  /api/health
  GET  /api/projects
  GET  /api/projects/{id}
  GET  /api/projects/{id}/components
  GET  /api/projects/{id}/quantities
  POST /api/projects/{id}/materials_split
  GET  /api/projects/{id}/reports/{report_type}
  POST /api/projects/{id}/reports/{report_type}/submit_erp
  GET  /                              (移动端主页)
  GET  /viewer/{id}                   (3D 查看器 HTML)

运行: python -m mech_elec_ai_calculator.mobile_viewer.server
或  : uvicorn mech_elec_ai_calculator.mobile_viewer.server:app
"""
import os
import json
import sys
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from common.models import BIMComponent, CalculationResult


# ============ 3D 轻量化生成器 ============
class LightweightModelGenerator:
    """
    把 BIM 构件转成轻量化 JSON (custom 格式)
    用于: 移动端 HTML 直接消费 Three.js 绘制

    数据结构: { components: [{id, name, type, position{x,y,z}, dimensions{w,d,h}, color, quantity, total_price, unit}] }
    """

    COLOR_MAP = {
        'cabinet': '#FF6B6B',
        'distribution_box': '#FFD93D',
        'equipment': '#6BCB77',
        'fixture': '#4D96FF',
        'cable': '#845EC2',
        'cable_tray': '#A3A380',
        'pipe': '#FF9F45',
        'other': '#CCCCCC',
    }

    def generate_simplified_json(self, components: List[BIMComponent], output_path: str):
        out = []
        for comp in components:
            t = comp.type.value if hasattr(comp.type, 'value') else str(comp.type)
            attrib = comp.attributes if isinstance(comp.attributes, dict) else {}

            dim = list(comp.dimensions) if isinstance(comp.dimensions, (list, tuple)) else [1, 1, 1]
            w = dim[0] if len(dim) > 0 else 1
            d = dim[1] if len(dim) > 1 else 1
            h = dim[2] if len(dim) > 2 else 1

            out.append({
                'id': comp.id,
                'name': comp.name,
                'type': t,
                'position': {'x': float(comp.position.x),
                             'y': float(comp.position.y),
                             'z': float(comp.position.z)},
                'dimensions': {'w': float(w), 'd': float(d), 'h': float(h)},
                'color': self.COLOR_MAP.get(t, '#CCCCCC'),
                'quantity': attrib.get('quantity', 0),
                'total_price': attrib.get('total_price', 0),
                'unit': attrib.get('unit', ''),
                'unit_price': attrib.get('unit_price', 0),
                'quantity_id': comp.quantity_id,
            })

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({'components': out, 'total_count': len(out),
                       'generated_at': datetime.now().isoformat()},
                      f, ensure_ascii=False, indent=2)
        return output_path

    def generate_from_repo(self, components: List[BIMComponent], output_dir: str) -> str:
        path = os.path.join(output_dir, f"model_lightweight_{len(components)}_{datetime.now().strftime('%Y%m%d%H%M')}.json")
        return self.generate_simplified_json(components, path)


# ============ 项目仓储 (内存存储) ============
class ProjectRepository:
    """项目仓库 —— 简化版内存存储，
    实际生产环境应替换为数据库 (SQLAlchemy)。

    data structure:
        { id: str, name: str, code: str, drawing: optional, components: [],
          calculation: Optional[CalculationResult], reports: dict }
    """

    def __init__(self):
        self._projects: Dict[str, Dict[str, Any]] = {}

    def add_project(self, name: str, code: str = "") -> str:
        pid = str(uuid4())
        self._projects[pid] = {
            'id': pid,
            'name': name,
            'code': code,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'drawing': None,
            'components': [],
            'calculation': None,
            'reports': {},
        }
        return pid

    def get_all(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': p['id'],
                'name': p['name'],
                'code': p['code'],
                'created_at': p['created_at'],
                'component_count': len(p['components']),
            }
            for p in self._projects.values()
        ]

    def get(self, pid: str) -> Optional[Dict[str, Any]]:
        return self._projects.get(pid)

    def set_drawing(self, pid, drawing_data):
        if pid in self._projects:
            self._projects[pid]['drawing'] = drawing_data

    def set_calculation(self, pid, calc: CalculationResult):
        if pid in self._projects:
            self._projects[pid]['calculation'] = calc

    def set_components(self, pid: str, components: List[BIMComponent]):
        if pid in self._projects:
            self._projects[pid]['components'] = components

    def add_report(self, pid: str, report_type: str, report):
        if pid in self._projects:
            self._projects[pid]['reports'][report_type] = report


# ============ 移动端 HTML 生成器 ============
def generate_mobile_html(pid: str, name: str, components_count: int = 0) -> str:
    """生成移动端 3D 查看器 HTML (Three.js)"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>{name} - 3D BIM 查看器</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, sans-serif; color: #333; background: #1a1a2e; overflow: hidden; }}
#container {{ position: absolute; top: 0; left: 0; right: 0; bottom: 280px; }}
#panel {{ position: absolute; bottom: 0; left: 0; right: 0; height: 280px; background: #fff; padding: 12px;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.15); overflow-y: auto; }}
#panel h3 {{ margin: 0 0 8px 0; font-size: 16px; color: #333; }}
#panel .row > div {{ padding: 4px 0; font-size: 13px; }}
#panel .label {{ color: #888; }}
#panel .val {{ font-weight: 500; }}
#panel .actions {{ display: flex; gap: 8px; margin-top: 10px; }}
.btn {{ flex: 1; padding: 10px; background: #667eea; color: #fff; border: 0; border-radius: 8px; font-size: 13px; }}
.btn.btn-secondary {{ background: #888; }}
header {{ position: fixed; top: 0; left: 0; right: 0; background: rgba(255,255,255,0.95); padding: 10px 15px; z-index: 10; }}
</style>
</head>
<body>
<div id="container"></div>
<header>{name}</header>
<div id="panel">
  <h3>📌 点击构件查看工程量</h3>
  <div class="row">
    <div>选中: <span class="val" id="info_name">未选择</span></div>
    <div><span class="label">构件类型: <span class="val" id="info_type">-</span></span></div>
    <div><span class="label">数量: <span class="val" id="info_qty">-</span></span></div>
    <div><span class="label">单价: <span class="val" id="info_price">-</span></span></div>
    <div><span class="label">合价: <span class="val" id="info_total">-</span></span></div>
    <div class="actions">
      <button class="btn" onclick="alert('查看工程量清单: /api/projects/{pid}/quantities')">查看清单</button>
      <button class="btn btn-secondary" onclick="location.href='/'">返回</button>
    </div>
  </div>
</div>

<script src="https://unpkg.com/three@0.150.0/build/three.min.js"></script>
<script src="https://unpkg.com/three@0.150.0/examples/js/controls/OrbitControls.js"></script>
<script>
let components = [];
let selectedMesh = null;
let camera, scene, renderer, controls;
let raycaster, mouse;

function init() {{
  const container = document.getElementById('container');
  camera = new THREE.PerspectiveCamera(75, container.clientWidth / (container.clientHeight || 1), 0.1, 5000);
  camera.position.set(120, 120, 120);

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1a2e);

  renderer = new THREE.WebGLRenderer({{ antialias: true }});
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(50, 100, 50);
  scene.add(dirLight);

  const gridHelper = new THREE.GridHelper(500, 50, 0x667eea, 0x334477);
  scene.add(gridHelper);

  raycaster = new THREE.Raycaster();
  mouse = new THREE.Vector2();

  fetch(`/api/projects/{pid}/components`).then(r => r.json()).then(data => {{
    components = data.components;
    for (let comp of components) {{
      let geo, mat, mesh;
      let col = comp.color || '#CCCCCC';
      if (comp.type === 'cable' || comp.type === 'pipe') {{
        geo = new THREE.CylinderGeometry(Math.max(3, comp.dimensions.w * 0.1 || 3), Math.max(3, comp.dimensions.h * 0.1 || 3));
      }} else {{
        geo = new THREE.BoxGeometry(1, 1, 1);
        let sx = Math.max(1, comp.dimensions.w * 0.5 || 10);
        let sy = Math.max(1, comp.dimensions.h * 0.5 || 10);
        let sz = Math.max(1, comp.dimensions.d * 0.5 || 10);
        geo.scale(sx, sy, sz);
      }}
      mat = new THREE.MeshPhongMaterial({{ color: col, opacity: 0.95, transparent: true }});
      mesh = new THREE.Mesh(geo, mat);
      mesh.position.x = comp.position.x * 0.1 || 0;
      mesh.position.z = comp.position.y * 0.1 || 0;
      mesh.position.y = comp.position.z * 0.1 || 0;
      mesh.userData = comp;
      scene.add(mesh);
    }}
    if (components.length > 0) {{
      const box = new THREE.Box3().setFromObject(scene);
      const center = box.getCenter(new THREE.Vector3());
      camera.position.set(center.x + 120, center.y + 80, center.z + 100);
      controls.target.copy(center);
    }}
    animate();
  }});

  renderer.domElement.addEventListener('click', onClick);
}}

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}}

function onClick(event) {{
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(scene.children, true);
  if (intersects.length > 0) {{
    if (selectedMesh) selectedMesh.material.emissive = new THREE.Color(0x000000);
    selectedMesh = intersects[0].object;
    selectedMesh.material.emissive = new THREE.Color(0xff6b6b);
    const comp = selectedMesh.userData;
    document.getElementById('info_name').innerText = comp.name;
    document.getElementById('info_type').innerText = comp.type;
    document.getElementById('info_qty').innerText = (comp.quantity || 0) + ' ' + (comp.unit || '');
    document.getElementById('info_price').innerText = '¥' + (comp.unit_price || 0);
    document.getElementById('info_total').innerText = '¥' + (comp.total_price || 0);
  }}
}}

window.addEventListener('resize', () => {{
  const container = document.getElementById('container');
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
}});

init();
</script>
</body>
</html>"""


# ============ REST API Server ============
def create_app(repository: Optional[ProjectRepository] = None):
    """创建 FastAPI 应用 (Web)"""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse
    except ImportError:
        print("请先安装: pip install fastapi uvicorn")
        raise

    app = FastAPI(title="BIM 移动端轻量化查看器")
    repo = repository or ProjectRepository()

    @app.get('/api/health')
    def health_check():
        return {"status": "ok", "service": "BIM Mobile Viewer"}

    @app.get('/api/projects')
    def list_projects():
        projects = repo.get_all()
        return {"projects": projects, "count": len(projects)}

    @app.get('/api/projects/{pid}')
    def get_project(pid: str):
        p = repo.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {"id": p['id'], 'name': p['name'], 'code': p['code'], 'created_at': p['created_at']}

    @app.get('/api/projects/{pid}/components')
    def list_components(pid: str):
        p = repo.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail="项目不存在")
        comp_list = []
        for c in p['components']:
            t = c.type.value if hasattr(c.type, 'value') else str(c.type)
            dim = list(c.dimensions) if isinstance(c.dimensions, (list, tuple)) else [1, 1, 1]
            w = dim[0] if len(dim) > 0 else 1
            d = dim[1] if len(dim) > 1 else 1
            h = dim[2] if len(dim) > 2 else 1
            attrib = c.attributes if isinstance(c.attributes, dict) else {}
            comp_list.append({
                'id': c.id,
                'name': c.name,
                'type': t,
                'position': {'x': c.position.x, 'y': c.position.y, 'z': c.position.z},
                'dimensions': {'w': w, 'd': d, 'h': h},
                'color': LightweightModelGenerator.COLOR_MAP.get(t, '#CCCCCC'),
                'quantity': attrib.get('quantity', 0),
                'total_price': attrib.get('total_price', 0),
                'unit': attrib.get('unit', ''),
                'unit_price': attrib.get('unit_price', 0),
                'quantity_id': c.quantity_id,
            })
        return {"project_id": pid, "components": comp_list, "count": len(comp_list)}

    @app.get('/api/projects/{pid}/quantities')
    def list_quantities(pid: str):
        p = repo.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail="项目不存在")
        calc = p.get('calculation')
        if not calc:
            raise HTTPException(status_code=404, detail="该项目还没有算量结果")

        all_items = (getattr(calc, 'devices', []) or []) + (getattr(calc, 'cables', []) or [])
        all_items += (getattr(calc, 'trunkings', []) or []) + (getattr(calc, 'pipes', []) or [])
        all_items += (getattr(calc, 'accessories', []) or [])
        total_cost = sum((it.total_price or 0) for it in all_items)

        def to_dict(item):
            return {
                'id': item.id, 'code': getattr(item, 'code', ''), 'name': item.name,
                'quantity': item.quantity, 'unit': item.unit,
                'unit_price': item.unit_price, 'total_price': item.total_price,
                'category': getattr(item, 'category', '')
            }

        return {
            "project_id": pid,
            "total_cost": total_cost,
            "devices": [to_dict(x) for x in getattr(calc, 'devices', []) or []],
            "cables": [to_dict(x) for x in getattr(calc, 'cables', []) or []],
            "trunkings": [to_dict(x) for x in getattr(calc, 'trunkings', []) or []],
            "pipes": [to_dict(x) for x in getattr(calc, 'pipes', []) or []],
            "accessories": [to_dict(x) for x in getattr(calc, 'accessories', []) or []],
        }

    @app.post('/api/projects/{pid}/materials_split')
    def split_materials(pid: str):
        p = repo.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail="项目不存在")
        calc = p.get('calculation')
        if not calc:
            raise HTTPException(status_code=404, detail="该项目还没有算量结果")

        from material_labor_split import MaterialLaborSplitter
        result = MaterialLaborSplitter().split(calc)

        def to_split(x):
            return {
                'item_id': x.item_id, 'name': x.name, 'quantity': x.quantity,
                'unit': x.unit, 'unit_price': x.unit_price,
                'total_price': x.total_price, 'supply_type': x.supply_type,
                'labor_amount': x.labor_amount, 'material_amount': x.material_amount,
                'labor_ratio': x.labor_ratio, 'material_ratio': x.material_ratio,
            }

        return {
            "project_id": pid,
            "summary": result.summary,
            "split": {
                "owner_equipment": [to_split(x) for x in result.owner_equipment],
                "owner_materials": [to_split(x) for x in result.owner_materials],
                "contractor": [to_split(x) for x in result.contractor],
                "labor": [to_split(x) for x in result.labor]
            }
        }

    @app.get('/api/projects/{pid}/reports/{report_type}')
    def get_report(pid: str, report_type: str = 'SETTLEMENT_V1'):
        p = repo.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail="项目不存在")
        calc = p.get('calculation')
        if not calc:
            raise HTTPException(status_code=404, detail="该项目还没有算量结果")

        from settlement_report import SettlementReportGenerator
        rgen = SettlementReportGenerator()
        report = rgen.generate_from_calc(
            calc, report_type=report_type,
            project_name=p['name'], project_code=p['code']
        )
        return {
            "report_id": report.report_id,
            "project_name": report.project_name,
            "project_code": report.project_code,
            "period_start": report.period_start,
            "period_end": report.period_end,
            "total_amount": report.summary.get('total_amount', 0),
            "summary": report.summary,
            "rows": [
                {
                    'row_id': r.row_id, 'item_id': r.item_id,
                    'code': r.code, 'name': r.name, 'unit': r.unit,
                    'quantity': r.quantity, 'unit_price': r.unit_price,
                    'total_price': r.total_price, 'supply_type': r.supply_type,
                    'notes': r.notes,
                }
                for r in report.rows
            ]
        }

    @app.post('/api/projects/{pid}/reports/{report_type}/submit_erp')
    def submit_erp(pid: str, report_type: str = 'SETTLEMENT_V1'):
        p = repo.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail="项目不存在")
        calc = p.get('calculation')
        if not calc:
            raise HTTPException(status_code=404, detail="该项目还没有算量结果")

        from settlement_report import SettlementReportGenerator, ERPClient
        rgen = SettlementReportGenerator()
        report = rgen.generate_from_calc(calc, report_type=report_type,
                                         project_name=p['name'], project_code=p['code'])
        client = ERPClient('csv', {'output_dir': './outputs/mobile_erp'})
        result = client.submit(report)
        return {'report_id': report.report_id, 'project_id': pid, 'ok': result.get('ok'), 'erp_response': result}

    @app.get('/', response_class=HTMLResponse)
    def root():
        projects = repo.get_all()
        html = "<!DOCTYPE html><html lang='zh-CN'><head>"
        html += "<meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        html += "<title>BIM 移动端轻量化查看器</title>"
        html += "<style>body { font-family:-apple-system,sans-serif;margin:0;background:#f5f5f5;" \
                "color:#333;}header { background: linear-gradient(135deg,#667eea,#764ba2);" \
                "color:#fff;padding:20px 15px;box-shadow:0 3px 8px rgba(0,0,0,0.15);}" \
                "h1 { margin:0 0 8px 0;font-size:22px;}.subtitle{font-size:12px;opacity:0.9;}" \
                ".container{padding:16px;max-width:768px;margin:0 auto;}" \
                ".card{background:#fff;border-radius:12px;padding:14px;margin-bottom:12px;" \
                "box-shadow:0 2px 6px rgba(0,0,0,0.1);}" \
                ".card h2{margin:0 0 8px 0;font-size:16px;}" \
                ".card .meta{color:#888;font-size:12px;margin-bottom:10px;}" \
                ".actions{display:flex;gap:8px;flex-wrap:wrap;}" \
                ".btn{background:#667eea;color:#fff;padding:10px 18px;border-radius:8px;" \
                "text-decoration:none;font-size:13px;font-weight:500;text-align:center;" \
                "flex:1;min-width:80px;}.btn-secondary{background:#333;}" \
                ".btn-gray{background:#888;}.empty{text-align:center;color:#aaa;padding:40px 20px;}" \
                "</style></head><body><header>" \
                "<h1>🏗️ BIM 移动端查看器</h1><div class='subtitle'>工程量查询 / 3D 模型 / 结算报表</div>" \
                "</header><div class='container'>"

        if not projects:
            html += "<div class='empty'>暂无项目，请先在服务器注册项目</div>"
        else:
            for p in projects:
                html += f"<div class='card'><h2>{p['name']}</h2>"
                html += f"<div class='meta'>项目编码: {p['code']}</div>"
                html += f"<div class='meta'>构件数: {p['component_count']}</div>"
                html += "<div class='actions'>"
                html += f"<a class='btn' href='/viewer/{p['id']}'>3D 查看</a>"
                html += f"<a class='btn btn-secondary' href='/api/projects/{p['id']}/quantities'>工程量</a>"
                html += f"<a class='btn btn-gray' href='/api/projects/{p['id']}/reports/SETTLEMENT_V1'>结算报表</a>"
                html += "</div></div>"

        html += "</div></body></html>"
        return HTMLResponse(content=html)

    @app.get('/viewer/{pid}', response_class=HTMLResponse)
    def viewer_3d(pid: str):
        p = repo.get(pid)
        if not p:
            raise HTTPException(status_code=404, detail="项目不存在")
        return HTMLResponse(content=generate_mobile_html(pid, p['name'], len(p['components'])))

    return app


def start_server(port: int = 8000, repository: Optional[ProjectRepository] = None):
    """启动 FastAPI 服务器"""
    try:
        import uvicorn
    except ImportError:
        print("请先安装: pip install fastapi uvicorn")
        sys.exit(1)
    app = create_app(repository)
    print(f"🌐 BIM 移动端 REST API 服务器:")
    print(f"   主页: http://localhost:{port}/")
    print(f"   API: http://localhost:{port}/api/health")
    print(f"   项目列表: http://localhost:{port}/api/projects")
    print()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    start_server()
