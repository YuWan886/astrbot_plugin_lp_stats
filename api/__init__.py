"""
API 模块包
包含排行榜生成、玩家数据统计等功能
"""

__version__ = "1.0.0"
__all__ = [
    "generate_rankings",
    "save_rankings_to_json", 
    "create_rank_message_nodes",
    "calculate_player_stats",
    "generate_stats_image"
]

# 导入主要功能以便直接访问
from .rankings import (
    generate_rankings,
    save_rankings_to_json,
    create_rank_message_nodes,
    calculate_player_stats
)

from .generate_player_stats_image import generate_stats_image