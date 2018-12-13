#encoding:utf-8
import queue

class ThreadFactory():

    all_task_done = False

    def queue_threads_worker(self,q,func):
        while not self.all_task_done:
            try:
                data = q.get(timeout=2)
                func(**data)
            except queue.Empty:  # 如果过了2秒还没有获得新任务，回去看一下是否已经all_done
                continue
            q.task_done()#任务完成，告诉q一声