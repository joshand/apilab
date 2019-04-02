[CmdletBinding()]
Param (
    [string] $name,
    [string] $organization,
    [string] $network,
    [string] $device,
    [string] $port,
    [string] $psk,
    [switch] $getorgs = $false,
    [switch] $getnets = $false,
    [switch] $getdevs = $false,
    [string] $newnet = $false,
    [string] $newdev = $false,
    [string] $newwhd = $false,
    [string] $setwhalert = $false,
    [string] $setssid = $false,
    [switch] $setssiddns = $false,
    [string] $setporttag = $false,
    [string] $setportvlan = $false,
    [switch] $help = $false
)

New-Variable -Scope global -Name headers
$global:headers = @{
	"Content-Type" = "application/json"
	"Accept" = "application/json"
	"X-Cisco-Meraki-API-Key" = "dc440e9ebf03a0935469cb586952c0448234d9d3"
}
New-Variable -Scope global -Name base_url
$global:base_url = "https://api.meraki.com/api/v0"

add-type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(
        ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) {
        return true;
    }
}
"@
$AllProtocols = [System.Net.SecurityProtocolType]'Ssl3,Tls,Tls11,Tls12'
[System.Net.ServicePointManager]::SecurityProtocol = $AllProtocols
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy

function callGETService {
	$uri = $global:base_url + $args[0];
	Write-Host 'Calling URI (GET):' $args[0];
	try {
		$response = Invoke-RestMethod -Method GET -Uri $uri -Headers $global:headers
	} catch {
		$ret = @{
			"statuscode" = $_.Exception.Response.StatusCode.value__
			"statusmsg" = $_.Exception.Response.StatusDescription
		}
		$response = $ret | ConvertTo-Json
	}
	return $response
}

function callPOSTService {
	$json = $args[1] | ConvertTo-Json
	Write-Host 'Calling URI (POST): ' $args[0];
	try {
		$response = Invoke-RestMethod -Method POST -Uri $uri -Body $json -Headers $global:headers
	} catch {
		$ret = @{
			"statuscode" = $_.Exception.Response.StatusCode.value__
			"statusmsg" = $_.Exception.Response.StatusDescription
		}
		$response = $ret
	} 
	return $response
}

function callPUTService {
	$json = $args[1] | ConvertTo-Json
	Write-Host 'Calling URI (PUT): ' $args[0];
	try {
		$response = Invoke-RestMethod -Method PUT -Uri $uri -Body $json -Headers $global:headers
 	} catch {
		$ret = @{
			"statuscode" = $_.Exception.Response.StatusCode.value__
			"statusmsg" = $_.Exception.Response.StatusDescription
		}
		$response = $ret
	}
	return $response
}

function find308dest {
	# Powershell really seems to be unfriendly with 308/Permanent Redirect given by
	#  Dashboard when making POST/PUT requests. Prior to issuing a POST/PUT, send the
	#  URL through this function, which will make a GET to determine the proper host
	#  to send the API request to.
	$fix_uri = $args[0] + $args[1];
	$fix_res = Invoke-WebRequest -Method GET -Uri $fix_uri -Headers $global:headers -MaximumRedirection 0 -ErrorAction SilentlyContinue
	$fix_url = $fix_res.Headers.Location
	$uri = $fix_url -replace $args[1],""

	return $uri
}

function getHelp {
	Write-Host "powershell -file mcmd.ps1 -action [name] [options]"
	Write-Host ""
	Write-Host "ACTION"
	Write-Host ""
	Write-Host "     -getorgs"
	Write-Host "          Returns a list of Organizations that the provided API Key has access to."
	Write-Host ""
	Write-Host "     -getnets"
	Write-Host "          Returns a list of Networks configured in the provided Organization."
	Write-Host "          Used together with -organization"
	Write-Host ""
	Write-Host "     -getdevs"
	Write-Host "          Returns a list of Devices configured in the provided Network."
	Write-Host "          Used together with -network"
	Write-Host ""
	Write-Host "     -newnet ""network name"""
	Write-Host "          Create a new network in a given Organization."
	Write-Host "          Used together with -organization"
	Write-Host ""
	Write-Host "     -newdev serial-number"
	Write-Host "          Claim a device into a given Network."
	Write-Host "          Used together with -network"
	Write-Host ""
	Write-Host "     -newwhd destination-url"
	Write-Host "          Creates a new Webhook Destination; Returns the Webhook ID."
	Write-Host "          Used together with -network"
	Write-Host ""
	Write-Host "     -setwhalert webhook-id"
	Write-Host "          Enable Configuration Change Alerts for a Webhook with the provided ID."
	Write-Host "          Used together with -network"
	Write-Host ""
	Write-Host "     -setssid ""ssid name"""
	Write-Host "          Configures a SSID for PSK with a provided Pre-Shared Key."
	Write-Host "          Used together with -network and -psk"
	Write-Host ""
	Write-Host "     -setssiddns"
	Write-Host "          Configures the Layer 3 Firewall for the first SSID to allow only Umbrella DNS."
	Write-Host "          Used together with -network"
	Write-Host ""
	Write-Host "     -setporttag ""tag-name"""
	Write-Host "          Sets a tag on a specfied switch port."
	Write-Host "          Used together with -network and -port"
	Write-Host ""
	Write-Host "     -setportvlan ""vlan-id"""
	Write-Host "          Sets a VLAN on a specfied switch port."
	Write-Host "          Used together with -network and -port"
	Write-Host ""
	Write-Host "OPTIONS"
	Write-Host ""
	Write-Host "     -organization"
	Write-Host "          Specify the Organization to apply the action to."
	Write-Host ""
	Write-Host "     -network"
	Write-Host "          Specify the Network to apply the action to."
	Write-Host ""
	Write-Host "     -device"
	Write-Host "          Specify the Device to apply the action to."
	Write-Host ""
	Write-Host "     -psk"
	Write-Host "          Specify the PSK to use when configuring a SSID."
	Write-Host ""
	Write-Host "     -port"
	Write-Host "          Specify the Port to use when configuring a switch port."
	Write-Host ""
}

# get all organizations
function getOrgs {
	$res = callGETService '/organizations'

	Foreach ($x in $res)
	{
		Write-Host '*' $x.id '"'$x.name'"'
	}
}

# get all networks
function getNets {
	$uri = '/organizations/' + $args[0] + '/networks';
	$res = callGETService $uri;

	Foreach ($x in $res)
	{
		Write-Host '*' $x.id '"'$x.name'"'
	}
}

# get all devices
function getDevs {
	$uri = '/networks/' + $args[0] + '/devices'
	$res = callGETService $uri

	Foreach ($x in $res)
	{
		Write-Host '*' $x.serial '"'$x.model'"' '"'$x.mac'"'
	}
}

# add network
function newNet {
	$network = @{
		name=$args[0]
		timeZone='Etc/GMT'
		type='switch appliance wireless'
	}
	$testuri = "/organizations"
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + '/organizations/' + $args[1] + '/networks'
	$res = callPOSTService $uri $network

	$id = $res.id
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host 'New network' '"'$id'"' 'created.'
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

# add device
function newDev {
	$device = @{
		serial=$args[0]
	}
	$testuri = "/networks/" + $args[1]
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + '/networks/' + $args[1] + '/devices/claim'
	$res = callPOSTService $uri $device

	$id = $res.id
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host 'New device' '"'$args[1]'"' 'claimed.'
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

# add webhook destination
function newWebhookDest {
	$wh = @{
		name='Webhook'
		sharedSecret=''
		url=$args[0]
	}
	$testuri = "/networks/" + $args[1]
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + '/networks/' + $args[1] + '/httpServers'
	$res = callPOSTService $uri $wh

	$id = $res.id
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host 'New webhook destination' '"'$id'"' 'created.'
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

# set webhook alert for config changes
function setWebhook {
	$wh = @{
		defaultDestinations=@{
			httpServerIds=@($args[0])
		}
		alerts=@(@{
			type='settingsChanged'
			enabled='true'
		})
	}
	$testuri = "/networks/" + $args[1]
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + "/networks/" + $args[1] + "/alertSettings"
	$res = callPUTService $uri $wh

	$id = $res.number
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host "Configuration update alerts enabled for webhook" '"'$args[0]'"' "."
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

# configure SSID
function setSsid {
	$ssid = @{
		name=$args[0]
		enabled='true'
		authMode='psk'
		encryptionMode='wpa'
		wpaEncryptionMode='WPA2 only'
		psk=$args[2]
	}
	$testuri = "/networks/" + $args[1]
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + "/networks/" + $args[1] + "/ssids/0"
	$res = callPUTService $uri $ssid

	$id = $res.number
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host "SSID" '"'$id'"' " configured."
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

# configure SSID L3 FW to only allow Umbrella DNS
function setSsidDns {
	$ssid = @{
		rules=@(
			@{
				comment='Allow Umbrella DNS'
				policy='allow'
				protocol='udp'
				destPort='53'
				destCidr='208.67.222.222/32'
			},
			@{
				comment='Allow Umbrella DNS'
				policy='allow'
				protocol='udp'
				destPort='53'
				destCidr='208.67.220.220/32'
			},
			@{
				comment='Block Other DNS'
				policy='deny'
				protocol='udp'
				destPort='53'
				destCidr='any'
			}
		)
	}
	$testuri = "/networks/" + $args[0]
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + "/networks/" + $args[0] + "/ssids/0/l3FirewallRules"
	$res = callPUTService $uri $ssid

	$id = $res.number
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host "DNS Restrictions set on SSID."
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

# configure tag on switch port
function setPortTag {
	$port = @{
		tags=$args[0]
	}
	$testuri = "/devices/" + $args[1] + "/switchPorts"
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + "/devices/" + $args[1] + "/switchPorts/" + $args[2]
	$res = callPUTService $uri $port

	$id = $res.number
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host "Tag" '"'$args[0]'"' "added to port" '"'$args[2]'"' "."
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

# configure vlan on switch port
function setPortVlan {
	$port = @{
		type='access'
		voiceVlan=''
		vlan=$args[0]
	}
	$testuri = "/devices/" + $args[1] + "/switchPorts"
	$newhost = find308dest $global:base_url $testuri
	$uri = $newhost + "/devices/" + $args[1] + "/switchPorts/" + $args[2]
	$res = callPUTService $uri $port

	$id = $res.number
	$sc = $res.statuscode
	if ($sc -eq $null) {
		Write-Host "Port" '"'$args[2]'"' "set as Access VLAN" '"'$args[0]'"' "."
	} else {
		$rout = $res | ConvertTo-Json
	        Write-Host ""
		Write-Host $rout
	}
}

If ($help -eq $true) {
	getHelp
} ElseIf ($getorgs -eq $true) {
	getOrgs
} ElseIf ($getnets -eq $true) {
	getNets $organization
} ElseIf ($getdevs -eq $true) {
	getDevs $network
} ElseIf ($newnet -ne $false) {
	newNet $newnet $organization
} ElseIf ($newdev -ne $false) {
	newDev $newdev $network
} ElseIf ($newwhd -ne $false) {
	newWebhookDest $newwhd $network
} ElseIf ($setwhalert -ne $false) {
	setWebhook $setwhalert $network
} ElseIf ($setssid -ne $false) {
	setSsid $setssid $network $psk
} ElseIf ($setssiddns -eq $true) {
	setSsidDns $network
} ElseIf ($setporttag -ne $false) {
	setPortTag $setporttag $device $port
} ElseIf ($setportvlan -ne $false) {
	setPortVlan $setportvlan $device $port
}
