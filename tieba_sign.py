#!/usr/bin/env python3
"""
百度贴吧自动签到脚本
通过GitHub Actions定时执行，实现贴吧自动签到功能
"""

import requests
import json
import os
import time
import random
import re
from typing import Dict, List, Optional

class TiebaSigner:
    """百度贴吧自动签到类"""
    
    def __init__(self, username: str, password: str):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://tieba.baidu.com/',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        self.session.headers.update(self.headers)
        
    def login(self) -> bool:
        """登录百度账号"""
        try:
            # 获取登录页面
            login_page_url = "https://passport.baidu.com/v2/api/?login"
            self.session.get(login_page_url)
            
            # 获取token
            token_url = "https://passport.baidu.com/v2/api/?getapi&tpl=mn&apiver=v3&class=login"
            token_response = self.session.get(token_url)
            token_data = token_response.json()
            
            # 构建登录参数
            login_data = {
                'username': self.username,
                'password': self.password,
                'token': token_data['data']['token'],
                'tpl': 'mn',
                'apiver': 'v3',
                'tt': str(int(time.time() * 1000)),
                'codestring': '',
                'isPhone': 'false',
                'safeflg': '0',
                'u': 'https://tieba.baidu.com/',
                'staticpage': 'https://tieba.baidu.com/tb/static-common/html/pass/v3Jump.html',
                'loginType': '1',
                'callback': 'parent.bdPass.api.login._postCallback'
            }
            
            # 执行登录
            login_url = "https://passport.baidu.com/v2/api/?login"
            login_response = self.session.post(login_url, data=login_data)
            
            # 检查登录是否成功
            if 'err_no=0' in login_response.text:
                print("登录成功！")
                return True
            else:
                print("登录失败，请检查账号密码")
                return False
                
        except Exception as e:
            print(f"登录过程中发生错误: {e}")
            return False
    
    def get_followed_bars(self) -> List[str]:
        """获取关注的贴吧列表"""
        try:
            bars_url = "https://tieba.baidu.com/f/like/mylike"
            response = self.session.get(bars_url)
            
            # 使用正则表达式提取贴吧名称
            pattern = r'/f\?kw=([^"]+)"'
            bars = re.findall(pattern, response.text)
            
            # 去重并解码URL编码的贴吧名
            decoded_bars = []
            for bar in set(bars):
                try:
                    decoded_bar = requests.utils.unquote(bar)
                    decoded_bars.append(decoded_bar)
                except:
                    decoded_bars.append(bar)
            
            print(f"获取到 {len(decoded_bars)} 个关注的贴吧")
            return decoded_bars
            
        except Exception as e:
            print(f"获取贴吧列表失败: {e}")
            return []
    
    def sign_bar(self, bar_name: str) -> Dict:
        """对单个贴吧进行签到"""
        try:
            # 获取tbs参数
            tbs_url = "http://tieba.baidu.com/dc/common/tbs"
            tbs_response = self.session.get(tbs_url)
            tbs_data = tbs_response.json()
            tbs = tbs_data['tbs']
            
            # 构建签到参数
            sign_data = {
                'ie': 'utf-8',
                'kw': bar_name,
                'tbs': tbs
            }
            
            # 执行签到
            sign_url = "http://tieba.baidu.com/sign/add"
            response = self.session.post(sign_url, data=sign_data)
            result = response.json()
            
            # 添加随机延迟，避免请求过快
            time.sleep(random.uniform(1, 3))
            
            return result
            
        except Exception as e:
            print(f"签到 {bar_name} 时发生错误: {e}")
            return {'error': 'no', 'no': 999, 'error_msg': str(e)}
    
    def sign_all_bars(self) -> Dict:
        """对所有关注的贴吧进行签到"""
        if not self.login():
            return {'success': False, 'message': '登录失败'}
        
        bars = self.get_followed_bars()
        if not bars:
            return {'success': False, 'message': '获取贴吧列表失败'}
        
        results = {
            'success': True,
            'total': len(bars),
            'signed': 0,
            'already_signed': 0,
            'failed': 0,
            'details': []
        }
        
        for bar in bars:
            print(f"正在签到: {bar}")
            result = self.sign_bar(bar)
            
            # 解析签到结果
            if result.get('no') == 0:
                status = "签到成功"
                results['signed'] += 1
            elif result.get('no') == 1101:
                status = "已签到"
                results['already_signed'] += 1
            else:
                status = f"签到失败: {result.get('error_msg', '未知错误')}"
                results['failed'] += 1
            
            detail = {
                'bar_name': bar,
                'status': status,
                'result': result
            }
            results['details'].append(detail)
            
            print(f"{bar}: {status}")
        
        return results

def main():
    """主函数"""
    # 从环境变量获取账号密码
    username = os.getenv('TIEBA_USERNAME')
    password = os.getenv('TIEBA_PASSWORD')
    
    if not username or not password:
        print("错误: 未设置贴吧账号或密码")
        print("请在GitHub仓库的Secrets中设置TIEBA_USERNAME和TIEBA_PASSWORD")
        return
    
    # 创建签到器并执行签到
    signer = TiebaSigner(username, password)
    results = signer.sign_all_bars()
    
    # 输出结果
    print("\n=== 签到结果 ===")
    print(f"总贴吧数: {results['total']}")
    print(f"成功签到: {results['signed']}")
    print(f"已签到: {results['already_signed']}")
    print(f"签到失败: {results['failed']}")
    
    # 保存结果到文件，供GitHub Actions使用
    with open('sign_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 生成简化的结果摘要
    summary = {
        'total': results['total'],
        'signed': results['signed'],
        'already_signed': results['already_signed'],
        'failed': results['failed'],
        'timestamp': time.time()
    }
    
    with open('summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()