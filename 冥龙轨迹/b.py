#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冥龙（DarkCreature）轨迹生成工具
==================================
基于 b.py 的思路，读取冥龙 JSON 数据，支持多种飞行轨迹形状
（圆形、椭圆形、心形、8字形、螺旋形、星形、正弦波），
绕中心点飞行；可自定义路径点数量，自动重编号节点 ID 并更新所有引用关系。

用法:
    python dark_dragon_track.py [输入json] [输出json]
    python dark_dragon_track.py            # 交互模式，默认读取 a.json
"""

import json
import copy
import os
import math
import sys


# ============================================================
# 第一部分：轨迹生成器
# 每个函数返回 [(x, y, z), ...] 列表，共 n 个点
# wave_amp / wave_freq 控制 Y 轴（高度）波浪起伏
# ============================================================

def gen_circle(cx, cy, cz, radius, n, wave_amp=0.0, wave_freq=2):
    """圆形轨迹（水平面）"""
    pts = []
    for i in range(n):
        t = 2.0 * math.pi * i / n
        x = cx + radius * math.cos(t)
        z = cz + radius * math.sin(t)
        y = cy + wave_amp * math.sin(wave_freq * t)
        pts.append((x, y, z))
    return pts


def gen_ellipse(cx, cy, cz, rx, rz, n, wave_amp=0.0, wave_freq=2):
    """椭圆形轨迹"""
    pts = []
    for i in range(n):
        t = 2.0 * math.pi * i / n
        x = cx + rx * math.cos(t)
        z = cz + rz * math.sin(t)
        y = cy + wave_amp * math.sin(wave_freq * t)
        pts.append((x, y, z))
    return pts


def gen_heart(cx, cy, cz, scale, n, wave_amp=0.0, wave_freq=2):
    """心形轨迹（水平面，俯视呈心形）"""
    pts = []
    for i in range(n):
        t = 2.0 * math.pi * i / n
        hx = 16.0 * math.sin(t) ** 3
        hz = (13.0 * math.cos(t) - 5.0 * math.cos(2 * t)
              - 2.0 * math.cos(3 * t) - math.cos(4 * t))
        x = cx + scale * hx
        z = cz + scale * hz
        y = cy + wave_amp * math.sin(wave_freq * t)
        pts.append((x, y, z))
    return pts


def gen_figure8(cx, cy, cz, radius, n, wave_amp=0.0, wave_freq=2):
    """8字形轨迹（双纽线 lemniscate of Gerono）"""
    pts = []
    for i in range(n):
        t = 2.0 * math.pi * i / n
        x = cx + radius * math.cos(t)
        z = cz + radius * math.sin(t) * math.cos(t)
        y = cy + wave_amp * math.sin(wave_freq * t)
        pts.append((x, y, z))
    return pts


def gen_spiral(cx, cy, cz, r_start, r_end, n, height, wave_amp=0.0, wave_freq=2):
    """螺旋形轨迹（半径渐变 + 高度爬升）"""
    pts = []
    for i in range(n):
        t = 2.0 * math.pi * i / n
        r = r_start + (r_end - r_start) * (i / max(n - 1, 1))
        x = cx + r * math.cos(t)
        z = cz + r * math.sin(t)
        y = cy + height * (i / max(n - 1, 1)) + wave_amp * math.sin(wave_freq * t)
        pts.append((x, y, z))
    return pts


def gen_star(cx, cy, cz, r_outer, r_inner, n, wave_amp=0.0, wave_freq=2):
    """星形轨迹（五角星，外径/内径交替）"""
    pts = []
    spikes = 5
    for i in range(n):
        t = 2.0 * math.pi * i / n
        blend = abs(math.cos(spikes / 2.0 * t))
        r = r_inner + (r_outer - r_inner) * blend
        x = cx + r * math.cos(t)
        z = cz + r * math.sin(t)
        y = cy + wave_amp * math.sin(wave_freq * t)
        pts.append((x, y, z))
    return pts


def gen_sine(cx, cy, cz, length, amp, n, h_freq=2, v_amp=0.0, v_freq=2):
    """正弦波形直线轨迹（沿 X 轴前进，Z 轴正弦摆动）"""
    pts = []
    for i in range(n):
        t = i / max(n - 1, 1)
        x = cx - length / 2 + length * t
        z = cz + amp * math.sin(h_freq * math.pi * t)
        y = cy + v_amp * math.sin(v_freq * 2 * math.pi * t)
        pts.append((x, y, z))
    return pts


# 形状注册表: id -> (名称, 生成函数)
SHAPES = {
    '1': ('圆形',     gen_circle),
    '2': ('椭圆形',   gen_ellipse),
    '3': ('心形',     gen_heart),
    '4': ('8字形',    gen_figure8),
    '5': ('螺旋形',   gen_spiral),
    '6': ('星形',     gen_star),
    '7': ('正弦波形', gen_sine),
}


def generate_shape(shape_id, cx, cy, cz, n, wave_amp, wave_freq, params):
    """统一调用入口，根据形状 id 分发到对应生成函数"""
    if shape_id == '1':
        return gen_circle(cx, cy, cz, params[0], n, wave_amp, wave_freq)
    elif shape_id == '2':
        return gen_ellipse(cx, cy, cz, params[0], params[1], n, wave_amp, wave_freq)
    elif shape_id == '3':
        return gen_heart(cx, cy, cz, params[0], n, wave_amp, wave_freq)
    elif shape_id == '4':
        return gen_figure8(cx, cy, cz, params[0], n, wave_amp, wave_freq)
    elif shape_id == '5':
        return gen_spiral(cx, cy, cz, params[0], params[1], n, params[2], wave_amp, wave_freq)
    elif shape_id == '6':
        return gen_star(cx, cy, cz, params[0], params[1], n, wave_amp, wave_freq)
    elif shape_id == '7':
        return gen_sine(cx, cy, cz, params[0], params[1], n, params[2], wave_amp, wave_freq)
    else:
        raise ValueError(f"未知形状: {shape_id}")


# ============================================================
# 第二部分：节点解析与遍历
# ============================================================

NODE_TYPES = ['DarkCreature', 'DarkCreatureParams', 'Rail', 'Marker']


def classify_node(node_data):
    """识别节点类型（根据顶层 key）"""
    for nt in NODE_TYPES:
        if nt in node_data:
            return nt
    return 'Unknown'


def parse_nodes(nodes):
    """
    遍历所有节点，按类型分类。
    返回: {类型: [节点键名列表]}
    """
    classified = {nt: [] for nt in NODE_TYPES}
    for key, data in nodes.items():
        nt = classify_node(data)
        classified.setdefault(nt, []).append(key)
    return classified


def get_node_num(key):
    """从 BstNode_xxx 提取数字部分"""
    return int(key.split('_')[1])


# ============================================================
# 第三部分：引用更新（通用递归）
# ============================================================

def update_references(obj, id_map):
    """
    递归遍历对象，将所有匹配 id_map 的字符串引用替换为新值。
    id_map: {旧BstNode键: 新BstNode键}
    这样不管引用字段叫什么（[CLUMP]params / patrolRail / dataPoints 等）都能正确更新。
    """
    if isinstance(obj, dict):
        for k in obj:
            val = obj[k]
            if isinstance(val, str) and val in id_map:
                obj[k] = id_map[val]
            else:
                update_references(val, id_map)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            val = obj[i]
            if isinstance(val, str) and val in id_map:
                obj[i] = id_map[val]
            else:
                update_references(val, id_map)


def validate_references(nodes):
    """验证所有 BstNode_ 引用是否指向存在的节点，返回错误列表"""
    errors = []
    valid_keys = set(nodes.keys())

    def check(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                check(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check(v, f"{path}[{i}]")
        elif isinstance(obj, str) and obj.startswith('BstNode_'):
            if obj not in valid_keys:
                errors.append(f"{path} -> {obj} (不存在)")

    for key, data in nodes.items():
        check(data, key)
    return errors


# ============================================================
# 第四部分：坐标更新与路径点调整
# ============================================================

def fmt(v):
    """格式化浮点数为字符串（保持与原 JSON 一致的字符串类型）"""
    return f"{v:.6f}"


def update_marker_pos(marker_node, x, y, z):
    """更新 Marker 节点的 pos"""
    marker_node['Marker']['pos'] = [fmt(x), fmt(y), fmt(z), "0.0"]


def update_darkcreature_pos(dc_node, x, y, z):
    """更新 DarkCreature 的 transform 第 4 行（位置）"""
    dc_node['DarkCreature']['transform'][3] = [fmt(x), fmt(y), fmt(z), "1.0"]


def make_marker_node(x, y, z):
    """基于模板创建一个新 Marker 节点"""
    return {
        "Marker": {
            "enabled": True,
            "scale": ["2.0", "2.0", "2.0", "0.0"],
            "quat": ["0.0", "0.0", "0.0", "1.0"],
            "pos": [fmt(x), fmt(y), fmt(z), "0.0"]
        }
    }


def adjust_rail_points(nodes, rail_key, target_count, template_marker_key):
    """
    调整指定 Rail 的路径点数量：
      - target_count > 当前数量: 复制模板 Marker 创建新节点并追加
      - target_count < 当前数量: 从末尾删除多余 Marker
    同时更新 dataPoints.Num 和 [CLUMP]data 列表。
    """
    rail = nodes[rail_key]['Rail']
    dp = rail['dataPoints']
    current_data = dp['[CLUMP]data']
    current_count = len(current_data)

    if target_count == current_count:
        return

    template = copy.deepcopy(nodes[template_marker_key])

    # 计算可用的新 ID（基于现有最大数字 + 1）
    existing_nums = []
    for k in nodes:
        if k.startswith('BstNode_'):
            try:
                existing_nums.append(get_node_num(k))
            except (ValueError, IndexError):
                pass
    next_num = max(existing_nums) + 1 if existing_nums else 1

    if target_count > current_count:
        # 增加路径点
        for i in range(target_count - current_count):
            new_key = f"BstNode_{next_num + i}"
            nodes[new_key] = copy.deepcopy(template)
            current_data.append(new_key)
    else:
        # 删除路径点（从末尾移除）
        for _ in range(current_count - target_count):
            rm_key = current_data.pop()
            if rm_key in nodes:
                del nodes[rm_key]

    dp['Num'] = str(target_count)


# ============================================================
# 第四部分(补): 坐标偏移 (b.py 核心思路)
# 取参考节点 -> 计算所有节点相对偏移 -> 输入新基准坐标 -> 整体平移
# ============================================================

def get_node_pos(node_data):
    """
    提取节点位置 (x, y, z)，兼容两种结构:
      - Marker:         node['Marker']['pos'] = [x, y, z, w]
      - DarkCreature:   node['DarkCreature']['transform'][3] = [x, y, z, w]
      - Rail:           node['Rail']['transform'][3] = [x, y, z, w]
    返回 (x, y, z) 浮点元组，无法提取时返回 None。
    """
    if 'Marker' in node_data:
        p = node_data['Marker']['pos']
        return float(p[0]), float(p[1]), float(p[2])
    for nt in ('DarkCreature', 'Rail'):
        if nt in node_data:
            p = node_data[nt]['transform'][3]
            return float(p[0]), float(p[1]), float(p[2])
    return None


def set_node_pos(node_data, x, y, z):
    """
    写入节点位置，保持原数据类型(字符串)和第4分量不变。
    对 Marker 写 pos，对 DarkCreature/Rail 写 transform[3]。
    """
    if 'Marker' in node_data:
        p = node_data['Marker']['pos']
        p[0] = fmt(x)
        p[1] = fmt(y)
        p[2] = fmt(z)
        return True
    for nt in ('DarkCreature', 'Rail'):
        if nt in node_data:
            p = node_data[nt]['transform'][3]
            p[0] = fmt(x)
            p[1] = fmt(y)
            p[2] = fmt(z)
            return True
    return False


def compute_offsets(nodes, ref_key):
    """
    以 ref_key 为参考节点，计算所有"可定位节点"的相对偏移。
    返回: {节点键: (dx, dy, dz)}
    (与 b.py 完全一致的思路)
    """
    ref_pos = get_node_pos(nodes[ref_key])
    if ref_pos is None:
        raise ValueError(f"参考节点 {ref_key} 无法提取坐标")

    ref_x, ref_y, ref_z = ref_pos
    offsets = {}
    for key, data in nodes.items():
        pos = get_node_pos(data)
        if pos is None:
            continue
        offsets[key] = (pos[0] - ref_x, pos[1] - ref_y, pos[2] - ref_z)
    return offsets, ref_pos


def apply_offset(nodes, offsets, ref_key, new_x, new_y, new_z):
    """
    将偏移应用到新基准坐标上: new_pos = new_base + offset
    遍历所有带偏移的节点并更新坐标 (b.py 核心逻辑)。
    """
    count = 0
    for key, (dx, dy, dz) in offsets.items():
        if key in nodes:
            if set_node_pos(nodes[key], new_x + dx, new_y + dy, new_z + dz):
                count += 1
    return count


def renumber_all(nodes, start_id):
    """
    重编号所有节点 ID，保持原有相对偏移，并更新所有引用。
    例: 原 min=99988801, start_id=10000000
        99988801 -> 10000000, 99988802 -> 10000001, ...
    返回全新的 nodes 字典。
    """
    old_nums = []
    for k in nodes:
        if k.startswith('BstNode_'):
            old_nums.append(get_node_num(k))

    if not old_nums:
        return nodes

    min_num = min(old_nums)

    # 建立旧键 -> 新键 的映射
    id_map = {}
    for k in nodes:
        old_num = get_node_num(k)
        new_num = start_id + (old_num - min_num)
        id_map[k] = f"BstNode_{new_num}"

    # 构建新字典（深拷贝数据）
    new_nodes = {}
    for k in nodes:
        new_nodes[id_map[k]] = copy.deepcopy(nodes[k])

    # 递归更新所有引用
    update_references(new_nodes, id_map)

    return new_nodes


# ============================================================
# 第五部分：交互辅助
# ============================================================

def input_float(prompt, default):
    """输入浮点数，支持默认值"""
    s = input(prompt).strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        print(f"  输入无效，使用默认值 {default}")
        return default


def input_int(prompt, default):
    """输入整数，支持默认值"""
    s = input(prompt).strip()
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        print(f"  输入无效，使用默认值 {default}")
        return default


def get_marker_range(nodes, marker_keys):
    """获取一组 Marker 的坐标范围"""
    xs, ys, zs = [], [], []
    for mk in marker_keys:
        if mk in nodes and 'Marker' in nodes[mk]:
            p = nodes[mk]['Marker']['pos']
            xs.append(float(p[0]))
            ys.append(float(p[1]))
            zs.append(float(p[2]))
    if not xs:
        return None
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


# ============================================================
# 第五部分(补): 坐标偏移模式 (b.py 核心流程)
# ============================================================

def run_offset_mode(nodes, dc_key, patrol_markers, cooldown_markers,
                    patrol_rail_key, cooldown_rail_key):
    """
    坐标偏移模式：完整复刻 b.py 的思路。
      1. 以 DarkCreature 为参考节点，计算所有节点相对偏移
      2. 打印偏移表
      3. 用户输入新基准坐标
      4. 整体平移: new_pos = new_base + offset
      5. 用户输入起始节点 ID，重编号并更新引用
      6. 验证 + 保存
    """
    print("\n" + "=" * 70)
    print("  坐标偏移模式 (保留现有轨迹形状，整体平移)")
    print("=" * 70)

    # --- 1. 计算偏移 (b.py 核心) ---
    # 参考节点 = DarkCreature 本体
    ref_key = dc_key
    try:
        offsets, ref_pos = compute_offsets(nodes, ref_key)
    except ValueError as e:
        print(f"错误: {e}")
        return

    ref_x, ref_y, ref_z = ref_pos
    print(f"\n[A] 参考节点: {ref_key}")
    print(f"    参考坐标: ({ref_x:.6f}, {ref_y:.6f}, {ref_z:.6f})")

    print(f"\n[B] 计算所有节点偏移 (共 {len(offsets)} 个可定位节点):")
    print("-" * 70)
    print(f"    {'节点ID':<22} {'类型':<18} {'dx':>11} {'dy':>11} {'dz':>11}")
    print("-" * 70)
    for key in offsets:
        nt = classify_node(nodes[key])
        dx, dy, dz = offsets[key]
        print(f"    {key:<22} {nt:<18} {dx:>11.6f} {dy:>11.6f} {dz:>11.6f}")

    # --- 2. 输入新基准坐标 ---
    print("\n" + "=" * 70)
    print("[C] 输入新的基准坐标 (将替换参考节点的坐标，其余节点按偏移平移):")
    print("-" * 70)
    new_x = input_float(f"    新基准 X (当前 {ref_x:.6f}, 回车保持): ", ref_x)
    new_y = input_float(f"    新基准 Y (当前 {ref_y:.6f}, 回车保持): ", ref_y)
    new_z = input_float(f"    新基准 Z (当前 {ref_z:.6f}, 回车保持): ", ref_z)
    print(f"\n    新基准坐标: ({new_x:.6f}, {new_y:.6f}, {new_z:.6f})")

    # --- 3. 应用偏移 ---
    print(f"\n[D] 应用偏移 (new_pos = new_base + offset):")
    print("-" * 70)
    moved = apply_offset(nodes, offsets, ref_key, new_x, new_y, new_z)
    print(f"    ✓ 已平移 {moved} 个节点")

    # 显示平移前后对比 (前 5 个)
    print(f"\n    平移前后对比 (前 5 个):")
    print(f"    {'节点ID':<22} {'旧坐标':<30} {'新坐标':<30}")
    print("    " + "-" * 80)
    shown = 0
    for key in offsets:
        if shown >= 5:
            break
        dx, dy, dz = offsets[key]
        old_x, old_y, old_z = ref_x + dx, ref_y + dy, ref_z + dz
        nx, ny, nz = new_x + dx, new_y + dy, new_z + dz
        old_s = f"({old_x:.2f},{old_y:.2f},{old_z:.2f})"
        new_s = f"({nx:.2f},{ny:.2f},{nz:.2f})"
        print(f"    {key:<22} {old_s:<30} {new_s:<30}")
        shown += 1

    # --- 4. 节点 ID 设置 ---
    print("\n" + "=" * 70)
    print("[E] 节点 ID 设置:")
    print("-" * 70)
    existing_min = min(get_node_num(k) for k in nodes if k.startswith('BstNode_'))
    start_id = input_int(f"    起始节点ID (当前最小 {existing_min}, 回车保持): ", existing_min)

    out_file = input("    输出文件名 (默认 dark_dragon_offset.json): ").strip()
    if not out_file:
        out_file = 'dark_dragon_offset.json'

    # --- 5. 重编号 ---
    print(f"\n[F] 重编号节点 (起始ID: {start_id}):")
    print("-" * 70)
    new_nodes = renumber_all(nodes, start_id)
    new_keys_sorted = sorted(new_nodes.keys(), key=get_node_num)
    print(f"    ✓ 节点总数: {len(new_nodes)}")
    print(f"    ✓ ID 范围: {new_keys_sorted[0]} ~ {new_keys_sorted[-1]}")

    # --- 6. 验证引用 ---
    print(f"\n[G] 验证引用完整性:")
    print("-" * 70)
    errors = validate_references(new_nodes)
    if errors:
        print(f"    ✗ 发现 {len(errors)} 个无效引用:")
        for e in errors[:10]:
            print(f"      {e}")
    else:
        print(f"    ✓ 所有引用完整有效")

    # --- 7. 保存 ---
    print(f"\n[H] 保存文件:")
    print("-" * 70)
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(new_nodes, f, indent=2, ensure_ascii=False)
    print(f"    ✓ 已保存: {out_file}")

    # --- 8. 摘要 ---
    print("\n" + "=" * 70)
    print("完成摘要")
    print("=" * 70)
    new_classified = parse_nodes(new_nodes)
    for nt in NODE_TYPES:
        keys = new_classified.get(nt, [])
        if keys:
            print(f"  {nt:<22} {len(keys)} 个  ({keys[0]} ~ {keys[-1]})")

    new_dc_key = new_classified['DarkCreature'][0]
    new_dc_pos = new_nodes[new_dc_key]['DarkCreature']['transform'][3]
    print(f"\n  DarkCreature 新位置: ({new_dc_pos[0]}, {new_dc_pos[1]}, {new_dc_pos[2]})")

    # 巡逻路径点示例
    new_dcp_key = new_classified['DarkCreatureParams'][0]
    new_pr_ref = new_nodes[new_dcp_key]['DarkCreatureParams'].get('[CLUMP]patrolRail', '')
    if new_pr_ref in new_nodes:
        new_pt_markers = new_nodes[new_pr_ref]['Rail']['dataPoints']['[CLUMP]data']
        print(f"\n  巡逻路径点 (前 3 个):")
        for mk in new_pt_markers[:3]:
            if mk in new_nodes:
                p = new_nodes[mk]['Marker']['pos']
                print(f"    {mk}: ({p[0]}, {p[1]}, {p[2]})")

    print("\n" + "=" * 70)
    print("✓ 坐标偏移完成!")
    print("=" * 70)


# ============================================================
# 第六部分：主程序
# ============================================================

def main():
    print("=" * 70)
    print("  冥龙（DarkCreature）轨迹生成工具")
    print("=" * 70)

    # --- 1. 读取文件 ---
    if len(sys.argv) >= 2:
        json_file = sys.argv[1]
    else:
        json_file = input("请输入冥龙 JSON 文件路径 (默认 a.json): ").strip()
        if not json_file:
            json_file = 'a.json'

    if not os.path.exists(json_file):
        print(f"错误: 找不到文件 {json_file}")
        return

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            nodes = json.loads(f.read())
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return

    print(f"\n[1] 读取文件: {json_file}")
    print(f"    总节点数: {len(nodes)}")

    # --- 2. 遍历节点并分类 ---
    classified = parse_nodes(nodes)

    print("\n[2] 节点遍历分类:")
    print("-" * 50)
    for nt in NODE_TYPES:
        keys = classified.get(nt, [])
        if keys:
            print(f"    {nt:<22} {len(keys)} 个")

    # 验证必要节点
    if not classified.get('DarkCreature'):
        print("\n错误: 未找到 DarkCreature 节点!")
        return
    if not classified.get('DarkCreatureParams'):
        print("\n错误: 未找到 DarkCreatureParams 节点!")
        return
    if len(classified.get('Rail', [])) < 2:
        print("\n错误: Rail 节点不足 2 个 (需要 patrol + cooldown)!")
        return

    # --- 3. 解析引用关系 ---
    dc_key = classified['DarkCreature'][0]
    dcp_key = classified['DarkCreatureParams'][0]
    dcp = nodes[dcp_key]['DarkCreatureParams']

    # 识别 patrol / cooldown rail
    patrol_rail_key = dcp.get('[CLUMP]patrolRail', '')
    cooldown_rail_key = dcp.get('[CLUMP]cooldownRail', '')
    rails = classified['Rail']

    if patrol_rail_key not in nodes:
        patrol_rail_key = rails[0]
    if cooldown_rail_key not in nodes:
        for r in rails:
            if r != patrol_rail_key:
                cooldown_rail_key = r
                break

    # 获取两条轨道的 Marker 列表
    patrol_markers = nodes[patrol_rail_key]['Rail']['dataPoints']['[CLUMP]data'][:]
    cooldown_markers = nodes[cooldown_rail_key]['Rail']['dataPoints']['[CLUMP]data'][:]

    print("\n[3] 引用关系解析:")
    print("-" * 50)
    print(f"    DarkCreature:        {dc_key}")
    print(f"      └─ params ->       {dcp_key}")
    print(f"    DarkCreatureParams:")
    print(f"      ├─ patrolRail ->   {patrol_rail_key}")
    print(f"      └─ cooldownRail -> {cooldown_rail_key}")
    print(f"    Patrol Markers:      {len(patrol_markers)} 个 ({patrol_markers[0]} ~ {patrol_markers[-1]})")
    print(f"    Cooldown Markers:    {len(cooldown_markers)} 个 ({cooldown_markers[0]} ~ {cooldown_markers[-1]})")

    # 显示当前坐标信息
    dc_pos = nodes[dc_key]['DarkCreature']['transform'][3]
    print(f"\n    当前 DarkCreature 位置: ({dc_pos[0]}, {dc_pos[1]}, {dc_pos[2]})")

    pt_range = get_marker_range(nodes, patrol_markers)
    if pt_range:
        (x0, x1), (y0, y1), (z0, z1) = pt_range
        print(f"    巡逻轨迹范围: X[{x0:.1f},{x1:.1f}] Y[{y0:.1f},{y1:.1f}] Z[{z0:.1f},{z1:.1f}]")

    # --- 4. 选择工作模式 ---
    print("\n" + "=" * 70)
    print("[4] 选择工作模式:")
    print("-" * 50)
    print("    1. 生成新轨迹  (按形状重排所有路径点坐标)")
    print("    2. 坐标偏移    (保留现有轨迹形状，整体平移到新基准坐标)")
    mode = input("输入序号 (默认 1): ").strip()
    if not mode:
        mode = '1'
    if mode == '2':
        run_offset_mode(nodes, dc_key, patrol_markers, cooldown_markers,
                        patrol_rail_key, cooldown_rail_key)
        return
    print("    ✓ 已选择: 生成新轨迹")

    # --- 4b. 选择轨迹形状 ---
    print("\n" + "=" * 70)
    print("[4b] 选择飞行轨迹形状:")
    print("-" * 50)
    for sid, (name, _) in SHAPES.items():
        print(f"    {sid}. {name}")
    shape_id = input("输入序号 (默认 1 圆形): ").strip()
    if not shape_id:
        shape_id = '1'
    if shape_id not in SHAPES:
        print(f"    无效选择，使用默认: 圆形")
        shape_id = '1'
    shape_name = SHAPES[shape_id][0]
    print(f"    ✓ 已选择: {shape_name}")

    # --- 5. 输入轨迹参数 ---
    print("\n" + "=" * 70)
    print("[5] 输入轨迹参数:")
    print("-" * 50)

    cx = input_float("    中心点 X (默认 0): ", 0.0)
    cy = input_float("    中心点 Y / 基础高度 (默认 12): ", 12.0)
    cz = input_float("    中心点 Z (默认 0): ", 0.0)

    # 形状特定参数
    patrol_params = []
    if shape_id == '1':
        patrol_params = [input_float("    巡逻轨道半径 (默认 25): ", 25.0)]
    elif shape_id == '2':
        rx = input_float("    X 半径 (默认 30): ", 30.0)
        rz = input_float("    Z 半径 (默认 20): ", 20.0)
        patrol_params = [rx, rz]
    elif shape_id == '3':
        patrol_params = [input_float("    心形缩放比例 (默认 1.5): ", 1.5)]
    elif shape_id == '4':
        patrol_params = [input_float("    8字半径 (默认 25): ", 25.0)]
    elif shape_id == '5':
        rs = input_float("    螺旋起始半径 (默认 10): ", 10.0)
        re_ = input_float("    螺旋终止半径 (默认 25): ", 25.0)
        h = input_float("    螺旋高度变化 (默认 5): ", 5.0)
        patrol_params = [rs, re_, h]
    elif shape_id == '6':
        ro = input_float("    星形外半径 (默认 25): ", 25.0)
        ri = input_float("    星形内半径 (默认 12): ", 12.0)
        patrol_params = [ro, ri]
    elif shape_id == '7':
        ln = input_float("    直线长度 (默认 50): ", 50.0)
        am = input_float("    波形幅度 (默认 15): ", 15.0)
        wf = input_float("    水平波形频率 (默认 2): ", 2.0)
        patrol_params = [ln, am, wf]

    wave_amp = input_float("    Y轴波浪幅度 (0=无, 默认 3): ", 3.0)
    wave_freq = input_int("    Y轴波浪频率 (默认 2): ", 2)

    # 冷却轨道
    print("\n    --- 冷却轨道 (cooldown) ---")
    use_same = input("    冷却轨道使用相同形状? (Y/n): ").strip().lower()
    if use_same == 'n':
        cd_shape_id = '1'
        cd_default = patrol_params[0] * 0.7 if patrol_params else 17.5
        cd_radius = input_float(f"    冷却轨道半径 (默认 {cd_default:.1f}): ", cd_default)
        cd_params = [cd_radius]
        cd_name = "圆形"
    else:
        cd_shape_id = shape_id
        cd_params = [p * 0.7 for p in patrol_params]
        cd_name = shape_name + " (缩小70%)"

    # 路径点数量
    print("\n    --- 路径点数量 ---")
    pt_count = input_int(f"    巡逻轨道点数 (默认 {len(patrol_markers)}): ", len(patrol_markers))
    cd_count = input_int(f"    冷却轨道点数 (默认 {len(cooldown_markers)}): ", len(cooldown_markers))

    # --- 6. 节点重编号参数 ---
    print("\n" + "=" * 70)
    print("[6] 节点 ID 设置:")
    print("-" * 50)
    start_id = input_int("    起始节点ID (默认 99988801): ", 99988801)

    # --- 7. 输出文件 ---
    out_file = input("    输出文件名 (默认 dark_dragon_modified.json): ").strip()
    if not out_file:
        out_file = 'dark_dragon_modified.json'

    # --- 8. 生成轨迹 ---
    print("\n" + "=" * 70)
    print("[7] 生成轨迹:")
    print("-" * 50)

    patrol_points = generate_shape(
        shape_id, cx, cy, cz, pt_count, wave_amp, wave_freq, patrol_params)
    print(f"    巡逻轨迹: {len(patrol_points)} 点, 形状={shape_name}")
    print(f"      起点: ({patrol_points[0][0]:.2f}, {patrol_points[0][1]:.2f}, {patrol_points[0][2]:.2f})")
    print(f"      终点: ({patrol_points[-1][0]:.2f}, {patrol_points[-1][1]:.2f}, {patrol_points[-1][2]:.2f})")

    cooldown_points = generate_shape(
        cd_shape_id, cx, cy, cz, cd_count, wave_amp, wave_freq, cd_params)
    print(f"    冷却轨迹: {len(cooldown_points)} 点, 形状={cd_name}")
    print(f"      起点: ({cooldown_points[0][0]:.2f}, {cooldown_points[0][1]:.2f}, {cooldown_points[0][2]:.2f})")

    # --- 9. 调整路径点数量（增删 Marker）---
    print("\n[8] 调整路径点数量:")
    print("-" * 50)
    template_pt = patrol_markers[0] if patrol_markers else dc_key
    template_cd = cooldown_markers[0] if cooldown_markers else template_pt

    if pt_count != len(patrol_markers):
        print(f"    巡逻轨道: {len(patrol_markers)} -> {pt_count}")
        adjust_rail_points(nodes, patrol_rail_key, pt_count, template_pt)
        patrol_markers = nodes[patrol_rail_key]['Rail']['dataPoints']['[CLUMP]data'][:]

    if cd_count != len(cooldown_markers):
        print(f"    冷却轨道: {len(cooldown_markers)} -> {cd_count}")
        adjust_rail_points(nodes, cooldown_rail_key, cd_count, template_cd)
        cooldown_markers = nodes[cooldown_rail_key]['Rail']['dataPoints']['[CLUMP]data'][:]

    if pt_count == len(patrol_markers) and cd_count == len(cooldown_markers):
        print("    点数无变化，跳过")

    # --- 10. 更新 Marker 坐标 ---
    print("\n[9] 更新路径点坐标:")
    print("-" * 50)
    for i, mk in enumerate(patrol_markers):
        if mk in nodes:
            x, y, z = patrol_points[i]
            update_marker_pos(nodes[mk], x, y, z)

    for i, mk in enumerate(cooldown_markers):
        if mk in nodes:
            x, y, z = cooldown_points[i]
            update_marker_pos(nodes[mk], x, y, z)

    print(f"    ✓ 巡逻路径点: {len(patrol_markers)} 个已更新")
    print(f"    ✓ 冷却路径点: {len(cooldown_markers)} 个已更新")

    # --- 11. 更新 DarkCreature 位置（=巡逻起点）---
    dc_x, dc_y, dc_z = patrol_points[0]
    update_darkcreature_pos(nodes[dc_key], dc_x, dc_y, dc_z)
    print(f"    ✓ DarkCreature 位置: ({dc_x:.2f}, {dc_y:.2f}, {dc_z:.2f})")

    # --- 12. 重编号所有节点 ---
    print(f"\n[10] 重编号节点 (起始ID: {start_id}):")
    print("-" * 50)
    new_nodes = renumber_all(nodes, start_id)
    new_keys_sorted = sorted(new_nodes.keys(), key=get_node_num)
    print(f"    ✓ 节点总数: {len(new_nodes)}")
    print(f"    ✓ ID 范围: {new_keys_sorted[0]} ~ {new_keys_sorted[-1]}")

    # --- 13. 验证引用完整性 ---
    print(f"\n[11] 验证引用完整性:")
    print("-" * 50)
    errors = validate_references(new_nodes)
    if errors:
        print(f"    ✗ 发现 {len(errors)} 个无效引用:")
        for e in errors[:10]:
            print(f"      {e}")
    else:
        print(f"    ✓ 所有引用完整有效")

    # --- 14. 保存 ---
    print(f"\n[12] 保存文件:")
    print("-" * 50)
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(new_nodes, f, indent=2, ensure_ascii=False)
    print(f"    ✓ 已保存: {out_file}")

    # --- 15. 摘要 ---
    print("\n" + "=" * 70)
    print("完成摘要")
    print("=" * 70)

    # 重新分类新节点
    new_classified = parse_nodes(new_nodes)
    for nt in NODE_TYPES:
        keys = new_classified.get(nt, [])
        if keys:
            print(f"  {nt:<22} {len(keys)} 个  ({keys[0]} ~ {keys[-1]})")

    # 显示新的 DarkCreature 位置
    new_dc_key = new_classified['DarkCreature'][0]
    new_dc_pos = new_nodes[new_dc_key]['DarkCreature']['transform'][3]
    print(f"\n  DarkCreature 位置: ({new_dc_pos[0]}, {new_dc_pos[1]}, {new_dc_pos[2]})")

    # 显示巡逻路径点示例
    new_patrol_rail = new_classified['DarkCreatureParams'][0]
    new_pr_ref = new_nodes[new_patrol_rail]['DarkCreatureParams'].get('[CLUMP]patrolRail', '')
    if new_pr_ref in new_nodes:
        new_pt_markers = new_nodes[new_pr_ref]['Rail']['dataPoints']['[CLUMP]data']
        print(f"\n  巡逻路径点 (前 3 个):")
        for mk in new_pt_markers[:3]:
            if mk in new_nodes:
                p = new_nodes[mk]['Marker']['pos']
                print(f"    {mk}: ({p[0]}, {p[1]}, {p[2]})")

    # 显示完整节点示例
    print(f"\n  完整节点示例 ({new_dc_key}):")
    sample = {new_dc_key: new_nodes[new_dc_key]}
    print(json.dumps(sample, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("✓ 全部完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()
