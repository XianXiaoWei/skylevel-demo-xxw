import json
import copy
import os

# 检查文件是否存在
json_file = 'aaa.json'
if not os.path.exists(json_file):
    print(f"错误: 找不到文件 {json_file}")
    print("请检查文件名是否正确")
    exit()

# 读取原始JSON文件
try:
    with open(json_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # 尝试解析JSON
        data = json.loads(content)
except json.JSONDecodeError as e:
    print(f"JSON解析错误: {e}")
    exit()

# 检查数据结构并提取节点
if isinstance(data, dict):
    # 检查是否是直接的节点数据（第一个key是BstNode_开头）
    first_key = list(data.keys())[0]
    if first_key.startswith('BstNode_'):
        nodes = data
        print("检测到直接节点数据格式")
    elif 'nodes' in data:
        nodes = data['nodes']
        print("检测到包含nodes字段的格式")
    else:
        print(f"未知数据格式，第一个key: {first_key}")
        print("尝试作为节点数据处理...")
        nodes = data
else:
    print("数据不是字典格式")
    exit()

# 获取第一个节点作为参考
first_node_id = list(nodes.keys())[0]
first_pos = nodes[first_node_id]['CandleObject']['transform'][3]

# 提取参考坐标 (确保是浮点数)
ref_x = float(first_pos[0])
ref_y = float(first_pos[1])
ref_z = float(first_pos[2])

print("=" * 80)
print("蜡烛节点坐标偏移工具 (带缩放)")
print("=" * 80)
print(f"\n参考节点: {first_node_id}")
print(f"参考坐标: ({ref_x:.6f}, {ref_y:.6f}, {ref_z:.6f})")

# 计算每个节点的偏移
print("\n计算所有节点的偏移值:")
print("-" * 80)
offsets = {}
for node_id, node_data in nodes.items():
    pos = node_data['CandleObject']['transform'][3]
    dx = float(pos[0]) - ref_x
    dy = float(pos[1]) - ref_y
    dz = float(pos[2]) - ref_z
    offsets[node_id] = (dx, dy, dz)
    print(f"{node_id}: 偏移 ({dx:>10.6f}, {dy:>10.6f}, {dz:>10.6f})")

# 用户输入新坐标
print("\n" + "=" * 80)
print("请输入新的基础坐标 (将替换第一个节点的坐标):")
print("-" * 80)
try:
    new_x = float(input("请输入 X 坐标: "))
    new_y = float(input("请输入 Y 坐标: "))
    new_z = float(input("请输入 Z 坐标: "))
except ValueError:
    print("错误: 请输入有效的数字")
    exit()

# 用户输入缩放倍数
print("\n" + "=" * 80)
print("请输入缩放倍数 (偏移和物体大小都会乘以该倍数):")
print("-" * 80)
print("  - 位置偏移:  X/Z = 基础坐标 + 偏移 × 缩放")
print("  - 位置偏移:  Y   = 基础坐标 + 偏移 (不缩放)")
print("  - 矩阵大小:  3x3 旋转/缩放部分 × 缩放倍数 (照常)")
print("  - 例如: 1.0=不缩放, 2.0=放大2倍, 0.5=缩小一半")
print("-" * 80)
try:
    scale = float(input("请输入缩放倍数 (默认 1.0): ") or "1.0")
    if scale == 0:
        print("错误: 缩放倍数不能为 0")
        exit()
except ValueError:
    print("错误: 请输入有效的数字")
    exit()

# 用户输入起始节点ID
print("\n" + "=" * 80)
print("请输入新的节点ID起始值:")
print("-" * 80)
try:
    start_node_id = int(input("请输入起始节点ID (例如: 99988852): "))
except ValueError:
    print("错误: 请输入有效的整数")
    exit()

print(f"\n新基础坐标: ({new_x:.6f}, {new_y:.6f}, {new_z:.6f})")
print(f"缩放倍数: {scale} (Y 轴坐标不缩放)")
print(f"起始节点ID: {start_node_id}")

# 创建新的节点数据
new_nodes = {}

# 更新所有节点的坐标和ID
print("\n生成新的节点ID和坐标:")
print("-" * 80)
for i, old_node_id in enumerate(nodes.keys()):
    # 生成纯数字ID
    pure_number = str(start_node_id + i)
    
    # 生成新节点ID (保持BstNode_前缀 + 数字)
    new_node_id = "BstNode_" + pure_number
    
    # 获取偏移
    dx, dy, dz = offsets[old_node_id]
    
    # 计算新坐标 = 基础坐标 + 偏移 × 缩放 (保持为字符串，加引号)
    # 注意: Y 轴坐标不缩放，偏移直接相加；X/Z 轴偏移乘以缩放倍数
    new_pos = [
        str(new_x + dx * scale),
        str(new_y + dy),
        str(new_z + dz * scale),
        "1.0"
    ]
    
    # 复制节点数据
    node_data = copy.deepcopy(nodes[old_node_id])
    
    # 更新坐标 (全部为字符串)
    node_data['CandleObject']['transform'][3] = new_pos
    
    # 缩放矩阵的 3x3 旋转/缩放部分 (前3行的前3列 × 缩放倍数)
    # transform 结构:
    #   [0] = [m00, m01, m02, 0.0]  →  [m00*s, m01*s, m02*s, 0.0]
    #   [1] = [m10, m11, m12, 0.0]  →  [m10*s, m11*s, m12*s, 0.0]
    #   [2] = [m20, m21, m22, 0.0]  →  [m20*s, m21*s, m22*s, 0.0]
    #   [3] = [tx,  ty,  tz,  1.0] (已在上面更新)
    # 注意: 矩阵缩放照常 (全部 × 缩放倍数), Y 轴不缩放只针对位置坐标
    for row in range(3):
        for col in range(3):
            original_val = float(node_data['CandleObject']['transform'][row][col])
            node_data['CandleObject']['transform'][row][col] = str(original_val * scale)
    
    # 更新bstGuid (纯数字，不加前缀)
    node_data['CandleObject']['bstGuid'] = pure_number
    
    # 添加到新节点字典 (键保持BstNode_前缀)
    new_nodes[new_node_id] = node_data
    
    print(f"旧ID: {old_node_id} -> 新ID: {new_node_id}")
    print(f"  bstGuid: {pure_number}")
    print(f"  坐标: ({new_pos[0]}, {new_pos[1]}, {new_pos[2]})")
    print(f"  矩阵已缩放 ×{scale}")

# 保存新的JSON文件
output_file = 'objects.level.bin_modified.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(new_nodes, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 80)
print(f"✓ 修改完成！")
print(f"新文件已保存为: {output_file}")
print("=" * 80)

# 显示修改后的节点信息
print("\n修改后的节点信息 (前10个):")
print("-" * 80)
print(f"{'节点ID':<20} {'bstGuid':<15} {'坐标 (x, y, z)':<40}")
print("-" * 80)
count = 0
for node_id, node_data in new_nodes.items():
    if count >= 10:
        break
    pos = node_data['CandleObject']['transform'][3]
    bstGuid = node_data['CandleObject']['bstGuid']
    print(f"{node_id:<20} {bstGuid:<15} ({pos[0]}, {pos[1]}, {pos[2]})")
    count += 1

print("\n节点ID范围:")
print(f"起始: BstNode_{start_node_id}")
print(f"结束: BstNode_{start_node_id + len(new_nodes) - 1}")
print(f"总节点数: {len(new_nodes)}")

print("\nbstGuid范围:")
print(f"起始: {start_node_id}")
print(f"结束: {start_node_id + len(new_nodes) - 1}")

# 显示缩放效果总结
print("\n" + "=" * 80)
print("缩放效果总结:")
print("-" * 80)
print(f"缩放倍数: {scale} (Y 轴坐标不缩放)")
print(f"位置偏移: X/Z 轴 偏移 × {scale}, Y 轴偏移不缩放")
print(f"矩阵大小: 3x3 旋转/缩放部分 × {scale} (照常)")
print(f"  - 例如: 原始 m00=0.511083 → 新 m00={0.511083 * scale:.6f}")

# 显示JSON中节点ID的格式验证
print("\n" + "=" * 80)
print("验证JSON中的格式:")
print("-" * 80)
sample_node_id = list(new_nodes.keys())[0]
sample_bstGuid = new_nodes[sample_node_id]['CandleObject']['bstGuid']
sample_transform = new_nodes[sample_node_id]['CandleObject']['transform']
print(f"节点键: {sample_node_id} (类型: {type(sample_node_id).__name__})")
print(f"bstGuid: {sample_bstGuid} (类型: {type(sample_bstGuid).__name__})")
print(f"坐标值类型: {type(sample_transform[3][0]).__name__}, {type(sample_transform[3][1]).__name__}, {type(sample_transform[3][2]).__name__}")
print(f"矩阵值类型: {type(sample_transform[0][0]).__name__} (均为字符串)")
print("✓ 节点键保持 BstNode_ 前缀，是字符串类型 (有引号)")
print("✓ bstGuid 是纯数字，是字符串类型 (有引号)")
print("✓ 所有坐标值和矩阵值都是字符串类型 (有引号)")

# 显示一个完整的节点示例
print("\n完整的节点示例:")
sample_data = {sample_node_id: new_nodes[sample_node_id]}
print(json.dumps(sample_data, indent=2))
