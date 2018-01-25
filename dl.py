#!/usr/bin/python
#coding:utf8
# requires: python2.7

import math, urllib, urlparse, socket, ssl, sys, threading, select, time, re, json, os
import requests
from collections import OrderedDict

# @Author: RedFoX #

'''
This is an open source project.
You can edit it as you want.
'''

'''
File downloader
download a file from terminal
features:
resume-pause

how this works?
get url file -> download -> pause? -> resume
'''

usage = '''%s <options> URL\n
options:
-yt for downloading youtube video
\t'''%sys.argv[0]


def convert_bytes(size_bytes):
    if size_bytes == 0: return"0B"
    size_name =("B","KB","MB","GB","TB","PB","EB","ZB","YB")
    i = int(math.floor(math.log(size_bytes,1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p,2)
    return"%s %s"%(s, size_name[i])


class argv_handler:
    argv = {}
    obj = True
    must = True
    def add(self, opt, arg_len=1, action=None):
        #
        self.argv[opt] = {'arg_len':arg_len, 'action':action}
    
    def parse(self):
        # parse sys.argv
        pos = 0
        options = OrderedDict() # used to know what option is filed in argv
        argv = sys.argv[1:]
        obj = []
        while pos < len(argv):
            arg = argv[pos]
            #print arg, pos, argv
            if self.argv.has_key(arg): # and not self.argv[arg].has_key('args'):
                # get args
                arg_len = self.argv[arg]['arg_len']
                args = argv[pos+1:pos+arg_len+1]
                #print args
                if len(args) < arg_len:
                    print('%r needs %d argument(s)'%(arg, arg_len))
                    sys.exit(1)
                self.argv[arg]['args'] = args
                pos += len(args)+1
                options[arg] = None
                continue
            
            elif not self.argv.has_key(arg):
                #print('Unknown option: %r'%arg)
                obj.append(arg)
            pos += 1
        if self.obj and len(obj) < 1:
            print('%r need at least 1 obj'%sys.argv[0])
            print("Usage:")
            print(usage)
            sys.exit(1)
        elif self.obj and len(obj) > 0: 
            obj = obj[-1]
        if not options and self.must:
            print('[ ! ] You should give at least 1 option for %r'%sys.argv[0])
            print("Usage:")
            print(usage)
            sys.exit(1)
        return self.argv, obj, options

dbug = True

class pmsg(object):
    def warning(self, msg):
        self.pmsg(msg, 'warning'.upper())
    
    def info(self, msg):
        self.pmsg(msg, 'info'.upper())
    
    
    def pmsg(self, msg, flag=None):
        if flag and isinstance(flag, str):
            msg = '[%s] %s'%(flag, str(msg))
        if dbug:
            sys.stdout.write(msg)
            sys.stdout.flush()

dprint = pmsg()

def format_filename(s):
    import string
    valid_chars ="-_.() %s%s"% (string.ascii_letters, string.digits)
    filename =''.join(c for c in s if c in valid_chars)
    #filename = filename.replace('','_') # I don't like spaces in filenames.
    return filename


class Downloader(object):
    buff_recv = 2048
    def __init__(self,):
        services = {'http':80, 'https':443, 'ftp':23}
        scheme = 'http' # default scheme
        handler.add('-yt', arg_len=0, action=self.youtube)
        handler.add('-bkp', arg_len=0)
        
        args, url, options = handler.parse()
        self.url = url
        if len(options) > 1:
            print('too many options\nPlease choose 1 option only')
            dprint.info('unexpected option: %s\n'%','.join(options.keys()[1:]))
            sys.exit(0)
        option = options.keys()[0]
        # get host from url
        scheme_find = url.find('://')
        if scheme_find > 0:
            scheme = url[:scheme_find]
            url = url[scheme_find+3:]
            if scheme.lower() and not services.has_key(scheme):
                dprint.warning('Don\'t know how to serve %r scheme\n'%(scheme))
                return
            dprint.info('Your scheme %r\n'%scheme)
        else:
            dprint.warning('unknown scheme\nusing default scheme: %s\n'%scheme)
            self.url = scheme+'://'+self.url
        url_path_find = url.find('/')
        if url_path_find > 0:
            url_path = url[url_path_find:]
            host = url[:url_path_find]
            dprint.info('Your url path %r\n'%url_path)
        else:
            url_path = '/'
            host = url
            #dprint.info('no url path')
        dprint.pmsg('Checking your host %r ..\n'%host)
        
        try:
            hostname = socket.gethostbyname(host)
        except socket.gaierror as e:
            #print dir(e)
            if e.errno == -3:
                print('No internet?\n%s'%e.strerror)
                return
            elif e.errno == -2:
                print('Unknown host %r\n%s'%(host, e.strerror))
                return
          
        port = services[scheme]
        print('Connecting to %s:%d'%(hostname, port))
        s = socket.socket()
        try:
            s.connect((hostname, port))
        except socket.error as e:
            print('Could not contact %s:%d\nPlease check your connection\n%s'%(hostname, port, e.strerror))
            return
        self.s = s
        self.url_path = url_path
        self.host = host
        args[option]['action']()
    
    def youtube(self):
        print('~Downloading youtube video')
        # get json video url
        #msg = 'GET %s HTTP/1.1\r\nHost: %s\r\n\r\n'%(self.url_path, self.host)
        headers = {'User-Agent':'Mozilla/5.0 (Linux; Android 6.0.1; A11W Build/HM2014011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.146 Mobile Safari/537.36',
        'Accept':'*/*', 'Connection':'close'}
        try:
            r = requests.get(self.url, headers=headers)
        except Exception as e:
            print("Failed to get your video\nplease try again later")
            print("Error:")
            print(e)
            return
        # parse video url
        dprint.info("parsing...\n")
        pattern = "var bootstrap_data = \"\)\]\}'({.*?})\";"
        JSON = re.compile(pattern, re.DOTALL)
        matches = JSON.search(r.text)
        if not matches:
            print('[ ! ] Invalid Youtube video')
            sys.exit(0)
        ori = matches.group(1)
        ori = ori.replace('\\"','\"')
        ori = ori.replace('\\\\"',"'")
        dprint.info('converting to json\n')
        try:
            data = json.loads(ori)
        except Exception as e:
            print('[ ! ] Not a valid Youtube video')
            sys.exit(1)
        dprint.info('parsing video info.\n')
        #title = data['content']['autonav']['video']['title']
        title = data['content']['swfcfg']['args']['title']
        title = format_filename(title)
        video_raw = data['content']['swfcfg']['args']['adaptive_fmts']
        #print video_url.split('url=')
        #print video_url
        video_url = []
        videos = []
        video_info = [{}]
        index_info = 0
        infos = 0
        videos_data = video_raw.split('\\u0026')
        pos = 0
        # , : end of info
        # split(=)
        #
        while pos < len(videos_data):
            d = str(videos_data[pos])
            eoi = d.split(',')
            
            if len(eoi) > 1:
                # eoi detected
                key, value = eoi[0].split('=')
                #video_info.append((key,value))
                video_info[index_info][key] = value
                #video_info.append('')
                index_info += 1
                video_info.append({})
                key, value = eoi[1].split('=')
                #video_info.append((key,value))
                video_info[index_info][key] = value
                pos += 1
                infos += 1
                continue
            
            key, value = d.split('=')
            if key == 'url':
                # url
                video_url.append(urllib.unquote(urllib.unquote(value)))
            else:
                # info
                #video_info.append((key,value))
                video_info[index_info][key] = value
            pos += 1
        # get video info
        size_bytes = 0
        dprint.info('getting video info..\n')
        for url in video_url:
            #print repr(url)
            #parsed = urlparse.urlparse(url)
            #print parsed
            query = urlparse.parse_qs(url)
            if not query.has_key('itag'):
                continue
            for i in video_info:
                # dict
                itag = i['itag']
                #print query['itag'], itag
                if query['itag'][0] == itag:
                    video_info.remove(i)
                    i['url'] = url
                    i['type'] = urllib.unquote(i['type'])
                    if not i.has_key('quality_label'):
                        i['quality_label'] = ''
                    # get file size
                    try:
                        r = requests.head(url)
                    except Exception as e:
                        #dprint.warning('
                        size = 'unknown'
                    else:
                        #print dir(r.headers)
                        #print r.headers.keys()
                        content_type = r.headers.get('Content-Type')
                        i['content_type'] = content_type
                        if content_type:
                            i['file_type'] = content_type.split('/')[-1]
                        else:
                            i['file_type'] = '?'
                        size = r.headers.get('Content-Length')
                        size_bytes = int(r.headers.get('Content-Length'))
                        i['size_bytes'] = size_bytes
                        if int(r.status_code) == 200 and size:
                            i['size'] = convert_bytes(int(size))
                        else:
                            i['size'] = '? Byte'
                    videos.append(i)
                    break
                
        print title
        #print videos
        #print len(videos)
        count = 0
        print("Select file to download:")
        for vid in videos:
            # quality_label, type, bitrate
            m = '[ %d ] {quality_label} ({type}) {size}'.format(**vid)%count
            count += 1
            print m
        #print len( video_url ), infos
        #print video_info
        index = raw_input('Please select : ')
        #
        
        try:
            index = int(index)
        except ValueError as e:
            return
        try:
            size_bytes = videos[index]['size_bytes']
            URL = videos[index]['url']
            content_type = videos[index]['content_type']
            xtype = videos[index]['file_type']
            quality = '(%s)'%videos[index]['quality_label']
            name = title+' '+quality+'.'+xtype
            if len(name) > 255:
                name = title[:255-(len(quality)+1+len(xtype)+1)]+' '+quality+'.'+xtype
           
        except IndexError as e:
            print e
            return
        choices = [('resume','ab'),('re-download','wb')]
        # resume : None
        # re-download : write then close (kosongin)
        pos = 0
        byte_start = 0
        byte_end = ''
        size_now = 0
        if os.path.exists(name) and os.path.isfile(name):
            # file already exists
            print('file already exists, do you want to?')
            while pos < len(choices):
                print '[%d] %s'%(pos, choices[pos][0])
                pos += 1
            index = raw_input('Please select : ')
            #
            
            try:
                index = int(index)
            except ValueError:
                return
            try:
                mode = choices[index][1]
            except IndexError as e:
                return
            
            f = open(name, mode)
            f.write('')
            f.close()
            size_now = int(os.path.getsize(name));
            if mode == 'ab': byte_start = size_now; byte_end = ''
        elif os.path.exists(name) and os.path.isdir(name):
            # it is a dir
            print('a dir named %r is exists\nPlease delete it first')
            return
            #file will be downloaded into %r dir'%(name, name)) 
            name = '%s/%s'%(name, name)
        else:
            # file or dir doesn't exists
            pass
        self.video_data = {}
        parsed = urlparse.urlparse(URL)
        host = parsed.netloc
        query = urlparse.parse_qs(parsed.query)
        querys = '&'.join( [ q+'='+','.join([ urllib.quote(x) for x in query[q] ]) for q in query ] )
        url = parsed.scheme+'://'+host+ parsed.path+'?'+querys
        self.video_data['url'] = url
        self.video_data['host'] = host
        self.video_data['content_type'] = content_type
        self.video_data['byte_start'] = byte_start
        self.video_data['byte_end'] = byte_end
        self.pkt = '''GET {url} HTTP/1.1\r
Accept: */*\r
Range: bytes={byte_start}-{byte_end}\r
Connection: close\r
Host: {host}\r
\r
'''.format(**self.video_data)
        self.name = name
        self.size_bytes = size_bytes
        self.size_now = size_now
        #print self.video_data['url'] 
        self.download()
        
    def download(self):
        print('Downloading %r'%self.name)
        now = self.size_now
        size_bytes = self.size_bytes
        sock = socket.socket()
        context = ssl._create_unverified_context()   
        conn = context.wrap_socket(sock)
        conn.connect((self.video_data['host'], 443))
        print('Connected')
        # send pkt then recv
        msg = self.pkt
        while msg:
            msg = msg[conn.send(msg):]
        inputs = [conn]
        get_header = True
        headers = ''
        res_line = None
        print("Downloading...")
        while True:
            i,o,e = select.select(inputs, inputs, inputs)
            if conn in i:
                try:
                    response = conn.recv(self.buff_recv)
                except Exception as e:
                    print e
                    break
                if not response: break
                if get_header:
                    pos = 0
                    data = response.splitlines(1)
                    while pos < len(data):
                        lines = data[pos]
                        if not lines.splitlines()[0]:
                            get_header = False
                            response = ''.join(data[pos+1:])
                            res_line = headers.splitlines(1)[0].rstrip().split(' ',2)
                            headers = ''.join(headers.splitlines(1)[1:])
                            import mimetools, StringIO
                            headers = mimetools.Message( StringIO.StringIO(headers))
                            print ' '.join(res_line[1:])
                            if headers.has_key('content-type') and headers['content-type'] != self.video_data['content_type']:
                                print('Invalid content type: %r != %r'%(headers['content-type'] , self.video_data['content_type']))
                                return
                            elif not headers.has_key('content-type'):
                                print('Content unknown')
                                return
                            #if headers.has_key('content-length'):
                            #    size_bytes = int(headers['content-length'])
                            break
                        headers += lines
                        pos += 1
                    if get_header:
                        continue
                now += len(response)
                self.f = open(self.name,'ab')
                self.f.write(response)
                self.f.close()
                print '%s/%s'%(convert_bytes(now),convert_bytes(size_bytes))



if len(sys.argv) > 1:
    handler = argv_handler()
    dl = Downloader()
    #print(sys.argv)


