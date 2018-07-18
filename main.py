import os
import requests
import urllib.request
import re
import eyed3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.WARNING)

folder = 'download' #下载到此文件夹下
if not os.path.exists(folder):
    os.makedirs(folder)
musicinfoFile = 'musicinfo.json'
mis = []    #加载本地json存储的歌曲信息
errorMsg = []

#歌曲信息结构体
class Musicinfo(object):
    def __init__(self):
        self.id = 0         #id
        self.title = ''     #歌曲名
        self.artists = []   #歌手
        self.album = ''     #专辑
    def __str__(self):
        return str(self.__dict__)
    def toJson(self):
        return self.__dict__
    @staticmethod
    def Jsonto(jdict):
        mi = Musicinfo()
        mi.id = jdict['id']
        mi.title = jdict['title']
        mi.artists = jdict['artists']
        mi.album = jdict['album']
        return mi

if os.path.exists(musicinfoFile):
    with open(musicinfoFile, 'r', encoding='utf-8') as f:
        mis = json.load(f, object_hook = Musicinfo.Jsonto)

#缓存中查找歌曲信息
def findmi(id):
    for i, mi in enumerate(mis):
        if mi.id == id:
            return i
    return None

#根据id下载音乐
def downloadMusic(id, Overlay = False):
    url = 'http://music.163.com/song/media/outer/url?id=%s.mp3' %(id)

    filename = str(id) + '.mp3'
    filepath = os.path.join(folder, filename)

    if not os.path.exists(filepath) or Overlay:
        try:
            logger.debug('open url: %s', url)
            r = urllib.request.urlopen(url)
            logger.debug('response status is: %s', r.status)
            data = r.read()
            if len(data) < 1024*500:
                mi = getMusicinfo(id)
                msg = 'FAILED: size of %s.mp3 is too small:%skb' %(id, len(data)//1024)
                print(msg)
                msg = '%s download failed' %(mi.__str__())
                errorMsg.append(msg)
                return None
            with open(filepath, 'wb') as f:
                f.write(data)
                print(filename, 'download success!')
        except Exception as e:
            msg = 'FAILED:%s' %(e)
            errorMsg.append(msg)
            print(msg)
    else:
        print('%s is already exist!' %(filename))

#根据id获取歌单音乐id列表
def getPlaylist(id):
    url = 'http://music.163.com/playlist?id=%s' %(id)
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'})
    contents = r.text
    res = r'<ul class="f-hide">(.*?)</ul>'
    mm = re.findall(res, contents, re.S | re.M)
    if mm:
        contents = mm[0]
    else:
        print('获取歌单信息失败！')
        os._exit(0)

    res = r'<li>(.*?)</li>'
    mm = re.findall(res, contents, re.S | re.M)

    playlist = []
    for value in mm:
        res = r'<a href=\"/song\?id=(\d+)\">(.*?)</a>'
        finds = re.match(res, value, re.S | re.M)
        playlist.append(finds[1])
    return playlist

#获取歌曲信息
def getMusicinfo(id, forceRequest = False):
    idx = findmi(id)
    if idx and not forceRequest:
        return mis[idx]
    url = 'http://music.163.com/song?id=%s' %(id)
    r = requests.get(url,headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'})
    contents = r.text

    res = r'<title>(.*?)</title>'
    mm = re.findall(res, contents, re.S | re.M)
    title = mm[0]
    
    res = r'<a href="/album\?id=\d+" class="s-fc7">(.*?)</a>'
    mm = re.findall(res, contents, re.S | re.M)

    infos = title.split(' - ')
    mi = Musicinfo()
    mi.id = id
    mi.title = infos[0]
    mi.artists = infos[1].split('/')
    mi.album = mm[0]
    if idx:
        mis[idx] = mi
    else:
        mis.append(mi)
    return mi

#设置歌曲信息
def setMusicinfo(id):
    file = str(id) + '.mp3'
    if os.path.exists(os.path.join(folder, file)):
        mi = getMusicinfo(id)
        if not mi:
            msg = 'FAILED: no music info of id: %s' %(id)
            errorMsg.append(msg)
            print(msg)
            return None
        audiofile = eyed3.load(os.path.join(folder, file))
        if audiofile:
            try:
                audiofile.initTag()
                audiofile.tag.title = mi.title
                audiofile.tag.album = mi.album
                audiofile.tag.artist = ' / '.join(mi.artists)
                audiofile.tag.save()
                filename = '%s - %s(id=%s).mp3' %(mi.title, ','.join(mi.artists), id)
                rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
                filename = re.sub(rstr, '', filename)
                os.rename(os.path.join(folder, file), os.path.join(folder, filename))
                print('rename %s => %s success!' %(file, filename))
            except Exception as e:
                msg = 'FAILED:%s' %(e)
                errorMsg.append(msg)
                print(msg)
        else:
            msg = 'FAILED:', mi.title, file, '获取tag失败！'
            errorMsg.append(msg)
            print(msg)

#设置所有歌曲信息
def setAllMusicinfo():
    for file in os.listdir(folder):
        mm = re.match(r'(\d+).mp3', file)
        if mm:
            setMusicinfo(mm[1])

#歌曲是否已下载
def isMusicExist(id):
    res = r'.*?\(id=(\d+)\).mp3'
    for file in os.listdir(folder):
        mm = re.findall(res, file, re.S | re.M)
        if mm and mm[0] == str(id):
            return file
    return None

#下载歌单
def downloadPlaylist(id):
    playlist = getPlaylist(id)
    num = len(playlist)
    for i, id in enumerate(playlist):
        print(r'(%s/%s)' %(i + 1, num))
        r = isMusicExist(id)
        if not r:
            downloadMusic(id)
            setMusicinfo(id)
        else:
            print('%s is already exist!' %(r))

#存储歌曲信息到json文件
with open('musicInfo.json', 'w', encoding='utf-8') as f:
    json.dump(mis, f, default=Musicinfo.toJson, ensure_ascii=False, indent=4)

def findOverlaps():
    overlap = {}
    res = r'.*?\(id=(\d+)\).mp3'
    for file in os.listdir(folder):
        mm = re.findall(res, file, re.S | re.M)
        if mm:
            mi = getMusicinfo(mm[0])
            if mi.title in overlap:
                overlap[mi.title].append(file)
            else:
                overlap[mi.title] = []
                overlap[mi.title].append(file)
    for key in overlap.keys():
                if len(overlap[key]) > 1:
                    print(key, overlap[key])

#歌单对应id
#   下载1 2310694248
#   下载2 2310664796
#   backup 2297363973
#downloadPlaylist(426706864)

setMusicinfo(525239752)

if len(errorMsg) != 0:
    print('error:')
    print('\n'.join(errorMsg))
print('exit')