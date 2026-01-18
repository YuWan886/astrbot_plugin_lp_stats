"""
幸运之柱玩家战绩查询插件
"""

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Image, Node, Plain
from typing import Dict, List, Any, Optional, Tuple, Union, AsyncGenerator
from pathlib import Path
import json
import datetime
import sys
import os
import time

# 导入 API 模块
sys.path.insert(0, str(Path(__file__).parent))
try:
    from api.process_scoreboard import (
        process_dat_to_json,
        process_json_to_grouped,
        load_scoreboard_data,
        group_scores_by_player
    )
    from api.generate_player_stats_image import generate_stats_image
    from api.rankings import (
        generate_rankings,
        save_rankings_to_json,
        create_rank_message_nodes
    )
    API_AVAILABLE = True
except ImportError as e:
    logger.error(f"导入 API 模块失败: {e}")
    API_AVAILABLE = False


class Config:
    """配置管理类"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.config_dict = config_dict or {}
        
        # 默认配置
        self.defaults = {
            "scoreboard_dat_path": "E:\\群组\\1.21.11-幸运之柱\\world\\data\\scoreboard.dat",
            "query_interval": 60
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config_dict.get(key, self.defaults.get(key, default))
    
    @property
    def scoreboard_dat_path(self) -> Path:
        """获取 scoreboard.dat 文件路径"""
        return Path(self.get("scoreboard_dat_path"))
    
    @property
    def query_interval(self) -> int:
        """获取查询间隔"""
        return self.get("query_interval", 60)


class DataManager:
    """数据管理类"""
    
    def __init__(self, plugin_dir: Path, config: Config):
        self.plugin_dir = plugin_dir
        self.config = config
        
        # 目录结构
        self.data_dir = plugin_dir / "data"
        self.output_dir = plugin_dir / "output"
        self.avatar_cache_dir = plugin_dir / "avatar_cache"
        
        # 数据文件路径
        self.scoreboard_json_path = self.data_dir / "scoreboard.json"
        self.player_scores_json_path = self.data_dir / "player_scores_grouped.json"
        self.rankings_json_path = self.data_dir / "rankings.json"
        
        # 创建必要的目录
        self._create_directories()
    
    def _create_directories(self) -> None:
        """创建必要的目录"""
        self.data_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.avatar_cache_dir.mkdir(exist_ok=True)
    
    def update_data_files(self) -> bool:
        """更新数据文件（如果需要）"""
        try:
            if not API_AVAILABLE:
                logger.error("API 模块不可用，无法更新数据文件")
                return False
            
            update_needed = False
            
            # 检查 scoreboard.dat 是否比 scoreboard.json 新
            if not self.scoreboard_json_path.exists():
                update_needed = True
            elif self.config.scoreboard_dat_path.exists():
                dat_mtime = self.config.scoreboard_dat_path.stat().st_mtime
                json_mtime = self.scoreboard_json_path.stat().st_mtime
                if dat_mtime > json_mtime:
                    update_needed = True
            
            if update_needed:
                logger.info("检测到数据文件需要更新，正在解析 scoreboard.dat...")
                
                # 使用 API 模块处理数据
                process_dat_to_json(
                    self.config.scoreboard_dat_path,
                    self.scoreboard_json_path
                )
                
                # 处理 JSON 到分组数据
                process_json_to_grouped(
                    self.scoreboard_json_path,
                    self.player_scores_json_path
                )
                
                logger.info("scoreboard.dat 解析和数据处理完成")
            
            return True
            
        except Exception as e:
            logger.error(f"更新数据文件时出错: {e}")
            return False
    
    def get_player_list(self) -> List[str]:
        """获取玩家列表"""
        try:
            if not self.player_scores_json_path.exists():
                # 如果数据文件不存在，先更新
                if not self.update_data_files():
                    return []
            
            with open(self.player_scores_json_path, 'r', encoding='utf-8') as f:
                player_data = json.load(f)
            
            # 过滤掉特殊玩家名
            players = []
            for name in player_data.keys():
                if (name and not name.startswith('$') and 
                    not name.startswith('#') and 
                    not name.startswith('%') and
                    not name.startswith('[')):
                    players.append(name)
            
            return sorted(players)
            
        except Exception as e:
            logger.error(f"获取玩家列表时出错: {e}")
            return []
    
    def get_player_data(self, player_name: str) -> Optional[List[Dict[str, Any]]]:
        """获取指定玩家的数据"""
        try:
            if not self.player_scores_json_path.exists():
                return None
            
            with open(self.player_scores_json_path, 'r', encoding='utf-8') as f:
                player_data = json.load(f)
            
            return player_data.get(player_name)
            
        except Exception as e:
            logger.error(f"获取玩家数据时出错: {e}")
            return None


class ImageGenerator:
    """图片生成器类"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
    
    def generate_player_stats_image(self, player_name: str) -> Tuple[Optional[Path], Optional[str]]:
        """生成玩家战绩图片"""
        try:
            if not API_AVAILABLE:
                return None, "API 模块不可用，无法生成图片"
            
            # 首先确保数据文件是最新的
            if not self.data_manager.update_data_files():
                return None, "数据文件更新失败"
            
            # 检查玩家是否存在
            player_data = self.data_manager.get_player_data(player_name)
            if not player_data:
                return None, f"未找到玩家 '{player_name}' 的数据"
            
            # 生成图片
            logger.info(f"正在为玩家 {player_name} 生成战绩图片...")
            
            # 使用 API 模块生成图片
            image = generate_stats_image(player_name, {player_name: player_data})
            
            # 保存图片到输出目录
            output_path = self.data_manager.output_dir / f"{player_name}_stats.png"
            image.save(output_path)
            
            logger.info(f"战绩图已保存: {output_path}")
            return output_path, None
            
        except Exception as e:
            logger.error(f"生成玩家战绩图片时出错: {e}")
            return None, str(e)


class RankingsManager:
    """排行榜管理类"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
    
    def generate_rankings(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """生成排行榜数据"""
        try:
            if not API_AVAILABLE:
                return None, "API 模块不可用，无法生成排行榜"
            
            # 确保数据文件是最新的
            if not self.data_manager.update_data_files():
                return None, "数据文件更新失败"
            
            # 使用 API 模块生成排行榜
            return generate_rankings(self.data_manager.player_scores_json_path)
            
        except Exception as e:
            logger.error(f"生成排行榜时出错: {e}")
            return None, str(e)
    
    def save_rankings(self, rankings: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """保存排行榜数据"""
        try:
            if not API_AVAILABLE:
                return False, "API 模块不可用，无法保存排行榜"
            
            return save_rankings_to_json(rankings, self.data_manager.rankings_json_path)
            
        except Exception as e:
            logger.error(f"保存排行榜数据时出错: {e}")
            return False, str(e)
    
    def create_rank_message_nodes(self, rankings: Dict[str, Any], bot_uin: int = 10000) -> List[Node]:
        """创建排行榜消息节点"""
        try:
            if not API_AVAILABLE:
                # 返回错误节点
                return [
                    Node(
                        uin=bot_uin,
                        name="错误",
                        content=[
                            Plain("API 模块不可用，无法生成排行榜消息\n")
                        ]
                    )
                ]
            
            return create_rank_message_nodes(rankings, bot_uin)
            
        except Exception as e:
            logger.error(f"创建排行榜消息节点时出错: {e}")
            # 返回错误节点
            return [
                Node(
                    uin=bot_uin,
                    name="错误",
                    content=[
                        Plain(f"创建排行榜消息时出错: {str(e)}\n")
                    ]
                )
            ]


@register("astrbot_plugin_lp_stats", "YuWan", "幸运之柱玩家战绩查询插件", "1.0.0")
class LPStatsPlugin(Star):
    """幸运之柱玩家战绩查询插件"""
    
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        
        # 初始化配置
        self.config = Config(config)
        
        # 初始化组件
        self.data_manager = DataManager(Path(__file__).parent, self.config)
        self.image_generator = ImageGenerator(self.data_manager)
        self.rankings_manager = RankingsManager(self.data_manager)
        
        # 查询时间跟踪字典，用于实现查询间隔限制
        self.last_query_time: Dict[str, float] = {}
    
    async def initialize(self) -> None:
        """插件初始化方法"""
        logger.info("幸运之柱玩家战绩查询插件已加载")
        logger.info(f"配置 - scoreboard.dat 路径: {self.config.scoreboard_dat_path}")
        logger.info(f"配置 - 查询间隔: {self.config.query_interval} 秒")
        
        # 检查必要的文件是否存在
        if not self.config.scoreboard_dat_path.exists():
            logger.warning(f"scoreboard.dat 文件不存在: {self.config.scoreboard_dat_path}")
        else:
            logger.info(f"找到 scoreboard.dat 文件: {self.config.scoreboard_dat_path}")
        
        # 检查 API 模块可用性
        if not API_AVAILABLE:
            logger.warning("API 模块导入失败，部分功能可能不可用")
        else:
            logger.info("API 模块加载成功")
    
    async def terminate(self) -> None:
        """插件销毁方法"""
        logger.info("幸运之柱玩家战绩查询插件已卸载")
    
    def _check_query_interval(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """检查用户查询间隔
        
        Args:
            user_id: 用户ID
            
        Returns:
            Tuple[是否允许查询, 剩余等待时间(秒)]
        """
        current_time = time.time()
        last_time = self.last_query_time.get(user_id)
        
        if last_time is None:
            # 用户第一次查询，允许并记录时间
            self.last_query_time[user_id] = current_time
            return True, 0
        
        # 计算距离上次查询的时间间隔
        time_since_last = current_time - last_time
        query_interval = self.config.query_interval
        
        if time_since_last < query_interval:
            # 查询过于频繁，返回剩余等待时间
            remaining_time = int(query_interval - time_since_last)
            return False, remaining_time
        else:
            # 允许查询，更新最后查询时间
            self.last_query_time[user_id] = current_time
            return True, 0
    
    @filter.command("stats")
    async def stats_command(self, event: AstrMessageEvent) -> AsyncGenerator[Any, Any]:
        """查询玩家战绩
        
        用法: /stats <玩家名>
        示例: /stats yuwan
        """
        message_str = event.message_str.strip()
        
        # 检查查询间隔
        user_id = event.session_id
        allowed, remaining = self._check_query_interval(user_id)
        
        if not allowed:
            yield event.plain_result(
                f"查询过于频繁，请等待 {remaining} 秒后再试。\n"
            )
            return
        
        # 解析命令参数
        parts = message_str.split()
        if len(parts) < 2:
            # 显示帮助信息
            help_text = (
                "幸运之柱玩家战绩查询\n"
                "用法: /stats <玩家名>\n"
                "示例: /stats yuwan\n\n"
                "可用命令:\n"
                "/stats <玩家名> - 查询指定玩家战绩\n"
                "/战绩 <玩家名> - 中文命令，功能相同\n"
                "/rank - 查看玩家排行榜\n"
                "/排行榜 - 中文命令，功能相同\n"
            )
            yield event.plain_result(help_text)
            return
        
        # 查询指定玩家战绩
        player_name = parts[1]
        yield event.plain_result(f"正在为玩家 {player_name} 生成战绩图，请稍候...")
        
        image_path, error = self.image_generator.generate_player_stats_image(player_name)
        
        if error:
            yield event.plain_result(f"生成战绩图失败: {error}")
            return
        
        # 发送图片
        try:
            if not image_path:
                yield event.plain_result("生成图片失败：图片路径为空")
                return
            
            # 发送图片
            yield event.image_result(str(image_path))
            
            # 添加文本说明
            # yield event.plain_result(f"玩家 {player_name} 的战绩图已生成！")
            
        except Exception as e:
            logger.error(f"发送图片时出错: {e}")
            yield event.plain_result(f"生成图片成功但发送失败: {e}")
    
    @filter.command("战绩")
    async def stats_chinese_command(self, event: AstrMessageEvent) -> AsyncGenerator[Any, Any]:
        """查询玩家战绩（中文命令）
        
        用法: /战绩 <玩家名>
        示例: /战绩 yuwan
        """
        # 处理中文命令，直接复用 stats_command 的逻辑
        message_str = event.message_str.strip()
        
        # 将 "/战绩" 替换为 "/stats" 然后调用相同的处理逻辑
        if message_str.startswith("/战绩"):
            new_message = "/stats" + message_str[3:]
            event.message_str = new_message
        
        # 使用 yield from 来调用异步生成器
        async for result in self.stats_command(event):
            yield result
    
    @filter.command("rank")
    async def rank_command(self, event: AstrMessageEvent) -> AsyncGenerator[Any, Any]:
        """查看玩家排行榜
        
        用法: /rank
        示例: /rank
        """
        # 检查查询间隔
        user_id = event.session_id
        allowed, remaining = self._check_query_interval(user_id)
        
        if not allowed:
            yield event.plain_result(
                f"查询过于频繁，请等待 {remaining} 秒后再试。\n"
            )
            return
        
        # 生成排行榜数据
        rankings, error = self.rankings_manager.generate_rankings()
        
        if error:
            yield event.plain_result(f"生成排行榜失败: {error}")
            return
        
        if rankings is None:
            yield event.plain_result("生成排行榜数据为空")
            return
        
        # 保存到 JSON 文件
        success, save_error = self.rankings_manager.save_rankings(rankings)
        if not success:
            logger.warning(f"保存排行榜数据失败: {save_error}")
        
        # 创建群合并转发消息
        # 获取机器人QQ号并转换为整数
        bot_uin_str = event.get_self_id()
        try:
            bot_uin = int(bot_uin_str)
        except (ValueError, TypeError):
            bot_uin = 10000  # 默认值
        
        nodes = self.rankings_manager.create_rank_message_nodes(rankings, bot_uin)
        
        # 创建 Nodes 对象（包含多个 Node 的合并转发消息）
        from astrbot.api.message_components import Nodes
        nodes_component = Nodes(nodes=nodes)
        
        # 发送合并转发消息
        yield event.chain_result([nodes_component]) 
    
    @filter.command("排行榜")
    async def rank_chinese_command(self, event: AstrMessageEvent) -> AsyncGenerator[Any, Any]:
        """查看玩家排行榜（中文命令）
        
        用法: /排行榜
        示例: /排行榜
        """
        # 直接复用 rank_command 的逻辑
        async for result in self.rank_command(event):
            yield result