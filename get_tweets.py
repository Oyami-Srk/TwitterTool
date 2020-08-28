#!python3
# requirement: selenium brotli browsermobproxy(HEAD from github)
#
# using release version of browsermobproxy cause bug that java
# process won't stop on macos
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from browsermobproxy import Server
import base64
import os
import brotli
import json
import time
import re
import argparse
import traceback

parser = argparse.ArgumentParser(
    description="Use selenium to get tweets json data")

group = parser.add_mutually_exclusive_group()
group.add_argument("-u",
                   "--url",
                   type=str,
                   nargs="+",
                   help="Tweets url to be fetched")
group.add_argument("-i",
                   "--input",
                   type=str,
                   dest="input_file",
                   help="Tweets urls list file")
group.add_argument("-l",
                   "--login",
                   dest="only_login",
                   action="store_true",
                   help="Only do login and save cookie")
group.required = True

parser.add_argument("-o",
                    "--output",
                    default="json",
                    type=str,
                    help="Output json dir")
parser.add_argument("--username", help="Twitter username")
parser.add_argument("--password", help="Twitter password")
parser.add_argument("-C",
                    "--cookie",
                    help="cookie json file",
                    default="cookie.json")
parser.add_argument("--bmp",
                    type=str,
                    metavar="browsermob-proxy",
                    default="./browsermob-proxy-2.1.4/bin/browsermob-proxy",
                    help="Browsermob-Proxy execute path")
parser.add_argument("--chromedriver",
                    type=str,
                    metavar="chromedriver",
                    default="./chromedriver",
                    help="Chrome driver execute path")
parser.add_argument("--headless", action="store_true")
parser.add_argument("--debug", action="store_true")
parser.add_argument("--http_proxy",
                    default="localhost:7890",
                    metavar="HOST:PORT",
                    help="http proxy address")
parser.add_argument("--log", default="tweets.log", help="Logs file")

url_filter = re.compile(r'twitter.com/(.+?)/status/(\d+)')
rux_jsonurl = "https://api.twitter.com/2/rux.json"

no_tweet = "此推文不存在。"
author_restrict = "此账号的所有者对可以查看其推文的用户进行了限制。"


class TweetNotExists(Exception):
    pass


def get_json_url(url: str) -> str:
    json_base_url = "https://api.twitter.com/2/timeline/conversation/%s.json"
    return json_base_url % (url_filter.findall(url)[0][1])


def init_environment(
        headless=False,
        proxy="localhost:7890",
        username="",
        password="",
        cookie_path="",
        bmp_server_path="./browsermob-proxy-2.1.4/bin/browsermob-proxy",
        chrome_driver_path="./chromedriver",
        is_debug=False):
    if is_debug:
        print("Debug mode enabled")
    server = Server(path=bmp_server_path)
    server.start()
    proxy = server.create_proxy({"httpProxy": proxy})
    proxy.blacklist(".*google.*", 404)

    chrome_options = webdriver.ChromeOptions()

    # Configure chrome options
    chrome_options.add_argument("--proxy-server={0}".format(proxy.proxy))
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("no-sandbox")
    chrome_options.add_argument("blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--dns-prefetch-disable")

    if headless:
        chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options,
                              executable_path=chrome_driver_path)
    try:
        if username and password:
            driver.get("https://twitter.com/login")

            username_field = driver.find_element_by_name(
                "session[username_or_email]")
            password_field = driver.find_element_by_name("session[password]")
            username_field.send_keys(username)
            password_field.send_keys(password)

            driver.find_element_by_xpath('//div[@role="button"]').click()

            print("Login succeed")

            if cookie_path:
                cookies = driver.get_cookies()
                with open(cookie_path, "w") as f:
                    json.dump(cookies, f)
        elif cookie_path and os.path.exists(cookie_path):
            print("Loading existing cookie")
            driver.get("https://twitter.com/")

            with open(cookie_path, "r") as f:
                cookies = json.load(f)
            for c in cookies:
                try:
                    driver.add_cookie(c)
                except Exception as e:
                    print("Error add cookie: " + str(e))
                    driver.quit()
                    proxy.close()
                    server.stop()
                    exit()

            driver.implicitly_wait(5)
            driver.get("https://twitter.com/settings/account")
            screen_name = driver.find_element_by_xpath(
                '//a[@href="/settings/screen_name"]/div/div/div[2]/span').text
            print("Login succeed as: " + screen_name)
        else:
            print(
                "Must have cookie or username/password in order to fetch twitter data"
            )
            close_environment({
                "server": server,
                "proxy": proxy,
                "driver": driver
            })
    except Exception as e:
        print("Error at trying login: " + str(e))
        driver.quit()
        proxy.close()
        server.stop()
        exit()

    return {
        "server": server,
        "proxy": proxy,
        "driver": driver,
        "is_debug": is_debug
    }


def close_environment(env):
    env['driver'].quit()
    env['proxy'].close()
    env['server'].stop()


def get_tweet_json(env, url):
    proxy = env['proxy']
    driver = env['driver']

    proxy.new_har('twitter',
                  options={
                      'captureHeaders': True,
                      'captureContent': True,
                      'captureBinaryContent': True
                  })
    try:
        driver.get(url)
    except TimeoutException:
        pass

    if env['is_debug']:
        print("Press Entry for next stage")
        input()

    for i in range(3):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article")))
        except:
            # check wheather retry button showed up
            driver.refresh()
            print(url.strip() + "retry for %d times" % (i))
            continue
        break

    # loaded
    result = proxy.har
    jsonurl = get_json_url(url)
    for entry in result['log']['entries']:
        _url = entry['request']['url']
        if jsonurl in _url or rux_jsonurl in _url:
            _response = entry['response']
            _content = _response['content']
            if _content['size'] == 0:
                continue
            try:
                decoded_text = brotli.decompress(
                    base64.b64decode(_content['text']))
            except:
                decoded_text = _content['text']
            """
            with open("a.json", "w") as f:
                json.dump(json.loads(decoded_text), f,
                          ensure_ascii=False, indent=4)
            """
            # driver.close()
            objs = json.loads(decoded_text)
            if 'globalObjects' in objs.keys():
                if objs['globalObjects']['tweets'] == {}:
                    msg = driver.find_element_by_tag_name('article')
                    if no_tweet in msg.text:
                        raise TweetNotExists()
                    elif author_restrict in msg.text:
                        return None
                    else:
                        continue
            else:
                continue
            return objs
    raise Exception("No entry matched")


if __name__ == "__main__":
    args = parser.parse_args()
    import sys
    if args.url:
        urls = args.url
    elif args.input_file:
        with open(args.input_file, "r") as f:
            urls = f.readlines()
    else:
        urls = []

    try:
        env = init_environment(headless=args.headless,
                               username=args.username,
                               password=args.password,
                               proxy=args.http_proxy,
                               bmp_server_path=args.bmp,
                               cookie_path=args.cookie,
                               chrome_driver_path=args.chromedriver,
                               is_debug=args.debug)
    except Exception as e:
        print("Environment setup failed.")
        print(e)
        traceback.print_exc()
        exit()

    if args.only_login:
        print("Run cleanup process")
        close_environment(env)
        exit()
    jd = args.output
    logfn = args.log

    i = 1
    length = len(urls)

    try:
        fplog = open(logfn, "a")
        for url in urls:
            try:
                obj = get_tweet_json(env, url)
                if obj == None:
                    fplog.writelines(
                        time.strftime("[%Y-%m-%d|%H:%M:%S]") + "[Restrict] " +
                        url.strip() + "\n")
                    print(url.strip() + " restrict!" + f" {i}/{length}")
                else:
                    if not env['is_debug']:
                        with open(
                                jd + "/" + url_filter.findall(url)[0][1] +
                                ".json", "w") as f:
                            json.dump(obj, f, indent=4, ensure_ascii=False)
                        fplog.writelines(
                            time.strftime("[%Y-%m-%d|%H:%M:%S]") + "[Done] " +
                            url.strip() + "\n")
                    print(url.strip() + " done!" + f" {i}/{length}")
            except TweetNotExists as e:
                if not env['is_debug']:
                    fplog.writelines(
                        time.strftime("[%Y-%m-%d|%H:%M:%S]") + "[NotExists] " +
                        url.strip() + "\n")
                print(url.strip() + " not exists!" + f" {i}/{length}")
            except Exception as e:
                if not env['is_debug']:
                    fplog.writelines(
                        time.strftime("[%Y-%m-%d|%H:%M:%S]") + "[Failed] " +
                        url.strip() + "\n")
                else:
                    print("Exception is: %s" % (str(e)))
                    traceback.print_exc()
                print(url.strip() + " failed!" + f" {i}/{length}")
            if i % 100 == 0:
                print('Sleep a while for twitter')
                time.sleep(5)
            time.sleep(1)
            i += 1
    finally:
        print("Run cleanup process")
        fplog.close()
        close_environment(env)
