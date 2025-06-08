# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Modify: 2024-04-03
# Repo: https://github.com/Cp0204/quark_auto_save
# ConfigFile: quark_config.json
"""
new Env('夸克自动追更');
0 8,18,20 * * * quark_auto_save.py
"""
import logging
import os
import re
import sys
import json
import time
import random
from json import JSONDecodeError

import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s",
    datefmt="%m-%d %H:%M:%S",
)

# 兼容青龙
try:
    from treelib import Tree
except:
    logging.info("正在尝试自动安装依赖...")
    os.system("pip3 install treelib &> /dev/null")
    from treelib import Tree

CONFIG_DATA = {}
NOTIFYS = []
GH_PROXY = os.environ.get("GH_PROXY", "https://ghproxy.net/")

MAGIC_REGEX = {
    "$TV": {
        "pattern": ".*?(S\\d{1,2}E)?P?(\\d{1,3}).*?\\.(mp4|mkv)",
        "replace": "\\1\\2.\\3",
    },
}


# 魔法正则匹配
def magic_regex_func(pattern, replace, taskname=""):
    keyword = pattern
    if keyword in CONFIG_DATA["magic_regex"]:
        pattern = CONFIG_DATA["magic_regex"][keyword]["pattern"]
        if replace == "":
            replace = CONFIG_DATA["magic_regex"][keyword]["replace"]
    if taskname:
        replace = replace.replace("$TASKNAME", taskname)
    # 正则文件名匹配
    year = datetime.now().year
    reg_arr = [
        {
            # '2024.06.08-第4期.mp4' to '20240608-第4期.mp4'
            'pattern': re.compile(r'(\d{4})\.(\d{2})\.(\d{2})'),
            'repl': r'\1\2\3'
        },
        {
            # '第20240728期喜人奇妙夜.mp4' to '20240728期喜人奇妙夜.mp4'
            'pattern': re.compile(r'^第((\d{8})([\s\S])*)'),
            'repl': r'\1'
        },
        {
            # '2025.4.4-第11期下.mp4' to '20250404-第11期下.mp4'
            'pattern': re.compile(r'(\d{4})\.(\d{1,2})\.(\d{1,2})'),
            'repl': lambda m: f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"
        },
        {
            # 兜底配置 
            # '0422春日焕新特辑毛雪汪小屋春日大变样.mp4' to '20240422春日焕新特辑毛雪汪小屋春日大变样.mp4'
            'pattern': re.compile(r'^(\d{4})(?=\D)'),
            'repl': fr'{year}\1'
        }
    ]
    return pattern, replace, reg_arr


# 发送通知消息
def send_ql_notify(title, body):
    try:
        # 导入通知模块
        import notify

        # 如未配置 push_config 则使用青龙环境通知设置
        if CONFIG_DATA.get("push_config"):
            CONFIG_DATA["push_config"]["CONSOLE"] = True
            notify.push_config = CONFIG_DATA["push_config"]
        notify.send(title, body)
    except Exception as e:
        if e:
            logging.info("发送通知消息失败！")


# 添加消息
def add_notify(text):
    global NOTIFYS
    NOTIFYS.append(text)
    logging.info(f"📢{text}")
    return text


# 下载配置
def download_file(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response.content)
        return True
    else:
        return False


# 读取CK
def get_cookies(cookie_val):
    if isinstance(cookie_val, list):
        return cookie_val
    elif cookie_val:
        if "\n" in cookie_val:
            return cookie_val.split("\n")
        else:
            return [cookie_val]
    else:
        return False


def update_alist(task):
    try:
        alist_leisure_strm_create = json.loads(task['alist_leisure_strm_create'])
    except JSONDecodeError as error:
        return
    if not alist_leisure_strm_create:
        pass
    if 'preserve_parent_directory' not in alist_leisure_strm_create:
        alist_leisure_strm_create['preserve_parent_directory'] = 'False'
    if 'keep_original_file_name' not in alist_leisure_strm_create:
        alist_leisure_strm_create['keep_original_file_name'] = 'False'
    if 'refresh_dir' not in alist_leisure_strm_create:
        alist_leisure_strm_create['refresh_dir'] = 'True'
    if 'series_name' not in alist_leisure_strm_create:
        alist_leisure_strm_create['series_name'] = task['taskname']
    if 'season_num' not in alist_leisure_strm_create:
        alist_leisure_strm_create['season_num'] = '2'
    if 'create_nfo' not in alist_leisure_strm_create:
        alist_leisure_strm_create['create_nfo'] = 'True'
    if 'url' not in alist_leisure_strm_create:
        alist_leisure_strm_create['url'] = '/quark' + task['savepath']
    # 两分钟后再调用接口
    requests.get(url=CONFIG_DATA.get('leisure_strm_create'), params=alist_leisure_strm_create)


class Quark:
    BASE_URL = "https://drive-pc.quark.cn"
    BASE_URL_APP = "https://drive-m.quark.cn"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 Safari/537.36 Channel/pckk_other_ch"

    def __init__(self, cookie, index=None):
        self.cookie = cookie.strip()
        self.index = index + 1
        self.is_active = False
        self.nickname = ""
        self.mparam = self.match_mparam_form_cookie(cookie)
        self.savepath_fid = {"/": "0"}

    def match_mparam_form_cookie(self, cookie):
        mparam = {}
        kps_match = re.search(r"(?<!\w)kps=([a-zA-Z0-9%]+)[;&]?", cookie)
        sign_match = re.search(r"(?<!\w)sign=([a-zA-Z0-9%]+)[;&]?", cookie)
        vcode_match = re.search(r"(?<!\w)vcode=([a-zA-Z0-9%]+)[;&]?", cookie)
        if kps_match and sign_match and vcode_match:
            mparam = {
                "kps": kps_match.group(1).replace("%25", "%"),
                "sign": sign_match.group(1).replace("%25", "%"),
                "vcode": vcode_match.group(1).replace("%25", "%"),
            }
        return mparam

    def _send_request(self, method, url, **kwargs):
        headers = {
            "cookie": self.cookie,
            "content-type": "application/json",
            "user-agent": self.USER_AGENT,
        }
        if "headers" in kwargs:
            headers = kwargs["headers"]
            del kwargs["headers"]
        if self.mparam and "share" in url and self.BASE_URL in url:
            url = url.replace(self.BASE_URL, self.BASE_URL_APP)
            kwargs["params"].update(
                {
                    "device_model": "M2011K2C",
                    "entry": "default_clouddrive",
                    "_t_group": "0%3A_s_vp%3A1",
                    "dmn": "Mi%2B11",
                    "fr": "android",
                    "pf": "3300",
                    "bi": "35937",
                    "ve": "7.4.5.680",
                    "ss": "411x875",
                    "mi": "M2011K2C",
                    "nt": "5",
                    "nw": "0",
                    "kt": "4",
                    "pr": "ucpro",
                    "sv": "release",
                    "dt": "phone",
                    "data_from": "ucapi",
                    "kps": self.mparam.get("kps"),
                    "sign": self.mparam.get("sign"),
                    "vcode": self.mparam.get("vcode"),
                    "app": "clouddrive",
                    "kkkk": "1",
                }
            )
            del headers["cookie"]
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            # print(f"{response.text}")
            # response.raise_for_status()  # 检查请求是否成功，但返回非200也会抛出异常
            return response
        except Exception as e:
            print(f"_send_request error:\n{e}")
            fake_response = requests.Response()
            fake_response.status_code = 500
            fake_response._content = (
                b'{"status": 500, "code": 1, "message": "request error"}'
            )
            return fake_response

    def common_headers(self):
        headers = {
            "cookie": self.cookie,
            "content-type": "application/json",
            "user-agent": self.USER_AGENT
        }
        return headers

    def init(self):
        account_info = self.get_account_info()
        if account_info:
            self.is_active = True
            self.nickname = account_info["nickname"]
            return account_info
        else:
            return False

    def get_account_info(self):
        url = "https://pan.quark.cn/account/info"
        querystring = {"fr": "pc", "platform": "pc"}
        headers = {
            "cookie": self.cookie,
            "content-type": "application/json",
        }
        response = requests.request(
            "GET", url, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            return response["data"]
        else:
            return False

    def get_growth_info(self):
        url = f"{self.BASE_URL}/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.mparam.get("kps"),
            "sign": self.mparam.get("sign"),
            "vcode": self.mparam.get("vcode"),
        }
        headers = {
            "content-type": "application/json",
        }
        response = requests.request(
            "GET", url, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            return response["data"]
        else:
            return False

    def get_growth_sign(self):
        url = f"{self.BASE_URL}/1/clouddrive/capacity/growth/sign"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.mparam.get("kps"),
            "sign": self.mparam.get("sign"),
            "vcode": self.mparam.get("vcode"),
        }
        payload = {
            "sign_cyclic": True,
        }
        headers = {
            "content-type": "application/json",
        }
        response = requests.request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            return True, response["data"]["sign_daily_reward"]
        else:
            return False, response["message"]

    def get_id_from_url(self, url):
        url = url.replace("https://pan.quark.cn/s/", "")
        pattern = r"(\w+)(\?pwd=(\w+))?(#/list/share.*/(\w+))?"
        match = re.search(pattern, url)
        if match:
            pwd_id = match.group(1)
            passcode = match.group(3) if match.group(3) else ""
            pdir_fid = match.group(5) if match.group(5) else 0
            return pwd_id, passcode, pdir_fid
        else:
            return None

    # 可验证资源是否失效
    def get_stoken(self, pwd_id, passcode=""):
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/token"
        querystring = {"pr": "ucpro", "fr": "pc"}
        payload = {"pwd_id": pwd_id, "passcode": passcode}
        headers = self.common_headers()
        response = requests.request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            return True, response["data"]["stoken"]
        else:
            return False, response["message"]

    def get_detail(self, pwd_id, stoken, pdir_fid, _fetch_share=0):
        list_merge = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/detail"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "pwd_id": pwd_id,
                "stoken": stoken,
                "pdir_fid": pdir_fid,
                "force": "0",
                "_page": page,
                "_size": "50",
                "_fetch_banner": "0",
                "_fetch_share": _fetch_share,
                "_fetch_total": "1",
                "_sort": "file_type:asc,updated_at:desc",
            }
            response = self._send_request("GET", url, params=querystring).json()
            if response["code"] != 0:
                return response
            if response["data"]["list"]:
                list_merge += response["data"]["list"]
                page += 1
            else:
                break
            if len(list_merge) >= response["metadata"]["_total"]:
                break
        response["data"]["list"] = list_merge
        return response

    def get_fids(self, file_paths):
        fids = []
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/info/path_list"
            querystring = {"pr": "ucpro", "fr": "pc"}
            payload = {"file_path": file_paths[:50], "namespace": "0"}
            headers = self.common_headers()
            response = requests.request(
                "POST", url, json=payload, headers=headers, params=querystring
            ).json()
            if response["code"] == 0:
                fids += response["data"]
                file_paths = file_paths[50:]
            else:
                logging.info(f"获取目录ID：失败, {response['message']}")
                break
            if len(file_paths) == 0:
                break
        return fids

    def ls_dir(self, pdir_fid, **kwargs):
        list_merge = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/sort"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "pdir_fid": pdir_fid,
                "_page": page,
                "_size": "50",
                "_fetch_total": "1",
                "_fetch_sub_dirs": "0",
                "_sort": "file_type:asc,updated_at:desc",
                "_fetch_full_path": kwargs.get("fetch_full_path", 0),
            }
            response = self._send_request("GET", url, params=querystring).json()
            if response["code"] != 0:
                return response
            if response["data"]["list"]:
                list_merge += response["data"]["list"]
                page += 1
            else:
                break
            if len(list_merge) >= response["metadata"]["_total"]:
                break
        response["data"]["list"] = list_merge
        return response

    def save_file(self, fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken):
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/save"
        querystring = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "app": "clouddrive",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": datetime.now().timestamp(),
        }
        payload = {
            "fid_list": fid_list,
            "fid_token_list": fid_token_list,
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "scene": "link",
        }
        headers = self.common_headers()
        response = requests.request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        return response

    def mkdir(self, dir_path):
        url = f"{self.BASE_URL}/1/clouddrive/file"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {
            "pdir_fid": "0",
            "file_name": "",
            "dir_path": dir_path,
            "dir_init_lock": False,
        }
        headers = self.common_headers()
        response = requests.request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        return response

    def rename(self, fid, file_name):
        url = f"{self.BASE_URL}/1/clouddrive/file/rename"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"fid": fid, "file_name": file_name}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def delete(self, filelist):
        url = "{self.BASE_URL}/1/clouddrive/file/delete"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"action_type": 2, "filelist": filelist, "exclude_fids": []}
        headers = self.common_headers()
        response = requests.request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        return response

    def recycle_list(self, page=1, size=30):
        url = f"{self.BASE_URL}/1/clouddrive/file/recycle/list"
        querystring = {
            "_page": page,
            "_size": size,
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
        }
        headers = self.common_headers()
        response = requests.request(
            "GET", url, headers=headers, params=querystring
        ).json()
        return response["data"]["list"]

    def recycle_remove(self, record_list):
        url = f"{self.BASE_URL}/1/clouddrive/file/recycle/remove"
        querystring = {"uc_param_str": "", "fr": "pc", "pr": "ucpro"}
        payload = {
            "select_mode": 2,
            "record_list": record_list,
        }
        headers = self.common_headers()
        response = requests.request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        return response

    def update_savepath_fid(self, tasklist):
        dir_paths = [
            re.sub(r"/{2,}", "/", f"/{item['savepath']}")
            for item in tasklist
            if not item.get("enddate")
               or (
                       datetime.now().date()
                       <= datetime.strptime(item["enddate"], "%Y-%m-%d").date()
               )
        ]
        if not dir_paths:
            return False
        dir_paths_exist_arr = self.get_fids(dir_paths)
        dir_paths_exist = [item["file_path"] for item in dir_paths_exist_arr]
        # 比较创建不存在的
        dir_paths_unexist = list(set(dir_paths) - set(dir_paths_exist) - set(["/"]))
        for dir_path in dir_paths_unexist:
            mkdir_return = self.mkdir(dir_path)
            if mkdir_return["code"] == 0:
                new_dir = mkdir_return["data"]
                dir_paths_exist_arr.append(
                    {"file_path": dir_path, "fid": new_dir["fid"]}
                )
                logging.info(f"创建文件夹：{dir_path}")
            else:
                logging.info(f"创建文件夹：{dir_path} 失败, {mkdir_return['message']}")
        # 储存目标目录的fid
        for dir_path in dir_paths_exist_arr:
            self.savepath_fid[dir_path["file_path"]] = dir_path["fid"]
        # print(dir_paths_exist_arr)

    def do_save_check(self, shareurl, savepath):
        try:
            pwd_id, passcode, pdir_fid = self.get_id_from_url(shareurl)
            is_sharing, stoken = self.get_stoken(pwd_id, passcode)
            share_file_list = self.get_detail(pwd_id, stoken, pdir_fid)["data"]["list"]
            fid_list = [item["fid"] for item in share_file_list]
            fid_token_list = [item["share_fid_token"] for item in share_file_list]
            file_name_list = [item["file_name"] for item in share_file_list]
            if not fid_list:
                return
            get_fids = self.get_fids([savepath])
            to_pdir_fid = (
                get_fids[0]["fid"] if get_fids else self.mkdir(savepath)["data"]["fid"]
            )
            save_file = self.save_file(
                fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken
            )
            if save_file["code"] == 41017:
                return
            elif save_file["code"] == 0:
                dir_file_list = self.ls_dir(to_pdir_fid)["data"]["list"]
                del_list = [
                    item["fid"]
                    for item in dir_file_list
                    if (item["file_name"] in file_name_list)
                    and ((datetime.now().timestamp() - item["created_at"]) < 60)
                ]
                if del_list:
                    self.delete(del_list)
                    recycle_list = self.recycle_list()
                    record_id_list = [
                        item["record_id"]
                        for item in recycle_list
                        if item["fid"] in del_list
                    ]
                    self.recycle_remove(record_id_list)
                return save_file
            else:
                return False
        except Exception as e:
            if os.environ.get("DEBUG") == True:
                logging.info(f"转存测试失败: {str(e)}")

    def do_save_task(self, task):
        # 判断资源失效记录
        if task.get("shareurl_ban"):
            logging.info(f"《{task['taskname']}》：{task['shareurl_ban']}")
            return

        # 链接转换所需参数
        pwd_id, passcode, pdir_fid = self.get_id_from_url(task["shareurl"])
        # logging.info("match: ", pwd_id, pdir_fid)

        # 获取stoken，同时可验证资源是否失效
        is_sharing, stoken = self.get_stoken(pwd_id, passcode)
        if not is_sharing:
            add_notify(f"❌《{task['taskname']}》：{stoken}\n")
            task["shareurl_ban"] = stoken
            return
        # logging.info("stoken: ", stoken)

        updated_tree = self.dir_check_and_save(task, pwd_id, stoken, pdir_fid)
        if updated_tree.size(1) > 0:
            add_notify(f"✅《{task['taskname']}》添加追更：\n{updated_tree}")
            return True
        else:
            logging.info(f"任务结束：没有新的转存任务")
            return False

    def dir_check_and_save(self, task, pwd_id, stoken, pdir_fid="", subdir_path=""):
        tree = Tree()
        tree.create_node(task["savepath"], pdir_fid)
        # 获取分享文件列表
        share_file_list = self.get_detail(pwd_id, stoken, pdir_fid)["data"]["list"]
        # logging.info("share_file_list: ", share_file_list)

        if not share_file_list:
            if subdir_path == "":
                task["shareurl_ban"] = "分享为空，文件已被分享者删除"
                add_notify(f"《{task['taskname']}》：{task['shareurl_ban']}")
            return tree
        elif (
                len(share_file_list) == 1
                and share_file_list[0]["dir"]
                and subdir_path == ""
        ):  # 仅有一个文件夹
            logging.info("🧠 该分享是一个文件夹，读取文件夹内列表")
            share_file_list = self.get_detail(
                pwd_id, stoken, share_file_list[0]["fid"]
            )["data"]["list"]

        # 获取目标目录文件列表
        savepath = re.sub(r"/{2,}", "/", f"/{task['savepath']}{subdir_path}")
        if not self.savepath_fid.get(savepath):
            if get_fids := self.get_fids([savepath]):
                self.savepath_fid[savepath] = get_fids[0]["fid"]
            else:
                logging.info(f"❌ 目录 {savepath} fid获取失败，跳过转存")
                return tree
        to_pdir_fid = self.savepath_fid[savepath]
        dir_file_list = self.ls_dir(to_pdir_fid)["data"]["list"]
        # logging.info("dir_file_list: ", dir_file_list)

        # 需保存的文件清单
        need_save_list = []
        reg_arr = []
        # 添加符合的
        for share_file in share_file_list:
            share_file_fid = share_file['fid']
            if share_file["dir"] and task.get("update_subdir", False):
                pattern, replace = task["update_subdir"], ""
            else:
                pattern, replace, reg_arr = magic_regex_func(
                    task["pattern"], task["replace"], task["taskname"]
                )
            # 正则文件名匹配
            if re.search(pattern, share_file["file_name"]):
                # 替换后的文件名
                save_name = (
                    re.sub(pattern, replace, share_file["file_name"])
                    if replace != ""
                    else share_file["file_name"]
                )
                for reg in reg_arr:
                    if re.match(reg['pattern'], share_file["file_name"]):
                        save_name = re.sub(reg['pattern'], reg['repl'], share_file["file_name"])
                        break
                # 忽略后缀
                if task.get("ignore_extension") and not share_file["dir"]:
                    compare_func = lambda a, b1, b2: (
                            os.path.splitext(a)[0] == os.path.splitext(b1)[0]
                            or os.path.splitext(a)[0] == os.path.splitext(b2)[0]
                    )
                else:
                    compare_func = lambda a, b1, b2: (a == b1 or a == b2)
                # 判断目标目录文件是否存在
                # todo 将share_file_list中需要保存的share_file的fid存储至数据库，通过对比fid确定是否是新增的文件
                file_exists = any(
                    compare_func(
                        dir_file["file_name"], share_file["file_name"], save_name
                    )
                    for dir_file in dir_file_list
                )
                if not file_exists:
                    share_file["save_name"] = save_name
                    need_save_list.append(share_file)
                elif share_file["dir"]:
                    # 存在并是一个文件夹
                    if task.get("update_subdir", False):
                        if re.search(task["update_subdir"], share_file["file_name"]):
                            logging.info(f"检查子文件夹：{savepath}/{share_file['file_name']}")
                            subdir_tree = self.dir_check_and_save(
                                task,
                                pwd_id,
                                stoken,
                                share_file["fid"],
                                f"{subdir_path}/{share_file['file_name']}",
                            )
                            if subdir_tree.size(1) > 0:
                                # 合并子目录树
                                tree.create_node(
                                    "📁" + share_file["file_name"],
                                    share_file["fid"],
                                    parent=pdir_fid,
                                )
                                tree.merge(share_file["fid"], subdir_tree, deep=False)
            # 指定文件开始订阅/到达指定文件（含）结束历遍
            if share_file["fid"] == task.get("startfid", ""):
                break

        fid_list = [item["fid"] for item in need_save_list]
        fid_token_list = [item["share_fid_token"] for item in need_save_list]
        save_name_list = [item["save_name"] for item in need_save_list]
        if fid_list:
            save_file_return = self.save_file(
                fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken
            )
            err_msg = None
            if save_file_return["code"] == 0:
                task_id = save_file_return["data"]["task_id"]
                query_task_return = self.query_task(task_id)
                if query_task_return["code"] == 0:
                    save_name_list.sort()
                    # 建立目录树
                    for item in need_save_list:
                        icon = (
                            "📁"
                            if item["dir"] == True
                            else "🎞️" if item["obj_category"] == "video" else ""
                        )
                        tree.create_node(
                            f"{icon}{item['save_name']}", item["fid"], parent=pdir_fid
                        )
                else:
                    err_msg = query_task_return["message"]
            else:
                err_msg = save_file_return["message"]
            if err_msg:
                add_notify(f"❌《{task['taskname']}》转存失败：{err_msg}\n")
        return tree

    def query_task(self, task_id):
        retry_index = 0
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/task"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "task_id": task_id,
                "retry_index": retry_index,
                "__dt": int(random.uniform(1, 5) * 60 * 1000),
                "__t": datetime.now().timestamp(),
            }
            headers = self.common_headers()
            response = requests.request(
                "GET", url, headers=headers, params=querystring
            ).json()
            if response["data"]["status"] != 0:
                if retry_index > 0:
                    logging.info('')
                break
            else:
                if retry_index == 0:
                    logging.info(
                        f"正在等待[{response['data']['task_title']}]执行结果"
                    )
                else:
                    logging.info(".")
                retry_index += 1
                time.sleep(0.500)
        return response

    def do_rename_task(self, task, subdir_path=""):
        pattern, replace, reg_arr = magic_regex_func(
            task["pattern"], task["replace"], task["taskname"]
        )
        if (not pattern or not replace) and not reg_arr:
            return 0
        savepath = re.sub(r"/{2,}", "/", f"/{task['savepath']}{subdir_path}")
        if not self.savepath_fid.get(savepath):
            self.savepath_fid[savepath] = self.get_fids([savepath])[0]["fid"]
        # 转成成功 但是我的文件里并没有
        time.sleep(5)
        dir_file_list = self.ls_dir(self.savepath_fid[savepath])["data"]["list"]
        dir_file_name_list = [item["file_name"] for item in dir_file_list]
        is_rename_count = 0
        for dir_file in dir_file_list:
            if dir_file["dir"]:
                is_rename_count += self.do_rename_task(
                    task, f"{subdir_path}/{dir_file['file_name']}"
                )
            if re.search(pattern, dir_file["file_name"]):
                save_name = (
                    re.sub(pattern, replace, dir_file["file_name"])
                    if replace != ""
                    else dir_file["file_name"]
                )
                for reg in reg_arr:
                    if re.match(reg['pattern'], dir_file["file_name"]):
                        save_name = re.sub(reg['pattern'], reg['repl'], dir_file["file_name"])
                        break
                # logging.info(f'save_name: {save_name}, dir_file_name: {dir_file["file_name"]}')
                if save_name != dir_file["file_name"] and (
                        save_name not in dir_file_name_list
                ):
                    logging.info(f"重命名：{dir_file['file_name']} → {save_name}")
                    rename_return = self.rename(dir_file["fid"], save_name)
                    if rename_return["code"] == 0:
                        is_rename_count += 1
                    else:
                        logging.info(
                            f"重命名：{dir_file['file_name']} → {save_name} 失败，{rename_return['message']}"
                        )
        return is_rename_count > 0


class Emby:
    def __init__(self, emby_url, emby_apikey):
        self.is_active = False
        if emby_url and emby_apikey:
            self.emby_url = emby_url
            self.emby_apikey = emby_apikey
            if self.get_info():
                self.is_active = True

    def get_info(self):
        url = f"{self.emby_url}/emby/System/Info"
        headers = {"X-Emby-Token": self.emby_apikey}
        querystring = {}
        response = requests.request("GET", url, headers=headers, params=querystring)
        if "application/json" in response.headers["Content-Type"]:
            response = response.json()
            logging.info(
                f"Emby媒体库: {response.get('ServerName', '')} v{response.get('Version', '')}"
            )
            return True
        else:
            logging.info(f"Emby媒体库: 连接失败❌ {response.text}")
            return False

    def refresh(self, emby_id):
        if emby_id:
            url = f"{self.emby_url}/emby/Items/{emby_id}/Refresh"
            headers = {"X-Emby-Token": self.emby_apikey}
            querystring = {
                "Recursive": "true",
                "MetadataRefreshMode": "FullRefresh",
                "ImageRefreshMode": "FullRefresh",
                "ReplaceAllMetadata": "false",
                "ReplaceAllImages": "false",
            }
            response = requests.request(
                "POST", url, headers=headers, params=querystring
            )
            if response.text == "":
                logging.info(f"🎞 刷新Emby媒体库：成功✅")
                return True
            else:
                logging.info(f"🎞 刷新Emby媒体库：{response.text}❌")
                return False

    def search(self, media_name):
        if media_name:
            url = f"{self.emby_url}/emby/Items"
            headers = {"X-Emby-Token": self.emby_apikey}
            querystring = {
                "IncludeItemTypes": "Series",
                "StartIndex": 0,
                "SortBy": "SortName",
                "SortOrder": "Ascending",
                "ImageTypeLimit": 0,
                "Recursive": "true",
                "SearchTerm": media_name,
                "Limit": 10,
                "IncludeSearchTypes": "false",
            }
            response = requests.request("GET", url, headers=headers, params=querystring)
            if "application/json" in response.headers["Content-Type"]:
                response = response.json()
                if response.get("Items"):
                    for item in response["Items"]:
                        if item["IsFolder"]:
                            logging.info(
                                f"🎞 《{item['Name']}》匹配到Emby媒体库ID：{item['Id']}"
                            )
                            return item["Id"]
            else:
                logging.info(f"🎞 搜索Emby媒体库：{response.text}❌")
        return False


def verify_account(account):
    # 验证账号
    logging.info(f"▶️ 验证第{account.index}个账号")
    if "__uid" not in account.cookie:
        logging.info(f"💡 不存在cookie必要参数，判断为仅签到")
        return False
    else:
        account_info = account.init()
        if not account_info:
            add_notify(f"👤 第{account.index}个账号登录失败，cookie无效❌")
            return False
        else:
            logging.info(f"👤 账号昵称: {account_info['nickname']}✅")
            return True


def format_bytes(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


def do_sign(account):
    if not account.mparam:
        logging.info("⏭️ 移动端参数未设置，跳过签到")
        logging.info('')
        return
    # 每日领空间
    growth_info = account.get_growth_info()
    if growth_info:
        growth_message = f"💾 {'88VIP' if growth_info['88VIP'] else '普通用户'} 总空间：{format_bytes(growth_info['total_capacity'])}，签到累计获得：{format_bytes(growth_info['cap_composition'].get('sign_reward', 0))}"
        if growth_info["cap_sign"]["sign_daily"]:
            sign_message = f"📅 签到记录: 今日已签到+{int(growth_info['cap_sign']['sign_daily_reward'] / 1024 / 1024)}MB，连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})✅"
            message = f"{sign_message}\n{growth_message}"
            logging.info(message)
        else:
            sign, sign_return = account.get_growth_sign()
            if sign:
                sign_message = f"📅 执行签到: 今日签到+{int(sign_return / 1024 / 1024)}MB，连签进度({growth_info['cap_sign']['sign_progress'] + 1}/{growth_info['cap_sign']['sign_target']})✅"
                message = f"{sign_message}\n{growth_message}"
                if (
                        CONFIG_DATA.get("push_config", {}).get("QUARK_SIGN_NOTIFY") == False
                        or os.environ.get("QUARK_SIGN_NOTIFY") == "false"
                ):
                    logging.info(message)
                else:
                    message = message.replace("今日", f"[{account.nickname}]今日")
                    add_notify(message)
            else:
                logging.info(f"📅 签到异常: {sign_return}")
    logging.info('')


def do_save(account, tasklist=[]):
    emby = Emby(
        CONFIG_DATA.get("emby", {}).get("url", ""),
        CONFIG_DATA.get("emby", {}).get("apikey", ""),
    )
    logging.info(f"转存账号: {account.nickname}")
    # 获取全部保存目录fid
    account.update_savepath_fid(tasklist)

    def check_date(task):
        return (
                not task.get("enddate")
                or (
                        datetime.now().date()
                        <= datetime.strptime(task["enddate"], "%Y-%m-%d").date()
                )
        ) and (
                not task.get("runweek")
                # 星期一为0，星期日为6
                or (datetime.today().weekday() + 1 in task.get("runweek"))
        )

    # 执行任务
    for index, task in enumerate(tasklist):
        # 判断任务期限
        if check_date(task):
            logging.info('')
            logging.info(f"#{index + 1}------------------")
            logging.info(f"任务名称: {task['taskname']}")
            logging.info(f"分享链接: {task['shareurl']}")
            logging.info(f"目标目录: {task['savepath']}")
            logging.info(f"正则匹配: {task['pattern']}")
            logging.info(f"正则替换: {task['replace']}")
            if task.get("enddate"):
                logging.info(f"任务截止: {task['enddate']}")
            if task.get("emby_id"):
                logging.info(f"刷媒体库: {task['emby_id']}")
            if task.get("ignore_extension"):
                logging.info(f"忽略后缀: {task['ignore_extension']}")
            if task.get("update_subdir"):
                logging.info(f"更子目录: {task['update_subdir']}")
            logging.info('')
            is_new = account.do_save_task(task)
            is_rename = account.do_rename_task(task)
            # 刷新alist
            if is_new or is_rename:
                update_alist(task)
                time.sleep(5)

            # 刷新媒体库
            if emby.is_active and (is_new or is_rename) and task.get("emby_id") != "0":
                if task.get("emby_id"):
                    emby.refresh(task["emby_id"])
                else:
                    match_emby_id = emby.search(task["taskname"])
                    if match_emby_id:
                        task["emby_id"] = match_emby_id
                        emby.refresh(match_emby_id)

    logging.info('')


def main():
    global CONFIG_DATA
    start_time = datetime.now()
    logging.info(f"===============程序开始===============")
    logging.info(f"⏰ 执行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info('')
    # 读取启动参数
    config_path = sys.argv[1] if len(sys.argv) > 1 else "quark_config.json"
    task_index = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else ""
    # 检查本地文件是否存在，如果不存在就下载
    if not os.path.exists(config_path):
        if os.environ.get("QUARK_COOKIE"):
            logging.info(
                f"⚙️ 读取到 QUARK_COOKIE 环境变量，仅签到领空间。如需执行转存，请删除该环境变量后配置 {config_path} 文件"
            )
            cookie_val = os.environ.get("QUARK_COOKIE")
            cookie_form_file = False
        else:
            logging.info(f"⚙️ 配置文件 {config_path} 不存在❌，正远程从下载配置模版")
            config_url = f"{GH_PROXY}https://raw.githubusercontent.com/Cp0204/quark_auto_save/main/quark_config.json"
            if download_file(config_url, config_path):
                logging.info("⚙️ 配置模版下载成功✅，请到程序目录中手动配置")
            return
    else:
        logging.info(f"⚙️ 正从 {config_path} 文件中读取配置")
        with open(config_path, "r", encoding="utf-8") as file:
            CONFIG_DATA = json.load(file)
        cookie_val = CONFIG_DATA.get("cookie")
        if not CONFIG_DATA.get("magic_regex"):
            CONFIG_DATA["magic_regex"] = MAGIC_REGEX
        cookie_form_file = True
    # 获取cookie
    cookies = get_cookies(cookie_val)
    if not cookies:
        logging.info("❌ cookie 未配置")
        return
    accounts = [Quark(cookie, index) for index, cookie in enumerate(cookies)]
    # 签到
    logging.info(f"===============签到任务===============")
    if type(task_index) is int:
        verify_account(accounts[0])
    else:
        for account in accounts:
            verify_account(account)
            do_sign(account)
    logging.info('')
    # 转存
    if accounts[0].is_active and cookie_form_file:
        logging.info(f"===============转存任务===============")
        # 任务列表
        tasklist = CONFIG_DATA.get("tasklist", [])
        if type(task_index) is int:
            do_save(accounts[0], [tasklist[task_index]])
        else:
            do_save(accounts[0], tasklist)
        logging.info('')
    # 通知
    if NOTIFYS:
        notify_body = "\n".join(NOTIFYS)
        logging.info(f"===============推送通知===============")
        send_ql_notify("【夸克自动追更】", notify_body)
        logging.info('')
    if cookie_form_file:
        # 更新配置
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(CONFIG_DATA, file, ensure_ascii=False, indent=2)

    logging.info(f"===============程序结束===============")
    duration = datetime.now() - start_time
    logging.info(f"😃 运行时长: {round(duration.total_seconds(), 2)}s")
    logging.info('')


if __name__ == "__main__":
    main()
