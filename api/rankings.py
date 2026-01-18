"""
排行榜处理模块
处理玩家数据并生成排行榜
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


def calculate_player_stats(player_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算玩家的统计数据
    
    参数:
        player_data: 玩家的计分项列表
        
    返回:
        dict: 包含各项统计数据的字典
    """
    stats = {
        "play_time_seconds": 0,  # 总游玩时长（秒）
        "games_played": 0,       # 游玩局数
        "wins": 0,               # 胜利局数
        "kills": 0,              # 击杀数
        "deaths": 0,             # 死亡数
    }
    
    for entry in player_data:
        objective = entry.get("Objective", "")
        score = entry.get("Score", 0)
        
        if objective == "PlayTime.Hour":
            stats["play_time_seconds"] += score * 3600  # 小时转秒
        elif objective == "PlayTime.Min":
            stats["play_time_seconds"] += score * 60    # 分钟转秒
        elif objective == "PlayTime.Sec":
            stats["play_time_seconds"] += score         # 秒
        elif objective == "CompletedCount":
            stats["games_played"] = score
        elif objective == "WinCount":
            stats["wins"] = score
        elif objective == "KilledCount":
            stats["kills"] = score
        elif objective == "DeathCount":
            stats["deaths"] = score
    
    return stats


def generate_rankings(player_scores_json_path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """生成排行榜数据
    
    参数:
        player_scores_json_path: player_scores_grouped.json 文件路径
        
    返回:
        tuple: (排行榜数据, 错误信息)
    """
    try:
        # 检查玩家数据文件是否存在
        if not player_scores_json_path.exists():
            return None, "玩家数据文件不存在，请先运行数据更新"
        
        with open(player_scores_json_path, 'r', encoding='utf-8') as f:
            all_player_data = json.load(f)
        
        # 过滤掉特殊玩家名
        player_stats = {}
        for player_name, player_data in all_player_data.items():
            if (player_name and not player_name.startswith('$') and 
                not player_name.startswith('#') and 
                not player_name.startswith('%') and
                not player_name.startswith('[')):
                stats = calculate_player_stats(player_data)
                player_stats[player_name] = stats
        
        if not player_stats:
            return None, "未找到有效的玩家数据"
        
        # 生成各项排行榜
        rankings = {
            "play_time": [],      # 游玩时长排行榜
            "games_played": [],   # 游玩局数排行榜
            "wins": [],           # 胜利局数排行榜
            "kills": [],          # 击杀数排行榜
            "deaths": [],         # 死亡数排行榜
            "kd_ratio": [],       # KD比率排行榜（击杀/死亡）
            "win_rate": [],       # 胜率排行榜（胜利/游玩局数）
        }
        
        # 计算各项数据并排序
        for player_name, stats in player_stats.items():
            # 游玩时长（秒转小时:分钟:秒格式）
            play_time_seconds = stats["play_time_seconds"]
            hours = play_time_seconds // 3600
            minutes = (play_time_seconds % 3600) // 60
            seconds = play_time_seconds % 60
            play_time_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # KD比率（避免除零）
            deaths = stats["deaths"] if stats["deaths"] > 0 else 1
            kd_ratio = stats["kills"] / deaths
            
            # 胜率（避免除零）
            games = stats["games_played"] if stats["games_played"] > 0 else 1
            win_rate = (stats["wins"] / games) * 100
            
            rankings["play_time"].append({
                "player": player_name,
                "value": stats["play_time_seconds"],
                "formatted": play_time_formatted,
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds
            })
            
            rankings["games_played"].append({
                "player": player_name,
                "value": stats["games_played"]
            })
            
            rankings["wins"].append({
                "player": player_name,
                "value": stats["wins"]
            })
            
            rankings["kills"].append({
                "player": player_name,
                "value": stats["kills"]
            })
            
            rankings["deaths"].append({
                "player": player_name,
                "value": stats["deaths"]
            })
            
            rankings["kd_ratio"].append({
                "player": player_name,
                "value": kd_ratio,
                "formatted": f"{kd_ratio:.2f}"
            })
            
            rankings["win_rate"].append({
                "player": player_name,
                "value": win_rate,
                "formatted": f"{win_rate:.1f}%"
            })
        
        # 对各项排行榜进行排序（降序，除了死亡数按升序排）
        for key in rankings:
            if key == "deaths":
                # 死亡数越少越好，所以按升序排
                rankings[key].sort(key=lambda x: x["value"])
            else:
                # 其他都是数值越大越好，按降序排
                rankings[key].sort(key=lambda x: x["value"], reverse=True)
        
        return rankings, None
        
    except Exception as e:
        return None, f"生成排行榜时出错: {str(e)}"


def save_rankings_to_json(rankings: Dict[str, Any], output_file: Path) -> Tuple[bool, Optional[str]]:
    """保存排行榜数据到 JSON 文件
    
    参数:
        rankings: 排行榜数据
        output_file: 输出文件路径
        
    返回:
        tuple: (成功标志, 错误信息)
    """
    try:
        # 准备要保存的数据
        data_to_save = {
            "generated_at": datetime.datetime.now().isoformat(),
            "rankings": {}
        }
        
        # 只保存前10名
        for key, rank_list in rankings.items():
            data_to_save["rankings"][key] = rank_list[:10]
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
        return True, None
        
    except Exception as e:
        return False, f"保存排行榜数据时出错: {str(e)}"


def create_rank_message_nodes(rankings: Dict[str, Any], bot_uin: int = 10000) -> List:
    """创建群合并转发消息节点
    
    参数:
        rankings: 排行榜数据
        bot_uin: 机器人QQ号，默认为10000
        
    返回:
        list: Node 对象列表
    """
    from astrbot.api.message_components import Node, Plain
    
    nodes = []
    
    # 各项排行榜配置
    rank_categories = [
        ("play_time", "🏆 游玩时长排行榜", "value", True, lambda x: x["formatted"]),
        ("games_played", "🎮 游玩局数排行榜", "value", True, None),
        ("wins", "🏅 胜利局数排行榜", "value", True, None),
        ("kills", "⚔️ 击杀数排行榜", "value", True, None),
        ("deaths", "💀 死亡数排行榜", "value", False, None),  # 死亡数越少越好
        ("kd_ratio", "📊 KD比率排行榜", "value", True, lambda x: x["formatted"]),
        ("win_rate", "📈 胜率排行榜", "value", True, lambda x: x["formatted"]),
    ]
    
    # 创建 Plain 元素列表
    plain_elements = []
    
    # 添加标题作为第一个 Plain 元素
    plain_elements.append(Plain("=== 幸运之柱玩家排行榜 ===\n\n"))
    
    for rank_key, title, value_key, descending, formatter in rank_categories:
        if rank_key not in rankings or not rankings[rank_key]:
            continue
            
        rank_list = rankings[rank_key][:10]
        
        # 为每个排行榜构建独立的文本
        rank_text = f"{title}\n"
        for i, item in enumerate(rank_list):
            rank_num = i + 1
            player = item["player"]
            value = item[value_key]
            
            # 使用格式化函数（如果有）
            if formatter:
                display_value = formatter(item)
            else:
                display_value = str(value)
            
            # 添加排名符号
            if rank_num == 1:
                rank_symbol = "🥇"
            elif rank_num == 2:
                rank_symbol = "🥈"
            elif rank_num == 3:
                rank_symbol = "🥉"
            else:
                rank_symbol = f"{rank_num}."
            
            rank_text += f"{rank_symbol} {player}: {display_value}\n"
        
        rank_text += "\n"
        plain_elements.append(Plain(rank_text))
    
    # 创建节点包含多个 Plain 元素
    main_node = Node(
        uin=bot_uin,
        name="幸运之柱排行榜",
        content=plain_elements
    )
    nodes.append(main_node)
    
    return nodes


def main():
    """命令行入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description="生成玩家排行榜")
    parser.add_argument("--input", "-i", required=True, help="player_scores_grouped.json 文件路径")
    parser.add_argument("--output", "-o", help="输出 rankings.json 文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / "rankings.json"
    
    if args.verbose:
        print(f"输入文件: {input_path}")
        print(f"输出文件: {output_path}")
    
    # 生成排行榜
    rankings, error = generate_rankings(input_path)
    
    if error:
        print(f"错误: {error}")
        return 1
    
    if args.verbose and rankings:
        print(f"成功处理 {sum(len(r) for r in rankings.values())} 条排行榜数据")
    
    # 保存到 JSON 文件
    if rankings:
        success, save_error = save_rankings_to_json(rankings, output_path)
        
        if not success:
            print(f"警告: {save_error}")
        elif args.verbose:
            print(f"排行榜数据已保存到: {output_path}")
        
        # 打印摘要
        print("\n排行榜摘要:")
        for key in ["play_time", "games_played", "wins", "kills", "deaths", "kd_ratio", "win_rate"]:
            if rankings[key]:
                top_player = rankings[key][0]["player"]
                top_value = rankings[key][0].get("formatted", rankings[key][0]["value"])
                print(f"  {key}: {top_player} ({top_value})")
    else:
        print("错误: 未能生成排行榜数据")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())