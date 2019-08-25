from flask import Flask
import time
import config
import requests
import json
from datetime import datetime, timedelta
import webexteamssdk


app = Flask(__name__)

# Get the event (most recent message) that triggered the webhook
def get_message(session, event, headers):
    url = f'https://api.ciscospark.com/v1/messages/{event["data"]["id"]}'
    response = session.get(url, headers=headers)
    return response.json()['text']


# Get user's info
def get_user(session, user_id, headers):
    url = f'https://api.ciscospark.com/v1/people/{user_id}'
    response = session.get(url, headers=headers)
    return response.json()


# Get user's name
def get_name(session, user_id, headers):
    data = get_user(session, user_id, headers)
    if data['displayName']:
        return data['displayName']
    else:
        return f'{data["firstName"]} {data["lastName"]}'


# Get user's emails
def get_emails(session, user_id, headers):
    data = get_user(session, user_id, headers)
    return data['emails']


# Get chatbot's own ID
def get_chatbot_id(session, webhook_event, headers):
    response = session.get('https://api.ciscospark.com/v1/people/me', headers=headers)
    return response.json()['id']


# Send a message in Webex Teams
def post_message(session, headers, payload, message):
    payload['markdown'] = message
    session.post('https://api.ciscospark.com/v1/messages/',
                 headers=headers,
                 data=json.dumps(payload))


# Send a message with file attachment in Webex Teams
def post_file(session, headers, payload, message, file_url):
    payload['file'] = file_url
    post_message(session, headers, payload, message)


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


# Clear your screen and display Miles!
def clear_screen(session, headers, payload):
    post_message(session, headers, payload,
                 '''```
                                   ./(((((((((((((((((/.
                             *(((((((((((((((((((((((((((((
                         .(((((((((((((((((((((((((((((((((((/
                       ((((((((((((((((((((((((((((((((((((((((/
                    ,((((((((((((((((((((((((((((((((((((((((((((
                  .((((((((((((((((((((     ((((((/     ((((((((((,
                 ((((((((((((((((((((((     ((((((/     (((((((((((
               /((((((((((((((((((((((((((((((((((((((((((((((((((((
              ((((((((((((((((((((((((((((((((((((((((((((((((((((((*
             ((((((((((((((((((((((((((((((((((((((((((((((((((((((((
            (((((((((((((((((((((((((((((((((((((((((((((((((((((((((
           ((((((((((((((((((((((((     ((((((((((((((/     (((((((((
          ,((((((((((((((((((((((((     ((((((((((((((/     ((((((((/
          (((((((((((((((((((((((((    .//////////////*    .((((((((
         ,(((((((((((((((((((((((((((((/              ((((((((((((.
         ((((((((((((((((((((((((((((((/              (((((((((((
         (((((((((((((((((((((((((((((((((((((((((((((((((((((((*
        .(((((((((((((((((((((((((((((((((((((((((((((((((((((*
        /((((((((((((((((((((((((((((((((((((((((((((((((((*
        (((((((((((((((((((((((((((((((((((((((((((((((*
        (((((((((((/.                     ....
        (((((((/
        (((((
        (((
        /.
    ''')


# List direct rooms (https://developer.webex.com/docs/api/v1/rooms/list-rooms)
def list_rooms(session, headers):
    url = 'https://api.ciscospark.com/v1/rooms?type=direct'
    response = session.get(url, headers=headers)
    return response.json()['items']


# List messages for room (https://developer.webex.com/docs/api/v1/messages/list-messages)
def list_messages(session, headers, room_id):
    url = f'https://api.ciscospark.com/v1/messages?roomId={room_id}'
    response = session.get(url, headers=headers)
    return response.json()['items']


# Function to prevent duplicating messages if matching snippet for user's email and within lookback time in minutes
def already_duplicated(session, headers, snippet, email, lookback):
    # Get current time
    now = datetime.utcnow()

    # Get list of rooms for chatbot, and then find user's room
    rooms = list_rooms(session, headers)
    for room in rooms:
        user_id = room['creatorId']
        if email in get_emails(session, user_id, headers):
            break

    # Get list of messages in that room
    messages = list_messages(session, headers, room['id'])

    # Filter on messages that match
    match_snippet = [m for m in messages if 'webex.bot' in m['personEmail'] and m['markdown'] == snippet]

    # See if any matched messages are within last lookback minutes
    if match_snippet:
        earlier = now - timedelta(minutes=lookback)
        matches = [m for m in match_snippet if earlier < datetime.strptime(m['created'], '%Y-%m-%dT%H:%M:%S.%fZ')]
        if matches:
            return True
    else:
        return False


@app.route('/', methods=['GET'])
def main_get():
    return "It's working"


@app.route('/', methods=['POST'])
def main():
    # Import user inputs from credentials.ini file, and use bot token to get ID
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization': f'Bearer {config.c["webex"]["token"]}'
    }
    session = requests.Session()

    # Webhook event/metadata received, so now retrieve the actual message for the event
    webhook_event = json.loads(event['body'])
    print(webhook_event)

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

    # Compose and format message to user
    payload = {'toPersonEmail': config.c["meraki"]["email"]}
    message = f'**{alert}**'

    # Add snapshot if motion detected
    if alert == 'Motion detected':
        timestamp = datetime.fromtimestamp(int(data['timestamp'])).isoformat() + 'Z'
        snapshots = meraki_snapshots(session, config.c["meraki"]["camkey"], webhook_event['networkId'], timestamp, device)
        if snapshots:
            (name, photo, video) = snapshots[0]
            message += f' - [{network}]({network_link})'
            message += f': _[{device}]({video})_'
        else:
            message = ''    # no snapshot
    else:
        if name:
            message += f' - _{name}_'
        message += f': [{network}]({network_link})'
        if device:
            message += f' - _[{device}]({device_link})_'

    # Prevent the same message from being sent repeatedly in the lookback timeframe
    if already_duplicated(session, headers, message, config.c["meraki"]["email"], 3):
        message = 'MUTED!! ' + message
        print(message)

    # Wait a bit, for camera to upload snapshot to link
    elif alert == 'Motion detected' and message != '':
        time.sleep(5)
        post_file(session, headers, payload, message, photo)

    # Add more alert information and format JSON
    elif data:
        message += f'  \n```{json.dumps(data, indent=2, sort_keys=True)}'[:-1]  # screwy Webex Teams formatting
        post_message(session, headers, payload, message)

    # Send the webhook without alert data
    elif message != '':
        post_message(session, headers, payload, message)

    # Let Meraki know success
    return {
        'statusCode': 200,
        'body': json.dumps('webhook received')
    }


# For Meraki network, return cameras' snapshots (optionally only for filtered cameras)
def meraki_snapshots(session, api_key, net_id, time=None, filters=None):
    # Get devices of network and filter for MV cameras
    headers = {
        'X-Cisco-Meraki-API-Key': api_key,
        # 'Content-Type': 'application/json'  # issue where this is only needed if timestamp specified
    }
    response = session.get(f'https://api.meraki.com/api/v0/networks/{net_id}/devices', headers=headers)
    devices = response.json()
    cameras = [device for device in devices if device['model'][:2] == 'MV']

    # Assemble return data
    snapshots = []
    for camera in cameras:
        # Remove any cameras not matching filtered names
        name = camera['name'] if 'name' in camera else camera['mac']
        tags = camera['tags'] if 'tags' in camera else ''
        tags = tags.split()
        if filters and name not in filters and not set(filters).intersection(tags):
            continue

        # Get video link
        if time:
            response = session.get(
                f'https://api.meraki.com/api/v0/networks/{net_id}/cameras/{camera["serial"]}/videoLink?timestamp={time}',
                headers=headers)
        else:
            response = session.get(
                f'https://api.meraki.com/api/v0/networks/{net_id}/cameras/{camera["serial"]}/videoLink',
                headers=headers)
        video_link = response.json()['url']

        # Get snapshot link
        if time:
            # Shift actual timestamp requested forward into future by some seconds, to account for beta feature's offset
            # now = datetime.strptime(time, '%Y-%m-%dT%H:%M:%SZ')
            # offset = 15
            # later = now + timedelta(seconds=offset)
            # time = later.isoformat() + 'Z'

            # Original algorithm
            headers['Content-Type'] = 'application/json'
            response = session.post(
                f'https://api.meraki.com/api/v0/networks/{net_id}/cameras/{camera["serial"]}/snapshot',
                headers=headers,
                data=json.dumps({'timestamp': time}))
        else:
            response = session.post(
                f'https://api.meraki.com/api/v0/networks/{net_id}/cameras/{camera["serial"]}/snapshot',
                headers=headers)

        # Possibly no snapshot if camera offline, photo not retrievable, etc.
        if response.ok:
            snapshots.append((name, response.json()['url'], video_link))

    return snapshots


# Determine whether to retrieve all cameras or just selected snapshots
def return_snapshots(session, headers, payload, api_key, net_id, message, cameras):
    try:
        # All cameras
        if message_contains(message, ['all', 'complete', 'entire', 'every', 'full']):
            post_message(session, headers, payload,
                         '📸 _Retrieving all cameras\' snapshots..._')
            snapshots = meraki_snapshots(session, api_key, net_id, None, None)

        # Or just specified/filtered ones
        else:
            post_message(session, headers, payload,
                         '📷 _Retrieving camera snapshots..._')
            snapshots = meraki_snapshots(session, api_key, net_id, None, cameras)

        # Wait a bit to ensure cameras to upload snapshots to links
        time.sleep(9)

        # Send cameras names with files (URLs)
        for (name, snapshot, video) in snapshots:
            post_file(session, headers, payload, f'[{name}]({video})', snapshot)
    except:
        post_message(session, headers, payload,
                     'Does your API key have write access to the specified network ID, with cameras running firmware 3.25 or higher? 😳')


# Disable port's PoE to trigger webhook alert
def disable_port(session, headers, payload, api_key, net_id):
    switch_serial = 'Q2**-****-****'
    response = meraki.getswitchportdetail(api_key, switch_serial, 5)
    if not response['enabled']:
        post_message(session, headers, payload, 'Port already disabled!')
    else:
        response = meraki.updateswitchport(api_key, switch_serial, 5, enabled=False)
        if response['enabled']:
            post_message(session, headers, payload, 'Something went wrong!')
        else:
            post_message(session, headers, payload, 'Disabled your switchport!')


# Enable port's PoE to undo above (and trigger another webhook)
def enable_port(session, headers, payload, api_key, net_id):
    switch_serial = 'Q2**-****-****'
    response = meraki.getswitchportdetail(api_key, switch_serial, 5)
    if response['enabled']:
        post_message(session, headers, payload, 'Port already enabled!')
    else:
        response = meraki.updateswitchport(api_key, switch_serial, 5, enabled=True)
        if response['enabled']:
            post_message(session, headers, payload, 'Enabled your switchport!')
        else:
            post_message(session, headers, payload, 'Something went wrong!')


if __name__ == '__main__':
    app.run()