"""
3D 交互式 BIM 查看器

生成基于 Three.js 的 HTML 页面，功能：
  • 加载所有 BIM 构件并渲染 3D 场景
  • 点击构件 → 右侧面板显示工程量信息
  • 修改数量/单价 → 联动更新模型
  • 支持鼠标拖拽旋转、滚轮缩放、右键平移
  • 分类显示/隐藏构件

使用方式：Viewer().generate(manager, output_path)
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple


class Viewer3D:
    """Three.js 交互式 BIM 查看器"""

    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<title>机电BIM 3D 查看器 | 量模一体化</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; font-family: "Microsoft YaHei", -apple-system, sans-serif; }
  #container { position: absolute; top: 0; left: 0; right: 360px; bottom: 0; background: #1a1a2e; }
  #panel {
    position: absolute; top: 0; right: 0; width: 360px; height: 100%;
    background: #16213e; color: #e8e8e8; padding: 16px; overflow-y: auto;
    border-left: 2px solid #0f3460;
  }
  #panel h1 { font-size: 18px; color: #e94560; margin-bottom: 8px; }
  #panel h2 { font-size: 14px; color: #53a8b6; margin: 16px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #0f3460; }
  .info-card { background: #0f3460; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
  .info-card .name { font-size: 15px; font-weight: bold; color: #e94560; margin-bottom: 8px; }
  .info-card .row { display: flex; justify-content: space-between; padding: 3px 0; font-size: 13px; }
  .info-card .row .label { color: #a0a0a0; }
  .info-card .row .value { color: #ffffff; font-weight: 500; }
  .empty-hint { color: #555; font-size: 12px; text-align: center; padding: 20px; }
  input[type="number"] {
    width: 120px; padding: 6px 8px; background: #1a1a2e; color: #fff;
    border: 1px solid #0f3460; border-radius: 4px; font-size: 13px;
  }
  button {
    padding: 8px 16px; background: #e94560; color: #fff; border: none;
    border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;
  }
  button:hover { background: #d63651; }
  .toggle-group { display: flex; flex-wrap: wrap; gap: 6px; }
  .toggle-btn {
    padding: 6px 12px; background: #0f3460; font-size: 12px; border-radius: 14px;
  }
  .toggle-btn.active { background: #53a8b6; }
  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat-box { background: #0f3460; padding: 10px; border-radius: 6px; text-align: center; }
  .stat-box .num { font-size: 20px; color: #53a8b6; font-weight: bold; }
  .stat-box .lbl { font-size: 11px; color: #a0a0a0; margin-top: 3px; }
  .hint { font-size: 11px; color: #888; margin-top: 12px; line-height: 1.6; }
</style>
</head>
<body>
<div id="container"></div>
<div id="panel">
  <h1>🏗️ 机电 BIM 3D 查看器</h1>
  <div class="stat-grid" id="stats"></div>

  <h2>📦 构件分类显示</h2>
  <div class="toggle-group" id="toggles"></div>

  <h2>🎯 选中构件信息</h2>
  <div id="selected-info" class="empty-hint">← 点击左侧3D场景中的构件查看详细信息</div>

  <h2>📝 修改工程量（联动更新）</h2>
  <div id="edit-area" class="info-card" style="display:none;">
    <div class="row"><span class="label">修改数量:</span>
      <input type="number" id="new-quantity" step="0.01" min="0" />
    </div>
    <div class="row" style="margin-top:8px;"><span class="label">修改单价:</span>
      <input type="number" id="new-price" step="0.01" min="0" />
    </div>
    <div style="margin-top:12px; text-align:center;">
      <button onclick="applyQuantityEdit()">🔄 确认修改</button>
    </div>
  </div>

  <h2>📊 变更日志</h2>
  <div id="change-log" class="empty-hint">暂无变更</div>

  <div class="hint">
    💡 操作提示：<br/>
    • 左键拖动：旋转视角<br/>
    • 右键拖动：平移画面<br/>
    • 滚轮：缩放视图<br/>
    • 点击构件：选中并查看工程量
  </div>
</div>

<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
  }
}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ============ 数据：从Python注入 ============
const MODEL_DATA = __MODEL_DATA__;

// ============ 三维场景初始化 ============
const container = document.getElementById('container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);
scene.fog = new THREE.Fog(0x1a1a2e, 20, 200);

const camera = new THREE.PerspectiveCamera(
  60, container.clientWidth / container.clientHeight, 0.1, 2000
);
camera.position.set(15, 12, 15);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.shadowMap.enabled = true;
container.appendChild(renderer.domElement);

// 光照
const ambient = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambient);
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(10, 20, 10);
dirLight.castShadow = true;
scene.add(dirLight);
const fillLight = new THREE.DirectionalLight(0x8888ff, 0.3);
fillLight.position.set(-10, 5, -10);
scene.add(fillLight);

// 地面 + 网格
const groundGeo = new THREE.PlaneGeometry(100, 100);
const groundMat = new THREE.MeshPhongMaterial({ color: 0x0f3460, side: THREE.DoubleSide });
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.01;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(100, 40, 0x53a8b6, 0x1f4068);
grid.position.y = 0;
scene.add(grid);

// 控制器
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(0, 1, 0);

// ============ 构件渲染 ============
const componentMeshes = [];       // [THREE.Mesh]
const componentDataMap = new Map(); // object3D.uuid -> 构件原始数据
const typeMeshes = {};            // type -> [mesh]
let selectedMesh = null;
let selectedComponent = null;
const changes = [];

// 类型颜色
const typeColors = {
  'cabinet': 0xe94560,
  'equipment': 0xf39c12,
  'distribution_box': 0x53a8b6,
  'fixture': 0xff6b6b,
  'switch': 0xffb3ba,
  'socket': 0xffd6a5,
  'lighting': 0xffff00,
  'cable': 0x2d6a4f,
  'cable_tray': 0x95a5a6,
  'pipe': 0x8d6e63,
  'other': 0x888888,
};

function hexToColor(hexStr) {
  // 可能是 '#rrggbb' 或 '0xrrggbb'
  if (!hexStr) return 0x888888;
  const h = hexStr.replace('#', '0x');
  try { return parseInt(h); } catch { return 0x888888; }
}

function buildComponents() {
  if (!MODEL_DATA || !MODEL_DATA.components) return;

  for (const comp of MODEL_DATA.components) {
    const type = comp.type;
    const dims = comp.dimensions;
    const pos = comp.position;
    const attrs = comp.attributes || {};
    const w = Math.max(0.05, dims.width || dims[0] || 0.5);
    const d = Math.max(0.05, dims.depth || dims[1] || 0.5);
    const h = Math.max(0.05, dims.height || dims[2] || 0.5);

    let mesh;
    const color = (attrs && attrs.color) ? hexToColor(attrs.color) : (typeColors[type] || 0x888888);

    if (type === 'cable' || type === 'pipe') {
      // 圆柱体
      const radius = Math.max(0.02, d / 2);
      const geo = new THREE.CylinderGeometry(radius, radius, w, 12);
      const mat = new THREE.MeshPhongMaterial({ color, shininess: 80 });
      mesh = new THREE.Mesh(geo, mat);
      mesh.rotation.z = Math.PI / 2;  // 水平放置
      mesh.position.set(pos.x, pos.z || 0, pos.y);
    } else {
      // 立方体
      const geo = new THREE.BoxGeometry(w, h, d);
      const mat = new THREE.MeshPhongMaterial({ color, shininess: 60 });
      mesh = new THREE.Mesh(geo, mat);
      // 中心放在地面以上
      mesh.position.set(pos.x, h / 2 + (pos.z || 0), pos.y);
    }

    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData = { componentId: comp.id, component: comp, baseColor: color };

    // 添加标签线
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(mesh.position.x, mesh.position.y + h, mesh.position.z),
      new THREE.Vector3(mesh.position.x, mesh.position.y + h + 0.5, mesh.position.z),
    ]);
    const line = new THREE.Line(lineGeo, new THREE.LineBasicMaterial({ color: 0xffffff, opacity: 0.3, transparent: true }));

    scene.add(mesh);
    scene.add(line);
    componentMeshes.push(mesh);
    componentDataMap.set(mesh.uuid, comp);
    if (!typeMeshes[type]) typeMeshes[type] = [];
    typeMeshes[type].push(mesh);
  }

  // 自动调整相机
  if (componentMeshes.length > 0) {
    const box = new THREE.Box3();
    for (const m of componentMeshes) box.expandByObject(m);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    controls.target.set(center.x, center.y, center.z);
    const dist = maxDim * 1.8 + 5;
    camera.position.set(center.x + dist, center.y + dist * 0.7, center.z + dist);
  }

  renderStats();
  renderToggles();
}

// ============ 选中 / 点击 ============
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

function onPointerDown(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(componentMeshes, false);
  if (intersects.length > 0) {
    selectMesh(intersects[0].object);
  } else {
    clearSelection();
  }
}
renderer.domElement.addEventListener('pointerdown', onPointerDown);

function selectMesh(mesh) {
  // 恢复之前的颜色
  if (selectedMesh) {
    selectedMesh.material.color.setHex(selectedMesh.userData.baseColor);
    selectedMesh.material.emissive.setHex(0x000000);
  }
  selectedMesh = mesh;
  selectedMesh.material.emissive.setHex(0x222222);
  selectedMesh.material.color.lerp(new THREE.Color(0xffffff), 0.4);

  const comp = componentDataMap.get(mesh.uuid);
  selectedComponent = comp;
  renderSelectedInfo(comp);
}

function clearSelection() {
  if (selectedMesh) {
    selectedMesh.material.color.setHex(selectedMesh.userData.baseColor);
    selectedMesh.material.emissive.setHex(0x000000);
  }
  selectedMesh = null;
  selectedComponent = null;
  document.getElementById('selected-info').innerHTML =
    '<div class="empty-hint">← 点击3D场景中的构件查看工程量</div>';
  document.getElementById('edit-area').style.display = 'none';
}

// ============ 面板渲染 ============
function renderStats() {
  const total = MODEL_DATA.components.length;
  const byType = {};
  for (const c of MODEL_DATA.components) {
    byType[c.type] = (byType[c.type] || 0) + 1;
  }
  const types = Object.keys(byType).length;
  document.getElementById('stats').innerHTML = `
    <div class="stat-box"><div class="num">${total}</div><div class="lbl">构件总数</div></div>
    <div class="stat-box"><div class="num">${types}</div><div class="lbl">构件类型</div></div>
    <div class="stat-box"><div class="num">${MODEL_DATA.total_cost ? MODEL_DATA.total_cost.toLocaleString() : '-'}</div><div class="lbl">总造价</div></div>
    <div class="stat-box"><div class="num">${(MODEL_DATA.bind_coverage * 100).toFixed(0)}%</div><div class="lbl">量模绑定</div></div>
  `;
}

function renderToggles() {
  const byType = {};
  for (const c of MODEL_DATA.components) {
    byType[c.type] = (byType[c.type] || 0) + 1;
  }
  const typeNames = {
    cabinet: '配电柜', equipment: '设备', distribution_box: '配电箱',
    fixture: '开关/插座', switch: '开关', socket: '插座', lighting: '照明',
    cable: '线缆', cable_tray: '桥架', pipe: '配管', other: '其他',
  };
  const container = document.getElementById('toggles');
  container.innerHTML = '';
  const allBtn = document.createElement('button');
  allBtn.className = 'toggle-btn active';
  allBtn.textContent = `全部 (${MODEL_DATA.components.length})`;
  allBtn.onclick = () => {
    for (const m of componentMeshes) m.visible = true;
    document.querySelectorAll('.toggle-btn').forEach(b => b.classList.add('active'));
  };
  container.appendChild(allBtn);

  for (const [t, n] of Object.entries(byType)) {
    const btn = document.createElement('button');
    btn.className = 'toggle-btn active';
    btn.textContent = `${typeNames[t] || t} (${n})`;
    btn.dataset.type = t;
    btn.onclick = () => {
      const show = !btn.classList.contains('hidden-now');
      const meshes = typeMeshes[t] || [];
      for (const m of meshes) m.visible = !show;
      btn.classList.toggle('active', show);
      btn.classList.toggle('hidden-now', !show);
    };
    container.appendChild(btn);
  }
}

function renderSelectedInfo(comp) {
  const attrs = comp.attributes || {};
  const q = attrs.quantity ?? '-';
  const up = attrs.unit_price ?? '-';
  const tp = attrs.total_price ?? '-';
  document.getElementById('selected-info').innerHTML = `
    <div class="info-card">
      <div class="name">${comp.name}</div>
      <div class="row"><span class="label">类型:</span><span class="value">${comp.type}</span></div>
      <div class="row"><span class="label">位置 (x, y, z):</span><span class="value">(${comp.position.x.toFixed(2)}, ${comp.position.y.toFixed(2)}, ${comp.position.z.toFixed(2)})</span></div>
      <div class="row"><span class="label">尺寸 (宽×深×高):</span><span class="value">${(comp.dimensions.width||comp.dimensions[0]||0).toFixed(2)} × ${(comp.dimensions.depth||comp.dimensions[1]||0).toFixed(2)} × ${(comp.dimensions.height||comp.dimensions[2]||0).toFixed(2)} m</span></div>
      <div class="row"><span class="label">数量:</span><span class="value">${q}${attrs.unit || ''}</span></div>
      <div class="row"><span class="label">单价:</span><span class="value">¥${up}</span></div>
      <div class="row"><span class="label">合价:</span><span class="value">¥${typeof tp === 'number' ? tp.toLocaleString() : tp}</span></div>
      <div class="row"><span class="label">构件ID:</span><span class="value" style="font-size:11px;">${comp.id.substring(0,18)}...</span></div>
      ${attrs.quantity_id ? `<div class="row"><span class="label">工程量ID:</span><span class="value" style="font-size:11px;">${attrs.quantity_id.substring(0,18)}...</span></div>` : ''}
    </div>
  `;
  document.getElementById('edit-area').style.display = 'block';
  document.getElementById('new-quantity').value = typeof q === 'number' ? q : (typeof q === 'string' ? parseFloat(q) || 0 : 0);
  document.getElementById('new-price').value = typeof up === 'number' ? up : (typeof up === 'string' ? parseFloat(up) || 0 : 0);
}

window.applyQuantityEdit = function() {
  if (!selectedComponent) return;
  const newQ = parseFloat(document.getElementById('new-quantity').value);
  const newP = parseFloat(document.getElementById('new-price').value);
  if (isNaN(newQ)) return;
  const attrs = selectedComponent.attributes || {};
  const oldQ = attrs.quantity || 0;
  const oldP = attrs.unit_price || 0;
  attrs.quantity = newQ;
  attrs.unit_price = newP;
  attrs.total_price = Math.round(newQ * newP * 100) / 100;
  changes.push({
    time: new Date().toLocaleTimeString(),
    name: selectedComponent.name,
    old: oldQ,
    new: newQ,
    price: newP,
    total: attrs.total_price,
  });
  renderSelectedInfo(selectedComponent);
  renderChangeLog();
  // 视觉反馈：闪烁
  if (selectedMesh) {
    selectedMesh.material.emissive.setHex(0x53a8b6);
    setTimeout(() => selectedMesh.material.emissive.setHex(0x222222), 300);
  }
};

function renderChangeLog() {
  const container = document.getElementById('change-log');
  if (changes.length === 0) {
    container.innerHTML = '<div class="empty-hint">暂无变更</div>';
    return;
  }
  container.innerHTML = changes.slice(-10).reverse().map(c => `
    <div class="info-card" style="padding:8px; margin-bottom:6px;">
      <div style="font-size:12px; color:#53a8b6;">${c.time}</div>
      <div style="font-size:12px; margin-top:4px;">${c.name}</div>
      <div style="font-size:12px; color:#e94560; margin-top:4px;">数量: ${c.old} → ${c.new}，合价: ¥${c.total.toLocaleString()}</div>
    </div>
  `).join('');
}

// ============ 响应式 ============
window.addEventListener('resize', () => {
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
});

// ============ 动画循环 ============
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

// ============ 启动 ============
buildComponents();
animate();
</script>
</body>
</html>
"""

    def __init__(self):
        pass

    def generate(
        self,
        model_manager,
        output_path: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成3D查看器HTML

        Args:
            model_manager: ModelManager 实例（包含构件和绑定）
            output_path: 输出的HTML文件路径
            extra_data: 可选的额外数据（如算量总价、审核状态等）
        """
        # 构件数据 + 几何信息（颜色等通过BIMGenerator附加）
        components_data = model_manager.export_to_dict()

        # 计算总造价
        total_cost = 0.0
        for comp in model_manager.components:
            if isinstance(comp.attributes, dict):
                tp = comp.attributes.get('total_price')
                if isinstance(tp, (int, float)):
                    total_cost += tp

        binding_report = model_manager.get_binding_report()

        # 合并 extra_data
        model_data = {
            'components': components_data['components'],
            'total_cost': total_cost,
            'bind_coverage': binding_report['coverage'],
            'binding_count': binding_report['components_with_quantity'],
        }
        if extra_data:
            model_data.update(extra_data)

        json_str = json.dumps(model_data, ensure_ascii=False, default=str)
        html = self.HTML_TEMPLATE.replace('__MODEL_DATA__', json_str)

        dir_name = os.path.dirname(output_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path


class SimpleViewerDataBuilder:
    """
    快速构建查看器数据的辅助工具 —— 不依赖ModelManager
    """
    @staticmethod
    def from_components(components, geometries):
        """直接从 BIMComponent 和 Geometry3D 列表构建数据"""
        result = []
        for comp in components:
            comp_id = comp.id if hasattr(comp, 'id') else str(id(comp))
            geom = geometries.get(comp_id, None) if isinstance(geometries, dict) else None
            color = getattr(geom, 'color', None) if geom else None
            data = {
                'id': comp_id,
                'name': comp.name if hasattr(comp, 'name') else '构件',
                'type': comp.type.value if hasattr(comp.type, 'value') else str(comp.type),
                'position': {
                    'x': float(comp.position.x),
                    'y': float(comp.position.y),
                    'z': float(comp.position.z),
                },
                'dimensions': {
                    'width': float(comp.dimensions[0]),
                    'depth': float(comp.dimensions[1]),
                    'height': float(comp.dimensions[2]),
                },
                'attributes': {
                    **(comp.attributes if isinstance(comp.attributes, dict) else {}),
                }
            }
            if color:
                data['attributes']['color'] = color
            result.append(data)
        return result
