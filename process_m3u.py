import requests
import logging
import re
from pathlib import Path
from typing import List, Tuple

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

def m3u_to_txt(content: str) -> List[Tuple[str, str]]:
    """将M3U格式转换为频道名称和URL的列表"""
    try:
        # 将内容按@分割，模拟JavaScript的替换操作
        content = re.sub(r'[\r\n]+', '@', content)
        
        # 匹配频道名称和URL
        matches = re.findall(r',([^,@]+)@([^@]+)', content)
        
        if not matches:
            logging.warning("No valid channels found in M3U content")
            return []
            
        # 清理匹配结果
        channels = [(name.strip(), url.strip()) for name, url in matches]
        logging.info(f"Successfully extracted {len(channels)} channels")
        return channels
        
    except Exception as e:
        logging.error(f"Error converting M3U to TXT: {e}")
        raise

def txt_to_m3u(channels: List[Tuple[str, str]]) -> str:
    """将频道列表转换回M3U格式"""
    try:
        result = ["#EXTM3U"]
        
        for name, url in channels:
            if not url.upper().startswith('HTTP'):
                continue
                
            result.append(f'#EXTINF:-1,{name}')
            result.append(url)
        
        processed_content = '\n'.join(result)
        logging.info(f"Successfully converted {len(channels)} channels to M3U format")
        return processed_content
        
    except Exception as e:
        logging.error(f"Error converting TXT to M3U: {e}")
        raise

def process_m3u(content: str) -> str:
    """处理 M3U 内容，包括格式转换和RTP地址替换"""
    try:
        # 首先执行m3u到txt的转换
        channels = m3u_to_txt(content)
        
        # 处理RTP地址和TVG-ID
        processed_channels = []
        rtp_count = 0
        tvg_count = 0
        
        for name, url in channels:
            # 处理TVG-ID
            if 'tvg-name="' in name and 'tvg-id="' not in name:
                tvg_name_match = re.search(r'tvg-name="([^"]*)"', name)
                if tvg_name_match:
                    tvg_name = tvg_name_match.group(1)
                    name = name.replace(f'tvg-name="{tvg_name}"', 
                                     f'tvg-name="{tvg_name}" tvg-id="{tvg_name}"')
                    tvg_count += 1
            
            # 处理RTP地址
            if url.startswith('rtp://'):
                url = url.replace('rtp://', 'http://10.109.60.250:4022/udp/')
                rtp_count += 1
            
            processed_channels.append((name, url))
        
        # 转换回M3U格式
        result = txt_to_m3u(processed_channels)
        
        logging.info(f"Replaced {rtp_count} RTP addresses")
        logging.info(f"Added {tvg_count} tvg-id attributes")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing M3U content: {e}")
        raise

def save_m3u(content: str, filename='processed.m3u'):
    """保存处理后的 M3U 文件"""
    try:
        output_path = Path(filename)
        output_path.write_text(content, encoding='utf-8')
        logging.info(f"Successfully saved processed M3U to {filename}")
    except Exception as e:
        logging.error(f"Failed to save M3U file: {e}")
        raise

def main():
    try:
        # 下载原始文件
        logging.info("Starting M3U processing")
        original_content = download_m3u()
        
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
