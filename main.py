import os
import json
import re
from typing import Dict, Any, List, Union
from mcp.server.fastmcp import FastMCP
from alibabacloud_cdn20180510.client import Client
from alibabacloud_cdn20180510.models import (
    AddCdnDomainRequest,
    ModifyCdnDomainRequest,
    BatchSetCdnDomainConfigRequest
)
from alibabacloud_tea_openapi import models as open_api_models

# 创建FastMCP实例
mcp = FastMCP("AliyunCDN")

def parse_source_info(source: Union[str, Dict]) -> Dict[str, Any]:
    """解析源站信息
    支持以下格式:
    1. IP地址: "1.2.3.4:80"
    2. 域名: "example.com:80"
    3. OSS域名: "oss://bucket.oss-cn-hangzhou.aliyuncs.com"
    4. 完整配置: {"type": "ipaddr", "content": "1.2.3.4", "port": 80}
    """
    if isinstance(source, dict):
        return source
        
    if isinstance(source, str):
        # 处理OSS格式
        if source.startswith("oss://"):
            return {
                "type": "oss",
                "content": source.replace("oss://", ""),
                "port": 80
            }
        
        # 处理IP或域名格式
        parts = source.split(":")
        content = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 80
        
        # 判断是否为IP地址
        is_ip = bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", content))
        
        return {
            "type": "ipaddr" if is_ip else "domain",
            "content": content,
            "port": port
        }
    
    raise ValueError("无效的源站格式")

def parse_cache_rule(rule: Union[str, Dict]) -> Dict[str, Any]:
    """解析缓存规则
    支持以下格式:
    1. 简单格式: "*.jpg:3600"
    2. 完整格式: {"path_pattern": "/*.jpg", "ttl": 3600}
    """
    if isinstance(rule, dict):
        return rule
        
    if isinstance(rule, str):
        pattern, ttl = rule.split(":")
        return {
            "path_pattern": pattern if pattern.startswith("/") else f"/{pattern}",
            "ttl": int(ttl)
        }
    
    raise ValueError("无效的缓存规则格式")

def parse_header(header: Union[str, Dict]) -> Dict[str, str]:
    """解析HTTP头
    支持以下格式:
    1. 简单格式: "Content-Type:text/html"
    2. 完整格式: {"key": "Content-Type", "value": "text/html"}
    """
    if isinstance(header, dict):
        return header
        
    if isinstance(header, str):
        key, value = header.split(":")
        return {"key": key.strip(), "value": value.strip()}
    
    raise ValueError("无效的HTTP头格式")

# CDN客户端配置
def create_cdn_client() -> Client:
    """创建阿里云CDN客户端"""
    config = open_api_models.Config(
        access_key_id=os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
        access_key_secret=os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
        region_id="cn-hangzhou"
    )
    return Client(config)

cdn_client = create_cdn_client()

@mcp.tool()
def add_cdn_domain(
    domain_name: str, 
    sources: Union[str, List[Union[str, Dict]]], 
    cdn_type: str = "web"
) -> str:
    """添加CDN加速域名
    
    Args:
        domain_name: 加速域名
        sources: 源站信息，支持以下格式:
                - 单个源站: "1.2.3.4:80" 或 "example.com:80" 或 "oss://bucket.oss-cn-hangzhou.aliyuncs.com"
                - 多个源站: ["1.2.3.4:80", "2.3.4.5:80"]
                - 完整配置: [{"type": "ipaddr", "content": "1.2.3.4", "port": 80}]
        cdn_type: CDN加速类型:
                - web: 图片小文件
                - download: 大文件下载
                - video: 视音频点播
                - live: 视音频直播
    """
    # 处理单个源站的情况
    if isinstance(sources, (str, dict)):
        sources = [sources]
    
    # 解析所有源站信息
    parsed_sources = [parse_source_info(source) for source in sources]
    
    # 创建请求对象
    request = AddCdnDomainRequest(
        domain_name=domain_name,
        sources=str(parsed_sources),
        cdn_type=cdn_type
    )
    
    # 发送请求
    response = cdn_client.add_cdn_domain(request)
    return f"域名 {domain_name} 添加成功"

@mcp.tool()
def delete_cdn_domain(domain_name: str) -> str:
    """删除CDN加速域名
    
    Args:
        domain_name: 要删除的加速域名
    """
    response = cdn_client.delete_cdn_domain(domain_name)
    return f"域名 {domain_name} 删除成功"

@mcp.tool()
def modify_cdn_source(domain_name: str, sources: List[Dict[str, Any]]) -> str:
    """修改CDN源站配置
    
    Args:
        domain_name: 加速域名
        sources: 新的源站信息
    """
    request = ModifyCdnDomainRequest(
        domain_name=domain_name,
        sources=str(sources)
    )
    response = cdn_client.modify_cdn_domain(request)
    return f"域名 {domain_name} 源站修改成功"

@mcp.tool()
def set_cdn_source_port(domain_name: str, port: int) -> str:
    """设置CDN源站端口
    
    Args:
        domain_name: 加速域名
        port: 回源端口,支持443/80等
    """
    config = {
        "functionArgs": [
            {
                "argName": "port",
                "argValue": str(port)
            }
        ],
        "functionName": "origin_port"
    }
    
    request = BatchSetCdnDomainConfigRequest(
        domain_names=domain_name,
        functions=json.dumps([config])
    )
    response = cdn_client.batch_set_cdn_domain_config(request)
    return f"域名 {domain_name} 回源端口设置成功"

@mcp.tool()
def set_cdn_protocol(domain_name: str, protocol: str) -> str:
    """设置CDN回源协议
    
    Args:
        domain_name: 加速域名
        protocol: 回源协议(HTTP/HTTPS/FOLLOW)
    """
    config = {
        "functionArgs": [
            {
                "argName": "protocol",
                "argValue": protocol
            }
        ],
        "functionName": "back_to_origin_protocol"
    }
    
    request = BatchSetCdnDomainConfigRequest(
        domain_names=domain_name,
        functions=json.dumps([config])
    )
    response = cdn_client.batch_set_cdn_domain_config(request)
    return f"域名 {domain_name} 回源协议设置成功"

@mcp.tool()
def set_cdn_cache(
    domain_name: str, 
    cache_rules: Union[str, List[Union[str, Dict]]]
) -> str:
    """设置CDN缓存策略
    
    Args:
        domain_name: 加速域名
        cache_rules: 缓存规则，支持以下格式:
                    - 单个规则: "*.jpg:3600"
                    - 多个规则: ["*.jpg:3600", "*.png:7200"]
                    - 完整配置: [{"path_pattern": "/*.jpg", "ttl": 3600}]
    """
    # 处理单个规则的情况
    if isinstance(cache_rules, (str, dict)):
        cache_rules = [cache_rules]
    
    # 解析所有缓存规则
    parsed_rules = [parse_cache_rule(rule) for rule in cache_rules]
    
    # 构造参数
    function_args = []
    for rule in parsed_rules:
        function_args.extend([
            {
                "argName": "ttl",
                "argValue": str(rule["ttl"])
            },
            {
                "argName": "path",
                "argValue": rule["path_pattern"]
            }
        ])
    
    config = {
        "functionArgs": function_args,
        "functionName": "cache_ttl"
    }
    
    request = BatchSetCdnDomainConfigRequest(
        domain_names=domain_name,
        functions=json.dumps([config])
    )
    response = cdn_client.batch_set_cdn_domain_config(request)
    return f"域名 {domain_name} 缓存策略设置成功"

@mcp.tool()
def set_cdn_https(domain_name: str, ssl_protocol: str, cert_name: str, cert_type: str) -> str:
    """配置HTTPS设置
    
    Args:
        domain_name: 加速域名
        ssl_protocol: SSL协议
        cert_name: 证书名称
        cert_type: 证书类型
    """
    config = {
        "functionArgs": [
            {
                "argName": "ssl_protocol",
                "argValue": ssl_protocol
            },
            {
                "argName": "cert_name",
                "argValue": cert_name
            },
            {
                "argName": "cert_type",
                "argValue": cert_type
            }
        ],
        "functionName": "https"
    }
    
    request = BatchSetCdnDomainConfigRequest(
        domain_names=domain_name,
        functions=json.dumps([config])
    )
    response = cdn_client.batch_set_cdn_domain_config(request)
    return f"域名 {domain_name} HTTPS配置设置成功"

@mcp.tool()
def set_cdn_headers(
    domain_name: str, 
    headers: Union[str, List[Union[str, Dict]]]
) -> str:
    """配置HTTP响应头
    
    Args:
        domain_name: 加速域名
        headers: HTTP头配置，支持以下格式:
                - 单个头: "Content-Type:text/html"
                - 多个头: ["Content-Type:text/html", "Cache-Control:no-cache"]
                - 完整配置: [{"key": "Content-Type", "value": "text/html"}]
    """
    # 处理单个头的情况
    if isinstance(headers, (str, dict)):
        headers = [headers]
    
    # 解析所有HTTP头
    parsed_headers = [parse_header(header) for header in headers]
    
    function_args = []
    for header in parsed_headers:
        function_args.append({
            "argName": "key",
            "argValue": header["key"]
        })
        function_args.append({
            "argName": "value",
            "argValue": header["value"]
        })
    
    config = {
        "functionArgs": function_args,
        "functionName": "custom_response_header"
    }
    
    request = BatchSetCdnDomainConfigRequest(
        domain_names=domain_name,
        functions=json.dumps([config])
    )
    response = cdn_client.batch_set_cdn_domain_config(request)
    return f"域名 {domain_name} HTTP响应头设置成功"

# 资源示例
@mcp.resource("cdn://domain/{domain_name}")
def get_domain_info(domain_name: str) -> Dict[str, Any]:
    """获取CDN域名信息
    
    Args:
        domain_name: CDN加速域名
    """
    # 这里可以实现获取域名详细信息的逻辑
    return {
        "domain": domain_name,
        "status": "running",
        "type": "web",
        "created_at": "2024-03-20"
    }

# 提示示例
@mcp.prompt()
def cdn_operation_prompt(operation: str, domain_name: str) -> str:
    """创建CDN操作的提示
    
    Args:
        operation: 操作类型
        domain_name: 域名
    """
    return f"请确认是否要对域名 {domain_name} 执行 {operation} 操作？"

@mcp.tool()
def setup_cdn_with_text(text: str) -> str:
    """通过自然语言文本配置CDN
    
    Args:
        text: 包含CDN配置需求的文本，例如：
              "帮我添加一个加速域名
               加速类型为 大文件下载
               mygslb04.xiangyuncdn.com
               源站类型，ipaddr
               源站的IP地址 211.131.56.91
               回源端口 81
               设置图片缓存1小时"
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 解析域名
    domain_name = None
    cdn_type = None
    source_type = None
    source_ip = None
    source_port = None
    cache_rules = []
    
    for line in lines:
        # 解析域名
        if '.xiangyuncdn.com' in line:
            domain_name = line.strip()
        
        # 解析加速类型
        elif '加速类型' in line:
            if '大文件下载' in line:
                cdn_type = 'download'
            elif '图片小文件' in line or '小文件' in line:
                cdn_type = 'web'
            elif '视音频' in line and '直播' in line:
                cdn_type = 'live'
            elif '视音频' in line:
                cdn_type = 'video'
        
        # 解析源站类型
        elif '源站类型' in line:
            if 'ipaddr' in line:
                source_type = 'ipaddr'
            elif 'domain' in line:
                source_type = 'domain'
            elif 'oss' in line:
                source_type = 'oss'
        
        # 解析源站IP
        elif 'IP地址' in line:
            source_ip = re.findall(r'\d+\.\d+\.\d+\.\d+', line)[0]
        
        # 解析端口
        elif '端口' in line:
            source_port = int(re.findall(r'\d+', line)[0])
        
        # 解析缓存规则
        elif '缓存' in line:
            if '图片' in line:
                pattern = '*.jpg,*.jpeg,*.png,*.gif'
            elif '视频' in line:
                pattern = '*.mp4,*.flv,*.m3u8'
            else:
                pattern = '*'
            
            # 解析时间
            hours = 1  # 默认1小时
            if '小时' in line:
                hours = int(re.findall(r'\d+', line)[0])
            elif '天' in line:
                hours = int(re.findall(r'\d+', line)[0]) * 24
            
            ttl = hours * 3600
            for ext in pattern.split(','):
                cache_rules.append(f"{ext}:{ttl}")
    
    if not domain_name:
        return "未能在文本中找到域名信息"
    
    # 构造源站信息
    source = {
        "type": source_type or "ipaddr",
        "content": source_ip,
        "port": source_port or 80
    }
    
    # 添加域名
    result = add_cdn_domain(
        domain_name=domain_name,
        sources=source,
        cdn_type=cdn_type or "web"
    )
    
    # 如果有缓存规则，设置缓存
    if cache_rules:
        set_cdn_cache(domain_name, cache_rules)
    
    return f"已完成CDN配置：\n{result}"

if __name__ == "__main__":
    mcp.run()
