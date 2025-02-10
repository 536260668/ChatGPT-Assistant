import os
os.environ["http_proxy"] = "http://127.0.0.1:7890"
os.environ["https_proxy"] = "http://127.0.0.1:7890"
import dotenv
import pprint
import json
from typing import List,Dict
from collections import defaultdict #可以自动实现 if notexist x=1；if exist x = x + 1
from fastapi import FastAPI,WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 允许的源列表，可以设置为 ["*"] 允许所有。 生产环境请明确指定来源
    allow_credentials=True,          # 是否允许 Cookie 等凭证
    allow_methods=["*"],             # 允许所有 HTTP 方法 (GET, POST, PUT, DELETE, OPTIONS, 等)
    allow_headers=["*"],             # 允许所有请求头
)

dotenv.load_dotenv()
print(os.getenv("API_KEY"))
from httpx import AsyncClient

async def non_stream_request(var:List[Dict[str,str]]): #初始化，List中的每一个元素都是一个dict（List[Dict]），该dict的键、值都是str（Dict[str,str]）
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.getenv("API_KEY"),
    }
    json_data  = {
       "model": "gpt-4o-mini",
        "messages":var,
        "temperature":0.7,
        "stream":False,
        "n":1,
        "max_tokens":1000,
    }
    async with AsyncClient() as client:
        response = await client.post(url=url,headers=headers,json=json_data,timeout=60)
        pprint.pprint(response.json())

async def stream_request(var:List[Dict[str,str]]): #初始化，List中的每一个元素都是一个dict（List[Dict]），该dict的键、值都是str（Dict[str,str]）
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.getenv("API_KEY"),
    }
    json_data  = {
       "model": "gpt-4o-mini",
        "messages":var,
        "temperature":0.7,
        "stream":True,
        "n":1,
        "max_tokens":1000,
    }
    async with AsyncClient() as client:
        async with client.stream("POST",url=url,headers=headers,json=json_data,timeout=60) as response:
            async for line in response.aiter_lines():
                if line.strip()=="":
                    continue
                line = line.replace("data: ","")
                if line == "[DONE]":
                    break
                data = json.loads(line)
                if data.get("choices") is None or len(data.get("choices")) == 0 or data.get("choices")[0].get('finish_reason') is not None:
                    return
                yield data.get("choices")[0]

@app.websocket("/chat")
async def chat(websocket:WebSocket):
    await websocket.accept()
    message = []
    while True:
        json_data_received = await websocket.receive_json()
        # data = await websocket.receive_text()
        data = json_data_received.get("data")
        passwd =  json_data_received.get("passwd")
        print(passwd)
        if data == "quit" or passwd != "passwd":
            await websocket.close()
            break
        message.append({"role": "user", "content": data})
        chat_msg = defaultdict(str)
        async for i in stream_request(message):
            print(i)
            if i.get('delta').get('role'):
                chat_msg['role'] = i.get('delta').get('role')
            if i.get('delta').get('content'):
                chat_msg['content'] += i.get('delta').get('content')
                await websocket.send_text( i.get('delta').get('content'))
        message.append(chat_msg)

if __name__ == "__main__":
    import asyncio

    # asyncio.run(non_stream_request([{"role": "user", "content": "Say this is a test!"}]))
    # asyncio.run(stream_request([{"role": "user", "content": "Say this is a test!"}]))
    # asyncio.run(chat("Say this is a test!"))
    import uvicorn
    uvicorn.run("chatgpt_api:app",host="0.0.0.0",port=8000,reload=True)
