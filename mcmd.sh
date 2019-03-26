#! /bin/bash

HEADER_CONTENT_TYPE="Content-Type: application/json"
HEADER_ACCEPT="Accept: application/json"
API_KEY="X-Cisco-Meraki-API-Key: bce348a3002d7d58b2c723fb0cb00bd99f02ca88"
BASE_URL="https://dashboard.meraki.com/api/v0"
COMM_FILE="/tmp/rest.json"
CURL_FILE="/tmp/curl.out"

function callGETService {
    local uri=$1
    local certAtt=""

    if [[ -n "$CA_CERT_PATH" ]]; then
        certAtt="--cacert $CA_CERT_PATH"
    fi

    echo "Calling URI (GET):" ${uri}
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
    echo "Sending Data:" ${json}
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
    curl -L -X PUT -H "${API_KEY}" -H "${HEADER_ACCEPT}" -H "${HEADER_CONTENT_TYPE}" "${BASE_URL}${uri}" --data-binary "${json}" 2> /dev/null > "${COMM_FILE}"
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
	echo "     newnet <\"network name\">"
	echo "          Create a new network in a given Organization."
	echo "          Used together with -O, --organization"
	echo ""
	echo "     newdev <serial-number>"
	echo "          Claim a device into a given Network."
	echo "          Used together with -N, --network"
	echo ""
	echo "     setssid <\"ssid name\">"
	echo "          Configures a SSID for PSK with a provided Pre-Shared Key."
	echo "          Used together with -N, --network and -P, --psk"
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
		orgid=$( echo $orgjson | grep -o '"id": *"[^"]*"' | grep -o '"[^"]*"$' )
		orgname=$( echo $orgjson | grep -o '"name": *"[^"]*"' | grep -o '"[^"]*"$' )
		echo "*" $orgid $orgname
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
		netid=$( echo $netjson | grep -o '"id": *"[^"]*"' | grep -o '"[^"]*"$' )
		netname=$( echo $netjson | grep -o '"name": *"[^"]*"' | grep -o '"[^"]*"$' )
		echo "*" $netid $netname
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
		devsn=$( echo $devjson | grep -o '"serial": *"[^"]*"' | grep -o '"[^"]*"$' )
		devmodel=$( echo $devjson | grep -o '"model": *"[^"]*"' | grep -o '"[^"]*"$' )
		devmac=$( echo $devjson | grep -o '"mac": *"[^"]*"' | grep -o '"[^"]*"$' )
		echo "*" $devsn $devmodel $devmac
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
    	newnet)
		    newNet "${ORGANIZATION}" "$2"
		    ;;
    	newdev)
		    newDev "${NETWORK}" "$2"
		    ;;
    	setssid)
		    setSsid "${NETWORK}" "$2" "${PSK}"
		    ;;
		*)
		    echo "Invalid arguments"
		    ;;
	esac
fi