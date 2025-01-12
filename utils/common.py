import os
import yaml
import base64
import logging
import requests
from datetime import datetime

def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 创建一个文件处理器，用于写入日志文件
    log_path = os.path.join(os.path.dirname(__file__), '../logs')
    os.makedirs(log_path, exist_ok=True)
    file_handler = logging.FileHandler(f'{log_path}/app_{datetime.now().strftime("%Y%m%d%H%M%S")}.log', encoding='utf-8')
    # file_handler = logging.FileHandler(f'{log_path}/debug.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # 创建一个日志格式器，并设置格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(formatter)
    # 将处理器添加到 logger
    logger.addHandler(file_handler)
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

# 设置全局 logger
logger = setup_logger()

# 设置全局配置
def returnConfigData():
    """
    返回配置文件数据（YAML格式）
    :return:
    """
    current_path = os.path.dirname(__file__)
    configData = yaml.load(open(current_path + '/../config.yaml', mode='r', encoding='UTF-8'), yaml.Loader)
    return configData

def saveConfigData(configData):
    """
    保存配置
    :param configData:
    :return:
    """
    current_path = os.path.dirname(__file__)
    with open(current_path + '/../config.yaml', mode='w') as file:
        yaml.dump(configData, file)

# 设置数据存储
def returnCachePath():
    """
    返回缓存文件夹路径
    :return:
    """
    cache_path = os.path.join(os.path.dirname(__file__), '../output')
    os.makedirs(cache_path, exist_ok=True)
    return cache_path

def returnPicCacheFolder():
    """
    返回图片缓存文件夹
    :return:
    """
    return returnCachePath() + '/picCacheFolder'

def returnVideoCacheFolder():
    """
    返回视频缓存文件夹
    :return:
    """
    return returnCachePath() + '/videoCacheFolder'

def returnAvatarFolder():
    """
    返回微信头像缓存文件夹
    :return:
    """
    return returnCachePath() + '/weChatAvatarFolder'

def clearCacheFolder():
    """
    清空缓存文件夹所有文件
    :return:
    """
    file_lists = []
    file_lists += [returnPicCacheFolder() + '/' + file for file in os.listdir(returnPicCacheFolder())]
    file_lists += [returnVideoCacheFolder() + '/' + file for file in os.listdir(returnVideoCacheFolder())]
    file_lists += [returnAvatarFolder() + '/' + file for file in os.listdir(returnAvatarFolder())]
    for rm_file in file_lists:
        os.remove(rm_file)
    return True

def initCacheFolder():
    """
    初始化缓存文件夹
    :return:
    """
    if not os.path.exists(returnPicCacheFolder()):
        os.mkdir(returnPicCacheFolder())
    if not os.path.exists(returnVideoCacheFolder()):
        os.mkdir(returnVideoCacheFolder())
    if not os.path.exists(returnAvatarFolder()):
        os.mkdir(returnAvatarFolder())
    logger.info(f'初始化缓存文件夹成功!!!')

def encode_image(image_path='', image_bin=None):
    if image_bin:
        return base64.b64encode(image_bin).decode('utf-8')
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def downloadFile(url, prefix='moyu_', suffix='.jpg', type='pic'):
    if type == 'pic':
        root_path = returnPicCacheFolder()
    elif type == 'video':
        root_path = returnVideoCacheFolder()
    elif type == 'avatar':
        root_path = returnAvatarFolder()
    else:
        root_path = returnCachePath()
    content = requests.get(url, timeout=30)
    if content.status_code == 200:
        file_name = prefix + datetime.now().strftime('%Y%m%d%H%M%S') + suffix
        file_path = os.path.join(root_path, file_name)
        with open(file_path, 'wb') as f:
            f.write(content.content)
        return file_path
    else:
        return ''