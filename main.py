#This version works also nice

import json
import atexit
from gpiozero import AngularServo
from time import sleep
from time import time
from gpiozero.pins.pigpio import PiGPIOFactory
import RPi.GPIO as GPIO
import threading
from flask import Flask, request, render_template
import asyncio
from time import strftime
from datetime import datetime, timedelta
from pushbullet import Pushbullet

from flask_socketio import SocketIO, emit

import time
import smbus2


app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app=app, cors_allowed_origins='*')
authentication_code = "o.Wdas4ROPhzOC5U2jcV8YONdGrjAPPgwo"
pb = Pushbullet(authentication_code)
device_id = 13352352



GPIO.setmode(GPIO.BCM)

singalPIN = 6
sense1pin = 26
sense2pin = 13
sense3pin = 16


PIR_prev_millis = datetime.now()
time_thresh = 10
switch_state = False
move_count = 0
sec_mode =  False

my_alarms = []
sense_data = [0,0,0]

factory = PiGPIOFactory()
servo = AngularServo(singalPIN, min_angle=0, max_angle=180, min_pulse_width=0.0005, max_pulse_width=0.0024, pin_factory=factory)


si7021_ADD = 0x40 #Add the I2C bus address for the sensor here
si7021_READ_TEMPERATURE = 0xF3 #Add the command to read temperature here

AS7262_ADD = 0x49 #Add the I2C bus address for the sensor here

#Set up a write transaction that sends the command to measure temperature
cmd_meas_temp = smbus2.i2c_msg.write(si7021_ADD,[si7021_READ_TEMPERATURE])

#Set up a read transaction that reads two bytes of data
read_result = smbus2.i2c_msg.read(si7021_ADD,2)

#Physical registers
AS7262_STATUS_REG = 0x00
AS7262_WRITE_REG = 0x01
AS7262_READ_REG = 0x02

#Virtual registers
AS7262_GRN_H = 0x0C
AS7262_GRN_L = 0x0D

cmd_rd_status = smbus2.i2c_msg.write(AS7262_ADD,[AS7262_STATUS_REG])
cmd_rd_result = smbus2.i2c_msg.write(AS7262_ADD,[AS7262_READ_REG])
cmd_wr_vreg_grn_h = smbus2.i2c_msg.write(AS7262_ADD,[AS7262_WRITE_REG,AS7262_GRN_H])
cmd_wr_vreg_grn_l = smbus2.i2c_msg.write(AS7262_ADD,[AS7262_WRITE_REG,AS7262_GRN_L])

read_byte = smbus2.i2c_msg.read(AS7262_ADD,1)

bus = smbus2.SMBus(1)

def light_sense():
    global cmd_wr_vreg_grn_l
    global cmd_wr_vreg_grn_h
    global cmd_rd_status
    global cmd_rd_result
    global read_byte
#Read Status
    bus.i2c_rdwr(cmd_rd_status,read_byte)
    status = read_byte.buf[0]
    #print(status)

#convert the result to an int

#Select result register
    bus.i2c_rdwr(cmd_wr_vreg_grn_l)

    time.sleep(0.1)

#Read Status
    bus.i2c_rdwr(cmd_rd_status,read_byte)
    status = read_byte.buf[0]
    #print(status)

#Read result
    bus.i2c_rdwr(cmd_rd_result,read_byte)
    l_status = read_byte.buf[0]
    #print(l_status.hex())

    time.sleep

    bus.i2c_rdwr(cmd_wr_vreg_grn_h)

    time.sleep(0.1)

#Read Status
    bus.i2c_rdwr(cmd_rd_status,read_byte)
    h_status = read_byte.buf[0]
    #print(status)

#Read result
    bus.i2c_rdwr(cmd_rd_result,read_byte)
    h_status = read_byte.buf[0]
    print(h_status.hex())
    
    v = int(h_status.hex(), 16)

    if v > 0x05:
        return True
    else:
        return False
    
def temp_sense():

    #Execute the two transactions with a small delay between them
    global cmd_meas_temp
    global read_result
    bus.i2c_rdwr(cmd_meas_temp)
    time.sleep(0.1)
    bus.i2c_rdwr(read_result)

    #convert the result to an int
    temperature = int.from_bytes(read_result.buf[0]+read_result.buf[1],'big')
    celsius = 175.72 * temperature / 65536 - 46.85
    #print(celsius)
    return celsius

# if light(cmd_wr_vreg_grn_l, cmd_wr_vreg_grn_h, cmd_rd_status, cmd_rd_result, read_byte):
#     print("there is light")
# else:
#     print("there is no light")

class Alarm():
    def _init_(self,alarm_type,time,frequency):
        self.alarm_type = alarm_type
        self.time = time
        self.status = True
        self.frequency = frequency

    
    def ring(self):
        if(self.alarm_type == "flicker"):
            flicker()
        elif(self.alarm_type == "on"):
            on_switch()
        elif(self.alarm_type == "off"):
            off_switch()
        
        self.status = False

        if self.frequency != "once":
            if self.frequency == "daily":
                self.time = self.time + timedelta(days=1)
                self.status = True
            if self.frequency == "weekly":
                self.time = self.time + timedelta(days=7)
                self.status = True





def handle_action(action):
    global switch_state
    global PIR_prev_millis
    if action == "on":
        on_switch()
        switch_state = True
        PIR_prev_millis = time()
        print("on")
    elif action == "off":
        off_switch()
        switch_state = False
        print("off")
        

def handle_alarms():
    global my_alarms
    global sec_mode
    while sec_mode ==  False:
        current_datetime = datetime.now()
        for i in range(len(my_alarms)):
            if current_datetime>my_alarms[i].time and my_alarms[i].status == True:
                my_alarms[i].ring()
                print("ringing")
        sleep(2)

@app.route('/', methods=['GET', 'POST'])
def home_page():
    if request.method == "POST":
        action = request.form["action"]
        #security_mode = request.form[ True]
        handle_action(action)
        # if security_mode == True:
        #     sec_mode =  True
        #     print("Security sec_mode Activated")
        # elif security_mode == False:
        #     sec_mode =  False
        #     print("Security sec_mode Deactivated")
    return render_template("home_3.html",temperature = sense_data[2])

@app.route('/change-recorded', methods=['GET', 'POST'])
def change_recorded_page():
    if request.method == "POST":
        password = request.form["password"]
        username = request.form["username"]
        print(password,username)
    return render_template("change_recorded.html")

@app.route('/about', methods=['GET', 'POST'])
def about_page():
    return render_template("about.html")


@app.route('/user-details', methods=['GET', 'POST'])
def user_details_page():
    return render_template("user_details.html")

@app.route('/alarms', methods=['GET', 'POST'])
def alarms_page():
    global my_alarms
    if request.method == "POST":
        alarm_id = request.form["alarm_id"]
        print(alarm_id)
        if int(alarm_id)-1 <= len(my_alarms):
            my_alarms[int(alarm_id)-1].status = False
            print("alarm disabled")
    return render_template("alarms.html",my_alarms = my_alarms)

@app.route('/add-alarm', methods=['GET', 'POST'])
def add_alarm_page():
    return render_template("add_alarm.html")

@app.route('/alarm-set', methods=['GET', 'POST'])
def alarms_set_page():
    global my_alarms
        
    if request.method == 'POST':
        time = request.form['datetime']
        
        print(time)

        time_mod = time.replace("T", " ")

        print(time_mod)

        time_obj = datetime.strptime(time_mod, "%Y-%m-%d %H:%M")

        print(time_obj)

        frequency = request.form['frequency']
        alarm_type = request.form['type']
        alarm = Alarm(alarm_type,time_obj,frequency)
        my_alarms.append(alarm)
        print("Alarm created")    
    return render_template("alarm_set.html")
    
@app.route('/disable-alarm', methods=['GET', 'POST'])
def disable_alarm_page():
    return render_template("alarm_disabled.html")


@app.route('/beta-features', methods=['GET', 'POST'])
def beta_features_page():
    global sec_mode
    if request.method == "POST":
        security_mode = request.form["security_mode"]
        print("I am receiving sec_mode data: ", security_mode)
        if security_mode == "true":
            sec_mode =  True
            print("Security sec_mode Activated. Mode: ", sec_mode)
        elif security_mode == "false":
            sec_mode =  False
            print("Security sec_mode Deactivated. Mode: ", sec_mode)
    return render_template("beta_features.html")

@app.route('/beta-features/auth', methods=['GET', 'POST'])
def beta_features_auth_page():
    return render_template("beta_features_auth.html")


@app.route('/beta-features/auth/confirmed', methods=['GET', 'POST'])
def beta_features_auth_confirmed_page():
    global authentication_code
    global pb
    if request.method == "POST":
        authentication_code = request.form["auth_code"]
        print("Updated authentication code")
        print(authentication_code)
        pb = Pushbullet(authentication_code)
        print("connection attempted")
    return render_template("beta_features_auth_confirmed.html")


@app.route('/send-test-message', methods=['GET', 'POST'])
def beta_features_test_message():
    global pb
    if request.method == "POST":
        push = pb.push_note("Hello from Raspberry Pi!","")
        print("Test message sent")
    return render_template("beta_features_auth_confirmed.html")


# @app.route('/security-mode', methods=['POST'])
# def security_mode():
#     global mode
#     if request.method == "POST":
#         data = request.get_json()
#         website_mode = data.get('security_mode')
#         if website_mode:
#             sec_mode =  True
#             print("Security sec_mode Activated")
#         elif website_mode == False:
#             sec_mode =  False
#             print("Security sec_mode Deactivated")
    
    # Here you can handle the security sec_mode data as per your application logic
    # For example, you can update the database or trigger certain actions based on the security mode

    #return jsonify({"message": "Security sec_mode updated successfully"}), 200


def flicker():
    for i in range(5):
        on_switch()
        sleep(1)
        off_switch()
        sleep(1)

def off_switch():
    servo.angle = 120
    sleep(0.2)
    servo.angle = 140

def on_switch():
    servo.angle = 160
    sleep(0.2)
    servo.angle = 140
 
def sensors_read():
    global sense_data
    a = GPIO.input(sense1pin)
    b = GPIO.input(sense2pin)
    c = GPIO.input(sense3pin)
    temperature = temp_sense()
    light_status = light_sense()
    
    # print("Top: ")
    # print(a,'\n')
    # print("Right: ")
    # print(b,'\n')
    # print("Left: ")
    # print(c,'\n')

    # print("Temperature = ",temperature,'\n')
    print("Light status = ",light_status,'\n')

    motion_sense = b
    sense_data[0] = motion_sense
    sense_data[1] = light_status
    sense_data[2] = temperature


def PIRprocess(curr_time):
    global PIR_prev_millis
    global switch_state
    global move_count
    global time_thresh
    global sense_data
    movement = sense_data[0]

    if not movement:
        if (curr_time > PIR_prev_millis + timedelta(seconds=10)) and (switch_state == True):
            off_switch()
            switch_state = False
    elif movement and move_count >4:
        if switch_state == False:
            if not sense_data[1]:
                on_switch()
            switch_state = True
        PIR_prev_millis = curr_time
        move_count = 0
    elif movement and move_count<=4:
        move_count+=1
        PIR_prev_millis = curr_time

def update_json():
    global switch_state
    global sense_data
    print(type(sense_data[2]))
    data = {
        "Switch State": switch_state,
        "Motion Sense": sense_data[0],
        "Light Level": sense_data[1],
        "Temperature": sense_data[2]
    }
    json_data = json.dumps(data)
    return json_data

def PIR_Manage():
    global sec_mode
    global sense_data
    while True:
        if sec_mode == False:
            curr_time = datetime.now()
            sensors_read()
            PIRprocess(curr_time)
            print(update_json())
        sleep(2)
        
def security_mode_active():
    global sec_mode
    global authentication_code
    global pb
    global sense_data
    sensor_detect = [0,0,0,0,0]
    i = 0
    #print("security mode is being called")
    while True:
        #print("security mode loop")
        if sec_mode == True:
            print("I have entered security loop")
            sensors_read()
            temp = sense_data[0]
            print("PIRSense Result: ", temp)
            sensor_detect[i] = temp
            
            if all(element == 1 for element in sensor_detect): 
                push = pb.push_note("There is someone in your room!","")
                print("Sent warning")
                sensor_detect = [0,0,0,0,0]
            i+=1
            if i == 5:
                i = 0
        sleep(2)    


def setup():  
    degrees = 145
    servo.angle = degrees
    GPIO.setup(sense1pin, GPIO.IN)
    GPIO.setup(sense2pin, GPIO.IN)
    GPIO.setup(sense3pin, GPIO.IN)
    GPIO.setup(singalPIN, GPIO.OUT)

    


setup()

def runApp():
    global app
    app.run(debug=False,port=80, host='0.0.0.0')
  


if __name__ == "__main__":
    
    security_mode_thread = threading.Thread(target=security_mode_active)
    print("sec mode thread")
    alarms_thread = threading.Thread(target=handle_alarms)
    print("alarms thread")
    sensor_thread = threading.Thread(target=PIR_Manage)
    print("sensor thread")
    server_thread = threading.Thread(target=runApp)
    print("server thread")

    security_mode_thread.start()
    print("sec mode thread started")
    alarms_thread.start()
    print("alarms thread started")
    sensor_thread.start()
    print("sensor thread started")
    server_thread.start()
    print("server thread started")







# Join threads to main program
# server_thread.join()
# sensor_thread.join()
# alarms_thread.join()
# security_mode_thread.join()