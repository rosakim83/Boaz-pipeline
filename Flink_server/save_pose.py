import boto3
import base64
import requests
import os
import random

def simulation(data):

    api_key=os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": "이미지를 분석해서 인원수,포즈,분위기를 : 형식으로 답변해줘 그리고 포즈 같은 경우에는 [브이, 꽃받침, 하트, 팔짱, 뽀뽀, 엄지올리기, 윙크]만 식별해서 답변해줘. \
                                    분위기는[사랑스러운, 귀여운, 즐거운, 장난스러운, 화목한, 무서움]\
                                    추가적인 설명은 하지 말고 예시랑 똑같이 답변해줘 \
                                    EX1)detected_pose: 브이, 하트/ detected_mood: 귀여운, 장난스러운,무서움\
                                    EX2)detected_pose: 꽃받침, 손하트, 팔짱/ detected_mood: 귀여운,사랑스러운,화목한"
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{data}"
            }
            }
        ]
        }
    ],
    "max_tokens": 300
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response = response.json()
    print(response)
    content_dic={}
    content= response['choices'][0]['message']['content']
    content_list=content.split("/")
    for item in content_list:
        if ':' in item:
            key, value = item.split(':')
            content_dic[key] = {'SS':[v.strip() for v in value.split(',')]}
        else:
            print(item)
            break

    return content_dic,data
if __name__ == '__main__':
    print(simulation('sd'))