# Mainserver.py and mainserver.html were attempts at port forwarding


from flask import Flask, request, render_template, redirect
from time import strftime
from datetime import datetime, timedelta

server_ip = '3.9.190.101'

app = Flask(__name__, template_folder='mainserver')

class device:
    def __init__(self,device_id,device_forwarding_port):
        self.device_id = device_id
        self.device_forwarding = device_forwarding_port

my_devices = []

device1 = device(12345678,42)

my_devices.append(device1)

def handle_device_id(device_id):
    for i in range(len(my_devices)):
        if device_id == my_devices[i].device_id:
            return my_devices[i].device_forwarding
        
    else:
        return 0


@app.route('/', methods=['GET', 'POST'])
def home_page():
    if request.method == "POST":
        device_id = request.form["device_id"]
        port_redirect = handle_device_id(device_id)
        if port_redirect != 0:
            url = 'https://'+server_ip+':'+port_redirect
            return redirect(url, code=301)
        
    return render_template("home.html",)
