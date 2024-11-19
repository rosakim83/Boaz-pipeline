import boto3
from botocore.exceptions import ClientError
import logging
import io
from PIL import Image, ImageDraw
import re
import time

aws_access_key="" 
aws_secret_key=""


class Choosecheese:
    def __init__(self):
        self.s3=boto3.client('s3',aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name='ap-northeast-2')
        self.logger = logging.getLogger(__name__)
        self.session = boto3.Session(aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name='ap-northeast-2')
        self.client = self.session.client('rekognition')

    #이미지 속 사람 얼굴 바운딩 박스 그리기
    def draw_bounding_box(self,bounding_boxs):
        img = Image.open(io.BytesIO(self.image_data))
        draw = ImageDraw.Draw(img)
        for bounding_box in bounding_boxs:
            width, height = img.size
            left = bounding_box['Left'] * width
            top = bounding_box['Top'] * height
            right = (bounding_box['Left'] + bounding_box['Width']) * width
            bottom = (bounding_box['Top'] + bounding_box['Height']) * height
            draw.rectangle(((left, top), (right, bottom)), outline=(255, 0, 0))
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        byte_img = byte_arr.getvalue()
        return byte_img
    
    # 네컷사진 프레임 별 crop 후 이미지 추출 
    def crop_face_from_image(self, bounding_box):
        # 이미지 로드
        img = Image.open(io.BytesIO(self.image_data))
        # BoundingBox에서 얼굴 위치와 크기 추출
        width, height = img.size
        left = bounding_box['Left'] * width
        top = bounding_box['Top'] * height
        right = (bounding_box['Left'] + bounding_box['Width']) * width
        bottom = (bounding_box['Top'] + bounding_box['Height']) * height
        # 이미지 크롭
        cropped_img = img.crop((left, top, right, bottom))
        # 크롭된 이미지를 바이트로 변환
        byte_arr = io.BytesIO()
        cropped_img.save(byte_arr, format='JPEG')
        byte_img = byte_arr.getvalue()
        return byte_img

    #저장된 가장 마지막 파일 이름 가져오기
    def get_last_file_in_folder(self, folder_name,bucket_name):    
        # 폴더 내의 객체 목록 가져오기
        response = self.s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix=folder_name
        )
        # 객체 목록이 비어있지 않은 경우
        if 'Contents' in response:
            # 객체 목록을 사전 순으로 정렬
            files = sorted(response['Contents'], key=lambda x: x['Key'])
            # 가장 마지막 파일의 이름 반환
            last_file_name = files[-1]['Key']
            last_file_name=re.sub(r'\..*','', last_file_name)
            return int(last_file_name.split('/')[-1])
        return 0
    #얼굴이 옆모습 혹은 너무 많이 가려져있는지 확인
    def is_face(self,face):
        response = self.client.detect_faces(Image= {'Bytes': face},Attributes=['ALL'])
        if response['FaceDetails'][0]['FaceOccluded']['Value']=='true':
            return False
        return True
    #유저 ID 기반 Collection 생성
    def create_collection(self, user_id):
        try:
            self.client.create_collection(CollectionId=user_id)
        except:
            print("user_id already exists")
    # collection에 사람 추가하는 매서드 
    def add_face_to_collection(self,user_id, user_face, member_id):
        print(f'- adding face to collection: {user_id}')
        
        try:
            response = self.client.index_faces(
                CollectionId=user_id,
                Image={
                    'Bytes': user_face,
                },
                DetectionAttributes=['ALL']
            )
        except ClientError:
            self.logger.exception(f'Failed to add face to collection: {user_id}')
            raise
        
        face_ids = [response["FaceRecords"][0]['Face']['FaceId']]
        self.create_user(face_ids,user_id, member_id)

    # 콜랙션에 유저 만들기 
    def create_user(self,face_ids,user_id,member_id):
        #유저 생성하기
        try:
            self.logger.info(f'Creating user: {user_id}, {member_id}')
            self.client.create_user(
                CollectionId=user_id,
                UserId=str(member_id)
            )
        except ClientError:
            self.logger.exception(f'Failed to create user with given user id: {member_id}')
            raise
        try:
            print('start associate' + str(member_id)+':'+str(face_ids))
            response = self.client.associate_faces(
                CollectionId=user_id,
                UserId=str(member_id),
                FaceIds=face_ids
            )
            print('Success associate')
            time.sleep(0.5)
        except ClientError:
            self.logger.exception("Failed to associate faces to the given user")
            raise

    def search_users(self, collection_id, image_file):

        response= self.client.search_faces_by_image(CollectionId=collection_id,
                                Image={'Bytes': image_file},
                                FaceMatchThreshold=0.98,
                                MaxFaces=10)
        faceMatches=response['FaceMatches']
        print ('Matching faces')
        for match in faceMatches:
            print(float(match['Similarity']))
            if float(match['Similarity'])>90:
                return match
            else:
                print('no matching')
                return False
        return False
    def search_users_by_face_id(self,collection_id, face_id):

        try:
            response = self.client.search_users(
                CollectionId=collection_id,
                FaceId=face_id,
            )
            print(f'- found {len(response["UserMatches"])} matches')
            print([f'- {x["User"]["UserId"]} - {x["Similarity"]}%' for x in response["UserMatches"]])
        except ClientError:
            print('error_search')
        else:
            print(response)
            if len(response['UserMatches'])==0:
                return False
            return response['UserMatches'][0]['User']['UserId']

    # 이미지에서 얼굴 검출 후 collection에 사용자 추가
    # 전체 사진 중 Crop된 첫번째 frame 과, 나머지 3개의 frame을 순차 비교, 비교되는 Frame 내의 얼굴들과 각각 비교.
    def search_and_add_users_by_image(self,user_id,image_data):
        self.logger.info(f'Searching for users using an image: {image_data}')
        dic={}
        tmp_mem=[]
        self.create_collection(user_id)
        self.image_data=image_data
        try:
            #원본 이미지 저장 
            last_file_name=self.get_last_file_in_folder(user_id,'boaz-bucket-original')+1
            self.s3.put_object(
                Bucket='boaz-bucket-original',
                Key=user_id+'/'+str(last_file_name)+'.jpg',
                Body=image_data
            )
        ## YOLO FRAME DETECT -> YOLO SERVER 필요해 13ms CROP -> IMAGE 
        







            # 이미지에서 얼굴 검출
            response = self.client.detect_faces(
                Image={
                    'Bytes':image_data,
                }
                ,
                Attributes=['ALL']
            )
            print(len(response['FaceDetails']))
            
            smile_value=self.smile_algorithn(user_id,response,last_file_name)
            # 각 얼굴에 대해 사용자 검색
            last_member=self.get_last_file_in_folder(user_id,'boaz-bucket-pdb')

            for face in response['FaceDetails']:
                crop_face=self.crop_face_from_image(face['BoundingBox'])
                match_faceid=self.search_users(user_id,crop_face)
                if match_faceid==False:
                    last_member+=1
                    self.add_face_to_collection(user_id, crop_face, last_member)
                    self.s3.put_object(
                        Bucket='boaz-bucket-pdb',
                        Key=user_id+'/'+str(last_member)+'.jpg',
                        Body=crop_face
                    )
                    tmp_mem.append(str(last_member))
                else:
                    ttmp=self.search_users_by_face_id(user_id,match_faceid['Face']['FaceId'])
                    tmp_mem.append(str(ttmp))

            tmp_mem=list(set(tmp_mem))
            dic['members']={'SS':tmp_mem}
            dic['miso_point']={'N':str(int(smile_value))}
            dic['detected_count']={'N': str(len(tmp_mem))}
            dic['originalS3']={'S':'https://boaz-bucket-original.s3.ap-northeast-2.amazonaws.com/'+str(last_file_name)+'.jpg'}
            dic['UserID']={'S':user_id}

            return dic
    
        except ClientError:
            self.logger.exception(f'Failed to perform SearchUsersByImage with given image: {self.image_data}')
            raise

    #스마일 탐지 알고리즘 
    def smile_algorithn(self, user_id,face_respones,last_file_name):
        price=0 
        bounding_boxs=[]
        for face in face_respones['FaceDetails']: # 얼굴 정보 추출 
            if face['Smile']['Value'] == True:  #웃는 얼굴이면 점수 환산 및 바운딩 박스 그리기
                bounding_boxs.append(face['BoundingBox'])
                for emotion in face['Emotions']:
                    if emotion['Type']=='HAPPY':
                        price+=int(emotion['Confidence'])
                        break
        smile_detect_image= self.draw_bounding_box(bounding_boxs)
        self.s3.put_object(
            Bucket='boaz-bucket-smile',
            Key=str(last_file_name)+'.jpg',
            Body=smile_detect_image
        )
        return price*0.1
        

