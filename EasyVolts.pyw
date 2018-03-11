import os

#importing wx files
import wx
 
#import the newly created GUI file
import EasyVoltsGUI
import serial.tools.list_ports
import serial
import configparser
from scanf import scanf
from time import sleep


def getCurrentLimit_mA(self, Uout_mV):
    if(0 == self.m_radioBox2_usbPower.GetSelection()):
        #2.5W mode
        Pmax_W = 2.5
    else:
        #5W mode
        Pmax_W = 5
    #calculate current
    if(Uout_mV > 5000):
        #stepUp mode
        Imax_mA = 525-(20*Uout_mV/1000)
    else:
        #stepDown mode
        Imax_mA = 579-(30*Uout_mV/1000)
    if(Pmax_W > 2.5):
        Imax_mA = Imax_mA*2
    return Imax_mA

def getConfig():
    myConfig = configparser.RawConfigParser()
    try:
        myConfig.read("easyvolts.conf")
        if not myConfig.has_section("port"):
            myConfig.add_section("port")
            myConfig.set("port", "name", " ")
        if not myConfig.has_section("autoset_value"):
            myConfig.add_section("autoset_value")
            myConfig.set("autoset_value", "status", "0") 
        if not myConfig.has_section("user_port"):
            myConfig.add_section("user_port")
            myConfig.set("user_port", "name", "UART(Rx,Tx)")
   
    except Exception as e:
            print('error: '+ str(e))   
    return myConfig

def saveConfig(myConfig):
    myConfig.write(open("easyvolts.conf", "w"))

def serialOpen(port) :
    ser = serial.Serial(port)
    ser.baudrate=115200*4
    ser.parity=serial.PARITY_NONE
    ser.stopbits=serial.STOPBITS_ONE
    ser.bytesize=serial.EIGHTBITS
    ser.timeout=0.1
    ser.xonxoff=False
    ser.rtscts=False
    ser.dsrdtr=False
    ser.flushInput() #flush input buffer, discarding all its contents
    return ser

def setVoltageCurrent(port, voltage_mV, current_mA) :
    msgByteArray = b'i'+bytes(str(current_mA),'utf-8') + b'\r'
    print(str(msgByteArray))
    port.write(msgByteArray)
    msgByteArray = b'u'+ bytes(str(voltage_mV),'utf-8') + b'\r'
    print(str(msgByteArray))
    port.write(msgByteArray)

#pin can be 'T' for Tx or 'R' for Rx. State can be 'h', 'l', 'z', 'r'
#pullMode can be 0(no pullUp/pullDown), 'h', 'l' - it's used only with Z state.
def setPinState(port, pin, state, pullMode) :
    if(('z' == state) and (pullMode != 0)):
        msgByteArray = bytes(str(state),'utf-8') + bytes(pin,'utf-8')  + bytes(pullMode,'utf-8') + b'\r'
    else :
        msgByteArray = bytes(str(state),'utf-8') + bytes(pin,'utf-8') + b'\r'
    print(str(msgByteArray))
    port.write(msgByteArray)

#pin can be 'T' for Tx or 'R' for Rx. pwmValue can be 0..1000 (0.1% units)
def setPinPwm(port, pin, pwmValue) :
    msgByteArray = b'p' + bytes(pin,'utf-8') + bytes(str(int(10*pwmValue)),'utf-8') + b'\r'
    print(str(msgByteArray))
    port.write(msgByteArray)

#pwmFreqDivValue can be 0..65535
def setPwmFreqDivider(port, pwmFreqDivValue) :
    port.write(b'f' + bytes(str(pwmFreqDivValue),'utf-8') + b'\r')
    
#mode can be 'U' for UART or 'M' for RS485+GPIO(Tx,Rx).
def setUserPortMode(port, mode) :
    msgByteArray = bytes(mode,'utf-8') + b'\r'
    print(str(msgByteArray))
    port.write(msgByteArray)
    
#inherit from the MainFrame created in wxFowmBuilder and create CalcFrame
class MainFrame(EasyVoltsGUI.MainFrame):
    targetVoltage_mV = 0
    targetCurrent_mA = 1000
    serialPort = 0
    config = 0
    zPullModeTx = 0 #0-noPullUp, 1-pullUp, 2-pullDown
    zPullModeRx = 0 #0-noPullUp, 1-pullUp, 2-pullDown
    
    #constructor
    def __init__(self,parent):
        #initialize parent class       
        EasyVoltsGUI.MainFrame.__init__(self,parent)
        try:
            #get config from file
            self.config = getConfig()
            #scan for available COM ports
            ports = serial.tools.list_ports.comports()
            print('number of ports: ' + str(len(ports)))
            for port in ports:
                  print(port.device + ': ' + port.hwid)                  
            #prepare choiceBox with available ports
            i = 0
            for portData in ports:
                self.m_choice1_comPort.Append(portData.device)
                if(self.config.get("port", "name") == portData.device):
                    self.m_choice1_comPort.SetSelection(i)
                    #generate CHOICE event to do all actions as if user have selected the port
                    wx.PostEvent(self.m_choice1_comPort, wx.CommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED )) 
                i = i + 1
            #prepare radioBox with user ports mode
            i = self.m_radioBoxMode.FindString(self.config.get("user_port", "name"))
            self.m_radioBoxMode.SetSelection(i)
            #set checkBox to saved state
            self.m_checkBox1_autoSetVoltage.SetValue(int(self.config.get("autoset_value", "status")))
        except Exception as e:
            print('error: '+ str(e))
 
    #wx calls this function with and 'event' object
    def controlPortSelectionHandler( self, event ):
        try:
            try:
                self.serialPort.close()
            except Exception:
                pass
            print("Open control serial port")
            self.serialPort = serialOpen(self.m_choice1_comPort.GetString(self.m_choice1_comPort.GetSelection()))
            self.m_staticText121_connectStatus.SetLabel('Port OPENED')
            self.m_staticText121_connectStatus.SetForegroundColour( wx.Colour( 255, 255, 0 ) )
            sleep(0.1)
            #generate wxEVT_RADIOBOX event to do all actions as if user have selected the user port mode. Do this after control port opening.
            wx.PostEvent(self.m_radioBoxMode, wx.CommandEvent(wx.wxEVT_RADIOBOX))
        except Exception as e:
            self.m_staticText121_connectStatus.SetLabel('Can\'t open!')
            self.m_staticText121_connectStatus.SetForegroundColour( wx.Colour( 255, 255, 0 ) )
            print('error: '+ str(e))

    def applyValuesButtonToggle( self, event ):
        try:
            Ilimit_mA = getCurrentLimit_mA(self, self.targetVoltage_mV)
            if(Ilimit_mA < self.targetCurrent_mA):
                #more power than allowed is requested. Reduce current limit to limit power at max acceptable power
                self.targetCurrent_mA = int(Ilimit_mA)
                self.m_slider2_current.SetValue(self.targetCurrent_mA)
                self.m_staticText16_targetCurrent.SetLabel(str(self.targetCurrent_mA/1000) + 'a')
            print('Set voltage:' + str(self.targetVoltage_mV) + 'mV. Set current:' + str(self.targetCurrent_mA) + 'mA.')
            setVoltageCurrent(self.serialPort, self.targetVoltage_mV, self.targetCurrent_mA)
            self.m_toggleBtn1.SetValue(False)
        except Exception as e:
            print('error: '+ str(e))

    def voltageScrollChanged( self, event ):
        try:
            self.targetVoltage_mV = self.m_slider1_voltage.GetValue()
            self.m_staticText15_targetVoltage.SetLabel(str(self.targetVoltage_mV/1000) + 'v')
            if(self.m_checkBox1_autoSetVoltage.IsChecked()):
                Ilimit_mA = getCurrentLimit_mA(self, self.targetVoltage_mV)
                if(Ilimit_mA < self.targetCurrent_mA):
                    #more power than allowed is requested. Reduce current limit to limit power at max acceptable power
                    self.targetCurrent_mA = int(Ilimit_mA)
                    self.m_slider2_current.SetValue(self.targetCurrent_mA)
                    self.m_staticText16_targetCurrent.SetLabel(str(self.targetCurrent_mA/1000) + 'a')
                setVoltageCurrent(self.serialPort, self.targetVoltage_mV, self.targetCurrent_mA)
                self.m_toggleBtn1.SetValue(False)
            else:
                self.m_toggleBtn1.SetValue(True)
        except Exception as e:
            print('error: '+ str(e))
    
    def currentScrollChanged( self, event ):
        try:
            self.targetCurrent_mA = self.m_slider2_current.GetValue()
            self.m_staticText16_targetCurrent.SetLabel(str(self.targetCurrent_mA/1000) + 'a')
            if(self.m_checkBox1_autoSetVoltage.IsChecked()):
                Ilimit_mA = getCurrentLimit_mA(self, self.targetVoltage_mV)
                if(Ilimit_mA < self.targetCurrent_mA):
                    #more power than allowed is requested. Reduce current limit to limit power at max acceptable power
                    self.targetCurrent_mA = int(Ilimit_mA);
                    self.m_slider2_current.SetValue(self.targetCurrent_mA)
                    self.m_staticText16_targetCurrent.SetLabel(str(self.targetCurrent_mA/1000) + 'a')
                setVoltageCurrent(self.serialPort, self.targetVoltage_mV, self.targetCurrent_mA)
                self.m_toggleBtn1.SetValue(False)
            else:
                self.m_toggleBtn1.SetValue(True)
        except Exception as e:
            print('error: '+ str(e))

    def guiTickTimer150ms( self, event ):
        try:
            line = str(self.serialPort.readline(), 'utf-8')
            if(len(line) > 10):
                #we recieve following line: "EasyVolts 	U(mV)=51    	^I(mA)=0". Parse it.
                parsedValues = scanf("EasyVolts 	U(mV)=%d    	%cI(mA)=%d", line)
                if(None != parsedValues):
                    self.m_staticText121_connectStatus.SetForegroundColour( wx.Colour( 0, 100, 0 ) )
                    self.m_staticText13_actualVoltage.SetLabel('{:.02f}'.format(int(parsedValues[0])/1000) + 'V')
                    self.m_staticText14_actualCurrent.SetLabel('{:.03f}'.format(int(parsedValues[2])/1000) + 'A')
                    if(parsedValues[1] == '_'):
                        self.m_staticText13_actualVoltage.SetForegroundColour( wx.Colour( 0, 0, 0 ) )
                        self.m_staticText14_actualCurrent.SetForegroundColour( wx.Colour( 0, 0, 0 ) )
                        self.m_staticText121_connectStatus.SetLabel('CONNECTED, PowerOff')
                    if(parsedValues[1] == ' '):
                        self.m_staticText13_actualVoltage.SetForegroundColour( wx.Colour( 0, 100, 0 ) )
                        self.m_staticText14_actualCurrent.SetForegroundColour( wx.Colour( 0, 100, 0 ) )
                        self.m_staticText121_connectStatus.SetLabel('CONNECTED, PowerOn')
                    if(parsedValues[1] == '^'):
                        self.m_staticText13_actualVoltage.SetForegroundColour( wx.Colour( 255, 255, 0 ) )
                        self.m_staticText14_actualCurrent.SetForegroundColour( wx.Colour( 255, 255, 0 ) )
                        self.m_staticText121_connectStatus.SetLabel('CONNECTED, Overcurrent!')
            else:
                if("T0\r\n" == line):
                    self.m_buttonTxRead.SetLabel("Read pin (0)")
                if("T1\r\n" == line):
                    self.m_buttonTxRead.SetLabel("Read pin (1)")
                if("R0\r\n" == line):
                    self.m_buttonRxRead.SetLabel("Read pin (0)")
                if("R1\r\n" == line):
                    self.m_buttonRxRead.SetLabel("Read pin (1)")
            
        except Exception as e:
            print('error: '+ str(e))

    def radioBoxModeChanged( self, event ):
        try:
            print('Set user port mode')
            self.config.set("user_port", "name", self.m_radioBoxMode.GetString(self.m_radioBoxMode.GetSelection()))
            if(0 == self.m_radioBoxMode.GetSelection()):
                setUserPortMode(self.serialPort, 'U')
                self.m_staticTextTxPin.SetLabel("Tx pin(UART)")
                self.m_staticTextRxPin.SetLabel("Rx pin(UART)")
                #PWM frequency divider
                self.m_textCtrlPwmFreqDiv.Disable()
                #Tx line controls
                self.m_buttonTxSetHigh.Disable()
                self.m_buttonTxSetLow.Disable()
                self.m_buttonTxRead.Disable()
                self.m_buttonTxSetZ.Disable()
                self.m_textCtrlTxPwm.Disable()
                #Rx line controls
                self.m_buttonRxSetHigh.Disable()
                self.m_buttonRxSetLow.Disable()
                self.m_buttonRxRead.Disable()
                self.m_buttonRxSetZ.Disable()
                self.m_textCtrlRxPwm.Disable()
            else:
                setUserPortMode(self.serialPort, 'M')
                self.m_staticTextTxPin.SetLabel("Tx pin(Z)")
                self.m_staticTextRxPin.SetLabel("Rx pin(Z)")
                #PWM frequency divider
                self.m_textCtrlPwmFreqDiv.Enable()
                #Tx line controls
                self.m_buttonTxSetHigh.Enable()
                self.m_buttonTxSetLow.Enable()
                self.m_buttonTxRead.Enable()
                self.m_buttonTxSetZ.Enable()
                self.m_textCtrlTxPwm.Enable()
                #Rx line controls
                self.m_buttonRxSetHigh.Enable()
                self.m_buttonRxSetLow.Enable()
                self.m_buttonRxRead.Enable()
                self.m_buttonRxSetZ.Enable()
                self.m_textCtrlRxPwm.Enable()
        except Exception as e:
            print('error: '+ str(e))
    
    def textCtrlPwmFreqDivEnter( self, event ):
        fDiv = int(self.m_textCtrlPwmFreqDiv.GetValue())
        #prevent entering 0 value
        if(fDiv == 0):
            fDiv = 1;
            self.m_textCtrlPwmFreqDiv.SetValue(str(fDiv))
        #show selected frequency
        if(fDiv < 240):
            self.m_staticText171_pwmFrequency.SetLabel(str(240.0/int(self.m_textCtrlPwmFreqDiv.GetValue())) + "kHz");
        else:
            self.m_staticText171_pwmFrequency.SetLabel(str(240000.0/int(self.m_textCtrlPwmFreqDiv.GetValue())) + "Hz");
        setPwmFreqDivider(self.serialPort, fDiv)
        event.Skip()
    
    def buttonTxSetHighClick( self, event ):
        setPinState(self.serialPort, 'T', 'h', 0)
        self.m_staticTextTxPin.SetLabel("Tx pin(HIGH)")
        event.Skip()
    
    def buttonRxSetHighClick( self, event ):
        setPinState(self.serialPort, 'R', 'h', 0)
        self.m_staticTextRxPin.SetLabel("Rx pin(HIGH)")
        event.Skip()
    
    def buttonTxSetLowClick( self, event ):
        setPinState(self.serialPort, 'T', 'l', 0)
        self.m_staticTextTxPin.SetLabel("Tx pin(LOW)")
        event.Skip()
    
    def buttonRxSetLowClick( self, event ):
        setPinState(self.serialPort, 'R', 'l', 0)
        self.m_staticTextRxPin.SetLabel("Rx pin(LOW)")
        event.Skip()
    
    def buttonTxReadClick( self, event ):
        setPinState(self.serialPort, 'T', 'r', 0)
        event.Skip()
    
    def buttonRxReadClick( self, event ):
        setPinState(self.serialPort, 'R', 'r', 0)
        event.Skip()
    
    def buttonTxSetZClick( self, event ):
        if(1 == self.zPullModeTx):
            #self.zPullModeTx = 1 - pullUp
            setPinState(self.serialPort, 'T','z','h')
            self.m_staticTextTxPin.SetLabel("Tx pin(Z+pU)")
        else :
            if(2 == self.zPullModeTx):
                #self.zPullModeTx = 1 - pullDown
                setPinState(self.serialPort, 'T','z','l')
                self.m_staticTextTxPin.SetLabel("Tx pin(Z+pD)")
            else :
                #self.zPullModeTx = 0 - no PullUp/PullDown
                setPinState(self.serialPort, 'T', 'z', 0)
                self.m_staticTextTxPin.SetLabel("Tx pin(Z)")
        event.Skip()
    
    def buttonRxSetZClick( self, event ):
        if(1 == self.zPullModeRx):
            #self.zPullModeRx = 1 - pullUp
            setPinState(self.serialPort, 'R', 'z', 'h')
            self.m_staticTextRxPin.SetLabel("Rx pin(Z+pU)")
        else :
            if(2 == self.zPullModeRx):
                #self.zPullModeRx = 1 - pullDown
                setPinState(self.serialPort, 'R', 'z', 'l')
                self.m_staticTextRxPin.SetLabel("Rx pin(Z+pD)")
            else :
                #self.zPullModeRx = 0 - no PullUp/PullDown
                setPinState(self.serialPort, 'R', 'z', 0)
                self.m_staticTextRxPin.SetLabel("Rx pin(Z)")
        event.Skip()
    
    def textCtrlTxPwmEnter( self, event ):
        value = float(self.m_textCtrlTxPwm.GetValue())
        if(value > 100.0):
            value = 100.0
            self.m_textCtrlTxPwm.SetValue(str(value))
        if(value < 0):
            value = 0
            self.m_textCtrlTxPwm.SetValue(str(value))
        setPinPwm(self.serialPort, 'T', value)
        self.m_staticTextTxPin.SetLabel("Tx pin(" + self.m_textCtrlTxPwm.GetValue() + "%)")
        event.Skip()
    
    def textCtrlRxPwmEnter( self, event ):
        value = float(self.m_textCtrlRxPwm.GetValue())
        if(value > 100.0):
            value = 100.0
            self.m_textCtrlRxPwm.SetValue(str(value))
        if(value < 0):
            value = 0
            self.m_textCtrlRxPwm.SetValue(str(value))
        setPinPwm(self.serialPort, 'R', value)
        self.m_staticTextRxPin.SetLabel("Rx pin(" + self.m_textCtrlRxPwm.GetValue() + "%)")
        event.Skip()

    def m_spinBtn_ZmodeRx_OnSpinUpHandler( self, event ):
        #0-noPullUp, 1-pullUp, 2-pullDown
        if(self.zPullModeRx < 2):
            self.zPullModeRx += 1 
        if(0 == self.zPullModeRx):
            self.m_buttonRxSetZ.SetLabel("Set Z-state");
        if(1 == self.zPullModeRx):
            self.m_buttonRxSetZ.SetLabel("Set Z+pullU");
        if(2 == self.zPullModeRx):
            self.m_buttonRxSetZ.SetLabel("Set Z+pullD");
        event.Skip()

    def m_spinBtn_ZmodeRx_OnSpinDownHandler( self, event ):
        #0-noPullUp, 1-pullUp, 2-pullDown
        if(self.zPullModeRx > 0):
            self.zPullModeRx -= 1
        if(0 == self.zPullModeRx):
            self.m_buttonRxSetZ.SetLabel("Set Z-state");
        if(1 == self.zPullModeRx):
            self.m_buttonRxSetZ.SetLabel("Set Z+pullU");
        if(2 == self.zPullModeRx):
            self.m_buttonRxSetZ.SetLabel("Set Z+pullD");
        event.Skip()
        
    def m_spinBtn_ZmodeTx_OnSpinUpHandler( self, event ):
        #0-noPullUp, 1-pullUp, 2-pullDown
        if(self.zPullModeTx < 2):
            self.zPullModeTx += 1
        if(0 == self.zPullModeTx):
            self.m_buttonTxSetZ.SetLabel("Set Z-state");
        if(1 == self.zPullModeTx):
            self.m_buttonTxSetZ.SetLabel("Set Z+pullU");
        if(2 == self.zPullModeTx):
            self.m_buttonTxSetZ.SetLabel("Set Z+pullD");
        event.Skip()

    def m_spinBtn_ZmodeTx_OnSpinDownHandler( self, event ):
        #0-noPullUp, 1-pullUp, 2-pullDown
        if(self.zPullModeTx > 0):
            self.zPullModeTx -= 1
        if(0 == self.zPullModeTx):
            self.m_buttonTxSetZ.SetLabel("Set Z-state");
        if(1 == self.zPullModeTx):
            self.m_buttonTxSetZ.SetLabel("Set Z+pullU");
        if(2 == self.zPullModeTx):
            self.m_buttonTxSetZ.SetLabel("Set Z+pullD");
        event.Skip()
        
    def closeProgramHandler( self, event ):
        try:
            if(self.serialPort != 0):
                self.config.set("port", "name", self.serialPort.port)
                setVoltageCurrent(self.serialPort, 0, 0)
                setUserPortMode(self.serialPort, 'M')
            if(self.m_checkBox1_autoSetVoltage.IsChecked()):
                self.config.set("autoset_value", "status", "1")
            else:
                self.config.set("autoset_value", "status", "0")    
            saveConfig(self.config)
            self.serialPort.close()
            print('exit!')
        except Exception as e:
            print('error: '+ str(e))
        self.Destroy()
	
app = wx.App(False)
frame = MainFrame(None)
frame.Show(True)
app.MainLoop()
