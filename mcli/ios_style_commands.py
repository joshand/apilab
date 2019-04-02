import merakiaddon
from cmd_arg_parser import *
from cmd_ios_style import *
from operator import itemgetter
import itertools, sys
import meraki
import os

netorglist = []
orglist = []
curorg = []
shortioscmdlist = []
netlist = []
curnet = []
shortioscmdlistorg = []
devlist = []
curdev = []
devnetorglist = []
intlist = []
curint = []
# current_org = 0
# current_net = 0
shortioscmdlistintswitch = []
shortioscmdlistint = []

def xstr(s):
    return '' if s is None else str(s)


def print_data(srcdata):
    widths = [max(map(len, col)) for col in zip(*srcdata)]
    for row in srcdata:
        print("  ".join((val.ljust(width) for val, width in zip(row, widths))))


def build_org_list(arg):
    global orglist

    srcdata = merakiaddon.get_meraki_orgs()
    newlist = sorted(srcdata, key=itemgetter('name'))

    outdata = [["#", "Organization ID", "Organization Name"]]
    ocount = 0
    for org in newlist:
        ocount += 1
        outdata.append([str(ocount), str(org["id"]), org["name"]])
    orglist = outdata
    return outdata


def build_net_list(arg):
    global netlist
    global curorg

    srcdata = merakiaddon.get_meraki_networks(curorg[1])
    outdata = [["#", "Network ID", "Network Type", "Network Name"]]
    if srcdata == {}:
        pass
    else:
        newlist = sorted(srcdata, key=itemgetter('name'))

        ocount = 0
        for org in newlist:
            ocount += 1
            outdata.append([str(ocount), str(org["id"]), org["type"], org["name"]])
        netlist = outdata
    return outdata


def build_dev_list(arg):
    global orglist
    global netlist
    global netorglist
    global curorg
    global curnet
    global devlist

    # print(curorg)
    # print(curnet)

    srcdata = merakiaddon.get_meraki_devices(curnet[1])
    outdata = [["#", "Serial #", "Model", "MAC Address", "WAN 1", "WAN 2", "LAN", "Name"]]
    if not srcdata:
        devlist = outdata
    else:
        newlist = sorted(srcdata, key=itemgetter('model'))

        ocount = 0
        for dev in newlist:
            ocount += 1
            outdata.append([str(ocount), dev["serial"], dev["model"], dev["mac"], xstr(dev.get("wan1Ip")), xstr(dev.get("wan2Ip")), xstr(dev.get("lanIp")), xstr(dev["name"])])
        devlist = outdata
    return devlist


def show_enabled(e_stat):
    if e_stat is True:
        return "Yes"
    else:
        return "No"


def build_devint_list(arg):
    global orglist
    global netlist
    global devlist
    global intlist
    global netorglist
    global curorg
    global curnet
    global curdev

    outdata = []

    devtype = merakiaddon.decode_model(curdev[2])
    if devtype == "unknown":
        devtype = merakiaddon.manual_decode_model(curorg[1], curnet[1], curdev[1])

    if devtype == "wireless":
        outdata = [["#", "Interface", "IP-Assignment", "Name", "Enabled?", "Auth", "Band"]]
        int_data = meraki.getssids(merakiaddon.meraki_api_token, curnet[1], suppressprint=True)
        for d in int_data:
            outdata.append([str(d["number"]), "SSID" + str(d["number"]), d["ipAssignmentMode"], d["name"], show_enabled(d["enabled"]), d["authMode"], d["bandSelection"]])
    elif devtype == "switch":
        outdata = [["#", "Interface", "Name", "Enabled?", "Type", "VLAN", "Voice VLAN"]]
        int_data = meraki.getswitchports(merakiaddon.meraki_api_token, curdev[1], suppressprint=True)
        for d in int_data:
            pname = d["name"]
            if pname is None:
                pname = ""
            pvoicevlan = d["voiceVlan"]
            if pvoicevlan is None:
                pvoicevlan = ""

            outdata.append([str(d["number"]), "Ethernet" + str(d["number"]), pname, show_enabled(d.get("enabled", "")), d.get("type", ""), str(d.get("vlan", "")), str(pvoicevlan)])
        #print(outdata)
    elif devtype == "appliance":
        outdata = [["#", "Interface", "IP-Address", "Name", "Enabled?", "Subnet"]]
        int_data = meraki.getvlans(merakiaddon.meraki_api_token, curnet[1], suppressprint=True)
        if int_data[0] == 'VLANs are not enabled for this network':
            pass
        else:
            for d in int_data:
                outdata.append([str(d["number"]), "VLAN" + str(d["id"]), d["applianceIp"], d["name"], "", d["subnet"]])

    # print(devtype)
    # srcdata = merakiaddon.get_meraki_devices(curnet[1])
    # if not srcdata:
    #     devlist = outdata
    # else:
    #     newlist = sorted(srcdata, key=itemgetter('model'))
    #
    #     ocount = 0
    #     for dev in newlist:
    #         ocount += 1
    #         outdata.append([str(ocount), dev["serial"], dev["model"], dev["mac"], xstr(dev.get("wan1Ip")), xstr(dev.get("wan2Ip")), xstr(dev.get("lanIp")), xstr(dev["name"])])
    #     devlist = outdata
    # return devlist
    intlist = outdata
    return intlist


def build_netorg_list(arg):
    global orglist
    global netlist
    global netorglist
    global curorg

    spinner = itertools.cycle(['-', '/', '|', '\\'])

    srcdata = merakiaddon.get_meraki_orgs()
    newolist = sorted(srcdata, key=itemgetter('name'))
    outdata = [["#", "Organization ID", "Network ID", "Network Type", "Organization Name", "Network Name"]]
    netorglist = list(outdata)
    ocount = 0
    for org in newolist:
        sys.stdout.write(next(spinner))  # write the next character
        sys.stdout.flush()  # flush stdout buffer (actual character display)
        sys.stdout.write('\b')  # erase the last written char

        srcodata = merakiaddon.get_meraki_networks(str(org["id"]))
        if srcodata == {}:
            outdata.append([" ", str(org["id"]), "", "", org["name"], "[Error. Unable to Display.]"])
        else:
            newlist = sorted(srcodata, key=itemgetter('name'))

            for net in newlist:
                ocount += 1
                outdata.append([str(ocount), str(org["id"]), str(net["id"]), net["type"], org["name"], net["name"]])
                netorglist.append([str(ocount), str(org["id"]), str(net["id"]), net["type"], org["name"], net["name"]])
    return outdata


def build_netorgdev_list(arg):
    global orglist
    global netlist
    global devnetorglist
    global curorg

    spinner = itertools.cycle(['-', '/', '|', '\\'])

    showdetail = 0
    if arg:
        if arg[0:1].capitalize() == "D":
            showdetail = 1

    srcdata = merakiaddon.get_meraki_orgs()
    newolist = sorted(srcdata, key=itemgetter('name'))
    if showdetail == 1:
        outdata = [["#", "Organization ID", "Network ID", "Network Type", "Organization Name", "Network Name", "Device Name", "Serial #", "Model", "MAC Address", "WAN 1", "WAN 2", "LAN"]]
    else:
        outdata = [["#", "Organization Name", "Network Name", "Device Name", "Model", "WAN 1", "WAN 2", "LAN"]]
    devnetorglist = list(outdata)
    ocount = 0
    for org in newolist:
        srcodata = merakiaddon.get_meraki_networks(str(org["id"]))
        if srcodata == {}:
            if showdetail == 1:
                outdata.append([" ", str(org["id"]), "", "", org["name"], "[Error. Unable to Display.]", "", "", "", "", "", "", ""])
        else:
            newlist = sorted(srcodata, key=itemgetter('name'))

            for net in newlist:
                sys.stdout.write(next(spinner))  # write the next character
                sys.stdout.flush()  # flush stdout buffer (actual character display)
                sys.stdout.write('\b')  # erase the last written char

                srcndata = merakiaddon.get_meraki_devices(net["id"])
                if not srcndata:
                    if showdetail == 1:
                        outdata.append([" ", str(org["id"]), "", "", org["name"], "[Error. Unable to Display.]", "", "", "", "", "", "", ""])
                else:
                    newnlist = sorted(srcndata, key=itemgetter('model'))
                    for dev in newnlist:
                        ocount += 1
                        if showdetail == 1:
                            outdata.append([str(ocount), str(org["id"]), str(net["id"]), net["type"], org["name"], net["name"], xstr(dev["name"]), dev["serial"], dev["model"], dev["mac"], xstr(dev.get("wan1Ip")), xstr(dev.get("wan2Ip")), xstr(dev.get("lanIp"))])
                            devnetorglist.append([str(ocount), str(org["id"]), str(net["id"]), net["type"], org["name"], net["name"], xstr(dev["name"]), dev["serial"], dev["model"], dev["mac"], xstr(dev.get("wan1Ip")), xstr(dev.get("wan2Ip")), xstr(dev.get("lanIp"))])
                        else:
                            outdata.append([str(ocount), org["name"], net["name"], xstr(dev["name"]), dev["model"], xstr(dev.get("wan1Ip")), xstr(dev.get("wan2Ip")), xstr(dev.get("lanIp"))])
                            devnetorglist.append([str(ocount), org["name"], net["name"], xstr(dev["name"]), dev["model"], xstr(dev.get("wan1Ip")), xstr(dev.get("wan2Ip")), xstr(dev.get("lanIp"))])

                #print_data(outdata)
                #outdata = []

    #print(outdata)
    return outdata


def resolve_arg(arg, datalist):
    retval = None

    for x in datalist:
        # print(x)
        for y in x:
            if y == arg:
                retval = x
                break

        if retval:
            break

    if retval is None:
        if isinstance(arg, int) and arg < len(datalist):
            retval = datalist[arg]

    return retval


# ----------------------
# ---- Root Command Line
# ----------------------
class IOSCmdLine(CmdLine):
    global shortioscmdlist
    shortioscmdlist = ["show", "organization", "network", "quit"]

    def __init__(self):
        CmdLine.__init__(self)

    def do_quit(self, args):
        """Quits the program."""
        raise SystemExit

    def do_show(self, arg):
        """Show dashboard information ['organizations', 'networks', 'devices', 'inventory']"""
        global orglist

        fullcmdlist = [
            ('organizations', 'show organizations'),
            ('networks', 'show networks in all organizations'),
            ('devices', 'show devices in all organizations'),
            ('inventory', 'Show every entity in the container hierarchy'),
        ]
        shortcmdlist = []
        for c in fullcmdlist:
            shortcmdlist.append(c[0])

        self.params = Command(arg[0], fullcmdlist)

        if arg[0]:
            usedcmd = self.params.closest_match(arg[0], shortcmdlist)
        else:
            usedcmd = ""

        if arg[0].find(" ") >= 0:
            newarg = arg[0][arg[0].find(" ")+1:]
        else:
            newarg = ""

        if usedcmd == "organizations":
            print_data(build_org_list(newarg))

        if usedcmd == "networks":
            print_data(build_netorg_list(newarg))

        if usedcmd == "devices":
            print_data(build_netorgdev_list(newarg))

    def do_organization(self, arg):
        """Enter context: organization"""
        global orglist
        global curorg
        global netlist
        global devlist
        global intlist

        if not arg[0]:
            print("You must select an organization.")
        else:
            # curorg = str(arg)
            # self.prompt="Org-" + orglist[int(arg)][2] + "#"
            # print(orglist[int(arg)])

            i = IOSCmdLineOrg()
            if len(orglist) <= 0:
                build_org_list("")
            curorg = resolve_arg(arg[0], orglist)
            if arg[1]:
                build_net_list("")
                delorg = input("There are " + str(len(netlist)-1) + " network(s) in the organization; are you sure you want to remove the Organization '" + curorg[2] + "' [yes / NO]? ")
                if delorg.lower().find("y") >= 0:
                    #TODO: Org Delete
                    print("Not Implemented in API yet.")

                orglist = []
                netlist = []
                devlist = []
                intlist = []
                i = IOSCmdLine()
                i.prompt = "#"
                i.params = Command("show", [])
                i.cmdloop()

            if curorg is None:
                neworg = input("Unable to find Organization. Would you like to create a new organization with this name [yes / NO]? ")
                if neworg.lower().find("y") >= 0:
                    an = meraki.addorg(merakiaddon.meraki_api_token, arg[0], suppressprint=True)
                    build_org_list("")
                    curorg = resolve_arg(arg[0], orglist)
                    i.prompt = "Org-" + curorg[2] + "#"
                    i.params = Command("show", [])
                    i.cmdloop()
            # if curorg is None:
            #     print("Unable to find Organization.")
            else:
                i.prompt = "Org-" + curorg[2] + "#"

                # if int(arg) > len(orglist):
                #     build_org_list("")
                # i.prompt = "Org-" + orglist[int(arg)][2] + "#"
                # curorg = orglist[int(arg)]
                # i.prompt = "Org-" + curorg + "#"
                i.params = Command("show", [])
                i.cmdloop()

    # def do_network(self, arg):
    #     "Enter context: organization/network"
    #     global orglist
    #     global netlist
    #     global netorglist
    #     global curorg
    #     global curnet
    #
    #     if not arg:
    #         print("You must select a network.")
    #     else:
    #         #self.prompt="Org-" + orglist[int(arg)][2] + "#"
    #         i = IOSCmdLineNet()
    #         i.prompt = "Org-" + netorglist[int(arg)][4] + "/" + "Net-" + netorglist[int(arg)][5] + "#"
    #         curnet = [0, netorglist[int(arg)][2], netorglist[int(arg)][3], netorglist[int(arg)][5]]
    #         curorg = [0, netorglist[int(arg)][1], netorglist[int(arg)][4]]
    #         i.params = Command("show", [])
    #         i.cmdloop()

    def default(self, arg):
        usingno = False
        if arg[0:2].lower() == "no":
            usingno = True
            arg = arg[2:].strip()
        global shortioscmdlist
        usedcmd = self.params.closest_match(arg, shortioscmdlist)
        argrest = arg[arg.find(" ")+1:]
        if usedcmd:
            try:
                getattr(IOSCmdLine, 'do_' + usedcmd)(self, [argrest, usingno])
            except Exception as e:
                print("Command '" + usedcmd + "' not found or not valid in default context. (" + arg + ")")
                print(e)
        else:
            print("Unknown command: ", usedcmd)


# -------------------------
# ---- Organization Context
# -------------------------
class IOSCmdLineOrg(CmdLine):
    global shortioscmdlistorg
    shortioscmdlistorg = ["show", "network", "end", "quit"]

    def __init__(self):
        CmdLine.__init__(self)

    def do_quit(self, args):
        """Quits the program."""
        raise SystemExit

    def do_end(self, args):
        """Exit contexts and configuration."""
        i = IOSCmdLine()
        i.prompt = "#"
        i.params = Command("show", [])
        i.cmdloop()

    # def do_create(self, arg):
    #     """Create new object ['network']."""
    #     fullcmdlist = [
    #         ('network', 'create network'),
    #     ]
    #     shortcmdlist = []
    #     for c in fullcmdlist:
    #         shortcmdlist.append(c[0])
    #
    #     self.params = Command(arg[0], fullcmdlist)
    #
    #     if arg[0]:
    #         usedcmd = self.params.closest_match(arg[0], shortcmdlist)
    #     else:
    #         usedcmd = ""
    #
    #     if arg[0].find(" ") >= 0:
    #         newarg = arg[0][arg[0].find(" ")+1:]
    #     else:
    #         newarg = ""
    #
    #     if usedcmd == "network":
    #         print("create network", newarg)
    #
    # def do_delete(self, arg):
    #     """Delete existing object ['network']."""
    #     fullcmdlist = [
    #         ('network', 'delete network'),
    #     ]
    #     shortcmdlist = []
    #     for c in fullcmdlist:
    #         shortcmdlist.append(c[0])
    #
    #     self.params = Command(arg, fullcmdlist)
    #
    #     if arg:
    #         usedcmd = self.params.closest_match(arg, shortcmdlist)
    #     else:
    #         usedcmd = ""
    #
    #     if arg.find(" ") >= 0:
    #         newarg = arg[arg.find(" ")+1:]
    #     else:
    #         newarg = ""
    #
    #     if usedcmd == "network":
    #         print("delete network", newarg)

    def do_show(self, arg):
        """Show dashboard information ['networks', 'configuration']"""
        global netlist

        fullcmdlist = [
            ('networks', 'show networks'),
            ('configuration', 'show configuration'),
        ]
        shortcmdlist = []
        for c in fullcmdlist:
            shortcmdlist.append(c[0])

        self.params = Command(arg[0], fullcmdlist)

        if arg[0]:
            usedcmd = self.params.closest_match(arg[0], shortcmdlist)
        else:
            usedcmd = ""

        if arg[0].find(" ") >= 0:
            newarg = arg[0][arg[0].find(" ")+1:]
        else:
            newarg = ""

        if usedcmd == "networks":
            print_data(build_net_list(newarg))

        if usedcmd == "configuration":
            r = meraki.getorg(merakiaddon.meraki_api_token, curorg[1], suppressprint=True)
            cfg = "organization " + str(r["id"]) + "\n"
            cfg += " name " + r["name"] + "\n"
            # cfg += "\n"
            # r = meraki.getorginventory(merakiaddon.meraki_api_token, curorg[1], suppressprint=True)
            # print(r)
            print(cfg)

    def do_network(self, arg):
        """Enter context: network"""
        global orglist
        global netlist
        global curorg
        global curnet
        global devlist
        global intlist

        if not arg[0]:
            print("You must select a network.")
        else:
            #self.prompt="Net-" + netlist[int(arg)][3] + "#"
            i = IOSCmdLineNet()
            if len(netlist) <= 0:
                build_net_list("")
            curnet = resolve_arg(arg[0], netlist)

            if arg[1]:
                build_dev_list("")
                delnet = input("There are " + str(len(devlist)-1) + " device(s) in the network; are you sure you want to remove the Network '" + curnet[3] + "' [yes / NO]? ")
                if delnet.lower().find("y") >= 0:
                    meraki.delnetwork(merakiaddon.meraki_api_token, curnet[1], suppressprint=True)

                netlist = []
                devlist = []
                intlist = []
                i = IOSCmdLineOrg()
                i.prompt = "Org-" + curorg[2] + "#"
                i.params = Command("show", [])
                i.cmdloop()

            if curnet is None:
                newnet = input("Unable to find Network. Would you like to create a new network with this name [yes / NO]? ")
                if newnet.lower().find("y") >= 0:
                    an = meraki.addnetwork(merakiaddon.meraki_api_token, curorg[1], arg[0], "appliance switch wireless", [], "Etc/GMT", suppressprint=True)
                    build_net_list("")
                    curnet = resolve_arg(arg[0], netlist)
                    i.prompt = "Org-" + curorg[2] + "/" + "Net-" + curnet[3] + "#"
                    i.params = Command("show", [])
                    i.cmdloop()
            else:
                # i.prompt = "Org-" + curorg[2] + "/" + "Net-" + netlist[int(arg)][3] + "#"
                i.prompt = "Org-" + curorg[2] + "/" + "Net-" + curnet[3] + "#"
                # curnet = netlist[int(arg)]
                i.params = Command("show", [])
                i.cmdloop()

    def default(self, arg):
        usingno = False
        if arg[0:2].lower() == "no":
            usingno = True
            arg = arg[2:].strip()
        global shortioscmdlistorg
        usedcmd = self.params.closest_match(arg, shortioscmdlistorg)
        argrest = arg[arg.find(" ")+1:]
        if usedcmd:
            try:
                getattr(IOSCmdLineOrg, 'do_' + usedcmd)(self, [argrest, usingno])
            except Exception as e:
                print("Command '" + usedcmd + "' not found or not valid in 'organization' context. (" + arg + ")")
                print(e)
        else:
            print("Unknown command: ", usedcmd)


# --------------------
# ---- Network Context
# --------------------
class IOSCmdLineNet(CmdLine):
    global shortioscmdlistnet
    shortioscmdlistnet = ["show", "device", "quit", "end", "webhookserver", "alert"]

    def __init__(self):
        CmdLine.__init__(self)

    def do_quit(self, args):
        """Quits the program."""
        raise SystemExit

    def do_end(self, args):
        """Exit contexts and configuration."""
        i = IOSCmdLine()
        i.prompt = "#"
        i.params = Command("show", [])
        i.cmdloop()

    def do_webhookserver(self, arg):
        """Set Webhook HTTP Server"""
        global curnet
        if isinstance(arg, list):
            http_server = arg[0]
        else:
            http_server = arg

        r = merakiaddon.addhttpserver(merakiaddon.meraki_api_token, curnet[1], http_server, suppressprint=True)
        if "id" in r:
            r = merakiaddon.sethttpserverdefaultalert(merakiaddon.meraki_api_token, curnet[1], r["id"], suppressprint=True)

    def do_alert(self, arg):
        """Set status of specific alert ['settingsChanged']"""
        global curnet
        if isinstance(arg, list):
            alert_type = arg[0]
        else:
            alert_type = arg

        r = merakiaddon.setalertstatus(merakiaddon.meraki_api_token, curnet[1], alert_type, suppressprint=True)

    def do_show(self, arg):
        """Show dashboard information ['devices', 'configuration']"""
        global devlist

        fullcmdlist = [
            ('devices', 'show devices'),
            ('configuration', 'show configuration'),
        ]
        shortcmdlist = []
        for c in fullcmdlist:
            shortcmdlist.append(c[0])

        self.params = Command(arg[0], fullcmdlist)

        if arg[0]:
            usedcmd = self.params.closest_match(arg[0], shortcmdlist)
        else:
            usedcmd = ""

        if arg[0].find(" ") >= 0:
            newarg = arg[0][arg[0].find(" ")+1:]
        else:
            newarg = ""

        if usedcmd == "devices":
            print_data(build_dev_list(newarg))

        if usedcmd == "configuration":
            r = meraki.getnetworkdetail(merakiaddon.meraki_api_token, curnet[1], suppressprint=True)
            r2 = merakiaddon.gethttpservers(merakiaddon.meraki_api_token, curnet[1], suppressprint=True)
            cfg = "network " + r["id"] + "\n"
            cfg += " name " + r["name"] + "\n"
            cfg += " type " + r["type"] + "\n"
            cfg += " timeZone " + r["timeZone"] + "\n"
            cfg += " tags " + str(r["tags"]) + "\n"
            cfg += " disableMyMerakiCom " + str(r["disableMyMerakiCom"]) + "\n"
            cfg += " disableRemoteStatusPage " + str(r["disableRemoteStatusPage"]) + "\n"
            cfg += " organizationId " + str(r["organizationId"]) + "\n"

            for wh in r2:
                cfg += " webhook " + wh["id"] + "\n"
                cfg += "  name " + wh["name"] + "\n"
                cfg += "  url " + wh["url"] + "\n"
                cfg += "  sharedSecret " + wh["sharedSecret"] + "\n"

            print(cfg)

    def do_device(self, arg):
        "Enter context: device"
        global orglist
        global netlist
        global curorg
        global curnet
        global curdev
        global devlist
        global intlist

        if not arg[0]:
            print("You must select a device.")
        else:
            #self.prompt="Net-" + netlist[int(arg)][3] + "#"
            i = IOSCmdLineDev()
            if len(devlist) <= 0:
                build_dev_list("")
            curdev = resolve_arg(arg[0], devlist)
            # if curdev is None:
            #     print("Unable to find Device.")
            if arg[1]:
                # build_dev_list("")
                delnet = input("There are " + str(len(devlist) - 1) + " device(s) in the network; are you sure you want to remove the Network '" + curnet[3] + "' [yes / NO]? ")
                if delnet.lower().find("y") >= 0:
                    meraki.delnetwork(merakiaddon.meraki_api_token, curnet[1], suppressprint=True)

                devlist = []
                intlist = []
                i = IOSCmdLineOrg()
                i.prompt = "Org-" + curorg[2] + "#"
                i.params = Command("show", [])
                i.cmdloop()

            if curdev is None:
                if arg[0][0:1].upper() == "Q" and len(arg[0]) == 14:
                    newdev = input("Unable to find Device. Would you like to claim the device into this network [yes / NO]? ")
                    if newdev.lower().find("y") >= 0:
                        an = meraki.adddevtonet(merakiaddon.meraki_api_token, curnet[1], arg[0], suppressprint=True)
                        build_dev_list("")
                        curdev = resolve_arg(arg[0], devlist)
                        i.prompt = "Org-" + curorg[2] + "/" + "Net-" + curnet[3] + "/" + "Dev-" + curdev[1] + "#"
                        i.params = Command("show", [])
                        i.cmdloop()
            else:
                i.prompt = "Org-" + curorg[2] + "/" + "Net-" + curnet[3] + "/" + "Dev-" + curdev[1] + "#"
                # if int(arg) > len(devlist):
                #     build_dev_list("")
                # i.prompt = "Org-" + curorg[2] + "/" + "Net-" + curnet[3] + "/" + "Dev-" + devlist[int(arg)][1] + "#"
                # curdev = devlist[int(arg)]
                i.params = Command("show", [])
                i.cmdloop()

    def default(self, arg):
        usingno = False
        if arg[0:2].lower() == "no":
            usingno = True
            arg = arg[2:].strip()
        global shortioscmdlistnet
        usedcmd = self.params.closest_match(arg, shortioscmdlistnet)
        argrest = arg[arg.find(" ")+1:]
        if usedcmd:
            try:
                getattr(IOSCmdLineNet, 'do_' + usedcmd)(self, [argrest, usingno])
            except Exception as e:
                print("Command '" + usedcmd + "' not found or not valid in 'network' context. (" + arg + ")")
                print(e)
        else:
            print("Unknown command: ", usedcmd)


# -------------------
# ---- Device Context
# -------------------
class IOSCmdLineDev(CmdLine):
    global shortioscmdlistdev
    shortioscmdlistdev = ["show", "interface", "quit", "end"]

    def __init__(self):
        CmdLine.__init__(self)

    def do_quit(self, args):
        """Quits the program."""
        raise SystemExit

    def do_end(self, args):
        """Exit contexts and configuration."""
        i = IOSCmdLine()
        i.prompt = "#"
        i.params = Command("show", [])
        i.cmdloop()

    def do_show(self, arg):
        """Show dashboard information ['interfaces', 'configuration']"""
        global devlist

        fullcmdlist = [
            ('interfaces', 'show interfaces'),
            ('configuration', 'show configuration'),
        ]
        shortcmdlist = []
        for c in fullcmdlist:
            shortcmdlist.append(c[0])

        self.params = Command(arg[0], fullcmdlist)

        if arg[0]:
            usedcmd = self.params.closest_match(arg[0], shortcmdlist)
        else:
            usedcmd = ""

        if arg[0].find(" ") >= 0:
            newarg = arg[0][arg[0].find(" ")+1:]
        else:
            newarg = ""

        if usedcmd == "interfaces":
            print_data(build_devint_list(newarg))

        if usedcmd == "configuration":
            r = meraki.getdevicedetail(merakiaddon.meraki_api_token, curnet[1], curdev[1], suppressprint=True)
            cfg = "device " + r["serial"] + "\n"
            cfg += " name " + str(r["name"]) + "\n"
            cfg += " mac " + r["mac"] + "\n"
            cfg += " model " + r["model"] + "\n"
            cfg += " lanIp " + str(r["lanIp"]) + "\n"
            cfg += " lat " + str(r["lat"]) + "\n"
            cfg += " lng " + str(r["lng"]) + "\n"
            cfg += " address " + r["address"] + "\n"
            cfg += " networkId " + r["networkId"] + "\n"
            print(cfg)

    def do_interface(self, arg):
        """Enter context: interface"""
        global orglist
        global netlist
        global devlist
        global intlist
        global curorg
        global curnet
        global curdev
        global curint

        if not arg[0]:
            print("You must select an interface.")
        else:
            #self.prompt="Net-" + netlist[int(arg)][3] + "#"
            if len(intlist) <= 0:
                build_devint_list("")
            curint = resolve_arg(arg[0], intlist)
            if curint[1].find("SSID") >= 0:
                i = IOSCmdLineIntSSID()
            elif curint[1].find("Ethernet") >= 0:
                i = IOSCmdLineIntSwitch()
            else:
                print("Security appliance interface configuration not yet implemented.")
            # print(arg[0], intlist, curint)
            i.prompt = "Org-" + curorg[2] + "/" + "Net-" + curnet[3] + "/" + "Dev-" + curdev[1] + "/" + "Int-" + curint[1] + "#"
            #curnet = netlist[int(arg)]
            i.params = Command("show", [])
            i.cmdloop()

    def default(self, arg):
        usingno = False
        if arg[0:2].lower() == "no":
            usingno = True
            arg = arg[2:].strip()
        global shortioscmdlistdev
        usedcmd = self.params.closest_match(arg, shortioscmdlistdev)
        argrest = arg[arg.find(" ")+1:]
        # print(arg, usedcmd, argrest)
        if usedcmd:
            try:
                getattr(IOSCmdLineDev, 'do_' + usedcmd)(self, [argrest, usingno])
            except Exception as e:
                print("Command '" + usedcmd + "' not found or not valid in 'device' context. (" + arg + ")")
                print(e)
        else:
            print("Unknown command: ", usedcmd)


# -------------------
# ---- Interface Context (SSID)
# -------------------
class IOSCmdLineIntSSID(CmdLine):
    global shortioscmdlistint
    shortioscmdlistint = ["show", "quit", "end", "name", "shut", "psk", "clear", "accesslist"]

    def __init__(self):
        CmdLine.__init__(self)

    def do_quit(self, args):
        """Quits the program."""
        raise SystemExit

    def do_end(self, args):
        """Exit contexts and configuration."""
        i = IOSCmdLine()
        i.prompt = "#"
        i.params = Command("show", [])
        i.cmdloop()

    def do_shut(self, arg):
        """Disable SSID"""
        global curnet
        global curint

        if isinstance(arg, list) and arg[1]:
            # no shut
            r = merakiaddon.putssidconfig(merakiaddon.meraki_api_token, curnet[1], "true", "", "", curint[0], suppressprint=True)
        else:
            # shut
            r = merakiaddon.putssidconfig(merakiaddon.meraki_api_token, curnet[1], "false", "", "", curint[0], suppressprint=True)
        # print(r)

    def do_name(self, arg):
        """Set SSID Name"""
        global curint
        if isinstance(arg, list):
            ssid_name = arg[0]
        else:
            ssid_name = arg

        r = merakiaddon.putssidconfig(merakiaddon.meraki_api_token, curnet[1], "", ssid_name, "", curint[0], suppressprint=True)
        # print(r)

    def do_psk(self, arg):
        """Set SSID PSK"""
        global curint
        if isinstance(arg, list):
            ssid_psk = arg[0]
        else:
            ssid_psk = arg

        r = merakiaddon.putssidconfig(merakiaddon.meraki_api_token, curnet[1], "", "", ssid_psk, curint[0], suppressprint=True)
        # print(r)

    def do_accesslist(self, arg):
        """Set SSID Layer 3 Firewall Rule"""
        global curint
        if isinstance(arg, list):
            ssid_l3fw = arg[0]
        else:
            ssid_l3fw = arg

        aclarr = ssid_l3fw.split(" ")
        # allow protocol udp port 53 dst Any description Test
        #   0       1     2    3   4  5   6       7        8

        newacl = []
        if len(aclarr) == 9:
            r2 = meraki.getssidl3fwrules(merakiaddon.meraki_api_token, curnet[1], curint[0], suppressprint=True)
            if len(r2) > 2:
                for rnum in range(0, len(r2) - 2):
                    newacl.append(r2[rnum])

            newacl.append({"comment": aclarr[8], "policy": aclarr[0], "protocol": aclarr[2], "destPort": aclarr[4], "destCidr": aclarr[6]})
            a = meraki.updatessidl3fwrules(merakiaddon.meraki_api_token, curnet[1], curint[0], newacl, suppressprint=True)
        else:
            print("Please check your access-list syntax and try again.\neg: accesslist allow protocol udp port 53 dst Any description Test")

    def do_clear(self, arg):
        """Clear specific configurations ['access-list']"""
        global devlist

        fullcmdlist = [
            ('access-list', 'clear access-list'),
        ]
        shortcmdlist = []
        for c in fullcmdlist:
            shortcmdlist.append(c[0])

        self.params = Command(arg[0], fullcmdlist)

        if arg[0]:
            usedcmd = self.params.closest_match(arg[0], shortcmdlist)
        else:
            usedcmd = ""

        if arg[0].find(" ") >= 0:
            newarg = arg[0][arg[0].find(" ")+1:]
        else:
            newarg = ""

        if usedcmd == "access-list":
            a = meraki.updatessidl3fwrules(merakiaddon.meraki_api_token, curnet[1], curint[0], [], allowlan=True, suppressprint=True)


    def do_show(self, arg):
        """Show dashboard information ['configuration']"""
        global devlist

        fullcmdlist = [
            ('configuration', 'show configuration'),
        ]
        shortcmdlist = []
        for c in fullcmdlist:
            shortcmdlist.append(c[0])

        self.params = Command(arg[0], fullcmdlist)

        if arg[0]:
            usedcmd = self.params.closest_match(arg[0], shortcmdlist)
        else:
            usedcmd = ""

        if arg[0].find(" ") >= 0:
            newarg = arg[0][arg[0].find(" ")+1:]
        else:
            newarg = ""

        if usedcmd == "configuration":
            #print_data(build_devint_list(newarg))
            r = meraki.getssiddetail(merakiaddon.meraki_api_token, curnet[1], curint[0], suppressprint=True)
            r2 = meraki.getssidl3fwrules(merakiaddon.meraki_api_token, curnet[1], curint[0], suppressprint=True)
            cfg = "interface SSID" + str(r["number"]) + "\n"
            cfg += " name " + r["name"] + "\n"
            if r["enabled"]:
                cfg += " no shut\n"
            else:
                cfg += " shut\n"
            cfg += " authMode " + r["authMode"] + "\n"
            cfg += " encryptionMode " + r.get("encryptionMode","") + "\n"
            cfg += " wpaEncryptionMode " + r.get("wpaEncryptionMode","") + "\n"
            cfg += " psk " + r.get("psk","") + "\n"
            cfg += " splashPage " + r["splashPage"] + "\n"
            cfg += " ssidAdminAccessible " + str(r["ssidAdminAccessible"]) + "\n"
            cfg += " ipAssignmentMode " + r["ipAssignmentMode"] + "\n"
            cfg += " minBitrate " + str(r["minBitrate"]) + "\n"
            cfg += " bandSelection " + r["bandSelection"] + "\n"
            cfg += " perClientBandwidthLimitUp " + str(r["perClientBandwidthLimitUp"]) + "\n"
            cfg += " perClientBandwidthLimitDown " + str(r["perClientBandwidthLimitDown"]) + "\n"

            cfg += " access-list l3FirewallRules\n"
            for rule in r2:
                thiscom = rule["comment"]
                thispol = rule["policy"]
                thispro = rule["protocol"]
                thispor = rule["destPort"]
                thisnet = rule["destCidr"]

                cfg += "  " + thispol + " protocol " + thispro + " port " + thispor + " dst " + thisnet + " description " + thiscom + "\n"

            print(cfg)

    def default(self, arg):
        usingno = False
        if arg[0:2].lower() == "no":
            usingno = True
            arg = arg[2:].strip()
        global shortioscmdlistint
        usedcmd = self.params.closest_match(arg, shortioscmdlistint)
        argrest = arg[arg.find(" ")+1:]
        if usedcmd:
            try:
                getattr(IOSCmdLineIntSSID, 'do_' + usedcmd)(self, [argrest, usingno])
            except Exception as e:
                print("Command '" + usedcmd + "' not found or not valid in 'SSID interface' context. (" + arg + ")")
                print(e)
        else:
            print("Unknown command: ", usedcmd)


# -------------------
# ---- Interface Context (Switch / Eth port)
# -------------------
class IOSCmdLineIntSwitch(CmdLine):
    global shortioscmdlistintswitch
    shortioscmdlistintswitch = ["show", "quit", "end", "shut", "tag", "vlan"]

    def __init__(self):
        CmdLine.__init__(self)

    def do_quit(self, args):
        """Quits the program."""
        raise SystemExit

    def do_end(self, args):
        """Exit contexts and configuration."""
        i = IOSCmdLine()
        i.prompt = "#"
        i.params = Command("show", [])
        i.cmdloop()

    def do_shut(self, arg):
        """Disable Interfacee"""
        global curnet
        global curint

        if isinstance(arg, list) and arg[1]:
            # no shut
            r = meraki.updateswitchport(merakiaddon.meraki_api_token, curdev[1], curint[0], enabled=True, suppressprint=True)
        else:
            # shut
            r = meraki.updateswitchport(merakiaddon.meraki_api_token, curdev[1], curint[0], enabled=False, suppressprint=True)
        # print(r)

    def do_tag(self, arg):
        """Set Interface Tag"""
        global curint
        if isinstance(arg, list):
            int_tag = arg[0]
        else:
            int_tag = arg

        r = meraki.updateswitchport(merakiaddon.meraki_api_token, curdev[1], curint[0], tags=[int_tag], suppressprint=True)
        # print(r)

    def do_vlan(self, arg):
        """Set Interface VLAN"""
        global curint
        if isinstance(arg, list):
            int_vlan = arg[0]
        else:
            int_vlan = arg

        r = meraki.updateswitchport(merakiaddon.meraki_api_token, curdev[1], curint[0], vlan=int_vlan, porttype="access", suppressprint=True)
        # print(r)

    def do_show(self, arg):
        """Show dashboard information ['configuration']"""
        global devlist

        fullcmdlist = [
            ('configuration', 'show configuration'),
        ]
        shortcmdlist = []
        for c in fullcmdlist:
            shortcmdlist.append(c[0])

        self.params = Command(arg[0], fullcmdlist)

        if arg[0]:
            usedcmd = self.params.closest_match(arg[0], shortcmdlist)
        else:
            usedcmd = ""

        if arg[0].find(" ") >= 0:
            newarg = arg[0][arg[0].find(" ")+1:]
        else:
            newarg = ""

        if usedcmd == "configuration":
            #print_data(build_devint_list(newarg))
            r = meraki.getswitchportdetail(merakiaddon.meraki_api_token, curdev[1], curint[0], suppressprint=True)
            cfg = "interface Ethernet" + str(r["number"]) + "\n"
            if r["name"]:
                cfg += " name " + str(r.get("name", "")) + "\n"
            else:
                cfg += " no name\n"
            if r["enabled"]:
                cfg += " no shut\n"
            else:
                cfg += " shut\n"
            cfg += " tags " + str(r.get("tags", "")) + "\n"
            if r["poeEnabled"]:
                cfg += " power inline\n"
            else:
                cfg += " power inline never\n"
            if r["type"] == "trunk":
                cfg += " switchport mode trunk\n"
                cfg += " switchport trunk allowed vlans " + str(r["allowedVlans"]) + "\n"
            else:
                cfg += " switchport mode access\n"
                cfg += " switchport access vlan " + str(r["vlan"]) + "\n"
                if r["voiceVlan"]:
                    cfg += " switchport voice vlan " + str(r["voiceVlan"]) + "\n"
                else:
                    cfg += " no switchport voice vlan\n"

            cfg += " isolationEnabled " + str(r["isolationEnabled"]) + "\n"
            cfg += " rstpEnabled " + str(r["rstpEnabled"]) + "\n"
            cfg += " stpGuard " + r["stpGuard"] + "\n"
            cfg += " accessPolicyNumber " + str(r.get("accessPolicyNumber", "")) + "\n"
            cfg += " linkNegotiation " + str(r["linkNegotiation"]) + "\n"
            print(cfg)

    def default(self, arg):
        usingno = False
        if arg[0:2].lower() == "no":
            usingno = True
            arg = arg[2:].strip()
        global shortioscmdlistintswitch
        usedcmd = self.params.closest_match(arg, shortioscmdlistintswitch)
        argrest = arg[arg.find(" ")+1:]
        if usedcmd:
            try:
                getattr(IOSCmdLineIntSwitch, 'do_' + usedcmd)(self, [argrest, usingno])
            except Exception as e:
                print("Command '" + usedcmd + "' not found or not valid in 'switch interface' context. (" + arg + ")")
                print(e)
        else:
            print("Unknown command: ", usedcmd)


if __name__ == '__main__':
    bot_app_name = os.getenv("MERAKI_API_TOKEN")

    if not bot_app_name:
        merakiaddon.meraki_api_token = input("Please enter your Meraki API Token:")
        merakiaddon.header = {"X-Cisco-Meraki-API-Key": merakiaddon.meraki_api_token}

    cmdLine = IOSCmdLine()
    cmdLine.params = Command("show", [])
    cmdLine.cmdloop()