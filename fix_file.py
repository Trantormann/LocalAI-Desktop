import os

# 修复 index.html
with open('templates/index.html', 'rb') as f:
    data = f.read()

# 找到 </html> 并截断后面的内容
end_marker = b'</html>'
idx = data.find(end_marker)
if idx != -1:
    clean_data = data[:idx + len(end_marker)] + b'\n'
    with open('templates/index.html', 'wb') as f:
        f.write(clean_data)
    print('index.html fixed')

# 修复 style.css
with open('static/css/style.css', 'rb') as f:
    data = f.read()

# 找到最后一个有效的 } 并截断
# 先检查是否有 null bytes
if b'\x00' in data:
    # 找到第一个 null byte 之前的内容
    idx = data.find(b'\x00')
    clean_data = data[:idx].rstrip() + b'\n'
    with open('static/css/style.css', 'wb') as f:
        f.write(clean_data)
    print('style.css fixed')
else:
    print('style.css already clean')

print('Done!')
