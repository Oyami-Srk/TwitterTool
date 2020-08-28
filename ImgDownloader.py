# -*- coding: utf-8 -*-
# -*- audhot: shiroko -*-
# -*- date: 18/07/03 -*-
# Description: Image downloader for any url

import os
import logging
import urllib.request
#from multiprocessing import Pool
from multiprocessing.dummy import Pool


class Downloader:
    """ Downloader main class """

    def __init__(self,
                 base_url='{}',
                 base_path='',
                 logger=logging.getLogger('log')):
        """ Generate downloader function via params """
        self.logger = logger
        self.logger.info("Downloader Starting...")
        self.pool = Pool(10)  # 10 processes, configurable later
        self.dl_list = []
        self.base_url = str(base_url)
        self.base_path = str(base_path)

    def get_status(self, clear=False):
        downloaded = []
        downloading = []
        failed = []
        for i in range(len(self.dl_list) - 1, -1, -1):
            result = self.dl_list[i]
            if result[1].ready() is False:
                downloading.append(result[0])
                if clear:
                    self.dl_list.pop(i)
                continue
            if result[1].get() is False:
                failed.append(result[0])
                continue
            downloaded.append(result[0])
            if clear:
                self.dl_list.pop(i)
        return {
            'Downloaded': downloaded,
            'Downloading': downloading,
            'Failed': failed
        }

    def dl_sync(self, url, path='', fn=''):
        return self.pool.apply(self.dl, (
            url,
            path,
            fn,
        ))

    def download(self, url, path='', fn='', referer=''):
        r = self.pool.apply_async(self.dl, (
            url,
            path,
            fn,
            referer,
        ))
        self.dl_list.append((url, r))

    def dl(self, url, path='', fn='', referer=''):
        try:
            path = self.make_sure_path(os.path.join(self.base_path, path))
            if isinstance(url, str):
                url = [url]
            url = self.base_url.format(*url)
            if fn == '':
                fn = os.path.basename(url)
            req = urllib.request.Request(url)
            req.add_header('Referer', referer)
            img = urllib.request.urlopen(req)
            if img.status is not 200:
                raise Exception('Image cannot be reached({})'.format(
                    img.status))
            with open(os.path.join(path, fn), 'wb') as f:
                f.write(img.read())
        except Exception as e:
            if os.path.exists(os.path.join(path, fn)):
                os.remove(os.path.join(path.fn))
            self.logger.error("Error downloading image: " + url + ' ; err: ' +
                              str(e))
            return False
        self.logger.info('Downloaded: ' + url)
        return True

    def close(self):
        try:
            self.pool.close()
            self.logger.info("Pool closed, wating for completing download.")
            self.pool.join()
        except Exception as e:
            self.logger.error("Error stopping the downloader: " + str(e))
            self.pool.terminate()
            return False
        self.logger.info("Downloader Stopped...")
        return True

    def make_sure_path(self, path):
        """ Make sure the path is exists"""
        path = str(path)  # anaconda-mode hasn't supported PEP-0484 yet, QAQ
        path = path.strip()

        if path is not '' and not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                self.logger.fatal("Cannot create dirs: " + path + " ; err: " +
                                  str(e))
            finally:
                self.logger.info("Created dirs: " + path)

        return path
