---
title: "Hugo 博客部署到腾讯云轻量服务器完整指南"
date: 2026-04-08T09:00:00+08:00
categories: ['教程', '运维']
tags: ['Hugo', '腾讯云', '部署', 'Nginx']
author: "plusluo"
---
本文手把手教你如何将 Hugo 静态博客部署到腾讯云轻量应用服务器，使用 Nginx 提供服务。

<!--more-->

## 第一步：构建静态文件

在本地执行 Hugo 构建命令：

```bash
hugo --minify
```

构建完成后，`public/` 目录下就是所有静态文件。

## 第二步：上传到服务器

使用 `rsync` 同步文件到服务器：

```bash
rsync -avz --delete public/ root@your-server:/var/www/plusluo-site/
```

## 第三步：配置 Nginx

```nginx
server {
    listen 80;
    server_name plusluo.site;
    root /var/www/plusluo-site;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

## 第四步：自动化部署

可以写一个简单的部署脚本 `deploy.sh`：

```bash
#!/bin/bash
echo "🚀 开始部署..."
hugo --minify
rsync -avz --delete public/ root@your-server:/var/www/plusluo-site/
echo "✅ 部署完成！"
```

大功告成！现在你的博客已经跑在云服务器上了。
