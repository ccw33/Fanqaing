# encoding:utf-8
import traceback

from Utils import scribe_utils, thread_utils
from model.fangqiang import ip as ip_model

from queue import Queue
import threading

ip_collection = ip_model.Fanqiang()
ip_list = list(ip_collection.query())
Elite = []

queue = Queue()


def job(ip_port_dict):
    try:
        elite = scribe_utils.test_elite(ip_port_dict['ip_with_port'],ip_port_dict['proxy_type'])
        if elite:
           ip_collection.update({'Elite': elite}, {'ip_with_port': ip_port_dict['ip_with_port']})
    except Exception as e:
        traceback.print_exc()


# factory = thread_utils.ThreadFactory()
#
# for i in range(20):
#     t = threading.Thread(target=factory.queue_threads_worker, args=(queue, job))
#     t.start()
#
# for ip_port_dict in ip_list:
#     queue.put({'ip_port_dict':ip_port_dict})
# queue.join()
# factory.all_task_done = True

if __name__=="__main__":
    factory = thread_utils.ThreadFactory()

    def job():
        try:#job里面必须要try catch，因为已经是最后一层，不处理会卡死queue
            pass
        except Exception:
            pass

    for i in range(20):
        t = threading.Thread(target=factory.queue_threads_worker,args=(queue,job))
        t.start()
    for i in range(300):
        queue.put({})
    queue.join()
    factory.all_task_done=True