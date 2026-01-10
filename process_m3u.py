import requests
import logging
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def download_m3u():
    """下载原始 M3U 文件"""
    url = "https://raw.githubusercontent.com/Tzwcard/ChinaTelecom-GuangdongIPTV-RTP-List/refs/heads/master/GuangdongIPTV_rtp_all.m3u8"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logging.info("Successfully downloaded M3U file")
        return response.text
    except requests.RequestException as e:
        logging.error(f"Failed to download M3U file: {e}")
        raise

def get_channel_group(channel_name: str) -> str:
    """根据频道名称确定分组"""
    channel_upper = channel_name.upper()
    
    # 央视频道
    if any(x in channel_upper for x in ['CCTV', '央视', '中央', 'CGTN']):
        return "央视高清"
    
    # 卫视频道(排除凤凰卫视)
    if '卫视' in channel_upper and '凤凰' not in channel_name:
        return "卫视高清"
    
    # 数字频道
    digital_patterns = r'CHC|求索|黑莓|哒啵|乐游|纪实|纯享|风云|第一剧场|女性时尚|兵器科技|怀旧剧场|世界地理|文化精品|央视台球|高尔夫网球|电视指南|都市剧场|金色学堂|哈哈炫动|游戏风云|欢笑剧场|第一财经|武术世界|文物宝库|梨园|天元围棋|弈坛春秋|劲爆体育'
    if re.search(digital_patterns, channel_upper):
        return "数字高清"
    
    # 国际时事
    if any(x in channel_upper for x in ['凤凰', 'NHK', 'CNA', 'ALJAZEERA', 'ARIRANG', 'RT']):
        return "国际时事"
    
    # 地方频道
    if any(x in channel_upper for x in ['茶频道', '快乐垂钓', '金鹰', '先锋', '湖南', '长沙', '山西', '黄河', '湖北', '浙江', '纪实科教', '卡酷', '陕西', '黑龙江']):
        return "地方特色"
    
    # NewTV系列
    if 'NEWTV' in channel_upper or '超级' in channel_upper:
        return "NewTV系列"
    
    # 咪咕体育
    if '咪咕' in channel_upper:
        return "咪咕体育"
    
    # CETV教育频道
    if 'CETV' in channel_upper:
        return "央视高清"
    
    return "其他"

def clean_channel_id(channel_name: str) -> str:
    """清理频道名称得到频道ID"""
    cleaned = channel_name.upper()
    cleaned = re.sub(r'\[.*?\]|[0-9\.]+M|[0-9]{3,4}[pP]?|[0-9\.]+FPS', '', cleaned)
    cleaned = cleaned.strip()
    cleaned = re.sub(r'超高清|超清|高清$|蓝光|频道$|标清|FHD|HD$|HEVC|HDR|-|\s+', '', cleaned)
    cleaned = cleaned.strip()
    
    if 'CCTV' in cleaned and 'CCTV4K' not in cleaned:
        cctv_match = re.search(r'CCTV[0-9+]{1,2}[48]?K?', cleaned)
        if cctv_match:
            return cctv_match.group(0).replace('4K', '')
        cctv_name_match = re.search(r'CCTV[^0-9]+', cleaned)
        if cctv_name_match:
            return cctv_name_match.group(0).replace('CCTV', '')
    
    return cleaned.replace('BTV', '北京')

def process_m3u(content: str) -> Tuple[str, Dict[str, List[Tuple[str, str]]]]:
    """处理 M3U 内容,返回M3U内容和分组的频道数据"""
    try:
        lines = content.split('\n')
        result = ["#EXTM3U"]
        
        # 用于存储TXT格式的数据: {分组名: [(频道名, URL), ...]}
        txt_data = {}
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            if line.startswith('#EXTINF:'):
                if i + 1 >= len(lines):
                    break
                    
                url = lines[i + 1].strip()
                
                if not url or (not url.startswith('rtp://') and not url.startswith('http://')):
                    i += 2
                    continue
                
                try:
                    channel_match = re.search(r'#EXTINF:-1.*,(.+)$', line)
                    if not channel_match:
                        i += 2
                        continue
                        
                    channel_name = channel_match.group(1).strip()
                    
                    # 处理RTP地址
                    if url.startswith('rtp://'):
                        url = url.replace('rtp://', 'http://192.168.2.2:55555/udp/')
                    
                    group = get_channel_group(channel_name)
                    channel_id = clean_channel_id(channel_name)
                    tvg_name = channel_id
                    logo_url = f"https://epg.112114.xyz/logo/{channel_id}.png"
                    
                    # 构建M3U格式
                    new_extinf = (
                        f'#EXTINF:-1 tvg-id="{tvg_name}" '
                        f'tvg-name="{tvg_name}" '
                        f'tvg-logo="{logo_url}" '
                        f'group-title="{group}",{channel_name}'
                    )
                    
                    result.extend([new_extinf, url])
                    
                    # 保存到TXT数据结构
                    if group not in txt_data:
                        txt_data[group] = []
                    txt_data[group].append((channel_name, url))
                    
                    logging.debug(f"Added channel: {channel_name} ({group})")
                    
                except Exception as e:
                    logging.warning(f"Error processing channel at line {i}: {e}")
                
                i += 2
            else:
                i += 1
        
        logging.info(f"Processed {(len(result)-1) // 2} channels")
        return '\n'.join(result), txt_data
        
    except Exception as e:
        logging.error(f"Error processing M3U content: {e}")
        raise

def generate_txt_content(txt_data: Dict[str, List[Tuple[str, str]]]) -> str:
    """生成TXT格式内容"""
    # 定义分组顺序
    group_order = [
        "央视高清",
        "卫视高清", 
        "数字高清",
        "国际时事",
        "地方特色",
        "NewTV系列",
        "咪咕体育"
    ]
    
    result = []
    
    for group in group_order:
        if group in txt_data and txt_data[group]:
            result.append(f"{group},#genre#")
            for channel_name, url in txt_data[group]:
                result.append(f"{channel_name},{url}")
            result.append("")  # 添加空行分隔
    
    # 添加其他未分类的频道
    if "其他" in txt_data and txt_data["其他"]:
        result.append("其他,#genre#")
        for channel_name, url in txt_data["其他"]:
            result.append(f"{channel_name},{url}")
    
    return '\n'.join(result)

def save_m3u(content: str, filename='processed.m3u'):
    """保存处理后的 M3U 文件"""
    try:
        output_path = Path(filename)
        output_path.write_text(content, encoding='utf-8')
        logging.info(f"Successfully saved processed M3U to {filename}")
        
        file_size = output_path.stat().st_size
        logging.info(f"Output file size: {file_size} bytes")
            
    except Exception as e:
        logging.error(f"Failed to save M3U file: {e}")
        raise

def save_txt(content: str, filename='processed.txt'):
    """保存处理后的 TXT 文件"""
    try:
        output_path = Path(filename)
        output_path.write_text(content, encoding='utf-8')
        logging.info(f"Successfully saved processed TXT to {filename}")
        
        file_size = output_path.stat().st_size
        logging.info(f"TXT file size: {file_size} bytes")
            
    except Exception as e:
        logging.error(f"Failed to save TXT file: {e}")
        raise

def main():
    try:
        logging.info("Starting M3U processing")
        original_content = download_m3u()
        
        lines = original_content.split('\n')
        logging.info(f"Downloaded content has {len(lines)} lines")
        
        # 处理内容,同时获取M3U和TXT数据
        processed_m3u, txt_data = process_m3u(original_content)
        
        # 保存M3U文件
        save_m3u(processed_m3u)
        
        # 生成并保存TXT文件
        txt_content = generate_txt_content(txt_data)
        save_txt(txt_content)
        
        logging.info("M3U and TXT processing completed successfully")
    except Exception as e:
        logging.error(f"Failed to process files: {e}")
        raise

if __name__ == "__main__":
    main()
