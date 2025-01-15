#import select
import sys

import time
#from datetime import datetime

import re
#import string

from machine import Pin, Timer

# constants
betweenButtonPauseMS = 50
pressButtonPauseMS = 100
buzzSetupNotifyOnMS = 200
buzzSetupNotifyOffMS = 800
buzzFlagOnMS = 300
buzzFlagOffMS = 200
customUpdateHoldMS = 5000

countdownWholeSeconds = 15

loopSleepMS = 50	# lag on detecting green request and red request
# does not affect false start detection because flag trigger
# is done at same time as starting clock, not when time expires

loopsPerTickle = (150*1000)/loopSleepMS	# under 3 minute auto shutdown

activateButtonValue = 0
releaseButtonValue = 1

activateFlagValue = 1
releaseFlagValue = 0

activateBuzzerValue = 1
releaseBuzzerValue = 0

signallingGoGreenValue = 0
quietGoGreenValue = 1

# state variables
finishedSetup = False
greenConfigured = False

timer = Timer()

# pins
gogreenPulldownInput = Pin(6, Pin.IN, Pin.PULL_DOWN)	# signals low

onesecPulldownOutput = Pin(2, Pin.OUT, Pin.PULL_DOWN)	# activate low
customPulldownOutput = Pin(3, Pin.OUT, Pin.PULL_DOWN)	# activate low
resetPulldownOutput = Pin(4, Pin.OUT, Pin.PULL_DOWN)	# activate low
startstopPulldownOutput = Pin(5, Pin.OUT, Pin.PULL_DOWN)	# activate low

flagPullupOutput = Pin(10, Pin.OUT, Pin.PULL_UP)	# activate high
buzzerPullupOutput = Pin(12, Pin.OUT, Pin.PULL_UP)	# activate high

led = Pin(25, Pin.OUT)

# subroutines

def startBuzz():
    buzzerPullupOutput.value(activateBuzzerValue)
    
def stopBuzz():
    buzzerPullupOutput.value(releaseBuzzerValue)
    
def startNotifyBuzz(timer):
    startBuzz()    
    timer.init(mode=Timer.ONE_SHOT, period=buzzSetupNotifyOnMS, callback=stopNotifyBuzz)

def stopNotifyBuzz(timer):
    stopBuzz()
    timer.init(mode=Timer.ONE_SHOT, period=buzzSetupNotifyOffMS, callback=startNotifyBuzz)
    
def doTripleBuzz():
    startBuzz()
    time.sleep_ms(buzzFlagOnMS)
    stopBuzz()
    time.sleep_ms(buzzFlagOffMS)
    
    startBuzz()
    time.sleep_ms(buzzFlagOnMS)
    stopBuzz()
    time.sleep_ms(buzzFlagOffMS)
    
    startBuzz()
    time.sleep_ms(buzzFlagOnMS)
    stopBuzz()
    # no final wait required after stopping buzz
    
def doStopClock():
#    global startstopPulldownOutput
#    global customPulldownOutput
    global greenConfigured
    
    startstopPulldownOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    startstopPulldownOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    customPulldownOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    customPulldownOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    startstopPulldownOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    startstopPulldownOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    greenConfigured = False

def doStartClock():
#    global flagPullupOutput
#    global customPulldownOutput
    global greenConfigured
    
    # trigger flag by shorting lines
    flagPullupOutput.value(activateFlagValue)	
    
    # start clock
    customPulldownOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    customPulldownOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    # restore flag
    flagPullupOutput.value(releaseFlagValue)

    # notify athlete aurally
    # (short delays above ok as sound still starts
    #  within first ~half-second of starting timer)
    doTripleBuzz()
    
    greenConfigured= True
    
def doStartup():
    global timer
#    global resetPulldownOutput
#    global onesecPulldownOutput
#    global buzzerPullupOutput
#    global customPulldownOutput
#    global countdownWholeSeconds
#    global pressButtonPauseMS
#    global betweenButtonPauseMS
#    global customUpdateHoldMS
    global finishedSetup
    
    # reset the clock to defaults
    resetPulldownOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    resetPulldownOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    led.toggle()
    
    # set up false start countdown duration    
    for addSec in range(countdownWholeSeconds):
        onesecPulldownOutput.value(activateButtonValue)
        startBuzz()
        time.sleep_ms(pressButtonPauseMS)
        
        onesecPulldownOutput.value(releaseButtonValue)
        stopBuzz()
        time.sleep_ms(betweenButtonPauseMS)
        
        led.toggle()
        
    # store the countdown in the clock's Custom button
    startNotifyBuzz(timer)	# start buzz pattern
    customPulldownOutput.value(activateButtonValue)
    time.sleep_ms(customUpdateHoldMS)
    
    timer.deinit()	# stop buzz pattern
    timer = Timer()
    customPulldownOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    led.toggle()
    
    doStopClock()
    led.toggle()
    doTripleBuzz()
    led.toggle()
    
    finishedSetup = True

################### main code
led.value(0)
doStartup()
led.value(1)

tickleCount = 0
while True:
    if greenConfigured and gogreenPulldownInput.value() == quietGoGreenValue:
        doStopClock()
    elif gogreenPulldownInput.value() == signallingGoGreenValue:
        doStartClock()
    else:
        time.sleep_ms(loopSleepMS)
        tickleCount += 1
        if tickleCount == loopsPerTickle:
            led.toggle()
            doStopClock()
            tickleCount = 0
            led.toggle()
        
        
