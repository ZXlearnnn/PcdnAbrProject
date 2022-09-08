import  redis
pool = redis.ConnectionPool(host='127.0.0.1',port=6380,db=0)
r = redis.StrictRedis(connection_pool=pool)

keys = r.keys()
print (keys)