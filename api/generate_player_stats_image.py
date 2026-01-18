"""
生成玩家战绩图脚本
数据来源: player_scores_grouped.json
"""

import json
import sys
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import io
import hashlib
import datetime


def load_player_data():
    """加载玩家数据"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(script_dir, "..", "data", "player_scores_grouped.json")
        data_path = os.path.normpath(data_file)
        
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print("错误: 未找到 player_scores_grouped.json 文件")
        print(f"尝试的路径: {data_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败 - {e}")
        sys.exit(1)


def get_player_stat(player_data, player_name, stat_key):
    """获取玩家的特定统计值"""
    scores = player_data.get(player_name, [])
    for entry in scores:
        if entry.get("Objective") == stat_key and "Score" in entry:
            return entry["Score"]
    return 0


def get_random_background():
    """从多个 API 获取随机背景图片"""
    apis = [
        {
            "name": "sex.nyan.run",
            "url": "https://sex.nyan.run/api/v2/img",
            "params": {"r18": False},
        },
        {
            "name": "lolicon.app",
            "url": "https://api.lolicon.app/setu/v2",
            "params": {"r18": 0, "regular": "regular"},
            "extract_url": True,
        },
        {
            "name": "pixiv.cat",
            "url": "https://api.pixiv.cat/v1/illust/random",
            "params": {"r18": "false"},
        },
    ]

    for api in apis:
        try:
            print(f"正在从 {api['name']} 获取背景图片...")
            response = requests.get(api["url"], params=api["params"], timeout=10)
            response.raise_for_status()

            if api.get("extract_url"):
                # 需要从 JSON 中提取图片 URL
                data = response.json()
                if data.get("data"):
                    image_url = data["data"][0]["urls"]["regular"]
                    print(f"获取到背景图片 URL: {image_url}")
                    img_response = requests.get(image_url, timeout=10)
                    img_response.raise_for_status()
                    image = Image.open(io.BytesIO(img_response.content))
                else:
                    continue
            else:
                # 直接获取图片数据
                image = Image.open(io.BytesIO(response.content))

            print(f"从 {api['name']} 获取背景图片成功")
            return image
        except Exception as e:
            print(f"警告: 从 {api['name']} 获取背景图片失败 - {e}")
            continue

    print("所有背景图片 API 均失败，使用默认渐变背景")
    return create_default_background()


def create_default_background():
    """创建默认的渐变背景"""
    width, height = 1200, 900
    image = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 创建渐变效果
    for y in range(height):
        r = int(60 + (20 * y / height))
        g = int(40 + (30 * y / height))
        b = int(80 + (40 * y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return image


def resize_and_blur_background(background, width, height, blur_radius=10):
    """调整背景大小并添加模糊效果"""
    # 调整尺寸
    bg = background

    # 模糊处理
    bg = bg.filter(ImageFilter.GaussianBlur(blur_radius))

    return bg


def draw_text_with_stroke(
    draw, position, text, font, text_color, stroke_color, stroke_width=3
):
    """绘制带描边的文字"""
    x, y = position
    for offset in range(-stroke_width, stroke_width + 1):
        for offset_y in range(-stroke_width, stroke_width + 1):
            if offset == 0 and offset_y == 0:
                continue
            draw.text((x + offset, y + offset_y), text, font=font, fill=stroke_color)

    draw.text(position, text, font=font, fill=text_color)


def load_font(size):
    """加载字体"""
    try:
        # 尝试加载系统字体
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",  # Windows 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",  # Windows 宋体
            "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux Droid Sans
        ]

        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue

        raise Exception("未找到可用的字体")
    except Exception as e:
        print(f"警告: 加载字体失败 - {e}")
        return ImageFont.load_default()


def get_minecraft_avatar(player_name, size=180):
    """从 Minecraft 头像 API 获取玩家头像，支持缓存"""
    # 基于脚本位置创建缓存目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = Path(os.path.join(script_dir, "..", "avatar_cache"))
    cache_dir.mkdir(exist_ok=True)

    # 生成缓存文件名
    cache_key = hashlib.md5(player_name.encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}_{size}.png"

    # 检查缓存是否存在
    if cache_file.exists():
        try:
            print(f"从缓存加载 {player_name} 的头像...")
            avatar = Image.open(cache_file).convert("RGBA")
            print("头像缓存加载成功")
            return avatar
        except Exception as e:
            print(f"警告: 缓存加载失败 - {e}")

    try:
        print(f"正在获取 {player_name} 的 Minecraft 头像...")

        # 首先获取玩家的 UUID
        uuid_url = f"https://api.mojang.com/users/profiles/minecraft/{player_name}"
        uuid_response = requests.get(uuid_url, timeout=10)
        uuid_response.raise_for_status()
        uuid_data = uuid_response.json()
        uuid = uuid_data.get("id")

        if not uuid:
            raise Exception("无法获取玩家 UUID")

        # 使用 Mineatar API 获取 Minecraft 头像
        url = f"https://api.mineatar.io/face/{uuid}"
        params = {"scale": 8, "overlay": "true", "download": "false", "format": "png"}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        avatar = Image.open(io.BytesIO(response.content)).convert("RGBA")

        # 保存到缓存
        avatar.save(cache_file)
        print("头像获取成功并已缓存")
        return avatar
    except Exception as e:
        print(f"警告: 获取 Minecraft 头像失败 - {e}")
        print("使用默认头像")
        return create_default_avatar(size)


def create_default_avatar(size):
    """创建默认的玩家头像"""
    avatar = Image.new("RGBA", (size, size), (100, 100, 150, 255))
    draw = ImageDraw.Draw(avatar)

    # 绘制默认头像内容
    draw.ellipse(
        [(0, 0), (size, size)], fill=(100, 100, 150), outline=(255, 255, 255), width=3
    )
    draw.text(
        (size // 2 - 40, size // 2 - 60),
        "头像",
        font=load_font(48),
        fill=(200, 200, 200),
    )

    return avatar


def generate_stats_image(player_name, player_data):
    """生成玩家战绩图"""
    print(f"\n正在生成 {player_name} 的战绩图...")

    # 获取玩家数据
    play_time_hour = get_player_stat(player_data, player_name, "PlayTime.Hour")
    play_time_min = get_player_stat(player_data, player_name, "PlayTime.Min")
    play_time_sec = get_player_stat(player_data, player_name, "PlayTime.Sec")
    completed_count = get_player_stat(player_data, player_name, "CompletedCount")
    win_count = get_player_stat(player_data, player_name, "WinCount")
    killed_count = get_player_stat(player_data, player_name, "KilledCount")
    death_count = get_player_stat(player_data, player_name, "DeathCount")

    print(f"游玩时长: {play_time_hour}时{play_time_min}分{play_time_sec}秒")
    print(f"游玩局数: {completed_count}")
    print(f"获胜局数: {win_count}")
    print(f"击杀次数: {killed_count}")
    print(f"死亡次数: {death_count}")

    # 创建图片
    width, height = 1200, 900
    img = Image.new("RGB", (width, height), (0, 0, 0))

    # 获取背景
    background = get_random_background()
    bg = resize_and_blur_background(background, width, height)
    img.paste(bg, (0, 0))

    draw = ImageDraw.Draw(img)

    # 加载字体
    title_font = load_font(60)
    info_font = load_font(40)
    stat_font = load_font(36)

    # 添加半透明遮罩
    mask = Image.new("RGBA", (width - 200, height - 200), (0, 0, 0, 150))
    img.paste(mask, (100, 100), mask)

    # 绘制标题
    title_text = f"{player_name} 的战绩"
    bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = bbox[2] - bbox[0]
    title_height = bbox[3] - bbox[1]
    title_x = (width - title_width) // 2
    draw_text_with_stroke(
        draw, (title_x, 120), title_text, title_font, (255, 255, 255), (0, 0, 0), 3
    )

    # 绘制玩家头像
    avatar_size = 180
    avatar_x = (width - avatar_size) // 2
    avatar_y = 220

    # 获取 Minecraft 头像
    avatar = get_minecraft_avatar(player_name, avatar_size)

    # 调整头像大小
    avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)

    # 创建圆形头像
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([(0, 0), (avatar_size, avatar_size)], fill=255)

    # 创建圆形头像
    circular_avatar = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
    circular_avatar.paste(avatar, (0, 0), mask)

    # 粘贴头像
    img.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)

    # 绘制头像边框
    draw.ellipse(
        [
            (avatar_x - 3, avatar_y - 3),
            (avatar_x + avatar_size + 3, avatar_y + avatar_size + 3),
        ],
        outline=(255, 255, 255),
        width=3,
    )

    # 绘制战绩信息
    stats = [
        f"游玩时长: {play_time_hour}时{play_time_min}分{play_time_sec}秒",
        f"游玩局数: {completed_count}",
        f"获胜局数: {win_count}",
        f"击杀次数: {killed_count}",
        f"死亡次数: {death_count}",
    ]

    info_start_y = avatar_y + avatar_size + 60
    info_spacing = 60

    # 左侧基本信息
    for i, stat in enumerate(stats):
        draw_text_with_stroke(
            draw,
            (160, info_start_y + i * info_spacing),
            stat,
            info_font,
            (255, 255, 255),
            (0, 0, 0),
            2,
        )

    # 右侧统计数据
    right_start_x = width - 520

    # 计算胜率
    if completed_count > 0:
        win_rate = (win_count / completed_count) * 100
        win_rate_text = f"胜率: {win_rate:.1f}%"
        draw_text_with_stroke(
            draw,
            (right_start_x, info_start_y),
            win_rate_text,
            stat_font,
            (255, 165, 0),
            (0, 0, 0),
            2,
        )

    # 计算场均击杀和死亡
    if completed_count > 0:
        avg_kill = killed_count / completed_count
        avg_death = death_count / completed_count
        avg_kd_text = f"场均: 击杀 {avg_kill:.1f} | 死亡 {avg_death:.1f}"
        draw_text_with_stroke(
            draw,
            (right_start_x, info_start_y + info_spacing),
            avg_kd_text,
            stat_font,
            (0, 255, 255),
            (0, 0, 0),
            2,
        )

    # 计算 K/D 比率
    if death_count > 0:
        kd_ratio = killed_count / death_count
        kd_text = f"K/D 比率: {kd_ratio:.2f}"
        draw_text_with_stroke(
            draw,
            (right_start_x, info_start_y + 2 * info_spacing),
            kd_text,
            stat_font,
            (255, 105, 180),
            (0, 0, 0),
            2,
        )

    # 添加生成时间文本在水印上方
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_text = f"生成时间: {current_time}"
    time_font = load_font(24)
    time_bbox = draw.textbbox((0, 0), time_text, font=time_font)
    time_width = time_bbox[2] - time_bbox[0]
    time_height = time_bbox[3] - time_bbox[1]
    time_x = (width - time_width) // 2
    time_y = height - time_height - 70  # 距离底部70像素（在水印上方）

    draw_text_with_stroke(
        draw,
        (time_x, time_y),
        time_text,
        time_font,
        (200, 200, 200),
        (0, 0, 0),
        1,
    )

    # 添加水印文本 "幸运之柱©一条鱼丸_" 在图片底部居中
    watermark_text = "幸运之柱©一条鱼丸_"
    watermark_font = load_font(24)
    bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
    watermark_width = bbox[2] - bbox[0]
    watermark_height = bbox[3] - bbox[1]
    watermark_x = (width - watermark_width) // 2
    watermark_y = height - watermark_height - 30  # 距离底部30像素

    draw_text_with_stroke(
        draw,
        (watermark_x, watermark_y),
        watermark_text,
        watermark_font,
        (255, 255, 0),
        (0, 0, 0),
        1,
    )

    # 保存图片
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "output")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{player_name}_stats.png")
    img.save(output_file)
    print(f"战绩图已保存为: {output_file}")

    return img


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python generate_player_stats_image.py <玩家名>")
        print("示例: python generate_player_stats_image.py yuwan")
        sys.exit(1)

    player_name = sys.argv[1]

    # 加载玩家数据
    player_data = load_player_data()

    # 检查玩家是否存在
    if player_name not in player_data:
        print(f"错误: 未找到玩家 '{player_name}' 的数据")
        print("可用玩家列表:")
        for name in player_data.keys():
            if (
                name
                and not name.startswith("$")
                and not name.startswith("#")
                and not name.startswith("%")
            ):
                print(f"  - {name}")
        sys.exit(1)

    # 生成战绩图
    generate_stats_image(player_name, player_data)


if __name__ == "__main__":
    main()
