import requests
import logging
from pathlib import Path

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

def process_m3u(content):
    """处理 M3U 内容，替换 RTP 地址"""
    try:
        # 替换所有的 rtp:// 为 http://10.109.60.250:4022/
        processed_content = content.replace('rtp://', 'http://10.109.60.250:4022/udp/')
        
        # 计算替换次数
        replacement_count = content.count('rtp://')
        logging.info(f"Replaced {replacement_count} occurrences of 'rtp://'")
        
        return processed_content
    except Exception as e:
        logging.error(f"Error processing M3U content: {e}")
        raise

def save_m3u(content, filename='processed.m3u'):
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
