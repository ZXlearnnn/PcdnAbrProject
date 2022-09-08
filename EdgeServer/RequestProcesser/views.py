from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.http.response import StreamingHttpResponse
from django_redis import get_redis_connection
from django.core.cache import cache, caches
from RequestProcesser.cachefunction import getdirsize, LRUCache, QualityCache  # , P2PCache
from arguments import get_args
import requests
import os

SOURCE_SERVER_76='10.103.11.76'

SOURCE_PORT='8080'

# The project configuration
PROJECT_PATH = '/home/maxt/EdgeServer'

NEED_SAVE = True
DETAIL_DATA_METRIC = False

# The arguments
DEFAULT_ARGS = get_args()

BitrateList = [100, 200, 240, 375, 550, 750, 1000, 1500, 2300, 3000, 4300, 5800, 6500, 70000, 7500, 8000, 12000, 17000, 20000]

# The name of the cache object
CONTENT_CACHE_OBJECT_NAME = 'SmartEdgeCache'
REQUEST_COUNT_OBJECT_NAME = 'RequestCountCache'
DATA_ID_INFO_OBJECT_NAME = 'DataIdInfoCache'


# The connection object with redis
CONTENT_CACHE_OBJECT = get_redis_connection(CONTENT_CACHE_OBJECT_NAME)
REQUEST_COUNT_OBJECT = get_redis_connection(REQUEST_COUNT_OBJECT_NAME)
DATA_ID_INFO_OBJECT = get_redis_connection(DATA_ID_INFO_OBJECT_NAME)##这是拿来做什么的

# Initialize the LRU Cache class
LRU = LRUCache(CONTENT_CACHE_OBJECT, DATA_ID_INFO_OBJECT, DEFAULT_ARGS)
QUALITY_LRU = QualityCache(CONTENT_CACHE_OBJECT, REQUEST_COUNT_OBJECT, DATA_ID_INFO_OBJECT, DEFAULT_ARGS)
# P2PCACHE = P2PCache(SEED_INFO_OBJECT)


# Create your views here.

PROJECT_PATH = '/home/maxt/EdgeServer'

# The Cache Strategy
PURE_LRU_STRATEGY = 'pure_lru'
QUALITY_LRU_STRATEGY = 'quality_lru'
DEFAULT_LRU_STRATEGY = QUALITY_LRU_STRATEGY

def Test(request):
    return HttpResponse('successful')

def TestRedirect(request,video_name):
    url = 'http://{}:{}/{}/video/x265/19/2'.format(SOURCE_SERVER_76,'8080',video_name)
    VideoFolderpath = os.path.join(PROJECT_PATH,'videodata/')
    SmartEdgeCache =get_redis_connection('SmartEdgeCache')
    if SmartEdgeCache.get(video_name):
        return FileResponse(open(SmartEdgeCache.get(video_name)),'rb')
    else:
        r = requests.get(url)
        with open(os.path.join(VideoFolderpath,'{}.mp4'.format(video_name)), 'wb') as f:
            f.write(r.content)
        return FileResponse(open(os.path.join(VideoFolderpath,'{}.mp4'.format(video_name)),'rb'))


def ContentRedirect73(request, video_name, track, segment_id, content_cache_redis_object=CONTENT_CACHE_OBJECT,
                       request_count_redis_object=REQUEST_COUNT_OBJECT,
                       data_id_redis_object=DATA_ID_INFO_OBJECT, cache_strategy=DEFAULT_LRU_STRATEGY):

    client_ip = request.GET.get('ip')
    print('The client ip is {}.'.format(client_ip))
    whole_video_name = video_name

    url = 'http://{}:{}/{}/video/x265/{}/{}' \
        .format(SOURCE_SERVER_76, SOURCE_PORT, video_name, track, segment_id)
    video_folder_path = os.path.join(PROJECT_PATH, 'videodata/{}'.format(whole_video_name))
    cache_path = os.path.join(video_folder_path, track)
    ##怎么好像是从高到低在匹配
    for track_try in reversed(range(int(track), len(BitrateList)+1)):
    # for track_try in reversed(range(1, len(BitrateList))):
        if content_cache_redis_object.get('{}+{}+seg{}'.format(whole_video_name, track_try, segment_id)) and \
                check_exist('{}+{}+seg{}'.format(whole_video_name, track_try, segment_id)):
            print('The key is {}+{}+seg{} and the value is {}'
                  .format(whole_video_name, track_try, segment_id,
                          content_cache_redis_object.get(
                              '{}+{}+seg{}'.format(whole_video_name, track_try, segment_id))))
            try:
                response = FileResponse(
                    open(content_cache_redis_object.get(
                        '{}+{}+seg{}'.format(whole_video_name, track_try, segment_id)), 'rb'))
            except FileNotFoundError:
                print('The file in {} is not found, it is a file not found error, not frequent.'
                      .format(content_cache_redis_object.get(
                        '{}+{}+seg{}'.format(whole_video_name, track_try, segment_id))))
                break
            except TypeError:
                print('The key {} is a NoneType, it is a type error, not frequent.'.format(
                    content_cache_redis_object.get('{}+{}+seg{}'.format(whole_video_name, track_try, segment_id))))
                break
            response['Width'] = int(track_try)
            response['origin'] = 'edge'
            response['data_id'] = \
                data_id_redis_object.hget(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_video_name, segment_id, track_try))
            print('Cache Hit!')
            return response

    # The track is not contained in the cache
    if not os.path.exists(cache_path):
        try:
            os.mkdir(cache_path)
        except FileNotFoundError:
            os.mkdir(video_folder_path)
            os.mkdir(cache_path)

    s = requests.Session()
    r = s.get(url, stream=True)

    if NEED_SAVE:
        response = StreamingHttpResponse(
            (chunk for chunk in r.iter_content(chunk_size=4096)),
                        save_object = open(os.path.join(cache_path, 'seg-{}.mp4'.format(segment_id)), 'wb',
                             buffering=1024 * 1024)
        )
        #content_cache_redis_object.set(
        #  '{}+{}+seg{}'.format(video_name, track, segment_id),
        #    os.path.join(cache_path, 'seg-{}.mp4'.format(segment_id))
        #)
        print('Cache not hit!')
        # print('The size of the content is {}'.format(len(r.content)))
        response['Width'] = int(track)
        response['origin'] = 'server'

        # 初始化可以用于存储的dict
        ##注意这里
        data_id = data_id_redis_object.incr('data_num')
        initial_hash_data_in_redis(data_id, client_ip, whole_video_name, segment_id, track)
        response['data_id'] = data_id


        if cache_strategy == PURE_LRU_STRATEGY:

            while LRU.check_eviction():
                LRU.eviction()

            # Set the content path in redis
            LRU.set_content_in_redis(whole_video_name, track, segment_id, cache_path)

        elif cache_strategy == QUALITY_LRU_STRATEGY:

            while QUALITY_LRU.check_eviction():
                QUALITY_LRU.eviction()

            # Set the content path in redis, the QUALITY_LRU is much complex, 需要确定是存在static_set还是存在LRU_set
            track_list_num = 1  # 此时只有1个，以后用户端限制带宽的时候可能会有多个，这个值也应该存入redis
            QUALITY_LRU.set_content_in_redis(
                whole_video_name, track, segment_id, cache_path, request_count_redis_object, track_list_num)

        else:
            raise NotImplementedError('The cache_strategy {} is not implemented.'.format(cache_strategy))
    else:
        response = StreamingHttpResponse(
            (chunk for chunk in r.iter_content(chunk_size=4096)))
        response['Width'] = int(track)
        response['origin'] = 'server'

    return response

def initial_hash_data_in_redis(
        data_id, client_ip, video_name, chunk_no, track, data_id_object=DATA_ID_INFO_OBJECT):
    # 存入seed object中
    network_flag, client_id = client_ip.split('.')[-2], client_ip.split('.')[-1]
    chunk_flag = '{}_{}_{}_{}'.format(video_name, chunk_no, network_flag, client_id)
    #tracks_num_in_seed_list = get_tracks_num_in_seed_list(video_name, chunk_no)

    data_id_object.hset('data_{}'.format(data_id), 'chunk_flag', chunk_flag)
    data_id_object.hset('data_{}'.format(data_id), 'track', track)

    if DETAIL_DATA_METRIC:
        data_id_object.hset('data_{}'.format(data_id), 'count_list', json.dumps([]))
    else:
        data_id_object.hset('data_{}'.format(data_id), 'phone_count', 0)
        data_id_object.hset('data_{}'.format(data_id), 'hdtv_count', 0)
        data_id_object.hset('data_{}'.format(data_id), '4ktv_count', 0)
        data_id_object.hset('data_{}'.format(data_id), 'total_quality_up', 0.0)
        data_id_object.hset('data_{}'.format(data_id), 'total_quality_down', 0.0)
        data_id_object.hset('data_{}'.format(data_id), 'total_rebuffer_time', 0.0)

    #data_id_object.hset('data_{}'.format(data_id), 'tracks_num_in_seed', json.dumps(tracks_num_in_seed_list))
    data_id_object.hset('data_{}'.format(data_id), 'client_count', 0)



# 有时候虽然有key，但是存在edge中的chunk的size为0或者直接没有该chunk，因此我需要预判一下这个文件存不存在
def check_exist(redis_key, content_cache_redis_object=CONTENT_CACHE_OBJECT):
    file_path = content_cache_redis_object.get(redis_key)
    try:
        if os.path.getsize(file_path) == 0:
            LRU.active_eviction(redis_key)
            return False
        else:
            return True
    except FileNotFoundError:
        pass
        return False

TEST1_ROOT = '/home/maxt/EdgeServer/test1'

def test1(request,video_name,track,segment_id):
    segment_id = str(int(segment_id)-1)
    if video_name == 'bbb' or 'sintel':
        segment_id = str(int(segment_id)+30)
    file_name='{}_2sec{}{}.mp4'.format(video_name,'0'*(4-len(segment_id)),segment_id)
    file_path = '{}/{}/{}/{}'.format(TEST1_ROOT,video_name,track,file_name)
    print(file_path)
    response = StreamingHttpResponse(open(file_path,'rb'))
    return response
