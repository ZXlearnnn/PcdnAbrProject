import os
import json
import time
import traceback
import sys
from os.path import join, getsize

KB_B = 1024
MB_KB = 1024
GB_MB = 1024

BitrateList = [100, 200, 240, 375, 550, 750, 1000, 1500, 2300, 3000, 4300, 5800, 6500, 70000, 7500, 8000, 12000, 17000, 20000]

DeviceType = ['phone', 'hdtv', '4ktv']

POOR_THRESH = 20
FAIR_THRESH = 40
GOOD_THRESH = 60
EXCELLENT_THRESH = 80
CHECK_INTERVAL = 2

VMAF_ROOT_PATH = '/home/maxt/VideoProcess/VmafJsonData'
CHUNK_SIZE_ROOT_PATH = '/home/maxt/VideoProcess/SizeJsonData'


def getdirsize(dir):
    size = 0
    for root, dirs, files in os.walk(dir):
        try:
            size += sum([getsize(join(root, name)) for name in files])
        except:
            print('Deleted file in the media file.')
            continue
    return size  # in bytes , if to MB, it should /1024/1024


class LRUCache:
    def __init__(self, redis_object, data_id_info_object, args):
        self.redis_object = redis_object
        self.data_id_info_object =data_id_info_object
        self.max_cache_size = args.max_cache_size
        self.cache_margin = args.cache_margin / GB_MB  # MB to GB
        self.args = args

    # Check whether we should trigger the cache eviction event
    # Return True means that they need content eviction
    def check_eviction(self):
        eviction_size = self.max_cache_size - self.cache_margin
        print("dirsize of {} is {} MB and eviction size is {}."
              .format(getdirsize(self.args.cache_path) / MB_KB / KB_B, (eviction_size * GB_MB)))
        if (getdirsize(self.args.cache_path) / MB_KB / KB_B) > (eviction_size * GB_MB):
            return True  # doing the eviction
        else:
            return False  # No need to eviction

    def active_eviction(self, redis_key):
        try:
            os.remove(self.redis_object.get(redis_key))
            self.redis_object.delete(redis_key)
            print('Content {} evicted.'.format(redis_key))
            # 删除data_id_hash
            if len(redis_key.split('+')) == 3:
                cache_info_list = redis_key.split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_info_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
        except FileNotFoundError:
            print('FileNotFoundError occur: the key is {} and the cache path is {}'
                  .format(redis_key, self.redis_object.get(redis_key)))
            self.redis_object.delete(redis_key)
            print('Delete the key {}, the content is not found'.format(redis_key))
            # 删除data_id_hash
            if len(redis_key.split('+')) == 3:
                cache_info_list = redis_key.split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_info_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))

    def eviction(self):
        random_key_list = []

        # Fill in the random key list
        while len(random_key_list) < self.args.lru_sample_num:
            random_key = self.redis_object.randomkey()
            if random_key not in random_key_list:
                random_key_list.append(random_key)

        # Find the key with the longest idle time
        # Generate the tuple (longest_idle_key, longest_idle_time)
        longest_idle_key = random_key_list[0]
        random_key_list.remove(longest_idle_key)
        longest_idle_time = self.redis_object.object('idletime', longest_idle_key)
        longest_idle_tuple = (longest_idle_key, longest_idle_time)
        for key in random_key_list:
            idle_time = self.redis_object.object('idletime', key)
            if idle_time is None:
                print('The idle time of key {} is None.'.format(key))
                try:
                    os.remove(self.redis_object.get(key))  # 删除缓存文件
                    self.redis_object.delete(key)  # 删除redis中的key
                    # 删除data_id_hash
                    if len(key.split('+')) == 3:
                        cache_info_list = key.split('+')
                        whole_name = cache_info_list[0]
                        track = cache_info_list[1]
                        chunk_no = cache_info_list[2][3:]
                        self.data_id_info_object.hdel(
                            'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
                except Exception as e:
                    print('Failed in Delete NoneType key content.')
                    print(''.join(traceback.format_exception(*sys.exc_info())))
                    self.redis_object.delete(key)
                    # 删除data_id_hash
                    if len(key.split('+')) == 3:
                        cache_info_list = key.split('+')
                        whole_name = cache_info_list[0]
                        track = cache_info_list[1]
                        chunk_no = cache_info_list[2][3:]
                        self.data_id_info_object.hdel(
                            'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
                continue
            if idle_time > longest_idle_time:
                longest_idle_tuple = (key, idle_time)

        # Remove the element with the longest idle key and the file
        try:
            os.remove(self.redis_object.get(longest_idle_tuple[0]))
            self.redis_object.delete(longest_idle_tuple[0])
            print('Content {} evicted.'.format(longest_idle_tuple[0]))
            # 删除data_id_hash
            if len(longest_idle_tuple[0].split('+')) == 3:
                cache_info_list = longest_idle_tuple[0].split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_info_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
        except FileNotFoundError:
            print('FileNotFoundError occur: the key is {} and the cache path is {}'
                  .format(longest_idle_tuple[0], self.redis_object.get(longest_idle_tuple[0])))
            self.redis_object.delete(longest_idle_tuple[0])
            print('Delete the key {}, the content is not found'.format(longest_idle_tuple[0]))
            # 删除data_id_hash
            if len(longest_idle_tuple[0].split('+')) == 3:
                cache_info_list = longest_idle_tuple[0].split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_info_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))

    def set_content_in_redis(self, video_name, bitrate, segment_id, cache_path):
        self.redis_object.set(
            '{}+{}+seg{}'.format(video_name, bitrate, segment_id),
            os.path.join(cache_path, 'seg-{}.m4s'.format(segment_id))
        )


# ---------------------------------按照chunk块质量缓存----------------------------------------
def get_chunk_size(video_name, track, chunk_no):
    json_file_path = os.path.join(CHUNK_SIZE_ROOT_PATH, video_name,
                                  'chunk_size', '{}_track{}_size.json'.format(video_name, track))
    data = open(json_file_path, encoding='utf-8')
    strJson = json.load(data)

    return strJson[str(chunk_no)]


def get_chunk_of_certain_quality(video_name, target_quality, device_type):
    chunk_dict_of_certain_quality = {}
    chunk_num = len(os.listdir(os.path.join(VMAF_ROOT_PATH, video_name, 'vmaf', '10', device_type)))
    for chunk_no in range(1, chunk_num + 1):
        chunk_dict_of_certain_quality[str(chunk_no)] = {}
        for track in range(1, len(BitrateList)):
            vmaf_json_path = os.path.join(VMAF_ROOT_PATH, video_name, 'vmaf', str(track), device_type)
            data = open(os.path.join(vmaf_json_path, 'seg-{}.json'.format(chunk_no)), encoding='utf-8')
            strJson = json.load(data)
            vmaf_value = float(strJson['VMAF score'])
            if vmaf_value < target_quality:
                if track < len(BitrateList) - 1:
                    continue
                else:
                    chunk_dict_of_certain_quality[str(chunk_no)]['track'] = track
                    chunk_dict_of_certain_quality[str(chunk_no)]['quality'] = vmaf_value
                    chunk_dict_of_certain_quality[str(chunk_no)]['size'] = get_chunk_size(video_name, track,
                                                                                          chunk_no)
            else:
                chunk_dict_of_certain_quality[str(chunk_no)]['track'] = track
                chunk_dict_of_certain_quality[str(chunk_no)]['quality'] = vmaf_value
                chunk_dict_of_certain_quality[str(chunk_no)]['size'] = get_chunk_size(video_name, track, chunk_no)
                break

    return chunk_dict_of_certain_quality


def weighted_get_chunk_of_certain_quality(video_name, target_quality, total_w_ph, total_w_hd, total_w_4k):
    chunk_dict_of_certain_quality = {}
    chunk_num = len(os.listdir(os.path.join(VMAF_ROOT_PATH, video_name, 'vmaf', '10', 'phone')))
    w_ph = float(total_w_ph) / float(total_w_ph + total_w_hd + total_w_4k)
    w_hd = float(total_w_hd) / float(total_w_ph + total_w_hd + total_w_4k)
    w_4k = float(total_w_4k) / float(total_w_ph + total_w_hd + total_w_4k)
    for chunk_no in range(1, chunk_num + 1):
        chunk_dict_of_certain_quality[str(chunk_no)] = {}
        for track in range(1, len(BitrateList)):
            vmaf_value_dict = {}
            for device_type in DeviceType:
                vmaf_json_path = os.path.join(VMAF_ROOT_PATH, video_name, 'vmaf', str(track), device_type)
                data = open(os.path.join(vmaf_json_path, 'seg-{}.json'.format(chunk_no)), encoding='utf-8')
                strJson = json.load(data)
                vmaf_value_dict[device_type] = float(strJson['VMAF score'])
            weighted_vmaf_value = w_ph * vmaf_value_dict['phone'] + w_hd * vmaf_value_dict['hdtv'] \
                                  + w_4k * vmaf_value_dict['4ktv']
            if weighted_vmaf_value < target_quality:
                if track < len(BitrateList) - 1:
                    continue
                else:
                    chunk_dict_of_certain_quality[str(chunk_no)]['track'] = track
                    chunk_dict_of_certain_quality[str(chunk_no)]['quality'] = weighted_vmaf_value
                    chunk_dict_of_certain_quality[str(chunk_no)]['size'] = get_chunk_size(video_name, track, chunk_no)
            else:
                chunk_dict_of_certain_quality[str(chunk_no)]['track'] = track
                chunk_dict_of_certain_quality[str(chunk_no)]['quality'] = weighted_vmaf_value
                chunk_dict_of_certain_quality[str(chunk_no)]['size'] = get_chunk_size(video_name, track, chunk_no)
                break
        return chunk_dict_of_certain_quality


def get_target_quality(video_name, allowed_cache_size, phone_weight, hdtv_weight, tv4k_weight):
    # 先判断在该cache size下target quality能否上60，若不能上60就不缓存该quality
    good_chunk_dict_of_certain_quality = \
        weighted_get_chunk_of_certain_quality(video_name, GOOD_THRESH, phone_weight, hdtv_weight, tv4k_weight)

    track_list = []
    quality_list = []
    size_list = []
    for chunk_no in range(1, len(good_chunk_dict_of_certain_quality) + 1):
        track_list.append(good_chunk_dict_of_certain_quality[str(chunk_no)]['track'])
        quality_list.append(good_chunk_dict_of_certain_quality[str(chunk_no)]['quality'])
        size_list.append(good_chunk_dict_of_certain_quality[str(chunk_no)]['size'])
    # The sum size should in MB
    sum_size = sum(size_list) / KB_B / MB_KB
    if sum_size >= allowed_cache_size:
        return None
    else:
        thresh = GOOD_THRESH
        while sum_size < allowed_cache_size:
            thresh += CHECK_INTERVAL
            if thresh > 100:
                break
            chunk_dict_of_certain_quality = \
                weighted_get_chunk_of_certain_quality(video_name, thresh, phone_weight, hdtv_weight, tv4k_weight)

            track_list = []
            quality_list = []
            size_list = []
            for chunk_no in range(1, len(chunk_dict_of_certain_quality) + 1):
                track_list.append(chunk_dict_of_certain_quality[str(chunk_no)]['track'])
                quality_list.append(chunk_dict_of_certain_quality[str(chunk_no)]['quality'])
                size_list.append(chunk_dict_of_certain_quality[str(chunk_no)]['size'])
            sum_size = sum(size_list) / KB_B / MB_KB

        return chunk_dict_of_certain_quality, track_list


# 根据历史关于视频的请求数量确定每个视频的target_quality
# 可以单独给django开个线程来执行target_quality_update
def update_target_quality(count_redis_object, args):
    # target_quality_dict = {'video_name': chunk_dict_of_certain_quality(包括每个chunk_no的track, quality, size)}
    # 之后判断该比特率是否值得缓存，可以利用该target_quality_dict，对应于该列表中的chunkno
    # uwsgi的多个线程要共享哪些chunk需要被缓存，每个chunk对应的track应该要简化一些，传入redis，以提升从redis中的读取速率
    target_quality_dict = {}
    video_request_count_dict = {}
    video_total_request_dict = {}  # 用于记录所有设备种类下的总请求个数，之后排序出队来决定target_quality
    # The key is video_name_device_type, e.g. bird_phone
    keys_list = count_redis_object.keys()
    total_count = 0
    for key in keys_list:
        if count_redis_object.type(key) == 'string':
            continue
        request_count = count_redis_object.get(key)
        key_element_list = key.split('_')  # VideoName_DeviceType
        video_name = key_element_list[0]
        device_type = key_element_list[1]
        if video_name not in video_request_count_dict:
            video_request_count_dict[video_name] = {}
            video_total_request_dict[video_name] = 0
        video_request_count_dict[video_name][device_type] = request_count
        video_total_request_dict[video_name] += request_count
        total_count += request_count
    count_redis_object.flushall()
    # 计算可分配的cache size, 进而计算出符合预期的target quality, 从请求次数最多的视频开始
    while len(video_total_request_dict) > 0:
        video_name = max(video_total_request_dict, key=video_total_request_dict.get)
        # The cache size in MB
        allowed_cache_size = \
            (sum(video_request_count_dict[video_name].values()) / float(total_count)) * args.max_cache_size * GB_MB

        phone_weight = float(video_request_count_dict[video_name]['phone']) / float(total_count)
        hdtv_weight = float(video_request_count_dict[video_name]['hdtv']) / float(total_count)
        tv4k_weight = float(video_request_count_dict[video_name]['4ktv']) / float(total_count)

        if not get_target_quality(video_name, allowed_cache_size, phone_weight, hdtv_weight, tv4k_weight):
            continue
        else:
            chunk_dict_of_certain_quality, track_list = \
                get_target_quality(video_name, allowed_cache_size, phone_weight, hdtv_weight, tv4k_weight)
            target_quality_dict[video_name] = chunk_dict_of_certain_quality
            # 将track list上传到redis中, 但如果用户比较多的话，用户可能只会请求低码率的视频，导致高流行度的视频的chunk不被缓存
            # 因此我会再建立一个表，代表着目前已缓存的track，如果有比它大的chunk被请求，就把这个小的替换掉
            # <video_name>_tracklist_1中存的是最好缓存的码率
            # <video_name>_tracklist_temp中存的是现有的码率，0代表没有该码率没有被缓存
            init_track_list = [0] * len(track_list)
            count_redis_object.set('{}_tracklist_1'.format(video_name), json.dumps(track_list))
            count_redis_object.set('{}_tracklist_temp'.format(video_name), json.dumps(init_track_list))

        del video_request_count_dict[video_name]
        del video_total_request_dict[video_name]
    return target_quality_dict


class QualityCache:
    def __init__(self, content_cache_redis_object, count_redis_object, data_id_info_object, args):
        self.content_cache_redis_object = content_cache_redis_object
        self.count_redis_object = count_redis_object
        self.data_id_redis_object = data_id_info_object
        self.max_cache_size = args.max_cache_size
        self.cache_margin = args.cache_margin / GB_MB  # MB to GB
        self.args = args

    def active_eviction(self, redis_key):
        try:
            os.remove(self.content_cache_redis_object.get(redis_key))  # 删除缓存文件
            self.content_cache_redis_object.delete(redis_key)  # 删除redis中的key
            self.content_cache_redis_object.srem('LRU_set', redis_key)
            print('Content {} evicted.'.format(redis_key))
            # 删除data_id_hash
            if len(redis_key.split('+')) == 3:
                cache_info_list = redis_key.split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_redis_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
        except FileNotFoundError:
            print('FileNotFoundError occur: the key is {} and the cache path is {}'
                  .format(redis_key, self.content_cache_redis_object.get(redis_key)))
            self.content_cache_redis_object.delete(redis_key)
            print('Delete the key {}, the content is not found'.format(redis_key))
            # 删除data_id_hash
            if len(redis_key.split('+')) == 3:
                cache_info_list = redis_key.split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_redis_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))

    # Check whether we should trigger the cache eviction event
    # Return True means that they need content eviction
    def check_eviction(self):
        eviction_size = self.max_cache_size - self.cache_margin
        print("dirsize is {} MB and eviction size is {}."
              .format(getdirsize(self.args.cache_path) / MB_KB / KB_B, (eviction_size * GB_MB)))
        if (getdirsize(self.args.cache_path) / MB_KB / KB_B) > (eviction_size * GB_MB):
            return True  # doing the eviction
        else:
            return False  # No need to eviction

    def eviction(self):
        # 需要写好替换策略，那些已经确定了target quality的就先不进行替换了
        if self.content_cache_redis_object.scard('LRU_set') < self.args.lru_sample_num:
            random_key_list = list(self.content_cache_redis_object.smembers('LRU_set'))
        else:
            random_key_list = self.content_cache_redis_object.srandmember('LRU_set', self.args.lru_sample_num)

        # Find the key with the longest idle time
        # Generate the tuple (longest_idle_key, longest_idle_time)
        longest_idle_key = random_key_list[0]
        random_key_list.remove(longest_idle_key)
        longest_idle_time = self.content_cache_redis_object.object('idletime', longest_idle_key)
        longest_idle_tuple = (longest_idle_key, longest_idle_time)
        for key in random_key_list:
            idle_time = self.content_cache_redis_object.object('idletime', key)
            if idle_time is None:
                print('The idle time of key {} is None.'.format(key))
                try:
                    os.remove(self.content_cache_redis_object.get(key))  # 删除缓存文件
                    self.content_cache_redis_object.delete(key)  # 删除redis中的key
                    self.content_cache_redis_object.srem('LRU_set', key)  # 把内容从LRU_set(随机池)中删掉
                    # 删除data_id_hash
                    if len(key.split('+')) == 3:
                        cache_info_list = key.split('+')
                        whole_name = cache_info_list[0]
                        track = cache_info_list[1]
                        chunk_no = cache_info_list[2][3:]
                        self.data_id_redis_object.hdel(
                            'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
                except:
                    print('Failed in Delete NoneType key content.')
                    print(''.join(traceback.format_exception(*sys.exc_info())))
                    self.content_cache_redis_object.delete(key)  # 删除redis中的key
                    self.content_cache_redis_object.srem('LRU_set', key)  # 把内容从LRU_set(随机池)中删掉
                    # 删除data_id_hash
                    if len(key.split('+')) == 3:
                        cache_info_list = key.split('+')
                        whole_name = cache_info_list[0]
                        track = cache_info_list[1]
                        chunk_no = cache_info_list[2][3:]
                        self.data_id_redis_object.hdel(
                            'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
                continue
            if longest_idle_time is None:
                longest_idle_time = idle_time
                longest_idle_tuple = (key, longest_idle_time)
            if idle_time > longest_idle_time:
                longest_idle_tuple = (key, idle_time)

        if not self.content_cache_redis_object.get(longest_idle_tuple[0]):
            if self.args.debug:
                print('WARNING: All the keys in the random key list are not existed. It is wired.')
            return
        # Remove the element with the longest idle key and the file
        try:
            os.remove(self.content_cache_redis_object.get(longest_idle_tuple[0]))  # 删除缓存文件
            self.content_cache_redis_object.delete(longest_idle_tuple[0])  # 删除redis中的key
            self.content_cache_redis_object.srem('LRU_set', longest_idle_tuple[0])
            print('Content {} evicted.'.format(longest_idle_tuple[0]))
            # 删除data_id_hash
            if len(longest_idle_tuple[0].split('+')) == 3:
                cache_info_list = longest_idle_tuple[0].split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_redis_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))
        except FileNotFoundError:
            print('FileNotFoundError occur: the key is {} and the cache path is {}'
                  .format(longest_idle_tuple[0], self.content_cache_redis_object.get(longest_idle_tuple[0])))
            self.content_cache_redis_object.delete(longest_idle_tuple[0])
            print('Delete the key {}, the content is not found'.format(longest_idle_tuple[0]))
            # 删除data_id_hash
            if len(longest_idle_tuple[0].split('+')) == 3:
                cache_info_list = longest_idle_tuple[0].split('+')
                whole_name = cache_info_list[0]
                track = cache_info_list[1]
                chunk_no = cache_info_list[2][3:]
                self.data_id_redis_object.hdel(
                    'edge_data_id_hash', '{}+{}+{}'.format(whole_name, chunk_no, track))

    def set_init_in_redis(self, video_name, bitrate, cache_path, request_count_redis_object, track_list_num):

        needed_track_list = []
        for track_list_no in range(1, track_list_num+1):
            if request_count_redis_object.get('{}_tracklist_{}'.format(video_name, track_list_no)):
                needed_track_list.append(
                    request_count_redis_object.get('{}_tracklist_{}'.format(video_name, track_list_no)))

        if len(needed_track_list) == 0:
            while self.content_cache_redis_object.exists('lock'):
                time.sleep(0.002)
                if self.args.debug:
                    print('DEBUG: Redis locked.')
            self.content_cache_redis_object.sadd(
                'LRU_set', '{}+{}+init.mp4'.format(video_name, bitrate))
            self.content_cache_redis_object.set(
                '{}+{}+init.mp4'.format(video_name, bitrate),
                os.path.join(cache_path, 'init.mp4'))
            return

        for track_list in needed_track_list:
            while self.content_cache_redis_object.exists('lock'):
                time.sleep(0.002)
                if self.args.debug:
                    print('DEBUG: Redis locked.')
            if bitrate in track_list:
                self.content_cache_redis_object.sadd(
                    'STATIC_set', '{}+{}+init.mp4'.format(video_name, bitrate)
                )
                self.content_cache_redis_object.set(
                    '{}+{}+init.mp4'.format(video_name, bitrate),
                    os.path.join(cache_path, 'init.mp4'))
                break
            else:
                self.content_cache_redis_object.sadd(
                    'LRU_set', '{}+{}+init.mp4'.format(video_name, bitrate))
                self.content_cache_redis_object.set(
                    '{}+{}+init.mp4'.format(video_name, bitrate),
                    os.path.join(cache_path, 'init.mp4'))
                break

    # 这里需要判断chunk应该被存入'LRU_set'还是static_set(target_quality指定了能缓存的track)
    # bitrate 是 1~10, 此时bitrate和track的概念是一样的
    def set_content_in_redis(self, video_name, bitrate, segment_id,
                             cache_path, request_count_redis_object, track_list_num):
        # 这里需要注意的是，chunk的index应该是segment_id-1
        needed_track_list = []
        for track_list_no in range(1, track_list_num+1):
            if request_count_redis_object.get('{}_tracklist_{}'.format(video_name, track_list_no)):
                needed_track_list.\
                    append(request_count_redis_object.get('{}_tracklist_{}'.format(video_name, track_list_no)))

        if len(needed_track_list) == 0:  # 说明该视频的流行度无法达到需求，因此把它放到动态的LRU_set中
            while self.content_cache_redis_object.exists('lock'):
                time.sleep(0.002)
                if self.args.debug:
                    print('DEBUG: Redis locked.')
            self.content_cache_redis_object.sadd(
                'LRU_set', '{}+{}+seg{}'.format(video_name, bitrate, segment_id))
            self.content_cache_redis_object.set(
                '{}+{}+seg{}'.format(video_name, bitrate, segment_id),
                os.path.join(cache_path, 'seg-{}.mp4'.format(segment_id)))
            return

        for track_list in needed_track_list:
            while self.content_cache_redis_object.exists('lock'):
                time.sleep(0.002)
                if self.args.debug:
                    print('DEBUG: Redis locked.')
            if bitrate == track_list[int(segment_id)-1]:
                self.content_cache_redis_object.sadd(
                    'STATIC_set', '{}+{}+seg{}'.format(video_name, bitrate, segment_id)
                )
                self.content_cache_redis_object.set(
                    '{}+{}+seg{}'.format(video_name, bitrate, segment_id),
                    os.path.join(cache_path, 'seg-{}.mp4'.format(segment_id)))
                break
            else:
                self.content_cache_redis_object.sadd(
                    'LRU_set', '{}+{}+seg{}'.format(video_name, bitrate, segment_id))
                self.content_cache_redis_object.set(
                    '{}+{}+seg{}'.format(video_name, bitrate, segment_id),
                    os.path.join(cache_path, 'seg-{}.mp4'.format(segment_id)))
                break
# -------------------------------------------------------------------------------------------


class P2PCache:
    def __init__(self, seed_info_redis_object):
        self.seed_info_redis_object = seed_info_redis_object




