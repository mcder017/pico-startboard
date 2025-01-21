#import select
import sys

import time
#from datetime import datetime

import re
#import string

from machine import Pin, Timer

# constants
minElectricalFlagMS = 100
minCarefulStopPauseMS = 510
minPreparedStopPauseMS = 150

betweenButtonPauseMS = 100
pressButtonPauseMS = 200

buzzSetupNotifyOnMS = 50
buzzSetupNotifyOffMS = 1500

buzzAttentionOnMS = 250
buzzAttentionOffMS = 150

buzzExpiredOnMS = 500
buzzExpiredOffMS = 1500

customUpdateHoldMS = 5300

countdownWholeSeconds = 15
countdownMS = (countdownWholeSeconds*1000)

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

buzzAtStartCountdown = True
buzzAtExpire = True

signallingGoGreenValue = 0
quietGoGreenValue = 1

attentionBuzzStopCount = 2

# state variables
finishedSetup = False
greenConfigured = False
attentionBuzzCount = 0
# store time.ticks_add(time.ticks_ms(), countdownMS) when light goes green
# while still green, test time.ticks_diff(greenExpireTick, time.ticks_ms()) <= 0
# to indicate expired (not forever, but within period of minutes)
greenExpireTick = 0
expiredBuzzing = False

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
    
def startInSetupBuzz(timer):
    startBuzz()    
    timer.init(mode=Timer.ONE_SHOT, period=buzzSetupNotifyOnMS, callback=stopInSetupBuzz)

def stopInSetupBuzz(timer):
    stopBuzz()
    timer.init(mode=Timer.ONE_SHOT, period=buzzSetupNotifyOffMS, callback=startInSetupBuzz)
    
def startInSetupBuzzPattern():
    startInSetupBuzz(timer)
    
def stopBuzzPattern():	# works for notify pattern, expired pattern, ...
    global timer    
    timer.deinit()	# stop periodic or one-shot possibly still in progress
    timer = Timer()    
    stopBuzz()		# ensure buzz pattern stopped "off"
    
def startExpiredBuzz(timer):
    if buzzAtExpire:
        startBuzz()    
    timer.init(mode=Timer.ONE_SHOT, period=buzzExpiredOnMS, callback=stopExpiredBuzz)

def stopExpiredBuzz(timer):
    stopBuzz()
    timer.init(mode=Timer.ONE_SHOT, period=buzzExpiredOffMS, callback=startExpiredBuzz)
    
def startExpiredBuzzPattern():
    startExpiredBuzz(timer)
    
def startAttentionBuzz(timer):
    startBuzz()    
    timer.init(mode=Timer.ONE_SHOT, period=buzzAttentionOnMS, callback=stopAttentionBuzz)

def stopAttentionBuzz(timer):
    global attentionBuzzCount
    stopBuzz()
    attentionBuzzCount += 1
    if attentionBuzzCount < attentionBuzzStopCount:
        timer.init(mode=Timer.ONE_SHOT, period=buzzAttentionOffMS, callback=startAttentionBuzz)        
    # else done
    
def startAttentionBuzzPattern():
    global attentionBuzzCount
    attentionBuzzCount = 0
    startAttentionBuzz(timer)
    
def doPrepareClock():
    # if stopped, custom restores stored value and starts clock
    # if running, custom does nothing
    # thus, custom ensures clock is running (as long as a custom value was stored)
    customOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    customOutput.value(releaseButtonValue)
    
    time.sleep_ms(max(minPreparedStopPauseMS, betweenButtonPauseMS))

    # st-sp toggles clock running status (to stopped)
    startstopOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    startstopOutput.value(releaseButtonValue)
    
    time.sleep_ms(betweenButtonPauseMS)

def doCarefulStopClock():
    # observed custom/start-stop, done twice, as sometimes stopping 1s low.
    # seeking to avoid that visual effect by expanding the first stop steps.
    customOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    customOutput.value(releaseButtonValue)
    
    time.sleep_ms(max(minCarefulStopPauseMS, betweenButtonPauseMS))

    # st-sp toggles clock running status (to stopped)
    startstopOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    startstopOutput.value(releaseButtonValue)
    
    time.sleep_ms(max(minCarefulStopPauseMS, betweenButtonPauseMS))
    
def doEnsureStopAndPrepareClock():
    doCarefulStopClock()	# custom / st-sp ensures clock stopped (if running, custom does nothing)
    doPrepareClock()	# when already stopped, custom starts clock at stored value, st-sp stops it promptly
    
def doStartClock():
    global greenExpireTick
    
    # clock starts counting at release of custom
    # (unless held long enough to store value)
    customOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)

    # trigger flag by shorting lines
    flagOutput.value(activateFlagValue)
    
    # notify athlete aurally
    if buzzAtStartCountdown:
        startAttentionBuzzPattern()	# returns promptly (uses timer to handle buzz)
    
    # start clock
    customOutput.value(releaseButtonValue)
    greenExpireTick = time.ticks_add(time.ticks_ms(), countdownMS)	# offset from timer green by button activation duration
    
    # avoid rapid button press, and ensure electrical flag recorded
    time.sleep_ms(max(minElectricalFlagMS, betweenButtonPauseMS))
    
    # restore flag
    flagOutput.value(releaseFlagValue)

def doStartup():
    global finishedSetup
    
    # reset the clock to defaults
    resetOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    resetOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    led.toggle()
    
    # again, in case first press only woke the clock
    resetOutput.value(activateButtonValue)
    time.sleep_ms(pressButtonPauseMS)
    resetOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    led.toggle()
    
    startInSetupBuzzPattern()
    
    # set up false start countdown duration    
    for addSec in range(countdownWholeSeconds):
        onesecOutput.value(activateButtonValue)
        #startBuzz()
        time.sleep_ms(pressButtonPauseMS)
        
        onesecOutput.value(releaseButtonValue)
        #stopBuzz()
        time.sleep_ms(betweenButtonPauseMS)
        
        led.toggle()
        
    # store the countdown in the clock's Custom button
    customOutput.value(activateButtonValue)
    time.sleep_ms(customUpdateHoldMS)
    
    customOutput.value(releaseButtonValue)
    time.sleep_ms(betweenButtonPauseMS)
    led.toggle()
    
    doEnsureStopAndPrepareClock()    
    led.toggle()

    stopBuzzPattern()
    
    startAttentionBuzzPattern()
    led.toggle()
    
    finishedSetup = True

################### main code
led.value(0)
doStartup()
led.value(1)

tickleCount = 0
while True:
    if greenConfigured and gogreenInput.value() == quietGoGreenValue:
        if expiredBuzzing:
            stopBuzzPattern()
            expiredBuzzing = False
        doEnsureStopAndPrepareClock()	# avoid race condition between operator and clock
        greenConfigured = False
        tickleCount = 0	# touched buttons
        
    elif not greenConfigured and gogreenInput.value() == signallingGoGreenValue:
        doStartClock()	# sets greenExpireTick soon after electrical flag event for green light
        greenConfigured = True
        tickleCount = 0	# touched buttons
        
    else:	# may or may not be greenConfigured
        time.sleep_ms(loopSleepMS)
        tickleCount += 1
        
        if not expiredBuzzing and greenConfigured and time.ticks_diff(greenExpireTick, time.ticks_ms()) <= 0:
            # recently expired and still green
            startExpiredBuzzPattern()
            expiredBuzzing = True
        
        if tickleCount == loopsPerTickle:
            led.toggle()
            if not greenConfigured:
                doPrepareClock()		# clock known stopped
            else:
                doEnsureStopAndPrepareClock()	# if user still showing green, still keep clock awake while buzzing continues
            tickleCount = 0
            led.toggle()
        
        
