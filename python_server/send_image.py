from confluent_kafka import Producer
import base64
import json
def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

p = Producer({'bootstrap.servers': '172.22.0.8'})

with open('/usr/script/python/data/1p_1.jpeg', 'rb') as f:
    data = f.read()
    encoded_data = base64.b64encode(data)


data= {'Userid':'test',
       'Image_data':str(encoded_data)}
json_data = json.dumps(data)
p.produce('mytopic', json_data, callback=delivery_report)

p.flush()