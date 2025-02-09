import requests
from bs4 import BeautifulSoup
import os
import time

# 目标网页 URL
url = 'https://www.bbc.co.uk/learningenglish/chinese/features/english-in-a-minute/ep-250207'
# 请求头部，模拟浏览器访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

try:
    # 获取网页内容
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # 确保请求成功
except requests.RequestException as e:
    print(f"请求失败: {e}")
    exit()

# 解析网页内容
soup = BeautifulSoup(response.content, 'html.parser')

# 等待video标签加载
max_attempts = 10
for _ in range(max_attempts):
    article = soup.find('div', {'role': 'article'})
    video = article.find('div', {'class': 'video'})
    
    if video:
        break
    
    time.sleep(1)  # 每次等待1秒
    
    # 重新获取页面内容
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException:
        continue

# 删除不需要的部分
elements_to_remove = [
    ('div', {'class': 'widget widget-pagelink widget-pagelink-next-activity'}),
    ('div', {'class': 'widget widget-list widget-list-automatic'}),
    ('div', {'class': 'widget widget-heading clear-left'}),
    ('div', {'class': 'widget-container widget-container-right'}),
    ('div', {'class': 'clearfix'}),
    ('div', {'class': 'widget widget-bbcle-featuresubheader'}),
    ('div', {'id': 'heading-intermediate-level'})
]

for element in elements_to_remove:
    part = article.find(*element)
    if part:
        part.decompose()  # 删除该部分

# 从 URL 中提取最后一个斜杠后的部分作为文件名
file_name = url.split('/')[-1]

# 生成适配移动端的 HTML
mobile_html = f"""
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="./style.css">
</head>
<body>
    {article.prettify()}
</body>
</html>
"""

# 确保文件夹存在
folder_path = '一分钟英语'
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# 将生成的 HTML 保存到本地文件，文件名为 URL 最后的部分
file_path = os.path.join(folder_path, f'{file_name}.html')
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(mobile_html)

print(f"HTML 文件已保存：{file_path}")