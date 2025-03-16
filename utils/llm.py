import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
from utils.common import logger, returnConfigData, returnVideoCacheFolder, downloadFile, encode_image

configData = returnConfigData()['llmServer']

model_dict = {
    'gemini-2.0-flash-exp': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'gemini-2.0-flash-exp'
    },
    'gemini-1.5-pro': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'gemini-1.5-pro'
    },
    'gemini-1.5-flash': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'gemini-1.5-flash'
    },
    'gemini-1.0-pro': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'gemini-1.0-pro'
    },
    'ernie-128k': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'ERNIE-Speed-128K'
    },
    'hunyuan': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'hunyuan-lite'
    },
    'spark': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'spark-lite'
    },
    'glm4-flash': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'glm-4-flash'
    },
    'glm4v-flash': {
        'api_key': configData['oa_api_key'],
        'base_url': configData['oa_base_url'],
        'model_name': 'glm-4v-flash'
    },
    'glm4-9b': {
        'api_key': configData['sf_api_key'],
        'base_url': 'https://api.siliconflow.cn/v1',
        'model_name': 'THUDM/glm-4-9b-chat'
    },
    'qwen2-7b': {
        'api_key': configData['sf_api_key'],
        'base_url': 'https://api.siliconflow.cn/v1',
        'model_name': 'Qwen/Qwen2.5-7B-Instruct'
    },
    'gemma2-9b':{
        'api_key': configData['sf_api_key'],
        'base_url': 'https://api.siliconflow.cn/v1',
        'model_name': 'google/gemma-2-9b-it'
    },
    'internlm':{
        'api_key': configData['il_api_key'],
        'base_url': 'https://internlm-chat.intern-ai.org.cn/puyu/api/v1',
        'model_name': 'internlm2.5-latest'
    },
    'groq':{
        'api_key': configData['groq_api_key'],
        'base_url': 'https://api.groq.com/openai/v1',
        'model_name': 'llama-3.1-70b-versatile'
    }
}

image_model_dict = {
    'Kwai-Kolors/Kolors': {
        'model_name': 'Kwai-Kolors/Kolors',
        'image_size': '1024x1024',
    },
    'flux': {
        'model_name': 'black-forest-labs/FLUX.1-schnell', # dev 0.18/张
        'image_size': '1024x576',
    },
    'sd3': {
        'model_name': 'stabilityai/stable-diffusion-3-medium',
        'image_size': '1536x1024',
    },
    'sdxl':{
        'model_name': 'stabilityai/stable-diffusion-xl-base-1.0',
        'image_size': '1536x1024',
    }
}

class LLM_API:
    def __init__(self, api_key, base_url, model):
        self.client =  OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
    
    def __call__(self, messages, temperature=0.7):
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=False
            )
            return completion.choices[-1].message.content
        except Exception as e:
            logger.error(f'LLM error: {e}')
            return ''

class UniLLM:
    def __init__(self):
        model_names = list(model_dict.keys())
        self.models = {name: LLM_API(api_key=model_dict[name]['api_key'], base_url=model_dict[name]['base_url'], model=model_dict[name]['model_name']) for name in model_names}

    def __call__(self, model_name_list, messages, temperature=0.7):
        for model_name in model_name_list:
            model = self.models.get(model_name)
            res = model(messages, temperature=temperature)
            if res:
                return res.strip()
        return ''

def generate_image(prompt='a cat', model='flux', img_size=None, batch_size=1):
    model_name = image_model_dict[model]['model_name']
    if not img_size:
        img_size = image_model_dict[model]['image_size']
    url = f"https://api.siliconflow.cn/v1/{model_name}/text-to-image"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {configData['sf_api_key']}"
    }
    data = {
        'prompt': prompt,
        'image_size': img_size,
        'batch_size': batch_size,
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        data = response.json()
        img_urls = [img['url'] for img in data['images']]
        return img_urls
    else:
        logger.error(f'{response.status_code}, 图片生成失败')
        return []

def generate_video(prompt='a cat running on a treadmill'):
    response = requests.post(configData['video_api_url'], json={"prompt": prompt, "num_frames": 25}, timeout=300)
    if response.status_code == 200:
        # 保存视频文件
        file_path = os.path.join(returnVideoCacheFolder, f"generate_video_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4")
        with open(file_path, "wb") as f:
            f.write(response.content)
        logger.info("视频生成成功")
        return file_path
    else:
        logger.error(f'{response.status_code}, 视频生成失败')
        return ''

def generate_video_sf(prompt='a cat running on a treadmill'):
    headers = {
        "Authorization": f"Bearer {configData['sf_api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "Lightricks/LTX-Video",
        "prompt": prompt,
        "seed": 2024,
    }
    response = requests.request("POST", "https://api.siliconflow.cn/v1/video/submit", json=payload, headers=headers)
    if response.status_code == 200:
        rid = response.json()['requestId']
        st = time.time()
        while True:
            response = requests.request("POST", "https://api.siliconflow.cn/v1/video/status", json={"requestId": rid}, headers=headers)
            if response.status_code == 200 and response.json()['status'] == 'Succeed':
                url = response.json()['results']['videos'][0]['url']
                file_path = downloadFile(url, prefix='ltx_video_', suffix='.mp4', type='video')
                logger.info("视频生成成功")
                return file_path
            elif time.time() - st > 120:
                logger.error(f"视频生成超时")
                return ''
            else:
                logger.info(f"视频生成中，{rid}")
            time.sleep(5)
    else:
        logger.error(f'{response.status_code}, 视频生成失败')
        return ''

def generate_math_solution(image_path=None, text=''):
    data = {
        "image": encode_image(image_path=image_path) if image_path else '',
        "text": text
    }
    response = requests.post(configData['math_api_url'], json=data)
    if response.status_code == 200:
        logger.info(f"{text} 解题请求成功")
        rid = response.json()['response_id']
        st = time.time()
        while True:
            response = requests.get(f"{configData['math_output_url']}/{rid}")
            if response.status_code == 200 and response.json()['status'] == True:
                return response.json()['text']
            elif time.time() - st > 180:
                logger.error(f"{text} 解题超时")
                return ''
            else:
                logger.info(f"{text} 解题等待 {rid}")
            time.sleep(5)
    else:
        logger.error(f'{response.status_code}, 解题请求失败')
        return ''

def generate_article(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    }
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        try:
            # title = soup.find('h1', attrs={'id': 'activity-name'}).get_text().strip()
            content = soup.find('div', attrs={'id': 'js_content'}) # html文件
            content = content.get_text().strip()
            dateframe = re.findall(r'var ct\s*=\s*.*\d{10}', str(soup))
            date = re.split('"', dateframe[0]) 
            date = time.strftime("%Y-%m-%d",time.localtime(int(date[1])))
            return {'content': content, 'date': date}
        except Exception as e:
            logger.error(f'文章解析失败 {e}')
            return {}
    else:
        logger.error(f'{response.status_code}, 文章获取失败')
        return {}

def test_vlm():
    model_name = 'gemini-1.5-flash'
    model = model_dict[model_name]
    llm = LLM_API(api_key=model['api_key'], base_url=model['base_url'], model=model['model_name'])
    base64_image = encode_image('output/emoji.jpg')
    messages = [
        {'role': 'user', 'content': [
            {"type": "text", "text": "这是用户发送的一个表情包图片，请理解图片内容，给我回复表情包的一个关键词，无需任何标点符号。"},
            {
            "type": "image_url",
            "image_url": {
                # "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                "url": f"data:image/jpeg;base64,{base64_image}"
            },
            }
        ]}
    ]
    result = llm(messages)
    print(result.strip())

def test_llm():
    model_name = 'groq'
    model = model_dict[model_name]
    llm = LLM_API(api_key=model['api_key'], base_url=model['base_url'], model=model['model_name'])
    messages = [{'role': 'user', 'content': '你好'}]
    result = llm(messages)
    print(result.strip())

if __name__ == '__main__':
    test_llm()
    