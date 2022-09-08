import os


NAME_LIST = ['bus','car','pedestrian','static','train']

for name in NAME_LIST:
    file_list = os.listdir(name)
    file_list.sort()
    idx = 1
    for file_name in file_list:
        command = 'mv {}/{} {}/LTE_{}.csv'.format(name,file_name,name,idx)
        print(command)
        os.system(command)
        idx += 1