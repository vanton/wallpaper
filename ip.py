import socket
import psutil
import pprint
pp = pprint.PrettyPrinter(indent=4)

def getIp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

print(getIp())
print(socket.gethostbyname(socket.gethostname()))

interfaces = psutil.net_if_addrs()
ip_list = []

for i in interfaces:
    for j in interfaces[i]:
        if j.family == 2:
            print("{:<40s}IP: {}".format(i, j.address))
            ip_list.append((i, j.address))

pp.pprint(ip_list)
