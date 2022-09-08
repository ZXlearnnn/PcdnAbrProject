import requests
import os
import json
import shutil
import time

EDGE_SERVER = '10.103.11.73:8080'
SOURCE_SERVER = '10.103.11.76:8080'
VIDEO_LIST = ['bbb', 'beauty', 'drivingPOV', 'honeyBee', 'jockey', 'readySetGo', 'sintel', 'windAndNature', 'yachtRide']
TRACK = 15

SPLIT_CHUNK_SIZE = 4096



if __name__ == '__main__':
    for video_name in VIDEO_LIST:
        mysession = requests.session()
        for track in range(1, 20):
            for chunkno in range(1, 11):
                chunk_size = 0
                chunk_state_dict = {}
                url = 'http://{}/{}/video/x265/{}/{}'.format(SOURCE_SERVER, video_name, track, chunkno)
                print('ready to send request to url:{}'.format(url))
                start_download_time = time.time()
                r = mysession.get(url)
                finish_download_time = time.time()
                print('get response')
                for chunk in r.iter_content(chunk_size=SPLIT_CHUNK_SIZE):
                    chunk_size += float(len(chunk))  # 单位是bytes
                chunk_download_time = finish_download_time - start_download_time
                bw = chunk_size * 8 / chunk_download_time / 1024 / 1024
                print('{} Mbit/s'.format(bw))

