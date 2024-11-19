import time
from pyflink.common import WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema 
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common import WatermarkStrategy
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.stream_execution_environment import StreamExecutionEnvironment
from person_smile import Choosecheese
import save_pose
import base64
import boto3
import json
from multiprocessing import Process

aws_access_key="" 
aws_secret_key=""

def put_to_dynamodb(merge_dic):
    merge_dic['timestamp']= {'S': str(int(time.time()))}
    Dynamodb = boto3.client('dynamodb',aws_access_key_id=aws_access_key,aws_secret_access_key=aws_secret_key,region_name='ap-northeast-2')
    Dynamodb.put_item(TableName='BOAZ', Item=merge_dic)
    print(merge_dic)

def preprocessing(data):
    person_smile=Choosecheese()
    data_json=json.loads(data)
    image_data=data_json['Image_data']
    userid=data_json['Userid']

    pose_dic,b64_data=save_pose.simulation(image_data[2:-1])
    im_bytes = base64.b64decode(b64_data)
    
    person_dic=person_smile.search_and_add_users_by_image(userid,im_bytes)    
    merge_dic={**pose_dic,**person_dic}
    print(merge_dic)
    p = Process(target=put_to_dynamodb, args=(merge_dic,))
    p.start()
    p.join()


class FlinkProcessing:

    def __init__(self):
        self.env=StreamExecutionEnvironment.get_execution_environment()
        self.env.add_jars("file:///usr/script/flink/Driver/flink-connector-kafka-3.0.2-1.18.jar")
        self.env.add_jars("file:///usr/script/flink/Driver/kafka-clients-3.5.1.jar")
    def flink_processing(self):
        source = KafkaSource.builder() \
                .set_bootstrap_servers("172.22.0.8:9092") \
                .set_topics("mytopic") \
                .set_value_only_deserializer(SimpleStringSchema()) \
                .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
                .build()    
        self.env.from_source(source, WatermarkStrategy.no_watermarks(), "Kafka Source")\
            .map(preprocessing)\
            .print()
        self.env.execute()  


if __name__ == "__main__":
    test= FlinkProcessing()
    test.flink_processing()



