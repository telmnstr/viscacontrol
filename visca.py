import pygame, socket, time, errno, struct, sys


#
#
# Cisco TelepresenceHD Camera Control Jank
#
# This controls Cisco cameras connected to a network via an ethernet to serial bridge such as the
#   Lantronix MSS or Digi Portserver TS series
#
# Cisco command reference:
#   https://www.cisco.com/c/dam/en/us/td/docs/telepresence/endpoint/camera/precisionhd/user_guide/precisionhd_1080p-720p_camera_user_guide.pdf
# Arduino Project with some good info:
#   https://github.com/foxworth42/arduino-VISCA-controller/blob/master/visca_controller/src/visca_controller.h
#
#
#

TCP_IP = '192.168.1.69'
TCP_PORT = 3001
BUFFER_SIZE = 1024
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

s.setblocking(False)

version = 'VISCA Control v0.2'

from pygame.locals import *
 
pygame.init()
screen = pygame.display.set_mode((800, 200))
pygame.display.set_caption(version)
clock = pygame.time.Clock()


BLACK   = ( 0, 0, 0 )
WHITE   = ( 255,255,255 )
GREY    = ( 128, 128, 128 )
RED     = ( 255, 0,  0 )
BLUE    = ( 0,  0,  255 )
YELLOW  = ( 255, 255, 0 )
PURPLE  = ( 255, 0, 255 )


panUp =         b'\x01\x06\x01\x00\x00\x03\x01\xFF' 
panDown =       b'\x01\x06\x01\x00\x00\x03\x02\xFF' 
panLeft =       b'\x01\x06\x01\x00\x00\x01\x03\xFF' 
panRight =      b'\x01\x06\x01\x00\x00\x02\x03\xFF' 
panStop =       b'\x01\x06\x01\x09\x09\x03\x03\xFF' 
panTiltPosReq = b'\x09\x06\x12\xFF' 

zoomCommand = b'\x01, \x04, \x07, \x2F, \xFF' 
zoomTele =    b'\x01\x04\x07\x2F\xFF' 
zoomWide =    b'\x01\x04\x07\x3F\xFF' 
zoomStop =    b'\x01\x04\x07\x00\xFF' 
zoomDirect =  b'\x01\x04\x47\x00\x00\x00\x00\xFF'
zoomPosReq =  b'\x09\x04\x47\xFF' 

focusAuto =     b'\x01\x04\x38\x02\xFF' 
focusManual =   b'\x01\x04\x38\x03\xFF' 
focusDirect =   b'\x01\x04\x48\x00\x00\x00\x00\xFF'
focusFar =      b'\x01\x04\x08\x20\xFF' 
focusNear =     b'\x01\x04\x08\x30\xFF' 
focusStop =     b'\x01\x04\x08\x00\xFF' 
focusModeInq =  b'\x09\x04\x38\xFF' 
focusPosReq =   b'\x09\x04\x48\xFF'

aeAuto =      b'\x01\x04\x39\x00\xFF'   # Automatic Exposure Settings
aeManual =    b'\x01\x04\x39\x03\xFF' 

addressCommand = b'\x88\x30\x01\xFF' # Sets camera address (Needed for Daisy Chaining)
irOff =          b'\x01\x06\x09\x03\xff' # Turn off IR control req for speed 
callLedOn =      b'\x01\x33\x01\x01\xff'
callLedOff =     b'\x01\x33\x01\x00\xff'
callLedBlink =   b'\x01\x33\x01\x02\xff'

videoMode1080p30 = b'\x01\x35\x00\x01\x00\xff'    # HDMI is 1080p30, SDI is 1080p30
videoMode1080p60 = b'\x01\x35\x00\x03\x00\xff'    # HDMI is 1080p60, SDI is 720p60
videoMode720p30  = b'\x01\x35\x00\x05\x00\xff'    # HDMI is 720p30, SDI is 720p30


camBytes = [ 0, b'\x81', b'\x82', b'\x83', b'\x84', b'\x85', b'\x86', b'\x87' ]

currentCamByte = camBytes[1] 
currentCam = 1     # Current camera selected, text
currentPos = 0     # Current position selection in array
recordPos = False      # Menu option that next position button is a record it
amount_received = 0
amount_expected = 1
CAPTURE = 0
positionArray = 0   # Array of [camera number 1 to 7][camera position 1 to 7][xy, zoom, focus]
position_keys = ["q", "w", "e", "r", "t", "y", "u", "i"]
speed_keys = ["z", "x", "c", "v", "b"]
speed_byte = [ 0 ]
currentCamSpeed = 2
camSpeedArray = [b'\x00\x00', b'\x02\x02',  b'\x03\x03', b'\x05\x05', b'\x0F\x0F']

statusMessage = ["0", 0 ]


# init arrays
currentPos = [[0]*8 for i in range(8)]
positionArray = [[[0]*8 for i in range(8)]*8 for j in range(8)]



# Load the movement data from file
#

f = open("visca.pos", "r")
for i in range(1,8):
     for j in range(8):
        positionArray[i][j][0] = f.read(8)   # Read in XY positions
        positionArray[i][j][1] = f.read(4)   # Read in Zoom positions
        positionArray[i][j][2] = f.read(4)   # Read in Focus positions
f.close()



# Init camera commands
# Try to avoid doing a reset or anything just incase there is a need to restart control
# app while production underway. 

print ("Telling cameras to enumerate addresses")
s.send(addressCommand)
time.sleep(1)           # short delay, no tight loops


print ("IR Remote off, Call LED off, Set video mode")
for i in range(1,7):
    s.send( camBytes[i] + irOff)
    s.send( camBytes[i] + callLedOff)
    s.send( camBytes[i] + videoMode1080p30)









#
# Store or recall position function
# 
def store_or_recall(camNum):

            currentPos[currentCam] = camNum
            if recordPos == True:
               get_position()
	       global recordPos
               recordPos = False
            else:
               MESSAGE = (currentCamByte + b'\x01\x06\x20' + positionArray[currentCam][currentPos[currentCam]][0] + positionArray[currentCam][currentPos[currentCam]][1] + positionArray[currentCam][currentPos[currentCam]][2] + b'\xff')
               s.send(MESSAGE)






#
# Send request to get pan/tilt, then zoom, then focus
#
# Cisco docs say the response should always be \x90\x50 ... but the responses follow
# camera IDs, cam 1 = \x90, 2 = \xa0, 3 = \xb0 and so on
#

def get_position():
     s.setblocking(True)
     s.send(currentCamByte + panTiltPosReq)

     while True:
        data = s.recv(11)
        if data:
            print     "  PosReq: PanTilt Received %d bytes. " % (len(data))
	    if data[1:2] == b'\x50':
                print "          Received PT inquiry response"
                positionArray[currentCam][currentPos[currentCam]][0] = data[2:-1]
                s.setblocking(False)
                break

     s.setblocking(True)
     s.send(currentCamByte + zoomPosReq)

     while True:
        data = s.recv(7)
        if data:
            print     "  PosReq: Zoom Received %d bytes: " % (len(data))
            if data[1:2] == b'\x50':
                print "          Received zoom inquiry response"
                positionArray[currentCam][currentPos[currentCam]][1] = data[2:-1]
                s.setblocking(False)
                break

     s.setblocking(True)
     s.send(currentCamByte + focusPosReq)

     while True:
        data = s.recv(7)
        if data:
            print     "  PosReq: Focus Received %d bytes: " % (len(data))
            if data[1:2] == b'\x50':
                print "          Received focus inquiry response"
                positionArray[currentCam][currentPos[currentCam]][2] = data[2:-1]
                s.setblocking(False)
                break

     statusMessage[0] = "Position logged"







#
# Write out all pan/tilt/zoom/focus data to the save file
#

def write_position_file():

     f = open("visca.pos", "w")

     for i in range(1,8):
        for j in range(8):
           f.write(positionArray[i][j][0])
           f.write(positionArray[i][j][1])
           f.write(positionArray[i][j][2])

     f.close()
     statusMessage[0] = "Position file written"












#
#
#
# Main Loop

 
while 1:
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()



# Camera move keys
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                print("Right key has been pressed")
                s.send(currentCamByte + panRight[:3] + camSpeedArray[currentCamSpeed] + panRight[5:]) 
 		currentPos[currentCam] = 9    # this blanks out the UI for chosen memory slot
            if event.key == pygame.K_LEFT:
                print("Left key has been pressed")
                s.send(currentCamByte + panLeft[:3] + camSpeedArray[currentCamSpeed] + panLeft[5:])
 		currentPos[currentCam] = 9
            if event.key == pygame.K_UP:
                print("Up key has been pressed")
                s.send(currentCamByte + panUp[:3] + camSpeedArray[currentCamSpeed] + panUp[5:])
 		currentPos[currentCam] = 9
            if event.key == pygame.K_DOWN:
                print("Down key has been pressed")
                s.send(currentCamByte + panDown[:3] + camSpeedArray[currentCamSpeed] + panDown[5:])
 		currentPos[currentCam] = 9
            if event.key == pygame.K_PERIOD:
                print(". key has been pressed")
                s.send(currentCamByte + zoomTele)
            if event.key == pygame.K_COMMA:
                print(", key has been pressed")
                s.send(currentCamByte + zoomWide)

# Camera stored position keys

            if event.key == pygame.K_q:
                print("q key has been pressed")
                store_or_recall(0)

            if event.key == pygame.K_w:
                print("w key has been pressed")
                store_or_recall(1)

            if event.key == pygame.K_e:
                print("e key has been pressed")
                store_or_recall(2)

            if event.key == pygame.K_r:
                print("r key has been pressed")
                store_or_recall(3)

            if event.key == pygame.K_t:
                print("t key has been pressed")
                store_or_recall(4)

            if event.key == pygame.K_y:
                print("y key has been pressed")
                store_or_recall(5)

            if event.key == pygame.K_u:
                print("u key has been pressed")
                store_or_recall(6)


            if event.key == pygame.K_0:
                print("0 key has been pressed")
                s.send(addressCommand)
                statusMessage[0] = "Sent re-address command to cams"

#               s.send(b'\x80\x30\x00\xff')
#               s.send(b'\x80\x30\x01\xff')
#               s.send(b'\x80\x30\x02\xff')
#               s.send(b'\x80\x30\x03\xff')




            if event.key == pygame.K_s:
	        print("s key has been pressed, saving position data")
                write_position_file()
                statusMessage[0] = "Position data written to disk"



# Camera Select Keys
            if event.key == pygame.K_1:
                print("1 key has been pressed, cam1 selected")
                currentCamByte = camBytes[1]
		currentCam = 1
            if event.key == pygame.K_2:
                print("2 key has been pressed, cam2 selected")
                currentCamByte = camBytes[2]
		currentCam = 2
            if event.key == pygame.K_3:
                print("3 key has been pressed, cam3 selected")
                currentCamByte = camBytes[3]
		currentCam = 3
            if event.key == pygame.K_4:
                print("4 key has been pressed, cam4 selected")
                currentCamByte = camBytes[4]
		currentCam = 4
            if event.key == pygame.K_5:
                print("5 key has been pressed, cam4 selected")
                currentCamByte = camBytes[5]
                currentCam = 5
            if event.key == pygame.K_6:
                print("6 key has been pressed, cam4 selected")
                currentCamByte = camBytes[6]
                currentCam = 6
            if event.key == pygame.K_7:
                print("7 key has been pressed, cam4 selected")
                currentCamByte = camBytes[7]
                currentCam = 7


# Camera Speed Keys
            if event.key == pygame.K_z:
                print("z key has been pressed, speed 0 selected")
                currentCamSpeed = 0 

            if event.key == pygame.K_x:
                print("x key has been pressed, speed 1 selected")
                currentCamSpeed = 1 

            if event.key == pygame.K_c:
                print("c key has been pressed, speed 2 selected")
                currentCamSpeed = 2

            if event.key == pygame.K_v:
                print("v key has been pressed, speed 3 selected")
                currentCamSpeed = 3

            if event.key == pygame.K_b:
                print("b key has been pressed, speed 4 selected")
                currentCamSpeed = 4



# Set flag to store a position versus move to it 

	    if event.key == pygame.K_m: 
		print("m key has been pressed, to capture position")
		recordPos = True

# Quit key
	    if event.key == pygame.K_EQUALS:
		print ("= key pressed, exit.")
                sys.exit()




# Upon releasing keys, stop movement
 
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_RIGHT:
                print("Right key has been released")
                s.send(currentCamByte + panStop)
            if event.key == pygame.K_LEFT:
                print("Right key has been released")
                s.send(currentCamByte + panStop)
            if event.key == pygame.K_UP:
                print("Up key has been released")
                s.send(currentCamByte + panStop)
            if event.key == pygame.K_DOWN:
                print("Down key has been released")
                s.send(currentCamByte + panStop)
            if event.key == pygame.K_PERIOD:
                print(". key has been released")
                s.send(currentCamByte + zoomStop)
            if event.key == pygame.K_COMMA:
                print(", key has been released")
                s.send(currentCamByte + zoomStop)





    try:
        data = s.recv(64)
        if not data:
            print "connection closed"
            s.close()
            break
        else:
            if data[:2] == b'\x90\x50':
               print "VISCA Reply: Cam1 OK"
	    elif data[:2] == b'\xa0\x50':
               print "VISCA Reply: Cam2 OK"
            elif data[:2] == b'\xb0\x50':
               print "VISCA Reply: Cam3 OK"
            elif data[:2] == b'\xc0\x50':
               print "VISCA Reply: Cam4 OK"
            elif data[:2] == b'\xd0\x50':
               print "VISCA Reply: Cam5 OK"
            elif data[:2] == b'\xe0\x50':
               print "VISCA Reply: Cam6 OK"
            elif data[:2] == b'\x60\x01':
	       print "VISCA Reply: Message Length Error"
            elif data[:2] == b'\x60\x02':
               print "VISCA Reply: Syntax error"
	    elif data[:2] == b'\x60\x03':
	       print "VISCA Reply: Command buffer full"
            elif data[:2] == b'\x60\x41':
               print "VISCA Reply: Command not executable"
            else:
               print "VISCA Received %d bytes." % (len(data))
#
#  This will print the data variable in hex, but can't seem to supress newlines
#              for character in data:
#                  print character.encode('hex')


    except socket.error, e:
        if e.args[0] == errno.EWOULDBLOCK: 
#            print 'EWOULDBLOCK'
             time.sleep(.1)           # short delay, no tight loops
        else:
	    print ("Failure to connect to TCP device for cameras?")
            print e
            break

# 
# Draw Screen Routine
#

    screen.fill(pygame.Color("BLACK"))

# Header and key info

    font = pygame.font.SysFont('Calibri', 40, True, False)
    pygame.draw.line(screen, BLUE, [0,30], [800, 30], 5)
    text = font.render("VISCA Control",True,WHITE)
    screen.blit(text, [0,0])
    text = font.render("Cam:",True,WHITE)
    screen.blit(text, [0,40])
    text = font.render("Pos:",True,WHITE)
    screen.blit(text, [0,70])
    text = font.render("Spd:",True,WHITE)
    screen.blit(text, [0,100])

    
# Menu Options

    font = pygame.font.SysFont('Calibri', 25, True, False)
    text = font.render("m",True,YELLOW)
    screen.blit(text, [300,40])
    text = font.render("Store camera position",True,GREY)
    screen.blit(text, [320,40])

    text = font.render("s",True,YELLOW)
    screen.blit(text, [300,60])
    text = font.render("Save all memories to disk",True,GREY)
    screen.blit(text, [320,60])

    text = font.render("=",True,YELLOW)
    screen.blit(text, [300,80])
    text = font.render("Exit application",True,GREY)
    screen.blit(text, [320,80])

    text = font.render (",   .",True,YELLOW)
    screen.blit(text, [300,100])
    text = font.render ("/    Zoom Out / In ", True,GREY)
    screen.blit(text, [310,100])

    font = pygame.font.SysFont('Calibri', 40, True, False)
    


# Cam number display
    for l in range(1,7):
        if currentCam == l:
	  text = font.render(str(l),True,RED)
          pygame.draw.rect(screen, RED, pygame.Rect(l*30+63, 39, 28, 28),  2)
        else:
	  text = font.render(str(l),True,GREY)
          pygame.draw.rect(screen, GREY, pygame.Rect(l*30+63, 39, 28, 28),  2)
        screen.blit(text, [l*30+70,40])

# Position display
    for l in range(7):
        if currentPos[currentCam] == l:
         text = font.render(position_keys[l],True,PURPLE)
	 pygame.draw.rect(screen, PURPLE, pygame.Rect(l*30+63, 70, 28, 28),  2)
        else:
         text = font.render(position_keys[l],True,GREY)
         pygame.draw.rect(screen, GREY, pygame.Rect(l*30+63, 70, 28, 28),  2)
        screen.blit(text, [l*30+70,70])

# Speed display
    for l in range(5):
        if currentCamSpeed == l:
         text = font.render(speed_keys[l],True,PURPLE)
         pygame.draw.rect(screen, PURPLE, pygame.Rect(l*30+63, 100, 28, 28),  2)
        else:
         text = font.render(speed_keys[l],True,GREY)
         pygame.draw.rect(screen, GREY, pygame.Rect(l*30+63, 100, 28, 28),  2)
        screen.blit(text, [l*30+70,100])


# Status message display (and erase after timeout)
    if statusMessage[0] != "0":

        if statusMessage[1] == 0:
           statusMessage[1] = int(time.time()) + 2   # Stash epoch time so we can blank this out after a few seconds
           print "Status time update %f " % int(time.time())

        if statusMessage[1] == int(time.time()):
           statusMessage[1] = 0
           statusMessage[0] = "0"
           print "WE SHOULD EXIT"

        if statusMessage[1] != 0:
           text = font.render(statusMessage[0],True,RED)
           screen.blit(text, [0,160])


  

    pygame.display.flip()
    clock.tick(60)



