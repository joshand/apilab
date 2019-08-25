#!/bin/bash

HEADER_CONTENT_TYPE="Content-Type: application/json"
HEADER_ACCEPT="Accept: application/json"
API_KEY="X-Cisco-Meraki-API-Key: 1234567890abcdefghijklmnopqrstuvwxyz1234"
BASE_URL="https://api.meraki.com/api/v0"
COMM_FILE="/tmp/rest.json"
CURL_FILE="/tmp/curl.out"

function callGETService {
    local uri=$1
    local certAtt=""

    if [[ -n "$CA_CERT_PATH" ]]; then
        certAtt="--cacert $CA_CERT_PATH"
    fi

    echo "Calling URI (GET):" ${uri}
#    echo ${API_KEY}
#    echo ${HEADER_ACCEPT}
#    echo ${HEADER_CONTENT_TYPE}
#    echo ${BASE_URL}
#    echo ${uri}
    curl -L -X GET -H "${API_KEY}" -H "${HEADER_ACCEPT}" -H "${HEADER_CONTENT_TYPE}" "${BASE_URL}${uri}" --output "${COMM_FILE}" 2> /dev/null > "${COMM_FILE}"
}

function callPOSTService {
    local uri=$1
    local json=$2
    local certAtt=""

    if [[ -n "$CA_CERT_PATH" ]]; then
        certAtt="--cacert $CA_CERT_PATH"
    fi

    echo "Calling URI (POST):" ${uri}
    curl --write-out '{"httpstatus":"%{http_code}"}' -L -X POST -H "${API_KEY}" -H "${HEADER_ACCEPT}" -H "${HEADER_CONTENT_TYPE}" "${BASE_URL}${uri}" --data-binary "${json}" 2> /dev/null > "${COMM_FILE}"
}

function callPUTService {
    local uri=$1
    local json=$2
    local certAtt=""

    if [[ -n "$CA_CERT_PATH" ]]; then
        certAtt="--cacert $CA_CERT_PATH"
    fi

    echo "Calling URI (PUT):" ${uri}
    curl --write-out '{"httpstatus":"%{http_code}"}' -L -X PUT -H "${API_KEY}" -H "${HEADER_ACCEPT}" -H "${HEADER_CONTENT_TYPE}" "${BASE_URL}${uri}" --data-binary "${json}" 2> /dev/null > "${COMM_FILE}"
}

function getHelp {
	echo "$0 [action] [options]"
	echo ""
	echo "ACTION"
	echo ""
	echo "     getorgs"
	echo "          Returns a list of Organizations that the provided API Key has access to."
	echo ""
	echo "     getnets"
	echo "          Returns a list of Networks configured in the provided Organization."
	echo "          Used together with -O, --organization"
	echo ""
	echo "     getdevs"
	echo "          Returns a list of Devices configured in the provided Network."
	echo "          Used together with -N, --network"
	echo ""
	echo "     gethealth"
	echo "          Returns the wireless health data for the provided network."
	echo "          Used together with -N, --network and -T, --timespan"
	echo ""
	echo "     newnet <\"network name\">"
	echo "          Create a new network in a given Organization."
	echo "          Used together with -O, --organization"
	echo ""
	echo "     newdev <serial-number>"
	echo "          Claim a device into a given Network."
	echo "          Used together with -N, --network"
	echo ""
	echo "     newwhd <\"destination-url\">"
	echo "          Creates a new Webhook Destination; Returns the Webhook ID."
	echo "          Used together with -N, --network"
	echo ""
	echo "     setwhalert <\"webhook-id\">"
	echo "          Enable Configuration Change Alerts for a Webhook with the provided ID."
	echo "          Used together with -N, --network"
	echo ""
	echo "     setssid <\"ssid name\">"
	echo "          Configures the first SSID for PSK with a provided Pre-Shared Key."
	echo "          Used together with -N, --network and -P, --psk"
	echo ""
	echo "     setssiddns"
	echo "          Configures the Layer 3 Firewall for the first SSID to allow only Umbrella DNS."
	echo "          Used together with -N, --network"
	echo ""
	echo "     setporttag <\"tag name\">"
	echo "          Sets a tag on a specfied switch port."
	echo "          Used together with -D, --device and -R, --port"
	echo ""
	echo "     setportvlan <\"vlan number\">"
	echo "          Sets a VLAN on a specfied switch port."
	echo "          Used together with -D, --device and -R, --port"
	echo ""
	echo "OPTIONS"
	echo ""
	echo "     -O, --organization"
	echo "          Specify the Organization to apply the action to."
	echo ""
	echo "     -N, --network"
	echo "          Specify the Network to apply the action to."
	echo ""
	echo "     -D, --device"
	echo "          Specify the Device to apply the action to."
	echo ""
	echo "     -P, --psk"
	echo "          Specify the PSK to use when configuring a SSID."
	echo ""
	echo "     -R, --port"
	echo "          Specify the Port to use when configuring a switch port."
	echo ""
	echo "     -T, --timespan"
	echo "          Specify the time duration (in hours) for the given operation."
	echo ""
}

# get all organizations
function getOrgs {
    callGETService "/organizations"

	local c=`cat $COMM_FILE`
	IFS='%'
	arr=$(echo $c | sed 's/},{/}%{/g' | tr -d "[]")

	for x in $arr
	do
		# add quotes to org json
		orgjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
		# parse json to get id and name
		orgid=$( echo $orgjson | grep -o '"id": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		orgname=$( echo $orgjson | grep -o '"name": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		echo "* $orgid - $orgname"
	done

	unset IFS
}

# get all networks
function getNets {
    callGETService "/organizations/$1/networks"

	local c=`cat $COMM_FILE`
	IFS='%'
	arr=$(echo $c | sed 's/},{/}%{/g' | tr -d "[]")

	for x in $arr
	do
		# add quotes to net json
		netjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
		# parse json to get id and name
		netid=$( echo $netjson | grep -o '"id": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		netname=$( echo $netjson | grep -o '"name": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		echo "* $netid - $netname"
	done

	unset IFS
}

# get all devices
function getDevs {
    callGETService "/networks/$1/devices"

	local c=`cat $COMM_FILE`
	IFS='%'
	arr=$(echo $c | sed 's/},{/}%{/g' | tr -d "[]")

	for x in $arr
	do
		# add quotes to dev json
		devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
		# parse json to get id and name
		devsn=$( echo $devjson | grep -o '"serial": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		devmodel=$( echo $devjson | grep -o '"model": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		devmac=$( echo $devjson | grep -o '"mac": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		echo "* $devsn - $devmodel - $devmac"
	done

	unset IFS
}

# add network
function newNet {
	local name=$2
	local json='{"name": "'${name}'", "timeZone": "Etc/GMT", "type": "switch appliance wireless"}'
    callPOSTService "/organizations/$1/networks" "${json}"

	local x=`cat $COMM_FILE`
	# add quotes to net json
	netjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	dtmp=$( echo $netjson | grep -o '"id": *"[^"]*"' | grep -o '"[^"]*"$' )

    local d=`echo $dtmp | cut -d' ' -f1 | sed 's/"//g'`
    if [ -z "$d" ]; then
    	cat $COMM_FILE
    	echo ""
    elif [ $d = "null" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "New network" $d "created."
	fi
}

# add device
function newDev {
	local sn=$2
	local json='{"serial": "'${sn}'"}'
    callPOSTService "/networks/$1/devices/claim" "${json}"

	local x=`cat $COMM_FILE`
	# add quotes to net json
	devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	stmp=$( echo $devjson | grep -o '"httpstatus": *"[^"]*"' | grep -o '"[^"]*"$' )

    local s=`echo $stmp | cut -d' ' -f2 | sed 's/"//g'`
    if [ $s != "200" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "New device" $sn "claimed."
	fi
}

# add webhook destination
function newWebhookDest {
	local whd=$2
	local json='{"name": "Webhook", "sharedSecret": "", "url": "'${whd}'"}'
    callPOSTService "/networks/$1/httpServers" "${json}"

	local x=`cat $COMM_FILE`
	# add quotes to net json
	netjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	dtmp=$( echo $netjson | grep -o '"id": *"[^"]*"' | grep -o '"[^"]*"$' )

    local d=`echo $dtmp | cut -d' ' -f1 | sed 's/"//g'`
    if [ -z "$d" ]; then
    	cat $COMM_FILE
    	echo ""
    elif [ $d = "null" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "New webhook destination" $d "created."
	fi
}

# set webhook alert for config changes
function setWebhook {
	local wh=$2
	local json='{"defaultDestinations": {"httpServerIds": ["'${wh}'"]}, "alerts": [{"type": "settingsChanged", "enabled": true}]}'
    callPUTService "/networks/$1/alertSettings" "${json}"

	local x=`cat $COMM_FILE`
	# add quotes to net json
	devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	stmp=$( echo $devjson | grep -o '"httpstatus": *"[^"]*"' | grep -o '"[^"]*"$' )

    local s=`echo $stmp | cut -d' ' -f2 | sed 's/"//g'`
    if [ $s != "200" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "Configuration update alerts enabled for webhook" $wh "."
	fi
}

# configure tag on switch port
function setPortTag {
	local tags=$2
	local json='{"tags": "'${tags}'"}'
    callPUTService "/devices/$1/switchPorts/$3" "${json}"

    local x=`cat $COMM_FILE`
	# add quotes to net json
	devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	stmp=$( echo $devjson | grep -o '"httpstatus": *"[^"]*"' | grep -o '"[^"]*"$' )

    local s=`echo $stmp | cut -d' ' -f2 | sed 's/"//g'`
    if [ $s != "200" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "Tag" $tags "added to port $3."
	fi
}

# configure vlan on switch port
function setPortVlan {
	local vlan=$2
	local json='{"type": "access", "voiceVlan": "", "vlan": "'${vlan}'"}'
    callPUTService "/devices/$1/switchPorts/$3" "${json}"

    local x=`cat $COMM_FILE`
	# add quotes to net json
	devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	stmp=$( echo $devjson | grep -o '"httpstatus": *"[^"]*"' | grep -o '"[^"]*"$' )

    local s=`echo $stmp | cut -d' ' -f2 | sed 's/"//g'`
    if [ $s != "200" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "Port $3 set as Access VLAN $vlan."
	fi
}

# configure SSID
function setSsid {
	local name=$2
	local psk=$3
	local json='{"name": "'${name}'", "enabled": true, "authMode": "psk", "encryptionMode": "wpa", "wpaEncryptionMode": "WPA2 only", "psk": "'${psk}'"}'
    callPUTService "/networks/$1/ssids/0" "${json}"

    local x=`cat $COMM_FILE`
	# add quotes to net json
	ssidjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	dtmp=$( echo $ssidjson | grep -o '"number": *"[^"]*"' | grep -o '"[^"]*"$' )

    local d=`echo $dtmp | cut -d' ' -f1 | sed 's/"//g'`
    if [ -z "$d" ]; then
    	cat $COMM_FILE
    	echo ""
    elif [ $d = "null" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "SSID" "'"$2"'" "configured."
	fi
}

# configure SSID L3 FW to only allow Umbrella DNS
function setSsidDns {
	local json='{"rules": [{"comment": "Allow Umbrella DNS", "policy": "allow", "protocol": "udp", "destPort": "53", "destCidr": "208.67.222.222/32"}, {"comment": "Allow Umbrella DNS", "policy": "allow", "protocol": "udp", "destPort": "53", "destCidr": "208.67.220.220/32"}, {"comment": "Block Other DNS", "policy": "deny", "protocol": "udp", "destPort": "53", "destCidr": "any"}]}'
    callPUTService "/networks/$1/ssids/0/l3FirewallRules" "${json}"

    local x=`cat $COMM_FILE`
	# add quotes to net json
	devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
	stmp=$( echo $devjson | grep -o '"httpstatus": *"[^"]*"' | grep -o '"[^"]*"$' )

    local s=`echo $stmp | cut -d' ' -f2 | sed 's/"//g'`
    if [ $s != "200" ]; then
    	cat $COMM_FILE
    	echo ""
    else
		echo "DNS Restrictions set on SSID."
	fi
}

# get wireless health
function getWirelessHealth {
	tsend=$(date +%s)
	offset="$((3600*$2))"
	tsstr="$(($tsend-offset))"
    callGETService "/networks/$1/connectionStats?t0=$tsstr&t1=$tsend"

	local c=`cat $COMM_FILE`
	IFS='%'
	arr=$(echo $c | sed 's/},{/}%{/g' | tr -d "[]")

	for x in $arr
	do
		# add quotes to dev json
		devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
		# parse json to get id and name
		devassoc=$( echo $devjson | grep -o '"assoc": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		devauth=$( echo $devjson | grep -o '"auth": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		devdhcp=$( echo $devjson | grep -o '"dhcp": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		devdns=$( echo $devjson | grep -o '"dns": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		devsuccess=$( echo $devjson | grep -o '"success": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		total="$((devassoc+devauth+devdhcp+devdns+devsuccess))"
		ftotal="$((devassoc+devauth+devdhcp+devdns))"
        echo "Wireless Health Information"
        echo "(Last $2 Hours)"
        echo "---------------------------"
        echo "     Total Connections: $total"
        echo "  Association Failures: $devassoc"
        echo "Authorization Failures: $devauth"
        echo "         DHCP Failures: $devdhcp"
        echo "          DNS Failures: $devdns"
        echo "                      ------"
        echo "    Failed Connections: $ftotal"
        echo "Successful Connections: $devsuccess"
        echo ""
	done
	unset IFS

    callGETService "/networks/$1/failedConnections?t0=$tsstr&t1=$tsend"

	local c=`cat $COMM_FILE`
	IFS='%'
	arr=$(echo $c | sed 's/},{/}%{/g' | tr -d "[]")

    count=0
    echo "Last 10 Failures"
    echo "---------------------------"
	for x in $arr
	do
		# add quotes to dev json
		devjson=$( echo $x | sed 's/:\([0-9]*\)\([,}]\)/:"\1"\2/g' )
		mac=$( echo $devjson | grep -o '"clientMac": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		step=$( echo $devjson | grep -o '"failureStep": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		ap=$( echo $devjson | grep -o '"serial": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		type=$( echo $devjson | grep -o '"type": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		vlan=$( echo $devjson | grep -o '"vlan": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
		ts=$( echo $devjson | grep -o '"ts": *[^"]*\.' | grep -o '[^:]*\.$' | sed 's/\.//g')
		curtime=$(date -r $ts)
		ssidnum=$( echo $devjson | grep -o '"ssidNumber": *"[^"]*"' | grep -o '"[^"]*"$' | sed 's/"//g')
        echo "* Client $mac failed at $curtime. Cause: $type ($step)."
        ((count++));if [[ count -eq 10 ]];then break;fi
    done
	unset IFS
}

if [ $# -eq 0 ]
  then
    echo "No arguments supplied"
    echo ""
    getHelp
  else
    POSITIONAL=()
    while [[ $# -gt 0 ]]
    do
      key="$1"

      case $key in
          -O|--organization)
          ORGANIZATION="$2"
          shift # past argument
          shift # past value
          ;;
          -N|--network)
          NETWORK="$2"
          shift # past argument
          shift # past value
          ;;
          -D|--device)
          DEVICE="$2"
          shift # past argument
          shift # past value
          ;;
          -P|--psk)
          PSK="$2"
          shift # past argument
          shift # past value
          ;;
          -R|--port)
          PORT="$2"
          shift # past argument
          shift # past value
          ;;
          -T|--timespan)
          TIMESPAN="$2"
          shift # past argument
          shift # past value
          ;;
          -?|--help)
		  getHelp
		  shift
          ;;
          --default)
          DEFAULT=YES
          shift # past argument
          ;;
          *)    # unknown option
          POSITIONAL+=("$1") # save it in an array for later
          shift # past argument
          ;;
      esac
    done
    set -- "${POSITIONAL[@]}" # restore positional parameters

#     echo ORGANIZATION    = "${ORGANIZATION}"
#     echo NETWORK         = "${NETWORK}"
#     echo DEVICE          = "${DEVICE}"
#     echo PSK             = "${PSK}"
# 	echo ""

    case $1 in
    	getorgs)
		    getOrgs
		    ;;
    	getnets)
		    getNets "${ORGANIZATION}"
		    ;;
    	getdevs)
		    getDevs "${NETWORK}"
		    ;;
    	gethealth)
		    getWirelessHealth "${NETWORK}" "${TIMESPAN}"
		    ;;
    	newnet)
		    newNet "${ORGANIZATION}" "$2"
		    ;;
    	newdev)
		    newDev "${NETWORK}" "$2"
		    ;;
    	newwhd)
		    newWebhookDest "${NETWORK}" "$2"
		    ;;
    	setwhalert)
		    setWebhook "${NETWORK}" "$2"
		    ;;
    	setssid)
		    setSsid "${NETWORK}" "$2" "${PSK}"
		    ;;
    	setssiddns)
		    setSsidDns "${NETWORK}"
		    ;;
    	setporttag)
		    setPortTag "${DEVICE}" "$2" "${PORT}"
		    ;;
    	setportvlan)
		    setPortVlan "${DEVICE}" "$2" "${PORT}"
		    ;;
		*)
		    echo "Invalid arguments"
		    ;;
	esac
fi