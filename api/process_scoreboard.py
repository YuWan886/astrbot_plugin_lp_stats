"""
1. 解析 Minecraft scoreboard.dat 文件（NBT格式）并转换为 JSON
2. 处理 scoreboard.json 数据，按玩家名分组 PlayerScores
"""

import nbtlib
import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional


def nbt_to_json(nbt_data):
    """递归将 nbtlib 对象转换为 JSON 可序列化的 Python 对象"""
    # 导入 nbtlib.tag 用于类型检查
    from nbtlib import tag
    
    if isinstance(nbt_data, tag.Compound):
        return {key: nbt_to_json(value) for key, value in nbt_data.items()}
    elif isinstance(nbt_data, tag.List):
        return [nbt_to_json(item) for item in nbt_data]
    elif isinstance(nbt_data, (tag.ByteArray, tag.IntArray, tag.LongArray)):
        # 数组类型转换为列表
        return list(nbt_data)
    elif isinstance(nbt_data, (tag.Byte, tag.Short, tag.Int, tag.Long)):
        # 整数类型
        return int(nbt_data)
    elif isinstance(nbt_data, (tag.Float, tag.Double)):
        # 浮点类型
        return float(nbt_data)
    elif isinstance(nbt_data, tag.String):
        # 字符串类型
        return str(nbt_data)
    else:
        # 对于其他类型（如 End, ByteTag 等），返回其字符串表示
        return str(nbt_data)


def parse_scoreboard_dat(file_path: Path) -> Any:
    """解析 scoreboard.dat 文件并返回 JSON 可序列化的数据"""
    print(f"正在解析文件: {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件 {file_path} 不存在")
    
    # 使用 nbtlib 加载文件（自动检测 gzip 压缩）
    nbt_file = nbtlib.load(file_path)
    
    # 在 nbtlib 2.x 中，File 对象本身就是字典，可以直接访问
    # 转换为 Python 字典
    data = nbt_to_json(nbt_file)
    
    return data


def export_to_json(data: Any, output_file: Path, indent: int = 2) -> None:
    """导出数据到 JSON 文件"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    print(f"数据已导出到: {output_file}")


def load_scoreboard_data(json_file: Path) -> Dict[str, Any]:
    """加载 scoreboard.json 文件"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"错误: 文件 {json_file} 不存在")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败 - {e}")
        sys.exit(1)


def clean_score_entry(score_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    清理计分项数据，移除 Locked 和 Name 字段
    
    参数:
        score_entry: 原始计分项字典
        
    返回:
        dict: 清理后的计分项字典
    """
    # 创建副本以避免修改原始数据
    cleaned = score_entry.copy()
    
    # 移除 Locked 字段
    cleaned.pop("Locked", None)
    
    # 移除 Name 字段
    cleaned.pop("Name", None)
    
    return cleaned


def group_scores_by_player(scoreboard_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    按玩家名分组 PlayerScores 数据
    
    参数:
        scoreboard_data: 从 scoreboard.json 加载的完整数据
        
    返回:
        dict: 按玩家名分组的字典，结构为:
            {
                "玩家名1": [
                    {"Objective": "计分项1", "Score": 100, ...},
                    {"Objective": "计分项2", "Score": 50, ...},
                    ...
                ],
                "玩家名2": [...],
                ...
            }
    """
    # 获取 PlayerScores 数组
    player_scores = scoreboard_data.get("data", {}).get("PlayerScores", [])
    
    if not player_scores:
        print("警告: 未找到 PlayerScores 数据")
        return {}
    
    # 使用 defaultdict 按玩家名分组
    grouped = defaultdict(list)
    
    for score_entry in player_scores:
        player_name = score_entry.get("Name", "未知玩家")
        # 清理计分项数据，移除 Locked 和 Name 字段
        cleaned_entry = clean_score_entry(score_entry)
        grouped[player_name].append(cleaned_entry)
    
    return dict(grouped)


def process_dat_to_json(dat_file: Path, output_json: Path) -> None:
    """处理 dat 文件到 JSON 的转换"""
    try:
        # 解析文件
        scoreboard_data = parse_scoreboard_dat(dat_file)
        
        # 输出为 JSON 文件
        export_to_json(scoreboard_data, output_json)
        
        # 同时打印一些摘要信息
        print("\n数据摘要:")
        print(f"根标签数量: {len(scoreboard_data)}")
        for key in scoreboard_data.keys():
            print(f"  - {key}: {type(scoreboard_data[key]).__name__}")
            
    except Exception as e:
        print(f"解析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def process_json_to_grouped(json_file: Path, output_grouped: Path) -> None:
    """处理 JSON 文件到分组数据的转换"""
    print(f"正在处理文件: {json_file}")
    
    # 1. 加载数据
    scoreboard_data = load_scoreboard_data(json_file)
    
    # 2. 按玩家分组（自动移除 Locked 和 Name 字段）
    grouped_scores = group_scores_by_player(scoreboard_data)
    
    if not grouped_scores:
        print("错误: 未找到任何玩家分数数据")
        sys.exit(1)
    
    print(f"成功处理 {len(grouped_scores)} 名玩家的数据")
    
    # 3. 导出数据
    export_to_json(grouped_scores, output_grouped)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="处理 Minecraft scoreboard 数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认路径执行完整处理流程
  python process_scoreboard.py --full-process --default-paths
  
  # 指定 scoreboard.dat 文件路径
  python process_scoreboard.py "E:\\群组\\1.21.11-幸运之柱\\world\\data\\scoreboard.dat"
  
  # 指定 scoreboard.dat 文件路径并执行完整处理
  python process_scoreboard.py --full-process "E:\\群组\\1.21.11-幸运之柱\\world\\data\\scoreboard.dat"
        """
    )
    
    # 位置参数：scoreboard.dat 文件路径（可选）
    parser.add_argument(
        "dat_file",
        nargs="?",
        help="scoreboard.dat 文件路径（可选，如果不提供则使用默认路径）"
    )
    
    # 可选参数
    parser.add_argument(
        "--full-process", "-f",
        action="store_true",
        help="执行完整处理流程（从 .dat 到分组 JSON）"
    )
    
    parser.add_argument(
        "--default-paths", "-d",
        action="store_true",
        help="使用默认路径（与 main.py 中定义的路径一致）"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出"
    )
    
    args = parser.parse_args()
    
    # 设置详细模式
    if args.verbose:
        print("详细模式已启用")
    
    # 确定文件路径
    if args.default_paths:
        # 使用与 main.py 一致的默认路径
        plugin_dir = Path(__file__).parent.parent
        data_dir = plugin_dir / "data"
        scoreboard_dat_path = Path("E:\\群组\\1.21.11-幸运之柱\\world\\data\\scoreboard.dat")
        scoreboard_json_path = data_dir / "scoreboard.json"
        player_scores_json_path = data_dir / "player_scores_grouped.json"
        
        print(f"使用默认路径:")
        print(f"  scoreboard.dat: {scoreboard_dat_path}")
        print(f"  scoreboard.json: {scoreboard_json_path}")
        print(f"  player_scores_grouped.json: {player_scores_json_path}")
        
        dat_file = scoreboard_dat_path
        output_json = scoreboard_json_path
        output_grouped = player_scores_json_path
        
    elif args.dat_file:
        # 使用用户提供的 dat 文件路径
        dat_file = Path(args.dat_file)
        
        # 确定输出文件路径（与 dat 文件同目录）
        dat_dir = dat_file.parent
        output_json = dat_dir / "scoreboard.json"
        output_grouped = dat_dir / "player_scores_grouped.json"
        
        print(f"使用指定路径:")
        print(f"  scoreboard.dat: {dat_file}")
        print(f"  scoreboard.json: {output_json}")
        print(f"  player_scores_grouped.json: {output_grouped}")
        
    else:
        # 既没有指定路径也没有使用默认路径，显示帮助信息
        parser.print_help()
        print("\n错误: 必须指定 scoreboard.dat 文件路径或使用 --default-paths 选项")
        sys.exit(1)
    
    # 确保输出目录存在
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_grouped.parent.mkdir(parents=True, exist_ok=True)
    
    # 执行处理流程
    if args.full_process:
        # 完整处理流程：dat -> json -> grouped
        print("\n开始完整处理流程...")
        
        # 步骤1: 将 dat 文件转换为 JSON
        print("\n=== 步骤1: 解析 scoreboard.dat 文件 ===")
        process_dat_to_json(dat_file, output_json)
        
        # 步骤2: 将 JSON 文件按玩家分组
        print("\n=== 步骤2: 按玩家分组数据 ===")
        process_json_to_grouped(output_json, output_grouped)
        
        print(f"\n完整处理流程完成！")
        print(f"  - 原始 JSON 文件: {output_json}")
        print(f"  - 分组 JSON 文件: {output_grouped}")
        
    else:
        # 只执行 dat 到 JSON 的转换
        print("\n开始 DAT 到 JSON 转换...")
        process_dat_to_json(dat_file, output_json)
        print(f"\n转换完成！JSON 文件已保存到: {output_json}")


if __name__ == "__main__":
    main()