import requests
import logging
import re
from pathlib import Path
from typing import List, Tuple, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def download_m3u():
    """下载原始 M3U 文件"""
    url = "https://raw.githubusercontent.com/Tzwcard/ChinaTelecom-GuangdongIPTV-RTP-List/refs/heads/master/GuangdongIPTV_rtp_all.m3u"
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
        return "央视"
    
    # 卫视频道（排除凤凰卫视）
    if '卫视' in channel_upper and '凤凰' not in channel_name:
        return "卫视"
    
    # 地方台和特殊频道
    region_patterns = r'北京|上海|NEWTV|IHOT|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾|重庆|香港'
    region_match = re.search(region_patterns, channel_upper)
    if region_match:
        return region_match.group(0)
    
    # 凤凰卫视
    if '凤凰' in channel_upper:
        return "香港"
    
    # 港澳台频道
    hk_tw_patterns = r'翡翠|明珠|民视|台视|华视|TVB|纬来|年代|原住民|中视|澳亚|东森|好消息电视台|大爱|博斯|ELEVEN|FOX|ASTRO|HBO|NIPPON|NHK|GSTV|无线'
    if re.search(hk_tw_patterns, channel_upper):
        return "港澳台"
    
    # 北京台
    if 'BTV' in channel_upper:
        return "北京"
    
    # 央视数字频道
    cctv_digital = r'世界地理|兵器科技|卫生健康|央视台球|女性时尚|怀旧剧场|文化精品|电视指南|第一剧场|风云剧场|风云足球|风云音乐|高尔夫网球|老故事|中学生'
    if re.search(cctv_digital, channel_name):
        return "央视"
    
    return "其他"

def clean_channel_id(channel_name: str) -> str:
    """清理频道名称得到频道ID"""
    # 移除特殊标记和清晰度标识
    cleaned = channel_name.upper()
    cleaned = re.sub(r'\[.*?\]|[0-9\.]+M|[0-9]{3,4}[pP]?|[0-9\.]+FPS', '', cleaned)
    cleaned = cleaned.strip()
    cleaned = re.sub(r'超高清|超清|高清$|蓝光|频道$|标清|FHD|HD$|HEVC|HDR|-|\s+', '', cleaned)
    cleaned = cleaned.strip()
    
    # 特殊处理CCTV频道
    if 'CCTV' in cleaned and 'CCTV4K' not in cleaned:
        cctv_match = re.search(r'CCTV[0-9+]{1,2}[48]?K?', cleaned)
        if cctv_match:
            return cctv_match.group(0).replace('4K', '')
        cctv_name_match = re.search(r'CCTV[^0-9]+', cleaned)
        if cctv_name_match:
            return cctv_name_match.group(0).replace('CCTV', '')
    
    return cleaned.replace('BTV', '北京')

def process_m3u(content: str) -> str:
    """处理 M3U 内容，添加分组和元数据"""
    try:
        lines = content.split('\n')
        result = ["#EXTM3U"]
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # 处理EXTINF行
            if line.startswith('#EXTINF:'):
                # 确保还有下一行
                if i + 1 >= len(lines):
                    break
                    
                url = lines[i + 1].strip()
                
                # 检查URL的有效性
                if not url or (not url.startswith('rtp://') and not url.startswith('http://')):
                    i += 2
                    continue
                
                try:
                    # 提取频道名称
                    channel_match = re.search(r'#EXTINF:-1.*,(.+)$', line)
                    if not channel_match:
                        i += 2
                        continue
                        
                    channel_name = channel_match.group(1).strip()
                    
                    # 处理RTP地址
                    if url.startswith('rtp://'):
                        url = url.replace('rtp://', 'http://192.168.2.2:55555/udp/')
                    
                    # 获取频道分组
                    group = get_channel_group(channel_name)
                    
                    # 获取频道ID
                    channel_id = clean_channel_id(channel_name)
                    
                    # 构建EPG标识和logo URL
                    tvg_name = channel_id
                    logo_url = f"https://epg.112114.xyz/logo/{channel_id}.png"
                    
                    # 构建新的EXTINF行
                    new_extinf = (
                        f'#EXTINF:-1 tvg-id="{tvg_name}" '
                        f'tvg-name="{tvg_name}" '
                        f'tvg-logo="{logo_url}" '
                        f'group-title="{group}",{channel_name}'
                    )
                    
                    result.extend([new_extinf, url])
                    logging.debug(f"Added channel: {channel_name} ({group})")
                    
                except Exception as e:
                    logging.warning(f"Error processing channel at line {i}: {e}")
                
                i += 2  # 跳过URL行
            else:
                i += 1
        
        logging.info(f"Processed {(len(result)-1) // 2} channels")
        return '\n'.join(result)
        
    except Exception as e:
        logging.error(f"Error processing M3U content: {e}")
        raise

def save_m3u(content: str, filename='processed.m3u'):
    """保存处理后的 M3U 文件"""
    try:
        output_path = Path(filename)
        output_path.write_text(content, encoding='utf-8')
        logging.info(f"Successfully saved processed M3U to {filename}")
        
        # 添加文件大小检查
        file_size = output_path.stat().st_size
        logging.info(f"Output file size: {file_size} bytes")
            
    except Exception as e:
        logging.error(f"Failed to save M3U file: {e}")
        raise

def main():
    try:
        # 下载原始文件
        logging.info("Starting M3U processing")
        original_content = download_m3u()
        
        # 输出原始内容的基本信息
        lines = original_content.split('\n')
        logging.info(f"Downloaded content has {len(lines)} lines")
        
        # 处理内容
        processed_content = process_m3u(original_content)
        
        # 保存处理后的文件
        save_m3u(processed_content)
        
        logging.info("M3U processing completed successfully")
    except Exception as e:
        logging.error(f"Failed to process M3U file: {e}")
        raise

if __name__ == "__main__":
    main()
