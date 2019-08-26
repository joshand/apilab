import re
from meraki import meraki
from webexteamssdk import WebexTeamsAPI
import os
import time
import requests
import json
import splunklib.results as results
import splunklib
from datetime import datetime
from datetime import timedelta
import base64
from statistics import mean
from flask import Flask, request, jsonify, Response
from collections import namedtuple

app = Flask(__name__)

# ======================================================================================================================

# Change these variables to match your Pod
pod_number = 0      # Replace this with your pod #
teams_token = "Token of Your Webex Teams Bot"
merakiapikey = "Your Meraki Dashboard Token"
devdict = {"mx": "mx_serial", "ms": "ms_serial", "mr": "mr_serial"}     # Devices from your Pod
myurl = "https://ngrok-url"

# ======================================================================================================================

# These shouldn't be changed
merakiorgnum = "578149602163688267"
merakiadmindefaultnetwork = "dCloud"
networkname = "API Lab Pod " + str(pod_number)
networktype = "appliance switch wireless"
nettemplate = "L_578149602163708318"
adminuser = "user+" + str(pod_number) + "@ciscodcloudpov.com"
samladdon = "API Lab HQ"
target_role = "SAML_API_Pod_" + str(pod_number)
org_acc = "none"
cam_list = ["Q2GV-JKBK-8V5T", "Q2JV-DMKZ-M692"]
cam_net_id = "L_578149602163708548"

api = WebexTeamsAPI(access_token=teams_token)


def arg_parser(arg_string, base_arg_name, expected_arg_count):
    m_arr = re.split(base_arg_name, arg_string, flags=re.IGNORECASE)
    m2_arr = m_arr[1].strip().split(" ")
    # print(arg_string, base_arg_name, expected_arg_count, m_arr, m2_arr)
    if len(m2_arr) < expected_arg_count:
        return [""] * expected_arg_count + [False, "Syntax Error; Expected " + str(
            expected_arg_count) + " arguments, received " + str(len(m2_arr)) + "."]
    elif m2_arr[expected_arg_count - 1] == "":
        return [""] * expected_arg_count + [False, "Syntax Error; Expected " + str(
            expected_arg_count) + " arguments, received " + str(len(m2_arr)) + "."]
    else:
        if len(m2_arr) > expected_arg_count:
            m2_out = []
            for x in range(0, expected_arg_count):
                if x + 1 == expected_arg_count:
                    m2_out.append(' '.join(m2_arr[x:]).strip())
                else:
                    m2_out.append(m2_arr[x])
            return m2_out + [True, ""]
        else:
            return m2_arr + [True, ""]


def get_message(event):
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': 'Bearer ' + teams_token
    }

    url = "https://api.ciscospark.com/v1/messages/" + event["data"]["id"]
    response = requests.get(url, headers=headers)
    if response.status_code == requests.codes.ok:
        # return response.json()['text']
        return response.content
    else:
        print(response.status_code, response.content.decode("utf-8"))


# Get chatbot's own ID
def get_chatbot_id(webhook_event):
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': 'Bearer ' + teams_token
    }

    response = requests.get('https://api.ciscospark.com/v1/people/me', headers=headers)
    return response.json()['id']


# List direct rooms (https://developer.webex.com/docs/api/v1/rooms/list-rooms)
def list_rooms():
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': 'Bearer ' + teams_token
    }

    url = 'https://api.ciscospark.com/v1/rooms?type=direct'
    response = requests.get(url, headers=headers)
    return response.json()['items']


# List messages for room (https://developer.webex.com/docs/api/v1/messages/list-messages)
def list_messages(rid):
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': 'Bearer ' + teams_token
    }

    url = 'https://api.ciscospark.com/v1/messages?roomId=' + rid
    response = requests.get(url, headers=headers)
    return response.json()['items']


# Get user's info
def get_user(uid):
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': 'Bearer ' + teams_token
    }
    url = 'https://api.ciscospark.com/v1/people/' + uid
    response = requests.get(url, headers=headers)
    return response.json()


# Get user's emails
def get_emails(user_id):
    data = get_user(user_id)
    return data['emails']


# Function to check whether message begins with one of multiple possible options
def message_begins(text, options):
    message = text.strip().lower()
    for option in options:
        if message.startswith(option):
            return True
    return False


# Function to check whether message contains one of multiple possible options
def message_contains(text, options):
    message = text.strip().lower()
    for option in options:
        if option in message:
            return True
    return False


def get_splunk_info(serial_number):
    max_days = 1
    # Run a one-shot search and display the results using the results reader
    import splunklib.client as client
    service = client.connect(username="admin", password="L@B@dm1n", host="splunk.ciscodemos.co", port="8089")

    # Set the parameters for the search:
    # - Search everything in a 24-hour time range starting June 19, 12:00pm
    # - Display the first 10 results
    d = datetime.utcnow()
    end_date = d.isoformat() + "+00:00"
    start_date = str((d - timedelta(days=max_days)).isoformat()) + "+00:00"
    print(start_date, end_date)

    kwargs_oneshot = {"earliest_time": start_date,
                      "latest_time": end_date,
                      "max_count": 25}
    # searchquery_oneshot = "search * | head 10"
    searchquery_oneshot = "search " + serial_number + " | head 20"

    oneshotsearch_results = service.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)

    # Get the results and display them using the ResultsReader
    reader = results.ResultsReader(oneshotsearch_results)
    items = []
    for item in reader:
        listparms = item["_raw"].split("msg=")
        etime = item["_raw"].split("name=")[0].strip()
        try:
            jmsg = {"time": etime, "raw": json.loads(listparms[1])}
            items.append(jmsg)
        except:
            pass

    print(items)
    f_counts = None
    f_objects = None
    f_lux = None
    for i in items:
        if not f_counts and "counts" in i["raw"]:
            f_counts = i["raw"]["counts"]["person"]
        if not f_objects and "objects" in i["raw"]:
            f_objects = i["raw"]["objects"]
        if not f_lux and "lux" in i["raw"]:
            f_lux = i["raw"]["lux"]

    return [f_counts, f_objects, f_lux]


def get_camera_uplink(apikey, net_id, cam_sn, time=None):
    headers = {"X-Cisco-Meraki-API-Key": apikey}
    if time:
        url = "https://api.meraki.com/api/v0/networks/" + net_id + "/cameras/" + cam_sn + "/videoLink?timestamp=" + time
    else:
        url = "https://api.meraki.com/api/v0/networks/" + net_id + "/cameras/" + cam_sn + "/videoLink"

    response = requests.get(url, headers=headers)
    return response


def get_camera_screenshot(apikey, net_id, cam_sn, time=None):
    headers = {"X-Cisco-Meraki-API-Key": apikey, "Content-Type": "application/json"}
    url = "https://api.meraki.com/api/v0/networks/" + net_id + "/cameras/" + cam_sn.strip() + "/snapshot"
    if time:
        data = json.dumps({'timestamp': time})
        response = requests.post(url, headers=headers, data=data)
    else:
        response = requests.post(url, headers=headers)
    print(url, response.status_code)

    return response


# Call GET: https://api.meraki.com/api_docs#list-the-organizations-that-the-user-has-privileges-on
def get_organizations(api_key):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get("https://api.meraki.com/api/v0/organizations", headers=headers)
    return response.json()


# Call GET: https://api.meraki.com/api_docs#list-the-status-of-every-meraki-device-in-the-organization
def get_device_statuses(api_key, org_id):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get("https://api.meraki.com/api/v0/organizations/" + org_id + "/deviceStatuses",
                            headers=headers)

    # Filter out orgs that do not have dashboard API access enabled, on the Organization > Settings page
    if response.ok:
        return response.json()
    else:
        return None


# Call GET: https://api.meraki.com/api_docs
def get_api_history(api_key, org_id):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get("https://api.meraki.com/api/v0/organizations/" + org_id + "/apiRequests", headers=headers)
    # print(response.status_code, response.content)

    # Filter out orgs that do not have dashboard API access enabled, on the Organization > Settings page
    if response.ok:
        return response.json()
    else:
        return None


# Call GET to new feature: /organizations/{{organizationId}}/uplinksLossAndLatency
def get_orgs_uplinks(api_key, org_id):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get("https://api.meraki.com/api/v0/organizations/" + org_id + "/uplinksLossAndLatency",
                            headers=headers)

    # Filter out orgs that do not have dashboard API access or the NFO enabled
    if response.ok:
        return response.json()
    else:
        return None


# Return device status for each org
def api_history(api_key, rid):
    orgs = get_organizations(api_key)
    responded = False

    for org in orgs:

        # Skip Meraki corporate for admin users
        if org['id'] == 1:
            continue

        # Org-wide device statuses
        # print(org['id'])
        history = get_api_history(api_key, org['id'])
        if history:
            message = "### **" + org["name"] + "**"
            message += "  \n```" + json.dumps(history[-1], indent=2, sort_keys=True) + ""[
                                                                                       :-1]  # screwy Teams formatting
            # post_message(session, headers, payload, message)
            api.messages.create(roomId=rid, html=message)
            responded = True

    if not responded:
        # post_message(session, headers, payload,
        #              'Does your API key have access to at least a single org with API enabled? 😫')
        api.messages.create(roomId=rid,
                            html='Does your API key have access to at least a single org with API enabled? 😫')


# Return device status for each org
def device_status():
    msg = ""
    orgs = get_organizations(merakiapikey)
    responded = False

    for org in orgs:
        # Skip Meraki corporate for admin users
        if org['id'] == 1:
            continue

        # Org-wide device statuses
        statuses = get_device_statuses(merakiapikey, org['id'])
        if statuses:

            # Tally devices across org
            total = len(statuses)
            online_devices = [device for device in statuses if device['status'] == 'online']
            online = len(online_devices)
            alerting_devices = [device for device in statuses if device['status'] == 'alerting']
            alerting = len(alerting_devices)
            offline_devices = [device for device in statuses if device['status'] == 'offline']
            offline = len(offline_devices)

            # Format message, displaying devices names if <= 10 per section
            message = "<b>" + org["name"] + "</b><br>"
            if online > 0:
                message += "<li>" + str(online) + " devices ✅ online (" + str(
                    round(online / total * 100, 1)) + "%)</li>"
                if online <= 10:
                    message += ': '
                    for device in online_devices:
                        if device['name']:
                            message += device["name"] + ", "
                        else:
                            message += device["mac"] + ", "
                    message = message[:-2]

            if alerting > 0:
                message += "<li>" + str(alerting) + " ⚠️ alerting_ (" + str(
                    round(alerting / total * 100, 1)) + "%)</li>"
                if alerting <= 10:
                    message += ': '
                    for device in alerting_devices:
                        if device['name']:
                            message += device["name"] + ", "
                        else:
                            message += device["mac"] + ", "
                    message = message[:-2]

            if offline > 0:
                message += "<li><b>" + str(offline) + " ❌ offline</b> (" + str(
                    round(offline / total * 100, 1)) + "%)</li>"
                if offline <= 10:
                    message += ': '
                    for device in offline_devices:
                        if device['name']:
                            message += device["name"] + ", "
                        else:
                            message += device["mac"] + ", "
                    message = message[:-2]

            # post_message(session, headers, payload, message)
            # api.messages.create(roomId=rid, markdown=message)
            msg += message
            responded = True

            # Show cellular failover information, if applicable
            cellular_online = [device for device in statuses if
                               'usingCellularFailover' in device and device['status'] == 'online']
            cellular = len(cellular_online)
            if cellular > 0:
                failover_online = [device for device in cellular_online if device['usingCellularFailover'] == True]
                failover = len(failover_online)

                if failover > 0:
                    msg += "> {failover} of {cellular} appliances online (" + str(
                        round(failover / cellular * 100, 1)) + "%) using 🗼 cellular failover"
                    # post_message(session, headers, payload,
                    #              f'> {failover} of {cellular} appliances online ({failover / cellular * 100:.1f}%) using 🗼 cellular failover')
                    # api.messages.create(roomId=rid, markdown="> {failover} of {cellular} appliances online (" + str(round(failover / cellular * 100, 1)) + "%) using 🗼 cellular failover")
                    return msg

        # Org-wide uplink performance
        uplinks = get_orgs_uplinks(merakiapikey, org['id'])
        if uplinks:

            # Tally up uplinks with worse performance than thresholds here
            loss_threshold = 7.0
            latency_threshold = 240.0
            loss_count = 0
            latency_count = 0

            for uplink in uplinks:
                perf = uplink['timeSeries']

                loss = mean([sample['lossPercent'] for sample in perf])
                if loss > loss_threshold and loss < 100.0:  # ignore probes to unreachable IPs that are incorrectly configured
                    loss_count += 1

                latency = mean([sample['latencyMs'] for sample in perf])
                if latency > latency_threshold:
                    latency_count += 1

            if loss_count > 0:
                msg += str(loss_count) + " device-uplink-probes currently have 🕳 packet loss higher than **" + str(
                    loss_threshold) + "%**!"
                # post_message(session, headers, payload,
                #              f'{loss_count} device-uplink-probes currently have 🕳 packet loss higher than **{loss_threshold:.1f}%**!')
                # api.messages.create(roomId=rid, html=str(loss_count) + " device-uplink-probes currently have 🕳 packet loss higher than **" + str(loss_threshold) + "%**!")
            if latency_count > 0:
                msg += str(latency_count) + " device-uplink-probes currently have 🐢 latency higher than **" + str(
                    latency_threshold) + " ms**!"
                # post_message(session, headers, payload,
                #              f'{latency_count} device-uplink-probes currently have 🐢 latency higher than **{latency_threshold:.1f} ms**!')
                # api.messages.create(roomId=rid, html=str(latency_count) + " device-uplink-probes currently have 🐢 latency higher than **" + str(latency_threshold) + " ms**!")
        msg += "<br>"

    if not responded:
        msg += 'Does your API key have access to at least a single org with API enabled? 😫'
        # post_message(session, headers, payload,
        #              'Does your API key have access to at least a single org with API enabled? 😫')
        # api.messages.create(roomId=rid, html='Does your API key have access to at least a single org with API enabled? 😫')

    return msg


def do_get_network_by_name(networkname):
    """
    This function searches the list of networks in Dashboard and returns the ID of one with a matching name
    networkname
    :return: string
    """
    if networkname == "":
        return ""

    net_info = meraki.getnetworklist(merakiapikey, merakiorgnum, suppressprint=True)
    for n in net_info:
        if n["name"] == networkname:
            return n["id"]
    return ""


def get_admin_id(un):
    org_admin = meraki.getorgadmins(merakiapikey, merakiorgnum, suppressprint=True)
    for a in org_admin:
        if un == a["email"]:
            return a["id"]

    else:
        return False


# Call GET: api_docs#list-the-http-servers-for-a-network
def get_api_http_servers(api_key, net_id):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get("https://api.meraki.com/api/v0/networks/" + net_id + "/httpServers", headers=headers)

    if response.ok:
        return response.json()
    else:
        return None


def add_api_http_servers(api_key, net_id, wh_name, wh_url):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    data = {"name": wh_name, "url": wh_url}
    response = requests.post("https://api.meraki.com/api/v0/networks/" + net_id + "/httpServers", data=data,
                             headers=headers)

    if response.ok:
        return response.json()
    else:
        return None


def get_alert_settings(api_key, net_id):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.get("https://api.meraki.com/api/v0/networks/" + net_id + "/alertSettings", headers=headers)
    if response.ok:
        return response.json()
    else:
        return None


def update_alert_settings(api_key, net_id, wh_id):
    cur_alert = get_alert_settings(api_key, net_id)
    servers = cur_alert["defaultDestinations"]["httpServerIds"]
    servers.append(wh_id)

    headers = {'X-Cisco-Meraki-API-Key': api_key, 'content-type': 'application/json'}
    data = {
        "defaultDestinations": {
            "emails": [],
            "snmp": False,
            "allAdmins": False,
            "httpServerIds": servers
        }
    }
    url = "https://api.meraki.com/api/v0/networks/" + net_id + "/alertSettings"
    print(url, data, headers)
    response = requests.put(url, json=data, headers=headers)
    print(response.content.decode("utf-8"))

    if response.ok:
        return response.json()
    else:
        return None


def del_api_http_servers(api_key, net_id, wh_id):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    response = requests.delete("https://api.meraki.com/api/v0/networks/" + net_id + "/httpServers/" + wh_id,
                               headers=headers)

    if response.ok:
        return response
    else:
        return None


def test_api_http_servers(api_key, net_id, wh_url):
    headers = {'X-Cisco-Meraki-API-Key': api_key}
    data = {"url": wh_url}
    response = requests.post("https://api.meraki.com/api/v0/networks/" + net_id + "/httpServers/webhookTests",
                             data=data, headers=headers)

    if response.ok:
        return response.json()
    else:
        return None


def pod_webhook(d, m_func):
    [opt, arg_state, arg_msg] = arg_parser(m_func, "webhooks", 1)
    if not arg_state:
        return arg_msg

    msg = ""
    print("pod_webhook", opt)
    netid = d["role"]
    webhooks = get_api_http_servers(merakiapikey, netid)

    if opt.strip() == "show" or opt.strip() == "list":
        if webhooks:
            for webhook in webhooks:
                if webhook["name"] != "Splunk":
                    return "Current Webhook: " + webhook["url"]

        return "Pod Webhook Not Found"
    elif opt.strip().find("add") >= 0:
        url = opt.split("add ")[1]
        whfound = False
        if webhooks:
            for webhook in webhooks:
                if webhook["name"] != "Splunk":
                    whfound = True
                    break

        if whfound:
            return "This bot can only allow a single Webhook in your Network. Please delete the existing one before adding a new one."
        else:
            if url.strip() == "":
                return "You must specify the URL for the Webhook"
            else:
                r = add_api_http_servers(merakiapikey, netid, "Pod Webhook", url)
                whid = r["id"]
                e = update_alert_settings(merakiapikey, netid, whid)
                if r:
                    return "Webhook Created"

        return "Unable to Add Webhook"
    elif opt.strip() == "del" or opt.strip() == "delete":
        whid = None
        if webhooks:
            for webhook in webhooks:
                if webhook["name"] == "Pod Webhook":
                    whid = webhook["id"]
                    break

        if whid:
            # client.http_servers.delete_network_http_server({"network_id": netid, "delete_network_http_server": {"id": whid}})
            del_api_http_servers(merakiapikey, netid, whid)
            return "Webhook Deleted"
        else:
            return "There is no Webhook to Delete. Please add one first."
    elif opt.strip() == "test":
        whurl = None
        if webhooks:
            for webhook in webhooks:
                if webhook["name"] == "Pod Webhook":
                    whurl = webhook["url"]
                    break

        if whurl:
            test_api_http_servers(merakiapikey, netid, whurl)
            return "Webhook Test Requested"
        else:
            return "There is no Webhook to Test. Please add one first."
    else:
        return "Unknown Webhook Operation"


def pod_status(d):
    ret = ""
    netinfo = meraki.getnetworkdetail(merakiapikey, d["role"], suppressprint=True)
    if netinfo:
        networkname = netinfo["name"]
        netid = d["role"]
        ret += "Network Name: " + networkname + "\nNetwork ID: " + netid + "\n"

        orgdevinv = meraki.getorginventory(merakiapikey, merakiorgnum, suppressprint=True)
        devlist = []
        for d in devdict:
            devlist.append(devdict[d])
        for d in orgdevinv:
            if d["serial"] in devlist:
                if d["networkId"] == netid:
                    ret += "<li>" + d["serial"] + " - Present In Network\n"
                else:
                    ret += "<li>" + d["serial"] + " - Missing From Network\n"

        return ret
    else:
        return "This Network Does Not Exist\n" + str(d)


def pod_health(d):
    return device_status()


def cam_inspect(rid):
    for c in cam_list:
        [f_counts, f_objects, f_lux] = get_splunk_info(c)
        # print(c, f_counts, f_objects, f_lux)
        msg = "<br><b>Number of People Detected</b>: " + str(f_counts) + "<br><b>Current Lux</b>: " + str(f_lux)
        return_snapshots(cam_net_id, rid, msg, c)


# Send a message in Webex Teams
def post_message(payload, message):
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': 'Bearer ' + teams_token
    }

    payload['markdown'] = message
    r = requests.post('https://api.ciscospark.com/v1/messages/',
                      headers=headers,
                      data=json.dumps(payload))
    return r.content.decode("UTF-8")


# Send a message with file attachment in Webex Teams
def post_file(payload, message, file_url):
    payload['file'] = file_url
    post_message(payload, message)


def return_snapshots(net_id, rid, msg, filters):
    api.messages.create(roomId=rid, html='📷 <i>Retrieving camera snapshots...</i>')
    snapshots = meraki_snapshots(net_id, None, filters)

    # Wait a bit to ensure cameras to upload snapshots to links
    time.sleep(9)

    # Send cameras names with files (URLs)
    for (name, snapshot, video) in snapshots:
        # api.messages.create(rid, html="<a href='" + video + "'>" + name + "</a>" + msg, urls=[snapshot])
        payload = {"roomId": rid}
        post_file(payload, "<a href='" + video + "'>" + name + "</a>" + msg, snapshot)


def meraki_snapshots(net_id, time=None, filters=None):
    # Get devices of network and filter for MV cameras
    devices = meraki.getnetworkdevices(merakiapikey, net_id, suppressprint=True)
    if devices:
        cameras = [device for device in devices if device['model'][:2] == 'MV']

        # Assemble return data
        snapshots = []
        for camera in cameras:
            # Remove any cameras not matching filtered names
            serial = camera['serial']
            name = camera['name'] if 'name' in camera else camera['mac']
            if filters and filters.lower() != serial.lower():
                continue

            # Get video link
            response = get_camera_uplink(merakiapikey, net_id, camera["serial"], time)
            video_link = response.json()['url']

            # Get snapshot link
            response = get_camera_screenshot(merakiapikey, net_id, camera["serial"], time)
            # print(serial, response.content.decode("utf-8"))

            # Possibly no snapshot if camera offline, photo not retrievable, etc.
            if response.ok:
                snapshots.append((name, response.json()['url'], video_link))

        return snapshots
    else:
        return []


def clear_screen():
    return '''```
                            7II                                     III                             
                           ~III                                     III,                            
                           :III                                     III,                            
                           :III                                     III,                            
                  ,+       :III        =                   +        III,       =,                   
                 ~III      :III      ,III                 III,      III,      III~                  
                 ~III      :III      :III                 III,      III,      III~                  
                 ~III      :III      :III                 III,      III,      III~                  
       ~III      ~III      :III      :III       ?II       III,      III,      III~      III~        
       ~III      ~III      :III      :III       III       III,      III,      III~      III+        
       ~III      ~III      :III      :III       III       III,      III,      III~      III+        
       ~III      ~III      :III       I?I       III       III       III,      III:      III~        
                           :III                                     III,                            
                           :III                                     III,                            
                            ?I~                                     ~I?                             


                  IIIIIIII     IIII      IIIIIIII       ,IIIIIII?      ,IIIIIIII?                   
                +IIIIIIIII     IIII     IIIIIIIII      IIIIIIIII?     IIIIIIIIIIII~                 
               :IIII:          IIII     IIII          IIII7          IIIII    :IIII,                
               7III            IIII     IIII?I=      ,IIII           IIII       IIII                
               IIII            IIII      ?IIIIII7    ~III~          ~III~       IIII                
               IIII            IIII         ,IIIII    IIII           IIII      ,IIII                
               ,IIII=          IIII           ?III    7IIII     :    ?IIII    =?III                 
                :IIIIIIIII     IIII     IIIIIIIII:     7IIIIIIII?     IIIIIIIIIIII,                 
                  ~IIIIIII     IIII     IIIIIIII         IIIIIII?       IIIIIIII~                   



     :77$               777                                                 ?7             ,$?      
     :7:$,             77$7                                                 ?7                      
     :7 77            ,7~77                                                 ?7                      
     :7  $I           77 77         +77I,             +77,      I77I        ?7                      
     :7  +7          ~$  77      7$7    +77      :7 77+  :   I7+    I$7     ?7      +$7     7,      
     :7   77         7I  77     77        7$     :77=       77        77    ?7    ,77       7,      
     :7    $?       77   77    7$          77    :77                  7$    ?7   77         7,      
     :7    I$       $:   77    $+          ,7,   :$,                  I7    ?7 77           7,      
     :7     77     77    77   ,7777777777777$+   :7           :777777?77    ?777:           7,      
     :7     ,$:   :$     77    7,                :7         77I       77    ?7 ,77          7,      
     :7      77   $I     77    7I                :7        I7         I$    ?7   7$?        7,      
     :7       77 I$      77    I7          7$    :7        77         77    ?7     $7,      7,      
     :7       :7,$,      77     I$~       7$     :7        =7=       7=7    ?7      :$7     7,      
     :7        777       77       777I?I777      :$         =$77?I7$7  $    ?$        77=   7,      
    '''


def setup_teams_webhook(name, targeturl, wh_resource="messages", wh_event="created"):
    # Get a list of current webhooks
    webhooks = api.webhooks.list()

    # Look for an Existing Webhook with this name, if found update it
    wh = None
    # webhooks is a generator
    for h in webhooks:
        if h.name == name:
            print("Found existing webhook.  Updating it.")
            wh = h

    # No existing webhook found, create new one
    # we reached the end of the generator w/o finding a matching webhook
    if wh is None:
        print("Creating new webhook.")
        wh = api.webhooks.create(
            name=name,
            targetUrl=targeturl,
            resource=wh_resource,
            event=wh_event,
        )

    # if we have an existing webhook, delete and recreate
    #   (can't update resource/event)
    else:
        # Need try block because if there are NO webhooks it throws error
        try:
            wh = api.webhooks.delete(webhookId=wh.id)
            wh = api.webhooks.create(
                name=name, targetUrl=targeturl,
                resource=wh_resource, event=wh_event
            )
        # https://github.com/CiscoDevNet/ciscoteamsapi/blob/master/ciscoteamsapi/api/webhooks.py#L237
        except Exception as e:
            msg = "Encountered an error updating webhook: {}"
            print(msg.format(e))

    return wh


def get_tag_data():
    """
    This function issues the API call to Dashboard to get the tracking tags (SAML Roles)
    :return: dictionary
    """
    saml_data = meraki.getsamlroles(merakiapikey, merakiorgnum, suppressprint=True)
    return saml_data


def parse_tag_data(tag_data, tag_search, tag_role):
    """
    This function parses the tracking tags (SAML Roles) to retrieve specific state values
    tag_data
    tag_search
    tag_role
    :return: string
    """
    for tgd in tag_data:
        if tgd["role"] == tag_role:
            if "tags" in tgd:
                for t in tgd["tags"]:
                    if t["tag"][0:len(tag_search) + 1] == tag_search + ":":
                        return t["tag"][len(tag_search) + 1:]
            else:
                return ""

    return ""


def get_pod_assigned(td, incoming_msg):
    admin_email = incoming_msg.personEmail

    rval = None
    for rolelist in td:
        if "tags" in rolelist:
            for t in rolelist["tags"]:
                tl = t["tag"].split(":")
                if tl[0] == "admin":
                    s = tl[1] + ('=' * (-len(tl[1]) % 4))
                    s_eml = base64.b64decode(s.encode("utf-8")).decode("utf-8")

                    print(admin_email, s_eml)
                    if admin_email == s_eml:
                        rval = rolelist

                if rval:
                    break

        if rval:
            break

    return rval


def webhook():
    try:
        webhook_event = json.loads(request.data.decode("UTF-8"))
    except:
        return ""
    netid = webhook_event["networkId"]
    rid = parse_tag_data(get_tag_data(), "roomId", netid)
    photo = None

    # Parse event data
    alert = webhook_event['alertType']
    data = webhook_event['alertData']
    name = data['name'] if 'name' in data else ''
    network = webhook_event['networkName']
    network = network.replace('@', '')  # @ sign messes up markdown
    network_link = webhook_event['networkUrl']
    device = webhook_event['deviceName'] if 'deviceName' in webhook_event else ''
    if device:
        device_link = webhook_event['deviceUrl']
    else:
        device_link = "https://dashboard.meraki.com"

    # Compose and format message to user
    payload = {'roomId': rid}
    message = "**" + alert + "**"

    # Add snapshot if motion detected
    if alert == 'Motion detected':
        timestamp = datetime.fromtimestamp(int(data['timestamp'])).isoformat() + 'Z'
        print("info=", merakiapikey, webhook_event['networkId'], timestamp, device)
        snapshots = meraki_snapshots(webhook_event['networkId'], time=None, filters=device)
        if snapshots:
            (name, photo, video) = snapshots[0]
            message += " - [" + network + "](" + network_link + ")"
            message += ": _[" + device + "](" + video + ")_"
        else:
            message = ''  # no snapshot
    else:
        if name:
            message += " - _" + name + "_"
        message += ": [" + network + "](" + network_link + ")"
        if device:
            message += " - _[" + device + "](" + device_link + ")_"

    # Wait a bit, for camera to upload snapshot to link
    if alert == 'Motion detected' and message != '':
        print("motion detected")
        time.sleep(5)
        post_file(payload, message, photo)

    # Add more alert information and format JSON
    elif data:
        print("data is present")
        message += "  \n```" + json.dumps(data, indent=2, sort_keys=True) + ""[:-1]  # screwy Webex Teams formatting
        post_message(payload, "**_Webhook Received:_**<br>" + message)

    # Send the webhook without alert data
    elif message != '':
        print("message not blank", payload, message)
        post_message(payload, "**_Webhook Received:_**<br>" + message)

    else:
        print("no message to return")

    # Let Meraki know success
    return ""


def exec_main(incoming_msg):
    td = get_tag_data()
    p = get_pod_assigned(td, incoming_msg)
    keyword = "apilab"

    if p:
        m_func = re.split(keyword, incoming_msg.text, flags=re.IGNORECASE)[1].strip()
        if m_func.lower() == "help":
            message = ""
            for c in [["help", "Get help for this bot."],
                      ["clear", "Clear the screen."],
                      ["status", "Get the Status of your lab Pod."],
                      ["health", "Get the Health of the Meraki Lab Network."],
                      ["webhooks",
                       "Webhook Operations: <b>webhook &lt;cmd&gt;</b>, where &lt;cmd&gt; is '<i>show</i>' to Show Webhook Information, '<i>add</i>' to Add a Webhook, '<i>del</i>' to Delete a Webhook or '<i>test</i>' to Test a Webhook."],
                      ["inspect", "Get Camera status from Camera test network."]]:
                cname = keyword + " " + c[0]
                message += "* **%s**: %s \n" % (cname, c[1])
            return message
        elif m_func.lower() == "clear":
            print(incoming_msg)
            return clear_screen()
        elif m_func.lower() == "status":
            return pod_status(p)
        elif m_func.lower() == "health":
            return pod_health(p)
        elif m_func.lower().find("webhooks") >= 0:
            return pod_webhook(p, m_func)
        elif m_func.lower().find("webhook") >= 0:
            return pod_webhook(p, m_func.replace("webhook", "webhooks"))
        elif m_func.lower() == "inspect":
            return cam_inspect(incoming_msg.roomId)
        else:
            return "Unknown argument: " + m_func
    else:
        return "No active lab session found for you. You have to reserve a lab before you can interact with me."


def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
def json2obj(data): return json.loads(data, object_hook=_json_object_hook)


@app.route('/', methods=['GET'])
def default():
    return "It's working!"


@app.route('/', methods=['POST'])
def teams_webhook():
    webhook_event = json.loads(request.data.decode("UTF-8"))
    message = json2obj(get_message(webhook_event))
    chatbot_id = get_chatbot_id(webhook_event)
    user_id = webhook_event['actorId']
    sender_emails = get_emails(user_id)
    payload = {'roomId': webhook_event['data']['roomId']}
    if user_id == chatbot_id:
        return ""

    # print(message)
    if message_contains(message.text, "apilab"):
        msg = exec_main(message)
    else:
        msg = ""

    print(msg)
    post_message(payload, msg)
    return ""


@app.route('/meraki', methods=['GET', 'POST'])
def meraki_webhook():
    webhook()


if __name__ == '__main__':
    print("Configuring Webhook.")
    w = setup_teams_webhook("Meraki Lab Reservation", myurl)
    print("Webhook ID: " + w.id)

    app.run()
