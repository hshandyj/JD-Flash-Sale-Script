#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import random
import logging
import requests
import configparser
import sys
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class JDSecKill(object):
    def __init__(self):
        try:
            # 先设置日志
            self.set_logger()
            
            # 读取配置文件
            self.config = self.get_config()
            self.logger.info("配置文件读取成功")
            
            # 同时输出到控制台和文件（根据配置决定是否输出到控制台）
            if not self.config.getboolean('config', 'disable_console_log', fallback=False):
                self.setup_console_logging()
            
            self.logger.info("开始初始化京东抢购脚本...")
            
            # 初始化变量
            self.sku_id = self.config.get('config', 'sku_id')
            self.buy_time = self.config.get('config', 'buy_time')
            self.buy_url = f"https://item.jd.com/{self.sku_id}.html"
            self.cookies = {}
            self.logger.info(f"初始化变量完成，商品ID: {self.sku_id}, 抢购时间: {self.buy_time}")
            self.logger.info(f"商品URL: {self.buy_url}")
            
            # 检查系统环境
            self.check_environment()
            
            # 创建浏览器对象
            self.logger.info("开始创建浏览器实例")
            self.browser = self.get_browser()
            self.logger.info("浏览器创建成功")
            
            # 登录状态
            self.is_login = False
            self.logger.info("脚本初始化完成")
        except Exception as e:
            self.logger.error(f"初始化错误: {e}")
            traceback.print_exc()
            raise
    
    def setup_console_logging(self):
        """设置控制台日志"""
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # 添加到logger
        self.logger.addHandler(console_handler)
        self.logger.info("控制台日志设置完成")
    
    def check_environment(self):
        """检查运行环境"""
        self.logger.info("检查运行环境")
        
        # 检查Python版本
        python_version = sys.version
        self.logger.info(f"Python版本: {python_version}")
        
        # 检查Selenium版本
        selenium_version = webdriver.__version__
        self.logger.info(f"Selenium版本: {selenium_version}")
        
        # 检查操作系统
        os_info = f"{sys.platform}"
        self.logger.info(f"操作系统: {os_info}")
        
        # 检查是否存在EdgeDriver
        try:
            import subprocess
            result = subprocess.run(['msedgedriver', '--version'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   shell=True)
            if result.returncode == 0:
                self.logger.info(f"EdgeDriver版本: {result.stdout.strip()}")
            else:
                self.logger.warning("无法获取EdgeDriver版本信息")
        except Exception as e:
            self.logger.warning(f"检查EdgeDriver时出错: {e}")
        
        self.logger.info("环境检查完成")
    
    def get_config(self):
        """读取配置文件"""
        self.logger.info("正在读取配置文件...")
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')
        self.logger.info("配置文件读取成功")
        return config
    
    def set_logger(self):
        """设置日志"""
        
        # 确保日志目录存在
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志文件路径
        log_file = os.path.join(log_dir, 'jd_seckill.log')
        
        # 创建logger
        self.logger = logging.getLogger('jd_seckill')
        self.logger.setLevel(logging.INFO)
        
        # 清除已有的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
        file_handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加到logger
        self.logger.addHandler(file_handler)
    
    def get_browser(self):
        """获取浏览器对象"""
        self.logger.info("开始配置浏览器选项")
        
        edge_options = Options()
        self.logger.info("创建Edge浏览器选项实例")
        
        # 添加详细的浏览器配置日志
        # 如果配置了无头模式，则启用
        if self.config.getboolean('config', 'headless'):
            edge_options.add_argument('--headless')
            self.logger.info("启用无头模式")
        else:
            self.logger.info("不使用无头模式")
            
        # 添加浏览器参数
        browser_args = [
            '--disable-gpu', 
            '--no-sandbox', 
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-popup-blocking',
            '--start-maximized'
        ]
        
        for arg in browser_args:
            edge_options.add_argument(arg)
            self.logger.info(f"添加浏览器参数: {arg}")
        
        self.logger.info("浏览器基本参数配置完成")
        
        # 使用配置的用户数据目录
        if self.config.get('config', 'edge_user_data'):
            user_data_dir = self.config.get('config', 'edge_user_data')
            self.logger.info(f"使用用户数据目录: {user_data_dir}")
            edge_options.add_argument(f'--user-data-dir={user_data_dir}')
        else:
            self.logger.info("不使用用户数据目录")
        
        try:
            self.logger.info("尝试创建Edge浏览器实例")
            browser = webdriver.Edge(options=edge_options)
            self.logger.info("Edge浏览器实例创建成功")
            
            # 获取浏览器版本信息
            try:
                browser_version = browser.capabilities['browserVersion']
                driver_version = browser.capabilities['msedge']['msedgedriverVersion'].split(' ')[0]
                self.logger.info(f"Edge版本: {browser_version}, EdgeDriver版本: {driver_version}")
            except:
                self.logger.warning("无法获取浏览器版本信息")
            
            return browser
        except Exception as e:
            self.logger.error(f"创建浏览器实例失败: {e}")
            traceback.print_exc()
            raise
    
    def login(self):
        """登录京东"""
        try:
            self.logger.info("开始登录京东")
            
            self.logger.info("访问京东登录页面")
            self.browser.get("https://passport.jd.com/new/login.aspx")
            
            self.logger.info("请扫描二维码登录")
            
            # 等待登录 - 使用多种可能的登录成功标志
            self.logger.info("等待登录完成，超时时间: 300秒")
            WebDriverWait(self.browser, 300).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'home.jd.com')]")),
                    EC.presence_of_element_located((By.CLASS_NAME, 'nickname')),
                    EC.presence_of_element_located((By.LINK_TEXT, '我的订单')),
                    EC.presence_of_element_located((By.LINK_TEXT, '我的京东')),
                    EC.presence_of_element_located((By.ID, 'ttbar-login'))
                )
            )
            
            # 保存cookies
            self.cookies = self.browser.get_cookies()
            self.is_login = True
            self.logger.info("登录成功")
            
            # 保存cookies到文件
            self.logger.info("保存cookies")
            with open('cookies.json', 'w') as f:
                json.dump(self.cookies, f)
            self.logger.info("cookies保存成功")
                
            return True
        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            traceback.print_exc()
            return False
    
    def check_login(self):
        """检查是否登录"""
        try:
            self.logger.info("检查登录状态")
        
            # 尝试先直接进行登录，不检查cookies
            self.logger.info("直接进行登录流程")
            return self.login()
        
        except Exception as e:
            self.logger.error(f"登录检查失败: {e}")
            traceback.print_exc()
            return self.login()  # 尝试重新登录
    
    def wait_for_buy_time(self):
        """等待抢购时间"""
        self.logger.info(f"等待抢购时间: {self.buy_time}")  
        try:
            target_time = datetime.strptime(self.buy_time, "%Y-%m-%d %H:%M:%S.%f")
            self.logger.info(f"目标抢购时间解析成功: {target_time}")
            
            while True:
                current_time = datetime.now()
                if current_time >= target_time:
                    self.logger.info("到达抢购时间，开始抢购")
                    break
                else:
                    remaining = (target_time - current_time).total_seconds()
                    self.logger.info(f"距离抢购时间还剩: {remaining:.2f}秒")
                    # 如果时间接近，缩短检查间隔
                    if remaining > 30:
                        time.sleep(10)
                    elif remaining > 5:
                        time.sleep(1)
                    else:
                        time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"等待抢购时间出错: {e}")
            traceback.print_exc()
    
    def seckill_by_direct(self):
        """直接抢购（直接进入结算页面）"""
        self.logger.info(f"开始直接抢购商品: {self.sku_id}")
        
        # 访问商品详情页
        self.logger.info(f"访问商品页面: {self.buy_url}")
        self.browser.get(self.buy_url)
        
        # 等待页面加载
        self.logger.info("等待页面加载完成...")
        WebDriverWait(self.browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        
        # 检查页面是否是商品页面
        if "京东" in self.browser.title and not "商品" in self.browser.title:
            self.logger.info("可能被重定向到首页，尝试再次访问商品页面")
            time.sleep(2)
            self.browser.get(self.buy_url)
            time.sleep(3)
        
        # 保存商品页面截图
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, f"direct_{self.sku_id}.png")
        self.browser.save_screenshot(screenshot_path)
        self.logger.info(f"已保存商品页面截图到{screenshot_path}")
        
        # 等待抢购时间
        self.logger.info("等待抢购时间")
        self.wait_for_buy_time()
        
        # 不断尝试点击抢购按钮
        max_retry = int(self.config.get('config', 'max_retry'))
        self.logger.info(f"开始尝试抢购，最大重试次数: {max_retry}")    
        
        # 定义可能的抢购按钮选择器 - 使用用户提供的实际按钮
        buy_button_selectors = [
            (By.ID, 'InitTradeUrl'),  # 立即购买
            (By.ID, 'InitCartUrl'),   # 加入购物车
            (By.CLASS_NAME, 'btn-special2'),  # 立即购买的class
            (By.CLASS_NAME, 'btn-special1'),  # 加入购物车的class
            (By.ID, 'btn-reservation'),
            (By.ID, 'btn-purchase'),
            (By.ID, 'purchase-button'),
            (By.LINK_TEXT, '抢购'),
            (By.LINK_TEXT, '立即抢购'),
            (By.LINK_TEXT, '立即购买')
        ]
        
        for i in range(max_retry):
            self.logger.info(f"第{i+1}次尝试")
            
            # 尝试各种抢购按钮选择器
            for by, selector in buy_button_selectors:
                try:
                    self.logger.info(f"尝试使用抢购按钮选择器: {by}={selector}")
                    
                    # 使用更短的等待时间，快速尝试多个选择器
                    button = WebDriverWait(self.browser, 1).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    
                    # 检查按钮文本是否包含抢购相关字眼
                    button_text = button.text.strip()
                    self.logger.info(f"找到按钮: {button_text}")
                    
                    # 任何按钮都尝试点击
                    self.logger.info(f"找到抢购按钮，点击: {button_text}")
                    button.click()
                    
                    # 保存点击抢购按钮后的截图
                    screenshot_path = os.path.join(screenshot_dir, f"after_click_{i+1}.png")
                    self.browser.save_screenshot(screenshot_path)
                    self.logger.info(f"已保存点击抢购按钮后的截图到{screenshot_path}")
                    
                    # 等待跳转到订单结算页面
                    self.logger.info("等待跳转到订单结算页面")
                    
                    # 尝试等待页面标题变为订单结算
                    try:
                        WebDriverWait(self.browser, 5).until(
                            lambda driver: "订单结算" in driver.title or 
                                         "确认订单" in driver.title or
                                         "下单" in driver.title or
                                         "order" in driver.current_url.lower()
                        )
                        self.logger.info("成功跳转到订单页面")
                    except:
                        self.logger.warning("等待跳转到订单页面超时")
                    
                    # 提交订单
                    self.logger.info("尝试提交订单")
                    
                    # 保存订单页面截图
                    screenshot_path = os.path.join(screenshot_dir, f"order_page_{i+1}.png")
                    self.browser.save_screenshot(screenshot_path)
                    
                    # 尝试各种提交订单按钮选择器
                    submit_selectors = [
                        (By.ID, 'order-submit'),
                        (By.CLASS_NAME, 'checkout-submit'),
                        (By.CLASS_NAME, 'btn-submit'),
                        (By.LINK_TEXT, '提交订单'),
                        (By.XPATH, "//button[contains(text(), '提交订单')]"),
                        (By.XPATH, "//a[contains(text(), '提交订单')]")
                    ]
                    
                    for submit_by, submit_selector in submit_selectors:
                        try:
                            self.logger.info(f"尝试使用提交订单按钮选择器: {submit_by}={submit_selector}")
                            
                            submit_button = WebDriverWait(self.browser, 2).until(
                                EC.element_to_be_clickable((submit_by, submit_selector))
                            )
                            submit_button.click()
                            
                            # 保存提交订单后的截图
                            screenshot_path = os.path.join(screenshot_dir, f"order_submitted_{i+1}.png")
                            self.browser.save_screenshot(screenshot_path)
                            
                            self.logger.info("抢购成功")
                            return True
                        except Exception as e:
                            self.logger.warning(f"点击提交订单按钮失败: {submit_by}={submit_selector}")
                            continue
                    
                    self.logger.warning("未找到提交订单按钮")   
                    break
                except Exception as e:
                    # 不记录每个选择器的错误，减少日志
                    continue
            
            # 刷新页面重试
            self.logger.info("刷新页面后重试")
            self.browser.refresh()
            
            # 等待页面加载
            try:
                WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
            except:
                self.logger.warning("页面刷新后加载超时")
                
            wait_time = random.uniform(0.1, 0.3)
            self.logger.info(f"等待{wait_time:.2f}秒后重试")
            time.sleep(wait_time)
        
        self.logger.info("达到最大重试次数，抢购失败")
        return False
    
    def run(self):
        """开始运行"""
        try:
            self.logger.info("脚本开始运行")
            
            # 检查登录状态
            self.logger.info("检查登录状态")
            if not self.check_login():
                self.logger.error("登录失败，终止程序")
                return
        
            self.logger.info("使用直接抢购模式")
            result = self.seckill_by_direct()
            
            if result:
                self.logger.info("抢购成功，请尽快完成支付")
            else:
                self.logger.info("抢购失败")
                
        except Exception as e:
            self.logger.error(f"运行过程中出现异常: {e}")
            traceback.print_exc()
        finally:
            # 如果不保持浏览器，则关闭
            if not self.config.getboolean('config', 'keep_browser'):
                self.logger.info("关闭浏览器")
                self.browser.quit()
            else:
                self.logger.info("保持浏览器窗口打开")
            
            self.logger.info("脚本运行结束")


if __name__ == "__main__":
    print("京东秒杀抢购脚本启动")
    try:
        seckill = JDSecKill()
        seckill.run()
    except KeyboardInterrupt:
        print("用户手动终止程序")
    except Exception as e:
        print(f"程序异常退出: {e}")
        traceback.print_exc()
    print("京东秒杀抢购脚本结束")