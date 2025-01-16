#import select
import sys

import time
#from datetime import datetime

import re
#import string

from machine import Pin, Timer

# constants
betweenButtonPauseMS = 100
pressButtonPauseMS = 100
buzzSetupNotifyOnMS = 200
buzzSetupNotifyOffMS = 800
buzzFlagOnMS = 300
buzzFlagOffMS = 200
customUpdateHoldMS = 5300

countdownWholeSeconds = 15

loopSleepMS = 50	# lag on detecting green request and red request
# does not affect false start detection because flag trigger
# is done at same time as starting clock, not when time expires

loopsPerTickle = (150*1000)/loopSleepMS	# under 3 minute auto shutdown

activateButtonValue = 1
releaseButtonValue = 0

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
onesecOutput = Pin(20, Pin.OUT)	# activate low
customOutput = Pin(26, Pin.OUT)	# activate low
resetOutput = Pin(16, Pin.OUT)	# activate low
startstopOutput = Pin(18, Pin.OUT)	# activate low

gogreenInput = Pin(6, Pin.IN, Pin.PULL_UP)	# signals low

flagOutput = Pin(10, Pin.OUT)	# activate high
buzzerOutput = Pin(12, Pin.OUT)	# activate high

led = Pin(25, Pin.OUT)

# subroutines

def startBuzz():
    buzzerOutput.value(activateBuzzerValue)
    
def stopBuzz():
    buzzerOutput.value(releaseBuzzerValue)
    
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
#    global startstopOutput
#    global customOutput
    global greenConfigured
    
    startstopOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    startstopOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    customOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    customOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    startstopOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    startstopOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    greenConfigured = False

def doStartClock():
#    global flagOutput
#    global customOutput
    global greenConfigured
    
    # trigger flag by shorting lines
    flagOutput.value(activateFlagValue)	
    
    # start clock
    customOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    customOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    
    # restore flag
    flagOutput.value(releaseFlagValue)

    # notify athlete aurally
    # (short delays above ok as sound still starts
    #  within first ~half-second of starting timer)
    doTripleBuzz()
    
    greenConfigured = True
    
def doStartup():
    global timer
#    global resetOutput
#    global onesecOutput
#    global buzzerOutput
#    global customOutput
#    global countdownWholeSeconds
#    global pressButtonPauseMS
#    global betweenButtonPauseMS
#    global customUpdateHoldMS
    global finishedSetup
    
    # reset the clock to defaults
    resetOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    resetOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    led.toggle()
    
    # set up false start countdown duration    
    for addSec in range(countdownWholeSeconds):
        onesecOutput.value(activateButtonValue)
        startBuzz()
        time.sleep_ms(pressButtonPauseMS)
        
        onesecOutput.value(releaseButtonValue)
        stopBuzz()
        time.sleep_ms(betweenButtonPauseMS)
        
        led.toggle()
        
    # store the countdown in the clock's Custom button
    startNotifyBuzz(timer)	# start buzz pattern
    customOutput.value(activateButtonValue)
    time.sleep_ms(customUpdateHoldMS)
    
    timer.deinit()	# stop buzz pattern
    timer = Timer()
    customOutput.value(releaseButtonValue)
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
    if greenConfigured and gogreenInput.value() == quietGoGreenValue:
        doStopClock()
    elif not greenConfigured and gogreenInput.value() == signallingGoGreenValue:
        doStartClock()
    else:
        time.sleep_ms(loopSleepMS)
        tickleCount += 1
        if tickleCount == loopsPerTickle:
            led.toggle()
            doStopClock()
            tickleCount = 0
            led.toggle()
        
        
